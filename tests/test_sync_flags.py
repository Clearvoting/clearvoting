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


def test_sync_states_constant_exists():
    """SYNC_STATES should be defined in sync.py with our 4 target states."""
    content = (PROJECT_ROOT / "sync.py").read_text()
    assert "SYNC_STATES" in content, "SYNC_STATES constant should exist in sync.py"
    assert '"NY"' in content, "SYNC_STATES should include NY"
    assert '"FL"' in content, "SYNC_STATES should include FL"
    assert '"CA"' in content, "SYNC_STATES should include CA"
    assert '"TX"' in content, "SYNC_STATES should include TX"
