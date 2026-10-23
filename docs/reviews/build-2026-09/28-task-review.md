# T8.1 review: titles, canonical, _inject_meta keys, sitemap, favicon, noindex (commit de83b01)

## Summary
The commit does what plan T8.1 asks, step by step, and matches spec §9.2 and §9.4. Only `app/main.py` and `tests/test_seo.py` changed.

- **Helpers.** `_og_title`, `_normalize_bill_params` and `_iso_day` match the plan text exactly.
- **`_inject_meta`** now takes the `image`, `canonical: False` and `h1` keys. `twitter:card` is `summary_large_image` only when an image is set. `og:url` and the canonical are dropped together.
- **Bill meta.** `_bill_meta` lost only its `og_title` line.
- **State meta.** `_state_meta` now uses the possessive title and a covered code only. The new `_zip_finder_meta` has `canonical: False`. `_serve_state_page` got its one-line switch, and the 404 handler got `"canonical": False`.
- **New routes and headers.** `/favicon.ico` was added. `X-Robots-Tag: noindex` is set on `/static/*.html`.
- **Sitemap.** Replaced as written: it lists /methodology and /privacy, with a `lastmod` per URL.
- **Left alone as the plan says.** Member and bill routes (T6.3 and T7.4) are unchanged.

Test edits follow step 1 as written: five tests replaced by name, one T7.4 assertion updated, the block appended, and the now-unused imports removed. Every test the plan says to keep is still there.

## Verification (run by the reviewer)
- **Full suite:** 1345 passed, 3 skipped.
- **Scope check:** `scope_check.py static/*.html` exits 0.
- **Step-10 curls,** against a fresh server on port 8011:
  - The Schumer title and og:title have no suffix, and the canonical is `S000148`.
  - H.J.Res. 20 gets the one-liner title. Its og:title is cut with `…` within 90 characters. The canonical has `type=hjres`.
  - `X999999` returns 404 with 0 canonicals.
  - The TX title is possessive, and the canonical is `state?code=TX` with the district dropped.
  - `zip=44101` has 0 canonicals and the title "Find your representatives".
  - The favicon is `image/svg+xml` with `public, max-age=31536000`.
  - `/static/member.html` carries `x-robots-tag: noindex`; `/` does not.
  - The sitemap has 1768 URLs and 1767 lastmods; only /privacy has none. /methodology's lastmod is 2026-09-05.
- **h1 rewrite on trust pages:** it leaves the text unchanged ("About ClearVoting", "Methodology &amp; Corrections"). The 404 shell has no static h1, so the renderer's h1 is not touched.
- **Sitemap URLs load:** a sample of 359 URLs (every non-bill URL plus every 8th bill) all return 200.
- **shoot.mjs** on state NY, /state, the member 404, /about, bill hjres 20 and member S000148: every mobile capture is scrollWidth=375 and every desktop capture 1280. There are no JSERROR or CSP lines. The 404's console note is its own 404 status, which is informational.
- The server was killed afterwards and port 8011 is confirmed free.

## Safety
- Every injected value goes through `html.escape`. The image width and height are cast with `int()`.
- The title and h1 substitutions now use lambda replacements. This is a small unlisted change from the plan's string replacement for `<title>`, and a better one: a backslash in a bill title can no longer be read as a regex group reference.
- No innerHTML, no inline script, and the CSP is unchanged.
- Each shell still has a literal `<title>` and `</head>`, and each page has exactly one `<title>` (asserted).

## Verdict: pass

## Issues
- **P2, `app/main.py` line 23: an unused import left over from T7.4.** `from app.render import _BILL_TYPE_LABELS, …` still imports `_BILL_TYPE_LABELS`, and nothing in main.py uses it. The implementer disclosed this. Fix: remove `_BILL_TYPE_LABELS` from that import in any later touch of the line. This does not block the task.
- **P2, `app/main.py` around line 372: a redundant local import.** Now that `BIOGUIDE_PATTERN` is imported at module level, the local import inside `serve_member` does nothing. The plan explicitly says to keep it for this task. Fix (optional): drop it in a later cleanup.
