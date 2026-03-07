import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_member_votes_demo_mode():
    """Demo mode returns mock voting data for known FL members."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes")

    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == "S001217"
    assert "stats" in data
    assert data["stats"]["total_votes"] > 0
    assert data["stats"]["participation_rate"] > 0
    assert "votes" in data
    assert len(data["votes"]) > 0
    assert "policy_areas" in data

    # Verify vote structure
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/UNKNOWN123/votes")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_member_votes_sorted_by_date():
    """Votes should be returned in reverse chronological order."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes")

    data = response.json()
    dates = [v["date"] for v in data["votes"]]
    assert dates == sorted(dates, reverse=True), "Votes should be sorted newest first"


@pytest.mark.asyncio
async def test_get_member_votes_pagination():
    """Pagination with limit and offset works."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes?limit=3&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["votes"]) == 3
    assert "total_count" in data
    assert data["total_count"] >= 3


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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes")

    data = response.json()
    stats = data["stats"]
    assert "total_votes" in stats
    assert "yea_count" in stats
    assert "nay_count" in stats
    assert "not_voting_count" in stats
    assert "participation_rate" in stats
    assert isinstance(stats["participation_rate"], (int, float))


@pytest.mark.asyncio
async def test_get_member_votes_house_member():
    """House member (Byron Donalds) returns voting data correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/D000032/votes")

    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == "D000032"
    assert len(data["votes"]) > 0
    assert data["votes"][0]["chamber"] == "House"


@pytest.mark.asyncio
async def test_get_member_votes_wrong_congress_demo():
    """Demo mode rejects congress values other than 119."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes?congress=118")

    assert response.status_code == 400
    assert "119" in response.json()["detail"]
