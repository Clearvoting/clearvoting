"""Home block renderers (spec §4.1, §6.4, §8 item 2): lead, Latest Vote card, the Record.
Pure-function tests on synthetic rows shaped like get_bills()/get_latest_vote()."""
import re

import pytest

from app import render

COUNTS = {"CA": 54, "FL": 29, "NY": 28, "TX": 39}
COVERAGE = {"members": 150, "since": "2021-01-03"}
LAST_SYNC = "2026-09-05T06:00:00Z"
AI_UPDATED = "2026-07-07"
PENDING = '<span class="seal seal--pending">No plain-English summary yet</span>'

VOTE = {
    "chamber": "House",
    "date": "September 3, 2026",
    "date_iso": "2026-09-03",
    "plain_question": "Final vote to pass",
    "result": "Passed",
    "counts": {"yeas": 237, "nays": 169, "present": 0, "absent": 27},
    "bill": {"congress": 119, "type": "hr", "number": 4795,
             "title": "Protect Economic and Academic Freedom Act of 2026"},
    "one_liner": None,
    "has_summary": False,
    "outcome": "Passed the House 237–169",
    "state_tallies": {"NY": [15, 11, 0]},
    "covered": [],
}
SUMMARIZED_VOTE = {**VOTE, "one_liner": "Bars federal funds for colleges that limit campus speech",
                   "has_summary": True}


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def _bill(number, one_liner=None, title=None, status="Passed the House 237–169",
          date="2026-09-03", provisions=None):
    return {
        "congress": 119, "type": "HR", "number": str(number),
        "title": title or f"Official title of H.R. {number}",
        "one_liner": one_liner, "provisions": provisions or [],
        "derived_status": status, "activity_date": date,
        "latestAction": {"actionDate": date, "text": "Passed House"},
    }


SUMMARIZED = [
    _bill(100 + i, one_liner=f"Plain headline {i}", provisions=[f"Provision {i}.{k}" for k in range(5)])
    for i in range(7)
]
LONG_TITLE = "To amend title 38, United States Code, " + "and for other related purposes " * 8


# --- Lead (§4.1 m2) ---

def test_home_lead_order_and_copy():
    html = render.render_home_lead(COUNTS, COVERAGE)
    order = [
        '<p class="kicker">An independent record of Congress</p>',
        '<h1 id="home-h1">See how your representatives vote.</h1>',
        '<p class="deck">',
        '<form class="zip-form" id="find" method="get" action="/state">',
        '<p class="state-links-label">Or choose a state:</p>',
        '<ul class="state-links">',
        '<p class="coverage">',
        '<details class="notify-disclosure">',
    ]
    positions = [html.index(marker) for marker in order]
    assert positions == sorted(positions)
    assert html.startswith('<div class="lead-main">')
    assert 'id="home-reps"' not in html  # the module-4 mount follows the card (render_home)
    assert ("ClearVoting covers California, Florida, New York and Texas today — 150 members "
            "and every bill that has had a roll-call vote since January 2021.") in html
    assert '<a class="state-link" href="/state?code=TX">Texas · 39</a>' in html


def test_coverage_sentence_without_the_index_drops_the_since_clause():
    html = render.render_home_lead(COUNTS, {"members": 150, "since": None})
    assert "every bill that has had a roll-call vote.</p>" in html
    assert " since " not in _text(html.split('<p class="coverage">')[1].split("</p>")[0])


# --- Latest Vote card (§4.1 m3, §8 item 2) ---

def test_card_heading_is_an_h2_styled_as_a_kicker():
    html = render.render_latest_vote_card(VOTE)
    assert html.startswith('<aside class="vote-card" aria-labelledby="latest-vote-h" data-ssr="1">')
    assert '<h2 class="kicker" id="latest-vote-h">The latest vote</h2>' in html


def test_card_dateline_uses_chamber_long_date_and_plain_question():
    html = render.render_latest_vote_card(VOTE)
    assert '<p class="dateline meta">U.S. House · September 3, 2026 · Final vote to pass</p>' in html


def test_card_without_a_displayable_summary_uses_the_official_title():
    html = render.render_latest_vote_card(VOTE, AI_UPDATED)
    assert ('<p class="card-headline official clamp2">'
            "Protect Economic and Academic Freedom Act of 2026</p>") in html
    assert PENDING in html
    assert ('<a class="arrow-link" href="/bill?congress=119&amp;type=hr&amp;number=4795">'
            "See the vote and the official summary →</a>") in html
    assert "Summarized by AI" not in html


def test_card_with_a_summary_uses_the_one_liner_and_attributes_it():
    html = render.render_latest_vote_card(SUMMARIZED_VOTE, AI_UPDATED)
    assert '<p class="card-headline">Bars federal funds for colleges that limit campus speech</p>' in html
    assert PENDING not in html
    assert ">What this bill does, in plain English →</a>" in html
    assert ("Summarized by AI from the bill's title, official summary and text excerpt"
            " · summaries last updated July 7, 2026") in html


def test_card_tally_bar_and_outcome_seal():
    html = render.render_latest_vote_card(VOTE)
    assert ('role="img" aria-label="Passed the House: 237 voted yes, 169 voted no, '
            '27 did not vote"') in html
    assert "237 yes · 169 no · 27 didn't vote" in _text(html)
    assert 'style="width:58.4%" data-yes="237"' in html
    assert 'style="width:41.6%" data-no="169"' in html
    assert '<span class="seal seal--moving">Passed the House 237–169</span>' in html


@pytest.mark.parametrize("bill_type, variant", [
    ("sjres", "moving"), ("hjres", "moving"), ("hconres", "moving"), ("sconres", "moving"),
    ("hres", "final"), ("sres", "final"),
])
def test_card_adoption_is_final_only_for_a_simple_resolution(bill_type, variant):
    # §6.4/§7.2: one chamber's adoption is final only when that chamber is the only one needed.
    vote = {**VOTE, "chamber": "Senate", "outcome": "Adopted by the Senate 51–47",
            "bill": {**VOTE["bill"], "type": bill_type}}
    html = render.render_latest_vote_card(vote)
    assert f'<span class="seal seal--{variant}">Adopted by the Senate 51–47</span>' in html


def test_card_tie_shows_the_outcome_seal_and_an_even_bar():
    # §4.1 m3 edge case: a tie shows the count and the result string (T1.2 result_phrase).
    tie = {**VOTE, "chamber": "Senate", "plain_question": "Vote to take it up",
           "counts": {"yeas": 50, "nays": 50, "present": 0, "absent": 0},
           "outcome": "Tied 50–50 — motion failed", "bill": {**VOTE["bill"], "type": "s"}}
    html = render.render_latest_vote_card(tie)
    assert '<span class="seal seal--moving">Tied 50–50 — motion failed</span>' in html
    assert 'aria-label="Tied: 50 voted yes, 50 voted no"' in html
    assert 'style="width:50.0%" data-yes="50"' in html
    assert "50 yes · 50 no" in _text(html)


def test_card_order_is_dateline_headline_result_link():
    html = render.render_latest_vote_card(VOTE)
    markers = ['class="dateline', 'class="card-headline', 'class="tally"',
               'seal--moving">Passed', 'class="arrow-link"']
    positions = [html.index(m) for m in markers]
    assert positions == sorted(positions)


def test_card_unavailable_keeps_the_card_and_heading():
    html = render.render_latest_vote_card(None)
    assert html.startswith('<aside class="vote-card vote-card--empty"')
    assert '<h2 class="kicker" id="latest-vote-h">The latest vote</h2>' in html
    assert "The latest vote isn't available right now." in html


# --- Tally and seal components (§6.4) ---

def test_tally_omits_didnt_vote_when_zero():
    html = render.render_tally({"yeas": 90, "nays": 6, "present": 0, "absent": 0}, "Passed the Senate")
    assert 'aria-label="Passed the Senate: 90 voted yes, 6 voted no"' in html
    assert "didn't vote" not in html


@pytest.mark.parametrize("variant", ["final", "moving", "pending", "ballot"])
def test_seal_variants(variant):
    assert render.render_seal("Seat up Nov 3", variant) == (
        f'<span class="seal seal--{variant}">Seat up Nov 3</span>')


def test_seal_unknown_variant_falls_back_to_moving():
    assert render.render_seal("x", "loud") == '<span class="seal seal--moving">x</span>'


# --- The Record (§4.1 m5) ---

def test_record_with_a_summarized_lead():
    bills = [dict(SUMMARIZED[0], title=LONG_TITLE)] + SUMMARIZED[1:]
    html = render.render_record(bills, LAST_SYNC, "2021-01-03", None, AI_UPDATED)
    assert html.startswith('<section class="record" id="record" aria-labelledby="record-h" data-ssr="1">')
    assert '<p class="kicker">The Record</p><h2 id="record-h">What Congress voted on</h2>' in html
    assert ('<p class="stamp meta">As of September 5, 2026 · every bill that has had a roll-call '
            "vote since January 2021, newest activity first.</p>") in html
    lead, _, rows = html.partition('<ul class="record-list">')
    assert '<p class="kicker">H.R. 100 · 119th Congress</p>' in lead
    assert '<p class="lead-headline"><a href="/bill?congress=119&amp;type=hr&amp;number=100">Plain headline 0</a></p>' in lead
    assert lead.count("<li>") == 4  # provisions capped at 4
    assert '<p class="official-line">Officially: To amend title 38' in lead
    assert "…</p>" in lead and "<summary>Show full title</summary>" in lead
    assert ">See who voted →</a>" in lead
    assert rows.count('class="bill-row"') == 6
    assert "Officially" not in rows
    assert "don't have a plain-English summary yet" not in html
    assert "Most recent plain-English summary" not in html
    assert ("Summarized by AI from the bill's title, official summary and text excerpt"
            " · summaries last updated July 7, 2026") in html


def test_record_with_a_withheld_lead_counts_rows_and_adds_the_latest_summary():
    lead_bill = _bill(4795, title="Protect Economic and Academic Freedom Act of 2026",
                      status={"text": "Passed the House 237–169", "variant": "moving"})
    bills = [lead_bill] + SUMMARIZED[1:4] + [_bill(201), _bill(202)] + SUMMARIZED[4:5]
    latest = _bill(6500, one_liner="Extend no-tax imports from 32 African countries through 2028",
                   provisions=["a", "b", "c", "d", "e"], date="2026-07-02", status="Passed both chambers")
    html = render.render_record(bills, LAST_SYNC, "2021-01-03", latest, AI_UPDATED)
    assert ("3 of the 7 bills below don't have a plain-English summary yet and show their "
            "official title.</p>") in html
    lead = html.split('<ul class="record-list">')[0]
    assert '<p class="lead-headline official"><a href=' in lead
    assert PENDING in lead
    assert "Show full title" not in lead  # 49 characters, under the 140 cap
    assert '<span class="seal seal--moving">Passed the House 237–169</span>' in lead
    rows = html.split('<ul class="record-list">')[1].split("</ul>")[0]
    assert rows.count('class="row-headline row-headline--official"') == 2
    block = html.split('<section class="latest-summary"')[1]
    assert '<h2 id="latest-summary-h">Most recent plain-English summary · Jul 2, 2026</h2>' in block
    assert block.count("<li>") == 4
    assert ">Extend no-tax imports from 32 African countries through 2028</a>" in block


def test_record_stamp_singular():
    bills = SUMMARIZED[:6] + [_bill(300)]
    html = render.render_record(bills, LAST_SYNC, "2021-01-03")
    assert ("1 of the 7 bills below doesn't have a plain-English summary yet and shows its "
            "official title.</p>") in html


def test_record_stamp_without_sync_or_index_is_capitalized():
    html = render.render_record(SUMMARIZED[:2], None)
    assert ('<p class="stamp meta">Every bill that has had a roll-call vote, newest activity first.</p>'
            in html)


@pytest.mark.parametrize("status, variant", [
    ("Became law", "final"),
    ("Passed both chambers", "final"),
    ({"text": "Adopted by the House 220–210", "variant": "final"}, "final"),    # hres (T1.2)
    ({"text": "Adopted by the Senate 51–47", "variant": "moving"}, "moving"),   # sjres (T1.2)
    ({"text": "Passed the House 237–169", "variant": "loud"}, "moving"),
    ("Passed the House 237–169", "moving"),
    ("Rejected by the House 189–235", "moving"),
    ({"text": "Passed the Senate 90–6", "variant": "final"}, "final"),
    (None, "moving"),
])
def test_row_seal_variant(status, variant):
    html = render.render_record([_bill(1, one_liner="x", status=status)], LAST_SYNC)
    assert f'class="seal seal--{variant}"' in html


def test_missing_status_reads_no_final_vote_yet():
    html = render.render_record([_bill(1, one_liner="x", status=None)], LAST_SYNC)
    assert '<span class="seal seal--moving">No final vote yet</span>' in html


@pytest.mark.parametrize("bills", [None, []])
def test_record_unavailable_keeps_the_head(bills):
    html = render.render_record(bills, LAST_SYNC)
    assert '<h2 id="record-h">What Congress voted on</h2>' in html
    assert "We couldn't load recent bills right now." in html
    assert "stamp" not in html


# --- Composition (§4.1 order, §9.1 hydration marker) ---

def test_render_home_puts_the_card_after_the_lead_and_the_record_last():
    html = render.render_home(COUNTS, COVERAGE, VOTE, SUMMARIZED, None, LAST_SYNC, AI_UPDATED)
    # No aria-label: section.lead is not a region landmark, so aside.vote-card nests in main only.
    assert html.startswith('<section class="lead"><div class="lead-main">')
    assert "aria-label=\"Start here\"" not in html
    # §4.1 modules m2, m3, m4 (mount), m5; §8 item 2 outline.
    assert (html.index('class="lead-main"') < html.index('<aside class="vote-card"')
            < html.index('</section><div class="home-reps" id="home-reps"></div><section class="record"'))
    assert html.count("<h1") == 1
