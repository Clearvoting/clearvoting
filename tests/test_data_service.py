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
    assert "Taxes" in result["issue_categories"]


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


def test_get_member_vote_summary_direction_stance(data_service):
    """Verify effective stance: Yea on 'against' = against, Nay on 'in_favor' = against."""
    result = data_service.get_member_vote_summary("S001217")
    areas = result["top_policy_areas"]
    # HR 1 has direction=against, vote=Yea → against Taxation
    tax_area = next(a for a in areas if a["name"] == "Taxation")
    assert tax_area["against"] == 1
    assert tax_area["in_favor"] == 0
    # S 100 has direction=in_favor, vote=Nay → against Armed Forces
    armed_area = next(a for a in areas if a["name"] == "Armed Forces and National Security")
    assert armed_area["against"] == 1
    assert armed_area["in_favor"] == 0


def test_get_member_vote_summary_not_found(data_service):
    result = data_service.get_member_vote_summary("X999999")
    assert result is None


def test_get_bill_votes(data_service):
    result = data_service.get_bill_votes(119, "hr", 1)
    assert result is not None
    assert len(result["senate"]) == 1
    assert result["senate"][0]["vote_number"] == 372
    assert len(result["house"]) == 1
    assert result["house"][0]["vote_number"] == 99


def test_get_bill_votes_hjres(data_service):
    result = data_service.get_bill_votes(119, "hjres", 20)
    assert result is not None
    assert len(result["senate"]) == 1
    assert len(result["house"]) == 1


def test_get_bill_votes_not_found(data_service):
    result = data_service.get_bill_votes(119, "hr", 9999)
    assert result is None


def test_get_bill_votes_exact_number_match(data_service):
    # H.R. 1 must not match H.R. 1002 (substring collision)
    result = data_service.get_bill_votes(119, "hr", 1)
    senate_numbers = [v["vote_number"] for v in result["senate"]]
    assert 400 not in senate_numbers
    # And H.R. 1002 resolves to only its own vote
    result = data_service.get_bill_votes(119, "hr", 1002)
    assert [v["vote_number"] for v in result["senate"]] == [400]
    assert result["house"] == []


def test_get_bill_votes_filters_by_congress(data_service):
    # 119th H.R. 1 must exclude the 118th congress's H.R. 1 vote
    result = data_service.get_bill_votes(119, "hr", 1)
    for vote in result["senate"]:
        assert vote["congress"] == 119
    # 118th H.R. 1 returns only its own vote
    result = data_service.get_bill_votes(118, "hr", 1)
    assert [v["vote_number"] for v in result["senate"]] == [100]
    assert result["house"] == []


def test_get_bill_votes_returns_summary_fields_only(data_service):
    # Bill page only needs vote refs; member positions come from the votes API
    result = data_service.get_bill_votes(119, "hr", 1)
    vote = result["senate"][0]
    assert "members" not in vote
    assert set(vote.keys()) == {
        "congress", "session", "vote_number", "vote_date", "question", "result", "counts"
    }


def test_get_bill_votes_scans_directories_once(data_service, monkeypatch):
    # The bill->votes index is built once; later calls must not rescan the directories
    calls = {"count": 0}
    real_glob = Path.glob

    def counting_glob(self, pattern):
        calls["count"] += 1
        return real_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", counting_glob)
    data_service.get_bill_votes(119, "hr", 1)
    scans_after_first = calls["count"]
    assert scans_after_first > 0
    data_service.get_bill_votes(119, "hjres", 20)
    data_service.get_bill_votes(119, "hr", 9999)
    assert calls["count"] == scans_after_first


def test_get_member_narrative(data_service):
    result = data_service.get_member_narrative("S001217")
    assert result is not None
    assert result["bioguide_id"] == "S001217"
    assert "taxation" in result["narrative"].lower()
    assert len(result["top_areas"]) == 2
    assert result["top_areas"][0]["area"] == "Taxation"


def test_get_member_narrative_case_insensitive(data_service):
    result = data_service.get_member_narrative("s001217")
    assert result is not None
    assert result["bioguide_id"] == "S001217"


def test_get_member_narrative_not_found(data_service):
    result = data_service.get_member_narrative("X999999")
    assert result is None
