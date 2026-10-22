"""Notify signup persistence: Google Sheets primary, JSONL fallback.

Signups must survive deploys — Render's filesystem is ephemeral, so JSONL is
only a local-dev/outage fallback, never the primary store.
"""
import json
import logging
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
        resp = await _post_notify({"email": "voter@example.com", "state": "OH"})

    assert resp.status_code == 200
    mock_sheets.append_row.assert_not_called()
    entry = json.loads(tmp_file.read_text().strip())
    assert entry["email"] == "voter@example.com"
    assert entry["state"] == "OH"


@pytest.mark.asyncio
async def test_notify_fallback_log_never_contains_the_email(tmp_path, caplog):
    """Spec §10 #16: the fallback log names the state, never the address."""
    tmp_file = tmp_path / "notify_signups.jsonl"
    limiter.reset()

    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", _make_sheets(available=False)), \
         caplog.at_level(logging.INFO, logger="app.routers.notify"):
        resp = await _post_notify({"email": "voter@example.com", "state": "OH"})

    assert resp.status_code == 200
    messages = [r.getMessage() for r in caplog.records]
    assert "signup saved to fallback, state=OH" in messages
    assert not any("voter@example.com" in m for m in messages)


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"email": "voter@example.com"},
    {"email": "voter@example.com", "state": ""},
    {"email": "voter@example.com", "state": "CA"},
    {"email": "voter@example.com", "state": "fl"},
    {"email": "voter@example.com", "state": "NY"},
    {"email": "voter@example.com", "state": "TX"},
    {"email": "voter@example.com", "state": "ZZ"},
    {"email": "voter@example.com", "state": "Ohio"},
])
async def test_notify_requires_an_uncovered_state(tmp_path, payload):
    """Spec §10 #16: the state is required and must be one we don't cover (46 + DC)."""
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=True, append_ok=True)
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify(payload)
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Choose a state ClearVoting doesn't cover yet"}
    mock_sheets.append_row.assert_not_called()
    assert not tmp_file.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("state, stored", [("OH", "OH"), ("dc", "DC"), (" wy ", "WY")])
async def test_notify_accepts_uncovered_states_and_dc(tmp_path, state, stored):
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=True, append_ok=True)
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify({"email": "voter@example.com", "state": state})
    assert resp.status_code == 200
    assert mock_sheets.append_row.call_args[0][0][2] == stored


# --- Email shape: the browser's type=email rule, ASCII, with a dot in the domain (F019) ---

@pytest.mark.asyncio
@pytest.mark.parametrize("email", [
    "a\x00b@c.de", "a\x07@b.co", "x@ev\u200bil.com", "x@\u202eevil.com", "vot\u200ber@example.com",
    "a@b..c", "a@-.-", "a@-b.co", "a@b-.co", "a@b", "@b.co", "a@.co", "a b@c.de", "a@b.co\x00",
    "<script>alert(1)</script>@a.bc", '=HYPERLINK("https://evil.example","x")@a.bc', "ünï@example.com",
])
async def test_notify_refuses_addresses_a_browser_email_field_would(tmp_path, email):
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=True, append_ok=True)
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify({"email": email, "state": "OH"})
    assert resp.status_code == 422
    mock_sheets.append_row.assert_not_called()
    assert not tmp_file.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("email, stored", [
    ("Voter@EXAMPLE.com", "Voter@example.com"),
    (" o'brien+news@Mail.Example.org\n", "o'brien+news@mail.example.org"),
    ("a@b.c", "a@b.c"),
])
async def test_notify_stores_the_address_with_only_the_domain_lowercased(tmp_path, email, stored):
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets(available=True, append_ok=True)
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        resp = await _post_notify({"email": email, "state": "OH"})
    assert resp.status_code == 200
    assert mock_sheets.append_row.call_args[0][0][1] == stored


# --- Rate limits (F011, F085) ---

CF_EDGE = "172.70.12.34"  # inside Cloudflare's 172.64.0.0/13
SIGNUP = {"email": "voter@example.com", "state": "OH"}


def _via_cloudflare(ip: str, edge: str = CF_EDGE) -> dict:
    return {"CF-Connecting-IP": ip, "X-Forwarded-For": f"{ip}, {edge}"}


async def _post_each(headers_list):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return [await client.post("/api/notify", json=SIGNUP, headers=headers) for headers in headers_list]


@pytest.mark.asyncio
async def test_sixth_signup_from_one_client_is_refused_before_any_write(tmp_path):
    tmp_file = tmp_path / "notify_signups.jsonl"
    mock_sheets = _make_sheets()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", mock_sheets):
        responses = await _post_each([{}] * 6)
    assert [r.status_code for r in responses] == [200] * 5 + [429]
    assert responses[5].headers["cache-control"] == "no-store"
    assert mock_sheets.append_row.call_count == 5
    assert not tmp_file.exists()


@pytest.mark.asyncio
async def test_cf_connecting_ip_that_is_not_an_address_gets_no_fresh_bucket(tmp_path):
    """F011: a new CF-Connecting-IP on every request that is not an IP address is skipped, so
    the requests are still one client, keyed by the hop the nearest proxy appended."""
    mock_sheets = _make_sheets()
    headers = [{"CF-Connecting-IP": f"client-{i}", "X-Forwarded-For": f"203.0.113.{i}, 198.51.100.7"}
               for i in range(6)]
    with patch("app.routers.notify.NOTIFY_FILE", tmp_path / "notify_signups.jsonl"), \
         patch("app.routers.notify._sheets", mock_sheets):
        responses = await _post_each(headers)
    assert [r.status_code for r in responses] == [200] * 5 + [429]
    assert mock_sheets.append_row.call_count == 5


@pytest.mark.asyncio
async def test_cf_connecting_ip_through_cloudflare_is_honoured(tmp_path):
    """Six visitors behind one Cloudflare edge are six clients; each still gets only five."""
    mock_sheets = _make_sheets()
    visitors = [_via_cloudflare(f"203.0.113.{i}") for i in range(6)]
    with patch("app.routers.notify.NOTIFY_FILE", tmp_path / "notify_signups.jsonl"), \
         patch("app.routers.notify._sheets", mock_sheets):
        first = await _post_each(visitors)
        repeat = await _post_each([visitors[0]] * 5)
    assert [r.status_code for r in first] == [200] * 6
    assert [r.status_code for r in repeat] == [200] * 4 + [429]


@pytest.mark.asyncio
async def test_signups_inside_one_ipv6_64_share_a_bucket(tmp_path):
    mock_sheets = _make_sheets()
    edge = "2606:4700:10::1"
    with patch("app.routers.notify.NOTIFY_FILE", tmp_path / "notify_signups.jsonl"), \
         patch("app.routers.notify._sheets", mock_sheets):
        same_64 = await _post_each([_via_cloudflare(f"2001:db8:1:2::{i + 1:x}", edge) for i in range(6)])
        next_64 = await _post_each([_via_cloudflare("2001:db8:1:3::1", edge)])
    assert [r.status_code for r in same_64] == [200] * 5 + [429]
    assert next_64[0].status_code == 200


@pytest.mark.asyncio
async def test_notify_cap_is_shared_by_every_client(tmp_path):
    """F011: 25 a minute in all, however many addresses send them."""
    mock_sheets = _make_sheets()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_path / "notify_signups.jsonl"), \
         patch("app.routers.notify._sheets", mock_sheets):
        responses = await _post_each([_via_cloudflare(f"203.0.113.{i}") for i in range(1, 27)])
    assert [r.status_code for r in responses] == [200] * 25 + [429]
    assert responses[25].headers["cache-control"] == "no-store"
    assert mock_sheets.append_row.call_count == 25
