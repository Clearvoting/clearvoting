# T7.3 review: site.js in-place ZIP lookup and bill slot fill (commit 69cc45c)

## Summary
The commit matches the plan exactly. A programmatic comparison found that all three JS blocks (the seven STRINGS keys, the bill-slot block and the export line) and the appended test block appear verbatim in `static/js/site.js` and `tests/test_formatter_parity.py`. Only those two files changed. The commit message matches Step 7 and ends with the Co-Authored-By line.

Spec compliance:
- §4.4 m2 (a)/(b): rows come from `/api/members/{state}/overview` through the shared `personRow`. Positions are read from the server `tr[data-bioguide]` rows, with no position fetch. A chamber without a roll call gets the "no recorded vote" line. The absent chip appears only when that chamber's roll call is rendered. Single, split, partial and none behave as the spec describes.
- §5.4 write rule 3: `rememberDistrict` is called only from `slotPick`, and `rewriteMastheadLink` runs after it. Split and partial lookups write nothing until a District button is pressed. Forget goes through the shared `rememberedLine`, and focus lands on the restored form's input.
- §8 items 10–11: the status line is written first, then focus moves to `#your-reps-h`.
- The house.gov link carries `rel=noopener`.

Safety checks:
- There is no innerHTML, insertAdjacentHTML, inline handler or document.title write.
- Selector interpolations use only the fixed chamber literals and bioguide IDs that pass the regex.
- The ZIP is validated to five digits before it is used in any URL.

Checks I ran:
- `node --check` is clean.
- scope_check.py exits 0.
- Full suite: 1290 passed, 2 skipped.
- Step 5 curls: the overview keys and member keys are as expected, `district` is an int, NY has 2 senators, 11201 is split [(NY,10,0.72),(NY,7,0.28)], 73949 is partial with 0.1367, and a malformed ZIP returns 400 with the spec detail.
- The grep finds `fillRepsSlot(` and `initZipInPlace(` only inside site.js. The data-chamber values the server renders are lowercase `house` and `senate`, which match the JS selectors.
- shoot.mjs on home, state?code=NY and member?id=G000602: all six captures print ok (1280 desktop, 375 mobile), with no JSERROR or CSP lines.
- The server was stopped afterwards.

The `.is-error` class has no CSS yet. That is expected, because the plan adds `.your-reps .status.is-error` in T7.4. bill.html does not load site.js until T7.4, so no current page is affected.

## Verdict
**pass**. It can ship as is. The notes below are optional P2 polish that the plan's verbatim code also contains. None of them blocks T7.4.

## Issues
| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | static/js/site.js (slotPick) | After a split or partial pick fills the rows, `#reps-zip-status` still says "ZIP 11201 spans two House districts. Choose yours below." This is a stale live-region line under the filled slot. | In `slotPick`, clear the status on success: `if (!filled) slotStatus(t('pageError'), true); else slotStatus('', false);`. |
| P2 | static/js/site.js (fillRepsSlot / slotPick) | `const home = stored \|\| picked` puts cv-home first. If `setItem` throws (for example quota) but an older cv-home is still readable, the slot draws the old district instead of the one just picked. | In `slotPick`, pass the pick through when `rememberDistrict(...)` returns null, and have `fillRepsSlot` prefer `picked` when it is given. Alternatively, accept this as a very rare edge case. |
| P2 | static/js/site.js (initZipInPlace) | The T2.3 behaviours are idempotent through `once()`, but `initZipInPlace` is not. A second call binds a second submit listener (two fetches and two writes) and a second pageshow listener. Today only T7.4's bill.js calls it, once. | Guard it with `if (!once('zip-in-place')) return;`, the same way the other inits do. |
