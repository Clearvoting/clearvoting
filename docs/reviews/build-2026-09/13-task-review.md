# T2.3 re-review: site.js behaviours, fix commit 583d5fe

## Summary
Commit 583d5fe fixes the round-1 P1 and takes up two of the round-1 P2s. The same hunks went into `static/js/site.js` and into the plan's T2.3 code block, and the interface notes now name `attempt` and the share-status reset.

- **Party toggle (P1).** Each press now gets a number: `show()` takes `const mine = ++attempt` and `hide()` runs `attempt++`. The code re-checks `mine !== attempt || !revealed` after the fetch/json, after `onShow`, and in the `catch`. If a Hide lands while an async `onShow` is still running, `onHide()` runs once more, so the page's late fill does not outlast the Hide. That extra call is the implementer's deviation, and I accept it: page `onHide` callbacks only clear spans, so running one twice is harmless.
- **Share.** The status line is emptied, then "Link copied" is written after 100 ms, so a second copy counts as a change and gets announced. A 100 ms delay is safer than 0 here.
- **Notify.** A 422 now shows the existing `invalidEmail` copy on the field, sets `aria-invalid` and `aria-describedby`, moves focus to the email field and re-enables submit. Network errors, 429 and 5xx still show `notifyFailed`. In this form the server can only answer 422 because of the email check: the state comes from a select and is ≤50 characters.
- **Constraints.** All copy comes from `STRINGS`. There is no new innerHTML, cookie, pushState or aria-live, and storage still goes only through the helpers.

## What I verified
- Full suite: **795 passed**. `node --check` is clean.
- Throwaway node `vm` race harness (scratchpad only; DOM stubs, fetch promises I resolve by hand). All six scenarios end in the right state:
  - Show → Hide → fetch resolves: label "Show", status "hidden", session key empty, `onShow` never called.
  - Show → Hide → Show, first fetch resolves late: the second reveal wins, with "Hide" / "shown" / key=1.
  - Show → Hide → Show, first fetch **fails** late: the stale catch leaves the newer reveal alone.
  - Slow async `onShow`, then Hide: ends hidden, with `onHide` called twice.
  - Remembered reveal (`show(false)` on load), with a press during the load: Hide wins.
  - Plain Show: works as before.
- Server on :8011 (port freed first, stopped after, port confirmed free): `/api/health`, `/`, `/state?code=NY`, `/member?id=S000148` and `/static/js/site.js` all return 200. The served site.js contains the guard 3 times. `POST /api/notify {"email":"a@b"}` returns 422, which is the case the new branch handles. `/` still does not load site.js.
- Scroll-width smoke on `/`: mobile scrollWidth=375, desktop 1280.

## Verdict: pass
The P1 is fixed and I confirmed the behaviour by running it, not just by reading the code. What remains is P2 and does not block.

## Issues (all P2, non-blocking)
| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | tests/test_static_assets.py (`test_site_js_storage_rules`) | The new assertions check that source strings exist (`const mine = ++attempt;`, a count of the guard line, `statusNode.textContent = '';`). They do not test behaviour. A refactor that keeps the text but breaks the order, or that reorders correct code, would pass or fail for the wrong reason. | Later task (T11.x), or whenever tests next touch site.js: turn the race harness into a real node test with a small DOM stub. It is about 40 lines and covers the Show→Hide→resolve and Show→Hide→Show→late-fail cases. Keep the T11.3 real-browser walkthrough item. |
| P2 | static/js/site.js `show()` catch | A stale failure returns early and never calls `onHide`. If a page's async `onShow` filled part of the page, then threw after the reader pressed Hide, that partial fill stays. The success path handles the same case by calling `onHide()` again. | Mirror the success path in the catch: `if (mine !== attempt \|\| !revealed) { if (!revealed && onHide) onHide(); return; }`. It is one line, and the plan block should get it too. It only matters when a page callback both fills and throws. |
| P2 | static/js/site.js `initShare` | The 100 ms timer is never cancelled. Say one press copies successfully and a second press within 100 ms fails and writes the URL as fallback text. The first timer then overwrites that with "Link copied". | Keep the timer id on the button and `clearTimeout` it before writing either message. Very unlikely in practice. |
| P2 | static/js/site.js `initNotify` 422 fallback | When `#notify-email-error` is missing, the invalid-email copy goes into `#notify-status`, but the `field-error` class is removed and focus goes to the email field, which is not described by that status. The T3.1 markup contract always renders the error node, so today this code never runs. | If the fallback stays, add `field-error` to the status, or drop the fallback and rely on the contract. |
| P2 (carried) | static/js/site.js `readHome`/`rememberDistrict` | NY-40 is still accepted. The implementer left this unchanged, as round 1 allowed. | Check the district against the state's count once `districts_expected` reaches the client. |
| P2 (carried) | static/js/site.js top-level names | New top-level names share one global scope with the page scripts. | T3.3+ should grep for duplicate top-level names when a page first loads site.js. |

---

# Round 1: T2.3 review, site.js behaviours (commit ab0b6f9)

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
