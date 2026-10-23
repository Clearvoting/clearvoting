"""ClearVote Data Sync Script

Pulls congressional data from Congress.gov and Senate.gov
and saves everything as JSON files in data/synced/ for the
web app to serve.

Usage:
    cd ~/Claude/Projects/Non-Profit/ClearVote
    source .venv/bin/activate

    # Full sync (all 8 steps):
    python sync.py

    # Government data only (for GitHub Actions Saturday cron):
    python sync.py --skip-ai

    # AI bill summaries only (for the Sunday ai-sync workflow):
    python sync.py --ai-only

    # Override default states:
    python sync.py --states NY,FL,CA,TX

    # Skip campaign finance:
    python sync.py --skip-ai --skip-donations
"""

import argparse
import asyncio
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import aclosing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv

load_dotenv()

from app.render import parse_threshold, plain_question, question_class
from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.data_service import (
    CURRENT_CONGRESS, _latest_official_summary, _parse_vote_date, roll_call_key, state_overview_payload,
)
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

# Congress/session pairs to sync — add older congresses to expand history
# Each congress has 2 sessions (odd year = session 1, even year = session 2)
CONGRESSES = [
    (117, 1), (117, 2),
    (118, 1), (118, 2),
    (119, 1), (119, 2),
]

# Default states to sync — update this list when expanding coverage
# The --states CLI flag overrides this. Previously defaulted to all 50+ states/territories.
SYNC_STATES = ["NY", "FL", "CA", "TX"]

# Sanity floors for member counts, set 2 below full delegation size (House
# districts + 2 senators) so vacant seats don't abort the sync while still
# catching truncated API responses (e.g. an unpaginated single page of 20).
# States not listed are unchecked.
MEMBER_COUNT_FLOORS = {"NY": 26, "FL": 28, "CA": 52, "TX": 38}

# Every real bioguide ID is one capital letter and six digits (the app routes and the
# og-card builder rely on the same shape). Sync turns IDs into file names, so an ID of
# any other shape from upstream never reaches a path (F050). Always use fullmatch.
_BIOGUIDE_RE = re.compile(r"^[A-Z]\d{6}$")


def _is_bioguide_id(value) -> bool:
    return isinstance(value, str) and _BIOGUIDE_RE.fullmatch(value) is not None


def _atomic_write_json(path: Path, data: dict | list, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            if compact:
                json.dump(data, f, separators=(",", ":"), sort_keys=True)
            else:
                json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _ai_summaries_digest(sync_dir: Path) -> str | None:
    path = sync_dir / "ai_summaries.json"
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ai_summaries_stamp(sync_dir: Path, rewrote: bool = False, today: str | None = None) -> dict:
    """The `ai_summaries_updated` date (spec §7.4) plus the file digest it was stamped
    against, for the next sync_metadata.json write.

    - The previous date is carried forward.
    - It becomes today when this run rewrote ai_summaries.json (`rewrote`), or when
      the file's digest differs from the one stored at the last metadata write. That
      second case catches --audit and --regenerate runs, which write no metadata.
    - A first write with no stored digest carries the date and records the digest.
    """
    try:
        previous = json.loads((sync_dir / "sync_metadata.json").read_text())
    except (OSError, ValueError):
        previous = {}
    if not isinstance(previous, dict):
        previous = {}
    digest = _ai_summaries_digest(sync_dir)
    updated = previous.get("ai_summaries_updated")
    stored = previous.get("ai_summaries_digest")
    if rewrote or (stored is not None and stored != digest):
        updated = today or datetime.now(timezone.utc).date().isoformat()
    stamp: dict = {"ai_summaries_digest": digest}
    if updated:
        stamp["ai_summaries_updated"] = updated
    return stamp


def _write_derived_json(path: Path, payload: dict, compact: bool = False) -> bool:
    """Write a file derived from other synced files, stamped with generated_at.

    When the stamp is the only thing that would change, the file is left alone, so a rebuild
    from unchanged inputs is byte-identical (the PR's reproducibility gate) and the weekly
    workflow commits nothing. Returns True when it wrote the file."""
    if path.exists():
        try:
            with open(path) as f:
                previous = json.load(f)
        except (json.JSONDecodeError, OSError):
            previous = None
        if isinstance(previous, dict):
            previous.pop("generated_at", None)
            if previous == payload:
                return False
    stamped = {**payload, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _atomic_write_json(path, stamped, compact=compact)
    return True


async def sync_members(client: CongressAPIClient, output_dir: Path, states: list[str] | None = None, rate_limit: float = 0.0) -> int:
    """Fetch current members of Congress for given states and save to members.json."""
    states = states or US_STATES
    all_members = []
    state_counts: dict[str, int] = {}
    for i, state in enumerate(states):
        print(f"  Fetching members for {state}... ({i + 1}/{len(states)})")
        try:
            data = await client.get_members_by_state(state)
            members = []
            for member in data.get("members", []):
                if not _is_bioguide_id(member.get("bioguideId")):
                    print(f"  WARNING: dropping {state} member with malformed bioguideId {member.get('bioguideId')!r}")
                    continue
                members.append(member)
            for member in members:
                member["stateCode"] = state
                terms = member.get("terms", {}).get("item", [])
                if terms:
                    member["chamber"] = terms[-1].get("chamber", "Unknown")
                all_members.append(member)
            state_counts[state] = len(members)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {state}: {e}")
        await asyncio.sleep(rate_limit)

    # Sanity check before writing — a floored state below its minimum means
    # the API returned truncated data (this is what shipped 20-member states).
    for state in states:
        floor = MEMBER_COUNT_FLOORS.get(state)
        if floor is not None and state_counts.get(state, 0) < floor:
            raise RuntimeError(
                f"Member sync sanity check failed: {state} returned "
                f"{state_counts.get(state, 0)} members, expected at least {floor}. "
                "Not writing members.json."
            )

    _atomic_write_json(output_dir / "members.json", {"members": all_members})
    print(f"  Saved {len(all_members)} members")
    return len(all_members)


# --- Roll-call fetch errors (F032) ---------------------------------------------------
# Only a definite "no such roll call" ends a session's vote loop quietly: api.congress.gov
# answers 404, and senate.gov answers 301 to this page (both checked 2026-10-21). Any other
# fetch error (timeout, 403/429/5xx, unparseable body) is retried after each of
# _VOTE_RETRY_WAITS seconds (a longer Retry-After wins, up to _VOTE_RETRY_MAX_WAIT). An error
# that outlasts the retries, or a payload _vote_payload_problem rejects, stops that session
# with an ERROR, and the step exits non-zero once every session has run. The waits keep six
# failing sessions well inside the workflow's 15/25-minute step timeouts.
_SENATE_VOTE_MISSING_PAGE = "/legislative/roll-call-vote-not-available.htm"
_VOTE_RETRY_WAITS = (5, 15)
_VOTE_RETRY_MAX_WAIT = 30


def _error_summary(exc: Exception) -> str:
    """One printable line for an upstream error. An HTTP error gives its status and URL
    path only: httpx's own message repeats the full URL, query string included (F047)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code} for {exc.request.url.path}"
    return type(exc).__name__


def _vote_not_found(exc: Exception) -> bool:
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    response = exc.response
    if response.status_code == 404:
        return True
    return response.is_redirect and response.headers.get("location", "").endswith(_SENATE_VOTE_MISSING_PAGE)


def _retry_wait(exc: Exception, default: float) -> float:
    """`default`, or a longer Retry-After (seconds form) capped at _VOTE_RETRY_MAX_WAIT."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            asked = float(exc.response.headers.get("retry-after", ""))
        except ValueError:
            return default
        return max(default, min(asked, _VOTE_RETRY_MAX_WAIT))
    return default


async def _fetch_vote(fetch, *args):
    """`await fetch(*args)` with retries. Returns None when upstream says the roll call does
    not exist; re-raises the last error once the retries are used up."""
    for wait in (*_VOTE_RETRY_WAITS, None):
        try:
            return await fetch(*args)
        except Exception as e:
            if _vote_not_found(e):
                return None
            if wait is None:
                raise
            delay = _retry_wait(e, wait)
            print(f"    {_error_summary(e)} — retrying in {delay:g}s")
            await asyncio.sleep(delay)


def _vote_payload_problem(vote) -> str | None:
    """Why a fetched roll call must not be written, or None. A written file is never
    fetched again, so a vote with no readable date or no member list stays unwritten."""
    if not isinstance(vote, dict):
        return "payload is not an object"
    if _parse_vote_date(str(vote.get("vote_date") or "")) is None:
        return f"unreadable vote_date {vote.get('vote_date')!r}"
    if not isinstance(vote.get("members"), list) or not vote["members"]:
        return "empty member list"
    return None


def _record_vote_failure(failures: list[str] | None, label: str, reason: str) -> None:
    print(f"  ERROR: {label}: {reason} — stopping this session; votes saved so far are kept")
    if failures is not None:
        failures.append(f"{label}: {reason}")


def _exit_on_vote_failures(failures: list[str]) -> None:
    """Exit 1, after every session has run, when any session stopped on an error."""
    if failures:
        print(f"ERROR: {len(failures)} vote session(s) stopped early:")
        for failure in failures:
            print(f"  {failure}")
        sys.exit(1)


async def sync_senate_votes(senate_service: SenateVoteService, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 1500, rate_limit: float = 0.0, failures: list[str] | None = None) -> int:
    """Fetch Senate roll call votes. Incremental — skips already-downloaded votes.

    Ends at the first roll call senate.gov does not have. Any other error is retried, then
    printed as an ERROR and appended to `failures` (see _fetch_vote)."""
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
        label = f"Senate {congress}-{session} vote {vote_num}"
        try:
            data = await _fetch_vote(senate_service.get_vote, congress, session, vote_num)
        except Exception as e:
            _record_vote_failure(failures, label, _error_summary(e))
            break
        if data is None:
            print(f"  No more Senate votes after {vote_num - 1}")
            break
        problem = _vote_payload_problem(data)
        if problem:
            _record_vote_failure(failures, label, problem)
            break
        _atomic_write_json(filepath, data)
        count += 1
        await asyncio.sleep(rate_limit)

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


async def sync_house_votes(client: CongressAPIClient, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 1500, rate_limit: float = 0.0, failures: list[str] | None = None) -> int:
    """Fetch House roll call votes from Congress.gov API. Incremental — skips existing files.

    Ends at the first roll call the API answers 404 for. Any other error is retried, then
    printed as an ERROR and appended to `failures` (see _fetch_vote)."""
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
        label = f"House {congress}-{session} vote {vote_num}"
        try:
            detail_resp = await _fetch_vote(client.get_house_vote_detail, congress, session, vote_num)
            if detail_resp is None:
                print(f"  No more House votes after {vote_num - 1}")
                break
            vote_data = detail_resp.get("houseRollCallVote", {})

            # A 404 here (detail found, member list not) leaves the list empty, which
            # _vote_payload_problem then reports.
            members_resp = await _fetch_vote(client.get_house_vote_members, congress, session, vote_num) or {}
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
                "vote_date": (vote_data.get("startDate") or "")[:10],
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
        except Exception as e:
            _record_vote_failure(failures, label, _error_summary(e))
            break
        problem = _vote_payload_problem(normalized)
        if problem:
            _record_vote_failure(failures, label, problem)
            break
        _atomic_write_json(filepath, normalized)
        count += 1
        await asyncio.sleep(rate_limit)

    print(f"  Saved {count} House votes")
    return count


# Stored bill records are re-fetched too (F002). A record used to be fetched once, so its
# laws, latestAction and summaries kept their first values and enacted bills never showed
# "Became law". Every record from an earlier Congress was first fetched after that Congress
# ended, so only current-Congress records can be stale.
BILL_REFRESH_CAP = 80   # re-fetches per run, most urgent first; new bills are not capped
BILL_REFRESH_DAYS = 7   # the sweep re-checks a current-Congress bill with no law after a week
_LAW_TYPES = frozenset({"hr", "s", "hjres", "sjres"})  # simple and concurrent resolutions never become law
_FINAL_TEXT_TYPES = frozenset({"Enrolled Bill", "Public Law"})


def _bill_key(bill: dict) -> str:
    """bills.json key of a bill record, e.g. '119-hr-1'."""
    return f"{bill.get('congress', 119)}-{str(bill.get('type', '')).lower()}-{bill.get('number', '')}"


def _bill_refresh_rank(bill: dict, newest_vote: str, sweep_cutoff: str) -> tuple | None:
    """Sort key of a stored record that needs re-fetching (most urgent first), or None.

    Tier 0: a roll call on the bill is newer than its latestAction.
    Tier 1: a bill with no law has an enrolled or public-law text version.
    Tier 2, the sweep: no law, and last checked on or before sweep_cutoff, oldest first.
    "Checked" is fetchedDate (ClearVote's own stamp of the last fetch) or, on a record
    fetched before that stamp existed, Congress.gov's updateDate."""
    if bill.get("congress") != CURRENT_CONGRESS:
        return None
    checked = str(bill.get("fetchedDate") or bill.get("updateDate") or "")[:10]
    action = str((bill.get("latestAction") or {}).get("actionDate") or "")[:10]
    if newest_vote > action:
        return (0, checked)
    if bill.get("laws"):
        return None
    versions = bill.get("textVersions")
    if str(bill.get("type", "")).lower() in _LAW_TYPES and isinstance(versions, list) and any(
            isinstance(v, dict) and v.get("type") in _FINAL_TEXT_TYPES for v in versions):
        return (1, checked)
    if checked <= sweep_cutoff:
        return (2, checked)
    return None


def _merge_refreshed_bill(stored: dict, fresh: dict, summaries, today: str) -> dict:
    """A re-fetched record merged over the stored one (F002), stamped fetchedDate=today.

    Fields Congress.gov sent replace the stored ones. Two fields ClearVote fills itself
    survive: summaries, unless the summary fetch returned some, and the textVersions list
    carrying the text fetch_bill_texts embedded. The bill-detail API sends textVersions
    only as a {count, url} reference, so the stored list stays unless the API now counts
    more versions than it holds; then the reference replaces it and fetch_bill_texts
    fetches the newer text in the same step."""
    merged = {**stored, **fresh, "fetchedDate": today}
    stored_versions = stored.get("textVersions")
    if isinstance(stored_versions, list):
        fresh_versions = fresh.get("textVersions")
        count = (fresh_versions.get("count") if isinstance(fresh_versions, dict)
                 else len(fresh_versions) if isinstance(fresh_versions, list) else None)
        if not isinstance(count, int) or count <= len(stored_versions):
            merged["textVersions"] = stored_versions
    summaries = [s for s in summaries if isinstance(s, dict)] if isinstance(summaries, list) else []
    merged["summaries"] = summaries or stored.get("summaries") or []
    return merged


async def sync_bills_from_votes(client: CongressAPIClient, output_dir: Path, rate_limit: float = 0.0,
                                max_refreshes: int = BILL_REFRESH_CAP, today: str | None = None) -> int:
    """Fetch bills referenced in Senate and House vote documents. Incremental: new bills
    are fetched in full, and up to max_refreshes stored records that look stale
    (_bill_refresh_rank) are re-fetched and merged in place (F002). A failed re-fetch
    keeps the stored record."""
    bills_path = output_dir / "bills.json"
    today = today or datetime.now(timezone.utc).date().isoformat()
    sweep_cutoff = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=BILL_REFRESH_DAYS)).date().isoformat()

    # Collect unique bill references as (congress, ref) tuples from both chambers,
    # and each bill's newest roll-call date
    bill_refs: set[tuple[int, str]] = set()
    newest_votes: dict[str, str] = {}
    for chamber_dir in ["senate", "house"]:
        vote_dir = output_dir / "votes" / chamber_dir
        if not vote_dir.exists():
            continue
        for vote_file in sorted(vote_dir.glob("*.json")):
            with open(vote_file) as f:
                vote = json.load(f)
            ref = _parse_bill_ref(vote.get("document", ""))
            if ref:
                vote_congress = vote.get("congress", 119)
                bill_refs.add((vote_congress, ref))
                parsed = _parse_vote_date(vote.get("vote_date") or "")
                key = f"{vote_congress}-{ref}"
                if parsed and parsed.date().isoformat() > newest_votes.get(key, ""):
                    newest_votes[key] = parsed.date().isoformat()

    if not bill_refs:
        print("  No bill references found in votes — skipping")
        return 0

    print(f"  Found {len(bill_refs)} unique bills referenced in votes")

    # Load existing bills to skip already-fetched ones (key -> position, for in-place refresh)
    existing_bills: list[dict] = []
    existing_keys: dict[str, int] = {}
    if bills_path.exists():
        with open(bills_path) as f:
            existing_bills = json.load(f).get("bills", [])
        for pos, b in enumerate(existing_bills):
            existing_keys[_bill_key(b)] = pos

    # Fetch new bills
    new_bills = []
    # Build comparable keys from bill_refs: "congress-ref" e.g. "119-hr-1"
    ref_keys = {(c, ref): f"{c}-{ref}" for c, ref in bill_refs}
    refs_to_fetch = sorted(
        [(c, ref) for (c, ref), key in ref_keys.items() if key not in existing_keys]
    )
    for i, (bill_congress, ref) in enumerate(refs_to_fetch):
        parts = ref.rsplit("-", 1)
        if len(parts) != 2:
            continue
        bill_type, bill_number_str = parts

        print(f"  Fetching {bill_type.upper()} {bill_number_str} (congress {bill_congress})... ({i + 1}/{len(refs_to_fetch)})")
        try:
            data = await client.get_bill(bill_congress, bill_type, int(bill_number_str))
            bill = data.get("bill", {})

            # Also fetch official summary
            try:
                summary_data = await client.get_bill_summary(bill_congress, bill_type, int(bill_number_str))
                bill["summaries"] = summary_data.get("summaries", [])
            except Exception:
                bill["summaries"] = []

            bill["fetchedDate"] = today
            new_bills.append(bill)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {ref}: {e}")
        await asyncio.sleep(rate_limit)

    # Re-fetch stored records that may be stale, most urgent first, replacing each in place
    due = []
    for key, pos in existing_keys.items():
        rank = _bill_refresh_rank(existing_bills[pos], newest_votes.get(key, ""), sweep_cutoff)
        if rank is not None:
            due.append((rank, key))
    to_refresh = [key for _, key in sorted(due)][:max_refreshes]
    if due:
        print(f"  Re-fetching {len(to_refresh)} of {len(due)} stored bills that may be stale (cap {max_refreshes})")
    refreshed = 0
    for i, key in enumerate(to_refresh):
        stored = existing_bills[existing_keys[key]]
        bill_congress = stored.get("congress")
        bill_type = str(stored.get("type", "")).lower()
        print(f"  Re-fetching {bill_type.upper()} {stored.get('number')} (congress {bill_congress})... ({i + 1}/{len(to_refresh)})")
        try:
            bill_number = int(stored.get("number"))
            data = await client.get_bill(bill_congress, bill_type, bill_number)
            fresh = data.get("bill") if isinstance(data, dict) else None
            if not isinstance(fresh, dict) or _bill_key(fresh) != key:
                raise ValueError("response is not this bill")
        except Exception as e:
            print(f"  WARNING: Failed to re-fetch {key}, keeping the stored record: {e}")
            await asyncio.sleep(rate_limit)
            continue
        try:
            summaries = (await client.get_bill_summary(bill_congress, bill_type, bill_number)).get("summaries")
        except Exception:
            summaries = None
        existing_bills[existing_keys[key]] = _merge_refreshed_bill(stored, fresh, summaries, today)
        refreshed += 1
        await asyncio.sleep(rate_limit)

    all_bills = existing_bills + new_bills
    _atomic_write_json(bills_path, {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills ({len(new_bills)} new, {refreshed} refreshed)")
    return len(all_bills)


def run_validation(output_dir: Path) -> int:
    """Validate data/synced; returns the failure count (0 = pass).

    When the data lives in this git repo, the previously committed state is
    loaded from HEAD so regressions (lost summaries, wiped scorecards) are
    caught BEFORE they are committed."""
    import subprocess
    from app.services.data_validator import validate_synced_data

    previous_summaries = None
    previous_scorecard_members = None
    try:
        rel = output_dir.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        rel = None
    if rel is not None:
        try:
            blob = subprocess.run(
                ["git", "show", f"HEAD:{rel}/ai_summaries.json"],
                capture_output=True, text=True, cwd=BASE_DIR, timeout=60,
            )
            if blob.returncode == 0:
                previous_summaries = json.loads(blob.stdout)
            listing = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", "HEAD", f"{rel}/member_votes"],
                capture_output=True, text=True, cwd=BASE_DIR, timeout=60,
            )
            if listing.returncode == 0:
                previous_scorecard_members = set()
                for name in listing.stdout.split():
                    show = subprocess.run(
                        ["git", "show", f"HEAD:{name}"],
                        capture_output=True, text=True, cwd=BASE_DIR, timeout=60,
                    )
                    if show.returncode == 0:
                        try:
                            if json.loads(show.stdout).get("scorecard"):
                                previous_scorecard_members.add(Path(name).stem)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"  (git comparison unavailable: {e})")

    failures, warnings = validate_synced_data(
        output_dir,
        previous_summaries=previous_summaries,
        previous_scorecard_members=previous_scorecard_members,
    )
    for w in warnings:
        print(f"  WARNING: {w}")
    for f in failures:
        print(f"  FAILURE: {f}")
    print(f"  Validation: {len(failures)} failure(s), {len(warnings)} warning(s)")
    return len(failures)


def _bill_text_excerpt(bill: dict) -> str:
    """Latest text version carrying embedded text. The bill-detail API stores
    textVersions as a URL-reference dict, so most bills have no embedded text
    until fetch_bill_texts runs."""
    versions = bill.get("textVersions")
    if not isinstance(versions, list):
        return ""
    with_text = [v for v in versions if isinstance(v, dict) and v.get("text")]
    if not with_text:
        return ""
    return max(with_text, key=lambda v: v.get("date") or "").get("text", "")


# Bill text is fetched only from www.congress.gov (every formats[].url today), never from
# whatever host an API response or a redirect names, and never more than 5 MB (F049).
_BILL_TEXT_HOSTS = frozenset({"www.congress.gov", "congress.gov"})
_BILL_TEXT_MAX_BYTES = 5 * 1024 * 1024


def _is_bill_text_url(url) -> bool:
    """https on www.congress.gov or congress.gov, with no user part or non-default port."""
    try:
        parts = urlsplit(str(url))
        port = parts.port
    except ValueError:
        return False
    return (parts.scheme == "https" and parts.hostname in _BILL_TEXT_HOSTS
            and parts.username is None and port in (None, 443))


async def fetch_bill_texts(client, output_dir: Path, rate_limit: float = 0.3, max_fetches: int | None = None) -> int:
    """Fetch the LATEST text version for bills with no embedded text.

    The writer generates from title + summary + text; without this step 99% of
    bills reach the AI with an empty text field. Incremental: bills that
    already carry text are skipped, so weekly runs only fetch new bills.

    www.congress.gov rate-limits aggressively from CI (July 4 sync failure):
    429s back off and retry twice, persistent 429s end the run with progress
    saved, and max_fetches caps a run so a backlog can't blow the CI step
    timeout — the next run resumes where this one stopped.

    The URL must pass _is_bill_text_url before the request and again after redirects,
    and the body is read in chunks up to _BILL_TEXT_MAX_BYTES."""
    bills_path = output_dir / "bills.json"
    if not bills_path.exists():
        print("  No bills.json — skipping text fetch")
        return 0
    with open(bills_path) as f:
        bills_data = json.load(f)
    bills = bills_data.get("bills", [])
    to_fetch = [b for b in bills if not _bill_text_excerpt(b)]
    print(f"  {len(to_fetch)} bills missing text (of {len(bills)})")

    fetched = 0
    rate_limited_out = False
    for i, bill in enumerate(to_fetch):
        if max_fetches is not None and fetched >= max_fetches:
            print(f"  Per-run cap of {max_fetches} reached — stopping; next run resumes")
            break
        bt = (bill.get("type") or "").lower()
        bn = str(bill.get("number") or "")
        congress = bill.get("congress", 119)
        try:
            resp = await client.get_bill_text(congress, bt, int(bn))
        except Exception as e:
            print(f"    Error listing text for {congress}-{bt}-{bn}: {e}")
            continue
        versions = resp.get("textVersions") or []
        versions = [v for v in versions if isinstance(v, dict)]
        if not versions:
            continue
        latest = max(versions, key=lambda v: v.get("date") or "")
        formats = latest.get("formats") or []
        url = next((f.get("url") for f in formats if f.get("type") == "Formatted Text"), None) \
            or next((f.get("url") for f in formats if f.get("type") == "Formatted XML"), None)
        if not url:
            continue
        if not _is_bill_text_url(url):
            print(f"    Skipping text for {congress}-{bt}-{bn}: URL is not on congress.gov over https")
            continue
        body = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as http:
                    async with http.stream("GET", url, follow_redirects=True) as candidate:
                        if not _is_bill_text_url(candidate.url):
                            raise ValueError(f"redirected off congress.gov to {candidate.url.host}")
                        candidate.raise_for_status()
                        chunks = bytearray()
                        async with aclosing(candidate.aiter_bytes()) as stream:
                            async for chunk in stream:
                                chunks.extend(chunk)
                                if len(chunks) > _BILL_TEXT_MAX_BYTES:
                                    raise ValueError(f"body over {_BILL_TEXT_MAX_BYTES} bytes")
                        body = chunks.decode(candidate.charset_encoding or "utf-8", errors="replace")
                break
            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response is not None else None
                if status == 429 and attempt < 2:
                    backoff = 30 * (attempt + 1)
                    print(f"    429 rate-limited on {congress}-{bt}-{bn} — backing off {backoff}s")
                    await asyncio.sleep(backoff)
                    continue
                if status == 429:
                    rate_limited_out = True
                else:
                    print(f"    Error fetching text body for {congress}-{bt}-{bn}: {e}")
                break
            except Exception as e:
                print(f"    Error fetching text body for {congress}-{bt}-{bn}: {e}")
                break
        if rate_limited_out:
            print("  Persistent 429s from congress.gov — stopping this run; progress saved, next run resumes")
            break
        if body is None:
            continue
        # Unescape after stripping tags: an escaped "&lt;tag&gt;" in the text is content, not markup.
        clean = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
        if not clean:
            continue
        latest["text"] = clean[:6000]
        bill["textVersions"] = versions
        fetched += 1
        if fetched % 50 == 0:
            _atomic_write_json(bills_path, bills_data)  # crash-safe checkpoints
            print(f"    ...{fetched} fetched ({i + 1}/{len(to_fetch)} scanned)")
        if rate_limit:
            await asyncio.sleep(rate_limit)

    if fetched:
        _atomic_write_json(bills_path, bills_data)
    print(f"  Fetched text for {fetched} bills")
    return fetched


async def sync_bill_summaries(
    output_dir: Path,
    api_key: str | None = None,
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

    # The store keeps batch history only. Saved "learnings" are not fed to the
    # grader: they were raw per-bill feedback (mostly praise) promoted to
    # standing grading rules with no review.
    learnings_store = GraderLearnings(learnings_path)
    grader.load_learnings([])

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

    async def _process_one_bill(key: str, bill: dict) -> None:
        """Process a single bill through the writer-grader loop."""
        title = bill.get("title", "")
        official_summary = _latest_official_summary(bill)
        bill_text = _bill_text_excerpt(bill)
        policy_area = bill.get("policyArea", {}).get("name")
        latest_action = (bill.get("latestAction") or {}).get("text", "")

        print(f"    Grading: {title[:60]}...")

        async def writer_fn(grader_feedback=None, _bill_id=key, _title=title, _official_summary=official_summary, _bill_text=bill_text, _policy_area=policy_area, _latest_action=latest_action, **kwargs):
            return await writer_service.generate_summary(
                bill_id=_bill_id,
                title=_title,
                official_summary=_official_summary,
                bill_text_excerpt=_bill_text[:6000],
                grader_feedback=grader_feedback,
                policy_area=_policy_area,
                latest_action=_latest_action,
            )

        loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
        try:
            result = await loop.run(
                summary_type="bill_summary",
                writer_kwargs={},
                # Same text excerpt the writer saw — without it, true
                # text-sourced details are graded as fabricated.
                grader_context={"title": title, "official_summary": official_summary,
                                "latest_action": latest_action,
                                "bill_text_excerpt": bill_text[:6000]},
            )

            summary_data = result.best_summary
            if summary_data.get("generation_failed"):
                # Never persist the parse-failure fallback — an absent entry
                # gets the router's honest "not available" treatment instead.
                print(f"    NOT SAVED — generation failed for {key}")
                stats["failed"] += 1
                stats["total"] += 1
                return
            one_liner = summary_data.get("one_liner")
            if not (isinstance(one_liner, str) and one_liner.strip()) or not summary_data.get("provisions"):
                # Same for a structurally empty result: the data validator
                # fails it (blocking the next weekly sync's commits), and a
                # saved key is never retried. Absent, the next run retries it.
                print(f"    NOT SAVED — empty one_liner or provisions for {key}")
                stats["failed"] += 1
                stats["total"] += 1
                return
            if result.needs_review:
                summary_data["needs_review"] = True
                stats["needs_review"].append(key)
                stats["failed"] += 1
            else:
                stats["passed"] += 1

            existing[key] = summary_data
            stats["total"] += 1
            grade_dist[result.best_grade.grade] = grade_dist.get(result.best_grade.grade, 0) + 1
        except Exception as e:
            print(f"    SKIPPED — {e}")
            stats["failed"] += 1
            stats["total"] += 1

    for batch_start in range(0, len(to_process), batch_size):
        batch = to_process[batch_start:batch_start + batch_size]
        print(f"  Batch {batch_start // batch_size + 1}/{(len(to_process) + batch_size - 1) // batch_size}")

        # Process bills in parallel within each batch
        await asyncio.gather(*[_process_one_bill(key, bill) for key, bill in batch])

        # Save after each batch (crash-safe)
        _atomic_write_json(summaries_path, existing)

    learnings_store.record_batch(
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        grade_distribution=grade_dist,
        needs_review_ids=stats["needs_review"],
        content_type="bill_summary",
    )
    learnings_store.save()

    print(f"  Summaries: {stats['passed']} passed, {stats['failed']} flagged for review")
    print(f"  Grades: {grade_dist}")
    if stats["needs_review"]:
        print(f"  Needs review: {stats['needs_review']}")

    return stats


async def sync_bill_arguments(
    output_dir: Path,
    api_key: str | None = None,
    batch_size: int = 5,
    rate_limit: float = 1.0,
) -> dict:
    """Generate AI both-sides arguments for all bills through the writer-grader loop.

    Arguments are embedded in the existing ai_summaries.json under an 'arguments' key.
    Incremental — skips bills that already have arguments.
    """
    from app.services.bill_arguments import BillArgumentsService
    from app.services.arguments_grader import ArgumentsGrader
    from app.services.writer_grader_loop import WriterGraderLoop
    from app.services.grader_learnings import GraderLearnings

    summaries_path = output_dir / "ai_summaries.json"
    bills_path = output_dir / "bills.json"
    learnings_path = output_dir / "grader_learnings.json"

    if not summaries_path.exists():
        print("  No ai_summaries.json — skipping bill arguments")
        return {"total": 0, "passed": 0, "failed": 0}

    with open(summaries_path) as f:
        summaries = json.load(f)

    if not bills_path.exists():
        print("  No bills.json — skipping bill arguments")
        return {"total": 0, "passed": 0, "failed": 0}

    with open(bills_path) as f:
        bills_list = json.load(f).get("bills", [])

    # Build bill lookup by key
    bill_lookup: dict[str, dict] = {}
    for bill in bills_list:
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", 119)
        key = f"{congress}-{bill_type}-{bill_number}"
        bill_lookup[key] = bill

    # Setup services
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    writer_service = BillArgumentsService(api_key=api_key, cache=cache)
    grader = ArgumentsGrader(api_key=api_key)

    # Batch history only — saved learnings are not fed to the grader (see
    # sync_bill_summaries).
    learnings_store = GraderLearnings(learnings_path)
    grader.load_learnings([])

    # Find summaries needing arguments (incremental)
    to_process = []
    for key, summary in summaries.items():
        if "arguments" not in summary and key in bill_lookup:
            to_process.append((key, summary, bill_lookup[key]))

    if not to_process:
        print("  All bills already have arguments — skipping")
        return {"total": 0, "passed": 0, "failed": 0}

    print(f"  Generating arguments for {len(to_process)} bills (batch size: {batch_size})")

    stats: dict = {"total": 0, "passed": 0, "failed": 0, "needs_review": []}
    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

    async def _process_one_bill(key: str, summary: dict, bill: dict) -> None:
        title = bill.get("title", "")
        summaries_list = bill.get("summaries", [])
        official_summary = summaries_list[0].get("text", "") if isinstance(summaries_list, list) and summaries_list else ""
        provisions = summary.get("provisions", [])

        print(f"    Arguments: {title[:60]}...")

        async def writer_fn(grader_feedback=None, _bill_id=key, _title=title, _official_summary=official_summary, _provisions=provisions, **kwargs):
            return await writer_service.generate_arguments(
                bill_id=_bill_id,
                title=_title,
                official_summary=_official_summary,
                provisions=_provisions,
                grader_feedback=grader_feedback,
            )

        loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
        try:
            result = await loop.run(
                summary_type="bill_arguments",
                writer_kwargs={},
                grader_context={"title": title, "official_summary": official_summary, "provisions": provisions},
            )

            arguments_data = result.best_summary
            if result.needs_review:
                arguments_data["needs_review"] = True
                stats["needs_review"].append(key)
                stats["failed"] += 1
            else:
                stats["passed"] += 1

            # Embed arguments into existing summary
            summaries[key]["arguments"] = arguments_data
            stats["total"] += 1
            grade_dist[result.best_grade.grade] = grade_dist.get(result.best_grade.grade, 0) + 1
        except Exception as e:
            print(f"    SKIPPED — {e}")
            stats["failed"] += 1
            stats["total"] += 1

    for batch_start in range(0, len(to_process), batch_size):
        batch = to_process[batch_start:batch_start + batch_size]
        print(f"  Batch {batch_start // batch_size + 1}/{(len(to_process) + batch_size - 1) // batch_size}")

        await asyncio.gather(*[_process_one_bill(key, summary, bill) for key, summary, bill in batch])

        # Save after each batch (crash-safe)
        _atomic_write_json(summaries_path, summaries)

    learnings_store.record_batch(
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        grade_distribution=grade_dist,
        needs_review_ids=stats["needs_review"],
        content_type="bill_arguments",
    )
    learnings_store.save()

    print(f"  Arguments: {stats['passed']} passed, {stats['failed']} flagged for review")
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
            congress = bill.get("congress", 119)
            key = f"{congress}-{bill_type}-{bill_number}"
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

    def _iso_vote_date(raw: str) -> str:
        """Senate XML dates are display strings ("September 9, 2025,  06:46 PM")
        which sort lexicographically, not chronologically. Store ISO 8601 so
        plain string sorts are chronological; the UI formats at render time."""
        parsed = _parse_vote_date(raw or "")
        return parsed.isoformat() if parsed else (raw or "")

    def _get_one_liner(bill_ref: str | None, bill_info: dict, doc: str, congress: int = 119) -> str:
        if bill_ref:
            summary_key = f"{congress}-{bill_ref}"
            ai_summary = ai_summaries.get(summary_key, {})
            if ai_summary.get("one_liner"):
                return ai_summary["one_liner"]
        return bill_info.get("title", doc)

    def _has_plain_summary(bill_ref: str | None, congress: int = 119) -> bool:
        """True only when a real AI plain-language one-liner exists — lets the UI
        show genuine plain English in 'Key Bills' instead of an official title or
        raw procedural text (which is what _get_one_liner falls back to)."""
        if not bill_ref:
            return False
        return bool(ai_summaries.get(f"{congress}-{bill_ref}", {}).get("one_liner"))

    def _get_direction(bill_ref: str | None, congress: int = 119) -> str | None:
        if bill_ref:
            summary_key = f"{congress}-{bill_ref}"
            summary = ai_summaries.get(summary_key, {})
            return summary.get("direction")
        return None

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
        bioguide_id = member.get("bioguideId")
        if not _is_bioguide_id(bioguide_id):
            # sync_members drops these; this covers an older or hand-edited members.json.
            print(f"  WARNING: skipping member with malformed bioguideId {bioguide_id!r}")
            continue
        chamber = member.get("chamber", "")
        member_last = member.get("name", "").split(",")[0].strip().lower()
        member_state = member.get("stateCode", "").upper()

        print(f"  Building votes for {member.get('directOrderName', bioguide_id)}...")

        member_vote_list = []

        if chamber == "Senate":
            # Match Senate votes by last name + state (Senate XML uses names, not bioguide IDs)
            for vote in senate_votes:
                # Skip Presidential Nominations (PN) — not legislation, no useful info
                doc_check = vote.get("document", "").strip()
                if doc_check.startswith("PN") or doc_check.startswith("P.N."):
                    continue

                matched = None
                for mv in vote.get("members", []):
                    if (mv.get("last_name", "").lower() == member_last
                            and mv.get("state", "").upper() == member_state):
                        matched = mv
                        break
                if not matched:
                    continue

                vote_congress = vote.get("congress", 119)
                doc = vote.get("document", "")
                bill_ref = _parse_bill_ref(doc)
                bill_key = f"{vote_congress}-{bill_ref}" if bill_ref else None
                bill_info = bill_lookup.get(bill_key, {}) if bill_key else {}

                member_vote_list.append({
                    "bill_number": doc,
                    "bill_id": f"{vote_congress}-{bill_ref}" if bill_ref else None,
                    "one_liner": _get_one_liner(bill_ref, bill_info, doc, congress=vote_congress),
                    "has_plain_summary": _has_plain_summary(bill_ref, congress=vote_congress),
                    "vote": matched.get("vote", ""),
                    "date": _iso_vote_date(vote.get("vote_date", "")),
                    "result": vote.get("result", ""),
                    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                    "chamber": "Senate",
                    "cbo_deficit_impact": None,
                    "direction": _get_direction(bill_ref, congress=vote_congress),
                    "congress": vote_congress,
                    "session": vote.get("session", 1),
                    "vote_number": vote.get("vote_number", 0),
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

                vote_congress = vote.get("congress", 119)
                doc = vote.get("document", "")
                bill_ref = _parse_bill_ref(doc)
                bill_key = f"{vote_congress}-{bill_ref}" if bill_ref else None
                bill_info = bill_lookup.get(bill_key, {}) if bill_key else {}

                member_vote_list.append({
                    "bill_number": doc,
                    "bill_id": f"{vote_congress}-{bill_ref}" if bill_ref else None,
                    "one_liner": _get_one_liner(bill_ref, bill_info, doc, congress=vote_congress),
                    "has_plain_summary": _has_plain_summary(bill_ref, congress=vote_congress),
                    "vote": matched.get("vote", ""),
                    "date": _iso_vote_date(vote.get("vote_date", "")),
                    "result": vote.get("result", ""),
                    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                    "chamber": "House",
                    "cbo_deficit_impact": None,
                    "direction": _get_direction(bill_ref, congress=vote_congress),
                    "congress": vote_congress,
                    "session": vote.get("session", 1),
                    "vote_number": vote.get("vote_number", 0),
                })

        # Compute stats
        yea = sum(1 for v in member_vote_list if v["vote"] in ("Yea", "Aye"))
        nay = sum(1 for v in member_vote_list if v["vote"] in ("Nay", "No"))
        not_voting = sum(1 for v in member_vote_list if v["vote"] == "Not Voting")
        total = len(member_vote_list)
        participation = round((yea + nay) / total * 100, 1) if total > 0 else 0

        policy_areas = sorted(set(v["policy_area"] for v in member_vote_list if v["policy_area"]))

        congresses_seen = sorted(set(v.get("congress", 119) for v in member_vote_list if v.get("congress")))

        # Scorecards are AI-generated in a separate step that needs an API key;
        # a rebuild must carry them forward, not reset them.
        out_path = member_votes_dir / f"{bioguide_id}.json"
        existing_scorecard = []
        if out_path.exists():
            try:
                existing_scorecard = json.loads(out_path.read_text()).get("scorecard", [])
            except (json.JSONDecodeError, OSError):
                pass

        record = {
            "member_id": bioguide_id,
            "congresses": congresses_seen if congresses_seen else [119],
            "stats": {
                "total_votes": total,
                "yea_count": yea,
                "nay_count": nay,
                "not_voting_count": not_voting,
                "participation_rate": participation,
            },
            "scorecard": existing_scorecard,
            "votes": sorted(member_vote_list,
                            key=lambda v: (v["date"], v.get("vote_number", 0)),
                            reverse=True),
            "policy_areas": policy_areas,
        }
        _atomic_write_json(out_path, record)
        count += 1

    print(f"  Built voting records for {count} members")
    return count


# --- Votes index (spec §10 #3) --------------------------------------------------------
# One pass over the roll-call files at sync time; the web runtime reads only this file.

# §4.3 m4: an amendment or motion names the measure it attaches to ("... to S.Con.Res. 5").
_PARENT_BILL_RE = re.compile(
    r"\bto (H\.R\.|S\.|H\.J\.Res\.|S\.J\.Res\.|H\.Con\.Res\.|S\.Con\.Res\.|H\.Res\.|S\.Res\.)\s*(\d+)"
)
_YES_VOTES = ("Yea", "Aye")
_NO_VOTES = ("Nay", "No")


def _state_tallies(members: list[dict]) -> dict[str, list[int]]:
    """{state: [yes, no, didn't vote]} for the covered states. Present counts in none of the three.
    An impeachment verdict's Guilty / Not Guilty count as yes / no, as senate.gov's own yeas /
    nays do (F064); only here, so _YES_VOTES / _NO_VOTES keep their meaning."""
    tallies = {code: [0, 0, 0] for code in sorted(SYNC_STATES)}
    for member in members:
        row = tallies.get(str(member.get("state") or "").upper())
        if row is None:
            continue
        vote = member.get("vote") or ""
        if vote in _YES_VOTES or vote == "Guilty":
            row[0] += 1
        elif vote in _NO_VOTES or vote == "Not Guilty":
            row[1] += 1
        elif vote == "Not Voting":
            row[2] += 1
    return tallies


def votes_index_payload(sync_dir: Path) -> dict:
    """votes_index.json without generated_at: every roll call under votes/{house,senate}, a
    per-bill list newest first with the bill's activity date, and the home page's latest vote.
    Pure: reads files, writes nothing (build_votes_index writes)."""
    bill_actions: dict[str, str] = {}
    bills_path = sync_dir / "bills.json"
    if bills_path.exists():
        with open(bills_path) as f:
            for bill in json.load(f).get("bills", []):
                key = f"{bill.get('congress')}-{str(bill.get('type', '')).lower()}-{bill.get('number')}"
                bill_actions[key] = str((bill.get("latestAction") or {}).get("actionDate") or "")[:10]

    roll_calls: dict[str, dict] = {}
    for chamber in ("house", "senate"):
        vote_dir = sync_dir / "votes" / chamber
        if not vote_dir.exists():
            continue
        for vote_file in sorted(vote_dir.glob("*.json")):
            with open(vote_file) as f:
                vote = json.load(f)
            congress = vote.get("congress")
            question = vote.get("question") or ""
            result = vote.get("result") or ""
            document = vote.get("document") or ""
            ref = _parse_bill_ref(document)
            parent = _PARENT_BILL_RE.search(question)
            parent_ref = _parse_bill_ref(f"{parent.group(1)} {parent.group(2)}") if parent else None
            parsed_date = _parse_vote_date(vote.get("vote_date") or "")
            counts = vote.get("counts") or {}
            key = roll_call_key(chamber, congress, vote.get("session"), vote.get("vote_number"))
            plain = plain_question(question)
            roll_calls[key] = {
                "question": question,
                "plain": plain,
                "class": question_class(question),
                "result": result,
                "counts": {name: int(counts.get(name) or 0) for name in ("yeas", "nays", "present", "absent")},
                "date": parsed_date.date().isoformat() if parsed_date else None,
                "document": document,
                "bill": f"{congress}-{ref}" if ref else None,
                "parent": f"{congress}-{parent_ref}" if parent_ref else None,
                "threshold": parse_threshold(result, plain, question),  # the one §7.2 threshold formatter
                "tallies": _state_tallies(vote.get("members") or []),
            }

    def vote_number(key: str) -> int:
        return int(key.rsplit("_", 1)[1])

    def newest(key: str) -> tuple:
        return (roll_calls[key]["date"] or "", vote_number(key), key)

    bills: dict[str, dict] = {key: {"roll_calls": [], "activity_date": None} for key in bill_actions}
    for key, rc in roll_calls.items():
        if rc["bill"]:
            bills.setdefault(rc["bill"], {"roll_calls": [], "activity_date": None})["roll_calls"].append(key)
    for bill_id, entry in bills.items():
        entry["roll_calls"].sort(key=newest, reverse=True)
        newest_vote = roll_calls[entry["roll_calls"][0]]["date"] if entry["roll_calls"] else None
        entry["activity_date"] = max(bill_actions.get(bill_id) or "", newest_vote or "") or None

    # The hero (§4.1 m3): the newest roll call on a bill we hold; within a day a decisive
    # vote leads a procedural one, then the higher vote number.
    held = [key for key, rc in roll_calls.items() if rc["bill"] in bill_actions and rc["date"]]
    latest = max(
        held,
        key=lambda key: (roll_calls[key]["date"], roll_calls[key]["class"] == "D", vote_number(key), key),
        default=None,
    )
    return {"roll_calls": roll_calls, "bills": bills, "latest": latest}


def build_votes_index(sync_dir: Path) -> int:
    """Write data/synced/votes_index.json (§10 #3); returns the roll-call count."""
    payload = votes_index_payload(sync_dir)
    written = _write_derived_json(sync_dir / "votes_index.json", payload, compact=True)
    print(f"  Votes index: {len(payload['roll_calls'])} roll calls, {len(payload['bills'])} bills, "
          f"latest {payload['latest']} ({'written' if written else 'unchanged'})")
    return len(payload["roll_calls"])


# --- State overview (spec §10 #7) -----------------------------------------------------

def _latest_decisive_vote(votes_path: Path, roll_calls: dict) -> dict | None:
    """The member's most recent class-D roll call on a bill (§4.2 signal line), whatever the
    position. member_votes rows are newest first, so the first qualifying row wins."""
    if not votes_path.exists():
        return None
    with open(votes_path) as f:
        rows = json.load(f).get("votes", [])
    for row in rows:
        if not row.get("bill_id"):
            continue
        try:
            key = roll_call_key(row.get("chamber"), row.get("congress"), row.get("session"), row.get("vote_number"))
        except (TypeError, ValueError):
            continue
        rc = roll_calls.get(key)
        if rc and rc.get("class") == "D":
            return {"rc": key, "bill_id": row["bill_id"], "position": row.get("vote") or "",
                    "date": rc.get("date") or str(row.get("date") or "")[:10]}
    return None


def state_overview_payloads(sync_dir: Path, states: list[str]) -> dict[str, dict]:
    """state_overview/{code}.json contents without generated_at, per state. Pure: writes nothing."""
    with open(sync_dir / "members.json") as f:
        members = json.load(f).get("members", [])
    with open(sync_dir / "votes_index.json") as f:
        roll_calls = json.load(f).get("roll_calls") or {}
    expected: dict[str, int] = {}
    crosswalk_path = sync_dir / "zip_districts.json"
    if crosswalk_path.exists():
        with open(crosswalk_path) as f:
            for key, rows in json.load(f).items():
                if key.startswith("_"):
                    continue
                for row in rows:
                    expected[row["state"]] = max(expected.get(row["state"], 0), int(row["district"]))
    payloads: dict[str, dict] = {}
    for code in states:
        state_members = [m for m in members if m.get("stateCode") == code]
        latest = {
            m["bioguideId"]: _latest_decisive_vote(sync_dir / "member_votes" / f"{m['bioguideId']}.json", roll_calls)
            for m in state_members if _is_bioguide_id(m.get("bioguideId"))
        }
        districts = expected.get(code) or max((m.get("district") or 0 for m in state_members), default=0)
        payloads[code] = state_overview_payload(code, members, latest, districts)
    return payloads


def build_state_overview(sync_dir: Path, states: list[str] | None = None) -> int:
    """Write data/synced/state_overview/{code}.json per covered state (§10 #7). Needs
    votes_index.json (run after --step votes-index); returns the number of states built."""
    if not (sync_dir / "votes_index.json").exists():
        print("  No votes_index.json — run --step votes-index first; state overviews not built")
        return 0
    states = states or SYNC_STATES
    for code, payload in state_overview_payloads(sync_dir, states).items():
        written = _write_derived_json(sync_dir / "state_overview" / f"{code}.json", payload)
        print(f"  State overview {code}: {len(payload['senators'])} senators, {len(payload['house'])} House "
              f"members, {payload['districts_expected']} districts ({'written' if written else 'unchanged'})")
    return len(states)


async def generate_scorecard_verdicts(
    output_dir: Path,
    api_key: str | None = None,
    rate_limit: float = 0.5,
) -> int:
    """Generate per-category scorecard verdicts for each member.

    Groups each member's votes by issue_categories (from AI summaries),
    computes in_favor/against ratios, and calls a lightweight LLM prompt
    for a one-line verdict per category. Stores scorecard in member vote JSON.

    Returns count of members processed.
    """
    from app.services.ai_summary import AISummaryService, ISSUE_CATEGORIES

    member_votes_dir = output_dir / "member_votes"
    if not member_votes_dir.exists():
        print("  No member_votes dir — skipping scorecard generation")
        return 0

    # Load AI summaries to get issue_categories per bill
    ai_summaries: dict[str, dict] = {}
    ai_summaries_path = output_dir / "ai_summaries.json"
    if ai_summaries_path.exists():
        with open(ai_summaries_path) as f:
            ai_summaries = json.load(f)

    # Setup LLM service for verdict generation
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    service = AISummaryService(api_key=api_key, cache=cache)

    verdict_system = """You are a nonpartisan legislative analyst. Write a single sentence (max 20 words) describing how this member voted on this issue. Be specific and factual. No adjectives. No opinions. Use "in favor" and "against" language. Example: "Voted against 48 of 50 bills to cap prices and raise wages"."""

    async def _process_member_scorecard(member_file: Path) -> bool:
        """Process one member's scorecard. Returns True if scorecard generated."""
        with open(member_file) as f:
            member_data = json.load(f)

        votes = member_data.get("votes", [])
        if not votes:
            return False

        # Skip if already has non-empty scorecard
        if member_data.get("scorecard") and len(member_data["scorecard"]) > 0:
            return True

        # Group votes by issue_categories
        category_votes: dict[str, list[dict]] = {}
        for v in votes:
            bill_id = v.get("bill_id")
            if not bill_id:
                continue
            summary = ai_summaries.get(bill_id, {})
            categories = summary.get("issue_categories", [])
            direction = v.get("direction")
            vote_position = v.get("vote", "").lower()
            is_yea = vote_position in ("yea", "aye")
            is_nay = vote_position in ("nay", "no")

            if direction == "in_favor":
                effective = "in_favor" if is_yea else ("against" if is_nay else None)
            elif direction == "against":
                effective = "against" if is_yea else ("in_favor" if is_nay else None)
            else:
                effective = None

            for cat in categories:
                if cat not in category_votes:
                    category_votes[cat] = []
                category_votes[cat].append({
                    "bill_id": bill_id,
                    "one_liner": v.get("one_liner", ""),
                    "vote": v.get("vote", ""),
                    "direction": effective or "neutral",
                })

        # Generate all verdicts in parallel
        async def _get_verdict(cat: str, cat_votes: list[dict]) -> dict:
            in_favor = sum(1 for cv in cat_votes if cv["direction"] == "in_favor")
            against = sum(1 for cv in cat_votes if cv["direction"] == "against")
            total = len(cat_votes)

            bills_sample = "\n".join(
                f"  - {cv['vote']}: {cv['one_liner']}" for cv in cat_votes[:10]
            )
            verdict_prompt = f"""Category: {cat}
Votes: {in_favor} in favor, {against} against, {total} total
Sample bills:
{bills_sample}

Write ONE sentence describing this voting pattern. Return only the sentence, no JSON."""

            try:
                verdict = await service._call_llm(verdict_system, verdict_prompt)
                verdict = verdict.strip().strip('"')
            except Exception:
                if against > in_favor:
                    verdict = f"Voted against {against} of {total} {cat.lower()} measures"
                else:
                    verdict = f"Voted in favor of {in_favor} of {total} {cat.lower()} measures"

            bills_list = [
                {"bill_id": cv["bill_id"], "one_liner": cv["one_liner"],
                 "vote": cv["vote"], "direction": cv["direction"]}
                for cv in cat_votes
            ]
            return {
                "category": cat, "in_favor": in_favor, "against": against,
                "total": total, "verdict": verdict, "bills": bills_list,
            }

        # Build verdicts for all categories in parallel
        tasks = []
        for cat in ISSUE_CATEGORIES:
            if cat in category_votes:
                tasks.append(_get_verdict(cat, category_votes[cat]))

        scorecard = await asyncio.gather(*tasks)
        scorecard = sorted(scorecard, key=lambda x: x["total"], reverse=True)
        member_data["scorecard"] = scorecard
        _atomic_write_json(member_file, member_data)
        return True

    # Process members in parallel batches of 5
    member_files = sorted(member_votes_dir.glob("*.json"))
    count = 0
    batch_size_members = 5
    for i in range(0, len(member_files), batch_size_members):
        batch = member_files[i:i + batch_size_members]
        results = await asyncio.gather(*[_process_member_scorecard(f) for f in batch])
        count += sum(1 for r in results if r)
        print(f"  Scorecards: {count}/{len(member_files)} members...")

    print(f"  Generated scorecards for {count} members")
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


async def sync_member_summaries(
    output_dir: Path,
    api_key: str | None = None,
    rate_limit: float = 1.0,
) -> dict:
    """Generate AI narrative summaries for each member through the writer-grader loop.

    Incremental — skips members who already have summaries.
    Returns stats dict with pass/fail counts.
    """
    from app.services.member_summary import MemberSummaryService
    from app.services.member_narrative_grader import MemberNarrativeGrader
    from app.services.writer_grader_loop import WriterGraderLoop
    from app.services.grader_learnings import GraderLearnings

    members_path = output_dir / "members.json"
    member_votes_dir = output_dir / "member_votes"
    summaries_path = output_dir / "member_summaries.json"
    learnings_path = output_dir / "grader_learnings.json"

    if not members_path.exists():
        print("  No members.json — skipping member summaries")
        return {"total": 0, "passed": 0, "failed": 0}

    with open(members_path) as f:
        members = json.load(f).get("members", [])

    # Load existing summaries (incremental)
    existing: dict[str, dict] = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    # Setup services
    service = MemberSummaryService(api_key=api_key)
    grader = MemberNarrativeGrader(api_key=api_key)

    # Batch history only — saved learnings are not fed to the grader (see
    # sync_bill_summaries).
    learnings_store = GraderLearnings(learnings_path)
    grader.load_learnings([])

    stats: dict = {"total": 0, "passed": 0, "failed": 0, "needs_review": []}
    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

    async def _process_one_member(member: dict) -> None:
        """Process a single member through the writer-grader loop."""
        bioguide_id = member["bioguideId"]

        if bioguide_id in existing or not _is_bioguide_id(bioguide_id):
            return

        votes_path = member_votes_dir / f"{bioguide_id}.json"
        if not votes_path.exists():
            return

        with open(votes_path) as f:
            vote_data = json.load(f)

        votes = vote_data.get("votes", [])
        if not votes:
            return

        member_name = member.get("directOrderName") or member.get("name", bioguide_id)
        chamber = member.get("chamber", "")
        state = member.get("state", member.get("stateCode", ""))
        congresses = vote_data.get("congresses", [119])
        member_stats = vote_data.get("stats", {})

        area_counts: dict[str, dict] = {}
        for v in votes:
            area = v.get("policy_area", "")
            if not area:
                continue
            if area not in area_counts:
                area_counts[area] = {"name": area, "in_favor": 0, "against": 0, "neutral": 0, "total": 0}
            area_counts[area]["total"] += 1
            direction = v.get("direction")
            is_yea = v.get("vote", "").lower() in ("yea", "aye")
            is_nay = v.get("vote", "").lower() in ("nay", "no")
            if direction == "in_favor":
                if is_yea:
                    area_counts[area]["in_favor"] += 1
                elif is_nay:
                    area_counts[area]["against"] += 1
            elif direction == "against":
                if is_yea:
                    area_counts[area]["against"] += 1
                elif is_nay:
                    area_counts[area]["in_favor"] += 1
            else:
                area_counts[area]["neutral"] += 1

        top_areas = sorted(area_counts.values(), key=lambda x: x["total"], reverse=True)[:5]

        seen_bills: set[str] = set()
        top_supported: list[str] = []
        top_opposed: list[str] = []
        for v in votes:
            bill_id = v.get("bill_id")
            one_liner = v.get("one_liner", "")
            if not one_liner or not bill_id or bill_id in seen_bills:
                continue
            seen_bills.add(bill_id)
            if v.get("vote", "").lower() in ("yea", "aye"):
                top_supported.append(one_liner)
            elif v.get("vote", "").lower() in ("nay", "no"):
                top_opposed.append(one_liner)

        print(f"  Grading narrative for {member_name}...")

        _top_supported = top_supported[:15]
        _top_opposed = top_opposed[:10]

        async def writer_fn(grader_feedback=None, _mn=member_name, _ch=chamber, _st=state, _co=congresses, _ms=member_stats, _ta=top_areas, _ts=_top_supported, _to=_top_opposed, **kwargs):
            return await service.generate_member_summary(
                member_name=_mn, chamber=_ch, state=_st, congresses=_co,
                stats=_ms, top_areas=_ta, top_supported=_ts, top_opposed=_to,
                grader_feedback=grader_feedback,
            )

        loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
        try:
            result = await loop.run(
                summary_type="member_narrative",
                writer_kwargs={},
                grader_context={
                    "top_areas": top_areas, "stats": member_stats,
                    "top_supported": _top_supported, "top_opposed": _top_opposed,
                },
            )

            summary_data = result.best_summary
            if result.needs_review:
                summary_data["needs_review"] = True
                stats["needs_review"].append(bioguide_id)
                stats["failed"] += 1
            else:
                stats["passed"] += 1

            summary_data["generated_at"] = datetime.now(timezone.utc).isoformat()
            existing[bioguide_id] = summary_data
            stats["total"] += 1
            grade_dist[result.best_grade.grade] = grade_dist.get(result.best_grade.grade, 0) + 1
        except Exception as e:
            print(f"  WARNING: Failed to generate summary for {member_name}: {e}")

    # Process members in parallel batches of 5
    to_process = [m for m in members if m["bioguideId"] not in existing]
    batch_size_members = 5
    for i in range(0, len(to_process), batch_size_members):
        batch = to_process[i:i + batch_size_members]
        await asyncio.gather(*[_process_one_member(m) for m in batch])
        _atomic_write_json(summaries_path, existing)
        print(f"  Narratives: {stats['total']}/{len(to_process)} processed...")

    learnings_store.record_batch(
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        grade_distribution=grade_dist,
        needs_review_ids=stats["needs_review"],
        content_type="member_narrative",
    )
    learnings_store.save()

    print(f"  Narratives: {stats['passed']} passed, {stats['failed']} flagged for review")
    print(f"  Grades: {grade_dist}")
    if stats["needs_review"]:
        print(f"  Needs review: {stats['needs_review']}")

    return stats


async def check_page_coherence(
    output_dir: Path,
    api_key: str | None = None,
    rate_limit: float = 1.0,
) -> dict:
    """Check coherence between narrative summaries and data sections.

    For each member, compares the narrative against stats, direction bars,
    and supported/opposed lists. If contradictions found, regenerates the
    narrative with coherence feedback (max 2 rounds).

    Returns stats dict with coherent/incoherent counts.
    """
    from app.services.page_coherence import PageCoherenceChecker
    from app.services.member_summary import MemberSummaryService

    members_path = output_dir / "members.json"
    member_votes_dir = output_dir / "member_votes"
    summaries_path = output_dir / "member_summaries.json"

    if not members_path.exists() or not summaries_path.exists():
        print("  No members or summaries — skipping coherence check")
        return {"total": 0, "coherent": 0, "incoherent": 0}

    with open(members_path) as f:
        members = json.load(f).get("members", [])

    with open(summaries_path) as f:
        summaries = json.load(f)

    checker = PageCoherenceChecker(api_key=api_key)
    writer = MemberSummaryService(api_key=api_key)

    # Saved learnings are not fed to the checker (see sync_bill_summaries).
    checker.load_learnings([])

    stats: dict = {"total": 0, "coherent": 0, "incoherent": 0, "fixed": 0, "contradictions": []}

    for member in members:
        bioguide_id = member["bioguideId"]
        if bioguide_id not in summaries or not _is_bioguide_id(bioguide_id):
            continue

        summary = summaries[bioguide_id]
        narrative = summary.get("narrative", "")
        if not narrative:
            continue

        # Load voting record for context
        votes_path = member_votes_dir / f"{bioguide_id}.json"
        if not votes_path.exists():
            continue

        with open(votes_path) as f:
            vote_data = json.load(f)

        votes = vote_data.get("votes", [])
        member_stats = vote_data.get("stats", {})

        # Compute top areas
        area_counts: dict[str, dict] = {}
        for v in votes:
            area = v.get("policy_area", "")
            if not area:
                continue
            if area not in area_counts:
                area_counts[area] = {"name": area, "in_favor": 0, "against": 0, "neutral": 0, "total": 0}
            area_counts[area]["total"] += 1
            direction = v.get("direction")
            is_yea = v.get("vote", "").lower() in ("yea", "aye")
            is_nay = v.get("vote", "").lower() in ("nay", "no")
            if direction == "in_favor":
                if is_yea:
                    area_counts[area]["in_favor"] += 1
                elif is_nay:
                    area_counts[area]["against"] += 1
            elif direction == "against":
                if is_yea:
                    area_counts[area]["against"] += 1
                elif is_nay:
                    area_counts[area]["in_favor"] += 1
            else:
                area_counts[area]["neutral"] += 1

        top_areas = sorted(area_counts.values(), key=lambda x: x["total"], reverse=True)[:5]

        # Collect supported/opposed (single seen set prevents a bill in both lists)
        seen_bills: set[str] = set()
        top_supported: list[str] = []
        top_opposed: list[str] = []
        for v in votes:
            bill_id = v.get("bill_id")
            one_liner = v.get("one_liner", "")
            if not one_liner or not bill_id or bill_id in seen_bills:
                continue
            seen_bills.add(bill_id)
            if v.get("vote", "").lower() in ("yea", "aye"):
                top_supported.append(one_liner)
            elif v.get("vote", "").lower() in ("nay", "no"):
                top_opposed.append(one_liner)

        member_name = member.get("directOrderName") or member.get("name", bioguide_id)
        print(f"  Checking coherence for {member_name}...")

        result = await checker.check(
            narrative=narrative,
            stats=member_stats,
            top_areas=top_areas,
            top_supported=top_supported[:8],
            top_opposed=top_opposed[:6],
        )

        stats["total"] += 1

        if result.is_coherent:
            stats["coherent"] += 1
        else:
            stats["incoherent"] += 1
            stats["contradictions"].extend(result.contradictions)
            print(f"    Contradictions: {result.contradictions}")

            # Regenerate with coherence feedback (max 2 rounds)
            chamber = member.get("chamber", "")
            state = member.get("state", member.get("stateCode", ""))
            congresses = vote_data.get("congresses", [119])

            for regen_round in range(2):
                new_summary = await writer.generate_member_summary(
                    member_name=member_name,
                    chamber=chamber,
                    state=state,
                    congresses=congresses,
                    stats=member_stats,
                    top_areas=top_areas,
                    top_supported=top_supported[:8],
                    top_opposed=top_opposed[:6],
                    grader_feedback=result.guidance,
                )

                recheck = await checker.check(
                    narrative=new_summary.get("narrative", ""),
                    stats=member_stats,
                    top_areas=top_areas,
                    top_supported=top_supported[:8],
                    top_opposed=top_opposed[:6],
                )

                if recheck.is_coherent:
                    new_summary["generated_at"] = datetime.now(timezone.utc).isoformat()
                    summaries[bioguide_id] = new_summary
                    stats["fixed"] += 1
                    print(f"    Fixed after round {regen_round + 1}")
                    break

                result = recheck

                await asyncio.sleep(rate_limit)

        await asyncio.sleep(rate_limit)

    # Save updated summaries
    _atomic_write_json(summaries_path, summaries)

    print(f"  Coherence: {stats['coherent']} coherent, {stats['incoherent']} incoherent, {stats['fixed']} fixed")

    return stats


async def backfill_bill_directions(
    output_dir: Path,
    api_key: str | None = None,
    rate_limit: float = 0.5,
) -> dict:
    """Backfill 'direction' field for existing AI summaries missing it.

    For each summary without a direction, sends a lightweight prompt with
    the one_liner, provisions, and policy_area to classify direction.

    Returns stats dict with total/updated/skipped counts.
    """
    from app.services.ai_summary import AISummaryService

    bills_path = output_dir / "bills.json"
    summaries_path = output_dir / "ai_summaries.json"

    if not summaries_path.exists():
        print("  No ai_summaries.json — nothing to backfill")
        return {"total": 0, "updated": 0, "skipped": 0}

    with open(summaries_path) as f:
        summaries = json.load(f)

    # Build bill lookup for policy areas
    bill_lookup: dict[str, dict] = {}
    if bills_path.exists():
        with open(bills_path) as f:
            bills_data = json.load(f)
        for bill in bills_data.get("bills", []):
            bt = bill.get("type", "").lower()
            bn = bill.get("number", "")
            congress = bill.get("congress", 119)
            key = f"{congress}-{bt}-{bn}"
            bill_lookup[key] = bill

    # Find summaries missing direction
    to_backfill = [
        (key, summary) for key, summary in summaries.items()
        if "direction" not in summary
    ]

    if not to_backfill:
        print("  All summaries already have direction — skipping")
        return {"total": len(summaries), "updated": 0, "skipped": len(summaries)}

    print(f"  Backfilling direction for {len(to_backfill)} summaries...")

    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    service = AISummaryService(api_key=api_key, cache=cache)

    system_prompt = """You are a nonpartisan legislative analyst. Classify the direction of a bill relative to its issue area.
Return ONLY valid JSON: {"direction": "in_favor"|"against"|"neutral"}
- "in_favor": creates, funds, expands, or tightens rules in the issue area
- "against": cancels, blocks, repeals, defunds, or loosens rules in the issue area
- "neutral": unclear, procedural, or mixed"""

    stats = {"total": len(summaries), "updated": 0, "skipped": 0}

    for i, (key, summary) in enumerate(to_backfill):
        bill = bill_lookup.get(key, {})
        policy_area = bill.get("policyArea", {}).get("name", "Unknown")
        one_liner = summary.get("one_liner", "")
        provisions = summary.get("provisions", [])
        provisions_text = "; ".join(provisions[:3])

        user_prompt = f"""Bill: {one_liner}
Provisions: {provisions_text}
Policy Area: {policy_area}

Return JSON only."""

        print(f"  [{i + 1}/{len(to_backfill)}] {one_liner[:60]}...")

        try:
            raw = await service._call_llm(system_prompt, user_prompt)
            from app.services.ai_summary import _strip_code_fences
            raw = _strip_code_fences(raw)
            result = json.loads(raw)
            direction = result.get("direction", "neutral")
            if direction not in ["in_favor", "against", "neutral"]:
                direction = "neutral"
            summary["direction"] = direction
            stats["updated"] += 1
        except Exception as e:
            print(f"    SKIPPED — LLM call failed (will retry next run): {e}")
            stats["skipped"] += 1

        await asyncio.sleep(rate_limit)

    _atomic_write_json(summaries_path, summaries)
    print(f"  Backfill complete: {stats['updated']} updated")

    # Rebuild member votes with direction data
    print("  Rebuilding member voting records...")
    await build_member_votes(output_dir)

    return stats


async def _run_audit(anthropic_key: str | None) -> None:
    """Grade existing summaries and only regenerate failures."""
    from app.services.ai_summary import AISummaryService
    from app.services.summary_grader import SummaryGrader
    from app.services.writer_grader_loop import WriterGraderLoop

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    api_key = anthropic_key or None

    bills_path = SYNC_DIR / "bills.json"
    summaries_path = SYNC_DIR / "ai_summaries.json"

    if not bills_path.exists():
        print("No bills.json — nothing to audit")
        return

    with open(bills_path) as f:
        bills = json.load(f).get("bills", [])

    existing: dict[str, dict] = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    # Build bill lookup by key
    bill_by_key: dict[str, dict] = {}
    for bill in bills:
        bt = bill.get("type", "").lower()
        bn = bill.get("number", "")
        congress = bill.get("congress", 119)
        key = f"{congress}-{bt}-{bn}"
        bill_by_key[key] = bill

    # Only audit bills that have existing summaries
    to_audit = [(k, existing[k]) for k in existing if k in bill_by_key]

    if not to_audit:
        print("No summaries to audit")
        return

    print("=== ClearVote Summary Audit ===")
    print(f"  Mode: {'API' if api_key else 'Claude CLI (Max plan)'}")
    print(f"  Summaries to audit: {len(to_audit)}")
    print()

    # Setup services
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    grader = SummaryGrader(api_key=api_key)
    writer_service = AISummaryService(api_key=api_key, cache=cache)
    # Saved learnings are not fed to the grader (see sync_bill_summaries).
    grader.load_learnings([])

    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    failures: list[tuple[str, dict]] = []

    # Phase 1: Grade existing summaries
    print("[1/3] Grading existing summaries...")
    for i, (key, summary) in enumerate(to_audit):
        bill = bill_by_key[key]
        title = bill.get("title", "")
        # Grade against the same inputs Phase 2 and the weekly path write
        # from: the latest official summary (summaries[0] is the introduced
        # version) and the bill text excerpt.
        official = _latest_official_summary(bill)
        latest_action = (bill.get("latestAction") or {}).get("text", "")

        print(f"  [{i + 1}/{len(to_audit)}] {title[:60]}...")

        grade_result = await grader.grade(
            summary_type="bill_summary",
            summary_text=json.dumps(summary),
            context={"title": title, "official_summary": official,
                     "latest_action": latest_action,
                     "bill_text_excerpt": _bill_text_excerpt(bill)[:6000]},
        )

        grade_dist[grade_result.grade] = grade_dist.get(grade_result.grade, 0) + 1

        if not grade_result.passed:
            failures.append((key, bill))
            print(f"    FAIL ({grade_result.grade}): {grade_result.feedback[:80]}")
        else:
            print(f"    PASS ({grade_result.grade})")

        await asyncio.sleep(0.5)

    print()
    print(f"  Grades: {grade_dist}")
    print(f"  Passed: {grade_dist.get('A', 0) + grade_dist.get('B', 0)}")
    print(f"  Failed: {len(failures)}")
    print()

    # Phase 2: Regenerate failures through writer-grader loop
    if failures:
        print(f"[2/3] Regenerating {len(failures)} failed summaries...")
        regen_stats = {"passed": 0, "failed": 0}

        for i, (key, bill) in enumerate(failures):
            title = bill.get("title", "")
            official = _latest_official_summary(bill)
            bill_text = _bill_text_excerpt(bill)
            policy_area = bill.get("policyArea", {}).get("name")
            latest_action = (bill.get("latestAction") or {}).get("text", "")

            print(f"  [{i + 1}/{len(failures)}] {title[:60]}...")

            async def writer_fn(grader_feedback=None, _key=key, _title=title, _official=official, _bill_text=bill_text, _policy_area=policy_area, _latest_action=latest_action, **kwargs):
                return await writer_service.generate_summary(
                    bill_id=_key,
                    title=_title,
                    official_summary=_official,
                    bill_text_excerpt=_bill_text[:6000],
                    grader_feedback=grader_feedback,
                    policy_area=_policy_area,
                    latest_action=_latest_action,
                )

            loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
            result = await loop.run(
                summary_type="bill_summary",
                writer_kwargs={},
                grader_context={"title": title, "official_summary": official,
                                "latest_action": latest_action,
                                "bill_text_excerpt": bill_text[:6000]},
            )

            new_summary = result.best_summary
            if result.needs_review:
                new_summary["needs_review"] = True
                regen_stats["failed"] += 1
                print(f"    Still failing ({result.best_grade.grade}) — flagged for review")
            else:
                regen_stats["passed"] += 1
                print(f"    Fixed ({result.best_grade.grade})")

            existing[key] = new_summary
            _atomic_write_json(summaries_path, existing)

            await asyncio.sleep(1.0)

        print()
        print(f"  Regenerated: {regen_stats['passed']} fixed, {regen_stats['failed']} still need review")
    else:
        print("[2/3] No failures — skipping regeneration")

    # Save final summaries
    _atomic_write_json(summaries_path, existing)

    # Phase 3: Rebuild member votes
    print()
    print("[3/3] Rebuilding member voting records...")
    await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)

    print()
    print("=== Audit complete ===")


async def sync_donations(
    sync_dir: Path,
    states: list[str] | None = None,
    rate_limit: float = 0.5,
) -> dict:
    """Sync campaign finance data from FEC API.

    For each member: searches FEC by name → gets candidate ID →
    finds principal committee → pulls top employers and occupations.
    Saves to donations.json. Incremental — skips already-synced members.
    """
    from app.services.fec_api import FECClient

    api_key = os.getenv("FEC_API_KEY", "")
    if not api_key:
        print("  FEC_API_KEY not set — skipping donation sync")
        print("  Get a free key at https://api.data.gov/signup/")
        return {}

    client = FECClient(api_key=api_key)

    # Load existing donations for incremental sync
    donations_path = sync_dir / "donations.json"
    if donations_path.exists():
        with open(donations_path) as f:
            donations = json.load(f)
    else:
        donations = {}

    # Load members to know who to sync
    members_path = sync_dir / "members.json"
    if not members_path.exists():
        print("  No members.json found — run full sync first")
        return {}
    with open(members_path) as f:
        members_data = json.load(f)
    members = members_data.get("members", [])

    # Filter to members in requested states
    if states:
        members = [m for m in members if m.get("stateCode", "") in states]

    # Skip already-synced members
    to_sync = [m for m in members if m.get("bioguideId", "").upper() not in donations]
    if not to_sync:
        print(f"  All {len(members)} members already synced — skipping")
        return {"synced": 0, "skipped": len(members), "errors": 0, "total": len(donations)}

    print(f"  Syncing donations for {len(to_sync)} members ({len(members) - len(to_sync)} already done)")

    synced = 0
    skipped = 0
    errors = 0

    for member in to_sync:
        bioguide = member.get("bioguideId", "").upper()
        name_raw = member.get("name", "")
        # Members data has "Last, First M." format — extract name without middle initial
        parts = name_raw.split(",")
        last_name = parts[0].strip()
        first_name_raw = parts[1].strip() if len(parts) > 1 else ""
        first_name = first_name_raw.split()[0] if first_name_raw else ""
        full_name = f"{last_name}, {first_name}" if first_name else last_name
        state = member.get("stateCode", "")
        chamber = member.get("chamber", "")
        office = "S" if chamber == "Senate" else "H" if chamber == "House" else ""

        try:
            # Step 1: Find candidate in FEC (full name, fallback to last name for nicknames)
            await asyncio.sleep(rate_limit)
            candidate = await client.search_candidate(full_name, state, office)
            if not candidate and first_name:
                await asyncio.sleep(rate_limit)
                candidate = await client.search_candidate(last_name, state, office)
            if not candidate:
                print(f"    {full_name} ({state}): not found in FEC — skipping")
                skipped += 1
                continue

            # Step 2: Get principal campaign committee
            await asyncio.sleep(rate_limit)
            committee_id = await client.get_principal_committee(candidate["candidate_id"])
            if not committee_id:
                print(f"    {full_name} ({state}): no campaign committee — skipping")
                skipped += 1
                continue

            # Step 3: Get top employers and occupations in parallel
            await asyncio.sleep(rate_limit)
            results = await asyncio.gather(
                client.get_top_employers(committee_id, cycle=2024),
                client.get_top_occupations(committee_id, cycle=2024),
                client.get_committee_totals(committee_id, cycle=2024),
                return_exceptions=True,
            )
            employers = results[0] if not isinstance(results[0], Exception) else []
            occupations = results[1] if not isinstance(results[1], Exception) else []
            totals = results[2] if not isinstance(results[2], Exception) else None

            donations[bioguide] = {
                "fec_candidate_id": candidate["candidate_id"],
                "committee_id": committee_id,
                "cycle": "2024",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "top_contributors": [
                    {"org_name": e["org_name"], "total": e["total"], "pacs": 0, "individuals": e["total"]}
                    for e in employers
                ],
                "top_industries": [
                    {"industry_name": o["industry_name"], "total": o["total"], "pacs": 0, "individuals": o["total"]}
                    for o in occupations
                ],
                "totals": totals or {},
            }
            synced += 1
            print(f"    {full_name} ({state}): {len(employers)} employers, {len(occupations)} occupations")

            # Save after each member (crash-safe)
            if synced % 5 == 0:
                _atomic_write_json(donations_path, donations)

        except Exception as e:
            print(f"    {full_name} ({state}): error — {_error_summary(e)}")
            errors += 1

    _atomic_write_json(donations_path, donations)
    print(f"  Donations sync: {synced} new, {skipped} skipped, {errors} errors ({len(donations)} total)")
    return {"synced": synced, "skipped": skipped, "errors": errors, "total": len(donations)}


async def _ai_preflight(anthropic_key: str) -> None:
    """Fail fast (exit 1) if the AI credential is dead.

    Without this, a dead credential (expired CLAUDE_CODE_OAUTH_TOKEN, revoked
    API key) degrades into a per-bill 'SKIPPED' exception for every bill,
    exit code 0, and a green CI run that generated nothing.
    """
    from app.services.grader_common import CLAUDE_MODEL

    try:
        if anthropic_key:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=anthropic_key)
            await client.messages.create(
                model=CLAUDE_MODEL, max_tokens=8,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
        else:
            from app.services.claude_cli import call_claude_cli
            await call_claude_cli("You echo exactly what is asked.",
                                  "Reply with exactly: OK")
    except Exception as e:
        print(f"ERROR: AI credential preflight failed — aborting before generation: {e}")
        if anthropic_key:
            print("  Check the ANTHROPIC_API_KEY secret/environment variable.")
        else:
            print("  Claude CLI mode: regenerate the token with 'claude setup-token' and")
            print("  update the CLAUDE_CODE_OAUTH_TOKEN secret (locally: 'claude auth login').")
        sys.exit(1)


async def main() -> None:
    parser = argparse.ArgumentParser(description="ClearVote Data Sync")
    parser.add_argument("--states", type=str, default=None,
                        help="Comma-separated state codes (e.g., NY,FL). Default: all states.")
    parser.add_argument("--grade", action="store_true",
                        help="Re-grade existing AI summaries without re-syncing source data.")
    parser.add_argument("--audit", action="store_true",
                        help="Grade existing summaries and only regenerate failures.")
    parser.add_argument("--backfill-direction", action="store_true",
                        help="Backfill direction field for AI summaries missing it.")
    parser.add_argument("--regenerate-member-summaries", action="store_true",
                        help="Force regeneration of all AI member summaries.")
    parser.add_argument("--check-coherence", action="store_true",
                        help="Check page coherence between narratives and data sections.")
    parser.add_argument("--regenerate-all-summaries", action="store_true",
                        help="Clear and regenerate ALL AI bill summaries and member summaries.")
    parser.add_argument("--regenerate-arguments", action="store_true",
                        help="Clear and regenerate all bill both-sides arguments.")
    parser.add_argument("--skip-donations", action="store_true",
                        help="Skip FEC donation sync (useful if no API key).")
    parser.add_argument("--resync-donations", action="store_true",
                        help="Clear and re-fetch all FEC donation data (fixes bad matches).")
    parser.add_argument("--step", type=str, default=None,
                        choices=["members", "senate-votes", "house-votes", "bills",
                                 "votes-index", "member-votes", "state-overview", "metadata", "validate"],
                        help="Run a single sync step (for CI incremental workflows).")
    parser.add_argument("--max-text-fetches", type=int, default=300,
                        help="Per-run cap on bill-text downloads (congress.gov rate-limits CI; the fetch is incremental).")
    parser.add_argument("--congress", type=int, default=None,
                        help="Specific congress number (use with --step senate-votes or house-votes).")
    parser.add_argument("--session", type=int, default=None,
                        help="Specific session number (use with --step senate-votes or house-votes).")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--skip-ai", action="store_true",
                            help="Skip the AI bill-summary step (5). Run government data only.")
    mode_group.add_argument("--ai-only", action="store_true",
                            help="Run only the AI bill-summary step (5). Assumes gov data is fresh.")
    args = parser.parse_args()

    raw_key = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_key = raw_key if raw_key.startswith("sk-") else ""

    # --- Offline builders: they read data/synced only, so no API key is needed ---
    if args.step == "votes-index":
        print("[step] Building the votes index...")
        build_votes_index(SYNC_DIR)
        return

    if args.step == "state-overview":
        states = [s.strip().upper() for s in args.states.split(",")] if args.states else SYNC_STATES
        print(f"[step] Building state overviews for {', '.join(states)}...")
        if not build_state_overview(SYNC_DIR, states=states):
            sys.exit(1)
        return

    # --- Single-step mode (for CI incremental workflows) ---
    if args.step:
        api_key = os.getenv("CONGRESS_API_KEY", "")
        if not api_key:
            print("ERROR: CONGRESS_API_KEY not set in .env")
            sys.exit(1)

        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
        client = CongressAPIClient(api_key=api_key, cache=cache)
        states = [s.strip().upper() for s in args.states.split(",")] if args.states else SYNC_STATES

        if args.step == "members":
            print(f"[step] Syncing members for {', '.join(states)}...")
            await sync_members(client, SYNC_DIR, states=states, rate_limit=0.5)

        elif args.step == "senate-votes":
            senate_service = SenateVoteService(cache=cache)
            pairs = [(args.congress, args.session)] if args.congress and args.session else CONGRESSES
            failures: list[str] = []
            for congress, session in pairs:
                print(f"[step] Syncing Senate votes — Congress {congress}, Session {session}...")
                await sync_senate_votes(senate_service, SYNC_DIR, congress=congress, session=session, rate_limit=0.3,
                                        failures=failures)
            _exit_on_vote_failures(failures)

        elif args.step == "house-votes":
            pairs = [(args.congress, args.session)] if args.congress and args.session else CONGRESSES
            failures = []
            for congress, session in pairs:
                print(f"[step] Syncing House votes — Congress {congress}, Session {session}...")
                await sync_house_votes(client, SYNC_DIR, congress=congress, session=session, rate_limit=0.3,
                                       failures=failures)
            _exit_on_vote_failures(failures)

        elif args.step == "bills":
            print("[step] Syncing voted-on bills...")
            await sync_bills_from_votes(client, SYNC_DIR, rate_limit=0.5)
            print("[step] Fetching bill text for bills missing it...")
            await fetch_bill_texts(client, SYNC_DIR, rate_limit=0.3, max_fetches=args.max_text_fetches)

        elif args.step == "member-votes":
            print("[step] Building member voting records...")
            await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)

        elif args.step == "validate":
            print("[step] Validating synced data...")
            if run_validation(SYNC_DIR):
                sys.exit(1)

        elif args.step == "metadata":
            print("[step] Writing sync metadata...")
            metadata = {
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "states_synced": states,
                "incremental": True,
            }
            metadata.update(_ai_summaries_stamp(SYNC_DIR))
            _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)

        return

    # --- Audit mode: grade existing, only regenerate failures ---
    if args.audit:
        await _run_audit(anthropic_key)
        return

    # --- Backfill direction mode ---
    if args.backfill_direction:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        print("=== ClearVote Direction Backfill ===")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
        print()
        await backfill_bill_directions(SYNC_DIR, api_key=anthropic_key or None)
        print()
        print("=== Backfill complete ===")
        return

    # --- Regenerate member summaries mode ---
    if args.regenerate_member_summaries:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        print("=== ClearVote Member Summary Regeneration ===")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
        print()
        # Clear existing summaries to force regeneration
        summaries_path = SYNC_DIR / "member_summaries.json"
        if summaries_path.exists():
            backup_path = SYNC_DIR / "member_summaries.backup.json"
            shutil.copy2(summaries_path, backup_path)
            print(f"  Backed up existing summaries to {backup_path.name}")
            _atomic_write_json(summaries_path, {})
            print("  Cleared existing member summaries")
        stats = await sync_member_summaries(SYNC_DIR, api_key=anthropic_key or None)
        print()
        if stats.get("total"):
            print(f"  Narratives graded: {stats['total']} ({stats.get('passed', 0)} passed, {stats.get('failed', 0)} flagged)")
        print("=== Regeneration complete ===")
        return

    # --- Regenerate arguments mode ---
    if args.regenerate_arguments:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        print("=== ClearVote Bill Arguments Regeneration ===")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
        print()

        # Strip existing arguments to force regeneration
        summaries_path = SYNC_DIR / "ai_summaries.json"
        if summaries_path.exists():
            with open(summaries_path) as f:
                summaries = json.load(f)
            for key in summaries:
                summaries[key].pop("arguments", None)
            _atomic_write_json(summaries_path, summaries)
            print(f"  Cleared existing arguments from {len(summaries)} summaries")

        batch = 10 if not anthropic_key else 5  # CLI is slower — use higher parallelism
        stats = await sync_bill_arguments(SYNC_DIR, api_key=anthropic_key or None, batch_size=batch, rate_limit=1.0)
        print()
        if stats.get("total"):
            print(f"  Arguments graded: {stats['total']} ({stats.get('passed', 0)} passed, {stats.get('failed', 0)} flagged)")
        print("=== Regeneration complete ===")
        return

    # --- Regenerate all summaries mode ---
    if args.regenerate_all_summaries:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        print("=== ClearVote Full Summary Regeneration ===")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
        print()

        # Back up and clear AI summaries
        ai_summaries_path = SYNC_DIR / "ai_summaries.json"
        if ai_summaries_path.exists():
            backup_path = SYNC_DIR / "ai_summaries.backup.json"
            shutil.copy2(ai_summaries_path, backup_path)
            print(f"  Backed up AI summaries to {backup_path.name}")
            _atomic_write_json(ai_summaries_path, {})
            print("  Cleared existing AI bill summaries")

        # Back up and clear member summaries
        member_summaries_path = SYNC_DIR / "member_summaries.json"
        if member_summaries_path.exists():
            backup_path = SYNC_DIR / "member_summaries.backup.json"
            shutil.copy2(member_summaries_path, backup_path)
            print(f"  Backed up member summaries to {backup_path.name}")
            _atomic_write_json(member_summaries_path, {})
            print("  Cleared existing member summaries")

        print()
        print("[1/4] Regenerating AI bill summaries...")
        summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key or None, batch_size=5, rate_limit=1.0)

        print()
        print("[2/4] Rebuilding member voting records...")
        await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)

        print()
        print("[3/4] Generating issue scorecard verdicts...")
        await generate_scorecard_verdicts(SYNC_DIR, api_key=anthropic_key or None)

        print()
        print("[4/4] Regenerating member narratives...")
        member_stats = await sync_member_summaries(SYNC_DIR, api_key=anthropic_key or None)

        print()
        print("=== Full regeneration complete ===")
        if summary_stats.get("total"):
            print(f"  Bill summaries: {summary_stats['total']} ({summary_stats.get('passed', 0)} passed)")
        if member_stats.get("total"):
            print(f"  Member narratives: {member_stats['total']} ({member_stats.get('passed', 0)} passed)")
        return

    # --- Check coherence mode ---
    if args.check_coherence:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        print("=== ClearVote Page Coherence Check ===")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
        print()
        coherence_stats = await check_page_coherence(SYNC_DIR, api_key=anthropic_key or None)
        print()
        if coherence_stats.get("total"):
            print(f"  Checked: {coherence_stats['total']} members")
            print(f"  Coherent: {coherence_stats.get('coherent', 0)}")
            print(f"  Incoherent: {coherence_stats.get('incoherent', 0)}")
            print(f"  Fixed: {coherence_stats.get('fixed', 0)}")
        print("=== Coherence check complete ===")
        return

    # --- Re-grade mode ---
    if args.grade:

        SYNC_DIR.mkdir(parents=True, exist_ok=True)

        print("=== ClearVote Re-Grade Mode ===")
        print("Re-grading all existing AI summaries...")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
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
        await sync_bill_summaries(SYNC_DIR, anthropic_key or None, batch_size=5, rate_limit=1.0)

        print()
        print("[2/2] Re-building member voting records...")
        await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key or None)

        print()
        print("=== Re-grade complete ===")
        return

    # --- Normal sync mode ---
    states = [s.strip().upper() for s in args.states.split(",")] if args.states else SYNC_STATES

    # --ai-only mode: skip government data steps, go straight to AI
    if args.ai_only:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        ai_digest_before = _ai_summaries_digest(SYNC_DIR)
        print("=== ClearVote AI-Only Sync ===")
        print(f"  Mode: {'API' if anthropic_key else 'Claude CLI (Max plan)'}")
        print()

        await _ai_preflight(anthropic_key)

        # Step 5: AI bill summaries — the only AI text the site publishes.
        # Arguments, scorecard verdicts, member narratives and coherence checks
        # are withdrawn; they run only through their own opt-in flags.
        print("[5/8] Generating graded AI bill summaries...")
        summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key or None, batch_size=5, rate_limit=1.0)

        # Step 8: Update only the AI keys of the metadata. last_sync,
        # states_synced and the counts describe the government-data sync (the
        # footer's "Data synced" date), so an AI run carries them over untouched.
        print()
        print("[8/8] Writing sync metadata...")
        try:
            metadata = json.loads((SYNC_DIR / "sync_metadata.json").read_text())
        except (OSError, ValueError):
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["ai_synced_at"] = datetime.now(timezone.utc).isoformat()
        metadata["summary_stats"] = summary_stats
        metadata.update(_ai_summaries_stamp(SYNC_DIR, rewrote=_ai_summaries_digest(SYNC_DIR) != ai_digest_before))
        _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)

        print()
        print("=== AI-only sync complete ===")
        if summary_stats.get("total"):
            print(f"  Bill summaries: {summary_stats['total']} ({summary_stats.get('passed', 0)} passed)")

        # A run that attempted work but persisted nothing means every call
        # failed (dead credential mid-run, hard outage). Exit non-zero so CI
        # shows red instead of a green run that generated nothing.
        # needs_review entries count as persisted — they are saved, just flagged.
        attempted = summary_stats.get("total", 0)
        persisted = summary_stats.get("passed", 0) + len(summary_stats.get("needs_review", []))
        if attempted > 0 and persisted == 0:
            print(f"ERROR: attempted {attempted} generations, persisted none — "
                  "treating as total failure.")
            sys.exit(1)
        return

    api_key = os.getenv("CONGRESS_API_KEY", "")
    if not api_key:
        print("ERROR: CONGRESS_API_KEY not set in .env")
        sys.exit(1)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    ai_digest_before = _ai_summaries_digest(SYNC_DIR)
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    client = CongressAPIClient(api_key=api_key, cache=cache)

    state_label = ", ".join(states) if states else "all states"
    print("=== ClearVote Data Sync ===")
    print(f"States: {state_label}")
    print(f"Output: {SYNC_DIR}")
    print()

    # Step 1: Members
    print("[1/8] Syncing members...")
    members_count = await sync_members(client, SYNC_DIR, states=states, rate_limit=0.5)

    # Step 2: Senate votes (all congresses)
    print()
    senate_service = SenateVoteService(cache=cache)
    print("[2/8] Syncing Senate votes...")
    senate_count = 0
    vote_failures: list[str] = []  # the run finishes, then exits 1 if any session stopped early
    for congress, session in CONGRESSES:
        print(f"  Congress {congress}, Session {session}...")
        count = await sync_senate_votes(senate_service, SYNC_DIR, congress=congress, session=session, rate_limit=0.3,
                                        failures=vote_failures)
        senate_count += count

    # Step 3: House votes (all congresses)
    print()
    print("[3/8] Syncing House votes...")
    house_count = 0
    for congress, session in CONGRESSES:
        print(f"  Congress {congress}, Session {session}...")
        count = await sync_house_votes(client, SYNC_DIR, congress=congress, session=session, rate_limit=0.3,
                                       failures=vote_failures)
        house_count += count

    # Step 4: Bills (only those referenced in votes from both chambers)
    print()
    print("[4/8] Syncing voted-on bills...")
    bills_count = await sync_bills_from_votes(client, SYNC_DIR, rate_limit=0.5)
    print("  Fetching bill text for bills missing it...")
    await fetch_bill_texts(client, SYNC_DIR, rate_limit=0.3, max_fetches=args.max_text_fetches)

    # Step 5: AI bill summaries (writer-grader loop) — the only AI text the
    # site publishes. Arguments, scorecard verdicts, member narratives and
    # coherence checks are withdrawn; they run only through their own flags.
    summary_stats = {}
    if not args.skip_ai:
        print()
        print(f"[5/8] Generating graded AI bill summaries ({'API' if anthropic_key else 'Claude CLI'})...")
        summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key or None, batch_size=5, rate_limit=1.0)
    else:
        print()
        print("[5/8] Skipping AI bill summaries (--skip-ai)")

    # Step 6: Member voting records (both chambers)
    print()
    print("[6/8] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)
    print("[6/8] Building the votes index...")
    build_votes_index(SYNC_DIR)
    build_state_overview(SYNC_DIR, states=states)

    # Step 7: Campaign finance (FEC)
    donations_stats = {}
    if not args.skip_donations:
        if args.resync_donations:
            donations_path = SYNC_DIR / "donations.json"
            if donations_path.exists():
                backup_path = SYNC_DIR / "donations.backup.json"
                shutil.copy2(donations_path, backup_path)
                print(f"  Backed up existing donations to {backup_path.name}")
                _atomic_write_json(donations_path, {})
                print("  Cleared existing donation data for re-sync")
        print()
        print("[7/8] Syncing campaign finance data (FEC)...")
        donations_stats = await sync_donations(SYNC_DIR, states=states, rate_limit=1.0)
    else:
        print()
        print("[7/8] Skipping campaign finance sync (--skip-donations)")

    # Step 8: Sync summary
    print()
    print("[8/8] Sync summary")

    # Write metadata
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "states_synced": states,
        "members_count": members_count,
        "bills_count": bills_count,
        "senate_votes_count": senate_count,
        "house_votes_count": house_count,
        "member_votes_count": member_votes_count,
        "summary_stats": summary_stats,
        "donations_stats": donations_stats,
    }
    metadata.update(_ai_summaries_stamp(SYNC_DIR, rewrote=_ai_summaries_digest(SYNC_DIR) != ai_digest_before))
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
    if donations_stats.get("total"):
        print(f"  Donations: {donations_stats['total']} members ({donations_stats.get('synced', 0)} new)")
    _exit_on_vote_failures(vote_failures)

if __name__ == "__main__":
    asyncio.run(main())
