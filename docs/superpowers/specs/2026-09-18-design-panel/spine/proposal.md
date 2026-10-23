# ClearVoting redesign — Approach "Spine: rebuild around the job"

Written 2026-09-18 (46 days to Election Day). Companion mockups: `home.html` (home + the merged delegation page in its ZIP-resolved, split-ZIP and unknown-ZIP states) and `member.html` (Sen. Charles E. Schumer, S000148). Both open from `file://`, mobile-first at 375px, with layouts at ≥768 and ≥1100.

---

## (a) Thesis

ClearVoting has exactly one job — take a person from *where I live* to *how my people voted* and let them take one more step to *what the bill was* — and every page should be a station on that single spine: ZIP (or state + district) → your two senators and your House member → that member's record → any vote → the bill. The homepage becomes nothing more than the entrance to the spine, the homepage delegation and `/state` collapse into one URL-addressable delegation page, the member page is rebuilt record-first with derived charts cut, and the bill page answers "how did my representatives vote" before anything else. Anything that is not on the spine (participation tiles, donuts, topic bars, tab strips, stat boxes, "what people are saying" in vote colours) is either reduced to a single factual line or removed, because the busy citizen's two clicks are the product and everything else is cost.

---

## (b) Information architecture

### Pages and URLs after the redesign

| URL | Role on the spine | Status |
|---|---|---|
| `/` | Entrance. ZIP field first, four state links second, coverage stated, then the Latest Vote and the Record (newest by date). | Rebuilt |
| `/state?code=NY` | **The one delegation page.** Canonical, shareable, server-rendered from a precomputed per-state file. Accepts `&district=10` (from the crosswalk or a district pick) and `&zip=11201` (renders the split-ZIP choice). Senators as a group, then House by district. Replaces the homepage's in-page delegation renderer. | Merged (homepage renderer retired; `state.js` rewritten on the homepage delegation component) |
| `/member?id=S000148` | The record. Header → summary → key votes → the record grouped by bill. | Rebuilt |
| `/bill?congress=119&type=hr&number=4795` | The bill: what it does, what happened, **how your representatives voted**, then the whole roll call. | Rebuilt (described in §c; no mockup) |
| `/about`, `/methodology`, `/privacy` | Trust pages. Static, visible without JS. | `/about` rewritten; two new static shells |
| `404` | Real 404 for unknown member/bill/state ids, with the spine's entrance (ZIP field) on it. | Rewritten |
| `/bills` (+ `?topic=`) | Bill browse/search. **Deferred** to a follow-up PR; the homepage keeps the existing collapsed browse panel at the very foot (offset bug fixed, nothing else) until then. | Deferred |

No URL shape changes. `/state?code=NY` stays the canonical form (no clean-path alias in this PR, so no 301 work); `?district=` and `?zip=` are additive query params on the same route. The homepage's state cards become `<a href="/state?code=NY">` so the delegation is a page, not a mode.

### The primary path

1. `/` — type ZIP `11570`, press **Find my representatives** (form is a plain `GET /state?zip=11570`, so it works with no JavaScript).
2. Server resolves 11570 → NY-4 (single match, 100 % land share) and 302s to `/state?code=NY&district=4`. The page opens with **Your representatives**: Sen. Gillibrand, Sen. Schumer, Rep. Laura Gillen (District 4). The full New York roster follows below, senators first, House by district.
   - Split ZIP (`11201` → NY-10 72 %, NY-7 28 %): no redirect; `/state?code=NY&zip=11201` renders the two senators plus a "11201 spans two districts — which is yours?" block listing Rep. Goldman (10) and Rep. Velázquez (7) as full member rows, each with a one-tap "This is my district" that sets `district=`. Nobody is blocked: both rows already link to the member pages.
   - Unknown or out-of-coverage ZIP: `/state?zip=44101` renders the four-state grid with "We couldn't place 44101 in New York, Florida, California or Texas — those are the four states ClearVoting covers today," and the notify form (with a state selector). No dead end, no spinner.
3. Tap a member → `/member?id=G000602`. Record-first page; first key vote is visible on the first mobile screen.
4. Tap any vote → `/bill?...`. The bill page opens with the outcome sentence and **Your representatives on this vote** (2 senators + 1 rep, from the remembered delegation), then the full roll call collapsed.
5. Every inner page carries a "Your representatives" link in the masthead nav that goes to the remembered `/state?code=NY&district=4` (or to `/#find` when nothing is remembered). Back on the browser always returns to a real URL.

Success measure (from the review): a first-time visitor reaches their own three members' pages in two clicks or fewer from any entry. On this spine it is ZIP → member = two taps.

---

## (c) Page by page

### Home (`/`)

**For:** getting the reader onto the spine in one action, and proving the promise (a real vote, in plain English, dated honestly) without spending the first screen on it.

**Above the fold — mobile (375×812):** compact masthead (logo, tagline and the three-item nav on one strip, ~120px); kicker "Midterm elections · Tuesday, November 3, 2026"; H1 "See how your representatives vote."; the ZIP form (label, 16px input, navy 48px button "Find my representatives"); the line "Or choose a state: California · Florida · New York · Texas" as four 44px tappable chips. The coverage sentence sits directly under them. Nothing else is on the first screen — the Latest Vote card begins at the fold.

**Above the fold — desktop (≥1100):** two-column lead. Left: kicker, H1, deck, ZIP form, state links, coverage line. Right: the Latest Vote card, structured (kicker, dateline "Sept 3, 2026 · U.S. House · H.R. 4795", headline, tally bar with "237 yes · 169 no", outcome "Passed the House", link). Both columns finish within 700px, so "The Record" head is visible at 1280×800.

**Modules in order:**
1. Masthead (kept verbatim; nav gains "Your representatives" and, on mobile, "Feedback").
2. Lead: election kicker + H1 + deck + **Find my representatives** (ZIP) + state links + coverage line ("Covers New York, Florida, California and Texas today — 150 members, every roll-call vote since 2021"). Notify form for other states lives behind "Somewhere else?" with a required state `<select>` (F39).
3. The Latest Vote — structured card, never a sentence template (F17). Rule (F02): the hero is the most recent roll call whose bill has a `one_liner`, *unless* a newer vote exists, in which case the newer vote is shown with its official title in body type and the link reads "See the vote and official summary →" with the tag "No plain-English summary yet". Today that is H.R. 4795 (passed 237–169, Sept 3).
4. The Record — newest six bills **by latest action date regardless of summary status** (F01), each row with its date, a "Plain-English summary coming" tag when there is no one-liner, the official title clamped to one line, and the section stamp "As of September 5, 2026 · Plain-English summaries current through July 2, 2026". Lead article = the newest bill *with* a summary (H.R. 6500, "Extend no-tax imports from 32 African countries through 2028", voted in the House Sept 1 and the Senate Aug 8), with provisions and "See who voted for it →".
5. Foot: the existing collapsed browse panel (unchanged, offset bug fixed) until `/bills` ships.
6. Footer (kept), with Feedback as a text link and "Report an error on this page".

**Cut and why:** the in-page delegation renderer (`app.js` `loadDelegation`, `selectState`, the party toggle and scroll-to-spinner) — the delegation is now a page (F04, F05, F21); "Voted yes 49 %" micro-bars on roster rows (F06); the sentence-template hero (F17); the 15-line official titles in Record rows (F37); the red notify button (F35/F39).

### Delegation (`/state?code=NY`, with `&district=` / `&zip=`)

**For:** the shareable, searchable home of a state's delegation and the page every ZIP lands on. It is the second station on the spine and the page a Google search for "New York representatives voting record" should hit.

**Above the fold — mobile:** masthead; kicker "New York · 28 members · As of Sept 5, 2026"; H1 "Your representatives" (when `district`/`zip` given) or "New York's representatives"; the ZIP/district strip ("ZIP 11201 · change") as a single 44px line; then the first member row (Sen. Gillibrand) in full: photo, name, seat, "In Congress since 2007", latest plain-English vote with a Yes/No chip. On the split-ZIP state the "11201 spans two districts" block sits between the senators and the House pick, still within the second screen.

**Above the fold — desktop:** the same, with the three "your" rows side by side in a 3-up grid under the header and the roster beginning immediately below.

**Modules in order:**
1. Header: kicker (state · member count · as-of), H1, the ZIP/district line, actions: **Party labels: hidden — show** (shared toggle, `aria-pressed`, session-scoped), **Share**.
2. Your representatives (only when `district`/`zip`): two senator rows + the House row(s). On split ZIPs the House rows are preceded by the disambiguation sentence and each row carries "This is my district" (a link to `&district=N`, which also writes `cv-home` in localStorage via JS). Because those rows carry two actions, they are the one place a member row is not itself an `<a>`: the card is a `<div>` with the name as the link and "This is my district" as a sibling link (no link-inside-link, F60); every other roster row stays a single whole-row `<a>`.
3. Senators (group label "U.S. Senate · both represent all of New York").
4. The House, by district (label "U.S. House · by district"), rows 1–26, each: photo, name, "District 4", "In Congress since 2025", the latest plain-English vote ("Latest vote · Sept 1 · Extend no-tax imports from 32 African countries through 2028 — **Voted yes**"), "On the ballot Nov 3, 2026" as a small factual mark on every House row and on Senate rows whose seat is in the 2026 list.
5. Foot: "Don't know your district? Enter your ZIP" (inline, same form), Congress.gov link, notify form for other states.

**Cut and why:** stat boxes ("60K votes cast"), participation bars and thresholds, support-rate sort, the alphabetical default, the comparison table on desktop, the `document.title` overwrite (F06, F34, F48, F20). Comparison, if any, is by chamber, district and tenure — non-ordinal facts.

**Row signal decision:** the review's roster-row suggestion ("one linked recent key vote per member") turns out, on real data, to be the same bill for all 28 New Yorkers (H.R. 6500, Sept 1 / Aug 8). That is not a flaw: the row reads "on the most recent vote, here is how each of them voted" — Espaillat, Ocasio-Cortez and Tonko voted no, Velázquez did not vote, the rest voted yes — which is the first genuinely differentiating fact the roster has ever shown, and it is the record, not a score.

### Member (`/member?id=S000148`)

**For:** who this person is and how they have actually voted, in plain English, with the first dated vote on the first screen.

**Above the fold — mobile:** masthead (compact); breadcrumb "← Your representatives · New York"; the header — 64px bordered photo, kicker "U.S. Senator · New York", H1 "Charles E. Schumer", one factual line "In Congress since 1981 · House 1981–99, Senate since 1999 · Voted in 1,060 of 1,061 roll calls · Not on the ballot in 2026", and the action row (Party labels: hidden — show · Share · Congress.gov); then the **Key votes** kicker and the first row: "Extend no-tax imports from 32 African countries through 2028 · H.R. 6500 · Passed 90–6 · Aug 8, 2026 · **Voted yes**". The AI summary is *below* key votes on mobile as a three-sentence clamp with "Read more" (F29); the record is on the second screen.

**Above the fold — desktop:** header as a broadsheet byline block (photo left, name and line right, actions right-aligned); two columns beneath: left = Key votes (4 yes + 4 no), right = the summary paragraph with its own date line. The record begins directly under both.

**Modules in order:**
1. Header (as above). One sticky element on mobile only: a 44px strip with the name and "Key votes · Record" in-page links appears after the header scrolls off (F30 resolved: this is the only sticky element; the tab bar and sticky filter row are gone).
2. **Key votes** — 4 supported + 4 opposed, equal by rule (F08's asymmetry), each a real `<a>` to `/bill`, with bill code, outcome ("Passed 90–6", "Blocked — needed 60 votes (47–50)"), date, and a Yes/No chip; caption "Chosen by rule: the most recent final votes on bills with a plain-English summary, spread across topics, equal numbers of yes and no."
3. **Summary** — the narrative, dated "Written June 13, 2026 from the official record; votes after that date are not reflected" (F40), with "Summary generated by AI" and "why we show this →" to `/methodology`.
4. **The record** — grouped by bill, newest first: one row per bill (headline = one-liner, else the official title with the tag "No plain-English summary yet"; never the same string twice), the member's final position, the outcome sentence and date; extra roll calls on the same bill collapsed under "2 procedural votes" (`<details>`); consecutive amendments/motions with no bill (`bill_id` null) collapsed into one dated row "4 amendments and motions · Aug 7–8, 2026" (`<details>` listing each with its result). Controls: one native `<select>` "All topics" (policy_area) and one checkbox "Show amendments and motions" (off by default). Server-side pagination, 15 bills per page, focus moved to the list heading on page change (F44).
5. **Sponsored bills (6)** — short inline list with the shared bill-code formatter and a plain "Last action" line.
6. **Campaign finance** — one line: "Campaign finance is reported to the FEC; see Schumer's filings on FEC.gov →" (link built from `fec_candidate_id`). No module (see §h on the F07/F56 contradiction).
7. Footer with "Report an error on this page".

**Cut and why:** the donut, the attendance ring and bar, the three stat tiles, the six topic bars ("What They Fight For"), the Service History card, the tab bar, the second sticky bar, the sticky filter row, "Copy Link" pill, the client-side recomputation of key bills and stats (F07, F26, F28, F30, F54). Participation survives as one factual clause using `stats.total_votes` and `stats.not_voting_count` verbatim (F26). "Votes by topic" is not carried: the direction model cannot be explained in one line without becoming an opinion (F28 says cut if it cannot be made neutral).

### Bill (`/bill?congress=119&type=hr&number=4795`) — described, not mocked

**For:** "Congress just voted on X — what does it do, and how did MY representatives vote?"

**Above the fold — mobile:** kicker "H.R. 4795 · 119th Congress · Passed the House"; H1 = one-liner when it exists, else the official title ("Protect Economic and Academic Freedom Act of 2026"); deck = the outcome sentence "The House passed it, 237 to 169, on September 3, 2026"; then **Your representatives on this vote** — for a remembered NY-4 reader: Rep. Laura Gillen — Voted yes/no (from the House vote file, by `bioguide_id`), and for a Senate vote the two senators; when nothing is remembered, the same slot holds the ZIP field ("Enter your ZIP to see how your representatives voted"). So the spine can be entered from a shared bill link.

**Modules in order:** kicker/H1/deck; Your representatives on this vote; **What it does** — provisions with the section-mark, or the honest empty state (no bullet, no AI disclaimer): "We haven't written a plain-English summary for this bill yet." followed by the first paragraph of the official summary promoted into the primary slot (for H.R. 4795: the bill prohibits colleges that take federal student aid from engaging in boycotts against Israel), with "Show full official summary"; byline row: sponsor (linked only if covered — Rep. Virginia Foxx (NC) is plain text "not in ClearVoting's coverage yet"), "1 cosponsor", policy area "Education", Share; **The votes** — one block per roll call with the plain outcome sentence, the mapped question ("Final vote to pass"), tally bar, then "All 406 votes" as a collapsed two-line list (name + state, chip right) with a state filter and name search, covered members linked; **Possible arguments** — relabelled "Possible arguments, drafted by AI — not attributed to anyone", collapsed by default, neutral rule colours, prefixes stripped at render; Congress.gov link.

**Cut and why:** the TOC chip row, the single-chip tag row, the floating Copy Link, "What People Are Saying" as a headline, the 20,000px open table, "Latest action" with the housekeeping motion (F10, F11, F12, F13, F15, F32, F33).

### About / Methodology / Privacy (+ 404)

**About:** who (Joseph Garcia, named, with contact), why, funding (volunteer, unfunded), what the site does not do. No animation; every section visible at load (F22). **Methodology:** sources and sync cadence, what AI writes and what it never touches, the neutrality rules rendered from the prompt (or with the number dropped), coverage gaps stated as facts ("60 of 1,610 bills have no plain-English summary; the summary writer has been paused since July 2, 2026"), the key-votes selection rule, the "possible arguments" provenance, a dated corrections log. **Privacy:** what the notify and feedback forms store (email, state, message, page URL) in a Google Sheet, retention, no analytics, fonts self-hosted so "no third-party requests" is true. Footer repointed. **404:** kicker "Not found", the sentence "That page doesn't exist — it may have moved, or the id in the link is wrong.", then the ZIP form ("Find your representatives instead") and the four state links, in navy, not red. Unknown `/member?id=`, `/bill?…` and `/state?code=` return this page with a real 404 status.

---

## (d) Visual system decisions

The broadsheet language stays (Playfair Display, Lora, Inter; navy ink on paper; double rules and hairlines; kickers). What changes is that it becomes one system across all templates.

**Typography roles (8 steps, the only allowed sizes):** kicker 0.75rem Inter 700 caps (floor; the masthead tagline and law seal move up to it) · meta 0.8rem Inter · ui 0.875rem Inter · body 1rem Lora · lede 1.125rem Lora · h3 1.35rem Playfair · h2 clamp(1.45rem, 3vw, 2rem) Playfair · display clamp(2rem, 5vw, 3.2rem) Playfair. One family per role. 12px is the floor for any text, 13px for meta on mobile. The member name, bill headline and About title become `<h1>` (feedback.js selectors updated in the same commit — the sanctioned change).

**Colour semantics (one `:root`, aliases deleted):** `--paper #F5F6FA` · `--card #FFFFFF` · `--ink #1B1B1B` · `--ink-soft #5B616B` · `--ink-meta #5F656D` (5.45:1 on paper; replaces both `--text-dim` and the old `--ink-meta`) · `--navy #112E51` · `--blue #0071BC` · `--blue-dim #205493` · `--yes #2E7D3A` · `--no #B3261E` · `--rule #D6D7D9` · `--rule-soft #E8E8E8` · `--error #8A1C1C` (distinct from `--no`). Red/green appear **only** inside the vote component (chip and tally bar). Primary buttons are navy; links are blue; the notify and feedback submit buttons are navy. `--accent-red`, `--vote-nay` and the hardcoded hover reds are gone. JS never carries a colour: it applies classes.

**Rules, not cards:** sections are separated by a 3px double rule (top-level) or a 1px hairline (rows). No nested white cards, no box-shadow except on the two interactive card types that survive: the state link card and the Latest Vote card. Member rows, key-vote rows and record rows are hairline-separated blocks on the paper ground with the whole row as the link target.

**Two chips only:** status chip (Inter 0.75rem caps, 4px radius: "Passed the House", "No plain-English summary yet", "On the ballot Nov 3") and the vote chip (Inter 0.8rem 700, 4px radius, `--yes`/`--no` fill at 12 % with the text in the full colour, always the words "Voted yes" / "Voted no" / "Didn't vote" / "Present"). The topic pill is deferred with `/bills`. One arrow convention (→) for onward links.

**Spacing:** 4px-based scale (0.25 / 0.5 / 0.75 / 1 / 1.5 / 2 / 3 / 4 rem). Section rhythm is identical on every page: double rule, 2.5rem, kicker, 0.5rem, heading, 1.5rem, content.

**Breakpoints:** one set, 560 / 880 / 1100, declared once in a fresh `static/css/site.css` written mobile-first with responsive rules co-located after each component. `styles.css` and `broadsheet.css` are retired together (F49, F51), not pruned.

**Touch targets:** one token `--tap: 44px` applied to nav links, chips that are controls, the party toggle, share, pagination, footer links, `<details>` summaries and the ZIP button. Inputs, selects and textareas are 16px.

**The feedback control:** on viewports under 880px there is no floating pill; Feedback lives in the masthead nav and in the footer as "Report an error on this page", plus an inline text link under each AI-written block ("Something wrong here? Tell us"). On desktop it is a 44px icon+label button fixed bottom-right with `env(safe-area-inset-bottom)`, and `main` reserves 72px of bottom padding so it never covers a CTA. The panel becomes a native `<dialog>` with `aria-labelledby`, a real `<label>`, `role=status` on the status line, and focus returned to the opener; all `#feedback-*` ids stay.

**Focus:** one global rule `:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible { outline: 2px solid var(--blue); outline-offset: 3px }` and every `outline: none` removed.

**Photos:** every member photo is a fixed-size box with the member's initials in Playfair on `--rule-soft` as the background, so a 404 from congress.gov leaves a legible monogram, not a broken icon; `alt` is the name, `loading=lazy` below the first row.

---

## (e) Finding coverage

### P0 and P1 (F01–F20)

| Id | How this approach resolves it |
|---|---|
| F01 | The Record lists newest bills by latest action date regardless of summary; designed fallback row (bill code, official title clamped, "Plain-English summary coming" tag); section stamp "As of Sept 5, 2026 · summaries current through July 2, 2026"; per-row dates. |
| F02 | Hero rule: newest vote wins; without a one-liner the link reads "See the vote and official summary →" and is tagged "No plain-English summary yet". `/ai-summary` returns `{available:false}` (404 semantics) and the bill page renders a real empty state: no section-mark bullet, no AI disclaimer, the first paragraph of the official summary promoted; "Loading summary…" copy. |
| F03 | ZIP field is the first control on every viewport, backed by the Census ZCTA→CD119 crosswalk (flagged new public data file), feeding `/state?code=&district=`; split ZIPs render the choice block; unknown ZIPs land on a designed state. Two taps from ZIP to a member page. |
| F04 | One delegation surface: `/state?code=NY` is canonical; homepage state cards are links; the homepage renderer is retired; senators-first then House by district; one vocabulary; party toggle present; `document.title` overwrite deleted. |
| F05 | `/state` served from a precomputed `data/synced/state_overview/{code}.json` written at sync time (one file read); the shell server-renders the roster so nothing spins; Cache-Control lets Cloudflare absorb repeats. |
| F06 | Stat boxes, Total Votes column, participation bars and thresholds, and metric sorts are all deleted; rows show photo, name, seat, tenure in words and the latest plain-English vote with the member's position. Participation appears only as a factual clause on the member header. |
| F07 | Member page order is header → key votes → summary → record; the donut, attendance, stat tiles, topic bars, Service History card and tabs are cut; tenure is one line computed from all `terms` ("House 1981–99, Senate since 1999"); one sticky name strip on mobile only. |
| F08 | Key votes are real links with bill code, outcome and date; 4 yes + 4 no by rule with the rule stated; the same row component is used for the record and for roster rows on `/state`. |
| F09 | Record grouped by bill; procedural votes collapsed under `<details>`; no-`bill_id` amendments collapsed into one dated group row; single headline slot (one-liner, else official title + tag) so no string repeats; default view is bills with the amendments toggle off. |
| F10 | Bill page leads with the outcome sentence and "Your representatives on this vote" from the remembered delegation (or a ZIP field in that slot); full roll call collapsed with state filter and name search; covered members linked; two-line list on mobile, never a sideways table. |
| F11 | One outcome-sentence generator ("The House passed it, 237 to 169, on September 3, 2026"), one question map ("On Passage" → "Final vote to pass"; cloture → "Vote to end debate (needed 60)"), one vote chip with "Voted yes/no/Didn't vote", one tally format "237 yes · 169 no" shared by home, delegation, member and bill. |
| F12 | Bill H1 = one-liner when present, official title demoted to the deck ("Officially: …"); server `<title>` = "H.R. 4795 — {one-liner}" or the official title truncated at ~70 chars on a word boundary; og:title under 90 chars; same formatter for page, tab and share card. |
| F13 | Module renamed "Possible arguments, drafted by AI — not attributed to anyone", disclaimer at the top, collapsed by default, neutral rule colours, "Supporters say/Critics say" prefixes stripped at render, About/Methodology describe it truthfully. (Kept rather than dropped — see §h.) |
| F14 | Fresh mobile-first stylesheet with responsive rules co-located after each component; no fixed-width stat rows exist any more; a `scrollWidth <= innerWidth` smoke check at 320 and 375 is in the definition of done. |
| F15 | Member, delegation and bill bodies rebuilt on the homepage containment model (rules, kickers, paper ground, no nested cards, no shadows except the two interactive cards); the bill page composed as one article; `.glance-card`/`.viz-section`/`.bill-section`/`.state-stat`/`.comparison-table`/`.mobile-card` deleted with the old stylesheet. |
| F16 | Single `--ink-meta #5F656D` (5.45:1 on paper); `--text-dim` deleted as a text colour; 12.8px floor for meta text; contrast checked against both paper and card in the DoD. |
| F17 | Hero is a structured card (chamber, date, result, tally, bill code, headline slot) — never a sentence template; official title only in body type, clamped. |
| F18 | Three real pages: `/about` (named maintainer, contact, funding), `/methodology` (sources, cadence, rules, AI scope, coverage gaps, corrections log), `/privacy` (what is stored, where, how long, no third-party requests once fonts are self-hosted). Footer repointed. |
| F19 | The FastAPI shell routes render the first content block as real HTML: home (hero card, Record rows, state counts), delegation (whole roster), member (header, key votes, summary, first 15 record rows), bill (kicker, H1, outcome sentence, provisions or empty state). JS enhances (party toggle, pagination, share, delegation memory). Literal `<title>` and `</head>` kept in every shell. |
| F20 | `og:image` on every page: member and state cards pre-rendered at sync time into `static/og/`, bill cards rendered on demand behind immutable caching, one static default; `twitter:card=summary_large_image`. The three `document.title` writes are deleted. One **Share** action in each page header (navigator.share → clipboard fallback with a visible "Link copied" status) on member, bill and delegation pages, always sharing the canonical URL. |

### P2/P3 this approach also resolves

F21 (ZIP/state on the first mobile screen; "Your representatives" nav item) · F22 (no entrance animation; observer deleted) · F23 (no floating pill under 880px; 44px desktop button; reserved bottom padding) · F24 (`<dialog>` feedback with label, status role, focus return) · F25 (one shared toggle "Party labels: hidden — show", `aria-pressed`, session-scoped, single page-level control on bills, full party names when revealed) · F26 (counts verbatim from `stats`; "Other" bucket; no derived attendance figure) · F27 (result vocabulary normalised; no empty chips; explicit "Amendment"/"Motion" labels; clickability from the shared typeMap so resolutions link) · F28 (module cut) · F29 (summary below key votes, clamped, body size) · F30 (one sticky strip; native selects; 16px inputs) · F31 (`formatBillCode` shared, Congress.gov form, ordinal helper) · F32 (derived status chip replaces "Latest action"; one date helper) · F33 (sponsors linked only when covered; cosponsor count shown) · F34 (delegation mobile rows: whole row tappable, labelled text, senators first, ZIP finder on top) · F35 (red/green only in the vote component; navy primaries; separate `--error`) · F36 (finance bars cut; participation traffic-lights cut; any remaining bar has `role=img` + label) · F37 (Record rows clamp the official title to one line) · F39 (state selector in the notify form; navy button; privacy line) · F40 (each AI block dated; footer separator rendered only with a value; coverage note) · F41 (election kicker on home; "On the ballot Nov 3, 2026" marks from the Senate-2026 list, flagged new data) · F42 (coverage sentence at the point of choice; unknown-ZIP state explains coverage) · F43 (aria-live moved to one status line per section) · F44 (focus management on pagination and notify success; `aria-expanded`; `autocomplete=email`) · F45 (one global focus rule) · F46 (`<h1>` on member/bill/about; feedback.js selectors updated) · F47 (44px token everywhere; no shrinking breakpoints) · F48 (roll-call list uses `<th scope>`/captions when a table is kept at desktop; sort affordances removed) · F49/F50/F51 (fresh single stylesheet, one token set, one breakpoint set) · F52 (real 404s, canonical normalisation, `/favicon.ico` route, per-URL lastmod) · F53 (Cache-Control on static, API and shells) · F54 (one `/api/members/{id}/page` payload; server-side pagination with `limit=15`; bill endpoint carries one-liner and vote summaries) · F55 (server-rendered first paint; self-hosted woff2 with preload and size-adjust fallback) · F56 (sponsored bills inline; finance reduced to one FEC line) · F57/F58/F59 (scale, two chips, spacing scale) · F60 (reduced-motion respected in JS; rows are real `<a>`; tabs removed) · F61 (error copy owns the failure) · F62 (narrative dated and demoted below key votes; generation-time fix deferred).

**Not addressed here:** F38 (topic URLs and `/bills`) — deferred with the browse page; only the offset bug is fixed. F63 (Render plan / pinger) — an ops decision for Joseph, noted in §g, not a design item.

---

## (f) Data and backend touches (small, named)

| # | Touch | File(s) |
|---|---|---|
| 1 | **ZIP crosswalk data file** `data/zip_districts.json` — `{"11201":[{"state":"NY","district":10,"share":0.72},{"state":"NY","district":7,"share":0.28}]}`, ≥5 % shares only, generated from the Census 2020 ZCTA↔CD119 relationship files (public domain, 17 U.S.C. §105), with a `_source` block naming the files and date. The build script moves from `tools/data/build_zip_crosswalk.py` into `scripts/build_zip_crosswalk.py`. | `data/zip_districts.json` (new), `scripts/build_zip_crosswalk.py` (new) |
| 2 | **Senate seats up in 2026** `data/senate_2026.json` — `{"source":"…senate.gov class list…","seats":[{"state":"FL","bioguide":"…"},…]}`; only used for the "On the ballot" mark. | `data/senate_2026.json` (new) |
| 3 | **ZIP endpoint** `GET /api/lookup/zip/{zip}` → `{zip, matches:[…]}` or `{zip, matches:[]}`; and `/state?zip=` handling in the shell route: single match → 302 to `?code=&district=`; several → render the choice; none → render the unknown state. | `app/routers/lookup.py` (new), `app/main.py` (`serve_state`) |
| 4 | **Precomputed delegation** `data/synced/state_overview/{code}.json` written at the end of the weekly sync (members with tenure line, latest plain-English vote + position, ballot mark); `get_state_overview` becomes a single file read; the old per-request 28-file scan is deleted. | `scripts/` sync entry that `weekly-sync.yml` calls (add a `build_state_overview()` step), `app/services/data_service.py`, `app/routers/members.py` |
| 5 | **Member page payload** `GET /api/members/{id}/page` → header facts, key votes (4+4 by rule, computed server-side with the existing picker logic), summary + `generated_at`, first 15 record rows *grouped by bill*, sponsored bills; `/votes` gains `group=bill`, `procedural=0/1`, `policy_area=` and honours `limit/offset`. | `app/routers/members.py`, `app/services/data_service.py` |
| 6 | **Record fallback + freshness** — `/api/bills` sorted by max(latestAction, last roll-call date) with `one_liner` nullable; `summarized_only` used only for the lead article; `summaries_through` (max `generated_at`) added to `/api/health` for the coverage stamp. | `app/services/data_service.py`, `app/routers/bills.py`, `app/main.py` health |
| 7 | **AI summary honesty** — `/ai-summary` returns `{available:false}` with 404 when missing; bill endpoint returns `one_liner`, `derived_status` (from the votes index) and per-roll-call outcome sentences. | `app/routers/bills.py`, `app/services/data_service.py` |
| 8 | **Server-rendered content block** — `_render_*_block()` helpers produce escaped HTML (`html.escape`, no templates engine needed) inserted at a `<!-- ssr -->` marker inside `<main>` by `_serve_html`; `_inject_meta` unchanged. | `app/main.py` |
| 9 | **Titles, canonical, 404s** — title rules per §e F12/F20; params normalised before canonical; unknown ids raise 404 → the new 404 shell; `/favicon.ico` route. | `app/main.py` |
| 10 | **og:image** — `scripts/build_og_cards.py` (Pillow, added to `requirements.txt`) renders 150 member + 4 state + 1 default PNG at sync; `GET /og/bill/{c}/{t}/{n}.png` renders on demand with `Cache-Control: public, max-age=31536000, immutable`. | `scripts/build_og_cards.py` (new), `app/routers/og.py` (new), `app/main.py` meta |
| 11 | **Caching** — `Cache-Control: public, max-age=31536000, immutable` on `/static`; `public, max-age=3600, stale-while-revalidate=86400` on `GET /api/*` and the HTML shells (shells carry nothing per-visitor — see §h). | `app/main.py` middleware |
| 12 | **Fonts self-hosted** — six woff2 files under `static/fonts/`, `@font-face` in `site.css`, googleapis removed from CSP. | `static/fonts/` (new), `static/css/site.css`, `app/main.py` CSP |
| 13 | **Delegation memory** — `cv-home` localStorage key `{state, district}` written by the delegation page when `district` is present; read by the nav link and the bill page's "Your representatives on this vote". `cv-show-party` moves to `sessionStorage`. | `static/js/site.js` (new shared file: formatBillCode, outcome sentence, vote chip, share, party toggle), `bill.js`, `state.js` |

Everything is flat JSON, in-process, no framework, no build step, CSP unchanged except removing the Google Fonts origin. No `innerHTML`; the bill page's `sanitizeHtml`/`SAFE_TAGS` block stays for the official summary.

---

## (g) Scope, risks, deferrals

| Page / piece | Size | Notes |
|---|---|---|
| Home | **M** | New lead + ZIP form, structured hero, Record fallback rows, notify state select; delegation renderer removed. |
| Delegation (`/state`) | **L** | Merged surface, precomputed file, server-rendered roster, ZIP/split/unknown states, share, party toggle. |
| Member | **L** | Record-first rebuild, grouping, server pagination, page payload, one sticky strip. |
| Bill | **L** | Outcome sentence, "your representatives" block, empty state, collapsed roll call with filter, arguments relabel. |
| About / Methodology / Privacy / 404 | **S** | Static shells; copy is the work. |
| Shared system (`site.css`, `site.js`, tokens, fonts, feedback dialog) | **M** | Written once, used by all pages. |
| Backend (rows 1–13 above) | **M** | Mostly additive; the risky part is server rendering inside `_serve_html`. |
| **Total** | **~3 L + 3 M + 1 S** — roughly four to five focused weeks for one engineer-agent loop, which fits before Nov 3 only if the deferrals below hold. |

**Risks.** (1) The ZCTA≠USPS-ZIP gap: PO-box ZIPs and new ZIPs miss the crosswalk — mitigated by the designed unknown-ZIP state and, as a follow-up, the keyless Census geocoder for street addresses. (2) Land-area share as the split heuristic can list a district with few residents — mitigated by showing every ≥5 % district as a full member row rather than guessing. (3) Server rendering doubles the places a data bug can show — mitigated by rendering from the same precomputed files the API serves. (4) members.json currency (resignations/special elections) is unverified — the delegation page adds an "As of {updateDate}" line and a "Wrong person? Tell us" link, and the sync script should diff the roster weekly (small follow-up). (5) The record-first member page depends on the server grouping being right for the 478 no-`bill_id` amendments — the amendments group row is the safety net.

**Deferred to a follow-up PR:** `/bills` with `?topic=` URLs and the topic pill (F38); address-level geocoder fallback; the Spanish-language layer (see §h, gaps); dark-mode and print stylesheets beyond the sane defaults (`color-scheme: light`, `@media print` hides chrome); the ops decision on Render's plan or a pinger (F63); the narrative regeneration rules (F62 at generation time); a roster-diff step in the weekly sync.

---

## (h) Resolving the Appendix C contradictions and covering the gaps

### Contradictions (C3), each with the principle used

1. **"Voted yes 49 %" praised vs F06/F08 calling it noise.** Principle: *a row shows the record, never a ratio.* Ratios reflect who controls the floor; a dated vote with a position is a fact. Roster rows carry the latest plain-English vote and the member's position; the yes-percentage is gone from every list.
2. **Keep both-sides pairing vs F13 drop it.** Principle: *label provenance before you show it, and don't let a label imply people.* The pairing structure stays as a neutrality mechanism, but retitled "Possible arguments, drafted by AI — not attributed to anyone", collapsed by default, in rule colours, on the bill page only. It is not dropped because the alternative (no counter-view at all) is a bigger neutrality risk 46 days out; it is not promoted because it is not the record.
3. **Record on mobile "clean stack" vs F37 official-title walls.** Both true of different rows. Principle: *official text is bounded everywhere it appears in a list.* The stack stays; official titles clamp to one line in rows and 140 chars on the lead article.
4. **F07 hide campaign finance vs F56 visible "Money" section.** Principle: *the spine shows what the person did; who paid is a different job and is shown only when it is current and complete.* Coverage is 80 of 150 members on the 2024 cycle, so no module; one factual line links to the member's FEC filings via `fec_candidate_id`. The PRD's FEC leading indicator becomes a sync target again when 2026-cycle data is loaded.
5. **F30 "three sticky layers" vs F07 wanting a mobile name strip vs "at most one sticky".** Principle: *one sticky element per page, and only where the page is long enough to need it.* Mobile gets a single 44px name strip after the header scrolls off; the tab bar and filter row no longer exist; desktop has no sticky element.
6. **F03/F41 new data files vs hard constraint 5.** The brief (2026-09-18 revision) sanctions exactly these two public files. They are added explicitly with `_source` blocks, never derived from existing JSON, and the crosswalk's land-area caveat is stated on `/methodology`.
7. **F46 promoting h2→h1 vs constraint 4.** The brief names this as the one sanctioned change; the selectors in `feedback.js` change in the same commit, and the `#feedback-*` ids and `#data-freshness` hook are untouched.
8. **F53 cached shells vs localStorage-driven personalisation vs F19 server-rendered first blocks vs F01 freshness.** Principle: *the server renders facts that are the same for everyone; the browser adds only what belongs to this reader.* Shells contain no per-visitor content (the delegation page is per-URL, not per-reader; the bill page's "Your representatives on this vote" slot is server-rendered as the ZIP field and swapped by JS from `cv-home`). So a one-hour shell cache is safe, and it lags the weekly sync by at most one hour, which is invisible against a seven-day data cadence; the "as of" stamps are rendered from the same cached data so they can never disagree with the content beside them.
9. **F20 on-demand Pillow on the free worker vs F05/F63 no headroom.** Principle: *render once, cache forever.* Member and state cards are built at sync time (154 files); bill cards render on first request and are cached immutably by Cloudflare; the default card is static. Worst case is one ~50ms render per new bill URL.
10. **Key-bills picker "sound, needs surfacing" vs F08 asymmetry.** Both hold: the selection logic is reused server-side; only the counts change to 4 + 4, and the rule is printed under the list.
11. **"Latest Vote ships hidden" as graceful degradation vs F55 layout shift.** Principle: *degrade by content, not by geometry.* The card is server-rendered so it never appears late; if the votes index is unavailable at render time the server emits the card with the sentence "The latest vote isn't available right now" at the same size.
12. **Five pages assessed vs six templates.** The 404 is designed here as a page on the spine (entrance form on it) and gets a real status code.
13. **F04 persist the last state vs "never persist the party reveal".** Principle: *persist facts about the reader; never persist a lens on the data.* Where you live is a fact you gave us that makes every page more useful and reveals nothing about the record; party is a lens whose absence *is* the product promise on every fresh visit. So `cv-home` is localStorage and `cv-show-party` is sessionStorage, and both are stated on `/privacy`.

### Gaps (C1) — covered or explicitly deferred

- **404 page** — designed (§c), real status codes (§f 9).
- **House-member pages** — the member layout is one template; House headers read "U.S. Representative · New York · District 4 · In Congress since 2025 · On the ballot Nov 3, 2026"; the 840KB vote file is no longer downloaded (server pagination). Members without donations lose nothing (the FEC line is omitted when `fec_candidate_id` is absent). Independents show "Independent" when party is revealed. Short-record members show fewer key votes ("2 key votes so far"). Departed/vacant seats: the roster shows "Vacant" for a district with no member in `members.json` (sync follow-up to detect).
- **Other states and bad `?code=`** — CA's 54-member roster is the same component (rows are short); invalid/lowercase/missing codes normalise or 404.
- **Bill data conditions** — no roll call: the votes section reads "No floor vote yet" and the "your representatives" slot is omitted; many amendments: each roll call is its own collapsed block with the outcome sentence; both chambers: one party control at page level; no official summary and no AI summary: the empty state shows title, sponsor, status and the Congress.gov link only; malformed URL: 404.
- **No-JS state** — the ZIP form is a GET, the delegation and member pages are server-rendered, `<details>` does the collapsing, so the whole primary path works with JS off; `<noscript>` only notes that party reveal and share need JS.
- **Tablet and 320px** — the 560/880/1100 set is designed at 320, 375, 768, 1024 and 1280 in the mockups; 320 is in the scroll-width check.
- **Print, dark mode, forced colours** — `@media print` hides masthead nav, share and feedback; `color-scheme: light` declared; forced-colors relies on real borders (the vote chip has a border, not only a fill). Full dark theme deferred.
- **Search states** — deferred with `/bills`; the homepage panel is unchanged except the offset fix.
- **Notify/feedback failure states** — inline error under the field ("We couldn't save that — try again or email …"), duplicate signup treated as success, `role=status` announcements; rate limiting already exists in `app/limiter.py` and is kept.
- **Broken photos** — monogram fallback (§d).
- **Hero edge cases** — nomination or no-bill votes render the structured card with `document` text and no bill link; ties and voice votes are handled by the outcome-sentence generator ("The Senate was tied, 50 to 50"; voice votes have no roll call and never become the hero).
- **Keyboard/screen-reader walkthrough** — added to the QA plan as a scripted pass over ZIP → member → bill → roll call before merge.
- **Back/forward** — every state is a URL; no `pushState` tricks; `/#find` anchor exists on home.
- **Cold start** — ops (F63) deferred to Joseph; caching (§f 11) means a cold origin still serves cached shells and JSON.
- **Spanish-speaking users** — not solvable in this PR without a translation layer; the design keeps all UI strings in one `site.js` map and the shells' copy in one place so a `lang=es` variant is a follow-up, and `/about` says so plainly.
- **members.json currency** — "As of" line on the delegation page from `updateDate`; roster-diff step deferred to the sync follow-up.
- **Analytics** — the site has none; the "two clicks to a member" metric is measured from server logs (path sequences), stated on `/privacy` as "server logs only, no cookies, no analytics scripts".
- **`needs_review` flags / audit grades** — not surfaced to readers (a grade is a score); used only in `/methodology`'s coverage paragraph as a count.
