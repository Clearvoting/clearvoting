# T2.1 review — static/css/site.css (commit 203d5fa)

## Summary
The commit adds `static/css/site.css` (19,580 bytes) and `tests/test_static_assets.py`, and it changes nothing else. I diffed both files against the plan's Step 1 and Step 3 blocks and they match byte for byte. The out-of-repo harness (`tools/shots/harness/site-css.html`) also matches Step 5b exactly.

What I re-ran myself:
- **Full suite:** 781 passed.
- **Step 5 greps:** each of the two breakpoints appears once. `box-shadow:` appears on two lines only (`.state-link` and `.vote-card`). No shell links site.css yet.
- **Server on :8011:** `/api/health` returned 200, and `/static/css/site.css` returned 200 with `text/css; charset=utf-8`. The CSP header is unchanged. I stopped the server afterwards and port 8011 is free.
- **shoot.mjs home:** desktop scrollWidth=1280, mobile scrollWidth=375.
- **Harness widths.mjs:** 320, 375, 560, 880 and 1280 all ok, with siteCss=true, overflowing=[] and exit 0.
- **By eye:** at 320 the chip sits above the headline. At 560 it moves into the 6.5rem left column. The split row's button wraps under the row, and the roll-call chips are right-aligned.

Spec check (§6.1–§6.6, §8 items 4 and 7):
- The token values, type scale, spacing scale and the two radii match the spec.
- The kicker size inversion works out to the same sizes as the spec: 0.8125rem under 560 and 0.75rem from 560 up.
- The red tokens are used only by the chip and tally rules. Errors use the separate `--error` token.
- There is one `:focus-visible` ring and no `outline: none`. `scroll-margin-top: 56px`, `color-scheme: light` and the reduced-motion block are all present.
- The floating feedback button, and its `main` / `html` padding at 72px, exist only from 880 up.
- Controls meet 44px: the masthead and footer links, `.btn--secondary`, `.party-toggle`, `summary`, `.state-link`, `.arrow-link` and `.remembered-line a`. `.btn` and inputs are 48px, and `.person` is at least 64px. Pager links are left to the later task that adds `.pager a` (plan line 18718).

The file has no dead rules and no inline script, and it adds no innerHTML. The tests check what the stylesheet does, not how it is written: token values, declaration-level grep gates, and contrast recomputed from the token table.

## Verdict
**pass.** The only issues below are P2 follow-ups. None of them blocks this task.

## Issues
| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | static/css/site.css (`.masthead-nav a`) | In the harness at 320px, the nav wraps to two 44px rows ("About" drops to a second row). Spec §6.3 asks for "one 44px row". The spec's real labels at under 880 (Home · My representatives · About) add up to about 320px against a 288px content width, so they will probably wrap at 320 too. | When the first shell links site.css (T3.x), check the real nav at 320 with Inter loaded. If it wraps, tighten the under-560 base rule, for example `padding: 0 var(--s1)`, `letter-spacing: 0.04em`, and restore the current values in the 560 block. |
| P2 | tests/test_static_assets.py (`test_colours_only_through_tokens`) | The gate catches hex and rgb()/hsl() literals but not named colours (`white`, `black`, `red`, ...). F50 says no literal colours outside `:root`. | In a later task that appends to this file, also assert that no `color`, `background` or `border*` value outside `:root` uses a named colour other than `transparent`, `currentColor`, `inherit` or `none`. |
| P2 | static/css/site.css (`#feedback-modal::backdrop`) | `var(--scrim)` on `::backdrop` only resolves in browsers where `::backdrop` inherits custom properties (Chrome 122+, Firefox 120+, Safari 17.4+). In older browsers the dialog opens with no scrim. The dialog still works, so this is cosmetic. | Accept this degradation, or note it at QA. A literal value here would break the token-only colour gate. |
