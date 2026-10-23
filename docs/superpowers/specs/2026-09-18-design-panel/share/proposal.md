# ClearVoting redesign — Approach "Arrive from a share"

Mobile-first landing pages for the member and bill URLs; the homepage shrinks to a ZIP field and the latest votes.
Written 2026-09-18 against the review of 2026-09-10 (F01–F63) and the brief. Mockups: `home.html`, `member.html`, `bill.html` in this folder (open from `file://`; 375px first, then ≥768 and ≥1100). All names, votes, dates, tallies and ZIP-to-district shares in the mockups are copied from `data/synced/` and the Census crosswalk in `tools/data/raw/`.

---

## (a) Thesis

Between now and November 3 most visits will be a phone opening a link someone texted or posted — a member page ("look how she voted") or a bill page ("the House just passed this") — not the homepage. So every member and bill URL is designed as a landing page: it orients in one sentence (who/what, plain English, the outcome), answers "how did *your* representatives vote" using a ZIP the browser remembers, puts a real share action and a real share card on the page, and keeps the task inside the first screen with nothing floating over it. The homepage becomes a short door: a ZIP field and the latest votes.

## (b) Information architecture

URLs that exist after the redesign (no shapes change; two new static pages, one optional parameter):

| URL | Role | Change |
|---|---|---|
| `/` | Door: ZIP entry + latest roll calls | Shrinks. Bill browse/search moves to `/bills`. |
| `/state?code=NY` (+ optional `&zip=11570` or `&district=4`) | The single delegation view; ZIP results land here with the user's district lifted to the top | Canonical form unchanged; homepage delegation renderer retired. No clean-path alias (not needed for the share thesis; avoids the 301 surface). |
| `/member?id=S000148` | Landing page for a person | Rebuilt |
| `/bill?congress=119&type=hr&number=4795` (+ optional `&zip=`) | Landing page for a vote/bill | Rebuilt |
| `/bills` | Newest bills and roll calls by action date, with the search box | New static page reusing the Record row component (search UI moved from `/`) |
| `/about`, `/methodology`, `/privacy` | Trust pages; footer links repointed | Two new static pages |
| `/404` | Real 404 with the ZIP field | Rebuilt |
| `/og/default.png`, `/og/member/{id}.png`, `/og/state/{code}.png`, `/og/bill/{c}/{t}/{n}.png` | Share cards | New routes |

Primary path: **shared link → member or bill page → "Your representatives" block** (ZIP remembered → three linked rows; no ZIP → inline ZIP field) **→ the other two members' pages → Share.** The homepage path is the same block one step earlier: ZIP → `/state?code=NY&zip=…` → member page.

Where you live is remembered (`localStorage["cv-zip"]`, `["cv-district"]`, `["cv-state"]`); every member and bill page reads it on load and fills its "Your representatives" block client-side. Party reveal is *not* remembered across visits (see (h)).

## (c) Page by page

### Home `/`
**For.** Get a first-time visitor to their own three members in one action; show that the site is alive (latest real votes, dated).
**Mobile fold (375×~700).** Masthead (compressed to ~110px) → election dateline strip → kicker + H1 "See how your representatives vote." → one-line deck → **ZIP field + "Find my representatives" button** (both 48px) → coverage line with the four state links. If a ZIP is remembered, a "Last time: ZIP 11570 · New York's 4th district → Show my representatives" panel sits under the field. The latest-votes list begins just below the fold.
**Desktop (≥1100).** Two columns: left (5/12) the lead + ZIP form, sticky; right (7/12) "The latest votes". No hero card, no state grid, no Record grid, no notify form, no browse/search.
**Modules in order.** 1 Masthead · 2 Election dateline (server-rendered, removed after Nov 3) · 3 Lead + ZIP form (+ remembered-ZIP panel or split-ZIP chooser) · 4 The latest votes: the three most recent roll calls across both chambers, each with chamber/date/bill kicker, headline (one-liner if it exists, else official title with the "Plain-English summary not yet written" seal and a clamped official-summary line), the outcome sentence, and — when a state is remembered — "New York: 13 yes · 11 no · 2 didn't vote" plus the user's own rep's chip · 5 Coverage note ("summaries exist for bills acted on through June 30, 2026") · 6 Link to `/bills` · 7 Footer with Send-feedback button.
**Cut and why.** The Latest Vote hero (its sentence template is one resolution away from legalese, F17; the latest-votes list gives the same fact structured). The four state cards as primary input (ZIP is what people know; states remain as text links, F03). The homepage delegation renderer (one delegation surface, F04/F05). The Record grid (stale under the summary filter, F01; replaced by newest-by-date rows here and the full list on `/bills`). Bill search/topic chips (moved to `/bills`, F38). The notify form (promises what it can't deliver, F39; replaced by an honest coverage link in the footer). The floating Feedback pill (F23).

### Delegation / State `/state?code=NY`
**For.** The shareable home of a state's delegation and the landing for a ZIP result.
**Mobile fold.** Masthead → election strip → kicker "New York · 28 members" + H1 "New York's representatives" → Share + party toggle row → if `zip`/`district` is present: **"Your representatives" block** (2 senators + the district's House member, 64px rows) with "Change ZIP"; otherwise the ZIP field → then "Senators" group.
**Desktop.** Same single column at 720px reading width with the ZIP/share aside on the right at ≥1100.
**Modules.** 1 Header · 2 Your representatives (or ZIP field; split-ZIP chooser when the crosswalk returns 2+ districts ≥5% share, listing each district's member and the land-area share; "Not sure?" links to the full list and house.gov by address) · 3 Senators (2 rows: photo, name, "U.S. Senator · since 1999", seat-up-in-2026 seal from the sanctioned list) · 4 House by district ascending (26 rows, each: photo, name, "District 4 · since 2025 · on the ballot Nov 3", and the member's most recent final-passage vote with a plain headline as the one varying fact) · 5 Share card + sources aside.
**Cut and why.** Stat boxes, Total Votes, participation bars, colour thresholds, metric sorts, the sortable-looking table (F06, F48, F34); the alphabetical order (F04); the "Voted yes 49%" micro-labels (F06, see (h)). The server renders the whole roster from the precomputed state file, so the page is complete without JS; JS only lifts the user's three rows to the top.

### Member `/member?id=S000148` — see `member.html`
**For.** "Who is this, and how do they actually vote" for someone who just tapped a link, plus the bridge to their other representatives.
**Mobile fold (375×~700).** Compressed masthead → election strip → photo (72px) + kicker "United States Senator · New York" + H1 + one factual line ("In Congress since 1981 — House 1981–1999, Senate since 1999 · Voted in 1,060 of 1,061 roll calls since 2021") → **Share this record** (44px, navy) + party toggle → ballot line ("Not on the ballot Nov 3 · seat next up in 2028 · New York's 26 House seats are all on the ballot") → **Your representatives** (three 64px rows; this page marked "You're here"). Key votes start at the fold's edge. When the header scrolls off, a single 44px sticky strip (name + Share) replaces the masthead — the only sticky element.
**Desktop (≥1100).** Main column (2/3): header with 96px photo and the action group to the right; ballot line; Your representatives; Key votes; Recent votes; In summary; Money. Aside (1/3, sticky): share card preview + Share + Congress.gov; Sources & corrections.
**Modules in order.** 1 Header · 2 Ballot line · 3 Your representatives · 4 Key votes — "Voted yes" (3) / "Voted no" (3), balanced, each a link to `/bill` with "H.R. 6500 · Senate passed it, 90 to 6 · Aug 8, 2026", with a caption stating the selection rule · 5 Recent votes grouped by bill: one row per bill (headline = one-liner, else "S. 5271 — official title" with the seal; member's chip; outcome sentence; a `<details>` "2 procedural votes on this bill" listing cloture/motions with their chips); ungrouped amendments render honestly as "Amendment: 'To strike section 2019.' · parent bill not identified in our data" with the roll-call source link; "Show 20 more votes" + the counts line "1,061 roll calls since 2021 · 519 yes · 540 no · 1 missed" · 6 In summary: the AI narrative, dated "Jun 13, 2026", clamped to three lines on mobile behind "Read the summary", with "votes most often on" topics as a meta line · 7 Money: collapsed, headed "FEC · 2024 election cycle · as of Mar 20, 2026", omitted entirely for the 70 members without data · 8 Share card + Sources aside · 9 Footer with feedback button.
**Cut and why.** Donut, attendance bar, three stat tiles, six topic bars, Service History card, tabs, the two filters (F07, F26, F28, F30): they restate one number or distinguish nobody, and they push the record four screens down. Sponsored Bills tab (deferred; a "Bills they sponsored" link to Congress.gov replaces it until a designed list exists, F56). "What They Fight For by Topic" (editorial, F28). Copy-link chip (replaced by Share, F20). Floating Feedback pill (F23).

### Bill `/bill?congress=119&type=hr&number=4795` — see `bill.html` (the no-summary state)
**For.** "Congress just voted on X — what does it do and how did my rep vote?" for someone who arrived from a post.
**Mobile fold.** Masthead → election strip → kicker "H.R. 4795 · 119th Congress" + status seal "Passed the House · not yet law" → H1 (one-liner when it exists; official title when it doesn't — the mockup shows the latter) → **outcome sentence in Lora: "The House passed it, 237 to 169, on September 3, 2026."** with a labelled tally bar → byline (introduced date, sponsor with coverage-aware linking, cosponsor count, topic, Congress.gov) → Share + party toggle → **"How did your representatives vote?"**: three rows with chips when a ZIP is remembered; otherwise the ZIP field (mockup shows the empty state). Sticky strip on scroll: "H.R. 4795 · House passed it, 237–169 · Share".
**Desktop.** Main column: header, Your representatives + by-state roll call, What this bill does, Where it stands. Aside: share card, Sources.
**Modules in order.** 1 Header + outcome · 2 How did your representatives vote (ZIP block) · 3 By state: four `<details>` groups with per-state tallies ("New York: 13 yes · 11 no · 2 didn't vote"), the user's state open by default, rows in district order with chips and links to `/member` · 4 "All 433 votes, every state" collapsed: name search + vote filter, two-line rows, uncovered members plain text, roll-call source link · 5 What this bill does: with a summary → one-liner headline already used, provision bullets with the section mark, "Officially: …" kicker, AI disclaimer under it; without → the dashed empty note "We haven't written a plain-English summary for this bill yet…" then the CRS official summary's first paragraph promoted, rest behind "Show the full official summary" (sanitized via the existing SAFE_TAGS block). No section-mark bullet, no AI disclaimer, no "Generating…" copy in this state · 6 Arguments (only when a summary exists): headed "Possible arguments, drafted by AI — not attributed to anyone", collapsed on mobile, neutral rule colours, prefixes stripped at render · 7 Where it stands: derived milestones ("Passed the House · Sep 3, 2026", "Introduced · Jul 29, 2025") instead of the raw latest-action string · 8 Share card + Sources aside.
**Cut and why.** TOC row, tag row, Copy Link chip, "Sponsors" card (F15); raw "House Vote #232 / On Agreeing to the Resolution / Result: Failed" block and the roll-call donut (F11); the 431-row table (F10); the fake "procedural" apology (F02).

### About / Trust `/about`, `/methodology`, `/privacy` (+ `/404`)
**For.** Let a teacher or a sceptic check who runs this and how neutrality is enforced in under a minute; and give a lost visitor the same door as the homepage.
**Mobile fold.** Kicker + H1 + the first paragraph, fully visible with no JavaScript and no entrance animation.
**Modules.** `/about`: who (a name and contact), why, funding, the four-state coverage statement with the reason, the November milestone. `/methodology`: data sources and sync cadence; what AI writes and what it never touches; the neutrality rules copied from `ai_summary.py` (no count in prose); known gaps — "60 of 1,610 bills have no plain-English summary; summaries exist for bills acted on through June 30, 2026"; how the key-votes rule works; a dated corrections log; the feedback route. `/privacy`: ZIP and party choice stay in the browser; the notify email and feedback text go to a Google Sheet; fonts self-hosted so no third-party request is made. `/404`: kicker "Not found", one sentence, the ZIP form, and links to `/bills` and `/state?code=…` — served with status 404 for soft-404s (F52); no red CTA.
**Cut.** The opacity-0 scroll reveal (F22); the "12 rules" claim (F18).

## (d) Visual system decisions

- **Palette and faces unchanged**: paper `#F5F6FA`, navy `#112E51`, blue `#0071BC`/`#205493`, Playfair Display / Lora / Inter. One token set in a fresh `broadsheet.css` (the old `styles.css` container rules are deleted, not re-skinned).
- **Type roles** (six sizes, nothing else): `--t-1` 12.8px Inter for kicker/meta/chips (the floor); `--t0` 14.4px Inter for UI and captions; `--t1` 17px Lora body; `--t2` 20px Playfair section heads; `--t3`/`--t4`/`--t5` for H1s via `clamp()`. Headlines in lists are Lora 500 (member/bill rows) or Playfair 700 (the latest votes on home) — bills read as text, not as tiles.
- **Colour semantics**: navy = structure and primary action; blue = links and kickers; grey ink `--ink-meta #5F656D` (5.45:1 on paper) is the single metadata colour, `--text-dim` is deleted; **red/green appear only inside the VoteChip and the tally bar**, with darker text variants (`--yes-text #1F5E2D`, `--no-text #8E1B21`, 6.9:1 and 7.8:1 on their tints) so no grey or green text sits below AA. The primary button is navy, never red.
- **Rules, not cards**: sections are separated by 1px hairlines; a 3px double rule marks the page's main task block ("Your representatives" / "Key votes") and the footer; the only boxed elements are the empty-state note (dashed), the remembered-ZIP panel and the share-card preview. No box shadows, no nested white cards.
- **VoteChip**: one component, labels "Yes" / "No" / "Didn't vote" / "Present", 28px pill, tinted background + border + text so the meaning survives greyscale. Used by home, state, member, bill.
- **Outcome sentence**: one generator, "The {House|Senate} {passed it|rejected it|agreed|…}, {yeas} to {nays}, on {date}", with the question map ("On Passage" → "Final vote to pass"; cloture → "Vote to end debate (needed 60)"; "Motion to Proceed" → "Vote to take up the bill").
- **Status seals**: navy filled for law/final state, outlined blue for moving, outlined grey for "Plain-English summary not yet written" and "Not on the ballot Nov 3" — the fallback state has its own mark so it can never be mistaken for content.
- **Touch targets**: `--tap: 44px` on every link row, button, summary, nav item and footer link; inputs 48px at 16px+ font (no iOS zoom); person rows 64px (52px inside roll-call groups).
- **The feedback control**: no floating pill. `#feedback-open` becomes a 44px ghost button in the footer ("Send feedback about this page") and the same id/modal are kept, so `feedback.js` hooks are untouched; the modal gets `role="dialog"`, a labelled textarea and focus return (F24). The page-context line the widget reads still comes from `.member-header h1` / `.bill-header h1` after the sanctioned h2→h1 promotion with selectors updated in the same commit.
- **Sticky**: at most one sticky element per page — a 44px name/outcome strip that appears only after the header scrolls out on <1100px, and only on member/bill/state.
- **Breakpoints**: 375 first; ≥768 widens gutters and puts header actions beside the photo; ≥1100 adds the aside column. Responsive rules live next to their module.
- **Election context**: a one-line dateline under the masthead on every page ("Election Day is Tuesday, Nov 3, 2026 · 46 days away"), computed server-side and removed after the date; per-member ballot line from the sanctioned Senate-seats file (House members are always "on the ballot Nov 3").
- **Photos**: 48/72/96px bordered squares; on load failure the `<img>` is replaced by a bordered initials block in Inter (no broken-image icon), handled in JS since CSP forbids inline handlers.

## (e) Finding coverage

| Finding | How this approach resolves it |
|---|---|
| F01 | Home shows the newest roll calls by date regardless of summary status, with the "summary not yet written" seal, an "as of Sep 5, 2026" stamp and the coverage note "summaries exist for bills acted on through June 30, 2026". `/bills` lists all bills newest-first the same way. |
| F02 | The hero is gone. Bill page renders a real empty state (dashed note, official CRS paragraph promoted, no section-mark bullet, no AI disclaimer, no "Generating…"); `ai-summary` returns `{available:false}` and the client renders the empty state from that. Home's first latest-vote row links to the bill with the seal visible before the tap. |
| F03 | ZIP field is the first control on home, state, bill (no-ZIP state), member (when nothing is remembered) and 404, backed by the Census crosswalk; split ZIPs show every district ≥5% share with the member's name and the land-area share; unknown ZIPs fall to the state list + house.gov address lookup. Success metric: three own members reachable in one action from any entry. |
| F04 | One delegation surface (`/state?code=XX`), homepage state links go there, `?zip=`/`?district=` lift the user's rows; the homepage renderer and `document.title` overwrite are deleted; ordering is senators then House by district everywhere. |
| F05 | Precomputed `data/synced/state_overview/{code}.json` at sync time; the state page and the "Your representatives" block read only that file and `members.json`; the per-request 28-file scan is removed. |
| F06 | No participation/support metrics anywhere on lists. Rows carry photo, name, seat, tenure in words, ballot status, and one recent linked vote. Participation survives only as the header's "Voted in 1,060 of 1,061 roll calls" fact line. |
| F07 | Member order is header → ballot line → Your representatives → Key votes → Recent votes → summary → money. Donut, attendance, stat tiles, topic bars, Service History, tabs are cut; service history is folded into the fact line (correctly: House 1981–1999, Senate since 1999). |
| F08 | Key votes are linked rows with outcome and date, balanced 3/3 with the rule stated, built on the same row component as Recent votes; state/home rows show one linked recent vote. |
| F09 | Recent votes are grouped by bill with procedural votes in a `<details>`; one headline slot (one-liner → "bill number — official title" → "Amendment: … parent bill not identified"); the duplicate title div is gone. |
| F10 | Bill page leads with the outcome band and "How did your representatives vote?" (ZIP-driven), then by-state groups with per-state tallies and linked rows, then "All 433 votes" collapsed with search/filter as two-line rows; uncovered members are plain text. |
| F11 | Outcome sentence at the top of the bill page and on every vote row; one VoteChip vocabulary (Yes / No / Didn't vote); question strings mapped to plain phrases; official terms only in the roll-call source link. |
| F12 | H1 = one-liner when it exists, official title as the "Officially:" kicker; when absent the official title is the H1 (mockup shows this). Server `<title>` = "{bill code} — {one-liner or 70-char official title} \| ClearVoting"; client never sets `document.title`. |
| F13 | Arguments block kept only when a summary exists, relabelled "Possible arguments, drafted by AI — not attributed to anyone", neutral rule colours, prefixes stripped, collapsed on mobile; About/methodology describe it honestly. |
| F14 | Member page rewritten mobile-first with `minmax(0,1fr)` and no fixed-width stat rows; responsive rules co-located; a scroll-width smoke check at 320/375 is part of definition of done. |
| F15 | All three inner pages are composed on the homepage containment model (hairlines, double rules, kickers); the `.glance-card/.viz-section/.bill-section/.state-stat/.comparison-table/.mobile-card` rules are deleted. |
| F16 | Single meta token `#5F656D`; `--text-dim` removed as a text colour; 12.8px floor; chip text tokens verified ≥6.9:1. |
| F17 | Hero removed; the latest-votes rows are structured (kicker, headline, outcome sentence) and never splice a title into a sentence template. |
| F18 | `/about`, `/methodology`, `/privacy` as real static pages; footer repointed; fonts self-hosted so the privacy page is true. |
| F19 | Server renders the first block of member (header, fact line, key votes, first 12 grouped votes), bill (header, outcome, by-state roll call, summary or empty state) and state (whole roster) inside `<main>`; home's latest votes are server-rendered. JS enhances (ZIP lift, pagination, share, party). |
| F20 | `og:image` + `summary_large_image` on every page from `/og/...` routes; server owns `<title>`; a navy "Share" button in the header action group (and the sticky strip) calling `navigator.share` with prewritten text and the canonical URL, clipboard + "Link copied" toast fallback; share on state pages too. |

P2/P3 also resolved: F21 (ZIP is on the first mobile screen), F22 (no opacity-0 content), F23 (no floating pill), F24 (dialog semantics), F25 (one party control, one label, session-only), F26 (one counts line from the data), F27 (row metadata regenerated), F28 (topic module cut), F29 (fact line + task block on the first screen), F30 (one sticky element, 16px inputs), F31 (one bill-code formatter), F32 (derived milestones instead of raw latest action), F33 (coverage-aware sponsor linking), F34 (recognition rows, 64px), F35/F36 (red/green only in the chip and labelled bar), F37 (official titles clamped to 2 lines), F38 (search moves to `/bills`; topic chips deferred), F39 (notify form removed), F40 (every AI module dated), F41 (election dateline + ballot lines), F42 (coverage stated at the ZIP field), F46 (h1 on every page), F47 (44px everywhere), F55 (no hidden-then-shown blocks; server-rendered), F57–F59 (six-step type scale, 4px spacing tokens, two chip styles), F61 (error copy names ClearVoting). Not addressed here: F43/F44/F45/F48/F60 beyond what the components imply (engineering hygiene in the build), F49–F51 (follow from the fresh stylesheet but are not designed), F53/F54 (in (f)), F56 (sponsored bills deferred), F62 (narrative prompt), F63 (ops).

## (f) Data/backend touches (small, named)

1. **ZIP crosswalk** — `tools/data/build_zip_crosswalk.py` (exists) emits `data/zip_districts.json` (Census 2020 ZCTA↔CD119, public domain, attribution in `/methodology`); new `GET /api/zip/{zip}` in `app/routers/members.py` returns `[{state, district, share, member_ids}]` or `{unknown:true}`; only shares ≥0.05 returned.
2. **Senate seats up in 2026** — `data/senate_2026.json` (sanctioned list, source cited); read in `app/services/data_service.py` to add `on_ballot_2026` / `next_election` to member detail and state overview.
3. **State overview precompute** — sync step writes `data/synced/state_overview/{code}.json` (roster in delegation order + each member's latest final-passage vote); `app/routers/members.py` `/overview` and the new server-rendered `/state` block read it.
4. **Record/latest-votes fallback** — `data_service.get_bills` gains `order=action_date` with `one_liner: null` preserved; `/api/votes/latest?limit=3` returns the last N roll calls across chambers with per-state tallies (`votes/{chamber}/*.json` already carry per-member state).
5. **AI-summary empty state** — `app/routers/bills.py` returns `{available:false, coverage_through:"2026-06-30"}` instead of the apology string; `bill.js` renders the empty note.
6. **Server-rendered content block** — `app/main.py` `_serve_html` gains a second injection point: a `<!--content-->` marker inside `<main>` replaced by HTML built with Python string templates (escaped) for member/bill/state/home; `<title>`/`</head>` untouched; client scripts detect the rendered block and skip the fetch.
7. **og:image** — `app/routers/og.py` with Pillow (add to `requirements.txt`; verify the Render build): default, state and member cards pre-rendered at sync into `static/og/`; bill cards rendered on first request and written to disk, `Cache-Control: public, max-age=31536000, immutable`. `_inject_meta` emits `og:image`, width/height, `twitter:card=summary_large_image`.
8. **Caching** — static assets `public, max-age=31536000` with the existing `?v=` busting; HTML shells and JSON APIs `public, s-maxage=600, stale-while-revalidate=3600` (was `no-store`); personalised state never comes from the server (see (h)). Fonts self-hosted under `static/fonts/` (CSP already allows `'self'`).
9. **Titles** — `main.py` bill title uses the one-liner or a 70-char word-boundary cut; the three `document.title` lines are deleted.

## (g) Scope, risks, deferrals

| Page / piece | Size |
|---|---|
| Home | S |
| State | M |
| Member | L |
| Bill | L |
| About / Methodology / Privacy / 404 | S |
| `/bills` list page | S |
| Crosswalk endpoint + ZIP block component | M |
| State precompute + server-rendered blocks | M |
| og:image routes + meta | M |
| Caching, fonts, titles | S |
| **Total** | **L** — roughly three build-loop phases; one PR |

Risks: (1) Server-rendered blocks duplicate rendering logic in Python and JS — mitigated by keeping the server block small (header + first list) and having JS take over from the same DOM. (2) Pillow on Render's build — if it fails, ship a static default card first (still fixes "no og:image"). (3) ZCTA ≠ USPS ZIP — PO-box ZIPs return `unknown`; the fallback path (state list + house.gov address link) must be designed, and it is. (4) Cached shells could show a 10-minute-old "latest vote" — acceptable given weekly sync; the as-of stamp is rendered from `sync_metadata`, so the page never claims a freshness it doesn't have.

Deferred to a follow-up: sponsored-bills list; topic chips and `/bills` search polish; Spanish-language strings (the components are text-only and tokenised for it, but no translation is scoped); dark mode and print stylesheets; a Census-geocoder address fallback inside the site (we link out to house.gov instead); analytics to measure the two-click metric (a privacy-respecting server-side count of `/api/zip` hits is the cheapest proxy); cold-start keep-alive.

Appendix C gaps covered or deferred: 404 (covered, (c)); House-member pages (the member template has no Senate-only modules; district and ballot line come from data; short-record members simply show fewer votes); no-donations members (Money section omitted); invalid `?code=` (real 404 page); bills with no roll call (bill page omits the roll-call block and says "No roll-call vote yet — voice votes and committee actions are not recorded as roll calls"); no-JS state (server-rendered blocks + `<noscript>` note where JS adds the ZIP lift); tablet widths (768 breakpoint designed; 320 in the smoke check); broken photos (initials fallback); hero edge cases (hero removed; nomination/no-bill votes use `document` as the headline with no bill link); members.json currency (deferred: a "Roster as of {members.json updateDate}" line in `/methodology`); Spanish speakers (deferred, above); notify/feedback failure states (feedback dialog gets visible error copy; notify form removed); print/dark (deferred).

## (h) Resolving the Appendix C contradictions that touch this design

1. **localStorage for ZIP vs. no persistence for party reveal.** Principle: *remember where you live, never how you look.* Location is a fact about the reader that makes every page answer their question; persisting it serves the task. Party is a lens on the facts, and the product promise is that each visit starts unframed. So ZIP/district/state persist in `localStorage`; the party reveal lives in `sessionStorage` (one explicit action per visit, honoured across the pages of that visit, gone when the tab closes) and never in a server payload.
2. **CDN-cached shells vs. personalised first blocks and Record freshness.** Principle: *the server renders what is true for everyone; the browser adds what is true for you.* Everything server-rendered (headers, rosters, roll calls by state, latest votes, as-of stamps) is identical for all visitors and safe to cache for 10 minutes; the "Your representatives" lift is a client-side rearrangement from localStorage over that same HTML. Freshness is stated by the server-rendered stamp, so a cached page is never more stale than it says.
3. **Hide vs. show campaign finance.** Principle: *show dated facts, hide undated ones.* Money stays, collapsed, below the record, headed with its cycle and as-of date, and is omitted for members without data. It is never in the fold and never a headline number.
4. **"Voted yes 49%" endorsed vs. F06/F08.** Keep the *vocabulary* ("voted yes"), drop the *percentage*. Rows show one linked recent vote instead.
5. **Both-sides arguments: keep the pairing vs. drop the module.** Keep the pairing structure only where a summary exists, but relabel it as AI-drafted and unattributed at the top, in neutral colours, collapsed on mobile. The neutrality proof is the symmetry, not the (false) attribution.
6. **Record "clean stack" vs. 15-line official titles.** The stack stays; official titles are clamped to two lines behind the "Officially:" kicker (home, `/bills`, member rows).
7. **F07's mobile sticky strip vs. F30's "at most one sticky".** One sticky element: the name strip *replaces* the masthead once the header leaves the viewport; nothing else is sticky.
8. **New data files vs. constraint 5.** Only the two sanctioned files are added, each with source and licence in `/methodology`; nothing else is invented.
9. **feedback.js hooks vs. h1 promotion.** Do the sanctioned change only: promote the two h2s to h1 and update the two selectors in the same commit; keep `#feedback-open`, `#feedback-*` ids and `#data-freshness`.
10. **Per-request Pillow on a free worker.** Pre-render member/state/default cards at sync; render bill cards once and cache to disk with immutable headers, so a viral share costs one render.
11. **Key-bills picker "sound" vs. 6-vs-4 asymmetry.** Keep the selection logic; make the counts symmetric (3 and 3 on mobile, up to 4 and 4 on desktop) and print the rule under the heading.
12. **Hidden Latest Vote card vs. layout shift.** Server-render it; if the data is missing the block is absent, not reserved.
13. **404 not assessed.** Designed above as a real page with the ZIP field.
