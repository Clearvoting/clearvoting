# AI Content Quality System — Writer-Grader Loop for Member Profiles

**Version:** 1.0
**Created:** March 10, 2026
**Status:** Draft — pending review

---

## Context

ClearVote is a government transparency tool. Each member's profile page shows five AI/data-driven sections under "At a Glance": a narrative summary, overview stats, "Where They Focus" direction bars, "What They Supported," and "What They Opposed." These sections are generated independently, and contradictions between them (e.g., narrative highlights environmental votes while the direction bars show mostly *weakening* on environment) destroy credibility. The bill summary pipeline already has a writer-grader loop with learnings — member narratives skip it entirely. Step 8 in `sync.py` is literally a placeholder waiting for this.

## Overview

**Current behavior:**
- Bill summaries go through `WriterGraderLoop` with `SummaryGrader` + `GraderLearnings` (`sync.py:286-417`)
- Member narratives are generated once with no quality check (`sync.py:628-755`)
- `member_summary.py` already accepts `grader_feedback` param but it's never used
- `sync.py:1158` — `# Step 8: Member summary grading (placeholder — not yet implemented)`
- Each section computed independently — no cross-section consistency check
- Learnings system only captures bill summary patterns

**New behavior:**
- Member narratives go through writer-grader loop with a member-specific grader
- Narrative writer receives a "data brief" showing actual strengthen/weaken ratios, preventing cherry-picking
- After all sections are assembled, a page coherence checker flags contradictions between narrative and data
- Learnings system captures patterns across all content types (bills, narratives, coherence)
- All 80 existing narratives regenerated through the new pipeline

## Design Decisions

**Separate `MemberNarrativeGrader` instead of reusing `SummaryGrader`.** The bill grader checks bill-specific things (direction accuracy, CRA vote context, provision structure) that don't apply to narratives. Member narratives need data-alignment checks ("does the narrative match the strengthen/weaken ratios?") that bill summaries don't. Same class pattern, different checklist.

**Inject a "data brief" into the writer prompt rather than just passing raw data.** The current prompt passes `top_areas` with counts, but the LLM sometimes ignores ratios and cherry-picks from sample bills. A computed plain-text brief like "Environment: 3 strengthening, 12 weakening — mostly weakening" as a MANDATORY CONSTRAINT forces alignment. This addresses the root cause.

**Page coherence checker as a separate service, not part of the grader.** The grader checks one piece of text against a quality checklist. Coherence checks consistency *between* multiple sections. Different responsibility, different prompt, different result structure. Lives alongside the grader in `app/services/`.

**One learnings file with content-type sections, not separate files.** Extend `grader_learnings.json` to use content-type keys (`bill_summary`, `member_narrative`, `page_coherence`). Avoids file proliferation. Backward-compatible migration from flat structure on first load.

**Regenerate all 80 narratives.** None were quality-checked. ~560 API calls worst case, ~$2-5 at Sonnet pricing. The `--regenerate-member-summaries` flag already exists.

---

## Phase 1: Member Narrative Grader + Writer-Grader Loop Wiring

**Completion gate:** `sync_member_summaries` uses `WriterGraderLoop` with the new grader. Tests pass.

### 1.1 Create `app/services/member_narrative_grader.py`

Follow `summary_grader.py` pattern. Same class structure (`grade()` method returning `GradeResult`), different checklist:

- **Reading level**: 7th-8th grade, no sentences over 25 words
- **No bias**: No adjectives, intent characterization, political framing (same rules as bill grader)
- **Data alignment** (NEW): If the narrative mentions a policy area, characterization must match the strengthen/weaken ratio in the grader context. E.g., if Environment is 3 strengthen / 12 weaken, narrative cannot imply the member supports environmental protections.
- **No cherry-picking** (NEW): Narrative must not highlight exceptions as if they are the pattern
- **Structure**: 3-5 sentences, includes specific numbers (vote counts, participation rate)
- **Completeness**: Must mention top 2-3 policy areas by vote count

Grader context receives: `top_areas` with direction counts, `stats`, `top_supported`, `top_opposed`.

### 1.2 Wire up `WriterGraderLoop` in `sync.py` `sync_member_summaries`

Modify `sync.py:628-755`. Follow the exact pattern from `sync_bill_summaries` (lines 286-417):
- Import `MemberNarrativeGrader`, `WriterGraderLoop`, `GraderLearnings`
- Create grader instance, load learnings
- Wrap `service.generate_member_summary()` as `writer_fn`
- Run `WriterGraderLoop.run()` for each member
- Track stats, extract patterns, record batch, save learnings

### 1.3 Tests

- `tests/test_member_narrative_grader.py` — Mock LLM. Test: data-aligned narrative passes, narrative contradicting data fails with specific feedback, cherry-picking detected.

---

## Phase 2: Enhanced Data Brief for Narrative Writer

**Completion gate:** `member_summary.py` prompt includes computed data constraints. Writer output aligns with data. Tests pass.

### 2.1 Add `_compute_data_brief()` to `app/services/member_summary.py`

Takes `top_areas` list, returns plain-text block:
```
DATA CONSTRAINTS (your narrative MUST align with these patterns):
- Economics and Public Finance: 80 strengthening, 64 weakening — leans strengthening
- Environment: 3 strengthening, 12 weakening — mostly weakening
```

Classification: >=75% one direction = "mostly X", 55-74% = "leans X", else "mixed"

### 2.2 Update `_build_prompt()` in `member_summary.py`

Insert data brief after the Top Policy Areas section. Add system prompt rule: "Your narrative MUST reflect the dominant direction shown in DATA CONSTRAINTS. Do NOT highlight exceptions as if they represent the overall pattern."

### 2.3 Tests

- Update `tests/test_member_summary.py` — Test `_compute_data_brief` output for various ratios. Verify prompt includes "DATA CONSTRAINTS".

---

## Phase 3: Page Coherence Checker

**Completion gate:** Coherence checker identifies contradictions between narrative and data sections. Integrated into sync pipeline as Step 8. Tests pass.

### 3.1 Create `app/services/page_coherence.py`

```python
@dataclass
class CoherenceResult:
    is_coherent: bool
    contradictions: list[str]
    guidance: str  # regeneration instructions if not coherent
```

Prompt sends all 5 sections' data to Claude and asks: "Do these sections tell a consistent story? Identify contradictions." Structured comparison, not creative writing.

### 3.2 Add `check_page_coherence()` to `sync.py`

New function, becomes Step 8 in the pipeline. For each member:
1. Assemble narrative + stats + top_areas + supported/opposed bills (same data the frontend renders)
2. Run coherence check
3. If contradictions found: regenerate narrative with `grader_feedback` = coherence `guidance`, max 2 rounds
4. Save updated narrative

Add `--check-coherence` CLI flag for standalone runs.

Update pipeline:
```python
# Step 8: Page coherence check
print("[8/9] Checking page coherence...")
await check_page_coherence(SYNC_DIR, api_key=anthropic_key or None)
```

### 3.3 Tests

- `tests/test_page_coherence.py` — Mock LLM. Test: coherent page passes, contradictory narrative+data fails with specific contradictions listed.

---

## Phase 4: Extended Learnings System

**Completion gate:** Learnings scoped by content type. Migration from flat format works. All three pipelines (bills, narratives, coherence) write learnings. Tests pass.

### 4.1 Modify `app/services/grader_learnings.py`

Add `content_type` parameter to all methods:
- `get_learnings(content_type: str)` / `add_learning(content_type: str, ...)`
- `record_batch(content_type: str, ...)` / `extract_patterns(content_type: str, ...)`

Data structure:
```json
{
  "bill_summary": { "learnings": [], "batch_history": [] },
  "member_narrative": { "learnings": [], "batch_history": [] },
  "page_coherence": { "learnings": [], "batch_history": [] }
}
```

Migration on `_load()`: if file has flat `{"learnings": [...], "batch_history": [...]}`, move to `"bill_summary"` key.

### 4.2 Update callers in `sync.py`

- `sync_bill_summaries`: pass `content_type="bill_summary"` to learnings calls
- `sync_member_summaries`: pass `content_type="member_narrative"`
- `check_page_coherence`: pass `content_type="page_coherence"`

### 4.3 Load learnings into member narrative grader and coherence checker

Same pattern as `SummaryGrader.load_learnings()` — inject into system prompt as "LEARNED PATTERNS."

### 4.4 Tests

- Update `tests/test_grader_learnings.py` — Test content-type scoping, flat→nested migration, backward compatibility.

---

## Phase 5: Regenerate All Members and Validate

**Completion gate:** All 80 members pass through new pipeline. Stats reported. Before/after comparison for known issues.

### 5.1 Update `--regenerate-member-summaries` in `sync.py`

Enhance to use full pipeline: writer-grader loop per narrative, then coherence check. Print stats: pass rate, common failures, coherence contradictions.

### 5.2 Run regeneration

```bash
cd ~/Documents/Claude/Projects/clearvote
source .venv/bin/activate
python sync.py --regenerate-member-summaries
python sync.py --check-coherence
```

Review output stats and spot-check a few member narratives.

---

## Files Touched

| File | Change |
|------|--------|
| `app/services/member_narrative_grader.py` | **Create** — Member-specific grader with data-alignment checks |
| `app/services/page_coherence.py` | **Create** — Cross-section consistency checker |
| `app/services/member_summary.py` | Modify — Add `_compute_data_brief()`, update prompt with data constraints |
| `app/services/grader_learnings.py` | Modify — Content-type scoping, flat→nested migration |
| `sync.py` | Modify — Wire writer-grader loop, add Step 8 coherence check, update learnings calls |
| `tests/test_member_narrative_grader.py` | **Create** |
| `tests/test_page_coherence.py` | **Create** |
| `tests/test_member_summary.py` | Modify — Data brief tests |
| `tests/test_grader_learnings.py` | Modify — Content-type scoping tests |

**Untouched:** `writer_grader_loop.py` (reusable as-is), `summary_grader.py` (bill-specific, stays), `member.js` (frontend renders whatever is in the JSON — improving data quality upstream fixes the display automatically), API routers.

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_member_narrative_grader.py` | Data alignment detection, cherry-pick detection, bias detection |
| Unit | `test_page_coherence.py` | Contradiction detection between sections, coherent pages pass |
| Unit | `test_member_summary.py` | Data brief computation, prompt includes constraints |
| Unit | `test_grader_learnings.py` | Content-type scoping, flat→nested migration |
| Integration | Regeneration run | All 80 members through full pipeline, stats review |

## Verification

1. Run existing tests: `cd ~/Documents/Claude/Projects/clearvote && source .venv/bin/activate && pytest`
2. Run regeneration: `python sync.py --regenerate-member-summaries`
3. Run coherence check: `python sync.py --check-coherence`
4. Spot-check 3-5 member pages in browser: `python app.py` → http://127.0.0.1:8001 → click member profiles
5. Verify narrative aligns with "Where They Focus" direction bars and supported/opposed lists

## Not In Scope

- **Frontend changes** — the frontend already renders whatever data is in the JSON files; fixing upstream quality fixes the display
- **Bill summary grader changes** — already working well (449/459 passing)
- **New API endpoints** — quality checks run during sync, not at request time
- **Grader UI/dashboard** — stats are logged to console during sync runs
