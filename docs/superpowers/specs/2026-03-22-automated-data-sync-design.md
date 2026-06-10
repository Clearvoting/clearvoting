# Automated Data Sync — Design Spec

**Date:** 2026-03-22
**Status:** Draft
**Goal:** Keep ClearVote voting data fresh on a weekly schedule with zero manual intervention for government data, and a supervised AI generation loop on Sundays.

---

## Overview

ClearVote's 12-step sync pipeline (`sync.py`) currently runs manually via CLI. This design automates it in two parts:

1. **Saturday (automated):** GitHub Actions runs government data sync — members, votes, bills, campaign finance. Commits results to `main`. Render auto-deploys.
2. **Sunday (supervised):** User starts a /loop in Claude Code that runs AI generation (bill summaries, arguments, scorecard verdicts, member narratives, coherence checks) using the Claude Max plan. Each iteration diagnoses and fixes errors. When complete, user commits and pushes.

**Data is fresh for Monday.**

---

## Part 1: GitHub Actions Workflow (Saturday Government Sync)

### Workflow File

`.github/workflows/weekly-sync.yml`

### Schedule

Every Saturday at 10:00 UTC (~6 AM ET summer / 5 AM ET winter).

```yaml
on:
  schedule:
    - cron: '0 10 * * 6'  # Saturday 10:00 UTC
  workflow_dispatch:  # Manual trigger for testing
```

### Steps

1. Check out repo (`main` branch)
2. Set up Python 3.12
3. Install dependencies from `requirements.txt`
4. Configure git identity for automated commits:
   ```yaml
   git config user.name "github-actions[bot]"
   git config user.email "github-actions[bot]@users.noreply.github.com"
   ```
5. Set environment variables from secrets:
   ```yaml
   env:
     CONGRESS_API_KEY: ${{ secrets.CONGRESS_API_KEY }}
     FEC_API_KEY: ${{ secrets.FEC_API_KEY }}
   ```
6. Run government data sync:
   ```
   python sync.py --skip-ai
   ```
   This runs steps 1–4, 7, 10, and 12 of the pipeline:
   - [1/12] Sync members (all states from `SYNC_STATES` constant)
   - [2/12] Sync Senate votes (incremental)
   - [3/12] Sync House votes (incremental)
   - [4/12] Sync bills from votes (incremental)
   - [7/12] Build member voting records (cross-references votes with members — not AI-dependent)
   - [10/12] Sync campaign finance / FEC (incremental)
   - [12/12] Write sync metadata (updates "last synced" timestamp)
7. Check if any files changed in `data/synced/`
8. If changes exist: commit with message `data: weekly government sync [automated]` and push to `main`
9. If no changes: skip commit (no-op week, Congress may not have been in session)

### Secrets Required

Add to GitHub repo settings (Settings → Secrets → Actions):

- `CONGRESS_API_KEY` — Congress.gov API key
- `FEC_API_KEY` — FEC API key for campaign finance

### Failure Handling

- GitHub sends email on workflow failure (default behavior)
- Since sync steps are incremental, a failed run loses nothing — next Saturday picks up where it left off
- `workflow_dispatch` trigger allows manual re-run if Saturday's cron fails
- Workflow sets a 45-minute timeout (typical run: 15-30 min)

### Estimated Runtime

15-30 minutes. Rate-limited by Congress.gov API (0.3-0.5s between calls). Senate votes are the slowest step (~2,172 files to check, though most are skipped as incremental).

---

## Part 2: Sync.py Changes

### New CLI Flags

**`--skip-ai`** — Skips all AI-dependent steps. Runs the government data pipeline:

| Step | Description | Notes |
|------|-------------|-------|
| 1/12 | Sync members | Uses `SYNC_STATES` default |
| 2/12 | Sync Senate votes | Incremental |
| 3/12 | Sync House votes | Incremental |
| 4/12 | Sync bills from votes | Incremental |
| 7/12 | Build member voting records | Cross-references votes with members (reads files, no API calls) |
| 10/12 | Sync campaign finance (FEC) | Incremental |
| 12/12 | Write sync metadata | Updates "last synced" timestamp |

Skips: 5 (bill summaries), 6 (bill arguments), 8 (scorecard verdicts), 9 (member narratives), 11 (coherence checks).

**`--ai-only`** — Runs only the AI-dependent steps. Assumes government data is already fresh from a prior sync:

| Step | Description | Notes |
|------|-------------|-------|
| 5/12 | AI bill summaries | Incremental (skips existing) |
| 6/12 | Bill arguments | Incremental |
| 8/12 | Scorecard verdicts | Per-member, per-category |
| 9/12 | AI member narratives | Incremental |
| 11/12 | Page coherence check | Validates narratives vs. data |
| 12/12 | Write sync metadata | Updates "last synced" timestamp |

When `--ai-only` is set, the `CONGRESS_API_KEY` check is bypassed (no government API calls are made).

These flags are mutually exclusive. If neither is passed, the full 12-step pipeline runs (existing behavior).

### Default States Configuration

Add a `SYNC_STATES` constant at the top of `sync.py` (next to `CONGRESSES`):

```python
SYNC_STATES = ["NY", "FL", "CA", "TX"]
```

- `--states` CLI flag overrides this, but the default is always the full list
- Eliminates the risk of forgetting a state and losing data in the members overwrite
- Single source of truth — update this constant when expanding to new states

**Behavior change note:** Currently, running bare `python sync.py` without `--states` defaults to all 50 states + territories. After this change, the default becomes the 4 states in `SYNC_STATES`. This is intentional — it matches ClearVote's current scope and prevents accidental full-country syncs.

### No Other Changes

The existing 12-step pipeline logic, error handling, rate limiting, and incremental behavior remain unchanged. We are only adding control flow flags.

---

## Part 3: Sunday AI Generation Loop

### How It Works

User opens Claude Code on Sunday and starts a /loop:

```
/loop 15m run the ClearVote AI sync
```

### Each Iteration

Claude Code performs the following on each loop cycle:

1. **Run the AI sync:**
   ```
   cd ~/Documents/Claude/Entrepreneurship/Non-Profit/ClearVote
   source .venv/bin/activate
   python sync.py --ai-only
   ```

2. **Check the output for:**
   - Errors (API timeouts, malformed responses, file write failures)
   - Warnings (flagged summaries, grader rejections beyond max iterations)
   - Progress counts (e.g., "Generated 5/12 new bill summaries")

3. **If errors found:**
   - Diagnose root cause from the sync output and logs
   - Attempt to fix (e.g., retry a failed step, adjust batch size, clear a corrupted cache entry)
   - Report what went wrong and what was done about it

4. **If no errors:**
   - Report progress: items processed this iteration, items remaining, total coverage
   - If nothing new to process (all items have summaries), report "AI sync complete — all items up to date"

5. **Wait for next iteration** (15 minutes) or report completion

### Completion

When all AI items are processed (no new work remains across 2 consecutive iterations):

1. Claude Code reports: "AI sync complete. Ready to commit and push."
2. User confirms
3. Commit: `data: weekly AI generation [supervised]`
4. Push to `main` → Render auto-deploys

### Error Scenarios and Responses

| Error | Diagnosis | Fix |
|-------|-----------|-----|
| Claude CLI timeout (120s) | Single bill/member took too long | Retry that item; if persistent, skip and flag for manual review |
| Rate limit from Claude Max | Too many calls in short window | Increase delay between calls, reduce batch size |
| Malformed AI response | Claude returned unparseable JSON | Retry with same prompt; if persistent, log and skip |
| File write error | Disk full or permissions | Report to user, pause loop |
| Grader rejects after max iterations | Summary doesn't meet quality bar | Accept best attempt, flag for manual review |
| Network error | Connectivity issue | Wait for next loop iteration, retry automatically |

### Estimated Runtime

- **Incremental (typical Sunday):** 5-15 minutes. Only new bills/members from Saturday's sync need processing. Usually 5-20 new items.
- **Full regeneration (rare):** 2-4 hours. Only needed when adding new states or using `--regenerate-*` flags.

---

## Part 4: Monitoring

### Automated Checks

- **GitHub Actions:** Email notification on workflow failure (built-in)
- **Sync metadata:** `data/synced/sync_metadata.json` records last sync timestamp, states synced, and item counts. The app footer shows "Data last updated [date]."
- **Staleness signal:** If the footer date is more than 9 days old (missed a Saturday), something failed.

### Manual Checks

- **GitHub Actions tab:** View run history, logs, and timing at any time
- **Sunday /loop output:** Real-time progress and error reporting during AI generation
- **Flagged summaries:** Sync output lists any bill IDs where the grader flagged quality issues

### No Additional Monitoring Infrastructure

At 4 states and weekly frequency, email notifications + the existing metadata endpoint are sufficient. If ClearVote scales to more states or higher frequency, consider adding a health check endpoint or Slack webhook.

---

## Weekly Flow Summary

```
Saturday ~6 AM ET (10:00 UTC)
  └─ GitHub Actions: sync.py --skip-ai
       └─ Commits gov data to main
            └─ Render auto-deploys (gov data fresh, AI data from last week)

Sunday (when convenient)
  └─ User opens Claude Code
       └─ /loop 15m: sync.py --ai-only
            └─ Each iteration: run, check, diagnose, fix, report
                 └─ When complete: commit + push
                      └─ Render auto-deploys (everything fresh)

Monday
  └─ All data current
```

---

## What This Design Does NOT Include

- **No Anthropic API key on the server** — AI generation runs locally via Claude Max plan
- **No database** — Flat JSON files remain the storage layer
- **No app hot-reload** — Render redeploys on each push to `main` (sufficient for weekly cadence)
- **No alerts beyond email** — No Slack, no PagerDuty, no dashboards
- **No changes to the existing 12-step pipeline logic** — Only adding control flow flags

---

## Known Tradeoffs

**Git repo size growth:** The `data/synced/` directory is currently ~174MB. Weekly commits of changed JSON files will grow the repo over time. JSON diffs compress well (incremental changes are small), so the actual git object growth per week is much less than 174MB — but over months the repo will grow. At the current 4-state scale, this is manageable for a long time (GitHub's soft limit is 1GB, hard limit 5GB). If repo size becomes an issue, mitigations include: shallow clones for CI, `git gc --aggressive`, squashing data commits periodically, or migrating to git-lfs or external storage. No action needed now.

**Branch protection:** If the `main` branch has protection rules (require PR reviews, status checks), the GitHub Actions bot will not be able to push directly. The workflow assumes direct push access to `main`. If protection is enabled, either add a bypass for the bot or switch to an auto-merge PR approach.

---

## Files Changed

| File | Change |
|------|--------|
| `sync.py` | Add `--skip-ai`, `--ai-only` flags and `SYNC_STATES` constant |
| `.github/workflows/weekly-sync.yml` | New file — GitHub Actions workflow |
| GitHub repo settings | Add `CONGRESS_API_KEY` and `FEC_API_KEY` secrets |

---

## Open Questions

None. Design is fully specified.
