import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_search_bills():
    mock_data = {"bills": [{"number": "1", "title": "Test Bill"}]}
    with patch("app.routers.search.get_congress_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_bills = AsyncMock(return_value=mock_data)
        mock_get.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/search/bills?q=wage")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_bills_requires_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/search/bills")
    assert response.status_code == 422
