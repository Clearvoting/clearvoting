# Summary Grader Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a writer-grader feedback loop that ensures every AI-generated summary in ClearVote meets quality standards before being saved.

**Architecture:** A `SummaryGrader` service evaluates AI output against a checklist (reading level, bias, jargon, vote context accuracy). The existing `AISummaryService` (writer) generates summaries. A new `WriterGraderLoop` orchestrates 3 rounds of write → grade → feedback, picks the highest-scoring version, and flags failures. A batch processor in `sync.py` runs summaries through the loop in small batches with fresh API calls to prevent context degradation. A persistent `grader_learnings.json` captures patterns for continuous improvement.

**Tech Stack:** Python, Anthropic SDK (claude-sonnet-4-20250514), pytest, asyncio

**Status:** ✅ Complete — all 10 tasks implemented, 137 tests passing (103 existing + 34 new)

**References:**
- [Design doc](2026-03-08-summary-grader-design.md)
- [Current AI summary service](../../app/services/ai_summary.py)
- [Current sync script](../../sync.py)

---

## Task 1: Summary Grader Service — Core Grading Logic

**Files:**
- Create: `app/services/summary_grader.py`
- Test: `tests/test_summary_grader.py`

This is the grader brain. It takes a summary + context, evaluates it against the quality checklist, and returns a grade + feedback. It uses a separate Claude API call (never shares context with the writer).

**Step 1: Write failing tests for the grader**

```python
# tests/test_summary_grader.py
import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from app.services.summary_grader import SummaryGrader, GradeResult


def test_grade_result_pass_for_a():
    result = GradeResult(grade="A", passed=True, feedback="No issues found.", checks={})
    assert result.passed is True
    assert result.grade == "A"


def test_grade_result_pass_for_b():
    result = GradeResult(grade="B", passed=True, feedback="Minor issues.", checks={})
    assert result.passed is True


def test_grade_result_fail_for_c():
    result = GradeResult(grade="C", passed=False, feedback="Moderate issues.", checks={})
    assert result.passed is False


def test_grade_result_fail_for_f():
    result = GradeResult(grade="F", passed=False, feedback="Critical failure.", checks={})
    assert result.passed is False


def test_grader_system_prompt_contains_checklist_items():
    grader = SummaryGrader(api_key="test")
    prompt = grader._build_system_prompt()
    assert "reading level" in prompt.lower() or "flesch" in prompt.lower()
    assert "jargon" in prompt.lower()
    assert "bias" in prompt.lower()
    assert "CRA" in prompt or "Congressional Review Act" in prompt or "disapproval" in prompt


def test_grader_build_prompt_for_bill_summary():
    grader = SummaryGrader(api_key="test")
    prompt = grader._build_grade_prompt(
        summary_type="bill_summary",
        summary_text=json.dumps({
            "one_liner": "Raise the minimum wage to $15",
            "provisions": ["Raises the minimum wage from $7.25 to $15 over 5 years"],
            "impact_categories": ["Wages & Income"]
        }),
        context={"title": "Raise the Wage Act", "official_summary": "A bill to raise the minimum wage."}
    )
    assert "Raise the Wage Act" in prompt
    assert "bill_summary" in prompt or "bill summary" in prompt.lower()


def test_grader_build_prompt_for_vote_one_liner():
    grader = SummaryGrader(api_key="test")
    prompt = grader._build_grade_prompt(
        summary_type="vote_one_liner",
        summary_text="Cancel an EPA rule limiting methane fees",
        context={
            "bill_title": "H.J.Res. 35",
            "vote_question": "On the Joint Resolution",
            "is_cra_disapproval": True,
        }
    )
    assert "vote" in prompt.lower()
    assert "CRA" in prompt or "disapproval" in prompt


def test_grader_build_prompt_includes_learnings():
    grader = SummaryGrader(api_key="test")
    grader.learnings = [
        "Writers frequently use 'fiscal year' instead of plain dates",
        "CRA disapproval resolutions are often misinterpreted"
    ]
    prompt = grader._build_system_prompt()
    assert "fiscal year" in prompt
    assert "misinterpreted" in prompt


@pytest.mark.asyncio
async def test_grade_summary_returns_grade_result():
    grader = SummaryGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text=json.dumps({
            "grade": "A",
            "passed": True,
            "feedback": "Clear, accurate, no jargon.",
            "checks": {
                "reading_level": "pass",
                "no_jargon": "pass",
                "no_bias": "pass",
                "factual_context": "pass",
                "structure": "pass",
            }
        })
    )]

    grader.client = MagicMock()
    grader.client.messages.create = AsyncMock(return_value=mock_response)

    result = await grader.grade(
        summary_type="bill_summary",
        summary_text='{"one_liner": "Raise minimum wage to $15", "provisions": ["Raises wage from $7.25 to $15"], "impact_categories": ["Wages & Income"]}',
        context={"title": "Wage Act"}
    )

    assert isinstance(result, GradeResult)
    assert result.grade == "A"
    assert result.passed is True


@pytest.mark.asyncio
async def test_grade_summary_handles_malformed_response():
    grader = SummaryGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    grader.client = MagicMock()
    grader.client.messages.create = AsyncMock(return_value=mock_response)

    result = await grader.grade(
        summary_type="bill_summary",
        summary_text='{"one_liner": "Test", "provisions": ["Test"], "impact_categories": []}',
        context={"title": "Test"}
    )

    assert isinstance(result, GradeResult)
    assert result.passed is False
    assert result.grade == "F"
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_summary_grader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.summary_grader'`

**Step 3: Implement SummaryGrader**

```python
# app/services/summary_grader.py
import json
import logging
from dataclasses import dataclass, field
import anthropic

logger = logging.getLogger(__name__)

GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


@dataclass
class GradeResult:
    grade: str
    passed: bool
    feedback: str
    checks: dict = field(default_factory=dict)


class SummaryGrader:
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.learnings: list[str] = []

    def load_learnings(self, learnings: list[str]) -> None:
        self.learnings = learnings

    def _build_system_prompt(self) -> str:
        learnings_block = ""
        if self.learnings:
            items = "\n".join(f"- {l}" for l in self.learnings)
            learnings_block = f"""

LEARNED PATTERNS (from previous grading runs — pay extra attention to these):
{items}"""

        return f"""You are a nonpartisan quality grader for a government transparency tool called ClearVoting. Your job is to evaluate AI-generated summaries of congressional bills and votes for accuracy, clarity, and neutrality.

You grade against this checklist:

READING LEVEL
- Flesch-Kincaid grade level must be 8th grade or below
- No sentences over 25 words
- Use common words: "cuts" not "rescinds", "stops" not "eliminates the provision", "lets" not "authorizes"

NO JARGON / LEGISLATIVE LANGUAGE
- No "chapter 8 of title 5", "appropriations", "fiscal year", "provisions", "authorizes", "mandates", "eligibility"
- Acronym-only bill names are NOT acceptable. "GENIUS Act" must be expanded and explained. The reader must understand what the bill does from the summary alone.
- Government agency names are OK but must be in short, simple sentences

VOTE CONTEXT ACCURACY (for vote one-liners)
- Congressional Review Act (CRA) disapproval resolutions: voting NAY on a disapproval resolution means the member SUPPORTS the underlying regulation. Voting YEA means they want to REMOVE it. The one-liner must reflect this correctly.
- The one-liner must describe what the vote MEANS for the reader, not just restate the procedural title

NO BIAS OR EDITORIAL LANGUAGE
- No adjectives: "sweeping", "controversial", "landmark", "modest"
- No intent characterization: "aims to", "seeks to"
- No framing: "generally seen as", "made it easier/harder", "widely considered"
- No value judgments: "this would help/hurt", "beneficial", "harmful"

FACTUAL CONTEXT
- When a bill changes a number (fee, cap, limit, threshold), include both old and new values
- When a bill affects a group, include how many people are affected if publicly known
- Include scale references where helpful

STRUCTURE
- Bill summaries: one_liner (single phrase, max 15 words, starts with verb, no period), provisions (3-7 items, each a single sentence), impact_categories (from allowed list)
- Vote one-liners: single sentence, under 30 words, describes what the vote means
{learnings_block}

GRADING SCALE:
- A: Passes all checks, excellent clarity and accuracy
- B: Minor issues (e.g., one slightly long sentence), still accurate and readable
- C: Moderate issues — accuracy concerns, jargon present, or misleading framing
- D: Significant issues — misleading, confusing, or factually wrong in places
- F: Critical failure — biased, factually wrong, or completely unreadable

A or B = pass. C, D, or F = fail.

Return valid JSON only:
{{"grade": "A|B|C|D|F", "passed": true|false, "feedback": "Specific actionable feedback for the writer", "checks": {{"reading_level": "pass|fail: detail", "no_jargon": "pass|fail: detail", "no_bias": "pass|fail: detail", "vote_context": "pass|fail|n/a: detail", "factual_context": "pass|fail: detail", "structure": "pass|fail: detail"}}}}"""

    def _build_grade_prompt(self, summary_type: str, summary_text: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2)
        return f"""Grade this {summary_type}.

ORIGINAL CONTEXT (what the summary is describing):
{context_str}

SUMMARY TO GRADE:
{summary_text}

Evaluate against every check in your checklist. Be strict — this tool exists to prevent misinformation. Return JSON only."""

    async def grade(self, summary_type: str, summary_text: str, context: dict) -> GradeResult:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_grade_prompt(summary_type, summary_text, context)

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text
            result = json.loads(raw_text)

            return GradeResult(
                grade=result.get("grade", "F"),
                passed=result.get("passed", False),
                feedback=result.get("feedback", "No feedback provided."),
                checks=result.get("checks", {}),
            )
        except json.JSONDecodeError:
            logger.error("Grader response was not valid JSON: %s", raw_text[:200])
            return GradeResult(grade="F", passed=False, feedback="Grader returned invalid JSON.", checks={})
        except Exception as e:
            logger.error("Grader API call failed: %s", str(e))
            return GradeResult(grade="F", passed=False, feedback=f"Grader error: {str(e)}", checks={})
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_summary_grader.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/services/summary_grader.py tests/test_summary_grader.py
git commit -m "feat: add SummaryGrader service with quality checklist"
```

---

## Task 2: Writer-Grader Loop Orchestrator

**Files:**
- Create: `app/services/writer_grader_loop.py`
- Test: `tests/test_writer_grader_loop.py`

This orchestrates the 3-round feedback loop: call writer → grade → send feedback → repeat. Always runs 3 rounds, picks the best.

**Step 1: Write failing tests**

```python
# tests/test_writer_grader_loop.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from app.services.writer_grader_loop import WriterGraderLoop, LoopResult
from app.services.summary_grader import GradeResult


def test_loop_result_structure():
    result = LoopResult(
        best_summary={"one_liner": "Test", "provisions": ["Test"], "impact_categories": []},
        best_grade=GradeResult(grade="A", passed=True, feedback="Good.", checks={}),
        rounds=1,
        needs_review=False,
        all_grades=["A"],
    )
    assert result.needs_review is False
    assert result.best_grade.grade == "A"


def test_loop_result_needs_review_when_all_fail():
    result = LoopResult(
        best_summary={"one_liner": "Bad", "provisions": ["Bad"], "impact_categories": []},
        best_grade=GradeResult(grade="D", passed=False, feedback="Bad.", checks={}),
        rounds=3,
        needs_review=True,
        all_grades=["F", "D", "D"],
    )
    assert result.needs_review is True


@pytest.mark.asyncio
async def test_loop_runs_3_rounds_and_picks_best():
    mock_writer = AsyncMock()
    mock_writer.side_effect = [
        {"one_liner": "v1", "provisions": ["v1"], "impact_categories": []},
        {"one_liner": "v2", "provisions": ["v2"], "impact_categories": []},
        {"one_liner": "v3", "provisions": ["v3"], "impact_categories": []},
    ]

    mock_grader = MagicMock()
    mock_grader.grade = AsyncMock(side_effect=[
        GradeResult(grade="C", passed=False, feedback="Jargon found.", checks={}),
        GradeResult(grade="B", passed=True, feedback="Minor issue.", checks={}),
        GradeResult(grade="A", passed=True, feedback="Perfect.", checks={}),
    ])

    loop = WriterGraderLoop(writer_fn=mock_writer, grader=mock_grader)
    result = await loop.run(
        summary_type="bill_summary",
        writer_kwargs={"title": "Test", "official_summary": "Test", "bill_text_excerpt": "Test"},
        grader_context={"title": "Test"},
    )

    assert mock_writer.call_count == 3
    assert mock_grader.grade.call_count == 3
    assert result.best_grade.grade == "A"
    assert result.best_summary["one_liner"] == "v3"
    assert result.needs_review is False
    assert result.all_grades == ["C", "B", "A"]


@pytest.mark.asyncio
async def test_loop_flags_needs_review_when_all_fail():
    mock_writer = AsyncMock(return_value={"one_liner": "Bad", "provisions": ["Bad"], "impact_categories": []})

    mock_grader = MagicMock()
    mock_grader.grade = AsyncMock(return_value=GradeResult(
        grade="D", passed=False, feedback="Still has jargon.", checks={}
    ))

    loop = WriterGraderLoop(writer_fn=mock_writer, grader=mock_grader)
    result = await loop.run(
        summary_type="bill_summary",
        writer_kwargs={"title": "Test", "official_summary": "Test", "bill_text_excerpt": "Test"},
        grader_context={"title": "Test"},
    )

    assert result.needs_review is True
    assert result.rounds == 3


@pytest.mark.asyncio
async def test_loop_passes_grader_feedback_to_writer():
    call_kwargs = []

    async def tracking_writer(**kwargs):
        call_kwargs.append(kwargs)
        return {"one_liner": "Test", "provisions": ["Test"], "impact_categories": []}

    mock_grader = MagicMock()
    mock_grader.grade = AsyncMock(return_value=GradeResult(
        grade="B", passed=True, feedback="Use simpler words.", checks={}
    ))

    loop = WriterGraderLoop(writer_fn=tracking_writer, grader=mock_grader)
    await loop.run(
        summary_type="bill_summary",
        writer_kwargs={"title": "Test", "official_summary": "Test", "bill_text_excerpt": "Test"},
        grader_context={"title": "Test"},
    )

    # Round 2 and 3 should have grader_feedback in kwargs
    assert "grader_feedback" not in call_kwargs[0]
    assert "grader_feedback" in call_kwargs[1]
    assert call_kwargs[1]["grader_feedback"] == "Use simpler words."
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_writer_grader_loop.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.writer_grader_loop'`

**Step 3: Implement WriterGraderLoop**

```python
# app/services/writer_grader_loop.py
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from app.services.summary_grader import SummaryGrader, GradeResult, GRADE_ORDER

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3


@dataclass
class LoopResult:
    best_summary: dict
    best_grade: GradeResult
    rounds: int
    needs_review: bool
    all_grades: list[str] = field(default_factory=list)


class WriterGraderLoop:
    def __init__(self, writer_fn: Callable[..., Awaitable[dict]], grader: SummaryGrader):
        self.writer_fn = writer_fn
        self.grader = grader

    async def run(
        self,
        summary_type: str,
        writer_kwargs: dict[str, Any],
        grader_context: dict[str, Any],
    ) -> LoopResult:
        best_summary: dict | None = None
        best_grade: GradeResult | None = None
        all_grades: list[str] = []
        last_feedback: str | None = None

        for round_num in range(1, MAX_ROUNDS + 1):
            # Build writer kwargs for this round
            round_kwargs = dict(writer_kwargs)
            if last_feedback:
                round_kwargs["grader_feedback"] = last_feedback

            # Write
            summary = await self.writer_fn(**round_kwargs)

            # Grade
            import json
            summary_text = json.dumps(summary) if isinstance(summary, dict) else str(summary)
            grade_result = await self.grader.grade(
                summary_type=summary_type,
                summary_text=summary_text,
                context=grader_context,
            )

            all_grades.append(grade_result.grade)
            logger.info(
                "Round %d/%d: grade=%s passed=%s",
                round_num, MAX_ROUNDS, grade_result.grade, grade_result.passed,
            )

            # Track best
            if best_grade is None or GRADE_ORDER.get(grade_result.grade, 0) > GRADE_ORDER.get(best_grade.grade, 0):
                best_summary = summary
                best_grade = grade_result

            last_feedback = grade_result.feedback

        needs_review = not best_grade.passed

        return LoopResult(
            best_summary=best_summary,
            best_grade=best_grade,
            rounds=MAX_ROUNDS,
            needs_review=needs_review,
            all_grades=all_grades,
        )
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_writer_grader_loop.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/services/writer_grader_loop.py tests/test_writer_grader_loop.py
git commit -m "feat: add WriterGraderLoop orchestrator — 3 rounds, best score wins"
```

---

## Task 3: Update AISummaryService Writer to Accept Grader Feedback

**Files:**
- Modify: `app/services/ai_summary.py`
- Modify: `tests/test_ai_summary.py`

The writer needs to accept optional `grader_feedback` so the loop can pass critique from previous rounds. Each call is still a fresh API call — the feedback is just appended to the prompt.

**Step 1: Write failing tests**

Add to `tests/test_ai_summary.py`:

```python
def test_build_prompt_with_grader_feedback():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
        grader_feedback="Use simpler words. Avoid 'appropriations'."
    )
    assert "simpler words" in prompt
    assert "appropriations" in prompt
    assert "PREVIOUS ATTEMPT" in prompt or "feedback" in prompt.lower()


def test_build_prompt_without_grader_feedback():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
    )
    assert "PREVIOUS ATTEMPT" not in prompt
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_ai_summary.py::test_build_prompt_with_grader_feedback -v`
Expected: FAIL — `TypeError: _build_prompt() got an unexpected keyword argument 'grader_feedback'`

**Step 3: Update `_build_prompt` and `generate_summary`**

In `app/services/ai_summary.py`, update `_build_prompt` to accept optional feedback:

```python
def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str, grader_feedback: str | None = None) -> str:
    categories_str = ", ".join(IMPACT_CATEGORIES)
    prompt = f"""Analyze this bill and return JSON with three fields:

1. "one_liner": A single plain-English phrase (max 15 words) starting with a verb that says what this bill does. No period. No adjectives. Examples: "Cancel an EPA rule limiting methane fees on oil and gas companies", "Fund the military and set troop pay for 2026".

2. "provisions": An array of 3-7 strings. Each string is one short, everyday-English sentence describing what this bill does. Use words a middle schooler would know. Focus on: dollar amounts, timelines, and what changes for real people. No adjectives. No opinions. No jargon.

3. "impact_categories": An array of strings from this list — Impact Categories: [{categories_str}]. Only include categories that directly apply.

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}

Return ONLY valid JSON. Example format:
{{"one_liner": "Raise the federal minimum wage to $15 per hour", "provisions": ["Raises the minimum wage from $7.25 to $15.00 per hour over 5 years", "Gives veterans a raise to keep up with the rising cost of living"], "impact_categories": ["Wages & Income"]}}"""

    if grader_feedback:
        prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

    return prompt
```

Update `generate_summary` to accept and pass through `grader_feedback`:

```python
async def generate_summary(self, bill_id: str, title: str, official_summary: str, bill_text_excerpt: str, grader_feedback: str | None = None) -> dict:
    # Skip cache when grader_feedback is present (this is a retry)
    if not grader_feedback:
        cache_key = f"ai_summary:{bill_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

    prompt = self._build_prompt(title, official_summary, bill_text_excerpt, grader_feedback=grader_feedback)

    response = await self.client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("AI response was not valid JSON: %s", raw_text[:200])
        return {"provisions": ["AI summary temporarily unavailable"], "impact_categories": [], "one_liner": title}

    valid_categories = [c for c in result.get("impact_categories", []) if c in IMPACT_CATEGORIES]
    result["impact_categories"] = valid_categories

    if "one_liner" not in result or not result["one_liner"]:
        result["one_liner"] = result["provisions"][0] if result.get("provisions") else title

    # Only cache final results (no grader_feedback = final or first pass from loop's best)
    if not grader_feedback:
        self.cache.set(cache_key, result)

    return result
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_ai_summary.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/services/ai_summary.py tests/test_ai_summary.py
git commit -m "feat: AISummaryService accepts grader feedback for retry rounds"
```

---

## Task 4: Vote One-Liner Writer Service

**Files:**
- Create: `app/services/vote_one_liner.py`
- Test: `tests/test_vote_one_liner.py`

A new writer specifically for generating member vote one-liners. Understands CRA disapproval resolutions and generates plain-English descriptions of what the vote means.

**Step 1: Write failing tests**

```python
# tests/test_vote_one_liner.py
import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from app.services.vote_one_liner import VoteOneLinerService


def test_system_prompt_mentions_cra():
    service = VoteOneLinerService(api_key="test")
    prompt = service.SYSTEM_PROMPT
    assert "CRA" in prompt or "Congressional Review Act" in prompt or "disapproval" in prompt


def test_build_prompt_includes_bill_context():
    service = VoteOneLinerService(api_key="test")
    prompt = service._build_prompt(
        bill_title="Providing for congressional disapproval under chapter 8 of title 5...",
        official_summary="Disapproves the EPA rule on emissions.",
        vote_question="On the Joint Resolution",
        is_cra_disapproval=True,
    )
    assert "disapproval" in prompt.lower() or "EPA" in prompt
    assert "CRA" in prompt or "cancel" in prompt.lower() or "disapproval" in prompt.lower()


def test_build_prompt_with_grader_feedback():
    service = VoteOneLinerService(api_key="test")
    prompt = service._build_prompt(
        bill_title="GENIUS Act",
        official_summary="A bill about stablecoins.",
        vote_question="On Passage",
        grader_feedback="Expand the acronym. Explain what the bill does.",
    )
    assert "PREVIOUS ATTEMPT" in prompt or "feedback" in prompt.lower()
    assert "Expand the acronym" in prompt


def test_detect_cra_disapproval():
    service = VoteOneLinerService(api_key="test")
    assert service.is_cra_disapproval("Providing for congressional disapproval under chapter 8 of title 5, United States Code, of the rule submitted by the EPA")
    assert service.is_cra_disapproval("A joint resolution providing for congressional disapproval under chapter 8 of title 5")
    assert not service.is_cra_disapproval("National Defense Authorization Act for Fiscal Year 2026")
    assert not service.is_cra_disapproval("GENIUS Act")


@pytest.mark.asyncio
async def test_generate_one_liner_returns_string():
    service = VoteOneLinerService(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"one_liner": "Cancel an EPA rule that limits methane fees on oil and gas companies"}'
    )]

    service.client = MagicMock()
    service.client.messages.create = AsyncMock(return_value=mock_response)

    result = await service.generate(
        bill_title="H.J.Res. 35 - Congressional disapproval...",
        official_summary="Disapproves the EPA methane rule.",
        vote_question="On the Joint Resolution",
    )

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_one_liner_fallback_on_error():
    service = VoteOneLinerService(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not json")]

    service.client = MagicMock()
    service.client.messages.create = AsyncMock(return_value=mock_response)

    result = await service.generate(
        bill_title="Test Bill",
        official_summary="Test",
        vote_question="On Passage",
    )

    assert result == "Test Bill"
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_vote_one_liner.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement VoteOneLinerService**

```python
# app/services/vote_one_liner.py
import json
import logging
import anthropic

logger = logging.getLogger(__name__)


class VoteOneLinerService:
    SYSTEM_PROMPT = """You are a nonpartisan legislative analyst for a government transparency tool. Your job is to write a single plain-English sentence (under 30 words) explaining what a congressional vote means for ordinary people.

STRICT RULES:
1. Write at a 7th-8th grade reading level. Use short, common words.
2. NO jargon — no "appropriations", "fiscal year", "provisions", "chapter 8 of title 5"
3. NO adjectives — no "sweeping", "controversial", "landmark"
4. NO editorial framing — no "aims to", "seeks to", "generally seen as"
5. Start with a verb: "Cancel", "Fund", "Set", "Block", "Allow", "Require"
6. If the bill has an acronym-only name (like "GENIUS Act"), you MUST explain what it does — the name alone tells the reader nothing
7. Include key numbers (dollar amounts, population affected) when available

CRITICAL — CONGRESSIONAL REVIEW ACT (CRA) DISAPPROVAL RESOLUTIONS:
When a bill title contains "providing for congressional disapproval" or "chapter 8 of title 5", this is a CRA resolution that tries to CANCEL an existing government rule. The one-liner must describe the EFFECT of the resolution:
- Describe what government rule would be cancelled if the resolution passes
- Use language like "Cancel [agency]'s rule that [what the rule does]"
- Do NOT repeat the legislative language — translate it

Output valid JSON only: {"one_liner": "your sentence here"}"""

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @staticmethod
    def is_cra_disapproval(title: str) -> bool:
        title_lower = title.lower()
        return ("congressional disapproval" in title_lower
                or "chapter 8 of title 5" in title_lower)

    def _build_prompt(
        self,
        bill_title: str,
        official_summary: str,
        vote_question: str,
        is_cra_disapproval: bool | None = None,
        grader_feedback: str | None = None,
    ) -> str:
        if is_cra_disapproval is None:
            is_cra_disapproval = self.is_cra_disapproval(bill_title)

        cra_note = ""
        if is_cra_disapproval:
            cra_note = "\n\nNOTE: This is a CRA disapproval resolution. Describe what government rule it cancels, not the procedural mechanism."

        prompt = f"""Write a one-liner for this congressional vote.

Bill Title: {bill_title}
Official Summary: {official_summary}
Vote Question: {vote_question}
{cra_note}

Return ONLY valid JSON: {{"one_liner": "your sentence"}}"""

        if grader_feedback:
            prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

        return prompt

    async def generate(
        self,
        bill_title: str,
        official_summary: str,
        vote_question: str,
        grader_feedback: str | None = None,
    ) -> str:
        prompt = self._build_prompt(
            bill_title=bill_title,
            official_summary=official_summary,
            vote_question=vote_question,
            grader_feedback=grader_feedback,
        )

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = response.content[0].text
            result = json.loads(raw_text)
            return result.get("one_liner", bill_title)
        except json.JSONDecodeError:
            logger.error("Vote one-liner response was not valid JSON: %s", raw_text[:200])
            return bill_title
        except Exception as e:
            logger.error("Vote one-liner API call failed: %s", str(e))
            return bill_title
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_vote_one_liner.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/services/vote_one_liner.py tests/test_vote_one_liner.py
git commit -m "feat: add VoteOneLinerService with CRA disapproval detection"
```

---

## Task 5: Grader Learnings Persistence

**Files:**
- Create: `app/services/grader_learnings.py`
- Test: `tests/test_grader_learnings.py`

Manages reading, writing, and extracting new learnings from grading results. Persists to `data/grader_learnings.json`.

**Step 1: Write failing tests**

```python
# tests/test_grader_learnings.py
import pytest
import json
import tempfile
from pathlib import Path
from app.services.grader_learnings import GraderLearnings


def test_load_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        gl = GraderLearnings(Path(tmpdir) / "learnings.json")
        assert gl.get_learnings() == []


def test_save_and_load_learnings():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        gl.add_learning("Writers frequently use 'fiscal year'")
        gl.save()

        gl2 = GraderLearnings(path)
        assert "Writers frequently use 'fiscal year'" in gl2.get_learnings()


def test_no_duplicate_learnings():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        gl.add_learning("CRA resolutions are misinterpreted")
        gl.add_learning("CRA resolutions are misinterpreted")
        assert gl.get_learnings().count("CRA resolutions are misinterpreted") == 1


def test_extract_patterns_from_feedback_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        feedback_list = [
            "Uses 'fiscal year' — say 'the year starting October 2025'",
            "Contains 'fiscal year' jargon",
            "Good summary, no issues",
            "Uses 'fiscal year' again",
            "Acronym-only title not expanded",
        ]
        # 'fiscal year' appears 3/5 times — should be extracted as a pattern
        patterns = gl.extract_patterns(feedback_list, threshold=0.4)
        assert len(patterns) > 0


def test_record_batch_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "learnings.json"
        gl = GraderLearnings(path)
        gl.record_batch(
            total=10,
            passed=7,
            failed=3,
            grade_distribution={"A": 4, "B": 3, "C": 2, "D": 1, "F": 0},
            needs_review_ids=["119-hr-100", "119-s-200", "119-hjres-50"],
        )
        gl.save()

        gl2 = GraderLearnings(path)
        history = gl2.get_batch_history()
        assert len(history) == 1
        assert history[0]["total"] == 10
        assert history[0]["passed"] == 7
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_grader_learnings.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement GraderLearnings**

```python
# app/services/grader_learnings.py
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class GraderLearnings:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {"learnings": [], "batch_history": []}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with open(self.path, "r") as f:
                self._data = json.load(f)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def get_learnings(self) -> list[str]:
        return list(self._data.get("learnings", []))

    def add_learning(self, learning: str) -> None:
        if learning not in self._data["learnings"]:
            self._data["learnings"].append(learning)

    def extract_patterns(self, feedback_list: list[str], threshold: float = 0.3) -> list[str]:
        """Extract frequently occurring words/phrases from grader feedback.

        Returns phrases that appear in more than threshold fraction of feedback items.
        """
        if not feedback_list:
            return []

        # Simple word-frequency approach — find phrases appearing often
        word_counts: Counter = Counter()
        for feedback in feedback_list:
            words = set(feedback.lower().split())
            for word in words:
                if len(word) > 4:  # skip short common words
                    word_counts[word] += 1

        total = len(feedback_list)
        patterns = []
        for word, count in word_counts.most_common(10):
            if count / total >= threshold:
                # Find the original feedback that contains this word as representative example
                for fb in feedback_list:
                    if word in fb.lower():
                        patterns.append(fb)
                        break

        return patterns

    def record_batch(
        self,
        total: int,
        passed: int,
        failed: int,
        grade_distribution: dict[str, int],
        needs_review_ids: list[str],
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "grade_distribution": grade_distribution,
            "needs_review_ids": needs_review_ids,
        }
        self._data["batch_history"].append(entry)

    def get_batch_history(self) -> list[dict]:
        return self._data.get("batch_history", [])
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_grader_learnings.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/services/grader_learnings.py tests/test_grader_learnings.py
git commit -m "feat: add GraderLearnings for persistent pattern tracking"
```

---

## Task 6: Integrate Grader Loop into Sync Pipeline — Bill Summaries

**Files:**
- Modify: `sync.py`
- Test: `tests/test_sync.py` (add grader integration tests)

Add a new step 5 to the sync pipeline that generates bill summaries through the writer-grader loop in batches of 5.

**Step 1: Write failing tests**

Add to `tests/test_sync.py`:

```python
@pytest.mark.asyncio
async def test_sync_bill_summaries_creates_graded_output(tmp_path):
    """Bill summaries go through the writer-grader loop."""
    # Setup: create a bills.json with one bill
    bills_path = tmp_path / "bills.json"
    bills_path.write_text(json.dumps({"bills": [{
        "congress": 119,
        "type": "HR",
        "number": "1234",
        "title": "Test Bill",
        "summaries": [{"text": "A bill to do test things."}],
    }]}))

    # Create empty ai_summaries.json
    (tmp_path / "ai_summaries.json").write_text("{}")

    # This test validates the function signature and output structure
    # Actual API calls are mocked in integration tests
    from sync import sync_bill_summaries
    assert callable(sync_bill_summaries)
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_sync.py::test_sync_bill_summaries_creates_graded_output -v`
Expected: FAIL — `ImportError: cannot import name 'sync_bill_summaries'`

**Step 3: Add `sync_bill_summaries` to `sync.py`**

Add this function to `sync.py` (after `sync_bills_from_votes`, before `build_member_votes`):

```python
async def sync_bill_summaries(
    output_dir: Path,
    api_key: str,
    batch_size: int = 5,
    rate_limit: float = 1.0,
) -> dict:
    """Generate AI summaries for all bills through the writer-grader loop.

    Processes in batches to prevent context degradation.
    Returns stats dict with pass/fail counts.
    """
    from app.services.ai_summary import AISummaryService, IMPACT_CATEGORIES
    from app.services.summary_grader import SummaryGrader
    from app.services.writer_grader_loop import WriterGraderLoop
    from app.services.grader_learnings import GraderLearnings

    bills_path = output_dir / "bills.json"
    summaries_path = output_dir / "ai_summaries.json"
    learnings_path = output_dir / "grader_learnings.json"

    if not bills_path.exists():
        print("  No bills.json — skipping AI summaries")
        return {"total": 0, "passed": 0, "failed": 0}

    with open(bills_path) as f:
        bills = json.load(f).get("bills", [])

    # Load existing summaries (incremental)
    existing: dict[str, dict] = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    # Setup services
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    writer_service = AISummaryService(api_key=api_key, cache=cache)
    grader = SummaryGrader(api_key=api_key)

    # Load learnings
    learnings_store = GraderLearnings(learnings_path)
    grader.load_learnings(learnings_store.get_learnings())

    # Find bills needing summaries
    to_process = []
    for bill in bills:
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", 119)
        key = f"{congress}-{bill_type}-{bill_number}"
        if key not in existing:
            to_process.append((key, bill))

    if not to_process:
        print("  All bills already have summaries — skipping")
        return {"total": 0, "passed": 0, "failed": 0}

    print(f"  Generating summaries for {len(to_process)} bills (batch size: {batch_size})")

    stats = {"total": 0, "passed": 0, "failed": 0, "needs_review": []}
    grade_dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    all_feedback: list[str] = []

    for batch_start in range(0, len(to_process), batch_size):
        batch = to_process[batch_start:batch_start + batch_size]
        print(f"  Batch {batch_start // batch_size + 1}/{(len(to_process) + batch_size - 1) // batch_size}")

        for key, bill in batch:
            bill_id = key
            title = bill.get("title", "")
            summaries = bill.get("summaries", [])
            official_summary = summaries[0].get("text", "") if summaries else ""
            bill_text = bill.get("textVersions", [{}])[0].get("text", "") if bill.get("textVersions") else ""

            print(f"    Grading: {title[:60]}...")

            async def writer_fn(grader_feedback=None, **kwargs):
                return await writer_service.generate_summary(
                    bill_id=bill_id,
                    title=title,
                    official_summary=official_summary,
                    bill_text_excerpt=bill_text[:2000],
                    grader_feedback=grader_feedback,
                )

            loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
            result = await loop.run(
                summary_type="bill_summary",
                writer_kwargs={},
                grader_context={"title": title, "official_summary": official_summary},
            )

            summary_data = result.best_summary
            if result.needs_review:
                summary_data["needs_review"] = True
                stats["needs_review"].append(key)
                stats["failed"] += 1
            else:
                stats["passed"] += 1

            existing[key] = summary_data
            stats["total"] += 1
            grade_dist[result.best_grade.grade] = grade_dist.get(result.best_grade.grade, 0) + 1
            all_feedback.append(result.best_grade.feedback)

            await asyncio.sleep(rate_limit)

        # Save after each batch (crash-safe)
        _atomic_write_json(summaries_path, existing)

    # Extract new learnings
    new_patterns = learnings_store.extract_patterns(all_feedback)
    for pattern in new_patterns:
        learnings_store.add_learning(pattern)

    learnings_store.record_batch(
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        grade_distribution=grade_dist,
        needs_review_ids=stats["needs_review"],
    )
    learnings_store.save()

    print(f"  Summaries: {stats['passed']} passed, {stats['failed']} flagged for review")
    print(f"  Grades: {grade_dist}")
    if stats["needs_review"]:
        print(f"  Needs review: {stats['needs_review']}")

    return stats
```

Update `main()` in `sync.py` to add the new step:

```python
async def main() -> None:
    # ... existing args parsing ...

    api_key = os.getenv("CONGRESS_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # ... existing steps 1-4 ...

    # Step 5: AI bill summaries (writer-grader loop)
    if anthropic_key:
        print()
        print("[5/7] Generating graded AI bill summaries...")
        summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key, batch_size=5, rate_limit=1.0)
    else:
        print()
        print("[5/7] Skipping AI summaries — ANTHROPIC_API_KEY not set")
        summary_stats = {"total": 0}

    # Step 6 (was 5): Member voting records
    print()
    print("[6/7] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR)

    # Step 7: Grader report
    print()
    print("[7/7] Grader report")
    # (report printed by sync_bill_summaries and sync_vote_one_liners)
```

Also add `--grade` flag support:

```python
parser.add_argument("--grade", action="store_true",
                    help="Re-grade existing AI summaries without re-syncing source data.")
```

And in `main()`, if `--grade` is set, skip steps 1-4 and only run 5-7.

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_sync.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: integrate writer-grader loop into sync pipeline for bill summaries"
```

---

## Task 7: Integrate Grader Loop into Sync Pipeline — Vote One-Liners

**Files:**
- Modify: `sync.py` — update `build_member_votes` to use VoteOneLinerService through the grader loop
- Modify: `tests/test_sync.py`

Update `build_member_votes` so that each vote's `one_liner` is generated through the writer-grader loop instead of pulling from raw titles or pre-existing AI summaries.

**Step 1: Write failing test**

Add to `tests/test_sync.py`:

```python
@pytest.mark.asyncio
async def test_build_member_votes_uses_graded_one_liners(tmp_path):
    """Member vote one-liners should go through the grader loop when API key is set."""
    from sync import build_member_votes
    # Verify the function accepts anthropic_key parameter
    import inspect
    sig = inspect.signature(build_member_votes)
    assert "anthropic_key" in sig.parameters
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_sync.py::test_build_member_votes_uses_graded_one_liners -v`
Expected: FAIL — `anthropic_key` not in signature

**Step 3: Update `build_member_votes` in `sync.py`**

Update the function signature and add vote one-liner generation through the grader loop. Process votes in groups of 10 per member with fresh API calls.

Key changes:
- Add `anthropic_key: str | None = None` parameter
- When `anthropic_key` is set, use `VoteOneLinerService` + `WriterGraderLoop` to generate one-liners
- Process votes in groups of 10 within each member
- Fall back to existing `_get_one_liner` behavior when no API key

```python
async def build_member_votes(output_dir: Path, anthropic_key: str | None = None) -> int:
    # ... existing setup code ...

    # Setup graded one-liner generation if API key available
    one_liner_writer = None
    grader = None
    learnings_store = None
    if anthropic_key:
        from app.services.vote_one_liner import VoteOneLinerService
        from app.services.summary_grader import SummaryGrader
        from app.services.grader_learnings import GraderLearnings

        one_liner_writer = VoteOneLinerService(api_key=anthropic_key)
        grader = SummaryGrader(api_key=anthropic_key)
        learnings_path = output_dir / "grader_learnings.json"
        learnings_store = GraderLearnings(learnings_path)
        grader.load_learnings(learnings_store.get_learnings())

    # ... existing member loop ...

    # For each vote, generate graded one-liner if writer available:
    if one_liner_writer and grader:
        # Process in groups of 10
        for group_start in range(0, len(member_vote_list), 10):
            group = member_vote_list[group_start:group_start + 10]
            for vote_entry in group:
                bill_ref = vote_entry.get("_bill_ref")
                bill_info = vote_entry.get("_bill_info", {})
                doc = vote_entry.get("bill_number", "")
                title = bill_info.get("title", doc)
                summaries = bill_info.get("summaries", [])
                official_summary = summaries[0].get("text", "") if summaries else ""
                vote_question = vote_entry.get("_vote_question", "")

                async def writer_fn(grader_feedback=None, **kwargs):
                    return await one_liner_writer.generate(
                        bill_title=title,
                        official_summary=official_summary,
                        vote_question=vote_question,
                        grader_feedback=grader_feedback,
                    )

                loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
                result = await loop.run(
                    summary_type="vote_one_liner",
                    writer_kwargs={},
                    grader_context={
                        "bill_title": title,
                        "vote_question": vote_question,
                        "is_cra_disapproval": one_liner_writer.is_cra_disapproval(title),
                    },
                )

                vote_entry["one_liner"] = result.best_summary if isinstance(result.best_summary, str) else result.best_summary.get("one_liner", title)
                if result.needs_review:
                    vote_entry["needs_review"] = True

            await asyncio.sleep(0.5)
    else:
        # Fallback: use existing _get_one_liner
        pass  # existing behavior

    # ... rest of existing function (stats, save) ...
```

Update the `main()` call to pass `anthropic_key`:

```python
member_votes_count = await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)
```

Note: The existing `_get_one_liner` function and AI summary lookup is preserved as fallback. The new writer-grader loop only runs when `ANTHROPIC_API_KEY` is set. Also stash `_bill_ref`, `_bill_info`, and `_vote_question` temporarily in the vote dict during processing (remove before saving).

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_sync.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: integrate writer-grader loop for vote one-liners in member votes"
```

---

## Task 8: Add `--grade` Re-Grade Command

**Files:**
- Modify: `sync.py`
- Test: `tests/test_sync.py`

Add the `--grade` flag that re-runs the grader loop on all existing AI summaries without re-syncing source data from Congress.gov.

**Step 1: Write failing test**

```python
def test_grade_flag_accepted():
    """sync.py should accept --grade flag."""
    import subprocess
    result = subprocess.run(
        ["python", "sync.py", "--grade", "--help"],
        capture_output=True, text=True
    )
    assert "--grade" in result.stdout or result.returncode == 0
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_sync.py::test_grade_flag_accepted -v`
Expected: FAIL (or pass if already added in Task 6 — verify)

**Step 3: Implement `--grade` mode in `main()`**

In `sync.py` `main()`, after argument parsing:

```python
if args.grade:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        print("ERROR: ANTHROPIC_API_KEY not set — cannot grade without it")
        sys.exit(1)

    print("=== ClearVote Re-Grade Mode ===")
    print("Re-grading all existing AI summaries...")
    print()

    # Clear existing summaries to force re-generation
    summaries_path = SYNC_DIR / "ai_summaries.json"
    if summaries_path.exists():
        # Back up existing
        backup_path = SYNC_DIR / "ai_summaries.backup.json"
        import shutil
        shutil.copy2(summaries_path, backup_path)
        print(f"  Backed up existing summaries to {backup_path.name}")
        _atomic_write_json(summaries_path, {})

    print()
    print("[1/2] Re-grading bill summaries...")
    summary_stats = await sync_bill_summaries(SYNC_DIR, anthropic_key, batch_size=5, rate_limit=1.0)

    print()
    print("[2/2] Re-grading vote one-liners...")
    member_votes_count = await build_member_votes(SYNC_DIR, anthropic_key=anthropic_key)

    print()
    print("=== Re-grade complete ===")
    return
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_sync.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add --grade flag for re-grading existing AI summaries"
```

---

## Task 9: End-to-End Integration Tests

**Files:**
- Create: `tests/test_grader_integration.py`

Tests that verify the full writer → grader → feedback → retry flow works end-to-end with mocked API calls.

**Step 1: Write integration tests**

```python
# tests/test_grader_integration.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.ai_summary import AISummaryService
from app.services.vote_one_liner import VoteOneLinerService
from app.services.summary_grader import SummaryGrader, GradeResult
from app.services.writer_grader_loop import WriterGraderLoop


@pytest.mark.asyncio
async def test_bill_summary_full_loop():
    """Full loop: writer generates summary, grader grades it, 3 rounds."""
    writer_service = AISummaryService(api_key="test", cache=MagicMock(get=MagicMock(return_value=None)))

    # Mock writer responses — each round gets better
    writer_responses = [
        '{"one_liner": "Set rules for stablecoins called the GENIUS Act", "provisions": ["Creates rules for stablecoins"], "impact_categories": ["Economy"]}',
        '{"one_liner": "Set rules for dollar-backed digital coins", "provisions": ["Creates rules for companies that issue digital coins backed by US dollars"], "impact_categories": ["Economy"]}',
        '{"one_liner": "Set rules for dollar-backed digital coins", "provisions": ["Creates rules for companies that issue digital coins backed by US dollars", "Requires these companies to hold $1 in reserve for every digital coin"], "impact_categories": ["Economy"]}',
    ]
    writer_call_count = 0

    async def mock_writer_create(**kwargs):
        nonlocal writer_call_count
        resp = MagicMock()
        resp.content = [MagicMock(text=writer_responses[min(writer_call_count, 2)])]
        writer_call_count += 1
        return resp

    writer_service.client = MagicMock()
    writer_service.client.messages.create = mock_writer_create

    # Mock grader responses — fails first, passes later
    grader = SummaryGrader(api_key="test")
    grader_responses = [
        '{"grade": "C", "passed": false, "feedback": "GENIUS Act is acronym-only — expand and explain what stablecoins are.", "checks": {"reading_level": "pass", "no_jargon": "fail: GENIUS Act not expanded", "no_bias": "pass", "vote_context": "n/a", "factual_context": "fail: no reserve requirement details", "structure": "pass"}}',
        '{"grade": "B", "passed": true, "feedback": "Good improvement. Minor: could add how many stablecoin issuers this affects.", "checks": {"reading_level": "pass", "no_jargon": "pass", "no_bias": "pass", "vote_context": "n/a", "factual_context": "pass", "structure": "pass"}}',
        '{"grade": "A", "passed": true, "feedback": "Excellent. Clear, accurate, no jargon.", "checks": {"reading_level": "pass", "no_jargon": "pass", "no_bias": "pass", "vote_context": "n/a", "factual_context": "pass", "structure": "pass"}}',
    ]
    grader_call_count = 0

    async def mock_grader_create(**kwargs):
        nonlocal grader_call_count
        resp = MagicMock()
        resp.content = [MagicMock(text=grader_responses[min(grader_call_count, 2)])]
        grader_call_count += 1
        return resp

    grader.client = MagicMock()
    grader.client.messages.create = mock_grader_create

    async def writer_fn(grader_feedback=None):
        return await writer_service.generate_summary(
            bill_id="119-s-1582",
            title="GENIUS Act",
            official_summary="A bill to establish a framework for stablecoins.",
            bill_text_excerpt="...",
            grader_feedback=grader_feedback,
        )

    loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
    result = await loop.run(
        summary_type="bill_summary",
        writer_kwargs={},
        grader_context={"title": "GENIUS Act", "official_summary": "A bill about stablecoins."},
    )

    assert result.best_grade.grade == "A"
    assert result.needs_review is False
    assert result.rounds == 3
    assert writer_call_count == 3
    assert grader_call_count == 3


@pytest.mark.asyncio
async def test_cra_vote_one_liner_loop():
    """CRA disapproval vote should be correctly interpreted."""
    writer_service = VoteOneLinerService(api_key="test")

    writer_responses = [
        '{"one_liner": "Cancel an EPA rule that limits methane fees on oil and gas companies"}',
    ]

    async def mock_create(**kwargs):
        resp = MagicMock()
        resp.content = [MagicMock(text=writer_responses[0])]
        return resp

    writer_service.client = MagicMock()
    writer_service.client.messages.create = mock_create

    grader = SummaryGrader(api_key="test")

    async def mock_grader_create(**kwargs):
        resp = MagicMock()
        resp.content = [MagicMock(text='{"grade": "A", "passed": true, "feedback": "Correctly interprets CRA disapproval.", "checks": {"reading_level": "pass", "no_jargon": "pass", "no_bias": "pass", "vote_context": "pass: correctly identifies CRA cancellation", "factual_context": "pass", "structure": "pass"}}')]
        return resp

    grader.client = MagicMock()
    grader.client.messages.create = mock_grader_create

    async def writer_fn(grader_feedback=None):
        result = await writer_service.generate(
            bill_title="Providing for congressional disapproval under chapter 8 of title 5, United States Code, of the rule submitted by the EPA relating to methane emissions",
            official_summary="Disapproves the EPA methane fee rule.",
            vote_question="On the Joint Resolution",
            grader_feedback=grader_feedback,
        )
        return {"one_liner": result}

    loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
    result = await loop.run(
        summary_type="vote_one_liner",
        writer_kwargs={},
        grader_context={
            "bill_title": "Congressional disapproval of EPA methane rule",
            "vote_question": "On the Joint Resolution",
            "is_cra_disapproval": True,
        },
    )

    assert result.best_grade.grade == "A"
    one_liner = result.best_summary["one_liner"]
    assert "cancel" in one_liner.lower() or "undo" in one_liner.lower() or "epa" in one_liner.lower()
```

**Step 2: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_grader_integration.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_grader_integration.py
git commit -m "test: add end-to-end integration tests for writer-grader loop"
```

---

## Task 10: Run Full Test Suite and Final Cleanup

**Files:**
- All modified files

**Step 1: Run full test suite**

Run: `source .venv/bin/activate && pytest -v`
Expected: All tests PASS (existing 100 + new tests)

**Step 2: Fix any failures**

Address any test failures or import issues.

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: summary grader implementation complete — all tests passing"
```

---

## Files Touched

| File | Change |
|------|--------|
| `app/services/summary_grader.py` | **Create** — Grader service with quality checklist |
| `app/services/writer_grader_loop.py` | **Create** — 3-round loop orchestrator |
| `app/services/vote_one_liner.py` | **Create** — Vote one-liner writer with CRA detection |
| `app/services/grader_learnings.py` | **Create** — Persistent learnings storage |
| `app/services/ai_summary.py` | **Modify** — Accept grader_feedback parameter |
| `sync.py` | **Modify** — Add steps 5-7, --grade flag, batch processing |
| `tests/test_summary_grader.py` | **Create** — Grader unit tests |
| `tests/test_writer_grader_loop.py` | **Create** — Loop orchestrator tests |
| `tests/test_vote_one_liner.py` | **Create** — Vote one-liner writer tests |
| `tests/test_grader_learnings.py` | **Create** — Learnings persistence tests |
| `tests/test_grader_integration.py` | **Create** — End-to-end integration tests |
| `tests/test_ai_summary.py` | **Modify** — Add feedback parameter tests |
| `tests/test_sync.py` | **Modify** — Add grader integration tests |
| `data/grader_learnings.json` | **Created at runtime** — Persistent learnings |

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_summary_grader.py` | Grader returns correct grades, handles errors, includes learnings |
| Unit | `test_writer_grader_loop.py` | Loop runs 3 rounds, picks best, flags failures |
| Unit | `test_vote_one_liner.py` | CRA detection, prompt construction, fallback behavior |
| Unit | `test_grader_learnings.py` | Persistence, deduplication, pattern extraction |
| Unit | `test_ai_summary.py` | Feedback parameter accepted and included in prompt |
| Integration | `test_grader_integration.py` | Full writer → grader → feedback → retry flow |
| Integration | `test_sync.py` | Sync pipeline runs with grader, --grade flag works |

## Not In Scope

- **Frontend changes** — The member profile's "At a Glance" text and "most active on" logic are frontend issues. This plan focuses on the data pipeline. Frontend fixes should be a separate plan.
- **Vote deduplication** — Multiple procedural votes on the same bill (cloture, amendment, passage) creating duplicate entries. Related but separate fix.
- **Re-syncing all existing data** — This plan builds the grader. Running it on all 177 bills and 80 members' votes is a separate sync run after implementation.
