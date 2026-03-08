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
