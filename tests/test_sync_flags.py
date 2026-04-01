# tests/test_sync_flags.py
"""Tests for sync.py CLI flags and configuration."""
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def test_sync_states_constant_exists():
    """SYNC_STATES should be defined in sync.py with our 4 target states."""
    content = (PROJECT_ROOT / "sync.py").read_text()
    assert "SYNC_STATES" in content, "SYNC_STATES constant should exist in sync.py"
    assert '"NY"' in content, "SYNC_STATES should include NY"
    assert '"FL"' in content, "SYNC_STATES should include FL"
    assert '"CA"' in content, "SYNC_STATES should include CA"
    assert '"TX"' in content, "SYNC_STATES should include TX"
