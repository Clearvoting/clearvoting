import json
import logging
import re
from datetime import datetime
from pathlib import Path

from app import render

logger = logging.getLogger(__name__)

# Matches bill documents in vote files, e.g. "H.R. 1", "H.Res. 24", "S.J.Res. 10".
# Tolerates optional spaces between abbreviation parts ("H. Res. 88").
_BILL_DOCUMENT_RE = re.compile(r"^([A-Za-z]+(?:\.\s*[A-Za-z]+)*\.?)\s+(\d+)$")

# Vote dates look like "June 5, 2026,  04:52 AM" (note the double space before time);
# also accept bare dates and ISO so synthetic/test data parses too.
_VOTE_DATE_FORMATS = ("%B %d, %Y, %I:%M %p", "%B %d, %Y", "%Y-%m-%d")


def _parse_vote_date(raw: str) -> datetime | None:
    cleaned = re.sub(r"\s+", " ", (raw or "").strip())
    for fmt in _VOTE_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _clean_vote_date(raw: str) -> str:
    """Strip the time off a vote date: 'June 5, 2026,  04:52 AM' -> 'June 5, 2026'."""
    parts = [p.strip() for p in (raw or "").split(",")]
    if len(parts) >= 2:
        return f"{parts[0]}, {parts[1]}"
    return (raw or "").strip()


def roll_call_key(chamber, congress, session, vote_number) -> str:
    """The votes_index.json key of one roll call, e.g. 'house/119_2_00295' (spec §10 #3).

    `chamber` is 'House'/'Senate' in member_votes rows and 'house'/'senate' for the vote
    directories; both give the same key. A missing part raises TypeError/ValueError."""
    return f"{str(chamber).strip().lower()}/{int(congress)}_{int(session)}_{int(vote_number):05d}"


# §3.2: five digits, optionally followed by a ZIP+4 suffix; surrounding spaces are ignored.
ZIP_INPUT_RE = re.compile(r"^\s*(\d{5})(?:[-\s]?\d{4})?\s*$")
ZIP_MATCH_SHARE = 0.05    # §5.1: a district matches at >= 5 % of the ZCTA's land area
ZIP_COVERED_SHARE = 0.95  # §5.1: below this, part of the ZIP lies outside the four covered states
COVERED_STATE_NAMES = {"CA": "California", "FL": "Florida", "NY": "New York", "TX": "Texas"}


def normalize_zip(raw: str | None) -> str | None:
    """The five-digit ZIP from a typed value ('11570-1234', ' 11570 ') or None when malformed."""
    match = ZIP_INPUT_RE.match(raw or "")
    return match.group(1) if match else None


def _latest_official_summary(bill: dict) -> str:
    """Congress.gov orders summaries oldest-first, so [0] is the introduced
    version — which can describe provisions that never became law (e.g. the
    IRA's introduced summary is Build Back Better). Prefer the Public Law
    summary; otherwise the newest by actionDate."""
    summaries = bill.get("summaries")
    if not isinstance(summaries, list) or not summaries:
        return ""
    law = [s for s in summaries if "public law" in (s.get("actionDesc") or "").lower()]
    pool = law or summaries
    best = max(pool, key=lambda s: s.get("actionDate") or "")
    return best.get("text", "") or ""


_STATE_CODE_RE = re.compile(r"[A-Z]{2}")


def overview_member(member: dict, latest_vote: dict | None = None) -> dict:
    """One delegation row of state_overview/{code}.json: raw members.json fields only (§10 #7).
    Seals, tenure lines and headlines are formatted at render time, so a formatter fix needs
    no resync. partyName is kept raw; the API strips it unless show_party=true."""
    terms = [
        {key: term[key] for key in ("chamber", "startYear", "endYear") if term.get(key) is not None}
        for term in ((member.get("terms") or {}).get("item") or [])
    ]
    senate = "Senate" in (member.get("chamber") or "")
    return {
        "bioguideId": member.get("bioguideId"),
        "name": member.get("name"),
        "district": None if senate else member.get("district"),
        "chamber": member.get("chamber"),
        "photo": (member.get("depiction") or {}).get("imageUrl"),
        "terms": terms,
        "partyName": member.get("partyName"),
        "latest_vote": latest_vote,
    }


def state_overview_payload(code: str, members: list[dict], latest_votes: dict[str, dict | None],
                           districts_expected: int) -> dict:
    """The delegation file for one state, without generated_at. Senators by name; House
    members by district, then name."""
    state_members = [m for m in members if m.get("stateCode") == code]
    senators = sorted((m for m in state_members if "Senate" in (m.get("chamber") or "")),
                      key=lambda m: str(m.get("name") or ""))
    house = sorted((m for m in state_members if "Senate" not in (m.get("chamber") or "")),
                   key=lambda m: (m.get("district") or 0, str(m.get("name") or "")))
    roster_as_of = max((str(m.get("updateDate") or "")[:10] for m in state_members), default="")
    return {
        "state": code,
        "state_name": COVERED_STATE_NAMES.get(code)
        or next((m.get("state") for m in state_members if m.get("state")), code),
        "roster_as_of": roster_as_of or None,
        "senators": [overview_member(m, latest_votes.get(m.get("bioguideId"))) for m in senators],
        "house": [overview_member(m, latest_votes.get(m.get("bioguideId"))) for m in house],
        "districts_expected": districts_expected,
    }


# ---------------------------------------------------------------------------
# Member page payload (plan T1.7; spec §4.3 m2, m4, m5, m7, §2.5 B, §10 #8).
# Pure functions over member_votes rows and votes_index.json entries, so the
# rules can be tested without a data directory.
# ---------------------------------------------------------------------------

RECORD_PER_PAGE = 15
RECORD_API_MAX_GROUPS = 50
RECENT_VOTES_LIMIT = 8
SPONSORED_LIMIT = 6
SPEAKER_QUESTION = "Election of the Speaker"
_YES_VOTES = frozenset({"Yea", "Aye"})
_NO_VOTES = frozenset({"Nay", "No"})
_KNOWN_POSITIONS = frozenset({
    "Yea", "Aye", "Nay", "No", "Not Voting", "Present", "Present, Giving Live Pair",
    "Guilty", "Not Guilty",
})
_PARTY_KEYS = frozenset({"party", "partyName", "partyCode"})
_MONEY_TOTAL_KEYS = ("total_receipts", "total_individual", "total_pac", "total_disbursements")
_BILL_ID_RE = re.compile(r"^(\d{1,3})-([a-z]+)-(\d{1,5})$")


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def rc_key_or_none(chamber, congress, session, vote_number) -> str | None:
    """T1.4's roll_call_key for rows that may be incomplete: 'Senate', 119, 2, 228 ->
    'senate/119_2_00228'. None instead of TypeError/ValueError, and None for a chamber
    that is neither House nor Senate. roll_call_key itself is not redefined."""
    name = str(chamber or "").strip().lower()
    if name.startswith("senate"):
        prefix = "senate"
    elif name.startswith("house"):
        prefix = "house"
    else:
        return None
    try:
        return roll_call_key(prefix, congress, session, vote_number)
    except (TypeError, ValueError):
        return None


def _bill_id_parts(bill_id) -> tuple[int, str, int] | None:
    """'119-hr-6500' -> (119, 'hr', 6500); None for anything else."""
    match = _BILL_ID_RE.match(str(bill_id or ""))
    if not match:
        return None
    return int(match.group(1)), match.group(2), int(match.group(3))


def position_class(vote) -> str:
    """§7.1 positions: Yea/Aye -> 'yes', Nay/No -> 'no', Not Voting -> 'nv', else 'other'."""
    vote = str(vote or "")
    if vote in _YES_VOTES:
        return "yes"
    if vote in _NO_VOTES:
        return "no"
    if vote == "Not Voting":
        return "nv"
    return "other"


def is_speaker_vote(row: dict, entry: dict | None) -> bool:
    """A Speaker election: the index question says so, or the position is a candidate name."""
    entry = entry or {}
    if SPEAKER_QUESTION in (entry.get("question"), entry.get("plain")):
        return True
    vote = str(row.get("vote") or "")
    return bool(vote) and vote not in _KNOWN_POSITIONS


def _newest_first(votes: list[dict]) -> list[dict]:
    """Newest first by calendar day, then roll-call number. Some stored times are twelve
    hours off inside a day, so the roll-call number orders votes within one day."""
    return sorted(
        votes,
        key=lambda v: (str(v.get("date") or "")[:10], _as_int(v.get("congress")),
                       _as_int(v.get("session")), _as_int(v.get("vote_number"))),
        reverse=True,
    )


def pick_recent_votes(votes: list[dict], roll_calls: dict, plain_one_liner,
                      limit: int = RECENT_VOTES_LIMIT) -> list[dict]:
    """'Recent votes' (§4.3 m2, §2.5 B). `votes` are member_votes rows, newest first.

    Candidates: a bill vote whose index class is D, whose bill has a displayable summary
    (`plain_one_liner(bill_id)` returns its one-liner), with a non-empty policy area and a
    Yea/Aye/Nay/No position. Dedupe: the first qualifying vote per bill, newest first; a bill
    is marked seen only when one of its votes is picked. Spread: round-robin over policy
    areas in order of each area's newest candidate. Output newest first. The member's
    position is never a selection criterion."""
    seen: set[str] = set()
    candidates: list[dict] = []
    for row in votes:
        bill_id = row.get("bill_id")
        if not bill_id or bill_id in seen:
            continue
        position = position_class(row.get("vote"))
        area = str(row.get("policy_area") or "").strip()
        key = rc_key_or_none(row.get("chamber"), row.get("congress"), row.get("session"), row.get("vote_number"))
        entry = roll_calls.get(key) if key else None
        parts = _bill_id_parts(bill_id)
        if position not in ("yes", "no") or not area or not entry or entry.get("class") != "D" or not parts:
            continue
        one_liner = plain_one_liner(bill_id)
        if not one_liner:
            continue
        seen.add(bill_id)
        candidates.append({
            "rc": key,
            "roll_call": entry,
            "chamber": "Senate" if key.startswith("senate/") else "House",
            "bill_id": bill_id,
            "congress": parts[0],
            "bill_type": parts[1],
            "bill_number": parts[2],
            "one_liner": one_liner,
            "position": position,
            "date": str(row.get("date") or ""),
            "policy_area": area,
        })
    by_area: dict[str, list[dict]] = {}
    for candidate in candidates:
        by_area.setdefault(candidate["policy_area"], []).append(candidate)
    queues = list(by_area.values())
    picked: list[dict] = []
    while len(picked) < limit and any(queues):
        for queue in queues:
            if queue and len(picked) < limit:
                picked.append(queue.pop(0))
    order = {candidate["rc"]: i for i, candidate in enumerate(candidates)}
    picked.sort(key=lambda candidate: order[candidate["rc"]])
    return picked


def filter_record_votes(votes: list[dict], topic, position, plain, plain_one_liner) -> list[dict]:
    """The record's GET filters (§4.3 m4), applied to vote rows before grouping: `topic`
    (policy area, exact), `position` ('yes' | 'no' | 'nv'), `plain` (only bills whose
    summary is displayable)."""
    kept = []
    for row in votes:
        if topic and str(row.get("policy_area") or "") != topic:
            continue
        if position and position_class(row.get("vote")) != position:
            continue
        if plain and not (row.get("bill_id") and plain_one_liner(row["bill_id"])):
            continue
        kept.append(row)
    return kept


def _record_vote(row: dict, roll_calls: dict, bills_by_id: dict) -> dict:
    """One member_votes row joined to its index entry (§4.3 m4). A Speaker-election row
    loses the candidate name here: a candidate-name position becomes 'Voted' (a real
    position such as 'Not Voting' stays), result 'Speaker elected'; the name
    returns only through /api/members/detail/{id}?show_party=true (§4.3 party reveal)."""
    key = rc_key_or_none(row.get("chamber"), row.get("congress"), row.get("session"), row.get("vote_number"))
    entry = roll_calls.get(key) if key else None
    parent = None
    parts = _bill_id_parts((entry or {}).get("parent"))
    if parts:
        parent_id = f"{parts[0]}-{parts[1]}-{parts[2]}"
        parent = {"bill_id": parent_id, "congress": parts[0], "bill_type": parts[1],
                  "bill_number": parts[2], "in_bills": parent_id in bills_by_id}
    vote = {
        "rc": key,
        "roll_call": entry,
        "chamber": "Senate" if str(row.get("chamber") or "").lower().startswith("senate") else "House",
        "vote": str(row.get("vote") or ""),
        "date": str(row.get("date") or ""),
        "result": str(row.get("result") or ""),
        "text": "" if row.get("bill_id") else str(row.get("one_liner") or row.get("bill_number") or "").strip(),
        "parent": parent,
    }
    if is_speaker_vote(row, entry):
        # Only a candidate name becomes 'Voted'; a real position ('Not Voting', 'Present')
        # stays as recorded. The result is the winner's name, so it is hidden either way.
        vote.update({"result": "Speaker elected", "text": ""})
        if vote["vote"] not in _KNOWN_POSITIONS:
            vote["vote"] = "Voted"
        if entry:
            vote["roll_call"] = {**entry, "result": "Speaker elected"}
    return vote


def group_record(votes: list[dict], roll_calls: dict, bills_by_id: dict, plain_one_liner) -> list[dict]:
    """The record as groups, newest first (§4.3 m4). `votes` are member_votes rows, newest first.

    - bill group (bill_id set): placed at its newest vote; `lead` = its latest class-D roll
      call, else its latest; `more` = the rest, newest first. `headline` = the displayable
      one-liner, else the bills.json official title, else the row's own string (never both).
    - other group (bill_id null): consecutive such votes on one calendar day share a row.
    - speaker group: one Speaker-election vote, candidate name removed."""
    groups: list[dict] = []
    bill_groups: dict[str, dict] = {}
    for row in votes:
        vote = _record_vote(row, roll_calls, bills_by_id)
        bill_id = row.get("bill_id")
        if bill_id:
            group = bill_groups.get(bill_id)
            if group is None:
                parts = _bill_id_parts(bill_id)
                one_liner = plain_one_liner(bill_id)
                title = (bills_by_id.get(bill_id) or {}).get("title")
                group = {
                    "kind": "bill",
                    "bill_id": bill_id,
                    "congress": parts[0] if parts else row.get("congress"),
                    "bill_type": parts[1] if parts else "",
                    "bill_number": parts[2] if parts else None,
                    "headline": one_liner or title or str(row.get("one_liner") or row.get("bill_number") or ""),
                    "displayable": bool(one_liner),
                    "policy_area": str(row.get("policy_area") or ""),
                    "_votes": [],
                }
                bill_groups[bill_id] = group
                groups.append(group)
            group["_votes"].append(vote)
        elif is_speaker_vote(row, roll_calls.get(vote["rc"]) if vote["rc"] else None):
            groups.append({"kind": "speaker", "vote": vote})
        else:
            day = vote["date"][:10]
            last = groups[-1] if groups else None
            if last is not None and last["kind"] == "other" and last["date"] == day:
                last["votes"].append(vote)
            else:
                groups.append({"kind": "other", "date": day, "votes": [vote]})
    for group in bill_groups.values():
        on_bill = group.pop("_votes")
        lead = next((v for v in on_bill if (v["roll_call"] or {}).get("class") == "D"), on_bill[0])
        group["lead"] = lead
        group["more"] = [v for v in on_bill if v is not lead]
    return groups


def _status_dict(value) -> dict:
    """render.bill_status() output as {"text", "variant"} — the shape every page renderer reads."""
    if isinstance(value, dict):
        text = str(value.get("text") or "")
        variant = value.get("variant")
    else:
        text, variant = str(value or ""), None
    if variant not in ("final", "moving"):
        variant = "final" if text == "Became law" or text.startswith("Adopted by the") else "moving"
    return {"text": text, "variant": variant}


class DataService:
    # The bill page (T1.8) and the sync's AI writer choose the same official summary.
    _latest_official_summary = staticmethod(_latest_official_summary)

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._members: list[dict] = []
        self._bills: list[dict] = []
        self._ai_summaries: dict[str, dict] = {}
        self._member_summaries: dict[str, dict] = {}
        self._donations: dict[str, dict] = {}
        self._metadata: dict = {}
        # (congress, bill_type, bill_number) -> {"senate": [...], "house": [...]},
        # built lazily on first get_bill_votes call (one scan of the vote dirs)
        self._bill_votes_index: dict[tuple[int, str, int], dict[str, list[dict]]] | None = None
        # The single most recent bill-linked vote, built lazily on first request.
        self._latest_vote_loaded = False
        self._latest_vote: dict | None = None
        # Sync-built roll-call index (§10 #3); {} when the file is absent.
        self._votes_index: dict = {}
        # Sanctioned data (§10 #1, #2): Senate seats up in 2026, and the ZIP crosswalk with
        # the district counts and member ids derived from it once at startup.
        self._senate_2026: dict[str, dict] = {}
        self._zip_districts: dict[str, list[dict]] = {}
        self._districts_expected: dict[str, int] = {}
        self._house_ids: dict[tuple[str, int], list[str]] = {}
        self._senator_ids: dict[str, list[str]] = {}
        # state_overview/{code}.json, read on first use and kept (§10 #7); None = file missing.
        self._state_overviews: dict[str, dict | None] = {}
        self._bills_by_id: dict[str, dict] | None = None  # bill_id -> bills.json row, built on first use
        self._load()

    def _load(self) -> None:
        self._members = self._read_json("members.json").get("members", [])
        self._bills = self._read_json("bills.json").get("bills", [])
        # Newest first so every consumer (homepage, browse, search) leads with
        # recent activity; bills without an action date sort last.
        self._bills.sort(
            key=lambda b: (b.get("latestAction") or {}).get("actionDate") or "",
            reverse=True,
        )
        if not self._members:
            logger.error("Loaded 0 members from %s — site will serve empty member data", self.data_dir / "members.json")
        if not self._bills:
            logger.error("Loaded 0 bills from %s — site will serve empty bill data", self.data_dir / "bills.json")
        self._ai_summaries = self._read_json("ai_summaries.json")
        self._member_summaries = self._read_json("member_summaries.json")
        self._donations = self._read_json("donations.json")
        # One read at startup replaces the per-request scans of votes/ (§9.6).
        self._votes_index = self._read_json("votes_index.json")
        if not self._votes_index:
            logger.warning("votes_index.json missing in %s — run: python sync.py --step votes-index", self.data_dir)
        metadata_path = self.data_dir / "sync_metadata.json"
        if metadata_path.exists():
            self._metadata = self._read_json("sync_metadata.json")
        seats = self._read_json("senate_2026.json").get("seats") or []
        self._senate_2026 = {s["bioguideId"]: s for s in seats if s.get("bioguideId")}
        # §5.1: keys starting with "_" (the _source block) are metadata, not ZCTAs.
        self._zip_districts = {
            key: rows for key, rows in self._read_json("zip_districts.json").items() if not key.startswith("_")
        }
        for rows in self._zip_districts.values():
            for row in rows:
                state, district = row.get("state"), row.get("district")
                if state and isinstance(district, int):
                    self._districts_expected[state] = max(self._districts_expected.get(state, 0), district)
        for m in self._members:
            state, bioguide = m.get("stateCode"), m.get("bioguideId")
            if not state or not bioguide:
                continue
            if "Senate" in (m.get("chamber") or ""):
                self._senator_ids.setdefault(state, []).append(bioguide)
            elif isinstance(m.get("district"), int):
                self._house_ids.setdefault((state, m["district"]), []).append(bioguide)
        for ids in (*self._senator_ids.values(), *self._house_ids.values()):
            ids.sort()

    def _read_json(self, filename: str) -> dict:
        path = self.data_dir / filename
        if not path.exists():
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def get_members_by_state(self, state_code: str) -> dict:
        state_code = state_code.upper()
        filtered = [m for m in self._members if m.get("stateCode") == state_code]
        return {"members": filtered}

    def get_members_by_district(self, state_code: str, district: int) -> dict:
        state_code = state_code.upper()
        filtered = [
            m for m in self._members
            if m.get("stateCode") == state_code and m.get("district") == district
        ]
        return {"members": filtered}

    def get_state_overview(self, code: str, fallback: bool = False) -> dict | None:
        """The precomputed delegation file (§10 #7): one read per state, then served from memory.

        Returns None when the file is missing (a warning is logged). With fallback=True, a missing
        file gives the members.json roster in the same shape with no latest votes (§4.2 states)."""
        code = str(code or "").upper()
        if not _STATE_CODE_RE.fullmatch(code):
            return None
        if code not in self._state_overviews:
            path = self.data_dir / "state_overview" / f"{code}.json"
            if path.exists():
                with open(path, "r") as f:
                    self._state_overviews[code] = json.load(f)
            else:
                self._state_overviews[code] = None
                logger.warning("state_overview/%s.json missing in %s — run: python sync.py --step state-overview",
                               code, self.data_dir)
        overview = self._state_overviews[code]
        if overview is None and fallback:
            members = self.get_members_by_state(code)["members"]
            expected = self.districts_expected(code) or max((m.get("district") or 0 for m in members), default=0)
            return {**state_overview_payload(code, members, {}, expected), "generated_at": None}
        return overview

    def get_member_detail(self, bioguide_id: str) -> dict | None:
        bioguide_id = bioguide_id.upper()
        for m in self._members:
            if m.get("bioguideId") == bioguide_id:
                return {"member": m}
        return None

    def get_member_votes(self, bioguide_id: str) -> dict | None:
        bioguide_id = bioguide_id.upper()
        path = self.data_dir / "member_votes" / f"{bioguide_id}.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)

        # Enrich each vote with simplified issue_categories from AI summaries
        categories_set: set[str] = set()
        for vote in data.get("votes", []):
            bill_id = vote.get("bill_id", "")
            summary = self._ai_summaries.get(bill_id, {})
            cats = summary.get("issue_categories", [])
            vote["issue_categories"] = cats
            categories_set.update(cats)

        data["categories"] = sorted(categories_set)
        return data

    def get_member_vote_summary(self, bioguide_id: str) -> dict | None:
        data = self.get_member_votes(bioguide_id)
        if not data:
            return None

        area_counts: dict[str, dict[str, int]] = {}
        for vote in data.get("votes", []):
            area = vote.get("policy_area") or ""
            if not area:
                continue
            if area not in area_counts:
                area_counts[area] = {"yea": 0, "nay": 0, "total": 0, "in_favor": 0, "against": 0, "neutral": 0}
            position = vote.get("vote", "").lower()
            direction = vote.get("direction")
            is_yea = position in ("yea", "aye")
            is_nay = position in ("nay", "no")
            if is_yea:
                area_counts[area]["yea"] += 1
            elif is_nay:
                area_counts[area]["nay"] += 1
            area_counts[area]["total"] += 1

            # Compute effective stance: Yea on "in_favor" or Nay on "against" = in_favor
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
            elif direction == "neutral" or direction is None:
                if is_yea or is_nay:
                    area_counts[area]["neutral"] += 1

        top_areas = sorted(area_counts.items(), key=lambda x: x[1]["total"], reverse=True)[:6]
        top_policy_areas = [
            {"name": name, "yea": counts["yea"], "nay": counts["nay"], "total": counts["total"],
             "in_favor": counts["in_favor"], "against": counts["against"], "neutral": counts["neutral"]}
            for name, counts in top_areas
        ]

        return {
            "member_id": data["member_id"],
            "stats": data["stats"],
            "top_policy_areas": top_policy_areas,
        }

    def get_member_narrative(self, bioguide_id: str) -> dict | None:
        bioguide_id = bioguide_id.upper()
        return self._member_summaries.get(bioguide_id)

    def get_bills_by_sponsor(self, bioguide_id: str) -> list[dict]:
        results = []
        for b in self._bills:
            for s in b.get("sponsors", []):
                if s.get("bioguideId") == bioguide_id:
                    results.append({
                        "congress": b.get("congress"),
                        "type": b.get("type", ""),
                        "number": b.get("number"),
                        "title": b.get("title", ""),
                        "introduced_date": b.get("introducedDate", ""),
                        "latest_action": b.get("latestAction", {}).get("text", ""),
                        "policy_area": b.get("policyArea", {}).get("name", "") if b.get("policyArea") else "",
                    })
                    break
        return results

    def get_bills(
        self,
        offset: int = 0,
        limit: int = 20,
        congress: int | None = None,
        summarized_only: bool = False,
    ) -> dict:
        bills = self._bills
        if congress is not None:
            bills = [b for b in bills if b.get("congress") == congress]
        if summarized_only:
            # Homepage "Record" leads with plain English, so skip bills the AI
            # hasn't summarized yet (mostly procedural resolutions).
            bills = [b for b in bills if self._bill_summary(b).get("one_liner")]
        paginated = [self._with_plain_summary(b) for b in bills[offset:offset + limit]]
        return {"bills": paginated}

    def _bill_summary(self, bill: dict) -> dict:
        key = f"{bill.get('congress')}-{bill.get('type', '').lower()}-{bill.get('number')}"
        return self.displayable_summary(key) or {}

    def _with_plain_summary(self, bill: dict) -> dict:
        """Attach the AI one-liner, provisions, and issue categories so lists can
        lead with plain English instead of the official title. Returns a shallow
        copy so the cached bill is never mutated."""
        summary = self._bill_summary(bill)
        return {
            **bill,
            "one_liner": summary.get("one_liner") or "",
            "provisions": summary.get("provisions") or [],
            "issue_categories": summary.get("issue_categories") or [],
        }

    def displayable_summary(self, bill_id: str) -> dict | None:
        """The AI summary a reader may see (§2.5 C): it exists and needs_review is not true.
        A withheld summary is treated exactly like a missing one on every surface."""
        summary = self._ai_summaries.get(str(bill_id or "").lower())
        if not summary or summary.get("needs_review"):
            return None
        return summary

    def seat_up_2026(self, member: dict) -> str | None:
        """§7.4: every House seat is on the Nov 3, 2026 ballot; a senator's seat is up only when
        senate_2026.json lists it ("regular" or "special"). Describes the seat, never the person."""
        if "Senate" not in (member.get("chamber") or ""):
            return "regular"
        seat = self._senate_2026.get(member.get("bioguideId") or "")
        return seat.get("kind") if seat else None

    def districts_expected(self, code: str) -> int:
        """House districts per state from the crosswalk (NY 26, FL 28, TX 38, CA 52); 0 if absent."""
        return self._districts_expected.get(str(code or "").upper(), 0)

    def lookup_zip(self, raw: str | None) -> dict | None:
        """ZIP → district(s) by the §5.1 rule. None when the input is not a ZIP.

        matches = districts with share >= 5 %; covered_share = the sum of every listed share.
        Precedence: none (no match) → partial (covered_share < 0.95) → single (one match)
        → split (2–4 matches)."""
        zip5 = normalize_zip(raw)
        if zip5 is None:
            return None
        rows = self._zip_districts.get(zip5) or []
        matches = [row for row in rows if (row.get("share") or 0) >= ZIP_MATCH_SHARE]
        if not matches:
            return {"zip": zip5, "kind": "none", "matches": []}
        covered = round(sum(row.get("share") or 0 for row in rows), 4)
        if covered < ZIP_COVERED_SHARE:
            kind = "partial"
        elif len(matches) == 1:
            kind = "single"
        else:
            kind = "split"
        return {"zip": zip5, "kind": kind, "covered_share": covered,
                "matches": [self._zip_match(row) for row in matches]}

    def _zip_match(self, row: dict) -> dict:
        state, district = row["state"], row["district"]
        return {
            "state": state,
            "state_name": COVERED_STATE_NAMES.get(state, state),
            "district": district,
            "share": row["share"],
            "member_ids": list(self._house_ids.get((state, district), [])),
            "senator_ids": list(self._senator_ids.get(state, [])),
        }

    def get_member_counts(self) -> dict:
        """Members actually synced per state — the honest count behind each state
        card and delegation heading (vacant/unsynced seats are not invented)."""
        counts: dict[str, int] = {}
        for m in self._members:
            code = m.get("stateCode")
            if code:
                counts[code] = counts.get(code, 0) + 1
        return counts

    def get_latest_vote(self) -> dict | None:
        """The most recent roll-call vote that maps to a bill we hold, preferring
        a final-passage vote over a procedural motion on the same day."""
        if not self._latest_vote_loaded:
            self._latest_vote = self._build_latest_vote()
            self._latest_vote_loaded = True
        return self._latest_vote

    def _build_latest_vote(self) -> dict | None:
        bill_index: dict[tuple, dict] = {}
        for b in self._bills:
            try:
                bill_index[(b.get("congress"), b.get("type", "").lower(), int(b.get("number")))] = b
            except (TypeError, ValueError):
                continue

        best_key = None
        best_payload = None
        for chamber in ("senate", "house"):
            vote_dir = self.data_dir / "votes" / chamber
            if not vote_dir.exists():
                continue
            for vote_file in vote_dir.glob("*.json"):
                with open(vote_file, "r") as f:
                    vote = json.load(f)
                parsed = self._parse_bill_document(vote.get("document", ""))
                if not parsed:
                    continue
                bill = bill_index.get((vote.get("congress"), parsed[0], parsed[1]))
                if not bill:
                    continue
                date = _parse_vote_date(vote.get("vote_date", ""))
                if not date:
                    continue
                result = (vote.get("result") or "").lower()
                question = (vote.get("question") or "").lower()
                decisive = "passage" in question or "bill passed" in result or "bill defeated" in result
                # Most recent calendar day wins; within that day a final-passage
                # vote beats a procedural motion; vote number breaks any last tie.
                sort_key = (date.date(), decisive, vote.get("vote_number") or 0)
                if best_key is None or sort_key > best_key:
                    best_key = sort_key
                    best_payload = {
                        "chamber": "Senate" if chamber == "senate" else "House",
                        "date": _clean_vote_date(vote.get("vote_date", "")),
                        "document": vote.get("document"),
                        "result": vote.get("result"),
                        "counts": vote.get("counts"),
                        "bill": {
                            "congress": bill.get("congress"),
                            "type": bill.get("type", "").lower(),
                            "number": int(bill.get("number")),
                            "title": bill.get("title", ""),
                        },
                    }
        return best_payload

    def get_bill_detail(self, congress: int, bill_type: str, bill_number: int) -> dict | None:
        bill_type = bill_type.upper()
        for b in self._bills:
            if (b.get("congress") == congress
                    and b.get("type", "").upper() == bill_type
                    and int(b.get("number", 0)) == bill_number):
                return {"bill": b, "subjects": b.get("subjects", {"legislativeSubjects": []})}
        return None

    def get_ai_summary(self, congress: int, bill_type: str, bill_number: int) -> dict | None:
        key = f"{congress}-{bill_type.lower()}-{bill_number}"
        return self._ai_summaries.get(key)

    def get_senate_vote(self, congress: int, session: int, vote_number: int) -> dict | None:
        filename = f"{congress}_{session}_{vote_number:05d}.json"
        path = self.data_dir / "votes" / "senate" / filename
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)

    def get_house_vote(self, congress: int, session: int, vote_number: int) -> dict | None:
        filename = f"{congress}_{session}_{vote_number:05d}.json"
        path = self.data_dir / "votes" / "house" / filename
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def _parse_bill_document(document: str) -> tuple[str, int] | None:
        """Parse a vote's document field into (normalized bill type, number).

        "H.R. 1" -> ("hr", 1), "S.J.Res. 10" -> ("sjres", 10). Returns None for
        non-bill documents (nominations like "PN807", amendment text, empty).
        """
        match = _BILL_DOCUMENT_RE.match(document.strip())
        if not match:
            return None
        bill_type = match.group(1).replace(".", "").replace(" ", "").lower()
        return bill_type, int(match.group(2))

    def _build_bill_votes_index(self) -> dict[tuple[int, str, int], dict[str, list[dict]]]:
        """Scan both vote directories once, mapping each bill to its vote summaries.

        Stores only summary fields (no per-member positions) — the bill page
        fetches full vote detail separately via the votes API.
        """
        index: dict[tuple[int, str, int], dict[str, list[dict]]] = {}
        for chamber in ("senate", "house"):
            vote_dir = self.data_dir / "votes" / chamber
            if not vote_dir.exists():
                continue
            # Sorted so votes list in filename (chronological) order
            for vote_file in sorted(vote_dir.glob("*.json")):
                with open(vote_file, "r") as f:
                    vote = json.load(f)
                parsed = self._parse_bill_document(vote.get("document", ""))
                if not parsed:
                    continue
                bill_type, bill_number = parsed
                key = (vote.get("congress"), bill_type, bill_number)
                entry = index.setdefault(key, {"senate": [], "house": []})
                entry[chamber].append({
                    "congress": vote.get("congress"),
                    "session": vote.get("session"),
                    "vote_number": vote.get("vote_number"),
                    "vote_date": vote.get("vote_date"),
                    "question": vote.get("question"),
                    "result": vote.get("result"),
                    "counts": vote.get("counts"),
                })
        return index

    def get_bill_votes(self, congress: int, bill_type: str, bill_number: int) -> dict | None:
        if self._bill_votes_index is None:
            self._bill_votes_index = self._build_bill_votes_index()
        entry = self._bill_votes_index.get((congress, bill_type.lower(), bill_number))
        if not entry:
            return None
        return {"senate": entry["senate"], "house": entry["house"]}

    def get_member_donations(self, bioguide_id: str) -> dict | None:
        bioguide_id = bioguide_id.upper()
        return self._donations.get(bioguide_id)

    def get_sync_metadata(self) -> dict:
        return self._metadata

    # ---- Member page payload (plan T1.7) ----

    def _index_roll_calls(self) -> dict:
        return (self._votes_index or {}).get("roll_calls") or {}

    def _index_bill_keys(self, bill_id: str) -> list[str]:
        """Roll-call keys for one bill, newest first (votes_index.json `bills`)."""
        entry = ((self._votes_index or {}).get("bills") or {}).get(bill_id)
        keys = entry.get("roll_calls") if isinstance(entry, dict) else entry
        return [key for key in (keys or []) if isinstance(key, str)]

    def _bill_lookup(self) -> dict[str, dict]:
        if self._bills_by_id is None:
            self._bills_by_id = {
                f"{b.get('congress')}-{str(b.get('type') or '').lower()}-{b.get('number')}": b
                for b in self._bills
            }
        return self._bills_by_id

    def _plain_one_liner(self, bill_id) -> str | None:
        """The AI one-liner only when the summary is displayable (exists, not needs_review)."""
        if not bill_id or not self.displayable_summary(bill_id):
            return None
        return (self._ai_summaries.get(bill_id) or {}).get("one_liner") or None

    def _bill_status_for(self, bill: dict, bill_id: str) -> dict:
        """§7.2 bill status seal from `laws` and the newest class-D roll call per chamber.
        The one bill-status path: the member page (sponsored rows), the bill page and
        T1.9's /api/bills `derived_status` all call this. An impeachment verdict is class D
        but never a bill seal, so it is skipped and an older decisive vote can stand."""
        latest_decisive: dict[str, dict | None] = {"house": None, "senate": None}
        roll_calls = self._index_roll_calls()
        for key in self._index_bill_keys(bill_id):
            chamber = key.split("/", 1)[0]
            entry = roll_calls.get(key)
            if (entry and entry.get("class") == "D" and latest_decisive.get(chamber, 0) is None
                    and "Guilty or Not Guilty" not in str(entry.get("question") or "")):
                latest_decisive[chamber] = entry
        laws = bill.get("laws") or []
        bill_type = str(bill.get("type") or "").lower()
        return _status_dict(render.bill_status(laws, latest_decisive, bill_type))

    def _nominations_since(self, first_day: str) -> int:
        """Senate roll calls on nominations (PN documents) on or after `first_day` (§4.3 m4)."""
        count = 0
        for key, entry in self._index_roll_calls().items():
            if not key.startswith("senate/"):
                continue
            document = str(entry.get("document") or "").strip()
            if (document.startswith("PN") or document.startswith("P.N.")) and str(entry.get("date") or "")[:10] >= first_day:
                count += 1
        return count

    def _complete_donation(self, bioguide_id: str) -> dict | None:
        """§4.3 m7: only when the four totals and fec_candidate_id exist; top donors never leave."""
        entry = self.get_member_donations(bioguide_id)
        if not isinstance(entry, dict):
            return None
        totals = entry.get("totals") or {}
        if not entry.get("fec_candidate_id") or any(totals.get(k) is None for k in _MONEY_TOTAL_KEYS):
            return None
        return {
            "fec_candidate_id": entry["fec_candidate_id"],
            "cycle": entry.get("cycle"),
            "last_updated": entry.get("last_updated"),
            "totals": {k: totals[k] for k in _MONEY_TOTAL_KEYS},
        }

    def _sponsored_row(self, row: dict) -> dict:
        """One get_bills_by_sponsor row for the page (§4.3 m5): no raw latest_action string."""
        bill_id = f"{row.get('congress')}-{str(row.get('type') or '').lower()}-{row.get('number')}"
        bill = self._bill_lookup().get(bill_id) or {}
        return {
            "congress": row.get("congress"),
            "type": row.get("type"),
            "number": row.get("number"),
            "title": row.get("title") or "",
            "introduced_date": row.get("introduced_date") or "",
            "policy_area": row.get("policy_area") or "",
            "one_liner": self._plain_one_liner(bill_id),
            "status": self._bill_status_for(bill, bill_id),
        }

    def filter_member_votes(self, votes: list[dict], topic, position, plain) -> list[dict]:
        return filter_record_votes(votes, topic, position, plain, self._plain_one_liner)

    def _record_from_votes(self, votes: list[dict], policy_areas, topic, position, plain) -> dict:
        topic = str(topic or "").strip() or None
        position = position if position in ("yes", "no", "nv") else None
        plain = bool(plain)
        bills = self._bill_lookup()
        chosen = filter_record_votes(votes, topic, position, plain, self._plain_one_liner)
        groups = group_record(chosen, self._index_roll_calls(), bills, self._plain_one_liner)
        bill_ids = {row["bill_id"] for row in votes if row.get("bill_id")}
        return {
            "groups": groups,
            "total_groups": len(groups),
            "matching_bills": sum(1 for group in groups if group["kind"] == "bill"),
            "topic": topic,
            "position": position,
            "plain": plain,
            "policy_areas": list(policy_areas or []),
            "plain_bills": sum(1 for bill_id in bill_ids if self._plain_one_liner(bill_id)),
            "total_bills": len(bill_ids),
        }

    def get_member_record(self, bioguide_id: str, topic: str | None = None, position: str | None = None,
                          plain: bool = False, congress: int | None = None) -> dict | None:
        """The whole grouped record (all pages); None when there is no member_votes file."""
        data = self.get_member_votes(bioguide_id)
        if not data:
            return None
        votes = _newest_first(data.get("votes") or [])
        if congress is not None:
            votes = [v for v in votes if v.get("congress") == congress]
        return self._record_from_votes(votes, data.get("policy_areas"), topic, position, plain)

    def get_member_page(self, bioguide_id: str, page: int = 1, topic: str | None = None,
                        position: str | None = None, plain: bool = False) -> dict | None:
        """Everything the member page renders (§4.3, §10 #8), party-free: header facts,
        Recent votes, one page of the grouped record, sponsored bills and campaign money.
        Reads startup data plus this member's one member_votes file. None for unknown ids."""
        detail = self.get_member_detail(bioguide_id)
        if not detail:
            return None
        raw_member = detail["member"]
        member_id = raw_member.get("bioguideId", "")
        sponsored = sorted(self.get_bills_by_sponsor(member_id),
                           key=lambda b: b.get("introduced_date") or "", reverse=True)
        result = {
            "member": {k: v for k, v in raw_member.items() if k not in _PARTY_KEYS},
            "seat": self.seat_up_2026(raw_member),
            "has_record": False,
            "stats": None,
            "other_count": None,
            "first_vote_date": None,
            "last_vote_date": None,
            "nominations_count": None,
            "recent_votes": [],
            "record": None,
            "sponsored": [self._sponsored_row(row) for row in sponsored[:SPONSORED_LIMIT]],
            "sponsored_count": len(sponsored),
            "donation": self._complete_donation(member_id),
        }
        data = self.get_member_votes(member_id)
        if not data:
            return result
        votes = _newest_first(data.get("votes") or [])
        raw_stats = data.get("stats") or {}
        stats = {k: _as_int(raw_stats.get(k)) for k in ("total_votes", "yea_count", "nay_count", "not_voting_count")}
        dates = [str(v.get("date")) for v in votes if v.get("date")]
        first = min(dates) if dates else None
        record = self._record_from_votes(votes, data.get("policy_areas"), topic, position, plain)
        pages = max(1, -(-record["total_groups"] // RECORD_PER_PAGE))
        page_no = min(max(1, _as_int(page) or 1), pages)
        start = (page_no - 1) * RECORD_PER_PAGE
        record["groups"] = record["groups"][start:start + RECORD_PER_PAGE]
        record.update({"page": page_no, "pages": pages, "per_page": RECORD_PER_PAGE})
        result.update({
            "has_record": True,
            "stats": stats,
            "other_count": stats["total_votes"] - stats["yea_count"] - stats["nay_count"] - stats["not_voting_count"],
            "first_vote_date": first,
            "last_vote_date": max(dates) if dates else None,
            "nominations_count": (self._nominations_since(first[:10])
                                  if raw_member.get("chamber") == "Senate" and first else None),
            "recent_votes": pick_recent_votes(votes, self._index_roll_calls(), self._plain_one_liner),
            "record": record,
        })
        return result

    def get_speaker_votes(self, bioguide_id: str) -> dict[str, str]:
        """Roll-call key -> this member's Speaker-election pick. Served only with the party
        reveal (/api/members/detail/{id}?show_party=true): a vote for a party's nominee is a party cue."""
        data = self.get_member_votes(bioguide_id)
        if not data:
            return {}
        roll_calls = self._index_roll_calls()
        picks: dict[str, str] = {}
        for row in data.get("votes") or []:
            key = rc_key_or_none(row.get("chamber"), row.get("congress"), row.get("session"), row.get("vote_number"))
            pick = str(row.get("vote") or "")
            if key and pick not in _KNOWN_POSITIONS and is_speaker_vote(row, roll_calls.get(key)):
                picks[key] = pick
        return picks
