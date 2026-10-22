import pytest
from datetime import datetime, timezone
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


# --- GET /api/members/{state}/overview (plan T4.2; spec §10 #7, §10 #9) ---
# The precomputed file plus render-ready fields, party-free by default. The old aggregate,
# rates and narrative snippet are gone with their only consumer, the old state.js.

NY_OVERVIEW = json.loads((FIXTURES / "state_overview" / "NY.json").read_text())
FL_IDS = {m["bioguideId"] for m in json.loads((FIXTURES / "members.json").read_text())["members"]
          if m.get("stateCode") == "FL"}
RENDER_READY = {"display_name", "initials", "seat_line", "seat_seal", "url", "photo", "latest_vote"}
LATEST_VOTE_READY = {"rc", "bill_id", "position", "date", "bill_code", "bill_url", "headline",
                     "displayable", "seal", "chip", "chip_class", "date_short"}
RETIRED = ("aggregate", "participation_rate", "support_rate", "total_votes", "yea_count",
           "nay_count", "narrative_snippet")


async def _get(path: str):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    _clear_data_service_cache()
    return response


@pytest.mark.asyncio
async def test_overview_is_the_precomputed_file_plus_render_ready_fields():
    # The seat seal is gone after Election Day (F066), so the request clock is pinned before it.
    with patch("app.main._now", return_value=datetime(2026, 10, 22, 18, 0, tzinfo=timezone.utc)):
        response = await _get("/api/members/NY/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "NY"
    assert data["state_name"] == "New York"
    assert data["districts_expected"] == NY_OVERVIEW["districts_expected"]
    assert data["roster_as_of"] == NY_OVERVIEW["roster_as_of"]
    assert [m["bioguideId"] for m in data["senators"]] == [m["bioguideId"] for m in NY_OVERVIEW["senators"]]
    assert [m["bioguideId"] for m in data["house"]] == [m["bioguideId"] for m in NY_OVERVIEW["house"]]
    for member in data["senators"] + data["house"]:
        assert RENDER_READY <= set(member)
        assert member["url"] == f"/member?id={member['bioguideId']}"
        if member["latest_vote"] is not None:
            assert LATEST_VOTE_READY <= set(member["latest_vote"])
            assert member["latest_vote"]["chip"] in {
                "Voted yes", "Voted no", "Didn't vote", "Present", "Guilty", "Not Guilty", "Voted"}
    gillen = next(m for m in data["house"] if m["bioguideId"] == "G000602")
    assert gillen["display_name"] == "Laura Gillen"
    assert gillen["seat_line"].startswith("District 4 · In Congress since ")
    assert gillen["seat_seal"] == "Seat up Nov 3"


@pytest.mark.asyncio
async def test_overview_drops_the_retired_aggregate_and_rates():
    text = (await _get("/api/members/NY/overview")).text
    for key in RETIRED:
        assert f'"{key}"' not in text


@pytest.mark.asyncio
async def test_overview_strips_party_by_default_and_reveals_on_request():
    default = await _get("/api/members/NY/overview")
    assert '"partyName"' not in default.text
    assert '"partyCode"' not in default.text
    revealed = (await _get("/api/members/NY/overview?show_party=true")).json()
    assert any(m.get("partyName") for m in revealed["senators"] + revealed["house"])


@pytest.mark.asyncio
async def test_overview_reads_no_member_vote_files():
    with patch.object(DataService, "get_member_votes", side_effect=AssertionError("request-path scan")):
        response = await _get("/api/members/NY/overview")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_overview_invalid_state_is_400():
    response = await _get("/api/members/INVALID/overview")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_overview_uncovered_state_is_404():
    response = await _get("/api/members/OH/overview")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_overview_missing_file_falls_back_to_members_json():
    # The fixtures carry only state_overview/NY.json; FL is served from members.json.
    response = await _get("/api/members/FL/overview")
    assert response.status_code == 200
    data = response.json()
    assert {m["bioguideId"] for m in data["senators"] + data["house"]} == FL_IDS
    assert all(m["latest_vote"] is None for m in data["senators"] + data["house"])
    assert '"partyName"' not in response.text


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
