# tests/test_sync_flags.py
"""Tests for sync.py CLI flags and configuration."""
import pathlib
import subprocess
import sys

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def test_skip_ai_flag_accepted():
    """sync.py should accept --skip-ai without error."""
    result = subprocess.run(
        [sys.executable, "sync.py", "--help"],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    assert "--skip-ai" in result.stdout, "--skip-ai should appear in help text"


def test_skip_ai_and_ai_only_mutually_exclusive():
    """--skip-ai and --ai-only should not be usable together."""
    result = subprocess.run(
        [sys.executable, "sync.py", "--skip-ai", "--ai-only"],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    assert result.returncode != 0, "Should fail when both flags are provided"


def test_ai_only_flag_accepted():
    """sync.py should accept --ai-only without error."""
    result = subprocess.run(
        [sys.executable, "sync.py", "--help"],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    assert "--ai-only" in result.stdout, "--ai-only should appear in help text"


async def test_ai_only_skips_congress_key_check(monkeypatch, tmp_path):
    """--ai-only must run to completion without CONGRESS_API_KEY.

    AI steps are mocked and SYNC_DIR redirected to tmp_path so main() exercises
    only the --ai-only control flow. SystemExit(1) here would mean the
    CONGRESS_API_KEY check ran.
    """
    from unittest.mock import AsyncMock
    import sync as sync_module

    monkeypatch.delenv("CONGRESS_API_KEY", raising=False)
    monkeypatch.setattr(sync_module, "SYNC_DIR", tmp_path)
    monkeypatch.setattr(sync_module, "_ai_preflight", AsyncMock())
    for step in ("sync_bill_summaries", "sync_bill_arguments", "generate_scorecard_verdicts",
                 "sync_member_summaries", "check_page_coherence"):
        monkeypatch.setattr(sync_module, step, AsyncMock(return_value={}))
    monkeypatch.setattr(sys, "argv", ["sync.py", "--ai-only"])

    await sync_module.main()

    assert sync_module.sync_member_summaries.await_count == 1
    assert (tmp_path / "sync_metadata.json").exists()


async def test_ai_preflight_exits_on_dead_credential(monkeypatch):
    """A dead credential (expired OAuth token, revoked key) must abort with
    exit code 1 — not degrade into per-bill failures and a green run."""
    import pytest
    import sync as sync_module
    from app.services import claude_cli

    async def dead_cli(*args, **kwargs):
        raise RuntimeError("claude CLI error: 401 unauthorized")
    monkeypatch.setattr(claude_cli, "call_claude_cli", dead_cli)

    with pytest.raises(SystemExit) as exc:
        await sync_module._ai_preflight("")
    assert exc.value.code == 1


async def test_ai_preflight_passes_with_working_cli(monkeypatch):
    """A working CLI credential lets the preflight return normally."""
    import sync as sync_module
    from app.services import claude_cli

    async def ok_cli(*args, **kwargs):
        return "OK"
    monkeypatch.setattr(claude_cli, "call_claude_cli", ok_cli)

    await sync_module._ai_preflight("")


async def test_ai_only_fails_when_nothing_persists(monkeypatch, tmp_path):
    """--ai-only must exit non-zero when generations were attempted but none
    persisted (credential died mid-run, hard outage)."""
    from unittest.mock import AsyncMock
    import pytest
    import sync as sync_module

    monkeypatch.setattr(sync_module, "SYNC_DIR", tmp_path)
    monkeypatch.setattr(sync_module, "_ai_preflight", AsyncMock())
    failed_stats = {"total": 5, "passed": 0, "failed": 5, "needs_review": []}
    for step in ("sync_bill_summaries", "sync_bill_arguments", "sync_member_summaries"):
        monkeypatch.setattr(sync_module, step, AsyncMock(return_value=dict(failed_stats)))
    for step in ("generate_scorecard_verdicts", "check_page_coherence"):
        monkeypatch.setattr(sync_module, step, AsyncMock(return_value={}))
    monkeypatch.setattr(sys, "argv", ["sync.py", "--ai-only"])

    with pytest.raises(SystemExit) as exc:
        await sync_module.main()
    assert exc.value.code == 1


def test_sync_states_constant_exists():
    """SYNC_STATES should be defined in sync.py with our 4 target states."""
    content = (PROJECT_ROOT / "sync.py").read_text()
    assert "SYNC_STATES" in content, "SYNC_STATES constant should exist in sync.py"
    assert '"NY"' in content, "SYNC_STATES should include NY"
    assert '"FL"' in content, "SYNC_STATES should include FL"
    assert '"CA"' in content, "SYNC_STATES should include CA"
    assert '"TX"' in content, "SYNC_STATES should include TX"
