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
