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


def test_ai_only_skips_congress_key_check():
    """--ai-only should not require CONGRESS_API_KEY.

    We verify this by checking the code structure: the --ai-only block
    must return before the CONGRESS_API_KEY check.
    """
    content = (PROJECT_ROOT / "sync.py").read_text()
    ai_only_return = content.find("if args.ai_only:")
    congress_key_check = content.find('CONGRESS_API_KEY not set')
    assert ai_only_return != -1, "--ai-only block should exist"
    assert congress_key_check != -1, "CONGRESS_API_KEY check should exist"
    assert ai_only_return < congress_key_check, \
        "--ai-only block should come before CONGRESS_API_KEY check"
    between = content[ai_only_return:congress_key_check]
    assert "return" in between, "--ai-only block should return before CONGRESS_API_KEY check"


def test_sync_states_constant_exists():
    """SYNC_STATES should be defined in sync.py with our 4 target states."""
    content = (PROJECT_ROOT / "sync.py").read_text()
    assert "SYNC_STATES" in content, "SYNC_STATES constant should exist in sync.py"
    assert '"NY"' in content, "SYNC_STATES should include NY"
    assert '"FL"' in content, "SYNC_STATES should include FL"
    assert '"CA"' in content, "SYNC_STATES should include CA"
    assert '"TX"' in content, "SYNC_STATES should include TX"
