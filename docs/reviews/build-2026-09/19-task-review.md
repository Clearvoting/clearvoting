# T4.2 review — Delegation atomic switch (/state route, overview reshape, state.js, home block)

Commit: 6e69c39 · Reviewer run: 2026-09-25

## Summary

The commit does what T4.2 asks. I compared the code blocks with the plan. `state.js` and the app.js "Home module 4" block are byte-identical to the plan, and so is the new overview test block in `tests/test_state_overview.py`. `test_state_route.py` differs from the plan by one regex. `serve_state`, its helpers and the new overview endpoint match Steps 4 and 8. The CSS delta follows Step 12: tokens only, no `.person` redeclaration, the 880 rules inside the existing block. `state.html` matches index.html's chrome with `aria-current` removed. Its three scripts are loaded in the plan's order and versions, with no inline script and a literal `<title>` and `</head>`.

The four deviations are justified:
- The route-test regex allows T4.1's `data-context-label` attribute.
- Step 9's intermediate count could not hold, because `<!--content-->` only exists in the new shell.
- `<body>` has no `home` class, since nothing keys on it.
- The CSS block sits above the breakpoints comment.

Nothing was narrowed.

## Verification (run by the reviewer)

- **Full suite:** 1055 passed. The task files give 63 passed (`test_state_route` 39 and `test_state_overview` 24).
- **scope_check.py:** exit 0 (state.html has 88 top-level names, index.html 92).
- **Fresh server on :8011:** I freed the port first and killed the server after. Every Step 16 curl matched:
  - 11570 and 11570-1234 return 302 to `/state?code=NY&district=4#mine` with `public, max-age=0, s-maxage=86400`.
  - 11201 returns 302 to code+zip, and that page returns 200 with the exact 72 %/28 % sentence. Goldman and Velázquez appear twice each.
  - 44101 renders not-found with 200. `abc` renders the five-digit error with 200.
  - `code=ZZ` returns 404, and `/api/members/OH/overview` returns 404.
  - NY-4 shows Gillen, Gillibrand and Schumer.
  - The FL D20 and TX D23 vacancy lines each appear once.
  - Party words: 0 on six state pages and on the default overview. `partyName` appears only with `show_party=true`.
  - Warm TTFB is about 2–3 ms.
- **Extra checks:**
  - A code/zip mismatch (CA+11570) returns 302 to the NY district.
  - The `zip` value is escaped in `value=`. For example, `"><img` comes back as `&quot;&gt;&lt;img`.
  - `district=<script>` is dropped.
  - The title is server-owned, and the CSP is unchanged.
- **shoot.mjs, 8 state URLs plus home:** every mobile capture shows scrollWidth=375 and every desktop capture 1280. There were no JSERROR and no CSP lines. On the NY-4 mobile capture, the first row is visible under the header, the House list is a closed `<details>`, and nothing floats.
- **home-reps.mjs:** 14/14 ok, HOME-REPS PASSED.
- **Out-of-scope code:** state.js and app.js add no `innerHTML`, no `document.title` and no inline handlers.

## Verdict: pass

No P0 or P1 issues. There are two P2 notes for the orchestrator. Neither blocks shipping.

## Issues

| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | static/js/state.js | After the main ZIP path (a single match, then 302 to `#mine`), `initHome()` writes cv-home, and `initRememberButton()` returns early because home already equals this district. The delegation page therefore shows no "Remembered: New York, District 4 · Change · Forget" line. Spec §5.4 says the line appears "wherever it is used", and C-13 says the key is written "with a visible … Forget control". §4.2 line 240 asks only for the button. The plan's code follows §4.2, and the implementer copied it verbatim. | Plan-level decision, not a fixer item. If §5.4 governs, show `rememberedLine(home, …)` in `.remember` when home matches, with Forget unhiding the Remember button. |
| P2 | app/render.py (T4.1) | District and ZIP pages show the H1 "Your representatives", then an H2 "Your representatives" for the `.yours` section. The heading is repeated. | Out of this task's scope (T4.1 renderer). Consider an H2 such as "Your senators and House member" in a later polish task. |
