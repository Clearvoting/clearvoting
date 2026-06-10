import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.member_summary import (
    MemberSummaryService, MEMBER_SUMMARY_SYSTEM_PROMPT, _compute_data_brief,
)


def test_system_prompt_has_no_bias_rules():
    """System prompt enforces facts-only, no editorializing."""
    assert "NO adjectives" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "7th-8th grade" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "facts" in MEMBER_SUMMARY_SYSTEM_PROMPT.lower()


def test_system_prompt_includes_data_constraint_rule():
    """System prompt instructs writer to follow DATA CONSTRAINTS."""
    assert "DATA CONSTRAINTS" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "highlight exceptions" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "in favor" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "against" in MEMBER_SUMMARY_SYSTEM_PROMPT


# --- _compute_data_brief tests ---


def test_compute_data_brief_mostly_in_favor():
    areas = [{"name": "Environment & Energy", "in_favor": 12, "against": 3, "total": 15}]
    brief = _compute_data_brief(areas)
    assert "DATA CONSTRAINTS" in brief
    assert "mostly in favor" in brief
    assert "12 in favor" in brief
    assert "3 against" in brief


def test_compute_data_brief_mostly_against():
    areas = [{"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15}]
    brief = _compute_data_brief(areas)
    assert "mostly against" in brief


def test_compute_data_brief_leans_in_favor():
    """55-74% should be classified as 'leans'."""
    areas = [{"name": "Cost of Living", "in_favor": 7, "against": 3, "total": 10}]
    brief = _compute_data_brief(areas)
    assert "leans in favor" in brief


def test_compute_data_brief_leans_against():
    areas = [{"name": "Cost of Living", "in_favor": 3, "against": 7, "total": 10}]
    brief = _compute_data_brief(areas)
    assert "leans against" in brief


def test_compute_data_brief_mixed():
    """~50/50 should be classified as 'mixed'."""
    areas = [{"name": "Cost of Living", "in_favor": 5, "against": 5, "total": 10}]
    brief = _compute_data_brief(areas)
    assert "mixed" in brief


def test_compute_data_brief_no_directional():
    """All neutral votes = no clear direction."""
    areas = [{"name": "Procedural", "in_favor": 0, "against": 0, "total": 10}]
    brief = _compute_data_brief(areas)
    assert "no clear direction" in brief


def test_compute_data_brief_empty():
    assert _compute_data_brief([]) == ""


def test_compute_data_brief_multiple_areas():
    areas = [
        {"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15},
        {"name": "Cost of Living", "in_favor": 80, "against": 64, "total": 144},
    ]
    brief = _compute_data_brief(areas)
    assert "Environment & Energy" in brief
    assert "Cost of Living" in brief
    assert "mostly against" in brief
    assert "leans in favor" in brief


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
            {"name": "Environment & Energy", "in_favor": 8, "against": 0, "total": 8},
            {"name": "Cost of Living", "in_favor": 3, "against": 1, "total": 4},
        ],
        top_supported=["Set military spending limits for 2026", "Fund clean energy research"],
        top_opposed=["Cancel an EPA rule on methane fees"],
    )
    assert "Gillibrand" in prompt
    assert "Environment & Energy" in prompt
    assert "Set military spending limits" in prompt
    assert "3" in prompt  # congresses covered count


def test_system_prompt_no_stat_repetition_rule():
    """System prompt tells AI not to repeat overall statistics."""
    assert "Do NOT mention total votes cast" in MEMBER_SUMMARY_SYSTEM_PROMPT


def test_build_prompt_no_yea_nay_lines():
    """Prompt no longer includes separate Yea/Nay stat lines."""
    service = MemberSummaryService(api_key=None)
    prompt = service._build_prompt(
        member_name="Test Member",
        chamber="Senate",
        state="New York",
        congresses=[119],
        stats={"total_votes": 100, "yea_count": 60, "nay_count": 40, "participation_rate": 95.0},
        top_areas=[],
        top_supported=[],
        top_opposed=[],
    )
    # Yea/Nay should not appear as separate stat lines
    assert "Yea:" not in prompt
    assert "Nay:" not in prompt
    assert "Participation rate:" not in prompt


def test_build_prompt_includes_data_constraints():
    """Prompt includes computed DATA CONSTRAINTS block."""
    service = MemberSummaryService(api_key=None)
    prompt = service._build_prompt(
        member_name="Test Member",
        chamber="Senate",
        state="New York",
        congresses=[119],
        stats={"total_votes": 100, "yea_count": 60, "nay_count": 40, "participation_rate": 95.0},
        top_areas=[
            {"name": "Environment & Energy", "in_favor": 3, "against": 12, "total": 15},
            {"name": "Cost of Living", "in_favor": 80, "against": 64, "total": 144},
        ],
        top_supported=["Test bill 1"],
        top_opposed=["Test bill 2"],
    )
    assert "DATA CONSTRAINTS" in prompt
    assert "mostly against" in prompt
    assert "leans in favor" in prompt


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
        top_areas=[{"name": "Environment & Energy", "in_favor": 8, "against": 0, "total": 8}],
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
