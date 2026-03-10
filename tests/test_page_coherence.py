import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from app.services.page_coherence import PageCoherenceChecker, CoherenceResult, COHERENCE_SYSTEM_PROMPT


def test_coherence_result_structure():
    result = CoherenceResult(is_coherent=True)
    assert result.is_coherent is True
    assert result.contradictions == []
    assert result.guidance == ""


def test_system_prompt_explains_page_sections():
    assert "NARRATIVE SUMMARY" in COHERENCE_SYSTEM_PROMPT
    assert "WHERE THEY FOCUS" in COHERENCE_SYSTEM_PROMPT
    assert "WHAT THEY SUPPORTED" in COHERENCE_SYSTEM_PROMPT
    assert "contradictions" in COHERENCE_SYSTEM_PROMPT.lower()


def test_checker_includes_learnings():
    checker = PageCoherenceChecker(api_key="test")
    checker.load_learnings(["Narratives often mischaracterize environmental votes"])
    prompt = checker._build_system_prompt()
    assert "LEARNED PATTERNS" in prompt
    assert "environmental" in prompt


@pytest.mark.asyncio
async def test_coherent_page_passes():
    """Page where narrative matches data should pass."""
    checker = PageCoherenceChecker(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text=json.dumps({
            "is_coherent": True,
            "contradictions": [],
            "guidance": "",
        })
    )]

    checker.client = MagicMock()
    checker.client.messages.create = AsyncMock(return_value=mock_response)

    result = await checker.check(
        narrative="Smith voted 200 times with 95% participation. Most votes were on economics.",
        stats={"total_votes": 200, "participation_rate": 95.0},
        top_areas=[
            {"name": "Economics", "strengthen": 80, "weaken": 64, "total": 144},
        ],
        top_supported=["Fund economic research"],
        top_opposed=["Cut economic funding"],
    )

    assert isinstance(result, CoherenceResult)
    assert result.is_coherent is True
    assert result.contradictions == []


@pytest.mark.asyncio
async def test_contradictory_narrative_fails():
    """Page where narrative contradicts data should fail with specific contradictions."""
    checker = PageCoherenceChecker(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text=json.dumps({
            "is_coherent": False,
            "contradictions": [
                "Narrative says member 'voted to strengthen environmental protections' but data shows 3 strengthening vs 12 weakening votes on Environment",
                "Narrative claims 500 total votes but stats show 200",
            ],
            "guidance": "Rewrite to reflect that Environment votes were mostly weakening (12 of 15). Use the correct total vote count of 200.",
        })
    )]

    checker.client = MagicMock()
    checker.client.messages.create = AsyncMock(return_value=mock_response)

    result = await checker.check(
        narrative="Smith voted 500 times and voted to strengthen environmental protections.",
        stats={"total_votes": 200, "participation_rate": 95.0},
        top_areas=[
            {"name": "Environment", "strengthen": 3, "weaken": 12, "total": 15},
        ],
        top_supported=["Fund economic research"],
        top_opposed=["Cancel EPA methane rule"],
    )

    assert result.is_coherent is False
    assert len(result.contradictions) == 2
    assert "environment" in result.contradictions[0].lower() or "Environment" in result.contradictions[0]
    assert result.guidance != ""


@pytest.mark.asyncio
async def test_handles_malformed_json():
    """Returns incoherent result when LLM returns invalid JSON."""
    checker = PageCoherenceChecker(api_key="test")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    checker.client = MagicMock()
    checker.client.messages.create = AsyncMock(return_value=mock_response)

    result = await checker.check(
        narrative="Test",
        stats={},
        top_areas=[],
        top_supported=[],
        top_opposed=[],
    )

    assert result.is_coherent is False
    assert len(result.contradictions) > 0


@pytest.mark.asyncio
async def test_handles_api_error_gracefully():
    """On API error, default to coherent to avoid blocking sync."""
    checker = PageCoherenceChecker(api_key="test")

    checker.client = MagicMock()
    checker.client.messages.create = AsyncMock(side_effect=Exception("API down"))

    result = await checker.check(
        narrative="Test",
        stats={},
        top_areas=[],
        top_supported=[],
        top_opposed=[],
    )

    # Default to coherent on error (don't block sync)
    assert result.is_coherent is True
