import json
import re
from pathlib import Path

# Matches bill documents in vote files, e.g. "H.R. 1", "H.Res. 24", "S.J.Res. 10".
# Tolerates optional spaces between abbreviation parts ("H. Res. 88").
_BILL_DOCUMENT_RE = re.compile(r"^([A-Za-z]+(?:\.\s*[A-Za-z]+)*\.?)\s+(\d+)$")


class DataService:
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
        self._load()

    def _load(self) -> None:
        self._members = self._read_json("members.json").get("members", [])
        self._bills = self._read_json("bills.json").get("bills", [])
        self._ai_summaries = self._read_json("ai_summaries.json")
        self._member_summaries = self._read_json("member_summaries.json")
        self._donations = self._read_json("donations.json")
        metadata_path = self.data_dir / "sync_metadata.json"
        if metadata_path.exists():
            self._metadata = self._read_json("sync_metadata.json")

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

    def get_bills(self, offset: int = 0, limit: int = 20) -> dict:
        paginated = self._bills[offset:offset + limit]
        return {"bills": paginated}

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
