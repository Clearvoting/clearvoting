# T2.3 review — site.js behaviours (commit ab0b6f9)

## Summary
The commit matches the plan exactly. I checked this by script: the Step 3 behaviours block sits verbatim, and only, above the Node export marker. The export list gained exactly the planned line, and both test appends match the plan byte for byte. All copy comes through `t()` from the T2.2 `STRINGS` (the spec's wording). The one hard-coded string, "Voted for {Name}", is spec §4.3 wording too.

Constraints hold:
- no `innerHTML`, `insertAdjacentHTML` or `outerHTML`
- no cookies and no `pushState`
- `history.replaceState` appears once (the `#mine` removal)
- storage is reached only through the try/catch helpers
- no `aria-pressed` and no `aria-live`
- no page loads site.js yet, so live pages are unchanged

Status nodes are filled only through `textContent`. The data contracts this code depends on match the server:
- `/api/members/{code}/overview` returns `senators`/`house` with `bioguideId` and `partyName`
- `/api/members/detail/{id}?show_party=true` returns `partyName` plus `speaker_votes`
- `POST /api/notify` accepts JSON `{email, state}`
- the canonical `<link>` is injected by the server

No new top-level name clashes with the existing page scripts today. I checked all 7 non-site scripts.

## What I verified
- Full suite: 795 passed. `node --check` is clean.
- Server on :8011 (port freed first): `/api/health`, `/`, `/state?code=NY`, `/member?id=S000148` and `/static/js/site.js` all return 200. site.js is served as text/javascript with nosniff, and `/` does not reference site.js.
- Scroll-width smoke on `/`: mobile scrollWidth=375, desktop 1280. The server was stopped and the port is free.

## Verdict: fix
One P1 correctness bug in the party toggle. The plan text carries it too, so the fix belongs in the plan's code as well. It is a mechanical guard with no design decision.

## Issues

### P1 — static/js/site.js, `initPartyToggle` → `show()`: a Hide pressed while the reveal is loading is overridden
- **Problem:** `show()` sets `revealed = true`, then awaits `fetch(url)`, `response.json()` and `onShow(payload)`. It never re-checks `revealed` after those waits.
- **Scenario:**
  1. On a slow connection, the reader presses Show. The label becomes "Hide party labels" at once.
  2. The reader presses again before the fetch returns. `hide()` runs: label "Show party labels", spans cleared, session key removed, status "Party labels hidden".
  3. The fetch then resolves. `show()` continues: it calls the page's `onShow(payload)`, which puts party back on screen on pages that pass callbacks (member, bill, delegation). It writes `sessionStorage['cv-show-party']='1'` and announces "Party labels shown".
- **Result:** the label says "Show" while party is visible, the status line is false (§8 item 10), and a reveal the reader turned off carries to the next page (§5.4, C-13). The same happens when the remembered reveal is re-applied on load (`show(false)`) and the reader presses the toggle during that fetch.
- **Fix:** give each reveal attempt a number (`let attempt = 0;`). `show()` starts with `const mine = ++attempt;` and `hide()` also runs `attempt++`. After each `await` in `show()` (after the fetch/json, and after `onShow`), add `if (mine !== attempt || !revealed) return;` before `fillSpans`, `onShow`, `storageSet` and `status`. Apply the same check in the `catch`, so a stale failure never resets a newer state. Mirror the change in the plan's T2.3 block (docs/superpowers/plans/2026-09-18-clearvoting-redesign.md, around line 9690) so later tasks that extend `show()` inherit it. Add a static assertion to `test_site_js_storage_rules` if a node DOM test is too heavy (for example, assert that the guard text is present), and cover the behaviour in the T11.3 QA walkthrough.

### P2 — static/js/site.js, `initShare`: a second "Link copied" is not announced
- **Problem:** a second copy writes the same text into a `role=status` node that already holds it. Screen readers do not announce an unchanged text, so a second press gives a screen-reader user no feedback.
- **Fix:** set `statusNode.textContent = ''` first, then write `t('linkCopied')` on the next tick (`setTimeout(…, 0)` or `requestAnimationFrame`).

### P2 — static/js/site.js, `initNotify`: a server-side email rejection shows the "try again in a few minutes" copy
- **Problem:** the browser's `type=email` check accepts `a@b`, but the server's `_EMAIL_RE` requires a dot and answers 422. The reader then sees "We couldn't save that. Please try again in a few minutes.", which is misleading.
- **Fix:** on `response.status === 422`, call `setEmailError(t('invalidEmail'))` and move focus to the email field instead. Keep `notifyFailed` for network errors, 429 and 5xx.

### P2 — static/js/site.js, `readHome`/`rememberDistrict`: any district from 1 to 99 is accepted for a covered state
- **Problem:** `NY` with district 40 is stored and linked, although NY has 26 districts. The server page handles an unknown district, so the harm is only a dead-end masthead link.
- **Fix (optional):** check the district against the state's district count once T4.x exposes `districts_expected`, or leave the server as the judge.

### P2 — static/js/site.js: new top-level names are in shared classic-script scope
- **Problem:** the new names include `once`, `bound`, `isWide`, `COVERED_STATES`, `BREAKPOINTS`, `HOME_KEY`, `PARTY_KEY`, `REDUCED_MOTION`, `canonicalUrl` and `copyText`. None clash today; I checked all current page scripts. But a later page script that declares any of them with `const`/`let` gets a load-time SyntaxError. A same-named `function` in a page script would silently replace site.js's version, for example a leftover `initPartyToggle` in a legacy enhancer.
- **Fix:** no change needed now. T3.3+ should grep for duplicate top-level names whenever a page first loads site.js, as the implementer's note says.
