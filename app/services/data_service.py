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


# ---------------------------------------------------------------------------
# Bill page payload (plan T1.8; spec §4.4, §7.2, §7.3, §10 #10).
# ---------------------------------------------------------------------------

CURRENT_CONGRESS = 119
COVERED_STATES = ("CA", "FL", "NY", "TX")
_RC_KEY_RE = re.compile(r"^(house|senate)/(\d{1,3})_(\d)_(\d{1,5})$")
_FULLNAME_PARTY_RE = re.compile(r"\s*\[[^\]]*\]\s*$")
_PARAGRAPHS_RE = re.compile(r"<p\b[^>]*>(.*?)</p\s*>", re.IGNORECASE | re.DOTALL)
_TITLE_ONLY_RE = re.compile(r"^\s*<(strong|b)\b[^>]*>.*</\1\s*>\s*$", re.IGNORECASE | re.DOTALL)


def relation_text(position, chamber_word: str) -> str:
    """§4.4 m2: a covered member's relation to one roll call, as chip text. `position` is
    the row's vote, or None when the member is not in the roll call at all."""
    if position is None:
        return f"Not in the {chamber_word} for this vote"
    position = str(position)
    if position in _YES_VOTES:
        return "Voted yes"
    if position in _NO_VOTES:
        return "Voted no"
    if position == "Not Voting":
        return "Didn't vote"
    if position in ("Present", "Present, Giving Live Pair"):
        return "Present"
    if position in ("Guilty", "Not Guilty"):
        return position
    return "Voted"


def first_paragraph_text(html_text) -> str:
    """The first <p> of substance of an official summary as plain text (§4.4 m4): no markup,
    no href, entities decoded, whitespace collapsed. A leading paragraph that is only a bold
    element, or at most 12 words with no terminal period, is the bill's short title and is
    skipped (116 of the 159 unsummarized bills with an official summary open that way).
    Falls back to the first paragraph, then to the whole input when it has no <p>."""
    text = str(html_text or "")
    chunks = _PARAGRAPHS_RE.findall(text)
    plain = [" ".join(render.strip_tags(chunk).split()) for chunk in chunks]
    for chunk, words in zip(chunks, plain):
        if not words:
            continue
        if _TITLE_ONLY_RE.match(chunk):
            continue
        if len(words.split()) <= 12 and not words.endswith((".", ":", ";")):
            continue
        return words
    if plain:
        return next((p for p in plain if p), "")
    return " ".join(render.strip_tags(text).split())


def _seal_text(entry: dict | None, chamber_word: str) -> str | None:
    """§7.2 seal text for one votes_index entry ('Passed the House 237–169')."""
    return render.result_phrase(entry, chamber_word) if entry else None


def _outcome_text(entry: dict | None, chamber_word: str) -> str | None:
    """§7.3 outcome sentence for one votes_index entry."""
    return render.outcome_sentence(entry, chamber_word) if entry else None


def _sponsor_without_party(sponsor: dict) -> dict:
    """sponsors[0] without party keys; fullName loses its '[R-AL-6]' suffix (§4.4 m6, §10 #9)."""
    clean = {k: sponsor.get(k) for k in ("bioguideId", "firstName", "lastName", "state", "district")
             if sponsor.get(k) is not None}
    clean["fullName"] = _FULLNAME_PARTY_RE.sub("", str(sponsor.get("fullName") or "")).strip()
    return clean


def _pick_rendered(roll_calls: list[dict]) -> list[dict]:
    """§4.4 m3: the roll calls the bill page renders — the head (newest decisive, else the
    newest) and the other chamber's newest decisive one, else that chamber's newest roll call
    (so a bill voted in both chambers always shows both; G7's slot relies on it); at most two.
    `roll_calls` are _roll_call_view() dicts, newest first; the same dict objects come back."""
    if not roll_calls:
        return []
    head = next((rc for rc in roll_calls if rc["class"] == "D"), roll_calls[0])
    other = next((rc for rc in roll_calls if rc["class"] == "D" and rc["chamber"] != head["chamber"]), None) \
        or next((rc for rc in roll_calls if rc["chamber"] != head["chamber"]), None)
    return [head, other] if other else [head]


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
        # Built from the votes index at startup by _index_bills() (spec §10 #11). The bill map
        # is T1.7's lazy _bill_lookup(); the bill -> roll-call keys are T1.7's _index_bill_keys().
        self._activity_dates: dict[str, str] = {}
        self._derived_statuses: dict[str, object] = {}
        # The hero payload: built on first request (one roll-call file read), then cached.
        self._latest_vote_built = False
        self._latest_vote_cache: dict | None = None
        # Sync-built roll-call index (§10 #3); {} when the file is absent.
        self._votes_index: dict = {}
        # Sanctioned data (§10 #1, #2): Senate seats up in 2026, and the ZIP crosswalk with
        # the district counts and member ids derived from it once at startup.
        self._senate_2026: dict[str, dict] = {}
        # /methodology prints the sources of the two sanctioned files (§4.6); both are kept
        # from the startup load so the request path never reads a file (§9.1).
        self._senate_file: dict = {}
        self._crosswalk_source: dict = {}
        self._zip_districts: dict[str, list[dict]] = {}
        self._districts_expected: dict[str, int] = {}
        self._house_ids: dict[tuple[str, int], list[str]] = {}
        self._senator_ids: dict[str, list[str]] = {}
        # state_overview/{code}.json, read on first use and kept (§10 #7); None = file missing.
        self._state_overviews: dict[str, dict | None] = {}
        self._bills_by_id: dict[str, dict] | None = None  # bill_id -> bills.json row, built on first use
        self._members_by_id: dict[str, dict] | None = None  # bioguideId -> members.json row, built on first use
        self._audit_grades: dict = {}
        # Coverage numbers for /api/health, /about and /methodology; computed once.
        self._coverage: dict | None = None
        self._earliest_rc: tuple[str | None] | None = None  # (date,) once computed; the index never changes after startup
        self._newest_rc: tuple[str | None] | None = None  # (date,) once computed, as _earliest_rc
        self._load()

    def _load(self) -> None:
        self._members = self._read_json("members.json").get("members", [])
        self._bills = self._read_json("bills.json").get("bills", [])
        if not self._members:
            logger.error("Loaded 0 members from %s — site will serve empty member data", self.data_dir / "members.json")
        if not self._bills:
            logger.error("Loaded 0 bills from %s — site will serve empty bill data", self.data_dir / "bills.json")
        self._ai_summaries = self._read_json("ai_summaries.json")
        self._member_summaries = self._read_optional_json("member_summaries.json")
        self._donations = self._read_optional_json("donations.json")
        self._audit_grades = self._read_optional_json("audit_grades.json")
        # One read at startup replaces the per-request scans of votes/ (§9.6).
        self._votes_index = self._read_json("votes_index.json")
        self._index_bills()
        if not self._votes_index:
            logger.warning("votes_index.json missing in %s — run: python sync.py --step votes-index", self.data_dir)
        self._metadata = self._read_optional_json("sync_metadata.json")
        self._senate_file = self._read_optional_json("senate_2026.json")
        try:
            seats = self._senate_file.get("seats") or []
            self._senate_2026 = {s["bioguideId"]: s for s in seats if s.get("bioguideId")}
        except (AttributeError, TypeError) as exc:
            logger.error("senate_2026.json seats are malformed — serving without them: %s", exc)
            self._senate_file, self._senate_2026 = {}, {}
        # §5.1: keys starting with "_" (the _source block) are metadata, not ZCTAs.
        crosswalk = self._read_optional_json("zip_districts.json")
        try:
            self._crosswalk_source = crosswalk.get("_source") or {}
            self._zip_districts = {key: rows for key, rows in crosswalk.items() if not key.startswith("_")}
            for rows in self._zip_districts.values():
                for row in rows:
                    state, district = row.get("state"), row.get("district")
                    if state and isinstance(district, int):
                        self._districts_expected[state] = max(self._districts_expected.get(state, 0), district)
        except (AttributeError, TypeError) as exc:
            logger.error("zip_districts.json rows are malformed — serving without the ZIP lookup: %s", exc)
            self._crosswalk_source, self._zip_districts, self._districts_expected = {}, {}, {}
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

    def _read_optional_json(self, filename: str) -> dict:
        """A file the site can serve without (F030). When it is malformed or not a JSON object,
        log an error and load {}, so one bad file drops its own feature instead of failing the
        whole load. members.json, bills.json, ai_summaries.json and votes_index.json go through
        _read_json and still fail it, which fails startup and keeps the previous deploy live."""
        try:
            data = self._read_json(filename)
        except (OSError, ValueError) as exc:
            logger.error("Could not load %s — serving without it: %s", self.data_dir / filename, exc)
            return {}
        if not isinstance(data, dict):
            logger.error("%s holds a JSON %s, not an object — serving without it",
                         self.data_dir / filename, type(data).__name__)
            return {}
        return data

    def get_members_by_state(self, state_code: str) -> dict:
        state_code = state_code.upper()
        filtered = [m for m in self._members if m.get("stateCode") == state_code]
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
            return json.load(f)

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
        """Bills newest activity first (spec §4.1 m5): activity date = max(latestAction,
        newest roll call), so a bill voted on last week leads even when its latestAction
        is older. one_liner is None unless the summary is displayable (§2.5 C);
        summarized_only keeps only bills with a displayable one-liner."""
        bills = self._bills
        if congress is not None:
            bills = [b for b in bills if b.get("congress") == congress]
        if summarized_only:
            bills = [b for b in bills if self._display_summary(b).get("one_liner")]
        return {"bills": [self._with_plain_summary(b) for b in bills[offset:offset + limit]]}

    @staticmethod
    def _bill_id_of(bill: dict) -> str:
        return f"{bill.get('congress')}-{str(bill.get('type', '')).lower()}-{bill.get('number')}"

    def _display_summary(self, bill: dict) -> dict:
        """The bill's AI summary when displayable (exists, not needs_review), else {}."""
        bill_id = self._bill_id_of(bill)
        return self._ai_summaries.get(bill_id, {}) if self.displayable_summary(bill_id) else {}

    def _with_plain_summary(self, bill: dict) -> dict:
        """A shallow copy of the bill with the displayable AI fields, its activity date
        and its derived status seal. Withheld and missing summaries look the same."""
        bill_id = self._bill_id_of(bill)
        summary = self._display_summary(bill)
        return {
            **bill,
            "one_liner": summary.get("one_liner") or None,
            "provisions": summary.get("provisions") or [],
            "issue_categories": summary.get("issue_categories") or [],
            "activity_date": self._activity_dates.get(bill_id) or None,
            "derived_status": self._derived_statuses.get(bill_id),
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

    # --- Votes index reads (spec §10 #3, #11): dict lookups, no directory scans ---

    @staticmethod
    def _split_rc_key(key: str) -> tuple[str, int, int, int] | None:
        """'house/119_2_00295' -> ('house', 119, 2, 295); None when malformed."""
        try:
            chamber, name = key.split("/", 1)
            congress, session, number = (int(part) for part in name.split("_"))
        except (AttributeError, ValueError):
            return None
        if chamber not in ("house", "senate"):
            return None
        return chamber, congress, session, number

    def _index_bills(self) -> None:
        """One startup pass: each bill's activity date (the index `bills[id].activity_date`,
        which T1.4 computed as max(latestAction, newest roll call); latestAction alone when
        the index does not list the bill) and its status seal (T1.7's _bill_status_for, the
        one status path). Then bills are sorted newest activity first. Dict work only;
        no roll-call file is opened."""
        index_bills = (self._votes_index or {}).get("bills") or {}
        self._activity_dates, self._derived_statuses = {}, {}
        for bill in self._bills:
            bill_id = self._bill_id_of(bill)
            entry = index_bills.get(bill_id)
            indexed = str(entry.get("activity_date") or "")[:10] if isinstance(entry, dict) else ""
            action = str((bill.get("latestAction") or {}).get("actionDate") or "")[:10]
            self._activity_dates[bill_id] = max(indexed, action)
            self._derived_statuses[bill_id] = self._bill_status_for(bill, bill_id)
        # Stable sort: bills with no date at all keep their file order at the end.
        self._bills.sort(key=lambda b: self._activity_dates[self._bill_id_of(b)], reverse=True)

    def get_latest_vote(self) -> dict | None:
        """The Latest Vote hero (spec §4.1 m3, F02). It is the index's `latest` key: the newest
        roll call on a bill we hold, with decisive votes first within a day. A newer
        unsummarized vote is shown, never skipped. Built once, with one roll-call file
        read for `covered`, then cached."""
        if not self._latest_vote_built:
            self._latest_vote_cache = self._build_latest_vote_from_index()
            self._latest_vote_built = True
        return self._latest_vote_cache

    def _build_latest_vote_from_index(self) -> dict | None:
        key = (self._votes_index or {}).get("latest")
        rc = self._index_roll_calls().get(key) if key else None
        parts = self._split_rc_key(key) if rc else None
        parsed = self._parse_bill_document(rc.get("document") or "") if parts else None
        if not parsed:
            return None
        chamber_dir, congress, session, number = parts
        bill_id = f"{congress}-{parsed[0]}-{parsed[1]}"
        bill = self._bill_lookup().get(bill_id)
        if bill is None:
            return None
        chamber = "Senate" if chamber_dir == "senate" else "House"
        one_liner = self._display_summary(bill).get("one_liner") or None
        seal = render.result_phrase(rc, chamber)
        date_iso = str(rc.get("date") or "")[:10]
        return {
            "rc": key,
            "chamber": chamber,
            # `date` stays a display string until T3.3 rewrites app.js, which prints it raw
            # (a Senate hero already read "August 8, 2026"); new readers use `date_iso`.
            "date": render.format_date(date_iso),
            "date_iso": date_iso,
            "document": rc.get("document"),
            "plain_question": rc.get("plain") or render.plain_question(rc.get("question") or ""),
            "result": rc.get("result"),
            "counts": rc.get("counts"),
            # On this endpoint `outcome` is the §7.2 seal (G3 reads it); `seal` names it the
            # way the bill page's roll calls do, where `outcome` is the §7.3 sentence instead.
            "seal": seal,
            "outcome": seal,
            "state_tallies": rc.get("tallies") or {},
            "bill": {
                "congress": bill.get("congress"),
                "type": parsed[0],
                "number": parsed[1],
                "title": bill.get("title", ""),
            },
            "one_liner": one_liner,
            "has_summary": one_liner is not None,
            # T1.8's one covered builder: every covered member of that chamber; a member
            # missing from the roll call reads position None, "Not in the {chamber} for this vote".
            "covered": self.covered_positions(
                chamber_dir, self._read_roll_call(chamber_dir, congress, session, number)),
        }

    def get_bill_detail(self, congress: int, bill_type: str, bill_number: int) -> dict | None:
        bill_type = bill_type.upper()
        for b in self._bills:
            if (b.get("congress") == congress
                    and b.get("type", "").upper() == bill_type
                    and int(b.get("number", 0)) == bill_number):
                return {"bill": b, "subjects": b.get("subjects", {"legislativeSubjects": []})}
        return None

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

    def get_member_donations(self, bioguide_id: str) -> dict | None:
        bioguide_id = bioguide_id.upper()
        return self._donations.get(bioguide_id)

    def get_sync_metadata(self) -> dict:
        return self._metadata

    def coverage_counts(self) -> dict:
        """The §4.6 coverage numbers, counted from the loaded data (never hard-coded).
        - shown: the summary exists and needs_review is not true (displayable_summary).
        - withheld: a summary exists but is flagged needs_review.
        - missing: no summary. shown + withheld + missing == bills.
        - audited: bills with an entry in audit_grades.json.
        - nominations_excluded: Senate roll calls on a nomination (document PN… / P.N.…),
          the ones build_member_votes leaves out of member records."""
        if self._coverage is None:
            bill_ids = [self._bill_id_of(b) for b in self._bills]
            shown = sum(1 for bill_id in bill_ids if self.displayable_summary(bill_id))
            withheld = sum(1 for bill_id in bill_ids
                           if bill_id in self._ai_summaries and not self.displayable_summary(bill_id))
            nominations = sum(
                1 for key, rc in self._index_roll_calls().items()
                if key.startswith("senate/")
                and str(rc.get("document") or "").strip().startswith(("PN", "P.N."))
            )
            self._coverage = {
                "bills": len(bill_ids),
                "shown": shown,
                "missing": len(bill_ids) - shown - withheld,
                "withheld": withheld,
                "audited": sum(1 for bill_id in bill_ids if bill_id in self._audit_grades),
                "nominations_excluded": nominations,
            }
        return dict(self._coverage)

    def latest_roll_call_date(self) -> str | None:
        """The newest roll-call date in the index (ISO), for the edition line on every page and
        health. Computed once, then served from memory (§9.1 request path), as the earliest."""
        if self._newest_rc is None:
            dates = (str(rc.get("date") or "")[:10] for rc in self._index_roll_calls().values())
            self._newest_rc = (max((d for d in dates if d), default=None),)
        return self._newest_rc[0]

    def earliest_roll_call_date(self) -> str | None:
        """The oldest roll-call date in the index (ISO): the "since January 2021" of the home
        coverage sentence and the Record stamp (spec §4.1). Computed once, then served from
        memory (§9.1 request path); None without the index."""
        if self._earliest_rc is None:
            dates = (str(rc.get("date") or "")[:10] for rc in self._index_roll_calls().values())
            self._earliest_rc = (min((d for d in dates if d), default=None),)
        return self._earliest_rc[0]

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

    # ---- Bill page payload (plan T1.8) ----

    def _member_lookup(self) -> dict[str, dict]:
        if self._members_by_id is None:
            self._members_by_id = {m["bioguideId"]: m for m in self._members if m.get("bioguideId")}
        return self._members_by_id

    def _senate_name_index(self) -> dict[tuple[str, str], str]:
        """(last name lower-cased, state) -> bioguideId for covered senators. Senate roll calls
        carry names, not ids, so this is the match sync.py build_member_votes uses."""
        return {
            (str(m.get("name") or "").split(",")[0].strip().lower(), str(m.get("stateCode") or "").upper()):
                m["bioguideId"]
            for m in self._members if m.get("chamber") == "Senate" and m.get("bioguideId")
        }

    def _row_covered_id(self, row: dict, senate: bool, senate_names: dict) -> str | None:
        if senate:
            key = (str(row.get("last_name") or "").strip().lower(), str(row.get("state") or "").upper())
            return senate_names.get(key)
        bioguide = str(row.get("bioguide_id") or "")
        return bioguide if bioguide in self._member_lookup() else None

    def covered_positions(self, chamber: str, roll_call: dict | None) -> dict[str, dict]:
        """Every covered member of this chamber and their relation to one roll-call file
        (§4.4 m2): House rows by bioguide_id, Senate rows by last name + state."""
        senate = str(chamber or "").lower().startswith("senate")
        word = "Senate" if senate else "House"
        positions: dict[str, str] = {}
        if roll_call:
            names = self._senate_name_index() if senate else {}
            for row in roll_call.get("members") or []:
                bioguide = self._row_covered_id(row, senate, names)
                if bioguide and bioguide not in positions:
                    positions[bioguide] = str(row.get("vote") or "")
        covered: dict[str, dict] = {}
        for member in self._members:
            bioguide = member.get("bioguideId")
            # members.json says "House of Representatives"; older fixture rows say "House".
            chamber_name = str(member.get("chamber") or "")
            in_chamber = chamber_name == "Senate" if senate else chamber_name.startswith("House")
            if not bioguide or not in_chamber:
                continue
            position = positions.get(bioguide)
            covered[bioguide] = {
                "name": render.display_name(member.get("name") or ""),
                "state": member.get("stateCode"),
                "district": None if senate else member.get("district"),
                "chamber": word,
                "position": position,
                "relation": relation_text(position, word),
            }
        return covered

    def _covered_state_rows(self, roll_call: dict, senate: bool, congress: int) -> list[dict]:
        """The CA/FL/NY/TX rows of one roll-call file, party removed (§4.4 m3). District only
        for covered House rows in the current Congress (earlier maps differ)."""
        names = self._senate_name_index() if senate else {}
        members = self._member_lookup()
        rows = []
        for row in roll_call.get("members") or []:
            state = str(row.get("state") or "").upper()
            if state not in COVERED_STATES:
                continue
            covered_id = self._row_covered_id(row, senate, names)
            district = None
            if not senate and covered_id and congress == CURRENT_CONGRESS:
                district = (members.get(covered_id) or {}).get("district")
            rows.append({
                "first_name": row.get("first_name") or "",
                "last_name": row.get("last_name") or "",
                "state": state,
                "vote": row.get("vote") or "",
                "bioguide_id": None if senate else (row.get("bioguide_id") or None),
                "covered_id": covered_id,
                "district": district,
            })
        return rows

    def _roll_call_view(self, key: str) -> dict | None:
        """One roll call for the bill page, from the index only (no file read)."""
        entry = self._index_roll_calls().get(key)
        match = _RC_KEY_RE.match(key)
        if not entry or not match:
            return None
        chamber = match.group(1)
        word = "Senate" if chamber == "senate" else "House"
        return {
            "key": key,
            "chamber": chamber,
            "congress": int(match.group(2)),
            "session": int(match.group(3)),
            "vote_number": int(match.group(4)),
            "date": str(entry.get("date") or "")[:10],
            "question": entry.get("question") or "",
            "plain": entry.get("plain") or render.plain_question(entry.get("question") or ""),
            "class": entry.get("class") or "P",
            "result": entry.get("result") or "",
            "counts": entry.get("counts") or {},
            "threshold": entry.get("threshold"),
            "document": entry.get("document") or "",
            "seal": _seal_text(entry, word),
            "outcome": _outcome_text(entry, word),
            "state_tallies": entry.get("tallies") or {},
            "rendered": False,
            "members": [],
            "covered": {},
        }

    def _read_roll_call(self, chamber: str, congress, session, vote_number) -> dict | None:
        try:
            congress, session, vote_number = int(congress), int(session), int(vote_number)
        except (TypeError, ValueError):
            return None
        if str(chamber or "").lower().startswith("senate"):
            return self.get_senate_vote(congress, session, vote_number)
        return self.get_house_vote(congress, session, vote_number)

    def official_summary_for(self, bill: dict) -> str | None:
        """The official summary the site shows (§4.4 m4-m5): Public Law first, else newest."""
        return self._latest_official_summary(bill) or None

    def get_bill_page(self, congress: int, bill_type: str, number: int) -> dict | None:
        """Everything the bill page renders (§4.4, §10 #10), from startup data plus at most
        two roll-call files: the head (newest decisive, else newest) and the other chamber's
        newest decisive roll call, else its newest roll call. None for an unknown bill."""
        bill_type = str(bill_type or "").lower()
        try:
            congress, number = int(congress), int(number)
        except (TypeError, ValueError):
            return None
        detail = self.get_bill_detail(congress, bill_type, number)
        if not detail:
            return None
        bill = detail["bill"]
        bill_id = f"{congress}-{bill_type}-{number}"
        has_summary = bool(self.displayable_summary(bill_id))
        summary = (self._ai_summaries.get(bill_id) or {}) if has_summary else {}
        official = self.official_summary_for(bill)
        roll_calls = [view for view in (self._roll_call_view(key) for key in self._index_bill_keys(bill_id)) if view]
        to_render = _pick_rendered(roll_calls)
        head = to_render[0] if to_render else None
        for rc in to_render:
            raw = self._read_roll_call(rc["chamber"], rc["congress"], rc["session"], rc["vote_number"])
            if raw is None:
                continue
            rc["rendered"] = True
            rc["members"] = self._covered_state_rows(raw, rc["chamber"] == "senate", rc["congress"])
            rc["covered"] = self.covered_positions(rc["chamber"], raw)
        sponsors = bill.get("sponsors") or []
        sponsor = _sponsor_without_party(sponsors[0]) if sponsors else None
        return {
            "bill_id": bill_id,
            "congress": congress,
            "bill_type": bill_type,
            "number": number,
            "title": bill.get("title") or "",
            "has_summary": has_summary,
            "one_liner": (summary.get("one_liner") or None) if has_summary else None,
            "provisions": list(summary.get("provisions") or []) if has_summary else [],
            "official_summary": official,
            "official_first_paragraph": first_paragraph_text(official) if official else None,
            "status": self._bill_status_for(bill, bill_id),
            "head": head,
            "roll_calls": roll_calls,
            "sponsor": sponsor,
            "sponsor_covered": bool(sponsor and sponsor.get("bioguideId") in self._member_lookup()),
            "cosponsors_count": (bill.get("cosponsors") or {}).get("count"),
            "policy_area": (bill.get("policyArea") or {}).get("name") or None,
            "introduced_date": bill.get("introducedDate") or None,
            "laws": [{"type": law.get("type"), "number": law.get("number")} for law in bill.get("laws") or []],
            "legislation_url": bill.get("legislationUrl") or None,
        }

    def annotate_roll_call_members(self, members: list[dict], senate: bool, congress: int) -> None:
        """Add covered_id and district to each /api/votes member row, in place (plan T7.4), with
        the same match and district rule as _covered_state_rows, so the rows site.js rcTableRow
        builds link covered members and print "District N" exactly as the server's rows do."""
        names = self._senate_name_index() if senate else {}
        lookup = self._member_lookup()
        for row in members:
            covered_id = self._row_covered_id(row, senate, names)
            district = None
            if not senate and covered_id and int(congress) == CURRENT_CONGRESS:
                district = (lookup.get(covered_id) or {}).get("district")
            row["covered_id"] = covered_id
            row["district"] = district
