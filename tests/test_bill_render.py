"""Bill page renderers (plan T7.1, T7.2, T7.4): pure functions over DataService.get_bill_page()."""
import io
import json
import os
import re
import shutil
import subprocess
import unicodedata
from html import escape
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app import render
from app.dependencies import get_data_service
from app.main import app
from app.services.data_service import DataService, first_paragraph_text

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
ROOT = Path(__file__).resolve().parent.parent

PAGE_KEYS = {
    "bill_id", "congress", "bill_type", "number", "title", "has_summary", "one_liner",
    "provisions", "official_summary", "official_first_paragraph", "status", "head", "roll_calls", "sponsor",
    "sponsor_covered", "cosponsors_count", "policy_area", "introduced_date", "laws",
    "legislation_url",
}
RC_KEYS = {
    "key", "chamber", "congress", "session", "vote_number", "date", "question", "plain",
    "class", "result", "counts", "seal", "outcome", "state_tallies", "rendered",
}
ROW_KEYS = {"first_name", "last_name", "state", "vote", "bioguide_id", "covered_id", "district"}


def _rc(**overrides):
    rc = {
        "key": "house/119_2_00295", "chamber": "house", "congress": 119, "session": 2,
        "vote_number": 295, "date": "2026-09-03", "question": "On Passage",
        "plain": "Final vote to pass", "class": "D", "result": "Passed",
        "counts": {"yeas": 237, "nays": 169, "present": 0, "absent": 27},
        "seal": "Passed the House 237–169",
        "outcome": "The House passed it, 237 to 169, on September 3, 2026.",
        "state_tallies": {"CA": [13, 35, 4], "FL": [22, 2, 3], "NY": [13, 11, 2], "TX": [25, 11, 1]},
        "rendered": False,
        "members": [],
    }
    rc.update(overrides)
    return rc


def _page(**overrides):
    head = _rc()
    page = {
        "bill_id": "119-hr-4795", "congress": 119, "bill_type": "hr", "number": 4795,
        "title": "Test Freedom Act of 2026",
        "has_summary": True,
        "one_liner": "Test one-liner: bars a practice",
        "provisions": ["Bars the first test practice", "Requires a second test report"],
        "official_summary": "<p>This bill prohibits a test practice.</p><p>Second paragraph.</p>",
        "official_first_paragraph": "This bill prohibits a test practice.",
        "status": {"text": "Passed the House 237–169", "variant": "moving"},
        "head": head,
        "roll_calls": [head],
        "sponsor": {"bioguideId": "F000450", "firstName": "Virginia", "lastName": "Foxx",
                    "state": "NC", "fullName": "Rep. Foxx, Virginia [R-NC-5]"},
        "sponsor_covered": False,
        "cosponsors_count": 1,
        "policy_area": "Education",
        "introduced_date": "2025-07-29",
        "laws": [],
        "legislation_url": "https://www.congress.gov/bill/119th-congress/house-bill/4795",
    }
    page.update(overrides)
    return page


def _unsummarized(**overrides):
    return _page(has_summary=False, one_liner=None, provisions=[], **overrides)


# --- Contract with T1.8 ---

def test_get_bill_page_contract_matches_the_renderers():
    page = DataService(data_dir=FIXTURES).get_bill_page(119, "hjres", 20)
    assert page is not None
    assert PAGE_KEYS <= set(page)
    assert page["roll_calls"], "fixture 119-hjres-20 has a House and a Senate roll call"
    for rc in page["roll_calls"]:
        assert RC_KEYS <= set(rc)
    rendered = [rc for rc in page["roll_calls"] if rc["rendered"]]
    assert 1 <= len(rendered) <= 2
    for rc in rendered:
        for row in rc["members"]:
            assert ROW_KEYS <= set(row)
            assert "party" not in row


def test_official_first_paragraph_skips_the_bold_title_paragraph():
    # The real CRS shape (119-hr-4795, 119-hr-4, 119-s-5): a bold short-title paragraph first.
    html = ("<p><strong>Protect Economic and Academic Freedom Act of 2026</strong></p>"
            "<p>This bill prohibits institutions of higher education (IHEs) that participate in "
            "federal student aid programs from engaging in boycotts against Israel.</p><p>Second.</p>")
    assert first_paragraph_text(html).startswith("This bill prohibits institutions")
    # A short heading-like paragraph without a period is skipped too; a real sentence is kept.
    assert first_paragraph_text("<p>Laken Riley Act</p><p>This bill requires detention.</p>") == \
        "This bill requires detention."
    assert first_paragraph_text("<p>This bill bans x.</p><p>Two.</p>") == "This bill bans x."
    # Only title paragraphs: fall back to the first one rather than print nothing.
    assert first_paragraph_text("<p><strong>Only A Title Act</strong></p>") == "Only A Title Act"


# --- Story head (§4.4 m1) ---

def test_head_with_displayable_summary_uses_one_liner_h1():
    html = render.render_bill_head(_page())
    assert html.startswith('<header class="bill-header">')
    assert ('<p class="kicker">H.R. 4795 · 119th Congress '
            '<span class="seal seal--moving">Passed the House 237–169</span></p>') in html
    assert "<h1>Test one-liner: bars a practice</h1>" in html
    assert '<p class="deck">Officially: Test Freedom Act of 2026</p>' in html
    assert "Show full title" not in html
    assert '<p class="outcome">The House passed it, 237 to 169, on September 3, 2026.</p>' in html
    assert 'aria-label="Passed the House: 237 voted yes, 169 voted no, 27 did not vote"' in html
    assert "No plain-English summary yet" not in html


def test_deck_is_capped_at_140_characters_with_full_title_disclosure():
    title = " ".join(["Providing for consideration of the bill"] * 8)
    html = render.render_bill_head(_page(title=title))
    deck = re.search(r'<p class="deck">Officially: (.*?)</p>', html).group(1)
    assert deck.endswith("…")
    assert len(deck) <= 141
    assert f"<summary>Show full title</summary><p>{title}</p>" in html


def test_withheld_or_missing_summary_uses_official_title_h1_and_pending_seal():
    html = render.render_bill_head(_unsummarized())
    assert '<h1 class="official">Test Freedom Act of 2026</h1>' in html
    assert "Officially:" not in html
    assert '<span class="seal seal--pending">No plain-English summary yet</span>' in html


def test_summary_with_provisions_but_no_one_liner_is_treated_as_unsummarized_everywhere():
    # has_summary is T1.5's truthy summary dict, not a bool; one predicate decides all modules.
    page = _page(has_summary={"one_liner": "", "provisions": ["Bars a test practice"]}, one_liner=None)
    assert render.bill_displayable(page) is False
    head = render.render_bill_head(page)
    assert '<span class="seal seal--pending">No plain-English summary yet</span>' in head
    assert '<h1 class="official">Test Freedom Act of 2026</h1>' in head
    what = render.render_what_it_does(page, "2026-07-07")
    assert "Summarized by AI" not in what and "<li>" not in what
    assert "We haven't written a plain-English summary for this bill yet" in what
    assert render.render_official_summary_slot(page) == ""
    assert render.bill_displayable(_page()) is True


@pytest.mark.parametrize("length", [1063, 1955])
def test_long_official_title_is_cut_at_200_on_a_word_boundary(length):
    title = (" ".join(["Providing for consideration of the bill"] * 60))[:length].strip()
    html = render.render_bill_head(_unsummarized(title=title))
    h1 = re.search(r'<h1 class="official">(.*?)</h1>', html).group(1)
    assert h1.endswith("…")
    assert len(h1) <= 201
    assert not h1[:-1].endswith(" ")
    assert title.startswith(h1[:-1])
    assert f"<summary>Show full title</summary><p>{title}</p>" in html


def test_title_with_markup_characters_is_escaped():
    title = 'The <b>Bold</b> & "Quoted" Act\'s Title'
    html = render.render_bill_head(_unsummarized(title=title))
    assert "<b>Bold</b>" not in html
    assert "The &lt;b&gt;Bold&lt;/b&gt; &amp; &quot;Quoted&quot; Act&#x27;s Title" in html


def test_fixture_bill_with_markup_title_renders_escaped():
    bills = json.loads((FIXTURES / "bills.json").read_text())["bills"]
    bill = next(b for b in bills if "<b>" in b["title"])
    page = DataService(data_dir=FIXTURES).get_bill_page(
        bill["congress"], bill["type"].lower(), int(bill["number"]))
    html = render.render_bill_head(page)
    h1 = html.split("<h1", 1)[1].split("</h1>", 1)[0]
    assert "<b>" not in h1
    assert "&lt;b&gt;" in html


def test_no_decisive_vote_describes_the_latest_recorded_vote():
    cloture = _rc(
        key="senate/119_2_00210", chamber="senate", vote_number=210, date="2026-08-08",
        plain="Vote to end debate (needed 60)", **{"class": "P"},
        result="Cloture on the Motion to Proceed Rejected",
        counts={"yeas": 52, "nays": 46, "present": 0, "absent": 2},
        seal="Debate not ended 52–46 (60 needed)",
        outcome=("On August 8, 2026, the Senate voted 52 to 46 to end debate; "
                 "60 votes were needed, so debate did not end."),
    )
    html = render.render_bill_head(_page(
        head=cloture, roll_calls=[cloture],
        status={"text": "No final vote yet", "variant": "moving"}))
    assert ("The latest recorded vote: on August 8, 2026, the Senate voted 52 to 46 to end "
            "debate; 60 votes were needed, so debate did not end.") in html
    assert '<span class="seal seal--moving">No final vote yet</span>' in html


def test_head_without_roll_call_has_no_outcome_or_tally():
    html = render.render_bill_head(_page(
        head=None, roll_calls=[], status={"text": "No final vote yet", "variant": "moving"}))
    assert 'class="outcome"' not in html
    assert 'role="img"' not in html


# --- What it does (§4.4 m4) and official summary (§4.4 m5) ---

def test_what_it_does_with_summary_lists_provisions_and_dated_ai_line():
    html = render.render_what_it_does(_page(), "2026-07-07")
    assert '<h2 id="what-h">What it does</h2>' in html
    assert ('<ul class="provisions"><li>Bars the first test practice</li>'
            "<li>Requires a second test report</li></ul>") in html
    assert ("Summarized by AI from the bill's title, official summary and text excerpt"
            " · summaries last updated July 7, 2026.") in html
    assert '<a href="/methodology#ai">How we keep it neutral →</a>' in html
    assert '<a href="/methodology#report">Something wrong here? Tell us</a>' in html
    assert "haven't written" not in html
    assert "Generating" not in html


def test_ai_line_without_a_summary_set_date_drops_only_the_date():
    html = render.render_what_it_does(_page(), None)
    assert "summaries last updated" not in html
    assert "Summarized by AI from the bill's title, official summary and text excerpt." in html


def test_unsummarized_bill_shows_note_plain_first_paragraph_and_empty_details():
    page = _unsummarized(
        official_summary="<p>This bill <em>prohibits</em> things &amp; more.</p><p>Second paragraph.</p>",
        official_first_paragraph="This bill prohibits things & more.")
    html = render.render_what_it_does(page, "2026-07-07")
    assert ('<p class="note">We haven\'t written a plain-English summary for this bill yet; '
            "the official summary is below.</p>") in html
    assert '<p class="official-para">This bill prohibits things &amp; more.</p>' in html
    assert "Second paragraph" not in html
    assert "<summary>Show the full official summary</summary>" in html
    assert '<div class="official-summary" id="official-summary-body"></div>' in html
    assert ("<noscript><p><a href=\"https://www.congress.gov/bill/119th-congress/house-bill/4795\" "
            "rel=\"noopener\">Read the full summary on Congress.gov →</a></p></noscript>") in html
    assert "Summarized by AI" not in html
    assert "<li>" not in html


def test_first_paragraph_is_read_from_the_page_and_escaped():
    # T1.8 already stripped markup; the renderer never re-parses official_summary and escapes
    # whatever text it is given.
    page = _unsummarized(official_summary="<p>Ignored here.</p>",
                         official_first_paragraph='<script>alert(1)</script>Safe "text"')
    html = render.render_what_it_does(page, None)
    assert "<script" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;Safe &quot;text&quot;" in html
    assert "Ignored here" not in html


def test_no_official_summary_either_links_to_the_bill_text():
    html = render.render_what_it_does(
        _unsummarized(official_summary=None, official_first_paragraph=None), None)
    assert "We haven't written a plain-English summary for this bill yet" in html
    assert ('<a class="source-link" href="https://www.congress.gov/bill/119th-congress/house-bill/4795/text" '
            'rel="noopener">Congress.gov has the bill text →</a>') in html
    assert "Show the full official summary" not in html


def test_official_summary_slot_only_with_displayable_summary_and_official_text():
    assert render.render_official_summary_slot(_unsummarized()) == ""
    assert render.render_official_summary_slot(_page(official_summary=None)) == ""
    html = render.render_official_summary_slot(_page())
    # Its own wrapper class: T2.1's .official is a site-wide type role (fallback headlines,
    # roster signal lines, the unsummarized H1) and must never pick up a section rule.
    assert html.startswith('<section class="section official-summary-section" aria-labelledby="official-h">')
    assert 'class="official"' not in html and 'class="section official"' not in html
    assert '<h2 id="official-h">Official summary</h2>' in html
    assert "<summary>Show the official summary</summary>" in html
    assert '<div class="official-summary" id="official-summary-body"></div>' in html
    assert "This bill prohibits" not in html


# --- Fact box (§4.4 m6) ---

def test_fact_box_uncovered_sponsor_is_plain_text_with_coverage_note():
    html = render.render_fact_box(_page())
    assert html.startswith('<section class="section fact-box" aria-labelledby="facts-h">')
    assert '<h2 id="facts-h" class="kicker">About this bill</h2>' in html
    assert ("<dt>Sponsor</dt><dd>Rep. Virginia Foxx (NC) — not in ClearVoting's coverage yet</dd>") in html
    assert "[R-" not in html
    assert "/member?id=F000450" not in html
    assert "<dt>Cosponsors</dt><dd>1</dd>" in html
    assert "<dt>Topic</dt><dd>Education</dd>" in html
    assert "<dt>Introduced</dt><dd>Jul 29, 2025</dd>" in html
    assert "<dt>Latest floor vote</dt><dd>Passed the House · Sep 3, 2026</dd>" in html
    assert "Became law" not in html
    # §8 item 10: the "Link copied" role=status node is present and empty in the server HTML,
    # after the actions row (a <p> cannot sit inside the actions container), as on T4.1/T6.1.
    assert ('<button class="btn btn--secondary share-btn" type="button" data-share>Share</button></div>'
            '<p class="share-status" role="status"></p>') in html
    assert '<div class="actions">' in html
    assert 'href="https://www.congress.gov/bill/119th-congress/house-bill/4795"' in html


def test_fact_box_covered_sponsor_is_linked_and_law_row_appears():
    sponsor = {"bioguideId": "E000001", "firstName": "Ada", "lastName": "Example",
               "state": "NY", "fullName": "Sen. Example, Ada [I-NY]"}
    html = render.render_fact_box(_page(
        sponsor=sponsor, sponsor_covered=True, laws=[{"type": "Public Law", "number": "119-6"}]))
    assert '<dt>Sponsor</dt><dd><a href="/member?id=E000001">Sen. Ada Example (NY)</a></dd>' in html
    assert "<dt>Became law</dt><dd>Public Law 119-6</dd>" in html


def test_fact_box_without_roll_calls_says_none_in_our_data():
    html = render.render_fact_box(_page(head=None, roll_calls=[]))
    assert "<dt>Latest floor vote</dt><dd>none in our data</dd>" in html


def test_fact_box_drops_links_that_are_not_congress_gov():
    html = render.render_fact_box(_page(legislation_url="javascript:alert(1)"))
    assert "javascript:" not in html
    assert "Congress.gov →" not in html


# --- Roll-call blocks (§4.4 m3, §6.4) and the reps slot (§4.4 m2) ---

def _members_119():
    """Fictional rows: two covered NY members, one uncovered NY row, one covered FL row."""
    return [
        {"first_name": "Bea", "last_name": "Beta", "state": "NY", "vote": "Yea",
         "bioguide_id": "B000001", "covered_id": "B000001", "district": 4},
        {"first_name": "Ann", "last_name": "Alpha", "state": "NY", "vote": "Nay",
         "bioguide_id": "A000001", "covered_id": "A000001", "district": 1},
        {"first_name": "Former", "last_name": "Member", "state": "NY", "vote": "Not Voting",
         "bioguide_id": "X000001", "covered_id": None, "district": None},
        {"first_name": "Cal", "last_name": "Gamma", "state": "FL", "vote": "Present",
         "bioguide_id": "C000001", "covered_id": "C000001", "district": 19},
    ]


def _group(html: str, state: str) -> str:
    return html.split(f'<details class="state-group" data-state="{state}">', 1)[1].split("</details>", 1)[0]


def test_your_reps_slot_is_the_shared_get_zip_form_with_empty_status():
    html = render.render_your_reps_slot(_page())
    assert '<section class="section your-reps" id="your-reps" aria-labelledby="your-reps-h">' in html
    assert '<h2 id="your-reps-h" tabindex="-1">How did your representatives vote?</h2>' in html
    # The same form every page uses (T3.1 render_zip_form): .zip-label + .zip-row, one pattern.
    form = render.render_zip_form(form_id="reps-zip-form",
                                  label="Enter your ZIP to see how your representatives voted")
    assert f'<div class="your-reps-body" id="your-reps-body">{form}</div>' in html
    assert '<form class="zip-form" id="reps-zip-form" method="get" action="/state">' in html
    assert ('<label class="zip-label" for="reps-zip-form-field">'
            'Enter your ZIP to see how your representatives voted</label>') in html
    assert '<p class="status" id="reps-zip-status" role="status"></p>' in html


def test_your_reps_slot_carries_no_page_data():
    # Nothing from the bill is interpolated, so it is not in the escaping registry; pin that
    # instead: two very different pages give the same slot.
    other = _page(bill_id="117-hres-8", title='<b>"x"</b>', one_liner="&amp;", congress=117)
    assert render.render_your_reps_slot(_page()) == render.render_your_reps_slot(other)


def test_your_reps_slot_is_omitted_without_a_roll_call():
    assert render.render_your_reps_slot(_page(head=None, roll_calls=[])) == ""


def test_vote_by_state_caption_source_toggle_and_four_closed_groups():
    head = _rc(rendered=True, members=_members_119())
    html = render.render_vote_by_state(_page(head=head, roll_calls=[head]))
    assert '<h2 id="by-state-h">The vote, by state</h2>' in html
    assert html.count('<button class="party-toggle" type="button">Show party labels</button>') == 1
    assert '<p class="party-status" role="status"></p>' in html
    assert ('<h3 id="rc-house-119-2-295">House roll call 295 · September 3, 2026 · '
            "Final vote to pass · Passed 237–169</h3>") in html
    assert '<a href="https://clerk.house.gov/Votes/2026295" rel="noopener">Roll call source →</a>' in html
    summaries = re.findall(r'<details class="state-group" data-state="(\w\w)"><summary>([^<]*)</summary>', html)
    assert summaries == [
        ("CA", "California: 13 yes · 35 no · 4 didn't vote"),
        ("FL", "Florida: 22 yes · 2 no · 3 didn't vote"),
        ("NY", "New York: 13 yes · 11 no · 2 didn't vote"),
        ("TX", "Texas: 25 yes · 11 no · 1 didn't vote"),
    ]
    assert "<caption>New York — House roll call 295</caption>" in html
    assert html.count('<thead><tr><th scope="col">Member</th><th scope="col">Vote</th></tr></thead>') == 4


def test_119th_house_rows_are_district_ordered_and_link_only_covered_members():
    head = _rc(rendered=True, members=_members_119())
    ny = _group(render.render_vote_by_state(_page(head=head, roll_calls=[head])), "NY")
    assert ny.index("Ann Alpha") < ny.index("Bea Beta") < ny.index("Former Member")
    assert ('<tr data-key="A000001" data-bioguide="A000001" data-position="Nay"><th scope="row">'
            '<a href="/member?id=A000001">Ann Alpha</a><span class="rc-seat">District 1</span>'
            '<span class="party"></span></th><td><span class="chip chip--no" data-short>No</span></td></tr>') in ny
    assert '<tr data-key="X000001" data-position="Not Voting"><th scope="row">Former Member' in ny
    assert "Didn&#x27;t vote" in ny
    assert "chip--present" in _group(render.render_vote_by_state(_page(head=head, roll_calls=[head])), "FL")


def test_row_chips_come_from_the_one_positions_table():
    assert not hasattr(render, "RC_SHORT_CHIP")
    for vote in ("Yea", "Nay", "Not Voting", "Present", "Guilty", "Some Candidate"):
        rc = _rc(rendered=True, members=[{"first_name": "Ann", "last_name": "Alpha", "state": "NY",
                                          "vote": vote, "bioguide_id": "A000001",
                                          "covered_id": None, "district": None}])
        chip = render.position_chip(vote)
        ny = _group(render.render_vote_by_state(_page(head=rc, roll_calls=[rc])), "NY")
        assert f'<span class="chip chip--{chip["variant"]}" data-short>{escape(chip["short"])}</span>' in ny


def test_earlier_congress_rows_sort_by_last_name_and_show_state_only():
    members = [
        {"first_name": "Zed", "last_name": "Zulu", "state": "NY", "vote": "Yea",
         "bioguide_id": "Z000001", "covered_id": None, "district": None},
        {"first_name": "Bea", "last_name": "Beta", "state": "NY", "vote": "Nay",
         "bioguide_id": "B000001", "covered_id": "B000001", "district": 4},
    ]
    rc = _rc(key="house/117_1_00006", congress=117, session=1, vote_number=6, date="2021-01-04",
             rendered=True, members=members, state_tallies={"NY": [1, 1, 0]})
    ny = _group(render.render_vote_by_state(_page(congress=117, head=rc, roll_calls=[rc])), "NY")
    assert ny.index("Bea Beta") < ny.index("Zed Zulu")
    assert "District" not in ny
    assert ny.count('<span class="rc-seat">NY</span>') == 2


def _rc_names(group: str) -> list[str]:
    return re.findall(r'<th scope="row">(?:<a [^>]+>)?([^<]+)', group)


def test_accented_last_names_sort_where_a_reader_looks_for_them():
    # F065: code-point order put "Cárdenas" after "Costa" and "Sánchez" after "Swalwell" in
    # H.R. 1319's California table. Accents and case are ignored, last name then first, like
    # vote.js rcSortMembers (localeCompare) for the groups bill.js builds.
    names = [("Mark", "Takano"), ("Linda", "Sánchez"), ("Eric", "Swalwell"), ("Jim", "Costa"),
             ("Tony", "Cárdenas"), ("Mark", "DeSaulnier"), ("Ken", "Calvert"), ("Nanette", "Barragán"),
             ("Ángela", "Zeta"), ("Bob", "zeta"), ("Ami", "Bera")]
    members = [{"first_name": first, "last_name": last, "state": "CA", "vote": "Yea",
                "bioguide_id": f"X{i:06d}", "covered_id": None, "district": None}
               for i, (first, last) in enumerate(names)]
    rc = _rc(key="house/117_1_00080", congress=117, session=1, vote_number=80, date="2021-03-11",
             rendered=True, members=members, state_tallies={"CA": [11, 0, 0]})
    ca = _group(render.render_vote_by_state(_page(congress=117, head=rc, roll_calls=[rc])), "CA")
    assert _rc_names(ca) == [escape(n) for n in (
        "Nanette Barragán", "Ami Bera", "Ken Calvert", "Tony Cárdenas", "Jim Costa", "Mark DeSaulnier",
        "Linda Sánchez", "Eric Swalwell", "Mark Takano", "Ángela Zeta", "Bob zeta")]


def test_119th_house_rows_in_one_district_fall_back_to_the_folded_name():
    members = [{"first_name": first, "last_name": last, "state": "CA", "vote": "Yea",
                "bioguide_id": bid, "covered_id": None, "district": district}
               for first, last, bid, district in (("Ed", "Swift", "S000001", 5), ("Lia", "Sánchez", "S000002", 5),
                                                  ("Al", "Young", "Y000001", 2))]
    rc = _rc(rendered=True, members=members, state_tallies={"CA": [3, 0, 0]})
    ca = _group(render.render_vote_by_state(_page(head=rc, roll_calls=[rc])), "CA")
    assert _rc_names(ca) == ["Al Young", "Lia Sánchez", "Ed Swift"]


def _fold(text):
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def test_fixture_117th_house_roll_call_rows_are_last_name_ordered():
    page = DataService(data_dir=FIXTURES).get_bill_page(117, "hres", 8)
    assert page is not None
    rendered = next(rc for rc in page["roll_calls"] if rc["rendered"])
    ny_members = [m for m in rendered["members"] if m["state"] == "NY"]
    expected = [escape(f'{m["first_name"]} {m["last_name"]}'.strip()) for m in sorted(
        ny_members, key=lambda m: (_fold(m["last_name"]), _fold(m["first_name"])))]
    ny = _group(render.render_vote_by_state(page), "NY")
    names = re.findall(r'<th scope="row">(?:<a [^>]+>)?([^<]+)', ny)
    assert names == expected
    assert "District" not in ny


def test_senate_block_uses_the_senate_source_page_and_state_seat():
    members = [{"first_name": "Ada", "last_name": "Example", "state": "NY", "vote": "Yea",
                "bioguide_id": None, "covered_id": "E000001", "district": None}]
    rc = _rc(key="senate/119_1_00372", chamber="senate", session=1, vote_number=372,
             seal="Passed the Senate 51–49", rendered=True, members=members,
             state_tallies={"NY": [1, 0, 0]})
    html = render.render_vote_by_state(_page(head=rc, roll_calls=[rc]))
    assert "https://www.senate.gov/legislative/LIS/roll_call_votes/vote1191/vote_119_1_00372.htm" in html
    assert "Senate roll call 372 · September 3, 2026 · Final vote to pass · Passed 51–49" in html
    assert '<tr data-key="NY-Example" data-bioguide="E000001" data-position="Yea">' in html
    assert '<span class="rc-seat">NY</span>' in html


def _verdict_rc(**overrides):
    """A synthetic impeachment verdict shaped like senate/117_1_00059 (H.Res. 24)."""
    members = [{"first_name": first, "last_name": last, "state": state, "vote": vote,
                "bioguide_id": None, "covered_id": None, "district": None}
               for first, last, state, vote in (("Ann", "Alpha", "NY", "Guilty"), ("Bo", "Beta", "NY", "Not Guilty"),
                                                ("Cy", "Gamma", "CA", "Guilty"), ("Di", "Delta", "CA", "Not Voting"))]
    return _rc(**{"key": "senate/117_1_00059", "chamber": "senate", "congress": 117, "session": 1,
                  "vote_number": 59, "date": "2021-02-13", "question": "Guilty or Not Guilty",
                  "plain": "Verdict on an article of impeachment (needed two-thirds)", "class": "D",
                  "result": "Not Guilty", "counts": {"yeas": 57, "nays": 43, "present": 0, "absent": 0},
                  "seal": "Not guilty 57–43 (two-thirds needed)", "members": members,
                  "state_tallies": {"CA": [1, 0, 1], "NY": [1, 1, 0]}, **overrides})


def test_verdict_state_groups_count_guilty_and_not_guilty():
    # F064: the rows read Guilty / Not Guilty, so the group summary names the same positions.
    rc = _verdict_rc(rendered=True)
    html = render.render_vote_by_state(_page(congress=117, bill_type="hres", number=24, head=rc, roll_calls=[rc]))
    summaries = re.findall(r'<details class="state-group" data-state="(\w\w)"><summary>([^<]*)</summary>', html)
    assert summaries == [("CA", "California: 1 guilty · 0 not guilty · 1 didn't vote"),
                         ("NY", "New York: 1 guilty · 1 not guilty · 0 didn't vote")]
    assert " yes · " not in html.split('<details class="rc-all"')[0].split("</h3>", 1)[1]
    assert '<span class="chip chip--other" data-short>Guilty</span>' in _group(html, "NY")


def test_collapsed_verdict_tally_lines_count_guilty_and_not_guilty():
    # bill.js reuses each <li> as the summary of the group it builds, so this one line covers both.
    head = _rc(rendered=True, members=_members_119())
    rc = _verdict_rc(rendered=False, members=[])
    html = render.render_vote_by_state(_page(head=head, roll_calls=[head, rc]))
    more = html.split('<details class="rc-more"', 1)[1].split("</details>", 1)[0]
    assert '<li data-state="CA">California: 1 guilty · 0 not guilty · 1 didn\'t vote</li>' in more
    assert '<li data-state="NY">New York: 1 guilty · 1 not guilty · 0 didn\'t vote</li>' in more
    # Any other roll call keeps yes / no.
    assert '<li data-state="NY">New York: 13 yes · 11 no · 2 didn\'t vote</li>' in render.render_vote_by_state(
        _page(head=head, roll_calls=[head, _rc(key="house/119_2_00100", vote_number=100)]))


def test_many_roll_calls_render_two_blocks_and_collapse_the_rest_newest_first():
    head = _rc(rendered=True, members=_members_119())
    other = _rc(key="senate/119_2_00400", chamber="senate", vote_number=400, rendered=True,
                seal="Passed the Senate 60–38", outcome="The Senate passed it, 60 to 38, on September 3, 2026.")
    extras = [_rc(key=f"house/119_2_{n:05d}", vote_number=n, **{"class": "P"},
                  plain="Vote on an amendment", seal="Amendment rejected 45–53",
                  outcome="On September 3, 2026, the House rejected an amendment, 45 to 53.")
              for n in range(154, 99, -1)]
    html = render.render_vote_by_state(_page(head=head, roll_calls=[other, head] + extras))
    assert html.count('<section class="rc-block"') == 2
    assert html.count('<details class="rc-more"') == 55
    assert html.index('data-rc="house/119_2_00295"') < html.index('data-rc="senate/119_2_00400"')
    assert html.index('data-rc="house/119_2_00154"') < html.index('data-rc="house/119_2_00100"')
    more = html.split('<details class="rc-more"', 1)[1].split("</details>", 1)[0]
    assert "<h3 class=\"rc-caption\">House roll call 154 · September 3, 2026 · Vote on an amendment · Amendment rejected 45–53</h3>" in more
    assert "On September 3, 2026, the House rejected an amendment, 45 to 53." in more
    assert '<li data-state="NY">New York: 13 yes · 11 no · 2 didn\'t vote</li>' in more
    assert 'data-current="1"' in more
    assert '<div class="rc-groups"></div>' in more
    assert "<table" not in more


def test_second_rendered_block_carries_its_own_outcome_and_tally():
    head = _rc(rendered=True, members=_members_119())
    other = _rc(key="senate/119_2_00400", chamber="senate", vote_number=400, rendered=True,
                seal="Passed the Senate 60–38", outcome="The Senate passed it, 60 to 38, on September 3, 2026.")
    html = render.render_vote_by_state(_page(head=head, roll_calls=[other, head]))
    senate = html.split('data-rc="senate/119_2_00400"', 1)[1]
    assert '<p class="outcome">The Senate passed it, 60 to 38, on September 3, 2026.</p>' in senate
    house = html.split('data-rc="house/119_2_00295"', 1)[1].split('data-rc="senate/119_2_00400"', 1)[0]
    assert 'class="outcome"' not in house


def test_house_decisive_head_plus_senate_procedural_renders_both_chambers():
    # 117-hr-3233, 117-hr-7, 117-hr-4350, 118-hr-6126: House passage plus Senate cloture only.
    # T1.8 renders the other chamber's decisive vote, else its newest roll call, so the slot
    # never claims the Senate has no recorded vote while a Senate block sits on the page.
    head = _rc(rendered=True, members=_members_119())
    cloture = _rc(key="senate/117_2_00100", chamber="senate", congress=117, session=2, vote_number=100,
                  **{"class": "P"}, plain="Vote to end debate (needed 60)", rendered=True,
                  seal="Debate not ended 52–46 (60 needed)",
                  outcome=("On September 3, 2026, the Senate voted 52 to 46 to end debate; "
                           "60 votes were needed, so debate did not end."))
    html = render.render_vote_by_state(_page(head=head, roll_calls=[cloture, head]))
    assert html.count('<section class="rc-block"') == 2
    assert 'data-chamber="senate"' in html and 'data-chamber="house"' in html
    senate = html.split('data-rc="senate/117_2_00100"', 1)[1]
    assert "60 votes were needed, so debate did not end." in senate
    assert 'data-current="0"' in senate


def test_fixture_118_hr_21_renders_one_block_per_roll_call():
    page = DataService(data_dir=FIXTURES).get_bill_page(118, "hr", 21)
    assert page is not None
    html = render.render_vote_by_state(page)
    rendered = html.count('<section class="rc-block"')
    assert rendered <= 2
    assert rendered + html.count('<details class="rc-more"') == len(page["roll_calls"])


def test_all_votes_details_is_empty_with_search_select_and_noscript():
    head = _rc(rendered=True, members=_members_119())
    html = render.render_vote_by_state(_page(head=head, roll_calls=[head]))
    assert ('<details class="rc-all" data-url="/api/votes/house/119/2/295" '
            'data-caption="House roll call 295"><summary>All 433 votes, every state</summary>') in html
    assert '<input type="search" id="rc-house-119-2-295-q" class="rc-all-q" autocomplete="off">' in html
    assert ('<select id="rc-house-119-2-295-show" class="rc-all-show"><option value="all">all</option>'
            '<option value="yes">yes</option><option value="no">no</option>'
            "<option value=\"nv\">didn't vote</option></select>") in html
    assert '<div class="rc-all-list"></div>' in html
    assert "Open the full list on the roll call source page →" in html


def test_bill_page_composition_and_heading_outline():
    head = _rc(rendered=True, members=_members_119())
    html = render.render_bill_page(_page(head=head, roll_calls=[head]), "2026-07-07")
    assert html.startswith('<div class="bill-grid" data-ssr="1" data-bill="119-hr-4795">')
    headings = re.findall(r"<(h[1-3])[^>]*>(.*?)</\1>", html)
    assert headings[0][0] == "h1"
    assert [text for tag, text in headings if tag == "h2"] == [
        "How did your representatives vote?", "The vote, by state", "What it does",
        "Official summary", "About this bill",
    ]
    assert html.index("How did your representatives vote?") < html.index("The vote, by state")
    assert html.index('<article class="bill-main">') < html.index('<section class="section fact-box"')
    # The five module wrappers share T2.1's .section role; none uses the .official type role.
    for wrapper in ('<section class="section your-reps"', '<section class="section vote-by-state"',
                    '<section class="section what-it-does"', '<section class="section official-summary-section"',
                    '<section class="section fact-box"'):
        assert wrapper in html, wrapper
    assert 'class="official"' not in html.split("</header>", 1)[1]


def test_bill_page_without_roll_calls_omits_modules_two_and_three():
    html = render.render_bill_page(_page(head=None, roll_calls=[],
                                         status={"text": "No final vote yet", "variant": "moving"}), None)
    assert "How did your representatives vote?" not in html
    assert "The vote, by state" not in html
    assert "none in our data" in html


# --- Route, shell and assets (plan T7.4) ---

SANITIZE_BLOCK = """const SAFE_TAGS = new Set(['P', 'EM', 'STRONG', 'B', 'I', 'BR', 'UL', 'OL', 'LI', 'A']);
function sanitizeHtml(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    doc.body.querySelectorAll('*').forEach(node => {
        if (!SAFE_TAGS.has(node.tagName)) {
            node.replaceWith(...node.childNodes);
        }
        for (const attr of [...node.attributes]) {
            if (attr.name !== 'href') node.removeAttribute(attr.name);
        }
    });
    return doc.body.innerHTML;
}"""

# The one sanctioned HTML sink, byte-identical to baseline bill.js lines 165–168 (June plan
# constraint 4: the sanitize/insertAdjacentHTML block stays untouched).
SINK_BLOCK = """        summaryDiv.textContent = '';
        // Content is sanitized — only safe tags (P, EM, STRONG, B, I, BR, UL, OL, LI, A) remain
        const sanitized = sanitizeHtml(latestSummary);
        summaryDiv.insertAdjacentHTML('afterbegin', sanitized);"""


async def _get_page(path: str):
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    get_data_service.cache_clear()
    return response


@pytest.mark.asyncio
async def test_bill_route_is_fully_server_rendered():
    response = await _get_page("/bill?congress=119&type=hjres&number=20")
    assert response.status_code == 200
    html = response.text
    assert "<!--content-->" not in html
    assert '<div class="bill-grid" data-ssr="1" data-bill="119-hjres-20">' in html
    assert re.search(r'<header class="bill-header">.*?<h1[ >]', html, re.S)
    for heading in ("How did your representatives vote?", "The vote, by state", "What it does", "About this bill"):
        assert heading in html
    for gone in ("Loading bill", "What People Are Saying", "Copy Link", "Generating", "bill-toc"):
        assert gone not in html


@pytest.mark.asyncio
async def test_roll_call_rows_carry_covered_id_and_district_for_js_built_tables():
    response = await _get_page("/api/votes/senate/119/1/372")
    assert response.status_code == 200
    members = response.json()["members"]
    assert all("covered_id" in m and "district" in m and "party" not in m for m in members)
    assert any(m["covered_id"] for m in members if m.get("state") in ("CA", "FL", "NY", "TX"))
    assert all(m["district"] is None for m in members)  # Senate rows never carry a district


@pytest.mark.asyncio
async def test_bill_route_reads_at_most_two_roll_call_files():
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
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
                response = await client.get("/bill?congress=119&type=hjres&number=20")
    get_data_service.cache_clear()
    assert response.status_code == 200
    roll_call_reads = [p for p in opened if f"{os.sep}votes{os.sep}" in p]
    assert len(roll_call_reads) <= 2


def test_bill_shell_links_only_the_new_assets():
    shell = (ROOT / "static" / "bill.html").read_text()
    assert "<title>" in shell and "</title>" in shell and "</head>" in shell
    assert '<main id="main-content" tabindex="-1"><!--content--></main>' in shell
    assert "/static/css/site.css?v=" in shell
    assert "styles.css" not in shell and "broadsheet.css" not in shell
    assert re.findall(r'<script src="/static/js/([a-z]+)\.js\?v=\d+"></script>', shell) == [
        "site", "vote", "bill", "feedback"]
    assert "<script>" not in shell and "onclick" not in shell and "onerror" not in shell


def test_bill_js_is_a_thin_enhancer_that_keeps_the_sanitize_block():
    bill_js = (ROOT / "static" / "js" / "bill.js").read_text()
    assert SANITIZE_BLOCK in bill_js
    assert SINK_BLOCK in bill_js
    assert bill_js.count("insertAdjacentHTML") == 1
    for gone in ("document.title", "renderBill", "arguments", "Copy Link", "localStorage",
                 "slotReadHome", "SLOT_ERROR", "RC_STATE_NAMES"):
        assert gone not in bill_js, gone


def test_bill_js_filters_summary_links_right_after_the_sink():
    # F010: the filter runs on what the pinned sink inserted, inside the same if.
    bill_js = (ROOT / "static" / "js" / "bill.js").read_text()
    assert SINK_BLOCK + "\n        billFilterSummaryLinks(summaryDiv);\n    }\n}" in bill_js


# bill.js runs in a node vm with stand-in nodes; URL is node's WHATWG parser, as in browsers.
_SUMMARY_LINKS_SCRIPT = r"""
const fs = require('fs');
const vm = require('vm');
class FakeNode {
  constructor(tag, href) { this.tagName = tag; this.attrs = { href }; }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  removeAttribute(name) { delete this.attrs[name]; }
}
const nodes = JSON.parse(fs.readFileSync(0, 'utf8')).map(([tag, href]) => new FakeNode(tag, href));
const root = { querySelectorAll: (sel) => (sel === '[href]' ? nodes.filter((n) => 'href' in n.attrs) : []) };
const context = { URL, Map, Set, window: { location: { origin: 'https://clearvoting.org' } },
                  document: { addEventListener() {} } };
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
context.billFilterSummaryLinks(root);
process.stdout.write(JSON.stringify(nodes.map((n) => n.attrs)));
"""

_SUMMARY_LINKS_KEPT = [
    "https://www.congress.gov/bill/119th-congress/house-bill/1",
    "https://crsreports.congress.gov/product/pdf/LSB/LSB10001",
    "https://www.gao.gov/products/gao-24-106001",
    "https://obamawhitehouse.archives.gov/briefing-room",
    "HTTPS://WWW.CONGRESS.GOV/public-laws/119th-congress",
]
_SUMMARY_LINKS_DROPPED = [
    "javascript:alert(document.domain)", " JaVaScRiPt:alert(1)", "java\tscript:alert(1)",
    "data:text/html,<script>alert(1)</script>", "//evil.example/register", "/\\evil.example/polling-place",
    "https://evil.example/", "http://www.congress.gov/bill/119", "https://www.congress.gov@evil.example/",
    "https://evil.example/.gov", "https://congress.gov.evil.example/", "https://evil.example\\.gov/",
    "/bill?congress=119&type=hr&number=1", "", "https://[::1]/",
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed (CI runs without it)")
def test_summary_links_keep_only_https_gov_hrefs_on_anchors():
    cases = ([["A", href] for href in _SUMMARY_LINKS_KEPT + _SUMMARY_LINKS_DROPPED]
             + [["P", "javascript:alert(2)"], ["LI", "https://www.congress.gov/"]])
    done = subprocess.run([shutil.which("node"), "-e", _SUMMARY_LINKS_SCRIPT, str(ROOT / "static" / "js" / "bill.js")],
                          input=json.dumps(cases), capture_output=True, text=True, check=True, timeout=60)
    out = json.loads(done.stdout)
    kept = len(_SUMMARY_LINKS_KEPT)
    assert len(out) == len(cases)
    for href, attrs in zip(_SUMMARY_LINKS_KEPT, out[:kept]):
        assert attrs == {"href": href, "rel": "noopener noreferrer nofollow"}, href
    for (tag, href), attrs in zip(cases[kept:], out[kept:]):
        assert attrs == {}, (tag, href)   # the href is gone; the element and its text stay


def test_vote_js_has_no_positions_table_and_builds_rows_with_the_shared_builder():
    vote_js = (ROOT / "static" / "js" / "vote.js").read_text()
    # [^\n]: under re.S a bare //.* would swallow everything after the first line comment.
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", vote_js, flags=re.S)
    assert "VOTE_COLORS" not in vote_js and "#" not in code
    assert "innerHTML" not in vote_js and ".style" not in vote_js
    # One positions table (T1.2 _POSITIONS ↔ site.js POSITIONS, held equal by T2.2's parity test).
    for duplicate in ("RC_SHORT", "Voted yes", "Didn't vote", "'Yes'", "rcRow("):
        assert duplicate not in code, duplicate
    assert "rcTableRow(" in code and "positionChip(" in code
    assert not hasattr(render, "RC_SHORT_CHIP")


def test_bill_css_never_restyles_the_shared_official_role():
    css = (ROOT / "static" / "css" / "site.css").read_text()
    bill_block = css.split("/* ---- Bill page (plan T7.4", 1)[1].split("@media", 1)[0]
    for selectors in re.findall(r"([^{}]+)\{", bill_block):
        parts = [p.strip() for p in selectors.split(",")]
        assert ".official" not in parts, selectors
    # The section rhythm is T2.1's .section role; no second double rule, no font shorthand.
    assert "3px double" not in bill_block
    assert not re.search(r"(?:^|[;{\s])font\s*:", bill_block)
    assert "linklike" not in css
    for stack in ("Playfair Display", "Lora,", "Inter,"):
        assert stack not in bill_block, stack


@pytest.mark.asyncio
async def test_bill_route_serves_the_error_state_when_rendering_fails():
    with patch("app.main.render_bill_page", side_effect=RuntimeError("boom")):
        response = await _get_page("/bill?congress=119&type=hjres&number=20")
    assert response.status_code == 503
    assert "We couldn't load this page right now." in response.text
    assert "<h1>H.J.Res. 20</h1>" in response.text
    assert '<header class="masthead">' in response.text


# --- Sticky strip (plan T10.4, spec §6.4) ---
_STRIP_FIXTURES = Path(__file__).parent / "fixtures" / "synced"


async def _strip_get(path: str):
    from app.dependencies import get_data_service
    from app.main import app
    with patch("app.dependencies.get_data_dir", return_value=_STRIP_FIXTURES):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(path)
    get_data_service.cache_clear()
    return response


def _strip_block(html: str) -> str:
    start = html.index('<div class="strip"')
    return html[start: html.index("</div>", start) + len("</div>")]


@pytest.mark.asyncio
async def test_bill_strip_repeats_the_head_seal_and_offers_share():
    html = (await _strip_get("/bill?congress=119&type=hr&number=1")).text
    main = html[html.index('<main id="main-content"'):]
    seal = re.search(r'class="seal seal--(?:final|moving)"[^>]*>([^<]+)<', main).group(1)
    strip = _strip_block(html)
    assert f'<p class="strip-label">H.R. 1 · {seal}</p>' in strip
    assert '<button type="button" class="btn--secondary strip-share" data-strip-share>Share</button>' in strip
    assert html.index('<div class="strip"') < html.index('<main id="main-content"')


def test_bill_strip_without_a_status_seal_shows_the_code_only():
    from app.render import render_bill_strip
    strip = render_bill_strip("H.R. 4795", '<main><span class="seal seal--pending">No plain-English summary yet</span></main>')
    assert '<p class="strip-label">H.R. 4795</p>' in strip
