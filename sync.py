"""ClearVote Data Sync Script

Pulls congressional data from Congress.gov and Senate.gov
and saves everything as JSON files in data/synced/ for the
web app to serve.

Usage:
    cd ~/Documents/Claude/Projects/clearvote
    source .venv/bin/activate
    python sync.py --states NY,FL
    python sync.py                    # all states
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService

BASE_DIR = Path(__file__).parent
SYNC_DIR = BASE_DIR / "data" / "synced"
CACHE_DIR = BASE_DIR / "data" / "cache"

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI",
]


def _atomic_write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


async def sync_members(client: CongressAPIClient, output_dir: Path, states: list[str] | None = None, rate_limit: float = 0.0) -> int:
    """Fetch current members of Congress for given states and save to members.json."""
    states = states or US_STATES
    all_members = []
    for i, state in enumerate(states):
        print(f"  Fetching members for {state}... ({i + 1}/{len(states)})")
        try:
            data = await client.get_members_by_state(state)
            for member in data.get("members", []):
                member["stateCode"] = state
                terms = member.get("terms", {}).get("item", [])
                if terms:
                    member["chamber"] = terms[-1].get("chamber", "Unknown")
                all_members.append(member)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {state}: {e}")
        await asyncio.sleep(rate_limit)

    _atomic_write_json(output_dir / "members.json", {"members": all_members})
    print(f"  Saved {len(all_members)} members")
    return len(all_members)


async def sync_senate_votes(senate_service: SenateVoteService, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 500, rate_limit: float = 0.0) -> int:
    """Fetch Senate roll call votes. Incremental — skips already-downloaded votes."""
    vote_dir = output_dir / "votes" / "senate"
    vote_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for vote_num in range(1, max_vote + 1):
        filename = f"{congress}_{session}_{vote_num:05d}.json"
        filepath = vote_dir / filename

        # Skip if already synced (incremental)
        if filepath.exists():
            count += 1
            continue

        print(f"  Fetching Senate vote {vote_num}...")
        try:
            data = await senate_service.get_vote(congress, session, vote_num)
            _atomic_write_json(filepath, data)
            count += 1
            await asyncio.sleep(rate_limit)
        except Exception:
            print(f"  No more Senate votes after {vote_num - 1}")
            break

    print(f"  Saved {count} Senate votes")
    return count


def _house_leg_to_document(leg_type: str | None, leg_number: str | None) -> str:
    """Convert House API legislationType/Number to document string matching bill ref format.

    Examples: ('HR', '153') -> 'H.R. 153', ('S', '100') -> 'S. 100',
              ('HJRES', '42') -> 'H.J.Res. 42', ('HRES', '5') -> 'H.Res. 5'
    """
    if not leg_type or not leg_number:
        return ""
    mapping = {
        "HR": f"H.R. {leg_number}",
        "S": f"S. {leg_number}",
        "HJRES": f"H.J.Res. {leg_number}",
        "SJRES": f"S.J.Res. {leg_number}",
        "HRES": f"H.Res. {leg_number}",
        "SRES": f"S.Res. {leg_number}",
        "HCONRES": f"H.Con.Res. {leg_number}",
        "SCONRES": f"S.Con.Res. {leg_number}",
    }
    return mapping.get(leg_type.upper(), f"{leg_type} {leg_number}")


async def sync_house_votes(client: CongressAPIClient, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 500, rate_limit: float = 0.0) -> int:
    """Fetch House roll call votes from Congress.gov API. Incremental — skips existing files."""
    vote_dir = output_dir / "votes" / "house"
    vote_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for vote_num in range(1, max_vote + 1):
        filename = f"{congress}_{session}_{vote_num:05d}.json"
        filepath = vote_dir / filename

        if filepath.exists():
            count += 1
            continue

        print(f"  Fetching House vote {vote_num}...")
        try:
            detail_resp = await client.get_house_vote_detail(congress, session, vote_num)
            vote_data = detail_resp.get("houseRollCallVote", {})

            members_resp = await client.get_house_vote_members(congress, session, vote_num)
            members_data = members_resp.get("houseRollCallVoteMemberVotes", {}).get("results", [])

            # Build counts from votePartyTotal
            party_totals = vote_data.get("votePartyTotal", [])
            yeas = sum(p.get("yeaTotal", 0) for p in party_totals)
            nays = sum(p.get("nayTotal", 0) for p in party_totals)
            not_voting = sum(p.get("notVotingTotal", 0) for p in party_totals)
            present = sum(p.get("presentTotal", 0) for p in party_totals)

            document = _house_leg_to_document(
                vote_data.get("legislationType"),
                vote_data.get("legislationNumber"),
            )

            # Normalize to same schema as Senate votes
            normalized = {
                "congress": vote_data.get("congress", congress),
                "session": vote_data.get("sessionNumber", session),
                "vote_number": vote_data.get("rollCallNumber", vote_num),
                "vote_date": vote_data.get("startDate", "")[:10],
                "question": vote_data.get("voteQuestion", ""),
                "document": document,
                "result": vote_data.get("result", ""),
                "title": "",
                "counts": {
                    "yeas": yeas,
                    "nays": nays,
                    "present": present,
                    "absent": not_voting,
                },
                "members": [
                    {
                        "bioguide_id": m.get("bioguideID", ""),
                        "first_name": m.get("firstName", ""),
                        "last_name": m.get("lastName", ""),
                        "party": m.get("voteParty", ""),
                        "state": m.get("voteState", ""),
                        "vote": m.get("voteCast", ""),
                    }
                    for m in members_data
                ],
                "chamber": "House",
            }

            _atomic_write_json(filepath, normalized)
            count += 1
            await asyncio.sleep(rate_limit)
        except Exception:
            print(f"  No more House votes after {vote_num - 1}")
            break

    print(f"  Saved {count} House votes")
    return count


async def sync_bills_from_votes(client: CongressAPIClient, output_dir: Path, congress: int = 119, rate_limit: float = 0.0) -> int:
    """Fetch only bills referenced in Senate and House vote documents. Incremental."""
    bills_path = output_dir / "bills.json"

    # Collect unique bill references from both Senate and House vote files
    bill_refs: set[str] = set()
    for chamber_dir in ["senate", "house"]:
        vote_dir = output_dir / "votes" / chamber_dir
        if not vote_dir.exists():
            continue
        for vote_file in sorted(vote_dir.glob("*.json")):
            with open(vote_file) as f:
                vote = json.load(f)
            ref = _parse_bill_ref(vote.get("document", ""))
            if ref:
                bill_refs.add(ref)

    if not bill_refs:
        print("  No bill references found in votes — skipping")
        return 0

    print(f"  Found {len(bill_refs)} unique bills referenced in votes")

    # Load existing bills to skip already-fetched ones
    existing_bills: list[dict] = []
    existing_keys: set[str] = set()
    if bills_path.exists():
        with open(bills_path) as f:
            existing_bills = json.load(f).get("bills", [])
        for b in existing_bills:
            key = f"{b.get('type', '').lower()}-{b.get('number', '')}"
            existing_keys.add(key)

    # Fetch new bills
    new_bills = []
    refs_to_fetch = sorted(bill_refs - existing_keys)
    for i, ref in enumerate(refs_to_fetch):
        parts = ref.rsplit("-", 1)
        if len(parts) != 2:
            continue
        bill_type, bill_number_str = parts

        print(f"  Fetching {bill_type.upper()} {bill_number_str}... ({i + 1}/{len(refs_to_fetch)})")
        try:
            data = await client.get_bill(congress, bill_type, int(bill_number_str))
            bill = data.get("bill", {})

            # Also fetch official summary
            try:
                summary_data = await client.get_bill_summary(congress, bill_type, int(bill_number_str))
                bill["summaries"] = summary_data.get("summaries", [])
            except Exception:
                bill["summaries"] = []

            new_bills.append(bill)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {ref}: {e}")
        await asyncio.sleep(rate_limit)

    all_bills = existing_bills + new_bills
    _atomic_write_json(bills_path, {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills ({len(new_bills)} new)")
    return len(all_bills)


async def sync_bill_summaries(
    output_dir: Path,
    api_key: str,
    batch_size: int = 5,
    rate_limit: float = 1.0,
) -> dict:
    """Generate AI summaries for all bills through the writer-grader loop.

    Processes in batches to prevent context degradation.
    Returns stats dict with pass/fail counts.
    """
    from app.services.ai_summary import AISummaryService
    from app.services.summary_grader import SummaryGrader
    from app.services.writer_grader_loop import WriterGraderLoop
    from app.services.grader_learnings import GraderLearnings

    bills_path = output_dir / "bills.json"
    summaries_path = output_dir / "ai_summaries.json"
    learnings_path = output_dir / "grader_learnings.json"

    if not bills_path.exists():
        print("  No bills.json — skipping AI summaries")
        return {"total": 0, "passed": 0, "failed": 0}

    with open(bills_path) as f:
        bills = json.load(f).get("bills", [])

    # Load existing summaries (incremental)
    existing: dict[str, dict] = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    # Setup services
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    writer_service = AISummaryService(api_key=api_key, cache=cache)
    grader = SummaryGrader(api_key=api_key)

    # Load learnings
    learnings_store = GraderLearnings(learnings_path)
    grader.load_learnings(learnings_store.get_learnings())

    # Find bills needing summaries
    to_process = []
    for bill in bills:
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", 119)
        key = f"{congress}-{bill_type}-{bill_number}"
        if key not in existing:
            to_process.append((key, bill))

    if not to_process:
        print("  All bills already have summaries — skipping")
        return {"total": 0, "passed": 0, "failed": 0}

    print(f"  Generating summaries for {len(to_process)} bills (batch size: {batch_size})")

    stats: dict = {"total": 0, "passed": 0, "failed": 0, "needs_review": []}
    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    all_feedback: list[str] = []

    for batch_start in range(0, len(to_process), batch_size):
        batch = to_process[batch_start:batch_start + batch_size]
        print(f"  Batch {batch_start // batch_size + 1}/{(len(to_process) + batch_size - 1) // batch_size}")

        for key, bill in batch:
            bill_id = key
            title = bill.get("title", "")
            summaries = bill.get("summaries", [])
            official_summary = summaries[0].get("text", "") if summaries else ""
            bill_text = bill.get("textVersions", [{}])[0].get("text", "") if bill.get("textVersions") else ""

            print(f"    Grading: {title[:60]}...")

            async def writer_fn(grader_feedback=None, _bill_id=bill_id, _title=title, _official_summary=official_summary, _bill_text=bill_text, **kwargs):
                return await writer_service.generate_summary(
                    bill_id=_bill_id,
                    title=_title,
                    official_summary=_official_summary,
                    bill_text_excerpt=_bill_text[:2000],
                    grader_feedback=grader_feedback,
                )

            loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
            result = await loop.run(
                summary_type="bill_summary",
                writer_kwargs={},
                grader_context={"title": title, "official_summary": official_summary},
            )

            summary_data = result.best_summary
            if result.needs_review:
                summary_data["needs_review"] = True
                stats["needs_review"].append(key)
                stats["failed"] += 1
            else:
                stats["passed"] += 1

            existing[key] = summary_data
            stats["total"] += 1
            grade_dist[result.best_grade.grade] = grade_dist.get(result.best_grade.grade, 0) + 1
            all_feedback.append(result.best_grade.feedback)

            await asyncio.sleep(rate_limit)

        # Save after each batch (crash-safe)
        _atomic_write_json(summaries_path, existing)

    # Extract new learnings
    new_patterns = learnings_store.extract_patterns(all_feedback)
    for pattern in new_patterns:
        learnings_store.add_learning(pattern)

    learnings_store.record_batch(
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        grade_distribution=grade_dist,
        needs_review_ids=stats["needs_review"],
    )
    learnings_store.save()

    print(f"  Summaries: {stats['passed']} passed, {stats['failed']} flagged for review")
    print(f"  Grades: {grade_dist}")
    if stats["needs_review"]:
        print(f"  Needs review: {stats['needs_review']}")

    return stats


async def build_member_votes(output_dir: Path, anthropic_key: str | None = None) -> int:
    """Cross-reference votes with members to build per-member voting records.

    When anthropic_key is set, vote one-liners will be generated through
    the writer-grader loop (not yet implemented — currently uses _get_one_liner fallback).
    """
    members_path = output_dir / "members.json"
    bills_path = output_dir / "bills.json"
    member_votes_dir = output_dir / "member_votes"
    member_votes_dir.mkdir(parents=True, exist_ok=True)

    if not members_path.exists():
        print("  No members.json — skipping")
        return 0

    with open(members_path) as f:
        members_data = json.load(f)

    # Build bill lookup for policy areas and titles
    bill_lookup: dict[str, dict] = {}
    if bills_path.exists():
        with open(bills_path) as f:
            bills_data = json.load(f)
        for bill in bills_data.get("bills", []):
            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number", "")
            key = f"{bill_type}-{bill_number}"
            bill_lookup[key] = bill

    # Load AI summaries for one_liner lookup
    ai_summaries: dict[str, dict] = {}
    ai_summaries_path = output_dir / "ai_summaries.json"
    if ai_summaries_path.exists():
        try:
            with open(ai_summaries_path) as f:
                ai_summaries = json.load(f)
        except json.JSONDecodeError:
            print("  Warning: ai_summaries.json is malformed — using raw titles")
            ai_summaries = {}

    def _get_one_liner(bill_ref: str | None, bill_info: dict, doc: str) -> str:
        if bill_ref:
            summary_key = f"119-{bill_ref}"
            ai_summary = ai_summaries.get(summary_key, {})
            if ai_summary.get("one_liner"):
                return ai_summary["one_liner"]
        return bill_info.get("title", doc)

    # Load all votes from both chambers
    senate_votes: list[dict] = []
    senate_dir = output_dir / "votes" / "senate"
    if senate_dir.exists():
        for vote_file in sorted(senate_dir.glob("*.json")):
            with open(vote_file) as f:
                senate_votes.append(json.load(f))

    house_votes: list[dict] = []
    house_dir = output_dir / "votes" / "house"
    if house_dir.exists():
        for vote_file in sorted(house_dir.glob("*.json")):
            with open(vote_file) as f:
                house_votes.append(json.load(f))

    all_members = members_data.get("members", [])
    count = 0

    for member in all_members:
        bioguide_id = member["bioguideId"]
        chamber = member.get("chamber", "")
        member_last = member.get("name", "").split(",")[0].strip().lower()
        member_state = member.get("stateCode", "").upper()

        print(f"  Building votes for {member.get('directOrderName', bioguide_id)}...")

        member_vote_list = []

        if chamber == "Senate":
            # Match Senate votes by last name + state (Senate XML uses names, not bioguide IDs)
            for vote in senate_votes:
                matched = None
                for mv in vote.get("members", []):
                    if (mv.get("last_name", "").lower() == member_last
                            and mv.get("state", "").upper() == member_state):
                        matched = mv
                        break
                if not matched:
                    continue

                doc = vote.get("document", "")
                bill_ref = _parse_bill_ref(doc)
                bill_info = bill_lookup.get(bill_ref, {}) if bill_ref else {}

                member_vote_list.append({
                    "bill_number": doc,
                    "bill_id": f"119-{bill_ref}" if bill_ref else None,
                    "one_liner": _get_one_liner(bill_ref, bill_info, doc),
                    "vote": matched.get("vote", ""),
                    "date": vote.get("vote_date", ""),
                    "result": vote.get("result", ""),
                    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                    "chamber": "Senate",
                    "cbo_deficit_impact": None,
                })

        elif chamber == "House of Representatives":
            # Match House votes by bioguide ID (Congress.gov API provides bioguide IDs)
            for vote in house_votes:
                matched = None
                for mv in vote.get("members", []):
                    if mv.get("bioguide_id", "") == bioguide_id:
                        matched = mv
                        break
                if not matched:
                    continue

                doc = vote.get("document", "")
                bill_ref = _parse_bill_ref(doc)
                bill_info = bill_lookup.get(bill_ref, {}) if bill_ref else {}

                member_vote_list.append({
                    "bill_number": doc,
                    "bill_id": f"119-{bill_ref}" if bill_ref else None,
                    "one_liner": _get_one_liner(bill_ref, bill_info, doc),
                    "vote": matched.get("vote", ""),
                    "date": vote.get("vote_date", ""),
                    "result": vote.get("result", ""),
                    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                    "chamber": "House",
                    "cbo_deficit_impact": None,
                })

        # Compute stats
        yea = sum(1 for v in member_vote_list if v["vote"] in ("Yea", "Aye"))
        nay = sum(1 for v in member_vote_list if v["vote"] in ("Nay", "No"))
        not_voting = sum(1 for v in member_vote_list if v["vote"] == "Not Voting")
        total = len(member_vote_list)
        participation = round((yea + nay) / total * 100, 1) if total > 0 else 0

        policy_areas = sorted(set(v["policy_area"] for v in member_vote_list if v["policy_area"]))

        record = {
            "member_id": bioguide_id,
            "congress": 119,
            "stats": {
                "total_votes": total,
                "yea_count": yea,
                "nay_count": nay,
                "not_voting_count": not_voting,
                "participation_rate": participation,
            },
            "scorecard": [],
            "votes": sorted(member_vote_list, key=lambda v: v["date"], reverse=True),
            "policy_areas": policy_areas,
        }
        _atomic_write_json(member_votes_dir / f"{bioguide_id}.json", record)
        count += 1

    print(f"  Built voting records for {count} members")
    return count


def _parse_bill_ref(document: str) -> str | None:
    """Parse bill document strings into normalized refs.

    Examples: 'H.R. 1' -> 'hr-1', 'S. 100' -> 's-100',
              'H.J.Res. 42' -> 'hjres-42', 'H.Res. 5' -> 'hres-5',
              'H.Con.Res. 14' -> 'hconres-14'
    """
    doc = document.strip()
    prefixes = [
        ("H.Con.Res. ", "hconres-"),
        ("S.Con.Res. ", "sconres-"),
        ("H.J.Res. ", "hjres-"),
        ("S.J.Res. ", "sjres-"),
        ("H.Res. ", "hres-"),
        ("S.Res. ", "sres-"),
        ("H.R. ", "hr-"),
        ("S. ", "s-"),
    ]
    for prefix, ref_prefix in prefixes:
        if doc.startswith(prefix):
            return f"{ref_prefix}{doc[len(prefix):]}"
    return None


async def main() -> None:
    parser = argparse.ArgumentParser(description="ClearVote Data Sync")
    parser.add_argument("--states", type=str, default=None,
                        help="Comma-separated state codes (e.g., NY,FL). Default: all states.")
    parser.add_argument("--grade", action="store_true",
                        help="Re-grade existing AI summaries without re-syncing source data.")
    args = parser.parse_args()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # --- Re-grade mode ---
    if args.grade:
        if not anthropic_key:
            print("ERROR: ANTHROPIC_API_KEY not set — cannot grade without it")
            sys.exit(1)

        SYNC_DIR.mkdir(parents=True, exist_ok=True)

        print("=== ClearVote Re-Grade Mode ===")
        print("Re-grading all existing AI summaries...")
        print()

        # Back up and clear existing summaries to force re-generation
        summaries_path = SYNC_DIR / "ai_summaries.json"
        if summaries_path.exists():
            backup_path = SYNC_DIR / "ai_summaries.backup.json"
            shutil.copy2(summaries_path, backup_path)
            print(f"  Backed up existing summaries to {backup_path.name}")
            _atomic_write_json(summaries_path, {})

        print()
        print("[1/2] Re-grading bill summaries...")
        await sync_bill_summaries(SYNC_DIR, anthropic_key, batch_size=5, rate_limit=1.0)

        print()
        print("[2/2] Re-building member voting records...")
        await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)

        print()
        print("=== Re-grade complete ===")
        return

    # --- Normal sync mode ---
    states = [s.strip().upper() for s in args.states.split(",")] if args.states else None

    api_key = os.getenv("CONGRESS_API_KEY", "")
    if not api_key:
        print("ERROR: CONGRESS_API_KEY not set in .env")
        sys.exit(1)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    client = CongressAPIClient(api_key=api_key, cache=cache)

    state_label = ", ".join(states) if states else "all states"
    print("=== ClearVote Data Sync ===")
    print(f"States: {state_label}")
    print(f"Output: {SYNC_DIR}")
    print()

    # Step 1: Members
    print("[1/7] Syncing members...")
    members_count = await sync_members(client, SYNC_DIR, states=states, rate_limit=0.5)

    # Step 2: Senate votes
    print()
    senate_service = SenateVoteService(cache=cache)
    print("[2/7] Syncing Senate votes...")
    senate_count = await sync_senate_votes(senate_service, SYNC_DIR, rate_limit=0.3)

    # Step 3: House votes
    print()
    print("[3/7] Syncing House votes...")
    house_count = await sync_house_votes(client, SYNC_DIR, rate_limit=0.3)

    # Step 4: Bills (only those referenced in votes from both chambers)
    print()
    print("[4/7] Syncing voted-on bills...")
    bills_count = await sync_bills_from_votes(client, SYNC_DIR, rate_limit=0.5)

    # Step 5: AI bill summaries (writer-grader loop)
    if anthropic_key:
        print()
        print("[5/7] Generating graded AI bill summaries...")
        summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key, batch_size=5, rate_limit=1.0)
    else:
        print()
        print("[5/7] Skipping AI summaries — ANTHROPIC_API_KEY not set")
        summary_stats = {"total": 0}

    # Step 6: Member voting records (both chambers)
    print()
    print("[6/7] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)

    # Step 7: Grader report
    print()
    print("[7/7] Sync summary")

    # Write metadata
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "states_synced": states or US_STATES,
        "members_count": members_count,
        "bills_count": bills_count,
        "senate_votes_count": senate_count,
        "house_votes_count": house_count,
        "member_votes_count": member_votes_count,
        "summary_stats": summary_stats,
    }
    _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)
    print()
    print("=== Sync complete ===")
    print(f"  Members: {members_count}")
    print(f"  Bills: {bills_count}")
    print(f"  Senate votes: {senate_count}")
    print(f"  House votes: {house_count}")
    print(f"  Member vote records: {member_votes_count}")
    if summary_stats.get("total"):
        print(f"  AI summaries graded: {summary_stats['total']} ({summary_stats.get('passed', 0)} passed)")


if __name__ == "__main__":
    asyncio.run(main())
