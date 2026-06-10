# Member Profile Summary Improvements — Design Document

**Date:** 2026-03-08
**Status:** Approved

## Problem

The "At a Glance" section on member profile pages has three issues:

1. **Misleading "most active on" text** — Says a member is "most active on environmental protection" when they voted 0 for / 8 against. "Most active" implies support or interest. It should be neutral.

2. **Duplicate bill titles** — The GENIUS Act appears in both "What They Supported" and "What They Opposed" because Congress votes on bills multiple times (cloture, amendments, final passage). Same bill also appears multiple times within a single list.

3. **Incomprehensible bill titles** — The `one_liner` field uses raw Congress.gov titles. CRA resolutions say "Providing for congressional disapproval under chapter 8 of title 5, United States Code..." which tells the reader nothing. AI summaries already have plain-language versions but they aren't used here.

## Solution

Three changes across three layers:

### 1. AI Summary Prompt — Add `one_liner` field

Add a third output field to the AI summary JSON: `one_liner` — a single plain-English phrase (max 15 words) starting with a verb that describes what the bill does. No period.

Examples:
- "Cancel an EPA rule limiting methane fees on oil and gas companies"
- "Set new rules for cryptocurrency trading platforms"
- "Fund the military and set troop pay for 2026"

The `one_liner` follows the same SYSTEM_PROMPT rules (no adjectives, no opinions, no jargon, 7th-8th grade reading level).

Regenerate all 177 AI summaries to include the new field.

### 2. Sync Script — Use AI `one_liner` instead of raw title

In `sync.py` `sync_member_votes()`, when building each vote record:
- Look up the AI summary for the bill by bill key
- If the summary has a `one_liner`, use it
- Otherwise fall back to the raw bill title

### 3. Frontend — Fix "At a Glance" display

In `member.js` `renderVotingSummary()`:
- Change "Most active on" to "Most votes in" — neutral, factual
- Deduplicate "What They Supported" / "What They Opposed" by `bill_id`
- Group votes by bill, keep only the last vote chronologically (final vote)
- Show each bill once in the appropriate list

## Approach Decision

Chose to add a purpose-built `one_liner` field (Approach A) over reusing `provisions[0]` (too long for bullet lists) or regex-matching CRA titles only (band-aid fix that misses other bad titles like reconciliation acts).

## Files Changed

- `app/services/ai_summary.py` — Add `one_liner` to prompt and output parsing
- `sync.py` — Pass AI summaries into `sync_member_votes()`, use `one_liner` for vote records
- `static/js/member.js` — Fix summary text, deduplicate vote lists
- `data/synced/ai_summaries.json` — Regenerated with `one_liner` field
- `data/synced/member_votes/*.json` — Rebuilt with plain-language one_liners
