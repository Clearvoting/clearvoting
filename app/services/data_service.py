import json
from pathlib import Path


class DataService:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._members: list[dict] = []
        self._bills: list[dict] = []
        self._ai_summaries: dict[str, dict] = {}
        self._member_summaries: dict[str, dict] = {}
        self._metadata: dict = {}
        self._load()

    def _load(self) -> None:
        self._members = self._read_json("members.json").get("members", [])
        self._bills = self._read_json("bills.json").get("bills", [])
        self._ai_summaries = self._read_json("ai_summaries.json")
        self._member_summaries = self._read_json("member_summaries.json")
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
            return json.load(f)

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
                area_counts[area] = {"yea": 0, "nay": 0, "total": 0, "strengthen": 0, "weaken": 0, "neutral": 0}
            position = vote.get("vote", "").lower()
            direction = vote.get("direction")
            is_yea = position in ("yea", "aye")
            is_nay = position in ("nay", "no")
            if is_yea:
                area_counts[area]["yea"] += 1
            elif is_nay:
                area_counts[area]["nay"] += 1
            area_counts[area]["total"] += 1

            # Compute effective stance: Yea on "strengthens" or Nay on "weakens" = strengthen
            if direction == "strengthens":
                if is_yea:
                    area_counts[area]["strengthen"] += 1
                elif is_nay:
                    area_counts[area]["weaken"] += 1
            elif direction == "weakens":
                if is_yea:
                    area_counts[area]["weaken"] += 1
                elif is_nay:
                    area_counts[area]["strengthen"] += 1
            elif direction == "neutral" or direction is None:
                if is_yea or is_nay:
                    area_counts[area]["neutral"] += 1

        top_areas = sorted(area_counts.items(), key=lambda x: x[1]["total"], reverse=True)[:3]
        top_policy_areas = [
            {"name": name, "yea": counts["yea"], "nay": counts["nay"], "total": counts["total"],
             "strengthen": counts["strengthen"], "weaken": counts["weaken"], "neutral": counts["neutral"]}
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
    def _bill_type_to_document_pattern(bill_type: str, bill_number: int) -> str | None:
        """Convert normalized bill type to the document field pattern used in vote files."""
        patterns = {
            "hr": f"H.R. {bill_number}",
            "s": f"S. {bill_number}",
            "hjres": f"H.J.Res. {bill_number}",
            "sjres": f"S.J.Res. {bill_number}",
            "hconres": f"H.Con.Res. {bill_number}",
            "sconres": f"S.Con.Res. {bill_number}",
            "hres": f"H.Res. {bill_number}",
            "sres": f"S.Res. {bill_number}",
        }
        return patterns.get(bill_type.lower())

    def _search_votes_in_dir(self, vote_dir: Path, pattern: str) -> list[dict]:
        """Search a vote directory for votes matching a bill document pattern."""
        votes = []
        if not vote_dir.exists():
            return votes
        pattern_lower = pattern.lower()
        for vote_file in vote_dir.glob("*.json"):
            with open(vote_file, "r") as f:
                vote = json.load(f)
            doc = vote.get("document", "").lower()
            if pattern_lower in doc:
                votes.append(vote)
        return votes

    def get_bill_votes(self, congress: int, bill_type: str, bill_number: int) -> dict | None:
        pattern = self._bill_type_to_document_pattern(bill_type, bill_number)
        if not pattern:
            return None
        senate_votes = self._search_votes_in_dir(
            self.data_dir / "votes" / "senate", pattern
        )
        house_votes = self._search_votes_in_dir(
            self.data_dir / "votes" / "house", pattern
        )
        if not senate_votes and not house_votes:
            return None
        return {"senate": senate_votes, "house": house_votes}

    def get_sync_metadata(self) -> dict:
        return self._metadata
