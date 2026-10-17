# T6.3 review — Member atomic switch (commit 23829fa)

## Summary
The commit does what plan T6.3 asks. `/member` is now a plain-`def` route that renders the page on the server. Unknown, missing or malformed ids return a real 404. The `page`, `topic`, `position` and `plain` params are validated, and none of them reach the canonical. A render or data failure goes through `_page_content` and shows the §4 error state with a 503. `member.html` is on site.css/site.js, and its chrome matches state.html. The only differences are the literal title, the `<main>` contents (marker plus noscript line) and the page script. `member.js` has gone from 1,022 lines to a thin enhancer that calls initPartyToggle, initShare and the breadcrumb, and uses no innerHTML, no `document.title` and no change listener. `/api/members/{id}/summary` and `get_member_vote_summary` are deleted. `_allowlist_member_payload` is applied to `/votes` (both branches), `/page` and `/detail`, and matches the plan verbatim. The CSS block matches the plan, and the old T2.1 `.pager` rule was replaced rather than duplicated. `.pager` is only used by the member renderer.

The six deviations are all justified:
- initPhotos is dropped because site.js's initSite already runs it, and its `complete && naturalWidth === 0` sweep covers images that errored before DOMContentLoaded.
- The redundant function-level import was dropped.
- The edition marker is placed where state.html has it.
- The CHECKED_ENDPOINTS list order changed, which has no effect.
- The Congress.gov browser check can't be done by an agent, so it is left for Joseph and recorded honestly.

## Verification (run by the reviewer)
- Full suite: 1213 passed, 2 skipped. scope_check.py exited 0 for all 8 shells.
- All 17 step-11 curls gave the expected values:
  - h1 "Charles E. Schumer"; 20 vote rows; the Senate fact line.
  - The G000602 ballot seal; page-2 Newer/Older #record links; "9 bills on Health · Voted no".
  - 0 party hits; 0 "Jeffries" on page=99.
  - Status codes 404, 404 and 422.
  - 0 retired keys in `/votes`; the reveal returns Jeffries; the header hook container is present.
  - Warm TTFB is about 7 ms.
  - Congress.gov URLs are .../charles-e-schumer/S000148 and .../nydia-m-velazquez/V000081.
- Extra checks: `page=-5` and a huge page number both return 200 (clamped). A `topic` containing `<script>` is escaped. `?id=X999999` gives the 404 page. The CSP header is `script-src 'self'` and `img-src 'self' https://www.congress.gov`. Flat `/votes` positions for G000602 are only Aye, Nay, No, Not Voting, Present, Voted and Yea, so Speaker names are masked.
- shoot.mjs: all 4 mobile captures read "ok scrollWidth=375" and all 4 desktop captures "ok scrollWidth=1280", with no JSERROR or CSP lines.
- member-checks.mjs printed 5 ok lines: fold tops 703 and 690, and the Speaker pick went empty, then "Voted for Jeffries", then empty.
- The server was stopped afterwards.

## Verdict: pass

## Issues
- **P2 — app/main.py (`serve_member`, topic param):** any `topic` string up to 120 characters is echoed in the server-rendered result line, e.g. "0 bills on <arbitrary text>". It is HTML-escaped, so it is safe from injection, but a crafted link can put arbitrary text on a clearvoting.org page. **Fix (optional, later):** pass `topic` through only when it is one of the member's `policy_areas` (the options in the select), and treat anything else as no topic.
- **P2 — process (spec §4.3 m5):** the commit body does not yet say "Congress.gov member link checked in a browser". **Fix:** Joseph opens the two URLs above in a desktop browser and confirms each reaches the right profile. No code change is needed.
