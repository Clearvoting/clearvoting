import pytest
from unittest.mock import patch
from pathlib import Path
from defusedxml.common import EntitiesForbidden
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.routers.bills import _is_safe_url
from app.services.senate_votes import parse_senate_vote_xml

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- SSRF URL Validation ---

def test_safe_url_accepts_congress_gov():
    assert _is_safe_url("https://www.congress.gov/bill/119/hr/1/text") is True
    assert _is_safe_url("https://congress.gov/some/path") is True
    assert _is_safe_url("https://api.congress.gov/v3/bill") is True


def test_safe_url_rejects_other_domains():
    assert _is_safe_url("https://evil.com/payload") is False
    assert _is_safe_url("https://169.254.169.254/latest/meta-data") is False
    assert _is_safe_url("https://localhost:8080/internal") is False


def test_safe_url_rejects_http_scheme():
    assert _is_safe_url("http://www.congress.gov/bill") is False


def test_safe_url_rejects_username_bypass():
    assert _is_safe_url("https://congress.gov@evil.com/payload") is False
    assert _is_safe_url("https://user:pass@www.congress.gov/bill") is False


def test_safe_url_rejects_empty_and_malformed():
    assert _is_safe_url("") is False
    assert _is_safe_url("not-a-url") is False
    assert _is_safe_url("ftp://congress.gov/file") is False


# --- Rate Limiting ---

@pytest.mark.asyncio
async def test_rate_limit_ai_summary():
    """AI summary endpoint returns 429 after exceeding rate limit."""
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = []
            for _ in range(12):
                resp = await client.get("/api/bills/119/hr/1/ai-summary")
                responses.append(resp.status_code)

    _clear_data_service_cache()
    assert 429 in responses, "Rate limiter should reject requests after limit exceeded"
    success_count = sum(1 for s in responses if s == 200)
    assert success_count == 10


# --- Input Validation ---

@pytest.mark.asyncio
async def test_invalid_bill_type_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/bills/119/faketype/1")
    assert resp.status_code == 400
    assert "Invalid bill type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_bill_types_accepted():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for bt in ["hr", "s", "hjres", "sjres", "HR", "S"]:
                resp = await client.get(f"/api/bills/119/{bt}/1")
                assert resp.status_code == 200, f"Bill type '{bt}' should be accepted"

    _clear_data_service_cache()


@pytest.mark.asyncio
async def test_invalid_bioguide_id_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/detail/INVALID")
    assert resp.status_code == 400
    assert "Invalid member ID" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_bioguide_id_accepted():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/members/detail/S001217")

    _clear_data_service_cache()
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_non_alpha_state_code_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/!!")
    assert resp.status_code == 400
    assert "2 letters" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_numeric_state_code_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/12")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_congress_out_of_range_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/bills/999/hr/1")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_messages_are_generic():
    """Error responses should not leak internal exception details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/bills/119/xxx/1")
    detail = resp.json()["detail"]
    assert "traceback" not in detail.lower()
    assert "exception" not in detail.lower()


# --- Security Headers ---

@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers["Permissions-Policy"]
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_swagger_and_openapi_disabled():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        docs = await client.get("/docs")
        redoc = await client.get("/redoc")
        openapi = await client.get("/openapi.json")

    assert docs.status_code == 404
    assert redoc.status_code == 404
    assert openapi.status_code == 404


@pytest.mark.asyncio
async def test_health_no_demo_mode_leak():
    """Health endpoint should not reveal whether API keys are configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    data = resp.json()
    assert "demo_mode" not in data
    assert data["status"] == "ok"


# --- XML Safety ---

def test_xxe_payload_blocked():
    """defusedxml should block XML External Entity attacks."""
    xxe_xml = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<roll_call_vote>
  <congress>119</congress>
  <session>2</session>
  <vote_number>1</vote_number>
  <vote_date>2026-01-01</vote_date>
  <vote_question_text>&xxe;</vote_question_text>
  <vote_document_text>Test</vote_document_text>
  <vote_result_text>Passed</vote_result_text>
  <vote_title>Test</vote_title>
  <count><yeas>50</yeas><nays>49</nays><present>0</present><absent>1</absent></count>
  <members></members>
</roll_call_vote>"""

    with pytest.raises(EntitiesForbidden):
        parse_senate_vote_xml(xxe_xml)
