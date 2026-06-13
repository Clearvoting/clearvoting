import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    """Patch data dir to use test fixtures and reset the DataService singleton."""
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- Members Router ---

@pytest.mark.asyncio
async def test_get_members_by_state():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 2
    for member in data.get("members", []):
        assert "partyName" not in member


@pytest.mark.asyncio
async def test_invalid_state_code():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/INVALID")
    assert response.status_code == 400


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
async def test_get_member_summary():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/summary")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == "S001217"
    assert "stats" in data
    assert "top_policy_areas" in data


@pytest.mark.asyncio
async def test_get_member_summary_not_found():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/X999999/summary")

    _clear_data_service_cache()
    assert response.status_code == 404


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
    assert len(data["bills"]) == 3


@pytest.mark.asyncio
async def test_list_bills_congress_filter():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            match = await client.get("/api/bills?congress=119")
            no_match = await client.get("/api/bills?congress=118")

    _clear_data_service_cache()
    assert match.status_code == 200
    assert len(match.json()["bills"]) == 3
    assert no_match.status_code == 200
    assert no_match.json()["bills"] == []


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


@pytest.mark.asyncio
async def test_get_bill_votes_includes_house():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hjres/20/votes")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert len(data["senate"]) == 1
    assert len(data["house"]) == 1
    # Vote refs are summary-only — member positions come from /api/votes/senate
    for vote in data["senate"] + data["house"]:
        assert "members" not in vote


@pytest.mark.asyncio
async def test_get_bill_votes_wrong_congress_returns_empty():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/117/hjres/20/votes")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["senate"] == []
    assert data["house"] == []


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
            match = await client.get("/api/search/bills?q=energy&congress=119")
            no_match = await client.get("/api/search/bills?q=energy&congress=118")

    _clear_data_service_cache()
    assert match.status_code == 200
    assert match.json()["total"] == 1
    assert no_match.status_code == 200
    assert no_match.json()["bills"] == []
    assert no_match.json()["total"] == 0
