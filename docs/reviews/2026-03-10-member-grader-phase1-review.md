# Review: Phase 1 -- Member Narrative Grader

**Commit:** 097b2dc
**Tests:** 189 passed
**Readiness:** Approve with P1s

## What shipped

- `app/services/member_narrative_grader.py` -- new grader with 6-check member-specific checklist (reading level, bias, data alignment, cherry-picking, structure, completeness)
- `sync.py` -- `sync_member_summaries` rewired to use `WriterGraderLoop` with the new grader; returns stats dict instead of count; learnings integration; backup on regenerate
- `tests/test_member_narrative_grader.py` -- 7 tests covering prompt content, data-aligned pass, data-contradiction fail, cherry-picking detection, malformed JSON handling
- `tests/test_sync.py` -- updated integration test mocks to match new writer-grader loop flow

## Issues Found

### P0 (blockers)

None.

### P1 (should fix)

**1. `WriterGraderLoop` type hint mismatch with `MemberNarrativeGrader`.**
`WriterGraderLoop.__init__` declares `grader: SummaryGrader` (the bill-specific class). `MemberNarrativeGrader` is a completely separate class -- not a subclass of `SummaryGrader`. This works at runtime because Python uses duck typing, and both classes expose the same `grade()` signature. But it is misleading and will break any future static analysis or type-checking (mypy/pyright). Fix: either (a) define a `Grader` protocol/ABC that both graders implement, or (b) change the type hint to `Protocol` with a `grade()` method. This is the right time to do it -- before Phase 4 adds a third consumer.

**2. Duplicate `GradeResult` and `_strip_code_fences` definitions.**
`member_narrative_grader.py` defines its own `GradeResult` dataclass and `_strip_code_fences` function, identical to those in `summary_grader.py`. These are now two separate classes (`MemberGR is SummaryGR` returns `False`). The `test_sync.py` integration test imports `GradeResult` from `summary_grader` to mock the grader return value -- it works only because the mock bypasses type checking. If any code ever compares `isinstance(result, GradeResult)` using the wrong import, it will silently fail. Fix: extract `GradeResult`, `GRADE_ORDER`, and `_strip_code_fences` into a shared module (e.g., `app/services/grader_common.py`) and import from there in both graders.

**3. Closure variable capture is correct but fragile.**
The explicit `_member_name = member_name` pattern (lines 744-752) correctly avoids the classic Python closure-over-loop-variable bug. Good. However, `_top_supported` and `_top_opposed` are sliced (`[:8]`, `[:6]`) both in the closure capture AND again in the `grader_context` dict (line 775-776). The double-slicing is harmless (slicing an already-sliced list is a no-op if it is already shorter) but it signals copy-paste rather than intentional design. Consolidate: slice once in the capture block, then reference the captured variables in both the closure and the grader context.

### P2 (nice to have)

**4. `GRADE_ORDER` defined but unused in `member_narrative_grader.py`.**
Line 20 defines `GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}` but nothing in the file references it. It is used in `writer_grader_loop.py` via the `summary_grader` import. If P1 #2 is addressed (shared module), this becomes moot. Otherwise, remove the dead definition.

**5. Tests mock the LLM response rather than testing grader logic.**
All async grader tests mock `client.messages.create` to return a pre-baked JSON response, then assert that the grader faithfully returns it. This proves the JSON parsing and error handling work, but does not test that the grader *prompt* would actually catch a data-misaligned narrative. This is the expected pattern for unit tests (matching `SummaryGrader` tests), but worth noting that there is no integration-level test that sends a bad narrative through the real prompt. This is fine for Phase 1 -- just flag it for Phase 5 validation.

**6. No rate-limit sleep between writer and grader API calls within the loop.**
`WriterGraderLoop.run()` calls `writer_fn` then `grader.grade` back-to-back, potentially 6 API calls per member (3 rounds x 2 calls). The outer loop in `sync.py` has `asyncio.sleep(rate_limit)` between members but nothing between rounds. For 80 members at worst-case 3 rounds, that is 480 API calls in rapid bursts. Unlikely to hit Anthropic rate limits at Sonnet pricing, but worth adding a small inter-round delay if this ever scales.

## Notes

- The grader checklist is well-designed. The 6 checks (reading level, bias, data alignment, cherry-picking, structure, completeness) map directly to the plan's requirements and cover the specific failure modes that motivated this work (narrative contradicting direction bars).
- The backup-on-regenerate addition (`shutil.copy2` to `member_summaries.backup.json`) is a nice operational touch not in the plan -- good deviation.
- The `stats` variable shadowing (outer `stats` dict vs inner `member_stats` rename on line 696) is handled correctly. The rename from `stats` to `member_stats` for the vote data avoids the collision with the tracking `stats` dict. Clean.
- Plan alignment is strong: all 3 sub-tasks (1.1, 1.2, 1.3) are implemented as specified. No scope creep, no missing pieces.

The P1s (#1 and #2) should be addressed before Phase 2, since Phase 2 will add the data brief to the writer and Phase 4 will add content-type scoping to learnings -- both of which will be cleaner if the shared types are already extracted.
