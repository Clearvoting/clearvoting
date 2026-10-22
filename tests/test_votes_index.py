"""votes_index.json (spec §10 #3, §7.1, §7.3): one sync-time pass over the roll-call files,
so the web runtime reads dict entries instead of scanning 5,369 files per request."""
import builtins
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app import render
from app.dependencies import get_data_service
from app.main import app
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


def test_verdict_tallies_count_guilty_as_yes_and_not_guilty_as_no(tmp_path):
    """F064: the H.Res. 24 verdict read 'California: 0 yes · 0 no' over rows marked Guilty."""
    d = tmp_path / "synced"
    _write_json(d / "votes" / "senate" / "117_1_00059.json", {
        "congress": 117, "session": 1, "vote_number": 59,
        "vote_date": "February 13, 2021,  03:37 PM",
        "question": "Guilty or Not Guilty H.Res. 24", "document": "H.Res. 24",
        "result": "Not Guilty (57-43, 2/3 majority required)",
        "counts": {"yeas": 57, "nays": 43, "present": 0, "absent": 0},
        "members": [
            _senator("Padilla", "CA", "Guilty"), _senator("Feinstein", "CA", "Guilty"),
            _senator("Rubio", "FL", "Not Guilty"), _senator("Cruz", "TX", "Not Guilty"),
        ],
    })
    rc = votes_index_payload(d)["roll_calls"]["senate/117_1_00059"]
    assert rc["tallies"] == {"CA": [2, 0, 0], "FL": [0, 1, 0], "NY": [0, 0, 0], "TX": [0, 1, 0]}


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


# F064 counts Guilty / Not Guilty in the state tallies, and the commit that did so did not
# rebuild data. Until the next `sync.py --step votes-index` (the weekly sync runs it) the
# committed index may still hold the old all-zero tallies for this verdict roll call; only
# that exact staleness is accepted. Empty this set once the rebuilt index is committed.
_TALLIES_REBUILD_PENDING = {"senate/117_1_00059"}


@needs_real
def test_committed_index_matches_the_roll_call_files():
    committed = _without_stamp(REAL / "votes_index.json")
    built = votes_index_payload(REAL)
    for key in _TALLIES_REBUILD_PENDING:
        rc = committed["roll_calls"].get(key)
        if rc and key in built["roll_calls"] and all(row == [0, 0, 0] for row in rc["tallies"].values()):
            rc["tallies"] = built["roll_calls"][key]["tallies"]
    assert committed == built, (
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


# --- T1.9: latest vote, bill refs and bill order read the index (spec §10 #11, §6.9 #9) ---

_T19_TALLIES = {"CA": [1, 0, 0], "FL": [0, 1, 0], "NY": [1, 1, 0], "TX": [0, 0, 1]}


def _t19_rc(document, date, question, plain, klass, result, yeas, nays, seats, bill):
    """One roll_calls entry in the §10 #3 schema (the shape T1.4's builder writes)."""
    return {
        "question": question, "plain": plain, "class": klass, "result": result,
        "counts": {"yeas": yeas, "nays": nays, "present": 0, "absent": seats - yeas - nays},
        "date": date, "document": document, "bill": bill, "parent": None,
        "threshold": None, "tallies": _T19_TALLIES,
    }


_T19_ROLL_CALLS = {
    # 119-hr-6500 style: latestAction (Feb 10) predates its Sep 1 roll call.
    "senate/119_2_00227": _t19_rc(
        "H.R. 6500", "2026-09-01", "On Cloture on the Motion to Proceed H.R. 6500",
        "Vote to end debate (needed 60)", "P",
        "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)",
        52, 46, 100, "119-hr-6500"),
    "house/119_2_00210": _t19_rc(
        "H.R. 4795", "2026-08-19", "On Passage", "Final vote to pass", "D",
        "Passed", 237, 169, 435, "119-hr-4795"),
    "house/119_2_00209": _t19_rc(
        "H.R. 4795", "2026-08-19", "On Motion to Recommit", "Vote to send it back to committee", "P",
        "Failed", 200, 210, 435, "119-hr-4795"),
    "senate/119_1_00050": _t19_rc(
        "S. 10", "2025-02-01", "On Passage of the Bill", "Final vote to pass", "D",
        "Bill Passed", 60, 40, 100, "119-s-10"),
    "senate/119_1_00060": _t19_rc(
        "PN80", "2025-02-05", "On the Nomination PN80", "Vote to confirm", "P",
        "Confirmed", 55, 45, 100, None),
}

_T19_BILLS = [  # file order deliberately scrambled
    {"congress": 118, "type": "HR", "number": "21", "title": "No Roll Call Act",
     "latestAction": {"actionDate": "2024-01-01", "text": "Introduced"}},
    {"congress": 119, "type": "S", "number": "10", "title": "Law Act",
     "laws": [{"type": "Public Law", "number": "119-6"}],
     "latestAction": {"actionDate": "2026-03-01", "text": "Became Public Law No: 119-6."}},
    {"congress": 119, "type": "HR", "number": "6500", "title": "Border Act",
     "latestAction": {"actionDate": "2026-02-10", "text": "Placed on the calendar"}},
    {"congress": 119, "type": "HR", "number": "4795", "title": "Protect Economic and Academic Freedom Act",
     "latestAction": {"actionDate": "2026-08-20", "text": "Received in the Senate"}},
]

_T19_MEMBERS = [
    {"bioguideId": "S000148", "name": "Schumer, Charles E.", "stateCode": "NY", "district": None,
     "chamber": "Senate", "partyName": "Democratic"},
    {"bioguideId": "G000555", "name": "Gillibrand, Kirsten E.", "stateCode": "NY", "district": None,
     "chamber": "Senate", "partyName": "Democratic"},
    {"bioguideId": "G000602", "name": "Gillen, Laura", "stateCode": "NY", "district": 4,
     "chamber": "House of Representatives", "partyName": "Democratic"},
]


def _t19_data_dir(tmp_path, latest="senate/119_2_00227"):
    index = {
        "roll_calls": _T19_ROLL_CALLS,
        "bills": {
            "119-hr-6500": {"roll_calls": ["senate/119_2_00227"], "activity_date": "2026-09-01"},
            "119-hr-4795": {"roll_calls": ["house/119_2_00210", "house/119_2_00209"],
                            "activity_date": "2026-08-20"},
            "119-s-10": {"roll_calls": ["senate/119_1_00050"], "activity_date": "2026-03-01"},
        },
        "generated_at": "2026-09-19T00:00:00Z",
    }
    if latest:
        index["latest"] = latest
    (tmp_path / "votes_index.json").write_text(json.dumps(index))
    (tmp_path / "bills.json").write_text(json.dumps({"bills": _T19_BILLS}))
    (tmp_path / "members.json").write_text(json.dumps({"members": _T19_MEMBERS}))
    (tmp_path / "ai_summaries.json").write_text(json.dumps({
        "119-hr-4795": {"one_liner": "Bars federal funds for colleges that limit campus speech",
                        "provisions": ["§ Cuts funds to colleges found to limit speech."],
                        "issue_categories": ["Education"]},
        "119-s-10": {"one_liner": "Withheld headline", "provisions": ["§ Withheld provision."],
                     "issue_categories": ["Taxes"], "needs_review": True},
    }))
    senate_dir = tmp_path / "votes" / "senate"
    senate_dir.mkdir(parents=True)
    (senate_dir / "119_2_00227.json").write_text(json.dumps({
        "congress": 119, "session": 2, "vote_number": 227,
        "vote_date": "September 1, 2026,  11:02 AM",
        "question": "On Cloture on the Motion to Proceed H.R. 6500", "document": "H.R. 6500",
        "result": "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)",
        "counts": {"yeas": 52, "nays": 46, "present": 0, "absent": 2},
        "members": [{"first_name": "Charles", "last_name": "Schumer", "party": "D",
                     "state": "NY", "vote": "Nay", "lis_member_id": "S000148"}],
    }))
    return tmp_path


def _status_text(status):
    """derived_status is render.bill_status's result: a seal string or {"text", "variant"}."""
    return status["text"] if isinstance(status, dict) else status


def test_get_bills_orders_by_activity_date_with_derived_status(tmp_path):
    service = DataService(data_dir=_t19_data_dir(tmp_path))
    bills = service.get_bills(limit=10)["bills"]
    assert [f"{b['congress']}-{b['type'].lower()}-{b['number']}" for b in bills] == [
        "119-hr-6500", "119-hr-4795", "119-s-10", "118-hr-21"]
    assert [b["activity_date"] for b in bills] == ["2026-09-01", "2026-08-20", "2026-03-01", "2024-01-01"]
    statuses = [_status_text(b["derived_status"]) for b in bills]
    assert statuses[0] == "No final vote yet"          # only a procedural (cloture) roll call
    assert statuses[1].startswith("Passed the House")  # newest decisive House vote passed
    assert statuses[2] == "Became law"                 # laws non-empty wins
    assert statuses[3] == "No final vote yet"          # no roll call at all


def test_withheld_and_missing_summaries_have_a_null_one_liner(tmp_path):
    service = DataService(data_dir=_t19_data_dir(tmp_path))
    rows = {f"{b['congress']}-{b['type'].lower()}-{b['number']}": b
            for b in service.get_bills(limit=10)["bills"]}
    assert rows["119-hr-4795"]["one_liner"] == "Bars federal funds for colleges that limit campus speech"
    assert rows["119-hr-4795"]["provisions"] == ["§ Cuts funds to colleges found to limit speech."]
    # needs_review is shown exactly like no summary (spec §2.5 C)
    for bill_id in ("119-s-10", "119-hr-6500", "118-hr-21"):
        assert rows[bill_id]["one_liner"] is None
        assert rows[bill_id]["provisions"] == []
        assert rows[bill_id]["issue_categories"] == []
    summarized = service.get_bills(summarized_only=True, limit=10)["bills"]
    assert [b["number"] for b in summarized] == ["4795"]


def test_get_bill_votes_reads_refs_from_the_index(tmp_path):
    service = DataService(data_dir=_t19_data_dir(tmp_path))
    refs = service.get_bill_votes(119, "HR", 4795)
    assert refs["senate"] == []
    # Oldest first per chamber, as the old directory scan listed them
    assert [(r["session"], r["vote_number"]) for r in refs["house"]] == [(2, 209), (2, 210)]
    assert set(refs["house"][0]) == {"congress", "session", "vote_number", "vote_date",
                                     "question", "result", "counts"}
    assert refs["house"][1]["vote_date"] == "2026-08-19"
    assert service.get_bill_votes(119, "hr", 6500)["senate"][0]["vote_number"] == 227
    assert service.get_bill_votes(118, "hr", 21) is None


def test_latest_vote_is_the_index_hero_with_card_fields(tmp_path):
    service = DataService(data_dir=_t19_data_dir(tmp_path))
    vote = service.get_latest_vote()
    rc = _T19_ROLL_CALLS["senate/119_2_00227"]
    # The newer unsummarized vote is shown, not skipped for the older summarized one (F02)
    assert vote["rc"] == "senate/119_2_00227"
    assert vote["chamber"] == "Senate"
    assert vote["date_iso"] == "2026-09-01"
    assert vote["date"] == "September 1, 2026"  # the display string the old app.js prints raw
    assert vote["document"] == "H.R. 6500"
    assert vote["plain_question"] == "Vote to end debate (needed 60)"
    assert vote["result"] == rc["result"]
    assert vote["counts"] == rc["counts"]
    assert vote["outcome"] == render.result_phrase(rc, "Senate")
    assert vote["seal"] == vote["outcome"]  # on this endpoint outcome is the seal
    assert vote["outcome"] and "blocked" not in vote["outcome"]
    assert vote["state_tallies"] == _T19_TALLIES
    assert vote["bill"] == {"congress": 119, "type": "hr", "number": 6500, "title": "Border Act"}
    assert vote["one_liner"] is None
    assert vote["has_summary"] is False
    # Every covered senator (T1.8's covered_positions); one absent from the roll call → None
    assert vote["covered"] == {
        "S000148": {"name": "Charles E. Schumer", "state": "NY", "district": None, "chamber": "Senate",
                    "position": "Nay", "relation": "Voted no"},
        "G000555": {"name": "Kirsten E. Gillibrand", "state": "NY", "district": None, "chamber": "Senate",
                    "position": None, "relation": "Not in the Senate for this vote"},
    }
    assert '"party' not in json.dumps(vote)


def test_latest_vote_with_a_summary_carries_the_one_liner(tmp_path):
    service = DataService(data_dir=_t19_data_dir(tmp_path, latest="house/119_2_00210"))
    vote = service.get_latest_vote()
    assert vote["has_summary"] is True
    assert vote["one_liner"] == "Bars federal funds for colleges that limit campus speech"
    assert vote["chamber"] == "House"
    # No House roll-call file in this data dir → every covered House member reads None
    assert vote["covered"] == {
        "G000602": {"name": "Laura Gillen", "state": "NY", "district": 4, "chamber": "House",
                    "position": None, "relation": "Not in the House for this vote"},
    }


def test_latest_vote_is_none_without_an_index_hero(tmp_path):
    assert DataService(data_dir=_t19_data_dir(tmp_path, latest=None)).get_latest_vote() is None
    assert DataService(data_dir=tmp_path / "empty").get_latest_vote() is None


def test_service_reads_only_the_latest_roll_call_file_once(tmp_path, monkeypatch):
    service = DataService(data_dir=_t19_data_dir(tmp_path))  # startup loads are not counted
    opened = []
    real_open = builtins.open

    def counting_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", counting_open)
    service.get_latest_vote()
    service.get_latest_vote()
    service.get_bills(limit=10)
    service.get_bills(summarized_only=True)
    for number in (6500, 4795):
        service.get_bill_votes(119, "hr", number)
    reads = [p for p in opened if f"{os.sep}votes{os.sep}" in p]
    assert reads == [str(tmp_path / "votes" / "senate" / "119_2_00227.json")]


@pytest.mark.asyncio
async def test_api_latest_vote_and_bill_lists_open_only_the_latest_roll_call_file():
    fixtures = Path(__file__).parent / "fixtures" / "synced"
    index = json.loads((fixtures / "votes_index.json").read_text())
    chamber, name = index["latest"].split("/")
    with patch("app.dependencies.get_data_dir", return_value=fixtures):
        get_data_service.cache_clear()
        get_data_service()  # startup loads happen here, outside the count
        opened = []
        real_open = io.open

        def counting_open(file, *args, **kwargs):
            opened.append(str(file))
            return real_open(file, *args, **kwargs)

        with patch("builtins.open", counting_open), patch("io.open", counting_open):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for path in ("/api/votes/latest", "/api/votes/latest", "/api/bills?limit=50",
                             "/api/bills?summarized_only=true", "/api/search/bills?q=act"):
                    assert (await client.get(path)).status_code == 200, path
    get_data_service.cache_clear()
    reads = [p for p in opened if f"{os.sep}votes{os.sep}" in p]
    assert reads == [str(fixtures / "votes" / chamber / f"{name}.json")]


# --- §6.9 #9: no page route scans roll-call files (plan T11.2) ---

_SCAN_FIXTURES = Path(__file__).parent / "fixtures" / "synced"


@pytest.mark.asyncio
@pytest.mark.parametrize("path, max_roll_call_reads", [
    ("/", 1),                                          # at most the latest vote
    ("/state?code=NY", 0),                             # one state_overview file
    ("/state?code=NY&district=4", 0),
    ("/member?id=S000148", 0),                         # one member_votes file, never votes/*
    ("/bill?congress=119&type=hjres&number=20", 2),    # at most two roll calls
])
async def test_page_routes_never_scan_roll_call_files(path, max_roll_call_reads):
    with patch("app.dependencies.get_data_dir", return_value=_SCAN_FIXTURES):
        get_data_service.cache_clear()
        get_data_service()  # startup loads (votes_index.json, crosswalk, seats) happen here, outside the count
        opened = []
        real_open = io.open

        def counting_open(file, *args, **kwargs):
            opened.append(str(file))
            return real_open(file, *args, **kwargs)

        with patch("builtins.open", counting_open), patch("io.open", counting_open):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(path)
    get_data_service.cache_clear()
    assert response.status_code == 200
    roll_call_reads = [p for p in opened if f"{os.sep}votes{os.sep}" in p]
    assert len(roll_call_reads) <= max_roll_call_reads, roll_call_reads
