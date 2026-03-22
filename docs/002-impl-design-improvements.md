# ClearVote Design Improvements — Data Visualization, Member Profiles, State Overview

**Version:** 1.1
**Created:** March 22, 2026
**Status:** Reviewed — ready for implementation

---

## Executive Summary

ClearVote's deployed UI is functional but text-heavy and uses a light "government website" aesthetic that doesn't match the project's design system. The PRD identifies data visualization as P0 — busy voters need to grasp patterns in seconds, not read paragraphs. Three approved mockups define the target: an improved home page with inline member card visualizations and a "How It Works" section, a redesigned member profile with donut charts/topic bars/stats dashboard, and a new state overview page with a comparison table.

This plan implements those mockups in four independently deployable phases. No backend changes are needed for Phases 1-2 — the existing API already returns all the data needed (stats, vote counts, categories, narratives). Phase 3 adds one new API endpoint for state-level aggregate stats. Phase 4 refines the home page.

### Scope

**In scope:**
- CSS/SVG data visualization components (participation rings, vote bars, donut charts, topic breakdown bars, attendance bars, ranking bars)
- Member profile redesign with stats dashboard, vote breakdown donut, attendance bar, topic support/opposition bars, key bills sections
- New state overview page (`/state`) with comparison table, aggregate stats, filter/sort controls, mobile card layout
- Home page improvements: "How It Works" section, enhanced member cards with participation rings and vote bars, improved hero
- Lora font addition to complete the three-font typography system

**Out of scope:**
- Dark theme migration (midnight blue + gold) — significant enough to warrant its own plan. The mockups were built with the current light palette. The design system color shift is a separate workstream.
- SEO meta tags — tracked separately in PRD as P0
- Automated data sync — separate infrastructure work
- House vote visualization on bill detail pages — separate scope

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Pure CSS + inline SVG for all charts, no JS charting libraries** | Maintains zero-dependency philosophy. SVG circles with `stroke-dasharray`/`stroke-dashoffset` for donuts and rings. CSS flexbox for bar charts. Keeps bundle size at zero. |
| **Frontend-only visualization — no new data aggregation in sync pipeline** | The existing `/api/members/{id}/summary` and `/api/members/{id}/votes` endpoints already return `stats` (yea_count, nay_count, participation_rate, total_votes) and `top_policy_areas` (with in_favor/against/neutral counts). All chart data can be computed from existing API responses. |
| **One new API endpoint for state overview, not a new sync step** | `/api/members/{state}/overview` computes aggregate stats (avg participation, avg support rate, member count, total votes) at request time from in-memory data. 80 members across 4 states means this computation is trivial — no caching needed. |
| **State overview as a new HTML page, not a section on the home page** | The comparison table with 28 rows (for NY) would overwhelm the home page. A dedicated `/state` route gives it room to breathe and creates a natural navigation flow: Home -> State Overview -> Member Profile. |
| **Add Lora font for body text** | The design system specifies three fonts (Playfair Display for headings, Lora for body/narratives, Inter for UI). Currently Lora is missing — only Inter and Playfair are loaded. Adding it completes the typography system. |
| **Extend member summary endpoint rather than creating a new one** | The home page member cards need participation rate and vote counts. Rather than adding N+1 API calls per card, extend the existing `/api/members/{state}` response with pre-computed stats from member_votes data, loaded at startup. |

### References

- [PRD](001-prd-clearvote.md) — Design Specs section (line 362+)
- [Mockups](../mockups/) — `home.html`, `member.html`, `state-overview.html`

---

## Architecture Overview

```
Current flow:
  Home page -> select state -> member cards (name/chamber only) -> member profile (text-heavy)

New flow:
  Home page (How It Works + enhanced cards with viz) -> select state
    -> member cards (participation ring, vote bar, narrative snippet)
    -> "View All Representatives" link -> State Overview (comparison table)
    -> click member -> Member Profile (stats dashboard, donut, topic bars, attendance)
```

Data flow for visualizations:
```
Existing API endpoints (no changes for Phase 1-2):
  /api/members/{state}           -> member list with stats (extended)
  /api/members/{id}/summary      -> stats + top_policy_areas + narrative
  /api/members/{id}/votes?limit=2000 -> all votes with categories

New API endpoint (Phase 3):
  /api/members/{state}/overview  -> aggregate stats + per-member summary data
```

---

## Phase 1: Data Visualization CSS Components + Typography

**Goal:** Establish reusable CSS/SVG visualization primitives and complete the typography system. No page-level changes yet — just the building blocks.

**Completion gate:** All visualization CSS classes exist in styles.css, Lora font is loaded, and the existing pages still render correctly with no visual regressions.

### 1.1 Add Lora font import

**File:** `static/index.html`, `static/member.html`, `static/bill.html`, `static/about.html`

Add `Lora:wght@400;500;600` to the existing Google Fonts import URL in each HTML file's `<link>` tag. Update the CSS `--font-body` variable usage: Lora for narrative/body text, Inter stays as the UI font.

**File:** `static/css/styles.css`

Add a new CSS custom property:
```css
--font-narrative: 'Lora', Georgia, serif;
```

Apply `font-family: var(--font-narrative)` to narrative text elements: `.summary-narrative`, `.voting-summary-card p`, hero text, and any long-form body text. Keep Inter as the default body font for UI elements (labels, stats, buttons, metadata).

### 1.2 Participation ring SVG component styles

**File:** `static/css/styles.css`

Add CSS for the SVG participation ring (used on member cards in Phase 4 and state overview in Phase 3):

```css
/* Participation Ring — SVG circle with stroke-dashoffset */
.participation-ring { width: 40px; height: 40px; flex-shrink: 0; }
.participation-ring circle { fill: none; stroke-width: 3; }
.ring-bg { stroke: var(--border-light); }
.ring-fill { stroke: var(--accent); stroke-linecap: round; transition: stroke-dashoffset 1s ease; }
.ring-text { font-family: var(--font-body); font-size: 8px; font-weight: 600; fill: var(--text-primary); text-anchor: middle; dominant-baseline: central; }
```

### 1.3 Vote split bar styles

**File:** `static/css/styles.css`

Add CSS for yea/nay split bars (used on member cards and state overview):

```css
/* Vote Split Bars — flexbox proportional bar */
.vote-bar-mini { display: flex; height: 6px; border-radius: 3px; overflow: hidden; flex: 1; min-width: 80px; }
.bar-yea { background: var(--vote-yea); transition: width 0.6s ease; }
.bar-nay { background: var(--vote-nay); transition: width 0.6s ease; }
.bar-missed { background: var(--vote-absent); transition: width 0.6s ease; }
```

### 1.4 Donut chart styles

**File:** `static/css/styles.css`

Add CSS for the member profile vote breakdown donut chart:

```css
/* Donut Chart — SVG stroke-dasharray */
.donut-row { display: flex; align-items: center; gap: 2.5rem; flex-wrap: wrap; }
.donut-chart { flex-shrink: 0; }
.donut-chart text { font-family: var(--font-body); fill: var(--text-primary); }
.donut-legend { display: flex; flex-direction: column; gap: 0.6rem; }
.legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-value { font-weight: 600; color: var(--text-primary); margin-left: auto; padding-left: 1rem; }
```

### 1.5 Topic breakdown dual-bar styles

**File:** `static/css/styles.css`

Add CSS for the topic support/opposition horizontal bars on member profiles:

```css
/* Topic Breakdown Bars — supported vs opposed */
.topic-bars { margin-top: 1rem; }
.topic-row { display: grid; grid-template-columns: 120px 1fr; align-items: center; gap: 0.5rem; padding: 0.6rem 0; border-bottom: 1px solid var(--border-light); }
.topic-row:last-child { border-bottom: none; }
.topic-name { font-size: 0.875rem; color: var(--text-primary); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.topic-dual-bar { display: flex; gap: 2px; height: 26px; align-items: center; }
.topic-supported-bar { background: var(--vote-yea); height: 100%; border-radius: 3px 0 0 3px; display: flex; align-items: center; justify-content: center; min-width: 24px; transition: width 0.6s ease; }
.topic-opposed-bar { background: var(--vote-nay); height: 100%; border-radius: 0 3px 3px 0; display: flex; align-items: center; justify-content: center; min-width: 24px; transition: width 0.6s ease; }
.bar-label { font-size: 0.7rem; font-weight: 600; color: #fff; line-height: 1; }
.topic-summary { grid-column: 2; font-size: 0.75rem; color: var(--text-dim); margin-top: -0.2rem; }
```

### 1.6 Stats dashboard card styles

**File:** `static/css/styles.css`

Add CSS for the stats dashboard cards used on member profiles:

```css
/* Stats Dashboard */
.stats-dashboard { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 1rem 1.5rem; text-align: center; }
.stat-card .stat-label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
.stat-card .stat-number { font-family: var(--font-heading); font-size: 1.5rem; font-weight: 700; color: var(--accent); line-height: 1.2; }
.stat-card .stat-detail { font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.2rem; }
```

### 1.7 Attendance bar styles

**File:** `static/css/styles.css`

```css
/* Attendance Progress Bar */
.attendance-bar-container { margin: 1rem 0; }
.attendance-label-row { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.3rem; }
.attendance-label { font-size: 0.875rem; color: var(--text-secondary); }
.attendance-pct { font-family: var(--font-heading); font-size: 1.5rem; font-weight: 700; color: var(--accent); }
.attendance-bar { height: 12px; background: var(--bg-primary); border-radius: 6px; overflow: hidden; }
.attendance-fill { height: 100%; background: linear-gradient(90deg, var(--accent-dim), var(--accent)); border-radius: 6px; transition: width 0.8s ease; }
.attendance-context { font-size: 0.75rem; color: var(--text-dim); margin-top: 0.3rem; }
```

### 1.8 Key bills section styles

**File:** `static/css/styles.css`

```css
/* Key Bills (Supported / Opposed) */
.key-bills-section { margin-top: 1rem; }
.key-bills-heading { font-family: var(--font-body); font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem; padding-left: 0.75rem; border-left: 3px solid; }
.supported-heading { color: var(--vote-yea); border-left-color: var(--vote-yea); }
.opposed-heading { color: var(--vote-nay); border-left-color: var(--vote-nay); }
.key-bills-list { list-style: none; padding: 0; margin: 0 0 1rem 0; }
.key-bills-list li { font-size: 0.875rem; color: var(--text-secondary); padding: 0.35rem 0 0.35rem 0.75rem; border-left: 3px solid var(--border-light); line-height: 1.5; }
.supported-heading + .key-bills-list li { border-left-color: rgba(46, 133, 64, 0.2); }
.opposed-heading + .key-bills-list li { border-left-color: rgba(205, 32, 38, 0.2); }
```

### 1.9 Visualization section container styles

**File:** `static/css/styles.css`

```css
/* Visualization Section Container */
.viz-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }
.viz-section h3 { font-family: var(--font-heading); font-size: 1.25rem; color: var(--text-primary); margin-bottom: 1rem; }
```

### 1.10 Responsive breakpoints for new components

**File:** `static/css/styles.css`

Add responsive rules for the new visualization components:

```css
@media (max-width: 768px) {
    .stats-dashboard { grid-template-columns: 1fr; }
    .donut-row { flex-direction: column; align-items: flex-start; }
    .topic-row { grid-template-columns: 100px 1fr; }
}
@media (max-width: 480px) {
    .topic-row { grid-template-columns: 80px 1fr; }
    .topic-name { font-size: 0.75rem; }
}
```

### 1.11 Add new design token CSS variables

**File:** `static/css/styles.css`

Add spacing and typography size tokens to `:root` that the mockups use:

```css
--text-xs: 0.75rem;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
--text-3xl: 2rem;
--space-xs: 0.5rem;
--space-sm: 1rem;
--space-md: 1.5rem;
--space-lg: 2.5rem;
--space-xl: 4rem;
--nav-height: 60px;
--font-narrative: 'Lora', Georgia, serif;
```

**Tests:**
- Visual regression: open each page in the browser and confirm nothing is broken
- The new CSS classes should not affect existing layouts since they are new class names not yet used in HTML

---

## Phase 2: Member Profile Redesign

**Goal:** Replace the text-heavy member profile with the mockup design: stats dashboard, vote breakdown donut chart, attendance bar, topic support/opposition bars, and key bills sections. All data comes from existing API endpoints — no backend changes.

**Completion gate:** Member profile page matches the mockup layout. Stats dashboard shows 3 cards (total votes, participation, support rate). Vote breakdown renders as an SVG donut. Topic bars show supported vs. opposed for each policy area. Key bills sections list top supported and opposed bills. All data is real (from API), not hardcoded.

### 2.1 Create visualization helper module

**File:** `static/js/viz.js` (new file)

Create a small JS file that attaches visualization factory functions to `window.ClearVoteViz` (following the same global-scope pattern as the existing `vote.js` which uses `window.ClearVotingUI`). These are NOT ES modules — the existing codebase does not use `type="module"` script tags.

Functions to implement:
- `createParticipationRing(percentage, size)` — returns SVG element with circle + text
- `createVoteSplitBar(yeaPct, nayPct, missedPct)` — returns div with proportional colored segments
- `createDonutChart(segments, total, size)` — returns SVG donut with legend (replaces existing vote.js pie chart for member profile context)
- `createTopicBar(supported, opposed, label)` — returns the dual horizontal bar row
- `createAttendanceBar(percentage, attended, total, congressLabel)` — returns the full attendance section
- `createStatCard(label, number, detail)` — returns a stat-card div

Each function creates and returns DOM elements using the CSS classes from Phase 1. No side effects, no DOM queries — pure element factories. Exposed as `window.ClearVoteViz.createParticipationRing(...)` etc.

### 2.2 Redesign the At a Glance section

**File:** `static/js/member.js` — `renderVotingSummary()` function (around line 474)

Rewrite `renderVotingSummary()` to produce the mockup layout:

1. **At a Glance card** (`.glance-card`) containing:
   - AI narrative paragraph (already exists, keep it)
   - AI attribution line (already exists, keep it)
   - **Stats dashboard** — 3 stat cards:
     - "Total Votes" — `stats.total_votes` with congress range detail
     - "Participation" — `stats.participation_rate`% with "of all floor votes" detail
     - "Support Rate" — computed `yea_count / (yea_count + nay_count) * 100`% with "voted yea" detail
   - **Key Bills Supported** — reuse existing `uniqueYea` logic but render as `.key-bills-list` with `.supported-heading`
   - **Key Bills Opposed** — reuse existing `uniqueNay` logic but render as `.key-bills-list` with `.opposed-heading`

### 2.3 Add vote breakdown donut chart section

**File:** `static/js/member.js` — `renderVotingStats()` function (around line 571)

After the current stats bar, add a new `.viz-section` containing:

1. Heading: "Vote Breakdown"
2. SVG donut chart (using `viz.js` helper) showing:
   - Yea segment: `stats.yea_count`
   - Nay segment: `stats.nay_count`
   - Not Voting segment: `stats.not_voting_count`
3. Legend with counts and percentages

This replaces the existing inline pie charts in the stats bar. Remove the current `renderVotePieChart` calls from the stats bar and replace with the donut section below the At a Glance card.

### 2.4 Add attendance visualization section

**File:** `static/js/member.js` — `renderVotingStats()` function

Add a new `.viz-section` below the donut chart containing:

1. Heading: "Attendance"
2. Attendance progress bar with percentage label
3. Context line: "Attended X of Y eligible floor votes (Nth-Nth Congress)"

Data: `stats.participation_rate`, `stats.total_votes`, congress range from `congresses` array.

### 2.5 Add topic support/opposition breakdown section

**File:** `static/js/member.js`

Add a new `.viz-section` below the attendance section containing:

1. Heading: "What They Fight For by Topic"
2. Explanatory subtext: "Each row shows how many bills this representative supported vs. opposed in that topic area."
3. For each item in `summaryData.top_policy_areas` (already returned by `/api/members/{id}/summary`):
   - Topic name label
   - Dual bar: supported width = `in_favor / (in_favor + against)`, opposed width = `against / (in_favor + against)`
   - Summary text: "X supported, Y opposed"

Data source: The existing `get_member_vote_summary()` in `data_service.py` already computes `top_policy_areas` with `in_favor`, `against`, `neutral`, `yea`, `nay`, and `total` counts per area. No backend changes needed.

### 2.6 Restructure the member page layout

**File:** `static/js/member.js` — `renderMember()` function

Reorder the rendered sections to match the mockup flow:

1. Member header (photo, name, meta, party toggle) — keep as is
2. Copy link button — keep as is
3. **At a Glance card** (narrative + stats dashboard + key bills) — moved from voting-summary
4. **Vote Breakdown donut** — new viz section
5. **Attendance bar** — new viz section
6. **Topic breakdown bars** — new viz section
7. **Tab bar** (Voting Record / Sponsored Bills / Campaign Finance) — keep as is
8. **Vote filters** (vote type + category dropdowns) — keep as is, moved inside Voting Record tab
9. **Vote list** — keep as is

### 2.7 Add vote filters with mockup styling

**File:** `static/js/member.js` — `renderVotingStats()` function

Restyle the existing filter dropdowns to match the mockup's `.filter-row` layout with the custom select arrow:

```css
.filter-row { display: flex; gap: 1rem; margin-bottom: 1rem; }
.filter-wrap { position: relative; display: inline-block; }
.filter-select { appearance: none; -webkit-appearance: none; ... }
.filter-arrow { position: absolute; right: 0.6rem; top: 50%; transform: translateY(-50%); ... }
```

The filter controls already exist and work — this is a CSS restyling, not a logic change.

### 2.8 Include viz.js on member page

**File:** `static/member.html`

Add `<script src="/static/js/viz.js?v=1"></script>` before `member.js` in the HTML.

### 2.9 Update CSP for Lora font

**File:** `app/main.py`

The CSP already allows `fonts.googleapis.com` and `fonts.gstatic.com`, so Lora will load without CSP changes. No action needed — including this note for completeness.

**Tests:**

| Type | Scope | Validates |
|------|-------|-----------|
| Manual | Member profile page | Stats dashboard renders 3 cards with correct numbers from API |
| Manual | Member profile page | Donut chart segments are proportional to yea/nay/not-voting counts |
| Manual | Member profile page | Topic bars show correct supported vs. opposed from summary API |
| Manual | Member profile page | Attendance bar shows correct participation rate |
| Manual | Member profile page | Key bills sections show real bill one-liners, not hardcoded text |
| Manual | Member profile page (mobile) | Stats dashboard stacks to single column, donut stacks vertically |
| Unit | `test_routers.py` | Existing member endpoint tests still pass (no API changes) |

---

## Phase 3: State Overview Page

**Goal:** Create a new `/state` page with a comparison table showing all representatives for a state side by side, with inline participation bars and vote-split bars, aggregate state stats, filter/sort controls, and a mobile card layout.

**Completion gate:** Navigating to `/state?code=NY` shows the state overview with comparison table populated from real data. Table rows link to member profiles. Filter by chamber and sort by name/participation/support rate work. Mobile view shows cards instead of the table.

### 3.1 Add state overview API endpoint

**File:** `app/routers/members.py`

Add a new endpoint that returns per-member stats alongside the member list.

**Route ordering note:** This route MUST be declared BEFORE the existing `/{state_code}/{district}` route in the file. Although FastAPI's type coercion means `overview` won't match `district: int`, explicit ordering prevents any ambiguity. Place this endpoint above `get_members_by_district`.

**Performance note:** This endpoint calls `get_member_votes()` per member, which reads per-member JSON files from disk. For a state with ~55 members (California), this is ~55 file reads per request. Since these files are small (~10-50KB each) and on local disk, this is acceptably fast (<100ms total). If this ever becomes a concern, the member_votes data could be pre-loaded into memory at startup — but that optimization is not needed now.

```python
@router.get("/{state_code}/overview")
async def get_state_overview(state_code: str):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    members_data = data_service.get_members_by_state(state_code)
    members = members_data.get("members", [])

    enriched = []
    total_participation = 0
    total_support = 0
    total_votes_all = 0
    count_with_stats = 0

    for m in members:
        bio_id = m.get("bioguideId", "")
        votes_data = data_service.get_member_votes(bio_id)
        stats = votes_data.get("stats", {}) if votes_data else {}
        narrative_data = data_service.get_member_narrative(bio_id)
        narrative_snippet = ""
        if narrative_data:
            full = narrative_data.get("narrative", "")
            narrative_snippet = full[:150] + "..." if len(full) > 150 else full

        participation = stats.get("participation_rate", 0)
        yea = stats.get("yea_count", 0)
        nay = stats.get("nay_count", 0)
        total_v = stats.get("total_votes", 0)
        support_rate = round(yea / (yea + nay) * 100) if (yea + nay) > 0 else 0

        enriched.append({
            **m,
            "participation_rate": participation,
            "support_rate": support_rate,
            "total_votes": total_v,
            "yea_count": yea,
            "nay_count": nay,
            "narrative_snippet": narrative_snippet,
        })

        if total_v > 0:
            total_participation += participation
            total_support += support_rate
            total_votes_all += total_v
            count_with_stats += 1

    avg_participation = round(total_participation / count_with_stats) if count_with_stats else 0
    avg_support = round(total_support / count_with_stats) if count_with_stats else 0

    return _strip_party({
        "members": enriched,
        "aggregate": {
            "total_members": len(members),
            "avg_participation": avg_participation,
            "avg_support_rate": avg_support,
            "total_votes": total_votes_all,
        },
    })
```

This endpoint reuses existing `DataService` methods. The computation is O(N) where N = members in a state (max ~55 for California) — negligible. Data is already in memory.

### 3.2 Create state overview HTML page

**File:** `static/state.html` (new file)

Create the HTML shell matching the structure of existing pages (member.html pattern):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Same head pattern as member.html: meta, fonts (including Lora from Phase 1), stylesheet, favicon -->
    <title>State Representatives — ClearVoting</title>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <header class="site-header"><!-- Same header as other pages --></header>
    <main id="main-content">
        <button class="back-link" onclick="history.back()">&larr; Change state</button>
        <div id="state-content">
            <div class="loading"><span class="spinner"></span> Loading state data...</div>
        </div>
    </main>
    <footer class="site-footer"><!-- Same footer as other pages --></footer>
    <!-- Feedback button and modal (same as other pages) -->
    <script src="/static/js/viz.js?v=1"></script>
    <script src="/static/js/state.js?v=1"></script>
    <script src="/static/js/feedback.js?v=5"></script>
</body>
</html>
```

### 3.3 Create state overview JavaScript module

**File:** `static/js/state.js` (new file)

Implements the state overview page logic:

1. **Init:** Read `?code=XX` from URL. If missing, show error with link to home page. Fetch `/api/members/{code}/overview`.

2. **State header:** Render state name (map code to full name), subtitle ("Congressional delegation — X Senators, Y House Representatives").

3. **Aggregate stats:** 4 stat cards in a grid: Representatives count, Avg Participation %, Avg Support Rate %, Total Votes Cast.

4. **Party toggle:** Same pattern as home page — reuse the `cv-show-party` localStorage key.

5. **Filter/sort controls:**
   - Chamber filter: All / Senate / House
   - Sort by: Name (A-Z), Participation (High to Low), Support Rate (High to Low), District

6. **Comparison table (desktop):** Render `<table>` with columns: Representative (photo + name), Chamber, District, Participation (mini bar + percentage), Vote Split (yea/nay bar), Total Votes. Each row is clickable and navigates to `/member?id={bioguideId}`.

7. **Member cards (mobile):** Same data as table but rendered as cards with photo, name, chamber, stats grid, and vote bar. Hidden on desktop, shown on mobile via CSS media query.

8. **Client-side filter/sort:** Filter by chamber and sort by selected criteria. Re-render the table/cards on change. No API calls — all done on the already-fetched data.

### 3.4 Add state overview CSS styles

**File:** `static/css/styles.css`

Add state-specific styles:

```css
/* State Overview */
.state-header { margin-bottom: 1.5rem; }
.state-header h1 { font-family: var(--font-heading); font-size: 2rem; color: var(--text-primary); }
.state-header .subtitle { font-size: 1rem; color: var(--text-secondary); }

.state-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2.5rem; }
.state-stat { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1rem 1.5rem; text-align: center; box-shadow: var(--shadow); }
.state-stat .label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; }
.state-stat .number { font-family: var(--font-heading); font-size: 1.5rem; font-weight: 700; color: var(--accent); }

/* Comparison Table */
.comparison-table { width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow); margin-bottom: 2.5rem; }
.comparison-table thead th { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; padding: 1rem; text-align: left; border-bottom: 2px solid var(--border); cursor: pointer; white-space: nowrap; }
.comparison-table thead th:hover { color: var(--accent); }
.comparison-table thead th.sorted { color: var(--accent); }
.comparison-table tbody tr { border-bottom: 1px solid var(--border-light); cursor: pointer; transition: background var(--transition); }
.comparison-table tbody tr:hover { background: var(--bg-card-hover); }
.comparison-table td { padding: 0.5rem 1rem; font-size: 0.875rem; vertical-align: middle; }

.member-cell { display: flex; align-items: center; gap: 0.5rem; }
.table-photo { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 2px solid var(--border); flex-shrink: 0; }
.table-photo-placeholder { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-card-hover); border: 2px solid var(--border); display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 0.7rem; flex-shrink: 0; }
.table-name { font-weight: 600; color: var(--text-primary); }
.table-name:hover { color: var(--accent); }
.table-chamber { font-size: 0.75rem; color: var(--text-dim); }

/* Mini bars for table cells */
.mini-bar-container { display: flex; align-items: center; gap: 0.5rem; }
.mini-bar-track { width: 60px; height: 6px; background: var(--bg-primary); border-radius: 3px; overflow: hidden; }
.mini-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.mini-bar-fill.high { background: var(--vote-yea); }
.mini-bar-fill.medium { background: #E8A820; }
.mini-bar-fill.low { background: var(--vote-nay); }
.mini-pct { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); min-width: 35px; }

.vote-split-bar { display: flex; height: 6px; width: 80px; border-radius: 3px; overflow: hidden; }
.split-yea { background: var(--vote-yea); }
.split-nay { background: var(--vote-nay); }
.split-text { font-size: 0.75rem; color: var(--text-dim); margin-top: 2px; }

/* Filter/sort controls */
.controls-bar { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; }
.controls-bar label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; }

/* Mobile cards (hidden on desktop) */
.member-cards-mobile { display: none; }
.mobile-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1rem; cursor: pointer; transition: all var(--transition); box-shadow: var(--shadow); }
.mobile-card:hover { border-color: var(--accent-dim); background: var(--bg-card-hover); }
.mobile-card-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; }
.mobile-card-photo { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid var(--border); flex-shrink: 0; }
.mobile-card-name { font-size: 1.125rem; font-weight: 600; color: var(--text-primary); }
.mobile-card-meta { font-size: 0.875rem; color: var(--text-secondary); }
.mobile-card-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 0.5rem; }
.mobile-stat { font-size: 0.875rem; color: var(--text-secondary); }
.mobile-stat strong { color: var(--text-primary); }
.mobile-vote-bar { display: flex; height: 6px; border-radius: 3px; overflow: hidden; margin-top: 0.5rem; }

@media (max-width: 768px) {
    .state-stats { grid-template-columns: repeat(2, 1fr); }
    .state-header h1 { font-size: 1.5rem; }
    .comparison-table { display: none; }
    .member-cards-mobile { display: block; }
    .controls-bar { flex-direction: column; align-items: stretch; }
}
```

### 3.5 Add route for state overview page

**File:** `app/main.py`

Add the HTML route:

```python
@app.get("/state")
async def serve_state():
    return _serve_html("state.html")
```

### 3.6 Add navigation link to state overview from home page

**File:** `static/js/app.js` — `renderMembers()` function

After rendering the member cards on the home page, add a "View All Representatives" link that navigates to `/state?code={stateCode}`. This creates the bridge between the simple member card view and the full comparison table.

### 3.7 Add "State Overview" to navigation

**File:** All HTML files (`index.html`, `member.html`, `bill.html`, `about.html`, `state.html`)

The navigation currently has Home, Browse Bills, About. No change needed — the state overview is accessed via the home page results, not the top nav. This keeps the nav clean. (The mockup shows the same nav structure.)

**Tests:**

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_routers.py` | New `/api/members/{state}/overview` endpoint returns correct structure |
| Unit | `test_routers.py` | Overview endpoint respects party stripping (no partyName in response) |
| Unit | `test_routers.py` | Overview endpoint returns 400 for invalid state code |
| Unit | `test_data_service.py` | Aggregate stats compute correctly for test data |
| Manual | `/state?code=NY` | Comparison table renders with real data for all NY members |
| Manual | `/state?code=NY` | Filter by Senate shows only 2 rows, House shows remaining |
| Manual | `/state?code=NY` | Sort by participation descending works correctly |
| Manual | `/state?code=NY` (mobile) | Table is hidden, cards are shown with correct data |
| Manual | `/state?code=NY` | Clicking a row navigates to `/member?id={bioguideId}` |

---

## Phase 4: Home Page Improvements

**Goal:** Improve the home page landing experience with a better hero section, "How It Works" educational section, and enhanced member cards showing participation rings, vote bars, and narrative snippets.

**Completion gate:** Home page matches the mockup with "How It Works" section visible, member cards show inline visualizations (participation ring, yea/nay bar, narrative snippet), and the hero has the improved copy.

### 4.1 Improve hero section

**File:** `static/index.html`

Update the hero section markup to match the mockup:

```html
<section class="hero">
    <h1>See how your representatives vote.</h1>
    <p class="tagline">Plain language. No spin. No party labels until you ask.</p>
    <p class="trust-line">Data from Congress.gov and Senate.gov</p>
</section>
```

Changes:
- `<h2>` becomes `<h1>` (semantically correct — this is the page's primary heading)
- Subtitle changes from "Facts only. No opinions. No spin." to "Plain language. No spin. No party labels until you ask." (more descriptive of the differentiator)
- Add trust line below

**File:** `static/css/styles.css`

Add `.tagline` and `.trust-line` styles. Update `.hero h1` styles (currently `.hero h2`):

```css
.hero .tagline { font-size: 1.125rem; color: var(--text-secondary); margin-bottom: 2.5rem; }
.hero .trust-line { font-size: 0.75rem; color: var(--text-dim); letter-spacing: 0.1em; text-transform: uppercase; margin-top: 1rem; }
```

### 4.2 Add "How It Works" section

**File:** `static/index.html`

Add the "How It Works" section between the lookup card and the results section:

```html
<section class="how-it-works">
    <h2>How It Works</h2>
    <div class="steps-grid">
        <div class="step">
            <div class="step-number">1</div>
            <h3>Pick your state</h3>
            <p>Select your state and optionally your district to find who represents you in Congress.</p>
        </div>
        <div class="step">
            <div class="step-number">2</div>
            <h3>See the record</h3>
            <p>View their actual voting history, issue positions, and campaign donors — all in plain English.</p>
        </div>
        <div class="step">
            <div class="step-number">3</div>
            <h3>Form your own opinion</h3>
            <p>Party labels hidden by default. Evaluate your representative on what they did, not their team.</p>
        </div>
    </div>
</section>
```

**File:** `static/css/styles.css`

Add "How It Works" styles:

```css
.how-it-works { max-width: var(--max-width); margin: 0 auto; padding: 2.5rem 1.5rem; border-top: 1px solid var(--border-light); }
.how-it-works h2 { font-family: var(--font-heading); font-size: 1.5rem; color: var(--text-primary); text-align: center; margin-bottom: 2.5rem; }
.steps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.step { text-align: center; padding: 1.5rem; }
.step-number { font-family: var(--font-heading); font-size: 2rem; color: var(--accent); line-height: 1; margin-bottom: 0.5rem; }
.step h3 { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
.step p { font-size: 0.875rem; color: var(--text-secondary); }

@media (max-width: 768px) {
    .steps-grid { grid-template-columns: 1fr; gap: 1rem; }
}
```

### 4.3 Enhance member cards with visualizations

**File:** `static/js/app.js` — `renderMembers()` function

Redesign each member card to include:

1. **Card header** — photo + name + chamber/state meta (keep existing)
2. **Stats row** — participation ring SVG + yea/nay split bar (new, using `viz.js` helpers)
3. **Narrative snippet** — 2-line truncated AI narrative (new, fetched from summary cache or lazy-loaded)
4. **"View Full Profile" link** (keep existing click-to-navigate behavior)

The member cards currently just show name/chamber/state. The enhanced cards need per-member stats. Two options for getting stats without N+1 API calls:

**Option A (chosen): Pre-fetch stats in the member list response.**

Extend the `/api/members/{state}` endpoint in `members.py` to optionally include basic stats. Add a query parameter `?include_stats=true`. When true, the endpoint enriches each member with data from `get_member_votes()`:

```python
@router.get("/{state_code}")
async def get_members_by_state(state_code: str, include_stats: bool = False):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_state(state_code)
    if include_stats:
        for m in data.get("members", []):
            bio_id = m.get("bioguideId", "")
            votes_data = data_service.get_member_votes(bio_id)
            if votes_data:
                m["stats"] = votes_data.get("stats", {})
            narrative = data_service.get_member_narrative(bio_id)
            if narrative:
                full = narrative.get("narrative", "")
                m["narrative_snippet"] = full[:150] + "..." if len(full) > 150 else full
    return _strip_party(data)
```

This approach: one API call per state lookup (already made), enriched with stats data that's already in memory. No extra round trips.

### 4.4 Include viz.js on home page

**File:** `static/index.html`

Add `<script src="/static/js/viz.js?v=1"></script>` before `app.js`.

### 4.5 Update app.js to use viz.js helpers

**File:** `static/js/app.js` — `renderMembers()` function

Update the card rendering to use `createParticipationRing()` and `createVoteSplitBar()` from `viz.js`. Show narrative snippet below the stats row. Update the `lookupMembers()` function to pass `include_stats=true` in the API call.

### 4.6 Add "View State Overview" link to results section

**File:** `static/js/app.js`

After the member grid renders, add a link: "View all representatives for {State} in detail" that navigates to `/state?code={stateCode}`. Placed below the member grid, above the browse bills section.

**Tests:**

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_routers.py` | `/api/members/{state}?include_stats=true` returns stats and narrative_snippet per member |
| Unit | `test_routers.py` | `/api/members/{state}` without include_stats still works (backward compatible) |
| Manual | Home page | "How It Works" section renders between lookup and results |
| Manual | Home page | Member cards show participation rings and vote bars with real data |
| Manual | Home page | Narrative snippets appear and are truncated at ~150 chars |
| Manual | Home page (mobile) | Steps grid collapses to single column, cards stack properly |
| Manual | Home page | "View State Overview" link appears and navigates correctly |

---

## Files Touched

| File | Change |
|------|--------|
| `static/css/styles.css` | Add all visualization CSS, design tokens, responsive rules, How It Works styles, state overview styles |
| `static/index.html` | Updated hero, add How It Works section, add viz.js script, add Lora font |
| `static/member.html` | Add viz.js script, add Lora font |
| `static/bill.html` | Add Lora font |
| `static/about.html` | Add Lora font |
| `static/state.html` | **New file** — state overview HTML shell |
| `static/js/viz.js` | **New file** — shared visualization helper functions |
| `static/js/state.js` | **New file** — state overview page logic |
| `static/js/member.js` | Redesign At a Glance, add donut/attendance/topic viz sections |
| `static/js/app.js` | Enhanced member cards, include_stats API call, state overview link |
| `app/main.py` | Add `/state` route |
| `app/routers/members.py` | Add `/overview` endpoint, extend state endpoint with `include_stats` |

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_routers.py` | New state overview endpoint structure and validation |
| Unit | `test_routers.py` | Extended state endpoint with include_stats parameter |
| Unit | `test_routers.py` | Party stripping works on enriched data |
| Unit | `test_data_service.py` | Member vote summary computes in_favor/against correctly |
| Manual | All pages | Lora font loads, narrative text uses it |
| Manual | Member profile | All visualization sections render with real data |
| Manual | State overview | Comparison table, filtering, sorting, mobile cards |
| Manual | Home page | Enhanced member cards, How It Works, hero |
| Manual | All pages (mobile) | Responsive layouts match mockup breakpoints |

---

## Not In Scope

- **Dark theme migration** — The PRD design audit mentions the midnight blue + gold palette, but applying that to the full site is a significant undertaking (rewriting every color value in 2,900 lines of CSS). The mockups were built with the existing light palette plus some new tokens. Dark theme is a separate plan.
- **House vote visualization** — Listed as P1 in the PRD. The bill detail page needs its own plan for rendering House vote data (which is already synced).
- **SEO meta tags** — Listed as P0 in the PRD. Dynamic meta tags for member/bill pages need server-side rendering changes and is a separate workstream.
- **Automated data sync** — Infrastructure work, not related to frontend visualization.
- **Participation ranking visualization** — The state overview mockup shows an "aggregate" participation ranking section. Deferred to a follow-up since the comparison table already provides this data in sortable form.

---

## Estimated Timeline

| Phase | Description | Time |
|-------|-------------|------|
| 1 | CSS visualization components + typography | 1-2 hours |
| 2 | Member profile redesign | 3-4 hours |
| 3 | State overview page | 3-4 hours |
| 4 | Home page improvements | 2-3 hours |
| **Total** | | **9-13 hours** |

---

## Provenance

This plan implements the P0 "Data Visualization / Graphs" item from the ClearVote PRD (v1.2, section "Prioritized Opportunities"). The specific designs come from three approved HTML/CSS mockups created on March 22, 2026, documented in the PRD's "Design Specs" section (v1.3). The mockups were reviewed and approved by Joseph before this plan was written.

---

## Revision History

### v1.1 (March 22, 2026) — Staff Engineer Review

Self-review as Staff Engineer. Issues found and resolved:

**P0 items resolved:**
- **viz.js module pattern:** Changed from ES module to global-scope pattern (`window.ClearVoteViz`) to match existing codebase convention (vote.js uses `window.ClearVotingUI`). The codebase does not use `type="module"` script tags.
- **Route ordering for `/overview` endpoint:** Added explicit note that the `/{state_code}/overview` route MUST be declared before `/{state_code}/{district}` in `members.py` to prevent routing ambiguity.

**P1 items resolved:**
- **Performance note for state overview endpoint:** Documented that the overview endpoint makes ~N file reads (one per member in the state) per request. Acceptable at current scale (~55 members max) but flagged for awareness.
- **Lora font on state.html:** Added note that the new state.html file must include the Lora font import from Phase 1.

**Verified:**
- Each phase is independently deployable: Phase 1 (CSS only, no behavior change), Phase 2 (member profile + viz.js, no new routes), Phase 3 (new page + new endpoint), Phase 4 (home page + endpoint extension).
- Dependency order is correct: Phase 2 creates viz.js, Phase 3 and 4 depend on it. Phase 1 CSS is used by all subsequent phases.
- No security concerns: new endpoint uses existing input validation (`_validate_state_code`), party stripping, and rate limiting. No user-provided data is rendered unescaped (DOM element factories, not innerHTML).
- No new secrets, environment variables, or external dependencies introduced.
