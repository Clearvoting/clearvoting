# T3.1 review — SSR plumbing: content and edition markers, edition line, error state

Commit: a5b3c6f (on 581596a). Reviewer run: 2026-09-25.

## Summary

The commit does what the plan says, line for line. `app/render.py` gains the "Shared page blocks" section (ELECTION_DAY, COVERED_STATES, NOTIFY_STATES with 47 entries, ZIP_INPUT_PATTERN, PAGE_ERROR_SENTENCE, `_pacific_today`, `render_edition`, `render_error`, `render_zip_form`, `render_state_links`, `render_notify_disclosure`). `app/main.py` gains `_edition_html`, `_page_content`, a module logger, and a `_serve_html` that takes `content_html` and `status_code`. The edition is filled after meta injection, the content is filled last, and the headers are unchanged. `DataService.earliest_roll_call_date()` is cached as the plan says. `tests/test_edition.py` is byte-identical to the plan's block. The test_data_service and test_render_escaping additions match the plan. The implementer's deviations are accurate and harmless: one test already passed before the change, `assert_escaped` was already updated, and the logger was added because none existed.

Spec copy checked against the spec text:
- §7.4 edition example: exact match.
- §4 common error sentence: exact match, with no mention of Congress.gov.
- §3.2 form and input attributes, including the pattern: exact match.
- §4.1 m2 notify disclosure: "Somewhere else?", "Choose your state", only uncovered states plus DC, "Notify me", the privacy line, the noscript copy, and no action or method on the form. All match.

Safety:
- Every data value goes through `h()`. Only constants go in raw: PAGE_ERROR_SENTENCE's `<em>`, fixed state codes, and the fixed class names.
- A probe with a hostile `latest_roll_call` came back escaped.
- No innerHTML, no inline script, and no change to `<title>` or `</head>`. The content is injected after `_inject_meta`, so server data never reaches the title.

## Verification (run by the reviewer)

- Full suite: 842 passed. Task files: 95 passed. test_edition.py collects 24.
- scope_check.py static/*.html: exit 0.
- Port 8011 freed first, uvicorn started, /api/health returned 200.
- Status codes: / 200, /state?code=NY 200, /about 200, /nope 404.
- `grep -c 'class="edition"'` on / returns 0, as expected because no shell has a marker yet. No marker text leaks into the page.
- shoot.mjs: home and state at desktop gave scrollWidth=1280, and at mobile gave scrollWidth=375. No JSERROR or CSP lines.
- Server stopped and the port is free.

## Verdict: pass

## Issues

| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | app/render.py (`render_edition`) | When `last_sync` is missing but a roll-call date exists, the first span is `edition-mid`. Under 560px that span is hidden (site.css), so mobile shows the line starting with " · Election Day…". The plan's tests don't cover this, and it is unlikely in practice because sync_metadata always carries last_sync. | Optional, later: add the separator by visible position, or never give the separator to the span that follows `edition-mid` when `edition-mid` is first. Not blocking. |
| P2 | app/render.py (`render_edition`) | A malformed `last_sync` (not ISO) prints raw, escaped, through `format_date` ("Data synced garbage") and is not left out. The data is controlled sync output, so the risk is low. | Optional: leave out the span when `format_date` returns its input unchanged. Not blocking. |
