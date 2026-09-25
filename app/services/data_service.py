import json
import logging
import re
from datetime import datetime
from pathlib import Path

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
