"""The two sanctioned data files (spec §2.2 #6, §5.1, §10 #1-#2) and the invariants
of the real-data fixture slices every later test relies on (§10 #22)."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SYNCED = ROOT / "data" / "synced"
FIXTURES = Path(__file__).parent / "fixtures" / "synced"
COVERED = {"CA", "FL", "NY", "TX"}
FIXTURE_ZIPS = {"10001", "11201", "11570", "73949", "88430", "89019", "97635"}


def _load(path: Path):
    return json.loads(path.read_text())


# --- Sanctioned files: provenance ---

@pytest.mark.parametrize("name", ["zip_districts.json", "senate_2026.json"])
def test_sanctioned_file_has_source(name):
    source = _load(SYNCED / name)["_source"]
    assert source["url"].startswith("https://")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["retrieved"])
    assert source["name"]


@pytest.mark.parametrize("name", ["zip_districts.json", "senate_2026.json"])
def test_sanctioned_file_listed_in_sources_md(name):
    sources_md = (ROOT / "data" / "SOURCES.md").read_text()
    source = _load(SYNCED / name)["_source"]
    assert f"data/synced/{name}" in sources_md
    assert source["retrieved"] in sources_md


# --- Crosswalk ---

def test_crosswalk_shape():
    data = _load(SYNCED / "zip_districts.json")
    # Loaders skip every "_" key; _source is the only one.
    assert [k for k in data if k.startswith("_")] == ["_source"]
    zips = {k: v for k, v in data.items() if not k.startswith("_")}
    assert len(zips) == 6639
    for zip_code, districts in zips.items():
        assert re.fullmatch(r"\d{5}", zip_code)
        assert districts, zip_code
        shares = [d["share"] for d in districts]
        assert shares == sorted(shares, reverse=True), zip_code
        for d in districts:
            assert d["state"] in COVERED
            assert isinstance(d["district"], int) and d["district"] >= 1
            assert 0 < d["share"] <= 1


def test_crosswalk_source_describes_land_area_share():
    source = _load(SYNCED / "zip_districts.json")["_source"]
    assert source["retrieved"] == "2026-09-11"
    assert source["url"] == "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/"
    assert "land area" in source["share"]
    assert "17 U.S.C." in source["licence"]


def test_crosswalk_known_zips():
    data = _load(SYNCED / "zip_districts.json")
    assert data["11570"] == [{"district": 4, "share": 1.0, "state": "NY"}]
    assert [(d["state"], d["district"]) for d in data["11201"]] == [("NY", 10), ("NY", 7)]
    assert data["73949"] == [{"district": 13, "share": 0.1367, "state": "TX"}]


# --- Senate seats up in 2026 ---

def test_senate_2026_seats():
    data = _load(SYNCED / "senate_2026.json")
    assert data["election_day"] == "2026-11-03"
    seats = {s["bioguideId"]: s for s in data["seats"]}
    assert set(seats) == {"C001056", "M001244"}
    assert seats["C001056"]["kind"] == "regular" and seats["C001056"]["state"] == "TX"
    assert seats["M001244"]["kind"] == "special" and seats["M001244"]["state"] == "FL"
    for seat in data["seats"]:
        assert type(seat["class"]) is int and seat["class"] in (1, 2, 3)


def test_senate_2026_seats_are_real_members():
    members = {m["bioguideId"] for m in _load(SYNCED / "members.json")["members"]}
    for seat in _load(SYNCED / "senate_2026.json")["seats"]:
        assert seat["bioguideId"] in members


# --- Fixture slices (§10 #22) ---

def test_fixture_sanctioned_files_mirror_real_ones():
    real = _load(SYNCED / "zip_districts.json")
    fixture = _load(FIXTURES / "zip_districts.json")
    assert fixture["_source"] == real["_source"]
    assert set(fixture) - {"_source"} == FIXTURE_ZIPS
    for zip_code in FIXTURE_ZIPS:
        assert fixture[zip_code] == real[zip_code]
    assert _load(FIXTURES / "senate_2026.json") == _load(SYNCED / "senate_2026.json")


def test_fixture_member_votes_are_whole_real_files():
    s000148 = _load(FIXTURES / "member_votes" / "S000148.json")
    assert len(s000148["votes"]) == 1061
    assert sum(1 for v in s000148["votes"] if v["bill_id"] is None) == 478
    g000602 = _load(FIXTURES / "member_votes" / "G000602.json")
    assert g000602["member_id"] == "G000602"


def test_fixture_roll_calls_keep_real_counts_and_covered_members():
    vote = _load(FIXTURES / "votes" / "house" / "119_2_00295.json")
    assert vote["document"] == "H.R. 4795"
    assert vote["counts"] == {"yeas": 237, "nays": 169, "present": 0, "absent": 27}
    assert {m["state"] for m in vote["members"]} <= COVERED
    old = _load(FIXTURES / "votes" / "house" / "117_1_00006.json")
    assert old["congress"] == 117
    assert "G000602" not in {m["bioguide_id"] for m in old["members"]}


def test_fixture_members_have_real_names_only():
    members = {m["bioguideId"]: m for m in _load(FIXTURES / "members.json")["members"]}
    assert members["S000148"]["name"] == "Schumer, Charles E."
    assert "directOrderName" not in members["S000148"]
    assert {"G000555", "G000602", "R000579", "C001056"} <= set(members)


def test_fixture_donations_cover_complete_empty_and_missing():
    donations = _load(FIXTURES / "donations.json")
    assert set(donations["S000148"]["totals"]) == {
        "total_receipts", "total_individual", "total_pac", "total_disbursements"
    }
    assert donations["R000579"]["totals"] == {}
    assert "D000032" not in donations


def test_fixture_ai_summaries_include_withheld_and_arguments():
    summaries = _load(FIXTURES / "ai_summaries.json")
    assert summaries["119-hr-7148"]["needs_review"] is True
    assert any("arguments" in s for s in summaries.values())
    assert "119-hr-4795" not in summaries  # a real unsummarized bill


def test_fixture_hostile_title_bill():
    bills = _load(FIXTURES / "bills.json")["bills"]
    hostile = [b for b in bills if b["number"] == "99999"]
    assert len(hostile) == 1
    for ch in ("<b>", "&", '"', "'"):
        assert ch in hostile[0]["title"]


def test_fixture_sync_metadata_has_ai_summaries_updated():
    assert _load(FIXTURES / "sync_metadata.json")["ai_summaries_updated"] == "2026-07-07"
