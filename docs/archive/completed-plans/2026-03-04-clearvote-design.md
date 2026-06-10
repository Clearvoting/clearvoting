# ClearVote — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Author:** Joseph Garcia + Claude

## Problem Statement

There is a lack of transparency in how U.S. Congress members vote on bills. Existing tools either editorialize, use subjective language, or present data in ways that are inaccessible to the average citizen. ClearVote addresses this by presenting only facts — what bills do, how representatives voted — in plain language, without bias.

## Mission

Enable citizens to hold their elected leaders accountable by providing unbiased, factual, plain-language access to congressional voting records.

## Core Principles

1. **No bias** — no adjectives, no opinion, no characterization of outcomes as positive/negative
2. **Plain language** — bill mechanisms explained in terms a working-class American would understand
3. **Facts first, party second** — party affiliation hidden by default; users see votes on merit before optionally revealing party lines
4. **No scoring or ranking** — representatives are not graded, rated, or compared

## Target Audience

General public — anyone who wants to understand what Congress is doing and how their representatives are voting.

## Core Experience

### Landing Page
- User enters zip code or state
- App shows their specific representatives (House + Senate) and recent votes
- Clean, accessible, no clutter

### Representative Profile
- Name, state, district, photo (from Congress.gov)
- Full voting record — each vote links to bill detail
- Party affiliation hidden by default — toggle button reveals it
- No scores, ratings, or rankings

### Bill Detail Page
- Official title and bill number
- Official Congress summary (directly from Congress.gov)
- **"What This Bill Does"** — AI-generated plain-language bullet points:
  - Key provisions extracted from bill text
  - Mechanisms only (dollar amounts, thresholds, rule changes)
  - No adjectives, no value judgments
- **Impact categories** — standardized tags:
  - Wages & Income, Healthcare, Small Business, Housing, Education, Taxes, Military/Veterans, Agriculture, Environment, Immigration, Criminal Justice, Technology, Infrastructure, Social Security/Medicare
- **Vote results** — full roll call (Yea/Nay/Not Voting/Present)
- Party affiliation toggle (hidden by default)

### Search & Browse
- Search by bill number, keyword, or topic
- Browse by impact category
- Browse by recent activity
- Filter votes by chamber (House/Senate)

## No-Bias Guardrails

1. AI bill summaries use strict prompting: extract mechanisms only, no adjectives, no characterization
2. Official Congress summary always shown alongside AI summary for transparency
3. No color-coding that implies judgment (no red/green on votes — use neutral colors)
4. No ranking, scoring, or grading of representatives
5. Party affiliation hidden by default across all views
6. Source attribution on all data (link back to Congress.gov)

## Technical Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | Pure HTML/CSS/JS (no frameworks) |
| Backend | Python + FastAPI |
| Data Source | Congress.gov API (free, official) |
| AI Summaries | Claude API (Anthropic) |
| Caching | Flat-file JSON |
| Styling | Dark theme — midnight blue (#0C1B33) + gold (#D4A853) |

## Data Flow

1. Congress.gov API provides bills, votes, members, and roll call data
2. FastAPI backend fetches and caches responses as JSON files
3. Claude API generates plain-language bill breakdowns on first request; results cached
4. Frontend requests data from FastAPI endpoints, renders client-side
5. Cache refreshes periodically (configurable interval)

## API Data Sources

- **Members:** `/member` endpoint — name, state, district, party, photo
- **Bills:** `/bill` endpoint — title, summary, full text, sponsors, status
- **Votes:** `/vote` endpoint — roll call votes by chamber and session
- **Member lookup by state/district:** Congress.gov member search

## Future Expansion

- Local government voting records (state legislature, city council)
- Architecture designed to be data-source-agnostic — frontend components work with any legislative body
- Notification system (get alerts when your reps vote)
- Shareable bill/vote links for social media

## Design Notes

- Same palette as Joe's Conduction projects (midnight blue + gold + warm off-white)
- Mobile-first responsive design
- Accessible (WCAG AA compliance, semantic HTML, keyboard navigation)
- No login required — fully public
