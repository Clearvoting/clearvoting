# ClearVoting redesign — Approach "Broadsheet complete: one design language, ruthlessly edited"

Written 2026-09-18 for the judge panel. Mockups: `home.html` and `member.html` in this directory (open from file://). Election Day is 46 days out; everything below is scoped to ship as one PR before then, with named deferrals.

## (a) Thesis

ClearVoting already has the right design language; it has never been finished, and the middle of every page is still a card dashboard wearing a broadsheet masthead. This approach writes one stylesheet from one token set, one type scale, one spacing scale and two breakpoints, and rebuilds every page on the homepage's rule-and-whitespace containment model — the front page is today's edition, the state page is the local desk, the member page is a profile column, the bill page is a story with a fact box. Every module must answer a question the busy citizen actually has, or it is cut; red is reserved for "No", green appears only inside the numbered tally bar, and every AI-authored or synced fact carries its own date.

## (b) Information architecture

Pages after the redesign (no URL shapes change; two static pages and one list page are added):

| URL | Page | Role in the metaphor |
|---|---|---|
| `/` | Front page | Today's edition: masthead, edition line, find-my-representatives, the latest vote, the Record |
| `/state?code=NY` (also accepts `?zip=11201`) | Delegation | The local desk: your representatives first, then the whole delegation. Single canonical delegation view; the homepage's four state cards are real links here |
| `/member?id=S000148` | Member | Profile column: header, at a glance, key votes, the record by bill, short side sections |
| `/bill?congress=119&type=hr&number=4795` | Bill | A story with a fact box: headline, deck, outcome sentence, fact box, provisions, roll call led by your delegation |
| `/bills` (new, small) | Archive | The full record by date and topic; search moves here off the front page |
| `/about`, `/methodology` (new), `/privacy` (new) | Trust | Three plain static pages; footer repointed |
| `/404` | Not in this edition | A broadsheet 404 with the ZIP finder |

Primary path (the measure: a first-time visitor reaches their own three members in two clicks from any entry):

1. `/` → type ZIP, submit (a plain GET form; no JavaScript required) → `/state?zip=11201` renders "Your representatives" at the top (2 senators + 1 House member; 2–4 when the ZIP straddles districts) above the full delegation.
2. Tap a name → `/member?id=…`. Two clicks. From a member's key vote → `/bill?…`, whose roll call opens with "Your delegation" because the ZIP is remembered.
3. Returning visitors: the front page shows the same "Your representatives" block under the finder without re-typing ("the local edition"). Search-engine visitors land on `/state` or `/member` with the finder one tap away in the masthead nav ("Find my representatives").

Retired from the IA: the homepage's in-page delegation renderer (`app.js` roster), the homepage browse panel and topic chips, the member page's tab bar, the bill page's table of contents.

## (c) Page by page

### Home `/` — today's edition

**For:** prove the promise in one glance and get the visitor to their own representatives in one action.

**Above the fold, mobile (375×812):** masthead (logo, tagline, nav on one wrapping row), the edition line ("Data synced September 5, 2026 · Latest roll call September 3 · Midterm elections Tuesday, November 3 — 46 days away"), kicker, H1 "See how your representatives vote.", one-line deck, the ZIP field and its navy "Find my representatives" button. The four state links start at the fold edge. Nothing else.

**Above the fold, desktop (1280):** the same lead in a 3:2 grid; right column holds "The latest vote" card, left column the H1 + finder + state links + coverage line. The "Your representatives" block (returning visitors) spans both columns below.

**Modules in order:**
1. Masthead + edition line. The edition line is the only place the three freshness facts live (sync date, latest roll call, days to the election), and each is a real field: `sync_metadata.last_sync`, newest `vote_date` across `votes/`, and a server-computed day count.
2. Lead: kicker, H1, deck, finder (ZIP primary; four state links secondary with real member counts from `/api/members/counts`; coverage stated plainly: "Right now ClearVoting covers California, Florida, New York and Texas — 150 members, every roll call since January 2021"; "Somewhere else?" is a disclosure with a state select + email, navy button, one-line privacy note).
3. The latest vote: a structured card, never a sentence template. Kicker, dateline ("U.S. House · September 3, 2026 · Final vote to pass"), headline = AI one-liner when it exists, otherwise the official title set in Lora 500 (body serif, not display), the "Plain-English summary coming" chip, the labelled tally bar, a four-cell fact list (result, sponsor + cosponsor count, topic, and how the visitor's state voted when a state is remembered — otherwise "New York" is replaced by the chamber split), and an honest link: "See the vote and the official summary →" when no summary exists, "What this bill does, in plain English →" when one does.
4. Your representatives (returning visitors only; otherwise absent). Exactly the block the state page renders.
5. The Record: newest bills by action date regardless of summary status; "As of September 5, 2026 · Newest first"; a coverage note ("Plain-English summaries are current through June 30, 2026. Newer bills show their official title until a summary is written; nothing is left out."); eight rows, two columns at ≥880. Summarized rows: bill code kicker, status seal, date, Playfair headline (one-liner), one meta line. The newest summarized bill (H.Con.Res. 108 today) also gets its three provision bullets — the one "lead article" on the page. Unsummarized rows: the official title in Lora 500 clamped to two lines, the pending chip, the tally. Foot: "The full record — 1,610 bills by date and topic →" to `/bills` and "1,550 of 1,610 bills have plain-English summaries".
6. Footer (kept verbatim, plus "Report an error on this page" as the feedback opener).

**Cut, and why:** the in-page delegation section (it is the state page now; one renderer, one URL); the browse panel, search box and topic chips (a busy citizen does not browse 1,610 bills from the front page; `/bills` keeps the capability for the few who do); "Updated weekly" (replaced by dated facts); the hero sentence template (`app.js:135`); the floating feedback pill; the notify form without a state field.

### Delegation `/state?code=NY` (and `?zip=`) — the local desk

**For:** the shareable, crawlable home of a state's delegation, and the landing for the ZIP path.

**Above the fold, mobile:** masthead + edition line; kicker "New York · 28 representatives"; H1 "New York's representatives"; a compact finder (ZIP field prefilled when `?zip=` is present, else empty) so a search-engine visitor can narrow to their district without going home; then "Your representatives" (when a ZIP is present) or "Your senators" (always first).

**Above the fold, desktop:** the same, with "Your senators" and "Your House member" side by side.

**Modules in order:**
1. Header: kicker, H1, one meta line ("2 senators · 26 House districts · roster as of March 8, 2026" — the newest `updateDate` in `members.json`, so roster staleness is visible), party line ("Party labels are hidden so the record speaks first — Show party labels", `aria-pressed`), Share.
2. Your representatives (ZIP present): senators group, then the House group. Split ZIP: "ZIP 11201 straddles two House districts (about 72% of its land is in District 10, 28% in District 7). Both are shown; your street decides which is yours." Unknown ZIP: "We don't have ZIP 11xxx in the Census file — choose your district below, or try a neighbouring ZIP." ZIP outside the four states: "ZIP 43215 is in a state ClearVoting doesn't cover yet" + the notify disclosure.
3. The delegation: senators as a labelled group, then "The House — by district" in district order 1–26. Each row is a person row (photo with monogram fallback, Playfair name as the link covering the whole row, seat line "District 4 · In Congress since 2025 · On the ballot this November", and one signal line: the member's most recent vote on a bill with a plain-English summary, with the vote chip, bill code, outcome and date). No percentages, no bars, no stats.
4. Footer.

**Cut, and why:** the four aggregate stat boxes, the participation bar and its traffic-light thresholds, Total Votes, the sort-by-metric dropdown, the comparison table and its fake sortable headers, the alphabetical order, the narrative snippet (150-char hard cut), the mobile card variant. The page keeps one list component on every viewport; the desktop is the same list with wider gutters and two columns for the House group at ≥880. Comparison is by chamber, district and tenure only — non-ordinal facts.

### Member `/member?id=S000148` — a profile column

**For:** who this person is and how they have actually voted, in plain English, within two mobile screens.

**Above the fold, mobile:** masthead + edition line; back link ("← New York's 28 representatives"); the protected broadsheet header (bordered photo with monogram fallback, kicker "U.S. Senator · New York", H1, byline "In Congress since 1981 — House 1981–1999, Senate since 1999. Not on the ballot this November."); the four-cell fact strip ("Roll calls voted 1,060 of 1,061", "Record covers Jan 2021 – Aug 8, 2026", "Votes most often on Economics and public finance", "Party: Hidden — show"); Share + Congress.gov. "At a glance" begins at the fold edge.

**Above the fold, desktop:** header with the fact strip in a row; the two-column body begins (7:4): main column = at a glance + key votes; side column = sponsored, money, ballot.

**Modules in order:**
1. Header (above). Every figure comes verbatim from `stats` (`total_votes − not_voting_count` of `total_votes`), `terms`, `narrative_top_areas[0]`, and the Senate-seats-up list. One sticky element on the page: a 44px running head (name · seat) that pins at the top once the header scrolls out, on every viewport. No sticky tabs, no sticky filters.
2. At a glance: the AI narrative, first three sentences visible, the rest behind "Read the rest" (a native `<details>`), provenance line "Written by AI on June 13, 2026 from roll calls through that date — votes since then appear below but are not in this summary" with a methodology link. The narrative's `generated_at` is the date.
3. Key votes: "Ten votes that show the record", one list ordered by date, each row = vote chip (Yes / No) + Playfair headline linking to `/bill` + one meta line (bill code · plain outcome with tally · date · policy area). The selection rule is printed in the section sub ("Chosen by rule, not by editors: final votes on bills with a plain-English summary, one per bill, spread across topics — six where he voted yes, four where he voted no") instead of being silently asymmetric.
4. The record: "Every roll call, by bill". Controls are two native 16px selects (Topic; Show: bills with a plain-English summary / all bills and resolutions / amendments and motions too) and a status line ("Showing bills with a plain-English summary · 259 of 268 bills · show all"). Rows are grouped by `bill_id`: vote chip = the member's position on the final roll call; kicker bill code; a status seal derived from the last result ("Passed the Senate 90–6", "Blocked in the Senate", "Adopted 50–47"); date; headline = one-liner, or the official title clamped to two lines plus the pending chip; a `<details>` "N roll calls on this bill" listing each step in plain phrases ("Vote to end debate and take it up · Agreed 89–4 (needed 60)") with the "Roll call source →" link as a sibling, never nested in a link. Amendments and motions (`bill_id` null) collapse under one disclosure per page ("3 amendment and motion votes in this period"), quoting the amendment text verbatim and never inventing a parent bill (the data has none). Pagination is server-side by bill ("Bills 1–8 of 259 · Older votes →") and moves focus to the section heading.
5. Side column (inline sections, no tabs): Sponsored (count + first two rows + "All 6 sponsored bills →"); Money ("$2.8 million raised, 2024 cycle" headline, four cells: individuals, PACs, spent, FEC source with its `last_updated` date; hidden entirely for the 70 members without data); November 3 ("Not on the ballot — this Senate seat is next up in 2028. Every House seat, including all 26 New York districts, is on this year's ballot" — for House members: "On the ballot this November").
6. Footer.

**House members** use the identical template: kicker "U.S. Representative · New York's 4th District", byline "In Congress since 2025", fact strip with the same four cells, ballot section "On the ballot this November". Their 840KB vote files never reach the browser: the record is paginated server-side (`/api/members/{id}/votes?offset&limit&grouped=1`).

**Cut, and why:** the donut, the attendance bar and its ring, the three stat tiles (all restate two numbers now in the fact strip), "What They Fight For by Topic" (editorial in name, direction-model bars unexplainable in one line; the topic select gives the same navigation without a judgment), the Service History card (folded into the byline), the tab bar, the Copy Link pill, the always-empty `vote-item-title`, "Bill Bill Passed" result strings, the empty policy chips, the per-page "Reveal party" pill (now one line in the fact strip).

### Bill `/bill?…` — a story with a fact box

**For:** "Congress just voted on X — what does it do, and how did my representative vote?"

**Above the fold, mobile:** masthead + edition line; kicker "H.Con.Res. 108 · 119th Congress · Failed in the House"; H1 = AI one-liner ("Order U.S. troops out of hostilities in Lebanon within seven days"); deck = official title in Lora 500; the outcome sentence in body serif ("The House rejected it, 189 to 235, on June 30, 2026."); the labelled tally bar. The fact box begins at the fold edge.

**Above the fold, desktop:** headline column (7) + fact box (4) side by side: the fact box is a hairline-ruled `<dl>`: Sponsor (linked only if in `members.json`, else "Rep. Rashida Tlaib (MI) — not in ClearVoting's coverage yet"), Cosponsors (count), Topic (`policyArea.name`), Introduced, Latest floor action (derived from the votes index, formatted date), Congress.gov (the canonical `legislationUrl`), Share.

**Modules in order:**
1. Story head (above). Server-rendered so the crawler and the share card see the answer; `<title>` = "H.Con.Res. 108 — Order U.S. troops out of hostilities in Lebanon within seven days | ClearVoting".
2. What it does: the section-mark provision bullets, followed by the AI provenance line ("Summarized by AI from the official text on {generated date}").
3. Official summary: muted serif, collapsed under "Show the official summary" — the existing `sanitizeHtml`/`SAFE_TAGS` block stays untouched.
4. The vote(s): one block per roll call: a caption that doubles as the visible heading ("House roll call 232 · June 30, 2026 · Vote to adopt · Rejected 189–235"), the tally bar, then **Your delegation** (when a ZIP or state is remembered: 2 senators + your House member(s) as person rows with vote chips; otherwise "Find your representatives' votes — enter your ZIP" inline), then "All 431 votes" collapsed: a state select + name filter, a two-line list on every viewport (name + state, vote chip right-aligned, name linked for the 150 covered members), never a horizontally scrolling table. One page-level party toggle in the roll-call head re-renders every block from one state; the party column, when shown, says "Democrat"/"Republican"/"Independent".
5. Footer.

**No-summary state (H.R. 4795 and the 59 others):** H1 = official title in Playfair (the only headline available), no deck, the outcome sentence, the tally, the fact box, then a neutral empty state in place of "What it does": "We haven't written a plain-English summary for this bill yet. Summaries are current through June 30, 2026." — no section-mark bullet, no AI disclaimer, no "Generating…" copy; the official summary's first paragraph is promoted open (not collapsed) so the page still answers "what does it do" from the official record.

**Cut, and why:** "What People Are Saying" (unsourced AI-drafted opinion cannot sit under a masthead that says "No opinions"; see (h) C-2); the table of contents chips; the tag row (`subjects` is a count, not a list); the floating Copy Link; "Latest action (2026-06-30): Motion to reconsider laid on the table…"; the donut with 431 in the centre; "Yea/Nay" and raw question strings (mapped to plain phrases through one shared formatter).

### About, Methodology, Privacy, and 404 — the trust pages

**For:** who runs this, how neutrality is enforced, where the data comes from, what is collected, and a corrections log. The footer's three links become three real destinations.

- `/about` (S): who (a name and a contact), why, funding ("volunteer, unfunded"), coverage ("four states, 150 members, every roll call since January 2021"), what the site does not do (no scores, no rankings, no endorsements, no party labels by default). Plain static HTML; no `opacity:0`, no observers, no animation.
- `/methodology` (S): sources and sync cadence; the neutrality rules as a list generated from `ai_summary.py` at build of the page (or the number dropped: "our rules for neutrality", listed in full); what AI writes and what it never touches; known gaps, dated ("Plain-English summaries are current through June 30, 2026 — 60 of 1,610 bills are waiting"; "Member narratives were written between March 16 and July 2, 2026"); how the key-votes rule works; the direction model, if it is ever surfaced again; a dated corrections log (a static list in the page, newest first).
- `/privacy` (S): what the notify form stores (email, state, timestamp, in a private Google Sheet), what feedback stores (message, page, timestamp), retention, and — once fonts are self-hosted — "this site makes no third-party requests except member photos from congress.gov."
- `/404` (S): masthead, kicker "Not in this edition", H1 "We don't have that page", one sentence ("The link may be old, or the bill or member may be outside our four-state coverage."), the ZIP finder, and links to the front page and the four states. Real 404 status for unknown member ids and bill keys (F52), navy button, no red.

Above the fold on every trust page is the H1 and the first paragraph of real text. All four are static files served through `_serve_html` so the server still owns `<title>` and `</head>`.

## (d) Visual system decisions

**One token set, one `:root`** (in a new `static/css/clearvoting.css`; `styles.css` and `broadsheet.css` are retired in the same PR, not pruned):

| Token | Value | Use |
|---|---|---|
| `--paper` | #F5F6FA | the page ground, everywhere |
| `--white` | #FFFFFF | footer, dialog, inputs, the two note blocks (split-ZIP and coverage), state links — never a card |
| `--ink` / `--ink-soft` / `--ink-meta` | #1B1B1B / #5B616B / #5F656D | body / decks and secondary prose / kickers, datelines, meta. `--ink-meta` is 5.45:1 on paper, 5.88:1 on white; `--text-dim` #8D9297 is deleted as a text colour |
| `--navy` / `--blue` / `--blue-dim` | #112E51 / #0071BC / #205493 | display type, rules, seals, buttons / links and focus rings / kickers and link hover |
| `--yes` / `--no` | #2E8540 / #CD2026 | **only** inside the tally bar and its numeric labels; `--no` is also the text colour of the "No" vote chip. `--accent-red` and the duplicate `--vote-nay` are deleted; buttons are navy; errors are ink on a hairline, never red |
| `--rule` / `--rule-soft` | #D6D7D9 / #E8E8E8 | 1px hairlines / the tally track |

**Colour semantics in one sentence:** navy says "this is the record", blue says "this is a link", red says "voted No", green only ever appears next to a number in the tally bar, and nothing else on the site is coloured.

**Type roles (8-step scale, one family per role):** `--t-kicker` .75rem Inter 700 uppercase .16em (floor: 12px, never below); `--t-meta` .8rem Inter; `--t-ui` .875rem Inter (controls, signal lines); `--t-body` 1rem Lora; `--t-lede` 1.125rem Lora; `--t-h3` 1.35rem Playfair; `--t-h2` clamp(1.45rem,3vw,2rem) Playfair; `--t-display` clamp(2.3rem,5vw,3.4rem) Playfair. Row headlines are Playfair 1.15rem; the *fallback* headline (an official title standing in for a one-liner) is Lora 500 1.05rem clamped to two lines — the typeface itself tells the reader "this is the official text, not our translation". Literal `font-size` values outside the scale are forbidden; every input, select and textarea is 16px (no iOS focus zoom).

**Spacing:** a 4px scale (`--s1` .25rem … `--s16` 4rem). Section rhythm is identical on every page: 3px double rule + 2.5rem above every top-level section, 1.5rem between section head and content, 1rem row padding inside rule lists.

**Rules, not cards.** Sections are separated by double rules, items by hairlines. There is no `box-shadow` anywhere and no `border-radius` except 4px on the two chips and 8px on form controls. The only bordered rectangles are the four state links (1px hairline, navy inversion on hover/selected), the photo frame, and the native `<dialog>`. The two note blocks (split ZIP, coverage note) are a 3px left rule on white — a newspaper's boxed note, not a card.

**Exactly two chips.** *Status seal* (Inter 700 uppercase, 4px radius): filled navy = final outcome ("Passed the House"), outlined blue = still moving ("Still in Congress", "Blocked in the Senate"), dashed grey = "Plain-English summary coming". *Vote chip* (same shape): "Yes" navy outline, "No" red outline, "Didn't vote" grey. No topic pills; topics are text in the meta line.

**The tally bar** is the single vote-outcome component (`role="img"` + `aria-label` "Passed the House, 237 voted yes, 169 voted no"), always followed by "237 voted yes / 169 voted no" in its own colours. One tally-label format site-wide: "237 yes – 169 no".

**One vocabulary, four formatters** in a small shared `static/js/format.js` (also mirrored in `app/main.py` for server rendering): `formatBillCode` (Congress.gov form: "H.Con.Res. 108"), `formatDate` (one input shape after Senate `vote_date` is normalised at sync), `plainQuestion` ("On Passage" → "Final vote to pass", "On Agreeing to the Resolution" → "Vote to adopt", cloture → "Vote to end debate (needed 60)", "Motion to Proceed" → "Vote to take it up", "Motion to Discharge" → "Vote to bring it to the floor", "Motion to Table" → "Vote to set it aside"), and `outcomeSentence` (chamber + question + result + counts → "The House rejected it, 189 to 235, on June 30, 2026").

**The feedback control:** no floating pill on any viewport. The opener is a footer button ("Report an error on this page", keeps `id="feedback-open"`) plus a masthead nav item is *not* added (nav stays four items). The panel is a native `<dialog id="feedback-modal">` with `aria-labelledby`, a real `<label>`, `role="status"` on `#feedback-status`, focus returned to the opener on close; all `#feedback-*` ids and `#data-freshness` are preserved so `feedback.js` keeps working. Every AI module's provenance line also links to the same opener.

**Touch and focus:** one interactive-size token `--tap: 44px` on nav links, footer links, state links, buttons, inputs, selects, disclosure summaries and row links; one global `:focus-visible` rule (2px `--blue`, 3px offset); every per-selector `outline:none` and low-alpha box-shadow ring is deleted.

**Breakpoints:** exactly two, 560 and 880, declared once at the end of the stylesheet; JS reads the same values through `matchMedia`. Tablet (768–1024) gets the ≥560 layout with the 1.5rem gutter until 880, then the two-column layouts. Definition-of-done checks: `scrollWidth <= innerWidth` at 320 and 375; no text under 12px; every token ≥4.5:1 on both `--paper` and `--white`; no control under 44px.

**Print:** a small `@media print` block (nav, actions and dialog hidden; white ground) because a civic record gets printed. Dark mode and forced-colours: deferred, but the system survives forced-colours because every meaning is carried by text and borders, never by fill alone.

## (e) Finding coverage

| Id | Sev | How this approach resolves it |
|---|---|---|
| F01 | P0 | The Record lists newest bills by `latestAction.actionDate` regardless of summary; unsummarized rows get the official title in Lora 500 + "Plain-English summary coming"; "As of {sync date}" on the section, a date on every row, and the coverage note "summaries current through June 30, 2026". No freshness signal describes anything other than the fact beside it. |
| F02 | P0 | Hero link text is conditional ("See the vote and the official summary →" when no `one_liner`); `/ai-summary` returns `{available:false}` for missing summaries; the bill page renders a neutral empty state with no section-mark bullet, no AI disclaimer, the official summary's first paragraph promoted; "Loading summary…" replaces "Generating…". |
| F03 | P1 | ZIP field is the first control on every viewport; `GET /state?zip=` (no JS needed) and `/api/districts/{zip}` read the Census crosswalk file (sanctioned new data file, attributed); split ZIPs show every district ≥5%; unknown and out-of-coverage ZIPs have designed states. |
| F04 | P1 | One delegation surface (`/state?code=XX`), state links are real links, the homepage renderer is retired; senators first, House by district; "voted yes" vocabulary; party toggle present; `document.title` overwrite removed. Last ZIP/state remembered in `localStorage` (see (h) C-13). |
| F05 | P1 | `data/synced/state_overview/{code}.json` precomputed at sync; the delegation endpoint is one small file read; `/state` is server-rendered from it; the ZIP path never waits on a 28-file scan. |
| F06 | P1 | Stat boxes, Total Votes, participation bars, thresholds and metric sorts are deleted. Roster rows carry photo, name, seat, tenure, ballot status and one dated linked vote. Participation appears once, as words, in the member fact strip. |
| F07 | P1 | Member order is header → fact strip → at a glance (3 sentences) → key votes → the record; donut, attendance, stat tiles, topic bars, Service History and tabs are cut. First key vote is within the second mobile screen. |
| F08 | P1 | Key votes are linked rows with vote chip, plain outcome + tally, date and topic; the same row component renders roster signal lines and the record; the selection rule is printed. |
| F09 | P1 | The record is grouped by `bill_id`, one row per bill with the final position and a "N roll calls" disclosure; default view is bills with plain summaries; amendments/motions collapse under one disclosure with verbatim text and no invented parent; the empty title div is gone. |
| F10 | P1 | Bill roll call leads with a captioned outcome band, then "Your delegation" from the remembered ZIP/state, then "All 431 votes" collapsed with state select + name filter, two-line rows, covered names linked. |
| F11 | P1 | `plainQuestion` + `outcomeSentence` + one vote chip ("Yes / No / Didn't vote") + one tally format used by every page; official terms survive only in the roll-call caption and source link. |
| F12 | P1 | Bill H1 = `one_liner`, deck = official title; server `<title>` = "{code} — {one-liner}", official title truncated at ~70 chars on a word boundary when no summary; og:title capped. |
| F13 | P1 | Module cut (see (h) C-2); About no longer describes it; vote colours are never used for anything but the tally bar. |
| F14 | P1 | Fresh mobile-first stylesheet, responsive rules co-located after base rules, two breakpoints; `minmax(0,1fr)` everywhere; the scroll-width smoke check is in the definition of done. |
| F15 | P1 | Every inner page is rebuilt on the rule/whitespace model; the `.glance-card/.viz-section/.bill-section/.state-stat/.comparison-table/.mobile-card` rules are not re-skinned — the files that hold them are retired. |
| F16 | P1 | One meta token at #5F656D (5.45:1 on paper); `--text-dim` deleted as a text colour; 12px floor. |
| F17 | P1 | The hero is a structured card; headline = one-liner or official title in body serif; never a sentence template. |
| F18 | P1 | `/about`, `/methodology`, `/privacy` shipped as static pages with the footer repointed; fonts self-hosted so the privacy page can say "no third-party requests". |
| F19 | P1 | Server renders the first block of `/state`, `/member`, `/bill` and the homepage's edition line, latest-vote card and Record from data already in process; JS only paginates, filters and renders the remembered-ZIP block. |
| F20 | P1 | `og:image` routes for member/bill/state (see (f)); the three `document.title` lines deleted; one "Share" action per page header (`navigator.share`, clipboard fallback with a visible "Link copied" status), always the canonical URL. |

**P2/P3 also resolved by this approach:** F21 (finder in the first mobile screen), F22 (no entrance animation; static trust pages), F23 (no floating pill), F24 (native `<dialog>`), F25 (one toggle component, one label, `aria-pressed`, session-scoped reveal, full party names), F26 (all counts verbatim from `stats`), F27 (result vocabulary via `plainQuestion`; no empty chips; amendments labelled as such), F28 (module cut), F29 (3-sentence clamp), F30 (one sticky element; native selects; 16px controls), F31 (`formatBillCode`), F32 (derived status seal; one date helper; Senate dates normalised at sync), F33 (coverage-aware sponsor linking + cosponsor count), F34 (person rows on every viewport; whole row tappable; no colour-only bars), F35 (red = No only; navy buttons), F36 (no PAC/individual bars — text cells; every SVG/bar composite has `role=img`), F37 (official title only on the bill page and, clamped, on unsummarized rows), F38 (`/bills?topic=&q=` as URL state; offset bug fixed by moving the increment after the fetch), F39 (state select in the notify form; confirmation echoes it; navy button), F40 (every AI module dated; footer separator rendered only with a value), F41 (edition line with the election date; ballot status per member from the sanctioned seats-up list), F42 (coverage stated at the point of choice), F43 (one `role=status` line per section; content containers static), F44 (focus moved to the section heading on pagination; `aria-expanded` on the notify disclosure via `<details>`; `autocomplete="email"`), F45 (one global `:focus-visible` rule), F46 (H1 on member, bill, about; `feedback.js` selectors updated in the same commit), F47 (`--tap` token), F48 (`<caption>`, `scope`, `<th scope=row>`; no fake sortable headers — the desktop table is gone), F49 (fresh ~25KB stylesheet; old files retired), F50 (one token set; JS applies classes, never inline colours), F51 (two breakpoints, declared once, mirrored in `matchMedia`), F55 (server-rendered first paint; self-hosted woff2 with `size-adjust` fallbacks), F56 (inline dated Sponsored and Money sections), F57 (8-step scale), F58 (two chips, two radii), F59 (4px spacing scale, one section rhythm), F60 (`prefers-reduced-motion` read once in JS; rows are real `<a>`; no tabs), F61 (error copy owns the failure), F62 (narrative clamped, dated, and subordinate to the linked key votes).

**Not addressed, honestly:** F52 (index hygiene: canonical normalisation, real 404s and `/favicon.ico` are included; per-URL `lastmod` and un-mounting `/static/*.html` are deferred), F53 (partly: static and API cache headers included; shell caching limited to `s-maxage=600`, see (h) C-8), F54 (partly: server-side pagination and one `/api/members/{id}/page` consolidation are included; the bill page's per-vote serial fetch is folded into one `/votes` response), F63 (an ops decision — paid instance or pinger — outside the design; the static shell cache means chrome shows during a cold start).

## (f) Data and backend touches (small, each named)

1. **ZIP crosswalk** — `data/zip_districts.json` (from `tools/data/build_zip_crosswalk.py`; Census 2020 ZCTA↔CD119 relationship files, public domain, attribution in a `_source` key and on `/methodology`). New route `GET /api/districts/{zip}` in a new `app/routers/districts.py` (loads the file once at startup, returns `{zip, state, districts:[{district, share}]}` or 404). `app/main.py` `/state` accepts `?zip=` and resolves it in-process.
2. **Senate seats up in 2026** — `data/senate_2026.json` (hand-kept list of bioguide ids, `_source: senate.gov class list`). Read by `data_service.get_member_detail` to emit `on_ballot_2026: bool` and `next_election_year`.
3. **Precomputed state files** — `data/synced/state_overview/{code}.json` written by the sync script (`scripts/` — the same job that writes `member_votes/`): senators + House by district with tenure, photo, `on_ballot_2026`, and each member's latest plain-summary vote. `app/routers/members.py` `/{state_code}/overview` and `/{state_code}` become file reads.
4. **Server-rendered content blocks** — `app/main.py`: `_serve_html` gains a second injection point, a literal `<!--content-->` marker inside `<main>` in each shell (the `<title>`/`</head>` contract is untouched). Small Jinja-free f-string renderers in a new `app/render.py` produce the header/fact-strip/first-block HTML for member, bill and state, and the edition line + latest vote + Record for home, using the same formatter functions as `format.js`.
5. **Record fallback + freshness** — `app/routers/bills.py` `/api/bills` default drops `summarized_only`; the response carries `summary_available`, `latest_action_date`, and the derived floor status from the votes index. `/ai-summary` returns `{available:false}` instead of the apology string (`app/routers/bills.py:60`).
6. **Formatters** — `static/js/format.js` (shared by `app.js`, `member.js`, `bill.js`, `state.js`, `vote.js`) and its Python twin in `app/render.py`; Senate `vote_date` normalised to ISO in the sync script.
7. **Titles and share cards** — `_inject_meta` in `app/main.py`: one-liner-first titles, 70-char word-boundary truncation, `og:image`, `og:image:width/height`, `twitter:card=summary_large_image`. New `app/routers/og.py` renders 1200×630 cards with Pillow (**a new dependency in `requirements.txt`**, not a build step) using the self-hosted fonts, with `Cache-Control: public, max-age=31536000` so Cloudflare serves repeats.
8. **Caching** — `app/main.py`: `/static` `public, max-age=31536000, immutable` (the `?v=` bust exists); `GET /api/*` and `/og/*` `public, max-age=3600, stale-while-revalidate=86400`; HTML shells `public, max-age=0, s-maxage=600, stale-while-revalidate=3600` (see (h) C-8).
9. **Fonts** — five woff2 files under `static/fonts/` (Playfair 700/800, Lora 400/500/400i, Inter 400/600/700); CSP `font-src 'self'`; the googleapis preconnects and allowances removed.
10. **Feedback hooks** — `static/js/feedback.js`: `.member-header h2` → `.member-header h1`, `.bill-header h2` → `.bill-header h1` (the sanctioned coordinated change); `openModal`/`closeModal` call `showModal()`/`close()` and return focus.
11. **404s** — `app/main.py` shell routes return the 404 page with status 404 when the member/bill lookup is empty; `/favicon.ico` route.

Nothing else changes: the Google Sheets write paths, the newest-first bill sort, the `sanitizeHtml` block, server-side party stripping and the sitemap all stay.

## (g) Scope, risks, deferrals

| Piece | Size | Notes |
|---|---|---|
| System stylesheet + formatters + fonts | M | New `clearvoting.css` (~25–30KB), `format.js`, `render.py`; retire two CSS files |
| Home | M | Finder, structured hero, Record with fallback rows, notify with state; server-rendered blocks |
| State | M | Precomputed file, ZIP states, person rows, server-rendered first block; retire `state.js` renderer |
| Member | L | Grouped record with server-side pagination, key votes rows, header/fact strip, side sections; retire `viz.js` |
| Bill | L | Story head, fact box, outcome sentences, "Your delegation", collapsed roll call list, empty state |
| About / Methodology / Privacy / 404 | S | Static pages |
| `/bills` archive | S | Server-rendered dated list with `?topic=`, `?q=`, `?page=` |
| Backend (ZIP route, seats list, precompute, caching, og:image, titles, 404s) | M | Eleven touches above; og:image is the largest |
| **Total** | **L (roughly three to four weeks of an autonomous build loop, one PR)** | Home + State + system first (the path), Member second, Bill third, trust pages and og:image last |

**Risks.** (1) The ZIP crosswalk is land-area share, not population, and ZCTA ≠ USPS ZIP: the split-ZIP copy says "about 72% of its land" deliberately and the unknown-ZIP state points to the district list; the address-level Census Geocoder fallback is deferred. (2) Pillow on a single free-tier worker: mitigated by CDN caching of every card and a static default card if the route fails. (3) Retiring `styles.css` and `broadsheet.css` in one PR means every page must be QA'd at 320/375/768/1280 before merge — the smoke checks in (d) are the gate. (4) The AI sync stays dormant: the design needs no change when it resumes (the pending chip and coverage note simply disappear as data arrives). (5) `on_ballot_2026` depends on a hand-kept list — it is small (the Class 2 seats plus any special elections, about 35 rows) and cited on `/methodology`.

**Deferred to a follow-up.** Address-level lookup via the Census Geocoder; clean-path aliases (`/state/ny`) with 301s; per-URL sitemap `lastmod`; un-mounting `/static/*.html`; dark mode; Spanish (the system's tokenised copy and `lang` attributes make it feasible, but 46 days is not enough to translate 1,550 summaries honestly); a sourced replacement for the arguments module; surfacing `audit_grades.json` "needs review" flags; abuse protection on the two write endpoints; analytics for the two-click metric; the paid Render instance or pinger (ops).

## (h) Appendix C contradictions, resolved with a stated principle

- **C-1 "Voted yes 49%" is the right vocabulary vs. F06 says the percentage is noise.** *Principle: keep the words, drop the statistic.* "Voted yes" is the site-wide vocabulary (vote chip, tally labels, outcome sentences); no rate appears on any list surface. Roster rows carry one dated vote instead.
- **C-2 Keep the both-sides pairing vs. F13 drop it.** *Principle: "Facts only" is a constraint on the body, not a slogan for the masthead — unsourced text does not appear as content.* The arguments module is cut from the bill page and from About until arguments can be attributed to real statements. The neutrality proof point moves to where it is true: party hidden by default, primary-source links in every row, provenance on every AI module.
- **C-3 The Record's mobile stack is clean vs. F37 rows dump legalese.** *Principle: the container was right, the row content was wrong.* The single-column stack stays; official titles leave the row (they live on the bill page as the deck) except when they are the only headline available, where they are clamped to two lines in the fallback face.
- **C-4 Hide campaign finance (F07) vs. show it inline (F56).** *Principle: a dated fact may be shown; an undated one may not.* Money is shown with the cycle in the headline ("$2.8 million raised, 2024 cycle"), the FEC `last_updated` date in the cell, and "The 2026 cycle is not yet in our data" in the sub; hidden entirely when there is no data.
- **C-5 Three sticky layers vs. a new mobile sticky strip vs. "at most one".** *Principle: one sticky element per page, and it must answer "where am I".* The member page keeps exactly one: the 44px running head. Filters and pagination are static; the side column is sticky only at ≥880 where it is not a layer over content.
- **C-6 New data files vs. hard constraint 5.** *Principle: the constraint forbids invented data, not attributed public data.* The brief sanctions exactly two files; both ship with a `_source` key, a build script for the crosswalk, and a `/methodology` entry.
- **C-7 `feedback.js` hooks vs. promoting h2 to h1.** *Principle: a hook is a contract between two files; changing both sides in one commit honours it.* Done as F46 specifies, in the same commit, with a test that both selectors still resolve.
- **C-8 CDN-cached shells vs. personalised first blocks and Record freshness.** *Principle: the server renders only what is identical for every visitor; anything personal is client-side from browser storage and never in the cached HTML. Freshness is measured against the sync cadence: a cache under 1% of the cadence is invisible.* "Your representatives" on the front page and "Your delegation" on bill pages are rendered by JS from the remembered ZIP; shells cache at the CDN for 10 minutes (`s-maxage=600`) against a weekly sync; F01's ten-week staleness is unrelated to a ten-minute edge cache.
- **C-9 On-demand Pillow og:images on a worker with no headroom.** *Principle: render once, serve from the edge.* Cards carry a one-year `Cache-Control` and are cached by Cloudflare per URL; the first request per page costs ~50ms; a static default card is the fallback for any render error.
- **C-10 Key-bills picker is sound vs. its asymmetry is a defect.** *Principle: explain the rule rather than hide it or change it.* The picker's logic is kept; the section sub prints "six where he voted yes, four where he voted no" and why.
- **C-11 "Latest Vote ships hidden" is graceful degradation vs. a layout-shift defect.** *Principle: degrade on the server, not in the browser.* The card is server-rendered when the data exists and omitted when it does not, so it is neither hidden nor shifting.
- **C-12 Five pages assessed vs. six templates.** The 404 page is designed above and gets a real status code.
- **C-13 Remember the last state in `localStorage` vs. never persist the party reveal.** *Principle: persist where the reader is, never what they chose to reveal.* Place (ZIP/state, `cv-zip`) is like a newspaper's local edition and persists in `localStorage` with a visible "remembered from your last visit · change" label; the party reveal is an explicit action that carries across pages within one visit (`sessionStorage`) and resets on the next.

**Appendix C gaps, covered or deferred:** 404 (covered), House-member pages (covered by the same template; server-side pagination for the large files), invalid `?code=` (404 page with the finder), bill data conditions (no roll call → no vote block and the fact box's "Latest floor action: none yet"; many amendment roll calls → collapsed under the bill; both chambers → two captioned blocks under one party toggle; no official summary → the empty state says so; malformed URL → 404), no-JS (every first block and both forms work without JavaScript; nothing starts at `opacity:0`), intermediate viewports (two breakpoints; tablet specified in (d)), print (included), dark/forced-colours (deferred; meaning never carried by fill alone), search states (`/bills` zero-results copy: "Nothing in the record matches 'x'. Try a broader word, or browse by topic."), notify/feedback failures (copy owns the failure; abuse protection deferred), broken photos (monogram behind every image), hero edge cases (structured card handles nominations and Senate votes with no bill via `document`; a tie or voice vote shows the result and no tally bar), keyboard/screen-reader walkthrough (definition of done), Back/forward (the ZIP path is a real navigation; no `pushState`), cold start (deferred to ops; cached shell shows chrome), Spanish (deferred, stated honestly), `members.json` currency (roster date shown on `/state`; a currency check belongs to the sync, deferred), instrumentation (deferred), `needs_review` flags (deferred).
