"""votes_index.json (spec §10 #3, §7.1, §7.3): one sync-time pass over the roll-call files,
so the web runtime reads dict entries instead of scanning 5,369 files per request."""
import json
from pathlib import Path

import pytest

from app import render
from app.services.data_service import DataService, roll_call_key
from sync import build_votes_index, votes_index_payload

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REAL = Path(__file__).parent.parent / "data" / "synced"


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _senator(last: str, state: str, vote: str) -> dict:
    return {"first_name": "A", "last_name": last, "party": "X", "state": state, "vote": vote}


def _synced(tmp_path: Path) -> Path:
    """Seven roll calls shaped like the real files: Senate display dates, House ISO dates."""
    d = tmp_path / "synced"
    senate = d / "votes" / "senate"
    house = d / "votes" / "house"
    _write_json(senate / "119_2_00209.json", {
        "congress": 119, "session": 2, "vote_number": 209,
        "vote_date": "August 8, 2026,  11:02 AM",
        "question": "On Cloture on the Motion to Proceed H.R. 6500", "document": "H.R. 6500",
        "result": "Cloture on the Motion to Proceed Agreed to (84-12, 3/5 majority required)",
        "counts": {"yeas": 84, "nays": 12, "present": 0, "absent": 4},
        "members": [_senator("Schumer", "NY", "Yea"), _senator("Cornyn", "TX", "Yea")],
    })
    _write_json(senate / "119_2_00210.json", {
        "congress": 119, "session": 2, "vote_number": 210,
        "vote_date": "August 8, 2026,  02:15 PM",
        "question": "On Passage of the Bill H.R. 6500", "document": "H.R. 6500",
        "result": "Bill Passed (90-6)",
        "counts": {"yeas": 90, "nays": 6, "present": 0, "absent": 4},
        "members": [
            _senator("Schumer", "NY", "Yea"), _senator("Gillibrand", "NY", "Yea"),
            _senator("Cornyn", "TX", "Nay"), _senator("Cruz", "TX", "Not Voting"),
            _senator("Moreno", "OH", "Yea"),
        ],
    })
    _write_json(senate / "119_2_00211.json", {
        "congress": 119, "session": 2, "vote_number": 211,
        "vote_date": "August 8, 2026,  03:40 PM",
        "question": "On the Amendment S.Amdt. 3001 to S.Con.Res. 5", "document": "S.Amdt. 3001",
        "result": "Amendment Rejected (45-53)",
        "counts": {"yeas": 45, "nays": 53, "present": 0, "absent": 2}, "members": [],
    })
    _write_json(senate / "119_2_00212.json", {
        "congress": 119, "session": 2, "vote_number": 212,
        "vote_date": "August 9, 2026,  10:00 AM",
        "question": "On the Nomination PN80", "document": "PN80",
        "result": "Nomination Confirmed (52-45)",
        "counts": {"yeas": 52, "nays": 45, "present": 0, "absent": 3}, "members": [],
    })
    _write_json(house / "119_2_00294.json", {
        "congress": 119, "session": 2, "vote_number": 294, "vote_date": "2026-09-02",
        "question": "On Motion to Suspend the Rules and Pass, as Amended", "document": "H.R. 5100",
        "result": "Failed", "title": "",
        "counts": {"yeas": 250, "nays": 170, "present": 0, "absent": 13}, "members": [], "chamber": "House",
    })
    _write_json(house / "119_2_00295.json", {
        "congress": 119, "session": 2, "vote_number": 295, "vote_date": "2026-09-03",
        "question": "On Passage", "document": "H.R. 4795", "result": "Passed", "title": "",
        "counts": {"yeas": 237, "nays": 169, "present": 0, "absent": 27},
        "members": [
            {"bioguide_id": "G000602", "state": "NY", "vote": "Aye"},
            {"bioguide_id": "G000599", "state": "NY", "vote": "No"},
            {"bioguide_id": "R000622", "state": "NY", "vote": "Present"},
            {"bioguide_id": "C001132", "state": "CA", "vote": "Not Voting"},
        ],
        "chamber": "House",
    })
    _write_json(house / "119_2_00296.json", {
        "congress": 119, "session": 2, "vote_number": 296, "vote_date": "2026-09-03",
        "question": "On Motion to Recommit", "document": "H.R. 4795", "result": "Failed", "title": "",
        "counts": {"yeas": 200, "nays": 215, "present": 0, "absent": 18}, "members": [], "chamber": "House",
    })
    _write_json(d / "bills.json", {"bills": [
        {"congress": 119, "type": "HR", "number": "6500", "latestAction": {"actionDate": "2026-07-30"}},
        {"congress": 119, "type": "HR", "number": "4795", "latestAction": {"actionDate": "2026-09-10"}},
        {"congress": 119, "type": "S", "number": "9", "latestAction": {"actionDate": "2026-05-01"}},
    ]})
    return d


def test_roll_calls_are_keyed_by_chamber_congress_session_and_number(tmp_path):
    index = votes_index_payload(_synced(tmp_path))
    assert sorted(index["roll_calls"]) == [
        "house/119_2_00294", "house/119_2_00295", "house/119_2_00296",
        "senate/119_2_00209", "senate/119_2_00210", "senate/119_2_00211", "senate/119_2_00212",
    ]
    assert roll_call_key("House", 119, 2, 295) == "house/119_2_00295"
    assert roll_call_key("senate", "119", "1", "7") == "senate/119_1_00007"


def test_entry_carries_question_class_counts_and_iso_date(tmp_path):
    rc = votes_index_payload(_synced(tmp_path))["roll_calls"]["senate/119_2_00210"]
    question = "On Passage of the Bill H.R. 6500"
    assert set(rc) == {"question", "plain", "class", "result", "counts", "date", "document",
                       "bill", "parent", "threshold", "tallies"}
    assert rc["question"] == question
    assert rc["plain"] == render.plain_question(question)
    assert rc["class"] == render.question_class(question) == "D"
    assert rc["result"] == "Bill Passed (90-6)"
    assert rc["counts"] == {"yeas": 90, "nays": 6, "present": 0, "absent": 4}
    assert rc["date"] == "2026-08-08"  # Senate display string parsed at sync time (§7.3)
    assert rc["document"] == "H.R. 6500"
    assert rc["bill"] == "119-hr-6500"
    assert rc["parent"] is None
    assert rc["threshold"] is None


def test_procedural_classes_thresholds_and_nominations(tmp_path):
    rcs = votes_index_payload(_synced(tmp_path))["roll_calls"]
    assert rcs["senate/119_2_00209"]["class"] == "P"
    assert rcs["senate/119_2_00209"]["threshold"] == "3/5"   # read from the Senate result
    assert rcs["house/119_2_00294"]["threshold"] == "2/3"    # implied by a House suspension
    assert rcs["house/119_2_00295"]["threshold"] is None
    assert rcs["house/119_2_00295"]["date"] == "2026-09-03"
    nomination = rcs["senate/119_2_00212"]
    assert nomination["bill"] is None
    assert nomination["class"] == "P"


def test_amendment_parent_is_parsed_from_the_question(tmp_path):
    amendment = votes_index_payload(_synced(tmp_path))["roll_calls"]["senate/119_2_00211"]
    assert amendment["bill"] is None
    assert amendment["parent"] == "119-sconres-5"


def test_tallies_cover_the_four_states_only(tmp_path):
    rcs = votes_index_payload(_synced(tmp_path))["roll_calls"]
    assert rcs["senate/119_2_00210"]["tallies"] == {
        "CA": [0, 0, 0], "FL": [0, 0, 0], "NY": [2, 0, 0], "TX": [0, 1, 1]}
    # Aye/No count as yes/no; Present is none of yes, no or didn't vote.
    assert rcs["house/119_2_00295"]["tallies"] == {
        "CA": [0, 0, 1], "FL": [0, 0, 0], "NY": [1, 1, 0], "TX": [0, 0, 0]}


def test_bills_list_roll_calls_newest_first_with_activity_date(tmp_path):
    bills = votes_index_payload(_synced(tmp_path))["bills"]
    assert bills["119-hr-6500"]["roll_calls"] == ["senate/119_2_00210", "senate/119_2_00209"]
    # latestAction (Jul 30) is older than the Aug 8 roll call, so the roll call dates the activity.
    assert bills["119-hr-6500"]["activity_date"] == "2026-08-08"
    # latestAction (Sep 10) is newer than the Sep 3 roll calls, so the action dates it.
    assert bills["119-hr-4795"]["roll_calls"] == ["house/119_2_00296", "house/119_2_00295"]
    assert bills["119-hr-4795"]["activity_date"] == "2026-09-10"
    assert bills["119-s-9"] == {"roll_calls": [], "activity_date": "2026-05-01"}
    assert bills["119-hr-5100"] == {"roll_calls": ["house/119_2_00294"], "activity_date": "2026-09-02"}


def test_latest_is_the_newest_bill_roll_call_decisive_first_within_a_day(tmp_path):
    # Sep 3 has a passage vote (295) and a later motion to recommit (296): the decisive one leads.
    # H.R. 5100 is not in bills.json and the Aug 9 nomination names no bill, so neither can lead.
    assert votes_index_payload(_synced(tmp_path))["latest"] == "house/119_2_00295"


def test_rebuild_from_the_same_inputs_is_byte_identical(tmp_path):
    d = _synced(tmp_path)
    assert build_votes_index(d) == 7
    first = (d / "votes_index.json").read_bytes()
    assert json.loads(first)["generated_at"]
    build_votes_index(d)
    assert (d / "votes_index.json").read_bytes() == first


def test_rebuild_after_a_new_roll_call_rewrites_the_file(tmp_path):
    d = _synced(tmp_path)
    build_votes_index(d)
    _write_json(d / "votes" / "house" / "119_2_00297.json", {
        "congress": 119, "session": 2, "vote_number": 297, "vote_date": "2026-09-04",
        "question": "On Passage", "document": "H.R. 6500", "result": "Passed", "title": "",
        "counts": {"yeas": 300, "nays": 120, "present": 0, "absent": 13}, "members": [], "chamber": "House",
    })
    assert build_votes_index(d) == 8
    index = json.loads((d / "votes_index.json").read_text())
    assert index["latest"] == "house/119_2_00297"
    assert index["bills"]["119-hr-6500"]["roll_calls"][0] == "house/119_2_00297"
    assert index["bills"]["119-hr-6500"]["activity_date"] == "2026-09-04"


def test_data_service_loads_the_index_once_at_startup(tmp_path):
    d = _synced(tmp_path)
    build_votes_index(d)
    ds = DataService(data_dir=d)
    assert ds._votes_index["latest"] == "house/119_2_00295"
    assert "senate/119_2_00210" in ds._votes_index["roll_calls"]


def test_data_service_without_an_index_has_an_empty_one(tmp_path):
    assert DataService(data_dir=tmp_path)._votes_index == {}


FIXTURE_REBUILD = ("python -c \"from pathlib import Path; from sync import build_votes_index; "
                   "build_votes_index(Path('tests/fixtures/synced'))\"")
needs_real = pytest.mark.skipif(not (REAL / "votes_index.json").exists(),
                                reason="real data/synced/votes_index.json not present")


def _without_stamp(path: Path) -> dict:
    data = json.loads(path.read_text())
    data.pop("generated_at")
    return data


def test_fixture_index_is_the_builder_output():
    """Any task that adds fixture roll calls or bills must rebuild the fixture index."""
    assert _without_stamp(FIXTURES / "votes_index.json") == votes_index_payload(FIXTURES), (
        f"tests/fixtures/synced/votes_index.json is stale; rebuild it with {FIXTURE_REBUILD}")


def test_fixture_index_covers_every_fixture_roll_call():
    index = json.loads((FIXTURES / "votes_index.json").read_text())
    for chamber in ("house", "senate"):
        for path in (FIXTURES / "votes" / chamber).glob("*.json"):
            assert f"{chamber}/{path.stem}" in index["roll_calls"]


def test_fixture_index_threshold_is_render_parse_threshold():
    """§7.2 one formatter: the index threshold is exactly render.parse_threshold's answer."""
    index = json.loads((FIXTURES / "votes_index.json").read_text())
    for key, rc in index["roll_calls"].items():
        assert rc["threshold"] == render.parse_threshold(rc["result"], rc["plain"], rc["question"]), key


@needs_real
def test_real_index_threshold_is_render_parse_threshold():
    index = json.loads((REAL / "votes_index.json").read_text())
    concur_fast = 0
    for key, rc in index["roll_calls"].items():
        assert rc["threshold"] == render.parse_threshold(rc["result"], rc["plain"], rc["question"]), key
        if "Suspend the Rules and Concur" in rc["question"]:
            concur_fast += 1
            assert rc["threshold"] == "2/3", key
    assert concur_fast  # 16 on today's data (14 "On Motion to…", 2 "On the Motion to…")


@needs_real
def test_committed_index_matches_the_roll_call_files():
    assert _without_stamp(REAL / "votes_index.json") == votes_index_payload(REAL), (
        "data/synced/votes_index.json is stale; run: python sync.py --step votes-index")


def _bill_status_text(laws: list, latest_decisive: dict) -> str:
    """render.bill_status (T1.2) is called only here. `latest_decisive` maps "House"/"Senate" to
    that chamber's newest class-D index entry. If Step 1 showed another argument shape, change
    only this body."""
    status = render.bill_status(laws, latest_decisive)
    return str(status.get("text") or "") if isinstance(status, dict) else str(status or "")


@needs_real
def test_every_bill_with_a_decisive_roll_call_gets_a_status_seal():
    """§7.1: a bill with a class-D roll call never shows "No final vote yet". The number of
    bills without one is computed from the table and printed (the spec's 115 is approximate)."""
    index = json.loads((REAL / "votes_index.json").read_text())
    laws = {f"{b.get('congress')}-{str(b.get('type', '')).lower()}-{b.get('number')}": b.get("laws") or []
            for b in json.loads((REAL / "bills.json").read_text())["bills"]}
    verdict = render.plain_question("Guilty or Not Guilty")  # §7.1: never a bill seal
    without_decisive = 0
    for bill_id, entry in index["bills"].items():
        latest_decisive: dict = {}
        for key in entry["roll_calls"]:  # newest first
            rc = index["roll_calls"][key]
            chamber = "House" if key.startswith("house/") else "Senate"
            if rc["class"] == "D" and rc["plain"] != verdict and chamber not in latest_decisive:
                latest_decisive[chamber] = rc
        if not latest_decisive:
            without_decisive += 1
            continue
        assert _bill_status_text(laws.get(bill_id, []), latest_decisive) != "No final vote yet", bill_id
    print(f"\nbills with no decisive roll call: {without_decisive} of {len(index['bills'])}")
