# ClearVote (ClearVoting) — Status

**What:** Unbiased congressional voting records with AI-generated plain-language bill summaries
**State:** Deployed to Render (auto-deploys from `main` on GitHub)
**URL:** ClearVoting.org
**Elevated:** Co-primary project (Mar 2026) based on LinkedIn traction

## SESSION HANDOFF (2026-07-02) — read this first

Full project/UI review + both P0 fixes + votes refresh + AI backfill: **shipped, merged,
and live.** One open PR (#24, docs-only: the review report + this STATUS update).

### What shipped this session (2026-07-01/02)
- **Full project review** (53 verified findings, 8 dimensions): see
  `docs/reviews/2026-07-01-full-project-ui-review.md` — it contains the prioritized
  week-by-week plan for what's next. Read it before starting new work.
- **PR #21 — waitlist emails persist to Google Sheets** ("Notify Signups" tab, auto-created).
  They previously died on Render's ephemeral disk every deploy.
- **PR #22 — vote dates stored as ISO 8601** → member vote records finally sort
  chronologically (was lexicographic: September 2021/2025 interleaved, June 2026 buried).
  Same-day votes tiebreak by roll-call number. Rebuilds no longer wipe AI scorecards.
  Shared `formatVoteDate()` in vote.js renders dates on member/bill pages.
- **PR #23 — votes refresh + AI backfill**: Senate through #192, House through #233,
  25 new bills (1,550 total), and **coverage back to 1,550/1,550 (100%)** — 29 summaries
  + 29 argument sets + Gallagher narrative generated via claude CLI on the Max plan
  (149/149 narratives). Member votes rebuilt so plain one-liners reach member pages.

### Top next-session priorities (in order)
1. **ANTHROPIC_API_KEY secret on GitHub** (Settings → Secrets → Actions) — unchanged #1.
   Saturday's sync adds bills; without the secret they sit summary-less until someone
   repeats this session's manual CLI run (which also required an interactive
   `claude auth login` — expired CLI tokens 401 silently).
2. **Homepage "Latest Vote" hero** renders raw official titles (broken grammar) even though
   plain one-liners exist — static/js/app.js `_build_latest_vote`; worst on mobile. (P1 in
   the review; highest-visibility remaining bug.)
3. **Regenerate member narratives/scorecards** — they were generated from the pre-fix
   mis-sorted vote lists; the data layer is fixed, narratives still reflect arbitrary
   samples. Scorecards are empty for 148/149 members (rebuild-wipe bug, now fixed).
4. **Trust pages** — footer Privacy/Methodology links point to /about which has neither,
   while the site collects emails. Review doc has the details.
5. **Rate limiting is inert in production** (limiter keys on proxy IP; one uvicorn flag).
6. Orphan cleanup: `member_votes/C001127.json` (member left Congress ~April).

### Operational notes / gotchas (still true)
- **Deploy = PR → merge → Render auto-deploys main.** Direct push AND self-merge of
  Claude-authored PRs are blocked; Joseph merges (or explicitly authorizes a merge).
- **The old `redesign/v4-homepage` stale-checkout hazard is RESOLVED** — the main checkout
  was reset to main on 2026-07-02 after salvaging this STATUS.md (the June 20 handoff had
  never been committed). Still: prefer fresh worktrees off origin/main for code edits.
- Local `mockups/` folder (v4 design reference) is untracked-local — don't delete.
- Lesson kept: read the actual rendered page, not just the metrics.

### Weekly GitHub Actions
- weekly-sync.yml (Saturdays) — government data sync, reliable.
- ai-sync.yml (Sundays) — AI generation; dormant until ANTHROPIC_API_KEY secret exists.
- tests.yml — pytest on every push/PR.
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

## Data (live, 2026-07-02)
4 states (NY, FL, CA, TX), 149 members incl. senators, 1,550 bills, 1,550 AI summaries
(100%) + argument sets (100%), 149/149 member narratives, vote dates ISO 8601 &
chronologically sorted, donations 2024 cycle (stale — see open items)

## Open Items (priority order)
1. **Add ANTHROPIC_API_KEY secret** on GitHub → ai-sync.yml takes over generation in
   the cloud (no laptop dependency), keeps summaries current as the weekly sync adds
   bills, and fills the 1 missing narrative. ~$5-10/mo ongoing. This is the single
   biggest remaining infra fix — the manual laptop loop is retired and won't self-heal.
2. **Analytics** (P1): Plausible/Fathom + Search Console — SEO shipped (server-side
   meta/OG/sitemap/robots), but nothing measures it yet; North Star is unmeasurable.
3. **Donations**: 2026 cycle + House office-filter bug + monthly CI step (still 2024).
4. **Trust pages**: privacy policy, methodology/corrections (needed before email capture
   collects addresses via /api/notify).
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
2026-03-05 · Last updated 2026-07-02
