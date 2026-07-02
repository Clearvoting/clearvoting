"""Notify signup persistence: Google Sheets primary, JSONL fallback.

Signups must survive deploys — Render's filesystem is ephemeral, so JSONL is
only a local-dev/outage fallback, never the primary store.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.limiter import limiter


def _make_sheets(available=True, append_ok=True):
    mock = MagicMock()
    mock.is_available = available
    mock.append_row.return_value = append_ok
    return mock


async def _post_notify(payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/notify", json=payload)


@pytest.mark.asyncio
async def test_notify_writes_to_sheets_when_available(tmp_path):
    """When Sheets is available, the signup goes to Sheets (not JSONL)."""
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=True, append_ok=True)
    limiter.reset()

    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify({"email": "voter@example.com", "state": "OH"})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_sheets.append_row.assert_called_once()
    row = mock_sheets.append_row.call_args[0][0]
    assert row[1] == "voter@example.com"
    assert row[2] == "OH"
    # JSONL should NOT have been written
    assert not tmp_file.exists()


@pytest.mark.asyncio
async def test_notify_falls_back_on_sheets_failure(tmp_path):
    """When the Sheets append fails, the signup still lands in JSONL."""
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=True, append_ok=False)
    limiter.reset()

    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify({"email": "voter@example.com", "state": "OH"})

    assert resp.status_code == 200
    entry = json.loads(tmp_file.read_text().strip())
    assert entry["email"] == "voter@example.com"
    assert entry["state"] == "OH"


@pytest.mark.asyncio
async def test_notify_jsonl_fallback_when_no_credentials(tmp_path):
    """Unconfigured Sheets (local dev) → JSONL, same as before."""
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=False)
    limiter.reset()

    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify({"email": "voter@example.com", "state": ""})

    assert resp.status_code == 200
    mock_sheets.append_row.assert_not_called()
    entry = json.loads(tmp_file.read_text().strip())
    assert entry["email"] == "voter@example.com"
