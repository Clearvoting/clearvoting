# Data Sync Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace live Congress.gov API calls and hardcoded demo data with a local sync script that pre-builds all data as JSON files, enabling all 50 states at zero hosting cost.

**Architecture:** A standalone sync script (`sync.py`) fetches all member, bill, and vote data from Congress.gov/Senate.gov, generates AI summaries via Claude, and saves everything as JSON files in `data/synced/`. A new `DataService` loads these files at startup and serves them to routers. Routers are simplified to a single code path — no more demo/live branching.

**Tech Stack:** Python, FastAPI, httpx, anthropic SDK, existing CacheService, flat-file JSON storage

**Design doc:** `docs/plans/2026-03-07-data-sync-architecture-design.md`

---

## Phase 1: DataService — Reading Pre-Built JSON Files

### Task 1: Create test fixture data and DataService skeleton

**Files:**
- Create: `tests/fixtures/synced/members.json`
- Create: `tests/fixtures/synced/bills.json`
- Create: `tests/fixtures/synced/ai_summaries.json`
- Create: `tests/fixtures/synced/votes/senate/119_1_00372.json`
- Create: `tests/fixtures/synced/member_votes/S001217.json`
- Create: `tests/fixtures/synced/sync_metadata.json`
- Create: `app/services/data_service.py`
- Create: `tests/test_data_service.py`

**Step 1: Create minimal test fixture files**

Create the `tests/fixtures/synced/` directory with small but realistic JSON files that match the shapes the app already returns. These are test-only — not the real synced data.

`tests/fixtures/synced/members.json`:
```json
{
  "members": [
    {
      "bioguideId": "S001217",
      "name": "Scott, Rick",
      "directOrderName": "Rick Scott",
      "state": "Florida",
      "stateCode": "FL",
      "district": null,
      "partyName": "Republican",
      "partyCode": "R",
      "chamber": "Senate",
      "terms": {"item": [
        {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": null, "stateCode": "FL"}
      ]},
      "depiction": {"imageUrl": "https://www.congress.gov/img/member/s001217_200.jpg", "attribution": ""},
      "currentMember": true
    },
    {
      "bioguideId": "D000032",
      "name": "Donalds, Byron",
      "directOrderName": "Byron Donalds",
      "state": "Florida",
      "stateCode": "FL",
      "district": 19,
      "partyName": "Republican",
      "partyCode": "R",
      "chamber": "House",
      "terms": {"item": [
        {"chamber": "House of Representatives", "congress": 119, "startYear": 2025, "endYear": null, "stateCode": "FL"}
      ]},
      "depiction": {"imageUrl": "https://www.congress.gov/img/member/d000032_200.jpg", "attribution": ""},
      "currentMember": true
    },
    {
      "bioguideId": "S000148",
      "name": "Schumer, Charles E.",
      "directOrderName": "Charles E. Schumer",
      "state": "New York",
      "stateCode": "NY",
      "district": null,
      "partyName": "Democrat",
      "partyCode": "D",
      "chamber": "Senate",
      "terms": {"item": [
        {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": null, "stateCode": "NY"}
      ]},
      "depiction": {"imageUrl": "https://www.congress.gov/img/member/s000148_200.jpg", "attribution": ""},
      "currentMember": true
    }
  ]
}
```

`tests/fixtures/synced/bills.json`:
```json
{
  "bills": [
    {
      "congress": 119,
      "type": "HR",
      "number": "1",
      "title": "One Big Beautiful Bill Act",
      "latestAction": {"actionDate": "2025-05-22", "text": "Passed Senate"},
      "sponsors": [{"bioguideId": "S001217", "fullName": "Rep. Smith, Jason [R-MO-8]"}],
      "policyArea": {"name": "Taxation"},
      "summaries": [{"text": "Official summary text here."}]
    },
    {
      "congress": 119,
      "type": "S",
      "number": "100",
      "title": "Veterans Benefits Enhancement Act",
      "latestAction": {"actionDate": "2025-04-10", "text": "Introduced in Senate"},
      "sponsors": [],
      "policyArea": {"name": "Armed Forces and National Security"},
      "summaries": []
    }
  ]
}
```

`tests/fixtures/synced/ai_summaries.json`:
```json
{
  "119-hr-1": {
    "provisions": [
      "Cuts taxes on tips for workers like servers and bartenders, up to $25,000 a year.",
      "Raises the limit on state and local tax deductions from $10,000 to $40,000."
    ],
    "impact_categories": ["Taxes", "Wages & Income"]
  }
}
```

`tests/fixtures/synced/votes/senate/119_1_00372.json`:
```json
{
  "congress": 119,
  "session": 1,
  "vote_number": 372,
  "vote_date": "2025-05-22",
  "question": "On Passage of the Bill",
  "document": "H.R. 1",
  "result": "Bill Passed",
  "title": "One Big Beautiful Bill Act",
  "counts": {"yeas": 51, "nays": 49, "present": 0, "absent": 0},
  "members": [
    {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea", "lis_member_id": "S001217"},
    {"first_name": "Charles", "last_name": "Schumer", "party": "D", "state": "NY", "vote": "Nay", "lis_member_id": "S000148"}
  ]
}
```

`tests/fixtures/synced/member_votes/S001217.json`:
```json
{
  "member_id": "S001217",
  "congress": 119,
  "stats": {
    "total_votes": 2,
    "yea_count": 1,
    "nay_count": 1,
    "not_voting_count": 0,
    "participation_rate": 100.0
  },
  "scorecard": [
    {"issue": "Taxes", "description": "Tax policy and reform", "votes_for": 1, "votes_against": 0, "total_votes": 1, "alignment_pct": 100}
  ],
  "votes": [
    {
      "bill_number": "H.R. 1",
      "bill_id": "119-hr-1",
      "one_liner": "One Big Beautiful Bill Act",
      "vote": "Yea",
      "date": "2025-05-22",
      "result": "Bill Passed",
      "policy_area": "Taxation",
      "chamber": "Senate",
      "cbo_deficit_impact": "+$2.3 trillion over 10 years"
    },
    {
      "bill_number": "S. 100",
      "bill_id": "119-s-100",
      "one_liner": "Veterans Benefits Enhancement Act",
      "vote": "Nay",
      "date": "2025-04-10",
      "result": "Bill Failed",
      "policy_area": "Armed Forces and National Security",
      "chamber": "Senate",
      "cbo_deficit_impact": null
    }
  ],
  "policy_areas": ["Taxation", "Armed Forces and National Security"]
}
```

`tests/fixtures/synced/sync_metadata.json`:
```json
{
  "last_sync": "2026-03-07T06:00:00Z",
  "members_count": 3,
  "bills_count": 2,
  "ai_summaries_count": 1,
  "senate_votes_count": 1,
  "member_votes_count": 1
}
```

**Step 2: Write the failing tests for DataService**

`tests/test_data_service.py`:
```python
import pytest
from pathlib import Path
from app.services.data_service import DataService

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


@pytest.fixture
def data_service():
    return DataService(data_dir=FIXTURES)


def test_get_members_by_state(data_service):
    result = data_service.get_members_by_state("FL")
    assert len(result["members"]) == 2
    assert all(m["stateCode"] == "FL" for m in result["members"])


def test_get_members_by_state_not_found(data_service):
    result = data_service.get_members_by_state("ZZ")
    assert result["members"] == []


def test_get_member_detail(data_service):
    result = data_service.get_member_detail("S001217")
    assert result["member"]["bioguideId"] == "S001217"
    assert result["member"]["directOrderName"] == "Rick Scott"


def test_get_member_detail_not_found(data_service):
    result = data_service.get_member_detail("X999999")
    assert result is None


def test_get_member_votes(data_service):
    result = data_service.get_member_votes("S001217")
    assert result["member_id"] == "S001217"
    assert result["stats"]["total_votes"] == 2
    assert len(result["votes"]) == 2


def test_get_member_votes_not_found(data_service):
    result = data_service.get_member_votes("X999999")
    assert result is None


def test_get_bills(data_service):
    result = data_service.get_bills()
    assert len(result["bills"]) == 2


def test_get_bills_pagination(data_service):
    result = data_service.get_bills(offset=0, limit=1)
    assert len(result["bills"]) == 1


def test_get_bill_detail(data_service):
    result = data_service.get_bill_detail(119, "hr", 1)
    assert result is not None
    assert result["bill"]["title"] == "One Big Beautiful Bill Act"


def test_get_bill_detail_not_found(data_service):
    result = data_service.get_bill_detail(119, "hr", 9999)
    assert result is None


def test_get_ai_summary(data_service):
    result = data_service.get_ai_summary(119, "hr", 1)
    assert result is not None
    assert len(result["provisions"]) == 2
    assert "Taxes" in result["impact_categories"]


def test_get_ai_summary_not_found(data_service):
    result = data_service.get_ai_summary(119, "s", 9999)
    assert result is None


def test_get_senate_vote(data_service):
    result = data_service.get_senate_vote(119, 1, 372)
    assert result is not None
    assert result["vote_number"] == 372
    assert len(result["members"]) == 2


def test_get_senate_vote_not_found(data_service):
    result = data_service.get_senate_vote(119, 1, 999)
    assert result is None


def test_get_members_by_district(data_service):
    result = data_service.get_members_by_district("FL", 19)
    assert len(result["members"]) == 1
    assert result["members"][0]["bioguideId"] == "D000032"


def test_get_sync_metadata(data_service):
    result = data_service.get_sync_metadata()
    assert result["members_count"] == 3
    assert "last_sync" in result
```

**Step 3: Run tests to verify they fail**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_data_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.data_service'`

**Step 4: Write the DataService implementation**

`app/services/data_service.py`:
```python
import json
from pathlib import Path
from typing import Any


class DataService:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._members: list[dict] = []
        self._bills: list[dict] = []
        self._ai_summaries: dict[str, dict] = {}
        self._metadata: dict = {}
        self._load()

    def _load(self) -> None:
        self._members = self._read_json("members.json").get("members", [])
        self._bills = self._read_json("bills.json").get("bills", [])
        self._ai_summaries = self._read_json("ai_summaries.json")
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
            if m.get("stateCode") == state_code and (m.get("district") == district or m.get("district") is None)
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

    def get_sync_metadata(self) -> dict:
        return self._metadata
```

**Step 5: Run tests to verify they pass**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_data_service.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add tests/fixtures/ tests/test_data_service.py app/services/data_service.py
git commit -m "feat: add DataService for reading pre-synced JSON data files

Phase 1 of data sync architecture — introduces DataService class that
reads congressional data from flat JSON files, plus test fixtures and
16 passing tests."
```

---

## Phase 2: Refactor Routers to Use DataService

### Task 2: Add DataService to dependencies and refactor members router

**Files:**
- Modify: `app/dependencies.py`
- Modify: `app/routers/members.py`
- Create: `tests/test_members_data_service.py`

**Step 1: Write failing tests for the refactored members router**

`tests/test_members_data_service.py` — tests that routers read from DataService (using fixtures):
```python
import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


@pytest.mark.asyncio
async def test_members_by_state_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL")

    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 2
    # Party should be stripped by default
    for m in data["members"]:
        assert "partyName" not in m
        assert "partyCode" not in m


@pytest.mark.asyncio
async def test_member_detail_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/detail/S001217")

    assert response.status_code == 200
    data = response.json()
    assert data["member"]["bioguideId"] == "S001217"


@pytest.mark.asyncio
async def test_member_detail_show_party():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/detail/S001217?show_party=true")

    data = response.json()
    assert "partyName" in data["member"]


@pytest.mark.asyncio
async def test_member_votes_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/votes")

    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == "S001217"
    assert len(data["votes"]) == 2


@pytest.mark.asyncio
async def test_member_votes_not_found():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/X999999/votes")

    assert response.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_members_data_service.py -v`
Expected: FAIL — `get_data_service` doesn't exist

**Step 3: Add DataService to dependencies.py**

Update `app/dependencies.py`:
```python
from functools import lru_cache
from pathlib import Path
from app.config import CONGRESS_API_KEY, ANTHROPIC_API_KEY, CACHE_DIR, CACHE_TTL_SECONDS, BASE_DIR
from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService
from app.services.ai_summary import AISummaryService
from app.services.data_service import DataService


def get_data_dir() -> Path:
    return BASE_DIR / "data" / "synced"


@lru_cache
def get_data_service() -> DataService:
    return DataService(data_dir=get_data_dir())


@lru_cache
def get_cache() -> CacheService:
    return CacheService(cache_dir=CACHE_DIR, ttl_seconds=CACHE_TTL_SECONDS)


@lru_cache
def get_congress_client() -> CongressAPIClient:
    return CongressAPIClient(api_key=CONGRESS_API_KEY, cache=get_cache())


@lru_cache
def get_senate_vote_service() -> SenateVoteService:
    return SenateVoteService(cache=get_cache())


@lru_cache
def get_ai_summary_service() -> AISummaryService:
    return AISummaryService(api_key=ANTHROPIC_API_KEY, cache=get_cache())
```

**Step 4: Refactor members router**

Replace `app/routers/members.py` with:
```python
import re
import copy
import logging
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/members", tags=["members"])

BIOGUIDE_PATTERN = re.compile(r"^[A-Z]\d{6}$")


def _validate_bioguide_id(bioguide_id: str) -> None:
    if not BIOGUIDE_PATTERN.match(bioguide_id.upper()):
        raise HTTPException(status_code=400, detail="Invalid member ID format")


def _validate_state_code(state_code: str) -> str:
    if not state_code.isalpha() or len(state_code) != 2:
        raise HTTPException(status_code=400, detail="State code must be 2 letters")
    return state_code.upper()


@router.get("/{bioguide_id}/votes")
async def get_member_votes(
    bioguide_id: str,
    congress: int = Query(119, ge=1, le=200),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    data = data_service.get_member_votes(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    sorted_votes = sorted(data["votes"], key=lambda v: v["date"], reverse=True)
    paginated = sorted_votes[offset:offset + limit]
    return {
        "member_id": data["member_id"],
        "congress": data["congress"],
        "stats": data["stats"],
        "scorecard": data.get("scorecard", []),
        "votes": paginated,
        "total_count": len(sorted_votes),
        "policy_areas": data["policy_areas"],
    }


@router.get("/{state_code}")
async def get_members_by_state(state_code: str):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_state(state_code)
    return _strip_party(data)


@router.get("/detail/{bioguide_id}")
async def get_member_detail(bioguide_id: str, show_party: bool = False):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    data = data_service.get_member_detail(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    return data if show_party else _strip_party(data)


@router.get("/{state_code}/{district}")
async def get_members_by_district(state_code: str, district: int):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_district(state_code, district)
    return _strip_party(data)


def _strip_party(data: dict) -> dict:
    """Remove party information from member data for default display."""
    stripped = copy.deepcopy(data)

    def _remove_party_fields(obj):
        if isinstance(obj, dict):
            for key in ["partyName", "party", "partyCode"]:
                obj.pop(key, None)
            for value in obj.values():
                _remove_party_fields(value)
        elif isinstance(obj, list):
            for item in obj:
                _remove_party_fields(item)

    _remove_party_fields(stripped)
    return stripped
```

**Step 5: Run the new tests**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_members_data_service.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add app/dependencies.py app/routers/members.py tests/test_members_data_service.py
git commit -m "refactor: members router reads from DataService instead of live API/mock

Removes _is_demo() branching and Congress API calls from members router.
All member data now served from pre-synced JSON files via DataService."
```

---

### Task 3: Refactor bills, votes, and search routers

**Files:**
- Modify: `app/routers/bills.py`
- Modify: `app/routers/votes.py`
- Modify: `app/routers/search.py`
- Create: `tests/test_bills_data_service.py`
- Create: `tests/test_votes_data_service.py`

**Step 1: Write failing tests for bills router**

`tests/test_bills_data_service.py`:
```python
import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


@pytest.mark.asyncio
async def test_list_bills_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills")

    assert response.status_code == 200
    data = response.json()
    assert len(data["bills"]) == 2


@pytest.mark.asyncio
async def test_get_bill_detail_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hr/1")

    assert response.status_code == 200
    data = response.json()
    assert data["bill"]["title"] == "One Big Beautiful Bill Act"


@pytest.mark.asyncio
async def test_get_ai_summary_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hr/1/ai-summary")

    assert response.status_code == 200
    data = response.json()
    assert len(data["provisions"]) == 2


@pytest.mark.asyncio
async def test_get_ai_summary_pending():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/s/100/ai-summary")

    assert response.status_code == 200
    data = response.json()
    assert "pending" in data["provisions"][0].lower() or "unavailable" in data["provisions"][0].lower()
```

**Step 2: Write failing tests for votes router**

`tests/test_votes_data_service.py`:
```python
import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


@pytest.mark.asyncio
async def test_get_senate_vote_from_data_service():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/1/372")

    assert response.status_code == 200
    data = response.json()
    assert data["vote_number"] == 372
    # Party stripped by default
    for member in data["members"]:
        assert "party" not in member


@pytest.mark.asyncio
async def test_get_senate_vote_show_party():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/1/372?show_party=true")

    data = response.json()
    assert data["members"][0]["party"] == "R"


@pytest.mark.asyncio
async def test_get_senate_vote_not_found():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        from app.dependencies import get_data_service
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/1/999")

    assert response.status_code == 404
```

**Step 3: Run tests to verify they fail**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_bills_data_service.py tests/test_votes_data_service.py -v`
Expected: FAIL — routers still use old code paths

**Step 4: Refactor bills router**

Replace `app/routers/bills.py` with:
```python
import logging
from fastapi import APIRouter, HTTPException, Path, Query, Request
from app.dependencies import get_data_service
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["bills"])

VALID_BILL_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}


def _validate_bill_type(bill_type: str) -> None:
    if bill_type.lower() not in VALID_BILL_TYPES:
        raise HTTPException(status_code=400, detail="Invalid bill type")


@router.get("")
async def list_bills(
    congress: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    data_service = get_data_service()
    return data_service.get_bills(offset=offset, limit=limit)


@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_bill_detail(congress, bill_type, bill_number)
    if not result:
        return {
            "bill": {"congress": congress, "type": bill_type.upper(), "number": str(bill_number),
                     "title": f"{bill_type.upper()}.{bill_number}", "latestAction": {}, "summaries": []},
            "subjects": {"legislativeSubjects": []}
        }
    return result


@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
@limiter.limit("10/minute")
async def get_ai_summary(request: Request, congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_ai_summary(congress, bill_type, bill_number)
    if result:
        return result
    return {"provisions": ["Summary pending — will be available after the next sync."], "impact_categories": []}


@router.get("/{congress}/{bill_type}/{bill_number}/votes")
async def get_bill_votes(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_bill_votes(congress, bill_type, bill_number)
    if result:
        return result
    return {"senate": [], "house": []}
```

Note: `get_bill_votes` is a new method needed on DataService. Add it:

In `app/services/data_service.py`, add this method:
```python
def get_bill_votes(self, congress: int, bill_type: str, bill_number: int) -> dict | None:
    bill_type = bill_type.lower()
    # Search senate votes for this bill
    senate_votes = []
    senate_dir = self.data_dir / "votes" / "senate"
    if senate_dir.exists():
        for vote_file in senate_dir.glob("*.json"):
            with open(vote_file, "r") as f:
                vote = json.load(f)
            doc = vote.get("document", "").lower()
            bill_ref = f"{bill_type}.{'' if bill_type == 's' else ' '}{bill_number}"
            if bill_ref in doc.lower() or f"h.r. {bill_number}" in doc.lower():
                senate_votes.append(vote)
    if not senate_votes:
        return None
    return {"senate": senate_votes, "house": []}
```

Also add the corresponding test fixture assertion in `tests/test_data_service.py`:
```python
def test_get_bill_votes(data_service):
    result = data_service.get_bill_votes(119, "hr", 1)
    assert result is not None
    assert len(result["senate"]) == 1
```

**Step 5: Refactor votes router**

Replace `app/routers/votes.py` with:
```python
import copy
import logging
from fastapi import APIRouter, HTTPException, Path
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.get("/senate/{congress}/{session}/{vote_number}")
async def get_senate_vote(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    data_service = get_data_service()
    data = data_service.get_senate_vote(congress, session, vote_number)
    if not data:
        raise HTTPException(status_code=404, detail="Vote not found")
    if not show_party:
        data = copy.deepcopy(data)
        for member in data.get("members", []):
            member.pop("party", None)
    return data
```

Note: House vote endpoints are removed for now — they were calling live Congress.gov API directly and the sync script will add house vote support later. If needed, add a stub that reads from `data/synced/votes/house/`.

**Step 6: Refactor search router**

Replace `app/routers/search.py` with:
```python
import logging
from fastapi import APIRouter, Query
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/bills")
async def search_bills(
    q: str = Query(..., min_length=1),
    congress: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    data_service = get_data_service()
    all_bills = data_service.get_bills(offset=0, limit=10000)
    # Server-side title search
    q_lower = q.lower()
    filtered = [b for b in all_bills["bills"] if q_lower in b.get("title", "").lower()]
    paginated = filtered[offset:offset + limit]
    return {"bills": paginated}
```

**Step 7: Run all new tests**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_bills_data_service.py tests/test_votes_data_service.py tests/test_data_service.py -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add app/routers/bills.py app/routers/votes.py app/routers/search.py app/services/data_service.py tests/test_bills_data_service.py tests/test_votes_data_service.py tests/test_data_service.py
git commit -m "refactor: bills, votes, search routers use DataService

All routers now read from pre-synced JSON files. No more _is_demo()
branching or live Congress.gov API calls during user requests.
Search now filters server-side by title."
```

---

### Task 4: Update existing tests and remove dead code

**Files:**
- Modify: `tests/test_routers.py`
- Modify: `tests/test_member_votes.py`
- Modify: `tests/test_security.py`
- Modify: `tests/test_search_router.py`

**Step 1: Update test_routers.py**

Existing tests mock `_is_demo` and `get_congress_client`. Update them to mock `get_data_dir` instead, pointing at the test fixtures. Each test should:
- Patch `app.dependencies.get_data_dir` to return `FIXTURES`
- Call `get_data_service.cache_clear()` to reset the singleton
- Remove all `_is_demo` and `get_congress_client` patches

**Step 2: Update test_member_votes.py**

Same pattern — these tests currently rely on demo mode reading from `mock_data.py`. Update them to patch `get_data_dir` and use the fixture data. Adjust assertions to match fixture data (e.g., `S001217` has 2 votes in fixtures, not 15+).

**Step 3: Update test_security.py**

Security tests for input validation (bad state codes, bad bioguide IDs, invalid bill types) should still pass since validation logic is unchanged. Tests that check security headers and rate limiting are unaffected. Review and update any that mock `_is_demo` or `get_congress_client`.

**Step 4: Update test_search_router.py**

The search router now reads from DataService. Update tests to patch `get_data_dir`.

**Step 5: Run the full test suite**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/ -v`
Expected: ALL PASS (58+ tests)

**Step 6: Commit**

```bash
git add tests/
git commit -m "test: update all existing tests to use DataService fixtures

Removes all _is_demo and get_congress_client mocks from router tests.
All tests now use the shared fixture data in tests/fixtures/synced/."
```

---

## Phase 3: The Sync Script

### Task 5: Sync script — members

**Files:**
- Create: `sync.py`
- Create: `tests/test_sync.py`

**Step 1: Write failing test for member sync**

`tests/test_sync.py`:
```python
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from sync import sync_members

STATES = ["FL", "NY"]  # Just test with 2 states


@pytest.mark.asyncio
async def test_sync_members(tmp_path):
    mock_client = MagicMock()
    mock_client.get_members_by_state = AsyncMock(side_effect=[
        {"members": [{"bioguideId": "S001217", "name": "Scott, Rick", "state": "Florida"}]},
        {"members": [{"bioguideId": "S000148", "name": "Schumer, Charles", "state": "New York"}]},
    ])

    await sync_members(mock_client, tmp_path, states=STATES)

    members_file = tmp_path / "members.json"
    assert members_file.exists()
    data = json.loads(members_file.read_text())
    assert len(data["members"]) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py::test_sync_members -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sync'`

**Step 3: Write the sync script — members portion**

`sync.py`:
```python
"""ClearVote Data Sync Script

Pulls congressional data from Congress.gov and Senate.gov,
generates AI summaries via Claude, and saves everything as
JSON files in data/synced/ for the web app to serve.

Usage:
    cd ~/Documents/Claude/Projects/clearvote
    source .venv/bin/activate
    python sync.py
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService
from app.services.ai_summary import AISummaryService

BASE_DIR = Path(__file__).parent
SYNC_DIR = BASE_DIR / "data" / "synced"
CACHE_DIR = BASE_DIR / "data" / "cache"

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI",
]


def _atomic_write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


async def sync_members(client: CongressAPIClient, output_dir: Path, states: list[str] | None = None) -> int:
    """Fetch all current members of Congress and save to members.json."""
    states = states or US_STATES
    all_members = []
    for i, state in enumerate(states):
        print(f"  Fetching members for {state}... ({i + 1}/{len(states)})")
        try:
            data = await client.get_members_by_state(state)
            for member in data.get("members", []):
                member["stateCode"] = state
                # Determine chamber from terms
                terms = member.get("terms", {}).get("item", [])
                if terms:
                    member["chamber"] = terms[0].get("chamber", "Unknown")
                all_members.append(member)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {state}: {e}")

    _atomic_write_json(output_dir / "members.json", {"members": all_members})
    print(f"  Saved {len(all_members)} members")
    return len(all_members)


async def main() -> None:
    api_key = os.getenv("CONGRESS_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        print("ERROR: CONGRESS_API_KEY not set in .env")
        sys.exit(1)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    client = CongressAPIClient(api_key=api_key, cache=cache)

    print("=== ClearVote Data Sync ===")
    print(f"Output: {SYNC_DIR}")
    print()

    # Step 1: Members
    print("[1/5] Syncing members...")
    members_count = await sync_members(client, SYNC_DIR)

    # Steps 2-5 will be added in subsequent tasks

    # Write metadata
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "members_count": members_count,
        "bills_count": 0,
        "ai_summaries_count": 0,
        "senate_votes_count": 0,
        "member_votes_count": 0,
    }
    _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)
    print()
    print("=== Sync complete ===")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py::test_sync_members -v`
Expected: PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add sync script with member sync

Phase 3 of data sync architecture — sync.py fetches all current
members of Congress from Congress.gov and saves to data/synced/members.json."
```

---

### Task 6: Sync script — bills

**Files:**
- Modify: `sync.py`
- Modify: `tests/test_sync.py`

**Step 1: Write failing test for bills sync**

Add to `tests/test_sync.py`:
```python
from sync import sync_bills

@pytest.mark.asyncio
async def test_sync_bills(tmp_path):
    mock_client = MagicMock()
    mock_client.get_bills = AsyncMock(side_effect=[
        {"bills": [
            {"number": "1", "type": "HR", "congress": 119, "title": "Test Bill", "url": "http://example.com"},
            {"number": "100", "type": "S", "congress": 119, "title": "Another Bill", "url": "http://example.com"},
        ]},
        {"bills": []},  # Second page empty — stops pagination
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": [{"text": "Summary text"}]})

    await sync_bills(mock_client, tmp_path)

    bills_file = tmp_path / "bills.json"
    assert bills_file.exists()
    data = json.loads(bills_file.read_text())
    assert len(data["bills"]) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py::test_sync_bills -v`
Expected: FAIL — `sync_bills` not defined

**Step 3: Add sync_bills to sync.py**

```python
async def sync_bills(client: CongressAPIClient, output_dir: Path, congress: int = 119) -> int:
    """Fetch bills from current Congress with pagination."""
    all_bills = []
    offset = 0
    limit = 50
    while True:
        print(f"  Fetching bills (offset={offset})...")
        try:
            data = await client.get_bills(congress=congress, offset=offset, limit=limit)
            bills = data.get("bills", [])
            if not bills:
                break
            all_bills.extend(bills)
            offset += limit
        except Exception as e:
            print(f"  WARNING: Failed at offset {offset}: {e}")
            break

    # Fetch summaries for each bill
    for i, bill in enumerate(all_bills):
        bill_type = bill.get("type", "").lower()
        bill_number = int(bill.get("number", 0))
        print(f"  Fetching summary for {bill_type.upper()}.{bill_number}... ({i + 1}/{len(all_bills)})")
        try:
            summary_data = await client.get_bill_summary(congress, bill_type, bill_number)
            bill["summaries"] = summary_data.get("summaries", [])
        except Exception as e:
            print(f"  WARNING: Failed summary for {bill_type}.{bill_number}: {e}")
            bill["summaries"] = []

    _atomic_write_json(output_dir / "bills.json", {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills")
    return len(all_bills)
```

Update `main()` to call it:
```python
    # Step 2: Bills
    print("[2/5] Syncing bills...")
    bills_count = await sync_bills(client, SYNC_DIR)
```

Update metadata: `"bills_count": bills_count,`

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add bill sync with pagination and summaries"
```

---

### Task 7: Sync script — Senate votes

**Files:**
- Modify: `sync.py`
- Modify: `tests/test_sync.py`

**Step 1: Write failing test**

Add to `tests/test_sync.py`:
```python
from sync import sync_senate_votes

@pytest.mark.asyncio
async def test_sync_senate_votes(tmp_path):
    mock_service = MagicMock()
    mock_service.get_vote = AsyncMock(side_effect=[
        {
            "congress": 119, "session": 1, "vote_number": 1,
            "vote_date": "2025-01-15", "question": "On Passage",
            "result": "Passed", "counts": {"yeas": 60, "nays": 40, "present": 0, "absent": 0},
            "members": [{"first_name": "Test", "last_name": "Sen", "party": "D", "state": "NY", "vote": "Yea"}],
        },
        Exception("Vote not found"),  # Stop fetching
    ])

    count = await sync_senate_votes(mock_service, tmp_path, congress=119, session=1, max_vote=2)

    vote_dir = tmp_path / "votes" / "senate"
    assert vote_dir.exists()
    assert (vote_dir / "119_1_00001.json").exists()
    assert count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py::test_sync_senate_votes -v`
Expected: FAIL

**Step 3: Implement sync_senate_votes**

```python
async def sync_senate_votes(senate_service: SenateVoteService, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 500) -> int:
    """Fetch Senate roll call votes."""
    vote_dir = output_dir / "votes" / "senate"
    vote_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for vote_num in range(1, max_vote + 1):
        filename = f"{congress}_{session}_{vote_num:05d}.json"
        filepath = vote_dir / filename

        # Skip if already synced (incremental)
        if filepath.exists():
            count += 1
            continue

        print(f"  Fetching Senate vote {vote_num}...")
        try:
            data = await senate_service.get_vote(congress, session, vote_num)
            _atomic_write_json(filepath, data)
            count += 1
        except Exception:
            # No more votes — stop
            print(f"  No more Senate votes after {vote_num - 1}")
            break

    print(f"  Saved {count} Senate votes")
    return count
```

Update `main()`:
```python
    senate_service = SenateVoteService(cache=cache)

    # Step 3: Senate votes
    print("[3/5] Syncing Senate votes...")
    senate_count = await sync_senate_votes(senate_service, SYNC_DIR)
```

Update metadata: `"senate_votes_count": senate_count,`

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add Senate vote sync with incremental updates"
```

---

### Task 8: Sync script — AI summaries

**Files:**
- Modify: `sync.py`
- Modify: `tests/test_sync.py`

**Step 1: Write failing test**

Add to `tests/test_sync.py`:
```python
from sync import sync_ai_summaries

@pytest.mark.asyncio
async def test_sync_ai_summaries(tmp_path):
    # Write a bills.json first
    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test Bill", "summaries": [{"text": "Official summary"}]},
        {"congress": 119, "type": "S", "number": "50", "title": "Another", "summaries": []},
    ]}
    _test_write_json(tmp_path / "bills.json", bills)

    # Existing summaries (should be skipped)
    existing = {"119-hr-1": {"provisions": ["Already done"], "impact_categories": ["Taxes"]}}
    _test_write_json(tmp_path / "ai_summaries.json", existing)

    mock_ai = MagicMock()
    mock_ai.generate_summary = AsyncMock(return_value={
        "provisions": ["New summary"], "impact_categories": ["Healthcare"]
    })

    mock_congress = MagicMock()
    mock_congress.get_bill_text = AsyncMock(return_value={"textVersions": []})

    count = await sync_ai_summaries(mock_ai, mock_congress, tmp_path)

    data = json.loads((tmp_path / "ai_summaries.json").read_text())
    assert "119-hr-1" in data  # Kept existing
    assert data["119-hr-1"]["provisions"] == ["Already done"]  # Not overwritten
    assert "119-s-50" in data  # New one added
    assert count == 1  # Only 1 new summary generated


def _test_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py::test_sync_ai_summaries -v`
Expected: FAIL

**Step 3: Implement sync_ai_summaries**

```python
async def sync_ai_summaries(ai_service: AISummaryService, congress_client: CongressAPIClient, output_dir: Path) -> int:
    """Generate AI summaries for bills that don't have one yet."""
    bills_path = output_dir / "bills.json"
    summaries_path = output_dir / "ai_summaries.json"

    if not bills_path.exists():
        print("  No bills.json found — skipping AI summaries")
        return 0

    with open(bills_path) as f:
        bills_data = json.load(f)

    # Load existing summaries
    existing = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    new_count = 0
    bills = bills_data.get("bills", [])
    for i, bill in enumerate(bills):
        congress = bill.get("congress", 119)
        bill_type = bill.get("type", "").lower()
        bill_number = int(bill.get("number", 0))
        bill_id = f"{congress}-{bill_type}-{bill_number}"

        if bill_id in existing:
            continue

        title = bill.get("title", "")
        summaries = bill.get("summaries", [])
        official_summary = summaries[0].get("text", "") if summaries else ""

        if not official_summary and not title:
            continue

        print(f"  Generating AI summary for {bill_id}... ({i + 1}/{len(bills)})")

        # Try to get bill text excerpt
        bill_text_excerpt = ""
        try:
            text_data = await congress_client.get_bill_text(congress, bill_type, bill_number)
            text_versions = text_data.get("textVersions", [])
            if text_versions:
                formats = text_versions[0].get("formats", [])
                for fmt in formats:
                    if fmt.get("type") == "Formatted Text":
                        import httpx
                        async with httpx.AsyncClient(timeout=10.0) as http_client:
                            resp = await http_client.get(fmt["url"])
                            if resp.status_code == 200:
                                bill_text_excerpt = resp.text[:5000]
                        break
        except Exception as e:
            print(f"  WARNING: Could not fetch bill text for {bill_id}: {e}")

        try:
            result = await ai_service.generate_summary(
                bill_id=bill_id,
                title=title,
                official_summary=official_summary,
                bill_text_excerpt=bill_text_excerpt,
            )
            existing[bill_id] = result
            new_count += 1
        except Exception as e:
            print(f"  WARNING: AI summary failed for {bill_id}: {e}")

    _atomic_write_json(summaries_path, existing)
    print(f"  Generated {new_count} new AI summaries ({len(existing)} total)")
    return new_count
```

Update `main()`:
```python
    ai_service = AISummaryService(api_key=anthropic_key, cache=cache) if anthropic_key else None

    # Step 4: AI summaries
    if ai_service:
        print("[4/5] Generating AI summaries...")
        ai_count = await sync_ai_summaries(ai_service, client, SYNC_DIR)
    else:
        print("[4/5] Skipping AI summaries (no ANTHROPIC_API_KEY)")
        ai_count = 0
```

Update metadata: `"ai_summaries_count": ai_count,`

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add AI summary sync — incremental, skips existing"
```

---

### Task 9: Sync script — member voting records

**Files:**
- Modify: `sync.py`
- Modify: `tests/test_sync.py`

**Step 1: Write failing test**

Add to `tests/test_sync.py`:
```python
from sync import build_member_votes

@pytest.mark.asyncio
async def test_build_member_votes(tmp_path):
    # Set up members
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "stateCode": "FL", "chamber": "Senate"},
    ]}
    _test_write_json(tmp_path / "members.json", members)

    # Set up bills
    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test Bill",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _test_write_json(tmp_path / "bills.json", bills)

    # Set up senate vote
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    vote = {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {"yeas": 60, "nays": 40, "present": 0, "absent": 0},
        "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R",
             "state": "FL", "vote": "Yea", "lis_member_id": "S001217"},
        ],
    }
    _test_write_json(vote_dir / "119_1_00001.json", vote)

    count = await build_member_votes(tmp_path)

    member_votes_dir = tmp_path / "member_votes"
    assert member_votes_dir.exists()
    s_file = member_votes_dir / "S001217.json"
    assert s_file.exists()
    data = json.loads(s_file.read_text())
    assert data["member_id"] == "S001217"
    assert data["stats"]["total_votes"] == 1
    assert data["stats"]["yea_count"] == 1
    assert len(data["votes"]) == 1
    assert count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py::test_build_member_votes -v`
Expected: FAIL

**Step 3: Implement build_member_votes**

```python
async def build_member_votes(output_dir: Path) -> int:
    """Cross-reference votes with members to build per-member voting records."""
    members_path = output_dir / "members.json"
    bills_path = output_dir / "bills.json"
    senate_dir = output_dir / "votes" / "senate"
    member_votes_dir = output_dir / "member_votes"
    member_votes_dir.mkdir(parents=True, exist_ok=True)

    if not members_path.exists():
        print("  No members.json — skipping")
        return 0

    with open(members_path) as f:
        members_data = json.load(f)

    # Build bill lookup for policy areas and titles
    bill_lookup: dict[str, dict] = {}
    if bills_path.exists():
        with open(bills_path) as f:
            bills_data = json.load(f)
        for bill in bills_data.get("bills", []):
            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number", "")
            key = f"{bill_type}-{bill_number}"
            bill_lookup[key] = bill

    # Load all senate votes
    all_votes: list[dict] = []
    if senate_dir.exists():
        for vote_file in sorted(senate_dir.glob("*.json")):
            with open(vote_file) as f:
                all_votes.append(json.load(f))

    # Build member vote records
    senate_members = [m for m in members_data.get("members", []) if m.get("chamber") == "Senate"]

    count = 0
    for member in senate_members:
        bioguide_id = member["bioguideId"]
        print(f"  Building votes for {member.get('directOrderName', bioguide_id)}...")

        member_vote_list = []
        for vote in all_votes:
            # Find this member's vote
            member_vote = None
            for mv in vote.get("members", []):
                if mv.get("lis_member_id") == bioguide_id:
                    member_vote = mv
                    break
            if not member_vote:
                continue

            # Parse bill reference from document field
            doc = vote.get("document", "")
            bill_ref = _parse_bill_ref(doc)
            bill_info = bill_lookup.get(bill_ref, {}) if bill_ref else {}

            member_vote_list.append({
                "bill_number": doc,
                "bill_id": f"119-{bill_ref}" if bill_ref else None,
                "one_liner": bill_info.get("title", doc),
                "vote": member_vote.get("vote", ""),
                "date": vote.get("vote_date", ""),
                "result": vote.get("result", ""),
                "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                "chamber": "Senate",
                "cbo_deficit_impact": None,
            })

        # Compute stats
        yea = sum(1 for v in member_vote_list if v["vote"] == "Yea")
        nay = sum(1 for v in member_vote_list if v["vote"] == "Nay")
        not_voting = sum(1 for v in member_vote_list if v["vote"] == "Not Voting")
        total = len(member_vote_list)
        participation = round((yea + nay) / total * 100, 1) if total > 0 else 0

        policy_areas = sorted(set(v["policy_area"] for v in member_vote_list if v["policy_area"]))

        record = {
            "member_id": bioguide_id,
            "congress": 119,
            "stats": {
                "total_votes": total,
                "yea_count": yea,
                "nay_count": nay,
                "not_voting_count": not_voting,
                "participation_rate": participation,
            },
            "scorecard": [],
            "votes": sorted(member_vote_list, key=lambda v: v["date"], reverse=True),
            "policy_areas": policy_areas,
        }
        _atomic_write_json(member_votes_dir / f"{bioguide_id}.json", record)
        count += 1

    print(f"  Built voting records for {count} members")
    return count


def _parse_bill_ref(document: str) -> str | None:
    """Parse 'H.R. 1' into 'hr-1' or 'S. 100' into 's-100'."""
    doc = document.strip()
    if doc.startswith("H.R. "):
        return f"hr-{doc[5:]}"
    if doc.startswith("S. "):
        return f"s-{doc[3:]}"
    if doc.startswith("H.J.Res. "):
        return f"hjres-{doc[9:]}"
    if doc.startswith("S.J.Res. "):
        return f"sjres-{doc[9:]}"
    return None
```

Update `main()`:
```python
    # Step 5: Member voting records
    print("[5/5] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR)
```

Update metadata: `"member_votes_count": member_votes_count,`

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_sync.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add member voting record builder — cross-references votes with members"
```

---

## Phase 4: Integration and Cleanup

### Task 10: Seed initial data and run full test suite

**Files:**
- Create: `data/synced/.gitkeep`
- Modify: `.gitignore` (if needed — ensure `data/synced/` is NOT gitignored)
- Modify: `.dockerignore` (ensure `data/synced/` is NOT docker-ignored)

**Step 1: Create the data/synced directory with .gitkeep**

```bash
mkdir -p data/synced/votes/senate data/synced/votes/house data/synced/member_votes
touch data/synced/.gitkeep
```

**Step 2: Verify .dockerignore does NOT exclude data/synced/**

Check `.dockerignore` — if `data/cache/` is excluded (it should be), make sure `data/synced/` is NOT excluded. If needed, update the ignore pattern from `data/` to `data/cache/`.

**Step 3: Update Dockerfile to include data/synced/**

Add to `Dockerfile` after `COPY static/ static/`:
```dockerfile
COPY data/synced/ data/synced/
```

**Step 4: Run the full test suite**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/ -v`
Expected: ALL PASS

If any old tests fail because they still reference `_is_demo` or `mock_data`, fix them.

**Step 5: Commit**

```bash
git add data/synced/.gitkeep Dockerfile .dockerignore
git commit -m "feat: data sync architecture complete

- DataService reads pre-synced JSON files
- Routers simplified to single code path (no demo/live branching)
- sync.py fetches members, bills, votes, AI summaries
- Dockerfile updated to include synced data
- All tests passing"
```

---

### Task 11: Run sync script and verify the full flow

**Step 1: Run the sync script**

```bash
cd ~/Documents/Claude/Projects/clearvote
source .venv/bin/activate
python sync.py
```

Watch the output — it should:
- Fetch members for all 50 states + territories
- Fetch bills from the 119th Congress
- Fetch Senate votes
- Generate AI summaries (if ANTHROPIC_API_KEY is set)
- Build member voting records

**Step 2: Verify the output files**

```bash
ls -la data/synced/
cat data/synced/sync_metadata.json
ls data/synced/member_votes/ | head -20
ls data/synced/votes/senate/ | head -20
```

**Step 3: Start the app and test manually**

```bash
uvicorn app.main:app --reload
```

- Visit http://127.0.0.1:8000 — select any state, verify members load
- Click a member — verify voting record loads
- Browse bills — verify bill list loads
- Click a bill — verify AI summary loads

**Step 4: Run the full test suite one more time**

Run: `cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit the synced data**

```bash
git add data/synced/
git commit -m "sync: initial full data sync — all 50 states"
```

---

Plan complete and saved to `docs/plans/2026-03-07-data-sync-architecture.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open a new session with executing-plans, batch execution with checkpoints

Which approach?