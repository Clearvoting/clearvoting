# Follow-up: Campaign Finance Improvements

## 1. Fix FEC Candidate Matching (Quick Win)

**Problem:** The sync uses last-name-only search against the FEC API, which returns wrong matches for ambiguous names (Scott → "Brent Scott Mack" instead of Rick Scott). 28 of 80 members failed during the initial sync.

**Fix:** Use full name (first + last) in the FEC search query. The members.json has "Last, First" format — extract both and pass to the API. May also need to add retry logic with backoff for 429s.

**Impact:** Would bring coverage from 51/80 to ~70+/80.

## 2. Upgrade Data Source — Three Options

### Option A: OpenSecrets Bulk Data (Recommended)

**Status:** The OpenSecrets API was shut down April 2025. Bulk data downloads are still available for educational/research use.

**Why it's the best data:**
- Standardizes employer names (Google LLC + Google Inc + Alphabet → Google)
- Industry/sector classification for every donor
- Combines PAC money + individual employee donations per organization
- Tracks dark money / outside spending (501c4s, Super PACs)
- Historical data going back decades with consistent categorization

**Access process:**
1. Sign up at opensecrets.org/open-data/bulk-data
2. Agree to Terms of Service
3. Register for a Bulk Data account (use .edu email if possible)
4. Wait for approval — ClearVote should qualify as civic/educational

**License: CC BY-NC-SA 3.0**
- Must credit "OpenSecrets" near any data citation
- Must link to opensecrets.org when data appears online
- Must include as source line under charts and graphs
- Non-commercial use only (ClearVote qualifies)
- Derivative works must use the same license

**Format:** Compressed CSV files with data dictionaries.

**Action items:**
- [ ] Apply for bulk data access at opensecrets.org/open-data/bulk-data
- [ ] Once approved, download contributor and industry tables
- [ ] Build import script to load CSVs into data/synced/donations.json format
- [ ] Add OpenSecrets attribution to Campaign Finance tab (required by license)

### Option B: Stay with FEC API (Current)

- Completely free, no restrictions, no approval needed
- Already integrated and working (51/80 members)
- Raw data — messy employer names, no industry coding, no PAC+individual bundling
- Fix the name matching issue (#1 above) to improve coverage

### Option C: ProPublica Campaign Finance API

- Free, pre-processed FEC data (updated daily, electronic filings every 15 min)
- Also has a Congress API (bills, votes, nominations) that could supplement ClearVote
- Need to email apihelp@propublica.org for API key
- 5,000 requests/day limit
- Less rich than OpenSecrets but better than raw FEC

## 3. Current State (as of 2026-03-19)

- FEC_API_KEY configured in .env
- 51/80 members have donation data in data/synced/donations.json
- Campaign Finance tab is live on member pages
- sync_donations() in sync.py handles incremental sync (re-running picks up where it left off)
- 28 failures: ~15 wrong FEC matches (ambiguous names), ~8 committee 404s (no 2024 data), ~5 rate-limited

## OpenSecrets Application (Submitted 2026-03-19)

**Project description submitted for bulk data access:**

> ClearVote (https://clearvoting.org) is a free, nonpartisan civic transparency tool that makes congressional voting records accessible to everyday citizens. The project pulls data from official government sources — Congress.gov, the Senate, and the House Clerk — and presents it in plain language so voters can see exactly how their representatives vote on the issues that matter to them.
>
> The platform currently covers representatives from New York, Florida, California, and Texas across the 117th through 119th Congresses. Each member profile includes AI-generated plain-language bill summaries, voting pattern analysis, sponsored legislation, and an "At a Glance" narrative that summarizes a representative's record without editorial framing. Party affiliations are hidden by default to encourage voters to evaluate representatives on their actions rather than their labels.
>
> We are building a Campaign Finance section to show voters who funds their representatives. We currently use the FEC API for contribution data, but the information is limited — raw filings lack standardized employer names, industry classification, and bundled PAC-plus-individual totals that give voters the full picture. OpenSecrets' enriched data would allow us to show meaningful contributor and industry breakdowns that connect the money to the votes.
>
> ClearVote is an open-source, non-commercial educational project. All OpenSecrets data would be credited prominently with source attribution on every page where it appears, in compliance with the CC BY-NC-SA 3.0 license. The goal is simple: give citizens the facts they need to make more informed voting decisions and hold their representatives accountable.

## Recommended Path

1. **Now:** Fix FEC name matching (#1) to get to ~70+ members with current data
2. **Soon:** Apply for OpenSecrets bulk data access
3. **Once approved:** Import OpenSecrets data, add attribution, replace FEC data for richer display
4. **Keep FEC as fallback** for any members OpenSecrets doesn't cover
