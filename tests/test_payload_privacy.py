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
FORBIDDEN_KEYS = {"party", "partyName", "partyCode", "arguments", "direction", "scorecard", "participation_rate",
                  "narrative", "issue_scorecard"}

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
    # Delegation (plan T4.2; spec §10 #7, §10 #9)
    "/api/members/NY/overview",
    # Member page and member payloads (plan T6.3; spec §10 #9)
    "/api/members/S000148/votes",
    "/api/members/S000148/votes?group=bill",
    "/api/members/S001217/votes",
    "/api/members/detail/S000148",
    "/api/members/G000602/page?page=2",
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
    assert not any(key.startswith("cbo_") for key in _all_keys(response.json()))


@pytest.mark.asyncio
async def test_home_html_has_no_party_labels():
    """Plan T3.3: the server-rendered home (lead, card, Record) carries no party label."""
    response = await _get("/")
    assert response.status_code == 200
    assert not PARTY_LEAK.search(response.text)


# --- Delegation page and overview (plan T4.2): party-free by default (§2.2 #10, §10 #9) ---

_STATE_FIXTURES = Path(__file__).parent / "fixtures" / "synced"
_STATE_PARTY_WORDS = re.compile(r"Democratic|Republican|Independent|\[[RDI]-")


async def _state_privacy_get(path: str):
    from app.dependencies import get_data_service
    with patch("app.dependencies.get_data_dir", return_value=_STATE_FIXTURES):
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    get_data_service.cache_clear()
    return response


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/state?code=NY", "/state?code=NY&district=4", "/state?code=NY&zip=11201",
    "/state?code=FL", "/state?code=TX&zip=73949", "/state?zip=44101", "/state",
])
async def test_state_html_has_no_party_labels(path):
    response = await _state_privacy_get(path)
    assert response.status_code == 200
    assert not _STATE_PARTY_WORDS.search(response.text)
    assert response.text.count('<span class="party"></span>') == response.text.count("data-bioguide=")


@pytest.mark.asyncio
async def test_overview_reveals_party_only_on_request():
    default = await _state_privacy_get("/api/members/NY/overview")
    assert not _STATE_PARTY_WORDS.search(default.text)
    assert '"partyName"' not in default.text
    revealed = (await _state_privacy_get("/api/members/NY/overview?show_party=true")).json()
    assert any(m.get("partyName") for m in revealed["senators"] + revealed["house"])


# --- Member page and member payloads (plan T6.3) ---

@pytest.mark.asyncio
@pytest.mark.parametrize("member_id", ["S000148", "G000602", "S001217"])
async def test_member_html_has_no_party_labels_by_default(member_id):
    response = await _get(f"/member?id={member_id}")
    assert response.status_code == 200
    assert not PARTY_LEAK.search(response.text)


@pytest.mark.asyncio
async def test_member_votes_mask_speaker_candidates_by_default():
    first = await _get("/api/members/G000602/votes?limit=1")
    total = first.json()["total_count"]
    tail = await _get(f"/api/members/G000602/votes?limit=50&offset={max(0, total - 50)}")
    assert "Jeffries" not in tail.text and "Johnson (LA)" not in tail.text
    speaker = [v for v in tail.json()["votes"] if v["date"].startswith("2025-01-03") and v["vote"] == "Voted"]
    assert speaker and speaker[0]["result"] == "Speaker elected"


@pytest.mark.asyncio
async def test_member_page_payload_never_names_the_speaker_candidate():
    first = await _get("/api/members/G000602/page")
    last = await _get(f"/api/members/G000602/page?page={first.json()['record']['pages']}")
    assert last.status_code == 200
    assert "Jeffries" not in last.text and "Johnson (LA)" not in last.text


@pytest.mark.asyncio
async def test_speaker_pick_and_party_only_with_show_party():
    default = await _get("/api/members/detail/G000602")
    assert "speaker_votes" not in default.json()
    assert "Jeffries" not in default.text
    revealed = await _get("/api/members/detail/G000602?show_party=true")
    assert revealed.json()["member"]["partyName"] == "Democratic"
    assert revealed.json()["speaker_votes"]["house/119_1_00002"] == "Jeffries"
