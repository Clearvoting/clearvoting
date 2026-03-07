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
