import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.member_summary import MemberSummaryService, MEMBER_SUMMARY_SYSTEM_PROMPT


def test_system_prompt_has_no_bias_rules():
    """System prompt enforces facts-only, no editorializing."""
    assert "NO adjectives" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "7th-8th grade" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "facts" in MEMBER_SUMMARY_SYSTEM_PROMPT.lower()


def test_build_prompt_includes_vote_data():
    """Prompt includes member's policy areas, vote counts, and top bills."""
    service = MemberSummaryService(api_key=None)
    prompt = service._build_prompt(
        member_name="Kirsten E. Gillibrand",
        chamber="Senate",
        state="New York",
        congresses=[117, 118, 119],
        stats={"total_votes": 500, "yea_count": 200, "nay_count": 295, "participation_rate": 99.0},
        top_areas=[
            {"name": "Environmental Protection", "strengthen": 8, "weaken": 0, "total": 8},
            {"name": "Finance and Financial Sector", "strengthen": 3, "weaken": 1, "total": 4},
        ],
        top_supported=["Set military spending limits for 2026", "Fund clean energy research"],
        top_opposed=["Cancel an EPA rule on methane fees"],
    )
    assert "Gillibrand" in prompt
    assert "Environmental Protection" in prompt
    assert "Set military spending limits" in prompt
    assert "500" in prompt  # total votes
    assert "99.0" in prompt or "99" in prompt  # participation rate


@pytest.mark.asyncio
async def test_generate_member_summary_returns_narrative():
    """generate_member_summary returns a dict with narrative field."""
    mock_response = json.dumps({
        "narrative": "Over the past 5 years, Gillibrand has focused on environmental protection and financial regulation.",
        "top_areas": ["Environmental Protection", "Finance and Financial Sector"],
    })

    service = MemberSummaryService(api_key="test-key")
    service._call_llm = AsyncMock(return_value=mock_response)

    result = await service.generate_member_summary(
        member_name="Kirsten E. Gillibrand",
        chamber="Senate",
        state="New York",
        congresses=[117, 118, 119],
        stats={"total_votes": 500, "yea_count": 200, "nay_count": 295, "participation_rate": 99.0},
        top_areas=[{"name": "Environmental Protection", "strengthen": 8, "weaken": 0, "total": 8}],
        top_supported=["Set military spending limits for 2026"],
        top_opposed=["Cancel an EPA rule on methane fees"],
    )

    assert "narrative" in result
    assert "Gillibrand" in result["narrative"]
    assert "top_areas" in result


@pytest.mark.asyncio
async def test_generate_member_summary_handles_invalid_json():
    """Returns fallback when LLM returns invalid JSON."""
    service = MemberSummaryService(api_key="test-key")
    service._call_llm = AsyncMock(return_value="Not valid JSON")

    result = await service.generate_member_summary(
        member_name="Test Member",
        chamber="Senate",
        state="New York",
        congresses=[119],
        stats={"total_votes": 10, "yea_count": 5, "nay_count": 5, "participation_rate": 100.0},
        top_areas=[],
        top_supported=[],
        top_opposed=[],
    )

    assert "narrative" in result
    assert result["narrative"] != ""


@pytest.mark.asyncio
async def test_generate_member_summary_with_grader_feedback():
    """Grader feedback is appended to the prompt for retry."""
    service = MemberSummaryService(api_key="test-key")

    calls = []
    async def capture_call(system, prompt):
        calls.append(prompt)
        return json.dumps({"narrative": "Fixed version.", "top_areas": []})

    service._call_llm = capture_call

    await service.generate_member_summary(
        member_name="Test Member",
        chamber="Senate",
        state="New York",
        congresses=[119],
        stats={"total_votes": 10, "yea_count": 5, "nay_count": 5, "participation_rate": 100.0},
        top_areas=[],
        top_supported=[],
        top_opposed=[],
        grader_feedback="Too many adjectives. Remove 'strong advocate'.",
    )

    assert "Too many adjectives" in calls[0]
