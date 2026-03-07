import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from sync import sync_members, sync_bills, sync_senate_votes, sync_ai_summaries, build_member_votes, _parse_bill_ref


def _write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


# --- sync_members ---

@pytest.mark.asyncio
async def test_sync_members(tmp_path):
    mock_client = MagicMock()
    mock_client.get_members_by_state = AsyncMock(side_effect=[
        {"members": [{"bioguideId": "S001217", "name": "Scott, Rick", "state": "Florida", "terms": {"item": [{"chamber": "Senate"}]}}]},
        {"members": [{"bioguideId": "S000148", "name": "Schumer, Charles", "state": "New York", "terms": {"item": [{"chamber": "Senate"}]}}]},
    ])

    count = await sync_members(mock_client, tmp_path, states=["FL", "NY"])

    members_file = tmp_path / "members.json"
    assert members_file.exists()
    data = json.loads(members_file.read_text())
    assert len(data["members"]) == 2
    assert count == 2
    # Verify stateCode and chamber were added
    assert data["members"][0]["stateCode"] == "FL"
    assert data["members"][0]["chamber"] == "Senate"


@pytest.mark.asyncio
async def test_sync_members_handles_api_error(tmp_path):
    mock_client = MagicMock()
    mock_client.get_members_by_state = AsyncMock(side_effect=[
        {"members": [{"bioguideId": "S001217", "name": "Scott", "terms": {"item": []}}]},
        Exception("API error"),
    ])

    count = await sync_members(mock_client, tmp_path, states=["FL", "NY"])

    data = json.loads((tmp_path / "members.json").read_text())
    assert len(data["members"]) == 1
    assert count == 1


# --- sync_bills ---

@pytest.mark.asyncio
async def test_sync_bills(tmp_path):
    mock_client = MagicMock()
    mock_client.get_bills = AsyncMock(side_effect=[
        {"bills": [
            {"number": "1", "type": "HR", "congress": 119, "title": "Test Bill"},
            {"number": "100", "type": "S", "congress": 119, "title": "Another Bill"},
        ]},
        {"bills": []},
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": [{"text": "Summary text"}]})

    count = await sync_bills(mock_client, tmp_path)

    bills_file = tmp_path / "bills.json"
    assert bills_file.exists()
    data = json.loads(bills_file.read_text())
    assert len(data["bills"]) == 2
    assert count == 2
    # Verify summaries were fetched
    assert len(data["bills"][0]["summaries"]) == 1


# --- sync_senate_votes ---

@pytest.mark.asyncio
async def test_sync_senate_votes(tmp_path):
    mock_service = MagicMock()
    mock_service.get_vote = AsyncMock(side_effect=[
        {
            "congress": 119, "session": 1, "vote_number": 1,
            "vote_date": "2025-01-15", "question": "On Passage",
            "result": "Passed", "counts": {"yeas": 60, "nays": 40, "present": 0, "absent": 0},
            "members": [{"first_name": "Test", "last_name": "Sen", "party": "D", "state": "NY", "vote": "Yea"}],
        },
        Exception("Vote not found"),
    ])

    count = await sync_senate_votes(mock_service, tmp_path, congress=119, session=1, max_vote=2)

    vote_dir = tmp_path / "votes" / "senate"
    assert vote_dir.exists()
    assert (vote_dir / "119_1_00001.json").exists()
    assert count == 1


@pytest.mark.asyncio
async def test_sync_senate_votes_skips_existing(tmp_path):
    """Incremental sync skips votes that already have files."""
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {"vote_number": 1})

    mock_service = MagicMock()
    mock_service.get_vote = AsyncMock(side_effect=[
        {
            "congress": 119, "session": 1, "vote_number": 2,
            "vote_date": "2025-01-16", "question": "On Passage",
            "result": "Failed", "counts": {"yeas": 40, "nays": 60, "present": 0, "absent": 0},
            "members": [],
        },
        Exception("No more"),
    ])

    count = await sync_senate_votes(mock_service, tmp_path, congress=119, session=1, max_vote=3)

    # Vote 1 was skipped (existing), vote 2 was fetched, vote 3 failed
    assert count == 2
    assert (vote_dir / "119_1_00002.json").exists()


# --- sync_ai_summaries ---

@pytest.mark.asyncio
async def test_sync_ai_summaries(tmp_path):
    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test Bill", "summaries": [{"text": "Official summary"}]},
        {"congress": 119, "type": "S", "number": "50", "title": "Another", "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    # Existing summaries (should be skipped)
    existing = {"119-hr-1": {"provisions": ["Already done"], "impact_categories": ["Taxes"]}}
    _write_json(tmp_path / "ai_summaries.json", existing)

    mock_ai = MagicMock()
    mock_ai.generate_summary = AsyncMock(return_value={
        "provisions": ["New summary"], "impact_categories": ["Healthcare"]
    })

    mock_congress = MagicMock()
    mock_congress.get_bill_text = AsyncMock(return_value={"textVersions": []})

    count = await sync_ai_summaries(mock_ai, mock_congress, tmp_path)

    data = json.loads((tmp_path / "ai_summaries.json").read_text())
    assert "119-hr-1" in data
    assert data["119-hr-1"]["provisions"] == ["Already done"]  # Not overwritten
    assert "119-s-50" in data  # New one added
    assert count == 1


@pytest.mark.asyncio
async def test_sync_ai_summaries_no_bills(tmp_path):
    """Skips gracefully when no bills.json exists."""
    mock_ai = MagicMock()
    mock_congress = MagicMock()

    count = await sync_ai_summaries(mock_ai, mock_congress, tmp_path)
    assert count == 0


# --- build_member_votes ---

@pytest.mark.asyncio
async def test_build_member_votes(tmp_path):
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott", "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test Bill",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    vote = {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {"yeas": 60, "nays": 40, "present": 0, "absent": 0},
        "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R",
             "state": "FL", "vote": "Yea", "lis_member_id": "S001217"},
        ],
    }
    _write_json(vote_dir / "119_1_00001.json", vote)

    count = await build_member_votes(tmp_path)

    member_votes_dir = tmp_path / "member_votes"
    assert member_votes_dir.exists()
    s_file = member_votes_dir / "S001217.json"
    assert s_file.exists()
    data = json.loads(s_file.read_text())
    assert data["member_id"] == "S001217"
    assert data["stats"]["total_votes"] == 1
    assert data["stats"]["yea_count"] == 1
    assert len(data["votes"]) == 1
    assert data["votes"][0]["bill_id"] == "119-hr-1"
    assert count == 1


@pytest.mark.asyncio
async def test_build_member_votes_no_members(tmp_path):
    """Skips gracefully when no members.json exists."""
    count = await build_member_votes(tmp_path)
    assert count == 0


# --- _parse_bill_ref ---

def test_parse_bill_ref_hr():
    assert _parse_bill_ref("H.R. 1") == "hr-1"
    assert _parse_bill_ref("H.R. 1234") == "hr-1234"


def test_parse_bill_ref_senate():
    assert _parse_bill_ref("S. 100") == "s-100"


def test_parse_bill_ref_joint_resolutions():
    assert _parse_bill_ref("H.J.Res. 42") == "hjres-42"
    assert _parse_bill_ref("S.J.Res. 10") == "sjres-10"


def test_parse_bill_ref_unknown():
    assert _parse_bill_ref("Something else") is None
    assert _parse_bill_ref("") is None
