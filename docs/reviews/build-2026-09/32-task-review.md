# T9.1 review — §6.9 browser gates, then retire styles.css / broadsheet.css / viz.js

Commits reviewed: 61cfd53 (step 4 landmarks + feedback button), 4309756 (step 6 targets/scroll fixes), beb7c0d (deletion + pytest guards).

## Summary

The task does what the plan and spec ask.

- **gates.mjs:** it is byte-identical to the plan's step 2 block. I extracted the block from the plan and diffed it. `package.json` pins `axe-core` 4.10.3.
- **Step 4 markup:** the vote card is now `<section class="vote-card" aria-labelledby="latest-vote-h" data-ssr="1">` and the fact box is `<section class="section fact-box" aria-labelledby="facts-h">`. The fact box keeps its T7.1 `.section` class. That deviation is correct: the plan's pattern would have missed it. `app.js` now uses the `section.vote-card` selector. The `.feedback-btn` is the last child of `<footer class="site-footer">` in all eight shells. No `aside` is left in app, static or tests.
- **Step 6 fixes:** each one follows the triage table. Tap-size rules go on the control's own class. Standalone links got a class; this rule applies to the methodology source URLs, which sit in their own `<p class="meta">`, and to the sponsor `<dd>` link, which is the only content in its cell. No sentence link was inflated. The chip got `white-space: normal` on its base rule, and no rule was changed only inside a breakpoint. No new `innerHTML`, no inline script, no copy change and no URL change. Folding the six fixes into one commit breaks the one-commit-per-fix rule. The 30 KB budget forced it, it is documented, and I accept it.
- **Step 7 test block:** it matches the plan verbatim, and the imports were added.
- **Step 9 deletion:** `static/css` now holds only `site.css`, and `static/js` holds exactly the seven expected enhancers.

## Verification (run by the reviewer)

- **pytest:** 1421 passed, 2 skipped.
- **scope_check.py:** exits 0 on all eight shells.
- **Server on :8011:** I freed the port first, then started it fresh.
  - `styles.css`, `broadsheet.css` and `viz.js` all return 404, with `cache-control: public, max-age=60`.
  - `site.css` returns `public, max-age=31536000, immutable`.
  - The phase-gate grep over `static` and `app` exits 1, so nothing references the old files.
  - The vote-card and fact-box `<section>` markup renders as the plan says.
  - The feedback button sits inside the footer on all 8 pages (count 1 on each).
  - The literal `<title>` is present.
- **`node gates.mjs` (full default set, after the deletion):** GATES PASSED.
  - tokens 20/20, contrast 25/25, status 88/88, scroll 88/88, fonts 84/84, targets 84/84
  - decor 84/84, floating 63/63, console 84/84, fold 13/13, axe 42/42, dialog 16/16
- **shoot.mjs smoke:** covered home, member, bill hres-354, bill 118-hr-21, methodology and 404. Every line is `ok`: mobile scrollWidth=375, desktop scrollWidth=1280. No JSERROR or CSP lines. The 404 captures carry only the expected "404 document" console note.
- **Saved runner output:** `tools/shots/gates-out/gates.json` is the post-deletion run (all 691 rows ok), ready for T11.1.
- **Server:** stopped afterwards.

## Verdict: pass

## Issues

None blocking. Non-blocking notes:

- **P2 (informational), static/css/site.css:** only about 37 bytes are left under the 30 KB rules budget that `test_site_css_exists_and_stays_under_30_kb` enforces. The T10.x tasks will need to trim or merge rules before they add any. This is not a defect in T9.1. Flag it to the T10 author.
- **P2 (cosmetic), commit beb7c0d message:** the message says "3,848-line styles.css" because it copies the plan's text. The deleted file had 3,763 lines. No action is needed.
