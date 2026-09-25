"""Tests for the homepage redesign: state counts, latest vote, bill plain-language
enrichment, party reveal, and the notify signup endpoint."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.limiter import limiter
from app import render
from app.services.data_service import DataService

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
    # Real synced members per state — fixtures hold FL x2, NY x4, TX x1.
    assert response.json()["counts"] == {"FL": 2, "NY": 4, "TX": 1}


# --- Latest vote ---

def _bill_id(bill: dict) -> str:
    return f"{bill['congress']}-{str(bill['type']).lower()}-{bill['number']}"


@pytest.mark.asyncio
async def test_latest_vote_is_the_index_hero():
    index = json.loads((FIXTURES / "votes_index.json").read_text())
    held = {_bill_id(b) for b in json.loads((FIXTURES / "bills.json").read_text())["bills"]}
    # F02 rule recomputed from the fixture index: newest date, decisive first within a day,
    # vote number last; only roll calls whose document is a bill we hold.
    candidates = []
    for key, rc in index["roll_calls"].items():
        parsed = DataService._parse_bill_document(rc.get("document") or "")
        congress = int(key.split("/")[1].split("_")[0])
        if parsed and f"{congress}-{parsed[0]}-{parsed[1]}" in held:
            candidates.append(((rc["date"][:10], rc.get("class") == "D", int(key.rsplit("_", 1)[1])), key))
    expected = max(candidates)[1]
    assert index["latest"] == expected

    response = await _get("/api/votes/latest")
    assert response.status_code == 200
    data = response.json()
    rc = index["roll_calls"][expected]
    assert data["rc"] == expected
    assert data["chamber"] == ("Senate" if expected.startswith("senate/") else "House")
    assert data["date_iso"] == rc["date"][:10]
    assert data["date"] == render.format_date(rc["date"][:10])
    assert data["counts"] == rc["counts"]
    assert data["plain_question"] == rc["plain"]
    assert data["state_tallies"] == rc["tallies"]
    assert data["outcome"] == data["seal"] == render.result_phrase(rc, data["chamber"])
    parsed = DataService._parse_bill_document(rc["document"])
    assert (data["bill"]["type"], data["bill"]["number"]) == parsed
    bill_id = f"{data['bill']['congress']}-{parsed[0]}-{parsed[1]}"
    summary = json.loads((FIXTURES / "ai_summaries.json").read_text()).get(bill_id) or {}
    displayable = bool(summary) and summary.get("needs_review") is not True
    assert data["has_summary"] == bool(displayable and summary.get("one_liner"))
    assert data["one_liner"] == (summary["one_liner"] if data["has_summary"] else None)
    for row in data["covered"].values():
        assert set(row) == {"name", "state", "district", "chamber", "position", "relation"}
    assert '"party' not in response.text


# --- Bills plain-language enrichment ---

@pytest.mark.asyncio
async def test_bills_include_plain_language_fields():
    response = await _get("/api/bills?limit=50")
    assert response.status_code == 200
    bills = response.json()["bills"]
    assert bills, "fixture should return bills"
    summaries = json.loads((FIXTURES / "ai_summaries.json").read_text())
    for bill in bills:
        summary = summaries.get(_bill_id(bill)) or {}
        displayable = bool(summary) and summary.get("needs_review") is not True
        # Nullable: missing and withheld summaries both read None (spec §4.1 m5, §2.5 C)
        assert bill["one_liner"] == ((summary.get("one_liner") or None) if displayable else None)
        assert bill["issue_categories"] == ((summary.get("issue_categories") or []) if displayable else [])
        assert isinstance(bill["provisions"], list)
        assert "derived_status" in bill and bill["derived_status"]
        assert "activity_date" in bill


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
