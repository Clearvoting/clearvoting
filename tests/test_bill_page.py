"""Bill page payload and additive roll-call fields (plan T1.8; spec §4.4, §7.2, §7.3, §10 #10)."""
import builtins
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.data_service import DataService, first_paragraph_text, relation_text

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REAL = Path(__file__).resolve().parent.parent / "data" / "synced"

PAGE_KEYS = {
    "bill_id", "congress", "bill_type", "number", "title", "has_summary", "one_liner",
    "provisions", "official_summary", "official_first_paragraph", "status", "head", "roll_calls",
    "sponsor", "sponsor_covered", "cosponsors_count", "policy_area", "introduced_date", "laws",
    "legislation_url",
}
RC_KEYS = {
    "key", "chamber", "congress", "session", "vote_number", "date", "question", "plain",
    "class", "result", "counts", "threshold", "document", "seal", "outcome", "state_tallies",
    "rendered", "members", "covered",
}
ROW_KEYS = {"first_name", "last_name", "state", "vote", "bioguide_id", "covered_id", "district"}


def _vote_file_reads(fn):
    """Run fn() and return (its result, the roll-call file paths it opened)."""
    real_open = builtins.open
    opened: list[str] = []

    def counting_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=counting_open):
        result = fn()
    return result, [p for p in opened if "/votes/house/" in p or "/votes/senate/" in p]


# --- Synthetic data dir: members, bills, three roll-call files, an index ---

def _member(bioguide, name, state, chamber, district=None):
    row = {"bioguideId": bioguide, "name": name, "stateCode": state, "state": state,
           "chamber": chamber, "partyName": "Democratic",
           "terms": {"item": [{"chamber": chamber, "startYear": 2021}]}}
    if district is not None:
        row["district"] = district
    return row


MEMBERS = [
    _member("A000001", "Alpha, Ann", "NY", "House of Representatives", 4),
    _member("B000002", "Beta, Bea", "NY", "House of Representatives", 5),
    _member("C000003", "Gamma, Cal", "FL", "House of Representatives", 7),
    _member("X000001", "Doe, Jane", "NY", "Senate"),
    _member("W000004", "Roe, Pat", "FL", "Senate"),
]


def _entry(question, plain, cls, result, day, document, counts=(60, 40, 0, 0)):
    yeas, nays, present, absent = counts
    return {"question": question, "plain": plain, "class": cls, "result": result,
            "counts": {"yeas": yeas, "nays": nays, "present": present, "absent": absent},
            "date": day, "document": document, "bill": None, "parent": None, "threshold": None,
            "tallies": {"CA": [0, 1, 0], "FL": [0, 1, 1], "NY": [2, 0, 0], "TX": [0, 1, 0]}}


ROLL_CALLS = {
    "senate/119_1_00020": _entry("On Passage of the Bill H.R. 50", "Final vote to pass", "D",
                                 "Bill Passed (60-40)", "2025-06-10", "H.R. 50"),
    "house/119_1_00010": _entry("On Passage", "Final vote to pass", "D", "Passed", "2025-05-01", "H.R. 50",
                                counts=(237, 169, 0, 27)),
    "house/119_1_00009": _entry("On Agreeing to the Amendment", "Vote on an amendment", "P", "Failed",
                                "2025-05-01", "H.R. 50", counts=(189, 235, 0, 9)),
    "house/119_1_00030": _entry("On Agreeing to the Amendment", "Vote on an amendment", "P", "Failed",
                                "2025-04-01", "H.R. 51", counts=(190, 230, 0, 13)),
}
INDEX_BILLS = {
    "119-hr-50": {"roll_calls": ["senate/119_1_00020", "house/119_1_00010", "house/119_1_00009"],
                  "activity_date": "2025-06-10"},
    "119-hr-51": {"roll_calls": ["house/119_1_00030"], "activity_date": "2025-04-01"},
}


def _house_row(bioguide, first, last, state, vote):
    return {"bioguide_id": bioguide, "first_name": first, "last_name": last, "party": "D",
            "state": state, "vote": vote}


def _senate_row(first, last, state, vote):
    return {"first_name": first, "last_name": last, "party": "R", "state": state, "vote": vote,
            "lis_member_id": "S999"}


ROLL_CALL_FILES = {
    ("house", "119_1_00010"): [
        _house_row("A000001", "Ann", "Alpha", "NY", "Yea"),
        _house_row("C000003", "Cal", "Gamma", "FL", "Not Voting"),
        _house_row("Z000009", "Zed", "Zulu", "FL", "Nay"),
        _house_row("O000001", "Oh", "Ohio", "OH", "Yea"),
    ],
    ("house", "119_1_00009"): [_house_row("A000001", "Ann", "Alpha", "NY", "Nay")],
    ("house", "119_1_00030"): [_house_row("B000002", "Bea", "Beta", "NY", "Yea")],
    ("senate", "119_1_00020"): [
        _senate_row("Jane", "Doe", "NY", "Yea"),
        _senate_row("John", "Doe", "CA", "Nay"),
        _senate_row("Sam", "Smith", "TX", "Nay"),
    ],
}


def _bill(number, title, summaries, sponsors, laws=None):
    bill = {"congress": 119, "type": "HR", "number": str(number), "title": title,
            "introducedDate": "2025-01-01", "latestAction": {"actionDate": "2025-06-10", "text": "Became law."},
            "sponsors": sponsors, "cosponsors": {"count": 3}, "policyArea": {"name": "Health"},
            "summaries": summaries,
            "legislationUrl": f"https://www.congress.gov/bill/119th-congress/house-bill/{number}"}
    if laws:
        bill["laws"] = laws
    return bill


BILLS = [
    _bill(50, "Test Act of 2025", [
        {"actionDate": "2025-01-01", "actionDesc": "Introduced in House", "text": "<p>Introduced version.</p>"},
        {"actionDate": "2025-03-01", "actionDesc": "Public Law",
         "text": "<p>This bill <em>bans</em> x &amp; y.</p><p>Second paragraph.</p>"},
        {"actionDate": "2025-05-01", "actionDesc": "Passed Senate", "text": "<p>Newest, not the law.</p>"},
    ], [{"bioguideId": "A000001", "fullName": "Rep. Alpha, Ann [D-NY-4]", "firstName": "Ann",
         "lastName": "Alpha", "state": "NY", "district": 4, "party": "D"}],
          laws=[{"type": "Public Law", "number": "119-6"}]),
    _bill(51, 'The <b>Bold</b> & "Quoted" Act', [
        {"actionDate": "2025-02-01", "actionDesc": "Introduced in House", "text": "<p>Older.</p>"},
        {"actionDate": "2025-04-01", "actionDesc": "Reported to House", "text": "<p>Newer.</p>"},
    ], [{"bioguideId": "S001195", "fullName": "Rep. Smith, Jason [R-MO-8]", "firstName": "Jason",
         "lastName": "Smith", "state": "MO", "district": 8, "party": "R"}]),
    _bill(52, "Never Voted Act", [], []),
]
SUMMARIES = {
    "119-hr-50": {"one_liner": "Bans x", "provisions": ["Bans x"], "issue_categories": [],
                  "arguments": {"for": ["unsourced"], "against": ["unsourced"]}},
    "119-hr-51": {"one_liner": "Withheld line", "provisions": ["Withheld"], "needs_review": True},
}


@pytest.fixture
def synthetic(tmp_path):
    (tmp_path / "members.json").write_text(json.dumps({"members": MEMBERS}))
    (tmp_path / "bills.json").write_text(json.dumps({"bills": BILLS}))
    (tmp_path / "ai_summaries.json").write_text(json.dumps(SUMMARIES))
    (tmp_path / "votes_index.json").write_text(json.dumps(
        {"roll_calls": ROLL_CALLS, "bills": INDEX_BILLS, "latest": "senate/119_1_00020",
         "generated_at": "2026-09-05T00:00:00Z"}))
    for (chamber, stem), rows in ROLL_CALL_FILES.items():
        folder = tmp_path / "votes" / chamber
        folder.mkdir(parents=True, exist_ok=True)
        congress, session, number = (int(p) for p in stem.split("_"))
        (folder / f"{stem}.json").write_text(json.dumps({
            "congress": congress, "session": session, "vote_number": number, "vote_date": "2025-05-01",
            "question": "On Passage", "document": "H.R. 50", "result": "Passed",
            "counts": {"yeas": 1, "nays": 1, "present": 0, "absent": 0}, "members": rows}))
    return DataService(data_dir=tmp_path)


# --- get_bill_page over the synthetic dir ---

def test_head_is_the_newest_decisive_roll_call_and_two_files_are_read(synthetic):
    page, reads = _vote_file_reads(lambda: synthetic.get_bill_page(119, "HR", 50))
    assert set(page) == PAGE_KEYS
    assert (page["bill_id"], page["congress"], page["bill_type"], page["number"]) == ("119-hr-50", 119, "hr", 50)
    assert [rc["key"] for rc in page["roll_calls"]] == [
        "senate/119_1_00020", "house/119_1_00010", "house/119_1_00009"]
    assert page["head"]["key"] == "senate/119_1_00020"
    assert [rc["rendered"] for rc in page["roll_calls"]] == [True, True, False]
    assert sorted(Path(p).name for p in reads) == ["119_1_00010.json", "119_1_00020.json"]
    for rc in page["roll_calls"]:
        assert set(rc) == RC_KEYS
    house = page["roll_calls"][1]
    assert (house["chamber"], house["congress"], house["session"], house["vote_number"]) == ("house", 119, 1, 10)
    assert house["date"] == "2025-05-01"
    assert house["state_tallies"] == ROLL_CALLS["house/119_1_00010"]["tallies"]
    assert house["plain"] == "Final vote to pass" and house["class"] == "D"
    assert isinstance(house["seal"], str) and house["seal"]
    assert isinstance(house["outcome"], str) and house["outcome"]
    skipped = page["roll_calls"][2]
    assert (skipped["members"], skipped["covered"]) == ([], {})


def test_covered_members_get_the_reader_relation(synthetic):
    page = synthetic.get_bill_page(119, "hr", 50)
    house = page["roll_calls"][1]["covered"]
    assert set(house) == {"A000001", "B000002", "C000003"}
    assert house["A000001"] == {"name": "Ann Alpha", "state": "NY", "district": 4, "chamber": "House",
                                "position": "Yea", "relation": "Voted yes"}
    assert (house["B000002"]["position"], house["B000002"]["relation"]) == (None, "Not in the House for this vote")
    assert house["C000003"]["relation"] == "Didn't vote"
    senate = page["roll_calls"][0]["covered"]
    assert set(senate) == {"X000001", "W000004"}
    assert (senate["X000001"]["relation"], senate["X000001"]["district"]) == ("Voted yes", None)
    assert senate["W000004"]["relation"] == "Not in the Senate for this vote"
    dumped = json.dumps(page)
    assert '"party"' not in dumped and "partyName" not in dumped and "Democratic" not in dumped


def test_rendered_rows_cover_only_the_four_states_without_party(synthetic):
    page = synthetic.get_bill_page(119, "hr", 50)
    house_rows = page["roll_calls"][1]["members"]
    assert all(set(row) == ROW_KEYS for row in house_rows)
    assert [row["state"] for row in house_rows] == ["NY", "FL", "FL"]
    assert house_rows[0] == {"first_name": "Ann", "last_name": "Alpha", "state": "NY", "vote": "Yea",
                             "bioguide_id": "A000001", "covered_id": "A000001", "district": 4}
    assert (house_rows[2]["covered_id"], house_rows[2]["district"]) == (None, None)
    senate_rows = page["roll_calls"][0]["members"]
    assert [(r["last_name"], r["state"], r["bioguide_id"], r["covered_id"]) for r in senate_rows] == [
        ("Doe", "NY", None, "X000001"), ("Doe", "CA", None, None), ("Smith", "TX", None, None)]


@pytest.mark.parametrize("position,chamber,expected", [
    ("Yea", "House", "Voted yes"), ("Aye", "House", "Voted yes"),
    ("Nay", "Senate", "Voted no"), ("No", "House", "Voted no"),
    ("Not Voting", "House", "Didn't vote"), ("Present", "Senate", "Present"),
    ("Present, Giving Live Pair", "Senate", "Present"), ("Guilty", "Senate", "Guilty"),
    ("Jeffries", "House", "Voted"),
    (None, "House", "Not in the House for this vote"), (None, "Senate", "Not in the Senate for this vote"),
])
def test_relation_text(position, chamber, expected):
    assert relation_text(position, chamber) == expected


def test_other_chamber_falls_back_to_its_newest_roll_call():
    # House decisive head; the Senate only took procedural votes (real: 117-hr-3233, 117-hr-7,
    # 117-hr-4350, 118-hr-6126). Both chambers render, still at most two roll calls (two reads).
    from app.services.data_service import _pick_rendered
    views = [{"key": "senate/119_1_00041", "chamber": "senate", "class": "P"},
             {"key": "senate/119_1_00040", "chamber": "senate", "class": "P"},
             {"key": "house/119_1_00012", "chamber": "house", "class": "D"}]
    picked = _pick_rendered(views)
    assert [rc["key"] for rc in picked] == ["house/119_1_00012", "senate/119_1_00041"]
    assert sorted(rc["chamber"] for rc in picked) == ["house", "senate"]
    # A decisive vote in the other chamber still wins over a newer procedural one. (senate/40 is
    # now the newest decisive roll call, so it becomes the head; compare the picked set.)
    views[1]["class"] = "D"
    assert sorted(rc["key"] for rc in _pick_rendered(views)) == ["house/119_1_00012", "senate/119_1_00040"]


def test_bill_without_a_decisive_vote_describes_its_latest(synthetic):
    page, reads = _vote_file_reads(lambda: synthetic.get_bill_page(119, "hr", 51))
    assert page["head"]["key"] == "house/119_1_00030" and page["head"]["class"] == "P"
    assert [rc["rendered"] for rc in page["roll_calls"]] == [True]
    assert page["status"]["text"] == "No final vote yet"
    assert len(reads) == 1


def test_bill_without_roll_calls_has_no_head_and_reads_no_files(synthetic):
    page, reads = _vote_file_reads(lambda: synthetic.get_bill_page(119, "hr", 52))
    assert (page["roll_calls"], page["head"], reads) == ([], None, [])
    assert page["status"] == {"text": "No final vote yet", "variant": "moving"}
    assert (page["sponsor"], page["sponsor_covered"]) == (None, False)
    assert (page["official_summary"], page["official_first_paragraph"]) == (None, None)


def test_official_summary_prefers_public_law_then_newest(synthetic):
    law = synthetic.get_bill_page(119, "hr", 50)
    assert law["official_summary"] == "<p>This bill <em>bans</em> x &amp; y.</p><p>Second paragraph.</p>"
    assert law["official_first_paragraph"] == "This bill bans x & y."
    assert synthetic.get_bill_page(119, "hr", 51)["official_summary"] == "<p>Newer.</p>"


def test_first_paragraph_text_skips_the_bold_short_title():
    # Real 119-hr-4795 shape: a bold short-title paragraph comes first (G7 T7.1 pins the same rule).
    html = ("<p><strong>Protect Economic and Academic Freedom Act of 2026</strong></p>"
            "<p>This bill prohibits institutions of higher education from engaging in boycotts.</p>")
    assert first_paragraph_text(html).startswith("This bill prohibits")
    assert first_paragraph_text("<p><strong>Only A Title Act</strong></p>") == "Only A Title Act"


def test_first_paragraph_text_is_plain_text():
    assert first_paragraph_text("<p>One <b>bold</b>\n  line.</p><p>Two.</p>") == "One bold line."
    assert first_paragraph_text("No paragraph tags &amp; entities") == "No paragraph tags & entities"
    out = first_paragraph_text('<p><script>alert(1)</script>Safe <a href="javascript:alert(1)">text</a></p>')
    assert "<" not in out and "javascript:" not in out and "Safe text" in out


def test_withheld_summary_is_shown_like_a_missing_one(synthetic):
    shown = synthetic.get_bill_page(119, "hr", 50)
    assert (shown["has_summary"], shown["one_liner"], shown["provisions"]) == (True, "Bans x", ["Bans x"])
    withheld = synthetic.get_bill_page(119, "hr", 51)
    assert (withheld["has_summary"], withheld["one_liner"], withheld["provisions"]) == (False, None, [])
    assert "unsourced" not in json.dumps(shown)


def test_sponsor_and_facts_carry_no_party_cue(synthetic):
    covered = synthetic.get_bill_page(119, "hr", 50)
    assert covered["sponsor"] == {"bioguideId": "A000001", "firstName": "Ann", "lastName": "Alpha",
                                  "state": "NY", "district": 4, "fullName": "Rep. Alpha, Ann"}
    assert covered["sponsor_covered"] is True
    assert (covered["cosponsors_count"], covered["policy_area"], covered["introduced_date"]) == (3, "Health", "2025-01-01")
    assert covered["laws"] == [{"type": "Public Law", "number": "119-6"}]
    assert covered["legislation_url"] == "https://www.congress.gov/bill/119th-congress/house-bill/50"
    assert covered["status"]["variant"] in ("final", "moving")
    other = synthetic.get_bill_page(119, "hr", 51)
    assert other["sponsor"]["fullName"] == "Rep. Smith, Jason" and other["sponsor_covered"] is False
    assert other["title"] == 'The <b>Bold</b> & "Quoted" Act'
    assert "[R-" not in json.dumps(other) and "[D-" not in json.dumps(covered)


def test_unknown_or_malformed_bill_has_no_page(synthetic):
    assert synthetic.get_bill_page(119, "hr", 999) is None
    assert synthetic.get_bill_page("x", "hr", 50) is None


# --- Fixture slices (T1.1) ---

@pytest.fixture(scope="module")
def fixture_service():
    return DataService(data_dir=FIXTURES)


def test_fixture_hjres_20_renders_both_chambers(fixture_service):
    page = fixture_service.get_bill_page(119, "hjres", 20)
    assert PAGE_KEYS <= set(page)
    assert len(page["roll_calls"]) == 2
    assert [rc["rendered"] for rc in page["roll_calls"]].count(True) == 2
    senate = next(rc for rc in page["roll_calls"] if rc["chamber"] == "senate")
    scott = next(row for row in senate["members"] if row["last_name"] == "Scott")
    assert scott["covered_id"] == "S001217"
    assert senate["covered"]["S001217"]["relation"] == relation_text(scott["vote"], "Senate")
    assert senate["covered"]["S000148"]["relation"] == "Not in the Senate for this vote"


def test_gillen_was_not_in_the_house_for_a_117th_congress_roll_call(fixture_service):
    covered = fixture_service.covered_positions("house", fixture_service.get_house_vote(117, 1, 6))
    assert covered["G000602"]["relation"] == "Not in the House for this vote"
    assert covered["D000032"]["relation"] == "Voted no"
    page = fixture_service.get_bill_page(117, "hres", 8)
    rendered = [rc for rc in page["roll_calls"] if rc["rendered"]]
    assert rendered
    for rc in rendered:
        assert rc["covered"]["G000602"]["relation"] == "Not in the House for this vote"
        assert all(row["district"] is None for row in rc["members"])


def test_fixture_118_hr_21_reads_at_most_two_roll_call_files(fixture_service):
    page, reads = _vote_file_reads(lambda: fixture_service.get_bill_page(118, "hr", 21))
    assert page is not None
    assert len(page["roll_calls"]) == len(fixture_service._index_bill_keys("118-hr-21"))
    assert len(reads) <= 2


def test_real_118_hr_21_reads_at_most_two_of_its_roll_call_files():
    if not (REAL / "votes_index.json").exists():
        pytest.skip("data/synced/votes_index.json not built")
    service = DataService(data_dir=REAL)
    page, reads = _vote_file_reads(lambda: service.get_bill_page(118, "hr", 21))
    assert len(page["roll_calls"]) == len(service._index_bill_keys("118-hr-21")) >= 50
    assert len(reads) <= 2
    assert sum(rc["rendered"] for rc in page["roll_calls"]) == len(reads)


# --- Routers: additive fields only ---

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
async def test_bill_payload_gains_official_summary_and_keeps_its_old_keys():
    data = (await _get("/api/bills/119/hjres/20")).json()
    assert {"bill", "subjects", "official_summary"} <= set(data)
    assert "sponsors" in data["bill"]
