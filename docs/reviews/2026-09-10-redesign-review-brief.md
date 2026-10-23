# ClearVoting redesign — context brief for review and design agents

Written 2026-09-10 for the review; reused 2026-09-18 for the design phase. Kept in the repo as provenance for
`2026-09-10-redesign-review.md` and the design spec.

## Paths
- Code: fresh worktree `/Users/josephgarcia/.clearvote-worktrees/redesign-2026-09` (branch `redesign/2026-09`, off origin/main f1dc535 —
  frontend identical to the live site).
  - static/index.html, member.html, bill.html, state.html, about.html, 404.html
  - static/css/styles.css (3,848 lines, shared base + inner-page classes, ~36% dead), static/css/broadsheet.css (455 lines, the "civic broadsheet" system)
  - static/js/app.js (home), member.js (1,022), bill.js, state.js, vote.js, viz.js, feedback.js
  - app/main.py (HTML shells, server-side SEO meta injection `_inject_meta`, CSP, sitemap), app/routers/*.py, app/services/data_service.py
  - data/synced/ — the live data (members.json, bills, member_votes/, AI summaries). Only fields that exist here may be shown.
  - docs/001-prd-clearvote.md (PRD: target user = "busy informed citizen"; milestone = Nov 2026 midterms)
  - docs/reviews/2026-09-10-redesign-review.md — THE REVIEW (63 verified findings F01–F63, protect-this list, 8 themes, guardrails, Appendix C critic)
  - docs/reviews/2026-07-01-full-project-ui-review.md — the prior review
  - docs/superpowers/plans/2026-06-13-inner-page-broadsheet.md — how inner pages were partially unified in June (hard constraints inside)
- Live-site screenshots (PNG; Read renders them): `/Users/josephgarcia/Claude/.playwright-mcp/cv-review/`
  home-desktop-full, home-mobile-full, home-mobile-fold, member-desktop-full, member-mobile-full (Sen. Schumer S000148; mobile is 445px wide = 70px overflow),
  bill-desktop-full, bill-mobile-full (H.Con.Res.108, has AI summary), bill-nosummary-desktop-full (H.R.4795, no AI summary), state-desktop-full, state-mobile-full (NY),
  about-desktop-full, about-mobile-full, home-desktop-a11y.md
- Live site: https://clearvoting.org — page URLs `/`, `/member?id=S000148`, `/bill?congress=119&type=hconres&number=108`, `/state?code=NY`, `/about`.
  API: /api/votes/latest, /api/bills?limit=20, /api/bills/{congress}/{type}/{number}, /api/members/{STATE}, /api/members/{STATE}/overview,
  /api/members/{STATE}/{district}, /api/members/detail/{bioguide}, /api/members/{bioguide}/votes, /api/members/{bioguide}/summary, /api/health.
  Use curl; do NOT use Playwright/browser MCP tools (shared browser).

## Product context
- Mission: "See how your representatives vote" — every vote in plain English, party labels hidden until asked. "Facts only. No opinions. No spin."
  Person-first: start with YOUR representative.
- Target user: the busy informed citizen — cares, no time, not a political junkie, on a phone. One visit, a few clicks, plain English.
- Milestone: Election Day is Tuesday, November 3, 2026. Today is 2026-09-18 (46 days out).
- Coverage: 4 states (NY, FL, CA, TX), 150 members, 1,610 bills, 1,550 AI summaries. The AI sync is dormant (GitHub secret missing), so the ~60 newest bills
  have no summary; fixing the sync is out of scope, but every fallback for missing summaries is in scope and must be honest.
- Design: "civic broadsheet" (v4, shipped June 2026): Playfair Display headings, Lora body, Inter UI, navy ink on paper, double rules, kickers. The review's
  verdict: protect the language; rebuild the middle of every page on it. Do not propose abandoning it.
- Owner: Joseph Garcia (Group PM, not an engineer). Deploy = PR → he merges → Render auto-deploys.

## Hard technical constraints (any design or plan that violates them is rejected)
1. Server-side SEO injection needs a literal `<title>…</title>` and `</head>` in every static HTML file; the server owns the title (client must not overwrite it).
2. CSP: `script-src 'self'` — no inline scripts or handlers. `img-src 'self' https://www.congress.gov` only.
3. No new `innerHTML`; bill.js's existing `sanitizeHtml`/SAFE_TAGS block stays.
4. feedback.js reads structural hooks (`.member-header h2`, `.bill-header h2`, `.state-header h1`, `#feedback-*`, `#data-freshness`); the only sanctioned change is
   promoting those h2s to h1 with the selectors updated in the same commit.
5. Real data only. The only new data files allowed are (a) the public-domain Census ZCTA→119th-District crosswalk and (b) a Senate-seats-up-in-2026 list,
   both flagged explicitly with source and attribution.
6. Stack stays: FastAPI + vanilla HTML/CSS/JS, no framework, no build step, no database. One PR.
7. Do not change URL shapes without 301s; canonical tags point at one form.

## ZIP → district feasibility (spike verified 2026-09-11)
Source: U.S. Census Bureau 2020 ZCTA ↔ 119th Congressional District relationship files,
https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/ — per-state `tab20_cd11920_zcta520_st{06,12,36,48}.txt` (pipe-delimited, UTF-8 with BOM;
columns GEOID_CD119_20 = state FIPS + 2-digit CD, GEOID_ZCTA5_20, AREALAND_PART / AREALAND_ZCTA5_20 = land-area share; no population share exists).
Public domain (17 U.S.C. §105). Results: NY 1,826 ZCTAs / FL 1,013 / CA 1,808 / TX 1,992; 67–84% map to one district, the rest to 2–4 (show every district
with ≥5% share and let the user pick). Compact JSON `{"10001":[{"state":"NY","district":12,"share":1.0}]}` ≈ 416 KB raw / 36 KB gzipped after trimming
<1% slivers. Caveats: ZCTA ≠ USPS ZIP (PO-box-only ZIPs absent → need an "unknown ZIP" path); share is land area, not population. The keyless Census
Geocoder (`geocoding.geo.census.gov/geocoder/geographies/onelineaddress?…&benchmark=Public_AR_Current&vintage=Current_Current&format=json`) returns
CD119 for a street address and works as an optional address-level fallback.
