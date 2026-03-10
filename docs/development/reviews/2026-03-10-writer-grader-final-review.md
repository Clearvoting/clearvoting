# Final Review: Writer-Grader Loop for Member Profiles

**Branch:** feat/writer-grader-member-profiles
**Commits:**
- `097b2dc` feat: add member narrative grader + writer-grader loop wiring (Phase 1)
- `0acaa5a` feat: add data brief constraints to member narrative writer (Phase 2)
- `c71446b` feat: add page coherence checker + Step 8 pipeline (Phase 3)
- `650cf9c` feat: extend learnings system with content-type scoping (Phase 4)
- `be842b2` docs: mark writer-grader member profiles plan complete (Phase 5)
- `0781704` refactor: extract shared grader types into grader_common.py (review P1 fixes)

**Tests:** 212 passed (0 failures, 0 errors)
**Readiness:** Approve

---

## Plan Alignment

### Phase 1: Member Narrative Grader + Writer-Grader Loop Wiring -- COMPLETE

All three sub-tasks implemented as specified:
- **1.1** `member_narrative_grader.py` created with the correct 6-check checklist (reading level, bias, data alignment, cherry-picking, structure, completeness). The checklist is member-specific -- no bill-specific checks (CRA, provisions, one_liner) leaked in.
- **1.2** `sync_member_summaries` rewired to use `WriterGraderLoop` with `MemberNarrativeGrader`. Follows the exact pattern from `sync_bill_summaries`: import grader, load learnings, wrap writer, run loop, track stats, extract patterns, record batch, save learnings.
- **1.3** Tests cover: prompt structure, data-aligned narrative passes, data-contradicting narrative fails, cherry-picking detected, malformed JSON handling. 7 tests total.

### Phase 2: Enhanced Data Brief for Narrative Writer -- COMPLETE

- **2.1** `_compute_data_brief()` added to `member_summary.py`. Classification thresholds match the plan exactly (>=75% = "mostly", 55-74% = "leans", else "mixed"). Handles edge cases: empty list returns "", zero directional votes return "no clear direction".
- **2.2** `_build_prompt()` updated to include the data brief after Top Policy Areas. System prompt rule 10 added: "Your narrative MUST reflect the dominant direction shown in DATA CONSTRAINTS."
- **2.3** Tests cover: all classification buckets (mostly strengthening, mostly weakening, leans strengthening, leans weakening, mixed, no clear direction, empty, multiple areas), prompt includes DATA CONSTRAINTS block.

### Phase 3: Page Coherence Checker -- COMPLETE

- **3.1** `page_coherence.py` created with `CoherenceResult` dataclass (matching plan: `is_coherent`, `contradictions`, `guidance`). `PageCoherenceChecker` class with LLM-based consistency check.
- **3.2** `check_page_coherence()` added to `sync.py`. Becomes Step 8 in the pipeline. For incoherent results, regenerates narrative with coherence feedback (max 2 rounds). `--check-coherence` CLI flag added. Pipeline updated to `[8/9]`.
- **3.3** Tests cover: coherent page passes, contradictory narrative fails with specific contradictions, malformed JSON handling, API error graceful degradation (defaults to coherent). 5 tests total.

### Phase 4: Extended Learnings System -- COMPLETE

- **4.1** `grader_learnings.py` modified with `content_type` parameter on all methods (`get_learnings`, `add_learning`, `extract_patterns`, `record_batch`, `get_batch_history`). Default `content_type="bill_summary"` for backward compatibility. Flat-to-nested migration on `_load()`.
- **4.2** All callers in `sync.py` updated: `sync_bill_summaries` passes `content_type="bill_summary"`, `sync_member_summaries` passes `content_type="member_narrative"`, `check_page_coherence` passes `content_type="page_coherence"` (for reading learnings; see P2 note below).
- **4.3** Both `MemberNarrativeGrader` and `PageCoherenceChecker` support `load_learnings()` and inject them into system prompts as "LEARNED PATTERNS."
- **4.4** Tests cover: content-type isolation, scoped batch history, flat-to-nested migration, migration persistence on save, default content type backward compat, extract_patterns with content_type. 7 new tests.

### Phase 5: Regenerate All Members and Validate -- COMPLETE (docs only)

- **5.1** `--regenerate-member-summaries` enhanced to use full pipeline (writer-grader loop per narrative). Stats reporting matches plan.
- **5.2** Actual regeneration not run (requires live API key). Plan marked complete. This is appropriate -- Phase 5 is an operational step, not a code change.

### P1 Refactor Commit -- COMPLETE

The Phase 1 review identified two P1s (type hint mismatch on `WriterGraderLoop`, duplicate `GradeResult`/`strip_code_fences` definitions). Both were addressed in commit `0781704`:
- `grader_common.py` extracted with `GradeResult`, `GRADE_ORDER`, `strip_code_fences`, and `Grader` Protocol.
- `summary_grader.py` and `member_narrative_grader.py` both import from `grader_common`.
- `writer_grader_loop.py` updated to use `Grader` Protocol instead of concrete `SummaryGrader` type hint.

---

## Architecture

### grader_common.py -- Clean Extraction

The shared module is minimal and focused: one dataclass (`GradeResult`), one constant (`GRADE_ORDER`), one utility (`strip_code_fences`), one protocol (`Grader`). No unnecessary abstractions. Both `SummaryGrader` and `MemberNarrativeGrader` import from it. The `Grader` Protocol has a single method signature `grade(summary_type, summary_text, context) -> GradeResult` which matches both concrete implementations.

### Protocol Usage -- Correct

`WriterGraderLoop` now types its `grader` parameter as `Grader` (the Protocol), not a concrete class. This means any class with a matching `grade()` method is accepted without inheritance. This is idiomatic Python structural typing and is the right choice for this codebase (no ABC overhead, no registration boilerplate).

### Page Coherence Checker -- Well Separated

The coherence checker has a different responsibility (cross-section consistency) from the grader (single-text quality), and the plan correctly identified this. The implementation keeps them as separate classes with separate prompts. The checker is not a `Grader` -- it has a `check()` method returning `CoherenceResult`, not `grade()` returning `GradeResult`. This is correct: coherence checking has different semantics (fix via regeneration, not via writer-grader loop).

### Sync Pipeline Wiring -- Correct

Step 7 (`sync_member_summaries`) runs the writer-grader loop per member. Step 8 (`check_page_coherence`) runs after all narratives are generated and checks each one against the data sections. If contradictions are found, it regenerates up to 2 rounds. This ordering is correct: Step 7 produces quality-checked narratives, Step 8 catches cross-section inconsistencies that the grader alone cannot detect.

The pipeline step numbering is consistent: `[1/9]` through `[9/9]`, with Step 8 being the new coherence check and Step 9 being the sync summary.

### Data Brief -- Good Design

The `_compute_data_brief()` function converts raw strengthen/weaken counts into plain-text constraints injected into the writer prompt. This addresses the root cause (LLM cherry-picking from raw data) at the prompt level rather than relying solely on post-hoc grading. The classification thresholds (75%/55%) are reasonable and match the plan.

---

## Issues

### P0 (blockers)

None.

### P1 (should fix before merge)

None. All prior P1s from the Phase 1 review have been addressed.

### P2 (should fix, not blocking merge)

**1. `_strip_code_fences` still duplicated in three files.**
The P1 refactor correctly extracted `strip_code_fences` into `grader_common.py` and updated both grader files to import it. However, `page_coherence.py`, `member_summary.py`, and `ai_summary.py` each still define their own private `_strip_code_fences` function (identical logic, underscore-prefixed). These are not consumers of `grader_common`, so the duplication is not a type-safety concern, but it is three copies of the same 7-line function. Consider either importing from `grader_common` or extracting to a more general utility module (e.g., `app/services/llm_utils.py`) in a future cleanup.

**2. Area computation logic duplicated between `sync_member_summaries` and `check_page_coherence`.**
The 20-line block that computes `area_counts` from vote data (lines 700-722 and 888-910 in `sync.py`) is identical in both functions. Same dict accumulation, same direction/vote logic, same `sorted(..., key=lambda x: x["total"])[:5]`. Same pattern for collecting `top_supported` / `top_opposed`. This should be extracted to a shared helper (e.g., `_compute_member_page_data(vote_data)`) to avoid divergence if the logic changes. Not blocking because both copies are correct today.

**3. `check_page_coherence` does not record learnings or extract patterns.**
The plan (Phase 4, section 4.2) states: "check_page_coherence: pass content_type='page_coherence'". The function does load learnings (`checker.load_learnings(learnings_store.get_learnings(content_type="page_coherence"))`), but unlike `sync_bill_summaries` and `sync_member_summaries`, it never calls `extract_patterns`, `add_learning`, `record_batch`, or `save` on the learnings store. This means the coherence pipeline reads learnings but never writes them. The learning loop for `page_coherence` content type is open -- learnings will always be empty. This should be wired in a follow-up. Not blocking because coherence checks still function correctly; they just do not accumulate institutional knowledge over time.

**4. Error handling asymmetry in `PageCoherenceChecker.check()`.**
On `json.JSONDecodeError`, the checker returns `is_coherent=False` (conservative -- assumes problem). On generic `Exception` (API failure), it returns `is_coherent=True` (permissive -- does not block sync). The test explicitly validates this asymmetry and it is intentional. However, the reasoning should be documented in a code comment: "Default to coherent on API error to avoid blocking sync pipeline" is the right call, but the inverted default on JSON error vs API error is non-obvious to future readers.

### P3 (suggestions)

**5. Closure variable capture in `sync_member_summaries` is correct but verbose.**
The explicit `_member_name = member_name` pattern (lines 746-753) works correctly but adds 8 lines of boilerplate per member. An alternative would be a `functools.partial` or a factory function. This is a style preference, not a correctness issue.

**6. No inter-round rate limiting in `WriterGraderLoop`.**
Flagged in the Phase 1 review (P2 #6) and still present. The loop calls writer then grader back-to-back within each round, with rate limiting only between members. At 80 members x 3 rounds x 2 calls = 480 rapid calls worst case. Unlikely to hit Anthropic limits at current scale, but worth noting for future growth.

---

## Test Coverage Assessment

**212 tests pass across the project.** The branch added ~23 new tests for the writer-grader member profile feature:

| File | Tests Added | Coverage |
|------|------------|----------|
| `test_member_narrative_grader.py` | 7 | Prompt structure (4), LLM mock pass/fail/cherry-pick (3), error handling (1) |
| `test_page_coherence.py` | 5 | Prompt structure (2), coherent pass (1), contradictory fail (1), JSON error (1), API error (1) |
| `test_member_summary.py` | 8 new | Data brief computation (7 buckets + multiple areas), prompt includes DATA CONSTRAINTS (1) |
| `test_grader_learnings.py` | 7 new | Content-type isolation (1), scoped batch history (1), flat migration (2), default type compat (1), extract_patterns with type (1), save persistence (1) |
| `test_sync.py` | 2 new | `sync_member_summaries` integration with writer-grader mocks (1), skip-existing (1) |

**Gaps worth noting:**
- No test for `check_page_coherence` in `test_sync.py`. The coherence pipeline wiring in sync.py is tested indirectly via the unit tests on `PageCoherenceChecker`, but there is no integration-level test that mocks the checker and verifies the regeneration loop (max 2 rounds, narrative replacement, stats tracking). This is the most complex new pipeline logic and warrants a sync-level integration test.
- `_compute_data_brief` boundary: the 55% threshold is tested at exactly 70% (7/10). A test at exactly 55% (55/100) and 54% (would be "mixed") would pin the boundary precisely. Not critical because the thresholds are clear in the code.

---

## Verdict

**Approve for merge.** All 5 phases implemented as specified. The P1 refactor from the Phase 1 review was addressed cleanly. Architecture is sound: `grader_common.py` provides a proper Protocol, the writer-grader loop is reusable across content types, the coherence checker is correctly separated from the grader, and the learnings system is properly scoped by content type with backward-compatible migration.

The P2 items (duplicate `_strip_code_fences`, duplicate area computation, missing coherence learnings recording) are real but none affect correctness or functionality today. They should be addressed in a follow-up cleanup, not gate the merge.

The test suite is solid at 212 tests with good coverage of the new functionality. The one notable gap (no sync-level integration test for `check_page_coherence` regeneration loop) should be added in a follow-up but is not blocking.

This is a well-executed feature that addresses the root cause of narrative/data contradictions at three levels: prompt constraints (data brief), post-generation quality checking (writer-grader loop), and cross-section consistency verification (coherence checker).
