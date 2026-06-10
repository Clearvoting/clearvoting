# Review: Task 1 -- Add `one_liner` to AI Summary Prompt

**Commit:** `f3f5f3c` feat: add one_liner field to AI summary prompt and parsing
**Branch:** feat/member-summary-improvements
**Reviewer:** Staff Engineer (automated)
**Date:** 2026-03-08

---

## Plan Alignment

The commit matches the plan's Task 1 almost exactly: prompt updated to request three fields, parsing adds `one_liner` with a fallback, three new tests match the plan's spec. Commit message matches the plan verbatim.

**One unplanned change:** Six new impact categories were added to `IMPACT_CATEGORIES` (Energy, Foreign Affairs, Civil Rights, Economy, Defense, Labor). This is not described in the plan but is a sensible addition -- the existing list was clearly incomplete for the bill corpus. No issues here, just noting it.

## What Was Done Well

- Fallback logic (`provisions[0]` then `title`) is defensive and covers both missing-key and empty-string cases.
- Prompt is clear, provides examples, and fits the existing SYSTEM_PROMPT style (factual, no framing).
- Tests cover the happy path, the fallback path, and prompt content verification -- the three cases that matter.
- All 103 tests pass, including the 3 new ones. No regressions.

## Issues

### P1 -- Error path omits `one_liner`

The `JSONDecodeError` catch on line 93-95 returns early with:

```python
return {"provisions": ["AI summary temporarily unavailable"], "impact_categories": []}
```

This dict has no `one_liner` key. Any downstream code (Task 2's sync, Task 3's frontend) that reads `result["one_liner"]` from this path will get a `KeyError` or `undefined`. Should be:

```python
return {"provisions": ["AI summary temporarily unavailable"], "impact_categories": [], "one_liner": title}
```

This is not a blocker for Task 1 in isolation (the error path is rare and the dict is not cached), but it will become a real bug once Task 2 and Task 3 consume `one_liner`. Recommend fixing during Task 2 at the latest.

### P1 -- No test for the empty-provisions + no-one_liner edge case

The fallback line is:

```python
result["one_liner"] = result["provisions"][0] if result.get("provisions") else title
```

There is a test for missing `one_liner` (falls back to `provisions[0]`), but no test for the case where both `one_liner` and `provisions` are missing/empty, which should fall back to `title`. This is a real path since the AI could return `{"provisions": [], "impact_categories": []}`. A one-line test addition would cover it.

### Suggestion -- New categories lack test coverage

The six new categories in `IMPACT_CATEGORIES` are not checked by `test_impact_categories_defined`. Not blocking, but the test would be more useful if it validated the full list or at least spot-checked a new entry.

## Verdict

**Approved with one required fix before Task 2.** The `JSONDecodeError` early-return must include `"one_liner": title` to avoid downstream KeyErrors. The missing edge-case test is recommended but not blocking.
