# Review: Issue Scorecards & Narrative Redesign

**Branch:** feature/issue-scorecards-narrative-redesign
**Commits:**
- `36ed0ef` feat: replace impact categories with 12 issue categories, change direction labels (Phase 1)
- `aa773d3` feat: add scorecard verdict generation, increase bill text, add regenerate flag (Phase 2)
- `20118c5` feat: update API endpoints with new field names and scorecard data (Phase 3)
- `a86af73` feat: replace mini bars with issue scorecards in frontend (Phase 4)

**Tests:** 224 passed (0 failures, 0 errors)
**Readiness:** Approve with issues noted

---

## Plan Alignment

### Phase 1: Backend Categories & Direction Refactoring -- COMPLETE

- Replaced 21 `IMPACT_CATEGORIES` with 12 `ISSUE_CATEGORIES` throughout all backend services, prompts, graders, and tests. The new categories ("Cost of Living", "Healthcare", "Jobs & Workers", etc.) are well-chosen and voter-centric.
- Direction labels changed from `strengthens`/`weakens` to `in_favor`/`against` across all services: `ai_summary.py`, `member_summary.py`, `data_service.py`, `page_coherence.py`, `member_narrative_grader.py`, `summary_grader.py`.
- `max_tokens` increased from 1024 to 1536 in `AISummaryService` for richer bill provisions.
- Member narrative prompt rewritten with journalist-style structure. Top supported/opposed bills increased from 8+6 to 15+10. Top areas increased from 3 to 6 in `data_service.py`.
- All test fixtures updated (`ai_summaries.json`, `member_summaries.json`, `member_votes/S001217.json`).
- All 224 tests pass.

### Phase 2: Sync Pipeline Updates -- COMPLETE

- `generate_scorecard_verdicts()` function added to `sync.py` (~130 lines). Groups member votes by `issue_categories` from AI summaries, computes in_favor/against ratios, generates LLM-based one-line verdicts per category, stores as `scorecard` field in member vote JSON.
- Bill text excerpt increased from 2,000 to 6,000 characters (in both `sync_bill_summaries` and `_run_audit`).
- `--regenerate-all-summaries` CLI flag added with backup logic, 3-step pipeline (bill summaries, member votes, member narratives).
- Pipeline steps renumbered from 9 to 10 with scorecard generation as Step 7.
- `build_member_votes` initializes empty `scorecard: []` in the member vote record structure.

### Phase 3: API Layer -- COMPLETE

- `bills.py` fallback response changed from `impact_categories` to `issue_categories`.
- `members.py` `/summary` endpoint now includes `issue_scorecard` from member vote data.
- `members.py` `/votes` endpoint now includes `scorecard` in response.

### Phase 4: Frontend -- COMPLETE

- Landing page (`app.js`): Replaced `IMPACT_CATEGORIES` with `ISSUE_CATEGORIES` array. `renderCardSnapshot` now shows compact scorecard preview (top 4 items) with color-coded in_favor/against ratios, with graceful fallback to `top_policy_areas`.
- Member page (`member.js`): `renderVotingSummary` replaced mini bars with full issue scorecard UI using `<details>` expandable bill lists. Direction-aware vote aggregation uses new `in_favor`/`against` terminology. Graceful fallback to top policy areas when no scorecard data.
- Bill page (`bill.js`): Renamed `impact_categories` to `issue_categories`, "Impact Areas" heading to "Issue Areas".
- CSS: Mini bar styles (`.summary-mini-bar`, `.summary-mini-bar-yea`, `.summary-mini-bar-strengthen`, `.summary-mini-bar-weaken`) replaced with new scorecard styles (`.issue-scorecard`, `.issue-scorecard-item`, `.scorecard-vote-badge`, etc.).

---

## Code Quality Assessment

### What Was Done Well

- **Thorough terminology migration.** The rename from `impact_categories`/`strengthens`/`weakens` to `issue_categories`/`in_favor`/`against` was executed across all Python source files, test files, and test fixtures with zero misses in application code.
- **Graceful fallbacks.** Both `app.js` and `member.js` fall back to `top_policy_areas` when no scorecard data exists. This ensures the UI works during the transition before summaries are regenerated.
- **Atomic writes.** Scorecard data is written via `_atomic_write_json`, consistent with the project's existing pattern.
- **Direction logic.** The effective stance computation in `generate_scorecard_verdicts` correctly inverts direction for Nay votes on "in_favor" bills and Yea votes on "against" bills, matching the same logic in `data_service.py`.
- **Backup-before-clear pattern.** The `--regenerate-all-summaries` flag backs up `ai_summaries.json` and `member_summaries.json` before clearing, which is good defensive practice.
- **LLM fallback.** `generate_scorecard_verdicts` has a non-LLM fallback when the API call fails, producing a factual sentence from the counts alone.

### Issues

#### Critical

None.

#### Important

**I-1: Synced data files still contain old terminology (must regenerate before deploy).**
The actual `data/synced/ai_summaries.json` (636 entries) still uses `impact_categories` and `strengthens`/`weakens` direction values. The `data/synced/member_votes/*.json` files also contain `strengthens`/`weakens` direction values. The `data/synced/member_summaries.json` narratives reference "strengthen" and "weaken" language.

This means:
- `generate_scorecard_verdicts` will find zero `issue_categories` in AI summaries, producing empty scorecards for all members.
- The fallback code paths will render `top_policy_areas` instead of scorecards, effectively hiding the new feature.
- Frontend category tags on bill pages will show nothing (the data has `impact_categories`, the code reads `issue_categories`).

The `--regenerate-all-summaries` flag was created precisely for this purpose, but it needs to be run before deploying. This is an operational step, not a code bug, but it should be documented clearly so it is not overlooked.

**Recommendation:** Add a note to the commit message or a migration comment in `sync.py` stating that `--regenerate-all-summaries` must be run before deployment. Alternatively, add a compatibility shim in `generate_scorecard_verdicts` and `data_service.py` that reads `impact_categories` as a fallback for `issue_categories`, and maps `strengthens`/`weakens` to `in_favor`/`against`, so the feature works with both old and new data during the transition period.

**I-2: `--regenerate-all-summaries` does not generate scorecards.**
The 3-step regeneration pipeline is: (1) bill summaries, (2) member votes, (3) member narratives. Step 7 from the main pipeline (`generate_scorecard_verdicts`) is missing. After running `--regenerate-all-summaries`, members will have empty scorecards.

**Files:** `/Users/josephgarcia/Documents/Claude/Projects/clearvote/sync.py` lines 1478-1496

**Recommendation:** Add `generate_scorecard_verdicts` as Step 3 (before member narratives become Step 4) in the `--regenerate-all-summaries` flow:
```python
print("[3/4] Generating issue scorecard verdicts...")
await generate_scorecard_verdicts(SYNC_DIR, api_key=anthropic_key or None)
```

**I-3: No tests for `generate_scorecard_verdicts`.**
This is the largest new function (~130 lines) and the core feature of this branch, but it has zero test coverage. The function contains LLM calls, direction inversion logic, file I/O, and aggregation logic that should be tested.

**Recommendation:** Add tests covering:
- Basic scorecard generation with mock LLM responses
- Direction inversion logic (Yea on "against" bill = effective "against")
- Empty votes producing no scorecard
- LLM failure triggering the fallback verdict
- Categories from AI summaries correctly grouping votes

**I-4: `renderScorecard` function in `member.js` uses an incompatible data schema.**
The `renderScorecard` function (lines 532-604) expects scorecard items with `issue.issue`, `issue.subtitle`, `issue.votes[].summary`, and `issue.votes[].deficit` fields. But `generate_scorecard_verdicts` produces items with `item.category`, `item.verdict`, `item.bills[].one_liner`, and `item.bills[].direction`. These two schemas are completely different.

The function is called at line 318: `if (data.scorecard && data.scorecard.length > 0) { renderScorecard(container, data.scorecard); }`. This would render broken/empty scorecard cards because every field access would return `undefined`.

The scorecard is also rendered correctly inside `renderVotingSummary` (lines 427-503) using the new schema from `summaryData.issue_scorecard`. So the old `renderScorecard` call at line 318 duplicates the display and uses the wrong schema.

**Files:** `/Users/josephgarcia/Documents/Claude/Projects/clearvote/static/js/member.js` lines 317-319, 532-604

**Recommendation:** Either remove the `renderScorecard` function and its call at line 318 entirely (since `renderVotingSummary` now handles it), or update `renderScorecard` to use the new schema. The old function appears to be dead code from a previous iteration.

#### Suggestions

**S-1: Unused CSS variable `--vote-weaken`.**
The CSS variable `--vote-weaken: #E8913A` (line 19 of `styles.css`) is no longer referenced anywhere. All the mini bar styles that used it have been removed.

**File:** `/Users/josephgarcia/Documents/Claude/Projects/clearvote/static/css/styles.css` line 19

**Recommendation:** Remove `--vote-weaken: #E8913A;` from `:root`.

**S-2: Unused `favorPct` variable in frontend.**
In both `app.js` (line 317) and `member.js` (line 436), `favorPct` is computed but never used. It appears to be leftover from a planned percentage display that was replaced with the ratio format.

**S-3: `generate_scorecard_verdicts` uses a private method from `AISummaryService`.**
Line 704: `verdict = await service._call_llm(verdict_system, verdict_prompt)`. Calling `_call_llm` directly (underscore prefix = private by convention) couples the scorecard generator to the internal implementation of `AISummaryService`. If `_call_llm` is renamed or its signature changes, this breaks silently.

**Recommendation:** Either make `_call_llm` a public method (rename to `call_llm`), or add a dedicated public method to `AISummaryService` for verdict generation.

**S-4: Rate limiting in `generate_scorecard_verdicts` sleeps even when LLM call failed.**
At line 738-739, the sleep happens whenever `scorecard` is non-empty, regardless of whether LLM calls were actually made (the fallback path does not call the LLM). This is minor since the fallback is rare, but it adds unnecessary delay.

**S-5: Page coherence prompt references "Issue Scorecards" but the checker does not receive scorecard data.**
The `COHERENCE_SYSTEM_PROMPT` in `page_coherence.py` (line 23) now mentions "ISSUE SCORECARDS" as section 3, but the `check()` method (line 79-84) passes `where_they_focus: top_areas` without scorecard data. The coherence checker cannot verify scorecard consistency because it never sees the scorecard. This is a minor gap -- the coherence checker will still validate narrative vs. other data, but it cannot catch scorecard-narrative conflicts.

---

## Architecture Assessment

- **Separation of concerns:** The scorecard generation is correctly placed in `sync.py` as an offline pipeline step rather than computed at request time. This follows the existing pattern where all data processing happens during sync.
- **Data flow is clean:** sync -> member_votes JSON -> API -> frontend. The scorecard data flows through established paths.
- **Backward compatibility:** The fallback paths in the frontend ensure the app works with both old and new data formats, which is good during migration.
- **The `--regenerate-all-summaries` flag** is a good addition for managing the data migration, though it needs the scorecard step added (I-2).

---

## Security

No new security concerns. The scorecard data is generated offline from trusted synced data. No new user inputs are accepted. The existing SSRF protections, rate limiting, and input validation remain intact.

---

## Summary

The implementation is well-structured and the terminology migration in source code is thorough. The main concern is that the **synced data files have not been regenerated** (I-1), which means the new scorecard feature will not work in production until `--regenerate-all-summaries` is run. The missing scorecard step in `--regenerate-all-summaries` (I-2) means even that command will not fully work without a fix. The `renderScorecard` function using an incompatible schema (I-4) will render broken UI for the votes-tab scorecard. Adding tests for the core `generate_scorecard_verdicts` function (I-3) would strengthen confidence in the direction inversion and aggregation logic.

Recommended action: fix I-2 and I-4 before merging, then run `--regenerate-all-summaries` before deploying to production.
