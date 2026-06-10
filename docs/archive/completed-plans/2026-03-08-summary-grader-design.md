# Summary Grader — Design Document

**Date:** 2026-03-08
**Status:** Approved

## Problem

AI-generated summaries in ClearVote contain quality issues that create misinformation:

1. **Raw legislative titles used as one-liners** — "Providing for congressional disapproval under chapter 8 of title 5, United States Code..." is not 8th grade reading level
2. **CRA disapproval votes misrepresented** — Voting Nay on a disapproval resolution means supporting the underlying regulation, but the system treats it as voting against the policy area (e.g., Gillibrand shown as opposing environmental protection when she's defending EPA rules)
3. **Acronym-only bill names** — "GENIUS Act" tells the reader nothing about what the bill does
4. **Duplicate procedural votes** — same bill appears in both Supported and Opposed lists due to multiple procedural votes (cloture, amendments, passage)
5. **Misleading "At a Glance" text** — "Most active on environmental protection" implies support when the member voted against all disapproval resolutions in that area

## Solution: Writer-Grader Loop

Every piece of AI-generated text goes through a 3-round writer-grader feedback loop before being saved. No exceptions.

### Scope

All AI-generated content in the system:

1. **Bill Summaries** — `provisions` array and `impact_categories` in `ai_summaries.json`
2. **Member Vote One-Liners** — the `one_liner` field in `member_votes/{bioguide}.json`, replacing raw Congress.gov titles with AI-generated plain-language descriptions

### Flow

```
Input Data (bill info OR vote + bill context)
    ↓
[WRITER] — Fresh API call, generates summary
    ↓
[GRADER] — Separate fresh API call, evaluates against quality checklist
    ↓
  Round 1 complete. Grader sends feedback.
    ↓
[WRITER] — New fresh API call with original data + grader feedback
    ↓
[GRADER] — New fresh API call, evaluates revision
    ↓
  Round 2 complete. Grader sends feedback.
    ↓
[WRITER] — New fresh API call with original data + grader feedback
    ↓
[GRADER] — New fresh API call, evaluates revision
    ↓
  Round 3 complete.
    ↓
  Pick highest-scoring version across all 3 rounds.
    ↓
  Highest score is A or B? → Save to output file.
  Highest score is C, D, or F? → Save with "needs_review": true flag.
```

### Key Design Decisions

- **Writer and grader are always separate API calls** — never in the same conversation, context stays clean
- **Grader never rewrites** — it only critiques. The writer does all writing. Prevents the grader from introducing its own bias.
- **Each retry is a fresh writer call** with only the original input data + the grader's specific feedback. No accumulated conversation history.
- **Always 3 rounds** — not "stop at first pass" but "best of 3 improving attempts"
- **Fail = flagged** — if the best of 3 still doesn't pass, save with `needs_review` flag for human review. No silent failures.

### Grader Checklist

**Reading Level**
- Flesch-Kincaid grade level ≤ 8th grade
- No sentences over 25 words
- Common words only — "cuts" not "rescinds", "stops" not "eliminates the provision"

**No Jargon / Legislative Language**
- No "chapter 8 of title 5", "appropriations", "fiscal year", "provisions", "authorizes", "mandates"
- Acronym-only titles flagged — "GENIUS Act" must be expanded and explained in plain English

**Vote Context Accuracy (for one-liners)**
- CRA disapproval resolutions correctly interpreted — voting Nay on a disapproval = supporting the underlying regulation
- The one-liner describes what the vote means, not just the procedural title

**No Bias or Editorial Language**
- No adjectives ("sweeping", "controversial", "landmark")
- No characterizations of intent ("aims to", "seeks to")
- No framing ("generally seen as", "made it easier")

**Factual Context Present**
- Before/after numbers included when a bill changes a cap, fee, or threshold
- Affected population sizes included when publicly known
- Scale references where helpful

**Structural**
- Bill summaries: 3-7 provisions, each a single sentence
- One-liners: single sentence, under 30 words
- Impact categories match the allowed list

**Grading Scale:**
- A — Passes all checks, excellent clarity
- B — Minor issues, still accurate and readable (pass)
- C — Moderate issues, accuracy concerns (fail)
- D — Significant issues, misleading or confusing (fail)
- F — Critical failure, factually wrong or biased (fail)

### Grader Learnings (Continuous Improvement)

After each batch run, the system analyzes grader feedback across all summaries:

- Identifies frequently flagged patterns (e.g., "Writers frequently use 'fiscal year'", "CRA resolutions misinterpreted on first pass")
- Saves new patterns to `data/grader_learnings.json`
- Future writer AND grader prompts load these learnings, so both sides improve over time
- The learnings file becomes a living record of quality standards learned from real data

### Batch Processing

To prevent context degradation:

**Bill Summaries:**
- Batch size: 5 bills per session
- Each batch is fresh API calls — no accumulated context
- Progress saved after each batch (crash-safe, can resume)

**Member Vote One-Liners:**
- Batch size: 1 member at a time
- Within a member, process votes in groups of 10
- Fresh API calls per group

### Integration into Sync Pipeline

**New pipeline (7 steps):**
1. Members
2. Senate votes
3. House votes
4. Bills
5. **Bill summaries** — writer-grader loop for each bill
6. **Member vote records** — cross-reference + writer-grader loop for one-liners
7. **Grader report** — pass/fail counts, grade distribution, flagged items, new learnings

**Commands:**
- `python sync.py --states NY,FL` — full sync with grading built in (always on)
- `python sync.py --grade` — re-grade existing summaries without re-syncing source data

### Batch Run Output

After every run:
- Total summaries processed
- Pass/fail counts and grade distribution (A/B/C/D/F)
- List of `needs_review` flagged items
- New learnings captured (if any)
