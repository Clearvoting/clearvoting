import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
import json
import logging

from app.services.data_service import DataService
from sync import build_state_overview, build_votes_index, state_overview_payloads

REAL = Path(__file__).parent.parent / "data" / "synced"
OVERVIEW_KEYS = {"state", "state_name", "roster_as_of", "generated_at", "senators", "house", "districts_expected"}
MEMBER_KEYS = {"bioguideId", "name", "district", "chamber", "photo", "terms", "partyName", "latest_vote"}

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- State Overview Endpoint ---

@pytest.mark.asyncio
async def test_state_overview_returns_correct_structure():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()

    assert "members" in data
    assert "aggregate" in data

    agg = data["aggregate"]
    assert "total_members" in agg
    assert "avg_participation" in agg
    assert "avg_support_rate" in agg
    assert "total_votes" in agg


@pytest.mark.asyncio
async def test_state_overview_member_data_shape():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()
    members = data["members"]

    assert len(members) == 2

    for member in members:
        assert "bioguideId" in member
        assert "participation_rate" in member
        assert "support_rate" in member
        assert "total_votes" in member
        assert "yea_count" in member
        assert "nay_count" in member
        assert "narrative_snippet" in member


@pytest.mark.asyncio
async def test_state_overview_aggregate_calculations():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()
    agg = data["aggregate"]

    assert agg["total_members"] == 2

    # S001217: participation=100, total_votes=2, yea=1, nay=1 -> support=50
    # D000032: participation=85, total_votes=3, yea=2, nay=1 -> support=67
    # avg_participation = round((100 + 85) / 2) = 92 (or 93 depending on rounding)
    assert agg["avg_participation"] in [92, 93]
    # avg_support = round((50 + 67) / 2) = 58 (or 59)
    assert agg["avg_support_rate"] in [58, 59]
    assert agg["total_votes"] == 5


@pytest.mark.asyncio
async def test_state_overview_strips_party():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()
    for member in data["members"]:
        assert "partyName" not in member
        assert "partyCode" not in member


@pytest.mark.asyncio
async def test_state_overview_invalid_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/INVALID/overview")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_state_overview_empty_state():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/CA/overview")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["aggregate"]["total_members"] == 0
    assert len(data["members"]) == 0


@pytest.mark.asyncio
async def test_state_overview_narrative_snippet():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/members/FL/overview")

    _clear_data_service_cache()
    data = response.json()

    # S001217 has a narrative in fixtures; D000032 does not
    s001217 = next(m for m in data["members"] if m["bioguideId"] == "S001217")
    d000032 = next(m for m in data["members"] if m["bioguideId"] == "D000032")

    assert len(s001217["narrative_snippet"]) > 0
    assert d000032["narrative_snippet"] == ""


@pytest.mark.asyncio
async def test_state_page_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/state")
    assert response.status_code == 200
    assert "ClearVoting" in response.text


# --- Precomputed delegation files (plan T1.6; spec §10 #7, §4.2) ---

def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _vote_row(bill_id, vote, date, chamber, number):
    return {"bill_id": bill_id, "vote": vote, "date": date, "chamber": chamber,
            "congress": 119, "session": 2, "vote_number": number}


def _overview_dir(tmp_path: Path) -> Path:
    d = tmp_path / "synced"
    _write_json(d / "members.json", {"members": [
        {"bioguideId": "S000148", "name": "Schumer, Charles E.", "state": "New York", "stateCode": "NY",
         "chamber": "Senate", "partyName": "Democratic", "updateDate": "2026-09-05T07:40:26Z",
         "depiction": {"imageUrl": "https://www.congress.gov/img/member/s000148_200.jpg"},
         "terms": {"item": [{"chamber": "House of Representatives", "startYear": 1981, "endYear": 1999},
                            {"chamber": "Senate", "startYear": 1999}]}},
        {"bioguideId": "G000555", "name": "Gillibrand, Kirsten E.", "state": "New York", "stateCode": "NY",
         "chamber": "Senate", "partyName": "Democratic", "updateDate": "2026-08-01T00:00:00Z",
         "terms": {"item": [{"chamber": "Senate", "startYear": 2009}]}},
        {"bioguideId": "G000602", "name": "Gillen, Laura", "state": "New York", "stateCode": "NY", "district": 4,
         "chamber": "House of Representatives", "partyName": "Democratic", "updateDate": "2026-07-01T00:00:00Z",
         "terms": {"item": [{"chamber": "House of Representatives", "startYear": 2025}]}},
        {"bioguideId": "C001056", "name": "Cornyn, John", "state": "Texas", "stateCode": "TX",
         "chamber": "Senate", "partyName": "Republican", "updateDate": "2026-09-01T00:00:00Z",
         "terms": {"item": [{"chamber": "Senate", "startYear": 2002}]}},
    ]})
    _write_json(d / "zip_districts.json", {
        "_source": {"name": "test"},
        "11570": [{"state": "NY", "district": 4, "share": 1.0}],
        "10001": [{"state": "NY", "district": 12, "share": 1.0}],
    })
    _write_json(d / "votes" / "senate" / "119_2_00210.json", {
        "congress": 119, "session": 2, "vote_number": 210, "vote_date": "August 8, 2026,  02:15 PM",
        "question": "On Passage of the Bill H.R. 6500", "document": "H.R. 6500", "result": "Bill Passed (90-6)",
        "counts": {"yeas": 90, "nays": 6, "present": 0, "absent": 4},
        "members": [{"last_name": "Schumer", "state": "NY", "vote": "Yea"}],
    })
    _write_json(d / "votes" / "senate" / "119_2_00220.json", {
        "congress": 119, "session": 2, "vote_number": 220, "vote_date": "August 20, 2026,  10:00 AM",
        "question": "On Cloture on the Motion to Proceed S. 5271", "document": "S. 5271",
        "result": "Cloture on the Motion to Proceed Agreed to (70-28, 3/5 majority required)",
        "counts": {"yeas": 70, "nays": 28, "present": 0, "absent": 2},
        "members": [{"last_name": "Schumer", "state": "NY", "vote": "Nay"},
                    {"last_name": "Gillibrand", "state": "NY", "vote": "Yea"}],
    })
    _write_json(d / "votes" / "house" / "119_2_00295.json", {
        "congress": 119, "session": 2, "vote_number": 295, "vote_date": "2026-09-03",
        "question": "On Passage", "document": "H.R. 4795", "result": "Passed",
        "counts": {"yeas": 237, "nays": 169, "present": 0, "absent": 27},
        "members": [{"bioguide_id": "G000602", "state": "NY", "vote": "Aye"}], "chamber": "House",
    })
    _write_json(d / "bills.json", {"bills": [
        {"congress": 119, "type": "HR", "number": "6500", "latestAction": {"actionDate": "2026-07-30"}},
        {"congress": 119, "type": "HR", "number": "4795", "latestAction": {"actionDate": "2026-09-03"}},
        {"congress": 119, "type": "S", "number": "5271", "latestAction": {"actionDate": "2026-08-20"}},
    ]})
    mv = d / "member_votes"
    _write_json(mv / "S000148.json", {"member_id": "S000148", "votes": [
        _vote_row("119-s-5271", "Nay", "2026-08-20T10:00:00", "Senate", 220),
        _vote_row("119-hr-6500", "Yea", "2026-08-08T14:15:00", "Senate", 210),
    ]})
    _write_json(mv / "G000555.json", {"member_id": "G000555", "votes": [
        _vote_row("119-s-5271", "Yea", "2026-08-20T10:00:00", "Senate", 220),
    ]})
    _write_json(mv / "G000602.json", {"member_id": "G000602", "votes": [
        _vote_row("119-hr-4795", "Aye", "2026-09-03", "House", 295),
    ]})
    return d


def _built(tmp_path: Path) -> tuple[Path, dict]:
    d = _overview_dir(tmp_path)
    build_votes_index(d)
    assert build_state_overview(d, states=["NY"]) == 1
    return d, json.loads((d / "state_overview" / "NY.json").read_text())


def test_builder_writes_raw_fields_only(tmp_path):
    d, overview = _built(tmp_path)
    assert set(overview) == OVERVIEW_KEYS
    assert (overview["state"], overview["state_name"]) == ("NY", "New York")
    assert overview["roster_as_of"] == "2026-09-05"    # max updateDate among the state's members
    assert overview["districts_expected"] == 12        # the crosswalk maximum for NY
    assert [m["bioguideId"] for m in overview["senators"]] == ["G000555", "S000148"]
    assert [m["bioguideId"] for m in overview["house"]] == ["G000602"]
    for member in overview["senators"] + overview["house"]:
        assert set(member) == MEMBER_KEYS
    schumer = overview["senators"][1]
    assert schumer["district"] is None
    assert schumer["photo"] == "https://www.congress.gov/img/member/s000148_200.jpg"
    assert schumer["terms"] == [{"chamber": "House of Representatives", "startYear": 1981, "endYear": 1999},
                                {"chamber": "Senate", "startYear": 1999}]
    assert overview["house"][0]["district"] == 4
    assert overview["senators"][0]["photo"] is None
    assert not (d / "state_overview" / "TX.json").exists()


def test_latest_vote_is_the_newest_decisive_bill_vote(tmp_path):
    _, overview = _built(tmp_path)
    by_id = {m["bioguideId"]: m for m in overview["senators"] + overview["house"]}
    # Schumer's newest row is the Aug 20 cloture vote (procedural); his latest final vote is Aug 8.
    assert by_id["S000148"]["latest_vote"] == {
        "rc": "senate/119_2_00210", "bill_id": "119-hr-6500", "position": "Yea", "date": "2026-08-08"}
    assert by_id["G000602"]["latest_vote"] == {
        "rc": "house/119_2_00295", "bill_id": "119-hr-4795", "position": "Aye", "date": "2026-09-03"}
    assert by_id["G000555"]["latest_vote"] is None   # only a procedural vote in the record


def test_rebuild_is_byte_identical(tmp_path):
    d, _ = _built(tmp_path)
    first = (d / "state_overview" / "NY.json").read_bytes()
    build_state_overview(d, states=["NY"])
    assert (d / "state_overview" / "NY.json").read_bytes() == first


def test_builder_needs_the_votes_index(tmp_path):
    d = _overview_dir(tmp_path)
    assert build_state_overview(d, states=["NY"]) == 0
    assert not (d / "state_overview").exists()


def test_state_overview_step_runs_without_congress_key(monkeypatch, tmp_path):
    import asyncio
    import sys
    import sync as sync_module
    d = _overview_dir(tmp_path)
    build_votes_index(d)
    monkeypatch.delenv("CONGRESS_API_KEY", raising=False)
    monkeypatch.setattr(sync_module, "SYNC_DIR", d)
    monkeypatch.setattr(sys, "argv", ["sync.py", "--step", "state-overview", "--states", "NY"])
    asyncio.run(sync_module.main())
    assert json.loads((d / "state_overview" / "NY.json").read_text())["state"] == "NY"


def _fixture_overview() -> dict:
    return json.loads((FIXTURES / "state_overview" / "NY.json").read_text())


def _keys(obj) -> set:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(_keys(v) for v in obj.values()))
    if isinstance(obj, list):
        return set().union(*(_keys(v) for v in obj))
    return set()


def test_fixture_overview_is_the_builder_output():
    committed = _fixture_overview()
    committed.pop("generated_at")
    assert committed == state_overview_payloads(FIXTURES, ["NY"])["NY"], (
        "tests/fixtures/synced/state_overview/NY.json is stale; rebuild it with "
        "python -c \"from pathlib import Path; from sync import build_state_overview; "
        "build_state_overview(Path('tests/fixtures/synced'), states=['NY'])\"")


def test_fixture_overview_has_no_party_key_but_partyName():
    assert {k for k in _keys(_fixture_overview()) if "party" in k.lower()} <= {"partyName"}


def test_fixture_latest_votes_are_decisive():
    index = json.loads((FIXTURES / "votes_index.json").read_text())["roll_calls"]
    overview = _fixture_overview()
    for member in overview["senators"] + overview["house"]:
        if member["latest_vote"]:
            assert index[member["latest_vote"]["rc"]]["class"] == "D"


def test_get_state_overview_reads_the_file_once():
    ds = DataService(data_dir=FIXTURES)
    first = ds.get_state_overview("NY")
    assert first == _fixture_overview()
    assert ds.get_state_overview("ny") is first   # served from memory after the first read


def test_get_state_overview_missing_file_logs_and_returns_none(caplog):
    ds = DataService(data_dir=FIXTURES)
    with caplog.at_level(logging.WARNING, logger="app.services.data_service"):
        assert ds.get_state_overview("FL") is None
    assert "state_overview/FL.json missing" in caplog.text


def test_get_state_overview_fallback_is_the_roster_without_signal_lines():
    ds = DataService(data_dir=FIXTURES)
    roster = ds.get_state_overview("FL", fallback=True)
    assert set(roster) == OVERVIEW_KEYS
    assert roster["generated_at"] is None
    members = roster["senators"] + roster["house"]
    fl = [m for m in json.loads((FIXTURES / "members.json").read_text())["members"] if m.get("stateCode") == "FL"]
    assert sorted(m["bioguideId"] for m in members) == sorted(m["bioguideId"] for m in fl)
    assert all(set(m) == MEMBER_KEYS and m["latest_vote"] is None for m in members)


@pytest.mark.parametrize("code", ["../members", "N", "NY1", "", "1A"])
def test_get_state_overview_rejects_non_state_codes(code):
    assert DataService(data_dir=FIXTURES).get_state_overview(code) is None


@pytest.mark.skipif(not (REAL / "state_overview" / "NY.json").exists(), reason="real overview files not present")
def test_committed_overviews_match_the_builder():
    payloads = state_overview_payloads(REAL, ["CA", "FL", "NY", "TX"])
    index = json.loads((REAL / "votes_index.json").read_text())["roll_calls"]
    for code, payload in payloads.items():
        committed = json.loads((REAL / "state_overview" / f"{code}.json").read_text())
        committed.pop("generated_at")
        assert committed == payload, f"state_overview/{code}.json is stale; run: python sync.py --step state-overview"
        for member in payload["senators"] + payload["house"]:
            if member["latest_vote"]:
                assert index[member["latest_vote"]["rc"]]["class"] == "D"
    assert {c: p["districts_expected"] for c, p in payloads.items()} == {"CA": 52, "FL": 28, "NY": 26, "TX": 38}
    assert {c: len(p["senators"]) for c, p in payloads.items()} == {"CA": 2, "FL": 2, "NY": 2, "TX": 2}
