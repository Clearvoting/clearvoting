"""Tests for the claude CLI subprocess wrapper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services import claude_cli


def _fake_proc():
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b'{"ok": true}', b""))
    proc.returncode = 0
    return proc


async def test_cli_call_ignores_user_level_settings(monkeypatch):
    """Running from /tmp only skips *project* config. Without an empty
    --setting-sources, user-level plugin hooks (e.g. the explanatory output
    style) and the owner's ~/.claude/CLAUDE.md inject prose instructions into
    every grader/writer call."""
    exec_mock = AsyncMock(return_value=_fake_proc())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", exec_mock)

    await claude_cli.call_claude_cli("system", "user")

    args = list(exec_mock.await_args.args)
    assert args[:2] == ["claude", "-p"]
    i = args.index("--setting-sources")
    assert args[i + 1] == ""
    # --bare also isolates, but it disables OAuth/keychain auth and would
    # break both the local Max-plan login and CLAUDE_CODE_OAUTH_TOKEN in CI.
    assert "--bare" not in args
    # Saved transcripts are the only record of raw LLM output for debugging.
    assert "--no-session-persistence" not in args


async def test_cli_call_disables_tools(monkeypatch):
    """Grader/writer calls are single-shot JSON; none of 895 saved sessions
    ever used a tool. Tool definitions still cost ~15k prompt tokens a call."""
    exec_mock = AsyncMock(return_value=_fake_proc())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", exec_mock)

    await claude_cli.call_claude_cli("system", "user")

    args = list(exec_mock.await_args.args)
    i = args.index("--tools")
    assert args[i + 1] == ""
    # --tools only covers built-ins; the account's claude.ai connectors
    # (Gmail, Drive, ...) still attach unless MCP config is made strict.
    assert "--strict-mcp-config" in args
