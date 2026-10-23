"""Tests for the claude CLI subprocess wrapper."""

import asyncio
import os
import stat
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import claude_cli


def _fake_proc():
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b'{"ok": true}', b""))
    proc.returncode = 0
    return proc


async def test_cli_call_ignores_user_level_settings(monkeypatch):
    """Running outside the project only skips *project* config. Without an empty
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


async def test_cli_env_drops_credentials_the_cli_never_uses(monkeypatch):
    """Prompts carry third-party bill text, so the subprocess must not hold the
    site's data/API/GitHub credentials. Its own CI login must survive."""
    stripped = (
        "CONGRESS_API_KEY", "FEC_API_KEY",
        "GOOGLE_SHEETS_CREDENTIALS_JSON", "GOOGLE_SHEETS_SPREADSHEET_ID",
        "GITHUB_TOKEN", "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    )
    for key in stripped:
        monkeypatch.setenv(key, "secret-" + key)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token")
    exec_mock = AsyncMock(return_value=_fake_proc())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", exec_mock)

    await claude_cli.call_claude_cli("system", "user")

    env = exec_mock.await_args.kwargs["env"]
    for key in stripped:
        assert key not in env
    assert not any(k.startswith("ACTIONS_") for k in env)
    assert not any(v.startswith("secret-") for v in env.values())
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "oauth-token"
    # PATH finds the binary; HOME holds the keychain login and transcripts.
    assert env["PATH"] == os.environ["PATH"]
    assert env["HOME"] == os.environ["HOME"]


@pytest.mark.parametrize("returncode", [0, 1])
async def test_cli_runs_in_private_temp_dir_and_removes_it(monkeypatch, returncode):
    """The shared /tmp holds other users' and sessions' files; each call gets
    its own owner-only directory, removed afterwards even when the CLI fails."""
    seen = {}

    async def fake_exec(*args, **kwargs):
        cwd = kwargs["cwd"]
        seen["cwd"] = cwd
        seen["mode"] = stat.S_IMODE(os.stat(cwd).st_mode)
        proc = _fake_proc()
        proc.returncode = returncode
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    if returncode:
        with pytest.raises(RuntimeError):
            await claude_cli.call_claude_cli("system", "user")
    else:
        await claude_cli.call_claude_cli("system", "user")

    assert os.path.realpath(seen["cwd"]) != os.path.realpath("/tmp")
    assert os.path.basename(seen["cwd"]).startswith("clearvote-claude-")
    assert seen["mode"] == 0o700
    assert not os.path.exists(seen["cwd"])
