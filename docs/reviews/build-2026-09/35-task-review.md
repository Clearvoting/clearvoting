# T10.3 review: Print block (cut-first), commits cc6490c + 7b4ba70

## Summary

This is a re-review after the fix commit 7b4ba70, which addressed the first review of cc6490c (P1: printing opened lazy `rc-all`/`rc-more` and started a roll-call fetch; P2: the notify signup form printed).

**CSS (cc6490c), unchanged since the first review.** The print block matches spec §6.8:
- It hides `.masthead-nav, .edition, .actions, .strip, dialog, .feedback-btn, .site-footer nav`.
- It prints on `var(--card)` (#fff) and sets `a::after { content: none }`.
- It has no font-size.
- It sits just above `@media (min-width: 560px)`.

Two deviations were accepted in the first review: `!important`, which beats the later 880px rules, and the shortened comments, which keep the file under the 30 KB budget.

**JS fix (7b4ba70).** `initPrint` now:
- selects `details:not([open]):not([data-url]):not([data-summary-slot])`;
- rejects any `<details>` that contains a `<form>`.

I checked this against `bill.js`. Its three toggle-fetch listeners bind to `details[data-summary-slot]`, `details.rc-all` (which has `data-url`) and `details.rc-more` (which has `data-url`), so every fetch-on-toggle block is excluded. The only `<details>` with a form is `render.py`'s `notify-disclosure`. The fix adds no innerHTML, no inline script and no shell or title change, and `afterprint` still closes exactly what was opened. The new test pins the three exclusion markers and the render.py markup they rely on. It checks the source text rather than behaviour, which is the project's usual way of testing JS (there is no JS test runner).

## What I checked

- **Tests:** 1455 passed, 3 skipped.
- **`scope_check.py`:** exits 0 on all 8 shells.
- **Fresh server on :8011.** I freed the port first and stopped the server afterwards.
- **`print-probe.mjs` (fires `beforeprint`):**
  - Bill hr4795 opened only the 4 prefilled `state-group` blocks, made `requests=[]`, and `openAfter=0`.
  - Member S000148 opened only `more-rcs` and plain prefilled details, made `requests=[]`, and `openAfter=0`.
  - Home, `state?code=NY` and `state?code=WA` (the uncovered state, where the notify form is) opened nothing.
  - `state?code=NY&district=4` opened the "All N House districts" list. That only triggers loading the lazy `congress.gov` photos, which `img-src` allows; there is no JS fetch.
- **`print-check`:** `visible-chrome=[]` and `body=rgb(255, 255, 255)` on member, bill, home and `state?code=NY`.
- **`shoot.mjs`:** scrollWidth=375 on mobile and 1280 on desktop, with no JSERROR or CSP lines.

**Note on the implementer's smoke.** The implementer tested `/state/ny`, and that URL returns **404**. The "missing photo" console note was actually the 404 page. The real route is `/state?code=NY`, and I re-ran the checks there: all clean. Nothing needs changing in the code. Future smokes should use `/state?code=XX`.

## Verdict: pass

## Issues

| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | static/js/site.js (initPrint) | Because `data-url` is excluded, a collapsed `details.rc-more` now stays closed on paper, so its outcome, tally and per-state tally lines (already server-rendered) do not print. Only the caption prints. This follows the task's rule that "printing never starts a fetch", but the printout for secondary roll calls is thinner. | No action for this task. If fuller print output is wanted later, open `rc-more` for print while its loader ignores a print-driven toggle (for example, a flag that `initPrint` sets). |
| P2 | static/css/site.css (budget) | Carried over: the rules are at 30649 of 30720 bytes. T10.4 (`.strip`) will break `test_site_css_exists_and_stays_under_30_kb`. | Orchestrator: plan a trim or a budget change before T10.4. |
