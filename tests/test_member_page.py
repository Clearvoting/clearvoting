"""Member page payload and grouped record (plan T1.7; spec §4.3 m2, m4, m5, m7, §2.5 B, §10 #8)."""
import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.data_service import (
    DataService,
    _newest_first,
    filter_record_votes,
    group_record,
    pick_recent_votes,
    rc_key_or_none,
    roll_call_key,
)

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REAL = Path(__file__).resolve().parent.parent / "data" / "synced"

PAGE_KEYS = {
    "member", "seat", "has_record", "stats", "other_count", "first_vote_date", "last_vote_date",
    "nominations_count", "recent_votes", "record", "sponsored", "sponsored_count", "donation",
}
RECORD_KEYS = {
    "groups", "page", "pages", "per_page", "total_groups", "matching_bills", "topic", "position",
    "plain", "policy_areas", "plain_bills", "total_bills",
}
RECENT_KEYS = {
    "rc", "roll_call", "chamber", "bill_id", "congress", "bill_type", "bill_number", "one_liner",
    "position", "date", "policy_area",
}


# --- Synthetic rows in the member_votes row shape (spec header note) ---

def _row(number, bill_id, vote="Yea", day="2026-08-08", area="Health", chamber="Senate",
         text="", result="Passed"):
    return {
        "bill_number": text, "bill_id": bill_id, "one_liner": text,
        "has_plain_summary": bool(bill_id), "vote": vote, "date": f"{day}T12:00:00",
        "result": result, "policy_area": area if bill_id else "", "chamber": chamber,
        "congress": 119, "session": 2, "vote_number": number,
    }


def _entry(cls="D", plain="Final vote to pass", question="On Passage of the Bill", parent=None,
           document="", result="Bill Passed (60-40)", day="2026-08-08"):
    return {
        "question": question, "plain": plain, "class": cls, "result": result,
        "counts": {"yeas": 60, "nays": 40, "present": 0, "absent": 0}, "date": day,
        "document": document, "bill": None, "parent": parent, "threshold": None,
        "tallies": {"CA": [0, 0, 0], "FL": [0, 0, 0], "NY": [1, 1, 0], "TX": [0, 0, 0]},
    }


def _key(row):
    return rc_key_or_none(row["chamber"], row["congress"], row["session"], row["vote_number"])


def _plain_except(*withheld):
    """A plain_one_liner stand-in: every bill has a displayable summary except `withheld`."""
    def plain_one_liner(bill_id):
        if not bill_id or bill_id in withheld:
            return None
        return f"Plain {bill_id}"
    return plain_one_liner


def _numbers(rows):
    return [row["vote_number"] for row in rows]


# --- Recent votes: the §4.3 m2 rule ---

def test_rc_key_or_none_matches_the_index_key_format():
    assert rc_key_or_none("Senate", 119, 2, 228) == "senate/119_2_00228"
    assert rc_key_or_none("House", "117", "1", "6") == "house/117_1_00006"
    assert rc_key_or_none("house", 119, 1, 2) == "house/119_1_00002"
    assert rc_key_or_none("House of Representatives", 119, 1, 2) == "house/119_1_00002"
    assert rc_key_or_none("Joint", 119, 1, 2) is None
    assert rc_key_or_none("Senate", None, 1, 2) is None
    # One key builder: the wrapper agrees with T1.4's roll_call_key wherever that one succeeds.
    assert rc_key_or_none("Senate", 119, 2, 228) == roll_call_key("Senate", 119, 2, 228)


def test_recent_votes_take_only_decisive_displayable_yes_no_votes_with_a_topic():
    rows = [
        _row(10, "119-hr-1", "Yea"),
        _row(9, "119-hr-2", "Nay"),                 # procedural roll call (class P)
        _row(8, "119-hr-3", "Yea"),                 # summary withheld or missing
        _row(7, "119-hr-4", "Yea", area=""),        # no policy area
        _row(6, "119-hr-5", "Present"),             # not a yes/no position
        _row(5, None, "Yea", text="To strike section 2019."),
        _row(4, "119-hr-6", "No", area="Energy"),
        _row(3, "119-hr-7", "Aye", area="Taxation"),
    ]
    index = {_key(r): _entry() for r in rows}
    index[_key(rows[1])] = _entry(cls="P", plain="Vote to end debate (needed 60)")
    picked = pick_recent_votes(rows, index, _plain_except("119-hr-3"))
    assert [p["bill_id"] for p in picked] == ["119-hr-1", "119-hr-6", "119-hr-7"]
    assert [p["position"] for p in picked] == ["yes", "no", "yes"]
    first = picked[0]
    assert set(first) == RECENT_KEYS
    assert first["rc"] == "senate/119_2_00010"
    assert first["roll_call"]["class"] == "D"
    assert (first["congress"], first["bill_type"], first["bill_number"]) == (119, "hr", 1)
    assert first["one_liner"] == "Plain 119-hr-1"
    assert (first["chamber"], first["policy_area"], first["date"]) == ("Senate", "Health", "2026-08-08T12:00:00")


def test_a_bill_is_marked_seen_only_when_one_of_its_votes_is_picked():
    rows = [_row(20, "119-hr-1", "Not Voting"), _row(19, "119-hr-1", "Nay"), _row(18, "119-hr-1", "Yea")]
    index = {_key(r): _entry() for r in rows}
    picked = pick_recent_votes(rows, index, _plain_except())
    assert [(p["rc"], p["position"]) for p in picked] == [("senate/119_2_00019", "no")]


def test_votes_without_an_index_entry_never_qualify():
    assert pick_recent_votes([_row(30, "119-hr-1", "Yea")], {}, _plain_except()) == []


def test_round_robin_spreads_topics_then_outputs_newest_first():
    health = [_row(50 - i, f"119-hr-{101 + i}", "Yea", area="Health") for i in range(7)]
    energy = [_row(43 - i, f"119-hr-{201 + i}", "Nay", area="Energy") for i in range(2)]
    rows = health + energy
    index = {_key(r): _entry() for r in rows}
    picked = pick_recent_votes(rows, index, _plain_except())
    assert [int(p["rc"][-5:]) for p in picked] == [50, 49, 48, 47, 46, 45, 43, 42]


def test_recent_votes_stop_at_eight_and_short_records_show_what_qualifies():
    many = [_row(100 - i, f"119-s-{i + 1}", "Yea", area=f"Area {i}") for i in range(12)]
    index = {_key(r): _entry() for r in many}
    assert [int(p["rc"][-5:]) for p in pick_recent_votes(many, index, _plain_except())] == list(range(100, 92, -1))
    assert len(pick_recent_votes(many[:3], index, _plain_except())) == 3


# --- The record: grouping (§4.3 m4) ---

def test_bill_group_leads_with_its_latest_decisive_roll_call():
    rows = [_row(30, "119-hr-1", "Yea"), _row(29, "119-hr-1", "Nay"), _row(28, "119-hr-1", "Yea")]
    index = {
        _key(rows[0]): _entry(cls="P", plain="Vote to end debate (needed 60)"),
        _key(rows[1]): _entry(),
        _key(rows[2]): _entry(cls="P", plain="Vote on an amendment"),
    }
    groups = group_record(rows, index, {"119-hr-1": {"title": "Official Title One"}}, _plain_except())
    assert len(groups) == 1
    group = groups[0]
    assert group["kind"] == "bill"
    assert (group["bill_id"], group["congress"], group["bill_type"], group["bill_number"]) == ("119-hr-1", 119, "hr", 1)
    assert (group["headline"], group["displayable"], group["policy_area"]) == ("Plain 119-hr-1", True, "Health")
    assert (group["lead"]["rc"], group["lead"]["vote"]) == ("senate/119_2_00029", "Nay")
    assert [v["rc"] for v in group["more"]] == ["senate/119_2_00030", "senate/119_2_00028"]


def test_bill_group_without_a_decisive_roll_call_leads_with_its_latest():
    rows = [_row(31, "119-hr-9", "Yea"), _row(30, "119-hr-9", "Nay")]
    index = {_key(r): _entry(cls="P", plain="Vote on an amendment") for r in rows}
    assert group_record(rows, index, {}, _plain_except())[0]["lead"]["rc"] == "senate/119_2_00031"


def test_unsummarized_or_withheld_bill_shows_the_official_title_once():
    rows = [_row(40, "119-hr-2", "Yea", text="A withheld AI line"), _row(39, "119-hr-3", "Nay", text="Raw title string")]
    index = {_key(r): _entry() for r in rows}
    groups = group_record(rows, index, {"119-hr-2": {"title": "An Act to do a thing"}},
                          _plain_except("119-hr-2", "119-hr-3"))
    assert [(g["headline"], g["displayable"]) for g in groups] == [
        ("An Act to do a thing", False), ("Raw title string", False)]


def test_other_votes_collapse_into_one_row_per_day_while_consecutive():
    rows = [
        _row(40, None, text="To strike section 2019."),
        _row(39, None, text=""),
        _row(38, "119-hr-1"),
        _row(37, None, text="In the nature of a substitute."),
        _row(36, None, day="2026-08-07", text="To strike section 12."),
    ]
    index = {_key(r): _entry(cls="P", plain="Vote on an amendment") for r in rows}
    groups = group_record(rows, index, {}, _plain_except())
    assert [(g["kind"], g.get("date")) for g in groups] == [
        ("other", "2026-08-08"), ("bill", None), ("other", "2026-08-08"), ("other", "2026-08-07")]
    assert [v["text"] for v in groups[0]["votes"]] == ["To strike section 2019.", ""]
    assert groups[0]["votes"][0]["chamber"] == "Senate"
    assert groups[2]["votes"][0]["text"] == "In the nature of a substitute."


def test_parent_bill_is_read_from_the_index_question():
    rows = [_row(60, None, text="To strike."), _row(59, None, text="To add."), _row(58, None, text="")]
    index = {
        _key(rows[0]): _entry(cls="P", plain="Vote on an amendment", parent="119-sconres-5"),
        _key(rows[1]): _entry(cls="P", plain="Vote on an amendment", parent="118-hr-99"),
        _key(rows[2]): _entry(cls="P", plain="Procedural vote"),
    }
    votes = group_record(rows, index, {"119-sconres-5": {"title": "Budget"}}, _plain_except())[0]["votes"]
    assert votes[0]["parent"] == {"bill_id": "119-sconres-5", "congress": 119, "bill_type": "sconres",
                                  "bill_number": 5, "in_bills": True}
    assert votes[1]["parent"]["in_bills"] is False
    assert votes[2]["parent"] is None


def test_speaker_election_rows_never_carry_a_candidate_name():
    row = _row(2, None, vote="Jeffries", day="2025-01-03", chamber="House", result="Johnson (LA)")
    index = {_key(row): _entry(cls="P", plain="Election of the Speaker", question="Election of the Speaker",
                               result="Johnson (LA)", day="2025-01-03")}
    groups = group_record([row], index, {}, _plain_except())
    assert groups[0]["kind"] == "speaker"
    vote = groups[0]["vote"]
    assert (vote["vote"], vote["result"], vote["rc"]) == ("Voted", "Speaker elected", "house/119_2_00002")
    assert vote["roll_call"]["result"] == "Speaker elected"
    dumped = json.dumps(groups)
    assert "Jeffries" not in dumped and "Johnson" not in dumped
    assert index[_key(row)]["result"] == "Johnson (LA)"  # the shared index entry is not mutated


def test_speaker_row_is_recognised_without_an_index_entry():
    row = _row(2, None, vote="Jeffries", day="2025-01-03", chamber="House", result="Johnson (LA)")
    groups = group_record([row], {}, {}, _plain_except())
    assert groups[0]["kind"] == "speaker" and groups[0]["vote"]["vote"] == "Voted"


def test_speaker_not_voting_row_keeps_its_real_position():
    row = _row(15, None, vote="Not Voting", day="2023-01-04", chamber="House", result="McCarthy")
    index = {_key(row): _entry(cls="P", plain="Election of the Speaker", question="Election of the Speaker",
                               result="McCarthy", day="2023-01-04")}
    groups = group_record([row], index, {}, _plain_except())
    assert groups[0]["kind"] == "speaker"
    vote = groups[0]["vote"]
    assert (vote["vote"], vote["result"]) == ("Not Voting", "Speaker elected")
    assert vote["roll_call"]["result"] == "Speaker elected"
    assert "McCarthy" not in json.dumps(groups)


def test_get_speaker_votes_leaves_out_real_positions():
    rows = [
        _row(15, None, vote="Not Voting", day="2023-01-04", chamber="House", result="McCarthy"),
        _row(16, None, vote="Jeffries", day="2023-01-04", chamber="House", result="McCarthy"),
    ]
    index = {_key(r): _entry(cls="P", plain="Election of the Speaker", question="Election of the Speaker",
                             result="McCarthy", day="2023-01-04") for r in rows}
    service = DataService(data_dir=FIXTURES)
    with patch.object(service, "get_member_votes", return_value={"votes": rows}), \
            patch.object(service, "_index_roll_calls", return_value=index):
        assert service.get_speaker_votes("X000001") == {_key(rows[1]): "Jeffries"}


def test_filters_apply_to_votes_before_grouping():
    rows = [
        _row(9, "119-hr-1", "Yea", area="Health"),
        _row(8, "119-hr-2", "No", area="Energy"),
        _row(7, "119-hr-3", "Nay", area="Health"),
        _row(6, None, "Not Voting"),
        _row(5, "119-hr-4", "Not Voting", area="Health"),
    ]
    plain = _plain_except("119-hr-3")
    assert _numbers(filter_record_votes(rows, "Health", None, False, plain)) == [9, 7, 5]
    assert _numbers(filter_record_votes(rows, None, "no", False, plain)) == [8, 7]
    assert _numbers(filter_record_votes(rows, None, "nv", False, plain)) == [6, 5]
    assert _numbers(filter_record_votes(rows, None, None, True, plain)) == [9, 8, 5]
    assert _numbers(filter_record_votes(rows, "Health", "yes", True, plain)) == [9]
    assert filter_record_votes(rows, None, None, False, plain) == rows


# --- DataService.get_member_page over a synthetic data dir ---

SENATOR = {"bioguideId": "X000001", "name": "Doe, Jane", "stateCode": "NY", "state": "New York",
           "chamber": "Senate", "partyName": "Democratic",
           "terms": {"item": [{"chamber": "Senate", "startYear": 2019}]},
           "updateDate": "2026-03-08T00:00:00Z"}
REP = {"bioguideId": "Y000002", "name": "Roe, Sam", "stateCode": "NY", "state": "New York",
       "chamber": "House of Representatives", "district": 4, "partyName": "Republican",
       "terms": {"item": [{"chamber": "House of Representatives", "startYear": 2025}]},
       "updateDate": "2026-03-08T00:00:00Z"}
NO_FILE = {"bioguideId": "Z000003", "name": "Poe, Al", "stateCode": "FL", "state": "Florida",
           "chamber": "House of Representatives", "district": 7, "partyName": "Independent",
           "terms": {"item": [{"chamber": "House of Representatives", "startYear": 2023}]},
           "updateDate": "2026-03-08T00:00:00Z"}
NO_FEC = {"bioguideId": "W000004", "name": "Loe, Bo", "stateCode": "TX", "state": "Texas",
          "chamber": "House of Representatives", "district": 2, "partyName": "Republican",
          "terms": {"item": [{"chamber": "House of Representatives", "startYear": 2021}]},
          "updateDate": "2026-03-08T00:00:00Z"}
FULL_TOTALS = {"total_receipts": 2790888, "total_disbursements": 3349300,
               "total_individual": 2345346, "total_pac": 202800}


def _sponsored_bill(number, introduced, sponsor="X000001"):
    return {"congress": 119, "type": "S", "number": str(number), "title": f"Test Act {number}",
            "introducedDate": introduced,
            "latestAction": {"actionDate": introduced, "text": "Passed Senate without amendment."},
            "sponsors": [{"bioguideId": sponsor, "fullName": "Sen. Doe, Jane [D-NY]", "firstName": "Jane",
                          "lastName": "Doe", "state": "NY", "party": "D"}],
            "policyArea": {"name": "Health"}}


def _service(tmp_path, votes=None, roll_calls=None, index_bills=None, bills=(), summaries=None,
             donations=None):
    (tmp_path / "member_votes").mkdir()
    (tmp_path / "members.json").write_text(json.dumps({"members": [SENATOR, REP, NO_FILE, NO_FEC]}))
    (tmp_path / "bills.json").write_text(json.dumps({"bills": list(bills)}))
    (tmp_path / "ai_summaries.json").write_text(json.dumps(summaries or {}))
    (tmp_path / "donations.json").write_text(json.dumps(donations or {}))
    (tmp_path / "votes_index.json").write_text(json.dumps({
        "roll_calls": roll_calls or {}, "bills": index_bills or {}, "latest": None,
        "generated_at": "2026-09-05T00:00:00Z"}))
    for member_id, rows in (votes or {}).items():
        stats = {
            "total_votes": len(rows),
            "yea_count": sum(1 for r in rows if r["vote"] in ("Yea", "Aye")),
            "nay_count": sum(1 for r in rows if r["vote"] in ("Nay", "No")),
            "not_voting_count": sum(1 for r in rows if r["vote"] == "Not Voting"),
            "participation_rate": 99.0,
        }
        (tmp_path / "member_votes" / f"{member_id}.json").write_text(json.dumps({
            "member_id": member_id, "congresses": [119], "stats": stats, "scorecard": [], "votes": rows,
            "policy_areas": sorted({r["policy_area"] for r in rows if r["policy_area"]})}))
    return DataService(data_dir=tmp_path)


def test_member_page_shape_is_party_free_with_header_facts(tmp_path):
    senator_rows = [
        _row(12, "119-s-1", "Yea"),
        _row(11, None, "Not Voting", day="2026-08-01"),
        _row(10, None, "Guilty", day="2021-02-13"),
    ]
    rep_rows = [_row(5, "119-s-1", "Nay", chamber="House")]
    roll_calls = {_key(r): _entry() for r in senator_rows + rep_rows}
    roll_calls["senate/119_1_00500"] = _entry(cls="P", plain="Vote to confirm", document="PN12", day="2025-03-01")
    roll_calls["senate/117_1_00001"] = _entry(cls="P", plain="Vote to confirm", document="PN1", day="2021-01-20")
    roll_calls["house/119_1_00900"] = _entry(cls="P", plain="Procedural vote", document="PN5", day="2025-03-01")
    ds = _service(tmp_path, votes={"X000001": senator_rows, "Y000002": rep_rows}, roll_calls=roll_calls)

    page = ds.get_member_page("x000001")
    assert set(page) == PAGE_KEYS
    assert page["member"]["bioguideId"] == "X000001"
    assert not {"party", "partyName", "partyCode"} & set(page["member"])
    assert page["has_record"] is True
    assert page["stats"] == {"total_votes": 3, "yea_count": 1, "nay_count": 0, "not_voting_count": 1}
    assert page["other_count"] == 1
    assert (page["first_vote_date"], page["last_vote_date"]) == ("2021-02-13T12:00:00", "2026-08-08T12:00:00")
    assert page["nominations_count"] == 1
    assert page["seat"] is None
    assert set(page["record"]) == RECORD_KEYS
    dumped = json.dumps(page)
    assert "Democratic" not in dumped and "participation_rate" not in dumped and "scorecard" not in dumped

    house = ds.get_member_page("Y000002")
    assert house["nominations_count"] is None
    assert house["seat"] == "regular"


def test_record_pages_hold_fifteen_groups_and_the_page_is_clamped(tmp_path):
    days = [(date(2026, 8, 8) - timedelta(days=i)).isoformat() for i in range(40)]
    rows = [_row(100 - i, None, "Yea", day=days[i], text=f"Amendment {i}") for i in range(40)]
    ds = _service(tmp_path, votes={"X000001": rows},
                  roll_calls={_key(r): _entry(cls="P", plain="Vote on an amendment") for r in rows})
    second = ds.get_member_page("X000001", 2)["record"]
    assert (second["page"], second["pages"], second["per_page"], second["total_groups"]) == (2, 3, 15, 40)
    assert len(second["groups"]) == 15
    assert second["groups"][0]["date"] == days[15]
    last = ds.get_member_page("X000001", 99)["record"]
    assert (last["page"], len(last["groups"])) == (3, 10)
    assert ds.get_member_page("X000001", 0)["record"]["page"] == 1


def test_record_filters_and_bill_counts(tmp_path):
    rows = [
        _row(9, "119-s-1", "Yea", area="Health"),
        _row(8, "119-s-2", "Nay", area="Energy"),
        _row(7, "119-s-1", "Nay", area="Health"),
        _row(6, None, "Yea", text="To strike."),
    ]
    summaries = {"119-s-1": {"one_liner": "Plain one", "provisions": ["One"]},
                 "119-s-2": {"one_liner": "Withheld line", "provisions": [], "needs_review": True}}
    ds = _service(tmp_path, votes={"X000001": rows}, roll_calls={_key(r): _entry() for r in rows},
                  summaries=summaries)

    everything = ds.get_member_page("X000001")["record"]
    assert (everything["total_groups"], everything["matching_bills"]) == (3, 2)
    assert (everything["plain_bills"], everything["total_bills"]) == (1, 2)
    assert everything["policy_areas"] == ["Energy", "Health"]
    assert (everything["topic"], everything["position"], everything["plain"]) == (None, None, False)

    health = ds.get_member_page("X000001", 1, "Health")["record"]
    assert (health["topic"], health["total_groups"], health["matching_bills"]) == ("Health", 1, 1)
    assert [v["rc"] for v in health["groups"][0]["more"]] == ["senate/119_2_00007"]

    no = ds.get_member_page("X000001", 1, None, "no")["record"]
    assert [g["bill_id"] for g in no["groups"]] == ["119-s-2", "119-s-1"]
    assert no["groups"][1]["lead"]["rc"] == "senate/119_2_00007"

    plain = ds.get_member_page("X000001", 1, None, None, True)["record"]
    assert [g["bill_id"] for g in plain["groups"]] == ["119-s-1"] and plain["plain"] is True
    assert plain["groups"][0]["headline"] == "Plain one"

    assert ds.get_member_page("X000001", 1, None, "maybe")["record"]["position"] is None
    assert ds.get_member_page("X000001", 1, "Nothing here")["record"]["groups"] == []


def test_recent_votes_on_the_page_use_the_index_and_withheld_summaries(tmp_path):
    rows = [_row(9, "119-s-1", "Yea", area="Health"), _row(8, "119-s-2", "Nay", area="Energy")]
    summaries = {"119-s-1": {"one_liner": "Plain one", "provisions": []},
                 "119-s-2": {"one_liner": "Withheld line", "provisions": [], "needs_review": True}}
    ds = _service(tmp_path, votes={"X000001": rows}, roll_calls={_key(r): _entry() for r in rows},
                  summaries=summaries)
    recent = ds.get_member_page("X000001")["recent_votes"]
    assert [(r["bill_id"], r["position"], r["one_liner"]) for r in recent] == [("119-s-1", "yes", "Plain one")]


def test_money_only_with_complete_totals_and_an_fec_id(tmp_path):
    donations = {
        "X000001": {"fec_candidate_id": "S8NY00082", "committee_id": "C00346312", "cycle": "2024",
                    "last_updated": "2026-03-20T00:10:39.880084+00:00", "totals": FULL_TOTALS,
                    "top_contributors": [{"org_name": "Example LLC", "total": 7500}]},
        "Y000002": {"fec_candidate_id": "H6FL01390", "cycle": "2024",
                    "last_updated": "2026-03-20T00:11:09+00:00", "totals": {}},
        "W000004": {"cycle": "2024", "last_updated": "2026-03-20T00:11:09+00:00", "totals": FULL_TOTALS},
    }
    ds = _service(tmp_path, donations=donations)
    assert ds.get_member_page("X000001")["donation"] == {
        "fec_candidate_id": "S8NY00082", "cycle": "2024",
        "last_updated": "2026-03-20T00:10:39.880084+00:00", "totals": FULL_TOTALS}
    assert ds.get_member_page("Y000002")["donation"] is None
    assert ds.get_member_page("W000004")["donation"] is None
    assert ds.get_member_page("Z000003")["donation"] is None


def test_sponsored_rows_are_capped_at_six_newest_first_with_a_status(tmp_path):
    bills = [_sponsored_bill(n, f"2025-01-0{n}") for n in range(1, 9)]
    bills.append(_sponsored_bill(99, "2025-02-01", sponsor="Y000002"))
    ds = _service(
        tmp_path, bills=bills,
        roll_calls={"senate/119_1_00077": _entry(result="Bill Passed (68-32)", day="2025-03-01")},
        index_bills={"119-s-8": {"roll_calls": ["senate/119_1_00077"], "activity_date": "2025-03-01"}},
        summaries={"119-s-8": {"one_liner": "Plain eight", "provisions": []},
                   "119-s-7": {"one_liner": "Withheld", "provisions": [], "needs_review": True}},
    )
    page = ds.get_member_page("X000001")
    assert page["sponsored_count"] == 8
    assert [b["number"] for b in page["sponsored"]] == ["8", "7", "6", "5", "4", "3"]
    assert set(page["sponsored"][0]) == {"congress", "type", "number", "title", "introduced_date",
                                         "policy_area", "one_liner", "status"}
    assert [b["one_liner"] for b in page["sponsored"][:2]] == ["Plain eight", None]
    for row in page["sponsored"]:
        assert isinstance(row["status"]["text"], str) and row["status"]["text"]
        assert row["status"]["variant"] in ("final", "moving")
    assert "Sen. Doe, Jane [D-NY]" not in json.dumps(page)


def test_member_without_a_vote_file_gets_the_header_only(tmp_path):
    page = _service(tmp_path).get_member_page("Z000003")
    assert page["has_record"] is False
    assert (page["stats"], page["record"], page["first_vote_date"], page["nominations_count"]) == (None, None, None, None)
    assert page["recent_votes"] == []
    assert page["member"]["bioguideId"] == "Z000003" and "partyName" not in page["member"]


def test_unknown_member_has_no_page(tmp_path):
    assert _service(tmp_path).get_member_page("Q999999") is None


# --- Fixture slices (T1.1): the real S000148 and G000602 files ---

@pytest.fixture(scope="module")
def fixture_service():
    return DataService(data_dir=FIXTURES)


def _vote_count(groups):
    total = 0
    for group in groups:
        if group["kind"] == "bill":
            total += 1 + len(group["more"])
        elif group["kind"] == "other":
            total += len(group["votes"])
        else:
            total += 1
    return total


def _no_bill_count(groups):
    return sum(len(g["votes"]) if g["kind"] == "other" else 1 for g in groups if g["kind"] != "bill")


def _whole_record(service, member_id):
    """The member's grouped record on every page at once: the record get_member_page pages."""
    data = service.get_member_votes(member_id)
    return service._record_from_votes(_newest_first(data["votes"]), data.get("policy_areas"), None, None, False)


def test_schumer_record_accounts_for_every_fixture_vote(fixture_service):
    rows = json.loads((FIXTURES / "member_votes" / "S000148.json").read_text())["votes"]
    assert len(rows) == 1061
    assert sum(1 for r in rows if r.get("bill_id") is None) == 478
    record = _whole_record(fixture_service, "S000148")
    assert _vote_count(record["groups"]) == 1061
    assert _no_bill_count(record["groups"]) == 478
    assert record["total_bills"] == len({r["bill_id"] for r in rows if r.get("bill_id")})


def test_schumer_fixture_amendment_row_carries_its_parent_bill(fixture_service):
    # Spec §10 #22: the parent parsed for the fixture's amendment. T1.1 cut senate/119_2_00223
    # ("S.Amdt. 6715 to S.Amdt. 6711 to H.R. 5334"; the S000148 row has bill_id null) for this.
    record = _whole_record(fixture_service, "S000148")
    others = [v for g in record["groups"] if g["kind"] == "other" for v in g["votes"]]
    vote = next(v for v in others if v["rc"] == "senate/119_2_00223")
    assert vote["parent"] == {"bill_id": "119-hr-5334", "congress": 119, "bill_type": "hr",
                              "bill_number": 5334, "in_bills": True}


def test_schumer_fixture_page_header_and_first_page(fixture_service):
    page = fixture_service.get_member_page("S000148")
    assert page["stats"] == {"total_votes": 1061, "yea_count": 519, "nay_count": 540, "not_voting_count": 1}
    assert page["other_count"] == 1
    assert page["first_vote_date"].startswith("2021-01-06")
    assert isinstance(page["nominations_count"], int)
    record = page["record"]
    assert len(record["groups"]) == 15
    assert record["pages"] == -(-record["total_groups"] // 15)
    assert len(page["sponsored"]) <= 6


def test_gillen_speaker_vote_is_neutral_on_every_page(fixture_service):
    first = fixture_service.get_member_page("G000602")
    assert first["stats"] == {"total_votes": 657, "yea_count": 335, "nay_count": 302, "not_voting_count": 16}
    assert first["other_count"] == 4
    assert first["nominations_count"] is None
    pages = [first] + [fixture_service.get_member_page("G000602", n) for n in range(2, first["record"]["pages"] + 1)]
    dumped = json.dumps(pages)
    assert "Jeffries" not in dumped and "Johnson (LA)" not in dumped
    speakers = [g for p in pages for g in p["record"]["groups"] if g["kind"] == "speaker"]
    assert [g["vote"]["vote"] for g in speakers] == ["Voted"]
    assert fixture_service.get_speaker_votes("G000602") == {"house/119_1_00002": "Jeffries"}
    assert fixture_service.get_speaker_votes("S000148") == {}


# --- Real data (data/synced; votes_index.json is committed by T1.4) ---

@pytest.fixture(scope="module")
def real_service():
    if not (REAL / "votes_index.json").exists() or not (REAL / "member_votes" / "S000148.json").exists():
        pytest.skip("data/synced/votes_index.json or S000148 member_votes not present")
    return DataService(data_dir=REAL)


def test_real_schumer_recent_votes_follow_the_published_rule(real_service):
    picked = real_service.get_member_page("S000148")["recent_votes"]
    assert 1 <= len(picked) <= 8
    rows = json.loads((REAL / "member_votes" / "S000148.json").read_text())["votes"]
    raw = {rc_key_or_none(r["chamber"], r["congress"], r["session"], r["vote_number"]): r for r in rows}
    roll_calls = real_service._votes_index["roll_calls"]
    for pick in picked:
        row = raw[pick["rc"]]
        assert roll_calls[pick["rc"]]["class"] == "D"
        assert pick["position"] == {"Yea": "yes", "Aye": "yes", "Nay": "no", "No": "no"}[row["vote"]]
        assert real_service.displayable_summary(pick["bill_id"])
        assert pick["policy_area"] == row["policy_area"] != ""
    assert len({p["bill_id"] for p in picked}) == len(picked)
    days = [p["date"][:10] for p in picked]
    assert days == sorted(days, reverse=True)

    def qualifies(r):
        key = rc_key_or_none(r["chamber"], r["congress"], r["session"], r["vote_number"])
        return (r.get("bill_id") and r.get("policy_area") and r["vote"] in ("Yea", "Aye", "Nay", "No")
                and real_service.displayable_summary(r["bill_id"])
                and roll_calls.get(key, {}).get("class") == "D")

    newest = next(r for r in sorted(
        rows, key=lambda r: (r["date"][:10], r["congress"], r["session"], r["vote_number"]), reverse=True)
        if qualifies(r))
    assert picked[0]["rc"] == rc_key_or_none(newest["chamber"], newest["congress"], newest["session"],
                                            newest["vote_number"])


def test_real_schumer_amendment_rows_carry_their_parent_bill(real_service):
    record = _whole_record(real_service, "S000148")
    others = [v for g in record["groups"] if g["kind"] == "other" for v in g["votes"]]
    with_parent = [v for v in others if (v["roll_call"] or {}).get("parent")]
    assert with_parent, "S000148 has amendment roll calls whose question names a parent bill"
    for vote in with_parent:
        assert vote["parent"]["bill_id"] == vote["roll_call"]["parent"]


# --- Routers (fixture data dir, the pattern of tests/test_routers.py) ---

async def _get(path):
    from app.dependencies import get_data_service
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    get_data_service.cache_clear()
    return response


@pytest.mark.asyncio
async def test_page_endpoint_returns_the_page_payload():
    response = await _get("/api/members/S000148/page")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == PAGE_KEYS | {"record_tree"}  # T10.2 adds the render tree
    assert data["member"]["bioguideId"] == "S000148"
    assert data["record"]["page"] == 1 and len(data["record"]["groups"]) == 15


@pytest.mark.asyncio
async def test_page_endpoint_passes_filters_through():
    record = (await _get("/api/members/S000148/page?page=2&position=no&plain=1")).json()["record"]
    assert (record["page"], record["position"], record["plain"]) == (min(2, record["pages"]), "no", True)
    for group in record["groups"]:
        assert group["kind"] == "bill" and group["displayable"] is True
        assert group["lead"]["vote"] in ("Nay", "No")


@pytest.mark.asyncio
async def test_page_endpoint_errors():
    assert (await _get("/api/members/X999999/page")).status_code == 404
    assert (await _get("/api/members/bad/page")).status_code == 400
    assert (await _get("/api/members/S000148/page?position=maybe")).status_code == 422


@pytest.mark.asyncio
async def test_page_endpoint_hides_speaker_candidate_names_and_party():
    first = (await _get("/api/members/G000602/page")).json()
    for n in range(1, first["record"]["pages"] + 1):
        response = await _get(f"/api/members/G000602/page?page={n}")
        assert response.status_code == 200
        assert "Jeffries" not in response.text
        assert '"partyName"' not in response.text and '"participation_rate"' not in response.text


@pytest.mark.asyncio
async def test_detail_reveals_speaker_votes_only_with_show_party():
    default = await _get("/api/members/detail/G000602")
    assert "speaker_votes" not in default.json() and "Jeffries" not in default.text
    revealed = (await _get("/api/members/detail/G000602?show_party=true")).json()
    assert revealed["speaker_votes"] == {"house/119_1_00002": "Jeffries"}
    assert revealed["member"]["bioguideId"] == "G000602"


def test_real_speaker_not_voting_rows_are_not_shown_as_voted(real_service):
    if not (REAL / "member_votes" / "H001095.json").exists():
        pytest.skip("H001095 not in the real data")
    first = real_service.get_member_page("H001095")
    pages = [first] + [real_service.get_member_page("H001095", n) for n in range(2, first["record"]["pages"] + 1)]
    raw = {_key(r): r["vote"] for r in json.loads((REAL / "member_votes" / "H001095.json").read_text())["votes"]}
    speakers = [g["vote"] for p in pages for g in p["record"]["groups"] if g["kind"] == "speaker"]
    assert speakers
    for vote in speakers:
        if raw.get(vote["rc"]) == "Not Voting":
            assert vote["vote"] == "Not Voting"
    assert "Not Voting" not in real_service.get_speaker_votes("H001095").values()


# --- In-place record pagination (plan T10.2): one render tree feeds the HTML and the JSON ---
import json as _json
import re as _re
import shutil as _shutil
import subprocess as _subprocess
from pathlib import Path as _Path
from unittest.mock import patch as _patch

import pytest as _pytest
from httpx import ASGITransport as _ASGITransport, AsyncClient as _AsyncClient

_ROOT = _Path(__file__).parent.parent
_FIXTURES = _ROOT / "tests" / "fixtures" / "synced"
_SITE_JS = _ROOT / "static" / "js" / "site.js"


async def _paging_get(path: str):
    from app.dependencies import get_data_service
    from app.main import app
    with _patch("app.dependencies.get_data_dir", return_value=_FIXTURES):
        get_data_service.cache_clear()
        async with _AsyncClient(transport=_ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(path)
    get_data_service.cache_clear()
    return response


def _record_list_block(html: str, hook: str = "data-record-list") -> str:
    """The <div {hook}=""> element, balanced on nested divs."""
    start = html.index(f'<div {hook}="">')
    depth, i = 0, start
    while True:
        next_open, next_close = html.find("<div", i), html.find("</div>", i)
        if next_open != -1 and next_open < next_close:
            depth, i = depth + 1, next_open + 4
        else:
            depth, i = depth - 1, next_close + 6
            if depth == 0:
                return html[start:i]


def test_tree_html_escapes_text_and_attributes():
    from app.render import N, tree_html
    out = tree_html(N("p", {"class": '"><img src=x>'}, "<script>alert(1)</script>", " &amp; "))
    assert "<script>" not in out and "<img" not in out
    assert out == '<p class="&quot;&gt;&lt;img src=x&gt;">&lt;script&gt;alert(1)&lt;/script&gt; &amp;amp; </p>'


@_pytest.mark.parametrize("bad", [
    lambda N: N("script", None, "x"),
    lambda N: N("a", {"onclick": "x"}),
    lambda N: N("a", {"href": "javascript:alert(1)"}),
    lambda N: N("a", {"href": "//evil.example/"}),
    lambda N: N("span", {"style": "color:red"}),
])
def test_tree_nodes_reject_what_the_allowlist_does_not_name(bad):
    from app.render import N
    with _pytest.raises(ValueError):
        bad(N)


def test_tree_allowlists_match_site_js():
    from app.render import TREE_ATTRS, TREE_TAGS
    source = _SITE_JS.read_text()

    def js_list(name):
        match = _re.search(rf"const {name} = \[([^\]]*)\]", source)
        assert match, f"site.js has no const {name} = [...]"
        return frozenset(_re.findall(r"'([^']+)'", match.group(1)))

    assert js_list("TREE_TAGS") == TREE_TAGS
    assert js_list("TREE_ATTRS") == TREE_ATTRS


@_pytest.mark.asyncio
@_pytest.mark.parametrize("query", ["", "&page=2", "&position=no", "&plain=1", "&topic=Health", "&position=nv&page=9"])
async def test_page_api_carries_everything_the_record_renders(query):
    from app.render import tree_html
    html = (await _paging_get(f"/member?id=S000148{query}")).text
    payload = (await _paging_get(f"/api/members/S000148/page?{query.lstrip('&')}")).json()
    assert set(payload["record_tree"]) == {"result", "list"}
    assert tree_html(payload["record_tree"]["list"]) == _record_list_block(html)
    assert tree_html(payload["record_tree"]["result"]) == _record_list_block(html, "data-record-result")


@_pytest.mark.asyncio
async def test_record_keeps_the_section_order_with_two_swap_targets():
    html = (await _paging_get("/member?id=S000148&position=no")).text
    order = [html.index(marker) for marker in (
        'id="record"', '<div data-record-result=""><p class="result-line">', 'class="meta record-count"',
        'data-record-filter=""', '<div data-record-list="">')]
    assert order == sorted(order)
    unfiltered = (await _paging_get("/member?id=S000148")).text
    assert '<div data-record-result=""></div>' in unfiltered


@_pytest.mark.asyncio
async def test_record_links_keep_the_filters_and_land_on_the_heading():
    import html as _html
    from app.render import tree_html
    payload = (await _paging_get("/api/members/S000148/page?position=no")).json()
    tags = _re.findall(r'<a [^>]*data-record-nav=""[^>]*>', tree_html(payload["record_tree"]["list"]))
    nav = [_html.unescape(_re.search(r'href="([^"]+)"', tag).group(1)) for tag in tags]
    assert nav, "page 1 of a filtered record has an 'Older votes' link"
    for href in nav:
        assert href.startswith("/member?id=S000148") and "position=no" in href and href.endswith("#record")


_HARNESS = r"""
const [sitePath, treePath] = process.argv.slice(2);
const tree = JSON.parse(require('fs').readFileSync(treePath, 'utf8'));
class Text { constructor(t) { this.data = String(t); } get textContent() { return this.data; } }
class Elem {
  constructor(tag) { this.tag = String(tag).toLowerCase(); this.attrs = []; this.kids = [];
    this.classList = { add: () => {}, remove: () => {}, toggle: () => {}, contains: () => false }; }
  setAttribute(k, v) { const hit = this.attrs.find(a => a[0] === k); if (hit) hit[1] = String(v); else this.attrs.push([k, String(v)]); }
  getAttribute(k) { const hit = this.attrs.find(a => a[0] === k); return hit ? hit[1] : null; }
  set className(v) { this.setAttribute('class', v); }
  get className() { return this.getAttribute('class') || ''; }
  appendChild(c) { this.kids.push(c); return c; }
  append(...cs) { cs.forEach(c => this.appendChild(typeof c === 'string' ? new Text(c) : c)); }
  set textContent(v) { this.kids = [new Text(v)]; }
  get textContent() { return this.kids.map(k => k.textContent).join(''); }
  addEventListener() {}
}
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const BOOL = new Set(['hidden', 'open']);
const html = n => n instanceof Text ? esc(n.data)
  : `<${n.tag}${n.attrs.map(([k, v]) => (BOOL.has(k) && v === '') ? ` ${k}` : ` ${k}="${esc(v)}"`).join('')}>${n.kids.map(html).join('')}</${n.tag}>`;
const noop = () => {};
const store = { getItem: () => null, setItem: noop, removeItem: noop };
Object.assign(globalThis, {
  window: globalThis, addEventListener: noop, removeEventListener: noop,
  document: { readyState: 'loading', addEventListener: noop, createElement: t => new Elem(t), createTextNode: t => new Text(t),
    querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
    documentElement: new Elem('html'), body: new Elem('body') },
  location: { href: 'http://127.0.0.1/', search: '', hash: '', pathname: '/' },
  history: { replaceState: noop }, localStorage: store, sessionStorage: store,
  matchMedia: () => ({ matches: false, addEventListener: noop, addListener: noop }),
});
const api = require(sitePath);
if (typeof api.buildTree !== 'function') { console.error('site.js does not export buildTree'); process.exit(2); }
process.stdout.write(html(api.buildTree(tree.result)) + html(api.buildTree(tree.list)));
"""


@_pytest.mark.asyncio
@_pytest.mark.skipif(_shutil.which("node") is None, reason="node not installed")
async def test_site_js_builds_the_same_record_as_the_server(tmp_path):
    from app.render import tree_html
    payload = (await _paging_get("/api/members/S000148/page?page=2&position=no")).json()
    (tmp_path / "tree.json").write_text(_json.dumps(payload["record_tree"]))
    (tmp_path / "harness.js").write_text(_HARNESS)
    result = _subprocess.run(
        [_shutil.which("node"), str(tmp_path / "harness.js"), str(_SITE_JS), str(tmp_path / "tree.json")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == tree_html(payload["record_tree"]["result"]) + tree_html(payload["record_tree"]["list"])


def test_site_js_record_paging_uses_replace_state_and_no_html_sinks():
    source = _SITE_JS.read_text()
    paging = source[source.index("function initRecordPaging"):]
    paging = paging[: paging.index("\n}\n") + 3]
    assert "history.replaceState" in paging and "pushState" not in source
    assert "innerHTML" not in paging and "insertAdjacentHTML" not in paging and "DOMParser" not in paging
    assert "focusHeading(" in paging
    assert "[data-record-result]" in paging and "[data-record-list]" in paging
    # The call, not the declaration: `function initRecordPaging() {` also contains "initRecordPaging()".
    assert _re.search(r"^\s+initRecordPaging\(\);", source, _re.M), "initRecordPaging(); is not called at init"
