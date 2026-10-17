# QA Report: ClearVoting redesign — final verification

**Date:** 2026-09-26
**Branch / commit:** `redesign/2026-09` at `b581437`
**Environment:** local uvicorn at http://127.0.0.1:8011 on the real `data/synced/`; Playwright gate runners out of repo (`~/.clearvote-worktrees/tools/shots/`)
**Plan:** group 11 (T11.1 browser gates, T11.2 pytest/grep/TTFB, T11.3 walkthrough)
**Verdict:** Pass — every scripted gate green; §8 item 13's VoiceOver pass is pending with Joseph before merge and §6.9 #10 after merge

## Definition of done (spec §6.9, §8 item 13)

| Gate | Result | Evidence |
|---|---|---|
| §6.9 #1 reflow: scrollWidth ≤ innerWidth at 320/375/768/1280 | Pass | gates `scroll` |
| §6.9 #2 no text under 12px; font-size only `var(--t-*)` | Pass | gates `fonts` + grep |
| §6.9 #3 every text token ≥ 4.5:1 on --paper and --card; tokens = §6.1 | Pass | gates `tokens`, `contrast` |
| §6.9 #4 standalone controls ≥ 44×44 | Pass | gates `targets` |
| §6.9 #5 box-shadow / border-radius rules | Pass | gates `decor` + grep |
| §6.9 #6 fold checks at 375×812; nothing floats under 880 | Pass | gates `fold`, `floating` |
| §6.9 #7 no inline script/handlers, no new innerHTML, literal <title>/</head> | Pass | grep.txt |
| §6.9 #8 axe: contrast, name/role, heading order, landmarks | Pass | gates `axe` |
| §6.9 #9 TTFB < 300 ms (4 URLs), startup < 2 s, no full scan | Pass | ttfb.txt, startup.txt, pytest |
| F55 layout shift < 0.1; no third-party requests | Pass | gates `cls`, `thirdparty` |
| Every page loads with the right status and no console error | Pass | gates `status`, `console` |
| Full pytest suite | Pass | pytest.txt |
| Derived files regenerate identically (§12.4 ops 2) | Pass | regen.txt |
| Fallback fixtures still represent their states | Pass | precheck.txt |
| ZIP 302: same Location with #mine, edge-cacheable | Pass | curl-302.txt |
| §8 item 13 keyboard + reading order (scripted) at 375 and 1280 | Pass | walk.json |
| §6.6 reduced motion honoured | Pass | walk.json |
| §8 item 13 VoiceOver pass | Pending (Joseph, before merge) | PR body "Before merging" |
| §6.9 #10 cf-cache-status HIT after the Cloudflare rule | Pending (ops, after merge) | PR body ops step 1a |

## Browser gates (T11.1)

Run at 2026-09-26T11:40:10.754Z over 38 pages × 320/375/768/1280 (axe at 375 and 1280), plus 4 JS-off renders at 375.

| Check | Passed |
|---|---|
| `tokens` | 20/20 |
| `contrast` | 25/25 |
| `status` | 156/156 |
| `cls` | 136/136 |
| `thirdparty` | 152/152 |
| `scroll` | 156/156 |
| `fonts` | 152/152 |
| `targets` | 152/152 |
| `decor` | 152/152 |
| `floating` | 114/114 |
| `console` | 152/152 |
| `nophoto` | 4/4 |
| `fold` | 13/13 |
| `axe` | 76/76 |
| `dialog` | 16/16 |

Pages: `404`, `404-bill-malformed`, `404-bill-unknown`, `404-member-bad`, `404-state-oh`, `about`, `bill-117-hres-8`, `bill-118-hr-21`, `bill-119-hr-1-withheld`, `bill-119-hr-4795-no-summary`, `bill-119-hr-4795-remembered`, `bill-119-hres-1499`, `bill-119-hres-354`, `bill-119-s-5271-no-decisive`, `home`, `home-remembered`, `member-g000602`, `member-party`, `member-r000579-empty-totals`, `member-s000148`, `member-s000148-no-p2`, `member-s000148-remembered`, `member-s000148-topic-p2`, `member-v000081-no-money`, `member-w000832-no-photo`, `methodology`, `privacy`, `state-ca`, `state-finder`, `state-fl-d20-vacant`, `state-lowercase-ny`, `state-ny`, `state-ny-d4`, `state-ny-d40-out-of-range`, `zip-malformed`, `zip-none-44101`, `zip-partial-73949`, `zip-split-11201`

Non-gated axe findings (informational): 0.

Layout shift on returning-visitor pages (informational; §9.6 inserts content after load by design): home-remembered@320 0.000, member-s000148-remembered@320 0.000, bill-119-hr-4795-remembered@320 0.000, bill-117-hres-8@320 0.000, home-remembered@375 0.018, member-s000148-remembered@375 0.000, bill-119-hr-4795-remembered@375 0.000, bill-117-hres-8@375 0.000, home-remembered@768 0.030, member-s000148-remembered@768 0.000, bill-119-hr-4795-remembered@768 0.091, bill-117-hres-8@768 0.032, home-remembered@1280 0.034, member-s000148-remembered@1280 0.000, bill-119-hr-4795-remembered@1280 0.007, bill-117-hres-8@1280 0.000.

Fallback fixtures (confirmed against the real data before the run):

```
precheck at 269b41c
ok   119-hr-1 is a withheld (needs_review) bill with a roll call
ok   119-s-5271 has roll calls and none is class D (115 such bills in the real data)
ok   117-hres-8 is a 117th-Congress bill with house/117_1_00006 in the index
ok   W000832 is a current member for the no-photo page (0 members without a photo in members.json; gates.mjs fails its photo request and gates the initials fallback)
ok   V000081 has no donations entry
ok   R000579 has a donations entry without complete totals
ok   FL District 20 is vacant in members.json
ok   NY has no District 40 (crosswalk max 26)
ok   ZIP 11201 is split (2+ districts at >= 5 %)
ok   ZIP 73949 is partial (covered share < 0.95)
ok   ZIP 44101 is not in the crosswalk
ok   ZIP 11570 is a single NY-4 match
ok   S000148 has more than 15 International Affairs bill groups (44)
ok   S000148 has more than 15 bill groups voted no (145)
PRECHECK OK
```

Cut-first status:

```
Cut-first items on redesign/2026-09 at 269b41c (spec §10.3 cut order: T10.1 og Phase B, T10.2 in-place pagination, T10.3 print, T10.4 sticky strip, T10.5 desktop fact strip, T8.4 og Phase A)
T10.1: 276760c feat(og): per-member and per-state share cards built at sync (plan T10.1)
T10.2: a4bc0ef feat(member): in-place record pagination and filtering (plan T10.2)
T10.3: cc6490c feat(print): print block and details opened for printing (plan T10.3)
T10.4: f7eb5d8 feat(strip): one sticky strip on member and bill pages (plan T10.4)
T10.5: fe63c48 feat(member): desktop fact strip in the member header (plan T10.5)
T8.4: 2eab658 feat(og): Phase A share cards for home, member, bill and state
```

## pytest, grep gates, TTFB and startup (T11.2)

pytest (tail):

```
........................................................................ [ 87%]
........................................................................ [ 91%]
........................................................................ [ 96%]
.................................................                        [100%]
1487 passed, 3 skipped in 11.14s
```

Grep gates:

```
PASS §6.1 exactly one top-level :root block in site.css: 1 found
PASS §6.9 #2 font-size only var(--t-*) outside :root
PASS §6.9 #2 no font: shorthand setting a size
PASS §6.9 #5 box-shadow only on .state-link and .vote-card
PASS §6.9 #5 border-radius only 0/4px/8px
PASS §6.3 breakpoints only 560 and 880, each declared once: ['560', '880']
PASS §6.3 no max-width media queries
PASS §8 item 7 no outline: none / 0
PASS §2.2 #13 nothing defaults to opacity:0
PASS §2.2 #2 index.html has a literal <title>…</title> and </head>
PASS §6.9 #7 index.html has no inline script or on* handler: []
PASS §2.2 #2 state.html has a literal <title>…</title> and </head>
PASS §6.9 #7 state.html has no inline script or on* handler: []
PASS §2.2 #2 member.html has a literal <title>…</title> and </head>
PASS §6.9 #7 member.html has no inline script or on* handler: []
PASS §2.2 #2 bill.html has a literal <title>…</title> and </head>
PASS §6.9 #7 bill.html has no inline script or on* handler: []
PASS §2.2 #2 about.html has a literal <title>…</title> and </head>
PASS §6.9 #7 about.html has no inline script or on* handler: []
PASS §2.2 #2 methodology.html has a literal <title>…</title> and </head>
PASS §6.9 #7 methodology.html has no inline script or on* handler: []
PASS §2.2 #2 privacy.html has a literal <title>…</title> and </head>
PASS §6.9 #7 privacy.html has no inline script or on* handler: []
PASS §2.2 #2 404.html has a literal <title>…</title> and </head>
PASS §6.9 #7 404.html has no inline script or on* handler: []
PASS §6.9 #7 app/render.py emits no on* handler: []
PASS §2.2 #4 innerHTML only in the bill.js sanitize block (2 lines): static/js/bill.js:19:    return doc.body.innerHTML; | static/js/bill.js:56:        summaryDiv.insertAdjacentHTML('afterbegin', sanitized);
PASS §2.2 #2 no client write to document.title
PASS §3.3 no pushState call
PASS §3.3 no cookies
PASS §9.6 no Google Fonts hosts
PASS §2.2 #8 retired assets unreferenced
PASS §10.1 Sheets write paths, render.yaml and Dockerfile unchanged
PASS §10.2 no new web-runtime dependency (Pillow stays out of requirements.txt)
PASS live /: one <title>, </head>, no inline script/handler: []
PASS live /state?code=NY: one <title>, </head>, no inline script/handler: []
PASS live /member?id=S000148: one <title>, </head>, no inline script/handler: []
PASS live /bill?congress=119&type=hr&number=4795: one <title>, </head>, no inline script/handler: []
PASS live /about: one <title>, </head>, no inline script/handler: []
PASS live /methodology: one <title>, </head>, no inline script/handler: []
PASS live /privacy: one <title>, </head>, no inline script/handler: []
PASS live /no-such-page-in-this-edition: one <title>, </head>, no inline script/handler: []
GREP GATES PASSED
```

TTFB, local and warm (median of 5, `curl -w %{time_starttransfer}`):

```
/                                          median TTFB    3 ms  PASS
/state?code=CA                             median TTFB    2 ms  PASS
/member?id=S000148                         median TTFB    8 ms  PASS
/bill?congress=118&type=hr&number=21       median TTFB    3 ms  PASS
```

Startup:

```
startup 0.26 s (PASS < 2 s); votes_index roll calls loaded: 5423
```

Derived data regeneration:

```
REGEN IDENTICAL (ignoring generated_at)
```

## Scripted walkthrough (T11.3, §8 item 13, keyboard and reading-order half)

Keyboard only (Tab/Enter/Escape and typing; no clicks), at 375×812 and 1280×800: / → ZIP 11570 → /state → member → recent vote → bill → roll call → Share → feedback dialog → party toggle, plus the cv-home rules (#mine, cached 302 replay, Remember, split, partial, Forget, in-place ZIP, a dispatched bfcache pageshow re-filling the slot) and the §6.6 reduced-motion computed styles. Reading order was checked from the DOM and ARIA snapshots (one h1 first, no skipped levels, DOM order = visual order at 375, landmarks, no aria-live containers, no nested links, status nodes empty in the server HTML).

- 375px: 92/92 steps pass
- 1280px: 87/87 steps pass

ZIP 302 headers (GET without following redirects; `curl -I` is not used because FastAPI answers HEAD with 405):

```
== GET /state?zip=11570
HTTP/1.1 302 Found
cache-control: public, max-age=0, s-maxage=86400
location: /state?code=NY&district=4#mine
== GET /state?zip=11570
HTTP/1.1 302 Found
cache-control: public, max-age=0, s-maxage=86400
location: /state?code=NY&district=4#mine
== GET /state?zip=11570-1234
HTTP/1.1 302 Found
cache-control: public, max-age=0, s-maxage=86400
location: /state?code=NY&district=4#mine
== GET /state?zip=11201
HTTP/1.1 302 Found
cache-control: public, max-age=0, s-maxage=86400
location: /state?code=NY&zip=11201
== GET /state?zip=73949
HTTP/1.1 302 Found
cache-control: public, max-age=0, s-maxage=86400
location: /state?code=TX&zip=73949
== GET /state?zip=44101
HTTP/1.1 200 OK
cache-control: public, max-age=0, s-maxage=600, stale-while-revalidate=3600
== GET /state?zip=abc
HTTP/1.1 200 OK
cache-control: public, max-age=0, s-maxage=600, stale-while-revalidate=3600
== GET /api/districts/11570
HTTP/1.1 200 OK
cache-control: public, max-age=86400, s-maxage=86400
== GET /api/districts/abc
HTTP/1.1 400 Bad Request
cache-control: no-store
```

## Findings verified here

| Finding | Verified by |
|---|---|
| F03 ZIP → district on site | walkthrough: ZIP 11570 lands on NY-4 with cv-home written |
| F04 one shareable delegation URL | walkthrough + gates on `/state?code=NY&district=4` |
| F05 no request-path scans | pytest `test_page_routes_never_scan_roll_call_files`, TTFB |
| F14 reflow at 320/375 | gates `scroll` on every page |
| F16 grey tokens pass AA | gates `tokens`/`contrast` recomputed from site.css |
| F24 accessible feedback dialog | walkthrough: focus on textarea, trapped, Esc returns focus |
| F25 party reveal | walkthrough: one control, sessionStorage only, new session hidden |
| F43 no aria-live containers | walkthrough reading-order check |
| F44 focus kept/moved | walkthrough: Forget keeps focus; in-place result focuses the heading |
| F45 focus ring | walkthrough: 2px outline on every control reached by Tab |
| F47 44px targets | gates `targets` |
| F54 member page never ships the vote file | TTFB on `/member?id=S000148`, pytest scan guard |
| F55 layout shift, third-party fonts | gates `cls`, `thirdparty` |
| F60 no link inside a link; reduced motion | walkthrough nested-link check; walkthrough reduced-motion check (computed `scroll-behavior: auto`, 0s transitions) |

## Not verified here

- §8 item 13 VoiceOver/NVDA pass: a human pass Joseph runs on the branch before merging (PR body, "Before merging"). The scripted keyboard and reading-order half above does not replace it.
- §6.9 #10 `cf-cache-status: HIT` on the second request: needs Joseph's Cloudflare Cache Rule (PR body, ops step 1a). Until it passes, F63 stays unmitigated.
- §12.4 ops step 2: the first weekly sync after merge runs `votes-index` and `state-overview` with their commit steps.
