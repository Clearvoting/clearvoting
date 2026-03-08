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


@pytest.mark.asyncio
async def test_loop_exits_early_on_a_grade():
    """When round 1 gets an A, don't waste API calls on rounds 2 and 3."""
    mock_writer = AsyncMock(
        return_value={"one_liner": "Perfect", "provisions": ["Perfect"], "impact_categories": []}
    )

    mock_grader = MagicMock()
    mock_grader.grade = AsyncMock(return_value=GradeResult(
        grade="A", passed=True, feedback="Perfect.", checks={}
    ))

    loop = WriterGraderLoop(writer_fn=mock_writer, grader=mock_grader)
    result = await loop.run(
        summary_type="bill_summary",
        writer_kwargs={"title": "Test"},
        grader_context={"title": "Test"},
    )

    assert mock_writer.call_count == 1
    assert mock_grader.grade.call_count == 1
    assert result.rounds == 1
    assert result.best_grade.grade == "A"
    assert result.all_grades == ["A"]
