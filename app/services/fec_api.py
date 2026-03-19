"""FEC (Federal Election Commission) API client for campaign finance data.

Uses the free OpenFEC API (api.open.fec.gov) to fetch:
- Candidate lookup (name → FEC candidate ID)
- Principal campaign committee lookup
- Top contributing employers (organizations)
- Top donor occupations (industry proxy)
- Donation size breakdown

API key: free from api.data.gov, 1,000 calls/hour.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open.fec.gov/v1"
NOISE_EMPLOYERS = {
    "NOT EMPLOYED", "SELF-EMPLOYED", "SELF EMPLOYED", "RETIRED", "N/A",
    "NONE", "HOMEMAKER", "STUDENT", "INFORMATION REQUESTED",
    "INFORMATION REQUESTED PER BEST EFFORTS", "REFUSED",
}


class FECClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _fetch(self, path: str, params: dict | None = None) -> dict:
        """Make an authenticated request to the FEC API."""
        request_params = {"api_key": self.api_key, "per_page": 20}
        if params:
            request_params.update(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}{path}", params=request_params)
            response.raise_for_status()
            return response.json()

    async def search_candidate(
        self, name: str, state: str, office: str = ""
    ) -> dict | None:
        """Search for a candidate by name and state.

        Returns dict with candidate_id, name, office, state, or None.
        """
        params = {"name": name, "state": state, "per_page": 5}
        if office:
            params["office"] = office
        data = await self._fetch("/candidates/search/", params)
        results = data.get("results", [])
        if not results:
            return None
        # Return best match (first result — API ranks by relevance)
        r = results[0]
        return {
            "candidate_id": r.get("candidate_id", ""),
            "name": r.get("name", ""),
            "office": r.get("office_full", ""),
            "state": r.get("state", ""),
            "party": r.get("party_full", ""),
        }

    async def get_principal_committee(self, candidate_id: str) -> str | None:
        """Get the principal campaign committee ID for a candidate."""
        data = await self._fetch(
            f"/candidate/{candidate_id}/committees/",
            {"designation": "P", "per_page": 1},
        )
        results = data.get("results", [])
        if not results:
            return None
        return results[0].get("committee_id")

    async def get_top_employers(
        self, committee_id: str, cycle: int = 2024, limit: int = 15
    ) -> list[dict]:
        """Get top contributing employers (organizations) for a committee.

        Filters out noise entries like "NOT EMPLOYED", "SELF-EMPLOYED", etc.
        Returns list of dicts with keys: org_name, total, count.
        """
        data = await self._fetch(
            "/schedules/schedule_a/by_employer/",
            {"committee_id": committee_id, "cycle": cycle, "sort": "-total", "per_page": limit + 10},
        )
        results = []
        for r in data.get("results", []):
            employer = (r.get("employer") or "").strip()
            if not employer or employer.upper() in NOISE_EMPLOYERS:
                continue
            results.append({
                "org_name": employer,
                "total": int(r.get("total", 0)),
                "count": int(r.get("count", 0)),
            })
            if len(results) >= limit:
                break
        return results

    async def get_top_occupations(
        self, committee_id: str, cycle: int = 2024, limit: int = 10
    ) -> list[dict]:
        """Get top donor occupations for a committee.

        Serves as industry proxy. Returns list of dicts with keys:
        industry_name, total, count.
        """
        data = await self._fetch(
            "/schedules/schedule_a/by_occupation/",
            {"committee_id": committee_id, "cycle": cycle, "sort": "-total", "per_page": limit + 5},
        )
        results = []
        for r in data.get("results", []):
            occupation = (r.get("occupation") or "").strip()
            if not occupation or occupation.upper() in NOISE_EMPLOYERS:
                continue
            results.append({
                "industry_name": occupation.title(),
                "total": int(r.get("total", 0)),
                "count": int(r.get("count", 0)),
            })
            if len(results) >= limit:
                break
        return results

    async def get_donation_size_breakdown(
        self, committee_id: str, cycle: int = 2024
    ) -> list[dict]:
        """Get contribution breakdown by size (small vs large donors).

        Returns list of dicts with keys: size, total, count.
        Size categories: 0 (unitemized <$200), 200, 500, 1000, 2000.
        """
        data = await self._fetch(
            "/schedules/schedule_a/by_size/",
            {"committee_id": committee_id, "cycle": cycle},
        )
        results = []
        for r in data.get("results", []):
            results.append({
                "size": int(r.get("size", 0)),
                "total": int(r.get("total", 0)),
                "count": r.get("count"),
            })
        return sorted(results, key=lambda x: x["total"], reverse=True)

    async def get_committee_totals(
        self, committee_id: str, cycle: int = 2024
    ) -> dict | None:
        """Get total receipts and disbursements for a committee."""
        data = await self._fetch(
            f"/committee/{committee_id}/totals/",
            {"cycle": cycle, "per_page": 1},
        )
        results = data.get("results", [])
        if not results:
            return None
        r = results[0]
        return {
            "total_receipts": int(r.get("receipts", 0)),
            "total_disbursements": int(r.get("disbursements", 0)),
            "total_individual": int(r.get("individual_contributions", 0)),
            "total_pac": int(r.get("other_political_committee_contributions", 0)),
        }
