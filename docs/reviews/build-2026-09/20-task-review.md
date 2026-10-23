# T5.1 review — About, Methodology, Privacy and 404 (commit 0e1e838)

## Summary

The commit does what the plan task says: four shells built on the state.html chrome, the renderers (`prompt_rules`, `render_about_counts`, `render_methodology`, `render_not_found`), the DataService startup load of `_crosswalk_source` / `_senate_file`, plain-`def` routes with the `_trust_block` 503 fallback, the 404 handler that survives a member-count failure, the feedback.js page_type tags, the footer/notify link repoint to `/methodology` / `/privacy`, and the product-strategy corrections. The copy matches the plan and spec §4.5–§4.8 word for word. The one planned change from the spec, the privacy reveal sentence, is correct: the reveal does reach our server, and a test guards it. The one unplanned change, `.trust .rules { list-style: decimal; }`, is justified: `ol[class]` resets list-style, and without the fix the rule numbers the page promises would not show.

Checked by the reviewer:
- Full suite: 1103 passed, 1 skipped. The skip is the planned font-host check, which waits for T8.3.
- `scope_check.py static/*.html`: exit 0.
- Live server on :8011, port freed first:
  - /about, /methodology and /privacy return 200. /no-such-page, /bills/nope and /state?code=ZZ return 404 with "Not in this edition".
  - Methodology counts equal /api/health: 1,610 bills, 1,435 shown, 60 missing, 115 withheld, 177 audited, 1,469 nominations, "last updated July 7, 2026", "Of the eight senators we cover".
  - Party-leak grep: 0. House.gov noopener link: 1. 'never sent to us': 0. No email addresses on any of the four pages.
  - The accuracy list starts at 14.
  - Census and senate.gov links are https and prefix-guarded. `_source.method` is not rendered.
  - Each page has one title and one description. The CSP header is unchanged.
- shoot.mjs: all four pages "ok scrollWidth=375" on mobile and "ok scrollWidth=1280" on desktop. There are no JSERROR or CSP lines. The only console note, on notfound, is the page's own 404 status.
- Escaping: every data value passes through `h()`. The `_trust_section` anchors and headings are module literals, and there is no new innerHTML. The shells have no inline script or handler.

## Verdict: pass

## Issues

| Sev | File | Problem | Fix |
|-----|------|---------|-----|
| P2 | static/css/site.css:248 | The trust block went directly under the `/* ---- Breakpoints: declared once, here, at the end (§6.3) ---- */` comment, which now heads a non-breakpoint block. The plan's "immediately above the first @media" was followed literally. | Move the Breakpoints comment down to sit directly above `@media (min-width: 560px)`. |
| P2 | static/css/site.css (.notfound) | "Go to the front page →" sits flush under the state chips with no top margin. The implementer flagged it too. | Add `.notfound > p:last-child { margin-top: var(--s6); }`, or fold it into a later polish task. |
| P2 | static/privacy.html (#third-party) | "No third-party requests except member photos from congress.gov" is not yet true: every shell still loads Google Fonts. The plan knows this; `test_privacy_third_party_claim_holds_no_font_hosts` is skipped until T8.3 self-hosts the fonts. | No action in T5.1. T8.3 must land before release. |
| P2 | app/main.py (/member, /bill) | Unknown `member?id=` and `bill` keys still return 200 without the 404 body, which spec §4.8 requires. That belongs to T6.x / T7.x, not this task. | Track in T6.3 / T7.4. |
