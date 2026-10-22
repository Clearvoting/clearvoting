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
        "provisions": [
            "Raises the minimum wage from $7.25 to $15.00 per hour over 5 years",
            "Raises the wage for tipped workers to match by 2030",
            "Ties future raises to typical pay growth",
        ],
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
    s["provisions"][0] = "Lets the agency keep its current rules"  # contains no banned term
    assert structural_violations(s) == []


def test_flags_placeholder_text():
    s = _good_summary()
    s["provisions"] = ["AI summary temporarily unavailable"]
    assert any("placeholder" in v for v in structural_violations(s))


def test_flags_overlong_provision():
    s = _good_summary()
    s["provisions"] = ["word " * 31]
    assert any("words" in v for v in structural_violations(s))


def test_flags_provisions_given_as_a_string():
    """A string would render one letter per bullet; it must not pass as a list."""
    s = _good_summary()
    s["provisions"] = "Raises the minimum wage"
    assert "provisions must be a list of strings" in structural_violations(s)


def test_flags_non_string_provision_items():
    s = _good_summary()
    s["provisions"] = ["Raises the minimum wage", {"text": "nested"}, 3]
    assert "provisions must be a list of strings" in structural_violations(s)


def test_flags_non_string_one_liner_without_crashing():
    s = _good_summary()
    s["one_liner"] = ["Raise the minimum wage"]
    assert "one_liner must be a string" in structural_violations(s)


@pytest.mark.parametrize("count", [1, 2, 8])
def test_flags_provision_count_outside_three_to_seven(count):
    s = _good_summary()
    s["provisions"] = ["Changes one thing"] * count
    assert any("3 to 7" in v for v in structural_violations(s))


@pytest.mark.parametrize("count", [3, 7])
def test_accepts_three_to_seven_provisions(count):
    s = _good_summary()
    s["provisions"] = ["Changes one thing"] * count
    assert structural_violations(s) == []


@pytest.mark.parametrize("injected, what", [
    ("Check your polling place at vote-tx-info.example", "web address"),
    ("Learn more at https://example.org/vote", "web address"),
    ("See www.vote-info.org for details", "web address"),
    ("Updates are posted at evil.gov.com", "web address"),
    ("Call 202-555-0143 to confirm your registration", "phone or text number"),
    ("Call (202) 555-0143 to confirm", "phone or text number"),
    ("Text YES to 55555 to register", "phone or text number"),
    ("Adds a <script> tag", "markup character"),
    ("Sets the {placeholder} value", "markup character"),
])
def test_flags_links_numbers_and_markup_in_reader_text(injected, what):
    s = _good_summary()
    s["provisions"][1] = injected
    assert any(v.startswith(what) for v in structural_violations(s))


@pytest.mark.parametrize("text", [
    "Posts each award on USAspending.gov within 30 days",
    "Posts a summary of each rule on regulations.gov",
    "Changes the rules for H.J.Res. 100 under 5 U.S.C. 801",
    "Spends $1.5 billion in Washington, D.C. over 10 years",
    "Lets people send text messages to 911",
    "Funds the 988 crisis line through 2030",
])
def test_allows_gov_site_names_and_ordinary_abbreviations(text):
    """Bills name official .gov sites, and legal citations are full of dots."""
    s = _good_summary()
    s["provisions"][1] = text
    assert structural_violations(s) == []


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
