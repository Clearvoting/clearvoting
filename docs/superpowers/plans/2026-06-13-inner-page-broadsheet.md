# Inner-Page Broadsheet Unification — Implementation Plan

**Goal:** Bring every ClearVoting page (member, bill, state, about) and every flow into the
same "civic broadsheet" design language as the redesigned homepage, so the site feels like
one intentional product end to end.

**Architecture (the key decision):** Promote the shared broadsheet system out of the
`body.home` scope into a single shared stylesheet, `static/css/broadsheet.css`, loaded on
**every** page. `home.css` is renamed/refactored into `broadsheet.css`:
- Token **aliases** (`--navy`, `--ink`, `--paper`, `--blue`, `--yes`, `--no`,
  `--font-display`, `--font-serif`, `--font-ui`, `--rule`…) move to `:root` so every page +
  every global selector can use them.
- Shared **chrome + utilities** (`.masthead`, `.masthead-nav`, `.site-footer`/`.footer-links`/
  `.credo`, `.kicker`, `.meta`, `.arrow-link`, `.section-head`, `.law-seal`, split/tally
  vote bars, double/hairline rules) are **un-scoped** from `.home` → global, so they render
  identically on all pages.
- Homepage-specific **layout** (`.lead`, `.action`, `.state-grid`, `.delegation` rows,
  `.record`, `.browse-panel`) stays scoped under `.home`.
- `styles.css` stays the shared base (tokens, reset, `.btn*`, `.spinner`, `.loading`,
  `.empty-state`, `.feedback-*`, forms, `.data-table`, `.impact-tag`) **and** holds the
  inner-page content classes, which we **restyle** in place to the broadsheet aesthetic.

**Why restyle, not rewrite:** The four inner pages are rendered entirely in JS
(member.js 1021 / bill.js 436 / state.js 444 lines) that already builds DOM with
`createElement`/`textContent` (no `innerHTML` — CSP- and security-hook-safe) and already
shares the palette + fonts. The jarring break is the **navy `.site-header` + gray footer**
plus missing broadsheet motifs (kickers, double rules, navy display headings). So unification
= shared CSS + header/footer markup swap + a focused per-page restyle pass + a few tiny JS
hooks. Rewriting 1,900 lines of working JS is unnecessary risk.

**Tech stack:** Python/FastAPI (serve + SEO meta injection), vanilla HTML/CSS/JS, JSON data.

---

## Hard constraints discovered during the audit (do not violate)

1. **SEO injection** (`app/main.py` `_inject_meta`): replaces the literal `<title>…</title>`
   and strips/injects `<meta name="description">`, then inserts og/canonical before
   `</head>`. **Every page must keep a literal `<title>…</title>` and `</head>`.** Do not
   remove them. Description meta is optional in the static file (injector adds it).
2. **Cache-bust auto-rewrite**: `_serve_html` rewrites every `?v=\d+` to a per-restart
   timestamp. Keep the `?v=N` pattern on asset links; exact numbers don't matter.
3. **CSP** (`script-src 'self'`, no `'unsafe-inline'`): **no inline event handlers.** The old
   `onclick="history.back()"` is a CSP violation — wire back-links via `addEventListener`.
   `img-src 'self' https://www.congress.gov` only. `style-src` allows inline styles
   (the `el()` helpers set `style=` — fine).
4. **No new `innerHTML`** (security hook). bill.js's existing `sanitizeHtml`/
   `insertAdjacentHTML` block for the official summary must be **left untouched**.
5. **JS structural contracts to preserve** (feedback.js reads these):
   `.member-header h2`, `.bill-header h2`, `.state-header h1`, ids `#feedback-*`,
   `#data-freshness`, `#about-feedback-cta`, classes `.animate-in`/`.animate-scale`,
   and the feedback button + modal markup on every page. `.hamburger` lookup is null-guarded
   → broadsheet masthead (no hamburger) is safe.
6. **member.js** queries `document.querySelector('.site-header')` (lines ~174, ~310) to offset
   its sticky name-bar and sticky tab-bar. After the masthead swap, update these to the new
   header (masthead is non-sticky → offset 0 for the sticky bar; tabs offset by sticky-bar
   height on desktop).
7. **No invented data.** Real member fields only: `name`("Last, First" → humanize),
   `directOrderName`, `depiction.imageUrl`, `district`, `terms.item[]`(startYear/endYear),
   `partyName`(only when show_party), `chamber`, `bioguideId`, `state`. **No "serving since",
   locality, or county fields exist** — never show them. Finance = `donations.json`;
   member narrative/top_areas = `member_summaries.json`; bill one_liner/provisions/arguments
   = `ai_summaries.json`.
8. **Party labels hidden by default + reveal toggle** on every page that shows party;
   vote colors always paired with text labels (already true in JS).
9. **Names humanized everywhere** ("Charles E. Schumer", not "Schumer, Charles E.") — all four
   JS files already do this; verify nothing regresses.

## Header/footer markup to apply on every inner page (identical to homepage)

Masthead (replaces `<header class="site-header">…`):
```html
<header class="masthead">
  <a href="/" class="logo" aria-label="ClearVoting home">Clear<span>Voting</span></a>
  <p class="masthead-tagline">Facts only · No opinions · No spin</p>
  <nav class="masthead-nav" aria-label="Main">
    <a href="/">Home</a>
    <a href="/#record">The Record</a>
    <a href="/about">About</a>   <!-- about page: aria-current="page" -->
  </nav>
</header>
```
Footer (replaces the old 3-line `<footer class="site-footer">`):
```html
<footer class="site-footer">
  <nav class="footer-links" aria-label="Footer">
    <a href="/about">About</a>
    <a href="/about">Methodology &amp; Corrections</a>
    <a href="/about">Privacy</a>
  </nav>
  <span class="meta">Data from <a href="https://congress.gov" …>Congress.gov</a> and
    <a href="https://senate.gov" …>Senate.gov</a> · <span id="data-freshness"></span></span>
  <p class="credo">ClearVoting does not express opinions on legislation or representatives.</p>
</footer>
```
Each inner page: add `<link rel="stylesheet" href="/static/css/broadsheet.css?v=1">` after
`styles.css`, set `<body class="broadsheet">`, keep skip-link + feedback button/modal, keep a
restyled `.back-link` on detail pages (wired via JS, not inline onclick).

---

## Phases

### Phase 1 — Shared `broadsheet.css` (foundation)
- Create `static/css/broadsheet.css` from `home.css`: aliases → `:root`; un-scope shared
  chrome/utilities from `.home`; keep homepage layout under `.home`; generalize body base to
  `body.home, body.broadsheet`.
- Delete `home.css`; point `index.html` at `broadsheet.css`.
- **Verify homepage is visually identical** (screenshot before/after desktop+mobile) and
  `pytest` green. This is the regression gate before touching inner pages.

### Phase 2 — Member page (the worst offender)
- member.html: masthead/footer swap, load broadsheet.css, `body class="broadsheet"`.
- member.js: update `.site-header` querySelectors → `.masthead`/offset logic; wire back-link
  listener (CSP-safe).
- styles.css restyle: `.member-header`, `.member-sticky-bar`, `.member-tab-bar`/`.member-tab`,
  `.glance-card`, `.viz-*` containers, `.service-compact`, `.filter-row`/`.filter-select`,
  `.vote-item`, `.impact-tag`, `.copy-link-btn`, `.source-link`, `.back-link` → broadsheet
  (navy display headings, kickers, hairline/double rules, refined spacing).
- Verify flows: delegation→senator, delegation→house rep, all three tabs, pagination,
  filters, At-a-Glance narrative, topic viz, vote→bill link. Desktop + mobile, 0 console errs.

### Phase 3 — Bill page
- bill.html: masthead/footer swap, load broadsheet.css, body class. Back-link wired in bill.js.
- styles.css restyle: `.bill-header`, `.bill-toc`, `.bill-section`/`#ai-summary-section`,
  `.provision-list` (§ markers), `.bill-arguments`/`.arguments-side(support/critics)`,
  `.official-summary`, `.vote-block`, `.vote-pie`/`.vote-summary`/`.data-table`/`.vote-label`,
  `.source-link`. Leave the sanitizeHtml/insertAdjacentHTML block untouched.
- Verify: What This Bill Does, supporter/critic args, official text expand, roll-call votes,
  party reveal, source links, sponsors→member. Desktop + mobile.

### Phase 4 — State page
- state.html: masthead/footer swap, load broadsheet.css, body class.
- styles.css restyle: `.state-header`, `.state-stats`/`.state-stat`, `.party-toggle-bar`,
  `.controls-bar`/`.filter-select`, `.comparison-table`, `.mobile-card*`, split bars.
- Verify reachable at `/state?code=NY`, desktop table + mobile cards, sort/filter, row→member.

### Phase 5 — About page
- about.html: masthead/footer swap, load broadsheet.css, body class. Keep `.animate-in`/
  `.animate-scale` + `#about-feedback-cta`.
- styles.css restyle `.about-*` to broadsheet (kickers, section heads, navy headings, rules).
- Verify content intact + feedback CTA works.

### Phase 6 — Cross-cutting polish & cleanup
- Remove/neutralize dead old-header CSS (`.site-header`/`.header-inner`/`.hamburger`) now
  unused. Audit shared `.btn*` so feedback modal + about CTA look right everywhere.
- Consistency sweep: header nav + footer identical on all pages; party-toggle behavior;
  humanized names; vote labels paired with color; WCAG AA contrast; visible focus; keyboard.
- Mobile ≤480 and desktop pass for every page.

### Phase 7 — Full verification
- `./.venv/bin/python -m pytest -q` → 319 passing.
- Playwright: screenshot every page desktop (1280) + mobile (390), walk all 14 flows from the
  brief, assert **zero console errors** on each.

### Phase 8 — PR
- One PR `redesign/inner-pages` → `main` with before/after notes. **Do not merge.**
