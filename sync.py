"""ClearVote Data Sync Script

Pulls congressional data from Congress.gov and Senate.gov,
generates AI summaries via Claude, and saves everything as
JSON files in data/synced/ for the web app to serve.

Usage:
    cd ~/Documents/Claude/Projects/clearvote
    source .venv/bin/activate
    python sync.py
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService
from app.services.ai_summary import AISummaryService

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


async def sync_members(client: CongressAPIClient, output_dir: Path, states: list[str] | None = None) -> int:
    """Fetch all current members of Congress and save to members.json."""
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
                    member["chamber"] = terms[0].get("chamber", "Unknown")
                all_members.append(member)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {state}: {e}")

    _atomic_write_json(output_dir / "members.json", {"members": all_members})
    print(f"  Saved {len(all_members)} members")
    return len(all_members)


async def sync_bills(client: CongressAPIClient, output_dir: Path, congress: int = 119) -> int:
    """Fetch bills from current Congress with pagination."""
    all_bills = []
    offset = 0
    limit = 50
    while True:
        print(f"  Fetching bills (offset={offset})...")
        try:
            data = await client.get_bills(congress=congress, offset=offset, limit=limit)
            bills = data.get("bills", [])
            if not bills:
                break
            all_bills.extend(bills)
            offset += limit
        except Exception as e:
            print(f"  WARNING: Failed at offset {offset}: {e}")
            break

    # Fetch summaries for each bill
    for i, bill in enumerate(all_bills):
        bill_type = bill.get("type", "").lower()
        bill_number = int(bill.get("number", 0))
        print(f"  Fetching summary for {bill_type.upper()}.{bill_number}... ({i + 1}/{len(all_bills)})")
        try:
            summary_data = await client.get_bill_summary(congress, bill_type, bill_number)
            bill["summaries"] = summary_data.get("summaries", [])
        except Exception as e:
            print(f"  WARNING: Failed summary for {bill_type}.{bill_number}: {e}")
            bill["summaries"] = []

    _atomic_write_json(output_dir / "bills.json", {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills")
    return len(all_bills)


async def sync_senate_votes(senate_service: SenateVoteService, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 500) -> int:
    """Fetch Senate roll call votes."""
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
        except Exception:
            print(f"  No more Senate votes after {vote_num - 1}")
            break

    print(f"  Saved {count} Senate votes")
    return count


async def sync_ai_summaries(ai_service: AISummaryService, congress_client: CongressAPIClient, output_dir: Path) -> int:
    """Generate AI summaries for bills that don't have one yet."""
    bills_path = output_dir / "bills.json"
    summaries_path = output_dir / "ai_summaries.json"

    if not bills_path.exists():
        print("  No bills.json found — skipping AI summaries")
        return 0

    with open(bills_path) as f:
        bills_data = json.load(f)

    # Load existing summaries
    existing = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    new_count = 0
    bills = bills_data.get("bills", [])
    for i, bill in enumerate(bills):
        congress = bill.get("congress", 119)
        bill_type = bill.get("type", "").lower()
        bill_number = int(bill.get("number", 0))
        bill_id = f"{congress}-{bill_type}-{bill_number}"

        if bill_id in existing:
            continue

        title = bill.get("title", "")
        summaries = bill.get("summaries", [])
        official_summary = summaries[0].get("text", "") if summaries else ""

        if not official_summary and not title:
            continue

        print(f"  Generating AI summary for {bill_id}... ({i + 1}/{len(bills)})")

        # Try to get bill text excerpt
        bill_text_excerpt = ""
        try:
            text_data = await congress_client.get_bill_text(congress, bill_type, bill_number)
            text_versions = text_data.get("textVersions", [])
            if text_versions:
                formats = text_versions[0].get("formats", [])
                for fmt in formats:
                    if fmt.get("type") == "Formatted Text":
                        import httpx
                        async with httpx.AsyncClient(timeout=10.0) as http_client:
                            resp = await http_client.get(fmt["url"])
                            if resp.status_code == 200:
                                bill_text_excerpt = resp.text[:5000]
                        break
        except Exception as e:
            print(f"  WARNING: Could not fetch bill text for {bill_id}: {e}")

        try:
            result = await ai_service.generate_summary(
                bill_id=bill_id,
                title=title,
                official_summary=official_summary,
                bill_text_excerpt=bill_text_excerpt,
            )
            existing[bill_id] = result
            new_count += 1
        except Exception as e:
            print(f"  WARNING: AI summary failed for {bill_id}: {e}")

    _atomic_write_json(summaries_path, existing)
    print(f"  Generated {new_count} new AI summaries ({len(existing)} total)")
    return new_count


async def build_member_votes(output_dir: Path) -> int:
    """Cross-reference votes with members to build per-member voting records."""
    members_path = output_dir / "members.json"
    bills_path = output_dir / "bills.json"
    senate_dir = output_dir / "votes" / "senate"
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

    # Load all senate votes
    all_votes: list[dict] = []
    if senate_dir.exists():
        for vote_file in sorted(senate_dir.glob("*.json")):
            with open(vote_file) as f:
                all_votes.append(json.load(f))

    # Build member vote records for senators
    senate_members = [m for m in members_data.get("members", []) if m.get("chamber") == "Senate"]

    count = 0
    for member in senate_members:
        bioguide_id = member["bioguideId"]
        print(f"  Building votes for {member.get('directOrderName', bioguide_id)}...")

        member_vote_list = []
        for vote in all_votes:
            member_vote = None
            for mv in vote.get("members", []):
                if mv.get("lis_member_id") == bioguide_id:
                    member_vote = mv
                    break
            if not member_vote:
                continue

            doc = vote.get("document", "")
            bill_ref = _parse_bill_ref(doc)
            bill_info = bill_lookup.get(bill_ref, {}) if bill_ref else {}

            member_vote_list.append({
                "bill_number": doc,
                "bill_id": f"119-{bill_ref}" if bill_ref else None,
                "one_liner": bill_info.get("title", doc),
                "vote": member_vote.get("vote", ""),
                "date": vote.get("vote_date", ""),
                "result": vote.get("result", ""),
                "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                "chamber": "Senate",
                "cbo_deficit_impact": None,
            })

        # Compute stats
        yea = sum(1 for v in member_vote_list if v["vote"] == "Yea")
        nay = sum(1 for v in member_vote_list if v["vote"] == "Nay")
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
    """Parse 'H.R. 1' into 'hr-1' or 'S. 100' into 's-100'."""
    doc = document.strip()
    if doc.startswith("H.R. "):
        return f"hr-{doc[5:]}"
    if doc.startswith("S. "):
        return f"s-{doc[3:]}"
    if doc.startswith("H.J.Res. "):
        return f"hjres-{doc[9:]}"
    if doc.startswith("S.J.Res. "):
        return f"sjres-{doc[9:]}"
    return None


async def main() -> None:
    api_key = os.getenv("CONGRESS_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        print("ERROR: CONGRESS_API_KEY not set in .env")
        sys.exit(1)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    client = CongressAPIClient(api_key=api_key, cache=cache)

    print("=== ClearVote Data Sync ===")
    print(f"Output: {SYNC_DIR}")
    print()

    # Step 1: Members
    print("[1/5] Syncing members...")
    members_count = await sync_members(client, SYNC_DIR)

    # Step 2: Bills
    print()
    print("[2/5] Syncing bills...")
    bills_count = await sync_bills(client, SYNC_DIR)

    # Step 3: Senate votes
    print()
    senate_service = SenateVoteService(cache=cache)
    print("[3/5] Syncing Senate votes...")
    senate_count = await sync_senate_votes(senate_service, SYNC_DIR)

    # Step 4: AI summaries
    print()
    if anthropic_key:
        ai_service = AISummaryService(api_key=anthropic_key, cache=cache)
        print("[4/5] Generating AI summaries...")
        ai_count = await sync_ai_summaries(ai_service, client, SYNC_DIR)
    else:
        print("[4/5] Skipping AI summaries (no ANTHROPIC_API_KEY)")
        ai_count = 0

    # Step 5: Member voting records
    print()
    print("[5/5] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR)

    # Write metadata
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "members_count": members_count,
        "bills_count": bills_count,
        "ai_summaries_count": ai_count,
        "senate_votes_count": senate_count,
        "member_votes_count": member_votes_count,
    }
    _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)
    print()
    print("=== Sync complete ===")
    print(f"  Members: {members_count}")
    print(f"  Bills: {bills_count}")
    print(f"  Senate votes: {senate_count}")
    print(f"  AI summaries: {ai_count}")
    print(f"  Member vote records: {member_votes_count}")


if __name__ == "__main__":
    asyncio.run(main())
