# ClearVote Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a public web app that shows how U.S. Congress members vote on bills, with plain-language AI-generated breakdowns and party affiliation hidden by default.

**Architecture:** FastAPI backend that proxies Congress.gov API (bills, members, House votes) and scrapes Senate.gov XML (Senate votes), with Claude API generating plain-language bill summaries. Pure HTML/CSS/JS frontend with state-based representative lookup, bill browser, and voting record display.

**Tech Stack:** Python 3.11+, FastAPI, httpx, Anthropic SDK, vanilla HTML/CSS/JS, flat-file JSON cache

**Version:** 1.0
**Created:** March 4, 2026
**Status:** Draft
**Design Doc:** [ClearVote Design](2026-03-04-clearvote-design.md)

---

## Executive Summary

ClearVote is a government transparency tool that presents congressional voting records without bias. Citizens can look up their representatives by state, see how they vote on bills, and read plain-language explanations of what each bill does — all without party labels shown by default. The app uses the official Congress.gov API for bills, members, and House votes, Senate.gov XML for Senate votes, and the Claude API to generate factual, adjective-free bill summaries.

### Scope

**In scope:**
- Representative lookup by state (senators) and state + district (House)
- Member profiles with voting records
- Bill detail pages with official + AI-generated plain-language summaries
- Impact category tags on bills
- Full roll call vote display
- Party affiliation toggle (hidden by default)
- Search/browse bills by keyword, topic, impact category
- Flat-file JSON caching of API responses

**Out of scope:**
- Zip code to congressional district lookup (future enhancement — requires geocoding API)
- Local/state government data (future expansion)
- User accounts or notifications
- Historical data before 117th Congress (can expand later)
- Real-time vote streaming

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Senate votes via XML scraping** | Congress.gov API only has House votes (beta). Senate publishes structured XML at predictable URLs — reliable and official. |
| **State selection instead of zip code** | Zip-to-district mapping requires geocoding API (complexity). State selection gives senators immediately; district can be entered manually for House reps. Good enough for MVP. |
| **Claude API for bill summaries** | Official CRS summaries exist but miss details relevant to working-class Americans. Claude can extract bill mechanisms in plain language with strict "no adjectives" prompting. Official summary always shown alongside for transparency. |
| **Cache-first architecture** | Congress data changes infrequently. Cache API responses as JSON files with configurable TTL to avoid rate limits and improve performance. |
| **Party hidden by default everywhere** | Core product differentiator. Toggle reveals party info only after user has seen the voting data on its merits. |

### References

- [ClearVote Design Doc](2026-03-04-clearvote-design.md)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  HTML/CSS/JS — state lookup, bill browse,        │
│  rep profiles, vote display, party toggle        │
└──────────────────────┬──────────────────────────┘
                       │ fetch() calls
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend                      │
│                                                  │
│  /api/members/{state}        → Member service    │
│  /api/members/{state}/{dist} → Member service    │
│  /api/member/{bioguideId}    → Member detail     │
│  /api/bills                  → Bill service      │
│  /api/bills/{congress}/{type}/{number}           │
│  /api/bills/{id}/summary     → AI summary svc    │
│  /api/votes/house/{congress}/{session}/{number}  │
│  /api/votes/senate/{congress}/{session}/{number} │
│  /api/search/bills           → Bill search       │
└───┬──────────────┬───────────────┬──────────────┘
    │              │               │
    ▼              ▼               ▼
┌────────┐  ┌───────────┐  ┌──────────────┐
│Congress│  │ Senate.gov │  │  Claude API  │
│.gov API│  │    XML     │  │  (Anthropic) │
│        │  │            │  │              │
│Members │  │Roll call   │  │Plain-language│
│Bills   │  │vote data   │  │bill summaries│
│H.Votes │  │            │  │              │
└────────┘  └───────────┘  └──────────────┘
    │              │               │
    └──────────────┴───────────────┘
                   │
            ┌──────▼──────┐
            │  JSON Cache  │
            │  data/cache/ │
            └─────────────┘
```

---

## Phase 1: Project Setup + Configuration

**Completion gate:** FastAPI app starts, serves a health check endpoint, project structure is in place with all dependencies installable.

### Task 1: Project scaffolding

**Files:**
- Create: `Projects/clearvote/requirements.txt`
- Create: `Projects/clearvote/app/__init__.py`
- Create: `Projects/clearvote/app/main.py`
- Create: `Projects/clearvote/app/config.py`
- Create: `Projects/clearvote/.env.example`
- Create: `Projects/clearvote/.gitignore`
- Test: `Projects/clearvote/tests/__init__.py`
- Test: `Projects/clearvote/tests/test_health.py`

**Step 1: Create project directory structure**

```bash
mkdir -p ~/Documents/Claude/Projects/clearvote/{app/{routers,services},tests,data/cache,static/{css,js},templates}
```

**Step 2: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
httpx==0.27.0
anthropic==0.40.0
python-dotenv==1.0.1
jinja2==3.1.4
pytest==8.3.0
pytest-asyncio==0.24.0
httpx[http2]==0.27.0
```

**Step 3: Write .env.example**

```
CONGRESS_API_KEY=your_congress_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CACHE_TTL_SECONDS=3600
```

**Step 4: Write .gitignore**

```
__pycache__/
*.pyc
.env
data/cache/
.venv/
```

**Step 5: Write config.py**

```python
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CONGRESS_API_KEY: str = os.getenv("CONGRESS_API_KEY", "")
CONGRESS_API_BASE: str = "https://api.congress.gov/v3"
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

SENATE_VOTE_BASE: str = "https://www.senate.gov/legislative/LIS/roll_call_votes"
```

**Step 6: Write main.py with health check**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="ClearVote", version="0.1.0")

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
```

**Step 7: Write the failing test**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
```

**Step 8: Run tests to verify they pass**

```bash
cd ~/Documents/Claude/Projects/clearvote && python -m pytest tests/test_health.py -v
```
Expected: PASS

**Step 9: Commit**

```bash
git init && git add -A && git commit -m "feat: project scaffolding with FastAPI health check"
```

---

## Phase 2: Congress.gov API Client + Caching Layer

**Completion gate:** Generic API client with file-based caching works. Can make cached requests to Congress.gov API.

### Task 2: Cache service

**Files:**
- Create: `app/services/cache.py`
- Test: `tests/test_cache.py`

**Step 1: Write the failing test**

```python
import pytest
import json
import time
from pathlib import Path
from app.services.cache import CacheService

@pytest.fixture
def cache_service(tmp_path):
    return CacheService(cache_dir=tmp_path, ttl_seconds=2)

def test_cache_miss_returns_none(cache_service):
    result = cache_service.get("nonexistent_key")
    assert result is None

def test_cache_set_and_get(cache_service):
    data = {"members": [{"name": "Test"}]}
    cache_service.set("test_key", data)
    result = cache_service.get("test_key")
    assert result == data

def test_cache_expires(cache_service):
    cache_service.set("expiring_key", {"data": True})
    time.sleep(3)
    result = cache_service.get("expiring_key")
    assert result is None
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_cache.py -v
```
Expected: FAIL — module not found

**Step 3: Write cache service**

```python
import json
import hashlib
import time
from pathlib import Path
from typing import Any
import tempfile
import os

class CacheService:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def get(self, key: str) -> Any | None:
        path = self._key_to_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                cached = json.load(f)
            if time.time() - cached["timestamp"] > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return cached["data"]
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, data: Any) -> None:
        path = self._key_to_path(key)
        payload = {"timestamp": time.time(), "data": data}
        fd, tmp_path = tempfile.mkstemp(dir=self.cache_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(payload, f)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_cache.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/cache.py tests/test_cache.py && git commit -m "feat: file-based cache service with TTL and atomic writes"
```

### Task 3: Congress API client

**Files:**
- Create: `app/services/congress_api.py`
- Test: `tests/test_congress_api.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.congress_api import CongressAPIClient

@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get.return_value = None
    return cache

@pytest.fixture
def client(mock_cache):
    return CongressAPIClient(api_key="test_key", cache=mock_cache)

@pytest.mark.asyncio
async def test_get_members_by_state(client, mock_cache):
    mock_response = {
        "members": [
            {"bioguideId": "T000001", "name": "Test Senator", "state": "FL"}
        ]
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_members_by_state("FL")
    assert len(result["members"]) == 1
    assert result["members"][0]["state"] == "FL"

@pytest.mark.asyncio
async def test_get_members_by_state_uses_cache(client, mock_cache):
    cached_data = {"members": [{"bioguideId": "C001", "name": "Cached"}]}
    mock_cache.get.return_value = cached_data
    result = await client.get_members_by_state("FL")
    assert result["members"][0]["name"] == "Cached"

@pytest.mark.asyncio
async def test_get_bill_detail(client):
    mock_response = {
        "bill": {"number": "1234", "title": "Test Bill", "congress": 119}
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_bill(119, "hr", 1234)
    assert result["bill"]["number"] == "1234"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_congress_api.py -v
```
Expected: FAIL

**Step 3: Write Congress API client**

```python
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

        async with httpx.AsyncClient() as client:
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
        params = {"offset": offset, "limit": limit}
        path = f"/bill/{congress}" if congress else "/bill"
        return await self._fetch(path, params)

    async def search_bills(self, query: str, congress: int | None = None, offset: int = 0, limit: int = 20) -> dict:
        params = {"offset": offset, "limit": limit}
        path = f"/bill/{congress}" if congress else "/bill"
        return await self._fetch(path, params)

    async def get_house_votes(self, congress: int, session: int) -> dict:
        return await self._fetch(f"/house-vote/{congress}/{session}")

    async def get_house_vote_detail(self, congress: int, session: int, vote_number: int) -> dict:
        return await self._fetch(f"/house-vote/{congress}/{session}/{vote_number}")

    async def get_house_vote_members(self, congress: int, session: int, vote_number: int) -> dict:
        return await self._fetch(f"/house-vote/{congress}/{session}/{vote_number}/members")
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_congress_api.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/congress_api.py tests/test_congress_api.py && git commit -m "feat: Congress.gov API client with caching"
```

---

## Phase 3: Senate Vote Scraper

**Completion gate:** Can fetch and parse Senate roll call vote XML into structured Python dicts.

### Task 4: Senate vote service

**Files:**
- Create: `app/services/senate_votes.py`
- Test: `tests/test_senate_votes.py`

**Step 1: Write the failing test**

```python
import pytest
from app.services.senate_votes import parse_senate_vote_xml

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<roll_call_vote>
  <congress>119</congress>
  <session>2</session>
  <vote_number>44</vote_number>
  <vote_date>March 2, 2026</vote_date>
  <vote_question_text>On Cloture on the Motion to Proceed</vote_question_text>
  <vote_document_text>H.R. 6644</vote_document_text>
  <vote_result_text>Agreed to</vote_result_text>
  <vote_title>A bill to increase the supply of housing in America</vote_title>
  <count>
    <yeas>84</yeas>
    <nays>6</nays>
    <present>1</present>
    <absent>9</absent>
  </count>
  <members>
    <member>
      <member_full>Alsobrooks (D-MD)</member_full>
      <first_name>Angela</first_name>
      <last_name>Alsobrooks</last_name>
      <party>D</party>
      <state>MD</state>
      <vote_cast>Yea</vote_cast>
      <lis_member_id>S428</lis_member_id>
    </member>
    <member>
      <member_full>Johnson (R-WI)</member_full>
      <first_name>Ron</first_name>
      <last_name>Johnson</last_name>
      <party>R</party>
      <state>WI</state>
      <vote_cast>Nay</vote_cast>
      <lis_member_id>S345</lis_member_id>
    </member>
  </members>
</roll_call_vote>
"""

def test_parse_senate_vote_xml():
    result = parse_senate_vote_xml(SAMPLE_XML)
    assert result["congress"] == 119
    assert result["session"] == 2
    assert result["vote_number"] == 44
    assert result["question"] == "On Cloture on the Motion to Proceed"
    assert result["result"] == "Agreed to"
    assert result["counts"]["yeas"] == 84
    assert result["counts"]["nays"] == 6
    assert len(result["members"]) == 2

def test_parse_member_votes():
    result = parse_senate_vote_xml(SAMPLE_XML)
    yea_member = result["members"][0]
    assert yea_member["last_name"] == "Alsobrooks"
    assert yea_member["party"] == "D"
    assert yea_member["state"] == "MD"
    assert yea_member["vote"] == "Yea"

    nay_member = result["members"][1]
    assert nay_member["vote"] == "Nay"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_senate_votes.py -v
```

**Step 3: Write Senate vote parser**

```python
import xml.etree.ElementTree as ET
import httpx
from app.services.cache import CacheService

def parse_senate_vote_xml(xml_string: str) -> dict:
    root = ET.fromstring(xml_string)

    counts_el = root.find("count")
    counts = {
        "yeas": int(counts_el.findtext("yeas", "0")),
        "nays": int(counts_el.findtext("nays", "0")),
        "present": int(counts_el.findtext("present", "0")),
        "absent": int(counts_el.findtext("absent", "0")),
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
        "document": root.findtext("vote_document_text", ""),
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
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

        result = parse_senate_vote_xml(response.text)
        self.cache.set(cache_key, result)
        return result
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_senate_votes.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/senate_votes.py tests/test_senate_votes.py && git commit -m "feat: Senate vote XML parser and fetch service"
```

---

## Phase 4: AI Bill Summary Service

**Completion gate:** Claude API generates plain-language, adjective-free bill summaries with impact category tags.

### Task 5: AI summary service

**Files:**
- Create: `app/services/ai_summary.py`
- Test: `tests/test_ai_summary.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_summary import AISummaryService, IMPACT_CATEGORIES

def test_impact_categories_defined():
    assert "Wages & Income" in IMPACT_CATEGORIES
    assert "Healthcare" in IMPACT_CATEGORIES
    assert "Housing" in IMPACT_CATEGORIES

def test_build_prompt():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1. The minimum wage shall be raised to $15."
    )
    assert "no adjectives" in prompt.lower() or "adjective" in prompt.lower()
    assert "Test Bill" in prompt
    assert "impact categories" in prompt.lower() or "Impact Categories" in prompt

@pytest.mark.asyncio
async def test_generate_summary_returns_expected_structure():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"provisions": ["Raises the federal minimum wage from $7.25 to $15.00 per hour"], "impact_categories": ["Wages & Income", "Small Business"]}')]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-1234",
            title="Minimum Wage Act",
            official_summary="A bill to raise the minimum wage.",
            bill_text_excerpt="The minimum wage shall be $15."
        )

    assert "provisions" in result
    assert "impact_categories" in result
    assert len(result["provisions"]) > 0
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_ai_summary.py -v
```

**Step 3: Write AI summary service**

```python
import json
import anthropic
from app.services.cache import CacheService

IMPACT_CATEGORIES = [
    "Wages & Income",
    "Healthcare",
    "Small Business",
    "Housing",
    "Education",
    "Taxes",
    "Military & Veterans",
    "Agriculture",
    "Environment",
    "Immigration",
    "Criminal Justice",
    "Technology",
    "Infrastructure",
    "Social Security & Medicare",
    "Government Operations",
]

SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your job is to extract factual information from bills and present it in plain language that any working American can understand.

STRICT RULES:
1. NO adjectives (no "sweeping", "controversial", "landmark", "modest", etc.)
2. NO value judgments (no "this would help/hurt", "beneficial", "harmful")
3. NO characterization of intent (no "aims to", "seeks to" — just state what the bill does)
4. NO political framing (no "progressive", "conservative", "bipartisan effort")
5. ONLY state mechanisms: what changes, what numbers change, what rules are created or removed
6. Use plain language a high school graduate would understand
7. Include specific numbers, dollar amounts, dates, and thresholds from the bill text

Output valid JSON only. No markdown, no commentary."""

class AISummaryService:
    def __init__(self, api_key: str, cache: CacheService):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cache = cache

    def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str) -> str:
        categories_str = ", ".join(IMPACT_CATEGORIES)
        return f"""Analyze this bill and return JSON with two fields:

1. "provisions": An array of 3-7 strings. Each string is one plain-language sentence describing a specific thing this bill would do. Focus on mechanisms: dollar amounts, thresholds, timelines, rules created or removed. No adjectives. No opinions.

2. "impact_categories": An array of strings from this list that apply to this bill: [{categories_str}]

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}

Return ONLY valid JSON. Example format:
{{"provisions": ["Changes X from $Y to $Z", "Creates a new program that does X"], "impact_categories": ["Wages & Income"]}}"""

    async def generate_summary(self, bill_id: str, title: str, official_summary: str, bill_text_excerpt: str) -> dict:
        cache_key = f"ai_summary:{bill_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        prompt = self._build_prompt(title, official_summary, bill_text_excerpt)

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text
        result = json.loads(raw_text)

        valid_categories = [c for c in result.get("impact_categories", []) if c in IMPACT_CATEGORIES]
        result["impact_categories"] = valid_categories

        self.cache.set(cache_key, result)
        return result
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_ai_summary.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/ai_summary.py tests/test_ai_summary.py && git commit -m "feat: AI bill summary service with strict no-bias prompting"
```

---

## Phase 5: API Routers

**Completion gate:** All FastAPI endpoints return data (mocked in tests). Members, bills, votes, and search endpoints functional.

### Task 6: Member router

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/members.py`
- Create: `app/dependencies.py`
- Test: `tests/test_members_router.py`

**Step 1: Write dependencies.py (service factory)**

```python
from functools import lru_cache
from app.config import CONGRESS_API_KEY, ANTHROPIC_API_KEY, CACHE_DIR, CACHE_TTL_SECONDS
from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService
from app.services.ai_summary import AISummaryService

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

**Step 2: Write member router**

```python
from fastapi import APIRouter, HTTPException
from app.dependencies import get_congress_client

router = APIRouter(prefix="/api/members", tags=["members"])

@router.get("/{state_code}")
async def get_members_by_state(state_code: str):
    state_code = state_code.upper()
    if len(state_code) != 2:
        raise HTTPException(status_code=400, detail="State code must be 2 letters")
    client = get_congress_client()
    try:
        data = await client.get_members_by_state(state_code)
        return _strip_party(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Congress API error: {str(e)}")

@router.get("/{state_code}/{district}")
async def get_members_by_district(state_code: str, district: int):
    state_code = state_code.upper()
    client = get_congress_client()
    try:
        data = await client.get_members_by_district(state_code, district)
        return _strip_party(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Congress API error: {str(e)}")

@router.get("/detail/{bioguide_id}")
async def get_member_detail(bioguide_id: str, show_party: bool = False):
    client = get_congress_client()
    try:
        data = await client.get_member(bioguide_id)
        if not show_party:
            data = _strip_party(data)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Congress API error: {str(e)}")

def _strip_party(data: dict) -> dict:
    """Remove party information from member data for default display."""
    import copy
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

**Step 3: Write test**

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_members_by_state():
    mock_data = {
        "members": [
            {"bioguideId": "T001", "name": "Test Senator", "state": "FL", "partyName": "Democrat"}
        ]
    }
    with patch("app.routers.members.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_members_by_state = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL")

    assert response.status_code == 200
    data = response.json()
    # Party info should be stripped by default
    for member in data.get("members", []):
        assert "partyName" not in member

@pytest.mark.asyncio
async def test_invalid_state_code():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/INVALID")
    assert response.status_code == 400
```

**Step 4: Register router in main.py — add import and include**

```python
from app.routers.members import router as members_router
app.include_router(members_router)
```

**Step 5: Run tests**

```bash
python -m pytest tests/test_members_router.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add app/routers/ app/dependencies.py tests/test_members_router.py && git commit -m "feat: member router with party stripping by default"
```

### Task 7: Bills router

**Files:**
- Create: `app/routers/bills.py`
- Test: `tests/test_bills_router.py`

**Step 1: Write bills router**

```python
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client, get_ai_summary_service

router = APIRouter(prefix="/api/bills", tags=["bills"])

@router.get("")
async def list_bills(
    congress: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    client = get_congress_client()
    try:
        return await client.get_bills(congress=congress, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int, bill_type: str, bill_number: int):
    client = get_congress_client()
    try:
        bill = await client.get_bill(congress, bill_type.lower(), bill_number)
        subjects = await client.get_bill_subjects(congress, bill_type.lower(), bill_number)
        bill["subjects"] = subjects
        return bill
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
async def get_ai_summary(congress: int, bill_type: str, bill_number: int):
    congress_client = get_congress_client()
    ai_service = get_ai_summary_service()
    try:
        bill_data = await congress_client.get_bill(congress, bill_type.lower(), bill_number)
        summary_data = await congress_client.get_bill_summary(congress, bill_type.lower(), bill_number)
        text_data = await congress_client.get_bill_text(congress, bill_type.lower(), bill_number)

        bill = bill_data.get("bill", {})
        title = bill.get("title", "")

        summaries = summary_data.get("summaries", [])
        official_summary = summaries[0].get("text", "") if summaries else ""

        text_versions = text_data.get("textVersions", [])
        bill_text_url = ""
        if text_versions:
            formats = text_versions[0].get("formats", [])
            for fmt in formats:
                if fmt.get("type") == "Formatted Text":
                    bill_text_url = fmt.get("url", "")
                    break

        bill_text_excerpt = ""
        if bill_text_url:
            import httpx
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(bill_text_url)
                if resp.status_code == 200:
                    bill_text_excerpt = resp.text[:5000]

        bill_id = f"{congress}-{bill_type}-{bill_number}"
        result = await ai_service.generate_summary(
            bill_id=bill_id,
            title=title,
            official_summary=official_summary,
            bill_text_excerpt=bill_text_excerpt,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
```

**Step 2: Write test**

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_list_bills():
    mock_data = {"bills": [{"number": "1", "title": "Test"}]}
    with patch("app.routers.bills.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_bills = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_bill_detail():
    mock_bill = {"bill": {"number": "1234", "title": "Test", "congress": 119}}
    mock_subjects = {"subjects": []}
    with patch("app.routers.bills.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_bill = AsyncMock(return_value=mock_bill)
        mock_client.get_bill_subjects = AsyncMock(return_value=mock_subjects)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hr/1234")
    assert response.status_code == 200
    assert response.json()["bill"]["number"] == "1234"
```

**Step 3: Register router in main.py**

```python
from app.routers.bills import router as bills_router
app.include_router(bills_router)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_bills_router.py -v
```

**Step 5: Commit**

```bash
git add app/routers/bills.py tests/test_bills_router.py && git commit -m "feat: bills router with AI summary endpoint"
```

### Task 8: Votes router

**Files:**
- Create: `app/routers/votes.py`
- Test: `tests/test_votes_router.py`

**Step 1: Write votes router**

```python
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client, get_senate_vote_service

router = APIRouter(prefix="/api/votes", tags=["votes"])

@router.get("/house/{congress}/{session}")
async def list_house_votes(congress: int, session: int):
    client = get_congress_client()
    try:
        return await client.get_house_votes(congress, session)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/house/{congress}/{session}/{vote_number}")
async def get_house_vote(congress: int, session: int, vote_number: int, show_party: bool = False):
    client = get_congress_client()
    try:
        vote = await client.get_house_vote_detail(congress, session, vote_number)
        members = await client.get_house_vote_members(congress, session, vote_number)
        if not show_party:
            members = _strip_party_from_votes(members)
        return {"vote": vote, "members": members}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/senate/{congress}/{session}/{vote_number}")
async def get_senate_vote(congress: int, session: int, vote_number: int, show_party: bool = False):
    service = get_senate_vote_service()
    try:
        data = await service.get_vote(congress, session, vote_number)
        if not show_party:
            for member in data.get("members", []):
                member.pop("party", None)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

def _strip_party_from_votes(data: dict) -> dict:
    import copy
    stripped = copy.deepcopy(data)
    if "members" in stripped:
        for member in stripped["members"]:
            for key in ["partyName", "party", "partyCode"]:
                member.pop(key, None)
    return stripped
```

**Step 2: Write test**

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_senate_vote():
    mock_data = {
        "congress": 119, "session": 2, "vote_number": 44,
        "question": "On Cloture", "result": "Agreed to",
        "counts": {"yeas": 84, "nays": 6, "present": 1, "absent": 9},
        "members": [
            {"first_name": "Test", "last_name": "Senator", "party": "D", "state": "FL", "vote": "Yea"}
        ],
    }
    with patch("app.routers.votes.get_senate_vote_service") as mock_get:
        mock_service = MagicMock()
        mock_service.get_vote = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/2/44")

    assert response.status_code == 200
    data = response.json()
    # Party should be stripped by default
    for member in data["members"]:
        assert "party" not in member
```

**Step 3: Register router in main.py**

```python
from app.routers.votes import router as votes_router
app.include_router(votes_router)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_votes_router.py -v
```

**Step 5: Commit**

```bash
git add app/routers/votes.py tests/test_votes_router.py && git commit -m "feat: votes router for House and Senate with party toggle"
```

---

## Phase 6: Frontend — Landing Page + State Lookup

**Completion gate:** Landing page loads, user can select a state and see their representatives (names, photos, chamber). Party info hidden.

### Task 9: HTML landing page

**Files:**
- Create: `static/index.html`
- Create: `static/css/styles.css`
- Create: `static/js/app.js`
- Modify: `app/main.py` (serve index.html)

**Step 1: Update main.py to serve the frontend**

Add to main.py:
```python
from fastapi.responses import FileResponse

@app.get("/")
async def serve_index():
    return FileResponse(str(static_dir / "index.html"))
```

**Step 2: Write index.html**

The landing page with:
- ClearVote header/logo
- Tagline: "See how your representatives vote. Facts only."
- State selection dropdown (all 50 states + DC + territories)
- Optional district number input
- "Find My Representatives" button
- Results area that shows member cards
- Search bar for bills
- Recent activity feed (latest votes)
- Footer with data source attribution

Key HTML structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClearVote — See How Your Representatives Vote</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <header class="site-header">
        <h1 class="logo">ClearVote</h1>
        <nav>
            <a href="/">Home</a>
            <a href="#browse">Browse Bills</a>
        </nav>
    </header>

    <main>
        <section class="hero">
            <h2>See how your representatives vote.</h2>
            <p>Facts only. No opinions. No spin.</p>
        </section>

        <section class="lookup">
            <!-- State dropdown, district input, submit button -->
        </section>

        <section id="results" class="results" hidden>
            <!-- Member cards rendered by JS -->
        </section>

        <section id="browse" class="browse">
            <!-- Bill search and recent activity -->
        </section>
    </main>

    <footer>
        <p>Data from <a href="https://congress.gov">Congress.gov</a> and <a href="https://senate.gov">Senate.gov</a>.</p>
        <p>ClearVote does not express opinions on legislation or representatives.</p>
    </footer>

    <script src="/static/js/app.js"></script>
</body>
</html>
```

**Step 3: Write styles.css**

Dark theme with midnight blue + gold palette. CSS custom properties for theming. Mobile-first responsive layout. Neutral colors for vote displays (no red/green).

Key design tokens:
```css
:root {
    --bg-primary: #0C1B33;
    --bg-secondary: #132744;
    --bg-card: #1A3055;
    --text-primary: #E8E0D4;
    --text-secondary: #B0A898;
    --accent-gold: #D4A853;
    --accent-gold-dim: #A8863F;
    --vote-yea: #5B8A72;
    --vote-nay: #8A5B5B;
    --vote-absent: #6B6B6B;
    --vote-present: #5B6F8A;
    --border: #2A4060;
    --font-body: 'Inter', system-ui, sans-serif;
    --font-heading: 'Playfair Display', serif;
}
```

**Step 4: Write app.js**

Core functionality:
- State dropdown population
- Fetch members by state (and optionally district)
- Render member cards (name, photo, state, chamber — NO party)
- Click member card → navigate to member profile page
- Bill search input → fetch and display results
- Party toggle button (hidden by default, reveals on click)

**Step 5: Run the app and verify manually**

```bash
cd ~/Documents/Claude/Projects/clearvote && uvicorn app.main:app --reload
```

**Step 6: Commit**

```bash
git add static/ && git commit -m "feat: landing page with state lookup and member cards"
```

---

## Phase 7: Frontend — Member Profile + Voting Record

**Completion gate:** Clicking a member shows their profile page with full voting record. Party toggle works.

### Task 10: Member profile page

**Files:**
- Create: `static/member.html`
- Create: `static/js/member.js`

**Step 1: Write member.html**

Profile page loaded via `/member.html?id={bioguideId}`. Shows:
- Member name, photo, state, district/chamber
- Party toggle button (with explanatory text: "See results first. Then reveal party affiliations.")
- Voting record table: Date | Bill | Vote | Result
- Each bill title links to bill detail page
- Votes shown as neutral-colored labels (Yea/Nay/Not Voting/Present)

**Step 2: Write member.js**

- Parse bioguide ID from URL params
- Fetch member detail from `/api/members/detail/{id}`
- Fetch their sponsored legislation
- Render profile and voting record
- Party toggle: button click adds `show_party=true` param to API calls, re-renders with party info
- Include a brief message before toggle: "You're viewing votes without party labels. Want to see party affiliations?"

**Step 3: Update main.py to serve member page**

```python
@app.get("/member")
async def serve_member():
    return FileResponse(str(static_dir / "member.html"))
```

**Step 4: Commit**

```bash
git add static/member.html static/js/member.js && git commit -m "feat: member profile page with voting record and party toggle"
```

---

## Phase 8: Frontend — Bill Detail Page

**Completion gate:** Bill detail page shows official summary, AI-generated plain-language breakdown, impact tags, and full roll call vote.

### Task 11: Bill detail page

**Files:**
- Create: `static/bill.html`
- Create: `static/js/bill.js`

**Step 1: Write bill.html**

Bill page loaded via `/bill.html?congress={N}&type={type}&number={num}`. Shows:
- Bill title and number
- Status indicator (introduced, passed House, passed Senate, signed into law, etc.)
- Official Congress summary (collapsible, shown by default)
- "What This Bill Does" section — AI-generated provisions (loaded async, with loading spinner)
- Impact category tags (pill-shaped labels)
- "How They Voted" section — roll call table
  - Columns: Name | State | Vote
  - Party column hidden by default, toggle button to reveal
  - Sort by vote (Yea first, then Nay, then Not Voting)
  - Vote counts summary bar (neutral colors)
- Link back to source on Congress.gov

**Step 2: Write bill.js**

- Parse bill params from URL
- Fetch bill detail from `/api/bills/{congress}/{type}/{number}`
- Fetch AI summary from `/api/bills/{congress}/{type}/{number}/ai-summary` (async, with loading state)
- Render all sections
- Party toggle on roll call table
- Link member names to their profile pages

**Step 3: Update main.py**

```python
@app.get("/bill")
async def serve_bill():
    return FileResponse(str(static_dir / "bill.html"))
```

**Step 4: Commit**

```bash
git add static/bill.html static/js/bill.js && git commit -m "feat: bill detail page with AI summary and roll call display"
```

---

## Phase 9: Frontend — Search and Browse

**Completion gate:** Users can search bills by keyword and browse by impact category. Recent activity feed works.

### Task 12: Search and browse functionality

**Files:**
- Create: `app/routers/search.py`
- Modify: `static/js/app.js` (add search + browse logic)
- Modify: `static/index.html` (add browse section)
- Test: `tests/test_search_router.py`

**Step 1: Write search router**

```python
from fastapi import APIRouter, Query
from app.dependencies import get_congress_client

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/bills")
async def search_bills(
    q: str = Query(..., min_length=1),
    congress: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    client = get_congress_client()
    return await client.search_bills(q, congress=congress, offset=offset, limit=limit)
```

**Step 2: Add browse-by-category to the landing page**

Impact category grid on the landing page. Each category is a clickable card that filters bills by that policy area/subject.

**Step 3: Add recent activity feed**

Fetch latest bills with actions and display on landing page as a simple list with date + bill title + latest action text.

**Step 4: Register search router in main.py**

**Step 5: Write test**

**Step 6: Commit**

```bash
git add app/routers/search.py static/ tests/test_search_router.py && git commit -m "feat: search and browse functionality with impact categories"
```

---

## Phase 10: Integration, Polish, and Mobile

**Completion gate:** All pages work end-to-end. Mobile responsive. Error states handled. Data source attribution present.

### Task 13: Integration and error handling

**Files:**
- Modify: All frontend JS files (error states, loading states)
- Modify: `static/css/styles.css` (mobile responsive, polish)

**Step 1: Add error states to all pages**

- API failure: "Unable to load data. Congress.gov may be temporarily unavailable."
- No results: "No representatives found for this state/district."
- AI summary loading: spinner + "Generating plain-language summary..."
- AI summary failure: graceful fallback to official summary only

**Step 2: Mobile responsive design**

- Hamburger menu on mobile
- Stack cards vertically
- Roll call table → card layout on small screens
- Touch-friendly tap targets (44px minimum)

**Step 3: Data source attribution**

- Footer on every page: "Data sourced from Congress.gov and Senate.gov"
- Each bill page: direct link to the bill on Congress.gov
- AI summary disclaimer: "This summary was generated by AI to present bill provisions in plain language. See the official summary above for the authoritative version."

**Step 4: Accessibility**

- Skip links
- ARIA labels on interactive elements
- Keyboard navigation for toggles and cards
- Sufficient color contrast (verify against WCAG AA)
- `prefers-reduced-motion` support

**Step 5: Full manual test**

1. Start app: `uvicorn app.main:app --reload`
2. Open browser to `http://localhost:8000`
3. Select a state → verify reps load without party info
4. Click party toggle → verify party info appears
5. Click a member → verify profile page with votes
6. Click a bill → verify detail page with AI summary
7. Search for a bill → verify results
8. Test on mobile viewport

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: integration polish — error handling, mobile responsive, accessibility"
```

---

## Files Touched

| File | Change |
|------|--------|
| `app/main.py` | FastAPI app, route mounting, static file serving |
| `app/config.py` | Configuration from env vars |
| `app/dependencies.py` | Service factory (cache, API client, AI service) |
| `app/routers/members.py` | Member lookup endpoints with party stripping |
| `app/routers/bills.py` | Bill detail and AI summary endpoints |
| `app/routers/votes.py` | House and Senate vote endpoints |
| `app/routers/search.py` | Bill search endpoint |
| `app/services/cache.py` | File-based JSON cache with TTL |
| `app/services/congress_api.py` | Congress.gov API client |
| `app/services/senate_votes.py` | Senate XML vote parser |
| `app/services/ai_summary.py` | Claude API bill summary generator |
| `static/index.html` | Landing page |
| `static/member.html` | Member profile page |
| `static/bill.html` | Bill detail page |
| `static/css/styles.css` | Full stylesheet (dark theme) |
| `static/js/app.js` | Landing page logic |
| `static/js/member.js` | Member profile logic |
| `static/js/bill.js` | Bill detail logic |

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_cache.py` | Cache set/get/expiry with atomic writes |
| Unit | `test_congress_api.py` | API client methods with mocked responses and cache |
| Unit | `test_senate_votes.py` | XML parsing of Senate roll call votes |
| Unit | `test_ai_summary.py` | AI prompt construction and response parsing |
| Integration | `test_health.py` | App starts and health endpoint responds |
| Integration | `test_members_router.py` | Member endpoints with party stripping |
| Integration | `test_bills_router.py` | Bill list and detail endpoints |
| Integration | `test_votes_router.py` | Vote endpoints with party toggle |
| Integration | `test_search_router.py` | Search endpoint |

## Not In Scope

- **Zip code → district lookup** — requires geocoding API integration, planned as future enhancement
- **Local/state government** — architecture supports it, but no data source integration in v1
- **User accounts** — no login, no saved preferences, fully public
- **Real-time vote streaming** — cache-based approach is sufficient for MVP
- **Historical data before 117th Congress** — can be expanded later
- **Push notifications** — future feature

## Provenance

This plan implements the design documented in [ClearVote Design Doc](2026-03-04-clearvote-design.md), which was collaboratively developed on March 4, 2026.
