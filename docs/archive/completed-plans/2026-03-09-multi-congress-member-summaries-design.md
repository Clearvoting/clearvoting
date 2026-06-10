# Multi-Congress Sync + AI Member Summaries — Design

**Created:** March 9, 2026

## Problem

ClearVote's member profile page shows raw vote data (policy area counts, lists of supported/opposed bills) but no narrative summary. Users can't quickly understand what a member cares about or how they've voted. The data only covers the 119th Congress (~14 months), limiting the picture.

## Solution

1. Expand the sync pipeline to pull 3 congresses (117th, 118th, 119th) — covering 2021-present (~5 years)
2. Generate AI member summaries using Sonnet — a 3-5 sentence narrative profile per member, based entirely on their voting record
3. Display the narrative at the top of the "At a Glance" card on the member detail page

## Design Decisions

**Sync 3 congresses (117, 118, 119).** 5 years gives Sonnet enough material to write meaningful profiles. The congress list is a constant — easy to extend when Joseph wants to go further back.

**Pre-compute summaries during sync, not on-demand.** Matches ClearVote's offline-first architecture. Everything is pre-computed and served from memory. No latency on page load, no error handling in the frontend.

**Use Sonnet for member summaries.** Haiku is too lightweight for synthesizing 500+ votes into coherent narrative. Opus is overkill for structured data summarization. Sonnet is the right balance of quality and cost.

**Keep Sonnet for bill one-liners.** Already using `claude-sonnet-4-20250514` — no model change needed.

**Facts only, no general knowledge.** Summaries are generated strictly from vote data we've synced. No career history, no external claims. Every statement in the summary can be traced to actual votes. Consistent with ClearVote's "facts, not framing" mission.

**Run member summaries through writer-grader loop.** Same quality control as bill summaries — ensures no editorializing slips through.

## Data Model

**Member votes** (`member_votes/<bioguideId>.json`):
- Currently: `congress: 119` (single value)
- New: `congresses: [117, 118, 119]`, each vote entry has its own `congress` field
- Votes from all congresses aggregated into one file per member

**Member summaries** (`member_summaries.json`):
- New file, keyed by bioguide ID
- Contains: `narrative` (string), `top_areas` (array), `generated_at` (timestamp)

**Bills** (`bills.json`):
- Already stores congress per bill — new bills from 117/118 appended

**AI summaries** (`ai_summaries.json`):
- Keys already include congress (`119-hr-1`) — extends naturally to `117-hr-1`, etc.

## Sync Pipeline

Current (7 steps) → New (9 steps):

1. Members (current only — no change)
2. Senate votes (loop: 117/1, 117/2, 118/1, 118/2, 119/1, 119/2)
3. House votes (loop: same 6 congress/session pairs)
4. Bills from votes (across all congresses)
5. Bill summaries (writer-grader loop for new bills only — incremental)
6. Member votes (aggregate across all congresses)
7. **NEW: Member summaries (Sonnet generates narrative per member)**
8. **NEW: Member summary grading (writer-grader loop)**
9. Summary report

Existing 119th Congress data is skipped (incremental sync). Only 117th and 118th data is fetched.

## Frontend

Narrative paragraph displayed at the top of the "At a Glance" card. Plain text, no special formatting. Existing data visualizations (policy bars, supported/opposed lists) remain below unchanged.

## Not In Scope

- UI redesign of the member profile page
- Syncing members from older congresses (only current members)
- Career history or general knowledge in summaries
- Real-time/on-demand summary generation
