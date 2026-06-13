import json
import pytest
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.limiter import limiter


@pytest.fixture(autouse=True)
def _use_tmp_notify_file(tmp_path):
    """Redirect notify signups to a temp file and reset the rate limiter."""
    tmp_file = tmp_path / "notify_signups.jsonl"
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file):
        yield tmp_file


# --- Happy path ---

@pytest.mark.asyncio
async def test_submit_signup_success(_use_tmp_notify_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/notify", json={"email": "joe@example.com", "state": "NY"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_signup_appended_to_file(_use_tmp_notify_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/notify", json={"email": "first@example.com", "state": "FL"})

    lines = _use_tmp_notify_file.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["email"] == "first@example.com"
    assert entry["state"] == "FL"
    assert "timestamp" in entry


# --- Validation errors ---

@pytest.mark.asyncio
async def test_invalid_email_rejected(_use_tmp_notify_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/notify", json={"email": "not-an-email", "state": "NY"})
    assert resp.status_code == 422
    assert not _use_tmp_notify_file.exists()
