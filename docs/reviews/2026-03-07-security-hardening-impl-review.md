# Review: ClearVote Security Hardening Implementation

**Review type:** Commits `672f732` through `e09d0d6` (5 commits, feat/security-hardening branch)
**Scope:** All 14 security findings from the audit, addressed across 5 phases: rate limiting, SSRF protection, error handling, input validation, security headers, XML safety, HTTP timeouts, and dependency updates
**Reviewer:** Staff engineer (security, correctness, test coverage, plan fidelity)
**Local verification:** `python3.11 -m pytest tests/ -v` — 58 passed, 0 failed, 0 errors

**Implementation plan:** `docs/plans/2026-03-07-security-hardening.md` (v1.1)
**Technical design:** N/A

## Summary

This branch delivers a comprehensive security hardening pass across all 14 identified findings. Every phase in the v1.1 plan is implemented and verifiably correct. The test suite expanded from 32 to 58 tests with zero regressions, and every new security control has direct test coverage. Two minor issues warrant follow-up: the `congress` path parameter on the member votes endpoint is missing bounds checking, and no logging sink is configured at startup so the new `logger.error` calls are effectively silent until that is addressed. Neither blocks the merge.

**Readiness:** Ready with corrections — two low-risk gaps documented as P1 below; no blockers.

---

## What shipped

- **Rate limiting (`app/limiter.py`, `app/main.py`, `app/routers/bills.py`)**: `slowapi` limiter extracted to its own module, wired through `SlowAPIMiddleware`, applied at 10 req/min per IP on the AI summary endpoint.
- **SSRF protection (`app/routers/bills.py`)**: `_is_safe_url` allowlists `congress.gov`, `www.congress.gov`, and `api.congress.gov`; rejects non-HTTPS schemes and username-in-URL bypass attempts. Gated before every outbound bill text fetch.
- **Generic error messages (all routers, `app/services/ai_summary.py`)**: All `detail=str(e)` and `detail=f"...{str(e)}"` replaced with `"External service temporarily unavailable"`. Actual errors logged via `logging.getLogger(__name__)`.
- **Input validation (`app/routers/bills.py`, `app/routers/members.py`)**: `VALID_BILL_TYPES` allowlist, `BIOGUIDE_PATTERN` regex (`^[A-Z]\d{6}$`), and `_validate_state_code` alpha+length check, each raising 400 on rejection.
- **Parameter bounds (all routers)**: `congress` constrained to `Path(ge=1, le=200)` on bill and vote endpoints; `session` constrained to `Path(ge=1, le=3)`; `congress` query param in `list_bills` constrained with `Query(None, ge=1, le=200)`. FastAPI returns 422 for out-of-range values.
- **Security headers (`app/main.py`)**: Middleware adds CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, and `Permissions-Policy` on every response.
- **Swagger/OpenAPI disabled (`app/main.py`)**: `docs_url=None, redoc_url=None, openapi_url=None` in FastAPI constructor.
- **Health endpoint hardened (`app/main.py`)**: `demo_mode` field removed from `/api/health` response.
- **HTTP timeouts (`app/services/congress_api.py`, `app/services/senate_votes.py`)**: `timeout=10.0` added to all `httpx.AsyncClient` instances.
- **XML safety (`app/services/senate_votes.py`)**: `xml.etree.ElementTree` replaced with `defusedxml.ElementTree` as a drop-in.
- **Dependency updates (`requirements.txt`)**: `jinja2==3.1.4` updated to `jinja2>=3.1.6` (CVE-2024-56201, CVE-2025-27516); `slowapi>=0.1.9` and `defusedxml>=0.7.1` added.
- **API key hardening (`app/services/congress_api.py`)**: `api_key` moved from query parameter to `X-Api-Key` request header, keeping it out of server logs and cached URLs.
- **Config bounds (`app/config.py`)**: `CACHE_TTL_SECONDS` clamped to 60–86400 seconds with `ValueError` fallback.
- **Test coverage (`tests/test_security.py`)**: 20 new tests covering URL validation, rate limiting, input validation, security headers, Swagger disablement, health info leak, and XXE payload.

---

## Strengths

- **`_is_safe_url` is defense-in-depth done right.** The allowlist-over-blocklist approach is the correct call. The `@` check for username-in-URL bypass is a non-obvious attack vector that was explicitly addressed after plan review, and it's tested with both the attack form (`https://congress.gov@evil.com`) and the credential form (`https://user:pass@www.congress.gov`). This is thorough.
- **Limiter extraction to `app/limiter.py` is a clean deviation from the plan.** The plan placed limiter setup inline in `app/main.py`. Extracting it to a dedicated module breaks the circular import that would occur when `bills.py` imports `limiter` while `main.py` imports `bills.py`. This is the right architectural call and shows the author was thinking ahead.
- **Rate limit test uses a single client session.** The plan flagged this requirement explicitly after the plan review, and the implementation follows through: all 12 requests run within a single `AsyncClient` context, ensuring the ASGI app state (and therefore the in-memory limiter counter) persists across requests. The test would give a false negative if the client were re-created per request.
- **XXE test is complete and correct.** The test constructs a full structurally-valid XML payload with an external entity reference to `/etc/passwd`, calls `parse_senate_vote_xml` directly, and asserts `EntitiesForbidden` is raised. This confirms the protection at the exact layer where the risk existed.
- **Test-driven regression protection.** The bioguide ID fix in `test_routers.py` (changing `T001` to `T000001`) is the right response to adding format validation — the old fixture value would now fail the new regex, and the fix was made correctly rather than suppressed.

---

## Production readiness blockers

None identified.

---

## High priority (P1)

### P1.1 — `congress` param on member votes endpoint has no bounds check

The `get_member_votes` endpoint in `app/routers/members.py` (line 34) declares `congress: int = 119` as a plain typed parameter. It is not wrapped in `Query(ge=1, le=200)`.

```python
# current — no bounds
async def get_member_votes(
    bioguide_id: str,
    congress: int = 119,
    ...
```

Every other `congress` parameter in the codebase was updated in Phase 2 (`bills.py` uses `Path(ge=1, le=200)`, `list_bills` uses `Query(None, ge=1, le=200)`, `votes.py` uses `Path(ge=1, le=200)`). This one was missed, likely because `get_member_votes` was added in the previous feature branch rather than the original scaffolding.

The fix is one line:

```python
congress: int = Query(119, ge=1, le=200),
```

### P1.2 — No logging sink configured; `logger.error` calls are effectively silent

The codebase now uses `logging.getLogger(__name__)` in five modules (`bills.py`, `members.py`, `votes.py`, `search.py`, `ai_summary.py`) and the warning in `search.py` fires on every request. However, `app/main.py` has no call to `logging.basicConfig()` or equivalent. Without a configured handler, Python's logging system discards all messages at the WARNING level and below by default, and outputs only WARNING and above to stderr through the last-resort handler — with no timestamp or module context.

This does not break the security model — errors are no longer forwarded to callers — but it means the `logger.error(...)` calls providing internal visibility are unreliable until this is configured.

Recommended addition to `app/main.py` at module level, before router imports:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
```

---

## Medium priority (P2)

- **`HSTS` header absent**: `Strict-Transport-Security` is not included in the security header middleware. This is appropriate if the app is running behind a reverse proxy that handles TLS termination and adds HSTS itself, but if it ever serves HTTPS directly, this should be added. The omission is not a bug at current deployment scope, but worth a comment in the middleware to explain the decision.

- **Rate limit test asserts exact success count**: `test_rate_limit_ai_summary` asserts `success_count == 10`. If `slowapi` processes the counter across the shared app instance between test runs, a previously-executed test that hit the same endpoint could cause this assertion to fail. Currently the limiter resets between test processes, but if the test file is ever refactored to share the app instance across test sessions, this will become flaky. Consider using a fresh `Limiter` instance per test run, or asserting `success_count >= 1` with `429 in responses` as the primary check.

- **`_is_safe_url` not guarded against `None` input**: `urlparse("")` handles empty strings gracefully (returns a parsed object with empty scheme and hostname, so the function correctly returns `False`). However, the code path in `get_ai_summary` that calls it only reaches `_is_safe_url` if `bill_text_url` is truthy (`if bill_text_url and _is_safe_url(bill_text_url)`), so there is no practical exposure. The existing unit test `test_safe_url_rejects_empty_and_malformed` correctly covers the empty string case.

- **`search.py` `congress` query param lacks bounds**: `congress: int | None = None` in `search.py` was not upgraded to `Query(None, ge=1, le=200)` as was done in `bills.py`. This is consistent with the search endpoint being a known-limited stub, but it is a minor inconsistency across the API surface.

---

## Readiness checklist

**P0 blockers**
- None

**P1 recommended**
- [ ] Add `Query(ge=1, le=200)` to `congress` param in `get_member_votes` (`app/routers/members.py` line 34)
- [ ] Add `logging.basicConfig(level=logging.INFO, ...)` to `app/main.py` so internal error logs are visible
