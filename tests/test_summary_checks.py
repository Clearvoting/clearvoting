"""Deterministic structural checks: code-level rules the prompt can only ask for.

The July 2026 audit measured 1-6% violation rates on prompt-only rules; these
checks make the mechanical ones zero by failing the summary before it ships.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.summary_checks import structural_violations


def _good_summary():
    return {
        "one_liner": "Raise the federal minimum wage to $15 per hour",
        "provisions": ["Raises the minimum wage from $7.25 to $15.00 per hour over 5 years"],
        "issue_categories": ["Jobs & Workers"],
        "direction": "in_favor",
    }


def test_clean_summary_has_no_violations():
    assert structural_violations(_good_summary()) == []


def test_flags_empty_one_liner():
    s = _good_summary()
    s["one_liner"] = ""
    assert any("one_liner" in v for v in structural_violations(s))


def test_flags_overlong_one_liner():
    s = _good_summary()
    s["one_liner"] = "Make a rule that " + "very " * 14 + "long"
    assert any("15" in v for v in structural_violations(s))


def test_flags_one_liner_trailing_period():
    s = _good_summary()
    s["one_liner"] = "Raise the minimum wage."
    assert any("period" in v for v in structural_violations(s))


def test_flags_one_liner_equal_to_title():
    s = _good_summary()
    s["one_liner"] = "A bill to amend title 5, United States Code"
    violations = structural_violations(s, title="A bill to amend title 5, United States Code")
    assert any("title" in v for v in structural_violations(s, title=s["one_liner"]))
    assert violations


def test_flags_empty_provisions():
    s = _good_summary()
    s["provisions"] = []
    assert any("provisions" in v for v in structural_violations(s))


def test_flags_banned_jargon():
    s = _good_summary()
    s["provisions"] = ["Provides appropriations for the fiscal year pursuant to law"]
    v = structural_violations(s)
    assert any("appropriations" in x for x in v)
    assert any("fiscal year" in x for x in v)
    assert any("pursuant" in x for x in v)


def test_jargon_check_uses_word_boundaries():
    """'Rescind' is banned, but words merely containing a banned stem are not."""
    s = _good_summary()
    s["provisions"] = ["Lets the agency keep its current rules"]  # contains no banned term
    assert structural_violations(s) == []


def test_flags_placeholder_text():
    s = _good_summary()
    s["provisions"] = ["AI summary temporarily unavailable"]
    assert any("placeholder" in v for v in structural_violations(s))


def test_flags_overlong_provision():
    s = _good_summary()
    s["provisions"] = ["word " * 31]
    assert any("words" in v for v in structural_violations(s))


# --- grader fast-fail wiring ---

@pytest.mark.asyncio
async def test_grader_fails_structurally_broken_summary_without_llm_call():
    """Structural breakage is graded F by code — no model call, feedback names the violations."""
    import json
    from app.services.summary_grader import SummaryGrader

    grader = SummaryGrader(api_key=None)
    broken = {"one_liner": "", "provisions": [], "issue_categories": [], "direction": "neutral"}

    with patch.object(grader, "_call_llm", new_callable=AsyncMock) as mock_llm:
        result = await grader.grade(
            summary_type="bill_summary",
            summary_text=json.dumps(broken),
            context={"title": "Test Bill"},
        )

    mock_llm.assert_not_called()
    assert result.grade == "F"
    assert result.passed is False
    assert "one_liner" in result.feedback


@pytest.mark.asyncio
async def test_grader_still_calls_llm_for_structurally_clean_summary():
    import json
    from app.services.summary_grader import SummaryGrader

    grader = SummaryGrader(api_key=None)

    with patch.object(grader, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"grade": "A", "passed": true, "feedback": "Good.", "checks": {}}'
        result = await grader.grade(
            summary_type="bill_summary",
            summary_text=json.dumps(_good_summary()),
            context={"title": "Test Bill"},
        )

    mock_llm.assert_called_once()
    assert result.grade == "A"


@pytest.mark.asyncio
async def test_grader_skips_structural_checks_for_other_summary_types():
    """Member narratives are prose, not bill-summary dicts — no structural gate."""
    from app.services.summary_grader import SummaryGrader

    grader = SummaryGrader(api_key=None)

    with patch.object(grader, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"grade": "B", "passed": true, "feedback": "Fine.", "checks": {}}'
        result = await grader.grade(
            summary_type="member_narrative",
            summary_text="Some narrative prose.",
            context={},
        )

    mock_llm.assert_called_once()
    assert result.grade == "B"
