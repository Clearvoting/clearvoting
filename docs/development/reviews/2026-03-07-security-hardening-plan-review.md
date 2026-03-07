# Review: Security Hardening Implementation Plan

**Review type:** `docs/plans/2026-03-07-security-hardening.md`
**Scope:** Full security hardening — 14 findings across 5 phases, all severity tiers
**Reviewer:** Staff engineer (security, reliability, correctness)
**Local verification:** Verified all code references against current source files

**Implementation plan:** `docs/plans/2026-03-07-security-hardening.md`
**Technical design:** N/A (security hardening, not a feature)

## Summary

The plan correctly identifies the right security issues and proposes reasonable fixes for most of them. The phasing by severity is appropriate. However, there are several technical accuracy problems that would cause implementation failures if followed as written, one missing security concern the audit should have caught, and a few places where the proposed fix is either incomplete or would break existing tests. The plan needs corrections before execution.

**Readiness:** Ready with corrections — 1 P0 blocker (will cause test/runtime failures), 5 P1 items that need clarification or adjustment before implementation begins.

---

## Strengths

- **Severity ordering is correct.** SSRF and rate limiting are genuinely the highest-risk items. Phasing by severity ensures the most impactful fixes land first.
- **SSRF mitigation is well-designed.** Domain allowlist with `urlparse` is the right approach. Avoiding blocklists is the correct call — DNS rebinding and IPv6 make blocklists unreliable.
- **`defusedxml` over configuring stdlib ET.** Correct decision. Drop-in replacement, minimal risk.
- **Error message remediation is thorough.** Identifying `json.loads` in `ai_summary.py` as a crash vector is a good catch — that's easy to miss.
- **Cache implementation is already solid.** SHA-256 key hashing, atomic writes via `tempfile` + `os.replace`, TTL expiry — the plan correctly does not propose changes here.

---

## Production readiness blockers

### P0.1 — `slowapi` `@limiter.limit()` requires `Request` parameter in the endpoint

**Risk:** Implementation will fail at runtime. `slowapi` requires the decorated function to accept a `Request` parameter so it can extract the client IP. The current `get_ai_summary` signature is `(congress: int, bill_type: str, bill_number: int)` with no `Request`. The plan does not mention adding this parameter.

**Requirement:** The plan must specify adding `request: Request` to the `get_ai_summary` endpoint signature and importing `Request` from `starlette.requests` (or `fastapi`).

**Implementation guidance:**
```python
from fastapi import Request

@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
@limiter.limit("10/minute")
async def get_ai_summary(request: Request, congress: int, bill_type: str, bill_number: int):
    ...
```

The `request` parameter is consumed by the `slowapi` decorator and does not need to be used in the function body. Without it, `slowapi` raises `TypeError` at call time.

---

## High priority (P1)

### P1.1 — `congress` parameter validation breaks existing `list_bills` endpoint

The plan says to add `Query(ge=1, le=200)` for `congress` in `bills.py`. But `list_bills` declares `congress: int | None = None` — it's optional and nullable. You cannot apply `Query(ge=1, le=200)` to an `Optional[int]` default of `None` without also allowing `None`. The plan needs to distinguish between endpoints where `congress` is required (path parameter — already validated by FastAPI as an int) and where it's an optional query parameter.

**In `bills.py`:** `congress` is a path parameter in `get_bill`, `get_ai_summary`, `get_bill_votes` (already typed as `int`, FastAPI rejects non-integers). It's an optional query parameter only in `list_bills`. No `Query()` bounds needed for path params — they're already constrained by path typing. For `list_bills`, use `congress: int | None = Query(None, ge=1, le=200)`.

**In `votes.py`:** `congress` and `session` are path parameters in all 3 endpoints. FastAPI already validates them as integers. Adding `Query()` to a path parameter is semantically wrong (it would make them query params). To bound path params, use `Path(ge=1, le=200)` from `fastapi` instead.

### P1.2 — CORS `allow_origins=["*"]` contradicts the security intent

The plan proposes `allow_origins=["*"]` with a comment to "tighten when deployed." A wildcard origin in a security hardening plan is a contradiction — it explicitly allows any domain to make cross-origin requests. Since the app serves its own frontend from the same origin, CORS is not needed at all for the current architecture. The plan should either:

1. Skip CORS entirely (recommended — same-origin serving means CORS is irrelevant), or
2. Add CORS with a specific origin that matches the deployment domain, configured via environment variable

Option 1 is simpler and more secure. CORS should only be added when there is a concrete need (e.g., separate frontend deployment), not preemptively with a wildcard.

### P1.3 — Phase 4.4 is in the wrong file

The plan says "Add CORS middleware" under Phase 4.4 with the note "Added in `main.py`, not `congress_api.py`. Listed here for logical grouping." This is confusing for the author executing the plan — the section header says `app/services/congress_api.py` but the code goes in `main.py`. If CORS is kept (see P1.2), it should be listed under Phase 3 alongside the other `main.py` middleware changes.

### P1.4 — Rate limit test (Phase 1.6) will be flaky

Testing "11th request returns 429" requires controlling the rate limiter's state. `slowapi` uses an in-memory store by default, but in test environments using `httpx.AsyncClient(transport=ASGITransport(...))`, the limiter state may or may not persist across requests depending on whether the app instance is shared. The plan should specify:

1. Use the same `AsyncClient` session for all 11 requests (so the ASGI app instance and its limiter state persist)
2. Consider testing `_is_safe_url` as a unit test (pure function, no HTTP needed) rather than through the endpoint

### P1.5 — `_is_safe_url` should also validate URL path structure

The current SSRF fix only checks the domain. But `urlparse("https://congress.gov@evil.com/")` returns `hostname="evil.com"` because `congress.gov` is parsed as a username. The validation should also reject URLs containing `@` characters, or use a stricter check:

```python
def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_FETCH_DOMAINS
        and "@" not in url
    )
```

---

## Medium priority (P2)

- **`list_house_votes` and `get_house_vote` in `votes.py` have no `_is_demo()` guard.** These endpoints will attempt to call the Congress.gov API even in demo mode (no API key set), resulting in 502 errors. The plan does not address this — it should add demo-mode guards or note this as out of scope. This is a pre-existing bug, not a security issue, but it will cause confusion when testing the security fixes.

- **`bill_type` validation should be a shared utility.** The plan says to add the allowlist check "in each endpoint that takes `bill_type`" — that's 4 endpoints in `bills.py`. A helper function `_validate_bill_type(bill_type: str)` would reduce repetition and ensure consistency. Alternatively, use a FastAPI dependency.

- **The `openapi_url` parameter should also be disabled.** The plan disables `/docs` and `/redoc` but not the OpenAPI JSON schema at `/openapi.json`. This endpoint is still accessible and documents the full API surface. Add `openapi_url=None` to the `FastAPI()` constructor.

- **Health endpoint leaks demo mode status.** The audit noted this but the plan does not address it. The `/api/health` endpoint returns `"demo_mode": true/false`. This is low-risk but should be removed for consistency with the "don't leak internal details" principle.

- **Search endpoint in demo mode.** The `search.py` router has no `_is_demo()` guard. It will always try to call the Congress.gov API. Since the plan already touches this file (Phase 5.3), the TODO comment should note this explicitly.

---

## Readiness checklist

**P0 blockers**
- [ ] Add `request: Request` parameter to rate-limited endpoint signatures in plan

**P1 recommended**
- [ ] Fix `congress` parameter handling: distinguish path params (use `Path()`) from query params (use `Query()` with `None` default)
- [ ] Remove CORS `allow_origins=["*"]` — either skip CORS entirely or use explicit origin
- [ ] Move CORS configuration to Phase 3 alongside other `main.py` middleware (if kept)
- [ ] Specify test strategy for rate limiting (shared client session, unit test for URL validation)
- [ ] Add `@` rejection to `_is_safe_url` to prevent username-in-URL bypass
