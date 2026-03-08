# Review: Task 2 -- Use AI `one_liner` in Sync Script

**Commit:** `085cacc` feat: use AI one_liner in member vote records instead of raw titles
**Branch:** feat/member-summary-improvements
**Reviewer:** Staff Engineer (automated)
**Date:** 2026-03-08

---

## Plan Alignment

The commit matches the plan's Task 2 specification exactly:

- `ai_summaries.json` is loaded at the top of `build_member_votes()` with a graceful `if exists()` guard. Matches the plan verbatim.
- `_get_one_liner()` helper function signature and logic match the plan: checks `bill_ref`, builds `119-{bill_ref}` key, looks up `ai_summary.get("one_liner")`, falls back to `bill_info.get("title", doc)`.
- Both `one_liner` assignments (Senate line 358, House line 385) replaced from inline `bill_info.get("title", doc)` to `_get_one_liner(bill_ref, bill_info, doc)`.
- Two new tests match the plan's test specifications: AI lookup happy path and fallback when no `ai_summaries.json` exists.
- Commit message matches the plan's suggested message.

No deviations from the plan.

## What Was Done Well

- The `_get_one_liner` closure captures `ai_summaries` from enclosing scope cleanly, avoiding parameter threading through the member loop. This is a good use of a nested function.
- Both Senate and House code paths updated identically -- no risk of one path using the old behavior.
- The `if ai_summaries_path.exists()` guard means existing deployments without `ai_summaries.json` work without modification. Zero-downtime upgrade path.
- Fallback chain is correct: AI one_liner > bill title > raw document string. This is critical because 0/177 existing summaries have a `one_liner` field today, so the fallback is the production path until Task 4 regenerates them.
- All 106 tests pass with no regressions.

## Issues

### P1 -- No test for House chamber AI one_liner lookup

Both new tests use Senate votes only (matching the plan's test spec). The House code path at line 385 also calls `_get_one_liner`, but no test exercises it with an `ai_summaries.json` present. While the implementation is identical (both paths call the same helper), a test for the House path would catch any future divergence between the two blocks. This is a one-test gap.

**Recommended fix:** Duplicate `test_build_member_votes_uses_ai_one_liner` with a House member (`chamber: "House of Representatives"`) and a House vote directory. Or, extend `test_build_member_votes_both_chambers` to include an `ai_summaries.json` and assert both members get the AI one_liner.

### P1 -- No test for `ai_summaries.json` present but bill not found in it

The fallback test covers "no `ai_summaries.json` file at all," but does not cover "file exists, bill key not in it." This is the most common production scenario right now (177 summaries exist, none have `one_liner`). The code handles it correctly via `.get(summary_key, {})`, but a test would document and protect this behavior.

**Recommended fix:** Add a test with an `ai_summaries.json` that contains entries for other bills but not the one being voted on. Assert the raw title is used.

### P1 -- Hardcoded congress number `119` in `_get_one_liner`

Line 305 builds the summary key as `f"119-{bill_ref}"`. This matches the existing hardcoded `119` on lines 357, 384, and 405 -- so this is consistent, not a regression. However, it means the function will silently fail to look up summaries if this code is ever used for a different congress. This is a pre-existing tech debt item, not a Task 2 issue, but worth noting since the helper function would be the natural place to parameterize it.

**No action required for this task.** Noting for future reference.

### Suggestion -- `json.load` without error handling

Line 301 calls `json.load(f)` on `ai_summaries.json` with no `try/except`. If the file is malformed JSON (e.g., truncated during a previous sync), `build_member_votes` will crash entirely instead of falling back to raw titles. The risk is low (the file is written atomically by the AI summary service), but a `try/except json.JSONDecodeError` with a warning and empty-dict fallback would be more defensive.

## Verdict

**Approved.** The implementation is clean, correct, and precisely matches the plan. The two missing test scenarios (House path and key-not-found) are real gaps but not blockers -- the code handles both cases correctly. Recommend addressing the P1 test gaps during Task 5 (full test suite pass) or as a quick follow-up.
