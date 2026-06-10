# Review: Data Sync Architecture

**Review type:** Feature branch `feat/data-sync-architecture` (5 commits: 33d9ea9..679f620)
**Scope:** Replace live Congress.gov API calls and hardcoded demo data with pre-synced JSON files served by DataService
**Reviewer:** Staff engineer (architecture, security, reliability, operability)
**Local verification:** `python -m pytest tests/ -v` — 86 passed in 3.27s

**Implementation plan:** `docs/plans/2026-03-07-data-sync-architecture.md`
**Technical design:** `docs/plans/2026-03-07-data-sync-architecture-design.md`

## Summary

This branch replaces ClearVote's split-brain architecture (demo mode vs. live API calls) with a clean single-path model: a sync script pre-builds all data as JSON files, and a DataService loads them at startup. Routers went from 250+ lines of branching logic to ~100 lines of clean DataService calls. The sync script handles members, bills, Senate votes, AI summaries, and per-member voting records with incremental updates. 86 tests pass covering all layers.

**Readiness:** Ready with corrections — two P1 items (see below) should be addressed before first real sync run.

---

## What shipped

- **DataService** (`app/services/data_service.py`): Reads pre-synced JSON files into memory at startup. 10 methods covering all data access patterns.
- **Router refactor** (4 routers): Removed all `_is_demo()` branching and live API calls. Single code path via DataService.
- **Sync script** (`sync.py`): 5 sync functions — members (all 50 states + territories), bills with pagination, Senate votes (incremental), AI summaries (incremental, skips existing), member voting records (cross-references votes with members).
- **Test suite**: 86 tests — 17 DataService unit tests, 13 sync function tests, updated existing router/security tests.
- **Deployment**: Dockerfile updated to COPY data/synced/ into container.

---

## Strengths

- **Clean architecture**: The split-brain elimination is well-executed. Going from two code paths in every router to one is a significant simplification.
- **Incremental sync**: Senate votes and AI summaries skip existing data, making re-runs fast and cheap.
- **Atomic writes**: All JSON writes use temp-file-then-rename, preventing corrupt data if sync is interrupted.
- **Security model**: API keys stay on Joseph's laptop. The deployed app makes zero external API calls — no key exposure risk.
- **Test coverage**: Good coverage across unit and integration layers. Fixtures are realistic and match production data shapes.

---

## Production readiness blockers

None — no P0 issues identified. The architecture is sound and tests pass.

---

## High priority (P1)

### P1.1 — DataService singleton not invalidated between requests in tests

Tests call `get_data_service.cache_clear()` to reset the LRU-cached singleton, but the cache clear happens both before and after the context manager. If a test fails mid-execution, the singleton could leak fixture data into subsequent tests.

**Recommendation:** Use a pytest fixture with `autouse` that always clears the cache in teardown, or better yet, use FastAPI dependency overrides in tests instead of patching `get_data_dir`.

### P1.2 — sync_bills fetches summaries sequentially

The bill summary fetch loop processes each bill one at a time. For a full Congress with hundreds of bills, this could take a very long time due to sequential HTTP calls.

**Recommendation:** Add a configurable concurrency limit (e.g., `asyncio.Semaphore(5)`) to fetch summaries in parallel batches. Not blocking for initial use since Congress.gov rate limits make sequential reasonable for now.

### P1.3 — House vote endpoints removed

The votes router no longer has house vote endpoints (`/api/votes/house/*`). Any frontend code referencing these will get 404s.

**Recommendation:** Verify frontend JS doesn't call house vote endpoints, or add stub endpoints that return empty results.

---

## Medium priority (P2)

- **mock_data.py not deleted**: The old `app/services/mock_data.py` (1,630 lines) is no longer imported by any router. It should be removed to avoid confusion.
- **Search is naive**: Server-side search does a case-insensitive title substring match against all bills loaded in memory. This works fine for hundreds of bills but won't scale to thousands. Consider adding policy area filtering.
- **No data freshness indicator in frontend**: The frontend doesn't show when data was last synced. The `sync_metadata.json` has this info — expose it via an API endpoint.
- **No `--dry-run` flag**: The sync script would benefit from a `--dry-run` mode that shows what it would fetch without actually writing files.

---

## Readiness checklist

**P0 blockers**
- [x] No P0 blockers identified

**P1 recommended**
- [ ] Verify frontend doesn't call removed house vote endpoints
- [ ] Consider adding test fixture cleanup in pytest teardown
- [ ] Consider parallel bill summary fetching for large syncs

---
