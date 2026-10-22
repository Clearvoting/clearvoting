"""Delegation renderers: person rows, the state page, the ZIP finder and not-found pages
(plan T4.1; spec §4.2, §5.3, §6.4 person row, §7.4 ballot copy).

The renderers are pure string builders over an overview dict; FakeDS supplies the five
DataService reads they make, so every expected string here is exact."""
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import pytest

from app import render

BALLOT_PERSON = re.compile(r"\b(On|Not on) the ballot")
STATUS_NODES = re.compile(r'<p class="[^"]*" role="status">([^<]*)</p>')
COUNTS = {"CA": 54, "FL": 29, "NY": 28, "TX": 39}
TERMS = {
    "G000602": {"item": [{"chamber": "House of Representatives", "startYear": 2025}]},
    "G000599": {"item": [{"chamber": "House of Representatives", "startYear": 2023}]},
    "X000001": {"item": [{"chamber": "House of Representatives", "startYear": 2021}]},
    "S000148": {"item": [
        {"chamber": "House of Representatives", "startYear": 1981, "endYear": 1999},
        {"chamber": "Senate", "startYear": 1999},
    ]},
    "G000555": {"item": [
        {"chamber": "House of Representatives", "startYear": 2007, "endYear": 2009},
        {"chamber": "Senate", "startYear": 2009},
    ]},
    "M001244": {"item": [{"chamber": "Senate", "startYear": 2025}]},
}
SUMMARIES = {
    "119-hr-4795": {"one_liner": "Sample one-liner for H.R. 4795", "provisions": []},
    "119-hr-6500": {"one_liner": "Sample withheld one-liner", "needs_review": True},
}
BILLS = {
    "119-hr-4795": {"title": "Sample official title for H.R. 4795"},
    "119-hr-6500": {"title": "Sample official title for H.R. 6500"},
}
VOTE_4795 = {"rc": "house/119_2_00295", "bill_id": "119-hr-4795", "position": "Yea", "date": "2026-09-03"}


class FakeDS:
    """The DataService reads the delegation renderers make, over hand-built data."""

    def __init__(self, summaries=None, bills=None, special=(), regular_senators=(), members=None):
        self.summaries = summaries or {}
        self.bills = bills or {}
        self.special = set(special)
        self.regular_senators = set(regular_senators)
        self.members = members or {}

    def displayable_summary(self, bill_id):
        summary = self.summaries.get(bill_id)
        if not summary or summary.get("needs_review") is True:
            return None
        return summary

    def get_bill_detail(self, congress, bill_type, number):
        bill = self.bills.get(f"{congress}-{bill_type.lower()}-{number}")
        return {"bill": bill} if bill else None

    def seat_up_2026(self, member):
        if "Senate" not in (member.get("chamber") or ""):
            return "regular"
        if member.get("bioguideId") in self.special:
            return "special"
        if member.get("bioguideId") in self.regular_senators:
            return "regular"
        return None

    def get_member_detail(self, bioguide_id):
        member = self.members.get(bioguide_id)
        return {"member": member} if member else None


def make_ds():
    return FakeDS(summaries=SUMMARIES, bills=BILLS, special={"M001244"},
                  members={bid: {"terms": terms} for bid, terms in TERMS.items()})


def member_raw(bioguide, name, *, district=None, chamber="House of Representatives",
               photo="", party="Democratic", latest_vote=None):
    return {"bioguideId": bioguide, "name": name, "district": district, "chamber": chamber,
            "photo": photo, "terms": [], "partyName": party, "latest_vote": latest_vote}


def ny_overview(districts_expected=10):
    return {
        "state": "NY",
        "state_name": "New York",
        "roster_as_of": "2026-09-05",
        "generated_at": "2026-09-22T00:00:00Z",
        "districts_expected": districts_expected,
        "senators": [
            member_raw("S000148", "Schumer, Charles E.", chamber="Senate",
                       photo="https://www.congress.gov/img/member/s000148_200.jpg",
                       latest_vote=dict(VOTE_4795, rc="senate/119_2_00210", position="Nay")),
            member_raw("G000555", "Gillibrand, Kirsten E.", chamber="Senate"),
        ],
        "house": [
            member_raw("G000599", "Goldman, Daniel S.", district=10,
                       latest_vote=dict(VOTE_4795, position="Not Voting")),
            member_raw("G000602", "Gillen, Laura", district=4,
                       photo="https://www.congress.gov/img/member/677427de0b34857ecc9090ad_200.jpg",
                       latest_vote=VOTE_4795),
            member_raw("X000001", "Example, Pat", district=1,
                       latest_vote=dict(VOTE_4795, bill_id="119-hr-6500")),
        ],
    }


def fields_for(bioguide):
    overview = ny_overview()
    raw = next(m for m in overview["senators"] + overview["house"] if m["bioguideId"] == bioguide)
    return render.overview_member_fields(raw, make_ds())


class _LinkNesting(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.nested = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            if self.depth:
                self.nested = True
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "a":
            self.depth -= 1


def has_nested_links(markup):
    parser = _LinkNesting()
    parser.feed(markup)
    parser.close()
    return parser.nested


def section(markup, opening):
    """The markup from `opening` to the first </section> after it."""
    return markup.split(opening, 1)[1].split("</section>", 1)[0]


# --- chips and render-ready fields ---

@pytest.mark.parametrize("position", [
    "Yea", "Aye", "Nay", "No", "Not Voting", "Present", "Present, Giving Live Pair",
    "Guilty", "Not Guilty", "Jeffries", None,
])
def test_overview_chip_fields_come_from_position_chip(position):
    # One §7.1 table (T1.2 position_chip, mirrored by site.js POSITIONS): the overview never
    # re-derives chip words. A Speaker-candidate name ("Jeffries") is a party cue and reads "Voted".
    raw = member_raw("G000602", "Gillen, Laura", district=4,
                     latest_vote=dict(VOTE_4795, position=position))
    vote = render.overview_member_fields(raw, make_ds())["latest_vote"]
    chip = render.position_chip(position)
    assert (vote["chip"], vote["chip_class"]) == (chip["text"], f"chip--{chip['variant']}")
    assert "Jeffries" not in vote["chip"]


def test_overview_member_fields_for_a_house_member():
    fields = fields_for("G000602")
    assert fields["display_name"] == "Laura Gillen"
    assert fields["initials"] == "LG"
    assert fields["seat_line"] == "District 4 · In Congress since 2025"
    assert fields["seat_seal"] == "Seat up Nov 3"
    assert fields["url"] == "/member?id=G000602"
    assert fields["photo"] == "https://www.congress.gov/img/member/677427de0b34857ecc9090ad_200.jpg"
    assert fields["partyName"] == "Democratic"  # passes through; the router strips it
    vote = fields["latest_vote"]
    assert vote["rc"] == "house/119_2_00295"
    assert vote["bill_code"] == "H.R. 4795"
    assert vote["bill_url"] == "/bill?congress=119&type=hr&number=4795"
    assert vote["headline"] == "Sample one-liner for H.R. 4795"
    assert vote["displayable"] is True
    assert vote["seal"] == ""
    assert (vote["chip"], vote["chip_class"]) == ("Voted yes", "chip--yes")
    assert vote["date_short"] == "Sep 3, 2026"


def test_overview_member_fields_for_a_senator_whose_seat_is_not_up():
    fields = fields_for("S000148")
    assert fields["seat_line"] == (
        "U.S. Senator · In Congress since 1981 — House 1981–1999, Senate since 1999")
    assert fields["seat_seal"] == ""
    assert fields["initials"] == "CS"
    assert (fields["latest_vote"]["chip"], fields["latest_vote"]["chip_class"]) == ("Voted no", "chip--no")


def test_special_election_seat_is_described_as_the_seat():
    raw = member_raw("M001244", "Moody, Ashley", chamber="Senate")
    assert render.overview_member_fields(raw, make_ds())["seat_seal"] == "Special election Nov 3"


@pytest.mark.parametrize("now, shown", [
    (datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc), True),
    (datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc), True),
    (datetime(2026, 11, 4, 8, 0, tzinfo=timezone.utc), False),   # midnight Pacific, Nov 4
])
def test_seat_seals_follow_the_request_clock(now, shown):
    # F066: rows stop saying "Seat up Nov 3" once Election Day is over in California.
    moody = member_raw("M001244", "Moody, Ashley", chamber="Senate")
    assert render.overview_member_fields(moody, make_ds(), now)["seat_seal"] == (
        "Special election Nov 3" if shown else "")
    html = render.render_state_page(ny_overview(), ds=make_ds(), now=now)
    assert ('<span class="seal seal--ballot">Seat up Nov 3</span>' in html) is shown
    assert ("seal--ballot" in html) is shown


def test_withheld_summary_falls_back_to_the_official_title():
    vote = fields_for("X000001")["latest_vote"]
    assert vote["headline"] == "Sample official title for H.R. 6500"
    assert vote["displayable"] is False
    assert vote["seal"] == "No plain-English summary yet"


def test_member_without_a_decisive_vote_has_no_latest_vote():
    assert fields_for("G000555")["latest_vote"] is None


# --- person rows ---

def test_person_row_is_one_link_covering_the_row():
    fields = fields_for("G000602")
    row = render.render_person_row(fields, fields["latest_vote"], state_code="NY")
    assert row.startswith(
        '<a class="person" href="/member?id=G000602" data-bioguide="G000602" '
        'data-state="NY" data-district="4">')
    assert ('<img src="https://www.congress.gov/img/member/677427de0b34857ecc9090ad_200.jpg" '
            'alt="" loading="lazy" width="56" height="56">') in row
    assert '<span class="photo" data-initials="LG">' in row
    assert '<span class="person-name">Laura Gillen</span>' in row
    assert '<span class="person-seat">District 4 · In Congress since 2025</span>' in row
    assert '<span class="seal seal--ballot">Seat up Nov 3</span>' in row
    assert ('Latest final vote · Sep 3, 2026 · Sample one-liner for H.R. 4795 — '
            '<span class="chip chip--yes">Voted yes</span>') in row
    assert '<span class="party"></span>' in row
    assert row.count("<a ") == 1
    assert "aria-label" not in row
    assert not BALLOT_PERSON.search(row)


def test_person_row_with_a_withheld_summary_shows_title_and_pending_seal():
    fields = fields_for("X000001")
    row = render.render_person_row(fields, fields["latest_vote"], state_code="NY")
    assert ('<span class="official">Sample official title for H.R. 6500</span> '
            '<span class="seal seal--pending">No plain-English summary yet</span>') in row
    assert "Sample withheld one-liner" not in row


def test_person_row_without_a_final_vote():
    fields = fields_for("G000555")
    row = render.render_person_row(fields, fields["latest_vote"], state_code="NY")
    assert '<span class="person-signal">No final votes on bills in our record yet</span>' in row
    assert 'class="chip' not in row
    assert "seal--ballot" not in row


def test_split_row_is_a_div_with_two_sibling_links():
    fields = fields_for("G000599")
    row = render.render_person_row(fields, fields["latest_vote"], split=True, state_code="NY")
    assert row.startswith(
        '<div class="person person--split" data-bioguide="G000599" data-state="NY" data-district="10">')
    assert '<a class="person-name" href="/member?id=G000599">Daniel S. Goldman</a>' in row
    assert ('<a class="btn btn--secondary" href="/state?code=NY&amp;district=10#mine">'
            'This is my district →</a>') in row
    assert '<span class="chip chip--nv">Didn&#x27;t vote</span>' in row
    assert row.count("<a ") == 2
    assert not has_nested_links(row)


def test_photo_is_only_ever_a_congress_gov_image():
    raw = member_raw("G000602", "Gillen, Laura", district=4, photo="javascript:alert(1)")
    fields = render.overview_member_fields(raw, make_ds())
    row = render.render_person_row(fields, None, state_code="NY")
    assert "<img" not in row
    assert '<span class="photo" data-initials="LG"></span>' in row


# --- the state page ---

def test_plain_state_page_is_the_whole_delegation():
    html = render.render_state_page(ny_overview(), ds=make_ds())
    assert html.startswith('<div class="delegation"><section class="state-header" data-state="NY" '
                           'data-context-label="New York">')
    assert '<p class="kicker">New York · 5 members · roster as of September 5, 2026</p>' in html
    assert "<h1>New York's representatives</h1>" in html
    assert '<section class="yours"' not in html
    senate = section(html, '<section class="senate"')
    assert '<h2 id="senate-h">U.S. Senate</h2>' in senate
    assert '<p class="kicker">Both represent all of New York</p>' in senate
    # Senators sorted by name: Gillibrand before Schumer.
    assert senate.index('data-bioguide="G000555"') < senate.index('data-bioguide="S000148"')
    house = section(html, '<section class="house"')
    assert '<h2 id="house-h">The House, by district</h2>' in house
    assert '<p class="kicker">By district, 1–10</p>' in house
    assert "<details>" not in house
    positions = [house.index(f'data-district="{d}"') for d in range(1, 11)]
    assert positions == sorted(positions)
    for vacant in (2, 3, 5, 6, 7, 8, 9):
        assert f"District {vacant} — vacant in our data" in house
    assert html.index('<h2 id="senate-h">') < html.index('<h2 id="house-h">')
    assert html.index('<h1>') < html.index('<h2 id="senate-h">')


def test_state_header_action_row_and_status_nodes():
    html = render.render_state_page(ny_overview(), ds=make_ds())
    # T2.3 contract: site.js initPartyToggle() fetches data-party-url once and fills every
    # [data-bioguide] .party span from payload.senators/house.
    assert ('<button class="party-toggle" type="button" '
            'data-party-url="/api/members/NY/overview?show_party=true">Show party labels</button>') in html
    assert ('data-share-url="https://clearvoting.org/state?code=NY" '
            'data-share-title="New York&#x27;s Representatives — Voting Records" '
            'data-share-text="How New York&#x27;s members of Congress vote">Share</button>') in html
    assert '<p class="meta">Party labels are hidden so the record speaks first.</p>' in html
    assert ("<noscript><p class=\"meta\">Party labels and remembering your district need JavaScript"
            "</p></noscript>") in html
    statuses = STATUS_NODES.findall(html)
    assert len(statuses) == 2 and all(text == "" for text in statuses)
    # No district: T3.1's compact ZIP form sits in the header (the same component as home).
    assert '<form class="zip-form zip-form--compact" id="zip-top" method="get" action="/state">' in html
    assert '<label class="zip-label" for="zip-top-field">Where do you live?</label>' in html
    assert html.count('<form class="zip-form') == 2  # header and foot; no second form builder
    assert 'id="remember-district"' not in html


def test_state_page_foot():
    html = render.render_state_page(ny_overview(), ds=make_ds())
    foot = html.split('<div class="state-foot">', 1)[1]
    assert '<form class="zip-form zip-form--compact" id="zip-foot" method="get" action="/state">' in foot
    assert ('<label class="zip-label" for="zip-foot-field">Don&#x27;t know your district? '
            'Enter your ZIP</label>') in foot
    assert ('Roster from Congress.gov, as of September 5, 2026 · Wrong person? '
            '<button type="button" class="btn btn--secondary" data-feedback-open>Report an error</button>') in foot
    assert ('href="https://www.congress.gov/members?q=%7B%22congress%22%3A119%2C%22member-state'
            '%22%3A%22New%20York%22%7D"') in foot
    assert render.render_notify_disclosure() in foot


def test_state_page_never_shows_party_or_a_ballot_line_about_a_person():
    html = render.render_state_page(ny_overview(), 4, ds=make_ds())
    assert not re.search(r"Democratic|Republican|Independent|\[[RDI]-", html)
    assert not BALLOT_PERSON.search(html)
    assert html.count('<span class="party"></span>') == html.count("data-bioguide=")


def test_district_page_leads_with_your_representatives():
    html = render.render_state_page(ny_overview(), 4, ds=make_ds())
    assert "<h1>Your representatives</h1>" in html
    # The h1 names no place, so the feedback context comes from the header attribute.
    assert '<section class="state-header" data-state="NY" data-context-label="New York, District 4">' in html
    assert '<p class="district-line">New York, District 4 · <a href="/#find">Change ZIP</a></p>' in html
    assert ('<button type="button" class="btn btn--secondary" id="remember-district" data-state="NY" '
            'data-state-name="New York" data-district="4" hidden>Remember District 4 as mine</button>') in html
    yours = section(html, '<section class="yours"')
    # The h1 already says "Your representatives"; the block names who is in it, so a
    # screen reader does not hear the same heading twice (QA 2026-09-26).
    assert '<h2 id="yours-h">Your senators and House member</h2>' in yours
    assert html.count(">Your representatives<") == 1
    assert '<ul class="reps reps--yours">' in yours
    for bioguide in ("G000555", "S000148", "G000602"):
        assert f'data-bioguide="{bioguide}"' in yours
    # U.S. Senate module omitted: each senator appears once on the page.
    assert '<section class="senate"' not in html
    assert html.count('data-bioguide="S000148"') == 1
    house = section(html, '<section class="house"')
    assert "<details><summary>All 10 New York House districts</summary>" in house
    assert 'id="zip-top"' not in html


def test_vacant_district_row_invites_a_correction():
    html = render.render_state_page(ny_overview(), 3, ds=make_ds())
    yours = section(html, '<section class="yours"')
    # Spec §4.2/§5.3: "District 3 — vacant in our data · Tell us if this is wrong", as one
    # wrapping line (the inline wrapper keeps the separator out of the row's grid).
    assert ('<span class="person-vacancy"><span class="person-name">District 3 — vacant in our data</span> · '
            '<button type="button" class="btn btn--secondary" data-feedback-open>Tell us if this is wrong'
            '</button></span>') in yours


def test_out_of_range_district_is_named_above_the_roster():
    for district in (40, 0):
        html = render.render_state_page(ny_overview(), district, ds=make_ds())
        assert f"<p class=\"note\">We don't have a District {district} in New York</p>" in html
        assert "<h1>New York's representatives</h1>" in html
        assert html.index('class="note"') < html.index('<section class="house"')


def test_split_zip_offers_each_district_with_land_area_wording():
    split = {"zip": "11201", "kind": "split", "covered_share": 1.0, "matches": [
        {"state": "NY", "state_name": "New York", "district": 10, "share": 0.7216,
         "member_ids": ["G000599"], "senator_ids": ["G000555", "S000148"]},
        {"state": "NY", "state_name": "New York", "district": 7, "share": 0.2784,
         "member_ids": [], "senator_ids": ["G000555", "S000148"]},
    ]}
    html = render.render_state_page(ny_overview(), None, split, ds=make_ds(), zip_value="11201")
    assert "<h1>Your representatives</h1>" in html
    yours = section(html, '<section class="yours"')
    assert '<h2 id="yours-h">Your senators and House members</h2>' in yours
    assert ("<p>ZIP 11201 spans two House districts — about 72 % of the ZIP's land area (not its residents) "
            "is in District 10 and 28 % in District 7. Both are shown; your street address decides "
            "which is yours.</p>") in yours
    assert ('<a class="source-link" href="https://www.house.gov/representatives/find-your-representative" '
            'rel="noopener">Not sure? Look up your district by street address on house.gov →</a>') in yours
    assert '<div class="person person--split" data-bioguide="G000599" data-state="NY" data-district="10">' in yours
    assert "District 7 — vacant in our data" in yours
    assert 'href="/state?code=NY&amp;district=7#mine">This is my district →</a>' in yours
    assert yours.index("District 10") < yours.index("District 7 — vacant")
    assert yours.index('data-bioguide="S000148"') < yours.index("spans two House districts")
    assert '<section class="senate"' not in html
    assert 'value="11201"' in html
    assert 'id="remember-district"' not in html
    assert not has_nested_links(html)


def test_three_way_split_lists_every_share():
    split = {"zip": "10000", "kind": "split", "covered_share": 1.0, "matches": [
        {"state": "NY", "district": 1, "share": 0.5}, {"state": "NY", "district": 2, "share": 0.3},
        {"state": "NY", "district": 4, "share": 0.2}]}
    html = render.render_state_page(ny_overview(), None, split, ds=make_ds(), zip_value="10000")
    assert ("ZIP 10000 spans three House districts — about 50 % of the ZIP's land area (not its residents) "
            "is in District 1, 30 % in District 2 and 20 % in District 4. All three are shown;") in html


def test_partial_zip_notes_the_share_outside_our_states():
    overview = {"state": "TX", "state_name": "Texas", "roster_as_of": "2026-09-05",
                "districts_expected": 13, "senators": [], "house": []}
    partial = {"zip": "73949", "kind": "partial", "covered_share": 0.1367,
               "matches": [{"state": "TX", "state_name": "Texas", "district": 13, "share": 0.1367,
                            "member_ids": [], "senator_ids": []}]}
    html = render.render_state_page(overview, None, partial, ds=make_ds(), zip_value="73949")
    assert ("<p>About 86 % of ZIP 73949's land area is outside California, Florida, New York and Texas; "
            "if you live in that part, we don't cover your state yet.</p>") in html
    assert "spans" not in section(html, '<section class="yours"')
    assert 'href="/state?code=TX&amp;district=13#mine">This is my district →</a>' in html
    assert "<h1>Your representatives</h1>" in html
    assert '<h2 id="yours-h">Your senators and House member</h2>' in html


def test_malformed_zip_error_keeps_the_value_and_describes_the_field():
    html = render.render_state_page(ny_overview(), None, None, "A ZIP code is five digits.",
                                    ds=make_ds(), zip_value="abc")
    assert 'value="abc"' in html
    assert 'aria-describedby="zip-top-field-error" aria-invalid="true"' in html
    assert '<p class="field-error" id="zip-top-field-error">A ZIP code is five digits.</p>' in html


# --- finder and not-found pages ---

def test_zip_finder_page():
    html = render.render_zip_finder_page(COUNTS)
    assert "<h1>Find your representatives</h1>" in html
    # The finder is the page's main control, so it is the full (non-compact) T3.1 form.
    assert html.count('<form class="zip-form" id="zip-top" method="get" action="/state">') == 1
    assert '<label class="zip-label" for="zip-top-field">Where do you live?</label>' in html
    for attr in ('name="zip"', 'inputmode="numeric"', 'autocomplete="postal-code"', 'maxlength="10"',
                 'pattern="\\s*[0-9]{5}([\\-\\s]?[0-9]{4})?\\s*"', "required"):
        assert attr in html
    assert '<button class="btn" type="submit">Find my representatives</button>' in html
    assert render.render_state_links(COUNTS) in html
    assert "field-error" not in html


def test_zip_finder_page_with_an_error():
    html = render.render_zip_finder_page(COUNTS, value="abc", error="A ZIP code is five digits.")
    assert 'value="abc"' in html
    assert '<p class="field-error" id="zip-top-field-error">A ZIP code is five digits.</p>' in html


def test_zip_not_found_copy():
    html = render.render_zip_not_found("44101", COUNTS)
    assert "<h1>Find your representatives</h1>" in html
    assert ("We couldn't match ZIP 44101 to a congressional district in California, Florida, New York or "
            "Texas — the four states ClearVoting covers. If you live in one of them, your ZIP may be a "
            "PO-box or business ZIP: choose your state below, or "
            '<a href="https://www.house.gov/representatives/find-your-representative" rel="noopener">'
            "look up your district by street address on house.gov →</a>. Somewhere else? Tell us your "
            "state and we'll email you when we add it.") in html
    assert 'value="44101"' in html
    assert render.render_state_links(COUNTS) in html
    assert render.render_notify_disclosure() in html
    assert html.index(render.render_state_links(COUNTS)) < html.index(render.render_notify_disclosure())
