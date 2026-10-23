import json
import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.limiter import limiter

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    """Patch data dir to use test fixtures and reset the DataService singleton."""
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- Members Router ---

@pytest.mark.asyncio
async def test_get_member_detail_strips_party_by_default():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/detail/S001217")

    _clear_data_service_cache()
    data = response.json()
    assert "partyName" not in data.get("member", {})
    assert "partyCode" not in data.get("member", {})


@pytest.mark.asyncio
async def test_get_member_detail_shows_party_when_requested():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/detail/S001217?show_party=true")

    _clear_data_service_cache()
    data = response.json()
    assert data["member"]["partyName"] == "Republican"


@pytest.mark.asyncio
async def test_member_summary_endpoint_is_deleted():
    """Member narratives are withdrawn (spec §2.5 A). No route matches the path any more."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/summary")

    _clear_data_service_cache()
    assert response.status_code == 404
    assert "narrative" not in response.text


# --- Bills Router ---

@pytest.mark.asyncio
async def test_list_bills():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    fixture_bills = json.loads((FIXTURES / "bills.json").read_text())["bills"]
    # Default page size is 20; the real-data fixtures hold more bills than that.
    assert len(data["bills"]) == min(len(fixture_bills), 20)


@pytest.mark.asyncio
async def test_list_bills_congress_filter():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            match = await client.get("/api/bills?congress=119")
            no_match = await client.get("/api/bills?congress=116")

    _clear_data_service_cache()
    fixture_bills = json.loads((FIXTURES / "bills.json").read_text())["bills"]
    in_119 = [b for b in fixture_bills if b["congress"] == 119]
    assert match.status_code == 200
    assert len(match.json()["bills"]) == min(len(in_119), 20)
    assert all(b["congress"] == 119 for b in match.json()["bills"])
    assert no_match.status_code == 200
    assert no_match.json()["bills"] == []


@pytest.mark.asyncio
async def test_list_bills_newest_activity_first_with_status():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills?limit=50")

    _clear_data_service_cache()
    assert response.status_code == 200
    bills = response.json()["bills"]
    dates = [b["activity_date"] or "" for b in bills]
    assert dates == sorted(dates, reverse=True)
    for bill in bills:
        assert bill["derived_status"]
        assert bill["one_liner"] is None or (isinstance(bill["one_liner"], str) and bill["one_liner"])


@pytest.mark.asyncio
async def test_latest_vote_extended_payload_keeps_old_keys_and_hides_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/latest")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    # Old app.js reads these (spec §10.3 commit 1: additive only)
    assert {"chamber", "date", "document", "result", "counts", "bill"} <= set(data)
    assert {"congress", "type", "number", "title"} <= set(data["bill"])
    # New card fields (spec §10 #11)
    assert {"one_liner", "has_summary", "plain_question", "outcome", "state_tallies", "covered"} <= set(data)
    assert '"party' not in json.dumps(data)


@pytest.mark.asyncio
async def test_search_tolerates_bills_without_a_summary():
    # one_liner is None for unsummarized/withheld bills; search must not call .lower() on it
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/search/bills?q=zzzz-no-such-bill")

    _clear_data_service_cache()
    assert response.status_code == 200
    assert response.json() == {"bills": [], "total": 0}


@pytest.mark.asyncio
async def test_get_bill_detail():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hr/1")

    _clear_data_service_cache()
    assert response.status_code == 200
    assert response.json()["bill"]["title"] == "One Big Beautiful Bill Act"


@pytest.mark.asyncio
async def test_get_bill_detail_not_found():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hr/999999")

    _clear_data_service_cache()
    assert response.status_code == 404


# --- Votes Router ---

@pytest.mark.asyncio
async def test_get_senate_vote_strips_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/1/372")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    for member in data["members"]:
        assert "party" not in member


@pytest.mark.asyncio
async def test_get_senate_vote_shows_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/1/372?show_party=true")

    _clear_data_service_cache()
    data = response.json()
    assert data["members"][0]["party"] == "R"


@pytest.mark.asyncio
async def test_get_house_vote_strips_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/house/119/1/99")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["vote_number"] == 99
    for member in data["members"]:
        assert "party" not in member


@pytest.mark.asyncio
async def test_get_house_vote_shows_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/house/119/1/99?show_party=true")

    _clear_data_service_cache()
    data = response.json()
    assert data["members"][0]["party"] == "R"


@pytest.mark.asyncio
async def test_get_house_vote_not_found():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/house/119/1/999")

    _clear_data_service_cache()
    assert response.status_code == 404


# --- Search Router ---

@pytest.mark.asyncio
async def test_search_bills_congress_filter():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            match = await client.get("/api/search/bills?q=beautiful&congress=119")
            no_match = await client.get("/api/search/bills?q=beautiful&congress=118")

    _clear_data_service_cache()
    assert match.status_code == 200
    assert match.json()["total"] == 1
    assert no_match.status_code == 200
    assert no_match.json()["bills"] == []
    assert no_match.json()["total"] == 0


# --- Bill detail allowlist (plan T7.4, spec §10 #9) ---

async def _get_json(path: str):
    limiter.reset()
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    _clear_data_service_cache()
    return response


@pytest.mark.asyncio
async def test_bill_detail_sponsor_has_built_name_and_no_party():
    response = await _get_json("/api/bills/119/hr/1")
    assert response.status_code == 200
    sponsor = response.json()["bill"]["sponsors"][0]
    assert "party" not in sponsor
    assert "[" not in sponsor["fullName"]


# --- Retired routes (F016): no page called them, so they are gone, not just unlinked ---

RETIRED_PATHS = [
    "/api/members/S000148/votes",
    "/api/members/S000148/votes?group=bill",
    "/api/members/S000148/donations",
    "/api/members/S000148/sponsored",
    "/api/members/counts",
    "/api/members/FL",
    "/api/members/FL/19",
    "/api/bills/119/hr/1/ai-summary",
    "/api/bills/119/hjres/20/votes",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", RETIRED_PATHS)
async def test_retired_api_paths_are_404(path):
    response = await _get_json(path)
    assert response.status_code == 404
