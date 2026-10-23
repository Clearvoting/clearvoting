# T7.4 review — Bill atomic switch (commit 1da63b6)

## Summary

The commit does what the plan asks. `static/js/bill.js` and `static/js/vote.js` match the plan's Step 7 and Step 8 code exactly (checked with a diff). The `/bill` route, `_bill_meta(page)`, `_bill_payload`, the `/ai-summary` allowlist, `annotate_roll_call_members` and the always-deepcopy in `votes.py` all match Steps 4–5 as written. The `bill.html` shell is byte-identical to `member.html` apart from the title, `<main>` and the script lines. Its masthead and footer/dialog match `index.html` too, except for the `aria-current` on Home, which correctly stays off on the bill page. The four scripts load in the required order, with no inline script and no `on*` handlers.

All four deviations hold up:
- **Test regex fix.** The comment-stripping fix (`//[^\n]*`) is correct. Under `re.S` the plan's `//.*` swallowed the rest of the file, so the test could not pass even against the plan's own vote.js.
- **Dropped `.rc-seat` rule.** Dropping the duplicate rule changes nothing on the page. T2.1 declares it at line 137, and all 144 `.rc-seat` spans sit inside `table.rc`, which sets the UI font.
- **Merged `.full-title p`.** Its declarations are identical to the rule it was merged into.
- **Imports.** Only the names that were missing were added.

## Verification (run by the reviewer)

- **Tests.** Full suite: 1321 passed, 3 skipped. All three skips are conditional and designed: fonts wait for T8.3, and the two old member.js/bill.js h1 checks are superseded now that both pages are server-rendered.
- **`scope_check.py static/*.html`:** exit 0 (bill.html: 124 names).
- **Step 12 curl checks, on a fresh server with port 8011 freed first.** Every line matched:
  - `1 1 1` for the three phase-gate bills.
  - The four module h2s: your-reps-h, by-state-h, what-h, facts-h.
  - Show full title: 1/1.
  - Unknown bill: 404.
  - 117-hr-1 ai-summary: `{"available":false} 404`.
  - 119-hr-3944 ai-summary: `['one_liner','provisions']`.
  - 0 party hits in the 119-hr-4795 bill payload.
  - 118-hr-21: 1 rc-block + 56 rc-more; warm time to first byte 0.003s.
  - `2 2 2` for 3233, 7 and 6126.
  - `/api/votes/house/119/1/99`: `True True`.
  - Other checks: the page's CSP is still `script-src 'self'` and `img-src 'self' https://www.congress.gov`, `type=zz` returns 404, and the page title is `H.R. 4795 — … | ClearVoting`.
- **Rendered markup the new scripts depend on.** `details.rc-all` carries `data-url` and `data-caption`, and its search box and Show menu (`.rc-all-q`, `.rc-all-show`) each have a label. `details.rc-more` carries `data-chamber`, `data-url` and `data-current`, and has `.state-tallies li[data-state]` and `.rc-groups`. Rows carry `data-key`, `data-position` and a `.party` span. `.party-toggle` is present.
- **Scroll-width smoke, both runs (bills, then the prime-ny4 remembered-home pages).** Every line reads `ok`: 375 on mobile, 1280 on desktop, with no JSERROR or CSP lines.
- **Visual.** In `bill-1499-mobile` (top 812px), "How did your representatives vote?" is inside the fold.
- **Safety.**
  - No new `innerHTML`. The one `insertAdjacentHTML` is the pinned sanitize sink.
  - `readHome()` checks the stored state against `COVERED_STATES`, so the `data-state="${home.state}"` selector cannot be injected.
  - The official-summary slot renders only when `official_summary` exists, so the "Loading summary…" text is always replaced.
  - A failed fetch resets `loaded` and shows `t('pageError')`.

## Verdict: pass

## Issues

- **P2 — static/css/site.css (budget, affects T8.3).** site.css is 30,713 bytes against the 30,720 test cap (7 bytes to spare). T8.3 Step 6 adds about 3.3 KB of `@font-face` rules to the same file and says the file must still be at or under 30,720 bytes. As planned, T8.3 cannot pass `test_site_css_exists_and_stays_under_30_kb`. Fix: this needs an orchestrator/plan decision before T8.3, not a change to this commit. Options: raise the §6.7 budget, put the `@font-face` block in its own small stylesheet, or trim site.css elsewhere.
- **P2 — static/css/site.css:329 (`.bill-header .kicker .seal { margin-left: var(--s2); }`, verbatim from the plan).** On 375px the two seals wrap onto their own lines under the kicker. The left margin then indents them about 8px from the kicker text (visible in bill-1499-mobile). This is cosmetic only. Fix, in a later polish pass: space the seals with flex/inline `gap` or `column-gap` on the kicker instead of `margin-left`.
- **P2 — tests/test_feedback.py:256–262 (and :248–253).** `test_old_bill_script_renders_the_title_as_h1_inside_bill_header` and its member twin now always skip, because both pages are server-rendered. They are dead tests. Fix: delete both in the Phase 9 retirement cleanup, where the old stylesheet check at :265 already expects the retirement.
