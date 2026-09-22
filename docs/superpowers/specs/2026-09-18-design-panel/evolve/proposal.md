# ClearVoting redesign — Approach "Evolve": fix the seams, keep the structure

Author: design agent (Evolve angle) · 2026-09-18 · Election Day 2026-11-03 (46 days)
Inputs: `docs/reviews/2026-09-10-redesign-review.md` (F01–F63 + Appendix C), the review brief, PRD §Target Users / Success Criteria, `static/`, `data/synced/`.
Mockups: `home.html`, `member.html` in this folder (open from `file://`). The bill page is specified in §c, not mocked, because this angle's thesis does not centre on it.

---

## (a) Thesis

Every page and module ClearVoting has today stays; each verified P0/P1 is fixed in place with the smallest change that makes the page honest, reachable and readable on a phone. The homepage is the reference design and is barely touched — the ZIP finder moves into its first screen, the Record and Latest Vote card tell the truth about summaries, and the inner pages are reordered and de-carded rather than rebuilt. The point is a conservative baseline that Joseph can merge as one PR before November 3 with no new framework, no new URL shapes, and no bet on the AI sync coming back.

## (b) Information architecture

Pages and URLs after the change (no shape changes; two new static pages; one new endpoint):

| URL | Status | What it is |
|---|---|---|
| `/` | kept, edited | Front door: ZIP/state finder in the first screen → delegation (same component) → The Record → notify |
| `/?zip=11570` / `/?state=NY` | new query params on the same page, `history.replaceState` | Shareable, Back-restorable homepage state (F04 partial) |
| `/state?code=NY` | kept, reordered | Same page, same renderer, but senators first, House by district, party toggle, share; linked from the homepage delegation |
| `/member?id=…` | kept, reordered | Header → summary → key bills → record → topic/sponsored/money |
| `/bill?congress=…&type=…&number=…` | kept, edited | One-liner headline, outcome sentence, honest empty state, delegation block, collapsed roll call |
| `/about` | kept, rewritten | Who/why/funding/name/contact; no entrance animation |
| `/methodology` | **new static page** | Sources, cadence, the real neutrality rules, what AI touches, known gaps, dated corrections log |
| `/privacy` | **new static page** | What is stored (email + state, feedback text + page), where, how long; third-party requests listed |
| `/404` (any unknown route or unknown id) | kept, edited | Navy CTA, "find my representatives" path; real 404 status for unknown ids (F52) |
| `/api/districts/{zip}` | **new endpoint** | Reads the Census ZCTA→CD119 crosswalk JSON; returns candidate districts |

Primary path: `/` → type ZIP (or tap state) → the delegation section scrolls into view with the user's 2 senators + House member pinned → tap a name → `/member` (summary + key bills within two mobile screens) → tap a key bill → `/bill` (outcome sentence + "your delegation" block). Two taps from landing to a member page; three to a bill.

## (c) Page by page

### Home (`/`) — mockup `home.html`

**For:** prove the promise in one glance and get the visitor to their own representatives in one action.

**Above the fold, mobile (375px):** masthead (logo, tagline, 4-item nav incl. "Find my representatives"), election dateline, kicker, H1 "See how your representatives vote.", deck, **ZIP field + Find button**, "Or pick your state" + 4 compact state cards. The Latest Vote card comes after the finder because the finder now lives inside `.lead-left` (the existing grid's left column), so on a single column it naturally precedes the card. Nothing else moves.

**Above the fold, desktop (≥1100px):** left column = kicker, H1, deck, finder (ZIP + state cards + coverage line); right column = structured Latest Vote card.

**Modules in order:** masthead → lead (H1 + finder | Latest Vote) → Your Delegation (same section; rows rebuilt) → The Record (as-of stamp; lead article = newest summarised bill; right list = newest by action date with fallback rows) → Browse toggle (unchanged panel) → Notify (with state select) → footer.

**What changed inside modules:**
- *Latest Vote card* (F02, F17): structured (kicker, dateline, headline, outcome sentence, tally, link). Headline = `one_liner` in Playfair when present, else the official title in Lora body weight (never inside a sentence template). Link text = "What this bill does, in plain English →" only when a summary exists; else "See the vote and the official summary →" plus a "Plain-English summary not written yet" tag.
- *Finder* (F03, F21, F42): ZIP input (16px, 44px tall, `inputmode=numeric`, `autocomplete=postal-code`), coverage line "Right now: CA, FL, NY and TX — 150 members, every roll-call vote since 2021". States: single match → scroll to delegation with the user's three members pinned; split ZCTA → "11580 covers more than one district. Which is yours?" list of districts with member names (≥5% land share, largest first, shares not printed); ZIP outside coverage/unknown → "We don't cover 30301 yet…" with the notify form one tap away; the state cards are always directly below so there is no dead end.
- *Delegation* (F04 partial, F06): same section, same IA (senators first, House by district). Rows are rebuilt for recognition: photo, name, seat, "In office since YYYY", ballot marker, and ONE non-ordinal fact that varies by member — their position on the latest roll call that has a plain-English summary (today: H.R. 6500, Sept. 1 in the House / Aug. 8 in the Senate), as a Yes/No/Didn't-vote chip. The yes-percentage split bars, the participation line and the 150-char narrative snippet are removed. A "Share this page" link goes to `/state?code=NY`; the chosen state/ZIP is written to the URL with `replaceState` and restored on load and Back.
- *The Record* (F01, F37, F40): as-of stamp ("Votes and bills as of September 5, 2026. Plain-English summaries are written through June 30, 2026…"). Lead article = most recent bill with a summary, labelled as such and dated. Right list = the six newest bills by action date regardless of summary, each with a status seal derived from the votes index ("Passed House", "Adopted"), the outcome and date, the official title clamped to one line, and a "Summary coming" tag. Official titles are dropped from summarised list rows (they live on the bill page); the lead keeps "Officially: …" capped at 140 chars.
- *Notify* (F39): state select + email (autocomplete), navy button, one-line privacy note.
- *Feedback* (F23): floating pill removed below 881px; footer gains "Report an error on this page"; desktop keeps a 44px icon button with `env(safe-area-inset-bottom)` and `main` reserves bottom padding.

**Cut:** yes-% bars and narrative snippets in roster rows (zero signal, imply ranking); the sentence-template hero; the external "Look it up by ZIP →" exit as the only district help (kept as a secondary house.gov link for street-address lookup).

### Delegation / State (`/state?code=NY`)

**For:** the shareable, crawlable home of one state's delegation.

**Above the fold, mobile:** masthead → h1 "New York's representatives" → sub "2 senators and 26 House members" → ZIP field (same component as home, pre-filtered to this state) → party toggle + share → "The Senate" label → first senator row. **Desktop:** same, roster in two columns.

**Modules:** header → finder (ZIP) → actions (party toggle, share) → Senate rows → House rows by district → house.gov fallback → footer.

**What changed:** `state.js` keeps its file and its `/api/members/{state}/overview` call but the overview response is now read from a precomputed file (§f), the default sort is chamber-then-district, the four stat boxes / participation bars / support-rate sort / Total Votes column / colour thresholds are deleted, the table on desktop becomes the same row component as the homepage roster (so `broadsheet.css:168-191` is reused, not `.comparison-table`), the mobile card becomes a whole-card tap target, and `document.title` is no longer overwritten. The homepage delegation links here for sharing; the two renderers converge on one row component but both files stay (this angle does not retire either).

**Cut:** stat-box row, Total Votes, participation bar and traffic-light colours, metric sorts, "Representatives 28" duplicate, fake-sortable headers (F06, F34, F36, F48).

### Member (`/member?id=S000148`) — mockup `member.html`

**For:** who this person is and how they actually vote, in plain English.

**Above the fold, mobile:** masthead → back link → photo (72px) + kicker "U.S. Senate · New York" + **h1** name + meta ("In Congress since 1981 — House 1981–1999, Senate 1999–present. Voted in 1,060 of 1,061 roll calls") + ballot marker + actions (Party: hidden · Show party labels · Share · Congress.gov) → the slim sticky name strip appears once the header scrolls away → "At a Glance" clamped to four lines with "Read the full summary". Key bills start on the second screen. **Desktop:** header full width; below it a 760px article column (summary, key bills, record, topics) with a sticky aside (sponsored bills, campaign money).

**Modules in order:** header → At a Glance (dated AI line) → Key bills (6 yes / 4 no, linked, dated, outcome, chip) → Voting record (filters: plain-summary-only checkbox default on, topic select; rows grouped one-per-bill with the bill's other roll calls folded into the line; amendment/motion votes — `bill_id: null` in the data — collapsed by date as "3 amendment and procedural votes, Aug. 7–8"; pagination that keeps focus) → Votes by topic (collapsed; raw Yes/No counts per topic, table with scope/caption) → aside: Sponsored bills (6, inline, shared formatter, plain last-action) → Campaign money (one headline from `donations.totals`, top occupations, dated FEC line; hidden for the 70 members with no filing) → "Report an error" line → footer.

**What changed:** h1 promotion with `feedback.js` selectors updated in the same commit (F46, constraint 4's sanctioned change); counts come from `stats.total_votes`/`not_voting_count` verbatim (F26); result strings normalised through one vocabulary ("Passed 90–6", "Did not advance — needed 60 votes, 52–46", "Adopted 50–47", "Set aside (tabled) 61–32", "Amendment rejected 32–64") (F11, F27); fallback headline slot never repeats the same string ("S. 5271 — no plain-English summary yet · Officially: …") (F09, F27); no empty chips; resolutions link to their bill pages via the shared `typeMap`; one sticky element; mobile-first CSS declared after base rules so the 70px overflow disappears (F14); AI line states the generation date and coverage (F40).

**Cut:** donut, attendance ring/bar, the three stat tiles, "What They Fight For by Topic" bars (replaced by the collapsed raw-count table), the Service History card (folded into the header meta), the tab bar and sticky filter row, the second `/detail?show_party=true` fetch (party comes from the toggle's own call), the stray "Copy Link" chip (F07, F08, F28, F29, F30, F56).

### Bill (`/bill?…`) — described, not mocked

**For:** "Congress just voted on X — what does it do, and how did my rep vote?"

**Above the fold, mobile:** masthead → back link → kicker "H.Con.Res. 108 · 119th Congress · Rejected by the House" → **h1** = `one_liner` ("Order U.S. troops out of hostilities in Lebanon within seven days") → deck = official title in Lora, muted → outcome sentence "The House rejected it, 189 to 235, on June 30, 2026." → byline row (sponsor, coverage-aware; "43 cosponsors"; policy area; Share) → first provision bullet. **Desktop:** the same as one article column, roll call to the right of the provisions on ≥1100.

**Modules:** header (as above) → What this bill does (provisions with section marks; AI line only when AI content rendered) → Arguments block, relabelled "Possible arguments, drafted by AI — not attributed to anyone", disclaimer at the top, "Supporters say/Critics say" prefixes stripped at render, neutral ink/rule colours, collapsed by default → Official summary (existing sanitiser, collapsed) → Roll call: outcome band → "Your delegation" block (from the ZIP/state saved on the homepage; senators + House member with chips and links) → "All 431 votes" collapsed, with state filter and name search; covered members link to `/member`, others plain text; mobile rendering is a two-line list, never a horizontally scrolling table → Sponsors (coverage-aware linking) → Congress.gov link.

**Empty state (no `one_liner`, F02):** the ai-summary endpoint returns `{available:false}` (404 semantics kept out of the URL); the page renders the official title as h1, the derived status and vote result above the fold, the first paragraph of the official summary promoted into the primary slot, a neutral "We haven't written a plain-English summary for this bill yet" line with no section mark and no AI disclaimer, and "Loading summary…" instead of "Generating…".

**Cut:** the TOC chips, the one-chip tag row (subjects aren't in the data; policy area moves to the byline), the raw "Latest action (2026-06-30): Motion to reconsider laid on the table…" line (replaced by the derived status), the per-block party toggles (one page-level toggle re-renders all blocks), the pie per roll call (F10, F11, F12, F13, F15, F25, F31, F32, F33).

### About / Trust pages (+404)

- `/about` (F18, F22): the existing sections with `animate-in`/`animate-scale` classes and the observer removed; adds a name and contact line ("Maintained by Joseph J. Garcia — contact: joe.garcia606@gmail.com or the feedback form"), the funding sentence, and the coverage statement moved up; "12 strict rules" replaced by a link to the methodology page; "what people are saying" language replaced by "possible arguments drafted by AI".
- `/methodology` (new static HTML, same shell): sources and sync cadence, what AI writes and does not touch, the neutrality rules generated from the prompt text (or counted correctly), known gaps stated plainly ("60 bills newer than June 30, 2026 have no plain-English summary; the summary job has been paused since early July"), a dated corrections log (`#corrections`, hand-edited).
- `/privacy` (new static HTML): what is collected (email + state on notify; feedback text + page URL; no analytics), where it goes (Google Sheets), how long, third-party requests (Google Fonts today; "none" once fonts are self-hosted — deferred, see §g).
- `404.html`: kicker "Not found", h1, one sentence, navy "Find my representatives" button to `/#find` and a "Back to ClearVoting" text link; the shell routes return HTTP 404 for unknown member/bill ids and unsupported state codes (lowercase codes are normalised first).
- Footer on every page: About · Methodology & Corrections · Privacy · Report an error on this page; freshness text rendered only when a value exists; roll-call sync date and summary coverage date stated separately.

## (d) Visual system decisions

- **Palette and fonts stay** (paper/navy/blue, Playfair/Lora/Inter). Two token edits only: `--ink-meta` → `#5F656D` (5.45:1 on paper, 5.88:1 on white) and `--text-dim` aliased to the same value for text (F16). Red/green (`--yes`/`--no`) are used by exactly two components: the tally bar and the vote chip; the chip carries text and a border, never colour alone (F35, F36). Primary buttons (Find, Notify, 404 CTA, feedback Send) become navy; `--accent-red` is retired from buttons.
- **Typography roles:** kicker 0.75rem Inter caps (12px floor); meta 0.8rem Inter; UI 0.875rem Inter; body 1rem Lora; lede 1.05–1.08rem Lora; h3 1.25rem Playfair; h2 1.45rem Playfair; display `clamp(2.1rem, 5vw, 3.2rem)`. The three sizes below 12px in `broadsheet.css` (0.66/0.68/0.70rem) are raised to the floor; nothing else on the scale changes (F57 partial).
- **Rules vs cards:** cards remain for the three interactive card types the homepage already has (state-card, vote-card, senator/roster row). Every other container on member/state/bill becomes a hairline section on paper (1px `--rule` between sections, 3px double `--navy` above a page's major section). No nested white cards, no box-shadow outside the interactive cards (F15, minimum version).
- **Chips:** two only — status seal (existing `.law-seal`, 4px radius, uppercase) and the vote chip (same shape with a dot). "Summary coming" and "no plain-English summary yet" tags reuse the seal outline. The bill TOC chips and topic pills on the bill page are removed (F58 partial).
- **Feedback control:** desktop ≥881px a 44px round navy icon button, bottom-right with safe-area inset and reserved page padding; below that, no floating element — "Report an error on this page" in the footer, "Report it" under the record, and Feedback in the nav. The modal becomes a native `<dialog>` with `aria-labelledby`, a real `<label>`, `role=status`, and focus return, keeping every `#feedback-*` id (F23, F24).
- **Touch targets:** one token `--tap: 44px` applied to nav links, footer links, party toggle, chips-as-buttons, pager, disclosure summaries, inputs and selects; 16px inputs to prevent iOS zoom (F30, F47).
- **Focus:** one global `:focus-visible` rule replaces the allowlists; every `outline:none` and low-alpha box-shadow substitute is deleted (F45).
- **Breakpoints:** 880 / 560 only, declared once at the end of each stylesheet; JS reads `matchMedia('(max-width: 880px)')` (F51). The dead `<=768/<=480` blocks in `styles.css` are deleted (not reordered), which is what fixes F14.
- **Motion:** no entrance animation anywhere; content defaults to `opacity:1`; JS smooth scroll checks `prefers-reduced-motion` (F22, F60).

## (e) Finding coverage

| Id | P | How Evolve resolves it |
|---|---|---|
| F01 | P0 | Record list = newest by action date with fallback rows and per-item dates; as-of stamp with the summary coverage date; lead article labelled "most recent with a plain-English summary" |
| F02 | P0 | Hero prefers the latest vote with a `one_liner`, else honest link text + tag; ai-summary endpoint returns `{available:false}`; real bill-page empty state; AI disclaimer only when AI content rendered |
| F03 | P1 | ZIP field in the first screen on every viewport, backed by the Census crosswalk + existing `/api/members/{state}/{district}`; split-ZIP and unknown-ZIP states designed; state cards stay as fallback |
| F04 | P1 | **Partially.** Homepage state/ZIP written to the URL (`replaceState`) and restored; `/state` reordered to match and linked as the share target; party toggle added to `/state`. Both renderers are kept — one canonical surface is deferred (§g) |
| F05 | P1 | Precomputed `data/synced/state_overview/{code}.json` at sync time; `/api/members/{state}?include_stats` and `/overview` read it; roster skeleton renders from `members.json` immediately |
| F06 | P1 | Stat boxes, Total Votes, participation bars/colours and metric sorts deleted; rows = photo, name, seat, tenure, position on the latest summarised roll call; participation shown only when <90% |
| F07 | P1 | Order: header → summary → key bills → record; donut, attendance, stat tiles, Service History card, tabs cut; one sticky strip on mobile |
| F08 | P1 | Key bills are links with bill code, dateline and outcome, using the same row component as the record; asymmetry explained in one line; the latest key vote appears on roster rows |
| F09 | P1 | One row per bill with other roll calls folded into the meta line; amendments/motions collapsed by date; default filter = plain-summary votes; fallback headline never repeats a string; empty title div removed |
| F10 | P1 | Outcome band + "Your delegation" block from the saved ZIP/state; full roll call collapsed with state filter and name search; covered members linked; two-line list on mobile |
| F11 | P1 | One outcome-sentence generator, one result vocabulary, one VoteChip ("Yes/No/Present/Didn't vote"), one tally format shared by `app.js`, `member.js`, `vote.js`, `state.js` |
| F12 | P1 | `one_liner` as bill h1 and in the server `<title>` ("H.Con.Res. 108 — {one-liner} \| ClearVoting"); official title as deck/description, truncated on a word boundary |
| F13 | P1 | Block kept but relabelled "Possible arguments, drafted by AI — not attributed to anyone", disclaimer on top, prefixes stripped, neutral colours, collapsed by default; About copy corrected |
| F14 | P1 | Dead `<=768/<=480` blocks deleted; member CSS rewritten mobile-first with overrides after base rules; stat rows gone; scroll-width check at 320/375 in QA |
| F15 | P1 | **Minimum version.** Cutting the chart modules removes most cards; the remaining containers (`.glance-card`, `.viz-section`, `.bill-section`, `.state-stat`, `.comparison-table`, `.mobile-card`) have their background/radius/shadow rules removed and section heads switched to kicker + hairline. `styles.css` is not rewritten (deferred, §g) |
| F16 | P1 | `--ink-meta` #5F656D; `--text-dim` aliased for text; 12px floor; contrast checked against paper and card in the definition of done |
| F17 | P1 | Structured hero; official title only ever in body type, ≤ ~90 chars with an ellipsis |
| F18 | P1 | `/about` rewritten with a name and contact; `/methodology` and `/privacy` added; footer repointed |
| F19 | P1 | **Partially.** The shell routes already have the data in process: server-render the member header + At-a-Glance, the bill header + outcome sentence, and the state header + roster names into `<main>`; JS fills the rest. Homepage Latest Vote card, Record entries and state counts are also server-rendered. Full server-rendering of vote lists is deferred |
| F20 | P1 | Delete the three `document.title` overwrites; one "Share" action in the header (`navigator.share`, clipboard fallback with a visible toast) on member, bill and state; `og:image` via one **static** branded card per page type + a per-page static default (no per-request rendering — see §h); `twitter:card=summary_large_image` |

P2/P3 also resolved by this approach: F21, F22, F23, F24, F25 (single toggle component, `aria-pressed`, session-scoped persistence, one page-level control on bill), F26, F27, F28 ("Votes by topic": full labels on their own line, raw Yes/No counts per topic in a captioned table, collapsed, the direction model dropped), F29, F30, F31 (shared `formatBillCode` + ordinal helper), F32 (derived status pill, one date helper), F33, F34, F35, F36, F37, F39, F40, F41 (election dateline; "On the ballot this November" for House seats and Senate seats from the sanctioned list), F42, F43 (aria-live moved to a status element), F44, F45, F46, F47, F48 (scope/caption on remaining tables; fake-sortable headers removed), F52 (canonical normalisation, real 404s, favicon route, per-URL lastmod), F53 (cache headers, §f), F56, F60, F61, F62 (partial: "leans" is not regenerated, but the module is dated and demoted below key bills).

Not addressed (deferred, see §g): F38 (`/bills` page and topic URLs; only the load-more offset bug is fixed), F49 (fresh stylesheet), F50 (single token vocabulary; JS still has constants), F51 (partial: breakpoints unified, but `styles.css` remains), F54 (waterfall consolidation beyond `limit=15`), F55 (self-hosted fonts; sized skeletons are added), F57/F58/F59 (partial: floors and two chips, not a full scale), F63 (paid instance / pinger — an ops decision for Joseph, recommended in the PR description).

## (f) Data and backend touches (small, named)

1. **ZIP crosswalk** — `data/zcta_cd119.json` (new, public domain, Census 2020 ZCTA↔CD119 relationship files for 06/12/36/48, trimmed <1% slivers, ~36KB gz) + `data/SOURCES.md` line with URL and retrieval date. `app/routers/districts.py` (new, ~30 lines): `GET /api/districts/{zip}` → `{zip, matches:[{state, district, share}], covered:bool}`; returns `covered:false` for ZIPs outside the four states or absent from the file. `app/main.py`: include the router. `static/js/app.js` and `state.js`: the finder component (one function shared by copy, no build step) calls it, then the existing `/api/members/{state}/{district}` for the pinned member.
2. **Senate seats up in 2026** — `data/senate_2026.json` (new, ~35 ids, source Senate.gov class list, flagged in `SOURCES.md`). `app/routers/members.py` `get_member_detail`: add `on_ballot_2026: bool` (House = true; Senate = id in list). Rendered in the member header and roster rows.
3. **Record freshness** — `app/services/data_service.py`: keep `summarized_only` but add `get_bills(newest_first=True)` untouched; `app/main.py` health/`_inject_meta` expose `summaries_through` (max `latestAction.actionDate` over bills with a summary = 2026-06-30) so the as-of stamp and footer read it. `app.js` fetches `/api/bills?limit=6` for the list and `/api/bills?summarized_only=true&limit=4` for the lead + also-list.
4. **Hero rule** — `data_service._build_latest_vote`: prefer the most recent vote whose bill has a `one_liner`; include `has_summary` in the payload so `app.js` picks the link text.
5. **Empty summary** — `app/routers/bills.py:60`: return `{"available": false}` instead of the apology string; `bill.js` renders the empty state from it.
6. **Precomputed state files** — `scripts/sync` (wherever the weekly sync writes `member_votes`): also write `data/synced/state_overview/{CA,FL,NY,TX}.json` with per-member `participation_rate`, `first_year`, `on_ballot_2026`, and `latest_summary_vote {bill_id, bill_number, one_liner, date, vote}`; `app/routers/members.py` `get_members_by_state(include_stats)` and `/overview` read that file and fall back to the current scan only if it is missing. Turns a 2–5s call into a file read.
7. **Server-rendered first block** — `app/main.py` `_serve_html`: a second injection point, a literal `<!-- ssr -->` comment inside `<main>` in `member.html`, `bill.html`, `state.html`, `index.html`, replaced with escaped HTML built by three small formatters in `app/services/ssr.py` (header + summary; header + outcome sentence + provisions; header + roster names; latest-vote card + record entries + counts). JS keeps enhancing; `<title>` and `</head>` untouched.
8. **Caching** — `app/main.py`: `Cache-Control: public, max-age=31536000, immutable` on `/static` (the `?v=` bust exists); `public, max-age=3600, stale-while-revalidate=86400` on `GET /api/*` and on the HTML shells (drop `no-store`). Because nothing in the HTML is per-visitor (§h), a cached shell is safe.
9. **og:image** — four static PNGs in `static/og/` (home, member, bill, state — branded broadsheet cards at 1200×630, made once in the design pass, no Pillow at request time); `_inject_meta` emits `og:image`, width/height and `summary_large_image`. Per-member images are deferred.
10. **Server titles** — `_member_meta`: first-last name form; `_bill_meta`: one-liner form when available, official title truncated at ~70 chars on a word boundary; canonical built from normalised params; unknown ids → `HTTPException(404)` served with `404.html`.
11. **Trust pages** — `static/methodology.html`, `static/privacy.html` (static, same shell, literal `<title>`/`</head>`); `app/main.py` two routes + sitemap entries; `/favicon.ico` route.
12. **feedback.js** — selectors `.member-header h1` / `.bill-header h1` in the same commit as the h1 promotion; the observer block (lines 195–217) deleted; `<dialog>` open/close with focus return.

## (g) Scope estimate, risks, deferrals

| Page / area | Size | Notes |
|---|---|---|
| Home | **M** | Finder component + crosswalk endpoint (the only genuinely new feature), hero rule, Record split, notify state, URL state |
| State | **S–M** | Reorder, delete stat modules, reuse row component, precomputed file |
| Member | **M** | Reorder, cut modules, row vocabulary, mobile-first CSS rewrite for this page only, h1 + feedback.js |
| Bill | **M** | One-liner h1, outcome generator, empty state, arguments relabel, delegation block + collapsed roll call with filter |
| About / Methodology / Privacy / 404 | **S** | Static HTML; copy is the main effort (needs Joseph's name/contact/funding sentence) |
| Backend / data | **S–M** | 12 touches above, each ≤ ~60 lines; crosswalk build script ~80 lines |
| **Total** | **M (one PR, roughly two focused weeks)** | Fits before November 3 with a week of QA; nothing depends on the AI sync |

**Risks.** (1) The precomputed state file and the crosswalk are the two things that must be generated by a script Joseph runs once; if the sync job is the place they are generated, the first deploy needs a manual run. (2) Keeping `styles.css` means the dead-CSS trap remains for the next change; the member-page CSS is rewritten but the file as a whole is not. (3) Cached shells mean a fresh sync is visible within an hour, not instantly — acceptable for weekly data, stated on the methodology page. (4) ZCTA ≠ USPS ZIP: PO-box ZIPs return "not found"; the copy handles it but some users will hit it. (5) Two delegation renderers persist; drift is possible until F04 is finished.

**Deferred to a follow-up.** One canonical delegation surface with `/state/ny` aliases and 301s (F04 full); a `/bills` page with topic URLs (F38); a fresh single stylesheet with one token set, scale and spacing grid (F49, F50, F57–F59); self-hosted fonts (F55); per-member og images; consolidating the member page's five fetches into one (F54); full server-rendering of vote lists; regenerating narratives without "leans" (F62); Spanish-language UI strings (Appendix C gap — noted as a real need for NY/FL/CA/TX; deferred because the data layer's summaries are English-only); the paid Render instance / uptime pinger (F63 — an ops decision surfaced in the PR description).

## (h) Appendix C — gaps and contradictions, resolved for this design

**Gaps (C1)** — covered: 404 page (§c), House-member pages (the member layout has no Senate-specific module; District appears in the kicker; House members use the same header), members without donation data (Money section hidden), invalid `?code=` (normalise, else 404), bills with no roll call (status "Introduced — no floor vote yet", delegation block omitted, "How your rep voted" heading not shown), bills with both chambers (one page-level party toggle, two outcome bands), no-JS state (server-rendered first block means header/summary/outcome are visible without JS; a `<noscript>` line says "Vote lists need JavaScript"), broken photos (`onerror`-free: the `<img>` gets a paper background and the row keeps its layout; alt is empty on rosters and descriptive on the header), hero edge cases (nomination or no-bill vote → headline = `v.document`, link to the roll call source instead of a bill page; tie or voice vote → outcome sentence from result string, tally omitted), tablet widths (880 breakpoint; 768–1024 uses the desktop grid with the aside stacked below), 320px (single column everywhere, chips wrap under the headline), `members.json` currency (out of scope to re-sync; the methodology page states the roster date from `updateDate` and the corrections log is the mechanism), Spanish-speaking users (deferred, stated above), search zero-results (kept panel gains "No bills matched — try a topic chip"), form failure states (inline `role=status` copy for invalid email, duplicate, and server error), instrumentation (none added; the "three members in two clicks" metric is measured by hand in QA). Explicitly deferred: print/dark/forced-colors stylesheets, keyboard walkthrough (QA task, not design), cold-start measurement, abuse protection on write endpoints (engineering), `needs_review` flags (no surface until the sync resumes).

**Contradictions (C3)** — each resolved with a stated principle:

1. *"Voted yes 49%" endorsed vs F06 removal.* Principle: **a roster shows facts that vary by person and don't rank them.** The percentage is removed; the vocabulary "voted yes/no" is kept, applied to one concrete roll call.
2. *Keep both-sides arguments vs F13 drop.* Principle: **keep the neutrality structure, fix the provenance.** The pairing stays, relabelled as AI-drafted possible arguments, collapsed, neutral colours.
3. *Record mobile stack is clean vs F37 title wall.* Principle: **the stack is right, the payload is wrong.** Structure kept; official titles clamped to one line and dropped from summarised rows.
4. *Hide finance (F07) vs inline Money (F56).* Principle: **show data that is dated honestly; hide data that has none.** Money is shown as one dated line ("2024 cycle, retrieved March 20, 2026"), in the aside, and hidden where absent.
5. *Sticky bars (F30 vs F07).* Principle: **at most one sticky element per page.** The desktop sticky bar and sticky tabs/filters are removed; a slim name strip is the only sticky element, mobile only.
6. *New data files vs constraint 5.* The brief itself sanctions exactly the crosswalk and the Senate-seats list; both are flagged in `data/SOURCES.md` with URL, licence and retrieval date. No other new data.
7. *feedback.js hooks vs h1 promotion.* The brief names this as the one sanctioned change; the two selectors change in the same commit as the h1s.
8. *Cached shells vs personalised blocks and Record freshness.* Principle: **nothing per-visitor goes into HTML.** The server-rendered blocks are per-URL (member/bill/state/home), not per-visitor; the "your delegation" block and the pinned House member are client-rendered from the ZIP/state the browser holds. A one-hour shell cache therefore never leaks state, and Record freshness lags a weekly sync by at most an hour, which the as-of stamp already describes (it reads the sync date, not the clock).
9. *Pillow og images on a free worker.* Resolved by not rendering per request: four static cards. Per-entity images are a follow-up once the origin has headroom.
10. *Key-bills picker "sound" vs 6-vs-4 asymmetry.* Principle: **keep the logic, explain the output.** The picker is untouched; one line under the list says why the counts differ.
11. *Hidden-then-revealed Latest Vote card: preserve vs layout shift.* Principle: **degrade gracefully, but from a reserved space.** The card is server-rendered; if the API fails at render time the shell ships a sized empty card with a one-line "Latest vote unavailable" note, so nothing reflows.
12. *Pages assessed 5 vs six templates.* The 404 page is treated as a page here (§c).
13. *Persist last state (F04) vs never persist party reveal.* Principle: **persist what helps the person find themselves; never persist what the product promises to withhold until asked.** Location (state/ZIP) is remembered in `localStorage` and pre-filled but is user-visible and one tap to clear; the party reveal is `sessionStorage` at most, so every fresh visit starts hidden. Both rules are written on the privacy page.
