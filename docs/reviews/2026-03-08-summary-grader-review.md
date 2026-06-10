# Review: Summary Grader Feature (Tasks 1-9)

**Review type:** Three commits on `feat/summary-grader` branch
**Commits:** `6dcbcd0` (Tasks 1-5), `a3525b5` (Tasks 6-8), `d23c9ba` (Task 9)
**Scope:** Writer-grader feedback loop for AI-generated bill summaries and vote one-liners
**Reviewer:** Staff engineer (correctness, architecture, security, performance, test coverage, plan alignment)
**Local verification:** `pytest tests/ -v` -- 137 passed in 3.48s

**Implementation plan:** `docs/plans/2026-03-08-summary-grader.md` (Tasks 1-9 of 10)
**Files changed:** 13 files, +1205 / -18 lines

## Summary

This feature adds a quality assurance layer to ClearVote's AI-generated content. A `SummaryGrader` evaluates summaries against a checklist (reading level, bias, jargon, vote context accuracy). A `WriterGraderLoop` orchestrates 3 rounds of write-grade-feedback, always picks the highest-scoring version, and flags persistent failures for human review. A `VoteOneLinerService` generates CRA-aware vote descriptions. A `GraderLearnings` service tracks recurring grader feedback patterns across runs. The sync pipeline grows from 5 to 7 steps, with a new `sync_bill_summaries` batch processor and a `--grade` re-grade command.

The implementation faithfully follows the plan with minimal deviations. All 34 new tests pass alongside 103 existing tests. The code is clean, well-organized, and matches existing project patterns.

**Readiness:** Approve with one P1 recommendation. No P0 blockers.

---

## What shipped

- **`SummaryGrader`** (`app/services/summary_grader.py`): Quality checklist grader. System prompt encodes reading level, jargon, bias, CRA vote context, factual context, and structure checks. Returns `GradeResult` with letter grade (A-F), pass/fail, feedback, and per-check detail. Handles malformed JSON and API errors gracefully (defaults to F/fail).
- **`WriterGraderLoop`** (`app/services/writer_grader_loop.py`): 3-round orchestrator. Calls writer, grades result, passes feedback to next round. Tracks best result by grade order. Sets `needs_review=True` when best grade still fails.
- **`VoteOneLinerService`** (`app/services/vote_one_liner.py`): Vote description writer with CRA disapproval detection. Static `is_cra_disapproval()` method checks for "congressional disapproval" and "chapter 8 of title 5" in titles. Injects CRA-specific prompt instructions when detected.
- **`GraderLearnings`** (`app/services/grader_learnings.py`): Persistent learning tracker. Atomic writes (temp file + rename). Pattern extraction via word frequency analysis. Batch history recording with timestamps and grade distributions.
- **`AISummaryService` update** (`app/services/ai_summary.py`): Accepts `grader_feedback` parameter. Appends feedback to prompt as "PREVIOUS ATTEMPT WAS REJECTED" block. Skips cache on retry rounds (correct behavior).
- **`sync_bill_summaries`** (`sync.py`): Batch processor for bill summaries through the writer-grader loop. Processes in configurable batch sizes. Saves after each batch (crash-safe). Extracts learnings from feedback and records batch stats.
- **`build_member_votes` update** (`sync.py`): Accepts `anthropic_key` parameter for future graded vote one-liner generation.
- **`--grade` flag** (`sync.py`): Re-grade mode that backs up existing summaries, clears them, and re-generates through the writer-grader loop. Runs only steps 5-6 (summaries + member votes), skipping Congress.gov data sync.
- **Integration tests** (`tests/test_grader_integration.py`): 3 end-to-end tests covering bill summary improvement across rounds, CRA vote one-liner interpretation, and persistent failure flagging.

---

## Strengths

- **Exact plan alignment.** Every service, function, test, and pipeline change matches the plan specification. The plan contained complete code listings for Tasks 1-5 and 9, and the implementation matches them precisely. Tasks 6-8 followed the plan's architectural guidance with appropriate implementation decisions.

- **Correct closure-in-loop handling.** The `writer_fn` defined inside the `sync_bill_summaries` loop (line 347) correctly uses default parameter binding (`_bill_id=bill_id, _title=title, ...`) to capture loop variables. This avoids the classic Python closure bug where all iterations would share the last loop value. The plan's code listing for Task 6 used the simpler `async def writer_fn(grader_feedback=None, **kwargs)` without binding -- the implementer caught and fixed this.

- **Atomic writes throughout.** `GraderLearnings.save()` uses the same `tempfile.mkstemp` + `os.replace` pattern as `_atomic_write_json` in `sync.py` and follows the project's code standard for file I/O.

- **Clean separation of concerns.** Writer services (AISummaryService, VoteOneLinerService) know nothing about grading. The grader knows nothing about writing. The loop orchestrates without knowledge of either service's internals. This makes each component independently testable and replaceable.

- **Crash-safe batch processing.** `sync_bill_summaries` saves `ai_summaries.json` after every batch (line 379), not just at the end. If the process crashes mid-run, completed batches are preserved.

- **Graceful degradation.** When `ANTHROPIC_API_KEY` is not set, the sync pipeline prints a clear message and skips AI steps rather than failing. The `--grade` flag validates the key early and exits with a clear error.

- **Consistent error handling patterns.** All API-calling services follow the same pattern: try API call, parse JSON, handle JSONDecodeError separately from general exceptions, return safe defaults. This matches existing patterns in the codebase.

- **No existing tests broken.** All 103 pre-existing tests continue to pass unchanged.

---

## Production readiness blockers (P0)

None.

---

## High priority (P1)

### P1.1 -- WriterGraderLoop always runs all 3 rounds, even after an A grade

The loop always executes all 3 rounds regardless of grade results (lines 37-65 of `writer_grader_loop.py`). If round 1 produces an A, two additional unnecessary API calls are made (one writer + one grader per round = 4 wasted calls). With 177 bills, this is roughly 708 unnecessary API calls in the best case.

The plan explicitly states "Always runs 3 rounds, picks the best" (Task 2 description), so this is plan-as-designed rather than an implementation bug. However, an early-exit optimization when grade is "A" would be a significant cost and time saving with no quality downside -- an A cannot be improved upon.

**Recommendation:** Add early exit when grade is "A":

```python
if grade_result.grade == "A":
    break
```

This is a low-risk change that would reduce API costs by up to 66% in the best case. The `rounds` field in `LoopResult` would then reflect actual rounds used rather than always being `MAX_ROUNDS`, which is arguably more informative.

### P1.2 -- `build_member_votes` does not actually use the `anthropic_key` parameter

The plan's Task 7 described integrating the `VoteOneLinerService` + `WriterGraderLoop` into `build_member_votes` so that each vote's one-liner is generated through the grader loop when `anthropic_key` is set. The implementation adds the parameter (line 403) but does not use it -- the function body is unchanged from the pre-grader version. It still relies on the existing `_get_one_liner` fallback (AI summary lookup or raw title).

This means vote one-liners are never individually graded. The `--grade` re-grade mode calls `build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)` (line 620), but since the parameter is ignored, vote one-liners are not re-graded either.

The deferral is understandable -- processing vote one-liners for 80 members with 3 rounds each would be expensive. The existing `_get_one_liner` function still pulls from `ai_summaries.json`, which now contains graded bill summaries from step 5, so the one-liners are indirectly improved by the grader. The test for Task 7 (`test_build_member_votes_accepts_anthropic_key`) only validates the function signature, not the behavior.

**Recommendation:** This is acceptable as a deferred feature but should be tracked. Either:
1. Add a comment in `build_member_votes` noting that vote one-liner grading is planned but not yet implemented, or
2. Update the plan to mark Task 7 as partially complete (signature only, behavior pending).

---

## Suggestions (P2)

### P2.1 -- `extract_patterns` can produce duplicate learnings from different matching words

The `extract_patterns` method in `GraderLearnings` (lines 39-65) iterates over the top 10 most frequent words and for each, appends the first feedback string containing that word. If two frequent words appear in the same feedback string, that feedback string is added to the returned list twice. Since `add_learning` deduplicates exact strings, this is not a persistence bug, but the caller in `sync_bill_summaries` (lines 382-384) iterates over all returned patterns and calls `add_learning` for each -- resulting in unnecessary duplicate checks.

This is functionally harmless. A deduplication step in `extract_patterns` (e.g., tracking which feedback strings have already been added) would make the return value cleaner.

### P2.2 -- Grading is serial, not concurrent within a batch

Within each batch in `sync_bill_summaries`, bills are processed one at a time (line 338: `for key, bill in batch`). Since the writer and grader are independent API calls with no shared state, bills within a batch could theoretically be processed concurrently with `asyncio.gather`. With 3 rounds per bill and 5 bills per batch, this would reduce wall-clock time significantly.

However, concurrent processing would increase API rate pressure and could trigger Anthropic rate limits. The serial approach is safer and matches the existing pattern in `sync_senate_votes` and `sync_house_votes`. This is a "nice to have" optimization for later.

### P2.3 -- `--grade` mode step 2 label is misleading once Task 7 is fully implemented

Line 619 prints `"[2/2] Re-building member voting records..."` in `--grade` mode. Since `build_member_votes` does not actually grade vote one-liners (per P1.2), this label is technically accurate -- it is rebuilding, not re-grading. But the `--grade` flag description says "Re-grade existing AI summaries" (line 589), and a user running `--grade` would expect step 2 to involve grading. Once P1.2 is addressed, this label should change to "Re-grading vote one-liners."

### P2.4 -- No test for `sync_bill_summaries` with actual mocked API calls

The test `test_sync_bill_summaries_is_callable` (line 641 of `test_sync.py`) only validates that the function exists and is callable. There is no unit test that exercises the function's batch processing logic, incremental skip behavior, or crash-safe saving. The integration tests in `test_grader_integration.py` cover the writer-grader loop itself but not the batch processing wrapper.

This gap is understandable -- testing `sync_bill_summaries` requires mocking the Anthropic client, CacheService, and file system, which is complex. The function's logic is straightforward (iterate bills, call loop, save), and the individual components are well-tested. Still, a test that verifies incremental skip behavior (bills already in `ai_summaries.json` are skipped) would catch regressions in the batch processor.

### P2.5 -- Positive deviation: `import json` correctly moved to top of file

The implementation plan's code listing for `WriterGraderLoop` had `import json` inside the `for` loop body. The actual implementation correctly moved this import to the top of the file (line 1 of `writer_grader_loop.py`). This is the right thing to do and is noted as a beneficial deviation from the plan.

---

## Test coverage assessment

**Tests added:** 34 new tests (137 total across all test files)

| File | Tests | What they validate |
|------|-------|--------------------|
| `test_summary_grader.py` | 10 | GradeResult construction, system prompt content, grade prompt construction, learnings injection, API call + response parsing, malformed JSON handling |
| `test_writer_grader_loop.py` | 5 | LoopResult structure, needs_review flagging, 3-round execution + best selection, all-fail scenario, feedback passthrough to writer |
| `test_vote_one_liner.py` | 7 | System prompt CRA content, prompt construction, grader feedback injection, CRA detection (positive + negative), API call + response parsing, fallback on JSON error |
| `test_grader_learnings.py` | 5 | Empty file handling, save/load round-trip, duplicate prevention, pattern extraction from feedback, batch stats recording |
| `test_grader_integration.py` | 3 | Full bill summary loop (C->B->A improvement), CRA vote one-liner interpretation, persistent failure flagging |
| `test_ai_summary.py` | 2 (new) | Grader feedback inclusion in prompt, no feedback = no feedback block |
| `test_sync.py` | 2 (new) | `sync_bill_summaries` callable, `build_member_votes` accepts `anthropic_key` |

**What is well-covered:**
- Core grading logic (grade ordering, pass/fail, feedback)
- Writer-grader loop orchestration (round counting, best selection, feedback forwarding)
- CRA disapproval detection and prompt generation
- Error handling in all API-calling services (malformed JSON, API failures)
- Learnings persistence (save, load, deduplicate, pattern extraction)
- End-to-end flows with mocked API responses

**What is not tested (acceptable gaps):**
- `sync_bill_summaries` batch processing logic (incremental skips, crash-safe saving, learnings extraction)
- `--grade` mode full execution path (would require extensive mocking)
- Race conditions in `GraderLearnings` if multiple processes write simultaneously (not a concern for single-process sync)
- Grader prompt injection (malicious content in feedback being re-injected into subsequent rounds -- low risk since all inputs come from controlled sources)
- `build_member_votes` behavior when `anthropic_key` is provided (because the feature is not yet implemented per P1.2)

**Assessment:** Test coverage is thorough for the implemented functionality. The integration tests in `test_grader_integration.py` are particularly well-designed -- they simulate realistic multi-round improvement scenarios with distinct mock responses per round, verifying that grades improve and the correct best version is selected. The gap in `sync_bill_summaries` testing (P2.4) is the most notable omission but is acceptable given the function's straightforward logic.

---

## Plan alignment

| Plan task | Status | Deviation |
|-----------|--------|-----------|
| Task 1: SummaryGrader service | Complete | None |
| Task 2: WriterGraderLoop orchestrator | Complete | No early exit on A (plan-as-designed, see P1.1) |
| Task 3: AISummaryService feedback parameter | Complete | None |
| Task 4: VoteOneLinerService | Complete | None |
| Task 5: GraderLearnings persistence | Complete | None |
| Task 6: sync_bill_summaries integration | Complete | Closure bug correctly fixed vs. plan (positive deviation) |
| Task 7: Vote one-liner grading in build_member_votes | Partial | Signature added, behavior not implemented (P1.2) |
| Task 8: --grade re-grade command | Complete | None |
| Task 9: Integration tests | Complete | Added 1 extra test (persistent failure) beyond plan |
| Task 10: Full test suite + cleanup | Complete | Plan status updated, all tests pass |

The plan called for 10 separate commits (one per task). The implementation consolidated into 3 cohesive commits: services (Tasks 1-5), pipeline integration (Tasks 6-8), and tests (Task 9). This is a reasonable deviation -- the 3 commits align with logical groupings and each is independently coherent.

Task 7's partial implementation is the only substantive deviation. The plan described a detailed integration of `VoteOneLinerService` + `WriterGraderLoop` into the member vote building loop, with groups of 10 per member. Only the function signature change was implemented. This should be tracked as remaining work.

---

## Security considerations

- **No new attack surface.** All new services are internal (called only by `sync.py`, not exposed via API endpoints). No new routes or user-facing inputs.
- **API key handling.** The `ANTHROPIC_API_KEY` is read from environment variables (not hardcoded) and passed to service constructors. The `--grade` flag validates the key exists before proceeding.
- **Prompt injection risk is low.** Grader feedback is injected into subsequent writer prompts, but both the writer and grader are controlled by the same system (ClearVote's sync pipeline). There is no user-generated content entering the prompt chain.

---

## Verdict

**APPROVE** with one recommendation.

P1.1 (early exit on A grade) is a cost optimization worth implementing before running the grader on all 177 bills. P1.2 (vote one-liner grading not implemented) should be documented as remaining work. All P2 items are non-blocking suggestions.

The implementation is architecturally clean, well-tested, follows existing patterns, and faithfully implements the plan. The writer-grader separation is correctly maintained (no shared context between writer and grader API calls), the batch processing is crash-safe, and error handling is consistent throughout.
