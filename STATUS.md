# ClearVote (ClearVoting) — Status

**What:** Unbiased congressional voting records with AI-generated plain-language bill summaries
**State:** Deployed to Render (auto-deploys from `main`)
**URL:** ClearVoting.org (Render)
**Elevated:** Co-primary project (Mar 2026) based on LinkedIn traction

## Current State
- 264 tests passing. Multi-congress sync complete (117th/118th/119th). AI member narratives live.
- Party affiliations hidden by default. "Facts only. No opinions. No spin."
- Stack: Python/FastAPI backend + vanilla HTML/CSS/JS frontend
- Design: Light official color scheme, Inter + Playfair Display typography

## API Keys
- `CONGRESS_API_KEY` in `.env` (valid)
- `ANTHROPIC_API_KEY` is placeholder (only needed for AI bill summaries)

## Data Sources
Congress.gov API (members, bills, House votes) + Senate.gov XML (Senate roll calls) + Claude API (summaries + narratives)

## Architecture
`sync.py` pulls all data offline → saves to `data/synced/` as JSON → `DataService` loads at startup → routers serve from memory. 9-step pipeline. `CONGRESSES` constant at top of sync.py controls which congresses to sync.

## Synced Data (as of Mar 10, 2026)
4 states (NY, FL, CA, TX), 80 members, 636 bills, 2,159 Senate votes, 1,023 House votes, 80 member vote profiles, 636 AI bill summaries, 80 AI member narratives

## Sync Notes
- `sync.py --states NY,FL,CA,TX` — MUST pass all states each run (overwrites members.json)
- Senate votes, House votes, and bills are incremental
- 117th Congress House votes returned 0 (API data availability)
- 8 bill summaries still need AI regeneration (missing provisions — require ANTHROPIC_API_KEY)

## Key Features
State/district member lookup, bill browse + search, per-member voting profiles, Senate XML + House API vote parsing, AI member narratives, security hardening (rate limiting, SSRF protection, security headers, defusedxml)

## AI Summary Standards (Joseph's Direction)
- 7th-8th grade reading level. No jargon.
- No editorial language — no characterizations of how people feel
- DO include factual context: before/after numbers, affected population sizes, scale references
- Principle: give readers enough facts to form their own opinion. Facts, not framing.
- Prompt: `app/services/ai_summary.py` SYSTEM_PROMPT (12 strict rules)

## AI Member Summaries
`app/services/member_summary.py` — Sonnet generates 3-5 sentence narrative per member. Facts only. Stored in `data/synced/member_summaries.json`. `--regenerate-member-summaries` flag to re-run.

## LinkedIn Traction (Mar 12, 2026)
Launch post: 44+ reactions, 13 comments, 1 repost — 3x previous best. Validates ClearVote as lead portfolio project.

## Strategic Position (Mar 13, 2026)
Elevated to co-primary alongside Conduction AI. ClearVote leads job applications (especially Anthropic) — it's live, uses Claude API, demonstrates responsible AI, has social proof. Resume v6 puts ClearVote first. Cover letters updated.

## Next Steps
1. Publish LinkedIn follow-up posts (3-post series)
2. Update LinkedIn profile (headline, About, Featured)
3. Explore non-profit path (501(c)(3) vs 501(c)(4))
4. Regenerate 8 incomplete bill summaries (need ANTHROPIC_API_KEY: 118-s-4554, 118-sjres-117, 119-hjres-72, 119-hr-1834, 119-hr-5214, 119-hr-6703, 119-hres-888, 119-hres-992)
5. Sync more states

## Known Issues
- 117th Congress House votes returned 0 (API data availability)
- 8 bill summaries missing provisions (need AI regeneration with valid API key)

## Key Files
- `sync.py` — data sync pipeline
- `app/services/ai_summary.py` — bill summary AI prompt
- `app/services/member_summary.py` — member narrative AI
- `data/synced/` — all synced JSON data
- `render.yaml` + `Dockerfile` — deployment config

## Design Docs
- `docs/plans/2026-03-04-clearvote-design.md`
- `docs/plans/2026-03-04-clearvote.md`

## Virtualenv
`.venv` with Python 3.13 — use `source .venv/bin/activate` before running tests

## Date Created
2026-03-05
