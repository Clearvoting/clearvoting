# House Vote Sync — Design Document

**Date:** 2026-03-08
**Status:** Approved

## Problem

ClearVote syncs Senate roll call votes but not House votes. Result: 72 of 80 members (all House reps) have empty voting profiles. Only the 8 Senators across 4 synced states have vote records.

## Solution

Add House roll call vote syncing via the Congress.gov API `/house-vote` endpoint. Three client methods already exist in `congress_api.py` but are unused by `sync.py`.

## Data Source

Congress.gov API:
- `GET /house-vote/{congress}/{session}` — list votes
- `GET /house-vote/{congress}/{session}/{vote_number}` — vote detail (bill, question, result, counts)
- `GET /house-vote/{congress}/{session}/{vote_number}/members` — per-member votes with bioguide IDs

## Architecture

### Updated Sync Pipeline

```
Before: Members → Senate Votes → Bills (from Senate) → Member Records (Senate only)
After:  Members → Senate Votes → House Votes → Bills (from both) → Member Records (both)
```

### New: `sync_house_votes()`

- Iterates vote numbers 1 through `max_vote` (default 500, matching Senate)
- Calls `get_house_vote_detail()` for vote metadata
- Calls `get_house_vote_members()` for per-member votes
- Merges into a single JSON file per vote
- Saves to `data/synced/votes/house/{congress}_{session}_{vote:05d}.json`
- Incremental: skips files that already exist
- Rate-limited with `asyncio.sleep(rate_limit)`

### Updated: `sync_bills_from_votes()`

- Scans both `votes/senate/` AND `votes/house/` for bill references
- No other changes — same deduplication and incremental logic

### Updated: `build_member_votes()`

- Removes Senate-only filter
- Senators matched against Senate vote files (by last name + state, existing logic)
- House members matched against House vote files (by bioguide ID — Congress.gov API provides this)
- Both produce the same output format in `member_votes/{bioguide_id}.json`

### Updated: `main()`

- Pipeline becomes 5 steps (House votes inserted as step 3)
- Metadata tracks `house_votes_count`

## Key Decisions

- **Cap at 500 votes** — matches Senate approach, configurable
- **Bioguide ID matching for House** — Congress.gov API uses bioguide IDs directly (more reliable than the name-matching needed for Senate XML)
- **Parallel directory structure** — `votes/house/` mirrors `votes/senate/`
- **Same JSON output format** — member vote records are chamber-agnostic

## What Changes

| File | Change |
|---|---|
| `sync.py` | New `sync_house_votes()`, update `sync_bills_from_votes()`, update `build_member_votes()`, update `main()` |
| `tests/test_sync.py` | New tests for House sync, updated tests for expanded functions |
| `data/synced/votes/house/` | New directory with vote JSON files |
| `data/synced/member_votes/` | Grows from 8 to 80 files |

## What Doesn't Change

Senate vote sync, frontend, routers, DataService, AI summaries — all untouched.
