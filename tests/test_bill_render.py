"""Bill page renderers (plan T7.1, T7.2, T7.4): pure functions over DataService.get_bill_page()."""
import json
import re
from html import escape
from pathlib import Path

import pytest

from app import render
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
    assert ('<a href="https://www.congress.gov/bill/119th-congress/house-bill/4795/text" '
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
    assert html.startswith('<aside class="section fact-box" aria-labelledby="facts-h">')
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
