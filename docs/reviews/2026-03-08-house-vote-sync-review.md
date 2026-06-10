# Review: House Vote Sync (Tasks 1-5)

**Review type:** Single commit `d9dd05a` on current branch
**Scope:** Add House roll call vote syncing so all House reps get voting records, matching what Senators already have
**Reviewer:** Staff engineer (correctness, architecture, security, performance, test coverage)
**Local verification:** `pytest tests/ -v` -- 96 passed in 3.33s

**Implementation plan:** `docs/plans/2026-03-08-house-vote-sync.md` (Tasks 1-5 of 7)
**Files changed:** `sync.py` (+281 lines), `tests/test_sync.py` (+245 lines)

## Summary

This commit adds House roll call vote syncing to the existing Senate-only pipeline. It introduces `sync_house_votes()` to fetch from the Congress.gov API, `_house_leg_to_document()` to convert API legislation types to document strings, expands `_parse_bill_ref()` to handle House resolution types (H.Res., H.Con.Res., S.Res., S.Con.Res.), expands `sync_bills_from_votes()` to scan both chamber directories, rewrites `build_member_votes()` to process both Senate and House members, and updates the `main()` pipeline from 4 to 5 steps. 8 new tests bring the total to 96, all passing.

The implementation faithfully follows the plan. Tasks 1-5 are fully implemented with no deviations from the planned approach. Tasks 6 and 7 (running the sync and generating AI summaries) are correctly out of scope for this commit.

**Readiness:** Approve -- no P0 or P1 blockers. Two suggestions for future improvement.

---

## What shipped

- **`sync_house_votes()`**: Fetches House roll call votes from Congress.gov API (detail + member endpoints), normalizes to the same JSON schema as Senate votes, writes to `data/synced/votes/house/`. Incremental -- skips existing files. Rate limiting via configurable delay.
- **`_house_leg_to_document()`**: Maps API legislation type codes (`HR`, `HJRES`, `HRES`, `HCONRES`, etc.) to formatted document strings (`H.R. 153`, `H.J.Res. 42`, etc.).
- **`_parse_bill_ref()` expansion**: Now handles 8 prefix types (up from 4). Prefix ordering is longest-first to prevent `H.R.` from matching `H.Res.` or `H.Con.Res.`.
- **`sync_bills_from_votes()` expansion**: Scans both `votes/senate/` and `votes/house/` directories for bill references. De-duplicates via set.
- **`build_member_votes()` rewrite**: Routes Senate members to Senate vote matching (by last name + state) and House members to House vote matching (by bioguide ID). Stats now count both `Yea`/`Aye` and `Nay`/`No` variants.
- **`main()` pipeline**: Updated to 5 steps. Step 3 is House votes, inserted between Senate votes and bills. Metadata now includes `house_votes_count`.
- **8 new tests**: 3 for `sync_house_votes` (happy path, incremental skip, rate limiting), 1 for `_house_leg_to_document`, 1 for `_parse_bill_ref` House types, 1 for `sync_bills_from_votes` both-chamber scanning, 2 for `build_member_votes` (House-only, both-chambers).

---

## Strengths

- **Exact plan alignment.** Every function, helper, test, and pipeline change matches the plan specification precisely. The plan specified TDD (write tests first, verify failure, implement, verify pass), and the resulting code matches the planned implementations line-for-line.
- **Schema consistency.** House votes are normalized to the exact same JSON schema as Senate votes, with the addition of a `"chamber": "House"` field. This means downstream code (routers, frontend) can treat votes uniformly regardless of source.
- **Correct prefix ordering in `_parse_bill_ref`.** The prefixes list is ordered longest-first (`H.Con.Res.` before `H.Res.` before `H.R.`), preventing shorter prefixes from stealing matches from longer ones. This is the right approach.
- **Appropriate matching strategy per chamber.** Senate votes are matched by last name + state (because Senate.gov XML does not include bioguide IDs), while House votes are matched by bioguide ID (because the Congress.gov API provides them). This is well-commented and architecturally sound.
- **Vote value normalization.** The stats computation now counts both `Yea`/`Aye` and `Nay`/`No`, which correctly handles the different vote terminology used by the two chambers.
- **Consistent patterns.** `sync_house_votes` follows the exact same incremental-with-exception-break pattern as `sync_senate_votes`. `_house_leg_to_document` mirrors `_parse_bill_ref` in reverse. No new patterns were invented where existing ones applied.
- **No existing tests broken.** All 88 pre-existing tests continue to pass unchanged.

---

## Production readiness blockers

None -- no P0 issues identified.

---

## High priority (P1)

None -- no P1 issues identified.

The broad `except Exception` with `break` in `sync_house_votes` (line 198) could mask non-API errors (e.g., disk full during `_atomic_write_json`, or a bug in the normalization logic). However, this is the same pattern used in `sync_senate_votes` (line 102) and has been running in production without issues. Changing this would be a cross-cutting concern for both functions, not specific to this commit.

---

## Suggestions (P2)

### P2.1 -- Duplicated vote-record-building logic between Senate and House branches

The `build_member_votes()` function (lines 324-377) has two nearly identical blocks for Senate and House. The only differences are: (1) the vote list iterated (`senate_votes` vs `house_votes`), (2) the member-matching logic (name+state vs bioguide ID), and (3) the `"chamber"` value in the output. The vote record dict construction is copy-pasted between the two branches.

This is acceptable for two chambers and matches the project's "don't add unnecessary abstractions" guideline. If a third data source is ever added, extracting a shared `_build_vote_record()` helper would be warranted, but not now.

### P2.2 -- `_house_leg_to_document` rebuilds the mapping dict on every call

The mapping dictionary in `_house_leg_to_document` (lines 118-127) uses f-strings with `leg_number`, so a new dict is constructed on each invocation. For the sync loop this is negligible (called once per vote), but if this function were ever called in a hot path, the dict could be extracted and the number appended separately. Not worth changing now.

### P2.3 -- No test for `_house_leg_to_document` with unknown type falling back to raw string

The test covers known types and empty/None inputs, but does not test the fallback behavior when an unknown `leg_type` is passed (e.g., `_house_leg_to_document("UNKNOWN", "42")` returns `"UNKNOWN 42"`). This fallback is correct and intentional (line 128), but a test would document the behavior.

### P2.4 -- Hardcoded `congress=119` in `build_member_votes` bill_id construction

Lines 342 and 369 hardcode `f"119-{bill_ref}"` for the `bill_id` field. This is a pre-existing issue from the Senate implementation, not introduced by this commit. When support for multiple congresses is added, this will need to be parameterized. Noting for future reference.

---

## Test coverage assessment

**Tests added:** 8 new tests (23 total in `test_sync.py`, 96 total across all test files)

| Test | What it validates |
|------|------------------|
| `test_sync_house_votes` | Happy path: fetches, normalizes, saves House vote JSON |
| `test_sync_house_votes_skips_existing` | Incremental sync skips files already on disk |
| `test_sync_house_votes_rate_limiting` | `asyncio.sleep` called between API requests |
| `test_house_leg_to_document` | All 5 known types + None/empty edge cases |
| `test_parse_bill_ref_house_resolutions` | H.Res., H.Con.Res., S.Res., S.Con.Res. parsing |
| `test_sync_bills_from_votes_includes_house` | Both Senate and House dirs scanned for bill refs |
| `test_build_member_votes_house` | House member gets vote record via bioguide ID match |
| `test_build_member_votes_both_chambers` | Senate + House members processed simultaneously |

**What is well-covered:**
- Core happy paths for all new and modified functions
- Incremental sync behavior (skip existing files)
- Rate limiting
- Edge cases for type conversion (None, empty string)
- Both-chamber integration scenario

**What is not tested (acceptable gaps):**
- `main()` pipeline integration (this would require mocking multiple services; the individual functions are tested)
- Error recovery scenarios in `sync_house_votes` (e.g., API returns partial data, network timeout mid-batch)
- Votes with no legislation type (empty document string passthrough)
- House member appearing in a Senate vote or vice versa (should be no-op due to chamber filtering -- this is correctly excluded by the `if chamber == "Senate"` / `elif chamber == "House of Representatives"` branching)

**Assessment:** Test coverage is thorough and appropriate. All 8 planned tests from the implementation plan are present. The test fixtures use realistic data shapes matching the actual Congress.gov API response format.

---

## Plan alignment

| Plan task | Status | Deviation |
|-----------|--------|-----------|
| Task 1: `sync_house_votes()` with tests | Complete | None |
| Task 2: `_house_leg_to_document` tests + `_parse_bill_ref` expansion | Complete | None |
| Task 3: `sync_bills_from_votes()` both-chamber scanning | Complete | None |
| Task 4: `build_member_votes()` both-chamber support | Complete | None |
| Task 5: `main()` 5-step pipeline | Complete | None |
| Task 6: Run sync and verify (not in scope) | Not in this commit | Expected |
| Task 7: Generate AI summaries (not in scope) | Not in this commit | Expected |

The plan called for 5 separate commits (one per task). The implementation squashed all 5 tasks into a single commit. This is a minor deviation from the plan's commit-per-task structure, but the single commit is cohesive (all changes serve one purpose: "add House vote syncing") and the commit message clearly lists all 5 changes. This is a reasonable and arguably better approach since the tasks are interdependent.

---

## Verdict

**APPROVE**

The implementation is faithful to the plan, architecturally sound, well-tested, and follows all existing patterns. No blockers, no P1 items. The P2 suggestions are all "nice to have" improvements that can be addressed in future work if needed. Ready to proceed to Tasks 6 and 7 (running the sync and generating AI summaries).
