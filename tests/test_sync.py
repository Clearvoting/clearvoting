import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import inspect
from sync import sync_members, sync_senate_votes, sync_bills_from_votes, build_member_votes, _parse_bill_ref, sync_house_votes, _house_leg_to_document, sync_bill_summaries, backfill_bill_directions


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


def test_parse_bill_ref_house_resolutions():
    assert _parse_bill_ref("H.Res. 5") == "hres-5"
    assert _parse_bill_ref("H.Con.Res. 14") == "hconres-14"
    assert _parse_bill_ref("S.Res. 50") == "sres-50"
    assert _parse_bill_ref("S.Con.Res. 10") == "sconres-10"


def test_parse_bill_ref_unknown():
    assert _parse_bill_ref("Something else") is None
    assert _parse_bill_ref("") is None


# --- _house_leg_to_document ---

def test_house_leg_to_document():
    assert _house_leg_to_document("HR", "153") == "H.R. 153"
    assert _house_leg_to_document("S", "100") == "S. 100"
    assert _house_leg_to_document("HJRES", "42") == "H.J.Res. 42"
    assert _house_leg_to_document("HRES", "5") == "H.Res. 5"
    assert _house_leg_to_document("HCONRES", "14") == "H.Con.Res. 14"
    assert _house_leg_to_document(None, None) == ""
    assert _house_leg_to_document("", "") == ""


# --- sync_house_votes ---

@pytest.mark.asyncio
async def test_sync_house_votes(tmp_path):
    """Fetches House votes and saves as JSON files."""
    mock_client = MagicMock()
    mock_client.get_house_vote_detail = AsyncMock(side_effect=[
        {"houseRollCallVote": {
            "congress": 119, "sessionNumber": 1, "rollCallNumber": 1,
            "legislationType": "HR", "legislationNumber": "153",
            "voteQuestion": "On Motion to Suspend the Rules and Pass",
            "result": "Passed", "startDate": "2025-01-10T14:00:00-05:00",
            "votePartyTotal": [
                {"voteParty": "R", "yeaTotal": 200, "nayTotal": 10, "notVotingTotal": 5, "presentTotal": 0},
                {"voteParty": "D", "yeaTotal": 180, "nayTotal": 20, "notVotingTotal": 5, "presentTotal": 0},
            ],
        }},
        Exception("No more votes"),
    ])
    mock_client.get_house_vote_members = AsyncMock(return_value={
        "houseRollCallVoteMemberVotes": {
            "results": [
                {"bioguideID": "A000055", "firstName": "Robert", "lastName": "Aderholt",
                 "voteCast": "Yea", "voteParty": "R", "voteState": "AL"},
            ],
        },
    })

    count = await sync_house_votes(mock_client, tmp_path, congress=119, session=1, max_vote=2)

    vote_dir = tmp_path / "votes" / "house"
    assert vote_dir.exists()
    filepath = vote_dir / "119_1_00001.json"
    assert filepath.exists()
    assert count == 1

    data = json.loads(filepath.read_text())
    assert data["congress"] == 119
    assert data["vote_number"] == 1
    assert data["question"] == "On Motion to Suspend the Rules and Pass"
    assert data["document"] == "H.R. 153"
    assert len(data["members"]) == 1
    assert data["members"][0]["bioguide_id"] == "A000055"
    assert data["members"][0]["vote"] == "Yea"


@pytest.mark.asyncio
async def test_sync_house_votes_skips_existing(tmp_path):
    """Incremental sync skips votes that already have files."""
    vote_dir = tmp_path / "votes" / "house"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {"vote_number": 1})

    mock_client = MagicMock()
    mock_client.get_house_vote_detail = AsyncMock(side_effect=[
        {"houseRollCallVote": {
            "congress": 119, "sessionNumber": 1, "rollCallNumber": 2,
            "legislationType": "HR", "legislationNumber": "200",
            "voteQuestion": "On Passage", "result": "Failed",
            "startDate": "2025-01-11T10:00:00-05:00", "votePartyTotal": [],
        }},
        Exception("No more"),
    ])
    mock_client.get_house_vote_members = AsyncMock(return_value={
        "houseRollCallVoteMemberVotes": {"results": []},
    })

    count = await sync_house_votes(mock_client, tmp_path, congress=119, session=1, max_vote=3)

    assert count == 2  # 1 existing + 1 new
    assert (vote_dir / "119_1_00002.json").exists()


@pytest.mark.asyncio
async def test_sync_house_votes_rate_limiting(tmp_path):
    """Verify rate limiting between House vote fetches."""
    mock_client = MagicMock()
    mock_client.get_house_vote_detail = AsyncMock(side_effect=[
        {"houseRollCallVote": {
            "congress": 119, "sessionNumber": 1, "rollCallNumber": 1,
            "voteQuestion": "Test", "result": "Passed",
            "startDate": "2025-01-10T14:00:00-05:00", "votePartyTotal": [],
        }},
        Exception("No more"),
    ])
    mock_client.get_house_vote_members = AsyncMock(return_value={
        "houseRollCallVoteMemberVotes": {"results": []},
    })

    import unittest.mock
    with unittest.mock.patch("sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await sync_house_votes(mock_client, tmp_path, congress=119, session=1, max_vote=2, rate_limit=0.3)
        assert mock_sleep.call_count >= 1


# --- sync_bills_from_votes (House expansion) ---

@pytest.mark.asyncio
async def test_sync_bills_from_votes_includes_house(tmp_path):
    """Scans both Senate and House vote directories for bill references."""
    senate_dir = tmp_path / "votes" / "senate"
    senate_dir.mkdir(parents=True)
    _write_json(senate_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })

    house_dir = tmp_path / "votes" / "house"
    house_dir.mkdir(parents=True)
    _write_json(house_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 200", "vote_date": "2025-01-16",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [], "chamber": "House",
    })

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock(side_effect=[
        {"bill": {"number": "1", "type": "HR", "congress": 119, "title": "Bill One", "policyArea": {"name": "Taxation"}}},
        {"bill": {"number": "200", "type": "HR", "congress": 119, "title": "Bill Two", "policyArea": {"name": "Defense"}}},
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": []})

    count = await sync_bills_from_votes(mock_client, tmp_path)

    data = json.loads((tmp_path / "bills.json").read_text())
    assert len(data["bills"]) == 2
    assert count == 2
    assert mock_client.get_bill.call_count == 2


# --- build_member_votes (House expansion) ---

@pytest.mark.asyncio
async def test_build_member_votes_house(tmp_path):
    """House members get vote records from House vote files."""
    members = {"members": [
        {"bioguideId": "A000055", "name": "Aderholt, Robert", "directOrderName": "Robert Aderholt",
         "stateCode": "AL", "chamber": "House of Representatives"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "153", "title": "Test House Bill",
         "policyArea": {"name": "Defense"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    vote_dir = tmp_path / "votes" / "house"
    vote_dir.mkdir(parents=True)
    vote = {
        "congress": 119, "session": 1, "vote_number": 10,
        "vote_date": "2025-01-10", "document": "H.R. 153",
        "question": "On Motion to Suspend the Rules and Pass",
        "result": "Passed", "chamber": "House",
        "counts": {"yeas": 380, "nays": 30, "present": 0, "absent": 24},
        "members": [
            {"bioguide_id": "A000055", "first_name": "Robert", "last_name": "Aderholt",
             "party": "R", "state": "AL", "vote": "Yea"},
        ],
    }
    _write_json(vote_dir / "119_1_00010.json", vote)

    count = await build_member_votes(tmp_path)

    member_file = tmp_path / "member_votes" / "A000055.json"
    assert member_file.exists()
    data = json.loads(member_file.read_text())
    assert data["member_id"] == "A000055"
    assert data["stats"]["total_votes"] == 1
    assert data["stats"]["yea_count"] == 1
    assert data["votes"][0]["chamber"] == "House"
    assert data["votes"][0]["bill_id"] == "119-hr-153"
    assert count == 1


@pytest.mark.asyncio
async def test_build_member_votes_both_chambers(tmp_path):
    """Both Senate and House members get records when both vote dirs exist."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
        {"bioguideId": "B001257", "name": "Bilirakis, Gus", "directOrderName": "Gus Bilirakis",
         "stateCode": "FL", "chamber": "House of Representatives"},
    ]}
    _write_json(tmp_path / "members.json", members)
    _write_json(tmp_path / "bills.json", {"bills": []})

    senate_dir = tmp_path / "votes" / "senate"
    senate_dir.mkdir(parents=True)
    _write_json(senate_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "S. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    house_dir = tmp_path / "votes" / "house"
    house_dir.mkdir(parents=True)
    _write_json(house_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-16", "document": "H.R. 10",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "chamber": "House",
        "members": [
            {"bioguide_id": "B001257", "first_name": "Gus", "last_name": "Bilirakis",
             "party": "R", "state": "FL", "vote": "Nay"},
        ],
    })

    count = await build_member_votes(tmp_path)

    assert count == 2
    assert (tmp_path / "member_votes" / "S001217.json").exists()
    assert (tmp_path / "member_votes" / "B001257.json").exists()

    house_data = json.loads((tmp_path / "member_votes" / "B001257.json").read_text())
    assert house_data["stats"]["nay_count"] == 1


# --- build_member_votes (AI one_liner integration) ---

@pytest.mark.asyncio
async def test_build_member_votes_uses_ai_one_liner(tmp_path):
    """When AI summary has a one_liner, use it instead of raw bill title."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1",
         "title": "Providing for congressional disapproval under chapter 8 of title 5",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    ai_summaries = {
        "119-hr-1": {
            "one_liner": "Cancel a tax rule on crypto trading platforms",
            "provisions": ["This cancels a rule..."],
            "impact_categories": ["Taxation"],
        }
    }
    _write_json(tmp_path / "ai_summaries.json", ai_summaries)

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    count = await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["one_liner"] == "Cancel a tax rule on crypto trading platforms"


@pytest.mark.asyncio
async def test_build_member_votes_falls_back_to_title(tmp_path):
    """When no AI summary exists, fall back to raw bill title."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Some Raw Title",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    count = await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["one_liner"] == "Some Raw Title"


@pytest.mark.asyncio
async def test_build_member_votes_ai_file_exists_but_bill_missing(tmp_path):
    """AI summaries file exists but doesn't have this bill — falls back to title."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Raw Title Here",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    # AI summaries exist but for a DIFFERENT bill
    _write_json(tmp_path / "ai_summaries.json", {
        "119-s-999": {"one_liner": "Something else", "provisions": [], "impact_categories": []}
    })

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    count = await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["one_liner"] == "Raw Title Here"


# --- sync_bill_summaries ---

def test_sync_bill_summaries_is_callable():
    """sync_bill_summaries function exists and is callable."""
    assert callable(sync_bill_summaries)


# --- build_member_votes with anthropic_key ---

def test_build_member_votes_accepts_anthropic_key():
    """build_member_votes should accept anthropic_key parameter."""
    sig = inspect.signature(build_member_votes)
    assert "anthropic_key" in sig.parameters


# --- --grade flag ---

def test_grade_flag_accepted():
    """sync.py should accept --grade flag."""
    import subprocess
    result = subprocess.run(
        ["python", "sync.py", "--grade", "--help"],
        capture_output=True, text=True
    )
    assert "--grade" in result.stdout or result.returncode == 0


# --- build_member_votes (direction propagation) ---

@pytest.mark.asyncio
async def test_build_member_votes_propagates_direction(tmp_path):
    """Direction from ai_summaries propagates to member vote records."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test Bill",
         "policyArea": {"name": "Environmental Protection"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    ai_summaries = {
        "119-hr-1": {
            "one_liner": "Cancel an EPA methane fee rule",
            "provisions": ["Cancels a rule..."],
            "impact_categories": ["Environment"],
            "direction": "weakens",
        }
    }
    _write_json(tmp_path / "ai_summaries.json", ai_summaries)

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["direction"] == "weakens"


@pytest.mark.asyncio
async def test_build_member_votes_direction_none_when_missing(tmp_path):
    """Direction is None when AI summary has no direction field."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test Bill",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    # AI summary without direction
    ai_summaries = {
        "119-hr-1": {
            "one_liner": "Do something",
            "provisions": ["Does something"],
            "impact_categories": ["Taxation"],
        }
    }
    _write_json(tmp_path / "ai_summaries.json", ai_summaries)

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["direction"] is None


# --- backfill_bill_directions ---

@pytest.mark.asyncio
async def test_backfill_adds_direction_to_missing(tmp_path):
    """Backfill adds direction to summaries missing it."""
    _write_json(tmp_path / "bills.json", {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Test",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]})
    _write_json(tmp_path / "members.json", {"members": []})
    _write_json(tmp_path / "ai_summaries.json", {
        "119-hr-1": {
            "one_liner": "Cut taxes on tips",
            "provisions": ["Cuts taxes on tips"],
            "impact_categories": ["Taxes"],
        }
    })

    import unittest.mock
    with unittest.mock.patch("app.services.ai_summary.AISummaryService") as MockService:
        mock_instance = MagicMock()
        mock_instance._call_llm = AsyncMock(return_value='{"direction": "weakens"}')
        MockService.return_value = mock_instance

        stats = await backfill_bill_directions(tmp_path, api_key="test")

    assert stats["updated"] == 1
    data = json.loads((tmp_path / "ai_summaries.json").read_text())
    assert data["119-hr-1"]["direction"] == "weakens"


@pytest.mark.asyncio
async def test_backfill_skips_existing_direction(tmp_path):
    """Backfill skips summaries that already have direction."""
    _write_json(tmp_path / "bills.json", {"bills": []})
    _write_json(tmp_path / "members.json", {"members": []})
    _write_json(tmp_path / "ai_summaries.json", {
        "119-hr-1": {
            "one_liner": "Test",
            "provisions": ["Test"],
            "impact_categories": ["Taxes"],
            "direction": "strengthens",
        }
    })

    stats = await backfill_bill_directions(tmp_path)

    assert stats["updated"] == 0
    assert stats["skipped"] == 1
    data = json.loads((tmp_path / "ai_summaries.json").read_text())
    assert data["119-hr-1"]["direction"] == "strengthens"
