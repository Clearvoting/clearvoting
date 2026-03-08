import defusedxml.ElementTree as ET
import httpx
from app.services.cache import CacheService


def parse_senate_vote_xml(xml_string: str) -> dict:
    root = ET.fromstring(xml_string)

    counts_el = root.find("count")
    counts = {
        "yeas": int(counts_el.findtext("yeas", "0") or "0"),
        "nays": int(counts_el.findtext("nays", "0") or "0"),
        "present": int(counts_el.findtext("present", "0") or "0"),
        "absent": int(counts_el.findtext("absent", "0") or "0"),
    }

    members = []
    for member_el in root.findall(".//members/member"):
        members.append({
            "first_name": member_el.findtext("first_name", ""),
            "last_name": member_el.findtext("last_name", ""),
            "party": member_el.findtext("party", ""),
            "state": member_el.findtext("state", ""),
            "vote": member_el.findtext("vote_cast", ""),
            "lis_member_id": member_el.findtext("lis_member_id", ""),
        })

    return {
        "congress": int(root.findtext("congress", "0")),
        "session": int(root.findtext("session", "0")),
        "vote_number": int(root.findtext("vote_number", "0")),
        "vote_date": root.findtext("vote_date", ""),
        "question": root.findtext("vote_question_text", ""),
        "document": root.findtext("document/document_name", "") or root.findtext("vote_document_text", ""),
        "result": root.findtext("vote_result_text", ""),
        "title": root.findtext("vote_title", ""),
        "counts": counts,
        "members": members,
    }


class SenateVoteService:
    BASE_URL = "https://www.senate.gov/legislative/LIS/roll_call_votes"

    def __init__(self, cache: CacheService):
        self.cache = cache

    def _build_url(self, congress: int, session: int, vote_number: int) -> str:
        vote_str = f"vote_{congress}_{session}_{vote_number:05d}"
        return f"{self.BASE_URL}/vote{congress}{session}/{vote_str}.xml"

    async def get_vote(self, congress: int, session: int, vote_number: int) -> dict:
        cache_key = f"senate_vote:{congress}:{session}:{vote_number}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        url = self._build_url(congress, session, vote_number)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        result = parse_senate_vote_xml(response.text)
        self.cache.set(cache_key, result)
        return result
