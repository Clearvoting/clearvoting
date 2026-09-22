# ClearVoting redesign — design spec (2026-09-18)

**Status:** synthesized 2026-09-18 from the judged panel; **the adversarial critique pass (feasibility / user / trust critics + revision) has not run yet** — run it before writing the implementation plan (see STATUS.md handoff of 2026-09-22). Single source of truth for the implementation plan once revised.
**Basis:** the "Spine" approach (judged winner, 135/150) with grafts from "Broadsheet", "Share" and "Evolve" where three judges recommended them and they strengthen the spine. Every graft decision is recorded in §2.4.
**Inputs:** `docs/reviews/2026-09-10-redesign-review.md` (F01–F63, Appendix C), `docs/reviews/2026-09-10-redesign-review-brief.md` (hard constraints, ZIP feasibility), `docs/001-prd-clearvote.md` (target user, success criteria), the four proposals under `~/.clearvote-worktrees/tools/design/`, and the code and data at `redesign/2026-09` (verified 2026-09-18 with `ls`/`python`; every field named below exists in `data/synced/` unless it is explicitly marked **new**).
**Dates:** today 2026-09-18; Election Day Tuesday 2026-11-03 (46 days). Data facts used below, from the repo: 150 members (CA 54, TX 39, FL 29, NY 28; 8 senators), 1,610 bills, 1,550 AI summaries (60 missing; newest summarized bill acted 2026-06-30; newest bill acted 2026-09-03), 5,369 roll calls (2,839 House, 2,530 Senate), `sync_metadata.last_sync` 2026-09-05, member narratives generated 2026-03-16 → 2026-07-02, donations for 80 members (2024 cycle, retrieved 2026-03-20), one member without a photo (W000832), ZIP crosswalk 6,639 ZCTAs of which 1,485 span more than one district.

---

## 1. Summary

**What changes for the person using the site.** You type your ZIP code on the first screen of the front page and land on one page that shows your two senators and your House member, with how each of them voted on the most recent bill. Tap a name and the first thing you see is a dated vote, in plain English, with a "Voted yes" or "Voted no" mark — not a paragraph and not a chart. Tap a vote and the bill page tells you what the bill does, what happened ("The House passed it, 237 to 169, on September 3, 2026") and how *your* representatives voted, before it shows anyone else. Every page says what date its facts are from, says plainly when a plain-English summary has not been written yet, never shows a score or a ranking, keeps party labels hidden until you ask, works on a phone without anything floating over the content, and can be shared with a real share button and a proper preview card. Party labels stay hidden until you ask, on every visit.

**The three outcomes this redesign is accountable for.**

1. **Two taps to your people.** A first-time visitor reaches the page of any one of their own three members in two taps from the front page (ZIP → delegation → member), on a 375px phone, with JavaScript off if need be. Measured in QA with the scripted path in §8.6 and, after launch, from server logs (`/state?zip=` → `/state?code=` → `/member` sequences).
2. **The record on the first screen.** On every member page at 375×812 the first dated, linked vote with the member's position is visible without scrolling; on every bill page the outcome sentence and the "How did your representatives vote?" block are visible without scrolling. Verified by the fold checks in §6.9.
3. **Nothing on the site says something the data does not support.** Both P0s (F01, F02) are closed by design, every AI-authored block carries its own date, every freshness stamp describes only the content beside it, and no module presents unsourced text as content. Verified by the copy checklist in §7.7.

---

## 2. Principles and guardrails

### 2.1 Protect (from the review's "What's working")

- The masthead + footer chrome (double rule, Playfair logo with the italic blue "Voting", uppercase Inter nav, tagline "Facts only · No opinions · No spin", footer credo) stays as one identical block on every template. It is compacted (§6.3) but not redesigned.
- The broadsheet language — Playfair Display for display, Lora for body, Inter for kicker/meta/UI, navy ink on paper, double rules and hairlines, kickers, the "STILL IN CONGRESS"-style status seal, the section-mark provision bullets — is the system; the redesign finishes it, it does not replace it.
- The plain-English bill lead pattern (one-liner headline, 3–4 Lora provision bullets, official title demoted to "Officially: …") is the template for every bill surface.
- The member narrative and the key-bills picker logic (dedupe per bill, skip anything without a plain summary, spread across policy areas) are kept; the picker moves server-side unchanged except for its counts (§4.3).
- Party hidden by default is executed at the data layer (server strips `partyName`/`party`); revealed only by an explicit action.
- Primary-source escape hatches ("Roll call source →", Congress.gov links) stay on every surface where they exist today.
- The official summary stays sanitized through `bill.js`'s existing `sanitizeHtml`/`SAFE_TAGS` block and collapsed.
- Chronological vote data, the two Google Sheets write paths, the newest-first bill sort and the server-side SEO injection (`_inject_meta`) stay untouched in behaviour.
- Existing accessibility scaffolding (skip link, landmarks, `role=status` on notify, visually-hidden labels, reduced-motion switch) is extended, not replaced.

### 2.2 Must not (from the review's "should NOT do" plus the brief's hard constraints)

1. No framework, no build step, no database: FastAPI + vanilla HTML/CSS/JS, flat JSON in `data/`. One PR, merged by Joseph.
2. Every shell keeps a literal `<title>…</title>` and `</head>`; the server owns the title; no client script writes `document.title`.
3. CSP `script-src 'self'`: no inline scripts, no inline event handlers (`onerror`, `onclick`). `img-src 'self' https://www.congress.gov` only.
4. No new `innerHTML`. `bill.js`'s `sanitizeHtml`/`SAFE_TAGS` block stays.
5. `feedback.js` structural hooks stay (`#feedback-modal`, `#feedback-open`, `#feedback-cancel`, `#feedback-overlay`, `#feedback-form`, `#feedback-message`, `#feedback-submit`, `#feedback-status`, `#feedback-context`, `.state-header h1`, `#data-freshness`, `#about-feedback-cta`). The single sanctioned change: `.member-header h2` → `.member-header h1` and `.bill-header h2` → `.bill-header h1`, with the two selectors in `feedback.js` changed in the same commit.
6. Real data only. The only new data files are (a) `data/zip_districts.json` (Census 2020 ZCTA ↔ 119th CD relationship files, public domain) and (b) `data/senate_2026.json` (Senate seats up for election in 2026, from senate.gov). Both carry a `_source` key and an entry in `data/SOURCES.md`. Nothing else is invented; no field is shown that is not in `data/synced/` or those two files.
7. No URL-shape changes. No clean-path aliases in this PR (so no 301 work); `?district=` and `?zip=` are additive query parameters on `/state`; canonical tags point at one form (§3.3).
8. No re-skinning of the old cards: `styles.css` and `broadsheet.css` are retired and replaced by one fresh `static/css/site.css`; `.glance-card`, `.viz-section`, `.bill-section`, `.state-stat`, `.comparison-table`, `.mobile-card`, `.service-compact` cease to exist.
9. No scores, grades, rankings or characterizations: no participation traffic lights, no high-to-low sorts, no yes-percentages on list rows, no "fights for", no "leans". Comparison only on non-ordinal facts (chamber, district, tenure). Red/green appear only inside the one vote component (§6.5).
10. Party labels never enter a default payload and the reveal never persists across visits.
11. The AI sync is not fixed here and the design does not assume it is fixed: newest-by-date Record, real empty states, dated AI blocks, a coverage note. When the sync resumes the design needs no change.
12. No promises that will not be true by November 3: no "we're adding more states" without a date; the notify form promises only what it can deliver; coverage is stated at the point of choice.
13. Definition-of-done gates, not preferences: nothing floats over the primary action on a phone; no control under 44px; no text under 12px; no text colour below 4.5:1 on paper or white; `document.documentElement.scrollWidth <= innerWidth` at 320 and 375; no content that defaults to `opacity:0`.

### 2.3 Appendix C contradictions, each resolved with a stated principle

| # | Contradiction | Principle | Resolution in this spec |
|---|---|---|---|
| C-1 | "Voted yes 49 %" praised as vocabulary vs F06/F08 calling the percentage noise | **A row shows the record, never a ratio.** Words stay, statistics go. | "Voted yes / Voted no" is the site-wide vocabulary (vote chip, tally labels, outcome sentences). No rate appears on any list row. Roster rows carry one dated vote with the member's position (§4.2). |
| C-2 | Keep the both-sides arguments pairing vs F13 drop the module | **"No opinions" is a constraint on the body, not a slogan on the masthead: unsourced text does not appear as content.** | The AI-drafted "What People Are Saying" / arguments module is **cut** from the bill page and from About. The neutrality proof moves to where it is true: party hidden by default, primary-source links on every row, a date on every AI block. A sourced replacement (attributed statements, floor debate, CBO/GAO) is deferred (§12). |
| C-3 | The Record on mobile is a "clean stack" vs F37's 15-line official titles | **The container was right; the row payload was wrong. Official text is bounded wherever it appears in a list.** | The single-column stack stays. Official titles leave summarized rows entirely (they live on the bill page as the deck) and are clamped to two lines, set in Lora 500, when they are the only headline available (§6.4). |
| C-4 | F07 "hide campaign finance until current" vs F56's visible Money section | **Show dated facts; never headline an undated or stale number; never a tile.** | One inline sentence below the record, only for the 80 members with a `donations.json` entry, built from `totals` with the cycle and the retrieval date in the sentence, plus an FEC.gov link built from `fec_candidate_id`; nothing for the other 70 (§4.3 module 7). No headline figure, no bars, no top-donor rows. |
| C-5 | F30 "three sticky layers" vs F07 asking for a mobile name strip vs "at most one sticky" | **One sticky element per page, and only where the page is long enough to need it; it must answer "where am I".** | Member and bill pages get exactly one 44px strip that appears after the header scrolls off (mobile and desktop); the delegation page and home have none. Tab bar and sticky filter row no longer exist (§6.6). |
| C-6 | F03/F41 propose new data files vs hard constraint 5 | **The constraint forbids invented data, not attributed public data.** | The brief (2026-09-18 revision) sanctions exactly these two files; both ship with a `_source` key, a build script for the crosswalk, an entry in `data/SOURCES.md`, and a paragraph on `/methodology` stating the land-area caveat (§5.1). |
| C-7 | F46 promoting h2→h1 vs constraint 4 | **A hook is a contract between two files; changing both sides in one commit honours it.** | Done exactly as constraint 4 allows: the two selectors change in the same commit as the h1 promotion; every `#feedback-*` id and `#data-freshness` are untouched; a test asserts both selectors resolve on the rendered pages. |
| C-8 | F53 CDN-cached shells vs localStorage personalisation vs F19 server-rendered first blocks vs F01 freshness | **The server renders only what is identical for every visitor of a URL; the browser adds only what belongs to this reader; a cache shorter than 1 % of the data cadence is invisible.** | Shells and API JSON carry nothing per-visitor (the delegation page is per-URL, not per-reader; the bill page's "your representatives" slot is server-rendered as the ZIP form and swapped by JS from storage). Shells are cached at the edge for 10 minutes (`s-maxage=600`) against a weekly sync; the "as of" stamps are rendered from the same cached data so they can never disagree with the content beside them. F01's ten-week staleness was a filter bug, unrelated to a ten-minute edge cache (§9.5). |
| C-9 | F20's on-demand Pillow og-image routes vs F05/F63 "no headroom on the free worker" | **Render once, serve from the edge; never render on the request path.** | Phase A ships four static 1200×630 cards (made once, committed); Phase B (last, cuttable) pre-renders 150 member + 4 state cards at sync time into `static/og/`. No per-request rendering exists in either phase; bill pages use the static bill card (§9.3). |
| C-10 | Key-bills picker "sound, needs surfacing" vs F08's hardcoded 6-vs-4 asymmetry | **Keep the logic, print the rule, balance the output.** | The picker's selection logic moves server-side unchanged; counts become 4 yes + 4 no; the rule is printed under the list (§4.3 module 2). |
| C-11 | "Latest Vote ships hidden" as graceful degradation vs F55's layout shift | **Degrade by content, not by geometry.** | The card is server-rendered so it never appears late; if the votes index is unavailable at render time the server emits the card at the same size with "The latest vote isn't available right now." (§4.1 module 3). |
| C-12 | Five pages assessed vs six templates | — | The 404 page is designed as a page on the spine (§4.8) and gets a real status code (§9.4). |
| C-13 | F04 "remember the last state in localStorage" vs "never persist the party reveal" | **Remember where you live, never how you look. Persist facts about the reader; never persist a lens on the data.** | `localStorage['cv-home']` holds `{state, district}` with a visible "Remembered: New York, District 4 · Forget" control; `sessionStorage['cv-show-party']` holds the reveal for one visit only; both rules are written on `/privacy` (§5.4). |

### 2.4 Judge grafts — adopted and declined

Adopted (with the section that specifies them): Share's bill-page roll-call composition (§4.4); the one-line edition line as the single carrier of freshness (§6.3, §7.4); a real Share action as a 44px secondary control in the header action row, not a large primary button (§6.4); per-state tally and "your rep" chip on the Latest Vote card, client-side (§4.1); photo fallback as an initials block and the outlined grey "Not on the ballot" seal (§6.4); cutting the arguments module (C-2); "Your representatives" block on the front page for returning visitors (§4.1); the bill fact box `<dl>` and the Lora-500 rule for official titles standing in as headlines (§4.4, §6.4); definition-of-done gates as checks plus a print block (§6.9, §6.8); tally inside the status seal ("Passed the Senate 90–6") on record rows (§7.2); a desktop-only fact strip in the member header folded to one line on mobile (§4.3); og:image in two steps (§9.3); `data/SOURCES.md` and inline `role=status` error copy (§5.1, §7.6); Share's honest amendment-row wording (§4.3 module 4); the coverage-aware notify form with a required state select behind "Somewhere else?" (§4.1 module 2); the storage principle in one line (C-13); path-first build order with the stylesheet retirement as the last, gated commit (§10.3); "Where do you live?" as the visible question above the ZIP field with state links showing real counts (§4.1); one checkbox with a count as the record's summary filter (§4.3 module 4).

Declined, with reasons: **Evolve's `?zip=`/`?state=` on the homepage with `history.replaceState`** — unnecessary because the ZIP form is a plain GET to `/state` that JavaScript never intercepts, so there is no JS-enhanced path to fall back from; adding a second URL for the same delegation would recreate F04. **Evolve's collapsed "Votes by topic" raw-count table** — raw yes/no counts per policy area invite exactly the ratio reading F06 forbids ("18 no on Environmental Protection" reads as a score), and F28's own test is "cut if it cannot be made neutral"; the record's topic `<select>` gives the same navigation with linked, dated votes instead. **Evolve's "attendance shown only when below 90 %" row copy** — participation is shown on every member header as a count ("Voted in 1,060 of 1,061 roll calls"), never on roster rows and never as a threshold, so there is no absence to explain; the rule "a count, never a grade" is stated once on `/methodology`. **Share's `&zip=` parameter on the bill URL** — the bill page's slot is filled from storage; a ZIP entered on a bill page submits to `/state?zip=` (the reader gets their delegation, a real outcome with JS off) rather than adding a second URL shape to 1,610 pages.

---

## 3. Information architecture

### 3.1 Pages and URLs after the redesign

| URL | Page | Change |
|---|---|---|
| `/` | Home: the entrance to the spine | Rebuilt. In-page delegation renderer retired; state cards become links; ZIP form first. |
| `/state?code=NY` | Delegation: the one canonical, shareable, server-rendered roster | Rebuilt on the homepage delegation component. Additive params: `&district=4` (shows "Your representatives"); `&zip=11201` (split-ZIP choice). `/state?zip=11570` (no code) is the form target: single match → **302** to `/state?code=NY&district=4`; split → **200** at `/state?code=NY&zip=11201`; unknown/uncovered → **200** at `/state?zip=44101` rendering the "can't place this ZIP" state. Invalid `code` (not CA/FL/NY/TX after uppercasing) → **404**. |
| `/member?id=S000148` | Member: header → key votes → summary → the record by bill | Rebuilt, record-first, server-rendered. Additive params for the record: `&page=2`, `&topic=Health`, `&plain=1`. Unknown id → **404**. |
| `/bill?congress=119&type=hr&number=4795` | Bill: what it does, what happened, how your representatives voted | Rebuilt, server-rendered. `type` is lower-cased before lookup and in canonical. Unknown bill → **404**. |
| `/about` | Who runs this, why, funding, contact, what the site does not do | Rewritten; static; no animation. |
| `/methodology` | **New.** Sources, cadence, the neutrality rules, what AI touches, coverage gaps with numbers, the key-votes rule, the ZIP caveat, a dated corrections log | New static shell with one server-filled paragraph (§4.6). |
| `/privacy` | **New.** What is stored, where, how long; browser storage; no third-party requests | New static shell (§4.7). |
| 404 | "Not in this edition" with the ZIP form | Rewritten; real 404 status for unknown ids/codes and unknown paths (§4.8). |
| `/favicon.ico` | **New route** serving `static/favicon.svg` content with a long max-age (or a small ICO) | F52. |
| `/static/og/*.png` | Share cards (Phase A: 4 static; Phase B: per member/state) | §9.3. |
| `/bills` | Bill browse/search page | **Deferred** (§12). The homepage keeps its collapsed browse panel at the foot with the "Load more" offset bug fixed and `?q=` reflected with `history.replaceState`; nothing else changes there. |

Retired: the homepage's in-page delegation (`app.js` `loadDelegation`/`selectState`), the member tab bar, the bill TOC row, the bill "What People Are Saying" module, `viz.js`, `styles.css`, `broadsheet.css`, all three `document.title` writes, the floating Feedback pill under 880px.

### 3.2 The primary path

1. `/` — type a ZIP into the first screen's field and press **Find my representatives**. The form is `<form method="get" action="/state">` with `<input name="zip" inputmode="numeric" pattern="[0-9]{5}" autocomplete="postal-code">`; JavaScript never intercepts it.
2. `/state?zip=11570` → the server resolves 11570 → NY-4 (single district with ≥5 % land share) → `302` → `/state?code=NY&district=4`. The page opens with **Your representatives** (Sen. Kirsten E. Gillibrand, Sen. Charles E. Schumer, Rep. Laura Gillen — District 4), then the full New York roster. Because `district` is in the URL, `site.js` writes `cv-home = {state:"NY", district:4}`.
   - Split ZIP: `/state?zip=11201` → `200` at `/state?code=NY&zip=11201` — the two senators, then "ZIP 11201 spans two House districts — which is yours?" listing Districts 10 and 7 (72 % / 28 % of the ZIP's land) as full member rows with a "This is my district →" link each (`/state?code=NY&district=10`). Nobody is blocked: the names already link to member pages.
   - Unknown or uncovered ZIP: `/state?zip=44101` → `200`: "We couldn't place ZIP 44101 in California, Florida, New York or Texas — the four states ClearVoting covers today." + the four state links + the notify form (with state select) + the house.gov link (§5.5). Non-5-digit input → the same page with "A ZIP code is five digits."
3. Tap a member → `/member?id=G000602`. First dated vote on the first screen.
4. Tap any vote → `/bill?…`. Outcome sentence and "How did your representatives vote?" in the fold, filled from `cv-home`.
5. The masthead nav item **My representatives** on every page goes to `/state?code=NY&district=4` when `cv-home` exists (rewritten by `site.js` at load; the server-rendered `href` is `/#find`), else to `/#find`.

Success measure: two taps from `/` to a member page; three to the bill. Back always returns to a real URL.

### 3.3 URL state rules

- **Canonical forms** (the only forms in `<link rel=canonical>`, the sitemap and Share): `/`, `/state?code=XX` (uppercase), `/member?id=X` (uppercase id), `/bill?congress=N&type=xx&number=N` (lowercase type), `/about`, `/methodology`, `/privacy`. The server normalizes case before lookup and before building canonical; a request with `type=HCONRES` renders with canonical `type=hconres`.
- **Additive, non-canonical, cache-safe parameters** (canonical strips them): `/state` `district`, `zip`; `/member` `page`, `topic`, `plain`. They are real server-side state (the server renders accordingly), so they work with JS off and Back restores them. The Share control never includes them.
- **Shareable selections that exist as URLs:** a state (`/state?code=NY`), a district's delegation (`/state?code=NY&district=4` — shareable but not canonical), a page of a member's record with a topic filter (`/member?id=S000148&topic=Health&page=2`), a bill. Topic-filtered bill lists (`/bills?topic=`) are deferred with `/bills`.
- **Storage** (§5.4): `localStorage['cv-home']`, `sessionStorage['cv-show-party']`. Nothing else. No cookies.
- **No `pushState`.** The only `history.replaceState` on the site is the homepage browse panel reflecting `?q=` (existing panel, F38 partial).

---

## 4. Page specs

Common to every page: compact masthead (§6.3), edition line (§7.4), `<main id="main-content" tabindex="-1">`, footer with the three trust links repointed (`/about`, `/methodology`, `/privacy`), "Report an error on this page" (`id="feedback-open"`), the data-source line with `#data-freshness` rendered only when a value exists (server-rendered from `last_sync`, the JS refresh from `/api/health` stays), the credo. Server-rendered content is inserted at a literal `<!--content-->` marker inside `<main>` by `_serve_html` (§9.1); each shell's `<main>` also carries `<noscript>` copy only where JS adds something (stated per page). Error state when the server cannot render (data missing at request time): the shell renders the masthead, the H1 from meta, and the sentence "We couldn't load this page right now. Try again in a moment, or use *Report an error* below to tell us." — never a Congress.gov excuse (F61).

### 4.1 Home (`/`)

**Purpose.** Get the reader onto the spine in one action; prove the promise (a real vote, in plain English, dated honestly) without spending the first screen on it.

**Mobile fold (375×812).** Masthead (logo, tagline, nav on one 44px row; ≈120px) → edition line (one line, ≈24px) → kicker "An independent record of Congress" → H1 "See how your representatives vote." → one-line deck → the finder: the visible question "Where do you live?" (Lora italic, `<label for="zip">`), a 48px ZIP field full width, a 48px full-width navy button **Find my representatives** (input and button stack under 560px so the field is never squeezed) → the line "Or choose a state:" with four 44px chips "California · 54", "Florida · 29", "New York · 28", "Texas · 39" (counts server-rendered from `get_member_counts()`) → the coverage sentence. Everything above lands by ≈560px; nothing else is on the first screen. If `cv-home` exists, `site.js` inserts under the button: "Remembered from your last visit: New York, District 4 → **Show my representatives** · Forget".

**Desktop fold (1280×800).** Two-column lead (3:2). Left: kicker, H1, deck, finder, state chips, coverage sentence, "Somewhere else?" disclosure. Right: the Latest Vote card. Both columns finish within ≈700px so "The Record" head is visible.

**Modules in order** (all server-rendered unless marked JS):

1. **Masthead + edition line** (§6.3, §7.4).
2. **Lead + finder.** Sources: counts from `data_service.get_member_counts()`; coverage sentence from `len(members)` and the fixed start of the vote record: "ClearVoting covers California, Florida, New York and Texas today — 150 members, every roll-call vote since January 2021." **"Somewhere else?"** is a native `<details>` holding the notify form: required `<select name="state">` (50 states + DC, "Choose your state"), `<input type="email" autocomplete="email">` 16px/48px, navy button **Notify me**, and the line "We store your email and your state, nothing else. *Privacy →*". POST unchanged (`/api/notify` accepts `email`, `state`). Success (JS, `role=status`, focus moved to it): "Thanks — we'll email you when {State} is added." Failure: "We couldn't save that. Try again, or email {contact} (see About)." Duplicate signups are treated as success. No-JS: the form posts normally and the API's JSON response is shown; acceptable (documented in `<noscript>`: "Sign-up confirmation needs JavaScript").
3. **The Latest Vote** — a structured `<aside class="vote-card">`, never a sentence template. Server-rendered from `get_latest_vote()` (extended, §10 #9): kicker "The latest vote"; dateline "U.S. House · September 3, 2026 · Final vote to pass" (`chamber`, `vote_date` via the date helper, `plain_question`); headline = AI `one_liner` in Playfair when the bill has one, else the official `bill.title` in Lora 500 clamped to two lines with the status chip "No plain-English summary yet"; the tally bar (§6.4) with "237 yes · 169 no"; the outcome line "Passed the House" as a status seal; the link "What this bill does, in plain English →" when a summary exists, else "See the vote and the official summary →". **JS enhancement** when `cv-home` exists: one appended meta line "New York: {n} yes · {n} no · {n} didn't vote · Your rep, Laura Gillen — **Voted yes**", computed from `state_tallies` and `covered` in the same payload (§10 #9); for a Senate vote the two senators' chips instead. Rule for which vote is shown (F02): the most recent roll call by date whose `document` parses to a bill in `bills.json`, decisive votes first within a day (existing logic) — a newer un-summarized vote is **not** skipped; it is shown honestly with the fallback headline. Edge cases: nomination or non-bill `document` never becomes the hero (existing `_parse_bill_document` filter); a tie renders "Tied, 50 to 50" and the result string; voice votes have no roll call and never appear. If the votes index is unavailable: the card renders at the same size with "The latest vote isn't available right now." (C-11).
4. **Your representatives** (JS only; absent for first-time visitors). When `cv-home` exists, `site.js` renders the identical three person rows the delegation page uses (§6.4 person row) from `/api/members/{state}/overview` (precomputed file, cached), under the head "Your representatives · remembered from your last visit · *Change* · *Forget*". Same component, same copy, no separate design.
5. **The Record.** Head: kicker "The Record", H2 "What Congress is doing, in plain English", stamp line "As of September 5, 2026 · newest first · Plain-English summaries are written through June 30, 2026; newer bills show their official title until a summary is written — nothing is left out." (`last_sync`; `summaries_through` = newest `latestAction.actionDate` among bills that have a summary, added to `/api/health` and used here). **Lead article** = the newest bill *with* a summary (`/api/bills?summarized_only=true&limit=1`): kicker (bill code · Congress ordinal), status seal with tally (e.g. "Rejected by the House 189–235"), date, Playfair headline = `one_liner`, the section-mark provisions (max 4), "Officially: {title}" capped at 140 characters with "Show full title" `<details>` when longer, link "See who voted →". **List** = the six newest bills by `latestAction.actionDate` regardless of summary (`/api/bills?limit=6`, default order now newest by action date with `one_liner` nullable): each row = kicker bill code, status seal (derived, §7.2), date, headline (Playfair `one_liner`, or Lora 500 official title clamped to two lines + chip "No plain-English summary yet"). No official title on summarized rows. Foot: "Browse all bills by topic →" (existing collapsed panel, unchanged except the offset fix and `?q=` in the URL).
6. **Footer.**

**States.** API/data unavailable at render: hero as above; Record renders the stamp line and "We couldn't load recent bills right now." No-JS: everything above renders; only modules 4 and the Latest Vote's per-state line are missing; the browse panel needs JS (its `<noscript>` says so).

**Removed and why.** The in-page delegation, its party toggle, its scroll-to-spinner and the `/api/members/{state}?include_stats=true` call (F04, F05, F21); "Voted yes 49 %" bars (F06); the sentence-template hero (F17); official titles on Record rows (F37); "Updated weekly" and the trust line (replaced by dated facts, F40); the red notify button and the state-less notify form (F35, F39); the external house.gov link as the only district help (kept only in the unknown-ZIP state, §5.5).

### 4.2 Delegation (`/state?code=NY`, with `&district=` / `&zip=`)

**Purpose.** The shareable, crawlable home of a state's delegation and the page every ZIP lands on; the page a search for "New York representatives voting record" should land on.

**Mobile fold.** Masthead + edition line → kicker "New York · 28 members · roster as of September 5, 2026" (`roster_as_of` = max `updateDate` in the state's members) → H1 "Your representatives" (when `district`/`zip` is present) or "New York's representatives" → the district line: "New York, District 4 · *Change ZIP*" (44px; when `district` present) or the compact ZIP form (same component as home, one row: field + 48px button) → action row: party toggle (§6.4), Share → the first person row in full. On the split-ZIP state the "spans two districts" block sits between the senators and the House pick, within the second screen.

**Desktop fold.** Same, with the three "your" rows in a 3-up grid under the header and the roster beginning immediately below.

**Modules in order** (server-rendered from `data/synced/state_overview/{code}.json`, §10 #5):

1. **Header** as above. The `<h1>` sits inside `.state-header` (hook kept). Party toggle and Share are 44px controls in one action row.
2. **Your representatives** (only with `district` or `zip`): two senator rows, then the House row(s). Split ZIP: the sentence "ZIP 11201 spans two House districts — about 72 % of its land is in District 10 and 28 % in District 7. Both are shown; your street decides which is yours." then each House row with a sibling link "This is my district →" (`/state?code=NY&district=10`). These rows are the one place a person row is a `<div>` with the name as the link and the district link as a sibling (no link-inside-link, F60). If the crosswalk names a district with no member in `members.json`: a row "District 7 — vacant in our data · *Tell us if this is wrong*".
3. **U.S. Senate** — group label "Both represent all of New York", two person rows.
4. **The House, by district** — label "By district, 1–26", person rows in district order; at ≥880 two columns. Vacant districts (numbers 1..N not present in `members.json`, N from the expected count in the sync) render as "District 7 — vacant in our data".
5. **Foot:** "Don't know your district? Enter your ZIP" (the same inline form), "Roster from Congress.gov, as of {roster_as_of} · Wrong person? *Report an error*", the Congress.gov delegation link, the notify disclosure for other states.

**Person row content** (§6.4): photo (56px, initials fallback), name (Playfair, the link covering the row), seat line "District 4 · In Congress since 2025" (from `district`, `terms.item[0].startYear`) with the ballot seal "On the ballot Nov 3, 2026" (House: always; Senate: only ids in `senate_2026.json`) or nothing for senators not up (the "Not on the ballot" seal is used on the member page only), and one signal line: "Latest vote · Sep 1, 2026 · {one_liner} — **Voted yes**" = the member's most recent vote in `member_votes/{id}.json` with `has_plain_summary == true` and a non-null `bill_id`, with the member's position as a vote chip and the row's link target unchanged (the bill is one tap further, on the member page). It is expected that most rows show the same bill; that is the first differentiating fact the roster has shown and it is the record, not a score. Members with no qualifying vote (short record): "No plain-English votes on record yet".

**Party reveal.** Rows are server-rendered with an empty `<span class="party"></span>`. On toggle, `site.js` fetches `/api/members/{code}/overview?show_party=true` (same file, party not stripped) and fills the spans with full names ("Democratic", "Republican", "Independent"); nothing re-renders; one `role=status` line says "Party labels shown".

**States.** `code` missing → the ZIP finder page (H1 "Find your representatives", the form, the four state links). Invalid `code` → 404. `district` out of range or not in the roster → the roster with "We don't have a District 40 in New York" above it. Overview file missing (first deploy before sync) → the server falls back to `get_members_by_state()` without signal lines and logs a warning. No-JS: everything renders; party reveal and the `cv-home` write need JS (`<noscript>`: "Party labels and the remembered-district link need JavaScript").

**Removed and why.** The four stat boxes ("60K votes cast"), participation bars and thresholds, support-rate sort, Total Votes, the alphabetical default, the comparison table and its fake-sortable headers, the mobile card variant, the 150-char narrative snippet, the `document.title` overwrite (F06, F34, F36, F48, F20).

### 4.3 Member (`/member?id=S000148`)

**Purpose.** Who this person is and how they have actually voted, in plain English, with the first dated vote on the first screen.

**Mobile fold (375×812).** Masthead + edition line → breadcrumb "← New York's representatives" (`/state?code=NY`; when `cv-home` matches the member's state, `site.js` points it at the district URL) → header: 64px bordered photo, kicker "U.S. Senator · New York" (House: "U.S. Representative · New York, District 4"), **H1** "Charles E. Schumer" (`displayName` from `name` "Last, First M."), the fact line "In Congress since 1981 — House 1981–1999, Senate since 1999 · Voted in 1,060 of 1,061 roll calls since January 2021" (from `terms.item`, `stats.total_votes`, `stats.not_voting_count`), the ballot seal ("On the ballot Nov 3, 2026" for House and listed senators; outlined grey "Not on the ballot Nov 3, 2026" otherwise), and the action row: party toggle · Share · Congress.gov → kicker "Key votes" and the first key-vote row with its chip, visible by ≈700px.

**Desktop fold.** Header as a byline block (photo left, name and fact line right, action row right-aligned) with the desktop fact strip (three cells: "Roll calls voted · 1,060 of 1,061", "Record covers · Jan 2021 – Aug 8, 2026" (min/max `date` in `member_votes`), "Party · hidden — Show party labels"); under it two columns (7:5): left Key votes (4 + 4 in two lists), right the summary with its date line. The record begins directly under both.

**Modules in order** (server-rendered from `get_member_page()`, §10 #8):

1. **Header** as above. `.member-header` wraps the `<h1>` (sanctioned hook change). One sticky element: a 44px strip with the name and two in-page links "Key votes · Record" appears after the header scrolls out (`IntersectionObserver` on the header; CSS `position:sticky` on a strip that is `hidden` until then); it is the only sticky element on the page.
2. **Key votes.** 4 supported + 4 opposed, chosen server-side by the existing picker logic (dedupe per `bill_id`, `has_plain_summary`, non-empty `policy_area`, spread across areas, most recent first; `Aye`→yes, `No`→no). Each row is the shared vote row (§6.4): chip "Voted yes"/"Voted no", Playfair headline = `one_liner` as the link to `/bill`, meta "H.R. 6500 · Passed the Senate 90–6 · Aug 8, 2026 · Economics and public finance" (bill code via the formatter, status seal text via §7.2 from `result`, date, `policy_area`). Caption under the list: "Chosen by rule, not by us: the most recent final votes on bills with a plain-English summary, spread across topics, four where the member voted yes and four where the member voted no. *How this works →*" (`/methodology#key-votes`). Short records: "2 key votes so far" with as many as qualify; none: the module is omitted.
3. **Summary.** H2 "In summary"; the narrative from `member_summaries.json[id].narrative`, at body size; on mobile the first three sentences visible, the rest behind a native `<details>` "Read the rest"; provenance line "Written by AI on June 14, 2026 from the official record; votes after that date are not reflected. *How we keep it neutral →* · *Something wrong here? Tell us*" (`generated_at`, the methodology link, the feedback opener). Omitted entirely when no narrative exists (no placeholder).
4. **The record.** H2 "Every roll call, by bill" with the count line "1,061 roll calls since January 2021 · 519 yes · 540 no · 1 not voting" — verbatim from `stats` (`yea_count`, `nay_count`, `not_voting_count`; `Present`/`Guilty`/other values are counted in an "other" figure only when non-zero: "· 1 other"). Controls (one row, native, 16px, 44px): `<select name="topic">` "All topics" + the member's `policy_areas`; `<input type="checkbox" name="plain" value="1">` "Only bills with a plain-English summary ({n} of {N} bills)"; a **Filter** button (the controls are a `GET` form to the same URL; JS may submit on change). Rows = groups, newest first, 15 groups per page:
   - **Bill group** (`bill_id` non-null): kicker bill code; status seal with tally from the final roll call's `result` (§7.2); date of the final roll call; headline = `one_liner` in Playfair when `has_plain_summary`, else the same string (the official title) in Lora 500 clamped to two lines with the chip "No plain-English summary yet" (the string is never printed twice, F09/F27); the member's chip for the final roll call; then, when the group has more than one roll call, a `<details>` "+ 2 more roll calls on this bill" listing each: plain question (§7.3) · result phrase · date · the member's chip · "Roll call source →" (a sibling link, never nested). The headline links to `/bill` for every type in the shared type map (H.R., S., H.J.Res., S.J.Res., H.Con.Res., S.Con.Res., H.Res., S.Res.), so resolutions link (F27).
   - **Amendments and motions group** (`bill_id` null): consecutive such votes are collapsed into one dated row per calendar day, e.g. "14 amendments and motions · Aug 8, 2026", a `<details>` listing each as "Amendment: "To strike section 2019." · parent bill not identified in our data · Set aside (tabled) 61–32 · **Voted yes** · Roll call source →" (the text is the vote's own `one_liner`/`bill_number` string, verbatim; no parent is ever inferred). Nominations (`bill_number` matching `PN\d+`) read "Nomination PN80 · Confirmed 52–46 · Voted yes". Speaker elections (`vote` is a surname) read "Election of the Speaker · Jan 3, 2025 · Voted for Jeffries" with no chip colour.
   - Pagination = real links "← Newer votes · Older votes →" carrying `page`, `topic`, `plain` and the fragment `#record` so the browser lands focus on the record heading (`tabindex="-1"`); `site.js` may enhance to fetch `/api/members/{id}/votes?group=bill&…` and swap in place, moving focus to the heading and calling `history.replaceState` — optional, cut first if the build slips.
5. **Sponsored bills ({count}).** Inline list of at most six rows (`get_bills_by_sponsor`), each: bill code (formatter) · headline (`one_liner` from the AI summaries when present, else `title` in Lora 500 clamped) · "Introduced {introduced_date}" · status seal derived from the votes index and `laws` (§7.2; when no floor vote: "In committee — no floor vote yet"). Omitted when the count is 0. Never the raw `latest_action` string.
6. **Ballot** — no separate module; the seal in the header and, for senators not on the list, nothing more (no "next up in 20XX": that year is not in the sanctioned data).
7. **Campaign money.** Only when `donations.json` has the member: one sentence — "In the 2024 election cycle this campaign reported $2.8 million raised ($2.3 million from individuals, $202,800 from PACs) and $3.3 million spent, according to the FEC; retrieved March 20, 2026. The 2026 cycle is not yet in our data. *Filings on FEC.gov →*" (`cycle`, `totals.total_receipts`, `totals.total_individual`, `totals.total_pac`, `totals.total_disbursements`, `last_updated`; link `https://www.fec.gov/data/candidate/{fec_candidate_id}/`). No headline number, no bars, no contributor rows (C-4).
8. **Footer** with "Report an error on this page".

**Party reveal.** The header carries an empty `<span class="party">`; on toggle `site.js` fetches `/api/members/detail/{id}?show_party=true` and writes `partyName` ("Democratic", "Republican", "Independent"); status line "Party labels shown".

**Share.** `navigator.share({title, text, url})` with title = the server title, text = "How Charles E. Schumer has voted in Congress, in plain English", url = canonical; fallback copies the canonical URL and shows "Link copied" in a `role=status` line beside the control for 3 s.

**States.** Unknown id → 404 page. Member without a photo (W000832) → initials block. Member without narrative → module 3 omitted. Member without donations (70) → module 7 omitted. Fewer than 8 qualifying key votes → as many as qualify with the count in the caption. Empty record page (topic filter yields nothing) → "No votes on {topic} in this record." and the controls. `member_votes` file missing → header from `members.json` plus "We don't have this member's roll-call record yet." No-JS: everything renders and paginates; party reveal, Share and the sticky strip need JS.

**Removed and why.** Donut, attendance ring/bar, three stat tiles, six topic bars ("What They Fight For"), the Service History card (folded into the fact line, correctly computed from all `terms`), tabs, the second sticky bar and the sticky filter row, "Copy Link", the client-side recomputation of key bills and stats, the `?limit=2000` download, the empty `vote-item-title` div, "Bill Bill Passed", empty policy chips, "Resolution — no details available" (F07, F08, F09, F26, F27, F28, F29, F30, F54, F56). "Votes by topic" is not carried (§2.4).

### 4.4 Bill (`/bill?congress=119&type=hr&number=4795`)

**Purpose.** "Congress just voted on X — what does it do, and how did MY representatives vote?"

**Mobile fold (375×812).** Masthead + edition line → kicker "H.R. 4795 · 119th Congress" with the status seal "Passed the House 237–169" → **H1** = `one_liner` (Playfair) when a summary exists, else the official title (Playfair — it is the only headline available) → deck: "Officially: {title}" in Lora 500 (only when the H1 is the one-liner) → the outcome sentence in Lora "The House passed it, 237 to 169, on September 3, 2026." → the tally bar → **How did your representatives vote?** with the three person rows and chips (JS from `cv-home`) or, server-rendered in the same slot, the ZIP form "Enter your ZIP to see how your representatives voted" (`GET /state`) — visible by ≈700px.

**Desktop fold.** Headline column (7) + fact box (5) side by side; the outcome sentence, tally and "How did your representatives vote?" under the headline column.

**Modules in order** (server-rendered from `get_bill_page()`, §10 #8):

1. **Story head**: kicker, seal, H1, deck, outcome sentence (§7.3; one per bill = the most recent decisive roll call; when there is no roll call: "No floor vote yet — introduced {introducedDate}."), tally bar for that roll call. `.bill-header` wraps the `<h1>` (sanctioned hook change). One sticky element: a 44px strip "H.R. 4795 · Passed the House 237–169 · Share" after the header scrolls out.
2. **How did your representatives vote?** Slot content by state: (a) `cv-home` present and the bill has a House roll call → the reader's House member row with the chip from `covered` (§10 #9; matched by `bioguide_id`), and for Senate roll calls the two senators' rows (matched server-side by `last_name` + `state` exactly as `sync.py build_member_votes` does, exposed as `covered`); a member absent from a roll call reads "Didn't vote"; (b) no `cv-home` → the ZIP form; (c) no roll call on the bill → the slot is omitted. Under the rows: "Remembered: New York, District 4 · *Change*".
3. **The vote, by state** (for the decisive roll call): four `<details>` groups "New York: {n} yes · {n} no · {n} didn't vote" (`state_tallies`), the reader's state open by default (JS; server renders all closed), rows in district order (`district` from `members.json` for covered members; the roll-call file has no district, so uncovered states are not listed here), each a two-line row: name (linked for the 150 covered members) + "District 4", chip right-aligned. Then **All {N} votes, every state** as a `<details>` with a name search `<input type="search">` (JS filter) and a "Show: all · yes · no · didn't vote" `<select>`, rows as above with the state in place of the district; uncovered members plain text. Never a horizontally scrolling table. Per roll call: caption "House roll call 295 · September 3, 2026 · Final vote to pass · Passed 237–169" (this caption is the visible heading and the `<caption>` when a `<table>` is used at ≥880), "Roll call source →". Server rendering rule: the full per-member list is rendered for up to two roll calls; for a bill with more, each extra roll call block renders its caption, outcome sentence, tally and state tallies, and the member list is fetched by `site.js` from `/api/votes/{chamber}/{c}/{s}/{n}` on first open (`<noscript>`: "Open the full list on the roll call source page"). One page-level party toggle in this section's head fills every list's party spans from `?show_party=true` (full names); no per-block toggles.
4. **What it does.** When a summary exists: the section-mark provision bullets (`provisions`), then "Summarized by AI from the official text. *How we keep it neutral →* · *Something wrong here? Tell us*". When none (60 bills today): no bullet, no AI line; the neutral note "We haven't written a plain-English summary for this bill yet. Summaries are written through June 30, 2026." followed by the first paragraph of the newest official summary (`summaries[-1].text` through `sanitizeHtml`) promoted open, then "Show the full official summary" `<details>`. When there is no official summary either: the note plus "Congress.gov has the bill text →". Loading copy anywhere JS fills: "Loading summary…", never "Generating…".
5. **Official summary** (when a plain summary exists): muted serif, collapsed under "Show the official summary"; existing `sanitizeHtml`/`SAFE_TAGS` block.
6. **Fact box** — a hairline-ruled `<dl>` (beside the headline at ≥880, after "What it does" below): Sponsor (linked only when `sponsors[0].bioguideId` is in `members.json`; else "Rep. Virginia Foxx (NC) — not in ClearVoting's coverage yet", plain text, built from `fullName` with the "[R-NC-5]" suffix stripped and `state`); Cosponsors (`cosponsors.count`); Topic (`policyArea.name`); Introduced (`introducedDate`); Latest floor action (derived from the votes index: "Passed the House · Sep 3, 2026"; else "None yet"); Became law (only when `laws` non-empty: "Public Law 119-6"); Congress.gov (`legislationUrl`); Share.
7. **Footer.**

**States.** No roll call → modules 2 and 3 omitted; fact box "Latest floor action: none yet". Many amendment roll calls → each a collapsed block after the decisive one, newest first. Both chambers → two roll-call blocks under one party toggle; the outcome sentence in the head is the most recent decisive one and the seal reads "Passed both chambers" when both passed. No official summary and no AI summary → module 4's minimal state. Malformed or unknown URL → 404. `type` in any case → normalized. No-JS: everything except the "your representatives" fill, the party reveal, the search filter and lists beyond the second roll call.

**Removed and why.** "What People Are Saying"/arguments (C-2), the TOC chip row, the one-chip tag row (`subjects` is a count), the floating Copy Link, "Latest action (2026-06-30): Motion to reconsider laid on the table…", the roll-call donut with 431 in the centre, "Yea/Nay", the 20,000px open table, the fake "procedural" apology with its AI disclaimer, the per-block party toggles, the sponsor link that 404s (F02, F10, F11, F12, F13, F15, F25, F32, F33).

### 4.5 About (`/about`)

**Purpose.** Who runs this, why, how it is funded, how to reach a human, what the site does not do.

**Fold (both viewports).** Kicker "About", H1 "About ClearVoting", the first paragraph. Static HTML, every section visible at load, no `.animate-*` classes, no observer.

**Sections in order:** Why we built this (existing copy, edited for length) · Who runs it — "ClearVoting is maintained by {name}, an independent volunteer. Contact: {email or form}." (open question §12) · Funding — "Unfunded and not affiliated with any campaign, party or advocacy group." · What we cover — "California, Florida, New York and Texas today: 150 members, every roll call since January 2021, 1,610 bills." (numbers server-filled from `/api/health` values) · What we don't do — no scores, rankings or endorsements; party labels hidden by default; no opinions. The "12 strict rules" sentence and "what people are saying" sentence are removed; neutrality detail moves to `/methodology` with a link. "Help us improve" keeps `#about-feedback-cta` (hook).

### 4.6 Methodology & Corrections (`/methodology`)

**Purpose.** The mechanism behind every trust claim, checkable in a minute by a teacher or a sceptic.

**Sections (anchors):** `#sources` — Congress.gov API (members, bills, House roll calls), Senate.gov XML (Senate roll calls), FEC (money), weekly automated sync; · `#freshness` — "Roll calls and bills are synced weekly; the edition line on every page shows the last sync and the newest roll call." · `#ai` — what the AI writes (bill one-liners and provisions, member narratives), what it never touches (votes, tallies, dates, names, outcomes, party); the neutrality rules copied verbatim from `app/services/ai_summary.py` under the heading "Our rules for neutrality" with no count in prose, guarded by a test that the page's list equals the prompt's; how summaries are graded (`audit_grades.json` exists; the number of bills flagged for review is stated as a count, never surfaced per bill) · `#coverage` — the server-filled paragraph: "{ai_summaries} of {bills} bills have a plain-English summary; {bills_missing_summary} do not. The summary writer has been paused since July 2, 2026; those bills show their official title. Member narratives were written between March 16 and July 2, 2026 and are dated where they appear." · `#key-votes` — the selection rule in full (§4.3 module 2) · `#counts` — "We show roll calls voted as a count, never as a grade, and never rank members by it." · `#zip` — the crosswalk source, licence, retrieval date, the land-area caveat ("shares are land area, not population; PO-box-only ZIPs are not in the Census file") and the ≥5 % rule · `#ballot` — the senate.gov source for seats up in 2026 · `#corrections` — "Corrections", a dated `<ol>` newest first, hand-edited, initially "No corrections logged yet." · `#report` — how to report an error (the feedback opener).

### 4.7 Privacy (`/privacy`)

**Sections:** What the notify form stores (email, state, timestamp) in a private Google Sheet; what the feedback form stores (message, page URL, timestamp); retention ("until you ask us to delete it — email {contact}"); what the browser stores — "We remember where you live, never how you look: your state and district stay in your browser (`cv-home`) until you press Forget; whether you revealed party labels is kept only until you close the tab and is never sent to us"; requests — "This site makes no third-party requests except member photos from congress.gov"; logs — "Server logs only, no cookies, no analytics scripts."

### 4.8 404

Kicker "Not in this edition", H1 "We don't have that page", one sentence "The link may be old, or the bill or member may be outside our four-state coverage.", the ZIP form ("Find your representatives instead"), the four state links, a text link to the front page. Navy button, no red. Served with status **404** for unknown paths, unknown `member?id=`, unknown `bill` keys and invalid `state?code=`. Cache `public, max-age=60`.

---

## 5. Find-your-representatives

### 5.1 The crosswalk data file

- **File:** `data/zip_districts.json` (**new**, sanctioned). Built by `scripts/build_zip_crosswalk.py` (moved from `tools/data/build_zip_crosswalk.py`, unchanged logic) from the four Census files `tab20_cd11920_zcta520_st{06,12,36,48}.txt` (U.S. Census Bureau, 2020 ZCTA ↔ 119th Congressional District relationship files, https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, public domain under 17 U.S.C. § 105).
- **Format:** `{"_source": {"name": "U.S. Census Bureau 2020 ZCTA to 119th Congressional District relationship files", "url": "…", "retrieved": "2026-09-11", "licence": "Public domain (17 U.S.C. §105)", "share": "land area (AREALAND_PART / AREALAND_ZCTA5_20)"}, "11201": [{"state": "NY", "district": 10, "share": 0.7216}, {"state": "NY", "district": 7, "share": 0.2784}], "11570": [{"state": "NY", "district": 4, "share": 1.0}], …}` — 6,639 ZCTAs, ≈413 KB raw, sorted, minified.
- **Trimming rule:** the build drops slivers under 1 % of the ZCTA's land (or keeps all when that would leave none); the lookup returns districts with share ≥ 5 %. **Single match** = exactly one district ≥ 5 %. Shares are shown to the reader only in the split-ZIP sentence, as whole percentages of *land*.
- **Attribution:** `_source` in the file, `data/SOURCES.md` (URL, licence, retrieval date, build command), `/methodology#zip`.

### 5.2 Endpoint contract

`GET /api/districts/{zip}` (new router `app/routers/districts.py`; the file is loaded once at startup).

- `zip` must be exactly five digits → else **400** `{"detail": "ZIP must be five digits"}`.
- Found: **200** `{"zip": "11570", "covered": true, "matches": [{"state": "NY", "state_name": "New York", "district": 4, "share": 1.0, "member_ids": ["G000602"]}]}` — `member_ids` from `members.json` (House members with that `stateCode` and `district`; may be empty for a vacancy).
- Not in the file or not in the four states: **200** `{"zip": "44101", "covered": false, "matches": []}`.
- Cache: `public, max-age=86400`. Rate limit: `slowapi` `60/minute` (the file is static; the limit only protects the worker).

The `/state` shell route calls the same in-process lookup (`data_service.lookup_zip`) — the API exists for `site.js` (the bill page never needs it) and for tests.

### 5.3 UI states

| State | Where | What renders |
|---|---|---|
| Single match | `302` → `/state?code=NY&district=4` | "Your representatives" block (2 senators + House member), roster below, `cv-home` written. |
| Split ZIP (2–4 districts ≥ 5 %) | `200` `/state?code=NY&zip=11201` | Senators, then the "spans N districts" block with each district's member row and "This is my district →". |
| Single match, district vacant in `members.json` | `302` → `…&district=7` | Senators; "District 7 — vacant in our data · Tell us if this is wrong". |
| Unknown ZIP (not in the Census file) | `200` `/state?zip=99999` | "We couldn't find ZIP 99999 in the Census district file. Try a neighbouring ZIP, choose your state below, or look up your district by street address on house.gov →" + four state links + notify disclosure. |
| Uncovered ZIP (other 46 states + DC) | `200` `/state?zip=44101` | "We couldn't place ZIP 44101 in California, Florida, New York or Texas — the four states ClearVoting covers today." + state links + notify (state pre-selected when the ZIP's state is known — it is not known from this file, so no pre-selection) + house.gov link. |
| Malformed input | `200` `/state?zip=abc` | "A ZIP code is five digits." with the form. |
| Empty submit | HTML `required` blocks it; server renders the finder page. |
| JS off | Identical — the form is a plain GET. |

### 5.4 Remembered selection

- **Key:** `localStorage['cv-home']` = `{"state":"NY","district":4,"savedAt":"2026-09-18"}`. Written by `site.js` on any `/state` page whose URL carries a valid `district` (the 302 target and the split-ZIP pick both land there; Share never emits `district`, so shared links do not overwrite a recipient's home). Read by: the masthead "My representatives" link, the home "Remembered / Your representatives" blocks, the Latest Vote per-state line, the member breadcrumb, the bill "How did your representatives vote?" slot.
- **Visible and revocable:** wherever it is used, the line "Remembered: New York, District 4 · Change · Forget" appears; **Forget** removes the key and re-renders the slot (ZIP form). **Change** goes to `/#find`.
- **Principle (C-13):** remember where you live, never how you look. Written on `/privacy`.
- **Party:** `sessionStorage['cv-show-party'] = "1"` while revealed; read by every page's toggle so the reveal carries across pages within a visit and resets when the tab closes.

### 5.5 Manual paths and the house.gov fallback

- **State + district by hand:** `/state?code=NY` shows the whole roster in district order, so a reader who knows their district scrolls to it; the URL `/state?code=NY&district=4` is typeable and linkable. No separate district `<select>` is added (the roster is the picker).
- **Street-address fallback:** in the unknown-ZIP state only, the link "Look up your district by street address on house.gov →" (`https://www.house.gov/representatives/find-your-representative`, `rel=noopener`, opens in the same tab). The keyless Census geocoder is deferred (§12).

---

## 6. Visual system

### 6.1 Tokens (one `:root` in `static/css/site.css`; `styles.css` and `broadsheet.css` are deleted)

| Token | Value | Contrast on paper #F5F6FA | on white #FFF | Use |
|---|---|---|---|---|
| `--paper` | #F5F6FA | — | — | page ground everywhere |
| `--card` | #FFFFFF | — | — | inputs, dialog, the two interactive cards (state chip, Latest Vote card), note blocks; never a content container |
| `--ink` | #1B1B1B | 15.95 | 17.22 | body, headings |
| `--ink-soft` | #5B616B | 5.78 | 6.24 | decks, secondary prose |
| `--ink-meta` | #5F656D | 5.45 | 5.88 | kickers, datelines, meta, captions (replaces `--text-dim` and the old `--ink-meta`) |
| `--navy` | #112E51 | 12.68 | 13.69 | display type, rules, seals, primary buttons; white on navy 13.69 |
| `--blue` | #0071BC | 4.76 | 5.14 | links, focus ring, kickers in links |
| `--blue-dim` | #205493 | 7.07 | 7.63 | link hover, kicker text |
| `--yes` | #2E7D3A | 4.73 | 5.11 | tally bar "yes" segment and its number only |
| `--yes-text` | #1F5E2D | 7.21 | 7.79 | "Voted yes" chip text (6.16 on its tint) |
| `--yes-tint` | #DDE7E3 | — | — | "Voted yes" chip fill (12 % of `--yes` over paper) |
| `--no` | #B3261E | 6.05 | 6.54 | tally bar "no" segment and its number only |
| `--no-text` | #8E1B21 | 8.35 | 9.02 | "Voted no" chip text (6.88 on its tint) |
| `--no-tint` | #EDDDE0 | — | — | "Voted no" chip fill |
| `--error` | #8A1C1C | 8.59 | 9.28 | form error text only (distinct from `--no`) |
| `--rule` | #D6D7D9 | decorative | decorative | 1px hairlines, photo frame |
| `--rule-soft` | #E8E8E8 | decorative | decorative | tally track, initials block background |
| `--tap` | 44px | | | minimum interactive height and width |
| `--radius-chip` / `--radius-ctl` | 4px / 8px | | | the only radii |

Deleted: `--accent-red`, `--vote-nay`, `--vote-yea`, `--text-dim`, `--bg-*`, `--text-*` aliases, the hardcoded hover reds, every literal colour in JS (`vote.js VOTE_COLORS`). JS applies classes; it never sets a colour.

### 6.2 Type scale (8 steps, the only allowed `font-size` values) and roles

| Name | Size | Family/weight | Role |
|---|---|---|---|
| `--t-kicker` | 0.75rem (12px floor; 13px on ≤560 via 0.8125rem) | Inter 700, uppercase, 0.14em tracking | kickers, seals, chip text, nav, masthead tagline |
| `--t-meta` | 0.8rem (12.8px) | Inter 400 | datelines, meta lines, captions, edition line |
| `--t-ui` | 0.875rem | Inter 500/600 | controls, labels, signal lines, footer links |
| `--t-body` | 1rem | Lora 400 | body, provisions, official summary |
| `--t-lede` | 1.125rem | Lora 400 | outcome sentence, deck |
| `--t-h3` | 1.35rem | Playfair 700 | row headlines (1.15rem in rows), section subheads |
| `--t-h2` | clamp(1.45rem, 3vw, 2rem) | Playfair 700 | section heads |
| `--t-display` | clamp(2rem, 5vw, 3.2rem) | Playfair 700 | page H1s |

Rule for official text: an official title standing in for a one-liner is set in **Lora 500** at 1.05rem, clamped to two lines (`-webkit-line-clamp: 2`), so the face itself says "this is the official text, not our translation". Inputs, selects and textareas are 16px (no iOS zoom). Fonts self-hosted (§9.6): Playfair Display 700, 800, 600 italic; Lora 400, 400 italic, 500; Inter 400, 600, 700.

### 6.3 Spacing, rules, breakpoints, masthead

- **Spacing:** 4px scale only — `--s1` 0.25rem, `--s2` 0.5, `--s3` 0.75, `--s4` 1, `--s6` 1.5, `--s8` 2, `--s10` 2.5, `--s12` 3, `--s16` 4. Section rhythm identical on every page: 3px double rule, 2.5rem, kicker, 0.5rem, heading, 1.5rem, content. Rows: 1rem vertical padding, 1px hairline between.
- **Rules, not cards:** no `box-shadow` anywhere except the two interactive cards (state chip, Latest Vote card: `0 1px 2px rgba(17,46,81,.08)`); no nested white containers; note blocks (split-ZIP, coverage, empty-summary) are a 3px left navy rule on white.
- **Breakpoints:** exactly two, **560** and **880**, declared once at the end of `site.css` (mobile-first; every override after its base rule) and mirrored in JS via `matchMedia('(min-width: 880px)')`. Tablet 560–879 uses the single-column layouts with 1.5rem gutters; ≥880 gets two-column layouts and the desktop fact strip. Gutters: 16px under 560, 24px to 880, auto-centred `max-width: 1100px` above.
- **Masthead (compact):** logo `clamp(1.6rem, 4.5vw, 2.4rem)`; tagline at `--t-kicker`; nav as one 44px row under the double rule with items **Home · My representatives · About** (≤880) and **Home · My representatives · The Record · About** (≥880, "The Record" → `/#record`). No hamburger (the `.hamburger` code path in `feedback.js` stays inert). Edition line (§7.4) directly under the nav at `--t-meta`, centred, one line (its middle segment hidden under 560).
- **Photos:** `<span class="photo" data-initials="CS"><img src="{depiction.imageUrl}" alt="" loading="lazy" width="56" height="56"></span>`; the span's `::before` prints the initials in Playfair on `--rule-soft` under the image; `site.js` listens for `error` events in the capture phase and removes the failed `<img>`, leaving the initials block. Header photos are not lazy. `alt=""` because the name is adjacent text.

### 6.4 Component inventory

| Component | Spec |
|---|---|
| **Masthead / footer** | As today's markup, compacted (§6.3); footer links About · Methodology & Corrections · Privacy · Report an error on this page (`<button id="feedback-open">`, 44px, text); data line "Data from Congress.gov and Senate.gov · <span id="data-freshness">Synced September 5, 2026</span>" (span server-filled; the " · " is inside the span so nothing dangles); credo. |
| **Kicker / deck** | `.kicker` (`--t-kicker`, `--ink-meta` or `--blue-dim` when linked); `.deck` (`--t-lede`, `--ink-soft`). |
| **Edition line** | `<p class="edition">` with three `<span>`s (§7.4). |
| **Status seal** | `.seal` — Inter 700 uppercase `--t-kicker`, 4px radius, 0.2rem 0.5rem padding. Variants: `.seal--final` filled navy, white text ("Passed the House 237–169", "Became law"); `.seal--moving` outlined 1px navy ("Still in Congress", "Blocked in the Senate 52–46", "No floor vote yet"); `.seal--pending` dashed 1px `--ink-meta`, `--ink-meta` text ("No plain-English summary yet"); `.seal--ballot` outlined 1px `--ink-meta` ("On the ballot Nov 3, 2026", "Not on the ballot Nov 3, 2026") so a fallback or ballot mark can never be mistaken for content. |
| **Vote chip** | `.chip` — Inter 700 `--t-kicker`, 4px radius, 1px border in the text colour, tint fill: `.chip--yes` ("Voted yes"), `.chip--no` ("Voted no"), `.chip--nv` ("Didn't vote", `--ink-meta` on paper, dashed border), `.chip--present` ("Present"), `.chip--other` (the raw value: "Guilty", "Not guilty", "Voted for Jeffries"; ink on paper). Short form `data-short` prints "Yes / No / Didn't vote / Present" inside roll-call lists whose caption says "Vote". Border + text + fill mean it survives greyscale and forced colours. |
| **Tally bar** | `.tally` — a `role="img"` with `aria-label="Passed the House: 237 voted yes, 169 voted no, 27 did not vote"`, a 10px track (`--rule-soft`) with `--yes` and `--no` segments separated by a 2px paper gap (widths set by `site.js`/server `style` on the segment — allowed: `style-src` keeps `'unsafe-inline'`; segments also carry `data-yes`/`data-no` so tests can read them), followed by the text "237 yes · 169 no" (numbers in `--yes`/`--no`, words in ink) and "· 27 didn't vote" in meta when non-zero. The only place green appears. |
| **Vote row** | `.vote-row` — `<a href="/bill?…">` covering the row: chip (top-left on mobile above the headline, left column ≥560 at 6.5rem), headline (Playfair 1.15rem or Lora 500 fallback), meta line (bill code · seal text · date · topic). Used for key votes, record bill groups, roster signal lines (without the link when nested). |
| **Person row** | `.person` — `<a href="/member?id=…">` covering the row (except split-ZIP rows, a `<div>` with two sibling links): photo 56px, name (Playfair 1.15rem), seat line + seal, signal line with chip, empty `<span class="party">`. Minimum height 64px; whole row is the tap target. |
| **Roll-call row** | `.rc-row` — two lines on all viewports: name (link for covered members; "Rep." / "Sen." prefix omitted — the caption says the chamber) + "District 4" or "NY", chip (short) right-aligned, empty party span. In a `<table>` at ≥880 with `<th scope="col">` and the name cell as `<th scope="row">`. |
| **Bill row** | `.bill-row` — kicker code, seal, date, headline (Playfair one-liner or Lora 500 fallback + pending seal). Used by the Record list and Sponsored bills. |
| **Button, primary** | `.btn` — navy fill, white text, Inter 700 `--t-ui`, 48px height, 8px radius. Only for form submits: Find my representatives, Notify me, Send (feedback), Filter. |
| **Button, secondary** | `.btn--secondary` — transparent, 1px navy border, navy text, 44px. Share, "This is my district →" (as a link styled as a button), Forget. |
| **Party toggle** | `<button class="party-toggle" type="button" aria-pressed="false">Show party labels</button>`, 44px text control in the action row; pressed → "Hide party labels"; a `role=status` sibling announces "Party labels shown / hidden". No `aria-label` override. |
| **Form field** | `<label>` visible above (`--t-ui` 600 navy), input 16px, 48px, 1px `--ink-meta` border, 8px radius, white; focus = the global ring plus a navy border; error text in `--error` under the field with `aria-describedby`. |
| **Disclosure** | native `<details><summary>` with a 44px summary line, a "+/–" text glyph, and `--t-ui`. |
| **Feedback control** | Footer button "Report an error on this page" on every viewport; on ≥880 an additional fixed 44×44px icon+label button bottom-right with `bottom: calc(1rem + env(safe-area-inset-bottom))`, and `main { padding-bottom: 72px }` at ≥880 so it never covers a CTA. Under 880 no floating element exists. |
| **Dialog** | `<dialog id="feedback-modal" aria-labelledby="feedback-title">` containing the existing `#feedback-form`, `<h2 id="feedback-title">Send feedback</h2>`, `<p id="feedback-context">`, `<label for="feedback-message">What did you see?</label>`, the textarea (16px), `#feedback-cancel`, `#feedback-submit` (primary), `<p id="feedback-status" role="status">`. `#feedback-overlay` is kept as an empty element for the hook. `showModal()` / `close()`, focus returned to the opener. |
| **Sticky strip** | `.strip` — 44px, paper background, hairline bottom, name/outcome text at `--t-ui` + in-page links or Share; `position: sticky; top: 0`; hidden until the header leaves the viewport. One per page, member and bill only. |
| **Note block** | `.note` — white, 3px left navy rule, body text; used for split-ZIP, coverage, empty-summary notes. |

### 6.5 Colour semantics

Navy says "this is the record"; blue says "this is a link or where your focus is"; red says "voted No" and nothing else; green appears only inside the tally bar next to a number. Errors are `--error` text on paper, never red fills. Primary action colour is navy. Nothing else on the site is coloured.

### 6.6 Motion and sticky

No entrance animation anywhere; nothing defaults to `opacity:0`; the `.animate-*` classes and the observer in `feedback.js` are deleted. Allowed motion: the dialog's native open, `<details>` open, the "Link copied" status appearing. `@media (prefers-reduced-motion: reduce)` zeroes transitions; `site.js` reads `matchMedia('(prefers-reduced-motion: reduce)')` once and uses `behavior: 'auto'` for any programmatic scroll. At most one sticky element per page (§2.3 C-5); focused elements carry `scroll-margin-top: 56px` so the strip never covers focus (WCAG 2.4.11).

### 6.7 The fate of the stylesheets

`static/css/site.css` (**new**, target ≤ 30 KB) is written from the components actually rendered by the seven templates and the JS files, mobile-first, tokens in one `:root`, responsive blocks at the end. `styles.css` (3,848 lines) and `broadsheet.css` (455 lines) are **deleted** in the last commit of the PR, gated by §6.9. Every `outline: none`, low-alpha focus shadow, `.category-tag`, `.hero-*`, `.stagger-children`, dashboard and viz rule dies with them. `@font-face` for the nine self-hosted faces lives at the top of `site.css`.

### 6.8 Print

`@media print { .masthead-nav, .edition, .actions, .strip, dialog, .feedback-btn, .site-footer nav { display: none } body { background: #fff } a::after { content: none } }` plus `<details>` opened for printing via `site.js` on `beforeprint`. Dark mode and forced-colours: `color-scheme: light` declared; meaning is carried by text and borders (chip borders, seal outlines) so forced-colours mode keeps it; a full dark theme is deferred.

### 6.9 Definition-of-done checks (run before the stylesheet-retirement commit and at PR)

1. `document.documentElement.scrollWidth <= window.innerWidth` on every template at 320 and 375 (and 768, 1280).
2. No rendered text computes to under 12px; no `font-size` literal outside the eight tokens (grep).
3. Every text token ≥ 4.5:1 on both `--paper` and `--card` (the table in §6.1; a script recomputes it).
4. No interactive element under 44×44 CSS px (script over `a, button, input, select, summary, [tabindex]`).
5. No `box-shadow` outside `.state-link` and `.vote-card`; no `border-radius` outside 4px/8px.
6. On `/member` at 375×812 the first `.vote-row` top is < 812px; on `/bill` the "How did your representatives vote?" heading top is < 812px; on `/` the Find button bottom is < 600px.
7. No inline `<script>`/handlers; no `innerHTML` in the diff; every shell has literal `<title>` and `</head>`.
8. Lighthouse/axe: zero contrast, name/role, heading-order or landmark errors on the seven templates.

---

## 7. Copy and vocabulary

### 7.1 Glossary (plain word ← official term; the official term survives only in the roll-call caption and source link)

| Plain | Replaces |
|---|---|
| Voted yes | Yea, Aye |
| Voted no | Nay, No |
| Didn't vote | Not Voting, absent |
| Present | Present, Present, Giving Live Pair |
| Guilty / Not guilty | (impeachment trial values, verbatim) |
| Voted for {Name} | Speaker-election values (a surname in the `vote` field) |
| Final vote to pass | On Passage; On Passage of the Bill |
| Vote to pass (fast-track, needed two-thirds) | On Motion to Suspend the Rules and Pass[, as Amended] |
| Vote to adopt | On Agreeing to the Resolution[, as Amended]; On the Resolution; On the Joint Resolution; On the Concurrent Resolution |
| Vote to adopt (fast-track, needed two-thirds) | On Motion to Suspend the Rules and Agree[, as Amended] |
| Vote on an amendment | On Agreeing to the Amendment; On the Amendment |
| Vote to end debate (needed 60) | On Cloture on the Motion to Proceed; On the Cloture Motion |
| Vote to take it up | On the Motion to Proceed; Motion to Proceed |
| Vote to send it back to committee | On Motion to Recommit; On the Motion to Recommit; On Motion to Commit |
| Vote to set it aside | On Motion to Table; On the Motion to Table; Table Motion to Reconsider |
| Vote to end debate on the rule | On Ordering the Previous Question |
| Vote to accept the Senate's changes / the House's changes | On Motion to Concur in the Senate Amendment[…]; On the Motion (Motion to Concur in the House Amendment…) |
| Vote to bring it to the floor | On Motion to Discharge; On the Motion to Discharge |
| Vote to waive a budget rule (needed 60) | On the Motion (Motion to Waive …) |
| Vote to confirm | On the Nomination |
| Vote to ratify a treaty (needed two-thirds) | On the Resolution of Ratification |
| Vote to override the veto (needed two-thirds) | Passage, Objections of the President To The Contrary Notwithstanding; On the Veto |
| Election of the Speaker | Election of the Speaker |
| Vote to adjourn | On Motion to Adjourn |
| Attendance call | Call of the House; Motion for Attendance |
| Procedural vote | any other question string (the official string stays in the caption) |

### 7.2 Result → seal text and outcome verb (one formatter, Python and JS twins)

House `result`: "Passed" → seal "Passed the House 237–169", verb "passed it"; "Failed" → "Rejected by the House 189–235", "rejected it"; "Agreed to" → "Adopted by the House 220–210", "adopted it"; a surname (Speaker election) → "Speaker elected", "elected {Name} Speaker". Senate `result` prefix (tally taken from `counts`): "Bill Passed" / "Joint Resolution Passed" → "Passed the Senate 90–6", "passed it"; "Bill Defeated" / "Joint Resolution Defeated" → "Rejected by the Senate", "rejected it"; "Cloture … Agreed to" → "Debate ended 89–4", "voted to end debate"; "Cloture … Rejected" → "Blocked in the Senate 52–46", "blocked it — 60 votes were needed"; "Motion to Proceed Agreed to" → "Taken up", "agreed to take it up"; "Amendment Agreed to / Rejected" → "Amendment adopted / rejected", …; "Motion to Table Agreed to" → "Set aside (tabled) 61–32", "set it aside"; "Nomination Confirmed" → "Confirmed 52–46", "confirmed the nomination"; "Resolution Agreed to" / "Concurrent Resolution Agreed to" → "Adopted"; "Veto Sustained" → "Veto stood", "let the veto stand"; anything else → seal = the result string before the parenthesis, verb "voted {yeas} to {nays}: {result}". Bill status seal (bill pages, Record rows, sponsored rows) derives from `laws` first ("Became law"), then the most recent decisive roll call per chamber ("Passed both chambers", "Passed the House 237–169", "Rejected by the House", "Blocked in the Senate 52–46"), else "No floor vote yet" (bills) / "In committee — no floor vote yet" (sponsored). Tally format everywhere: "237 yes · 169 no" in prose blocks, "237–169" inside seals.

### 7.3 Outcome sentence

"The {House|Senate} {verb}, {yeas} to {nays}, on {Month D, YYYY}." — e.g. "The House passed it, 237 to 169, on September 3, 2026." Ties: "The Senate tied, 50 to 50, on {date}; the motion {failed|passed on the Vice President's vote}" from the result string. Cloture: "The Senate blocked it, 52 to 46, on August 8, 2026 — 60 votes were needed." Nominations: "The Senate confirmed the nomination, 52 to 46, on {date}." Dates through one helper: long form "September 3, 2026" in sentences; short "Sep 3, 2026" in meta rows; Senate `vote_date` display strings are parsed by the existing `_parse_vote_date` formats and never printed raw (no timestamps, no double spaces).

### 7.4 Freshness and the edition line

`<p class="edition"><span>Data synced September 5, 2026</span><span class="edition-mid"> · Latest roll call September 3</span><span> · Election Day is Tuesday, November 3 — 46 days away</span></p>` — sources `sync_metadata.last_sync`, the newest `vote_date` across roll calls (from the latest-vote index), a server-computed day count. Under 560 the middle span is hidden. On Election Day the third span reads "Election Day is today"; from November 4 it is omitted; nothing else on the site mentions the election except the ballot seals. Per-module stamps: Record "As of {last_sync} · Plain-English summaries are written through {summaries_through}"; AI narrative "Written by AI on {generated_at}"; AI provisions "Summarized by AI from the official text"; roster "roster as of {roster_as_of}"; money "retrieved {last_updated}". Footer: "Synced {last_sync}" only. "Updated weekly" is gone.

### 7.5 Bill codes, names, tenure

`formatBillCode(type, number)` → "H.R. 4795", "S. 5271", "H.J.Res. 20", "S.J.Res. 11", "H.Con.Res. 108", "S.Con.Res. 5", "H.Res. 1398", "S.Res. 417" (the server's `_BILL_TYPE_LABELS` map, exported to `site.js`); `ordinal(119)` → "119th" (11–13 → "th"). `displayName("Schumer, Charles E.")` → "Charles E. Schumer". Tenure from `terms.item`: one chamber → "In Congress since 2025"; two → "In Congress since 1981 — House 1981–1999, Senate since 1999". Vote chips never carry a year; the seat line does.

### 7.6 AI attribution, arguments, errors, party control

- Attribution wording (one per module, at the foot, with the date): "Written by AI on {date} from the official record" (narratives); "Summarized by AI from the official text" (provisions). No AI line appears where no AI text rendered. Never "Generating…"; always "Loading summary…".
- Arguments: the module is cut (C-2). `/methodology#ai` says: "We do not publish arguments for or against a bill. An earlier version showed AI-drafted 'supporters say / critics say' bullets; they were unattributed and have been removed until they can be sourced."
- Errors own the failure: "We couldn't load this page right now. Try again in a moment, or use *Report an error* below to tell us." · notify/feedback: "We couldn't save that. Try again, or email {contact}." · invalid email: "That doesn't look like an email address." All in `role=status`/`aria-describedby` lines, `--error` text.
- Party control: exactly one label pair everywhere — **"Show party labels"** / **"Hide party labels"** — with the sentence "Party labels are hidden so the record speaks first." shown once per page in the action row's tooltip-free meta line on the delegation page only. Revealed values are full names: "Democratic", "Republican", "Independent".
- Election context line: factual, non-partisan (§7.4). Ballot seals only state a fact from the sanctioned file. No "vote for/against", no "before you vote" imperatives.

### 7.7 Copy checklist (outcome 3)

Every AI block has a date · every freshness stamp names only what it sits beside · no "procedural" apology exists · no un-summarized bill is hidden from a newest-first list · no percentage on a list row · no "leans"/"fights for" · no grey text below `--ink-meta` · no red outside the vote component · "Yea/Nay" appears only in captions/source links · every count comes from `stats` verbatim · no page blames Congress.gov for a ClearVoting failure.

---

## 8. Accessibility (WCAG 2.2 AA items that apply)

1. **1.1.1** Photos `alt=""` with adjacent names; the header photo likewise; tally bars `role="img"` + `aria-label`; no other images.
2. **1.3.1** One `<h1>` per page (member name, bill headline, "New York's representatives", About/Methodology/Privacy titles); h2 sections, h3 rows; landmarks `header/nav/main/footer`; roll-call tables (≥880) with `<caption>`, `<th scope="col">`, name cells `<th scope="row">`; lists are `<ul>/<ol>`.
3. **1.3.5** `autocomplete="postal-code"` on ZIP, `autocomplete="email"` on email.
4. **1.4.3 / 1.4.11** Text ≥ 4.5:1 (§6.1); focus ring 2px `--blue` (4.76:1 on paper) with 3px offset; chip borders in the text colour ≥ 4.5:1; tally segments carry numbers so segment-to-segment contrast is not the sole cue.
5. **1.4.4 / 1.4.10 / 1.4.12** rem-based type, reflow at 320 with no horizontal scroll (§6.9), no fixed heights on text containers.
6. **2.1.1 / 2.1.2** Everything reachable by keyboard; the dialog traps focus natively and Esc closes it.
7. **2.4.1** Skip link retained; **2.4.2** unique server titles; **2.4.3** DOM order = visual order (no CSS reordering of the fold); **2.4.4** row links have full accessible names ("Laura Gillen, District 4, latest vote: … voted yes" via the row's text; no "read more"); **2.4.6** headings and labels describe content; **2.4.7** one global `:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible { outline: 2px solid var(--blue); outline-offset: 3px }` and no `outline: none` anywhere; **2.4.11** `scroll-margin-top` so the sticky strip never obscures focus.
8. **2.5.3** Visible text = accessible name on every control (no `aria-label` overriding visible text); **2.5.8** targets ≥ 44px (exceeds the 24px minimum).
9. **3.1.1** `lang="en"`; **3.2.3** the same nav on every page; **3.3.1 / 3.3.3** errors identified in text next to the field with `aria-describedby`; **3.3.2** visible labels; **3.3.7** the remembered district avoids redundant entry.
10. **4.1.2** `aria-pressed` on the party toggle, `aria-expanded` from native `<details>`, `<dialog>` semantics; **4.1.3** status messages: one `role="status"` element per section ("New York delegation loaded, 28 members" is not needed — rosters are server-rendered; "Party labels shown", "Link copied", "Thanks — we'll email you…", "Filter applied: 12 bills on Health") and **no `aria-live` on content containers** (F43).
11. **Focus management:** pagination lands on the record heading (`tabindex="-1"`, fragment or JS); notify success moves focus to the status line; dialog close returns focus to `#feedback-open`; "Forget" keeps focus on the re-rendered slot's first control.
12. **Headings/tables** as above; **reduced motion** (§6.6); **no link-inside-link** (rows are `<a>`; source links are siblings); **no `role=link` on divs**.
13. **Scripted QA walkthrough** (definition of done): keyboard-only and VoiceOver/NVDA pass over `/` → ZIP → `/state` → member → key vote → bill → roll call → Share → party toggle → feedback dialog, at 375 and 1280.

---

## 9. Reach

### 9.1 Server-rendered content

`_serve_html(filename, meta, content_html)` replaces a literal `<!--content-->` inside `<main>` with escaped HTML built by `app/render.py` (f-strings + `html.escape`, no template engine, no new dependency) from the same functions the API uses (`get_member_page`, `get_bill_page`, `get_state_overview`, `get_latest_vote`, `get_bills`). Rendered blocks: **home** — edition line, hero card, Record lead + six rows, state counts; **state** — header + whole roster (28–54 rows); **member** — header, key votes, summary, the requested record page, sponsored, money; **bill** — story head, ZIP-form slot, by-state groups and the first two roll-call lists, provisions or empty state, fact box; **methodology** — the coverage paragraph. `<title>`/`</head>` handling in `_inject_meta` is unchanged. `site.js` detects rendered blocks (`data-ssr="1"`) and never re-fetches what is on the page.

### 9.2 Titles and canonical (server only; no client writes)

- Home: unchanged. Member: "Charles E. Schumer (NY) — Voting Record | ClearVoting". Bill: "H.R. 4795 — {one-liner} | ClearVoting" or "H.R. 4795 — {official title truncated at 70 characters on a word boundary}… | ClearVoting"; description = the official title (or the one-liner when the title is the headline); `og:title` = the title without " | ClearVoting", capped at 90 characters. State: "New York's Representatives — Voting Records | ClearVoting" (same with `district`/`zip`; canonical strips them). About/Methodology/Privacy/404: static.
- Canonical rules in §3.3; params normalized before lookup and before the canonical string; the 404 page carries no canonical.
- Sitemap: adds `/methodology`, `/privacy`; per-URL `lastmod` = bill `latestAction.actionDate`, member last vote `date`, state `roster_as_of`, home/about `last_sync`. `/static/*.html` are served with `X-Robots-Tag: noindex` via the static mount's response headers (a tiny middleware on `/static/*.html`).

### 9.3 og:image

- **Phase A (in the PR):** four static 1200×630 PNGs in `static/og/` — `default.png` (home/about/trust), `member.png`, `bill.png`, `state.png` — broadsheet cards (paper ground, masthead wordmark, a one-line descriptor "Voting record", "How Congress voted", "Your representatives"), made once by `scripts/build_og_cards.py` run locally with Pillow (a dev-time script; Pillow is **not** added to runtime `requirements.txt` in this phase) and committed. `_inject_meta` emits `og:image` (absolute URL), `og:image:width`/`height`, `og:image:alt`, and `twitter:card=summary_large_image`.
- **Phase B (last, cuttable):** `scripts/build_og_cards.py` gains member and state variants (name/state + "Voting record") pre-rendered at sync into `static/og/member/{id}.png` and `static/og/state/{code}.png` (154 files) with a `weekly-sync.yml` step; `_inject_meta` prefers the per-entity file when it exists. Bill cards stay static (the one-liner is already in `og:title`/description). No request-path rendering in either phase (C-9).

### 9.4 404s and index hygiene

Unknown member id, bill key or state code → `HTTPException(404)` → the 404 shell with status 404. `/favicon.ico` route (`Cache-Control: public, max-age=31536000`). Case-normalized canonicals. Soft-404 junk pages disappear.

### 9.5 Cache-Control (reconciled with per-visitor content and freshness, C-8)

| Response | Header |
|---|---|
| `/static/*` (CSS, JS, fonts, og) | `public, max-age=31536000, immutable` (the `?v=` bust already exists; fonts and og files are content-named or versioned) |
| HTML shells (`/`, `/state`, `/member`, `/bill`, trust pages) | `public, max-age=0, s-maxage=600, stale-while-revalidate=3600` — browsers revalidate; Cloudflare serves for 10 minutes and refreshes in the background. Nothing per-visitor is in the HTML. |
| `GET /api/*` (data) | `public, max-age=300, s-maxage=3600, stale-while-revalidate=86400` — data changes only on deploy. `?show_party=true` variants are distinct URLs. |
| `/api/health` | `no-store` (it is the freshness probe). |
| `POST /api/notify`, `/api/feedback` | `no-store`. |
| 404 pages | `public, max-age=60`. |

Freshness: the weekly sync commits and redeploys; the longest a stale shell can live at the edge is 10 minutes after the deploy, against a 7-day cadence (0.1 %). The "as of" stamps are rendered from the same data as the content, so a cached page never claims a freshness it does not have. A cold Render origin still lets Cloudflare serve cached shells and JSON (`stale-while-revalidate`), so a share-link spike does not show the host's splash to everyone (F63 mitigation; the plan/pinger decision is Joseph's, §12).

### 9.6 Performance

Self-hosted fonts (nine woff2 under `static/fonts/`, `font-display: swap`, `<link rel="preload" as="font">` for Playfair 700, Lora 400, Inter 400; `size-adjust`/`ascent-override` fallbacks on Georgia/Arial); the googleapis/gstatic preconnects and CSP allowances are removed. Member pages never download the full vote file (server pagination, 15 groups). Bill pages load in one request for up to two roll calls. Reserved space: none needed (server-rendered first paint); the optional "Your representatives" block on home is inserted below the finder and therefore never shifts the fold. State overview is a one-file read (§10 #5) and CDN-cached.

---

## 10. Backend touches (every server-side change, with its file and why it is small)

| # | Change | File(s) | Why small |
|---|---|---|---|
| 1 | Crosswalk data file + build script; `data/SOURCES.md` with URL, licence, retrieval date, build command | `data/zip_districts.json` (new), `scripts/build_zip_crosswalk.py` (moved from `tools/data/`), `data/SOURCES.md` (new) | Script already exists and is verified; file is ≈413 KB, loaded once. |
| 2 | Senate seats up in 2026 | `data/senate_2026.json` (new): `{"_source": {"name": "U.S. Senate — Class II senators and 2026 special elections", "url": "https://www.senate.gov/…", "retrieved": "…"}, "seats": [{"state": "TX", "bioguideId": "…", "kind": "regular|special"}, …]}`; consumed by `data_service.on_ballot_2026(member)` (House → true; Senate → id in list) | ≈35 rows nationwide; only the eight covered senators matter (expected: the Texas Class II seat and the Florida seat filled by appointment in 2025 — verify against senate.gov when building). |
| 3 | ZIP lookup | `app/routers/districts.py` (new, ≈40 lines): `GET /api/districts/{zip}`; `data_service.lookup_zip(zip) -> list[dict]` (loads the file at startup, applies the ≥5 % rule, attaches `member_ids`); router included in `main.py` | Dict lookup, no I/O per request. |
| 4 | `/state` with `zip`/`district` | `app/main.py serve_state`: `zip` → single match 302 / split render / unknown render; invalid `code` → 404; `district` passed to the renderer | Branching in one route handler. |
| 5 | Precomputed delegation | `sync.py build_state_overview()` (new step `--step state-overview` run after `member-votes` in `.github/workflows/weekly-sync.yml`) writes `data/synced/state_overview/{CA,FL,NY,TX}.json` (schema: `state`, `state_name`, `roster_as_of`, `generated_at`, `senators[]`, `house[]`, `vacant_districts[]`; each member: `bioguideId`, `name`, `display_name`, `district`, `chamber`, `photo`, `since`, `tenure_line`, `on_ballot_2026`, `partyName`, `latest_vote {bill_id, bill_code, one_liner, date, chamber, position, seal}`); `data_service.get_state_overview(code)` = one file read with an in-memory cache; `members.py` `/{state}/overview` returns it (party stripped unless `show_party=true`); the per-request 28-file scan and `include_stats` branches are deleted | Reuses the existing member_votes files at sync time; the runtime path becomes a file read. First deploy runs the step once by hand. |
| 6 | Member page payload and grouped record | `data_service.get_member_page(id, page, topic, plain)` (header facts from `members.json` + `stats`; key votes 4+4 by the ported picker; narrative + `generated_at`; grouped record page; sponsored; donations `totals`); `members.py` `/votes` gains `group=bill`, `plain=1`, `policy_area=`, honours `limit/offset` (max 50 groups); new `GET /api/members/{id}/page?page=&topic=&plain=` | One function feeds both the shell and the API; grouping is a single pass over the already-loaded list. |
| 7 | Record freshness and honest lists | `data_service.get_bills()` default order = newest `latestAction.actionDate`, `one_liner` nullable, `derived_status` per bill from the votes index + `laws`; `/api/health` gains `summaries_through` and `latest_roll_call` | Sort key change plus two computed fields. |
| 8 | Bill page payload and AI-summary honesty | `data_service.get_bill_page()` (head, derived status, outcome sentences per roll call, `plain_question`, `state_tallies`, `covered` positions for the 150 members — House by `bioguide_id`, Senate by `last_name`+`state` as in `sync.py build_member_votes` — official-summary first paragraph); `bills.py` `/ai-summary` returns **404** `{"available": false}` when missing; `/votes` payload gains `outcome`, `plain_question`, `state_tallies`, `covered` per roll call | Additive fields; the fake apology string is deleted. |
| 9 | Latest vote payload | `_build_latest_vote` adds `one_liner`, `has_summary`, `plain_question`, `outcome`, `state_tallies`, `covered` | Same loop, more fields. |
| 10 | Formatters, Python side | `app/render.py` (new): `format_bill_code`, `ordinal`, `display_name`, `tenure_line`, `format_date`, `plain_question`, `result_phrase`, `outcome_sentence`, `bill_status`; a test asserts parity with `site.js` on a fixture list | Pure functions. |
| 11 | Server-rendered blocks | `app/render.py` block renderers; `main.py _serve_html` gains the `<!--content-->` replacement; routes for home, state, member, bill, methodology pass content | String building; `_inject_meta` untouched. |
| 12 | Titles, canonical, 404s, favicon, sitemap, trust routes | `main.py`: `_member_meta`/`_bill_meta`/`_state_meta` per §9.2; normalization; `HTTPException(404)` on empty lookups; `/favicon.ico`; `/methodology`, `/privacy`; sitemap entries + per-URL `lastmod`; `X-Robots-Tag` on `/static/*.html` | Edits inside existing helpers. |
| 13 | Caching + CSP | `main.py` middleware: Cache-Control per §9.5; CSP `style-src 'self' 'unsafe-inline'`, `font-src 'self'`, no googleapis/gstatic | Header strings. |
| 14 | og:image | `_inject_meta` emits the four tags; `scripts/build_og_cards.py` (new, dev-time; Phase B adds a sync step and Pillow to a `requirements-sync.txt` or the sync job's install line, never the web runtime) | Phase A is four committed PNGs. |
| 15 | Feedback hooks | `static/js/feedback.js`: `.member-header h1`, `.bill-header h1`; `showModal()`/`close()` with focus return; observer block and `.animate-*` handling deleted; `#feedback-open` is now the footer button (desktop also has the fixed one with the same handler via class) | The sanctioned change plus deletions. |
| 16 | Shells | `static/index.html`, `state.html`, `member.html`, `bill.html`, `about.html`, `404.html` rewritten on the new masthead/footer; `methodology.html`, `privacy.html` new; each keeps literal `<title>` and `</head>` and a `<!--content-->` marker | Templates. |
| 17 | Client | `static/js/site.js` (new, shared: formatters twin, chip/row builders via `el()`, share, party toggle, photo fallback, delegation memory, sticky strip, focus helpers); `app.js`, `state.js`, `member.js`, `bill.js`, `vote.js` rewritten as thin enhancers (`bill.js` keeps the `sanitizeHtml`/`SAFE_TAGS` block verbatim); `viz.js` deleted | Most rendering moved to the server. |
| 18 | Stylesheet | `static/css/site.css` new; `styles.css`, `broadsheet.css` deleted (last commit) | §6.7. |
| 19 | Tests | `tests/`: ZIP lookup (single/split/unknown/malformed), `/state?zip=` 302/200/404, member page grouping (S000148 fixture: 1,061 votes, 478 null `bill_id`), formatter parity, 404 statuses, cache headers, feedback selectors resolve, methodology rule list equals the prompt, fold checks via a headless run | Extends the existing pytest suite. |

### 10.1 Not touched

Google Sheets write paths (`notify.py`, `feedback.py`, `sheets.py`), `sanitizeHtml`, server-side party stripping, the sync's data-fetch steps, `render.yaml`, the AI writer jobs.

### 10.2 New dependencies

None at web runtime. Pillow only in the dev/sync context for og cards (Phase B).

### 10.3 Recommended commit order (path first; each boundary is a safe stopping point)

1. Data + endpoints: crosswalk, seats file, `/api/districts`, state overview precompute, `/ai-summary` honesty, bills order, health fields, formatters + tests.
2. `site.css` alongside the old files, `site.js`, compact masthead/footer/edition line on all shells, feedback dialog + h1 hooks.
3. Home + delegation (ZIP path end-to-end, server-rendered), 404 + trust pages.
4. Member page (server-rendered, grouped record).
5. Bill page (server-rendered, roll call by state).
6. Titles/canonical/404s/sitemap/caching/fonts/og Phase A.
7. Retire `styles.css`/`broadsheet.css` (gated by §6.9).
8. og Phase B (cut first if the schedule slips), then record in-place pagination enhancement.

---

## 11. Finding coverage

| Id | Sev | Resolved by | How |
|---|---|---|---|
| F01 | P0 | §4.1 m5, §7.4, §10 #7 | Record newest by action date regardless of summary; designed fallback row; section stamp + coverage note; per-row dates. |
| F02 | P0 | §4.1 m3, §4.4 m4, §10 #8 | Structured hero with conditional link text and pending seal; `/ai-summary` 404 `{available:false}`; real empty state, no bullet, no AI line; "Loading summary…". |
| F03 | P1 | §3.2, §5 | ZIP form first on every viewport; Census crosswalk; split/unknown states; two taps. |
| F04 | P1 | §3.1, §4.2, §5.4 | One canonical delegation page; state chips are links; homepage renderer retired; senators first, House by district; party toggle; `document.title` write deleted; district remembered. |
| F05 | P1 | §10 #5, §9.5 | Precomputed per-state file, one read, server-rendered, CDN-cached; the 28-file scan deleted. |
| F06 | P1 | §4.2, §2.3 C-1 | Stat boxes, bars, thresholds, metric sorts, Total Votes deleted; rows carry one dated vote; participation is a count on the member header only. |
| F07 | P1 | §4.3 | Header → key votes → summary → record; donut, attendance, tiles, topic bars, Service History, tabs cut; one sticky strip. |
| F08 | P1 | §4.3 m2, §2.3 C-10 | Key votes are linked rows with code, seal+tally, date; 4+4 with the rule printed; same row component everywhere; roster rows show one linked vote. |
| F09 | P1 | §4.3 m4 | Record grouped by bill; extra roll calls in `<details>`; amendments collapsed per day with honest wording; single headline slot; empty title div gone. |
| F10 | P1 | §4.4 m2–3 | Outcome band; "How did your representatives vote?" from storage; by-state groups with tallies; all-votes collapsed with search; covered names linked; two-line rows. |
| F11 | P1 | §7.1–7.3 | One plain question map, outcome sentence, vote chip, tally format across every page. |
| F12 | P1 | §4.4 m1, §9.2 | One-liner as H1 and title; official title as deck; 70-char word-boundary fallback; og:title cap. |
| F13 | P1 | §2.3 C-2, §7.6 | Module cut; methodology states why; vote colours never reused. |
| F14 | P1 | §6.3, §6.7, §6.9 | Fresh mobile-first stylesheet, overrides after base rules, `minmax(0,1fr)`, scroll-width gate at 320/375. |
| F15 | P1 | §4.2–4.4, §6.3, §6.7 | Every inner page on the rules/whitespace model; card container rules deleted with the old files; bill page as one article with a fact box. |
| F16 | P1 | §6.1 | `--ink-meta` #5F656D (5.45/5.88); `--text-dim` deleted; 12px floor; contrast gate on both grounds. |
| F17 | P1 | §4.1 m3 | Structured card; fallback title in Lora 500, clamped; never a sentence template. |
| F18 | P1 | §4.5–4.7, §9.6 | Three real pages; footer repointed; fonts self-hosted so the privacy claim is true. |
| F19 | P1 | §9.1 | First block (and more) server-rendered on home, state, member, bill; `<title>`/`</head>` kept. |
| F20 | P1 | §9.3, §9.2, §6.4 | og:image two-phase; server-only titles; one Share action with `navigator.share` + clipboard fallback on member, bill, state. |
| F21 | P2 | §4.1 fold, §6.3 | ZIP field by ≈560px on 375; "My representatives" nav item. |
| F22 | P2 | §4.5, §6.6, §10 #15 | No entrance animation; observer deleted; static trust pages. |
| F23 | P2 | §6.4 feedback | No floating element under 880; 44px desktop button with safe-area and reserved padding; footer opener everywhere. |
| F24 | P2 | §6.4 dialog | Native `<dialog>`, `aria-labelledby`, label, `role=status`, focus return; ids kept. |
| F25 | P2 | §6.4 party toggle, §7.6, §5.4 | One label pair, `aria-pressed`, no `aria-label` override, one page-level control on bills, full party names, session-scoped. |
| F26 | P2 | §4.3 m4 | Counts verbatim from `stats`; "other" bucket; no derived attendance figure. |
| F27 | P2 | §7.2, §4.3 m4 | Result vocabulary; no empty chips; explicit Amendment/Nomination/Speaker labels; resolutions link via the shared type map. |
| F28 | P2 | §2.4 declined graft, §4.3 removed | Module cut; topic `<select>` on the record instead. |
| F29 | P2 | §4.3 fold | Key votes above the summary on mobile; three-sentence clamp; body size. |
| F30 | P2 | §6.6, §6.4 form field | One sticky strip; native selects; 16px controls. |
| F31 | P2 | §7.5 | `formatBillCode` + `ordinal`, Python and JS twins. |
| F32 | P2 | §7.2, §4.4 m6 | Derived status seal and "Latest floor action"; one date helper; Senate dates parsed, never raw. |
| F33 | P2 | §4.4 m6 | Sponsor linked only when covered; plain text with state otherwise; cosponsor count. |
| F34 | P2 | §4.2 | ZIP finder on top; senators first; whole-row tap targets; text on every signal; no bars. |
| F35 | P2 | §6.1, §6.5 | Red only in the vote component; navy primaries; separate `--error`; `--accent-red`/`--vote-nay` deleted. |
| F36 | P2 | §4.3 m7, §4.2 | Finance bars and participation traffic-lights gone; tally bar has `role=img` + label and numbers. |
| F37 | P2 | §4.1 m5, §2.3 C-3 | Official titles off summarized rows; clamped Lora 500 fallback rows; 140-char cap on the lead. |
| F38 | P2 | §3.1 (deferred) | `/bills` and `?topic=` URLs deferred; offset bug fixed; `?q=` reflected. |
| F39 | P2 | §4.1 m2 | Required state select; navy button; privacy line; confirmation echoes the state. |
| F40 | P2 | §7.4 | Every AI block dated; edition line; footer separator inside the span; coverage note. |
| F41 | P2 | §7.4, §6.4 seal, §10 #2 | Edition line with the election date; ballot seals from the sanctioned list. |
| F42 | P2 | §4.1 m2, §5.3 | Coverage sentence at the point of choice; unknown-ZIP state explains coverage; bill pages let uncovered visitors find their row in "All votes". |
| F43 | P2 | §8 item 10 | No `aria-live` on containers; one `role=status` per section. |
| F44 | P2 | §8 item 11 | Focus to the record heading on paging; to the status on notify success; `<details>` gives `aria-expanded`; `autocomplete=email`. |
| F45 | P2 | §8 item 7 | One global `:focus-visible` rule; every `outline:none` deleted. |
| F46 | P2 | §2.2 #5, §4.3, §4.4 | `<h1>` on member, bill, about; the two `feedback.js` selectors updated in the same commit. |
| F47 | P2 | §6.1 `--tap`, §6.9 | 44px everywhere; no shrinking breakpoint. |
| F48 | P2 | §4.4 m3, §8 item 2 | `<caption>`, `scope`, row headers; no fake-sortable headers (the state table is gone). |
| F49 | P2 | §6.7 | Fresh `site.css`; old files deleted; long-lived cache on `/static`. |
| F50 | P2 | §6.1 | One token set; JS applies classes only. |
| F51 | P2 | §6.3 | Two breakpoints declared once; `matchMedia` mirrors them; no dead media blocks. |
| F52 | P2 | §9.2, §9.4 | Canonical normalization; real 404s; `/favicon.ico`; `noindex` on `/static/*.html`; per-URL `lastmod`. |
| F53 | P2 | §9.5 | Cache-Control on static, API, shells; reconciled with per-visitor content (C-8). |
| F54 | P2 | §10 #6, #8, §9.6 | Server pagination (15 groups); one page function; bill payload carries one-liner and vote summaries; no `limit=2000`. |
| F55 | P2 | §9.1, §9.6 | Server-rendered first paint; self-hosted woff2 with preload and metric fallbacks; no hidden-then-shown blocks. |
| F56 | P3 | §4.3 m5, m7 | Sponsored inline with the formatter and derived status; money as one dated sentence; hidden without data. |
| F57 | P3 | §6.2 | Eight-step scale; one family per role; 12px floor. |
| F58 | P3 | §6.4 | Two chips (seal, vote chip); two radii; one arrow glyph. |
| F59 | P3 | §6.3 | 4px spacing scale; one section rhythm. |
| F60 | P3 | §6.6, §8 item 12 | Reduced motion honoured in JS; rows are real `<a>`; tabs removed. |
| F61 | P3 | §7.6 | Error copy owns the failure. |
| F62 | P3 | §4.3 m3 | Narrative dated, clamped, subordinate to linked key votes; regeneration without "leans" deferred (§12). |
| F63 | P3 | §9.5, §12 | Edge caching keeps chrome up during a cold start; the plan/pinger decision is Joseph's (open question). |

---

## 12. Out of scope, deferred, and open questions

### 12.1 Deferred (explicit)

- `/bills` page with `?topic=`/`?q=` URLs and the topic pill (F38); search zero-results design beyond the existing panel's "No bills matched — try another word".
- Clean-path aliases (`/state/ny`) with 301s.
- Per-bill og:image cards; og Phase B if the schedule slips.
- Address-level lookup via the keyless Census geocoder (the house.gov link covers it).
- A sourced replacement for the arguments module (attributed statements, floor debate, CBO/GAO).
- Full dark mode; forced-colours audit beyond the border-carried meaning; a full print design beyond §6.8.
- Spanish-language layer: all UI strings live in one place (`site.js` string map; shell copy in the shells) and `lang` attributes are set, so an `es` variant is feasible; 46 days is not enough to translate 1,550 summaries honestly. `/about` states this plainly.
- Regenerating member narratives without "leans" and without the shared template opener (F62, generation-time).
- Weekly roster-diff step in the sync to catch resignations/special elections (members.json currency); until then the roster date is printed and "Wrong person? Report an error" is one tap away.
- Abuse protection beyond the existing `slowapi` limits on the two write endpoints; analytics for the two-click metric (server-log path counts only).
- Surfacing `audit_grades.json` / `needs_review` per bill (a grade is a score; only a count on `/methodology`).
- Render plan upgrade or an external pinger (ops).
- Cold-start measurement in September.
- Normalizing Senate `vote_date` strings in the 2,530 files at sync (the read-time helper covers it).

### 12.2 Appendix C gaps — covered or deferred

404 (covered §4.8); House-member pages (same template; district in the kicker; server pagination so the 840 KB file never ships; no-donation members omit the money sentence; Independents show "Independent" on reveal; short records show fewer key votes; vacancies render as "vacant in our data"); other states and bad `?code=` (same component for CA's 54; invalid/lowercase normalized or 404); bill data conditions (no roll call, many amendment roll calls, both chambers, no official summary, malformed URL — all in §4.4 states); no-JS (every page's first block and both forms work without JS; `<noscript>` names what needs it); tablet/320 (two breakpoints, gutters, gates); print (covered), dark/forced (partly deferred); search states (deferred with `/bills`); notify/feedback failures (covered §7.6; abuse protection deferred); broken photos (initials block); hero edge cases (§4.1 m3); keyboard/screen-reader walkthrough (§8 item 13); Back/forward (every state is a URL; no `pushState`); cold start (deferred to ops; edge cache mitigates); Spanish (deferred, stated); members.json currency (roster date shown; diff step deferred); instrumentation (server logs, stated on `/privacy`); `needs_review` flags (count only).

### 12.3 Open questions for Joseph (PM-level only; every technical call above is made)

1. **About page identity:** publish your name and which contact — the personal email, a dedicated address, or "use the feedback form" only? The trust pages and the error copy need one contact string.
2. **Ops spend before November:** pay for an always-on Render instance for the election window, or accept a free external 5-minute pinger against `/api/health`? Edge caching mitigates but does not remove the cold-start splash for the first uncached URL.
3. **Confirm two neutrality calls that change what the product says:** (a) the AI "supporters say / critics say" module is removed entirely rather than relabelled — reversible later with sourced content; (b) campaign money appears as one dated 2024-cycle sentence with an FEC link for the 80 members who have data (not hidden, not a headline number). Both are my recommendation; say so if you want either flipped.
