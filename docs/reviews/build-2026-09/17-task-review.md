# T3.3 review — Home atomic switch (commit 6fc84d4)

## Summary
The home page is now built on the server and styled only by site.css. The commit follows the plan closely:
- `static/js/app.js` matches the plan's step-8 file byte for byte.
- The four test files match the plan's step-1 text.
- `notify.py`, `members.py`, `bills.py`, `search.py`, and the `main.py` functions `_home_content` and `serve_index` match steps 3–6.
- The `index.html` outline matches step 7: literal `<title>` and `</head>`, `<!--edition-->` in the masthead, `<!--content-->` in `<main>`, no inline script or `on*=` handler, footer links pointing to `/about`, the native feedback dialog, and the scripts site → app → feedback.

I re-ran every check myself:
- **Tests:** 953 pass. `scope_check.py` exits 0 (88 names on index.html).
- **Fresh server on :8011, now stopped:**
  - Page content: 6 bill rows, one "The latest vote" h2, the coverage line (150 members, since January 2021), and state chips CA 54, FL 29, NY 28, TX 39.
  - Edition line: correct at 39 days.
  - Stamp: 6 of 7, which equals 7 pending seals minus 1 on the card.
  - Footer: freshness is filled on the server.
  - Party-leak counts are 0 on `/`, `/api/bills?limit=7` and `/api/search/bills?q=act`.
  - Inline scripts: 0. `"stats"`: 0. Notify with CA returns 400. `/state?code=NY` still links styles.css.
  - TTFB is about 2.5 ms. The CSP header is `script-src 'self'` with `img-src 'self' https://www.congress.gov`.
- **Smoke:** `shoot.mjs` gives scrollWidth 375 on mobile and 1280 on desktop for both `/` and `/?q=housing`, with no JSERROR or CSP lines.
- **Gates:** `gates-v0.mjs` passes everything. At 375, findBottom is 529, JS and no-JS. At 1280, recordTop is 775.

I looked at the mobile screenshot once. The order is lead, finder, card, Record, latest summary, browse, then footer, and the layout is sound.

The implementer's deviations hold up:
- **gates-v0.mjs fallback:** the plan names this fallback.
- **`_month_year` guard:** a 2-line fix for a T3.2 P2 that this commit exposes by wiring `render_home` into GET /.
- **Fold tightening:** the step-15 remedy. The CSS stays within budget.

## Verdict: pass

## Issues
- **P2 — static/css/site.css (`.record` padding-block).** The fold remedy also cut the Record's top padding from s10 to s8. That is outside the plan's named remedy targets (`.lead`, `.lead-main` and the 880 `.vote-card` min-height). The change is harmless and does not move anything above the finder. Fix: none required. Record it in the phase log so T9.1's layout gate starts from the right baseline.
- **P2 — static/index.html (description meta on disk).** The shell still holds the old description ("…no party labels until you ask"). The server replaces it with the meta description, so what visitors get is correct, and the plan said to keep "the existing description meta". Fix: optional. Align it the next time this shell is touched.
