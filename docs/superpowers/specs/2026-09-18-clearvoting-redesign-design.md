# ClearVoting redesign — design spec (2026-09-18)

**Status:** revised after adversarial critique on 2026-09-22 (115 issues: 115 fixed, 0 rejected), then a completeness check the same day (10 small inline fixes: seal wording, signal-line label, count line, partial-ZIP count, Senate-file schema, bill-slot data source, `ai_summaries_updated` persistence, route order, additive-only commit 1, overview API fields); single source of truth for the implementation plan.
**Revision notes:** three critics (feasibility, user, trust) and a fourth cross-check raised 115 issues. None was rejected outright. Parts of nine were declined or superseded where two critics proposed different fixes for one problem; §2.5 lists each part and the reason. The revision also made three product calls (§2.5 A–C); Joseph confirmed all three, and the merge-by/cut-first trade, on 2026-09-22.
**Basis:** the "Spine" approach (judged winner, 135/150) with grafts from "Broadsheet", "Share" and "Evolve" where three judges recommended them and they strengthen the spine. Every graft decision is recorded in §2.4.
**Inputs:** `docs/reviews/2026-09-10-redesign-review.md` (F01–F63, Appendix C), `docs/reviews/2026-09-10-redesign-review-brief.md` (hard constraints, ZIP feasibility), `docs/001-prd-clearvote.md` (target user, success criteria), the four proposals under `~/.clearvote-worktrees/tools/design/`, and the code and data at `redesign/2026-09` (re-verified 2026-09-22 with `ls`/`grep`/`python`). Every field named below exists in `data/synced/` unless it is marked **new** (a file or field this PR writes) or **index** (a field of the new `data/synced/votes_index.json`, §10 #3). Note: `member_votes/{id}.json` rows carry only `bill_number, bill_id, one_liner, has_plain_summary, vote, date, result, policy_area, chamber, congress, session, vote_number` (plus `direction`, `cbo_deficit_impact`, which are never shown). There is no `question` and no tally, so the roll-call question, counts and decisive class always come from the index, joined on `(chamber, congress, session, vote_number)`.
**PM decisions (Joseph, 2026-09-22), treated as given:** About names "Joseph Garcia", and the only contact is the feedback form. No Render plan change in this PR (cold start is deferred to ops). The AI arguments module is removed. Campaign money is one dated 2024-cycle sentence with an FEC link. "On the ballot" copy describes the seat, never the person.
**Dates:** today 2026-09-22; Election Day Tuesday 2026-11-03 (42 days). **Merge-by date: Monday 2026-10-13** (§10.3). Data facts from the repo: 150 members (CA 54, TX 39, FL 29, NY 28; 8 senators). 1,610 bills, and every one has at least one roll call, because `bills.json` is built from roll-call documents. 1,550 AI summaries: 60 bills have none, and 115 summaries carry `needs_review: true` (they failed the automated grader) and are withheld from display (§2.5 C). 5,369 roll calls: 2,839 House and 2,530 Senate. Of the Senate roll calls, 1,469 are on nominations (`PN` documents), which `sync.py build_member_votes` leaves out of member records. `sync_metadata.last_sync` is 2026-09-05. `ai_summaries.json` has no per-entry date; its last change in git is 2026-07-07. Member narratives were generated 2026-03-16 → 2026-07-02 (withdrawn, §4.3 m3). `donations.json` has 80 entries (2024 cycle, retrieved 2026-03-20): 71 have `totals`, 9 have an empty `totals`, and 1 is for a member not in the roster. One member has no photo (W000832). ZIP crosswalk: 6,639 ZCTAs. 1,485 touch more than one district, and 1,226 are split under the ≥5 % rule. 10 cross into uncovered states, and 4 of those have no covered district at ≥5 %.

---

## 1. Summary

**What changes for the person using the site.** You type your ZIP code on the first screen of the front page. You land on one page that shows your two senators and your House member, and how each voted on their latest final vote on a bill. Tap a name, and the first thing you see is a dated vote with a "Voted yes" or "Voted no" mark, not a paragraph and not a chart. Tap a vote, and the bill page tells you what the bill does and what happened ("The House passed it, 237 to 169, on September 3, 2026"). It shows how *your* representatives voted before it shows anyone else, and you can enter your ZIP right there without leaving the page. Every page says what date its facts are from and says plainly when a plain-English summary has not been written. No page shows a score, a ranking or a stance label. Party labels stay hidden until you ask, on every visit. Pages work on a phone with nothing floating over the content, and they can be shared with a real share button and a proper preview card.

**The three outcomes this redesign is accountable for.**

1. **Two taps to your people.** A first-time visitor reaches the page of any one of their own three members in two taps from the front page (ZIP → delegation → member), on a 375px phone, with JavaScript off if need be. Verified before launch by the scripted QA path (§8 item 13). After launch, a rough proxy only: the count of `/state?zip=` 302s in origin logs. Edge caching hides repeat views from the origin, and the logs have no per-visitor key, so the full funnel cannot be measured without analytics, which are deferred.
2. **The record on the first screen.** On every member page at 375×812, the first dated, linked vote with the member's position is visible without scrolling. On every bill page, including the longest-titled bills, the outcome sentence and the "How did your representatives vote?" block are visible without scrolling. Verified by the fold checks in §6.9.
3. **Nothing on the site says something the data does not support.** Both P0s (F01, F02) are closed by design. Every AI-written block says what it was written from and carries a date: bill summaries carry the date the summary set last changed (`ai_summaries_updated`, **new**, §7.4), because the data holds no per-summary date. Every freshness stamp describes only the content beside it. Every count states its scope (Senate records exclude nominations; bills are those with a roll call). No module presents unsourced or stance-labelled text as content. Verified by the copy checklist in §7.7 and the tests in §10 #22.

---

## 2. Principles and guardrails

### 2.1 Protect (from the review's "What's working")

- The masthead and footer chrome stays as one identical block on every template: double rule, Playfair logo (800, with the italic 600 blue "Voting"), uppercase Inter nav, the tagline "Facts only · No opinions · No spin", and the footer credo. It is compacted (§6.3), not redesigned.
- The broadsheet language is the system, and the redesign finishes it rather than replacing it: Playfair Display for display, Lora for body, Inter for kicker, meta and UI, navy ink on paper, double rules and hairlines, kickers, the status-seal component (kept, with the new wording of §7.2), and the section-mark provision bullets.
- The plain-English bill lead pattern is the template for every bill surface: one-liner headline, 3–4 Lora provision bullets, and the official title demoted to "Officially: …".
- The key-bills picker's principles are kept: dedupe per bill, skip anything without a displayable plain summary, spread across policy areas. It moves server-side and changes twice (§4.3 m2, §2.5 B): only decisive votes qualify, and the member's position is no longer a selection criterion.
- **Not kept:** the member narrative (§2.5 A). It was on the review's protect list, but the data shows it is a per-topic stance summary built from AI-assigned `direction` labels ("mostly/leans in favor"; `member_summary.py:49-71`).
- Party hidden by default is enforced at the data layer, and now also covers every default API payload (§10 #9) and Speaker-election candidate names (§4.3 m4). It is revealed only by an explicit action.
- Primary-source escape hatches ("Roll call source →", Congress.gov links) stay on every surface where they exist today.
- The official summary's JS rendering stays sanitized through `bill.js`'s existing `sanitizeHtml`/`SAFE_TAGS` block and stays collapsed. The server-rendered first paragraph is plain text (§4.4 m4).
- Behaviour that stays: chronological vote data, the two Google Sheets write paths, newest-first bill sorting (the key becomes the activity date, §4.1 m5), and server-side SEO injection (`_inject_meta`). The title and `</head>` contract is unchanged; its tag list is extended (§9.2).
- Existing accessibility scaffolding (skip link, landmarks, `role=status` on notify, visually-hidden labels, reduced-motion switch) is extended, not replaced.

### 2.2 Must not (from the review's "should NOT do" plus the brief's hard constraints)

1. No framework, no build step, no database: FastAPI + vanilla HTML/CSS/JS, flat JSON in `data/`. One PR, merged by Joseph.
2. Every shell keeps a literal `<title>…</title>` and `</head>`. The server owns the title, and no client script writes `document.title`.
3. CSP `script-src 'self'`: no inline scripts and no inline event handlers (`onerror`, `onclick`). `img-src 'self' https://www.congress.gov` only.
4. No new `innerHTML`. `bill.js`'s `sanitizeHtml`/`SAFE_TAGS` block stays.
5. `feedback.js` structural hooks stay (`#feedback-modal`, `#feedback-open`, `#feedback-cancel`, `#feedback-overlay`, `#feedback-form`, `#feedback-message`, `#feedback-submit`, `#feedback-status`, `#feedback-context`, `.state-header h1`, `#data-freshness`, `#about-feedback-cta`). The one sanctioned structural change: `.member-header h2` → `.member-header h1` and `.bill-header h2` → `.bill-header h1`, with the two selectors in `feedback.js` changed in the same commit. The `#data-freshness` id stays; the `/api/health` fetch that overwrote it is deleted (§10 #17).
6. Real data only. The only new data files are (a) `data/synced/zip_districts.json` (Census 2020 ZCTA ↔ 119th CD relationship files, public domain) and (b) `data/synced/senate_2026.json` (Senate seats up in 2026, from senate.gov). Both carry a `_source` object and an entry in `data/SOURCES.md`. They live in `data/synced/` so the existing `get_data_dir()` loader and the Dockerfile's `COPY data/synced/` both reach them. The other new files are derived only from existing data: `votes_index.json` and `state_overview/*.json` (§10 #3, #7). No field is shown that is not in `data/synced/`, those two files, or a derivation named in this spec.
7. No URL-shape changes. No clean-path aliases in this PR, so no 301 work. `?district=`, `?zip=`, `?position=` and the others in §3.3 are additive query parameters. Canonical tags point at one form (§3.3).
8. No re-skinning of the old cards. `styles.css` and `broadsheet.css` are retired and replaced by one fresh `static/css/site.css`. `.glance-card`, `.viz-section`, `.bill-section`, `.state-stat`, `.comparison-table`, `.mobile-card` and `.service-compact` cease to exist.
9. No scores, grades, rankings, stance labels or characterizations: no participation traffic lights, no high-to-low sorts, no yes-percentages on list rows, no "fights for", no "leans"/"mostly in favor", no "N of M" stance ratios, and no characterizing outcome verbs ("blocked", "let the veto stand"). This applies to AI-written text as well as site copy, which is why the narrative module is withdrawn. Comparison happens only on non-ordinal facts (chamber, district, tenure). Red and green appear only inside the one vote component (§6.5).
10. Party labels never enter a default payload, and the reveal never persists across visits. "Payload" includes every `/api/*` JSON response: sponsors' `party`, the `[R-AL-6]` suffix in `fullName`, roll-call `members[].party`, and Speaker-election candidate names (§10 #9).
11. The AI sync is not fixed here, and the design does not assume it is: a newest-by-activity Record, real empty states, a date on the summary set, and a coverage note computed from data. When the sync resumes the design needs no change, because no copy hard-codes a date or says "paused".
12. No promises that will not be true by November 3: no "we're adding more states" without a date. The notify form promises only what it can deliver, and coverage is stated at the point of choice.
13. Definition-of-done gates, not preferences: nothing floats over the primary action on a phone; no standalone control under 44px (§6.9 #4 defines the set); no text under 12px; no text colour below 4.5:1 on paper or white; `document.documentElement.scrollWidth <= innerWidth` at 320 and 375; no content that defaults to `opacity:0`.

### 2.3 Appendix C contradictions, each resolved with a stated principle

| # | Contradiction | Principle | Resolution in this spec |
|---|---|---|---|
| C-1 | "Voted yes 49 %" praised as vocabulary vs F06/F08 calling the percentage noise | **A row shows the record, never a ratio.** Words stay, statistics go. | "Voted yes / Voted no" is the site-wide vocabulary (vote chip, tally labels, outcome sentences). No rate appears on any list row. Roster rows carry one dated vote with the member's position (§4.2). |
| C-2 | Keep the both-sides arguments pairing vs F13 drop the module | **"No opinions" is a constraint on the body, not a slogan on the masthead: unsourced or stance-labelled text does not appear as content.** | Two modules are **cut**, and no API serves them: the AI-drafted "What People Are Saying"/arguments module (bill page, About, and `arguments`/`direction` in `/ai-summary`), and, on the same principle, the member narrative (§2.5 A). The neutrality proof moves to where it is true: party hidden by default, primary-source links on every row, dated AI blocks. A sourced replacement (attributed statements, floor debate, CBO/GAO) is deferred (§12). |
| C-3 | The Record on mobile is a "clean stack" vs F37's 15-line official titles | **The container was right; the row payload was wrong. Official text is bounded wherever it appears.** | The single-column stack stays. Official titles leave summarized rows entirely (they live on the bill page as the capped deck). When an official title is the only headline available, it is set in Lora 500 and clamped to two lines in lists, or capped at 200 characters with a "Show full title" disclosure on the bill page (§4.4, §6.2). |
| C-4 | F07 "hide campaign finance until current" vs F56's visible Money section | **Show dated facts; never headline an undated or stale number; never a tile.** | One inline sentence below the record, only for the 71 members whose `donations.json` entry has the totals it needs, with the reporting period and retrieval date in the sentence and an FEC.gov link (§4.3 m7). Other members get one meta line saying the data isn't there. No headline figure, no bars, no top-donor rows. |
| C-5 | F30 "three sticky layers" vs F07 asking for a mobile name strip vs "at most one sticky" | **One sticky element per page, only where the page is long enough to need it, and it must answer "where am I".** | Member and bill pages get at most one 44px fixed strip that appears after the header scrolls off, without shifting layout (§6.4). The strip is **cut-first** (§10.3). The delegation page and home have none. The tab bar and sticky filter row no longer exist. |
| C-6 | F03/F41 propose new data files vs hard constraint 5 | **The constraint forbids invented data, not attributed public data.** | The brief sanctions exactly these two files. Both ship with a `_source` object written by their build step, an entry in `data/SOURCES.md`, and a paragraph on `/methodology` (the crosswalk's land-area caveat; the Senate list without party letters) (§5.1, §4.6). |
| C-7 | F46 promoting h2→h1 vs constraint 4 | **A hook is a contract between two files; changing both sides in one commit honours it.** | The two selectors change in the same commit as the h1 promotion. Every `#feedback-*` id and `#data-freshness` stay. A test asserts both selectors resolve on the rendered pages. |
| C-8 | F53 CDN-cached shells vs localStorage personalisation vs F19 server-rendered first blocks vs F01 freshness | **The server renders only what is identical for every visitor of a URL, and the browser adds only what belongs to this reader. A cache shorter than 1 % of the data cadence is invisible, but it exists only if the edge is configured to cache.** | Shells and API JSON carry nothing per-visitor. The bill page's "your representatives" slot is server-rendered as the ZIP form and swapped by JS from storage. Only 200 responses (and the ZIP 302s) get long-lived headers (§9.5). Edge caching of HTML and `/api/*` happens **only after Joseph adds the Cloudflare Cache Rule** (§12.4 ops step 1). Until then F63 is unmitigated, and no copy relies on caching. |
| C-9 | F20's on-demand Pillow og-image routes vs F05/F63 "no headroom on the free worker" | **Render once, serve from the edge; never render on the request path.** | Phase A ships four static 1200×630 cards (made once, committed). Phase B (last, cuttable) pre-renders 150 member and 4 state cards at sync time into `static/og/`. No per-request rendering exists in either phase (§9.3). |
| C-10 | Key-bills picker "sound, needs surfacing" vs F08's hardcoded 6-vs-4 asymmetry | **Select by a rule that does not look at the member's position, and print the rule exactly as the code applies it.** | "Recent votes": the eight most recent decisive votes on bills with a displayable summary, one per topic where possible, whatever the member's position (§4.3 m2). Picking a forced 4 yes + 4 no would manufacture an even-looking profile (§2.5 B). |
| C-11 | "Latest Vote ships hidden" as graceful degradation vs F55's layout shift | **Degrade by content, not by geometry.** | The card is server-rendered, so it never appears late. If the votes index is unavailable at render time, the server emits the card at the same size with "The latest vote isn't available right now." (§4.1 m3). |
| C-12 | Five pages assessed vs six templates | — | The 404 page is designed as a page on the spine (§4.8) and gets a real status code (§9.4). |
| C-13 | F04 "remember the last state in localStorage" vs "never persist the party reveal" | **Remember where you live, never how you look. Persist facts about the reader, only on the reader's own act; never persist a lens on the data.** | `localStorage['cv-home']` holds `{state, district}`. It is written only after a ZIP lookup by this reader or a "Remember" tap (§5.4), with a visible "Remembered: New York, District 4 · Forget" control. `sessionStorage['cv-show-party']` holds the reveal for this tab's session only. Both rules are written on `/privacy`. |

### 2.4 Judge grafts — adopted and declined

**Adopted**, with the section that specifies each:
- Share's bill-page roll-call composition (§4.4).
- The one-line edition line as the single carrier of freshness (§6.3, §7.4).
- A real Share action as a 44px secondary control in the header action row, not a large primary button (§6.4).
- The per-state tally and "your rep" chip on the Latest Vote card, client-side (§4.1).
- The initials-block photo fallback (§6.3).
- Cutting the arguments module (C-2).
- The "Your representatives" block on the front page for returning visitors (§4.1).
- The bill fact box `<dl>`, and the Lora-500 rule for official titles standing in as headlines (§4.4, §6.2).
- Definition-of-done gates as checks (§6.9), plus a print block (§6.8, cut-first).
- The tally inside the status seal ("Passed the Senate 90–6") on record rows (§7.2).
- A desktop-only fact strip in the member header, folded to one line on mobile (§4.3).
- og:image in two steps (§9.3).
- `data/SOURCES.md` and inline `role=status` error copy (§5.1, §7.6).
- Share's honest amendment-row wording, now with the parent bill read from the roll-call question (§4.3 m4).
- The coverage-aware notify form, with a required state select listing only uncovered states, behind "Somewhere else?" (§4.1 m2).
- The storage principle in one line (C-13).
- Path-first build order, with each page's shell and JS in one commit and the stylesheet retirement as the last, gated commit (§10.3).
- "Where do you live?" as the visible question above the ZIP field, with state links showing real counts (§4.1).
- One checkbox with a count as the record's summary filter (§4.3 m4).

**Declined**, with reasons:
- **Evolve's `?zip=`/`?state=` on the homepage with `history.replaceState`.** Unnecessary: the ZIP form is a plain GET to `/state`, so there is no JS-enhanced path to fall back from, and a second URL for the same delegation would recreate F04.
- **Evolve's collapsed "Votes by topic" raw-count table.** Raw yes/no counts per policy area invite exactly the ratio reading F06 forbids ("18 no on Environmental Protection" reads as a score), and F28's own test is "cut if it cannot be made neutral". The record's topic and position selects give the same navigation with linked, dated votes.
- **Evolve's "attendance shown only when below 90 %" row copy.** Participation is a count with its scope on every member header ("Voted in 1,060 of the 1,061 Senate votes on bills, amendments and motions in our record"), never on roster rows and never as a threshold. The rule "a count, never a grade" is stated once on `/methodology`.
- **Share's `&zip=` parameter on the bill URL.** With JS, a ZIP entered on a bill page is resolved in place through `/api/districts/{zip}` and fills the slot without leaving the page (§4.4 m2). Without JS it submits to `/state?zip=`, so the reader still gets their delegation, and 1,610 pages get no second URL shape.
- **Share's outlined "Not on the ballot" seal.** Dropped by the PM decision that ballot copy describes the seat. Senators whose seat is not up show no seal at all (§6.4).

### 2.5 Decisions made in this revision, and critique parts declined

**Product calls made during revision — confirmed by Joseph on 2026-09-22, together with the 2026-10-13 merge-by and cut-first trade (§10.3).**

- **A. Member narratives are withdrawn in this PR.** `member_summary.py` feeds the writer per-topic "mostly/leans in favor/against" labels (55–74 % = "leans") computed from the AI-assigned `direction` field. 34 of 150 narratives contain "lean", and 11 contain "N of M"/"about half" ratios. Showing them breaks §2.2 #9, and regenerating them is out of scope. The module is cut from the member page, and `/api/members/{id}/summary` is deleted. `/methodology#ai` says: "Member summaries are withdrawn until they can be rewritten without stance labels." This is reversible later with regenerated text.
- **B. "Key votes (4 yes + 4 no)" becomes "Recent votes".** Selecting by the member's own position manufactures an even-looking profile for members who vote 90 % one way, and "key" implies an importance judgement the rule does not make. The picker now takes the eight most recent decisive votes regardless of position (§4.3 m2).
- **C. Summaries flagged `needs_review` (115) are withheld.** They failed our own automated check, so they are shown like unsummarized bills: the official title plus the "No plain-English summary yet" seal. They are excluded from Recent votes and the hero headline, and counted on `/methodology`. No new data and no per-bill grade is involved.

**Parts of critique fixes declined or superseded** (each issue's problem is still fixed):

1. "Drop unused Playfair 800 / 600 italic" is declined: the protected logo uses both (`broadsheet.css:58-59`). Inter 500 is added instead of changing `--t-ui` (§6.2).
2. The Election Day countdown uses America/Los_Angeles, not America/New_York, so "Election Day is today" lasts until California polls close (§7.4).
3. jinja2 block macros are declined in favour of the other option the issue offered: one escape helper `h()` plus a test that feeds hostile strings through every renderer. This keeps one rendering style and adds no second template layer (§9.1).
4. The fixes that kept "4 yes + 4 no with a decisive filter" are superseded by B. Their decisive-only filter, Yea/Aye/Nay/No mapping and "mark seen only after a pick" are adopted.
5. The fixes that kept narratives while hiding the 34 "lean" ones, or that scoped the rule to site copy, are superseded by A.
6. A state-only `cv-home`, and per-row "This is my district" / "These are my senators" buttons on every roster row, are declined. They would put a second control inside every whole-row-link person row (the F60 link-in-link risk) and add a second storage shape. Instead there is a "Remember District 4 as mine" button on district URLs and the ZIP form on every delegation page (§5.4).
7. The cross-state ZIP rule "summed share < 0.5 → not found" is declined in favour of one rule that never hides a covered match. No district ≥ 5 % → not found. A covered share under 0.95 → show the match with an "outside our four states" note, with no 302 and no `cv-home` write (§5.1).
8. "Build both indices in a startup hook" is declined in favour of the sync-time `votes_index.json`, so a cold start does not pay the 5,369-file scan (§10 #3).
9. "Give `/api/health` max-age=60" is declined: the only per-page health fetch (feedback.js freshness) is deleted, so `/api/health` stays `no-store` and is called by no page.

---

## 3. Information architecture

### 3.1 Pages and URLs after the redesign

| URL | Page | Change |
|---|---|---|
| `/` | Home: the entrance to the spine | Rebuilt. In-page delegation renderer retired; state cards become links; ZIP form first. |
| `/state?code=NY` | Delegation: the one canonical, shareable, server-rendered roster | Rebuilt on the homepage delegation component. Additive params: `&district=4` (shows "Your representatives"), `&zip=11201` (a ZIP's matches; used for split and cross-state ZIPs). **`/state?zip=…` (no `code`) is the form target:** the server normalizes the input (accepts `11570`, `11570-1234`, `11570 1234`, surrounding spaces) → single covered match → **302** `/state?code=NY&district=4#mine`; split or cross-state match → **302** `/state?code=NY&zip=11201`, which renders **200**; no match → **200** at `/state?zip=44101` rendering the not-found state (§5.3); malformed → **200** with "A ZIP code is five digits." `code` + `zip` that disagree → the lookup is re-run and **302** to the ZIP's state. Invalid `code` (not CA/FL/NY/TX after uppercasing) → **404**. |
| `/member?id=S000148` | Member: header → recent votes → the record by bill | Rebuilt, record-first, server-rendered. Additive params for the record: `&page=2`, `&topic=Health`, `&position=no`, `&plain=1`. Unknown id → **404**. |
| `/bill?congress=119&type=hr&number=4795` | Bill: what it does, what happened, how your representatives voted | Rebuilt, server-rendered. `type` is lower-cased before lookup and in canonical. Unknown bill → **404**. |
| `/about` | Who runs this, why, funding, contact, what the site does not do | Rewritten; static; no animation. |
| `/methodology` | **New.** Sources, cadence, the neutrality rules, what AI touches, coverage and scope with numbers, the recent-votes rule, the ZIP caveat, a dated corrections log | New static shell with server-filled counts (§4.6). |
| `/privacy` | **New.** What is stored, where, by whom, how long; browser storage; third-party requests | New static shell (§4.7). |
| 404 | "Not in this edition" with the ZIP form | Rewritten; real 404 status for unknown ids/codes and unknown paths (§4.8). |
| `/favicon.ico` | **New route** serving `static/favicon.svg` content with a long max-age | F52. |
| `/static/og/*.png` | Share cards (Phase A: 4 static; Phase B: per member/state) | §9.3. |
| `/bills` | Bill browse/search page | **Deferred** (§12). The homepage keeps its collapsed browse panel at the foot. The "Load more" offset bug is fixed, the panel reflects `?q=` with `history.replaceState`, and `app.js` reads `?q=` on load to open the panel and run the search. |

Retired: the homepage's in-page delegation (`app.js` `loadDelegation`/`selectState`), the member tab bar, the member narrative and its API, the bill TOC row, the bill "What People Are Saying" module, `viz.js`, `styles.css`, `broadsheet.css`, all three `document.title` writes, the floating Feedback pill under 880px, and the `feedback.js` freshness fetch.

### 3.2 The primary path

1. **`/`:** type a ZIP into the first screen's field and press **Find my representatives**. The form is `<form method="get" action="/state">` with `<input name="zip" inputmode="numeric" autocomplete="postal-code" maxlength="10" pattern="\s*[0-9]{5}([\-\s]?[0-9]{4})?\s*" required>`. JavaScript never intercepts it. The server applies the same rule: `^\s*(\d{5})(?:[-\s]?\d{4})?\s*$` → the first five digits.
2. **`/state?zip=11570`:** the server resolves 11570 → NY-4 (one district ≥5 %, covered share ≥0.95) and returns `302` → `/state?code=NY&district=4#mine`. The page opens with **Your representatives**: Sen. Kirsten E. Gillibrand, Sen. Charles E. Schumer, and Rep. Laura Gillen (District 4). The full New York House roster follows, collapsed. `site.js` sees `#mine`, writes `cv-home = {state:"NY", district:4}`, and removes the fragment with `history.replaceState`.
   - **Split ZIP:** `/state?zip=11201` → `302` → `/state?code=NY&zip=11201` (200). You see the two senators, then "ZIP 11201 spans two House districts — which is yours?" with Districts 10 and 7 as full member rows (about 72 % / 28 % of the ZIP's *land area*, not its residents). Each has a "This is my district →" link (`/state?code=NY&district=10#mine`), and there is "Not sure? Look up your district by street address on house.gov →". Nobody is blocked: the names already link to member pages.
   - **No match:** `/state?zip=44101` (200). The one not-found message (§5.3), then the four state links, then the notify disclosure.
3. **Tap a member** → `/member?id=G000602`. The first dated vote is on the first screen.
4. **Tap any vote** → `/bill?…`. The outcome sentence and "How did your representatives vote?" sit in the fold, filled from `cv-home`, or resolved in place from a ZIP typed on the page.
5. **Masthead "My representatives"** (every page) goes to `/state?code=NY&district=4` when `cv-home` exists (`site.js` rewrites the link at load; the server-rendered `href` is `/#find`), else to `/#find`.

Success measure: two taps from `/` to a member page; three to the bill. Back always returns to a real URL.

### 3.3 URL state rules

- **Canonical forms** (the only forms in `<link rel=canonical>`, the sitemap and Share): `/`, `/state?code=XX` (uppercase), `/member?id=X` (uppercase id), `/bill?congress=N&type=xx&number=N` (lowercase type), `/about`, `/methodology`, `/privacy`. The server normalizes case before lookup and before building canonical, so a request with `type=HCONRES` renders with canonical `type=hconres`.
- **Additive, non-canonical, cache-safe parameters** (canonical strips them): on `/state`, `district` and `zip`; on `/member`, `page`, `topic`, `position` and `plain`. They are real server-side state (the server renders accordingly), so they work with JS off and Back restores them. The Share control never includes them.
- **The `#mine` fragment** is never sent to the server and never cached. It exists only on the ZIP 302 target and on "This is my district" links, and it is the only automatic trigger for writing `cv-home` (§5.4).
- **Shareable selections that exist as URLs:** a state (`/state?code=NY`), a district's delegation (`/state?code=NY&district=4`, shareable but not canonical), a filtered page of a member's record (`/member?id=S000148&topic=Health&position=no&page=2`), and a bill. Topic-filtered bill lists (`/bills?topic=`) are deferred with `/bills`.
- **Storage** (§5.4): `localStorage['cv-home']` and `sessionStorage['cv-show-party']`, nothing else. No cookies. `site.js` removes the legacy `localStorage['cv-show-party']` once on load.
- **No `pushState`.** `history.replaceState` has exactly three uses: the homepage browse panel reflecting `?q=`; removing `#mine` after the write; and the optional in-place record pagination (cut-first).

---

## 4. Page specs

**Common to every page:**
- Compact masthead (§6.3) and edition line (§7.4); `<main id="main-content" tabindex="-1">`.
- Footer: the three trust links repointed (`/about`, `/methodology`, `/privacy`), "Report an error on this page" (`id="feedback-open"`), the data-source line and the credo. `#data-freshness` is rendered by the server only when `last_sync` exists; no JS rewrites it.
- Server-rendered content is inserted at a literal `<!--content-->` marker inside `<main>` by `_serve_html` (§9.1). Each shell's `<main>` carries `<noscript>` copy only where JS adds something (stated per page).
- Heading outline per template (§8 item 2).
- **Error state** when the server cannot render (data missing at request time): the masthead, the H1 from `meta['h1']` (each route sets it; it defaults to the page title without " | ClearVoting"), and the sentence "We couldn't load this page right now. Please try again in a moment, or use *Report an error* below to tell us." Never a Congress.gov excuse (F61).

### 4.1 Home (`/`)

**Purpose.** Get the reader onto the spine in one action, and prove the promise (a real vote, dated honestly) without spending the first screen on it.

**Mobile fold (375×812), top to bottom:**
- Masthead: logo, tagline, and nav on one 44px row (≈120px).
- Edition line (one line, ≈24px).
- Kicker "An independent record of Congress", then H1 "See how your representatives vote.", then a one-line deck.
- The finder: the visible question "Where do you live?" (Lora italic, `<label for="zip">`), a hint line "5-digit ZIP code" (`.meta`, the field's `aria-describedby` until an error replaces it; omitted where the label already says ZIP; the field's `title` is "A ZIP code is five digits." so the browser's own validation message is plain) (QA 2026-09-26), a 48px full-width ZIP field, and a 48px full-width navy button **Find my representatives**. Input and button stack under 560px so the field is never squeezed.
- The line "Or choose a state:" with four 44px chips "California · 54", "Florida · 29", "New York · 28", "Texas · 39" (counts server-rendered from `get_member_counts()`).
- The coverage sentence.

All of this lands by ≈560px, and nothing else is on the first screen.

**Desktop fold (1280×800).** A two-column lead (3:2). Left: kicker, H1, deck, finder, state chips, coverage sentence, and the "Somewhere else?" disclosure. Right: the Latest Vote card. Both columns finish within ≈700px so "The Record" head is visible.

**Modules in order** (all server-rendered unless marked JS):

1. **Masthead + edition line** (§6.3, §7.4).
2. **Lead + finder.**
   - **Coverage sentence:** "ClearVoting covers California, Florida, New York and Texas today — 150 members and every bill that has had a roll-call vote since January 2021." Numbers come from `len(members)` and the earliest roll-call date in the index.
   - **"Somewhere else?"** is a native `<details>` holding the notify form: a required `<select name="state">` listing the 46 uncovered states plus DC (CA, FL, NY and TX are *not* options; the placeholder is "Choose your state"), `<input type="email" autocomplete="email">` at 16px/48px, and the navy button **Notify me**. Below: "We store your email, your state and the time you signed up. *Privacy →*".
   - **Submission:** the form has **no `action`/`method`**. `site.js` POSTs JSON to `/api/notify` (`email`, `state`). Without JS the form does nothing, and `<noscript>` says "Signing up needs JavaScript."
   - **Result copy** (JS, `role=status`, focus moved to it). Success: "Thanks — we'll email you when {State} is added." Failure: "We couldn't save that. Please try again in a few minutes." Duplicate signups are treated as success.
   - **Returning visitors:** the "Remembered from your last visit: New York, District 4 → Show my representatives · Forget" line appears under the button **only when** module 4 fails to load. Otherwise module 4 is the remembered view.
3. **The Latest Vote**: a structured `<aside class="vote-card">`, never a sentence template. Server-rendered from `get_latest_vote()` (§10 #11).
   - **Dateline:** kicker "The latest vote", then "U.S. House · September 3, 2026 · Final vote to pass" (`chamber`, `vote_date` via the date helper, the plain question of §7.1).
   - **Headline:** the AI `one_liner` in Playfair when the bill has a displayable summary (exists and not `needs_review`). Otherwise the official `bill.title` in Lora 500, clamped to two lines, with the seal "No plain-English summary yet".
   - **Result:** the tally bar (§6.4) with "237 yes · 169 no"; the outcome as a status seal ("Passed the House 237–169").
   - **Link:** "What this bill does, in plain English →" when a displayable summary exists, else "See the vote and the official summary →".
   - **JS enhancement** when `cv-home` exists: `site.js` fetches `/api/votes/latest` (edge-cacheable; it carries `state_tallies` and `covered`) and appends one meta line: "New York: {n} yes · {n} no · {n} didn't vote · Your rep, Laura Gillen — **Voted yes**". For a Senate vote, the two senators' chips instead. The reader-relation rules of §4.4 m2 apply ("Not in the House for this vote").
   - **Which vote is shown (F02):** the most recent roll call by date whose `document` parses to a bill in `bills.json`, with decisive votes (§7.1) first within a day. A newer un-summarized vote is **not** skipped; it is shown honestly with the fallback headline.
   - **Edge cases:** nomination and non-bill documents never become the hero (existing `_parse_bill_document` filter). A tie renders "Tied, 50 to 50" and the result string. Voice votes have no roll call and never appear. If the votes index is unavailable, the card renders at the same size with "The latest vote isn't available right now." (C-11).
4. **Your representatives** (JS only; absent for first-time visitors). When `cv-home` exists, `site.js` renders the same three person rows the delegation page uses (§6.4 person row) from `/api/members/{state}/overview` (precomputed file, cacheable). The head reads "Your representatives · remembered from your last visit · *Change* · *Forget*". Same component, same copy, no separate design. It is inserted below the finder, so it never shifts the fold.
5. **The Record.**
   - **Head:** kicker "The Record", H2 "What Congress voted on". Stamp line: "As of September 5, 2026 · every bill that has had a roll-call vote since January 2021, newest activity first · {n} of the {m} bills below don't have a plain-English summary yet and show their official title." (`last_sync`; `n` and `m` counted from the rendered rows). When `n` = 0, the last clause is omitted.
   - **Order:** by **activity date** = max(`latestAction.actionDate`, the bill's newest roll-call date from the index). This fixes bills such as 119-hr-6500, whose `latestAction` (Feb 10) predates its Sep 1 roll call.
   - **List:** the seven most recent bills by activity date, regardless of summary (`/api/bills?limit=7`, `one_liner` nullable). The first is set as the **lead**: kicker (bill code · Congress ordinal), status seal with tally (§7.2), date, and headline. With a displayable summary, the headline is the Playfair `one_liner`, followed by up to 4 section-mark provisions, "Officially: {title}" capped at 140 characters (with "Show full title" `<details>` when longer), and "See who voted →". Without one, the headline is the Lora 500 official title capped at 140 characters with "Show full title", plus the pending seal. Rows 2–7 each show: kicker bill code, status seal, date, and headline (the Playfair `one_liner`, or the Lora 500 official title clamped to two lines plus the pending seal). No official title on summarized rows.
   - **After the list:** when the lead has no displayable summary, a compact block "Most recent plain-English summary · {activity date}" with that bill's Playfair one-liner, provisions (max 4) and link (`/api/bills?summarized_only=true&limit=1`). When the lead has one, this block is omitted.
   - **Foot:** "Browse all bills by topic →" (the existing collapsed panel, unchanged except the offset fix and `?q=`).
6. **Footer.**

**States.**
- Data unavailable at render: the hero behaves as above; the Record renders its head and "We couldn't load recent bills right now."
- No-JS: everything above renders except module 4, the Latest Vote's per-state line, and the notify form (its `<noscript>` says so). The browse panel needs JS (its `<noscript>` says so).

**Removed and why.**
- The in-page delegation, its party toggle, its scroll-to-spinner, and the `/api/members/{state}?include_stats=true` call (F04, F05, F21).
- The "Voted yes 49 %" bars (F06).
- The sentence-template hero (F17).
- Official titles on Record rows (F37).
- "Updated weekly" and the trust line, replaced by dated facts (F40).
- The red notify button and the state-less notify form (F35, F39).
- The "written through {date}" claim, which was false for 23 older unsummarized bills.

### 4.2 Delegation (`/state?code=NY`, with `&district=` / `&zip=`)

**Purpose.** The shareable, crawlable home of a state's delegation and the page every ZIP lands on; the page a search for "New York representatives voting record" should land on.

**Mobile fold, top to bottom:**
- Masthead + edition line.
- Kicker "New York · 28 members · roster as of September 5, 2026" (`roster_as_of` = max `updateDate` among the state's members).
- H1 "Your representatives" (when `district` or `zip` is present) or "New York's representatives".
- The district line, when `district` is present: "New York, District 4 · *Change ZIP*" (44px), plus a 44px secondary button **Remember District 4 as mine** that appears only when `cv-home` does not already equal this district. Otherwise the compact ZIP form (same component as home, one row: field + 48px button).
- The action row: party toggle (§6.4) and Share.
- The first person row in full.

On a split-ZIP page, the "spans two districts" block sits between the senators and the House pick, within the second screen.

**Desktop fold.** The same, with the three "your" rows in a 3-up grid under the header.

**Modules in order** (server-rendered from `data/synced/state_overview/{code}.json`, §10 #7):

1. **Header** as above. The `<h1>` sits inside `.state-header` (hook kept). The party toggle and Share are 44px controls in one action row, with the meta line "Party labels are hidden so the record speaks first."
2. **Your senators and House member** (only with `district` or `zip`; "House members" when a ZIP offers more than one district — the h1 already says "Your representatives", so the block names who is in it): the two senator rows, then the House row(s).
   - **Split ZIP:** a note block: "ZIP 11201 spans two House districts — about 72 % of the ZIP's land area (not its residents) is in District 10 and 28 % in District 7. Both are shown; your street address decides which is yours. *Not sure? Look up your district by street address on house.gov →*". Then each House row with a sibling link "This is my district →" (`/state?code=NY&district=10#mine`). These rows are the one place a person row is a `<div>`, with the name as the link and the district link as a sibling (no link inside a link, F60).
   - **Cross-state ZIP** (covered share < 0.95): add "About {p} % of ZIP {zip}'s land area is outside California, Florida, New York and Texas; if you live in that part, we don't cover your state yet." `cv-home` is not written.
   - **Vacancy:** if the crosswalk names a district with no member in `members.json`, the row reads "District 7 — vacant in our data · *Tell us if this is wrong*".
3. **U.S. Senate**: group label "Both represent all of New York", two person rows. **Omitted on `district`/`zip` URLs**, because module 2 already shows both senators.
4. **The House, by district**: label "By district, 1–26", person rows in district order, two columns at ≥880.
   - On `district`/`zip` URLs the group is a `<details>` "All 26 New York House districts" (closed). On plain `/state?code=` it is an open section.
   - **Vacant districts** are the numbers 1..N with no member in `members.json`. N = the maximum district for the state in the crosswalk, computed once at startup (NY 26, FL 28, TX 38, CA 52; today FL-20 and TX-23 are vacant). They render as "District 20 — vacant in our data".
5. **Foot:** "Don't know your district? Enter your ZIP" (the same inline form); "Roster from Congress.gov, as of {roster_as_of} · Wrong person? *Report an error*"; the Congress.gov delegation link; the notify disclosure for other states.

**Person row content** (§6.4):
- Photo (56px, initials fallback) and name (Playfair; the link covers the row).
- Seat line: "District 4 · In Congress since 2025" (from `district` and the earliest `terms.item[].startYear`).
- The seat seal from `seat_up_2026` (§7.4): "Seat up Nov 3" for every House seat and for Cornyn's seat; "Special election Nov 3" for Moody's seat; nothing for the other six senators.
- One signal line: "Latest final vote · Sep 3, 2026 · {headline} — **Voted yes**" (the label says "final" because a newer procedural vote may exist). This is the member's most recent **decisive** roll call on a bill (index class, §7.1). The headline is the `one_liner` when the bill's summary is displayable, else the official title clamped to one line plus the pending seal. The member's position is shown as a vote chip; the row's link target is unchanged (the bill is one tap further, on the member page). Most rows are expected to show the same bill; that is the record, not a score. Members with no decisive bill vote: "No final votes on bills in our record yet".

**Party reveal.** Rows are server-rendered with an empty `<span class="party"></span>`. On toggle, `site.js` fetches `/api/members/{code}/overview?show_party=true` (same file, party not stripped) and fills the spans with full names ("Democratic", "Republican", "Independent"). Nothing re-renders. One `role=status` line (present and empty in the HTML) gets "Party labels shown".

**States.**
- `code` missing → the ZIP finder page (H1 "Find your representatives", the form, the four state links).
- Invalid `code` → 404.
- `district` out of range or not in the roster → the roster with "We don't have a District 40 in New York" above it.
- Overview file missing → the server falls back to `get_members_by_state()` without signal lines and logs a warning. This is defensive only: the files are committed in the PR (§10 #7).
- No-JS: everything renders. The party reveal and the "Remember" button need JS (`<noscript>`: "Party labels and remembering your district need JavaScript").

**Removed and why.** The four stat boxes ("60K votes cast"), participation bars and thresholds, the support-rate sort, Total Votes, the alphabetical default, the comparison table and its fake-sortable headers, the mobile card variant, the 150-char narrative snippet, and the `document.title` overwrite (F06, F34, F36, F48, F20).

### 4.3 Member (`/member?id=S000148`)

**Purpose.** Who this person is and how they have actually voted, with the first dated vote on the first screen.

**Mobile fold (375×812), top to bottom:**
- Masthead + edition line.
- Breadcrumb "← New York's representatives" (`/state?code=NY`). When `cv-home` matches the member's state, `site.js` points it at the district URL.
- Header: 64px bordered photo; kicker "U.S. Senator · New York" (House: "U.S. Representative · New York, District 4"); **H1** "Charles E. Schumer" (`display_name` from `name`, "Last, First M.").
- The fact line, with a House and a Senate form:
  - House: "In Congress since 2025 · Voted in 641 of the 657 House roll calls since January 2025"
  - Senate: "In Congress since 1981 — House 1981–1999, Senate since 1999 · Voted in 1,060 of the 1,061 Senate votes on bills, amendments and motions in our record since January 2021"
  - Sources: `terms.item`; `stats.total_votes` minus `stats.not_voting_count`; `stats.total_votes`; the month of the earliest `date` in `member_votes`.
- The seat seal ("This seat is on the ballot Nov 3, 2026" / "Special election for this seat Nov 3, 2026"; nothing when the seat is not up).
- The action row: party toggle · Share · Congress.gov.
- Kicker "Recent votes" and the first vote row with its chip, visible by ≈700px.

**Desktop fold.** The header as a byline block (photo left, name and fact line right, action row right-aligned), with the desktop fact strip. It has three cells:
- "Roll calls voted · 1,060 of 1,061"
- "Record covers · Jan 2021 – Aug 8, 2026" (min and max `date` in `member_votes`)
- "Party · hidden — Show party labels"

Under it, Recent votes in two columns (4 + 4, in order). The record begins directly below.

**Modules in order** (server-rendered from `get_member_page()`, §10 #8):

1. **Header** as above. `.member-header` wraps the `<h1>` (the sanctioned hook change). Optional (cut-first): a 44px fixed strip with the name and two in-page links "Recent votes · Record", shown after the header scrolls out (§6.4 sticky strip).
2. **Recent votes.** Eight rows, chosen server-side by one rule:
   - **Candidates:** the member's roll calls with a non-null `bill_id`, a displayable summary (`has_plain_summary` and not `needs_review`), a non-empty `policy_area`, a **decisive** question class (index, §7.1), and a position of Yea/Aye (→ yes) or Nay/No (→ no).
   - **Dedupe:** walk newest first and keep the first qualifying roll call per `bill_id`. A bill is marked seen only when a vote is picked, so a later decisive vote is not lost behind a "Not Voting" one.
   - **Spread:** round-robin by policy area in order of each area's newest vote, so the first pick is the newest vote overall, and so on. Output is sorted newest first.
   - **Row** (shared vote row, §6.4): chip "Voted yes"/"Voted no"; Playfair headline = `one_liner`, linked to `/bill`; meta "H.R. 6500 · Passed the Senate 90–6 · Aug 8, 2026 · Economics and public finance" (bill code via the formatter, seal via §7.2 from the index, date, `policy_area`).
   - **Caption:** "The eight most recent final votes on bills with a plain-English summary, one per topic where possible, whatever the member's position. *How this list is chosen →*" (`/methodology#recent-votes`).
   - **Short records:** "{n} recent votes so far" with as many as qualify. None: the module is omitted.
3. **Summary: withdrawn** (§2.5 A). Nothing renders and no placeholder appears. `/methodology#ai` carries the withdrawal line.
4. **The record.**
   - **H2:** House: "Every roll call, by bill". Senate: "Votes on bills, amendments and motions, by bill".
   - **Count line**, verbatim from `stats`: "1,061 roll calls since January 2021 · 519 yes · 540 no · 1 didn't vote · 1 other". `Present`/`Guilty`/candidate names are counted in "· {n} other" (= `total_votes` − `yea_count` − `nay_count` − `not_voting_count`; `stats` has no such field) only when non-zero (S000148 has one "Guilty"; G000602 has 4). For senators, a second meta line: "Senate votes on nominations ({n} since {month YYYY}) aren't in this record yet. *Why →*" (`/methodology#coverage`; `n` counted from index roll calls with `PN` documents on or after the member's first vote).
   - **Controls** (one row, native, 16px, 44px), all in a `GET` form to the same URL (JS may submit on change): `<select name="topic">` "All topics" + the member's `policy_areas`; `<select name="position">` "All positions · Voted yes · Voted no · Didn't vote"; `<input type="checkbox" name="plain" value="1">` "Only bills with a plain-English summary ({n} of {N} bills)"; a **Filter** button. The result count is a server-rendered line under the heading ("12 bills on Health"), and the heading receives focus through `#record`.
   - **Rows** are groups, newest first, 15 groups per page:
     - **Bill group** (`bill_id` non-null): kicker bill code; status seal with tally from the group's latest decisive roll call, else its latest roll call (§7.2, from the index); that roll call's date. The headline is the `one_liner` in Playfair when the summary is displayable. Otherwise it is the `one_liner` field's string (which holds the official title) in Lora 500, clamped to two lines, with the pending seal; the string is never printed twice (F09/F27). The member's chip is for that roll call. When the group has more than one roll call, a `<details>` "+ 2 more roll calls on this bill" lists each as: plain question (§7.1) · result phrase (§7.2) · date · the member's chip · "Roll call source →" (a sibling link, never nested). The headline links to `/bill` for every type in the shared type map (H.R., S., H.J.Res., S.J.Res., H.Con.Res., S.Con.Res., H.Res., S.Res.), so resolutions link (F27).
     - **Other votes group** (`bill_id` null): consecutive such votes collapse into one dated row per calendar day, e.g. "14 amendments and motions · Aug 8, 2026". A `<details>` lists each as "{Label}{parent} · {result phrase} · **{chip}** · Roll call source →":
       - Label, from the `result` prefix: `Amendment…` → "Amendment"; `Motion…` or a procedural question → "Motion"; otherwise the §7.1 plain question (e.g. "Attendance call").
       - Text: the vote's own `one_liner`/`bill_number` string verbatim, in quotes, when non-empty.
       - Parent: " to S.Con.Res. 5" when the index `question` names one (pattern `\bto (H\.R\.|S\.|H\.J\.Res\.|S\.J\.Res\.|H\.Con\.Res\.|S\.Con\.Res\.|H\.Res\.|S\.Res\.)\s*\d+`; 377 of S000148's 478). Linked to `/bill` when that bill is in `bills.json`. This reads the data; nothing is inferred.
       - When there is no text and no parent: "{Chamber} vote · no bill or amendment text in our data · {result phrase} · {chip} · Roll call source →" (17 of S000148's rows; G000602's 11 quorum and "Present" rows read e.g. "Attendance call · Jan 6, 2026 · Present").
     - **Speaker elections** (`vote` is a candidate name) read "Election of the Speaker · Jan 3, 2025 · Voted · Roll call source →" with a neutral chip "Voted". The candidate's name ("Voted for {Name}") appears only while the party reveal is on, from the `show_party=true` payload (§4.3 party reveal). A vote for a party's nominee is a party cue.
     - Nominations never appear (they are not in `member_votes`).
   - **Pagination:** real links "← Newer votes · Older votes →" carrying `page`, `topic`, `position`, `plain` and the fragment `#record`, so the browser lands focus on the record heading (`tabindex="-1"`). Cut-first enhancement: `site.js` fetches `/api/members/{id}/page?…` and swaps in place, moving focus to the heading and calling `history.replaceState`.
5. **Bills they sponsored that got a floor vote ({n}).** An inline list of at most six rows (`get_bills_by_sponsor`): bill code (formatter) · headline (`one_liner` when the summary is displayable, else `title` in Lora 500, clamped) · "Introduced {introduced_date}" · status seal (§7.2). Under the list, for every member including n = 0, "All legislation {Name} sponsored, on Congress.gov →" (`https://www.congress.gov/member/{slug}/{bioguideId}`, where `slug` is the display name lower-cased and hyphenated; QA checks one link resolves). When n = 0 the module shows only the heading "Bills they sponsored that got a floor vote (0)" and that link. Never the raw `latest_action` string.
6. **Ballot:** no separate module. The seat seal in the header is the only ballot fact; no "next up in 20XX", because that year is not in the sanctioned data.
7. **Campaign money.** Only when `donations[id].totals` has `total_receipts`, `total_individual`, `total_pac` and `total_disbursements`, and the entry has `fec_candidate_id` (71 members). One sentence: "In the 2023–2024 FEC reporting period (the 2024 cycle), this member's campaign committee reported $2.8 million raised ($2.3 million from individuals, $202,800 from PACs) and $3.3 million spent; retrieved March 20, 2026. The 2025–2026 period is not yet in our data. *Filings on FEC.gov →*" (`cycle`, the four totals, `last_updated`; link `https://www.fec.gov/data/candidate/{fec_candidate_id}/`). For every other member, one meta line: "Campaign finance isn't in our data for this member yet." No headline number, no bars, no contributor rows (C-4).
8. **Footer** with "Report an error on this page".

**Party reveal.** The header carries an empty `<span class="party">`. On toggle, `site.js` fetches `/api/members/detail/{id}?show_party=true`, which returns `partyName` and `speaker_votes` (a map from roll-call key to candidate name for this member). It writes "Democratic"/"Republican"/"Independent" into the span and "Voted for {Name}" into each Speaker row's empty `<span class="speaker-pick" data-rc="house/118_1_00002">`. The status line reads "Party labels shown".

**Share.** `navigator.share({title, text, url})`, where title is the server title, text is "How Charles E. Schumer has voted in Congress", and url is canonical. The fallback copies the canonical URL and writes "Link copied" into a `role=status` node that is present and empty in the server HTML.

**States.**
- Unknown id → 404 page.
- Member without a photo (W000832) → initials block.
- Member without money totals → the one meta line.
- Fewer than 8 recent votes → as many as qualify, with the count in the caption.
- Filter yields nothing → "No votes match these filters." and the controls.
- `member_votes` file missing → header from `members.json` plus "We don't have this member's roll-call record yet."
- No-JS: everything renders and paginates. The party reveal, Share and the sticky strip need JS.

**Removed and why.**
- The donut, the attendance ring/bar, the three stat tiles, and the six topic bars ("What They Fight For").
- The Service History card, folded into the fact line and computed correctly from all `terms`.
- Tabs, the second sticky bar and the sticky filter row, and "Copy Link".
- The client-side recomputation of key bills and stats, and the `?limit=2000` download.
- The empty `vote-item-title` div, "Bill Bill Passed", empty policy chips, and "Resolution — no details available" (F07, F08, F09, F26, F27, F28, F29, F30, F54, F56).
- The AI narrative (§2.5 A).
- "Votes by topic" is not carried (§2.4).
- The old "All Votes / Yea / Nay / Not Voting" filter is **kept** as the position select.

### 4.4 Bill (`/bill?congress=119&type=hr&number=4795`)

**Purpose.** "Congress just voted on X — what does it do, and how did MY representatives vote?"

**Mobile fold (375×812), top to bottom:**
- Masthead + edition line.
- Kicker "H.R. 4795 · 119th Congress" with the status seal "Passed the House 237–169".
- **H1:** the `one_liner` (Playfair) when the summary is displayable. Otherwise the official title in **Lora 500 at `--t-h3`**, cut at 200 characters on a word boundary with "…", with a "Show full title" `<details>` right under it holding the full text.
- Deck (only when the H1 is the one-liner): "Officially: {title}" in Lora 500, capped at 140 characters on a word boundary, with the same "Show full title" disclosure when longer.
- The outcome sentence (Lora) "The House passed it, 237 to 169, on September 3, 2026.", then the tally bar.
- **How did your representatives vote?**: the three person rows with chips (JS from `cv-home`) or, server-rendered in the same slot, the ZIP form "Enter your ZIP to see how your representatives voted". This block is visible by ≈700px, including on the fold-check fixtures with the longest titles (119-hres-1499, 1,063 characters; 119-hres-354, 1,955 characters; §6.9 #6).

**Desktop fold.** Headline column (7) and fact box (5) side by side. The outcome sentence, tally and "How did your representatives vote?" sit under the headline column.

**Modules in order** (server-rendered from `get_bill_page()`, §10 #10):

1. **Story head**: kicker, seal, H1, deck, outcome sentence, and tally bar.
   - The outcome sentence describes the bill's most recent **decisive** roll call (§7.1, §7.3).
   - If the bill has no decisive roll call (115 bills today, e.g. cloture-only or amendment-only), the seal is "No final vote yet". The sentence describes the latest roll call by its plain question: "The latest recorded vote: on August 8, 2026 the Senate voted 52 to 46 to end debate on taking it up; 60 votes were needed, so debate did not end."
   - `.bill-header` wraps the `<h1>` (the sanctioned hook change).
   - Optional (cut-first): a 44px fixed strip "H.R. 4795 · Passed the House 237–169 · Share" after the header scrolls out.
2. **How did your representatives vote?**
   - **Slot content:**
     - (a) `cv-home` present → the reader's House member row and two senator rows. Names, photos and districts come from `/api/members/{state}/overview` (the same edge-cacheable file the home block uses), because on a roll call from an earlier Congress the reader's current members are often not in the rendered list at all. Positions come from the page's server-rendered state groups (module 3): the server puts `data-bioguide` on every covered member's row (Senate rows matched by `last_name` + `state` at render time), and JS looks each current member up by that attribute. No position is fetched.
     - A chamber with no roll call rendered on this bill (e.g. a Senate-only cloture vote) gets one line in place of its rows: "The {House|Senate} has no recorded vote on this bill in our data." The "Not in the … for this vote" chip is used only when that chamber's roll call exists and the member is absent from it.
     - (b) No `cv-home` → the ZIP form. With JS, the form calls `GET /api/districts/{zip}` in place. A single covered match writes `cv-home` and fills the slot. A partial match shows its district(s) inline with the "outside our four states" note and writes nothing until the reader picks one. A split shows the district choice inline (buttons "District 10" / "District 7", each writing `cv-home` and filling the slot). No match shows the not-found sentence of §5.3 with the state links. Without JS the form is a plain GET to `/state`.
     - (c) Defensive only (no bill in the data lacks a roll call): no roll call → the slot is omitted.
   - **Per-row relation to the roll call:**
     - In the roll-call member list with a position → chip ("Voted yes", "Voted no", "Present").
     - In the list with "Not Voting" → "Didn't vote".
     - **Not in the list at all** → "Not in the {House|Senate} for this vote" as a neutral grey chip with no colour. 1,121 of 1,610 bills are from the 117th or 118th Congress, when many current members were not yet serving (117_1_00006 lists Katko for NY).
   - **Matching:** House rows by `bioguide_id`; Senate by `last_name` + `state`, exactly as `sync.py build_member_votes` does.
   - Under the rows: "Remembered: New York, District 4 · *Change* · *Forget*".
   - The slot is re-filled on `pageshow` when `event.persisted`, so a page restored from the back-forward cache is correct.
3. **The vote, by state** (for the head's roll call). Four `<details>` groups "New York: {n} yes · {n} no · {n} didn't vote" (`state_tallies` from the index). The reader's state opens by default (JS); the server renders all four closed.
   - **Rows** are two-line rows (name, linked for the 150 covered members; chip right-aligned) inside one `<table>` per group at every width (§6.4 roll-call row).
   - **District:** printed only for roll calls in the current Congress (119th), from `members.json`, with rows in district order. For earlier Congresses, district maps differ (and changed again in NY for 2024) and former members are not in `members.json`, so rows are sorted by last name and show the state only ("NY").
   - **Uncovered states** are not listed here; the roll-call file has no district.
   - **"All {N} votes, every state"** is a `<details>` whose list is **not** server-rendered. On first open, `site.js` fetches `/api/votes/{chamber}/{c}/{s}/{n}` and renders rows with a name search `<input type="search">` and a "Show: all · yes · no · didn't vote" `<select>` (`<noscript>`: "Open the full list on the roll call source page →").
   - **Per roll call:** the caption "House roll call 295 · September 3, 2026 · Final vote to pass · Passed 237–169" as the block's visible h3 (§8 item 2), repeated as each table's `<caption>` (e.g. "New York — House roll call 295"), and "Roll call source →".
   - **Server rendering rule:** the state groups are rendered for the head roll call and at most one more (the other chamber's decisive vote). Every other roll call on the bill (newest first, collapsed) renders its caption, outcome sentence, tally and state tallies from the index. Its state groups are fetched by `site.js` on first open from `/api/votes/…`. Nothing on this page reads more than two roll-call files per request (118-hr-21 has 57 roll calls).
   - One page-level party toggle in this section's head fills every list's party spans from `?show_party=true` (full names). No per-block toggles.
4. **What it does.**
   - **Displayable summary:** the section-mark provision bullets (`provisions`), then "Summarized by AI from the bill's title, official summary and text excerpt · summaries last updated July 7, 2026. *How we keep it neutral →* · *Something wrong here? Tell us*" (the date is `ai_summaries_updated`, §7.4).
   - **None** (the 60 missing plus the 115 withheld): no bullets and no AI line. The note "We haven't written a plain-English summary for this bill yet; the official summary is below." Then the **first paragraph of the official summary as plain text**: the server picks the summary with `_latest_official_summary` (moved from `sync.py` to `data_service`: prefer the Public Law summary, else the newest by `actionDate`; the old `bill.js` read `summaries[0]`, which is the *oldest*), then strips tags with a stdlib `html.parser` stripper (no markup, no `href`; §10 #10). Then "Show the full official summary" `<details>`, filled by JS through `sanitizeHtml`, with `<noscript>` "Read the full summary on Congress.gov →". When there is no official summary either: the note plus "Congress.gov has the bill text →".
   - Loading copy anywhere JS fills: "Loading summary…", never "Generating…".
5. **Official summary** (when a displayable summary exists): muted serif, collapsed under "Show the official summary", filled by JS through the existing `sanitizeHtml`/`SAFE_TAGS` block, using the same `_latest_official_summary` choice (exposed in the payload as `official_summary`).
6. **Fact box**: a hairline-ruled `<dl>` (beside the headline at ≥880; after "What it does" below 880).
   - **Sponsor:** "Rep. Gary Palmer (AL)", built from the `fullName` prefix ("Rep."/"Sen."), `firstName`, `lastName` and `state`. The `fullName` string itself is never shown, because it carries "[R-AL-6]". Linked only when `sponsors[0].bioguideId` is in `members.json`; otherwise plain text plus "— not in ClearVoting's coverage yet".
   - **Cosponsors** (`cosponsors.count`), **Topic** (`policyArea.name`), **Introduced** (`introducedDate`).
   - **Latest floor vote:** from the index, e.g. "Passed the House · Sep 3, 2026".
   - **Became law:** only when `laws` is non-empty ("Public Law 119-6").
   - **Congress.gov** (`legislationUrl`) and **Share**.
7. **Footer.**

**States.**
- Many amendment roll calls → each a collapsed block after the head roll call, newest first.
- Both chambers → two rendered roll-call blocks under one party toggle. The head outcome is the most recent decisive vote, and the seal reads "Passed both chambers" when both passed.
- No official summary and no AI summary → module 4's minimal state.
- Malformed or unknown URL → 404. `type` in any case → normalized.
- *Defensive only* (unreachable with today's `bills.json`; covered by one synthetic fixture test, not QA'd as a live path): no roll call → modules 2–3 omitted; seal "No final vote yet"; fact box "Latest floor vote: none in our data".
- No-JS: everything except the "your representatives" fill, the party reveal, the "All N votes" list, and state groups beyond the two rendered roll calls.

**Removed and why.** "What People Are Saying"/arguments (C-2), the TOC chip row, the one-chip tag row (`subjects` is a count), the floating Copy Link, "Latest action (2026-06-30): Motion to reconsider laid on the table…", the roll-call donut with 431 in the centre, "Yea/Nay", the 20,000px open table, the fake "procedural" apology with its AI disclaimer, the per-block party toggles, and the sponsor link that 404s (F02, F10, F11, F12, F13, F15, F25, F32, F33).

### 4.5 About (`/about`)

**Purpose.** Who runs this, why, how it is funded, how to reach a human, what the site does not do.

**Fold (both viewports).** Kicker "About", H1 "About ClearVoting", the first paragraph. Static HTML with every section visible at load; no `.animate-*` classes, no observer.

**Sections in order:**
- **Why we built this:** the existing copy, edited for length.
- **Who runs it:** "ClearVoting is maintained by Joseph Garcia, an independent volunteer. To reach him, use *Report an error* at the foot of any page, or the form below."
- **Funding:** "Unfunded and not affiliated with any campaign, party or advocacy group."
- **What we cover:** "California, Florida, New York and Texas today: 150 members and 1,610 bills — every bill that has had a roll-call vote since January 2021. The site is in English only for now." The numbers are server-filled from the same counts as `/api/health`.
- **What we don't do:** no scores, rankings or endorsements; party labels hidden by default; no opinions. The "12 strict rules" sentence and the "what people are saying" sentence are removed; neutrality detail moves to `/methodology`, with a link.
- **Help us improve:** keeps `#about-feedback-cta` (hook).

### 4.6 Methodology & Corrections (`/methodology`)

**Purpose.** The mechanism behind every trust claim, checkable in a minute by a teacher or a sceptic. Every number is server-filled, and no sentence carries a hand-typed date except the corrections log.

**Sections (anchors):**
- **`#sources`:** Congress.gov API (members, bills, House roll calls), Senate.gov XML (Senate roll calls), FEC (money); a weekly automated sync.
- **`#freshness`:** "Roll calls and bills are synced weekly; the edition line on every page shows the last sync and the newest roll call."
- **`#coverage`:** "ClearVoting holds {bills} bills — every bill that has had a roll-call vote since January 2021 in the House or Senate. Bills that never reached a roll-call vote are not in our data." Then "Senate records on member pages include votes on bills, amendments and motions; the {pn} Senate votes on nominations since January 2021 aren't included yet. House records include every House roll call."
- **`#ai`:**
  - What the AI writes: bill one-liners and provisions, from the bill's title, official summary and a text excerpt.
  - What it never touches: votes, tallies, dates, names, outcomes, party.
  - The neutrality rules, copied verbatim from `app/services/ai_summary.py` under "Our rules for neutrality", with no count in prose; a test checks the page's list equals the prompt's.
  - Coverage: "{shown} of {bills} bills have a plain-English summary. {missing} have none yet, and {withheld} summaries are withheld because they did not pass our automated accuracy check; those bills show their official title. Plain-English summaries were last updated {ai_summaries_updated}." Plus: "{audited} summaries were spot-checked by a second AI review."
  - The withdrawal line: "Member summaries are withdrawn until they can be rewritten without stance labels."
  - The arguments line (§7.6).
- **`#recent-votes`:** the selection rule in full, exactly as §4.3 m2 implements it.
- **`#counts`:** "We show roll calls voted as a count, never as a grade, and never rank members by it."
- **`#zip`:** the crosswalk source, licence and retrieval date (from `_source`); the caveat ("shares are land area, not population; PO-box-only and business ZIPs are not in the Census file; a ZIP that crosses a state line is shown with a note"); the ≥5 % rule.
- **`#ballot`:** "Every House seat is on the ballot on November 3, 2026. Of the eight senators we cover, the Texas seat held by John Cornyn is up for its regular election and the Florida seat held by Ashley Moody is up in a special election. Source: senate.gov class lists, retrieved {retrieved}." Written without party letters; `_source.method` is never rendered verbatim.
- **`#corrections`:** "Corrections", a dated `<ol>` newest first, hand-edited, initially "No corrections logged yet."
- **`#report`:** how to report an error (the feedback opener).

### 4.7 Privacy (`/privacy`)

**Sections**, written to match the code:
- **Notify form:** stores your email, your state and the time, in a private Google Sheet. "If the spreadsheet is unavailable, a sign-up may be written to a temporary file on our server, which is deleted when the server restarts."
- **Feedback form:** stores your message, the address of the page you were on (which may include a ZIP you typed), the page type and item id, and the time, in the same Google account.
- **Deletion:** "To have your email deleted, send a request through the feedback form with the address to remove." Requests land in the feedback sheet and are handled by hand.
- **Browser storage:** "We remember where you live, never how you look. Your state and district stay in your browser (`cv-home`) until you press Forget. Whether you revealed party labels is kept only for this browsing session in this tab and is never sent to us."
- **Logs:** "The ZIP you type becomes part of the page address, so it appears in our hosts' request logs along with your IP address. We use those logs only for counts of page paths. Render keeps request logs for a limited period set by its plan; we keep no copy."
- **Processors:** Google (Sheets), Render (hosting), Cloudflare (network).
- **Third-party requests:** "This site makes no third-party requests except member photos from congress.gov, which receives only our site's address as the referrer."
- "No cookies, no analytics scripts."

`notify.py` stops logging the email address (§10 #16), so the privacy page makes no claim about emails in logs.

### 4.8 404

Kicker "Not in this edition", H1 "We don't have that page", and one sentence: "The link may be old, or the bill or member may be outside our four-state coverage." Then the ZIP form ("Find your representatives instead"), the four state links, and a text link to the front page. Navy button, no red. Served with status **404** for unknown paths, unknown `member?id=`, unknown `bill` keys and invalid `state?code=`. No canonical tag. Cache `public, max-age=60`.

---

## 5. Find-your-representatives

### 5.1 The crosswalk data file

- **File:** `data/synced/zip_districts.json` (**new**, sanctioned). Built by `scripts/build_zip_crosswalk.py` (moved from `~/.clearvote-worktrees/tools/data/build_zip_crosswalk.py`, where it already exists) from the four Census files `tab20_cd11920_zcta520_st{06,12,36,48}.txt`. Source: U.S. Census Bureau, 2020 ZCTA ↔ 119th Congressional District relationship files, https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, public domain under 17 U.S.C. § 105. **One change to the script:** it writes a `_source` object; the verified file built on 2026-09-11 has none. The trimming and share logic are unchanged.
- **Format:** `{"_source": {"name": "U.S. Census Bureau 2020 ZCTA to 119th Congressional District relationship files", "url": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/", "retrieved": "2026-09-11", "licence": "Public domain (17 U.S.C. §105)", "share": "land area (AREALAND_PART / AREALAND_ZCTA5_20), covered states only"}, "11201": [{"state": "NY", "district": 10, "share": 0.7216}, {"state": "NY", "district": 7, "share": 0.2784}], "11570": [{"state": "NY", "district": 4, "share": 1.0}], …}`. 6,639 ZCTAs, ≈413 KB raw, sorted, minified. Shares are fractions of the whole ZCTA's land, so a ZCTA that crosses into an uncovered state sums to less than 1.
- **Loader:** `data_service` loads the file once at startup and skips every key starting with `_`.
- **Trimming rule:** the build drops slivers under 1 % of the ZCTA's land (or keeps all when that would leave none).
- **Lookup rule** (`lookup_zip`):
  - `matches` = districts with share ≥ 5 %; `covered_share` = the sum of all listed shares.
  - **No match** when the ZIP is absent or `matches` is empty (88430, 89010, 89060, 89061).
  - **Single** when exactly one match and `covered_share ≥ 0.95`.
  - **Split** when 2–4 matches.
  - Precedence: no match first, then partial, then single/split.
  - **Partial** whenever there is a match and `covered_share < 0.95` (6 ZCTAs, each with one match; the other 4 cross-state ZCTAs are no match; e.g. 73949 at 0.137 TX, 89019 at 0.215 CA, 79922 at 0.829 TX, 97635 at 0.928 CA): rendered like a split (never a 302 to a district, never a `cv-home` write), with the "outside our four states" note.
- Shares are shown to the reader only in the split and partial notes, as whole percentages of *land area*. Counts: 1,226 ZCTAs are split under the rule (1,485 touch more than one district before it).
- **Attribution:** `_source` in the file, `data/SOURCES.md` (URL, licence, retrieval date, build command), `/methodology#zip`.

### 5.2 Endpoint contract

`GET /api/districts/{zip}` (new router `app/routers/districts.py`). Used by the bill page's in-place ZIP form (§4.4 m2) and by tests.

- `zip` is normalized with the §3.2 rule. Anything else → **400** `{"detail": "A ZIP code is five digits"}`.
- **Found:** **200** `{"zip": "11570", "kind": "single|split|partial", "covered_share": 1.0, "matches": [{"state": "NY", "state_name": "New York", "district": 4, "share": 1.0, "member_ids": ["G000602"], "senator_ids": ["G000555", "S000148"]}]}`. `member_ids` (House members with that `stateCode` and `district`) may be empty for a vacancy.
- **No match:** **200** `{"zip": "44101", "kind": "none", "matches": []}`.
- **Headers:** `public, max-age=86400, s-maxage=86400` on 200s (the file changes only on deploy); errors per §9.5.
- **Rate limit:** `slowapi` `60/minute`, keyed per client as fixed in §10 #18.

The `/state` route calls the same in-process `data_service.lookup_zip`.

### 5.3 UI states

| State | Where | What renders |
|---|---|---|
| Single match | `302` → `/state?code=NY&district=4#mine` | "Your representatives" block (2 senators + House member), roster below (collapsed), `cv-home` written from `#mine`. |
| Split ZIP (2–4 districts ≥ 5 %) | `302` → `/state?code=NY&zip=11201` (200) | Senators, then the "spans N districts" note with the land-area wording and the house.gov link, then each district's member row with "This is my district →". |
| Partial (covered share < 0.95) | `302` → `/state?code=TX&zip=73949` (200) | As split, with one or more rows, plus "About 86 % of ZIP 73949's land area is outside California, Florida, New York and Texas; if you live in that part, we don't cover your state yet." No `cv-home` write. |
| Single match, district vacant in `members.json` | `302` → `…&district=20#mine` | Senators; "District 20 — vacant in our data · Tell us if this is wrong". |
| No match (any ZIP not placed: other states, PO-box/business ZIPs, typos) | `200` `/state?zip=44101` | One message: "We couldn't match ZIP 44101 to a congressional district in California, Florida, New York or Texas — the four states ClearVoting covers. If you live in one of them, your ZIP may be a PO-box or business ZIP: choose your state below, or look up your district by street address on house.gov →. Somewhere else? Tell us your state and we'll email you when we add it." Then the four state links, then the notify disclosure (uncovered states only). |
| Malformed input | `200` `/state?zip=abc` | "A ZIP code is five digits." with the form (the field keeps the typed value, `aria-describedby` on the error). |
| ZIP+4 or spaces | normalized | Same as the five-digit ZIP; the redirect target carries only the five digits. |
| Empty submit | HTML `required` blocks it | The server renders the finder page. |
| JS off | — | Identical: the form is a plain GET. |

### 5.4 Remembered selection

- **Key:** `localStorage['cv-home']` = `{"state":"NY","district":4,"savedAt":"2026-09-22"}`.
- **Written only on the reader's own act:**
  - (1) landing on a URL with the `#mine` fragment (the single-match 302 target and every "This is my district →" link);
  - (2) tapping **Remember District 4 as mine** on a district URL;
  - (3) picking a single match, or a split or partial district, in the bill page's in-place ZIP form.
  An address-bar or shared `/state?code=NY&district=4` link without `#mine` never writes. Share never emits `district` or `#mine`.
- **Read by:** the masthead "My representatives" link, the home "Your representatives" block, the Latest Vote per-state line, the member breadcrumb, and the bill "How did your representatives vote?" slot.
- **Visible and revocable:** wherever it is used, the line "Remembered: New York, District 4 · Change · Forget" appears. **Forget** removes the key and re-renders the slot (the ZIP form), keeping focus on its first control. **Change** goes to `/#find`.
- **Principle (C-13):** remember where you live, never how you look. Written on `/privacy`.
- **Party:** `sessionStorage['cv-show-party'] = "1"` while revealed. Every page's toggle reads it, so the reveal carries across pages within this tab's session and is gone in a new session.

### 5.5 Manual paths and the house.gov fallback

- **State + district by hand:** `/state?code=NY` shows the whole House roster in district order, so a reader who knows their district scrolls to it. The URL `/state?code=NY&district=4` is typeable and linkable, and its "Remember" button stores it. No separate district `<select>` is added (the roster is the picker).
- **Street-address fallback:** "Look up your district by street address on house.gov →" (`https://www.house.gov/representatives/find-your-representative`, `rel=noopener`, same tab). It appears in the no-match state and inside every split or partial note. The keyless Census geocoder is deferred (§12).

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
| `--tap` | 44px | | | minimum interactive height and width of standalone controls |
| `--radius-chip` / `--radius-ctl` | 4px / 8px | | | the only radii |

Deleted: `--accent-red`, `--vote-nay`, `--vote-yea`, `--text-dim`, `--bg-*`, the `--text-*` aliases, the hardcoded hover reds, and every literal colour in JS (`vote.js VOTE_COLORS`). JS applies classes; it never sets a colour.

### 6.2 Type scale (the only allowed `font-size` values are these tokens) and roles

| Name | Size | Family/weight | Role |
|---|---|---|---|
| `--t-kicker` | 0.75rem; redefined to 0.8125rem inside the ≤560 block | Inter 700, uppercase, 0.14em tracking | kickers, seals, chip text, nav, masthead tagline |
| `--t-meta` | 0.8rem (12.8px) | Inter 400 | datelines, meta lines, captions, edition line |
| `--t-ui` | 0.875rem | Inter 500 (labels, signal lines, footer links) / 600 (controls) | controls, labels, signal lines, footer links |
| `--t-body` | 1rem | Lora 400 | body, provisions, official summary; also every input, select and textarea (16px, no iOS zoom) |
| `--t-official` | 1.05rem | Lora 500 | an official title standing in for a one-liner, clamped to two lines in lists (`-webkit-line-clamp: 2`) |
| `--t-lede` | 1.125rem | Lora 400 | outcome sentence, deck |
| `--t-row` | 1.15rem | Playfair 700 | row headlines, person names |
| `--t-h3` | 1.35rem | Playfair 700 (Lora 500 for a bill-page official-title H1) | section subheads; the bill-page fallback H1 |
| `--t-h2` | clamp(1.45rem, 3vw, 2rem) | Playfair 700 | section heads |
| `--t-display` | clamp(2rem, 5vw, 3.2rem) | Playfair 700 | page H1s |
| `--t-logo` | clamp(1.6rem, 4.5vw, 2.4rem) | Playfair 800 (italic 600 "Voting") | masthead logo only |

**Rule for official text:** an official title standing in for a one-liner is set in **Lora 500**, so the face itself says "this is the official text, not our translation". It is clamped to two lines in lists, capped at 140 characters in the home lead, capped at 200 characters as the bill H1, and capped at 140 characters as the deck, with the full text in a "Show full title" disclosure.

**Fonts** are self-hosted (§9.6), ten woff2 files: Playfair Display 700, 800, 600 italic; Lora 400, 400 italic, 500; Inter 400, 500, 600, 700. `static/fonts/OFL.txt` (SIL Open Font Licence) is committed with them.

### 6.3 Spacing, rules, breakpoints, masthead

- **Spacing:** a 4px scale only: `--s1` 0.25rem, `--s2` 0.5, `--s3` 0.75, `--s4` 1, `--s6` 1.5, `--s8` 2, `--s10` 2.5, `--s12` 3, `--s16` 4. Section rhythm is identical on every page: 3px double rule, 2.5rem, kicker, 0.5rem, heading, 1.5rem, content. Rows have 1rem vertical padding and a 1px hairline between.
- **Rules, not cards:** no `box-shadow` anywhere except the two interactive cards (state chip and Latest Vote card: `0 1px 2px rgba(17,46,81,.08)`); no nested white containers. Note blocks (split ZIP, coverage, empty summary) are a 3px left navy rule on white.
- **Breakpoints:** exactly two, **560** and **880**, declared once at the end of `site.css` (mobile-first; every override after its base rule) and mirrored in JS via `matchMedia('(min-width: 880px)')`.
  - Tablet (560–879) uses the single-column layouts with 1.5rem gutters; ≥880 gets two-column layouts and the desktop fact strip.
  - Gutters: 16px under 560, 24px up to 880, auto-centred `max-width: 1100px` above.
- **Masthead (compact):**
  - Logo at `--t-logo`; tagline at `--t-kicker`.
  - Nav as one 44px row under the double rule: **Home · My representatives · About** (≤880), and **Home · My representatives · The Record · About** (≥880; "The Record" → `/#record`). No hamburger; the `.hamburger` code path in `feedback.js` stays inert.
  - The edition line (§7.4) sits directly under the nav at `--t-meta`, centred on one line, with its middle segment hidden under 560.
- **Photos:** `<span class="photo" data-initials="CS"><img src="{depiction.imageUrl}" alt="" loading="lazy" width="56" height="56"></span>`. The span's `::before` prints the initials in Playfair on `--rule-soft` *underneath* the image layer; the `img` has `color: transparent`, so a broken image shows no alt glyph. `site.js` removes a failed `<img>` in two ways: a capture-phase `error` listener, and on init a sweep of every `img` where `complete && naturalWidth === 0` (for images that failed before the script ran). Header photos are not lazy. `alt=""` because the name is adjacent text. Tested with a bad URL.

### 6.4 Component inventory

| Component | Spec |
|---|---|
| **Masthead / footer** | As today's markup, compacted (§6.3). Footer links: About · Methodology & Corrections · Privacy · Report an error on this page (`<button id="feedback-open">`, 44px, text). Data line: "Data from Congress.gov and Senate.gov<span id="data-freshness"> · Synced September 5, 2026</span>" (span server-filled; the " · " is inside the span so nothing dangles when it is absent; no JS writes it). Then the credo. |
| **Kicker / deck** | `.kicker` (`--t-kicker`, `--ink-meta`, or `--blue-dim` when linked); `.deck` (`--t-lede`, `--ink-soft`). |
| **Edition line** | `<p class="edition">` with three `<span>`s (§7.4). |
| **Status seal** | `.seal`: Inter 700 uppercase `--t-kicker`, 4px radius, 0.2rem 0.5rem padding. Variants: `.seal--final`, filled navy with white text ("Became law", "Passed both chambers", "Adopted by the House 220–210" for a simple resolution); `.seal--moving`, outlined 1px navy ("Passed the House 237–169" when the other chamber's vote is also needed, "Rejected by the House 189–235", "Debate not ended 52–46 (60 needed)", "No final vote yet"); `.seal--pending`, dashed 1px `--ink-meta` with `--ink-meta` text ("No plain-English summary yet"); `.seal--ballot`, outlined 1px `--ink-meta`, **seat copy only**: "Seat up Nov 3" (rows), "This seat is on the ballot Nov 3, 2026" (member header), "Special election Nov 3" / "Special election for this seat Nov 3, 2026" (Moody). No negative ballot variant exists. |
| **Vote chip** | `.chip`: Inter 700 `--t-kicker`, 4px radius, 1px border in the text colour, tint fill. `.chip--yes` ("Voted yes"); `.chip--no` ("Voted no"); `.chip--nv` ("Didn't vote", `--ink-meta` on paper, dashed border); `.chip--present` ("Present"); `.chip--other` (ink on paper: "Guilty", "Not guilty", "Voted" for Speaker elections); `.chip--absent` ("Not in the House for this vote", `--ink-meta`, dotted border, no fill). Short form `data-short` prints "Yes / No / Didn't vote / Present" inside roll-call tables. Border + text + fill mean it survives greyscale and forced colours. |
| **Tally bar** | `.tally`: a wrapper holding (1) a `role="img"` element with `aria-label="Passed the House: 237 voted yes, 169 voted no, 27 did not vote"`, which is a 10px track (`--rule-soft`) with `--yes` and `--no` segments separated by a 2px paper gap (widths set by server `style` on each segment, allowed because `style-src` keeps `'unsafe-inline'`; segments also carry `data-yes`/`data-no` so tests can read them); and (2) a **sibling** `<p>` with the visible text "237 yes · 169 no" (numbers in `--yes`/`--no`, words in ink) and "· 27 didn't vote" in meta when non-zero. The only place green appears. |
| **Vote row** | `.vote-row`: an `<a href="/bill?…">` covering the row, containing the chip (top-left above the headline on mobile; a left column of 6.5rem at ≥560), the headline (`--t-row` Playfair or `--t-official` Lora 500 fallback), and the meta line (bill code · seal text · date · topic). Used for recent votes, record bill groups, and roster signal lines (without the link when nested). Rows contain no heading elements. |
| **Person row** | `.person`: an `<a href="/member?id=…">` covering the row (except split-ZIP rows, which are a `<div>` with two sibling links). Photo 56px, name (`--t-row`), seat line + seat seal, signal line with chip, empty `<span class="party">`. Carries `data-bioguide`, `data-state` and `data-district`. Minimum height 64px; the whole row is the tap target. |
| **Roll-call table** | One structure at every width: `<table class="rc">` with a `<caption>` (the roll-call caption), `<thead>` with `<th scope="col">Member</th><th scope="col">Vote</th>`, and one row per member: `<th scope="row">` (name, linked for covered members, then "District 4" or "NY" on a second line, then an empty party span) and `<td>` (short chip). Two columns fit at 320 without `display` overrides. The "Rep."/"Sen." prefix is omitted because the caption names the chamber. |
| **Bill row** | `.bill-row`: kicker code, seal, date, headline (Playfair one-liner, or Lora 500 fallback + pending seal). Used by the Record list and the sponsored list. |
| **Button, primary** | `.btn`: navy fill, white text, Inter 600 `--t-ui`, 48px height, 8px radius. Only for form submits: Find my representatives, Notify me, Send (feedback), Filter. |
| **Button, secondary** | `.btn--secondary`: transparent, 1px navy border, navy text, 44px. Share, "This is my district →" (a link styled as a button), Remember District N as mine, Forget. |
| **Party toggle** | `<button class="party-toggle" type="button">Show party labels</button>`, a 44px text control in the action row. On press its text becomes "Hide party labels". **No `aria-pressed`**: the visible label is the state, so the accessible name never contradicts it. One `role=status` sibling (present and empty in the HTML) gets "Party labels shown" / "Party labels hidden". No `aria-label` override. |
| **Form field** | `<label>` visible above (`--t-ui` 600 navy), input at `--t-body` (16px), 48px, 1px `--ink-meta` border, 8px radius, white. Focus = the global ring plus a navy border. Error text in `--error` under the field, with `aria-describedby`. |
| **Disclosure** | Native `<details><summary>` with a 44px summary line, a "+/–" text glyph, and `--t-ui`. |
| **Feedback control** | The footer button "Report an error on this page" on every viewport. At ≥880, an additional fixed 44×44px icon+label button bottom-right with `bottom: calc(1rem + env(safe-area-inset-bottom))`, plus `main { padding-bottom: 72px }` and `html { scroll-padding-bottom: 72px }` so it never covers a CTA or a focused element. Under 880 no floating element exists. |
| **Dialog** | `<dialog id="feedback-modal" aria-labelledby="feedback-title">` containing the existing `#feedback-form`, `<h2 id="feedback-title">Send feedback</h2>`, `<p id="feedback-context">`, `<label for="feedback-message">What did you see?</label>`, the textarea (16px, `autofocus`, so it gets initial focus on `showModal()`), `#feedback-cancel`, `#feedback-submit` (primary), and `<p id="feedback-status" role="status">` (present and empty). `#feedback-overlay` is kept as an empty element for the hook. On success the dialog stays open showing "Thanks — sent." until the reader closes it; `close()` returns focus to the opener. Failure: "We couldn't send that. Please try again in a few minutes." |
| **Sticky strip** (cut-first) | `.strip`: a direct child of `<body>`, `position: fixed; top: 0; left: 0; right: 0`, 44px, paper background, hairline bottom. It holds the name or outcome text at `--t-ui` plus in-page links or Share. Hidden by `transform: translateY(-100%)` + `visibility: hidden` until the header leaves the viewport (`IntersectionObserver`), so showing it changes no layout (no CLS). One per page, member and bill only. |
| **Note block** | `.note`: white, 3px left navy rule, body text; used for the split-ZIP, partial-ZIP, coverage and empty-summary notes. |

### 6.5 Colour semantics

Navy says "this is the record". Blue says "this is a link or where your focus is". Red says "voted No" and nothing else. Green appears only inside the tally bar next to a number. Errors are `--error` text on paper, never red fills. The primary action colour is navy. Nothing else on the site is coloured.

### 6.6 Motion and sticky

- No entrance animation anywhere, and nothing defaults to `opacity:0`. The `.animate-*` classes and the observer in `feedback.js` are deleted.
- Allowed motion: the dialog's native open, `<details>` open, the strip's transform, and status text appearing.
- `@media (prefers-reduced-motion: reduce)` zeroes transitions. `site.js` reads `matchMedia('(prefers-reduced-motion: reduce)')` once and uses `behavior: 'auto'` for any programmatic scroll.
- At most one sticky/fixed content element per page (C-5). Focused elements carry `scroll-margin-top: 56px`, so the strip never covers focus (WCAG 2.4.11).

### 6.7 The fate of the stylesheets

`static/css/site.css` (**new**, target ≤ 30 KB) is written from the components actually rendered by the seven templates and the JS files: mobile-first, tokens in one `:root`, responsive blocks at the end. Each page switches from the old stylesheets to `site.css` in the same commit that rewrites that page (§10.3). `styles.css` (3,848 lines) and `broadsheet.css` (455 lines) are **deleted** in the last commit, once no shell links them, gated by §6.9. Every `outline: none`, low-alpha focus shadow, `.category-tag`, `.hero-*`, `.stagger-children`, dashboard and viz rule goes with them. `@font-face` for the ten self-hosted faces lives at the top of `site.css`.

### 6.8 Print (cut-first)

`@media print { .masthead-nav, .edition, .actions, .strip, dialog, .feedback-btn, .site-footer nav { display: none } body { background: #fff } a::after { content: none } }`, plus `<details>` opened for printing by `site.js` on `beforeprint`. For dark mode and forced colours: `color-scheme: light` is declared, and meaning is carried by text and borders (chip borders, seal outlines), so forced-colours mode keeps it. A full dark theme is deferred.

### 6.9 Definition-of-done checks

**Runners.** Items 1–6 and 8 need a browser. They run at QA from the out-of-repo Playwright setup in `~/.clearvote-worktrees/tools/shots/`, as a gate script `gates.mjs` written next to `shoot.mjs` during the build. They do **not** run in pytest or CI: `tests.yml` installs only `requirements.txt`, with no browser. Items 7, 9 and 10 are pytest or grep checks in the repo, or ops checks. The browser gates run before the stylesheet-retirement commit and at PR.

1. `document.documentElement.scrollWidth <= window.innerWidth` on every template at 320 and 375 (and 768, 1280).
2. No rendered text computes to under 12px. No `font-size` value in `site.css` other than `var(--t-*)` outside the `:root` token block (grep).
3. Every text token is ≥ 4.5:1 on both `--paper` and `--card` (the table in §6.1; a script recomputes it).
4. **Target size.** Every *standalone* control is ≥ 44×44 CSS px: `button`, `input` (except checkbox, whose `<label>` row is 44px), `select`, `summary`, `.vote-row`, `.person`, `.bill-row`, masthead nav links, footer links and buttons, action-row items, state chips, "Roll call source →", "Change", "Forget", "This is my district →", "Remember…", pagination links, and the breadcrumb.
   - Exempt (WCAG 2.5.8 inline exception): `a` inside running text (a `p`, `li` or `dd` sentence), and `[tabindex="-1"]` focus targets.
5. No `box-shadow` outside `.state-link` and `.vote-card`, and no `border-radius` outside 4px/8px.
6. **Fold checks at 375×812.**
   - `/member?id=S000148` and `/member?id=G000602`: the first `.vote-row` top is < 812px.
   - `/bill` for 119-hr-4795, 119-hres-1499 (a 1,063-character title) and 119-hres-354 (1,955 characters): the "How did your representatives vote?" heading top is < 812px.
   - `/`: the Find button bottom is < 600px.
7. No inline `<script>` or handlers, and no `innerHTML` in the diff; every shell has a literal `<title>` and `</head>` (pytest + grep).
8. axe (via Playwright): zero contrast, name/role, heading-order or landmark errors on the seven templates.
9. **TTFB budget** (local, warm, measured with `curl -w %{time_starttransfer}`): `/`, `/state?code=CA`, `/member?id=S000148` and the 118-hr-21 bill page each under 300 ms. App startup, including loading `votes_index.json`, is under 2 s locally. The first request after a cold start does no full scan of the roll-call files (asserted by a test that the render path never opens `votes/*/*.json` except the at most two roll calls of a bill page and the latest vote).
10. **Post-deploy (ops, §12.4):** after Joseph adds the Cloudflare Cache Rule, running `curl -sI` twice on `/state?code=NY`, `/member?id=S000148` and `/api/votes/latest` shows `cf-cache-status: HIT` on the second request. Until this passes, F63 is recorded as unmitigated.

---

## 7. Copy and vocabulary

### 7.1 Glossary and question classes (one table, shared by the Python and JS formatters)

The official term survives only in the roll-call caption's source link. Each question matches the table in order: the first matching pattern wins, parentheticals are read, and a trailing bill reference is ignored. **Class D = decisive** (the vote on the measure itself); **class P = procedural**. `votes_index.json` stores the class per roll call, computed by the same table in `sync.py`. A test runs the table over every real question string and asserts every bill with a D roll call gets a status seal other than "No final vote yet". With this table, 115 bills have no D vote; the old `_build_latest_vote` rule missed 1,144.

| Plain question | Motion noun (for sentences) | Official question | Class |
|---|---|---|---|
| Final vote to pass | — | On Passage; On Passage of the Bill | D |
| Vote to pass (fast-track, needed two-thirds) | — | On (the) Motion to Suspend the Rules and Pass[, as Amended]; … Pass Certain Bills… | D |
| Vote to adopt | — | On Agreeing to the Resolution[, as Amended]; On the Resolution; On the Joint Resolution; On the Concurrent Resolution | D |
| Vote to adopt (fast-track, needed two-thirds) | — | On (the) Motion to Suspend the Rules and Agree[…] | D |
| Vote to accept the other chamber's changes | — | On (the) Motion to [Suspend the Rules and] Concur in the Senate/House Amendment[…]; On the Motion (Motion to Concur in the House Amendment…) | D |
| Vote to override the veto (needed two-thirds) | — | Passage, Objections of the President To The Contrary Notwithstanding; On Overriding the Veto; On the Veto | D |
| Vote to ratify a treaty (needed two-thirds) | — | On the Resolution of Ratification | D |
| Verdict on an article of impeachment (needed two-thirds) | — | Guilty or Not Guilty | D (never a bill seal; shown only in records) |
| Vote on an amendment | an amendment | On Agreeing to the Amendment; On the Amendment | P |
| Vote to end debate (needed 60) | a motion to end debate | On Cloture on the Motion to Proceed; On the Cloture Motion | P |
| Vote to take it up | a motion to take it up | On the Motion to Proceed; Motion to Proceed | P |
| Vote to send it back to committee | a motion to send it back to committee | On Motion to Recommit; On the Motion to Recommit; On Motion to Commit; On Motion to Refer | P |
| Vote to set it aside | a motion to set it aside | On Motion to Table; On the Motion to Table; Table Motion to Reconsider | P |
| Vote to end debate on the rule | a motion to end debate on the rule | On Ordering the Previous Question | P |
| Vote to bring it to the floor | a motion to bring it to the floor | On (the) Motion to Discharge | P |
| Vote to waive a budget rule (needed 60) | a motion to waive a budget rule | On the Motion (Motion to Waive …) | P |
| Vote on a point of order | a point of order | On the Point of Order | P |
| Vote to confirm | — | On the Nomination | P (never in records or seals; index only) |
| Election of the Speaker | — | Election of the Speaker | P |
| Vote to adjourn | a motion to adjourn | On Motion to Adjourn; On the Motion to Adjourn | P |
| Attendance call | — | Call of the House; Call by States; Motion for Attendance | P |
| Procedural vote | a procedural motion | any other question string | P |

**Positions:** Yea/Aye → "Voted yes"; Nay/No → "Voted no"; Not Voting → "Didn't vote"; Present / Present, Giving Live Pair → "Present"; Guilty / Not Guilty → verbatim; a candidate name (Speaker election) → "Voted" (the name only with the party reveal, §4.3).

### 7.2 Result → seal text and outcome phrase (one formatter, Python and JS twins)

**Inputs:** the question class and plain question (§7.1), the `result` string, and `counts` (from the index; House `result` carries no tally). The threshold is read from the Senate result's "(3/5 majority required)" / "(2/3 majority required)", or implied by a House suspension or veto question.

**Class D:**

| Result | Seal | Outcome verb (§7.3) |
|---|---|---|
| Passed / Bill Passed / Joint Resolution Passed / Agreed to / Resolution Agreed to / Concurrent Resolution Agreed to / Motion to Concur Agreed to | "Passed the {House\|Senate} 237–169" (resolutions: "Adopted by the {House\|Senate} 220–210") | "passed it" / "adopted it" / "accepted the {other chamber}'s changes" |
| Failed / Bill Defeated / Joint Resolution Defeated / Resolution Rejected | "Rejected by the {House\|Senate} 189–235", with " (two-thirds needed)" when a suspension or veto threshold applied | "rejected it" |
| Veto override agreed to | "Veto overridden in the {House\|Senate} 290–130" | "voted to override the veto" |
| Veto override failed / Veto Sustained | "Veto override failed 250–170 (two-thirds needed)" | "did not override the veto" |
| Guilty / Not Guilty | "Not guilty 57–43 (two-thirds needed)" | "voted {57} to {43}; {two-thirds} were needed to convict" |

**Class P:**

| Result | Seal | Outcome verb |
|---|---|---|
| Cloture … Agreed to | "Debate ended 89–4" | "voted to end debate" |
| Cloture … Rejected | "Debate not ended 52–46 (60 needed)" | "voted {52} to {46} to end debate; 60 votes were needed, so debate did not end" |
| Amendment Agreed to / Rejected | "Amendment adopted 60–38" / "Amendment rejected 45–53" | "adopted an amendment" / "rejected an amendment" |
| Any other P with Passed / Agreed to / … Agreed to | "Motion agreed to 55–44" | "agreed to {motion noun}" |
| Any other P with Failed / Rejected / Not Sustained | "Motion rejected 189–235" | "rejected {motion noun}" |
| Speaker election | "Speaker elected" | — (records only) |
| Ties | from the result string: "Tied 50–50 — motion failed" / "… agreed to on the Vice President's vote" | — |
| Anything unmatched | the result string before the parenthesis, verbatim | "voted {yeas} to {nays}: {result}" |

The words "blocked", "let the veto stand" and "taken up" never appear (a test greps the formatter output).

**Bill status seal** (bill pages, Record rows, sponsored rows):
1. `laws` non-empty → "Became law".
2. Else, from the most recent class-D roll call per chamber: both passed → "Passed both chambers"; one passed → "Passed the House 237–169" (`.seal--final` when it was the only chamber needed, i.e. a simple resolution, "Adopted by the House 220–210"; otherwise the same text as `.seal--moving`). The seal never predicts the next step ("Senate next" would be false for the 1,121 bills from ended Congresses and for bills the other chamber passed without a roll call). The most recent D vote is rejected → "Rejected by the House 189–235"; when the chambers differ (one passed, the other's latest D vote rejected), the seal states the newer of the two.
3. Else (no D roll call) → "No final vote yet".

There is no "In committee" status: every bill in `bills.json` has a roll call. Tally format everywhere: "237 yes · 169 no" in prose blocks and "237–169" inside seals.

### 7.3 Outcome sentence

- **Class D:** "The {House|Senate} {verb}, {yeas} to {nays}, on {Month D, YYYY}." For example, "The House passed it, 237 to 169, on September 3, 2026."
- **Class P** (used only when a bill has no D roll call, and for extra roll-call blocks): "On {date}, the {House|Senate} {verb}, {yeas} to {nays}." For example, "On August 8, 2026, the Senate rejected a motion to send it back to committee, 45 to 53."
- **Cloture rejected:** "On August 8, 2026, the Senate voted 52 to 46 to end debate; 60 votes were needed, so debate did not end."
- **Ties:** "The Senate tied, 50 to 50, on {date}; the motion {failed|passed on the Vice President's vote}", read from the result string.
- **Dates** go through one helper: long form "September 3, 2026" in sentences, short "Sep 3, 2026" in meta rows. Senate `vote_date` display strings are parsed at sync into ISO dates in the index, so nothing prints raw (no timestamps, no double spaces).

### 7.4 Freshness, the edition line, and ballot copy

`<p class="edition"><span>Data synced September 5, 2026</span><span class="edition-mid"> · Latest roll call September 3</span><span> · Election Day is Tuesday, November 3 — 42 days away</span></p>`.

- **Sources:** `sync_metadata.last_sync`; the newest roll-call date in the index; and a day count computed at render time from today's date in **America/Los_Angeles** (`zoneinfo`), so "today" lasts until California polls close.
- Under 560 the middle span is hidden. On November 3 (Pacific) the third span reads "Election Day is today"; from November 4 it is omitted. Tests cover Nov 2, Nov 3 and Nov 4, including 21:00 and 23:59 Pacific.
- Nothing else on the site mentions the election except the seat seals.
- **Per-module stamps:**
  - Record: "As of {last_sync} · … newest activity first · {n} of the {m} bills below don't have a plain-English summary yet".
  - AI provisions: "Summarized by AI from the bill's title, official summary and text excerpt · summaries last updated {ai_summaries_updated}".
  - Roster: "roster as of {roster_as_of}". Money: "retrieved {last_updated}". Footer: " · Synced {last_sync}" only.
- **`ai_summaries_updated`** (**new** field in `sync_metadata.json`): the date `ai_summaries.json` last changed. It is set once in this PR from `git log -1 --format=%cs -- data/synced/ai_summaries.json` (2026-07-07), and from then on it is written by the sync's AI step whenever it writes that file. All three `sync_metadata.json` writers in `sync.py` (the `--step metadata` branch, the `--ai-only` path and the full sync) today build a fresh dict and would drop the field on the next weekly run, so each must carry the existing value forward unless it rewrote `ai_summaries.json` (§10 #11, with a test).
- "Updated weekly" is gone.

**Ballot copy describes the seat, never the person** (PM decision). `data_service.seat_up_2026(member)` returns `"regular"` for every House member and for senators listed with `kind: "regular"`, `"special"` for senators listed with `kind: "special"`, and `None` otherwise. Copy:
- Rows: "Seat up Nov 3" / "Special election Nov 3".
- Member header: "This seat is on the ballot Nov 3, 2026" / "Special election for this seat Nov 3, 2026".
- Otherwise nothing.

No string pairs "On the ballot" or "Not on the ballot" with a person. A case-sensitive test fails if `\b(On|Not on) the ballot` matches anywhere in `app/render.py`, the shells or `site.js` (the seat copy "This seat is on the ballot" does not match).

### 7.5 Bill codes, names, tenure

- `formatBillCode(type, number)` → "H.R. 4795", "S. 5271", "H.J.Res. 20", "S.J.Res. 11", "H.Con.Res. 108", "S.Con.Res. 5", "H.Res. 1398", "S.Res. 417" (the server's `_BILL_TYPE_LABELS` map, exported to `site.js`).
- `ordinal(119)` → "119th" (11–13 → "th").
- `displayName("Schumer, Charles E.")` → "Charles E. Schumer". `members.json` has no `directOrderName`, so this is the only path.
- Tenure from `terms.item`: one chamber → "In Congress since 2025"; two → "In Congress since 1981 — House 1981–1999, Senate since 1999".
- The record's start is "since {Month YYYY}" of the member's earliest vote, never a fixed "January 2021".
- Vote chips never carry a year; the seat line does.

### 7.6 AI attribution, arguments, errors, party control

- **Attribution** (one per module, at the foot): "Summarized by AI from the bill's title, official summary and text excerpt · summaries last updated {ai_summaries_updated}" (provisions). No AI line appears where no AI text rendered. Never "Generating…"; always "Loading summary…".
- **Arguments:** the module is cut (C-2), and `/ai-summary` no longer returns `arguments` or `direction`. `/methodology#ai` says: "We do not publish arguments for or against a bill. An earlier version showed AI-drafted 'supporters say / critics say' bullets; they were unattributed and have been removed until they can be sourced."
- **Errors own the failure:**
  - Page: "We couldn't load this page right now. Please try again in a moment, or use *Report an error* below to tell us."
  - Notify: "We couldn't save that. Please try again in a few minutes."
  - Feedback: "We couldn't send that. Please try again in a few minutes."
  - Invalid email: "That doesn't look like an email address."
  - All in `role=status`/`aria-describedby` lines, `--error` text. No copy points to an email address (the contact is the feedback form).
- **Party control:** exactly one label pair everywhere, **"Show party labels"** / **"Hide party labels"**. The sentence "Party labels are hidden so the record speaks first." appears once, in the delegation page's action-row meta line. Revealed values are full names: "Democratic", "Republican", "Independent".
- **Election context** is factual and non-partisan (§7.4). No "vote for/against", no "before you vote" imperatives.

### 7.7 Copy checklist (outcome 3)

- Every AI block says what it was written from and carries the summary-set date.
- Every freshness stamp names only what it sits beside.
- Every count names its scope (Senate records exclude nominations; bills are those with a roll call).
- No "procedural" apology exists, and no un-summarized or withheld bill is hidden from a newest-first list.
- No percentage on a list row. No "leans", "mostly in favor", "fights for", or "N of M" stance ratio anywhere, including AI text (tested over every rendered template and every default API payload).
- No "blocked", "let the veto stand" or "taken up".
- Ballot copy never names or implies the person.
- No grey text below `--ink-meta`, and no red outside the vote component.
- "Yea/Nay" appears only in source links.
- Every count comes from `stats` or the index verbatim.
- No page blames Congress.gov for a ClearVoting failure.
- No `{placeholder}` survives in shipped copy.

---

## 8. Accessibility (WCAG 2.2 AA items that apply)

1. **1.1.1** Photos have `alt=""` with adjacent names, and the header photo likewise. Tally bars are `role="img"` + `aria-label`, with their visible text in a sibling (§6.4). No other images.
2. **1.3.1** Landmarks are `header/nav/main/footer`. Lists are `<ul>/<ol>`. Roll-call lists are always `<table>` with `<caption>`, `<th scope="col">` and row-header name cells (§6.4). Rows (vote, person, bill) contain no headings. **Heading outline per template:**
   - home: h1 "See how your representatives vote." → h2 "The latest vote" (card), "Your representatives" (JS), "What Congress voted on", "Most recent plain-English summary", "Browse all bills by topic"
   - state: h1 → h2 "Your senators and House member(s)" (district/zip only), "U.S. Senate", "The House, by district"
   - member: h1 name → h2 "Recent votes", the record heading, "Bills they sponsored that got a floor vote", "Campaign money"
   - bill: h1 headline → h2 "How did your representatives vote?", "The vote, by state" (h3 per roll-call block), "What it does", "Official summary", "About this bill" (fact box, visually a kicker)
   - about / methodology / privacy: h1 → h2 per section
   - 404: h1 only
   - dialog: h2 "Send feedback"
3. **1.3.5** `autocomplete="postal-code"` on ZIP and `autocomplete="email"` on email.
4. **1.4.3 / 1.4.11** Text ≥ 4.5:1 (§6.1). The focus ring is 2px `--blue` (4.76:1 on paper) with a 3px offset. Chip borders are in the text colour, ≥ 4.5:1. Tally segments carry numbers, so segment-to-segment contrast is not the only cue.
5. **1.4.4 / 1.4.10 / 1.4.12** rem-based type, reflow at 320 with no horizontal scroll (§6.9), no fixed heights on text containers.
6. **2.1.1 / 2.1.2** Everything is reachable by keyboard. The dialog traps focus natively, and Esc closes it.
7. **Navigation and focus (2.4.x):**
   - **2.4.1** The skip link is retained. **2.4.2** Titles are unique and server-set.
   - **2.4.3** DOM order = visual order (no CSS reordering of the fold).
   - **2.4.4** Row links have full accessible names from the row's text ("Laura Gillen, District 4, latest final vote: … voted yes"); no "read more".
   - **2.4.6** Headings and labels describe content.
   - **2.4.7** One global `:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible { outline: 2px solid var(--blue); outline-offset: 3px }`, and no `outline: none` anywhere.
   - **2.4.11** `scroll-margin-top: 56px` (strip) and, at ≥880, `html { scroll-padding-bottom: 72px }` (fixed feedback button), so nothing obscures focus.
8. **2.5.3** Visible text = accessible name on every control (no `aria-label` overriding visible text; the party toggle has no `aria-pressed` contradiction, §6.4). **2.5.8** Standalone targets ≥ 44px (§6.9 #4); inline text links use the inline exception.
9. **3.1.1** `lang="en"`. **3.2.3** The same nav on every page. **3.3.1 / 3.3.3** Errors are identified in text next to the field with `aria-describedby`. **3.3.2** Visible labels. **3.3.7** The remembered district avoids redundant entry.
10. **4.1.2 / 4.1.3** `aria-expanded` comes from native `<details>`, and `<dialog>` has native semantics.
    - Status messages: every `role="status"` node is **present and empty in the server HTML**, and JS only sets its `textContent`. Nodes: "Party labels shown/hidden", "Link copied", "Thanks — we'll email you…", "Thanks — sent.", the in-place ZIP result.
    - The record filter result is not a live message: it is a server-rendered count line under the record heading, which receives focus via `#record`.
    - **No `aria-live` on content containers** (F43).
11. **Focus management:** pagination and filters land on the record heading (`tabindex="-1"`, fragment). Notify success moves focus to the status line. The dialog opens with focus on the textarea and returns focus to its opener on close. "Forget" keeps focus on the re-rendered slot's first control. The in-place ZIP result moves focus to the filled slot's heading.
12. **Structure:** reduced motion (§6.6); **no link inside a link** (rows are `<a>`, and source links are siblings); **no `role=link` on divs**.
13. **Scripted QA walkthrough** (definition of done): a keyboard-only pass and a VoiceOver/NVDA pass over `/` → ZIP → `/state` → member → recent vote → bill → roll call → Share → party toggle → feedback dialog, at 375 and 1280.

---

## 9. Reach

### 9.1 Server-rendered content

- **How it works:** `_serve_html(filename, meta, content_html)` replaces a literal `<!--content-->` inside `<main>` with HTML built by `app/render.py` from the same functions the API uses (`get_member_page`, `get_bill_page`, `get_state_overview`, `get_latest_vote`, `get_bills`).
- **Escaping:** f-strings with **one escape helper `h()`** (`html.escape(str(x), quote=True)`) around every interpolated data value. URLs are built only from validated ids or codes plus `urllib.parse.quote`. No template engine is added. A test feeds `<script>alert(1)</script>`, `"><img src=x>`, `&amp;` and `javascript:` strings through every block renderer and asserts none survives unescaped.
- **Rendered blocks:**
  - home: edition line, hero card, the Record, state counts
  - state: header and the whole roster (28–54 rows)
  - member: header, recent votes, the requested record page, sponsored, money
  - bill: story head, the ZIP-form slot, state groups for at most two roll calls, extra roll-call summaries from the index, provisions or the plain-text official paragraph, fact box
  - methodology: the server-filled counts
- **Request path:** SSR routes are plain `def` (not `async def`), so any blocking file read runs in FastAPI's threadpool and never stalls the event loop. The render path reads only in-memory data (`bills.json`, `members.json`, `ai_summaries.json`, `votes_index.json`, state overview files, all loaded at startup) plus one `member_votes` file per member page and at most two roll-call files per bill page.
- **Hydration:** `site.js` detects rendered blocks (`data-ssr="1"`) and never re-fetches what is on the page.

### 9.2 Titles, canonical and `_inject_meta` (server only; no client writes)

- **Titles:**
  - Home: unchanged.
  - Member: "Charles E. Schumer (NY) — Voting Record | ClearVoting".
  - Bill: "H.R. 4795 — {one-liner} | ClearVoting", or "H.R. 4795 — {official title truncated at 70 characters on a word boundary}… | ClearVoting". Today's format "H.R. 1: {official title}" is replaced. The description is the official title (or the one-liner when the title is the headline).
  - `og:title` is the title without " | ClearVoting", capped at 90 characters.
  - State: "New York's Representatives — Voting Records | ClearVoting" (the same with `district`/`zip`; canonical strips them).
  - About, Methodology, Privacy and 404: static.
- **`_inject_meta` changes, listed explicitly:** the literal `<title>` and `</head>` contract is unchanged. `meta` gains:
  - an optional `image` key, which adds `og:image` (absolute URL), `og:image:width`/`height` and `og:image:alt`;
  - `twitter:card` becomes `summary_large_image`;
  - an optional `canonical` key: `False` omits the canonical tag, and the 404 handler passes it (today it passes `url`, so a canonical is emitted);
  - `h1` for the error state.
  Content is injected after meta.
- **Canonical rules** are in §3.3. Params are normalized before lookup and before the canonical string is built.
- **Sitemap:** adds `/methodology` and `/privacy`. Per-URL `lastmod` = the bill's activity date, the member's last vote `date`, the state's `roster_as_of`, and `last_sync` for home and about. `/static/*.html` is served with `X-Robots-Tag: noindex` by a small middleware on `/static/*.html`.

### 9.3 og:image

- **Phase A (in the PR):** four static 1200×630 PNGs in `static/og/`: `default.png` (home, about, trust pages), `member.png`, `bill.png`, `state.png`. They are broadsheet cards (paper ground, masthead wordmark, a one-line descriptor: "Voting record", "How Congress voted", "Your representatives"), made once by `scripts/build_og_cards.py`, run locally with Pillow, and committed. This is a dev-time script; Pillow is **not** added to runtime `requirements.txt`.
- **Phase B (last, cut-first):** `scripts/build_og_cards.py` gains member and state variants (name/state + "Voting record"), pre-rendered at sync into `static/og/member/{id}.png` and `static/og/state/{code}.png` (154 files) by a `weekly-sync.yml` step. `_inject_meta` prefers the per-entity file when it exists. `/static/og/` is served with `public, max-age=86400` (not immutable), because Phase B rewrites files under stable names. Bill cards stay static. No request-path rendering in either phase (C-9).

### 9.4 404s and index hygiene

- Unknown member id, bill key or state code → `HTTPException(404)` → the 404 shell with status 404 and no canonical.
- `/favicon.ico` route (`Cache-Control: public, max-age=31536000`).
- Case-normalized canonicals.
- Soft-404 junk pages disappear.

### 9.5 Cache-Control (reconciled with per-visitor content and freshness, C-8)

The middleware sets headers by status first, then by route:

| Response | Header |
|---|---|
| Any 5xx; any 4xx except 404 (including slowapi's 429 and validation 400/422) | `no-store` |
| 404 | `public, max-age=60` |
| `/static/*` 200 (CSS, JS, fonts) | `public, max-age=31536000, immutable`. Busting uses `?v=`, where `_asset_version` = `RENDER_GIT_COMMIT` (first 12 characters) when set, else a hash of the `static/` file list and mtimes computed at startup, **not** the process start time (Render's free instance restarts after idle, which today changes `?v=` several times a day). |
| `/static/og/*` 200 | `public, max-age=86400` |
| HTML shells 200 (`/`, `/state`, `/member`, `/bill`, trust pages) | `public, max-age=0, s-maxage=600, stale-while-revalidate=3600`. Nothing per-visitor is in the HTML. |
| `/state?zip=` 302 responses | `public, max-age=0, s-maxage=86400` (the lookup is static per deploy) |
| `GET /api/*` 200 (data) | `public, max-age=300, s-maxage=3600, stale-while-revalidate=86400`. `?show_party=true` variants are distinct URLs. |
| `/api/health` | `no-store` (no page calls it any more; §2.5 item 9) |
| `POST /api/notify`, `/api/feedback` | `no-store` |

**Freshness.** The weekly sync commits and redeploys, so the longest a stale shell can live at the edge is 10 minutes after a deploy, against a 7-day cadence (0.1 %). The "as of" stamps are rendered from the same data as the content, so a cached page never claims a freshness it does not have.

**Cold start (F63).** PM decision: no Render plan change in this PR, and cold start is deferred to ops. Cloudflare serves clearvoting.org, but by default it does **not** cache HTML or extensionless JSON whatever `s-maxage` says (the review measured `cf-cache-status: DYNAMIC` everywhere). These headers only take effect after the Cloudflare Cache Rule in §12.4 ops step 1. With the rule in place, cached shells and JSON (including `stale-while-revalidate`) are served during a cold start, but the first request for any uncached URL still waits on the origin. That includes a first visitor's per-ZIP 302, since each ZIP URL is cached separately. F63 is therefore "partly mitigated once the rule is live; first-visit uncached URLs remain exposed; accepted by PM decision 2026-09-22". No user-facing copy depends on caching.

### 9.6 Performance

- **Fonts:** ten self-hosted woff2 files under `static/fonts/`, with `font-display: swap`, `<link rel="preload" as="font">` for Playfair 700, Lora 400 and Inter 400, and `size-adjust`/`ascent-override` fallbacks on Georgia and Arial. The googleapis/gstatic preconnects and CSP allowances are removed.
- **Member pages** never download the full vote file (server pagination, 15 groups).
- **Bill pages** render in one request, reading at most two roll-call files, and lazy-load everything else.
- **Startup** loads `votes_index.json` (one pass, ≈1–2 MB) instead of scanning 5,369 roll-call files (0.74 s + 0.72 s locally today for the two lazy scans, plausibly several times that on Render's free CPU).
- **Reserved space:** none needed (server-rendered first paint). The optional "Your representatives" block on home is inserted below the finder, so it never shifts the fold. The state overview is a one-file read (§10 #7) and cacheable.

---

## 10. Backend touches (every server-side change, with its file and why it is small)

| # | Change | File(s) | Why small |
|---|---|---|---|
| 1 | Crosswalk data file + build script writing `_source`; `data/SOURCES.md` with URL, licence, retrieval date and build command for both sanctioned files | `data/synced/zip_districts.json` (new, rebuilt with `_source`), `scripts/build_zip_crosswalk.py` (moved from `~/.clearvote-worktrees/tools/data/`; adds `_source`), `data/SOURCES.md` (new) | The script exists and is verified; the file is ≈413 KB, loaded once. |
| 2 | Senate seats up in 2026 | `data/synced/senate_2026.json` (new, **already built and verified 2026-09-19**, copied from `~/.clearvote-worktrees/tools/data/`). Schema: `_source` {name, url (senate.gov Class II and Class III pages), retrieved "2026-09-19", scope, method}, `election_day` "2026-11-03", `seats` [{state "TX", bioguideId "C001056", name, class 2, kind "regular"}, {state "FL", bioguideId "M001244", name, class 3, kind "special"}] (`class` is an integer). Only the covered states are listed; House seats are up by definition. Consumed by `data_service.seat_up_2026(member)` (§7.4). `_source.method` contains party letters and is never rendered. | Two rows. |
| 3 | **Votes index** (fixes the missing question and tally, the decisive class, the request-path scans, and the activity date) | `sync.py build_votes_index()`, a new step `--step votes-index` (added to the `--step` choices and run in `weekly-sync.yml` after the vote steps, with its own commit). It writes `data/synced/votes_index.json` (**new**, committed in the PR): `roll_calls` keyed `"house/119_2_00295"` → {`question`, `plain` (§7.1 plain question), `class` "D"/"P", `result`, `counts` {yeas, nays, present, absent}, `date` (ISO), `document`, `bill` "119-hr-4795" or null, `parent` (bill key parsed from `question`) or null, `threshold`, `tallies` {CA, FL, NY, TX: [yes, no, didn't vote]}}; `bills` key → roll-call keys newest first, plus `activity_date`; `latest` (the hero's roll-call key); and `generated_at`. `data_service` loads it once at startup; `validate` checks that every `member_votes` row's key exists in it. | One pass over files the sync already reads; the runtime becomes dict lookups. |
| 4 | ZIP lookup | `app/routers/districts.py` (new, ≈50 lines): `GET /api/districts/{zip}`; `data_service.lookup_zip(zip)` (loads the file at startup, skips `_` keys, normalizes ZIP+4, applies §5.1, attaches `member_ids` and `senator_ids`); the router is included in `main.py`. District counts per state (for vacancies) are derived from the crosswalk at startup. | Dict lookup, no I/O per request. |
| 5 | `/state` with `zip`/`district` | `app/main.py serve_state` (plain `def`): `zip` → normalize → single 302 with `#mine` / split or partial 302 to `code`+`zip` / none renders the not-found state; `code`+`zip` mismatch → 302; invalid `code` → 404; `district` passed to the renderer. | Branching in one route handler. |
| 6 | Seat helper | `data_service.seat_up_2026(member)` (replaces the proposed `on_ballot_2026`). | Five lines. |
| 7 | Precomputed delegation | `sync.py build_state_overview()`, a new step `--step state-overview` (in the `--step` choices; run after `votes-index` in `weekly-sync.yml` with its own commit step). It writes `data/synced/state_overview/{CA,FL,NY,TX}.json`, **generated and committed in this PR** (Render rebuilds from git; there is no by-hand step on the host). Schema: **raw fields only**: `state`, `state_name`, `roster_as_of`, `generated_at`, `senators[]`, `house[]`, `districts_expected`; each member: `bioguideId`, `name`, `district`, `chamber`, `photo`, `terms` (start years per chamber), `partyName`, `latest_vote` {`rc` (index key), `bill_id`, `position`, `date`}. Seals, tenure lines and headlines are formatted at render time by `app/render.py`, so a formatter fix needs no resync. `data_service.get_state_overview(code)` is one file read with an in-memory cache. `members.py` `/{state}/overview` returns it (party stripped unless `show_party=true`), adding per member at response time the render-ready fields `site.js` needs for the home block and the bill slot (display name, seat seal text, and for `latest_vote` the headline, whether it is displayable, bill code, seal text and chip), produced by the same `app/render.py` functions, so the JS never re-derives a question class. The per-request 28-file scan and the `include_stats` branches are deleted. | Reuses member_votes and the index at sync time; the runtime path becomes a file read. |
| 8 | Member page payload and grouped record | `data_service.get_member_page(id, page, topic, position, plain)`: header facts from `members.json` + `stats`; the first-vote month; the nomination count for senators; recent votes by the §4.3 m2 rule; a grouped record page joined to the index; sponsored; money only when totals are complete. `members.py` `/votes` gains `group=bill`, `plain=1`, `policy_area=`, `position=` and honours `limit/offset` (max 50 groups). New `GET /api/members/{id}/page?page=&topic=&position=&plain=`, registered **before** the catch-all `/{state_code}/{district}` route in `members.py` (otherwise `/S000148/page` is captured as a district lookup); a test hits it. `/api/members/detail/{id}?show_party=true` adds `speaker_votes`. **`GET /api/members/{id}/summary` is deleted** (§2.5 A). | One function feeds both the shell and the API; grouping is a single pass over the loaded list plus index lookups. |
| 9 | **Default payloads are allowlisted** (party, scores, arguments) | Serializers in `members.py`, `bills.py` and `votes.py`: bill payloads run `_strip_party` over `sponsors`/`cosponsors` and replace `fullName` with the built name (no `[R-AL-6]`); roll-call payloads drop `members[].party` unless `show_party=true`; `/ai-summary` returns only `one_liner` and `provisions` (and **404** `{"available": false}` when missing or `needs_review`); member vote payloads drop `scorecard`, `direction`, `participation_rate` and `cbo_*`; Speaker candidate names only with `show_party=true`. | Field allowlists at the router boundary. |
| 10 | Bill page payload and summary honesty | `data_service.get_bill_page()`: head, derived status, outcome sentences per roll call, plain questions, `state_tallies` and `covered` positions for the covered members (House by `bioguide_id`, Senate by `last_name`+`state`, as in `sync.py build_member_votes`), the §4.4 m2 reader relation, and `official_summary` chosen by `_latest_official_summary` (moved from `sync.py` into `data_service` and imported by both). `app/render.py strip_tags()` (a stdlib `html.parser.HTMLParser` subclass collecting text only) produces the plain first paragraph, with a test covering `<script>`, `<a href="javascript:…">` and entity payloads. `displayable_summary(bill_id)` = the summary exists and `needs_review` is not true; it is used by every surface. `/votes` gains `outcome`, `plain_question`, `state_tallies` and `covered` per roll call. | Additive fields; the fake apology string is deleted. |
| 11 | Latest vote and bills order | `_build_latest_vote` / `_build_bill_votes_index` are replaced by index reads. `get_latest_vote` adds `one_liner`, `has_summary`, `plain_question`, `outcome`, `state_tallies` and `covered` (one roll-call file read, cached). `get_bills()` defaults to activity-date order, `one_liner` nullable, and `derived_status` per bill. `/api/health` gains `latest_roll_call`, `ai_summaries_updated` and the coverage counts (bills, shown, missing, withheld, audited, nominations excluded). `sync.py`: the three `sync_metadata.json` writers preserve `ai_summaries_updated` and the AI paths set it when they write `ai_summaries.json` (§7.4); `sync_metadata.json` is seeded with 2026-07-07 in this PR. | Sort key change plus computed fields from the index; one carried-forward key in three dicts. |
| 12 | Formatters, Python side | `app/render.py` (new): `h`, `format_bill_code`, `ordinal`, `display_name`, `tenure_line`, `format_date`, `plain_question`, `question_class`, `result_phrase`, `outcome_sentence`, `bill_status`, `seat_seal`, `sponsor_name`, `strip_tags`. A test asserts parity with `site.js` on a fixture list of real question/result strings. | Pure functions. |
| 13 | Server-rendered blocks | `app/render.py` block renderers; `main.py _serve_html` gains the `<!--content-->` replacement; routes for home, state, member, bill and methodology pass content; SSR routes are plain `def`. | String building. |
| 14 | Titles, canonical, `_inject_meta`, 404s, favicon, sitemap, trust routes | `main.py`: `_member_meta`/`_bill_meta`/`_state_meta` per §9.2; the `_inject_meta` changes listed in §9.2; normalization; `HTTPException(404)` on empty lookups; the 404 handler passes `canonical=False`; `/favicon.ico`; `/methodology`, `/privacy`; sitemap entries + per-URL `lastmod`; `X-Robots-Tag` on `/static/*.html`. | Edits inside existing helpers. |
| 15 | Caching, CSP, asset version | `main.py` middleware: Cache-Control by status then route (§9.5); CSP `style-src 'self' 'unsafe-inline'`, `font-src 'self'`, no googleapis/gstatic; `_asset_version` from `RENDER_GIT_COMMIT` or a static-file hash. | Header strings. |
| 16 | Notify hardening | `app/routers/notify.py`: `state` required and validated against the 46 uncovered states + DC (400 otherwise); the JSONL-fallback `logger.warning` no longer prints the email (it logs "signup saved to fallback, state=XX"). Otherwise the Sheets write path is unchanged. | Two edits. |
| 17 | Feedback hooks | `static/js/feedback.js`: `.member-header h1`, `.bill-header h1`; `showModal()`/`close()` with focus return; the success state stays in the dialog; the observer block and `.animate-*` handling are deleted; the `/api/health` freshness fetch (lines 177–191) is deleted, with `#data-freshness` kept; `#feedback-open` is now the footer button (desktop also has the fixed one, with the same handler via class). | The sanctioned change plus deletions. |
| 18 | Rate-limit key | `app/limiter.py`: `key_func` = `CF-Connecting-IP` when present, else the first `X-Forwarded-For` entry, else `request.client.host`. Today every visitor shares the proxy's bucket, so limits are global. Spoofing the header can only evade a limit, which is no worse than today. | One function. |
| 19 | og:image | `_inject_meta` emits the image tags; `scripts/build_og_cards.py` (new, dev-time). Phase B adds a sync step and Pillow to the sync job's install line, never the web runtime. | Phase A is four committed PNGs. |
| 20 | Shells | `static/index.html`, `state.html`, `member.html`, `bill.html`, `about.html` and `404.html` rewritten on the new masthead/footer; `methodology.html` and `privacy.html` new. Each keeps a literal `<title>` and `</head>` and a `<!--content-->` marker. | Templates. |
| 21 | Client | `static/js/site.js` (new, shared): the formatters' twin, chip/row builders via `el()`, share, party toggle, photo fallback + sweep, `cv-home` rules (`#mine`, Remember, Forget), legacy-key cleanup, the in-place ZIP lookup, sticky strip, and focus helpers. `app.js`, `state.js`, `member.js`, `bill.js` and `vote.js` are rewritten as thin enhancers (`bill.js` keeps the `sanitizeHtml`/`SAFE_TAGS` block verbatim, now fed the `official_summary` field). `app.js` reads `?q=` on load. `viz.js` is deleted. | Most rendering moves to the server. |
| 22 | Tests | **Fixtures:** new slices cut from real data under `tests/fixtures/synced/`: S000148 and G000602 `member_votes`; one 117th-Congress House roll call (117_1_00006) and bill; 118-hr-21 with its roll calls (for index coverage, not file reads); a `votes_index.json` built from the fixture roll calls by the real builder; `donations.json` with one complete, one empty-`totals` and one missing entry; one `state_overview/NY.json`; a crosswalk subset (11570, 11201, 73949, 89019, 88430, 97635, 10001) with `_source`; `senate_2026.json`; `sync_metadata.json` with `ai_summaries_updated`; `ai_summaries.json` including one `needs_review` entry and one with `arguments`; and a bill titled with `<b>&"'` characters. `directOrderName` is removed from the fixture `members.json` (real data has none). **New tests:** ZIP lookup (single, split, partial, none, ZIP+4, whitespace, malformed); `/state?zip=` 302 (with `#mine`) / 302 split / 200 none / 404; the `code`/`zip` mismatch 302; the question-class table over every question string in the real `votes/` (skipped when absent, run locally) and in fixtures; formatter parity Python↔JS; outcome and seal strings, including "no 'blocked'"; the recent-votes rule on S000148 (only D questions, Yea/Nay mapping, newest first); member page grouping (S000148: 1,061 votes, 478 null `bill_id`, parent parsed for the fixture's amendment); the Speaker candidate absent from default payloads; the bill reader relation (G000602 on a 117th roll call → "Not in the House for this vote"); an SSR **party-leak test** (no `Democratic|Republican|Independent|\[[RDI]-` in the default HTML of home, state, member and bill, nor in default JSON of every GET endpoint); a payload key test (no `party`, `partyName`, `partyCode`, `arguments`, `direction`, `scorecard`, `participation_rate` in default payloads); SSR escaping over every renderer; `strip_tags` hostile payloads; no "On the ballot"/"Not on the ballot" in render code; no `\blean` or stance ratio in any rendered page; 404 statuses and no canonical on 404; Cache-Control by status (200, 302, 404, 429, 500); feedback selectors resolve; the methodology rule list equals the prompt; `_source.url` and `_source.retrieved` present in both sanctioned files; the countdown at the Nov 2–4 boundaries in America/Los_Angeles; the money sentence only when totals are complete. **Rewritten or deleted:** `test_seo.py` unknown-id tests (200 fallback → 404) and the title format; `test_state_overview.py` aggregate, narrative-snippet and per-request tests (→ file-backed overview); `test_security.py` CSP string (no googleapis, `font-src 'self'`); `test_member_summary.py`/`test_member_narrative_grader.py` endpoint-level tests (the endpoint is deleted; generator unit tests stay); `test_homepage.py` hero/record expectations; `test_routers.py` `/ai-summary` shape. Browser gates run outside CI (§6.9). | Extends the existing pytest suite. |
| 23 | Doc correction | `docs/product-strategy.md:72` and `:169` ("All 50 states + DC", "now all 50 states") corrected to the four covered states. | Two lines. |

### 10.1 Not touched

The Google Sheets write paths (`feedback.py`, `sheets.py`; `notify.py` only as in #16), `sanitizeHtml`, server-side party stripping (extended, not replaced), the sync's data-fetch steps, `render.yaml`, the Dockerfile (the new files live in `data/synced/`), and the AI writer jobs other than stamping `ai_summaries_updated` (§10 #11; the member-summary writer stays in the repo but its output is not served).

### 10.2 New dependencies

None at web runtime. Pillow only in the dev/sync context for og cards.

### 10.3 Schedule, minimum shippable scope, and commit order

**Merge-by: Monday 2026-10-13**, three weeks before Election Day, so server-rendered pages can be crawled and shared before November 3. If the build is behind on **2026-10-06**, the cut-first items below are dropped in order until it fits.

**Minimum shippable scope (must merge):**
- data and endpoints (#1–#11, #16, #18);
- the ZIP → delegation → member → bill spine, server-rendered;
- the trust pages (About, Methodology, Privacy, 404);
- caching headers and titles/canonical/404s;
- the formatters and the tests of #22.

**Cut-first, in this order:**
1. og Phase B.
2. In-place record pagination.
3. The print block.
4. The sticky strip.
5. The desktop fact strip (the fact line already carries its facts).
6. og Phase A (cards stay the current default).

**Commit order.** Each commit leaves every template working. A page's shell, its JS, its render blocks and its switch from the old stylesheets to `site.css` land in the **same** commit; the other pages keep the old stylesheets until their own commit.

1. **Data and endpoints (additive only):** the crosswalk with `_source`, the seats file, SOURCES.md, the votes index step and file, the state overview step and files, `/api/districts`, new payload fields and new endpoints, bills order, health fields, notify and limiter fixes, formatters + render helpers + tests. No page changes, and **no existing field or endpoint that an old page reads is removed or reshaped here**: the old `app.js` reads `include_stats`/`participation_rate`, `state.js` reads `/{state}/overview` and `participation_rate`, `member.js` reads `/summary` and `participation_rate`, `bill.js` reads `arguments`, and `vote.js` reads `members[].party`. Each removal or reshape from #7–#10 lands in the commit that rewrites its consumer: the `include_stats` branch with commit 3 (home), the overview reshape with commit 4, the `/summary` deletion and member-payload trims with commit 6, and the `/ai-summary`, sponsor and roll-call party trims with commit 7. The party-leak and payload-key tests are enabled per endpoint in those same commits.
2. **`site.css` and `site.js` added** (linked by no page yet); the `feedback.js` dialog, freshness deletion and the h1 hooks, **together with** the member and bill header h1 promotion in the old `member.js`/`bill.js` markup (the sanctioned hook change stays in one commit).
3. **Home:** shell, `app.js`, render blocks, `site.css`, compact masthead, footer and edition line.
4. **Delegation:** shell, `state.js`, render blocks, `site.css` (ZIP path end to end).
5. **Trust pages + 404:** About, Methodology, Privacy, 404 (shells, routes, server-filled counts).
6. **Member page:** shell, `member.js`, render blocks, `site.css`.
7. **Bill page:** shell, `bill.js`, `vote.js`, render blocks, `site.css`.
8. **Titles, canonical, 404 statuses, sitemap, caching middleware, fonts, og Phase A.**
9. **Retire `styles.css`/`broadsheet.css` and `viz.js`** (gated by §6.9; by now no shell links them).
10. **Cut-first extras:** og Phase B, then in-place pagination, then the print block and the sticky strip.

---

## 11. Finding coverage

Status: **resolved** = the spec fully addresses the finding; **partial** = addressed with a stated gap; **deferred** = out of this PR (§12).

| Id | Sev | Status | Resolved by | How / gap |
|---|---|---|---|---|
| F01 | P0 | resolved | §4.1 m5, §7.4, §10 #3, #11 | The Record lists the newest bills by activity date (max of latest action and newest roll call) regardless of summary; the lead is the newest bill, with fallback styling; the most recent summarized bill sits after the list with its own label; the stamp counts unsummarized rows instead of claiming a "written through" date. |
| F02 | P0 | resolved | §4.1 m3, §4.4 m4, §10 #9–10 | Structured hero with conditional link text and the pending seal; `/ai-summary` 404 `{available:false}` (also for `needs_review`); a real empty state with a plain-text official paragraph; no bullet, no AI line; "Loading summary…". |
| F03 | P1 | resolved | §3.2, §5 | ZIP form first on every viewport; accepts ZIP+4; Census crosswalk; split, partial and no-match states; two taps. |
| F04 | P1 | resolved | §3.1, §4.2, §5.4 | One canonical delegation page; state chips are links; the homepage renderer retired; senators first, House by district; party toggle; the `document.title` write deleted; the district remembered after a ZIP lookup or a "Remember" tap (not from copied links). |
| F05 | P1 | resolved | §10 #3, #7, §9.1, §9.5 | Precomputed per-state file and votes index; one read; server-rendered; no request-path scans; `def` routes; cacheable once the edge rule exists. |
| F06 | P1 | resolved | §4.2, §2.3 C-1 | Stat boxes, bars, thresholds, metric sorts and Total Votes deleted; rows carry one dated decisive vote; participation is a scoped count on the member header only. |
| F07 | P1 | resolved | §4.3 | Header → recent votes → record; donut, attendance, tiles, topic bars, Service History and tabs cut; at most one fixed strip (cut-first). |
| F08 | P1 | resolved | §4.3 m2, §2.3 C-10, §2.5 B | Recent votes are linked rows with code, seal + tally and date; only decisive votes; chosen without regard to position; the rule printed exactly as implemented; the same row component everywhere; roster rows show one linked decisive vote. |
| F09 | P1 | resolved | §4.3 m4 | Record grouped by bill; extra roll calls in `<details>` with the plain question from the index; other votes collapsed per day with labels from the result prefix and parents read from the question; a single headline slot; the empty title div gone. |
| F10 | P1 | resolved | §4.4 m2–3 | Outcome band; "How did your representatives vote?" from storage or an in-place ZIP lookup; "Not in the House for this vote" distinguished from "Didn't vote"; by-state groups with tallies; the all-votes list lazy with search; covered names linked; two-line rows. |
| F11 | P1 | resolved | §7.1–7.3 | One question-class table, outcome sentence, vote chip and tally format across every page, shared by the Python and JS formatters. |
| F12 | P1 | resolved | §4.4 m1, §9.2 | One-liner as H1 and title; official title as a 140-char deck; a 200-char Lora H1 fallback with "Show full title"; 70-char title fallback; og:title cap. |
| F13 | P1 | resolved | §2.3 C-2, §7.6, §10 #9 | Module cut from pages **and** APIs; methodology states why; vote colours never reused. |
| F14 | P1 | resolved | §6.3, §6.7, §6.9 | Fresh mobile-first stylesheet, overrides after base rules, `minmax(0,1fr)`, scroll-width gate at 320/375. |
| F15 | P1 | resolved | §4.2–4.4, §6.3, §6.7 | Every inner page on the rules/whitespace model; card container rules deleted with the old files; the bill page as one article with a fact box. |
| F16 | P1 | resolved | §6.1 | `--ink-meta` #5F656D (5.45/5.88); `--text-dim` deleted; 12px floor; contrast gate on both grounds. |
| F17 | P1 | resolved | §4.1 m3 | Structured card; fallback title in Lora 500, clamped; never a sentence template. |
| F18 | P1 | resolved | §4.5–4.7, §9.6 | Three real pages; About names Joseph Garcia with the feedback form as contact; Privacy matches the code (processors, logs, fallback file); footer repointed; fonts self-hosted so the privacy claim is true. |
| F19 | P1 | resolved | §9.1 | First blocks (and more) server-rendered on home, state, member and bill; `<title>`/`</head>` kept; escaping via `h()` with a hostile-input test. |
| F20 | P1 | resolved | §9.3, §9.2, §6.4 | og:image in two phases; server-only titles; one Share action with `navigator.share` + clipboard fallback on member, bill and state. |
| F21 | P2 | resolved | §4.1 fold, §6.3 | ZIP field by ≈560px on 375; "My representatives" nav item. |
| F22 | P2 | resolved | §4.5, §6.6, §10 #17 | No entrance animation; observer deleted; static trust pages. |
| F23 | P2 | resolved | §6.4 feedback | No floating element under 880; 44px desktop button with safe-area, reserved padding and scroll-padding; footer opener everywhere. |
| F24 | P2 | resolved | §6.4 dialog | Native `<dialog>`, `aria-labelledby`, label, initial focus, `role=status`, success in the dialog, focus return; ids kept. |
| F25 | P2 | resolved | §6.4 party toggle, §7.6, §5.4 | One label pair; the label is the state (no contradictory `aria-pressed`); no `aria-label` override; one page-level control on bills; full party names; session-scoped. |
| F26 | P2 | resolved | §4.3 m4, §4.3 fold | Counts verbatim from `stats`, with scope (Senate excludes nominations, with the count and a methodology note) and the member's real start month; an "other" bucket; no derived attendance figure. |
| F27 | P2 | resolved | §7.2, §4.3 m4 | Result vocabulary by question class; no empty chips; explicit Amendment/Motion/Speaker labels and empty-text wording; resolutions link via the shared type map. The nomination row is removed (nominations are not in member records). |
| F28 | P2 | resolved | §2.4 declined graft, §4.3 removed | Module cut; topic and position selects on the record instead. |
| F29 | P2 | resolved | §4.3 fold, §2.5 A | Recent votes lead the page; the narrative is withdrawn rather than clamped. |
| F30 | P2 | resolved | §6.6, §6.4 form field | At most one fixed strip; native selects; 16px controls. |
| F31 | P2 | resolved | §7.5 | `formatBillCode` + `ordinal`, Python and JS twins. |
| F32 | P2 | resolved | §7.2, §4.4 m6 | Derived status seal from decisive votes; "Latest floor vote"; one date helper; Senate dates normalized in the index. |
| F33 | P2 | resolved | §4.4 m6 | Sponsor linked only when covered; built name with state, never the `[R-AL-6]` string; cosponsor count. |
| F34 | P2 | resolved | §4.2 | ZIP finder on top; senators first; whole-row tap targets; text on every signal; no bars; no duplicate rows on district URLs. |
| F35 | P2 | resolved | §6.1, §6.5 | Red only in the vote component; navy primaries; a separate `--error`; `--accent-red`/`--vote-nay` deleted. |
| F36 | P2 | resolved | §4.3 m7, §4.2 | Finance bars and participation traffic lights gone; the tally bar has `role=img` + label and sibling visible numbers. |
| F37 | P2 | resolved | §4.1 m5, §2.3 C-3, §4.4 | Official titles off summarized rows; clamped Lora 500 fallback rows; 140/200-char caps with disclosure on the lead and bill page. |
| F38 | P2 | **partial** | §3.1, §12.1 | The offset bug is fixed, and `?q=` is reflected and read on load. Gap: the `/bills` page and `?topic=` URLs are deferred. |
| F39 | P2 | resolved | §4.1 m2, §10 #16 | Required state select (uncovered states only, validated server-side); navy button; privacy line; confirmation echoes the state; honest no-JS copy. |
| F40 | P2 | resolved | §7.4, §4.6 | The AI summary set is dated (`ai_summaries_updated`); edition line; footer separator inside the span and no JS overwrite; the coverage note is computed from data. |
| F41 | P2 | resolved | §7.4, §6.4 seal, §10 #2 | Edition line with the election date; seat seals from the sanctioned list, describing the seat, never the person. |
| F42 | P2 | resolved | §4.1 m2, §5.3, §4.5, §10 #23 | Coverage sentence at the point of choice; one honest not-found state; the English-only line on About; product-strategy.md corrected; uncovered visitors can find their row in "All votes". |
| F43 | P2 | resolved | §8 item 10 | No `aria-live` on containers; status nodes present and empty in the HTML. |
| F44 | P2 | resolved | §8 item 11 | Focus to the record heading on paging and filtering; to the status on notify success; to the textarea in the dialog; `<details>` gives `aria-expanded`; `autocomplete=email`. |
| F45 | P2 | resolved | §8 item 7 | One global `:focus-visible` rule; every `outline:none` deleted. |
| F46 | P2 | resolved | §2.2 #5, §4.3, §4.4, §10.3 commit 2 | `<h1>` on member, bill and about; the two `feedback.js` selectors updated in the same commit. |
| F47 | P2 | resolved | §6.1 `--tap`, §6.9 #4 | 44px for standalone controls, with the inline-link exception defined; no shrinking breakpoint. |
| F48 | P2 | resolved | §4.4 m3, §6.4, §8 item 2 | One `<table>` structure with `<caption>`, `scope` and row headers at every width; no fake-sortable headers (the state table is gone). |
| F49 | P2 | resolved | §6.7, §9.5 | Fresh `site.css`; old files deleted; long-lived cache on `/static` with a stable `?v=`. |
| F50 | P2 | resolved | §6.1 | One token set; JS applies classes only. |
| F51 | P2 | resolved | §6.3 | Two breakpoints declared once; `matchMedia` mirrors them; no dead media blocks. |
| F52 | P2 | resolved | §9.2, §9.4 | Canonical normalization; real 404s without canonical; `/favicon.ico`; `noindex` on `/static/*.html`; per-URL `lastmod`. |
| F53 | P2 | **partial** | §9.5, §12.4 | Cache-Control by status and route, reconciled with per-visitor content (C-8). Gap: edge caching of HTML/JSON needs Joseph's Cloudflare Cache Rule (ops step 1), verified by §6.9 #10. |
| F54 | P2 | resolved | §10 #8, #10, §9.6 | Server pagination (15 groups); one page function; bill payload carries the one-liner and vote summaries; no `limit=2000`; at most two roll-call file reads per bill page. |
| F55 | P2 | resolved | §9.1, §9.6 | Server-rendered first paint; self-hosted woff2 with preload and metric fallbacks; no hidden-then-shown blocks; the strip toggles without layout shift. |
| F56 | P3 | resolved | §4.3 m5, m7 | Sponsored list scoped honestly ("that got a floor vote") with a Congress.gov link to all sponsored legislation; money as one dated sentence only when totals are complete; a meta line otherwise. |
| F57 | P3 | resolved | §6.2 | Named type tokens only (no literals); one family per role; 12px floor; Inter 500 added. |
| F58 | P3 | resolved | §6.4 | Two chip families (seal, vote chip); two radii; one arrow glyph. |
| F59 | P3 | resolved | §6.3 | 4px spacing scale; one section rhythm. |
| F60 | P3 | resolved | §6.6, §8 item 12 | Reduced motion honoured in JS; rows are real `<a>`; no extra controls inside row links; tabs removed. |
| F61 | P3 | resolved | §7.6 | Error copy owns the failure and points only to channels that exist. |
| F62 | P3 | **partial** | §2.5 A, §4.3 m3 | The narratives with "leans" and stance ratios are withdrawn in this PR. Gap: regenerating them without stance labels or the template opener is deferred (§12.1). |
| F63 | P3 | **partial** | §9.5, §12.4 | PM decision: no plan change in this PR. Edge caching partly mitigates once the Cache Rule is live; the first request for an uncached URL (including each first-visit ZIP 302) still meets a cold origin. |

---

## 12. Out of scope, deferred, decisions and ops

### 12.1 Deferred (explicit)

- The `/bills` page with `?topic=`/`?q=` URLs and the topic pill (F38); search zero-results design beyond the existing panel's "No bills matched — try another word".
- Clean-path aliases (`/state/ny`) with 301s.
- Per-bill og:image cards; og Phase B if the schedule slips.
- Address-level lookup via the keyless Census geocoder (the house.gov link covers it).
- A sourced replacement for the arguments module (attributed statements, floor debate, CBO/GAO).
- Regenerated member narratives without stance labels ("mostly/leans"), ratios or the shared template opener, and the member-summary generator's `direction`-based classification (F62).
- Senate nomination votes in member records (a `build_member_votes` change plus a resync).
- Per-summary `generated_at` in `ai_summaries.json` (the dataset date covers this PR).
- Full dark mode; a forced-colours audit beyond the border-carried meaning; a print design beyond §6.8.
- A Spanish-language layer. All UI strings live in one place (the `site.js` string map; shell copy in the shells) and `lang` attributes are set, so an `es` variant is feasible, but 42 days is not enough to translate 1,550 summaries honestly. `/about` says the site is English-only for now.
- A weekly roster-diff step in the sync to catch resignations and special elections (members.json currency). Until then the roster date is printed, and "Wrong person? Report an error" is one tap away.
- Abuse protection beyond the `slowapi` limits (now keyed per client, §10 #18); analytics for the two-tap metric (origin-log 302 counts only).
- Surfacing `audit_grades.json` or per-bill grades (a grade is a score; only counts appear on `/methodology`).
- A Render plan upgrade or an external pinger (PM decision: ops, after this PR).
- Cold-start measurement.

### 12.2 Appendix C gaps — covered or deferred

- **404:** covered (§4.8).
- **House-member pages:** the same template, with the district in the kicker; complete House records ("Every roll call, by bill"); quorum and "Present" rows labelled from the index; server pagination, so the 840 KB file never ships; the money meta line for members without totals; Independents show "Independent" on reveal; short records show fewer recent votes; vacancies render as "vacant in our data".
- **Other states and bad `?code=`:** the same component for CA's 54; invalid or lowercase codes normalized, or 404.
- **Bill data conditions:** covered in §4.4 states: many roll calls, both chambers, no decisive vote (115 bills), no official summary, withheld summary, malformed URL. Note: C1's premise that most bills have no roll call does not hold in the data (0 of 1,610), so the no-roll-call state is defensive only and has a synthetic fixture instead of a QA walkthrough.
- **No-JS:** every page's first block and the ZIP form work without JS; `<noscript>` names what needs it (notify, party labels, remembering).
- **Tablet and 320:** two breakpoints, gutters, gates.
- **Print** (cut-first); **dark mode and forced colours** partly deferred.
- **Search states:** deferred with `/bills`.
- **Notify and feedback failures:** covered (§7.6), with honest copy for a shared-backend outage.
- **Broken photos:** initials block plus an early-failure sweep.
- **Hero edge cases:** §4.1 m3.
- **Keyboard and screen-reader walkthrough:** §8 item 13.
- **Back/forward:** every state is a URL, there is no `pushState`, and bfcache restores re-fill the bill slot.
- **Cold start:** deferred to ops (PM decision); partly mitigated by the edge once configured.
- **Spanish:** deferred, and stated on About.
- **members.json currency:** the roster date is shown; the diff step is deferred.
- **Instrumentation:** origin-log counts only, stated on `/privacy`.
- **`needs_review` flags:** withheld from display and counted (§2.5 C).

### 12.3 Decisions (closed 2026-09-22)

1. **About page identity** (PM decision): "Maintained by Joseph Garcia, an independent volunteer"; contact = the feedback form only; every "email {contact}" string is removed (§4.5, §4.7, §7.6).
2. **Ops spend** (PM decision): no Render plan change in this PR; cold start is deferred to ops (§9.5, F63).
3. **Neutrality calls** (PM decision): the AI arguments module is removed, not relabelled; campaign money is one dated 2024-cycle sentence with an FEC link, for the 71 members with complete totals (§4.3 m7).
4. **Ballot copy** (PM decision): it describes the seat, never the person (§7.4).
5. **Revision calls** (§2.5 A–C): narratives withdrawn; "Recent votes" chosen without regard to position; `needs_review` summaries withheld. These stand unless Joseph overturns them before the plan is written.

### 12.4 Ops steps for Joseph (outside the repo; done at merge)

1. **Cloudflare Cache Rule** for clearvoting.org (Caching → Cache Rules → Create rule):
   - Match: hostname equals `clearvoting.org` AND request method is GET AND (URI path equals `/` OR starts with `/state` OR `/member` OR `/bill` OR `/api/`, OR equals `/about`, `/methodology` or `/privacy`), AND the URI path is not `/api/health`, `/api/notify` or `/api/feedback`.
   - Action: **Eligible for cache**; Edge TTL: **use cache-control header if present**; Browser TTL: **respect origin**; cache key: **include the full query string**.
   - Then verify §6.9 #10.
2. After the first deploy, confirm the weekly sync ran the new `votes-index` and `state-overview` steps and committed their outputs (the Actions log shows both commit steps).
