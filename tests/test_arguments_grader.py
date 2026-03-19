import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.arguments_grader import ArgumentsGrader


def test_grader_system_prompt_includes_checks():
    grader = ArgumentsGrader(api_key="test")
    prompt = grader._build_system_prompt()
    assert "ATTRIBUTION" in prompt
    assert "SPECIFICITY" in prompt
    assert "BALANCE" in prompt
    assert "NO BIAS" in prompt
    assert "READING LEVEL" in prompt


def test_grader_system_prompt_with_learnings():
    grader = ArgumentsGrader(api_key="test")
    grader.load_learnings(["Arguments must reference dollar amounts"])
    prompt = grader._build_system_prompt()
    assert "dollar amounts" in prompt
    assert "LEARNED PATTERNS" in prompt


def test_grader_system_prompt_without_learnings():
    grader = ArgumentsGrader(api_key="test")
    prompt = grader._build_system_prompt()
    assert "LEARNED PATTERNS" not in prompt


@pytest.mark.asyncio
async def test_grade_passing_arguments():
    grader = ArgumentsGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"grade": "A", "passed": true, "feedback": "Excellent balance and specificity.", "checks": {"attribution": "pass", "specificity": "pass", "balance": "pass", "no_bias": "pass", "reading_level": "pass", "structure": "pass"}}'
    )]

    with patch.object(grader, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await grader.grade(
            summary_type="bill_arguments",
            summary_text='{"supporters": ["Supporters say..."], "critics": ["Critics say..."]}',
            context={"title": "Test Bill", "official_summary": "A bill."},
        )

    assert result.grade == "A"
    assert result.passed is True


@pytest.mark.asyncio
async def test_grade_failing_arguments():
    grader = ArgumentsGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"grade": "D", "passed": false, "feedback": "Arguments are too generic. No specific provisions referenced.", "checks": {"attribution": "pass", "specificity": "fail: no dollar amounts or provisions referenced", "balance": "pass", "no_bias": "pass", "reading_level": "pass", "structure": "pass"}}'
    )]

    with patch.object(grader, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await grader.grade(
            summary_type="bill_arguments",
            summary_text='{"supporters": ["Supporters say this is good"], "critics": ["Critics say this is bad"]}',
            context={"title": "Test Bill", "official_summary": "A bill."},
        )

    assert result.grade == "D"
    assert result.passed is False
    assert "generic" in result.feedback.lower()


@pytest.mark.asyncio
async def test_grade_handles_invalid_json_response():
    grader = ArgumentsGrader(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='not valid json')]

    with patch.object(grader, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await grader.grade(
            summary_type="bill_arguments",
            summary_text="test",
            context={"title": "Test"},
        )

    assert result.grade == "F"
    assert result.passed is False


@pytest.mark.asyncio
async def test_grade_handles_api_error():
    grader = ArgumentsGrader(api_key="test")

    with patch.object(grader, "client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=Exception("API timeout"))
        result = await grader.grade(
            summary_type="bill_arguments",
            summary_text="test",
            context={"title": "Test"},
        )

    assert result.grade == "F"
    assert result.passed is False
    assert "API timeout" in result.feedback
