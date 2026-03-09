"""Wrapper to call Claude via the CLI using the user's Max plan.

When no ANTHROPIC_API_KEY is configured, the AI services fall back
to calling the `claude` CLI which uses the user's Claude Max
subscription — no API billing required.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def call_claude_cli(
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Call Claude via the CLI. Pipes prompt via stdin to handle long inputs."""
    full_prompt = f"<system>\n{system_prompt}\n</system>\n\n{user_prompt}"

    # Remove CLAUDECODE env var to allow nested CLI invocation
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    proc = await asyncio.create_subprocess_exec(
        "claude", "-p",
        "--output-format", "text",
        "--model", model,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate(input=full_prompt.encode("utf-8"))

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8").strip()
        stdout_msg = stdout.decode("utf-8").strip()
        full_error = error_msg or stdout_msg or f"exit code {proc.returncode}"
        logger.error("claude CLI failed (exit %d): %s", proc.returncode, full_error)
        raise RuntimeError(f"claude CLI error: {full_error}")

    return stdout.decode("utf-8").strip()
