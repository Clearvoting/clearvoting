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
