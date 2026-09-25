"""Member page blocks (spec §4.3) — plan Tasks T6.1–T6.3.

The renderers are pure functions over DataService.get_member_page() output, so the
unit tests build that dict directly from real values (S000148, G000602, W000832,
donations.json, roll-call files). Fixture- and real-data tests are added by T6.2/T6.3."""
import html
import re
from pathlib import Path

import pytest

from app import render

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REAL = Path(__file__).parent.parent / "data" / "synced"


def _text(fragment: str) -> str:
    """Visible text of an HTML fragment: tags dropped, entities decoded, spaces collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


SCHUMER = {
    "bioguideId": "S000148",
    "name": "Schumer, Charles E.",
    "state": "New York",
    "stateCode": "NY",
    "district": None,
    "chamber": "Senate",
    "terms": {"item": [
        {"chamber": "House of Representatives", "startYear": 1981, "endYear": 1999},
        {"chamber": "Senate", "startYear": 1999},
    ]},
    "depiction": {"imageUrl": "https://www.congress.gov/img/member/s000148_200.jpg"},
}
GILLEN = {
    "bioguideId": "G000602",
    "name": "Gillen, Laura",
    "state": "New York",
    "stateCode": "NY",
    "district": 4,
    "chamber": "House of Representatives",
    "terms": {"item": [{"chamber": "House of Representatives", "startYear": 2025}]},
    "depiction": {"imageUrl": "https://www.congress.gov/img/member/677427de0b34857ecc9090ad_200.jpg"},
}
WAHAB = {  # the one member with no photo in members.json
    "bioguideId": "W000832",
    "name": "Wahab, Aisha",
    "state": "California",
    "stateCode": "CA",
    "district": 14,
    "chamber": "House of Representatives",
    "terms": {"item": [{"chamber": "House of Representatives", "startYear": 2026}]},
}
GILLEN_STATS = {"total_votes": 657, "yea_count": 335, "nay_count": 302, "not_voting_count": 16}

# votes_index.json roll_calls entries (spec §10 #3), values from data/synced/votes/senate/119_2_00228.json
RC_HR6500_PASSAGE = {
    "question": "On Passage of the Bill H.R. 6500", "plain": "Final vote to pass", "class": "D",
    "result": "Bill Passed (90-6, 3/5 majority required)",
    "counts": {"yeas": 90, "nays": 6, "present": 1, "absent": 3},
    "date": "2026-08-08", "document": "H.R. 6500", "bill": "119-hr-6500", "parent": None,
    "threshold": "3/5", "tallies": {},
}


def _recent(n: int) -> list[dict]:
    """n rows shaped like get_member_page()['recent_votes'], alternating yes/no."""
    base = {
        "rc": "senate/119_2_00228", "roll_call": RC_HR6500_PASSAGE, "chamber": "Senate",
        "bill_id": "119-hr-6500", "congress": 119, "bill_type": "hr", "bill_number": 6500,
        "one_liner": "Extend no-tax imports from 32 African countries through 2028",
        "position": "yes", "date": "2026-08-08T03:37:00",
        "policy_area": "Foreign Trade and International Finance",
    }
    return [dict(base, position="yes" if i % 2 == 0 else "no") for i in range(n)]


def _page(member=SCHUMER, **overrides) -> dict:
    """A dict shaped like DataService.get_member_page() (the T1.7 contract)."""
    page = {
        "member": member,
        "seat": None,
        "has_record": True,
        "stats": {"total_votes": 1061, "yea_count": 519, "nay_count": 540, "not_voting_count": 1},
        "first_vote_date": "2021-01-06",
        "last_vote_date": "2026-08-08",
        "nominations_count": 1203,
        "recent_votes": _recent(8),
        "record": {
            "groups": [], "page": 1, "pages": 1, "per_page": 15, "total_groups": 0,
            "matching_bills": 0, "topic": None, "position": None, "plain": False,
            "policy_areas": ["Health", "Taxation"], "plain_bills": 150, "total_bills": 268,
        },
        "sponsored": [],
        "sponsored_count": 0,
        "donation": None,
    }
    page.update(overrides)
    return page


def _house_page(member=GILLEN, **overrides) -> dict:
    base = dict(stats=GILLEN_STATS, first_vote_date="2025-01-03", nominations_count=None, seat="regular")
    base.update(overrides)
    return _page(member, **base)


# --- Header (§4.3 fold, m1) ---

def test_senator_header_fold_copy():
    out = render.render_member_header(_page())
    text = _text(out)
    assert "← New York's representatives" in text
    assert 'href="/state?code=NY" data-state="NY"' in out
    assert "U.S. Senator · New York" in text
    assert re.search(r'<header class="member-header"[^>]*>.*<h1>Charles E\. Schumer</h1>', out, re.S)
    assert ("In Congress since 1981 — House 1981–1999, Senate since 1999 · Voted in 1,060 of the 1,061 "
            "Senate votes on bills, amendments and motions in our record since January 2021") in text


def test_representative_header_kicker_fact_line_and_seat_seal():
    out = render.render_member_header(_house_page())
    text = _text(out)
    assert "U.S. Representative · New York, District 4" in text
    assert "In Congress since 2025 · Voted in 641 of the 657 House roll calls since January 2025" in text
    assert "This seat is on the ballot Nov 3, 2026" in text
    assert "seal--ballot" in out


def test_special_election_seat_copy_describes_the_seat():
    out = render.render_member_header(_page(seat="special"))
    assert "Special election for this seat Nov 3, 2026" in _text(out)


def test_no_seat_seal_when_the_seat_is_not_up():
    out = render.render_member_header(_page(seat=None))
    assert "ballot" not in out.lower()
    assert "Special election" not in out


def test_header_photo_is_not_lazy_and_has_empty_alt():
    out = render.render_member_header(_page())
    assert '<img src="https://www.congress.gov/img/member/s000148_200.jpg" alt="" width="64" height="64">' in out
    assert 'data-initials="CS"' in out
    assert "loading=" not in out


def test_member_without_photo_gets_the_initials_block():
    out = render.render_member_header(_house_page(WAHAB))
    assert 'data-initials="AW"' in out
    assert "<img" not in out


def test_photo_from_a_host_outside_the_csp_is_dropped():
    member = dict(SCHUMER, depiction={"imageUrl": "https://example.com/s000148.jpg"})
    assert "<img" not in render.render_member_header(_page(member))


def test_header_action_row_and_empty_status_nodes():
    out = render.render_member_header(_page())
    assert '<button class="party-toggle" type="button">Show party labels</button>' in out
    assert "aria-pressed" not in out
    assert out.count('role="status"></span>') == 2
    assert '<span class="party"></span>' in out
    assert 'data-share-url="https://clearvoting.org/member?id=S000148"' in out
    assert 'data-share-text="How Charles E. Schumer has voted in Congress"' in out
    assert 'href="https://www.congress.gov/member/charles-e-schumer/S000148"' in out


@pytest.mark.parametrize("name, bioguide, slug", [
    ("Nydia M. Velázquez", "V000081", "nydia-m-velazquez"),   # the three accented names in members.json
    ("Nanette Diaz Barragán", "B001300", "nanette-diaz-barragan"),
    ("Linda T. Sánchez", "S001156", "linda-t-sanchez"),
    ("Charles E. Schumer", "S000148", "charles-e-schumer"),
])
def test_congress_gov_member_slug_folds_accents(name, bioguide, slug):
    assert render._mp_congress_gov_member_url(name, bioguide) == f"https://www.congress.gov/member/{slug}/{bioguide}"


def test_header_without_a_record_shows_tenure_only():
    out = render.render_member_header(_page(has_record=False, stats=None, first_vote_date=None))
    text = _text(out)
    assert "In Congress since 1981" in text
    assert "Voted in" not in text


# --- Shared vote row (§6.4) and Recent votes (§4.3 m2) ---

def test_vote_row_is_one_link_with_chip_headline_and_meta():
    out = render.render_vote_row(
        "/bill?congress=119&type=hr&number=6500", '<span class="chip chip--yes">Voted yes</span>',
        "Extend no-tax imports", True, ["H.R. 6500", "", "Aug 8, 2026"])
    assert out.startswith('<a class="vote-row" href="/bill?congress=119&amp;type=hr&amp;number=6500">')
    assert out.count("<a ") == 1
    assert 'class="row-headline"' in out
    assert "<h" not in out.replace("href", "")  # rows contain no heading elements
    assert "H.R. 6500 · Aug 8, 2026" in _text(out)  # empty meta parts are skipped


def test_vote_row_official_title_fallback_and_no_link():
    out = render.render_vote_row(None, "", "A bill to amend the Help America Vote Act of 2002", False, ["S. 5271"])
    assert out.startswith('<div class="vote-row">')
    assert 'class="row-headline row-headline--official"' in out


def test_recent_votes_rows_link_and_carry_the_meta_line():
    out = render.render_recent_votes(_recent(8))
    # The mobile fold names a *kicker* "Recent votes" (§4.3): an h2 styled as a kicker, the
    # same markup as the home card's "The latest vote" (completeness residual 4).
    assert '<h2 class="kicker" id="recent-h">Recent votes</h2>' in out
    assert out.count('class="vote-row"') == 8
    assert 'href="/bill?congress=119&amp;type=hr&amp;number=6500"' in out
    text = _text(out)
    assert "H.R. 6500 · Passed the Senate 90–6 · Aug 8, 2026 · Foreign Trade and International Finance" in text
    assert text.count("Voted yes") == 4
    assert text.count("Voted no") == 4
    assert '<span class="chip chip--yes">Voted yes</span>' in out
    assert '<span class="chip chip--no">Voted no</span>' in out


def test_recent_votes_caption_prints_the_rule_and_links_it():
    out = render.render_recent_votes(_recent(8))
    assert ("The eight most recent final votes on bills with a plain-English summary, one per topic "
            "where possible, whatever the member's position. How this list is chosen →") in _text(out)
    assert 'href="/methodology#recent-votes"' in out


def test_short_record_says_how_many_qualify():
    out = render.render_recent_votes(_recent(3))
    assert out.count('class="vote-row"') == 3
    assert "3 recent votes so far." in _text(out)
    assert "The eight" not in out


def test_one_recent_vote_is_singular():
    assert "1 recent vote so far." in _text(render.render_recent_votes(_recent(1)))


def test_no_qualifying_votes_omits_the_module():
    assert render.render_recent_votes([]) == ""


# --- Bills they sponsored that got a floor vote (§4.3 m5) ---

SPONSORED = [
    {"congress": 119, "type": "S", "number": "3385", "title": "Lower Health Care Costs Act",
     "introduced_date": "2025-12-08",
     "one_liner": "Keep health insurance tax credits in place for three more years through 2028",
     "status": {"text": "No final vote yet", "variant": "moving"}},
    {"congress": 118, "type": "SRES", "number": "417", "title": "A resolution standing with Israel against terrorism.",
     "introduced_date": "2023-10-19", "one_liner": None,
     "status": {"text": "Adopted by the Senate 97–0", "variant": "final"}},
]


def test_sponsored_rows_heading_and_congress_gov_link():
    out = render.render_sponsored(SPONSORED, "Charles E. Schumer", "S000148", total=2)
    text = _text(out)
    assert '<h2 id="sponsored-h">Bills they sponsored that got a floor vote (2)</h2>' in out
    assert out.count('class="bill-row"') == 2
    assert 'href="/bill?congress=119&amp;type=s&amp;number=3385"' in out
    assert 'href="/bill?congress=118&amp;type=sres&amp;number=417"' in out
    assert "S. 3385" in text and "S.Res. 417" in text
    assert "Introduced Dec 8, 2025" in text
    assert "Adopted by the Senate 97–0" in text
    assert 'href="https://www.congress.gov/member/charles-e-schumer/S000148"' in out
    assert "All legislation Charles E. Schumer sponsored, on Congress.gov →" in text


def test_sponsored_row_without_displayable_summary_uses_the_official_title_once():
    out = render.render_sponsored(SPONSORED, "Charles E. Schumer", "S000148", total=2)
    assert out.count("A resolution standing with Israel against terrorism.") == 1
    assert 'class="row-headline row-headline--official"' in out
    assert "No plain-English summary yet" in out


def test_sponsored_list_is_capped_at_six_rows_but_counts_all():
    bills = [dict(SPONSORED[0], number=str(3000 + i)) for i in range(8)]
    out = render.render_sponsored(bills, "Charles E. Schumer", "S000148", total=8)
    assert out.count('class="bill-row"') == 6
    assert "(8)</h2>" in out


def test_no_sponsored_bills_shows_heading_and_link_only():
    out = render.render_sponsored([], "Laura Gillen", "G000602", total=0)
    assert "Bills they sponsored that got a floor vote (0)" in _text(out)
    assert "bill-row" not in out
    assert 'href="https://www.congress.gov/member/laura-gillen/G000602"' in out


# --- Campaign money (§4.3 m7) ---

SCHUMER_DONATION = {  # data/synced/donations.json["S000148"] (top_contributors trimmed)
    "fec_candidate_id": "S8NY00082", "committee_id": "C00346312", "cycle": "2024",
    "last_updated": "2026-03-20T00:10:39.880084+00:00", "top_contributors": [], "top_industries": [],
    "totals": {"total_receipts": 2790888, "total_disbursements": 3349300,
               "total_individual": 2345346, "total_pac": 202800},
}
EMPTY_TOTALS_DONATION = {  # data/synced/donations.json["P000622"]
    "fec_candidate_id": "H6FL01390", "committee_id": "C00893594", "cycle": "2024",
    "last_updated": "2026-03-20T00:11:09.485021+00:00", "top_contributors": [], "top_industries": [],
    "totals": {},
}
MONEY_SENTENCE = (
    "In the 2023–2024 FEC reporting period (the 2024 cycle), this member's campaign committee reported "
    "$2.8 million raised ($2.3 million from individuals, $202,800 from PACs) and $3.3 million spent; "
    "retrieved March 20, 2026. The 2025–2026 period is not yet in our data. Filings on FEC.gov →"
)
NO_MONEY = "Campaign finance isn't in our data for this member yet."


def test_money_sentence_when_totals_are_complete():
    out = render.render_money(SCHUMER_DONATION)
    assert '<h2 id="money-h">Campaign money</h2>' in out
    assert MONEY_SENTENCE in _text(out)
    assert 'href="https://www.fec.gov/data/candidate/S8NY00082/"' in out


def test_money_meta_line_when_totals_are_empty():
    out = render.render_money(EMPTY_TOTALS_DONATION)
    assert NO_MONEY in _text(out)
    assert "fec.gov" not in out


def test_money_meta_line_when_member_has_no_entry():
    assert NO_MONEY in _text(render.render_money(None))


def test_money_meta_line_when_a_total_or_the_fec_id_is_missing():
    partial = dict(SCHUMER_DONATION, totals={"total_receipts": 2790888})
    no_id = dict(SCHUMER_DONATION, fec_candidate_id="")
    assert NO_MONEY in _text(render.render_money(partial))
    assert NO_MONEY in _text(render.render_money(no_id))


def test_money_never_prints_bars_or_contributors():
    out = render.render_money(dict(SCHUMER_DONATION, top_contributors=[{"org_name": "BARCLAYS", "total": 6600}]))
    assert "BARCLAYS" not in out
    assert "%" not in out


# ===================== The record (§4.3 m4) — plan T6.2 =====================

from app.services.data_service import DataService  # noqa: E402

# votes_index entries, values from the real roll-call files named in each comment
RC_HR6500_CLOTURE = {  # illustrative procedural vote on the same bill
    "question": "On Cloture on the Motion to Proceed H.R. 6500", "plain": "Vote to end debate (needed 60)",
    "class": "P", "result": "Cloture on the Motion to Proceed Agreed to (89-4, 3/5 majority required)",
    "counts": {"yeas": 89, "nays": 4, "present": 0, "absent": 7}, "date": "2026-08-03",
    "document": "H.R. 6500", "bill": "119-hr-6500", "parent": None, "threshold": "3/5", "tallies": {},
}
RC_S5271_CLOTURE = {  # votes/senate/119_2_00231.json
    "question": "On Cloture on the Motion to Proceed S. 5271", "plain": "Vote to end debate (needed 60)",
    "class": "P", "result": "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)",
    "counts": {"yeas": 52, "nays": 46, "present": 0, "absent": 2}, "date": "2026-08-08",
    "document": "S. 5271", "bill": "119-s-5271", "parent": None, "threshold": "3/5", "tallies": {},
}
RC_TABLE_227 = {  # votes/senate/119_2_00227.json
    "question": "On the Motion to Table S.Amdt. 6747 to S.Amdt. 6732 to H.R. 6500 (No short title on file)",
    "plain": "Vote to set it aside", "class": "P", "result": "Motion to Table Agreed to (61-32)",
    "counts": {"yeas": 61, "nays": 32, "present": 0, "absent": 7}, "date": "2026-08-08",
    "document": "To strike section 2019.", "bill": None, "parent": "119-hr-6500", "threshold": None, "tallies": {},
}
RC_QUORUM = {  # votes/house/119_2_00001.json
    "question": "Call of the House", "plain": "Attendance call", "class": "P", "result": "Passed",
    "counts": {"yeas": 0, "nays": 0, "present": 406, "absent": 24}, "date": "2026-01-06",
    "document": "", "bill": None, "parent": None, "threshold": None, "tallies": {},
}
RC_ADJOURN = {  # votes/house/119_1_* "On Motion to Adjourn" (G000602 voted Aye)
    "question": "On Motion to Adjourn", "plain": "Vote to adjourn", "class": "P", "result": "Failed",
    "counts": {"yeas": 8, "nays": 403, "present": 0, "absent": 22}, "date": "2025-06-12",
    "document": "", "bill": None, "parent": None, "threshold": None, "tallies": {},
}
RC_SPEAKER = {  # votes/house/119_1_00002.json
    "question": "Election of the Speaker", "plain": "Election of the Speaker", "class": "P",
    "result": "Johnson (LA)", "counts": {"yeas": 0, "nays": 0, "present": 0, "absent": 0},
    "date": "2025-01-03", "document": "", "bill": None, "parent": None, "threshold": None, "tallies": {},
}
PARENT_HR6500 = {"bill_id": "119-hr-6500", "congress": 119, "bill_type": "hr", "bill_number": 6500, "in_bills": True}
S5271_TITLE = "A bill to amend the Help America Vote Act of 2002 to require voters to provide photo identification."


def _vote(rc_key, rc, vote, when, result, chamber="Senate", text="", parent=None) -> dict:
    return {"rc": rc_key, "roll_call": rc, "chamber": chamber, "vote": vote, "date": when,
            "result": result, "text": text, "parent": parent}


def _bill_group(bill_type="hr", number=6500, headline="Extend no-tax imports from 32 African countries through 2028",
                displayable=True, lead=None, more=None) -> dict:
    return {"kind": "bill", "bill_id": f"119-{bill_type}-{number}", "congress": 119,
            "bill_type": bill_type, "bill_number": number, "headline": headline,
            "displayable": displayable,
            "lead": lead or _vote("senate/119_2_00228", RC_HR6500_PASSAGE, "Yea", "2026-08-08T03:37:00",
                                  "Bill Passed (90-6, 3/5 majority required)"),
            "more": more or []}


def _record(**overrides) -> dict:
    record = {"groups": [_bill_group()], "page": 1, "pages": 1, "per_page": 15, "total_groups": 1,
              "matching_bills": 1, "topic": None, "position": None, "plain": False,
              "policy_areas": ["Health", "Taxation"], "plain_bills": 150, "total_bills": 268}
    record.update(overrides)
    return record


def test_record_heading_is_the_focus_target_senate_wording():
    out = render.render_record_section(_page(record=_record()))
    assert '<h2 id="record" tabindex="-1">Votes on bills, amendments and motions, by bill</h2>' in out
    assert 'aria-labelledby="record"' in out


def test_record_heading_house_wording():
    out = render.render_record_section(_house_page(record=_record()))
    assert '<h2 id="record" tabindex="-1">Every roll call, by bill</h2>' in out


def test_count_line_is_verbatim_from_stats_with_the_other_bucket():
    text = _text(render.render_record_section(_page(record=_record())))
    assert "1,061 roll calls since January 2021 · 519 yes · 540 no · 1 didn't vote · 1 other" in text


def test_count_line_omits_other_when_it_is_zero():
    page = _page(record=_record(), stats={"total_votes": 10, "yea_count": 6, "nay_count": 4, "not_voting_count": 0})
    text = _text(render.render_record_section(page))
    assert "10 roll calls since January 2021 · 6 yes · 4 no · 0 didn't vote" in text
    assert "other" not in text.split("didn't vote")[1].split("Senate votes")[0]


def test_house_count_line_counts_present_and_speaker_as_other():
    text = _text(render.render_record_section(_house_page(record=_record())))
    assert "657 roll calls since January 2025 · 335 yes · 302 no · 16 didn't vote · 4 other" in text


def test_senators_get_the_nominations_scope_line():
    out = render.render_record_section(_page(record=_record()))
    assert ("Senate votes on nominations (1,203 since January 2021) aren't in this record yet. Why →"
            in _text(out))
    assert 'href="/methodology#coverage"' in out


def test_house_members_have_no_nominations_line():
    assert "nominations" not in render.render_record_section(_house_page(record=_record()))


def test_filter_form_is_a_plain_get_form():
    out = render.render_record_section(_page(record=_record()))
    assert '<form class="record-filter" id="record-filter" method="get" action="/member#record">' in out
    assert '<input type="hidden" name="id" value="S000148">' in out
    assert '<option value="">All topics</option>' in out
    assert '<option value="Health">Health</option>' in out
    text = _text(out)
    assert "All positions" in text and "Voted yes" in text and "Voted no" in text and "Didn't vote" in text
    assert '<input type="checkbox" id="record-plain" name="plain" value="1">' in out
    assert "Only bills with a plain-English summary (150 of 268 bills)" in text
    assert '<button class="btn" type="submit">Filter</button>' in out


def test_active_filters_are_reflected_and_counted():
    record = _record(topic="Health", position="no", plain=True, matching_bills=12)
    out = render.render_record_section(_page(record=record))
    assert '<option value="Health" selected>Health</option>' in out
    assert '<option value="no" selected>Voted no</option>' in out
    assert 'name="plain" value="1" checked>' in out
    assert "12 bills on Health · Voted no · with a plain-English summary" in _text(out)
    assert out.index("12 bills on Health") < out.index('class="meta record-count"')


def test_unfiltered_record_has_no_result_line():
    assert 'class="result-line"' not in render.render_record_section(_page(record=_record()))


def test_bill_group_row_seal_date_chip_and_more_roll_calls():
    more = [_vote("senate/119_2_00210", RC_HR6500_CLOTURE, "Yea", "2026-08-03T17:30:00",
                  "Cloture on the Motion to Proceed Agreed to (89-4, 3/5 majority required)")]
    out = render.render_record_section(_page(record=_record(groups=[_bill_group(more=more)])))
    text = _text(out)
    assert "H.R. 6500 · Passed the Senate 90–6 · Aug 8, 2026" in text
    assert 'class="row-headline">Extend no-tax imports from 32 African countries through 2028<' in out
    assert "+ 1 more roll call on this bill" in text
    phrase = render.result_phrase(RC_HR6500_CLOTURE, "Senate")
    assert f"Vote to end debate (needed 60) · {phrase} · Aug 3, 2026 · Voted yes · Roll call source →" in text
    assert ('href="https://www.senate.gov/legislative/LIS/roll_call_votes/vote1192/vote_119_2_00210.htm"'
            in out)
    group = out[out.index('<li class="group group--bill">'):]
    assert group.index("</a>") < group.index("<details")  # the details sit beside the row link, not in it


def test_two_more_roll_calls_are_plural():
    more = [_vote("senate/119_2_00210", RC_HR6500_CLOTURE, "Yea", "2026-08-03T17:30:00", "x")] * 2
    out = render.render_record_section(_page(record=_record(groups=[_bill_group(more=more)])))
    assert "+ 2 more roll calls on this bill" in _text(out)


def test_unsummarized_bill_prints_the_official_title_once_with_the_pending_seal():
    lead = _vote("senate/119_2_00231", RC_S5271_CLOTURE, "Nay", "2026-08-08T04:36:00",
                 "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)")
    group = _bill_group("s", 5271, S5271_TITLE, False, lead)
    out = render.render_record_section(_page(record=_record(groups=[group])))
    assert out.count(S5271_TITLE) == 1
    assert 'class="row-headline row-headline--official"' in out
    assert "No plain-English summary yet" in out
    assert f"S. 5271 · {render.result_phrase(RC_S5271_CLOTURE, 'Senate')} · Aug 8, 2026" in _text(out)


@pytest.mark.parametrize("bill_type", ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"])
def test_every_bill_type_links_to_its_bill_page(bill_type):
    out = render.render_record_section(_page(record=_record(groups=[_bill_group(bill_type, 7)])))
    assert f'href="/bill?congress=119&amp;type={bill_type}&amp;number=7"' in out


def test_amendment_motion_row_names_its_parent_bill_and_links_it():
    vote = _vote("senate/119_2_00227", RC_TABLE_227, "Yea", "2026-08-08T02:36:00",
                 "Motion to Table Agreed to (61-32)", text="To strike section 2019.", parent=PARENT_HR6500)
    out = render.render_record_section(_page(record=_record(groups=[{"kind": "other", "date": "2026-08-08", "votes": [vote]}])))
    text = _text(out)
    assert "1 motion · Aug 8, 2026" in text
    phrase = render.result_phrase(RC_TABLE_227, "Senate")
    assert f'Motion "To strike section 2019." to H.R. 6500 · {phrase} · Voted yes · Roll call source →' in text
    assert 'to <a href="/bill?congress=119&amp;type=hr&amp;number=6500">H.R. 6500</a>' in out


def test_parent_not_in_bills_json_is_named_but_not_linked():
    vote = _vote("senate/119_2_00227", RC_TABLE_227, "Yea", "2026-08-08T02:36:00",
                 "Motion to Table Agreed to (61-32)", text="To strike section 2019.",
                 parent=dict(PARENT_HR6500, in_bills=False))
    out = render.render_record_section(_page(record=_record(groups=[{"kind": "other", "date": "2026-08-08", "votes": [vote]}])))
    assert "to H.R. 6500" in _text(out)
    assert "number=6500" not in out


def test_vote_with_no_text_and_no_parent_says_so():
    rc = dict(RC_TABLE_227, parent=None, result="Motion Rejected (50-49, 3/5 majority required)",
              plain="Procedural vote", question="On the Motion")
    vote = _vote("senate/119_2_00151", rc, "Nay", "2026-06-05T23:39:00", "Motion Rejected (50-49, 3/5 majority required)")
    out = render.render_record_section(_page(record=_record(groups=[{"kind": "other", "date": "2026-06-05", "votes": [vote]}])))
    phrase = render.result_phrase(rc, "Senate")
    assert f"Senate vote · no bill or amendment text in our data · {phrase} · Voted no" in _text(out)


def test_house_procedural_vote_without_text_reads_as_a_chamber_motion():
    """§4.3 m4: a procedural question is labelled "Motion", and a Motion with no text and no
    parent reads "{Chamber} vote · no bill or amendment text in our data · …"."""
    vote = _vote("house/119_1_00160", RC_ADJOURN, "Aye", "2025-06-12T00:00:00", "Failed", chamber="House")
    out = render.render_record_section(_house_page(record=_record(groups=[{"kind": "other", "date": "2025-06-12", "votes": [vote]}])))
    phrase = render.result_phrase(RC_ADJOURN, "House")
    text = _text(out)
    assert f"House vote · no bill or amendment text in our data · {phrase} · Voted yes" in text
    assert "Vote to adjourn" not in text
    assert "1 motion · Jun 12, 2025" in text


def test_attendance_call_row_reads_like_the_spec():
    vote = _vote("house/119_2_00001", RC_QUORUM, "Present", "2026-01-06T00:00:00", "Passed", chamber="House")
    out = render.render_record_section(_house_page(record=_record(groups=[{"kind": "other", "date": "2026-01-06", "votes": [vote]}])))
    text = _text(out)
    assert "Attendance call · Jan 6, 2026 · Present · Roll call source →" in text
    assert 'href="https://clerk.house.gov/Votes/20261"' in out


def test_a_day_of_amendments_and_motions_collapses_into_one_row():
    votes = []
    for i in range(14):
        result = "Amendment Rejected (45-53)" if i % 2 else "Motion to Table Agreed to (61-32)"
        votes.append(_vote(f"senate/119_2_{200 + i:05d}", dict(RC_TABLE_227, result=result), "Yea",
                           "2026-08-08T01:00:00", result, text="To strike section 2019."))
    out = render.render_record_section(_page(record=_record(groups=[{"kind": "other", "date": "2026-08-08", "votes": votes}])))
    assert out.count('<li class="group group--other">') == 1
    assert "14 amendments and motions · Aug 8, 2026" in _text(out)


def test_speaker_row_is_neutral_and_carries_an_empty_pick_slot():
    vote = _vote("house/119_1_00002", RC_SPEAKER, "Jeffries", "2025-01-03T00:00:00", "Johnson (LA)", chamber="House")
    out = render.render_record_section(_house_page(record=_record(groups=[{"kind": "speaker", "vote": vote}])))
    assert "Election of the Speaker · Jan 3, 2025 · Voted" in _text(out)
    assert '<span class="speaker-pick" data-rc="house/119_1_00002"></span>' in out
    assert "Jeffries" not in out
    assert "Johnson" not in out


def test_speaker_vote_inside_a_day_group_is_still_masked():
    vote = _vote("house/119_1_00002", RC_SPEAKER, "Jeffries", "2025-01-03T00:00:00", "Johnson (LA)", chamber="House")
    quorum = _vote("house/119_1_00001", dict(RC_QUORUM, date="2025-01-03"), "Present", "2025-01-03T00:00:00",
                   "Passed", chamber="House")
    group = {"kind": "other", "date": "2025-01-03", "votes": [vote, quorum]}
    out = render.render_record_section(_house_page(record=_record(groups=[group])))
    assert "Jeffries" not in out and "Johnson" not in out
    assert 'data-rc="house/119_1_00002"' in out


def test_filters_that_match_nothing_say_so():
    out = render.render_record_section(_page(record=_record(groups=[], topic="Health", matching_bills=0, total_groups=0)))
    assert "No votes match these filters." in _text(out)
    assert 'id="record-filter"' in out


def test_pagination_links_carry_page_filters_and_the_record_fragment():
    record = _record(page=2, pages=3, topic="Health", position="no", plain=True, matching_bills=40)
    out = render.render_record_section(_page(record=record))
    assert '<nav class="pager" aria-label="Record pages">' in out
    assert 'href="/member?id=S000148&amp;topic=Health&amp;position=no&amp;plain=1#record">← Newer votes</a>' in out
    assert 'href="/member?id=S000148&amp;page=3&amp;topic=Health&amp;position=no&amp;plain=1#record">Older votes →</a>' in out
    assert "Page 2 of 3" in _text(out)


def test_first_and_last_pages_have_one_direction_only():
    first = render.render_record_section(_page(record=_record(page=1, pages=3)))
    last = render.render_record_section(_page(record=_record(page=3, pages=3)))
    assert "Older votes →" in first and "← Newer votes" not in first
    assert "← Newer votes" in last and "Older votes →" not in last


def test_single_page_record_has_no_pager():
    assert 'class="pager"' not in render.render_record_section(_page(record=_record()))


def test_member_page_composes_the_modules_in_fold_order():
    out = render.render_member_page(_page(record=_record(), sponsored=SPONSORED, sponsored_count=2,
                                          donation=SCHUMER_DONATION))
    order = [out.index("<h1>"), out.index('id="recent-h"'), out.index('class="vote-row"'),
             out.index('id="record"'), out.index('id="sponsored-h"'), out.index('id="money-h"')]
    assert order == sorted(order)
    assert "narrative" not in out.lower() and "summary-module" not in out


def test_member_without_a_roll_call_file_gets_the_header_and_one_sentence():
    page = _page(has_record=False, stats=None, first_vote_date=None, recent_votes=[],
                 record=None, nominations_count=None)
    out = render.render_member_page(page)
    assert "We don't have this member's roll-call record yet." in _text(out)
    assert 'id="record"' not in out and 'id="recent-h"' not in out
    assert 'id="sponsored-h"' in out and 'id="money-h"' in out


# --- Fixture-driven (tests/fixtures/synced, real slices from T1.1) ---

@pytest.fixture(scope="module")
def fixture_service():
    return DataService(FIXTURES)


def test_schumer_page_from_fixtures(fixture_service):
    page = fixture_service.get_member_page("S000148", 1, None, None, False)
    out = render.render_member_page(page)
    text = _text(out)
    assert "<h1>Charles E. Schumer</h1>" in out
    assert ("Voted in 1,060 of the 1,061 Senate votes on bills, amendments and motions in our record "
            "since January 2021") in text
    assert "1,061 roll calls since January 2021 · 519 yes · 540 no · 1 didn't vote · 1 other" in text
    assert out.index("<h1>") < out.index('id="record"')


def test_gillen_page_from_fixtures(fixture_service):
    page = fixture_service.get_member_page("G000602", 1, None, None, False)
    text = _text(render.render_member_page(page))
    assert "U.S. Representative · New York, District 4" in text
    assert "In Congress since 2025 · Voted in 641 of the 657 House roll calls since January 2025" in text
    assert "657 roll calls since January 2025 · 335 yes · 302 no · 16 didn't vote · 4 other" in text
    assert "This seat is on the ballot Nov 3, 2026" in text


# --- Real data (data/synced; votes_index.json is committed by T1.4) ---

def _all_pages(service, member_id: str) -> str:
    first = service.get_member_page(member_id, 1, None, None, False)
    pages = int(first["record"]["pages"])
    html_pages = [render.render_record_section(first)]
    for n in range(2, pages + 1):
        html_pages.append(render.render_record_section(service.get_member_page(member_id, n, None, None, False)))
    return "".join(html_pages)


@pytest.fixture(scope="module")
def real_service():
    if not (REAL / "votes_index.json").exists():
        pytest.skip("data/synced/votes_index.json not built")
    return DataService(REAL)


def test_real_gillen_record_labels_attendance_calls_and_hides_the_speaker_pick(real_service):
    out = _all_pages(real_service, "G000602")
    text = _text(out)
    assert "Attendance call · Jan 6, 2026 · Present" in text
    assert 'class="speaker-pick" data-rc="house/119_1_00002"' in out
    assert "Jeffries" not in out


def test_real_schumer_amendment_row_links_its_parent_bill(real_service):
    out = _all_pages(real_service, "S000148")
    assert 'Motion "To strike section 2019." to H.R. 6500' in _text(out)
    assert 'to <a href="/bill?congress=119&amp;type=hr&amp;number=6500">H.R. 6500</a>' in out


# §2.2 #9, §7.7, §10 #22: no stance labels or stance ratios on a rendered page. "about half"
# is deliberately not in the pattern: 119-sjres-80's one-liner "Reopen about half of a
# 23-million-acre Alaska oil reserve to drilling" is bill text on S000148's and G000602's
# records. "fight for" (no s) appears in official bill text in bills.json, so only the
# spec's "fights for" is matched.
STANCE_LANGUAGE = re.compile(
    r"\blean(s|ed|ing)?\b|mostly (in favor|against)|fights for"
    r"|\b\d[\d,]* of (the )?\d[\d,]* [a-z ]*?(in favor|against)", re.I)
NARRATIVE_MARKUP = re.compile(r'id="(summary|narrative)|class="[^"]*(member-summary|narrative)')


@pytest.mark.parametrize("member_id", ["S000148", "G000602", "W000832"])
def test_real_member_pages_carry_no_stance_language(real_service, member_id):
    page = real_service.get_member_page(member_id, 1, None, None, False)
    out = render.render_member_page(page) + _all_pages(real_service, member_id)
    assert not STANCE_LANGUAGE.search(_text(out))
    assert not NARRATIVE_MARKUP.search(out)
