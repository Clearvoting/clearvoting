import httpx
from app.services.cache import CacheService


class CongressAPIClient:
    def __init__(self, api_key: str, cache: CacheService, base_url: str = "https://api.congress.gov/v3"):
        self.api_key = api_key
        self.base_url = base_url
        self.cache = cache

    async def _fetch(self, path: str, params: dict | None = None) -> dict:
        cache_key = f"congress:{path}:{params}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}{path}"
        request_params = {"api_key": self.api_key, "format": "json"}
        if params:
            request_params.update(params)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=request_params)
            response.raise_for_status()
            data = response.json()

        self.cache.set(cache_key, data)
        return data

    async def get_members_by_state(self, state_code: str, current_only: bool = True) -> dict:
        params = {}
        if current_only:
            params["currentMember"] = "true"
        return await self._fetch(f"/member/{state_code}", params)

    async def get_members_by_district(self, state_code: str, district: int, current_only: bool = True) -> dict:
        params = {}
        if current_only:
            params["currentMember"] = "true"
        return await self._fetch(f"/member/{state_code}/{district}", params)

    async def get_member(self, bioguide_id: str) -> dict:
        return await self._fetch(f"/member/{bioguide_id}")

    async def get_bill(self, congress: int, bill_type: str, bill_number: int) -> dict:
        return await self._fetch(f"/bill/{congress}/{bill_type}/{bill_number}")

    async def get_bill_summary(self, congress: int, bill_type: str, bill_number: int) -> dict:
        return await self._fetch(f"/bill/{congress}/{bill_type}/{bill_number}/summaries")

    async def get_bill_text(self, congress: int, bill_type: str, bill_number: int) -> dict:
        return await self._fetch(f"/bill/{congress}/{bill_type}/{bill_number}/text")

    async def get_bill_subjects(self, congress: int, bill_type: str, bill_number: int) -> dict:
        return await self._fetch(f"/bill/{congress}/{bill_type}/{bill_number}/subjects")

    async def get_bills(self, congress: int | None = None, offset: int = 0, limit: int = 20) -> dict:
        params = {"offset": str(offset), "limit": str(limit)}
        path = f"/bill/{congress}" if congress else "/bill"
        return await self._fetch(path, params)

    async def get_house_votes(self, congress: int, session: int) -> dict:
        return await self._fetch(f"/house-vote/{congress}/{session}")

    async def get_house_vote_detail(self, congress: int, session: int, vote_number: int) -> dict:
        return await self._fetch(f"/house-vote/{congress}/{session}/{vote_number}")

    async def get_house_vote_members(self, congress: int, session: int, vote_number: int) -> dict:
        return await self._fetch(f"/house-vote/{congress}/{session}/{vote_number}/members")
