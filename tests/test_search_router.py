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
async def test_search_bills():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/search/bills?q=beautiful")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert len(data["bills"]) == 1
    assert "Beautiful" in data["bills"][0]["title"]


@pytest.mark.asyncio
async def test_search_bills_requires_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/search/bills")
    assert response.status_code == 422
