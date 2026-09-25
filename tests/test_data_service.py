import json
import logging
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
    # Real members.json has no directOrderName; display names come from render.display_name.
    assert result["member"]["name"] == "Scott, Rick"
    assert "directOrderName" not in result["member"]


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
    fixture_bills = json.loads((FIXTURES / "bills.json").read_text())["bills"]
    # Default page size is 20; the real-data fixtures hold more bills than that.
    assert len(result["bills"]) == min(len(fixture_bills), 20)


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


def _write_bills(tmp_path, bills):
    (tmp_path / "bills.json").write_text(json.dumps({"bills": bills}))


def test_get_bills_sorted_newest_first(tmp_path):
    # File order is deliberately scrambled; load must sort by latestAction.actionDate desc
    _write_bills(tmp_path, [
        {"congress": 118, "type": "HR", "number": "5", "title": "Old Bill",
         "latestAction": {"actionDate": "2024-03-12", "text": "Became law"}},
        {"congress": 119, "type": "S", "number": "9", "title": "No Action Bill"},
        {"congress": 119, "type": "HR", "number": "2", "title": "Newest Bill",
         "latestAction": {"actionDate": "2025-05-30", "text": "Passed House"}},
        {"congress": 119, "type": "HR", "number": "3", "title": "No Date Bill",
         "latestAction": {"text": "Introduced"}},
        {"congress": 119, "type": "HR", "number": "4", "title": "Mid Bill",
         "latestAction": {"actionDate": "2025-01-15", "text": "Introduced"}},
    ])
    service = DataService(data_dir=tmp_path)
    numbers = [b["number"] for b in service.get_bills(limit=10)["bills"]]
    # Newest first; bills without an action date sort last (in original file order)
    assert numbers == ["2", "4", "5", "9", "3"]


def test_get_bills_congress_filter(tmp_path):
    _write_bills(tmp_path, [
        {"congress": 119, "type": "HR", "number": "1", "title": "New Bill",
         "latestAction": {"actionDate": "2025-05-22"}},
        {"congress": 118, "type": "HR", "number": "5", "title": "Old Bill",
         "latestAction": {"actionDate": "2024-03-12"}},
    ])
    service = DataService(data_dir=tmp_path)
    result = service.get_bills(congress=118)
    assert [b["number"] for b in result["bills"]] == ["5"]
    # Omitting congress returns all bills
    assert len(service.get_bills()["bills"]) == 2


def test_get_house_vote(data_service):
    result = data_service.get_house_vote(119, 1, 99)
    assert result is not None
    assert result["vote_number"] == 99
    assert len(result["members"]) == 1


def test_get_house_vote_not_found(data_service):
    result = data_service.get_house_vote(119, 1, 999)
    assert result is None


def test_load_logs_error_when_members_or_bills_empty(tmp_path, caplog):
    # Missing/empty data files must log loudly but not crash (degraded site still boots)
    with caplog.at_level(logging.ERROR, logger="app.services.data_service"):
        service = DataService(data_dir=tmp_path)
    assert service.get_bills()["bills"] == []
    messages = [r.getMessage() for r in caplog.records]
    assert any("members" in m for m in messages)
    assert any("bills" in m for m in messages)


def test_load_populated_data_logs_no_errors(caplog):
    with caplog.at_level(logging.ERROR, logger="app.services.data_service"):
        DataService(data_dir=FIXTURES)
    assert not caplog.records


# --- Withheld summaries, seats and the official summary (plan T1.5; spec §2.5 C, §7.4, §10 #10) ---

def _ai_fixture() -> dict:
    return json.loads((FIXTURES / "ai_summaries.json").read_text())


def test_displayable_summary_withholds_needs_review(data_service):
    summaries = _ai_fixture()
    withheld = next(k for k, v in summaries.items() if v.get("needs_review"))
    shown = next(k for k, v in summaries.items() if not v.get("needs_review"))
    assert data_service.displayable_summary(shown) == summaries[shown]
    assert data_service.displayable_summary(withheld) is None
    assert data_service.displayable_summary("119-hr-999999") is None


def _summary_dir(tmp_path: Path) -> Path:
    d = tmp_path / "synced"
    d.mkdir()
    (d / "bills.json").write_text(json.dumps({"bills": [
        {"congress": 119, "type": "HR", "number": "10", "title": "Shown Act", "latestAction": {"actionDate": "2026-09-01"}},
        {"congress": 119, "type": "HR", "number": "11", "title": "Withheld Act", "latestAction": {"actionDate": "2026-08-01"}},
        {"congress": 119, "type": "HR", "number": "12", "title": "Missing Act", "latestAction": {"actionDate": "2026-07-01"}},
    ]}))
    (d / "ai_summaries.json").write_text(json.dumps({
        "119-hr-10": {"one_liner": "Funds rural clinics", "provisions": ["Adds clinics"], "issue_categories": ["Health"]},
        "119-hr-11": {"one_liner": "Flagged text", "provisions": ["Flagged"], "issue_categories": ["Health"],
                      "needs_review": True},
    }))
    return d


def test_withheld_summary_lists_like_a_missing_one(tmp_path):
    ds = DataService(data_dir=_summary_dir(tmp_path))
    rows = {b["number"]: b for b in ds.get_bills()["bills"]}
    assert rows["10"]["one_liner"] == "Funds rural clinics"
    for number in ("11", "12"):
        assert not rows[number]["one_liner"]
        assert rows[number]["provisions"] == []
        assert rows[number]["issue_categories"] == []
    assert [b["number"] for b in ds.get_bills(summarized_only=True)["bills"]] == ["10"]


@pytest.mark.parametrize("member, expected", [
    ({"bioguideId": "G000602", "chamber": "House of Representatives"}, "regular"),
    ({"bioguideId": "D000032", "chamber": "House"}, "regular"),
    ({"bioguideId": "C001056", "chamber": "Senate"}, "regular"),
    ({"bioguideId": "M001244", "chamber": "Senate"}, "special"),
    ({"bioguideId": "S000148", "chamber": "Senate"}, None),
])
def test_seat_up_2026(data_service, member, expected):
    assert data_service.seat_up_2026(member) == expected


def test_seat_up_2026_without_the_seats_file(tmp_path):
    ds = DataService(data_dir=tmp_path)
    assert ds.seat_up_2026({"bioguideId": "C001056", "chamber": "Senate"}) is None
    assert ds.seat_up_2026({"bioguideId": "G000602", "chamber": "House of Representatives"}) == "regular"


def test_latest_official_summary_lives_in_data_service():
    import sync
    from app.services.data_service import _latest_official_summary
    assert sync._latest_official_summary is _latest_official_summary
    bill = {"summaries": [
        {"actionDate": "2021-09-27", "actionDesc": "Introduced in House", "text": "BBB draft text"},
        {"actionDate": "2022-08-16", "actionDesc": "Public Law", "text": "IRA enacted text"},
    ]}
    assert DataService._latest_official_summary(bill) == "IRA enacted text"
