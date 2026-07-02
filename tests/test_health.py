import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir(data_dir=FIXTURES):
    """Patch data dir to use test fixtures and reset the DataService singleton."""
    return patch("app.dependencies.get_data_dir", return_value=data_dir)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_record_counts():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["members"] == 3
    assert data["bills"] == 3
    assert data["ai_summaries"] == 1
    assert data["member_summaries"] == 1
    # Coverage is intersected (bills that actually have a summary) and precise
    # enough that 1521/1525 can never read as 1.0 again.
    assert data["summary_coverage"] == 0.3333
    assert data["bills_missing_summary"] == 2


@pytest.mark.asyncio
async def test_health_check_zero_bills_coverage(tmp_path):
    with _patch_data_dir(tmp_path):
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["members"] == 0
    assert data["bills"] == 0
    assert data["summary_coverage"] == 0
