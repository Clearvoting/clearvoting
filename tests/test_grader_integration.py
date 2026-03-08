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


@pytest.mark.asyncio
async def test_loop_with_persistent_failure():
    """When all 3 rounds fail, the result should be flagged for review."""
    writer_service = AISummaryService(api_key="test", cache=MagicMock(get=MagicMock(return_value=None)))

    async def mock_writer_create(**kwargs):
        resp = MagicMock()
        resp.content = [MagicMock(text='{"one_liner": "Bad summary with appropriations and fiscal year jargon", "provisions": ["Authorizes appropriations for fiscal year 2026"], "impact_categories": ["Government Operations"]}')]
        return resp

    writer_service.client = MagicMock()
    writer_service.client.messages.create = mock_writer_create

    grader = SummaryGrader(api_key="test")

    async def mock_grader_create(**kwargs):
        resp = MagicMock()
        resp.content = [MagicMock(text='{"grade": "D", "passed": false, "feedback": "Contains jargon: appropriations, fiscal year, authorizes. Rewrite in plain English.", "checks": {"reading_level": "fail", "no_jargon": "fail: appropriations, fiscal year", "no_bias": "pass", "vote_context": "n/a", "factual_context": "fail", "structure": "pass"}}')]
        return resp

    grader.client = MagicMock()
    grader.client.messages.create = mock_grader_create

    async def writer_fn(grader_feedback=None):
        return await writer_service.generate_summary(
            bill_id="119-hr-999",
            title="Test Bill",
            official_summary="Test",
            bill_text_excerpt="Test",
            grader_feedback=grader_feedback,
        )

    loop = WriterGraderLoop(writer_fn=writer_fn, grader=grader)
    result = await loop.run(
        summary_type="bill_summary",
        writer_kwargs={},
        grader_context={"title": "Test Bill", "official_summary": "Test"},
    )

    assert result.needs_review is True
    assert result.best_grade.grade == "D"
    assert result.rounds == 3
