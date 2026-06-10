# ClearVote Data Sync Architecture — Design Document

**Date:** 2026-03-07
**Status:** Approved
**Goal:** Replace live Congress.gov API calls and hardcoded demo data with a local sync script that pre-builds all data as JSON files, enabling all 50 states at zero hosting cost.

---

## Problem

ClearVote currently operates in two modes:

1. **Demo mode** — returns hardcoded Florida data from `mock_data.py`. Limited to 4 members and 10 bills.
2. **Live mode** — calls Congress.gov API in real-time per user request. Slow, fragile, and member voting records return 501 (not implemented).

Neither mode supports all 50 states. Live mode would hit Congress.gov on every page load for 535+ members, risking rate limits and slow responses. AI summaries are generated per-request via Claude, which is expensive and exposes the API key in the running server.

## Solution

A local sync script (`sync.py`) that runs on Joseph's laptop. It:

1. Pulls all member, bill, and vote data from Congress.gov and Senate.gov
2. Generates AI summaries for new bills via Claude
3. Saves everything as JSON files in `data/synced/`
4. Files are committed to git and deployed with the container

The web app reads exclusively from these pre-built JSON files. No live API calls during user requests.

## Architecture

### Data Flow

```
Joseph runs sync.py on laptop
  → Congress.gov API (free) → members, bills, votes
  → Senate.gov XML (free) → Senate roll call votes
  → Claude API (Joseph's key, local only) → AI summaries for new bills
  → Saves to data/synced/ as JSON files
  → git commit + push
  → Cloud Run auto-redeploys with new data

User visits ClearVote
  → App reads from data/synced/ JSON files (in-memory at startup)
  → Returns data instantly
  → No external API calls, no API keys needed at runtime
```

### File Structure

```
data/synced/
  members.json            ← all 535+ current members of Congress
  bills.json              ← recent bills with official summaries
  ai_summaries.json       ← Claude-generated plain-language summaries
  votes/
    senate/               ← one JSON per Senate roll call vote
    house/                ← one JSON per House vote
  member_votes/
    {bioguide_id}.json    ← per-member voting record (one file each)
  sync_metadata.json      ← last sync timestamp, record counts
```

### Sync Script Behavior

- **Incremental** — only processes new bills/votes since last sync. AI summaries skip bills already summarized.
- **Resumable** — if interrupted, re-running picks up where it left off (checks existing files).
- **Visible** — prints progress to terminal as it runs.
- **Idempotent** — running twice produces the same result.

### App Changes

1. **New `DataService` class** — loads `data/synced/` JSON files into memory at startup. Provides methods matching current router needs (`get_members_by_state`, `get_member_detail`, `get_member_votes`, `get_bills`, `get_bill_detail`, `get_ai_summary`, `get_bill_votes`).

2. **Routers simplified** — remove `_is_demo()` branching and live API call paths. All routers call `DataService` methods. Response shapes stay identical.

3. **AI summary endpoint** — reads from `ai_summaries.json` instead of calling Claude. Returns "Summary pending" if a bill hasn't been summarized yet.

4. **Removed from request path** — `mock_data.py` (replaced by real data), live `CongressAPIClient` calls from routers (moved to sync script), real-time Claude calls (moved to sync script).

5. **Kept** — `CongressAPIClient` class (used by sync script), `AISummaryService` class (used by sync script), `SenateVoteService` class (used by sync script), `CacheService` (used by sync script during its run).

## Operational Model

**Running the sync:**
```bash
cd ~/Documents/Claude/Projects/clearvote
source .venv/bin/activate
python sync.py
```

**Deploying updated data:**
```bash
git add data/synced/
git commit -m "sync: daily data update"
git push
```

**Frequency:** Run manually when desired. During Congressional session, once per day is sufficient. During recess, once per week or less.

**If the sync fails:** The app serves the last successfully synced data. Congressional data is slow-moving — being one day stale is invisible to users.

## API Key Security

- **Anthropic API key** stays only on Joseph's laptop in `.env` (gitignored). Never deployed to Cloud Run, GitHub, or any server.
- **Congress.gov API key** same — local only. The deployed app makes zero external API calls.
- **Future state:** When ClearVote becomes a non-profit, a dedicated Claude account + GitHub Actions can automate the sync. The script is identical — only the trigger changes.

## Cost

| Component | Cost |
|---|---|
| Congress.gov API | Free |
| Senate.gov XML | Free |
| Claude API (AI summaries) | ~$0.50-1.00 initial bulk run, ~$0.05-0.10/day after (Joseph's existing plan) |
| Cloud Run (web app) | Free tier (2M requests/month) |
| Cloud Storage | Not used — data is in the container |
| **Total ongoing** | **~$0** |

## What This Enables

- **All 50 states** — every current member of Congress, not just FL
- **Member voting records** — solves the 501 gap in real mode
- **Fast responses** — no external API calls during user requests
- **Reliability** — app works even if Congress.gov is down
- **Simple operations** — one script, one command, familiar git workflow

## Future Migration Path

When ClearVote becomes a non-profit with its own infrastructure:

1. Create a dedicated Anthropic account for ClearVote
2. Move sync script to GitHub Actions with cron schedule (daily at 6 AM ET)
3. Optionally move JSON files to Google Cloud Storage instead of git
4. The sync script code stays the same — only the trigger and storage location change
