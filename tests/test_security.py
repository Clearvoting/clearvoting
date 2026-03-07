import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.routers.bills import _is_safe_url


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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = []
        for _ in range(12):
            resp = await client.get("/api/bills/119/hr/1/ai-summary")
            responses.append(resp.status_code)

    # First 10 should succeed (200), 11th+ should be rate-limited (429)
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for bt in ["hr", "s", "hjres", "sjres", "HR", "S"]:
            resp = await client.get(f"/api/bills/119/{bt}/1")
            assert resp.status_code == 200, f"Bill type '{bt}' should be accepted"


@pytest.mark.asyncio
async def test_invalid_bioguide_id_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/detail/INVALID")
    assert resp.status_code == 400
    assert "Invalid member ID" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_bioguide_id_accepted():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/detail/S001217")
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
        # Invalid bill type gives a clear but safe message
        resp = await client.get("/api/bills/119/xxx/1")
    detail = resp.json()["detail"]
    assert "traceback" not in detail.lower()
    assert "exception" not in detail.lower()
