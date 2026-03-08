import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from sync import sync_members, sync_senate_votes, sync_bills_from_votes, build_member_votes, _parse_bill_ref


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


@pytest.mark.asyncio
async def test_sync_members_rate_limiting(tmp_path):
    """Verify rate limiting delay is called between API requests."""
    mock_client = MagicMock()
    mock_client.get_members_by_state = AsyncMock(side_effect=[
        {"members": [{"bioguideId": "A1", "terms": {"item": [{"chamber": "Senate"}]}}]},
        {"members": [{"bioguideId": "B1", "terms": {"item": [{"chamber": "Senate"}]}}]},
    ])

    import unittest.mock
    with unittest.mock.patch("sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await sync_members(mock_client, tmp_path, states=["FL", "NY"], rate_limit=0.1)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.1)


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


@pytest.mark.asyncio
async def test_sync_senate_votes_rate_limiting(tmp_path):
    """Verify rate limiting between Senate vote fetches."""
    mock_service = MagicMock()
    mock_service.get_vote = AsyncMock(side_effect=[
        {"congress": 119, "session": 1, "vote_number": 1, "vote_date": "2025-01-15",
         "question": "Test", "result": "Passed", "counts": {}, "members": []},
        Exception("No more"),
    ])

    import unittest.mock
    with unittest.mock.patch("sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await sync_senate_votes(mock_service, tmp_path, congress=119, session=1, max_vote=2, rate_limit=0.3)
        assert mock_sleep.call_count >= 1


# --- sync_bills_from_votes ---

@pytest.mark.asyncio
async def test_sync_bills_from_votes(tmp_path):
    """Only fetches bills that appear in Senate vote documents."""
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })
    _write_json(vote_dir / "119_1_00002.json", {
        "congress": 119, "session": 1, "vote_number": 2,
        "document": "S. 100", "vote_date": "2025-01-16",
        "question": "On Passage", "result": "Failed",
        "counts": {}, "members": [],
    })
    # Duplicate bill ref — should only fetch once
    _write_json(vote_dir / "119_1_00003.json", {
        "congress": 119, "session": 1, "vote_number": 3,
        "document": "H.R. 1", "vote_date": "2025-01-17",
        "question": "On the Motion", "result": "Passed",
        "counts": {}, "members": [],
    })

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock(side_effect=[
        {"bill": {"number": "1", "type": "HR", "congress": 119, "title": "Test Bill", "policyArea": {"name": "Taxation"}}},
        {"bill": {"number": "100", "type": "S", "congress": 119, "title": "Senate Bill", "policyArea": {"name": "Healthcare"}}},
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": [{"text": "Summary"}]})

    count = await sync_bills_from_votes(mock_client, tmp_path)

    bills_file = tmp_path / "bills.json"
    assert bills_file.exists()
    data = json.loads(bills_file.read_text())
    assert len(data["bills"]) == 2
    assert count == 2
    # Should have fetched exactly 2 unique bills
    assert mock_client.get_bill.call_count == 2


@pytest.mark.asyncio
async def test_sync_bills_from_votes_no_votes(tmp_path):
    """Handles missing vote directory gracefully."""
    mock_client = MagicMock()
    count = await sync_bills_from_votes(mock_client, tmp_path)
    assert count == 0


@pytest.mark.asyncio
async def test_sync_bills_from_votes_skips_existing(tmp_path):
    """Skips bills already in bills.json (incremental)."""
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })

    # Pre-existing bills.json with HR 1 already synced
    _write_json(tmp_path / "bills.json", {"bills": [
        {"number": "1", "type": "HR", "congress": 119, "title": "Already Here", "summaries": []},
    ]})

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock()  # Should not be called

    count = await sync_bills_from_votes(mock_client, tmp_path)

    assert count == 1  # 1 bill total (the existing one)
    assert mock_client.get_bill.call_count == 0  # No new fetches


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
             "state": "FL", "vote": "Yea", "lis_member_id": "S404"},
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
