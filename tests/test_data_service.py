import pytest
from pathlib import Path
from app.services.data_service import DataService

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


@pytest.fixture
def data_service():
    return DataService(data_dir=FIXTURES)


def test_get_members_by_state(data_service):
    result = data_service.get_members_by_state("FL")
    assert len(result["members"]) == 2
    assert all(m["stateCode"] == "FL" for m in result["members"])


def test_get_members_by_state_not_found(data_service):
    result = data_service.get_members_by_state("ZZ")
    assert result["members"] == []


def test_get_member_detail(data_service):
    result = data_service.get_member_detail("S001217")
    assert result["member"]["bioguideId"] == "S001217"
    assert result["member"]["directOrderName"] == "Rick Scott"


def test_get_member_detail_not_found(data_service):
    result = data_service.get_member_detail("X999999")
    assert result is None


def test_get_member_votes(data_service):
    result = data_service.get_member_votes("S001217")
    assert result["member_id"] == "S001217"
    assert result["stats"]["total_votes"] == 2
    assert len(result["votes"]) == 2


def test_get_member_votes_not_found(data_service):
    result = data_service.get_member_votes("X999999")
    assert result is None


def test_get_bills(data_service):
    result = data_service.get_bills()
    assert len(result["bills"]) == 3


def test_get_bills_pagination(data_service):
    result = data_service.get_bills(offset=0, limit=1)
    assert len(result["bills"]) == 1


def test_get_bill_detail(data_service):
    result = data_service.get_bill_detail(119, "hr", 1)
    assert result is not None
    assert result["bill"]["title"] == "One Big Beautiful Bill Act"


def test_get_bill_detail_not_found(data_service):
    result = data_service.get_bill_detail(119, "hr", 9999)
    assert result is None


def test_get_ai_summary(data_service):
    result = data_service.get_ai_summary(119, "hr", 1)
    assert result is not None
    assert len(result["provisions"]) == 2
    assert "Taxes" in result["impact_categories"]


def test_get_ai_summary_not_found(data_service):
    result = data_service.get_ai_summary(119, "s", 9999)
    assert result is None


def test_get_senate_vote(data_service):
    result = data_service.get_senate_vote(119, 1, 372)
    assert result is not None
    assert result["vote_number"] == 372
    assert len(result["members"]) == 2


def test_get_senate_vote_not_found(data_service):
    result = data_service.get_senate_vote(119, 1, 999)
    assert result is None


def test_get_members_by_district(data_service):
    result = data_service.get_members_by_district("FL", 19)
    assert len(result["members"]) == 1
    assert result["members"][0]["bioguideId"] == "D000032"


def test_get_sync_metadata(data_service):
    result = data_service.get_sync_metadata()
    assert result["members_count"] == 3
    assert "last_sync" in result


def test_get_member_vote_summary(data_service):
    result = data_service.get_member_vote_summary("S001217")
    assert result["member_id"] == "S001217"
    assert result["stats"]["total_votes"] == 2
    assert result["stats"]["participation_rate"] == 100.0
    areas = result["top_policy_areas"]
    assert len(areas) == 2
    names = [a["name"] for a in areas]
    assert "Taxation" in names
    assert "Armed Forces and National Security" in names
    tax_area = next(a for a in areas if a["name"] == "Taxation")
    assert tax_area["yea"] == 1
    assert tax_area["nay"] == 0
    assert tax_area["total"] == 1
    armed_area = next(a for a in areas if a["name"] == "Armed Forces and National Security")
    assert armed_area["yea"] == 0
    assert armed_area["nay"] == 1
    assert armed_area["total"] == 1


def test_get_member_vote_summary_not_found(data_service):
    result = data_service.get_member_vote_summary("X999999")
    assert result is None


def test_get_bill_votes(data_service):
    result = data_service.get_bill_votes(119, "hr", 1)
    assert result is not None
    assert len(result["senate"]) == 1
    assert "house" in result


def test_get_bill_votes_hjres(data_service):
    result = data_service.get_bill_votes(119, "hjres", 20)
    assert result is not None
    assert len(result["senate"]) == 1
    assert len(result["house"]) == 1


def test_get_bill_votes_not_found(data_service):
    result = data_service.get_bill_votes(119, "hr", 9999)
    assert result is None
