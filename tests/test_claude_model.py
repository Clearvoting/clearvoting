"""Regression guard: every Claude call site uses the shared CLAUDE_MODEL constant.

Hardcoded date-suffixed model IDs retire and break all AI generation at
once — the model lives in one place: grader_common.
"""

import inspect

from app.services import (
    ai_summary,
    arguments_grader,
    bill_arguments,
    claude_cli,
    grader_common,
    member_narrative_grader,
    member_summary,
    page_coherence,
    summary_grader,
    vote_one_liner,
)

CLAUDE_SERVICE_MODULES = [
    ai_summary,
    arguments_grader,
    bill_arguments,
    claude_cli,
    member_narrative_grader,
    member_summary,
    page_coherence,
    summary_grader,
    vote_one_liner,
]


def test_claude_model_is_undated_alias():
    assert grader_common.CLAUDE_MODEL == "claude-sonnet-5-5"


def test_reply_text_skips_leading_thinking_block():
    """Sonnet 5.5 thinks by default: an API reply can open with a thinking block whose
    text is empty (display "omitted"), so content[0].text is not the reply."""
    from types import SimpleNamespace

    response = SimpleNamespace(content=[
        SimpleNamespace(type="thinking", thinking="", signature="sig"),
        SimpleNamespace(type="text", text='{"grade": "A"}'),
    ])
    assert grader_common.reply_text(response) == '{"grade": "A"}'


def test_api_call_sites_read_reply_by_type_and_size_for_thinking():
    for module in CLAUDE_SERVICE_MODULES:
        source = inspect.getsource(module)
        assert "content[0]" not in source, (
            f"{module.__name__} reads the API reply by position; use reply_text()"
        )
        if "messages.create(" in source:
            assert "max_tokens=MAX_TOKENS" in source, (
                f"{module.__name__} sizes max_tokens for the reply only; thinking counts too"
            )


def test_all_services_use_shared_model_constant():
    for module in CLAUDE_SERVICE_MODULES:
        assert getattr(module, "CLAUDE_MODEL", None) == grader_common.CLAUDE_MODEL, (
            f"{module.__name__} does not import CLAUDE_MODEL from grader_common"
        )
        source = inspect.getsource(module)
        assert 'model="claude' not in source, (
            f"{module.__name__} hardcodes a model string instead of using CLAUDE_MODEL"
        )


def test_claude_cli_default_model_is_shared_constant():
    default = inspect.signature(claude_cli.call_claude_cli).parameters["model"].default
    assert default == grader_common.CLAUDE_MODEL
