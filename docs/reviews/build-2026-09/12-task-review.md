# T2.2 review: static/js/site.js formatter twins and DOM builders (commit 8e7008c)

## Summary
The commit adds `static/js/site.js`, a classic script that no page links yet, and `tests/test_formatter_parity.py`, which is byte-identical to the plan's Step 2 text. Every name in the task's Produces list is present, and the export block matches the plan exactly.

The implementer changed three things from the plan's Step 4 draft. Each follows the plan's rule that Python is the source of truth:
- The question table was copied over from `render.QUESTION_CLASSES` using the Step 5 script.
- `resultPhrase`/`outcomeSentence` were rewritten as a line-for-line port of `render.result_phrase`/`render.outcome_sentence`. I read the two side by side: branch order, the tie rule, the impeachment/veto/adopt/concur/cloture/amendment branches, the "needed" suffixes and the nomination/Speaker handling all match.
- The small helpers (`displayName` split at the first comma, `formatDate` validation, `positionChip` trim and case) now behave like Python.

JS cannot see `render.py`'s row `threshold` column, so site.js derives it: `'2/3'` when the plain question contains "needed two-thirds". Against the current Python table that rule has 0 mismatches (checked with a script).

Safety: no innerHTML, outerHTML, insertAdjacentHTML, eval, document.title or style colour writes. All DOM goes through `el()`, `setAttribute` and text nodes. `<img>` is built only for `https://www.congress.gov/` URLs, and `rcTableRow` hrefs are limited to validated bioguide ids.

## Verification (run by the reviewer)
- Full suite: **791 passed**. `tests/test_formatter_parity.py`: **10 passed**, all 5 node output-parity tests included. These run over the synthetic rows, the fixture index and every real roll call.
- `node --check` passes. "no shell loads site.js yet" and "clean" were printed. The Step 7 one-liner printed exactly the expected line (`H.Con.Res. 108 | 113th | Charles E. Schumer | Sep 3, 2026 | Passed the House 237–169 | The House passed it, 237 to 169, on September 3, 2026.`).
- Server on :8011 (freed first, stopped after): `/api/health` 200. `/static/js/site.js` 200 `text/javascript`, 25,368 bytes. The home HTML does not reference site.js.
- No mobile scroll-width smoke was run, because no page loads this script yet.

## Verdict
**pass**

## Issues (all P2, non-blocking)
| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | tests/test_formatter_parity.py | `_py_question_rows` drops Python's `threshold` column. site.js infers the threshold from the plain question ("needed two-thirds" → 2/3). If render.py ever gives a row a threshold its plain text doesn't state, no structural test fails. Output parity would catch it only if some data row reached that branch. | Add one structural assert: every `render.QUESTION_CLASSES` row has `threshold == ('2/3' if 'needed two-thirds' in plain else None)`. It could go with T2.3's appends. |
| P2 | app/render.py:180 | A comment says "site.js twoThirdsNeeded (G2) tests the same alternation". site.js has no `twoThirdsNeeded`; the equivalent is `TWO_THIRDS_QUESTION_RE` inside `parseThreshold`. This task may not edit Python. | Change the comment to name `TWO_THIRDS_QUESTION_RE`/`parseThreshold` the next time a task touches render.py. |
| P2 | static/js/site.js:69 | `formatBillCode('hr', null)` returns `"H.R."`, but Python `format_bill_code('hr', None)` returns `"H.R. None"`. The parity inputs never pass a null number, so the test doesn't see it. The JS output is the better one. | Leave the JS as is. If it matters, make Python's `format_bill_code` treat `None` as `''` in a later render.py task. |
| P2 | static/js/app.js, bill.js, state.js, member.js | Those scripts also declare top-level `el` (and app.js declares `clear`, `ordinal`, `MONTHS`). Loading them with site.js on one page would throw a duplicate-declaration SyntaxError. Harmless now, because nothing loads site.js. | Already handled by the plan: later tasks rewrite those scripts, and the plan's combined no-duplicate-const check runs at line ~21314. Whoever links site.js first must remove the older helpers. |
