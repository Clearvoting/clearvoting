# T11.1 review: browser gates at PR over every page and every fallback state

**Head reviewed:** 269b41c (redesign/2026-09, after merge 789609e and data regen 1539a7a). There is no new repo commit, because no gate failed. The work lives out of repo: `tools/shots/gates.mjs` and the evidence in `tools/qa/` and `tools/shots/gates-out-pr/`.
**Verdict:** pass

## What I checked (independently, on the current head)
- **Tests.** pytest: 1482 passed, 3 skipped, 0 failed. `scope_check.py static/*.html` exited 0. `git status --short` is empty. `git log HEAD..origin/main -- data/synced` is empty after a fresh fetch. `git log main..HEAD --grep="plan T11.1"` returns 0 lines, which is correct when no gate failed.
- **gates.mjs matches plan step 3 (a) to (f).** It has the 38-page `DEFAULT_PAGES` set, verbatim apart from the no-photo flag. The `DIALOG_NAMES`/`NOJS_NAMES` renames are in. So are the `SHIFT_OBSERVER` in `openPage`, `clsInfo`, the `cls` check (gated only on non-`home` pages) and the `thirdparty` check, and the `cls_info` key in the `gates.json` write. The earlier fix is kept: `openPage` removes `cv-home` on pages without `home:true`. That fix is correct, because localStorage is shared across one browser context.
- **Full gate set, re-run by me** into a scratch outdir against a freshly started uvicorn on :8011. It took about 4 minutes and ended `GATES PASSED`, `exit 0`, with the same counts as the implementer's log. Those are: tokens 20/20, contrast 25/25, status 156/156, cls 136/136 (34 first-visit pages × 4 widths), thirdparty 152/152, scroll 156/156, fonts/targets/decor/console 152/152, floating 114/114, nophoto 4/4, fold 13/13, axe 76/76 and dialog 16/16.
- **Evidence is fresh.** `gates-out-pr/gates.json` has ran_at 2026-09-26T11:40Z, which is after the last app/static/data commit (07:32 local = 11:32Z), so T11.3's stale-evidence guard will accept it. It has 1476 rows and 0 failures. `precheck.txt` ends `PRECHECK OK`. `cutfirst.txt` lists all six cut-first items as landed. `gates-summary.txt` names head 269b41c and ends `GATES PASSED`.
- **Statuses by curl.** `/state?code=ny`, `?zip=44101`, `?zip=abc`, `district=40` and `/member?id=W000832` return 200. `/state?code=OH`, `/member?id=X999999`, the unknown bill and the malformed bill return 404. The CSP header is unchanged: `script-src 'self'` and `img-src 'self' https://www.congress.gov`.
- **Scroll-width smoke.** I ran it on the four spine pages plus W000832. All 10 lines were `ok`: every mobile capture was scrollWidth=375 and every desktop capture 1280, with no JSERROR or CSP lines. I stopped the server afterwards, and port 8011 is free.

## Deviation assessment: the no-photo fixture
The real data no longer has a member without a photo: 0 of the members in members.json lack one after main's 2026-09 syncs. That left plan step 2's candidate swap with nothing to swap in. The implementer's adaptation is sound and stays within the task's scope:
- It changes only the out-of-repo harness. No site code or data changed.
- It sets `noPhoto: true` on `member-w000832-no-photo`. That makes the page-level route answer congress.gov photo requests with HTTP 404, so the page goes through the real §6.3 fallback: `site.js initPhotos`/`dropBrokenPhoto` removes the broken img and the initials show.
- `openPage` is shared by the layout, axe and dialog passes, so the no-photo state is covered in all three passes, not only layout.
- The new `nophoto` check confirms that no `.photo img` is left and that the header's `data-initials` is non-empty. That makes the gate prove the state instead of assuming it.
- The console-error exemption covers only congress.gov img URLs, and only on that one page.
- The server-side path for a member with no imageUrl is still covered by pytest (the WAHAB fixture).
- The precheck line fails and lists candidates if a photo-less member reappears, so the fixture cannot drift silently.

This is now the only way the no-photo state occurs in production: congress.gov failing the image. So the gate is arguably more realistic than before.

## Issues (none block the PR)
| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | tests/test_member_render.py:48 | The comment `# the one member with no photo in members.json` is stale: since the 2026-09 syncs, W000832 has a photo. The test builds its own dict, so its behaviour is unaffected. | Reword it to something like "a member with no depiction (fixture; the real data had one until the 2026-09 sync)". This can ride along with T11.2 or T11.3. |
| P2 | tools/shots/gates.mjs (info line) versus tests/test_static_assets.py | The gates info line reports site.css at 33892 raw bytes against a 30720 target, while the pytest budget (30719 per the T10.5 review) passes. The two use different measures, which the QA report could present as a contradiction. | In T11.2/T11.3, state which measure spec §6.7 means (for example gzip versus raw) in the QA report, or align the info line with the pytest measure. |
| P2 | tools/qa/gates-summary.txt | `thirdparty152/152 pass` has no space, because the plan's step 7 uses `padEnd(10)` and `thirdparty` is 10 characters. This is cosmetic only: T11.3 reads gates.json, not this file. | Optionally change it to `padEnd(11)` the next time the summary is regenerated. |
