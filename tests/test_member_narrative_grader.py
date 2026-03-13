import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from app.services.member_narrative_grader import MemberNarrativeGrader, GradeResult


def test_grade_result_structure():
    result = GradeResult(grade="A", passed=True, feedback="Good.", checks={})
    assert result.grade == "A"
    assert result.passed is True


def test_grader_system_prompt_contains_member_checklist():
    grader = MemberNarrativeGrader(api_key="test")
    prompt = grader._build_system_prompt()
    assert "reading level" in prompt.lower() or "7th-8th" in prompt
    assert "DATA ALIGNMENT" in prompt
    assert "CHERRY-PICKING" in prompt
    assert "bias" in prompt.lower()
    assert "3-5 sentences" in prompt


def test_grader_system_prompt_does_not_contain_bill_specific_checks():
    """Member grader should not check for CRA, provisions, or bill structure."""
    grader = MemberNarrativeGrader(api_key="test")
    prompt = grader._build_system_prompt()
    assert "CRA" not in prompt
    assert "provisions" not in prompt
    assert "one_liner" not in prompt


def test_grader_build_prompt_includes_context():
    grader = MemberNarrativeGrader(api_key="test")
    context = {
        "top_areas": [
            {"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15},
            {"name": "Cost of Living", "in_favor": 80, "against": 64, "total": 144},
        ],
        "stats": {"total_votes": 200, "participation_rate": 95.0},
    }
    prompt = grader._build_grade_prompt(
        summary_type="member_narrative",
        summary_text='{"narrative": "Test narrative."}',
        context=context,
    )
    assert "Environment" in prompt
    assert "member_narrative" in prompt
    assert "ground truth" in prompt.lower()


def test_grader_includes_learnings_in_prompt():
    grader = MemberNarrativeGrader(api_key="test")
    grader.load_learnings([
        "Writers often cherry-pick environmental votes",
        "Participation rates are frequently omitted",
    ])
    prompt = grader._build_system_prompt()
    assert "cherry-pick" in prompt
    assert "Participation" in prompt
    assert "LEARNED PATTERNS" in prompt


@pytest.mark.asyncio
async def test_grade_data_aligned_narrative_passes():
    """Narrative that matches data ratios should pass."""
    grader = MemberNarrativeGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text=json.dumps({
            "grade": "A",
            "passed": True,
            "feedback": "Narrative accurately reflects data.",
            "checks": {
                "reading_level": "pass",
                "no_bias": "pass",
                "data_alignment": "pass: narrative correctly shows mostly against on Environment & Energy",
                "no_cherry_picking": "pass",
                "structure": "pass",
                "completeness": "pass",
            }
        })
    )]

    grader.client = MagicMock()
    grader.client.messages.create = AsyncMock(return_value=mock_response)

    result = await grader.grade(
        summary_type="member_narrative",
        summary_text='{"narrative": "Smith voted 200 times with 95% participation. On Environment & Energy, Smith voted against 12 times and in favor 3 times. On Cost of Living, Smith cast 144 votes with a slight lean in favor."}',
        context={
            "top_areas": [
                {"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15},
                {"name": "Cost of Living", "in_favor": 80, "against": 64, "total": 144},
            ],
            "stats": {"total_votes": 200, "participation_rate": 95.0},
        },
    )

    assert isinstance(result, GradeResult)
    assert result.grade == "A"
    assert result.passed is True


@pytest.mark.asyncio
async def test_grade_narrative_contradicting_data_fails():
    """Narrative that contradicts data should fail with data_alignment feedback."""
    grader = MemberNarrativeGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text=json.dumps({
            "grade": "D",
            "passed": False,
            "feedback": "Narrative says member 'voted to protect the environment' but data shows 3 in_favor vs 12 against — mostly against. This contradicts the data.",
            "checks": {
                "reading_level": "pass",
                "no_bias": "pass",
                "data_alignment": "fail: Environment & Energy is 3 in_favor / 12 against but narrative implies support for environmental protections",
                "no_cherry_picking": "fail: highlights 3 in-favor votes while ignoring 12 against votes",
                "structure": "pass",
                "completeness": "pass",
            }
        })
    )]

    grader.client = MagicMock()
    grader.client.messages.create = AsyncMock(return_value=mock_response)

    result = await grader.grade(
        summary_type="member_narrative",
        summary_text='{"narrative": "Smith voted to protect the environment and support environmental regulations."}',
        context={
            "top_areas": [
                {"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15},
            ],
            "stats": {"total_votes": 200, "participation_rate": 95.0},
        },
    )

    assert isinstance(result, GradeResult)
    assert result.grade == "D"
    assert result.passed is False
    assert "data" in result.feedback.lower() or "contradict" in result.feedback.lower()


@pytest.mark.asyncio
async def test_grade_cherry_picking_detected():
    """Narrative that highlights exceptions should fail."""
    grader = MemberNarrativeGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text=json.dumps({
            "grade": "C",
            "passed": False,
            "feedback": "Narrative leads with the 3 in-favor votes on environment but ignores the 12 against votes. This cherry-picks exceptions.",
            "checks": {
                "reading_level": "pass",
                "no_bias": "pass",
                "data_alignment": "fail: misleading emphasis",
                "no_cherry_picking": "fail: leads with 3 in-favor votes, omits 12 against",
                "structure": "pass",
                "completeness": "pass",
            }
        })
    )]

    grader.client = MagicMock()
    grader.client.messages.create = AsyncMock(return_value=mock_response)

    result = await grader.grade(
        summary_type="member_narrative",
        summary_text='{"narrative": "Smith voted in favor of environmental rules on 3 occasions."}',
        context={
            "top_areas": [
                {"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15},
            ],
            "stats": {"total_votes": 200, "participation_rate": 95.0},
        },
    )

    assert result.passed is False
    assert "cherry" in result.feedback.lower() or "exception" in result.feedback.lower()


@pytest.mark.asyncio
async def test_grade_handles_malformed_json():
    """Grader returns F on invalid JSON response."""
    grader = MemberNarrativeGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    grader.client = MagicMock()
    grader.client.messages.create = AsyncMock(return_value=mock_response)

    result = await grader.grade(
        summary_type="member_narrative",
        summary_text='{"narrative": "Test"}',
        context={"top_areas": [], "stats": {}},
    )

    assert result.grade == "F"
    assert result.passed is False
