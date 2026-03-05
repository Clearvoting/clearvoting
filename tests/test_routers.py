import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


# --- Members Router ---

@pytest.mark.asyncio
async def test_get_members_by_state():
    mock_data = {
        "members": [
            {"bioguideId": "T001", "name": "Test Senator", "state": "FL", "partyName": "Democrat"}
        ]
    }
    with patch("app.routers.members._is_demo", return_value=False), \
         patch("app.routers.members.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_members_by_state = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL")

    assert response.status_code == 200
    data = response.json()
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
    mock_data = {
        "member": {"bioguideId": "T001", "firstName": "Test", "party": "Democrat", "partyName": "Democrat"}
    }
    with patch("app.routers.members._is_demo", return_value=False), \
         patch("app.routers.members.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_member = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/detail/T001")

    data = response.json()
    assert "party" not in data.get("member", {})
    assert "partyName" not in data.get("member", {})


@pytest.mark.asyncio
async def test_get_member_detail_shows_party_when_requested():
    mock_data = {
        "member": {"bioguideId": "T001", "firstName": "Test", "party": "Democrat", "partyName": "Democrat"}
    }
    with patch("app.routers.members._is_demo", return_value=False), \
         patch("app.routers.members.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_member = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/detail/T001?show_party=true")

    data = response.json()
    assert data["member"]["partyName"] == "Democrat"


# --- Bills Router ---

@pytest.mark.asyncio
async def test_list_bills():
    mock_data = {"bills": [{"number": "1", "title": "Test"}]}
    with patch("app.routers.bills._is_demo", return_value=False), \
         patch("app.routers.bills.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_bills = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_bill_detail():
    mock_bill = {"bill": {"number": "1234", "title": "Test", "congress": 119}}
    mock_subjects = {"subjects": []}
    with patch("app.routers.bills._is_demo", return_value=False), \
         patch("app.routers.bills.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_bill = AsyncMock(return_value=mock_bill)
        mock_client.get_bill_subjects = AsyncMock(return_value=mock_subjects)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/bills/119/hr/1234")
    assert response.status_code == 200
    assert response.json()["bill"]["number"] == "1234"


# --- Votes Router ---

@pytest.mark.asyncio
async def test_get_senate_vote_strips_party():
    mock_data = {
        "congress": 119, "session": 2, "vote_number": 44,
        "question": "On Cloture", "result": "Agreed to",
        "counts": {"yeas": 84, "nays": 6, "present": 1, "absent": 9},
        "members": [
            {"first_name": "Test", "last_name": "Senator", "party": "D", "state": "FL", "vote": "Yea"}
        ],
    }
    with patch("app.routers.votes.get_senate_vote_service") as mock_get:
        mock_service = MagicMock()
        mock_service.get_vote = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/2/44")

    assert response.status_code == 200
    data = response.json()
    for member in data["members"]:
        assert "party" not in member


@pytest.mark.asyncio
async def test_get_senate_vote_shows_party():
    mock_data = {
        "congress": 119, "session": 2, "vote_number": 44,
        "question": "On Cloture", "result": "Agreed to",
        "counts": {"yeas": 84, "nays": 6, "present": 1, "absent": 9},
        "members": [
            {"first_name": "Test", "last_name": "Senator", "party": "D", "state": "FL", "vote": "Yea"}
        ],
    }
    with patch("app.routers.votes.get_senate_vote_service") as mock_get:
        mock_service = MagicMock()
        mock_service.get_vote = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/votes/senate/119/2/44?show_party=true")

    data = response.json()
    assert data["members"][0]["party"] == "D"
