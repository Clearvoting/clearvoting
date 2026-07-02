"""Post-sync validation of data/synced — bad data fails the sync loudly.

Encodes the July 2026 incidents as assertions so they cannot recur silently:
scorecard wipes on rebuild, display-string vote dates, lexicographic sort,
placeholder summaries shipped to readers, silent summary loss.

Two severities: FAILURES block the sync (exit non-zero); WARNINGS are printed
but do not block (e.g. orphan files for departed members).
"""
import json
import re
from pathlib import Path

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_PLACEHOLDER_MARKERS = ("temporarily unavailable",)


def _load(path: Path):
    with open(path) as f:
        return json.load(f)


def validate_synced_data(
    sync_dir: Path,
    previous_summaries: dict | None = None,
    previous_scorecard_members: set | None = None,
) -> tuple[list[str], list[str]]:
    """Validate data/synced. Returns (failures, warnings)."""
    failures: list[str] = []
    warnings: list[str] = []

    # --- members.json ---
    members_path = sync_dir / "members.json"
    if not members_path.exists():
        failures.append("members.json missing")
        return failures, warnings
    try:
        members = _load(members_path).get("members", [])
    except json.JSONDecodeError:
        failures.append("members.json is not valid JSON")
        return failures, warnings
    member_ids = {m.get("bioguideId") for m in members if m.get("bioguideId")}
    if not member_ids:
        failures.append("members.json contains no members")

    # --- bills.json ---
    bills_path = sync_dir / "bills.json"
    bill_keys: set = set()
    if bills_path.exists():
        try:
            bills = _load(bills_path).get("bills", [])
            bill_keys = {f"{b.get('congress')}-{str(b.get('type', '')).lower()}-{b.get('number')}" for b in bills}
        except json.JSONDecodeError:
            failures.append("bills.json is not valid JSON")
    else:
        failures.append("bills.json missing")

    # --- ai_summaries.json ---
    summaries: dict = {}
    summaries_path = sync_dir / "ai_summaries.json"
    if summaries_path.exists():
        try:
            summaries = _load(summaries_path)
        except json.JSONDecodeError:
            failures.append("ai_summaries.json is not valid JSON")
        for key, s in summaries.items():
            text = " ".join([(s.get("one_liner") or "")] + [str(p) for p in (s.get("provisions") or [])]).lower()
            for marker in _PLACEHOLDER_MARKERS:
                if marker in text:
                    failures.append(f"ai_summaries[{key}]: placeholder text shipped to readers")
            if not (s.get("one_liner") or "").strip():
                failures.append(f"ai_summaries[{key}]: empty one_liner")
            if not s.get("provisions"):
                failures.append(f"ai_summaries[{key}]: empty provisions")

    if previous_summaries:
        lost = set(previous_summaries) - set(summaries)
        for key in sorted(lost)[:10]:
            failures.append(f"summary lost vs previous sync: {key}")
        if len(lost) > 10:
            failures.append(f"...and {len(lost) - 10} more lost summaries")

    # --- member_votes/*.json ---
    votes_dir = sync_dir / "member_votes"
    scorecard_members: set = set()
    seen_files: set = set()
    if votes_dir.exists():
        for f_path in sorted(votes_dir.glob("*.json")):
            member_id = f_path.stem
            seen_files.add(member_id)
            try:
                record = _load(f_path)
            except json.JSONDecodeError:
                failures.append(f"member_votes/{member_id}.json is not valid JSON")
                continue
            if member_id not in member_ids:
                warnings.append(f"member_votes/{member_id}.json is an orphan (not in members.json)")
                continue  # orphans are stale by definition — don't hold them to current rules
            if record.get("scorecard"):
                scorecard_members.add(member_id)
            votes = record.get("votes", [])
            keys = []
            for v in votes:
                date = v.get("date", "")
                if not _ISO_DATE.match(date):
                    failures.append(f"member_votes/{member_id}.json: non-ISO vote date {date!r}")
                    break
                keys.append((date, v.get("vote_number", 0)))
            if keys and keys != sorted(keys, reverse=True):
                failures.append(f"member_votes/{member_id}.json: votes not sorted newest-first")
    missing_files = member_ids - seen_files
    for member_id in sorted(missing_files):
        failures.append(f"member {member_id} has no member_votes file")

    if previous_scorecard_members:
        wiped = previous_scorecard_members - scorecard_members - (previous_scorecard_members - member_ids)
        for member_id in sorted(wiped):
            failures.append(f"scorecard wiped for {member_id} (present in previous sync, empty now)")

    return failures, warnings
