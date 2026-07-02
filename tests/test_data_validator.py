"""Sync-time data validation: bad data must fail the sync, not deploy quietly.

Encodes the July 2026 incidents as assertions: scorecard wipes, display-string
dates, lexicographic sort, placeholder summaries, silent summary loss.
"""
import json
from pathlib import Path

import pytest

from app.services.data_validator import validate_synced_data


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _good_sync_dir(tmp_path: Path) -> Path:
    d = tmp_path / "synced"
    _write(d / "members.json", {"members": [
        {"bioguideId": "S000148", "name": "Schumer", "stateCode": "NY", "chamber": "Senate"},
    ]})
    _write(d / "bills.json", {"bills": [
        {"congress": 119, "type": "S", "number": "2", "title": "Secure America Act"},
    ]})
    _write(d / "ai_summaries.json", {"119-s-2": {
        "one_liner": "Fund border patrol through 2029",
        "provisions": ["Gives money to border agencies"],
        "issue_categories": ["Immigration"], "direction": "in_favor",
    }})
    _write(d / "member_votes" / "S000148.json", {
        "member_id": "S000148",
        "stats": {"total_votes": 2, "yea_count": 1, "nay_count": 1, "not_voting_count": 0, "participation_rate": 100.0},
        "scorecard": [{"category": "Immigration", "verdict": "x"}],
        "votes": [
            {"bill_number": "S. 2", "date": "2026-06-24T22:30:00", "vote": "Yea", "vote_number": 129},
            {"bill_number": "S. 1", "date": "2025-09-09T18:46:00", "vote": "Nay", "vote_number": 511},
        ],
    })
    return d


def test_good_data_passes(tmp_path):
    failures, warnings = validate_synced_data(_good_sync_dir(tmp_path))
    assert failures == []


def test_placeholder_summary_fails(tmp_path):
    d = _good_sync_dir(tmp_path)
    data = json.loads((d / "ai_summaries.json").read_text())
    data["119-s-2"]["provisions"] = ["AI summary temporarily unavailable"]
    _write(d / "ai_summaries.json", data)
    failures, _ = validate_synced_data(d)
    assert any("placeholder" in f for f in failures)


def test_non_iso_vote_date_fails(tmp_path):
    d = _good_sync_dir(tmp_path)
    mv = json.loads((d / "member_votes" / "S000148.json").read_text())
    mv["votes"][0]["date"] = "September 9, 2025,  06:46 PM"
    _write(d / "member_votes" / "S000148.json", mv)
    failures, _ = validate_synced_data(d)
    assert any("ISO" in f for f in failures)


def test_mis_sorted_votes_fail(tmp_path):
    d = _good_sync_dir(tmp_path)
    mv = json.loads((d / "member_votes" / "S000148.json").read_text())
    mv["votes"].reverse()  # oldest first — wrong
    _write(d / "member_votes" / "S000148.json", mv)
    failures, _ = validate_synced_data(d)
    assert any("sort" in f.lower() for f in failures)


def test_missing_member_votes_file_fails(tmp_path):
    d = _good_sync_dir(tmp_path)
    (d / "member_votes" / "S000148.json").unlink()
    failures, _ = validate_synced_data(d)
    assert any("S000148" in f for f in failures)


def test_orphan_member_votes_file_warns_not_fails(tmp_path):
    d = _good_sync_dir(tmp_path)
    _write(d / "member_votes" / "C001127.json", {"member_id": "C001127", "votes": [], "scorecard": []})
    failures, warnings = validate_synced_data(d)
    assert failures == []
    assert any("C001127" in w for w in warnings)


def test_summary_loss_vs_previous_fails(tmp_path):
    """A sync must never drop a summary that previously existed."""
    d = _good_sync_dir(tmp_path)
    previous = {"119-s-2": {"one_liner": "x"}, "119-s-99": {"one_liner": "y"}}
    failures, _ = validate_synced_data(d, previous_summaries=previous)
    assert any("119-s-99" in f for f in failures)


def test_scorecard_wipe_vs_previous_fails(tmp_path):
    """A rebuild must never reduce the number of members with scorecards."""
    d = _good_sync_dir(tmp_path)
    mv = json.loads((d / "member_votes" / "S000148.json").read_text())
    mv["scorecard"] = []
    _write(d / "member_votes" / "S000148.json", mv)
    failures, _ = validate_synced_data(d, previous_scorecard_members={"S000148"})
    assert any("scorecard" in f.lower() for f in failures)


def test_empty_one_liner_in_data_fails(tmp_path):
    d = _good_sync_dir(tmp_path)
    data = json.loads((d / "ai_summaries.json").read_text())
    data["119-s-2"]["one_liner"] = ""
    _write(d / "ai_summaries.json", data)
    failures, _ = validate_synced_data(d)
    assert any("one_liner" in f for f in failures)


def test_validate_step_is_wired():
    """sync.py exposes the validate step."""
    import sync
    assert callable(sync.run_validation)
