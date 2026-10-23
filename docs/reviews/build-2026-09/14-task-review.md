# T2.4 review — Feedback hooks: h1 promotion, native dialog, freshness server-filled

**Commit:** 581596a  **Reviewer date:** 2026-09-25  **Verdict:** pass

## Summary

The commit does what plan T2.4 and spec §2.2 #5, C-7, §6.4 (dialog + footer), §6.6 and §10 #17 ask, in one commit:

- **Hook change (C-7):** `member.js:123` and `bill.js:100` now render `h1`. `feedback.js` reads `.member-header h1`, `.bill-header h1` and `.state-header h1`. All five `styles.css` selectors and both `broadsheet.css` selectors moved from h2 to h1. No `h2` header selector is left anywhere in `static/`, `app/` or `tests/` except the negative assertions.
- **feedback.js:** matches the plan's Step 7 text line for line. The only difference is one reworded comment, needed so the plan's own `e.target === modal` gate passes. It uses `showModal()`/`close()`, returns focus to the opener on every close, keeps the success message in the dialog, uses the plan's failure copy verbatim with `.field-error`, and has the delegated `[data-feedback-open]` opener and the `data-context-label` preference. It does not use `innerHTML` or `setTimeout`, and the observer and the `/api/health` fetch are gone.
- **Shells:** all six have the same dialog diff (identical md5 on five; about.html also drops its seven animation classes). The copy is verbatim from spec §6.4: "Send feedback" and "What did you see?". The textarea has `autofocus`, the status line has `role="status"` and starts empty, the placeholder and the inline `style="width:auto"` are gone, and the freshness separator now sits inside the span.
- **Server freshness:** `_freshness_text` escapes the date and returns "" when `last_sync` is missing. It reads in-memory metadata, so a page load does no extra file read. `_fill_freshness` runs in `_serve_html`, so the 404 page gets it too.
- **CSS:** the Entrance Animations block is deleted. No page or script still references `animate-*`, `stagger-children`, `hover-lift`, `hero-animate`, `ClearVotingAnimate`, `feedback-success` or `feedback-error`.

## Verification (re-run by reviewer)

- `node --check static/js/feedback.js`: clean.
- Full suite: **808 passed**. Targeted `test_feedback.py` + `test_static_assets.py`: **45 passed**, the number the plan expects.
- `scope_check.py static/*.html`: exit 0.
- Fresh server (port freed first), Step 11 curls:
  - `/about` → `<span id="data-freshness"> · Synced September 5, 2026</span>`, and the same on `/`, `/state`, `/member` and `/bill`.
  - The 404 page has `Senate.gov</a><span id="data-freshness"> · Synced …`.
  - About has 0 `animate-` matches.
  - The dialog tag appears once on each of the six pages.
  - The served feedback.js has 0 banned matches.
  - `/no-such-page` returns 404.
  - The CSP header is unchanged (`script-src 'self'`, `img-src 'self' https://www.congress.gov`).
- `shoot.mjs` on all six pages:
  - Every desktop capture is 1280.
  - Every mobile capture is 375 except `member-mobile` at 445. That is the known F14 overflow; the plan expects it and this task must not change it.
  - No JSERROR or CSP lines. The only console note is the expected resource 404 on the 404 page.
- `gates.mjs --only=dialog`: exit 0, 12/12 PASS.
  - Context reads "About: New York", "About: Charles E. Schumer" and "About: Protect Economic and Academic Freedom Act of 2026", so the h1 hooks resolve on the rendered pages (C-7).
  - Focus lands in the textarea on open and returns to `#feedback-open` on every page at both widths.
- Server stopped; port 8011 free.

## Deviations (accepted)

1. **feedback.js comment reworded:** the plan's Step 7 text conflicts with its own gate, and the code is unchanged. Correct call.
2. **Plan line numbers:** the implementer read the section by its heading because the line numbers had drifted. No impact.
3. **gates.mjs:** created outside the repo with the plan's v0 content, as Step 13 instructs.

## Issues

None blocking. Notes for later tasks (no action in T2.4):

| Sev | File | Note |
|---|---|---|
| P2 (note) | static/js/feedback.js `setStatus` | A second successful send in the same open dialog clears the status and then sets the same "Thanks — sent." text in the next promise tick. Some screen readers skip announcing an identical string (the same class of issue T2.3 fixed for "Link copied"). The text follows the plan verbatim. If the T9.1 keyboard/VoiceOver walkthrough (§8 item 13) flags it, apply the T2.3 re-announce pattern there. |
| P2 (note) | static/css/styles.css `.feedback-status.field-error` | Uses the hard-coded `#8A1C1C` (as the plan specifies) instead of a token. styles.css is retired in T9.1, and site.css already uses `var(--error)`. No action. |
