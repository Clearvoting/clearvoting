import httpx
from urllib.parse import parse_qsl, urlsplit

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
        request_params = {"format": "json"}
        if params:
            request_params.update(params)
        headers = {"X-Api-Key": self.api_key}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=request_params, headers=headers)
            response.raise_for_status()
            data = response.json()

        self.cache.set(cache_key, data)
        return data

    async def get_members_by_state(self, state_code: str, current_only: bool = True) -> dict:
        params = {"limit": "250"}
        if current_only:
            params["currentMember"] = "true"
        data = await self._fetch(f"/member/{state_code}", params)
        members = list(data.get("members", []))

        # Follow pagination.next until exhausted. Only URLs under our own base
        # URL are followed, and each page is re-issued through _fetch so the
        # API key stays in headers instead of GETting an arbitrary URL.
        next_url = data.get("pagination", {}).get("next")
        pages_followed = 0
        while next_url and next_url.startswith(f"{self.base_url}/") and pages_followed < 20:
            parts = urlsplit(next_url)
            path = parts.path[len(urlsplit(self.base_url).path):]
            next_params = dict(parse_qsl(parts.query))
            next_params.pop("format", None)
            next_params.pop("api_key", None)
            page = await self._fetch(path, next_params)
            members.extend(page.get("members", []))
            next_url = page.get("pagination", {}).get("next")
            pages_followed += 1

        return {"members": members}

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
