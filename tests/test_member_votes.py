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


@pytest.mark.asyncio
async def test_get_member_votes_from_data_service():
    """DataService returns voting data for known member."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/votes")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == "S001217"
    assert "stats" in data
    assert data["stats"]["total_votes"] > 0
    assert data["stats"]["participation_rate"] > 0
    assert "votes" in data
    assert len(data["votes"]) > 0
    assert "policy_areas" in data

    vote = data["votes"][0]
    assert "bill_number" in vote
    assert "one_liner" in vote
    assert "vote" in vote
    assert vote["vote"] in ("Yea", "Nay", "Not Voting")
    assert "date" in vote
    assert "result" in vote
    assert "policy_area" in vote


@pytest.mark.asyncio
async def test_get_member_votes_unknown_member():
    """Unknown member returns 404."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/X999999/votes")

    _clear_data_service_cache()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_member_votes_sorted_by_date():
    """Votes should be returned in reverse chronological order."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/votes")

    _clear_data_service_cache()
    data = response.json()
    dates = [v["date"] for v in data["votes"]]
    assert dates == sorted(dates, reverse=True), "Votes should be sorted newest first"


@pytest.mark.asyncio
async def test_get_member_votes_pagination():
    """Pagination with limit and offset works."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/votes?limit=1&offset=0")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert len(data["votes"]) == 1
    assert "total_count" in data
    assert data["total_count"] >= 1


@pytest.mark.asyncio
async def test_get_member_votes_invalid_params():
    """Negative offset or zero limit returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        neg_offset = await client.get("/api/members/S001217/votes?offset=-1")
        zero_limit = await client.get("/api/members/S001217/votes?limit=0")

    assert neg_offset.status_code == 422
    assert zero_limit.status_code == 422


@pytest.mark.asyncio
async def test_get_member_votes_stats_structure():
    """Stats include all required fields."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/S001217/votes")

    _clear_data_service_cache()
    data = response.json()
    stats = data["stats"]
    assert "total_votes" in stats
    assert "yea_count" in stats
    assert "nay_count" in stats
    assert "not_voting_count" in stats
    assert "participation_rate" in stats
    assert isinstance(stats["participation_rate"], (int, float))
