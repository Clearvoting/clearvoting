# ClearVote Security Hardening

**Version:** 1.1
**Created:** March 7, 2026
**Status:** Reviewed — ready for implementation

---

## Overview

A security audit of the ClearVote codebase identified 14 findings across critical, medium, and low priority tiers. The app currently has no rate limiting, no input format validation on several path parameters, no security response headers, unvalidated outbound URL fetching (SSRF risk), and error messages that leak internal details. This plan addresses all findings in 5 phases, ordered by severity.

**Current behavior:**
- No rate limiting on any endpoint, including the cost-generating AI summary endpoint (`app/routers/bills.py`)
- Server fetches arbitrary URLs from Congress.gov API responses without domain validation (`app/routers/bills.py:get_ai_summary`)
- Raw exception messages forwarded to callers via `HTTPException(detail=str(e))` across all routers
- No security headers (CSP, X-Frame-Options, etc.) in responses (`app/main.py`)
- FastAPI Swagger UI and ReDoc exposed at `/docs` and `/redoc` (`app/main.py`)
- `bill_type` and `bioguide_id` path params accept any string (`app/routers/bills.py`, `app/routers/members.py`)
- No timeouts on outbound HTTP calls (`app/services/congress_api.py`, `app/routers/bills.py`)
- XML parsed with stdlib `ET` instead of `defusedxml` (`app/services/senate_votes.py`)
- Jinja2 pinned to 3.1.4, missing CVE patches from 3.1.5/3.1.6

**New behavior:**
- Rate limiting on AI summary endpoint (and global fallback)
- All outbound URL fetches validated against domain allowlist
- Generic error messages returned to callers; details logged internally
- Full security header middleware
- Swagger UI disabled
- Input validation on all path parameters with allowlists/regex
- 10-second timeouts on all outbound HTTP calls
- `defusedxml` for XML parsing
- Dependencies updated

---

## Design Decisions

**Use `slowapi` for rate limiting.** It's the standard FastAPI rate limiting library, built on `limits`. Alternatives: custom middleware (more code, same result), reverse proxy rate limiting (requires deployment changes Joseph hasn't set up). `slowapi` is the simplest option that works at the application level.

**Validate outbound URLs with a domain allowlist, not a blocklist.** Allowlisting `congress.gov` and `senate.gov` is safer than trying to block internal IPs (which is fragile due to IPv6, DNS rebinding, etc.).

**Use custom middleware for security headers rather than a third-party package.** The header list is small and well-known. Adding a dependency for 10 lines of middleware is unnecessary.

**Disable Swagger UI via FastAPI constructor params, not middleware.** Simplest and most reliable approach — `docs_url=None, redoc_url=None, openapi_url=None`.

**Skip CORS middleware.** The frontend is served from the same origin as the API, so CORS is not needed. Adding `allow_origins=["*"]` would weaken security. CORS should only be added when a concrete cross-origin need arises (e.g., separate frontend deployment).

**Add `defusedxml` as a dependency rather than configuring stdlib `ET`.** `defusedxml` is the Python community's recommended approach and is a drop-in replacement.

---

## Phase 1: Rate Limiting and SSRF Protection (Critical)

**Completion gate:** AI summary endpoint has per-IP rate limits. All outbound URL fetches are validated against a domain allowlist. Tests cover both.

### 1.1 `requirements.txt` — Add `slowapi`

Add `slowapi>=0.1.9` to dependencies.

### 1.2 `app/main.py` — Configure rate limiter

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
```

### 1.3 `app/routers/bills.py` — Rate limit AI summary endpoint

Apply `@limiter.limit("10/minute")` to `get_ai_summary`. This limits each IP to 10 AI summary requests per minute. **Important:** `slowapi` requires a `Request` parameter in the endpoint signature to extract the client IP. Add `request: Request` as the first parameter (import from `fastapi`). The parameter is consumed by the decorator and does not need to be used in the function body.

```python
from fastapi import Request

@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
@limiter.limit("10/minute")
async def get_ai_summary(request: Request, congress: int, bill_type: str, bill_number: int):
```

### 1.4 `app/routers/bills.py` — Validate bill text URL before fetching

```python
ALLOWED_FETCH_DOMAINS = {"congress.gov", "www.congress.gov", "api.congress.gov"}

def _is_safe_url(url: str) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_FETCH_DOMAINS
        and "@" not in url  # Prevent username-in-URL bypass (e.g., https://congress.gov@evil.com)
    )
```

Only fetch `bill_text_url` if `_is_safe_url()` returns True. Otherwise skip text fetching and generate summary without bill text excerpt.

### 1.5 `app/routers/bills.py` — Add timeout to bill text fetch

```python
async with httpx.AsyncClient(timeout=10.0) as http_client:
```

### 1.6 Tests — Rate limiting and SSRF

- Test `_is_safe_url` as a unit test (pure function): rejects non-congress.gov domains, rejects `http://` scheme, rejects `@` in URL, accepts valid congress.gov URLs
- Test rate limiting: use a single `AsyncClient` session for all requests so the ASGI app instance and its limiter state persist; send 11 requests to a demo-mode `/ai-summary` endpoint and verify the 11th returns 429

---

## Phase 2: Error Handling and Input Validation (High)

**Completion gate:** No raw exception messages reach callers. All path parameters have format validation. Tests cover invalid inputs.

### 2.1 All routers — Replace `detail=str(e)` with generic messages

In `bills.py`, `members.py`, `votes.py`, `search.py`: replace every `detail=str(e)` or `detail=f"...{str(e)}"` with a generic message like `"External service temporarily unavailable"`. Log the actual error with Python's `logging` module.

### 2.2 `app/services/ai_summary.py` — Wrap JSON parsing in try/except

```python
try:
    parsed = json.loads(raw_text)
except json.JSONDecodeError:
    logger.error("AI response was not valid JSON: %s", raw_text[:200])
    return {"provisions": ["AI summary temporarily unavailable"], "impact_categories": []}
```

### 2.3 `app/routers/bills.py` — Validate `bill_type` against allowlist

```python
VALID_BILL_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}

# In each endpoint that takes bill_type:
if bill_type.lower() not in VALID_BILL_TYPES:
    raise HTTPException(status_code=400, detail="Invalid bill type")
```

### 2.4 `app/routers/members.py` — Validate `bioguide_id` format

```python
import re
BIOGUIDE_PATTERN = re.compile(r"^[A-Z]\d{6}$")

# In endpoints that take bioguide_id:
if not BIOGUIDE_PATTERN.match(bioguide_id.upper()):
    raise HTTPException(status_code=400, detail="Invalid member ID format")
```

### 2.5 `app/routers/members.py` — Validate `state_code` is alphabetic

Add `if not state_code.isalpha()` check before the existing length check.

### 2.6 `app/routers/bills.py`, `votes.py` — Bound `congress` and `session` params

**Important distinction:** `congress` and `session` are path parameters in most endpoints (already typed as `int` by FastAPI). Use `Path(ge=1, le=200)` from `fastapi` for path params — not `Query()`. The only query-param `congress` is in `list_bills` where it's optional: use `congress: int | None = Query(None, ge=1, le=200)`. For `session` path params in `votes.py`, use `Path(ge=1, le=3)`.

### 2.7 Tests — Input validation

- Test invalid bill_type returns 400
- Test invalid bioguide_id format returns 400
- Test non-alpha state_code returns 400
- Test congress out of range returns 422

---

## Phase 3: Security Headers and Swagger (Medium)

**Completion gate:** All responses include security headers. `/docs` and `/redoc` return 404.

### 3.1 `app/main.py` — Add security header middleware

```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https://www.congress.gov; "
        "script-src 'self'; "
        "connect-src 'self'"
    )
    return response
```

### 3.2 `app/main.py` — Disable Swagger UI and OpenAPI schema

```python
app = FastAPI(title="ClearVote", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
```

Also disables `/openapi.json` which otherwise exposes the full API schema.

### 3.3 Tests — Security headers

- Test that API responses include all security headers
- Test that `/docs`, `/redoc`, and `/openapi.json` return 404

---

## Phase 4: HTTP Timeouts and XML Safety (Medium-Low)

**Completion gate:** All outbound HTTP calls have explicit timeouts. XML parsing uses `defusedxml`.

### 4.1 `requirements.txt` — Add `defusedxml`

Add `defusedxml>=0.7.1`.

### 4.2 `app/services/congress_api.py` — Add timeout to AsyncClient

The existing `AsyncClient` in `__init__` needs `timeout=10.0`.

### 4.3 `app/services/senate_votes.py` — Replace `xml.etree.ElementTree` with `defusedxml`

```python
import defusedxml.ElementTree as ET  # replaces xml.etree.ElementTree
```

Drop-in replacement — no other code changes needed.

### 4.4 Tests — Timeouts and XML

- Test that `defusedxml` is used (parse test with XXE payload confirms it's blocked)

---

## Phase 5: Dependency Updates and Cleanup (Low)

**Completion gate:** All dependencies at latest secure versions. Search endpoint documented as known limitation.

### 5.1 `requirements.txt` — Update Jinja2 pin

Change `jinja2==3.1.4` to `jinja2>=3.1.6`.

### 5.2 `app/services/congress_api.py` — Use header for API key if supported

Check if Congress.gov API supports `X-Api-Key` header. If so, switch from query parameter to header. If not, document as a known limitation.

### 5.3 `app/routers/search.py` — Add TODO comment for broken query param

The search endpoint ignores the `q` parameter. Add a clear comment and log warning so this is visible to future developers.

### 5.4 `app/config.py` — Add bounds checking to CACHE_TTL_SECONDS

```python
_raw_ttl = os.getenv("CACHE_TTL_SECONDS", "3600")
try:
    CACHE_TTL_SECONDS: int = max(60, min(86400, int(_raw_ttl)))
except ValueError:
    CACHE_TTL_SECONDS: int = 3600
```

### 5.5 Final test run — All tests pass

Run full test suite. Verify no regressions.

---

## Files Touched

| File | Change |
|------|--------|
| `requirements.txt` | Add `slowapi`, `defusedxml`; update `jinja2` |
| `app/main.py` | Rate limiter setup, security headers middleware, disable Swagger/OpenAPI, remove demo_mode from health |
| `app/routers/bills.py` | Rate limit AI summary, URL validation, bill_type allowlist, generic errors, congress bounds |
| `app/routers/members.py` | bioguide_id regex, state_code alpha check, generic errors |
| `app/routers/votes.py` | Generic errors, congress/session bounds |
| `app/routers/search.py` | Generic errors, TODO comment |
| `app/services/ai_summary.py` | JSON parse error handling |
| `app/services/congress_api.py` | HTTP timeout, API key header |
| `app/services/senate_votes.py` | Switch to `defusedxml` |
| `app/config.py` | CACHE_TTL bounds checking |
| `tests/test_security.py` | New: rate limiting, SSRF, headers, input validation tests |
| `tests/test_member_votes.py` | Add bioguide_id validation test |
| `tests/test_routers.py` | Add bill_type and state_code validation tests |

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_security.py` | Rate limiting returns 429, SSRF URL validation, security headers present, Swagger disabled |
| Unit | `test_routers.py` | Invalid bill_type → 400, invalid state_code → 400, congress out of range → 422 |
| Unit | `test_member_votes.py` | Invalid bioguide_id → 400 |
| Integration | All test files | No regressions from security changes |

---

## Not In Scope

- **Authentication/authorization** — ClearVote is intentionally a public read-only app. Auth would contradict the "open government data" mission.
- **WAF or reverse proxy configuration** — deployment-level concern, not application code.
- **Penetration testing** — this plan addresses code-level findings only.
- **Google Fonts privacy** — noted as a finding but replacing with self-hosted fonts is a UX task, not a security fix.

---

## Revision History

### v1.1 (March 7, 2026) — Staff Engineer review corrections

Addresses items from [security hardening plan review](../development/reviews/2026-03-07-security-hardening-plan-review.md):

**P0 blockers resolved:**
- **`slowapi` requires `Request` param**: Added `request: Request` to the rate-limited endpoint signature in Phase 1.3

**P1 items resolved:**
- **`congress` param handling**: Clarified use of `Path()` for path params vs `Query()` for query params in Phase 2.6
- **CORS wildcard removed**: Removed CORS middleware entirely (same-origin serving makes it unnecessary). Added design decision explaining why.
- **Phase 4.4 misfiled**: Removed CORS from Phase 4; no longer applicable
- **Rate limit test strategy**: Specified single `AsyncClient` session approach and unit testing for `_is_safe_url` in Phase 1.6
- **`_is_safe_url` `@` bypass**: Added `"@" not in url` check to prevent username-in-URL attacks in Phase 1.4

**P2 items incorporated:**
- **`openapi_url=None`**: Added to Phase 3.2 alongside docs/redoc disabling
- **Health endpoint demo_mode leak**: Added to Files Touched; will remove `demo_mode` from health response
