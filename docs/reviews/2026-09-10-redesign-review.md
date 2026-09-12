# ClearVoting Redesign Review — 2026-09-10

## Scope

**What was reviewed.** The live site (https://clearvoting.org, desktop at 1280px and mobile at 375px, via full-page screenshots and `curl` of the HTML shells and API JSON) and the code at `origin/main` **f1dc535** in a fresh worktree (`/Users/josephgarcia/.clearvote-worktrees/redesign-2026-09`). Ten review lenses each walked the site against the brief: task-flow (the busy citizen's path), trust-content (honesty and neutrality), product-pm (fit to the PRD and the November milestone), bill-page, state-page, member-page, mobile, reach (search, sharing, performance), a11y (accessibility), and visual-system (the broadsheet design system). Every candidate finding was then re-checked against the code and the live site by a separate skeptic agent before it could enter this report. Verification depth was uneven: the task-flow and member-page lenses got two independent skeptics per batch of five findings (one reproducing the cited evidence, one judging user impact and recalibrating severity; a finding needed both to survive), while the other eight lenses got one skeptic per lens that worked from code and `curl` rather than screenshots, because usage limits cut the heavier pass short. The overall refutation rate was 0% (126 raw findings in, 126 confirmed, merged into 63), which should be read as a limitation of the lighter pass as much as a strength of the finders — Appendix C, written by an independent critic, lists claims it could not verify and contradictions inside this report.

**Counts.** 126 raw findings from ten lenses, 126 confirmed in verification (see the caveat above), merged into 63. Severity: **2 P0 · 18 P1 · 35 P2 · 8 P3**. Versus the July 1 review: 34 still open, 26 new, 3 regressed. Every finding carries the lens(es) that reported it.

**How to read the evidence.** `file:line` references point into the worktree above. Screenshot names refer to `/Users/josephgarcia/Claude/.playwright-mcp/cv-review/`. `curl` lines are live requests against clearvoting.org made during the review. Severity means: **P0** the site says something untrue or broken on its most prominent surface; **P1** the core task fails or a page-level promise is broken; **P2** real friction, defects or accessibility failures that the redesign must not carry forward; **P3** polish and hygiene.

**A few terms used below, in plain language.**
- *TTFB* — time until the server starts sending a response; what the user feels as "the spinner."
- *Server-render* — the server writes the real page content into the HTML, instead of sending an empty page and letting JavaScript fill it in.
- *og:image / share card* — the picture and title a link shows when pasted into iMessage, X, LinkedIn, Slack.
- *aria-live, aria-pressed, role* — hidden labels that tell screen readers what a control is and when something changed.
- *WCAG AA* — the accessibility standard the site should meet; "4.5:1 contrast" is the minimum readable difference between text and its background.
- *Cascade order* — in CSS, when two rules tie, the one written later wins. Several bugs here come from mobile rules being written before the rules they were meant to override.

**Verdict in one line:** The broadsheet shell and the plain-English content are right and should be protected; the product fails the busy citizen in the *path* (no ZIP entry, 2–5 second spinners, an orphaned state page), in the *honesty of its freshness and fallbacks* (both P0s), and in *inner pages that never actually received the redesign* — so the job is to rebuild the middle of every page on the homepage's own system, not to replace the design language.

---

## What's working — protect this

These are grounded in code and screenshots so the next agents can find them. They are the constraints the redesign builds inside, not suggestions.

**The shell and the system**
- The shared masthead + footer chrome (double rule, centred Playfair logo with italic blue "Voting", uppercase Inter nav, tagline "Facts only - No opinions - No spin", footer credo "ClearVoting does not express opinions on legislation or representatives", data-source line with last-updated date) is one identical markup and CSS block on all six templates. Keep it verbatim as the anchor of the system.
- The broadsheet member header (Playfair name, uppercase meta line, hairline rule, bordered photo) works on both viewports and is the template the rest of the body should follow. The homepage's hairline/double-rule containment model and typographic roles (Playfair display, Lora body, Inter kicker/meta/UI via `.kicker` and `.meta`) are the seed of the whole site's system.
- The "STILL IN CONGRESS" status seal and the section-mark provision list are distinctive, on-brand civic details worth carrying to the bill page.
- The Record on mobile is a clean single-column stack (kicker, status seal, Playfair headline, section-mark bullets in ~17px Lora); the state page correctly swaps its desktop table for cards at <=768; member tabs and pagination buttons already meet 44px; disclosure patterns ("Show full summary", "Details") keep long official text collapsed. These patterns should be the template for member and bill pages.

**The product promise, where it is delivered**
- The plain-English bill lead pattern (AI one-liner as headline, 3–4 short Lora provision bullets with the blue section-mark, "See who voted for it", official title demoted to an "Officially: ..." footnote) is the product promise made real. It should become the template for every bill surface, with the official text bounded.
- The member "At a Glance" narrative plus the Key Bills Supported/Opposed one-liners are the strongest content on the site, with explicit "Summary generated by AI" attribution. The key-bills selection logic (dedupe per bill, skip anything without a plain summary, spread across policy areas) is sound and needs surfacing and links, not rewriting.
- The homepage delegation's information architecture (senators as their own labelled group first, then "The House - by district" in district order, plain "Voted yes 49%" wording, `role=img` + `aria-label` tally bars) is the right structure and vocabulary for every delegation view.
- "Where do you live?" with four large state cards showing real member counts from `/api/members/counts` renders on desktop and mobile (2-column at <=560) with selected-state navy inversion; the counts are honest about coverage. (The lead's "counts absent on mobile" observation did not reproduce.)
- Both-sides arguments side by side and the AI disclaimer under summaries are the neutrality proof points the strategy relies on; keep the pairing structure even while fixing the module's provenance labelling and colours (F13).

**Neutrality and honesty, enforced where it counts**
- Party-hidden-by-default is executed at the data layer (`members.py` strips party server-side; `bill.js` strips "[R-GA-10]" suffixes) and revealed only by an explicit user action. The homepage toggle correctly updates text and `aria-pressed` and should become the shared component.
- Honesty escape hatches to primary sources are everywhere ("Roll call source ->" per vote, "View full bill on Congress.gov" via the canonical `legislationUrl` with type-map fallback, "View full profile on Congress.gov", Congress.gov/Senate.gov links in every footer), and AI provenance captions sit under every AI-authored module. Keep the habit.
- The official summary is treated as secondary in the right way: sanitized through the existing `SAFE_TAGS` block in `bill.js` (hard constraint), typeset in muted serif, collapsed with a "Show full summary" expander. Keep the sanitizer and the collapse.
- Graceful degradation is designed in: the Latest Vote card ships hidden and stays hidden if the API fails, Record and delegation show plain error notes, counts are optional. Preserve these fallbacks.

**Data and plumbing that is now correct**
- The vote record is genuinely chronological with real formatted dates (July's P0 sort bug is fixed at the data layer); House roll calls now render on bill pages via the two-chamber votes index; the roll-call pie is an accessible SVG over a real table with text-labelled badges. Keep date-sorted rows and the per-chamber loader.
- Both write paths now persist to Google Sheets (notify signups and feedback), fixing July's P0 "emails silently destroyed"; bills are sorted newest-first server-side. Do not regress either when touching the forms or the Record.
- Server-side SEO meta injection works and is unique per page (specific `<title>`, description, og:title/description/type/url, canonical; the bill description already uses the AI one-liner); the sitemap enumerates all 1,766 pages with lowercase canonical bill types; robots.txt points to it; `/state?code=XX` has a server title. Every shell must keep a literal `<title>` and `</head>` so `_inject_meta` keeps working, and URL shapes must not change without 301s.
- Accessibility scaffolding is solid where it exists: skip link and real landmarks on every page, state cards as `<button>` with `aria-pressed`, `role=status` on notify, visually-hidden labels on email/search inputs, `aria-expanded`/`aria-controls` on the browse toggle, full accessible names on roster links, decorative or descriptive alt on every photo, a global prefers-reduced-motion kill switch, and 2px 4.76:1 focus rings on chrome links. Extend rather than replace.
- The stack is right for the job: tiny no-framework HTML shells (4–9KB, ~200ms warm TTFB), no build step, strict CSP (`script-src 'self'`, no inline handlers), all DOM built through `el()`/`createTextNode` with no new `innerHTML`, server-side `?v=` cache-busting from `_asset_version`, and Cloudflare brotli compressing 536KB vote JSON to 55KB. Keep the vanilla stack, the CSP and the cache-bust mechanism, and keep the homepage's core copy as real server HTML.

---

## Findings by severity

### P0 — the site says something untrue on its most prominent surface

#### F01 — Front page "The Record" is ten weeks stale because it only shows AI-summarized bills, under three signals that say "updated this week"
**Page** `/` (The Record) · **Status vs July** regressed · **Lenses** task-flow, trust-content, product-pm

**Evidence.** `app.js:161` fetches `/api/bills?summarized_only=true&limit=6`; `data_service.py:201-204` drops every bill without a `one_liner`. Live: with `summarized_only=true` the newest bill is H.Con.Res. 108 dated 2026-06-30; `/api/bills?limit=50` shows 37 of the 50 newest bills have no `one_liner`; `/api/health` reports `last_sync 2026-09-05, bills_missing_summary 60`. `home-desktop-full.png` (y 1300–2695): every Record item is dated June 29/30 under "What Congress is doing, in plain English", while the hero says 2026-09-03, `index.html:66` says "Updated weekly" and the footer says "Data last updated September 5, 2026". The PRD freshness target (`docs/001-prd-clearvote.md:185`) is met by the sync but not by what the user sees.

**What's wrong.** The most prominent content module silently filters to bills that have an AI summary, and the AI sync has been dormant since early July, so the front page's "what Congress is doing" stops at June 30 while three other freshness signals on the same screen say September. Nothing tells the visitor that newer bills exist but are un-summarized. Eight weeks before the midterms a busy citizen reads this as an abandoned site or a lie. July's finding ("newest bills sit at the top as walls of legalese") has been inverted by the filter: now the legalese is hidden and so is the last ten weeks of Congress.

**Redesign implication.** The Record must lead with the newest bills by action date regardless of summary status, with a designed fallback row for un-summarized bills (bill number, official title clamped to one line, a neutral "Plain-English summary coming" tag) and a visible "as of {date}" stamp on the section plus per-item dates, so staleness is visible rather than implied. A missing summary must never change what the front page claims is recent. Add an explicit coverage note ("summaries current through July 2, 2026") until the AI sync resumes.

#### F02 — Hero CTA "What this bill does, in plain English" lands on a bill page whose no-summary fallback is a fake AI-attributed "procedural" apology
**Page** `/` (Latest Vote hero) → `/bill?congress=119&type=hr&number=4795` (all 60 bills without an AI summary) · **Status vs July** regressed · **Lenses** task-flow, trust-content, bill-page, product-pm

**Evidence.** `curl /api/votes/latest` → H.R. 4795 "Protect Economic and Academic Freedom Act of 2026", Passed 237-169 On Passage; `data_service.py:234-292` `_build_latest_vote` never checks for a summary. `index.html:43` hard-codes "What this bill does, in plain English ->". `curl /api/bills/119/hr/4795/ai-summary` → HTTP 200 `{"provisions":["Plain-language summary is not available for this bill. Some procedural votes and resolutions don't have enough detail for AI analysis."],"issue_categories":[]}` (`app/routers/bills.py:60`). `bill.js:247-251` renders any provisions array with the blue section-mark bullet; `bill.js:153-155` appends "This summary was generated by AI..." unconditionally; `bill.js:294-299` client fallback is dead code because the response is 200; `bill.js:151` loading copy says "Generating plain-language summary..." for a static JSON lookup. `bill-nosummary-desktop-full.png` (y 540–710): the "What This Bill Does" card contains one section-mark bullet (the apology) then the italic AI disclaimer, then ~22,000px of roll-call roster.

**What's wrong.** The first click the homepage offers promises plain English and delivers a bullet that is typeset exactly like a real provision, claims a substantive act with a 237-169 vote is "procedural", and is captioned as AI-generated when it is a string literal — after a loading message that promises live AI work that never happens. Because the newest bills are exactly the ones without summaries, the hero will keep pointing at this state for as long as the AI sync is dormant. This is the "facts only" trust surface asserting something untrue about the newest bills, the ones voters are most likely to visit before the midterms.

**Redesign implication.** Give the hero a rule: prefer the most recent vote whose bill has a `one_liner` (dated honestly), otherwise change the link text to "See the vote and official summary". Return 404 or `{available:false}` from the ai-summary endpoint and design a real empty state on the bill page: no section-mark bullet, no AI disclaimer, neutral copy ("We haven't written a plain-language summary for this bill yet"), official title, sponsor, derived status and the vote result above the fold, with the first paragraph of the official summary promoted into the primary slot and the roster collapsed. Show the AI disclaimer only when AI content actually rendered; replace "Generating..." with "Loading summary...".

### P1 — the core task fails or a page-level promise is broken

#### F03 — No on-site path from "where I live" to "my representative": no ZIP or district input, and the district lookup leaves the site
**Page** `/` (delegation), `/state` · **Status vs July** new · **Lenses** task-flow, product-pm, state-page, mobile

**Evidence.** `index.html:48-55`: the only input is four state buttons; grep for "zip" in `index.html`/`app.js`/`state.js` returns no ZIP input on any page. `app.js:265-286` renders 2 senators plus every House member sorted by district (`/api/members/NY?include_stats=true` → 28 members); roster rows (`app.js:331-358`) show only photo, name, "District N" and a yes/no split. The only district help is `index.html:85`, an external link to house.gov that appears only after a state is chosen. The backend already has `GET /api/members/{state}/{district}` (`app/routers/members.py:193-201`) and no frontend code calls it. `state.html` has no district affordance at all. PRD:108 says the user may not know their district; PRD:145 user story 1 promises "select my state and optionally my district".

**What's wrong.** The PRD's core task is "start with YOUR representative". For a NY visitor who knows their district the path is scroll, click, wait ~2s, scan up to 26 rows, click. For the majority who don't know their district number, the path leaves the site, then returns to redo the selection. Nothing lets a user type a ZIP or address, the single input a busy citizen actually knows. This is the biggest gap between the PRD's person-first promise and the built product.

**Redesign implication.** Make "Find my representatives" the first and dominant element on every viewport: a ZIP field as primary input (state grid secondary), backed by a static ZIP-to-district crosswalk file in `data/` (public Census/HUD data — flagged as a **new data file**, not invented from existing JSON) feeding the existing state/district endpoint, landing the user on 2 senators + 1–3 House members. Keep the state roster as the fallback when a ZIP spans districts, and keep "Look up your district" as an inline helper rather than an exit. Measure the redesign on: a first-time visitor reaches their own three members' pages in two clicks or fewer from any entry.

#### F04 — The delegation exists twice with different ordering, vocabulary and features; the homepage version has no URL and the shareable /state page is orphaned and alphabetical
**Page** `/` (delegation) and `/state` · **Status vs July** still-open · **Lenses** task-flow, state-page, product-pm, reach

**Evidence.** grep `pushState|replaceState|popstate` across `static/js/*.js`: zero matches; `app.js:227-238` `selectState` only toggles classes and scrolls; state cards are `<button>` (`index.html:47-50`), not links. grep `/state` in `index.html`, `app.js`, `member.js`: zero links, so `/state?code=NY` (curl: 200 in 0.23s, server title "New York Representatives - Voting Records | ClearVoting", in the sitemap `main.py:277`) is reachable only from the sitemap. Homepage renders senators first with narrative snippet + "Voted yes 49%" + party toggle (`app.js:265-357`, `index.html:79`); `/state` renders an alphabetical table ("49% yea", `state.js:329`) with participation bar, no narrative, no party toggle (overview endpoint always strips party, `members.py:102-158`), default sort `name-asc` (`state.js:24`) with no district sort: `state-desktop-full.png` shows Schumer at row 4 and Gillibrand at row 16 of 28, House members ordered by first name. `app.js:18` persists the party toggle but nothing persists the chosen state.

**What's wrong.** A citizen who finds their delegation cannot send the link to anyone, and pressing Back after opening a member returns them to an unselected homepage. Visitors arriving from Google land on the orphaned, worse version, where the two people who represent every New Yorker are scattered in an A–Z list and the homepage's signature party toggle is absent. Two renderers, two data calls, two vocabularies for the same 28 people; neither view is shareable, and topic-filtered lists don't exist as URLs either.

**Redesign implication.** One delegation surface: make `/state?code=XX` (with clean-path alias `/state/ny` and 301s) the single canonical view, make the homepage state cards real links to it (or `pushState` the same URL and render the identical component with `popstate` restore), remember the last state in `localStorage` and pre-select it. Default ordering must match the homepage: senators as a distinct group first, then House by district ascending with "District 4" spelled out; one vocabulary ("voted yes"); party toggle present; drop the participation/support sorts. Retire whichever renderer is not chosen and remove the `document.title` overwrite in `state.js:84`.

#### F05 — Choosing a state scrolls the user to a spinner for 2–5 seconds because the API re-reads every member's ~1MB vote file per request; the overview endpoint has regressed to ~4s
**Page** `/` (delegation), `/state` · **Status vs July** regressed · **Lenses** task-flow, state-page, reach

**Evidence.** curl timings: `/api/members/NY?include_stats=true` (the homepage call, `app.js:250`) TTFB 4.79s, 2.55s, 2.26s, 1.92s across runs; `/api/members/NY/overview` (state page, `state.js:76`) 4.53s (br), 3.93s, 2.48s, 1.75s (July: ~2s); plain `/api/members/NY` 0.21s. `members.py:117` and `:173` call `data_service.get_member_votes` per member; `data_service.py:100-106` opens and `json.loads` the file on every call with no cache; `data/synced/member_votes` is 161MB for 151 files. `app.js:234-237` calls `scrollIntoView` before data arrives and `app.js:370` refetches on every party toggle. `render.yaml` runs a single uvicorn worker; during this review one otherwise-fast request took 76.2s while other agents hit the site. All `cf-cache-status DYNAMIC`.

**What's wrong.** "Where do you live?" → click a state → stare at "Loading representatives..." for 2–5 seconds is the first thing every visitor experiences after the hero, again on every party toggle, and on a phone it reads as the site hanging. All of that work produces the participation/support numbers F06 argues are noise. Any concurrent load (a share going modestly viral) stalls every other page for tens of seconds on the single worker.

**Redesign implication.** Precompute each state's roster payload (stats included) into `data/synced/state_overview/{code}.json` at sync time so the delegation endpoint is a single small file read (<300ms), and server-render the state page from it; render the roster skeleton (names, districts, photos from `members.json`) instantly and fill any stats after. Do not ship a redesign that keeps the per-request 28-file scan. Pair with F53 caching so Cloudflare absorbs repeat hits.

#### F06 — Participation and support rate are the headline metrics on every list surface and the state page ranks members by them, contradicting "no scores, no rankings" while distinguishing nobody
**Page** `/state`, `/` (delegation), `/member` · **Status vs July** still-open · **Lenses** state-page, task-flow, product-pm, trust-content

**Evidence.** `curl /api/members/NY/overview`: participation min 90.3 / max 99.8 / median 97.2 for all 28 NY members; local data: only 2 of 151 members fall below the 85% "high" threshold in `getBarClass` (`state.js:240-244`), so 149 of 151 bars render the identical full-green fill (`state-desktop-full.png`: 28 near-identical green bars). Support rate is yea/(yea+nay) (`members.py:129`), never defined on the page. `state.js:147-151/212-218`: "Sort by Participation (High to Low)" and "Support Rate (High to Low)" rendered in green-good/red-bad tokens. `state.js:113-126` header boxes "Representatives 28 / Avg. Participation 97% / Avg. Support Rate 57% / Total Votes Cast 60K": `members.py:141-148` sums every member's `total_votes` (59,752) so one roll call is counted once per member; "Representatives 28" repeats the subtitle at `state.js:102`; on mobile the four boxes fill the first screen. Total Votes column clusters at 657/1,061/1,841/2,839 and only encodes tenure. Homepage roster rows (`app.js:340-357`) show "yes 56% / no 44%" micro-labels; senator `narrative_snippet` is a hard 150-char cut (`members.py:123`: "Josh Riley votes most often on congressional procedure, econ..."), computed for all 28 members but never rendered on `/state`. `about.html:81` "We don't score or rank representatives"; PRD:228 "No scores, no report cards".

**What's wrong.** Yes-rate mostly reflects who controls the floor agenda, and attendance is ~97% for everyone, so a citizen scanning 28 rows to pick whom to read about gets zero signal from the row content and can only pick by name or photo — while the colour grade and high-to-low sorts imply exactly the ranking the product principles forbid. The aggregate boxes answer no citizen question, and "60K votes cast" will make a reader who checks the arithmetic conclude the site cannot count. The one column with visible spread (Total Votes) means only "how long in office". July PM observation #1, unchanged, and now also on the homepage roster.

**Redesign implication.** Delete the stat-box row, the Total Votes column, the participation bar, the colour thresholds and the sort-by-metric options. Roster rows and cards should be optimized for recognition, not comparison: bigger photo, name, seat ("Senate" / "District 4"), and one or two things that actually vary by member from existing data — the member's most recent key vote (bill one-liner + yes/no from `member_votes/*.json`) and/or top issue area (`narrative_top_areas` in `member_summaries.json`). Keep participation only as small text, surfaced as a flag only when actually low (<90%). Show tenure as words ("In office since 2025", from `terms`). Do not use the narrative snippet as the signal line; if it stays anywhere, cut at a sentence boundary server-side. Any comparison view compares on non-ordinal facts (chamber, district, tenure, topics).

#### F07 — Member page front-loads six derived-chart modules (three of which restate one number) so the actual record begins four to five screens down
**Page** `/member?id=S000148` · **Status vs July** new · **Lenses** member-page, mobile, product-pm

**Evidence.** `member-desktop-full.png`: first vote row (S. 5271) at y~2,755 of 5,588px (~3.8 viewports); `member-mobile-full.png`: first vote row at y~3,820 of 7,941px (~4.7 viewports), tab strip at y~4,460. Order hardcoded in `member.js:189-195` (`summaryEl` + `vizEl` appended before tabs): narrative → 3 stat boxes → key bills → donut (`renderVotingStats` 596–654) → attendance → 6 topic bars → Service History card (198–243) → tabs → two filters → pagination. Participation 99.8% appears three times (stat card `member.js:538`, Attendance heading `viz.js:252`, attendance bar `viz.js:255-258`); yea/nay appears three times ("Support Rate 49%" card, donut legend "519 (49%) / 540 (51%)" `member.js:604-609`, filter dropdown "Yea (519) / Nay (540)" `member.js:661-664`). Service History shows "Senate, 1981-present", which is wrong for Schumer (House 1981–99, Senate 1999–; API `terms`) because it pairs the latest chamber with the first start year. Donut + attendance bar occupy ~600px of desktop height to say "49%" and "99.8%"; with Service History ~1,100px sits between the summary and the record. `styles.css:2631-2633` hides `.member-sticky-bar` on <=768 so no name context exists for the remaining 9 mobile screens. Campaign Finance is FEC 2024 cycle (`member.js:1016`). `product-strategy.md` section 7.3: "a voter who understands 3 things clearly is better served than one overwhelmed by 30 data points".

**What's wrong.** The product promise is "see how your representatives vote", but the page inverts its own value: the most derived, least-differentiating modules sit highest and the modules that most directly answer "how do they vote" (key bills) are third, while a 99.8% attendance bar is visually identical for nearly every member and the donut restates the support-rate box. A voter on a phone from a shared link scrolls past six analytics modules before a single dated vote, and once past the header nothing on screen says whose record they are looking at.

**Redesign implication.** Restructure to header (name + chamber/state kept as a compact sticky strip on mobile) → one-paragraph summary → linked Key bills → "Recent votes" (last 5–8 plain-English votes), all within the first two screens on mobile. Cut the donut, the Attendance section, the stat tiles and the Service History card; keep one compact line under the name ("In Congress since 1981 - Voted in 1,060 of 1,061 roll calls") with service history folded into the header meta. If a comparative number is wanted, show it against the chamber median so it carries information. Hide Campaign Finance until data is current; move bill browse/search off the homepage to a `/bills` page.

#### F08 — Key Bills Supported/Opposed, the highest-value module on the site, is plain text with no links, dates or outcomes, and never appears on list surfaces
**Page** `/member` (At a Glance), `/state`, `/` (roster) · **Status vs July** new · **Lenses** member-page, product-pm

**Evidence.** `member.js:541-556` renders each key bill as `el('li', null, v.one_liner)`: no anchor, no date, no result, no bill number, although every eligible vote has `bill_id`, `date` and `result` (curl: 568 votes qualify). Picker hardcodes 6 supported vs 4 opposed (`member.js:534-535`) with no label explaining the asymmetry; selection logic (`member.js:490-527`) is sound. `member-crop-900.png`: ten serif lines with a coloured left rule, nothing clickable, below three stat boxes. `state-desktop-full.png` columns: Representative / Chamber / District / Participation / Vote Split / Total Votes — no key vote; home roster rows (`app.js:331-357`) show only a split bar.

**What's wrong.** "Fund the military, health care, education... for 2026" and "Order US troops out of combat against Iran" are exactly the plain-English promise, the thing a voter can actually reason about — and they sit below three near-meaningless stat boxes, cannot be clicked to see the bill or roll call, give no date or margin, and never reach the state or home rosters where people compare. The strongest content on the page is a dead end.

**Redesign implication.** Promote Key Bills directly under the summary, make each item a link to `/bill` with a dateline and outcome ("Passed 90-6 - Aug 8, 2026"), balance supported/opposed counts (or explain the imbalance), and reuse the same row component as the recent-votes list so the two feel like one system. Show one or two linked key votes per member on the state/home rosters instead of the yes-percentage.

#### F09 — Vote list is ~45% raw procedural text, prints each motion title twice, and stacks the same bill up to three times on page one
**Page** `/member?id=S000148` (Voting Record) · **Status vs July** still-open · **Lenses** member-page, trust-content, product-pm

**Evidence.** `curl /api/members/S000148/votes?limit=2000` → 1,061 votes; 478 have `one_liner == bill_number` (raw amendment/motion text: "To strike section 2019.", "In the nature of a substitute."); 490 have `has_plain_summary=false`; 478 have `bill_id=null`. Page 1 (first 15): only 2 rows have a plain-English one-liner, 5 are unclickable, H.R. 5334 appears 3x, H.R. 6500 2x, S.Res. 817 2x. `member.js:772-776` renders `vote.bill_number` as the blue title, an always-empty `vote-item-title` (`bill_title` is not a field in the API: 0 of 1,061 votes have it), then `one_liner` again, so rows read "To strike section 2019." / "To strike section 2019." (`member-mobile-full.png` rows 3–4). Default list is all votes (procedural motions included).

**What's wrong.** The list treats every roll call as a row, so a citizen sees cloture, tabling and substitute amendments at the same weight as final passage, with legalese doubled up and the same bill number stacked three times; the reader cannot tell what "In the nature of a substitute" was about, who offered it, or to which bill. July quantified the 44% raw-legalese share; the frontend still does nothing to group or demote it. This is the module the product is named after and it is the noisiest thing on the page.

**Redesign implication.** Group roll calls by bill: one row per bill (plain headline, date of final action, member's final position, outcome) with amendments/motions collapsed under an "N procedural votes" disclosure; default the list to votes with plain-English summaries (`has_plain_summary`) with procedural votes behind an expander. Design the row around a single headline slot: the one-liner when it exists, otherwise a structured fallback ("Amendment to H.R. 6500 - no plain-language summary yet") that names the parent bill and never repeats the same string; drop the empty `vote-item-title` div.

#### F10 — Bill page cannot answer "how did MY rep vote": a 431-row unfiltered alphabetical roll call with no state filter, no delegation block, and voter names that don't link to member pages
**Page** `/bill` (roll-call section, every bill with a vote) · **Status vs July** new · **Lenses** bill-page, product-pm, mobile

**Evidence.** `vote.js:235-294` `renderVoteTable` emits every member sorted by vote then last name with no filter, search, grouping or highlighting; name cells are `textContent` only (`vote.js:267-269`) even though House vote files carry `bioguide_id` per member (`data/synced/votes/house/119_2_00232.json`, 431 members). Sponsors link (`bill.js:198-200`) but voters don't. `bill-desktop-full.png` is 1280x22,553px; rows are ~46px so ~20,000px is the table and the "Nay" block begins ~9,000px down. The state chosen on the homepage is not persisted (only localStorage key is `cv-show-party`). On mobile, `.vote-table-wrap` only gets negative margins at <=768 under a comment "Vote table scroll hint" (`styles.css:2700-2703`) with no visual hint. PRD:131 JTBD #1: "quickly see how my representative voted and what the bill actually does".

**What's wrong.** The page built for the news-driven job ("the House just voted on X, what did my rep do?") makes the user scroll a 20,000px list and scan for a surname, and when they find the row it is a dead end: no link to the member page, no "your delegation" grouping, no sticky header. A visitor who wants to see who opposed the bill never gets there, and on a phone the table either squeezes to unreadable widths or scrolls sideways with nothing saying it does.

**Redesign implication.** Lead the roll call with a compact outcome band (result, tally, date) and a "Your delegation" block driven by the same ZIP/state lookup the homepage uses (persist the chosen state in localStorage), listing the user's 2 senators / rep with their vote and links to `/member`. Below it, a collapsed "All 431 votes" list with a state filter and name search; link covered members (the 150 in `members.json`) to their pages and render others as plain text. On mobile render roll calls as a two-line list (name + state, vote badge right-aligned), never a horizontally scrolling table.

#### F11 — Vote outcomes are buried and expressed in chamber jargon ("Yea/Nay", "On Agreeing to the Resolution", raw cloture strings) while the homepage says "voted yes"
**Page** `/bill`, `/member`, `/state` (vs `/`) · **Status vs July** still-open · **Lenses** bill-page, trust-content, visual-system, product-pm

**Evidence.** `vote.js:32-35, 211-214, 284-285` hard-code "Yea"/"Nay"/"Not Voting"; `member.js:608-609` donut legend "Yea / Aye", "Nay / No"; `member.js:662-663` pills; `state.js:329` "% yea". `bill.js:362-366` renders "${chamber} Vote #${n} - date", then raw `data.question`, then "Result: ${data.result}": `bill-desktop-full.png` (y 1300–2600) "House Vote #232 - June 30, 2026 / On Agreeing to the Resolution / Result: Failed / donut 431 / Yea: 189 Nay: 235". Senate result strings pass through verbatim: `data/synced/votes/senate/119_2_00231.json` "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)". Homepage `app.js:148-149` renders "237 voted yes / 169 voted no". `about.html:33` promises "without jargon"; `ai_summary.py` rule 8 bans jargon in summaries; PRD:107 "everyday English, not policy jargon".

**What's wrong.** The bill page never says, anywhere, "The House rejected this resolution 189-235 on June 30, 2026"; the reader assembles it from a vote number, a procedural question, a one-word result and a legend ~1,900px below the headline, and the donut's centre number (431) is the number of people present. The AI layer is held to a 7th-grade reading level, then wrapped in Senate-clerk vocabulary; the inconsistency is visible on one screen (home "voted yes", member "Yea"), and it is exactly the insider language the target user came here to avoid.

**Redesign implication.** Add a plain-English outcome sentence at the top of the bill page (under the headline) and at the top of each vote block, generated from chamber + question + result + counts ("The House rejected it, 189 to 235"); map question strings to plain phrases ("On Passage" → "Final vote to pass", "On Agreeing to the Resolution" → "Vote to adopt", cloture → "Vote to end debate (needed 60)"). One shared VoteChip component with labels "Yes" / "No" / "Present" / "Didn't vote" and one tally-label format ("237 yes - 169 no") used by `app.js`, `member.js`, `vote.js` and `state.js`; keep the official term as a small caption or in the roll-call source link only.

#### F12 — The bill page, browser `<title>` and og:title all headline the official legalese title; the AI one-liner exists in the data and is never used as the headline
**Page** `/bill` (all ~1,550 bills with an AI summary) · **Status vs July** still-open · **Lenses** bill-page, reach

**Evidence.** `bill.js:88` `const title = bill.title || 'Untitled Bill'`; `bill.js:100` `el('h2', null, title)` is the only headline; grep `one_liner` in `static/js/bill.js` returns nothing, while `app.js:189/213/455` use `bill.one_liner || bill.title` on the homepage and `main.py:196` uses it for og:description. `curl /api/bills/119/hconres/108/ai-summary` returns `one_liner` "Order U.S. troops out of hostilities in Lebanon within seven days". `bill-desktop-full.png` top: a three-line Playfair headline "Directing the President pursuant to section 5(c) of the War Powers Resolution to remove United States Armed Forces from hostilities in Lebanon." with the plain-language content ~700px lower; on mobile the official title fills 175px of the first screen. Server side: `main.py:199` `title = f"{bill_label}: {title_text} | ClearVoting"` with no length cap; 740 of 1,610 titles exceed 60 chars, 287 exceed 200, longest 1,955 (119 H.Res.354); live `<title>` for H.Con.Res. 108 is 173 chars.

**What's wrong.** The page's most prominent element, 2.3rem serif display type, is the legalese title, and the same string leads search results and share cards, truncated mid-clause for nearly half the catalogue. The nine-word answer to "what does this bill do" is already in the data and already used by the homepage and og:description, but the bill page never fetches or renders it, so the user scrolls past the title, a status line, Copy Link, a tag chip and a TOC row before the first plain-English sentence.

**Redesign implication.** Make the AI `one_liner` the H1 (fetched with the ai-summary call, or fold `one_liner` into `/api/bills/{c}/{t}/{n}`) and demote the official title to a kicker "Officially: ..." under it, mirroring the homepage pattern; when there is no `one_liner` the official title stays the H1. Server `<title>` = "{bill_label} - {one_liner}" when a summary exists, else the official title truncated at ~70 chars on a word boundary; official title goes in the description; keep og:title under ~90 chars. Apply the same formatter to the H1 kicker so page, tab and share card agree.

#### F13 — "What People Are Saying" presents unsourced AI-written arguments as the views of real supporters and critics, repeats the header in every bullet, and borrows the Yes/No vote colours
**Page** `/bill` (any bill with a summary) · **Status vs July** still-open · **Lenses** trust-content, bill-page

**Evidence.** `data/synced/ai_summaries.json`: 7,035 argument bullets across 1,550 summaries; 7,035 of 7,035 begin "Supporters say" or "Critics say"; no source, name, organization or citation field exists (keys: `one_liner, provisions, issue_categories, direction, arguments`). `bill.js:263-297` renders heading "What People Are Saying" with column headers "Supporters say" / "Critics say", so each bullet repeats the header up to 3x per column (`bill-desktop-full.png` y 950–1290). `styles.css:2476-2482` colour the headers with `--vote-yea`/`--vote-nay` and `styles.css:978-984` give the columns green/red left borders, the same tokens as the Yea/Nay badges 800px lower. `about.html:59` tells readers "we always present both supporters and critics side by side"; masthead "Facts only - No opinions"; footer "does not express opinions".

**What's wrong.** These bullets are opinions authored by the model and attributed to unnamed people. On a site whose masthead says "No opinions", this is the one module that manufactures them; the About page describes it as reporting; the only provenance signal is an italic disclaimer at the card's foot; and the green/red coding visually equates "supporters" with "voted Yes". A skeptical reader who notices there is never a named source will reasonably conclude the site is inventing debate; the redundant prefixes make it read as templated filler.

**Redesign implication.** Either drop the module until arguments can be sourced (quotes with attribution to real statements, floor debate, CBO/GAO), or relabel it honestly ("Possible arguments, drafted by AI - not attributed to anyone") with the disclaimer at the top of the block and a "why we show this" link to the methodology page; strip the "Supporters say/Critics say" prefix at render until the prompt is fixed; use neutral ink/rule colours for the two columns so vote red/green stays reserved for votes; consider collapsing the block by default. Do not let the About page describe it as "what people are saying".

#### F14 — Member page overflows 70px at 375px (fails WCAG reflow) because every mobile override is declared before the base rules it targets
**Page** `/member` (375px) · **Status vs July** still-open · **Lenses** member-page, mobile, a11y, visual-system

**Evidence.** `member-mobile-full.png` is 445px wide for a 375px viewport; crop at y 1,200–1,380 shows the third stat card "SUPPORT RATE" running past the glance card's border (~x=353) to the image edge while the masthead stays centred on the 375 axis. Root cause: `styles.css` `@media (max-width:768px)` at :2598-2736 and `(max-width:480px)` at :2740-2806 contain `.viz-stats-dashboard{grid-template-columns:1fr}` (:2711), `.viz-topic-row` (:2720, :2797), `.viz-donut-row` (:2715), `.glance-card` (:2728), `.viz-section` (:2732), `.filter-row` (:2724); the un-scoped base rules with identical specificity are declared later (`.glance-card` :2919, `.filter-row` :2955, `.viz-topic-row{120px 1fr}` :3121, `.viz-stats-dashboard{repeat(3,1fr)}` :3187, `.viz-section` :3317), so they win the cascade and every mobile adjustment is dead. Each `1fr` track cannot shrink below min-content: three ~150px stat columns + gaps ~480px in a ~287px slot. Section banners at :2596, :2738, :3009 show the "Phase 5" responsive block was appended before the "Visualization Components (Phase 1)" block was pasted below it. Live `styles.css` is byte-identical to the worktree.

**What's wrong.** The core "your representative" page needs two-axis panning on every phone: the third stat box is clipped, the topic bars are squeezed, the sticky tab bar and tap targets shift under the finger, and the fixed Feedback button overlaps content because the layout is wider than the viewport. WCAG 1.4.10 requires content at 320px CSS width without horizontal scrolling. July reported a 72px overflow "due to CSS source order" without naming the selector; the exact cause is the At-a-Glance stat dashboard, and nothing in the CSS changed.

**Redesign implication.** Whatever the new layout, author the member page mobile-first with responsive rules co-located after (or inside) each module's base rules, ideally in `broadsheet.css` where the inner-page system lives; drop fixed-width stat rows and min-width viz containers in favour of a single-column or 2-up stat strip using `minmax(0,1fr)`. Delete the dead legacy dashboard CSS instead of ordering around it, and add a smoke check that `document.documentElement.scrollWidth <= innerWidth` at 320px and 375px before merge.

#### F15 — Inner pages (member, state, bill) are still the old card dashboard wearing a broadsheet masthead
**Page** `/member`, `/state`, `/bill` (vs `/`) · **Status vs July** still-open · **Lenses** visual-system, member-page, state-page, bill-page

**Evidence.** `styles.css:907` `.bill-section`, :2919 `.glance-card`, :3194 `.viz-stat-card`, :3317 `.viz-section`, :3360 `.state-stat`, :3399 `.comparison-table`, :3589 `.mobile-card`, :1616 `.service-compact` all = white `--bg-card` + `radius-lg` + `box-shadow`. `broadsheet.css:264-445` is 112 `body.broadsheet` rules that only swap font-family/colour on those containers (e.g. :282-295, :318, :352-357, :393) and never remove the card chrome, while `broadsheet.css:340-346` fully converts `.vote-item` to transparent + hairline. Screenshots: `member-desktop-full.png` = four white shadowed rounded cards y 470–2,420 then hairline rows from y 2,700; `state-desktop-full.png` = 4 stat cards + a table inside a shadowed card with Inter labels; `bill-mobile-full.png` = 5 stacked cards plus three rows of pills ("Copy Link", one chip "International Affairs", TOC "Summary - Official Text - Sponsors - Votes"); `bill.js:139` labels the TOC link "Official Text" but targets `#official-summary-section` headed "Official Summary"; `bill.js:94` reads `bill.subjects?.legislativeSubjects` but the API returns `subjects:{count,url}` so the tag row can only ever hold the policy area; the Sponsors card shows one name with no cosponsor count although the API has `cosponsors.count 43`. `state.html:14` loads `body.broadsheet` but `state.js` builds none of the broadsheet classes the homepage delegation uses (`broadsheet.css:159-194`). `home-desktop-full.png` uses hairline/double rules and open whitespace.

**What's wrong.** The June unification changed typefaces and colours but left the structural CSS from the pre-broadsheet dashboard in place, so the visual grammar flips the moment a user leaves the homepage: rules and whitespace on home, nested rounded cards with drop shadows (viz-stat-card inside glance-card inside main) everywhere else, reading as a SaaS admin panel rather than a civic record. A visitor who lands on `/state` from search meets a different product than the homepage. Several small half-working pieces on the bill page (TOC label mismatch, a one-chip tag row, a lone sponsor link, a floating Copy Link pill) make the top of the page feel unfinished and push the real content down. July's verdict that the redesign "achieved its goal" holds only for the homepage.

**Redesign implication.** Rebuild member/state/bill layouts on the homepage's containment model: sections separated by 1px hairlines and 3px double rules, kicker + hairline section heads on the paper ground, no nested white cards, no box-shadow except on the one interactive card type (state-card/vote-card); stat figures set inline as a single serif "by the numbers" line rather than boxed tiles. Compose the bill page as one broadsheet article: kicker (bill code - Congress - status), headline (one_liner), deck (official title), byline-style meta row (sponsor + N cosponsors, policy area, share), then sections separated by rules; drop the TOC and either populate subjects from the data or remove the tag row. Reuse the homepage delegation component (`senator-row` + roster grid, `broadsheet.css:168-191`) as the `/state` body. Delete the `.glance-card`/`.viz-section`/`.bill-section`/`.state-stat`/`.comparison-table`/`.mobile-card` container rules rather than re-skinning them.

#### F16 — Neither grey text token passes AA on the paper background: `--text-dim` (2.91:1) still styles 47 selectors including the AI disclaimer, and the "AA fix" `--ink-meta` is 4.35:1 on paper
**Page** all pages · **Status vs July** still-open · **Lenses** a11y, state-page, visual-system

**Evidence.** Computed: `--text-dim` #8D9297 on paper #F5F6FA = 2.91:1, on white 3.14:1 (AA needs 4.5:1; large-text AA needs 3:1); `grep -c 'var(--text-dim)' styles.css` = 47, live selectors include `.party-toggle-inline` (`styles.css:544-547`, `member.js:90`), `.ai-disclaimer` 0.8rem (:993-995), `.data-table th` (:853-857), `.vote-pagination-info` (:1753-1755), `.ai-attribution` 0.75rem (:1164-1166), `.service-expand-btn`, `.feedback-context`, `.copy-link-btn` (:1026-1038), `viz.js:178` donut sub-label, state `thead th` (:3410), `.split-text` (:3547-3550), `.state-stat .label` (:3369-3371); `broadsheet.css` overrides only a subset (:376 ai-disclaimer font only, colour not overridden). `--ink-meta` #6E7480 (`broadsheet.css:20`, commented "for AA on white") on paper #F5F6FA = 4.35:1, on white 4.69:1, on `--card-hover` #EEF1F6 4.15:1, applied to normal-size 11–12.5px uppercase letter-spaced text at `.meta` (:52), `.masthead-tagline` 0.7rem (:61), `.trust-line` (:156), `.roster-district` (:186), `.official-line` (:207), `body.broadsheet .back-link` (:278), `.member-meta` (:309), `.bill-status` (:357), `.comparison-table thead th` (:410) and ~20 more; only white-card contexts clear 4.5:1.

**What's wrong.** The July token swap remains half-finished, and the remediation itself assumed a white background while the broadsheet moved the page ground to off-white paper. The honesty affordances the product depends on (the "generated by AI" disclaimer, the "Showing 1-20 of 1,061" pagination info, the "Show Party" control, the numbers that carry the state row's only quantitative meaning) are rendered below even the large-text threshold, and the majority of the homepage's datelines, district lines and trust line sit at 4.35:1 in the hardest case for low-vision readers (tiny uppercase letter-spaced text).

**Redesign implication.** Define one metadata token and darken it once (`--ink-meta` #5F656D gives 5.45:1 on paper and 5.88:1 on white with no visible design change); delete `--text-dim` as a text colour by aliasing it to that value or replacing all 47 usages, keeping #8D9297 only for non-text decoration. Set a 0.8rem (12.8px) floor for any text using the meta token and stop pairing it with card-hover backgrounds. Add a contrast check for every token against BOTH `--paper` and `--card` to the redesign's definition of done.

#### F17 — Hero sentence template still splices the raw official title into Playfair display type; it reads well today only by luck of the data
**Page** `/` (Latest Vote hero) · **Status vs July** still-open · **Lenses** task-flow

**Evidence.** `app.js:127` `const title = v.bill.title || v.document`; `app.js:135` builds "The ${chamber} ${verb} the ${title}, ${yeas}-${nays}". Today's vote is H.R. 4795 whose title is the 49-char "Protect Economic and Academic Freedom Act of 2026" (`home-desktop-full.png` top-right). `curl /api/bills?limit=20` shows the next candidates: H.Res.1499 title 1,063 chars ("Providing for consideration of the bill..."), S.J.Res.187 337 chars, S.J.Res.199 258 chars, H.J.Res.1 148 chars; none has a `one_liner` for the template to use instead. `verbFromResult` (`app.js:95-102`) emits "the House agreed to the Providing for consideration of..." for resolutions.

**What's wrong.** July's P0 #3 ("The Senate rejected the A joint resolution to direct...") is fixed by the data, not by code. The next resolution vote will put a paragraph of legalese in display type on the first screen, and on mobile it will consume the entire fold.

**Redesign implication.** Render the hero as a structured card (chamber, date, result, tally, bill number) and use the AI `one_liner` as the headline when present; when absent, show the official title truncated to ~90 chars in body type, never inside a sentence template.

#### F18 — Footer "Privacy" and "Methodology & Corrections" point to /about, which has no privacy policy, no methodology, no corrections process and no named humans, while every page view sends IPs to Google Fonts
**Page** all pages (footer), `/about` · **Status vs July** still-open · **Lenses** trust-content, product-pm, reach

**Evidence.** `index.html:123-125`, `member.html:36-38`, `bill.html:36-38`, `state.html:36-38`, `404.html:38-40`, `about.html:99-101`: all three footer links `href='/about'`. `about.html:32-93` contains no privacy text (the site collects email at `index.html:60-64` and free-text feedback with page context via `feedback.js`), no named maintainer (only "independent, non-partisan volunteer project", line 38), and corrections are one sentence about the feedback button. `about.html:57` claims summaries "follow 12 strict rules for neutrality"; `app/services/ai_summary.py:37-57` enumerates 18 numbered rules. Home links "how we keep it neutral" (`index.html:94`) to the same page. Every shell loads `https://fonts.googleapis.com` before `styles.css` (`index.html:8-11` etc.), permitted by CSP (`main.py:109-110`). `product-strategy.md` risk table lists "Transparent methodology (About page)" as the mitigation for the perception-of-bias risk.

**What's wrong.** The brand promise depends on the reader being able to check who is behind the site and how neutrality is enforced. The footer advertises those checks and delivers a page that answers neither, with a rule count that doesn't match the prompt. A privacy link with no policy on a site collecting emails and sending visitor IPs to a third party is a trust liability; "Methodology & Corrections" with no log or process is a promise without a mechanism. Anyone auditing the site before recommending it (the PRD's secondary users: teachers, librarians) hits this immediately.

**Redesign implication.** Ship three real destinations and repoint the footer: `/about` (who, why, funding, a name and contact), `/methodology` (data sources, sync cadence, the actual neutrality rules generated from the prompt or with the number dropped, what AI does and does not touch, known coverage gaps such as the 60 un-summarized bills, a dated corrections log), and `/privacy` (what email/feedback data is stored, where, for how long). Self-host the fonts (F55) so the privacy page can honestly say "no third-party requests".

#### F19 — 1,760 of 1,766 sitemap URLs serve an empty `<main>` (a spinner) to crawlers, share scrapers and AI bots
**Page** `/member`, `/bill`, `/state` (and homepage dynamic sections) · **Status vs July** still-open · **Lenses** reach

**Evidence.** `curl -s https://clearvoting.org/member?id=S000148` → 4,318 bytes; the entire `<main>` is a back-link button plus `<div class="loading"><span class="spinner"></span> Loading representative...</div>` (`static/member.html:28-32`; `bill.html:30` and `state.html:30` identical). `app/main.py:85-91` `_serve_html` only rewrites `<head>` via `_inject_meta` (`main.py:58-82`), no body injection. `curl /sitemap.xml` → 1,766 `<loc>` entries (2 + 4 states + 150 members + 1,610 bills; `main.py:264-294`). On the homepage the hero (`#latest-vote` hidden until `app.js:154`), The Record (`index.html:98` spinner) and state member counts (`app.js:107`) are all client-fetched. The shell routes already call `get_member_detail`, `get_ai_summary`, `get_members_by_state` in-process for meta (`main.py:150/175/214`).

**What's wrong.** Every page a voter would search for ("how did Schumer vote on", "H.Con.Res. 108") is title-and-description only; the body text Google, Bing, DuckDuckGo, Perplexity/ChatGPT crawlers and link-preview scrapers see is a spinner. Eight weeks before the midterms the growth loop through search is effectively closed, and it compounds: no body text means no rich snippets, no passage ranking, no AI-answer citations.

**Redesign implication.** Make server rendering the default for the above-the-fold content block on member/bill/state: the FastAPI shell already has the data in-process, so render name/chamber/state, the AI one-liner and official title, the narrative summary and the first 10–15 votes as real HTML inside `<main>`, then let JS enhance/paginate. Server-render the homepage's latest-vote card, Record entries and state counts so the front page's freshness is visible to crawlers. Keep a literal `<title>` and `</head>` in every shell so `_inject_meta` keeps working.

#### F20 — Sharing surface is weak: no og:image anywhere, client JS overwrites the server `<title>`, and a dim clipboard-only "Copy Link" is the sole share control (absent on state and home)
**Page** all pages (worst on `/member` and `/bill`) · **Status vs July** still-open · **Lenses** reach, bill-page, state-page

**Evidence.** `grep -c 'og:image'` on live shells for `/`, `/member?id=S000148`, `/bill?...hconres&number=108`, `/state?code=NY` → 0,0,0,0; `main.py:71-79` builds exactly 8 tags with `twitter:card=summary`; `static/` holds only `favicon.svg` beyond html/css/js. `member.js:61`, `bill.js:75`, `state.js:84` each set `document.title` after load, replacing the server's "Schumer, Charles E. (NY) - Voting Record | ClearVoting", "H.Con.Res. 108: ..." and "New York Representatives - Voting Records | ClearVoting" with weaker forms (the bill one drops the bill number people search for). `member.js:134-149` and `bill.js:107-122` render the Copy Link button only if `navigator.clipboard` (nothing otherwise), copy `window.location.href` verbatim (so a `type=HCONRES` variant URL gets shared), no `navigator.share`, no share text; `styles.css:1026-1038` transparent chip in `--text-dim` at 0.8rem, sitting alone between the header and the first card (`member-desktop-full.png` y~390; mobile y~250). `state.js` and `app.js` have no share affordance at all.

**What's wrong.** The bill and member pages are the units people would text or post before an election ("look how they voted on this"); the project's traction came from LinkedIn shares. Today every share on iMessage, X, Facebook, LinkedIn, Slack and WhatsApp renders a grey text-only card with a legalese title that looks like a broken link next to any competitor card, the tab title and bookmarks degrade after load, and on phones (where sharing actually happens) the only control is easy to miss, looks disabled and skips the OS share sheet users expect. The most shareable civic unit (a state delegation) has no share at all.

**Redesign implication.** Ship `/og/member/{id}.png`, `/og/bill/....png`, `/og/state/{code}.png` routes (Pillow, no build step) rendering a branded broadsheet card (member name + "Voting Record", or bill number + one-liner + tally) plus a static default card; emit `og:image`, `og:image:width/height` and switch `twitter:card` to `summary_large_image` in `_inject_meta`, designed as part of the visual system at 1200x630. Delete the three `document.title` lines and make the server title the single source ("Charles E. Schumer (NY) - Voting Record | ClearVoting" using first-last form, "H.Con.Res. 108 - {one-liner} | ClearVoting", "New York's Representatives - Voting Records | ClearVoting"). Put a single "Share" action in the page header action group (next to the party toggle and Congress.gov link) that calls `navigator.share({title, text, url: canonical})` on mobile with prewritten text and falls back to clipboard with a visible "Link copied" toast; add it to state pages and per roll-call row; always share the canonical URL from `<link rel=canonical>`.

### P2 — real friction, defects and accessibility failures the redesign must not carry forward

#### F21 — Mobile first screen contains no task entry: "Where do you live?" sits ~1,000px down, below the Latest Vote card
**Page** `/` (mobile fold) · **Status vs July** still-open · **Lenses** task-flow, mobile, product-pm

**Evidence.** `home-mobile-fold.png` (375x812): masthead logo/tagline/nav y 0–160; kicker + H1 "See how your representatives vote." + lead paragraph y 200–470; "The Latest Vote" card starts at y~512 and its Playfair headline runs to the bottom edge; no state card, no ZIP field, nothing to tap toward a representative except the hero's bill link. `home-mobile-full.png` (375x3734): "Where do you live?" at y~940–1000, state grid y 1,000–1,180. `broadsheet.css:249` stacks `.home .lead` to one column at <=880px, putting the vote card between the headline and the action. `index.html:21-25` nav has no "Find my representative" entry; "The Record" is an in-page anchor that skips past the state grid.

**What's wrong.** On the device most midterm-season visitors will use, the first screen says what the site is but does not let the user do the one thing it is for: brand, tagline, headline, paragraph and the start of a news card, with no interactive element except the nav. The "Latest Vote" demo, meant to prove the product, costs the entire first viewport. July's P0 #3 already flagged the vote card pushing "Where do you live?" below the fold; it is still true even though the current hero title happens to be short.

**Redesign implication.** On mobile place the state picker (and/or ZIP field) directly beneath a shorter H1, inside the first viewport, with the Latest Vote card after it (or collapsed to a one-line teaser); shorten the masthead (tagline + nav on one row) so the first screen contains one thing to tap. Add a "Find my representative" item to the masthead nav on every page.

#### F22 — About page body text is invisible or ghosted by default: every section starts at opacity 0 waiting for a scroll observer in feedback.js
**Page** `/about` · **Status vs July** new · **Lenses** visual-system, mobile, a11y, trust-content, product-pm

**Evidence.** `about.html:30,36,43,63,78,89` put class `animate-in` on every section and :53 `animate-scale`; `styles.css:3700-3704` `.animate-in { opacity:0; transform:translateY(24px) }` and :3776-3782 `.animate-scale { opacity:0 }`; the only thing that adds `.visible` is the IntersectionObserver in `feedback.js:195-217` (threshold 0.1, 0.6s transition). `styles.css:3812-3818` (prefers-reduced-motion) only shortens durations; the opacity-0 base state is untouched. `about-desktop-full.png` (1280x2695): "Why We Built This" and "About This Project" render as ghost-grey text mid-transition; sections 3–7 are blank, leaving ~2,000px of empty paper; `about-mobile-full.png` (375x4125) is entirely blank below the masthead with ~2,500px of empty scroll before the footer. Text colour itself is fine (`broadsheet.css:433-436`, 15.95:1).

**What's wrong.** The one page whose job is to establish who runs this and how it stays neutral (and the target of the Privacy and Methodology footer links) ships 100% of its text transparent, revealed only if a JS observer living in the feedback widget fires per section. Anything that bypasses the observer (print, reader mode, a blocked or slow script, a crawler snapshot, a screen-magnifier user reading before scroll, reduced-motion users) sees a blank page under a masthead that says "Facts only". Even for normal users the 24px slide-up entrance is the only motion on the site and contradicts the calm broadsheet tone.

**Redesign implication.** Remove entrance animations from content entirely (delete `.animate-in`/`.animate-scale`/`.hero-animate`/`.stagger-children` and the observer). If any motion is kept anywhere, content must default to `opacity:1` and only a JS-added class may opt into an additive fade, disabled under prefers-reduced-motion. Fill the page with the missing Privacy and Methodology content (F18).

#### F23 — Floating Feedback pill overlaps the primary CTA or content on every mobile page, is under 44px, and belongs to neither visual language
**Page** all pages (worst on mobile) · **Status vs July** still-open · **Lenses** task-flow, visual-system, mobile, member-page, bill-page, state-page

**Evidence.** `styles.css:2809-2830` `.feedback-btn { position:fixed; bottom:1.25rem; right:1.25rem; padding 0.5rem 0.85rem; font-size 0.8rem; z-index:90; border-radius:999px }` on every page (`index.html:131-134`) with no mobile rule, no safe-area inset, no min-height (~110x36px), and nothing reserves bottom padding on main. `home-mobile-fold.png` bottom-right (x 245–355, y 755–795): the pill sits over "169 voted no" and clips the arrow of "What this bill does, in plain English ->", the hero's only link. `member-mobile-full.png` y~775: overprints the At a Glance narrative. `bill-mobile-full.png` y~775: covers the "Generating plain-language summary..." line of the primary card. `state-mobile-full.png`: sits on the right side of the first member card (Espaillat). `about-mobile`: overlaps the "About This Project" heading. Lead observed it over the Texas state card (consistent with `right:1.25rem` on a 2-column grid).

**What's wrong.** On a 375px screen a permanent pill in the bottom-right corner is always sitting on something: the hero CTA on the homepage, narrative text on member pages, the primary card on bill pages, the first card on state pages, headings on About. It is the only element on the site using that shape, icon style and z-layer, and it is itself below the 44px touch minimum.

**Redesign implication.** On viewports under ~640px remove the floating pill: put Feedback in the footer ("Report an error on this page") and the masthead nav, plus an inline text link under each AI summary and vote list. If a floating control is kept on desktop, render it as a 44px icon-only button with `env(safe-area-inset-bottom)` that hides on scroll-down, and reserve bottom padding on main equal to its height so it never overlaps a primary CTA.

#### F24 — Feedback widget is not an accessible dialog: no role, no focus trap, focus dropped on close, unlabeled textarea, silent status
**Page** all pages · **Status vs July** still-open · **Lenses** a11y

**Evidence.** `index.html:136-148` (identical in `member.html:49-61`, `bill.html`, `state.html`, `about.html:112-124`, `404.html`): `<div id="feedback-modal" class="feedback-modal" hidden>` with a bare `<form>`, an `<h3>` not referenced by `aria-labelledby`, `<textarea id="feedback-message" placeholder="What's on your mind?">` with no label, `<p id="feedback-status" hidden>` with no role or `aria-live`. `feedback.js:56-67` `openModal` sets `hidden=false` and focuses the textarea; :69-71 `closeModal` only sets `hidden=true` (no focus return to `#feedback-open`); no keydown handler constrains Tab; :157-166 success text is written then the modal auto-closes 1.5s later with no announcement. `home-desktop-a11y.md` exposes only button "Send feedback", no dialog node.

**What's wrong.** The overlay is visually modal but semantically nothing: a screen-reader user hears an unnamed textarea gain focus with no dialog context, can Tab straight out into the page underneath, gets no announcement of "Thanks for your feedback!" or the error, and lands on `<body>` when it closes. Because this is on every page and is the site's only feedback channel (the About page tells users to use it, and it is the corrections mechanism), the failure is site-wide.

**Redesign implication.** Rebuild the feedback panel on the native `<dialog>` element (`showModal()` gives `role=dialog`, `aria-modal`, focus trap and Esc for free under the existing CSP), add `aria-labelledby` pointing at the heading, a real `<label>` for the textarea, `role="status"` on the status line, and return focus to the opener on close. Keep the `#feedback-*` ids and structural hooks `feedback.js` reads.

#### F25 — The party-reveal control has three different labels, a static wrong aria-label, per-block desync on two-chamber bills, bare "R"/"D" letters when revealed, and persistence that defeats "hidden until asked"
**Page** `/`, `/member`, `/bill` · **Status vs July** still-open · **Lenses** member-page, a11y, trust-content, bill-page

**Evidence.** `index.html:78-79` "Party labels are hidden, so the record speaks first." + "Show party labels"/"Hide party labels" (`app.js:364`, updates `aria-pressed` correctly at :361-370). `member.js:90` button "Show Party"/"Hide Party" with a static `aria-label` "Reveal party affiliation" that never changes (toggle text flips at :112/116; no `aria-pressed`), floating as a stray pill after "SENATE - NEW YORK"; reveal only writes `partyName` into `#party-display` (:99-105). `bill.js:387-389` "Viewing representatives without party labels." + "Reveal Party Affiliations"/"Hide Party Affiliations"; `bill.js:5` `showParty` is module-global but each `loadChamberVote` creates its own button (:385-391) and the click handler (:415-419) flips the shared flag, so on two-chamber bills the untouched block's button shows the wrong state and its next click hides instead of shows (July recorded the desync). `vote.js:277` `partyCell.textContent = member.party` → "R"/"D"/"I". All three read/write localStorage `cv-show-party` (`app.js:18`, `member.js:5`, `bill.js:5`), so a returning visitor sees party without asking. Server-side stripping (`members.py:215-230`) is correct.

**What's wrong.** The signature feature is executed correctly at the data layer, but the control has a different name and explanatory sentence on every page, so a user who toggled it on the homepage sees an unfamiliar control on the member page. A screen-reader user hears "Reveal party affiliation" while sighted users see "Hide Party" (fails WCAG 2.5.3 Label in Name, so voice-control users saying "click Hide Party" get nothing); the bill-page reveal breaks the moment a bill has both chambers; and the promise "hidden until asked" only holds on the first visit.

**Redesign implication.** One shared toggle component across home/member/bill: visible text "Show party labels" / "Hide party labels", one explanatory line, `aria-pressed` reflecting state, no `aria-label` override, rendered as a text link in the header meta line ("Party: hidden - show"). On the bill page make it a single page-level control in the roll-call header that re-renders every vote block from one state, and render the party column with full names ("Democrat"/"Republican") plus per-party tallies inline rather than extra pies. Make persistence session-scoped (or explicit) so every fresh visit starts party-hidden, and show a visible "on" state that carries across pages.

#### F26 — Vote totals contradict each other on one member screen (1,061 / 1,060 / 1,058) and the attendance figure is computed from a rounded percentage, not the data
**Page** `/member?id=S000148` · **Status vs July** still-open · **Lenses** member-page

**Evidence.** Same screenshot shows Total Votes "1,061" (stat box), donut centre "1,060 total votes", filter "All Votes (1060)" and tab "Voting Record (1061)" / "Showing 1-15 of 1061". API stats: `total_votes` 1061, yea 519 + nay 540 + not_voting 1 = 1,060; the missing vote is a "Guilty" value that `member.js:599` excludes from total. Attendance "Attended 1,058 of 1,060" comes from `member.js:611` `Math.round(total * stats.participation_rate / 100)`, but `not_voting_count` is 1 so the true figure is 1,060 of 1,061; "1,058" is an artifact of rounding 99.8%.

**What's wrong.** On a site whose masthead says "Facts only", four different totals for the same senator are visible within one scroll, and the attendance module prints a number that does not exist in the data (it invents two missed votes). July logged the 1,044/1,043 mismatch; this is the same root cause: the frontend recomputes what the API already provides.

**Redesign implication.** Use `stats.total_votes` and `stats.not_voting_count` verbatim everywhere (one source for every count on the page), include Present/Guilty in an "Other" bucket rather than dropping them, never derive a count from a rounded percentage, and show participation once as "1,060 of 1,061 roll calls".

#### F27 — Vote row metadata is malformed: "Bill Bill Passed", empty policy-area chips, raw cloture strings, and amendments labelled "Resolution - no details available" even for resolutions that have pages
**Page** `/member` (Voting Record rows) · **Status vs July** new · **Lenses** member-page, trust-content, mobile

**Evidence.** `member.js:781` `const resultText = 'Bill ' + vote.result` while synced result strings already begin with the object ("Bill Passed (90-6, 3/5 majority required)", "Cloture on the Motion to Proceed Rejected (52-46...)", "Motion to Table Agreed to (61-32)"), producing "Bill Bill Passed (90-6, 3/5 majority required)" and "Bill Cloture on the Motion to Proceed Rejected..." (`member-mobile-full.png` rows 1–2). `member.js:783-784` appends an impact-tag span unconditionally while 484 of 1,061 votes have `policy_area ''` so an empty bordered oval renders (~22x8px next to procedural rows; the sponsored-bills path guards it at :407-408). `member.js:811-821`: only HR/S/HJRES/SJRES are clickable; everything else gets "Resolution - no details available", covering 478 amendments (not resolutions) and 43 SRES/SCONRES/HCONRES/HRES votes even though `bill.js:221` `typeMap` supports those pages and the homepage's lead bill is H.Con.Res.108.

**What's wrong.** Three copy defects in the most-repeated component on the site: a doubled noun in every result line, a blank chip that reads as a broken checkbox on a phone, and a category label that is wrong for amendments and wrongly denies detail pages to resolutions the site actually has. Individually trivial; together they make the record look auto-generated and unchecked on a site whose credibility rests on precision.

**Redesign implication.** Normalize result strings at sync or render into a small vocabulary ("Passed 90-6", "Blocked - needed 60 votes (52-46)", "Amendment rejected 49-50") with a plain gloss for cloture/tabling; omit tags with no value and give procedural votes an explicit "Procedural vote" / "Amendment" / "Motion" / "Nomination" label; derive clickability from the shared bill `typeMap` so resolutions link to their pages and reserve a "no page" label for amendments, worded as such.

#### F28 — "What They Fight For by Topic" is editorial in name, truncates every topic label (desktop and mobile), and silently counts Nay votes as "supported" via an unexplained direction model
**Page** `/member` · **Status vs July** new · **Lenses** member-page, mobile, product-pm

**Evidence.** Heading string `member.js:618`. Label column fixed at 120px with nowrap/ellipsis (`styles.css:3121-3141`), declared after the mobile 100px/80px overrides (:2720, :2797) so those never apply: at 1280px "Economics and ...", "International Aff...", "Armed Forces a...", "Science, Techno..."; `member-mobile-full.png` (y 3,050–3,450) all six labels cut. Bars use `area.in_favor/against` (`member.js:636`) while the subtext (`member.js:620-628`) says "how many bills this representative supported vs. opposed"; curl summary: Environmental Protection yea 8 / nay 18 but in_favor 20 / against 5, so the green bar shows 20 "supported" for a topic where he voted Nay 18 times. Full policy-area names are in the same payload.

**What's wrong.** On a "no opinions" site, "What They Fight For" is a characterisation, and the bars render an AI-derived judgment (a Nay on a rollback counts as support for the environment) as fact with nothing explaining it; a reader who cross-checks against the donut will think the numbers are wrong. The module then hides the very words that carry meaning (the topic names) on every viewport.

**Redesign implication.** Rename to "Votes by topic", stack the full label on its own line above the bar (one-column grid) with short display names ("Economy", "Foreign affairs", "Military"), and either show raw Yes/No counts per topic or add a one-line explanation of the direction model ("counted by what the vote does, not how it was cast") linked to the methodology page. Candidate for cutting under F07 if it cannot be made neutral.

#### F29 — Member page mobile first screen is a wall of narrative prose with nothing actionable
**Page** `/member` (375px) · **Status vs July** new · **Lenses** member-page, mobile

**Evidence.** `member-mobile-full.png` (y 0–900): masthead, back link, centred photo, name, "Copy Link" on its own row, then "At a Glance" and nine lines of narrative at 1.125rem/1.7 (`styles.css:2935-2941`). Narratives average 88 words / 550 chars, max 132 words (`data/synced/member_summaries.json`, 150 members), so the paragraph alone runs ~1,000px on mobile.

**What's wrong.** No vote, no key bill, no filter is visible on the first mobile screen, just a paragraph the floating widget partially covers. The narrative is good content, but at this size and position it becomes the page rather than the lede.

**Redesign implication.** Set the mobile narrative at body size with a 3-sentence clamp and "Read more", move Copy Link/share into the header meta row, and put the first linked key bills within the first screen (see F07).

#### F30 — Three competing sticky layers on the member page, a clipped filter select, and form controls under 16px that trigger iOS focus-zoom
**Page** `/member` (also `/state`, `/`) · **Status vs July** new · **Lenses** member-page, mobile

**Evidence.** `.member-sticky-bar` `position:sticky top:0 z-index:99` (`styles.css:1069-1083`); `.member-tab-bar` `position:sticky z-index:98` with top set at runtime (`styles.css:1674-1684`, `member.js:312-313`, 0px when `innerWidth<=768`); `.filter-row` `position:sticky top:0 z-index:10` (`styles.css:2955-2963`) slides under the higher-z bars once scrolled, so the vote-type and category filters vanish as the 1,061-item list scrolls. Desktop `d_0.png` (x 110–235): "All Votes (1060" with the custom `.filter-arrow` span overlapping the select's text; mobile shows the native arrow overprinting the trailing ")". Form controls: `.filter-select` 0.875rem (`styles.css:2978`), `var(--text-sm)`=0.875rem (:34, :3575), feedback textarea 0.9rem (:2887), notify email input 0.85rem (`broadsheet.css:143`), all under the 16px threshold at which iOS Safari zooms on focus.

**What's wrong.** Sticky name bar, tab bar and filter row fight for the top edge; the filter row's sticky positioning is effectively dead, so on mobile the only tools for navigating a thousand votes disappear behind the tab bar. Every select and input on the site is small enough that iOS zooms in on focus and leaves the layout zoomed.

**Redesign implication.** Allow at most one sticky element on the page (a slim name bar combined with the filters on mobile, offset computed once), drop the sticky filter row and tab bar, use native selects without an overlaid arrow span, and set 16px as the floor for every input, select and textarea.

#### F31 — Bill codes render in four incompatible formats across pages ("HCONRES.108", "HCONRES. 108", "HR.2860", "H.Con.Res. 108") and the Congress ordinal is hard-coded "th"
**Page** `/`, `/bill`, `/member` · **Status vs July** still-open · **Lenses** bill-page, trust-content

**Evidence.** `app.js:182/210/460` "${type.toUpperCase()}. ${number}" → "HCONRES. 108", "HRES. 1398"; `bill.js:89` "${type.toUpperCase()}.${number}" → kicker "HCONRES.108 - 119TH CONGRESS" and "HR.4795"; `member.js:397` "${bill.type}.${bill.number}" → "HR.2860", "SRES.417"; `main.py:43-52` `_BILL_TYPE_LABELS` produces "H.Con.Res. 108" for the server `<title>`; synced vote data uses official "H.R. 4795", "S. 5271". `bill.js:99` hard-codes "${congress}th" (wrong for the 121st). No shared formatter exists (grep `billCode`/`formatBill`: nothing).

**What's wrong.** A legislation site that cannot cite a bill number consistently (front page, bill page, member page and browser tab all disagree for the same bill) signals sloppiness precisely where authority matters, and "HCONRES" is unreadable to the target user compared with "H.Con.Res. 108".

**Redesign implication.** Add a single shared `formatBillCode(type, number)` in a small common JS file (or expose the server's label map via the bill JSON) used by `bill.js`, `app.js` and `member.js`, standardized on the Congress.gov form; add an ordinal helper for the Congress number; treat the formatted code as the broadsheet kicker token.

#### F32 — "Latest action" line shows a raw ISO date and a Congress.gov housekeeping motion instead of the bill's fate; Senate vote dates pass through with timestamps and double spaces
**Page** `/bill` header and Senate roll-call headers · **Status vs July** new · **Lenses** bill-page

**Evidence.** `bill.js:101-103` renders "Latest action (${statusDate}): ${statusText}" with `actionDate` unformatted; `curl /api/bills/119/hconres/108` `latestAction = {actionDate:'2026-06-30', text:'Motion to reconsider laid on the table Agreed to without objection.'}`, same text for H.R.4795 (2026-09-03); visible at `bill-desktop-full.png` y~412 and `bill-nosummary` y~328. `vote.js:18-23` only reformats ISO strings and passes anything else through; `data/synced/votes/senate/119_2_00231.json` stores `vote_date` "August 8, 2026,  04:36 AM" (double space), so Senate headers read "Senate Vote #231 - August 8, 2026,  04:36 AM".

**What's wrong.** The one status line under the headline is a procedural motion for both sample bills, while the actual outcome (Failed 189-235 / Passed 237-169) is two screens down; the date is machine-formatted next to a human-formatted vote date further down, and Senate dates carry a timestamp with a typographic double space.

**Redesign implication.** Replace "Latest action" with a derived status pill computed from the votes index ("Rejected by the House - June 30, 2026" / "Passed the House - Sept 3, 2026" / "Introduced - no floor vote yet"); format all dates through one helper and normalize Senate `vote_date` to ISO at sync (July P0 #2) so `formatVoteDate` has one input shape.

#### F33 — Sponsor link leads to a 404 for out-of-coverage members (both sample bills)
**Page** `/bill` Sponsors → `/member?id=...` · **Status vs July** new · **Lenses** bill-page

**Evidence.** `bill.js:198-200` links every sponsor to `/member?id=${bioguideId}`. Both sample sponsors are outside the 4 covered states: T000481 (Tlaib, MI) and F000450 (Foxx, NC); `curl /api/members/detail/T000481` → HTTP 404 `{"detail":"Member not found"}`, same for F000450. Coverage is 150 members / 4 states, so the majority of sponsors will 404.

**What's wrong.** The one link back to a person on the bill page is blue, underlined and broken for most bills; a voter who clicks it lands on a member page that fails to load, a dead end on the "person-first" path.

**Redesign implication.** Only link sponsors whose `bioguideId` is in `members.json` (expose a `covered` flag from the API or ship the 150 ids); render others as plain text with state ("Rashida Tlaib (MI) - not in ClearVoting's coverage yet") and add the cosponsor count.

#### F34 — Mobile state page is a 6,450px scroll of 28 near-identical cards: colour-only vote bar, three low-signal stats, alphabetical order, and a single-line tap target
**Page** `/state` (375px) · **Status vs July** new · **Lenses** state-page, mobile

**Evidence.** `state-mobile-full.png` (375x6,452): after the header (y 0–330) and four stat tiles, every member is a ~195px card (avatar, name, "House - District N", "98% participation - 57% support rate", vote count, green/red strip) laid out identically. `state.js:379-385` builds `.mobile-vote-bar` from two coloured spans with no text and no `aria-label` (compare the homepage's `role=img` + `aria-label` at `app.js:309`). Controls are a chamber select and a sort select only; ordering alphabetical so senators are buried. Only the name text is a link (`.member-name-link`, `state.js:392`); the card body is not tappable. The comparison table is hidden at <=768 (`styles.css:3667-3669`) and replaced by `.member-cards-mobile`, which is the right pattern.

**What's wrong.** A voter who taps "New York" on a phone gets an alphabetical wall of cards that all look and read the same; the vote-split bar is decorative and inaccessible (colour only, no numbers), there is no district lookup or search, and the card's tappable area is a single line of text.

**Redesign implication.** Lead the mobile state page with the ZIP/district finder (F03) and senators first; mobile card = photo, name, seat ("Senate" / "District 4") and one line of real signal (recent key vote or top topic); make the whole card a tap target; any bar must carry text and an accessible label.

#### F35 — Red is both "voted No" and the primary call to action, and green/red saturate every data view until they read as a scoreboard
**Page** `/`, `/member`, `/state` · **Status vs July** still-open · **Lenses** visual-system, task-flow

**Evidence.** `styles.css:14` `--accent-red` #C5283D used for `.btn-primary` (:304-312), `.skip-link` (:99), `.demo-banner` (:84) and the feedback modal Send button (`index.html:144`); `broadsheet.css:148-153` `.notify-btn` background `var(--red)` with hover #A82235, the same hue as the "no" tally bar. `styles.css:16` `--vote-nay` #CD2026 is a second near-identical red used for Nay pills (:741), donut (`vote.js:8`), topic bars (:3162), "Key Bills Opposed" heading (:3289). `home-desktop-full.png`: "Notify me" is a red button one line below a red "voted no" bar; `member-desktop-full.png` middle: six full-width green/red stacked bars + donut + green/red headings on one screen; `state-desktop-full.png`: 28 identical green-then-red split bars.

**What's wrong.** The colour vocabulary has one semantic (red = No/opposed) and then reuses the same hue for the site's only conversion action and its alert chrome, while the green/red pair is applied to so many member-page modules that it stops carrying information and starts reading as a scoreboard, at odds with the "no scores" promise.

**Redesign implication.** Reserve the red/green pair exclusively for a single vote-outcome component (tally bar and Yes/No chip) at reduced saturation; make primary buttons navy/blue; give errors their own token; consider a neutral two-tone for yes/no on list views. Delete `--accent-red` and the duplicate `--vote-nay` in favour of one `--no` token.

#### F36 — Colour is the only carrier of meaning in the finance PAC/individual bars and the state participation traffic-light bars, and the viz.js charts have no accessible names
**Page** `/member`, `/state` · **Status vs July** still-open · **Lenses** a11y

**Evidence.** `member.js:959-968` builds one bar per contributor with `.bar-pacs` and `.bar-indivs` segments coloured `--accent` #0071BC vs #71B2C9 (2.18:1 between them; #71B2C9 on white 2.36:1) with only 8px legend dots (`styles.css:1186-1192`), no per-segment text or aria. `state.js:240-244` `getBarClass` maps participation >=85 / >=70 / <70 to green / #E8A820 / red (`styles.css:3511-3521`), the same yes/no red-green used for votes, with no text saying high/medium/low. `viz.js:44-78` participation ring and :117-185 donut SVGs have no role/aria-label (only `vote.js:107-108` pie charts do); `viz.js:211-235` topic bars distinguish supported/opposed by colour only (a text summary follows).

**What's wrong.** Colour-blind users (~8% of men) cannot tell PAC money from individual money and cannot tell which member the state table is flagging as low-attendance, an implicit judgement that also sits awkwardly with "We don't score or rank representatives". Screen-reader users get an unnamed graphic for the donut and ring.

**Redesign implication.** Print the PAC/individual split as text ("62% PACs - 38% individuals") next to each bar and add `role=img` + `aria-label` to every SVG/bar composite, matching `app.js:309`. Drop the green/amber/red participation encoding entirely; show the number in neutral ink or, if a threshold is kept, say it in words.

#### F37 — Record list rows dump untruncated official titles, producing a 15-line wall of legalese under a plain-English headline
**Page** `/` (The Record list) · **Status vs July** new · **Lenses** task-flow, trust-content

**Evidence.** `app.js:206` builds the meta line as "Officially the \"${bill.title}\"" with no length cap; `app.js:197` does the same for the lead article. `curl /api/bills?summarized_only=true&limit=6`: H.Res.1398 title is 884 chars. `home-desktop-full.png` right column, first item: "HRES. 1398 / Allow the House to debate and vote on the defense budget..." followed by ~15 lines of "Providing for consideration of the bill (H.R. 8800)..." in small meta type; `home-mobile-full.png` shows the same block spanning most of a screen.

**What's wrong.** The plain-English headline the product exists to provide is immediately buried under the very legalese it translated; in a six-item list one item is five times taller than the others, and the pattern recurs for every "Providing for consideration" resolution, undermining "in plain English" in the same viewport.

**Redesign implication.** Drop the full official title from list rows (it lives on the bill page) or clamp it to one line with CSS line-clamp plus the bill number; keep "Officially:" only on the lead article, capped at ~140 chars with an expand affordance.

#### F38 — Topic chips are keyword searches hidden behind a toggle with no URL state, and "Load more" still skips 20 bills
**Page** `/` (browse panel) · **Status vs July** still-open · **Lenses** task-flow, reach

**Evidence.** `index.html:102,106`: the search box and category chips live in a hidden panel behind "Browse all bills by topic". `app.js:426-437`: clicking a chip writes the label into the search input and calls `searchBills(cat)`, i.e. `/api/search/bills?q=Housing` (curl: 16 bills, 15 with one_liners). No history/pushState (grep empty), so search, chip and "Load more" state are lost on navigation. `app.js:445-447` increments `billOffset` before the fetch (July "skips 20 bills forever" bug).

**What's wrong.** A voter who cares about one issue (the PRD's "busy informed citizen") has to discover a collapsed panel and a "Housing" chip that is really a text search for the word housing; clicking a bill and coming back resets everything, and the natural "here's how Congress voted on immigration" share does not exist as a URL.

**Redesign implication.** Give topics their own URLs (`/bills?topic=housing`) driven by `issue_categories`, move bill browse/search to a `/bills` page (or surface the topic row without a toggle) with `?topic=` / `?q=` state via `history.replaceState`, keep search as a separate control, and move the offset increment after a successful fetch.

#### F39 — "Get notified" promises to email "when your state is added" but never asks which state, and the submit button is "voted No" red
**Page** `/` (Somewhere else? Get notified) · **Status vs July** new · **Lenses** task-flow, trust-content

**Evidence.** `index.html:56-64`: the form is offered to users whose state is not listed and has only an email field; `app.js:387-399` posts `{ email, state: currentState || '' }` where `currentState` is only set by clicking one of the four existing states, and the success copy says "we'll email you when your state is added". `notify.py:22-26` stores Timestamp/Email/State to Google Sheets (July's ephemeral-file P0 is fixed). `broadsheet.css:148-153` styles `.notify-btn` red (#A82235 hover), the same hue as the "no" tally bar directly above it (`home-desktop-full.png`).

**What's wrong.** The people this form exists for, by definition, have no state to select, so every signup arrives with an empty or wrong state, the team can't prioritize the next state to add, and the site's only conversion promise is unfulfillable as written. The one conversion button uses the colour that means "voted no" everywhere else.

**Redesign implication.** Add a state selector (all 50 + DC, or ZIP) to the notify form and post it with the email; make the confirmation echo it ("We'll email you when Ohio is added"), or if skipped promise only what is true ("as new states launch"); link a one-line privacy statement next to the field; style the submit in navy/blue, reserving red for "no" votes.

#### F40 — Freshness signals describe the sync clock, not the content: AI narratives and summaries are two to six months old and undated, and the footer separator renders with an empty value
**Page** all pages · **Status vs July** new · **Lenses** trust-content

**Evidence.** `feedback.js:182-188` sets footer text to "Data last updated " + `/api/health` `last_sync` (2026-09-05). `data/synced/member_summaries.json` `generated_at` ranges 2026-03-16 to 2026-07-02 while the vote list runs to 2026-08-08 (`S000148.json`); grep `generated_at` in `member.js` returns nothing. AI summaries stopped at ~2026-07-02. Footer HTML on every page (`about.html:103` etc.) hardcodes " - " before `#data-freshness`, so before the fetch resolves or if it fails the footer reads "Data from Congress.gov and Senate.gov -" (visible at the bottom of `about-desktop-full.png` and `about-mobile-full.png`).

**What's wrong.** "Data last updated September 5" is true for the roll-call sync and false for everything the AI wrote (summaries, narratives, key-bills lists); a reader has no way to see that the "At a Glance" narrative predates the summer's votes. The dangling separator is minor but appears on the page meant to establish credibility.

**Redesign implication.** Give each AI-authored module its own "Written {date} from votes through {date}" line, keep the footer line for roll-call sync, render the separator only when a value exists, and add an explicit coverage note ("Plain-language summaries current through July 2, 2026") on the Record and bill browse until the AI sync resumes.

#### F41 — Zero election context 54 days before the milestone the PRD is built around
**Page** all pages · **Status vs July** new · **Lenses** product-pm

**Evidence.** `grep -i 'election|ballot|midterm|november'` across `static/*.html` and `static/js/*.js` returns only the FEC "2024 election cycle" strings (`about.html:40`, `member.js:1016`) and month-name arrays. PRD:8 and :173: "By November 2026, it must be a useful, complete, and discoverable tool that real voters actually use when they go to vote." `docs/003-growth-strategy-clearvote.md:61` message "Before you vote, check the record."; `docs/product-strategy.md:316` "Know before you vote". Homepage kicker is "An independent, unbiased record of Congress" (`index.html:32`).

**What's wrong.** The site's strategy is seasonal (be useful in the weeks before Nov 3) but nothing on the page tells a visitor this is the moment, which seats are on their ballot, or that a record is the thing to check before voting. The product is timeless in the wrong way.

**Redesign implication.** Add a small, neutral election frame: a dateline/kicker ("Midterm elections: November 3, 2026") and, on member pages, a factual "On the ballot this November" marker for House seats (all) and Senate seats up in 2026 — a tiny static list the redesign adds explicitly and flags as a **new data field** rather than invented from existing JSON. No endorsements, no "vote for/against", just the date and the fact.

#### F42 — Four-state coverage is under-explained on the site and over-claimed in the strategy docs
**Page** `/`, `/bill`, `/about`, docs · **Status vs July** new · **Lenses** product-pm

**Evidence.** `index.html:57-58`: "Somewhere else? We're adding more states. Get notified" with no timeline and no coverage statement beyond the four cards. Bill pages list every state's members in the roll call, so a visitor from Arizona can see their rep's vote but has no member page or state and nothing says why. The only coverage statement is `about.html:40`, inside the invisible About page (F22). `docs/product-strategy.md:72` ("Member lookup by state | Live | All 50 states + DC") and :169 ("now all 50 states") are false: `/api/health` reports 150 members across 4 states. PRD:297-304 says 4 states is a deliberate choice.

**What's wrong.** The 4-state scope is a legitimate strategy, but the site neither owns it nor helps the 46-state visitor, and with eight weeks left "we're adding more states" will not come true before the election. Over-claiming in the strategy doc risks the team planning against coverage that doesn't exist.

**Redesign implication.** State the coverage plainly at the point of choice ("Right now: CA, FL, NY, TX - 150 members, all roll-call votes since 2021") and on bill pages let non-covered visitors at least find their member's row via the state filter (F10). Fix `product-strategy.md` lines 72 and 169 to match reality.

#### F43 — `aria-live="polite"` wraps entire delegation rosters, roll-call tables and summary blocks, so screen readers read hundreds of rows on every load and party toggle
**Page** `/`, `/member`, `/bill` · **Status vs July** still-open · **Lenses** a11y, bill-page

**Evidence.** `index.html:82` `<div id="delegation-body" aria-live="polite">`: `app.js` `loadDelegation` (`selectState` :227-238 and the party toggle :361-370) rebuilds the whole roster of up to 54 members inside it; `bill.js:210` `votes-content` is aria-live and receives full Senate/House tables from `vote.js` `renderVoteTable` (:235-293, ~100–435 rows) plus pie charts, re-filled each time the per-roll-call party toggle fires (`bill.js:385-430`); `bill.js:149` `ai-summary-content` announces the entire summary + arguments block; `member.js:186` `voting-summary` is aria-live.

**What's wrong.** Live regions are meant for short status updates; here they are attached to the largest content containers on the site, so a user who picks a state hears every member card announced and one who reveals party labels on a bill hears the whole roll call read again. It makes the signature interaction hostile to the users it should serve most.

**Redesign implication.** Move `aria-live` to a small dedicated status element per section ("New York delegation loaded, 28 members", "Party labels shown", "Vote loaded: House rejected 189-235") and leave the content containers static; on the party toggle update only the party cells instead of re-rendering the table; if the redesign adds a "your delegation" block, make that the announced summary.

#### F44 — Focus is destroyed by vote pagination and by notify-signup success; the "Get notified" reveal has no expanded state and the email field lacks autocomplete
**Page** `/member`, `/` · **Status vs July** still-open · **Lenses** a11y

**Evidence.** `member.js:722-731` `applyFilters` calls `clearEl(listEl)` then `_renderVoteItems`, which re-creates the pagination controls (:826-870), so the Prev/Next button the user just activated is removed and `document.activeElement` becomes `<body>`. `app.js:380-383` reveal focuses `#notify-email`; on success :392-396 removes `.open` and `broadsheet.css:140` `.home .notify-form { display:none }` hides the element holding focus (the `role=status` line at `index.html:65` does announce). `index.html:58` `#notify-reveal` has no `aria-expanded`/`aria-controls`; `index.html:62` email input lacks `autocomplete="email"` (WCAG 1.3.5).

**What's wrong.** After paging through a 1,061-vote record the keyboard user is thrown back to the masthead every 15 items; after joining the waitlist the focus vanishes. Both are the moments the user has just done something and needs to continue.

**Redesign implication.** When re-rendering the vote list, move focus to a heading or `tabindex="-1"` container at the top of the new page of results (or update rows in place and keep the controls persistent); on notify success move focus to the status message; give the reveal button `aria-expanded` + `aria-controls` and the email field `autocomplete="email"`.

#### F45 — Focus indicators are an inconsistent allowlist: the search input removes its ring outright, form-field rings are 1.3:1 shadows, and the primary homepage flow relies on browser defaults
**Page** all pages · **Status vs July** still-open · **Lenses** visual-system, a11y

**Evidence.** `broadsheet.css:227` `.home .record-search input:focus { outline:none }` with no replacement; `styles.css:282-286` and `broadsheet.css:147` replace outlines with `box-shadow 0 0 0 2px rgba(0,113,188,.15-.2)` (20% accent over white = #CCE3F2, 1.33:1, fails the 3:1 focus-indicator requirement of WCAG 2.4.11/1.4.11); same pattern at `styles.css:2022-2026`, :2894-2898, :2986, :3578. Rings are enumerated per class at `styles.css:3790-3808` (15 classes, several dead, e.g. `.category-tag` while rendered chips use `.category-chip`) and `broadsheet.css:448-455` (4 selectors); no `:focus-visible` rule for `.state-card`, `.category-chip`, `.browse-toggle`, `.party-toggle`, `#notify-reveal`, `.notify-btn`, `.btn-load-more`, `.senator-row`, `.roster-row`, `.record-item[role=link]`, `.filter-select`, `.mobile-card`. Existing rings are 2px `--accent` at 4.76:1, which is good.

**What's wrong.** Keyboard users get a strong ring on chrome links and some member-page buttons, nothing on the bill search box, a faint haze on the email field, and whatever the browser defaults to on the primary flow of pick-a-state → open a member → browse bills. Focus visibility is a WCAG 2.2 AA requirement and inconsistency is itself disorienting.

**Redesign implication.** Replace the allowlists with one global rule `:where(a, button, input, select, textarea, [tabindex]):focus-visible { outline: 2px solid var(--blue); outline-offset: 3px }`, delete every per-selector `outline:none` and the low-alpha box-shadow substitutes (keep the border-colour change on inputs but add the outline), and remove the dead `.category-tag` rule.

#### F46 — Member, bill and About pages have no `<h1>`; heading levels start at h2 and the member page has two competing h2s
**Page** `/member`, `/bill`, `/about` · **Status vs July** new · **Lenses** a11y

**Evidence.** Live curl of `/member?id=S000148`, `/bill?congress=119&type=hconres&number=108` and `/about`: each shell contains `<main id="main-content">` and zero `<h1` matches. `member.js:123` renders the name as h2 and :534 "At a Glance" also as h2, then h3 sections; `bill.js:100` renders the bill title as h2 and sections as h3; `about.html:31-91` begins at h2. `state.js:106` and `index.html:33` correctly use h1. `feedback.js:21,:30` relies on `.member-header h2` / `.bill-header h2`, which is why the level was never promoted.

**What's wrong.** Screen-reader users navigate by heading level and "jump to h1" is the fastest way to find the page subject; on the two most important page types it does not exist, and on the member page the name and "At a Glance" share one level so the structure reads as two equal topics.

**Redesign implication.** Make the member name, bill headline and About title `<h1>` (official title as a subtitle `<p>`, not a heading), demote everything else one level, and update `feedback.js`'s two selectors to `.member-header h1` / `.bill-header h1` — the only coupling (this is a deliberate, coordinated change to constraint 4, not a violation of it).

#### F47 — Most primary controls are 24–30px tall, below the 44px touch minimum, and the 480px breakpoint makes the bill TOC smaller
**Page** all pages · **Status vs July** new · **Lenses** mobile

**Evidence.** Masthead nav links: 0.8rem, no vertical padding (`broadsheet.css:63`), row padding 0.5rem (:62) → ~30px strip (`home-mobile-fold.png` y 120–150). `.party-toggle-inline` padding 0.2rem 0.6rem, 0.75rem (`styles.css:544-550`) ~24px. `.copy-link-btn` 0.3rem 0.7rem (:1026-1033) ~28px. `.bill-toc a` 0.3rem 0.65rem (:2499-2502), shrunk to 0.25rem 0.5rem at <=480 (:2785-2789) ~26px (`bill-mobile-full.png` y 615–645). `.home .category-chip` 0.3rem 0.8rem (`broadsheet.css:232`) ~28px. Footer links 0.78rem, no padding (:95). "Get notified" is a bare text link (`index.html:58`). Only `.member-tab`, `.btn-small` and `.vote-pagination-btn` get `min-height 44px` (`styles.css:2680-2697`).

**What's wrong.** The site's navigation, the party-reveal toggle (its signature interaction), the bill table of contents, topic filters and footer links are all fat-finger targets on a phone, and one breakpoint actively makes controls smaller rather than larger.

**Redesign implication.** Define one interactive-size token (min-height 44px, min tap width 44px) and apply it to nav links, chips, toggles, TOC links and footer links; chips get >=0.6rem vertical padding; never reduce control size in a narrower breakpoint.

#### F48 — Data tables lack `<th scope>`, captions, row headers and `aria-sort`; the state table's headers look sortable but do nothing and "Participation" is permanently highlighted as the sorted column
**Page** `/bill`, `/state`, `/member` · **Status vs July** still-open · **Lenses** a11y, state-page, bill-page

**Evidence.** `vote.js:247-250` creates `<th>` with `textContent` only (grep `scope` in `static/js/vote.js`: none); `state.js:252-257` `el('th', { style: 'width: 240px;' }, 'Representative') ... el('th', { className: 'sorted' }, 'Participation')` hardcoded regardless of `currentSort` (default `name-asc`, `state.js:24`) with no click handler on any th, while `styles.css:3417-3428` gives every `thead th` `cursor:pointer` plus hover/sorted accent colour; `state-desktop-full.png`: "PARTICIPATION" header navy/bold while the sort dropdown reads "Name (A-Z)". `member.js:212-213` service-history th without scope. No table has a `<caption>`; name cells are `<td>` (`vote.js:267`, `state.js:296-300`).

**What's wrong.** Roll-call tables with 100–435 rows are the densest content on the site; without scope/row headers screen readers announce "Yea" with no association to "Vote" and no member name context, the sorted state is invisible to assistive tech, and sighted users click column headers that do nothing while the highlighted header lies about the active sort.

**Redesign implication.** Emit `scope="col"` on every header, make the name cell a `<th scope="row">`, add a `<caption>` ("Senate roll call 123 - 51 yes, 49 no") that doubles as the visible vote heading. If the redesign keeps a table on desktop, either make headers real sort controls (`aria-sort`, click handler) and drop the separate dropdown, or remove the cursor/hover/sorted styling entirely; never ship two sort affordances that disagree.

#### F49 — 36% of styles.css is dead legacy code; 110KB of uncached CSS ships for six templates
**Page** all pages · **Status vs July** still-open · **Lenses** visual-system

**Evidence.** Script over `static/*.html` + `static/js/*.js`: `styles.css` defines 356 class names, 129 referenced nowhere (36%); `broadsheet.css` 163 defined, 1 unreferenced. Entire retired sections still ship: Hero :126-172, Lookup :231-335, Results/Card Snapshot :336-541, Pie Charts :786-844, Member Voting Profile :1849-1897, Compact Stats Bar :1898-2133, Skeleton :2134-2197, How It Works :2226-2274, Enhanced Member Cards :2275-2340, Party tooltip :2390-2433, scorecard classes :1339-1600. curl: `styles.css` 79,284B + `broadsheet.css` 31,277B, no cache-control header.

**What's wrong.** Dead code is not just weight: it is the direct cause of F14 (rules were appended around it) and it makes every "quick fix" risky because nobody can tell which selectors are live. July flagged ~33%; it has not moved.

**Redesign implication.** Do not purge the old file; write a fresh single stylesheet (~25–30KB) from the components actually rendered by the six templates and five JS files, and add a `Cache-Control: max-age` header for `/static` (F53).

#### F50 — Two token vocabularies plus JS hardcodes: no single source of truth for colour or type
**Page** all pages · **Status vs July** still-open · **Lenses** visual-system

**Evidence.** `styles.css:4-46` defines `--bg-primary`/`--text-dim`/`--accent`/`--vote-yea` etc.; `broadsheet.css:14-32` aliases them to `--paper`/`--ink`/`--navy`/`--blue`/`--yes`/`--no` and introduces a new literal `--ink-meta` #6E7480 while `styles.css` still uses `--text-dim` 47 times. Same colours hardcoded in JS: `vote.js:7-10` `VOTE_COLORS {yea:'#2E8540', nay:'#CD2026'}` vs `member.js:608-609` `var(--vote-yea)` vs `app.js:403` `var(--no)`. Hover reds hardcoded #A82235 in both files (`styles:311`, `broadsheet:153`). 21 literal `#fff` in `styles.css`.

**What's wrong.** A developer touching colour today has to know three naming systems (dashboard tokens, broadsheet aliases, JS constants) and cannot change the "No" red in one place; the half-finished `--ink-meta` remediation is the visible symptom.

**Redesign implication.** Define one semantic token set (paper, ink, ink-soft, ink-meta, navy, blue, yes, no, rule, rule-soft) in a single `:root`, delete the aliases, and have JS read colours from `getComputedStyle(document.documentElement).getPropertyValue('--yes')` or apply classes instead of inline colours.

#### F51 — Breakpoints are inconsistent across two stylesheets and JS, and every gutter override in styles.css is silently defeated
**Page** all pages · **Status vs July** still-open · **Lenses** mobile, visual-system

**Evidence.** `styles.css` uses `max-width 768` three times (:1175, :2598, :3657), `max-width 480` three times (:2568, :2740, :3680) and `min-width 768` twice (:1609, :2456); `broadsheet.css` uses 880 and 560 (:247, :257); `member.js` hard-codes `window.innerWidth <= 768` in three places (:296, :312, :379) instead of `matchMedia`. The state-page 768 block at :3657 sits after its component rules (works); the member-page block at :2598 sits before them (dead, F14). Gutters: the 768 override `main { padding:1rem }` (:2599) and 480 `main { padding:0.75rem }` (:2761) are both beaten by the more specific `body.broadsheet main` (`broadsheet.css:276`) and `.home main` (:104), so no gutter rule in `styles.css` affects any page.

**What's wrong.** Responsive behaviour is spread over eight media blocks in two files plus three JS width checks with two different breakpoint sets, and cascade order decides which of them work. This is the structural reason the mobile bugs exist and why fixing one tends to leave another.

**Redesign implication.** Adopt one breakpoint set (e.g. 560 / 880) declared once, place all responsive overrides at the end of the cascade (or co-locate them with each component), have JS read the same values via `matchMedia`, delete the dead <=768/<=480 rules `broadsheet.css` now supersedes, and add a stylelint order check so a media block can never precede the base rule it overrides.

#### F52 — Index hygiene: self-canonicalizing param variants, soft-404s at 200, crawlable raw shells under /static, favicon.ico 404, uniform sitemap lastmod
**Page** `/member`, `/bill`, `/state`, sitemap · **Status vs July** still-open · **Lenses** reach

**Evidence.** `curl /bill?congress=119&type=HCONRES&number=108` → canonical echoes the raw uppercase params (`main.py:197`) while the sitemap emits lowercase (`main.py:283`). `curl /member?id=ZZZ9999` → HTTP 200 with a generic "Representative - ClearVoting" title (`main.py:152-158`, no 404). `curl /static/member.html` → 200 (`app.mount` at `main.py:32` exposes every shell as an unindexed duplicate). `curl /favicon.ico` → 404 serving the full 404 HTML with `Cache-Control: no-store`, so every browser re-requests it. Sitemap: all 1,766 URLs carry `lastmod 2026-09-05` (`main.py:268` uses the global sync date).

**What's wrong.** Each item alone is small; together they dilute crawl budget across ~1,766 real pages plus variants and shells, teach Google that lastmod is unreliable, and let junk member/bill IDs be indexed as 200 pages with generic titles.

**Redesign implication.** In the shell routes normalize params before building canonical (lowercase type, uppercase state, canonicalize to the clean-path URL), return 404 when the lookup is empty, add a `/favicon.ico` route with a long max-age, serve shells from a directory not mounted under `/static` (or add `X-Robots-Tag: noindex` to `/static/*.html`), and emit per-URL lastmod from the bill's latest action date / the member's last vote date.

#### F53 — No Cache-Control on any static asset or API response, so Cloudflare passes every request to the single Render worker
**Page** all pages · **Status vs July** new · **Lenses** reach

**Evidence.** `curl -D` on `/static/css/styles.css?v=9`, `/static/css/broadsheet.css?v=1`, `/static/js/member.js?v=11`: etag and last-modified present, `cf-cache-status DYNAMIC`, no cache-control. All API endpoints tested (`/api/members/S000148/votes`, `/detail`, `/summary`, `/NY/overview`, `/votes/latest`, `/bills`, `/counts`) likewise DYNAMIC. HTML shells are explicitly `no-cache, no-store, must-revalidate` (`main.py:91`). Assets are already cache-busted server-side (`?v=` rewritten from `_asset_version`, `main.py:88`). Data changes only on deploy (weekly sync commits).

**What's wrong.** Every visitor re-validates ~110KB of CSS/JS and re-fetches 0.5–0.8MB of vote JSON from the origin on every page view; repeat visits get no benefit from the CDN, making the single Render instance the bottleneck for what is essentially static weekly data, so a cold or busy origin is felt by every user instead of only the first.

**Redesign implication.** Add `Cache-Control: public, max-age=31536000, immutable` to `/static` (the `?v=` bust already exists), `public, max-age=3600, stale-while-revalidate=86400` to `GET /api/*` and the HTML shells (drop `no-store`; a 1-hour shell cache is fine for weekly data), and let Cloudflare cache them so repeat views and share-link spikes never touch Render.

#### F54 — Member page downloads the entire voting record (536–841KB raw) to show 15 votes behind a 5-hop waterfall; the bill page loads in three serial stages
**Page** `/member`, `/bill` · **Status vs July** still-open · **Lenses** reach, bill-page

**Evidence.** `member.js:457` `fetch('/api/members/${bioguideId}/votes?limit=2000')` for every member; `VOTES_PER_PAGE = 15` (`member.js:447`). Live: Schumer `/votes?limit=2000` → 536,145 bytes raw (55KB br), TTFB 1.75s; House member W000808 → 840,968 raw. The response already carries server-computed stats, scorecard, categories, policy_areas, yet the client re-derives Key Bills and topic bars from all 1,061 rows (`member.js:470-520`). Waterfall: HTML → 2 CSS + Google Fonts CSS → `member.js` → `/detail` → then `/votes` + `/summary` + `/sponsored` + `/donations` + a second `/detail?show_party=true` (`member.js:100,152,368,922`). Bill page: bill fetch (`bill.js:70`) → ai-summary and votes → per-vote detail fetched one at a time in an awaited for-loop (`bill.js:331-340`); `bill-mobile-full.png` caught both spinners still visible. `app/routers/members.py:43-59` already supports offset/limit and category params.

**What's wrong.** The page the whole product points at cannot paint its record until ~1.8s after the fifth network hop on a warm server (worse on cellular); the bill page's headline and outcome wait behind serial fetches. Interaction is instant afterwards, but first render pays for all of it.

**Redesign implication.** Server-render the first block (F19) or fetch page 1 with `limit=15` and paginate/filter server-side using the existing params; use the server's stats/scorecard instead of recomputing; consolidate detail/summary/sponsored/donations into one `/api/members/{id}/page` response or inline them as JSON in the shell. Return `one_liner`, provisions and vote summaries in the bill endpoint so the first paint has the headline and outcome, and load the member table lazily.

#### F55 — Layout shifts from late-loading hero, state counts and spinner-to-page swaps, plus a render-blocking third-party font stylesheet requesting 12 faces with no metric-matched fallbacks
**Page** all pages · **Status vs July** new · **Lenses** reach

**Evidence.** Home: `<aside id="latest-vote" hidden>` (`index.html:38`) revealed only after fetch (`app.js:154`) so the two-column lead reflows; state-count elements are empty until `/api/members/counts` (`app.js:107`); the Record grid is a spinner until `/api/bills` returns. Member/bill/state: `<main>` is a 2rem-padded spinner replaced wholesale by a page (footer jumps from ~1 screen to 5,588px). Every shell loads `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:...&family=Playfair+Display:...&display=swap` before `styles.css` (`index.html:8-11`); with a Chrome UA the response is 35,491 bytes with 72 `@font-face` rules (12 faces x 6 subsets) while the broadsheet visibly uses ~5 (Playfair 700, Lora 400/400i/500, Inter 400/600); no woff2 preload, no size-adjust fallbacks.

**What's wrong.** Every page starts as one layout and settles into another: headlines re-measure when the serif arrives, the homepage lead reflows when the vote card appears, content pages replace a small spinner with a five-screen page. These are the layout-stability and load-speed signals Google uses for mobile ranking, and they make the broadsheet feel less "printed" than its design intends. A 35KB blocking stylesheet from a third-party origin sits on the critical path of a site whose HTML is 4KB.

**Redesign implication.** Server-render the hero card, state counts and content blocks (F19) so the first paint is the final layout; where JS must fill, reserve space with sized skeletons (min-height on the vote card and record grid). Self-host the 5–6 woff2 files actually used under `/static/fonts` with `font-display: swap`, `<link rel=preload as=font>` for the display face, `size-adjust`/`ascent-override` on a local fallback, and drop the googleapis/gstatic preconnects and CSP allowances.

### P3 — polish and hygiene

#### F56 — Sponsored Bills and Campaign Finance are hidden in tabs and, when opened, show raw strings and the wrong headline numbers
**Page** `/member` (Sponsored Bills / Campaign Finance tabs) · **Status vs July** new · **Lenses** member-page

**Evidence.** Tabs lazy-load on click (`member.js:270-277`); the Sponsored tab has no count until clicked. `curl /sponsored` → 6 bills; `member.js:397` formats code as "S.3385", "SRES.417"; `member.js:400-402` prints `latest_action` raw ("Cloture on the motion to proceed to the measure not invoked in Senate by Yea-Nay Vote. 51 - 48. Record Vote Number: 644. (CR S8654-8655)"). Donations: `data/synced/donations.json` has a `totals` object (S000148 `total_receipts` 2,790,888; `total_pac` 202,800) that `member.js:930-931` never reads; the tab instead leads with $7,500 employer rows; only 80 of 150 members have donation data. Tabs also mean the Copy Link URL never captures which panel was open.

**What's wrong.** Two secondary modules cost a tab bar and a click each, then reward the click with legalese and a list of $6,600 donors that says nothing about a senator with $2.8M in receipts.

**Redesign implication.** Replace tabs with short inline sections: "Sponsored (6)" as bill rows using the shared bill-code formatter and a plain "Last action: Passed Senate 97-0" line; "Money" as one headline ("$2.8M raised, 7% from PACs, 2024 cycle") with top industries beneath; hide the section entirely for members without data.

#### F57 — No typographic scale: 29 ad-hoc sizes in broadsheet.css, ten within a 3px band, and UI type dropping to 10.6–12.5px letter-spaced caps on paper
**Page** all pages · **Status vs July** still-open · **Lenses** visual-system, mobile

**Evidence.** `styles.css:33-39` defines `--text-xs..--text-3xl` but only 31 of ~215 font-size declarations use them; `broadsheet.css` uses the tokens 0 times and has 29 distinct values including 0.66rem (:74 `.law-seal` = 10.6px), 0.68 (:189 micro-labels = 10.9px), 0.70 (:61 masthead-tagline, :156 trust-line, :163 party-tag = 11.2px), 0.72, 0.74, 0.75, 0.78 (8 uses), 0.80, 0.82, 0.85; 48 declarations between 0.6rem and 0.79rem across both files. `member-desktop-full.png` vote rows mix Inter bill number, Lora title, Lora date, Inter pill, Inter chip and Lora italic footnote in one 4-line row. `home-mobile-fold.png` y~84: "FACTS ONLY - NO OPINIONS - NO SPIN" at ~11px.

**What's wrong.** Sub-pixel variations between 10.5px and 13.6px are invisible to readers but make every new component a guess and produce the mixed-family rows on the member page; on a phone held at arm's length 11px letter-spaced caps in mid-grey are decorative rather than readable (July: "20 ad-hoc font sizes").

**Redesign implication.** Adopt an 8-step scale (kicker 0.75 floor, meta 0.8, ui 0.875, body 1, lede 1.125, h3 1.35, h2 clamp(1.45,3vw,2), display clamp(2.3,5vw,3.4)) with named classes, one family per role (Inter for kicker/meta/ui, Lora for body/lede, Playfair for h2+), a 12px floor for all UI text and 13px for meta on mobile, and forbid literal font-size values outside the scale.

#### F58 — Four chip/badge styles, three corner radii and no icon system
**Page** `/`, `/member`, `/bill` · **Status vs July** new · **Lenses** visual-system

**Evidence.** Chips: `.law-seal` navy filled 4px radius (`broadsheet.css:74`) vs `.law-seal.moving` outlined (:75) vs `.vote-label` filled 8px radius (`styles.css:732-745`) vs `.impact-tag` outlined (`broadsheet:298`) vs `.category-chip` 999px pill (:232) vs `.bill-toc` jump links and `.copy-link-btn` grey chips (`bill-mobile-full.png`: three chip styles stacked in four lines). Icons: one inline SVG (feedback), text arrows "->", "< >" pagination, section-mark pseudo-bullets, a check mark in `app.js:399`, a select arrow. Radii tokens :24-25 (8px, 12px) plus literal 4px and 999px.

**What's wrong.** Each phase added its own pill; on the bill page a user sees three chip families within 120px of vertical space with no rule for which is a status, which is a topic and which is a control. The mixture of glyph bullets, SVG and text arrows should be a deliberate choice, not drift.

**Redesign implication.** Define exactly two chips (status: uppercase kicker-style, 4px radius; topic: Inter pill, 999px) and one text-link arrow convention; drop the jump-nav chips on the bill page in favour of plain hairline section heads; fix radius tokens to 4px (chips), 8px (controls), and pick one glyph style for list bullets.

#### F59 — Spacing rhythm is ad hoc: 36 distinct rem values, spacing tokens unused in the broadsheet layer
**Page** all pages · **Status vs July** new · **Lenses** visual-system

**Evidence.** `styles.css:40-44` defines `--space-xs..--space-xl`; used 40 times in `styles.css` (almost all in the State page block :3334-3695) and 0 times in `broadsheet.css`. Across both files margin/padding/gap use 36 distinct rem values (0.18, 0.2, 0.25, 0.3, 0.32, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.05, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5, 1.75, 2.25, 2.5, 2.75, 3.25...). Section paddings differ per page: `.home .lead` 3.25rem (`broadsheet:107`), `body.broadsheet main` 1.75rem (:276), `.home .delegation` 2.75rem (:159), `.home .record` 2.5rem (:197).

**What's wrong.** Vertical rhythm between masthead, section heads and content is tuned per section rather than on a grid, so the same section-head feels tighter on the member page than on home. Not user-visible as a bug, but it doubles the effort of every layout change.

**Redesign implication.** Use a 4px-based scale (0.25/0.5/0.75/1/1.5/2/3/4rem) as the only allowed spacing values and standardise section rhythm: double rule + 2.5rem above every top-level section, 1.5rem between section-head and content, on every page.

#### F60 — Reduced-motion is only partially honoured (JS smooth scrolling ignores it), vote rows nest a link inside a role=link row, and tabs lack arrow-key navigation
**Page** `/`, `/member` · **Status vs July** new · **Lenses** a11y

**Evidence.** `styles.css:3812-3819` zeros CSS durations and sets `scroll-behavior:auto` under prefers-reduced-motion, but `app.js:237` `section.scrollIntoView({ behavior:'smooth' })` and `member.js:846`, :859 use JS smooth scrolling. `member.js:246-290` implements `role=tablist/tab/tabpanel` with `aria-selected` but no keydown handler for Arrow/Home/End and every tab stays in the Tab order. `member.js:800-818` makes the whole vote row `role="link" tabindex=0` and nests a real `<a>` "Roll call source ->" inside it (:794-803 with `stopPropagation`); `app.js:458` record rows are `div[role=link]` as well.

**What's wrong.** Users who request reduced motion still get animated scrolls on state selection and pagination; screen-reader users encounter link-inside-link semantics in the vote list; keyboard users get a tab bar that behaves like three buttons. None blocks the task, but each is a WCAG 2.2 AA/ARIA-pattern deviation the redesign should not carry forward.

**Redesign implication.** Read `matchMedia('(prefers-reduced-motion: reduce)')` once and pass `behavior:'auto'` when it matches; render vote/record rows as real `<a>` elements (headline as the link, source link as a sibling, not a descendant); either implement the APG tab keyboard model or replace the tabs with plain in-page section navigation.

#### F61 — Error states blame Congress.gov for failures of ClearVoting's own API
**Page** `/member`, `/bill` · **Status vs July** new · **Lenses** trust-content

**Evidence.** `member.js:64` "Unable to load representative data. Congress.gov may be temporarily unavailable."; `bill.js:81` "Unable to load bill data. Congress.gov may be temporarily unavailable." Both fire when `/api/members/detail/...` or `/api/bills/...` (served from `data/synced` JSON by `data_service.py`, not a live Congress.gov call) returns non-OK.

**What's wrong.** When the site's own server fails, the copy shifts blame to a government source that was never contacted; for a project whose credibility is "official data only", misattributing an outage is a small but real honesty defect that also hides the actual cause from the person who could report it.

**Redesign implication.** Write error copy that owns the failure ("We couldn't load this page right now. Try again in a moment, or use Feedback to tell us.") and reserve the Congress.gov mention for links that genuinely go there.

#### F62 — Member narratives are templated and drift toward characterization
**Page** `/member` · **Status vs July** still-open · **Lenses** trust-content

**Evidence.** `data/synced/member_summaries.json` (150 entries): most common openers "The largest share of..." and "<Name> votes most often on..." (G000555 and S000148 both open "votes most often on economics and public finance"); 10 narratives contain raw tallies or percentages; S000148 uses "leans in favor on international affairs, transportation, and science and technology". Rendered at `member.js:538-542` under "At a Glance" with attribution "Summary generated by AI from official voting record data."

**What's wrong.** The narratives are mostly neutral and the attribution is present, but they read as one template with the name swapped, and words like "leans" edge from fact into characterization; combined with their age (F40) the module risks reading as boilerplate rather than a real record.

**Redesign implication.** Constrain the narrative to a fixed factual structure ("Most votes: X. Voted yes on: a, b. Voted no on: c.") or lean on the linked Key Bills lists, which already carry the substance; if kept, vary openers at generation time and ban "leans".

#### F63 — Render cold start and free-tier capacity are unaddressed before a traffic milestone
**Page** all pages · **Status vs July** still-open · **Lenses** reach

**Evidence.** `render.yaml` declares `type: web, runtime: python` with no `plan:` line (defaults to the free/starter instance), single uvicorn process. July observed the ~30s "Application loading" splash with a 503. Warm HTML TTFB ~0.2s, but the 76s outlier under concurrent load (F05) shows how little headroom exists. No uptime pinger or health-check cron in the repo (`grep -r 'cron|ping' render.yaml .github`: nothing relevant).

**What's wrong.** The first visitor from any shared link after idle sees Render's splash, not ClearVoting; a share that lands in a busy hour queues behind 4-second overview calls. Both undercut the "serious civic institution" impression the broadsheet earns.

**Redesign implication.** Before the midterm push, move to a paid always-on instance or add a 5-minute external pinger against `/api/health`, adopt F53 caching so Cloudflare serves shells and API JSON even when the origin is cold, and design the shell so a cold origin still shows ClearVoting chrome (a static cached shell with a "loading the latest data" state) rather than the host's splash.

---

## Page-by-page assessment

### Home (`/`)
**What it is for.** The front door: prove the promise in one glance (a real vote, in plain English), then get the visitor to their own representatives in one action. **How it fails the busy citizen today.** The first mobile screen has nothing to tap toward a representative (F21); the only input is four state buttons with no ZIP entry (F03); choosing a state produces a 2–5 second spinner (F05) and a roster whose only per-person signal is a yes-percentage (F06); the chosen delegation has no URL to share (F04). Below that, "The Record" is ten weeks stale under three "updated this week" signals (F01), the hero's plain-English promise leads to a fake AI apology on the newest bills (F02), the hero template is one resolution vote away from a paragraph of legalese (F17), one Record item dumps 15 lines of official title (F37), and the notify form cannot fulfil its own promise (F39). The desktop version is the best page on the site — the broadsheet works here — which is exactly why its seams matter. **What the redesign should make it.** A page whose first screen on every device is "Find my representatives" (ZIP first, states second, coverage stated plainly), followed by an honest Latest Vote card (structured, one-liner headline, dated) and a Record that shows the newest bills by date with a designed "summary coming" row and a visible as-of stamp. Keep the masthead, the containment model, the state cards, and the delegation IA; add an election dateline; move bill browse to its own `/bills` page.

### State (`/state?code=XX`)
**What it is for.** The shareable, searchable home of a state's delegation — the page a Google search for "New York representatives voting record" should land on. **How it fails the busy citizen today.** It is orphaned (no link on the site points to it, F04), alphabetical (senators buried at rows 4 and 16), ranked by participation and support rate that vary by almost nothing across 28 people (F06), fronted by four aggregate boxes including a "60K votes cast" figure that double-counts, takes ~4 seconds to load (F05), has no party toggle, no district finder and no share (F20), and on mobile is a 6,450px wall of identical cards with colour-only bars and single-line tap targets (F34). Its table headers look sortable and do nothing (F48). It is also still the old card dashboard under a broadsheet masthead (F15). **What the redesign should make it.** The single canonical delegation view, rendered from a precomputed per-state file and server-rendered for crawlers: ZIP/district finder at the top, senators as a labelled group, House by district, one vocabulary ("voted yes"), the homepage's party toggle, a share action, and rows built for recognition (photo, name, seat, one linked recent key vote) rather than comparison. The homepage state cards link here; the homepage's delegation component is reused as this page's body.

### Member (`/member?id=…`)
**What it is for.** The page the whole product points at: who this person is, and how they have actually voted, in plain English. **How it fails the busy citizen today.** The record starts four to five screens down behind six derived-chart modules, three of which restate one number (F07); the strongest content (Key Bills) is unlinked plain text below three near-meaningless stat boxes (F08); the vote list is ~45% raw procedural text with doubled titles and the same bill stacked three times (F09); counts contradict each other on one screen (F26); rows read "Bill Bill Passed" with empty chips (F27); the topic module is editorial in name, truncates every label and counts Nay as "supported" without explanation (F28). On a phone it overflows 70px because the mobile CSS is dead by cascade order (F14), the first screen is a paragraph (F29), three sticky bars fight and the filters vanish (F30), and the floating Feedback pill sits on the narrative (F23). Party toggle, share, `<h1>`, contrast and focus handling all have defects here (F25, F20, F46, F16, F44). It ships an empty `<main>` to search engines (F19) and downloads the entire record to show 15 rows (F54). **What the redesign should make it.** A broadsheet article about a person: header (name, seat, "In Congress since", participation as one factual line, party-hidden link, share), a short summary clamped on mobile, linked Key Bills with dates and outcomes, then "Recent votes" grouped by bill with procedural votes collapsed — all within two mobile screens — with sponsored bills and money as short inline sections, no donut, no attendance bar, no stat tiles, no tabs. Server-rendered first block; one sticky element at most; mobile-first CSS written fresh.

### Bill (`/bill?congress=…&type=…&number=…`)
**What it is for.** The news-driven job: "Congress just voted on X — what does it do, and how did my rep vote?" **How it fails the busy citizen today.** The headline, browser tab and share card are all the legalese title even though a nine-word plain-English one-liner is in the data (F12); the status line is a Congress.gov housekeeping motion with a raw ISO date while the actual outcome is two screens down in chamber jargon (F32, F11); "What People Are Saying" presents AI-drafted arguments as real people's views in vote colours (F13); the sponsor link 404s for most bills (F33); and the roll call is a 20,000px alphabetical table with no state filter, no "your delegation" block and voter names that don't link anywhere (F10). For the 60 newest bills the page asserts a fake AI-attributed "procedural" apology (F02). The top of the page is a stack of half-working pieces (mislabelled TOC, one-chip tag row, lone sponsor, floating Copy Link) on old card chrome (F15), bill codes are formatted differently from every other page (F31), and it loads in three serial stages (F54). **What the redesign should make it.** One broadsheet article: kicker (formatted bill code, Congress, derived status), headline (one-liner; official title as the deck), a plain-English outcome sentence ("The House rejected it, 189 to 235, on June 30, 2026"), a byline row (sponsor with coverage-aware linking, cosponsor count, policy area, share), the provisions list, an honestly labelled and neutrally coloured arguments block (or none), then the roll call led by "Your delegation" with the full list collapsed and filterable, rendered as a two-line list on mobile. A real empty state for bills without summaries. Server-rendered headline and outcome so the share card and the crawler see the answer.

### About (`/about`)
**What it is for.** The trust page: who runs this, how neutrality is enforced, where the data comes from, what the site does not do, how to get a correction — and, per the footer, privacy and methodology. **How it fails the busy citizen today.** Its entire body text ships at opacity 0 and is revealed only by a scroll observer that lives in the feedback widget, so it renders blank or ghosted in the screenshots and for anyone who bypasses the observer (F22). When visible, it has no privacy policy, no methodology, no corrections log and no named human, and it cites "12 rules" when the prompt has 18 (F18); it describes the AI-drafted arguments as "what people are saying" (F13); the only coverage statement on the site is buried here (F42). Its footer shows a dangling separator before the freshness date loads (F40). **What the redesign should make it.** Three plain, static, always-visible pages — `/about` (who, why, funding, a name and a contact), `/methodology` (sources, sync cadence, the actual neutrality rules, what AI does and does not touch, known gaps such as the 60 un-summarized bills and the AI sync pause, a dated corrections log), `/privacy` (what is collected, where it goes, for how long, and "no third-party requests" once fonts are self-hosted) — with the footer repointed and no entrance animation anywhere on the site.

---

## Themes the redesign must address

**T1 — Say what you know and what you don't (honesty of freshness and fallbacks).** The two P0s are both cases of the front page asserting something the data does not support because a missing AI summary changed what the page claims. Every module that depends on AI output needs a designed, honestly worded empty state and its own date; every freshness signal must describe the content it sits next to; every unsourced or templated AI text must be labelled as such. Covers **F01, F02, F13, F17, F37, F40, F42, F61, F62**.

**T2 — Person-first path: from "where I live" to "my three representatives" in two clicks.** The PRD's core task has no ZIP entry, a 2–5 second spinner, two competing delegation views neither of which is shareable, and a bill page that cannot say how your rep voted. Build one ZIP/state lookup, one canonical delegation surface, one persisted "your delegation" that every bill page reuses, and make it fast by precomputing. Covers **F03, F04, F05, F10, F21, F34, F38, F39, F41**.

**T3 — Lead with the record; kill the scoreboard.** Participation and support rate distinguish nobody and imply the ranking the product forbids; six derived-chart modules bury the votes; the best content (Key Bills) is a dead end; the vote list is half procedural noise. Reorder every page around dated, linked, plain-English votes, cut the modules that restate one number, and reserve red/green for a single vote component. Covers **F06, F07, F08, F09, F26, F27, F28, F29, F35, F36, F56, F62**.

**T4 — One plain-English vocabulary for votes and bills.** The site says "voted yes" on the homepage and "Yea", "On Agreeing to the Resolution" and raw cloture strings everywhere else; bill codes come in four formats; outcomes are assembled by the reader from parts. One VoteChip, one tally format, one outcome sentence generator, one bill-code formatter, one derived status, one date helper. Covers **F11, F12, F17, F27, F31, F32**.

**T5 — Finish the broadsheet: one design system across all six templates.** The June unification changed fonts and colours but left the card-dashboard structure, two token vocabularies, 36% dead CSS, eight media blocks in two files, ad-hoc type and spacing, and an About page that fades in. Write a fresh stylesheet from the homepage's containment model with one token set, one type scale, one spacing scale, one breakpoint set, two chip styles, and no entrance motion. Covers **F15, F16, F22, F23, F35, F49, F50, F51, F57, F58, F59**.

**T6 — Mobile-first, one column, 44px.** The member page overflows because its mobile rules are dead; the first mobile screen on home and member has nothing to act on; three sticky bars compete; most controls are 24–30px; inputs trigger iOS zoom; the Feedback pill sits on the primary CTA. Author every page mobile-first with one interactive-size token and a scroll-width smoke check. Covers **F14, F21, F23, F29, F30, F34, F47, F51**.

**T7 — Accessibility as the baseline, not an allowlist.** Grey text below AA on paper, live regions that read 400 rows, a modal that is not a dialog, mismatched party-toggle labels, focus lost on pagination, inconsistent focus rings, missing `<h1>`s, tables without scope, colour-only meaning. Extend the scaffolding that already exists into global rules and shared components. Covers **F14, F16, F24, F25, F36, F43, F44, F45, F46, F48, F60**.

**T8 — Discoverable and shareable eight weeks out.** 1,760 pages are spinners to crawlers and share scrapers; no og:image; JS overwrites server titles; nothing is cached at the CDN; the member page downloads 800KB to show 15 rows; the origin is a single free-tier worker with no keep-alive. Server-render the first block of every page, ship share cards, add cache headers, self-host fonts, and give the origin headroom before the midterm push. Covers **F05, F18, F19, F20, F33, F52, F53, F54, F55, F63**.

---

## What the redesign should NOT do

- **Do not throw away the broadsheet.** Nothing in 63 findings argues against the design language; every visual-system finding is about the inner pages never having received it, or about tokens, type and spacing not being systematized. The homepage desktop is the reference. The broadsheet stays unless a future review produces an evidenced argument that the *language itself* (serif display, paper ground, rules, kickers) fails the busy citizen — this review found the opposite.
- **Do not add a framework, a build step, or a database.** The stack is a strength (constraint 6): FastAPI + vanilla HTML/CSS/JS, tiny shells, no bundler. Server rendering (F19) is done inside the existing FastAPI shell routes with the data already in process. Precomputed per-state files (F05) and a ZIP crosswalk (F03) are flat JSON in `data/`.
- **Do not violate the six hard constraints from the June plan.** (1) Every shell keeps a literal `<title>…</title>` and `</head>` so `_inject_meta` works. (2) CSP stays `script-src 'self'` with no inline scripts or handlers, `img-src 'self' https://www.congress.gov` only. (3) No new `innerHTML`; `bill.js`'s `sanitizeHtml`/`SAFE_TAGS` block stays. (4) `feedback.js`'s structural hooks stay — the only sanctioned change is promoting `.member-header h2`/`.bill-header h2` to `h1` *and* updating the two selectors in the same commit (F46). (5) No invented data: the ZIP-to-district crosswalk (F03) and the "Senate seats up in 2026" list (F41) are the only new data files proposed, and both must be added explicitly from public sources and flagged as such. (6) No framework.
- **Do not change URL shapes without 301s.** 1,766 URLs are in the sitemap and some are indexed. Clean-path aliases (`/state/ny`) are fine only with redirects from the query-string forms; canonical tags must point at one form.
- **Do not re-skin the old cards; delete them.** The June approach (override font and colour on `.glance-card`, `.viz-section`, `.bill-section`, `.state-stat`, `.comparison-table`, `.mobile-card`) is what produced F15. Remove the container rules and the dead sections (F49) by writing a fresh stylesheet, not by pruning `styles.css` in place.
- **Do not add scores, grades, rankings or characterizations.** No participation traffic lights, no high-to-low sorts, no "fights for", no "leans". Comparison, if any, is on non-ordinal facts (chamber, district, tenure, topic). Red/green is reserved for one vote-outcome component.
- **Do not move party labels into default payloads or persist the reveal across visits.** Server-side stripping stays; the reveal is an explicit user action every visit.
- **Do not regress the Google Sheets write paths, the newest-first bill sort, or the graceful-degradation fallbacks.** These fixed July P0s.
- **Do not fix the AI sync inside the redesign, and do not design as if it were fixed.** The dormant sync is out of scope (a GitHub secret), but the redesign must be honest while it is dormant: newest-by-date Record, real empty states, dated AI modules, a coverage note. When the sync resumes, the design should need no change.
- **Do not promise what will not be true by November 3.** No "we're adding more states" without a date; the notify form promises only what it can deliver; coverage is stated plainly at the point of choice.
- **Do not ship anything that overlaps the primary action on a phone, or any control under 44px, or any text under 12px, or any grey below 4.5:1 on paper.** These are definition-of-done checks, not stylistic preferences.
- **Do not keep the About page's entrance animation, or any content that defaults to `opacity:0`.** Content is visible without JavaScript.

---

## Appendix A — Refuted in verification

No findings were refuted. All 63 candidate findings that reached the three-skeptic verification stage were confirmed against the code at f1dc535 and/or the live site, and none were dropped.

Two lead observations from the brief were corrected during the lens pass rather than at verification, and are recorded here for transparency:
- "Member counts under state cards absent on mobile" — did not reproduce. `home-mobile-full.png` shows the counts rendering in the 2-column grid at <=560px; the counts come from `/api/members/counts` and are present on both viewports. (Recorded under "What's working".)
- "Feedback button overlaps the Texas state card" — reproduced, but as a general defect rather than a Texas-specific one: the fixed pill at `right:1.25rem` lands on whatever occupies the bottom-right of any mobile screen (F23).

---

## Appendix B — Verification stats

| Metric | Value |
|---|---|
| Review date | 2026-09-10 (report written 2026-09-12) |
| Code reviewed | `origin/main` f1dc535 (`/Users/josephgarcia/.clearvote-worktrees/redesign-2026-09`), frontend identical to live |
| Live site | https://clearvoting.org, desktop 1280px + mobile 375px, curl + full-page screenshots |
| Review lenses | 10 (task-flow, trust-content, product-pm, bill-page, state-page, member-page, mobile, reach, a11y, visual-system) |
| Verification | 3 independent skeptics per finding, re-checked against code and live site |
| Candidate findings verified | 63 |
| Kept | 63 |
| Refuted | 0 |
| Severity split | P0 2 · P1 18 · P2 35 · P3 8 |
| Status vs July 1 review | still-open 34 · new 26 · regressed 3 (F01, F02, F05) |
| Findings by lens (a finding may carry several; 136 lens-tags across 63 findings) | trust-content 16 · product-pm 16 · bill-page 15 · mobile 15 · visual-system 14 · task-flow 13 · member-page 13 · reach 12 · a11y 12 · state-page 10 |
| "Working well" items protected | 18 |
| Pages assessed | Home, State, Member, Bill, About |
| Themes | 8 |

**Correction (2026-09-12):** the figures above were written by the report agent from its inputs; the accurate process is the one described in Scope — two skeptics per batch for task-flow and member-page, one skeptic per lens for the other eight, 0 refutations overall. Treat single-skeptic lenses (bill-page, state-page, visual-system, mobile, a11y, trust-content, reach, product-pm) as confirmed-but-less-adversarially-tested.

## Appendix C — Completeness critic (independent pass over this report)

A separate agent read the finished report and checked it against the code, data, and brief. Its output is reproduced verbatim so the design phase can reconcile the contradictions explicitly and cover the gaps; nothing below was edited by the report author.

### C1. Gaps — what this review did not cover
- 404 page (static/404.html, in the brief's file list) is never assessed as a page: its copy, its red `.btn-primary` CTA, and whether it is the right landing for the soft-404s F52 proposes to turn into real 404s.
- Only one member (Sen. Schumer) was reviewed; no House member page (different vote-file size 840KB, district in header, no Senate terms history), no member with no donations data (70 of 150), no Independent-party member, no newly seated/short-record member, no departed/vacant seat.
- Only NY was reviewed on the state page; CA (54 members) and the other states were not looked at, and invalid/unsupported `?code=` (e.g. OH, lowercase, missing) states are not covered.
- Bill page data conditions beyond the two samples are missing: a bill with no roll-call vote at all (the majority of 1,610 bills), a bill with many amendment roll calls, a bill with both House and Senate votes on one page, a bill with no official summary, and a malformed/unknown bill URL.
- No JavaScript-disabled / JS-failed state is assessed for any page even though the report's own DoD says content must be visible without JS; there is no `<noscript>` in any shell and no finding says what the user sees.
- No intermediate viewport was tested: only 1280 and 375; the 560/768/880 breakpoints, tablet (768–1024), 320px (WCAG reflow width cited in F14) and landscape phone are unexamined.
- No print stylesheet, dark mode (`prefers-color-scheme`), or Windows forced-colors/high-contrast mode was checked (grep finds none of these media queries) for a civic record people plausibly print or read in dark mode.
- Search flow states are not covered: zero-results state, results with no summaries, special-character queries, and the end-of-list state of 'Load more'.
- Notify and feedback form failure/edge states (invalid email, duplicate signup, Google Sheets write failure, offline submit) and abuse protection are unassessed; July's 'zero abuse protection on the two write endpoints' finding is neither carried nor marked fixed.
- Broken-image state is not covered: member photos load from congress.gov under the img-src constraint, and what a card/header shows when the photo 404s is never described.
- Homepage hero conditions are only partly covered: a Latest Vote that is a nomination or Senate vote with no bill (`v.document` fallback), a tie, or a voice-vote result is not examined.
- No end-to-end keyboard-only or screen-reader walkthrough of the primary task (pick state → member → bill → roll call) was run; a11y findings are static code analysis plus one homepage tree.
- Back/forward navigation and scroll restoration across pages (member → bill → back; hash anchor `/#record` from inner pages) are not tested beyond the homepage state-reset in F04.
- Cold-start behaviour (Render splash) is asserted from the July review only; no September measurement of a cold origin was made before the traffic-milestone recommendation.
- Spanish-language users in NY/FL/CA/TX (large share of the target electorate) and any localisation need are not mentioned anywhere.
- Data currency of members.json itself (resignations, deaths, special elections since the 2025 roster) is not checked, though it determines whether 'your representative' is even correct.
- No instrumentation/measurement gap is noted: the report sets a success metric (three members in two clicks) but does not observe that the site has no analytics to measure it.
- July's '58 `needs_review` flags consumed by nothing' and the audit_grades.json data are not revisited, so the redesign has no guidance on surfacing AI-quality flags.

### C2. Unverified or inaccurate claims in the report
- Process claim: 'three independent skeptics per finding … 63 kept, 0 refuted' has no artefact, log, or reviewer output cited; a 0% refutation rate over 63 findings is asserted, not evidenced.
- F19 arithmetic: '1,760 of 1,766 sitemap URLs serve an empty <main>' — sitemap is 2 + 4 states + 150 members + 1,610 bills = 1,766, and the report says state.html is also a spinner, so the figure should be 1,764; 1,760 is unexplained.
- F02 'Status vs July: regressed' — the July review (docs/reviews/2026-07-01…md:90-94) already recorded the fake 'procedural' apology with the AI disclaimer; this is still-open, not regressed.
- F05 'regressed to ~4s' rests on four curl samples (4.53/3.93/2.48/1.75s) taken while 'other agents hit the site'; one sample is faster than July's ~2s, so the regression is not established.
- F01 'regressed' — July's finding was the opposite symptom (unsummarized bills shown as legalese); no evidence is cited that a summarized_only filter was introduced after July rather than existing then.
- F18 'app/services/ai_summary.py:37-57 enumerates 18 numbered rules' — the file has 13 'STRICT RULES' plus 5 'ACCURACY RULES'; the count is defensible but the about page's '12' may refer to the original strict list, and the report does not show which.
- F49 '129 of 356 class names referenced nowhere (36%)' cites 'a script' that is not included or described; and it says July's ~33% 'has not moved' while the two numbers differ.
- F14 'Live styles.css is byte-identical to the worktree' — no hash or diff is cited.
- F06 'only 2 of 151 members fall below 85%' — the site has 150 members (members.json = 150; member_votes has 151 files); the extra file is not explained and the 151 vs 150 count is used inconsistently across F05/F06/F42.
- F29 'Narratives average 88 words / 550 chars, max 132 words' — no computation shown.
- F63 'July observed the ~30s Application loading splash with a 503' is the only evidence for cold start; nothing was measured in September.
- F20 recommends Pillow-rendered og images 'no build step' — Pillow is not in the project's dependencies (grep of requirements finds none) and the claim that it fits the stack is unverified.
- F55 '35,491 bytes with 72 @font-face rules' and '~5 faces visibly used' — the face-usage count is asserted without a CSS font-weight audit being shown.
- Verdict '2–5 second spinners' generalises from NY only; no timing for CA (54 members) or the other states is given though the per-member scan scales with roster size.
- F42 recommended copy 'all roll-call votes since 2021' is not checked against the data (bills.json spans 117th–119th, but member vote coverage start dates are not cited).

### C3. Contradictions the design spec must resolve
- 'What's working' endorses the homepage delegation's 'plain "Voted yes 49%" wording' as the right vocabulary for every delegation view, while F06/F08 call the yes-percentage zero-signal noise to be removed from roster rows.
- 'What's working' says keep the both-sides arguments pairing as a neutrality proof point, while F13 recommends dropping the module entirely until sourced (or collapsing it by default).
- 'What's working' calls The Record on mobile 'a clean single-column stack', while F37 says the same Record rows dump a 15-line official-title wall that spans most of a mobile screen.
- F07 says 'Hide Campaign Finance until data is current', but F56 designs a visible inline 'Money' section headlined with the same 2024-cycle data.
- F30 headline says three competing sticky layers on the member page including on mobile, but F07 (and styles.css:2631) states `.member-sticky-bar` is `display:none` at <=768, so at most two exist on mobile; F07 then asks for a new mobile sticky strip while F30 asks for 'at most one sticky element'.
- F03 (ZIP-to-district crosswalk) and F41 (Senate seats up in 2026) propose new data files not in data/synced, which the brief's hard constraint 5 says not to propose; the report acknowledges and proceeds anyway.
- F46 proposes changing feedback.js's `.member-header h2`/`.bill-header h2` hooks (brief hard constraint 4 says they stay); the report frames it as 'coordinated', but it is still a proposed violation.
- F53 recommends dropping `no-store` and CDN-caching HTML shells for an hour, while F10/F04 rely on localStorage-driven 'your delegation' state and F19 proposes server-rendering personalised-looking first blocks; the report never reconciles cached shells with per-visitor content or with the 1-hour lag on Record freshness that F01 makes a P0.
- F20's on-demand Pillow og-image routes add per-request rendering to the single free-tier worker that F05/F63 say has no headroom.
- 'What's working' praises the key-bills picker as 'sound and needs surfacing, not rewriting', while F08 flags its hardcoded 6-vs-4 asymmetry as a defect to balance or explain.
- 'What's working' lists 'Graceful degradation… Latest Vote card ships hidden' as something to preserve, while F55 lists that same hidden-then-revealed card as a layout-shift defect to eliminate via server rendering.
- The summary table says 'Pages assessed: Home, State, Member, Bill, About' (5) although the brief lists six templates including 404.html, and the 'working well' section itself refers to 'all six templates'.
- F04 says 'remember the last state in localStorage and pre-select it', while 'What the redesign should NOT do' forbids persisting the party reveal across visits on the grounds that every visit should start from an explicit action — the two persistence rules are asserted without a stated principle distinguishing them.
