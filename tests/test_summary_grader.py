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
            "issue_categories": ["Jobs & Workers"]
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
        summary_text='{"one_liner": "Raise minimum wage to $15", "provisions": ["Raises wage from $7.25 to $15"], "issue_categories": ["Jobs & Workers"]}',
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
        summary_text='{"one_liner": "Test", "provisions": ["Test"], "issue_categories": []}',
        context={"title": "Test"}
    )

    assert isinstance(result, GradeResult)
    assert result.passed is False
    assert result.grade == "F"


# Real grader output shapes captured from `claude -p` transcripts (2026-09-28):
# the JSON body is fine but its edges are not. Shortened; boundary glitch kept verbatim.
STRAY_QUOTE_AFTER_OBJECT = '''{"grade":"B","passed":true,"feedback":"Strong, accurate summary. One issue: Provision 2 runs to approximately 27 words.","checks":{"structure":"fail: Provision 2 is over 25 words","direction_accuracy":"pass: 'in_favor' is correct — the bill expands eligibility, which qualifies as 'expands rules in the issue area.'"}}"'''

FINAL_BRACE_DROPPED = '''{"grade":"C","passed":false,"feedback":"Two provisions exceed the 25-word sentence limit.","checks":{"structure":"fail: Provisions 1 and 3 are over 25 words","direction_accuracy":"pass: the bill creates new requirements, consistent with 'in_favor.'"}'''

PROSE_BEFORE_OBJECT = (
    "★ Insight ─────────────────────────────────────\n"
    "Grading this summary requires attention to whether plain-language substitutions hold up.\n"
    "─────────────────────────────────────────────────\n\n"
    '{"grade":"A","passed":true,"feedback":"Strong, accurate summary with plain language throughout.","checks":{"structure":"pass"}}'
)

VALID_BILL_SUMMARY = '{"one_liner": "Raise minimum wage to $15", "provisions": ["Raises wage from $7.25 to $15"], "issue_categories": ["Jobs & Workers"]}'


@pytest.mark.asyncio
@pytest.mark.parametrize("raw, grade, passed, feedback", [
    (STRAY_QUOTE_AFTER_OBJECT, "B", True, "Strong, accurate summary. One issue: Provision 2 runs to approximately 27 words."),
    (FINAL_BRACE_DROPPED, "C", False, "Two provisions exceed the 25-word sentence limit."),
    (PROSE_BEFORE_OBJECT, "A", True, "Strong, accurate summary with plain language throughout."),
], ids=["stray_quote_after_object", "final_brace_dropped", "prose_before_object"])
async def test_grade_recovers_real_malformed_grader_output(raw, grade, passed, feedback):
    grader = SummaryGrader(api_key="test")
    grader._call_llm = AsyncMock(return_value=raw)

    result = await grader.grade(summary_type="bill_summary", summary_text=VALID_BILL_SUMMARY, context={"title": "Wage Act"})

    assert (result.grade, result.passed, result.feedback) == (grade, passed, feedback)


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [
    '{"grade":"B","passed":true,"feedback":"Strong, accurate summary. (1) Provision 3 runs to appro',
    '{"grade":"B","passed":true',
], ids=["mid_string", "after_complete_value"])
async def test_grade_still_fails_on_cut_off_output(raw):
    """Recovery must not invent a grade from a response that stops before the object is done."""
    grader = SummaryGrader(api_key="test")
    grader._call_llm = AsyncMock(return_value=raw)

    result = await grader.grade(summary_type="bill_summary", summary_text=VALID_BILL_SUMMARY, context={"title": "Wage Act"})

    assert (result.grade, result.passed) == ("F", False)
