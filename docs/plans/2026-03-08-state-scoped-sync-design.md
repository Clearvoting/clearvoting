# State-Scoped Sync — Design Document

**Date:** 2026-03-08
**Status:** Approved

## Problem

The current `sync.py` pulls ALL congressional data (56 states/territories, every bill in the 119th Congress, up to 500 Senate votes, AI summaries for all bills). This would require 10,000+ API calls, exceed Congress.gov's 5,000 requests/hour rate limit, and take hours to complete.

## Solution

Scope the sync to specific states (starting with NY and FL) so only relevant data is pulled. Generate AI summaries in-session via Claude Code (Max plan) instead of through the Anthropic API.

## Architecture

### CLI Interface

```
python sync.py --states NY,FL
python sync.py --states NY,FL,CA,TX    # add more states later
python sync.py                          # no change: syncs all states (original behavior)
```

### Sync Pipeline (5 steps)

| Step | Scope | API Source | Estimated Calls (NY+FL) |
|------|-------|-----------|------------------------|
| 1. Members | Only specified states | Congress.gov | ~2 |
| 2. Senate votes | All (each XML has all 100 senators) | Senate.gov XML | ~100-200 |
| 3. Bills | Only bills referenced in Senate votes | Congress.gov | ~100-200 |
| 4. AI summaries | Skipped in script | N/A | 0 |
| 5. Member votes | Only specified states' members | Local computation | 0 |

**Total: ~300-400 API calls** (down from 10,000+)

### Rate Limiting

- 0.5s delay between Congress.gov API calls
- 0.3s delay between Senate.gov XML fetches
- Stays well within 5,000 requests/hour limit

### Resume / Incremental Sync

- Senate votes: already incremental (skips existing files) — no change needed
- Bills: check if bill already exists in bills.json before fetching
- Members: always re-fetch (cheap, 1 call per state)

### AI Summaries Strategy

- `sync.py` skips AI summary generation entirely (step 4 becomes a no-op)
- After sync completes, Claude Code reads `bills.json` and generates summaries in-session
- Summaries written to `ai_summaries.json` using the same format the app expects
- When volume outgrows in-session generation, swap in a real `ANTHROPIC_API_KEY`

### Bill Scoping Logic

Instead of paginating through all 10,000+ bills in the 119th Congress:
1. Parse Senate vote XMLs for bill references (e.g., "H.R. 1", "S. 100")
2. Extract unique bill identifiers
3. Fetch only those specific bills from Congress.gov (one API call each)

This gives us only bills that were actually voted on — the ones that matter for voting records.

## Data Flow

```
sync.py --states NY,FL
  ├── Step 1: Congress.gov → members for NY, FL → members.json
  ├── Step 2: Senate.gov → all roll call votes → data/synced/votes/senate/*.json
  ├── Step 3: Parse vote files for bill refs → Congress.gov → bills.json
  ├── Step 4: Skip (AI summaries generated in-session)
  └── Step 5: Cross-reference votes × members → data/synced/member_votes/*.json

Claude Code (in-session):
  └── Read bills.json → generate summaries → ai_summaries.json
```

## Incremental Scaling

States can be added incrementally:
- `python sync.py --states CA` adds California members and their vote records
- Senate votes are shared across all states (already downloaded)
- Bills referenced in votes are also shared (already downloaded)
- Only new member vote cross-references need to be built

## Files Changed

- `sync.py` — add `--states` flag, rate limiting, bill scoping from votes, skip AI step
- No changes to `app/` code (DataService reads the same JSON format)
- No changes to frontend
