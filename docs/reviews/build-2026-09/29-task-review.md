# T8.2 review — Cache-Control middleware and stable asset version

Commit: `3fcb5b9` (app/main.py, tests/test_caching.py). Reviewer date: 2026-09-25.

## Summary

The commit follows the plan task line for line. It adds the eight `CACHE_*` constants, `_cache_control_for` (status first, then route), the middleware call placed after the X-Robots-Tag lines, and `server_error_handler`, which returns a no-store 500 and sits directly above `custom_exception_handler`. It also adds `_compute_asset_version`, which uses RENDER_GIT_COMMIT[:12] when that is set and otherwise a hash of the static/ file list with sizes and mtimes. The no-cache header on `_serve_html` is gone, and `import time` was removed after confirming nothing else uses it. `_version_re` has not changed, so the shells on disk keep their digit `?v=N` links. The test file matches the plan verbatim. Every row of the spec §9.5 table is covered in the rule function, and the tests check it both at unit level and through the app.

## Verification (run by reviewer)

- Full suite: 1394 passed, 3 skipped.
- scope_check.py static/*.html: exit 0.
- Local server on :8011 (port freed first, stopped afterwards, confirmed free):
  - `/`, `/state?code=NY`, `/member?id=S000148`, `/bill?congress=119&type=hr&number=4795`, `/methodology`, `/about` and `/privacy` all return `public, max-age=0, s-maxage=600, stale-while-revalidate=3600`.
  - `/state?zip=11570` returns a 302 to `/state?code=NY&district=4#mine` with `public, max-age=0, s-maxage=86400`.
  - `/no-such-page` and `/member?id=X999999` return a 404 with `public, max-age=60`.
  - `/api/votes/latest` returns the API header, `/api/health` returns `no-store`, and `/api/districts/11570` keeps its own day-long header.
  - `/api/districts/abc` returns a 400 with `no-store`. `POST /api/feedback {}` returns a 422 with `no-store`, and `HEAD /` returns a 405 with `no-store`.
  - `/static/favicon.svg` returns `immutable`, and `/favicon.ico` returns `public, max-age=31536000`.
  - The `?v=` token was `099a959dc423` on both home and member, and it was identical after a restart.
  - Warm member-page TTFB was about 0.007s.
- shoot.mjs on home, member, bill and state: all ok, mobile scrollWidth=375, desktop 1280, no JSERROR or CSP lines.

## Spec / constraint check

- §9.5 table: every row is implemented as written. The 404 rule comes before the route rules, the other 4xx/5xx get no-store (the 429 and 500 paths are exercised through the app), and `/static/og/` is matched before `/static/`.
- §2.3 C-8: no per-visitor content was added to the shells.
- The `<title>` and `</head>` shells, the CSP, innerHTML use and feedback.js are all untouched. No URL-shape changes, and no data, .env or sync.py edits.

## Verdict: pass

## Issues

- **P2 — app/main.py (`_ZIP_REDIRECT_CACHE` at the /state?zip= RedirectResponse; the explicit header on `serve_favicon`).** These are now redundant with the middleware and give the same value from two sources. Fix (optional, later cleanup): leave as is, or drop `_ZIP_REDIRECT_CACHE` and let `CACHE_ZIP_REDIRECT` in the middleware own it. The implementer already recorded this. It is harmless.
- **P2 — static/*.html (`/static/favicon.svg`, linked without `?v=`).** It now gets `max-age=31536000, immutable`, so a changed favicon.svg would not reach returning browsers. This matches the spec, which makes every `/static/*` 200 immutable. Fix (optional): rename the file if it ever changes, or add `?v=` to the icon link in a later shell edit.
- **P2 — tests/test_caching.py `test_500_is_never_stored`.** It triggers the 500 by patching `DataService.get_sync_metadata`, which ties the test to how `/sitemap.xml` is built internally. Fix (optional): none needed now. If sitemap stops calling that method, point the test at another route that reads data.
