import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- State Overview Endpoint ---

@pytest.mark.asyncio
async def test_state_overview_returns_correct_structure():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()

    assert "members" in data
    assert "aggregate" in data

    agg = data["aggregate"]
    assert "total_members" in agg
    assert "avg_participation" in agg
    assert "avg_support_rate" in agg
    assert "total_votes" in agg


@pytest.mark.asyncio
async def test_state_overview_member_data_shape():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()
    members = data["members"]

    assert len(members) == 2

    for member in members:
        assert "bioguideId" in member
        assert "participation_rate" in member
        assert "support_rate" in member
        assert "total_votes" in member
        assert "yea_count" in member
        assert "nay_count" in member
        assert "narrative_snippet" in member


@pytest.mark.asyncio
async def test_state_overview_aggregate_calculations():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()
    agg = data["aggregate"]

    assert agg["total_members"] == 2

    # S001217: participation=100, total_votes=2, yea=1, nay=1 -> support=50
    # D000032: participation=85, total_votes=3, yea=2, nay=1 -> support=67
    # avg_participation = round((100 + 85) / 2) = 92 (or 93 depending on rounding)
    assert agg["avg_participation"] in [92, 93]
    # avg_support = round((50 + 67) / 2) = 58 (or 59)
    assert agg["avg_support_rate"] in [58, 59]
    assert agg["total_votes"] == 5


@pytest.mark.asyncio
async def test_state_overview_strips_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()
    for member in data["members"]:
        assert "partyName" not in member
        assert "partyCode" not in member


@pytest.mark.asyncio
async def test_state_overview_invalid_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/INVALID/overview")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_state_overview_empty_state():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/CA/overview")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["aggregate"]["total_members"] == 0
    assert len(data["members"]) == 0


@pytest.mark.asyncio
async def test_state_overview_narrative_snippet():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()

    # S001217 has a narrative in fixtures; D000032 does not
    s001217 = next(m for m in data["members"] if m["bioguideId"] == "S001217")
    d000032 = next(m for m in data["members"] if m["bioguideId"] == "D000032")

    assert len(s001217["narrative_snippet"]) > 0
    assert d000032["narrative_snippet"] == ""


@pytest.mark.asyncio
async def test_state_page_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/state")
    assert response.status_code == 200
    assert "ClearVoting" in response.text
