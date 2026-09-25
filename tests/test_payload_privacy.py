"""Default payloads carry no party labels and no retired keys (spec §2.2 #10, §10 #9).

CHECKED_ENDPOINTS is the list of default GET paths both tests walk. Each consumer's rewrite
commit appends its endpoints to this list literal (§10.3: enabled per endpoint in that commit)."""
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.limiter import limiter
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
PARTY_LEAK = re.compile(r"Democratic|Republican|Independent|\[[RDI]-")
FORBIDDEN_KEYS = {"party", "partyName", "partyCode", "arguments", "direction", "scorecard", "participation_rate"}

CHECKED_ENDPOINTS = [
    "/api/districts/11570",
    "/api/districts/11201",
    "/api/districts/73949",
    "/api/districts/88430",
    "/api/members/S000148/page",
    "/api/members/G000602/page",
    # Home and the endpoints it reads (plan T3.3; spec §2.2 #10, §10 #9)
    "/api/bills",
    "/api/bills?limit=7",
    "/api/bills?summarized_only=true&limit=1",
    "/api/search/bills?q=act",
    "/api/votes/latest",
    "/api/members/CA",
    "/api/members/FL",
    "/api/members/NY",
    "/api/members/TX",
]


def _all_keys(obj) -> set:
    found: set = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.add(key)
            found |= _all_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            found |= _all_keys(item)
    return found


async def _get(path: str):
    from app.dependencies import get_data_service
    limiter.reset()
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(path)
    get_data_service.cache_clear()
    return response


@pytest.mark.asyncio
@pytest.mark.parametrize("path", CHECKED_ENDPOINTS)
async def test_default_payload_has_no_party_labels(path):
    response = await _get(path)
    assert response.status_code == 200
    assert not PARTY_LEAK.search(response.text)


@pytest.mark.asyncio
@pytest.mark.parametrize("path", CHECKED_ENDPOINTS)
async def test_default_payload_has_no_retired_keys(path):
    response = await _get(path)
    assert response.status_code == 200
    assert not _all_keys(response.json()) & FORBIDDEN_KEYS


@pytest.mark.asyncio
async def test_home_html_has_no_party_labels():
    """Plan T3.3: the server-rendered home (lead, card, Record) carries no party label."""
    response = await _get("/")
    assert response.status_code == 200
    assert not PARTY_LEAK.search(response.text)
