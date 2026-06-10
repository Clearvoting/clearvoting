# ClearVote (ClearVoting) — Status

**What:** Unbiased congressional voting records with AI-generated plain-language bill summaries
**State:** Deployed to Render (auto-deploys from `main` on GitHub)
**URL:** ClearVoting.org
**Elevated:** Co-primary project (Mar 2026) based on LinkedIn traction

## Current State (2026-06-10)
- Full multi-agent review completed + P0 fixes implemented (this session, pending merge)
- 285 tests passing. Stack: Python/FastAPI + vanilla HTML/CSS/JS, data as JSON in git
- Weekly GitHub Action syncs government data (Saturdays, reliable); NEW: ai-sync.yml
  (Sundays) automates AI generation once ANTHROPIC_API_KEY secret is added; NEW: tests.yml
  runs pytest on every push/PR
- Party affiliations hidden by default. "Facts only. No opinions. No spin."

## P0 Fixes Shipped (2026-06-10, pending merge)
1. **Member pagination** — live site had only 20 members/state and ZERO senators (API
   first-page truncation). Now 148 members incl. senators, with sanity floors that abort
   the sync on truncated data.
2. **Model retirement** — all 9 AI call sites pinned claude-sonnet-4-20250514 (retires
   Jun 15). Now a shared CLAUDE_MODEL constant = claude-sonnet-4-6.
3. **Bill-vote matching** — "H.R. 1" substring-matched H.R. 1002 etc. and ignored
   congress; also rescanned 4,605 files per request (seconds, event-loop blocking).
   Now an exact in-memory index: HR 1 went 268 wrong votes/12MB → 24 right votes/7KB.
4. **Vote cap** — 500/session cap silently truncated 5 sessions; raised to 1500
   (backfill happens via weekly sync).
5. **Health endpoint** now reports record counts + summary coverage (was invisible).
6. Repo reconciled: April's stranded work (no-overall-stats narratives) committed;
   docs reorganized into docs/archive + docs/reviews.

## Data (local, 2026-06-10)
4 states (NY, FL, CA, TX), 148 members, 1,450 bills, 658 AI bill summaries (45%
coverage), 80 member narratives (68 new members lack narratives), donations 2024
cycle (80 members, stale)

## Open Items (priority order)
1. **Merge the fixes PR** → Render deploys; then manually dispatch weekly-sync to
   backfill capped votes
2. **Add ANTHROPIC_API_KEY secret** on GitHub → ai-sync.yml closes the 797-bill
   summary gap (~$55-75 one-time backfill, ~$5-10/mo) and generates narratives for
   the 68 new members
3. **SEO + analytics** (P1 from review): server-side titles/meta/OG, sitemap,
   robots.txt, Plausible — the declared #1 growth channel, zero implementation,
   midterms Nov 2026
4. **Coverage honesty**: 4-state note + email capture; demo banner is dead code
5. **House votes on bill pages** (synced but never rendered; 83% of bills affected)
6. Donations: 2026 cycle + House office-filter bug + monthly CI step
7. Trust pages: privacy policy, who-runs-this, corrections/methodology

## API Keys
- `CONGRESS_API_KEY` in `.env` (valid)
- `ANTHROPIC_API_KEY` placeholder locally; needed as GitHub secret for ai-sync.yml

## Key Files
- `sync.py` — data sync pipeline (`--step members|bills|...`, `--ai-only`, `--skip-ai`)
- `app/services/grader_common.py` — shared CLAUDE_MODEL constant
- `app/services/ai_summary.py` — bill summary prompt (12 neutrality rules)
- `.github/workflows/` — weekly-sync.yml, ai-sync.yml (new), tests.yml (new)
- `data/synced/` — all synced JSON data

## Sync Notes
- `sync.py --step members --states NY,FL,CA,TX` — pass all states (overwrites members.json)
- Member count floors abort sync on truncated data (vacant seats tolerated)
- Senate/House votes and bills are incremental; AI steps skip existing items

## Virtualenv
`.venv`, Python 3.13 — recreated 2026-06-10 (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`)

## Date Created
2026-03-05 · Last updated 2026-06-10
