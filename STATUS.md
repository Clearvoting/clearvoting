# ClearVote (ClearVoting) — Status

**What:** Unbiased congressional voting records with AI-generated plain-language bill summaries
**State:** Deployed to Render (auto-deploys from `main` on GitHub)
**URL:** ClearVoting.org
**Elevated:** Co-primary project (Mar 2026) based on LinkedIn traction

## SESSION HANDOFF (2026-09-22) — REDESIGN IN FLIGHT, read this first

**Where the work lives.** Branch `redesign/2026-09` in the worktree `/Users/josephgarcia/.clearvote-worktrees/redesign-2026-09`
(off origin/main f1dc535; frontend identical to live). The main checkout at `Projects/Non-Profit/ClearVote` is untouched and
~49 commits behind — do not work there. Persistent helper artifacts (outside the repo, survive scratchpad wipes):
`/Users/josephgarcia/.clearvote-worktrees/tools/` — `shots/shoot.mjs` (Playwright batch screenshots, desktop 1280 + mobile 375,
prints scrollWidth), `data/zip_districts.json` + `build_zip_crosswalk.py` (+ `raw/` Census files), `data/senate_2026.json`
(verified against senate.gov 2026-09-19: Cornyn TX regular, Moody FL special), `design/` (four proposals + mockups + judge
screenshots), `plan/index_tasks.py`. Launchable workflow scripts (must live under the vault): `~/Claude/.claude/workflows/clearvote/`
— `design-workflow.js`, `spec-critique-workflow.js`, `plan-workflow.js`, `build-workflow.js`.

**Done (all committed on the branch).**
1. Review — `docs/reviews/2026-09-10-redesign-review.md`: 63 verified findings (2 P0, 18 P1, 35 P2, 8 P3), 18 protect-this items,
   8 themes, guardrails, Appendix C (independent critic: gaps, unverified claims, contradictions). Brief: `…-review-brief.md`.
2. Design panel — `docs/superpowers/specs/2026-09-18-design-panel/` (README has the scores): Spine 135, Broadsheet 133, Share 130,
   Evolve 130; winner votes citizen+PM → Spine, designer → Broadsheet.
3. Design spec — `docs/superpowers/specs/2026-09-18-clearvoting-redesign-design.md` (659 lines, 12 sections: IA/URLs, page specs
   with every fallback state, ZIP feature, tokens with computed contrast, glossary, WCAG list, reach, 19 backend touches, F01–F63
   coverage, deferrals). **Critique done 2026-09-22** (`795b22f`): 4 critics (feasibility/user/trust/F01–F63 traceability) raised
   115 issues (10 blocker, 52 major), all fixed (9 partial fixes declined with reasons, §2.5); a completeness check made 10 inline
   fixes → "ready with notes". Spec is now 1,107 lines; adds sync-time `votes_index.json`, merge-by **2026-10-13** + cut-first list (§10.3).
4. Baseline: 370 tests pass from the worktree with the main checkout's venv; app boots locally (`uvicorn app.main:app --port 8011`).

**Plan done 2026-09-25** (`04d9e39`): `docs/superpowers/plans/2026-09-18-clearvoting-redesign.md` (40 tasks, ids `T<step>.<n>`, 11 phases =
spec §10.3 commit order) + `docs/reviews/2026-09-18-redesign-plan-review.md` (verdict **Ready**; 141 issues, 2 P0/54 P1 all resolved).
Task index: `~/.clearvote-worktrees/tools/plan/tasks.json` (build positions n=1..40; cut-first = n 31, 33–37; minimum shippable = the rest).
Plan working files (fragments, map.json, review-log.json, assemble_plan.py) live in `~/.clearvote-worktrees/tools/plan/` (a git repo).
Build launched 2026-09-25 with `start: 1` — see `docs/reviews/build-2026-09/` for per-task reviews and `git log` for progress.

**Not done.** Build (+ adversarial plan review) → build → QA → push + PR (Joseph merges).

**Next session, in order (each is one Workflow call; the scripts carry all context).**
1. ~~Spec critique~~ — done 2026-09-22 (`795b22f`, `5cdc26e`). ~~Plan~~ — done 2026-09-25 (`04d9e39`).
   Plan workflow launched 2026-09-22 as run `wf_4ddf70c2-75c` (resumable only in that session; otherwise relaunch fresh).
2. Plan: `Workflow({scriptPath: ".../plan-workflow.js"})` — architect map → parallel task writers → assembled plan at
   `docs/superpowers/plans/2026-09-18-clearvoting-redesign.md` → 3 adversarial reviewers → revised plan + review doc at
   `docs/reviews/2026-09-18-redesign-plan-review.md`. Read the review's readiness verdict before building. Commit both.
3. Build: `python3 ~/.clearvote-worktrees/tools/plan/index_tasks.py <plan.md> > ~/.clearvote-worktrees/tools/plan/tasks.json`, then
   `Workflow({scriptPath: ".../build-workflow.js", args: {tasks: <contents of tasks.json as a JSON array>, start: 1}})` — sequential:
   fresh implementer per task (TDD, smoke, commit) → reviewer → up to two fix rounds; stops on ANY task that does not pass review
   (never builds on a failed task); returns `next_start`. Tasks titled "(cut-first)" can be skipped with `start`/`stop` if behind on Oct 6.
   Relaunch with `start: <next_start>` after any stop. Per-task reviews land in `docs/reviews/build-2026-09/`.
4. QA (`/qa` against the local server, all pages at 375/768/1280 + every fallback state), update this STATUS + NOW.md, push the branch,
   open the PR (Joseph merges; Render auto-deploys main).

**PM decisions — all confirmed by Joseph 2026-09-22 and baked into plan-workflow.js.** Spec §2.5 adds: (A) member narratives withdrawn
(34/150 used "leans" stance labels) and `/summary` deleted; (B) "Key votes 4 yes + 4 no" → "Recent votes" (8 newest decisive, any position);
(C) the 115 `needs_review` summaries (failed the site's own grader) withheld; (D) merge-by 2026-10-13, cut extras if behind on Oct 6. Earlier:
(a) About page names "Joseph Garcia" as maintainer; contact = the feedback form only, no email published. (b) No Render plan change
in this PR (cold start deferred to ops). (c) The AI "supporters say / critics say" module is removed (unsourced text is not content);
campaign money is one dated 2024-cycle sentence with an FEC link for the 80 members who have data. (d) "On the ballot" copy always
describes the seat, never the person.

**Gotchas that cost days.** Workflow resume replay is keyed by agent-call ORDER: parallel agents that finish in a different order on replay miss the cache, so keep long runs sequential (the build is) and persist results to files; cap live agents (~4); split any agent that cannot finish inside one usage window. Usage-limit windows cut workflows mid-run: resume with `resumeFromRunId` in the SAME session; after a
session-id rotation the journal is gone — scripts accept `args.done` / `args.start` to skip finished work. Keep verifiers cheap
(grep/curl first, ≤2 screenshots, effort medium; ~200k tokens per screenshot-heavy agent). Never keep phase artifacts only in the
scratchpad. `Workflow({scriptPath})` only accepts paths under the vault. Do not use the Playwright MCP inside workflow agents (shared
browser) — use `tools/shots/shoot.mjs`. Deploy is PR → Joseph merges; direct push and self-merge are blocked.

## SESSION HANDOFF (2026-07-02) — (previous)

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
- ai-sync.yml (Sundays) — AI generation; dormant until the CLAUDE_CODE_OAUTH_TOKEN
  secret exists (Max subscription, preferred) or ANTHROPIC_API_KEY (pay-per-token).
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
1. **Add CLAUDE_CODE_OAUTH_TOKEN secret** on GitHub (Settings → Secrets → Actions)
   → ai-sync.yml takes over generation in the cloud on the Max subscription ($0/mo;
   token from `claude setup-token`, lasts ~1 year). Keeps summaries current as the
   weekly sync adds bills. This is the single biggest remaining infra fix — the
   manual laptop loop won't self-heal. (ANTHROPIC_API_KEY still works as the
   pay-per-token fallback, ~$5-10/mo.)
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
- `ANTHROPIC_API_KEY` placeholder locally; ai-sync.yml prefers the
  `CLAUDE_CODE_OAUTH_TOKEN` GitHub secret (Max subscription via `claude setup-token`)

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
