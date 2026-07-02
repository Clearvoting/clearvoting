"""Tests for the homepage redesign: state counts, latest vote, bill plain-language
enrichment, party reveal, and the notify signup endpoint."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.limiter import limiter

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


async def _get(path):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    _clear_data_service_cache()
    return response


# --- Member counts ---

@pytest.mark.asyncio
async def test_member_counts():
    response = await _get("/api/members/counts")
    assert response.status_code == 200
    # Real synced members per state — fixtures hold FL x2, NY x1.
    assert response.json()["counts"] == {"FL": 2, "NY": 1}


# --- Latest vote ---

@pytest.mark.asyncio
async def test_latest_vote_picks_newest_bill_linked_passage():
    response = await _get("/api/votes/latest")
    assert response.status_code == 200
    data = response.json()
    # Newest fixture vote that maps to a held bill is the Senate's H.R. 1 passage.
    assert data["chamber"] == "Senate"
    assert data["bill"]["type"] == "hr"
    assert data["bill"]["number"] == 1
    assert data["bill"]["title"] == "One Big Beautiful Bill Act"
    assert data["counts"]["yeas"] == 51


# --- Bills plain-language enrichment ---

@pytest.mark.asyncio
async def test_bills_include_plain_language_fields():
    response = await _get("/api/bills")
    assert response.status_code == 200
    bills = response.json()["bills"]
    assert bills, "fixture should return bills"
    for bill in bills:
        assert "one_liner" in bill
        assert isinstance(bill["one_liner"], str)  # never null
        assert isinstance(bill["provisions"], list)
        assert isinstance(bill["issue_categories"], list)
    hr1 = next(b for b in bills if b["type"] == "HR" and str(b["number"]) == "1")
    assert hr1["issue_categories"] == ["Taxes", "Cost of Living"]


@pytest.mark.asyncio
async def test_summarized_only_excludes_bills_without_one_liner():
    response = await _get("/api/bills?summarized_only=true")
    assert response.status_code == 200
    bills = response.json()["bills"]
    # Every returned bill must carry a usable plain-language headline.
    assert all(b["one_liner"] for b in bills)


# --- Party reveal ---

@pytest.mark.asyncio
async def test_state_members_hide_party_by_default():
    response = await _get("/api/members/FL")
    assert response.status_code == 200
    for member in response.json()["members"]:
        assert "partyName" not in member


@pytest.mark.asyncio
async def test_state_members_show_party_when_requested():
    response = await _get("/api/members/FL?show_party=true")
    assert response.status_code == 200
    members = response.json()["members"]
    assert members
    assert all("partyName" in m for m in members)


# --- Notify signup ---

@pytest.fixture(autouse=True)
def _use_tmp_notify_file(tmp_path):
    tmp_file = tmp_path / "notify_signups.jsonl"
    unavailable_sheets = MagicMock()
    unavailable_sheets.is_available = False
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", unavailable_sheets):
        yield tmp_file


async def _post_notify(payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/notify", json=payload)


@pytest.mark.asyncio
async def test_notify_accepts_valid_email(_use_tmp_notify_file):
    response = await _post_notify({"email": "voter@example.com", "state": "OH"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    lines = _use_tmp_notify_file.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["email"] == "voter@example.com"
    assert entry["state"] == "OH"
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_notify_rejects_bad_email():
    response = await _post_notify({"email": "not-an-email"})
    assert response.status_code == 422
