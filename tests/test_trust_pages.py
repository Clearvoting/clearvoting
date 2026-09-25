"""Trust pages (About, Methodology, Privacy) and the 404 page — plan Task T5.1.

Counts are asserted against the DataService, never hard-coded, so these tests hold
when the fixtures or the real data change (spec §4.6; "115" is approximate)."""
import inspect
import re
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app import render
from app.main import app
from app.services.ai_summary import SYSTEM_PROMPT

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REPO = Path(__file__).parent.parent
STATIC = REPO / "static"
PARTY_LEAK = re.compile(r"Democratic|Republican|Independent|\[[RDI]-")

# Synthetic counts for the pure-renderer tests (route tests use the real adapter).
COUNTS = {
    "members": 150, "senators": 8, "bills": 1610, "shown": 1435, "missing": 60,
    "withheld": 115, "audited": 1200, "nominations": 1469,
    "since": "2021-01-03", "ai_summaries_updated": "2026-07-07",
}
CROSSWALK_SOURCE = {
    "name": "U.S. Census Bureau 2020 ZCTA to 119th Congressional District relationship files",
    "url": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/",
    "retrieved": "2026-09-11",
    "licence": "Public domain (17 U.S.C. §105)",
    "share": "land area (AREALAND_PART / AREALAND_ZCTA5_20), covered states only",
}
SENATE = {
    "_source": {
        "name": "U.S. Senate — senators by class",
        "url": "https://www.senate.gov/senators/Class_II.htm and https://www.senate.gov/senators/Class_III.htm",
        "retrieved": "2026-09-19",
        "method": "Class II page lists Cornyn (R-TX); Class III page lists Moody (R-FL).",
    },
    "election_day": "2026-11-03",
    "seats": [
        {"state": "TX", "bioguideId": "C001056", "name": "Cornyn, John", "kind": "regular", "class": 2},
        {"state": "FL", "bioguideId": "M001244", "name": "Moody, Ashley", "kind": "special", "class": 3},
    ],
}


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


async def _get(path: str):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    _clear_data_service_cache()
    return response


def _fixture_counts() -> dict:
    """The same adapter the routes use, over the fixture data."""
    from app.main import _trust_counts
    with _patch_data_dir():
        _clear_data_service_cache()
        counts = _trust_counts()
    _clear_data_service_cache()
    return counts


class _Outline(HTMLParser):
    """(level, text) of every h1–h6 inside <main> (the dialog's h2 sits outside <main>)."""

    def __init__(self):
        super().__init__()
        self.in_main = 0
        self.current = None
        self.headings: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main += 1
        elif self.in_main and re.fullmatch(r"h[1-6]", tag):
            self.current = [int(tag[1]), ""]

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main -= 1
        elif self.current and tag == f"h{self.current[0]}":
            self.headings.append((self.current[0], self.current[1].strip()))
            self.current = None

    def handle_data(self, data):
        if self.current:
            self.current[1] += data


def _outline(html: str) -> list[tuple[int, str]]:
    parser = _Outline()
    parser.feed(html)
    return parser.headings


def _assert_h1_then_h2(outline):
    assert outline, "no headings inside <main>"
    assert outline[0][0] == 1
    assert [level for level, _ in outline].count(1) == 1
    for (prev, _), (level, text) in zip(outline, outline[1:]):
        assert level <= prev + 1, f"heading level skipped at {text!r}"
    assert any(level == 2 for level, _ in outline[1:])


# --- Pure renderers ---

def test_prompt_rules_splits_the_two_numbered_lists():
    rules = render.prompt_rules(SYSTEM_PROMPT)
    assert rules["neutrality"][0].startswith("NO adjectives")
    assert rules["accuracy"][0].startswith("MATCH THE SCOPE EXACTLY")
    assert not any(r[:1].isdigit() for r in rules["neutrality"] + rules["accuracy"])
    assert not any(r.startswith("Output valid JSON") for r in rules["accuracy"])


def test_about_counts_sentence():
    out = render.render_about_counts(COUNTS)
    assert ("California, Florida, New York and Texas today: 150 members and 1,610 bills — "
            "every bill that has had a roll-call vote since January 2021. "
            "The site is in English only for now.") in out


def test_about_counts_without_a_first_vote_date_drops_the_month():
    out = render.render_about_counts({**COUNTS, "since": None})
    assert "every bill that has had a roll-call vote. The site is in English only for now." in out


def test_methodology_coverage_and_ai_sections():
    rules = render.prompt_rules(SYSTEM_PROMPT)
    out = render.render_methodology(COUNTS, CROSSWALK_SOURCE, rules, SENATE)
    for anchor in ("coverage", "ai", "recent-votes", "counts", "zip", "ballot"):
        assert f'id="{anchor}"' in out
    assert ("ClearVoting holds 1,610 bills — every bill that has had a roll-call vote since "
            "January 2021 in the House or Senate.") in out
    assert "the 1,469 Senate votes on nominations since January 2021 aren't included yet." in out
    assert ("1,435 of 1,610 bills have a plain-English summary. 60 have none yet, and 115 summaries "
            "are withheld because they did not pass our automated accuracy check; those bills show "
            "their official title. Plain-English summaries were last updated July 7, 2026.") in out
    assert "1,200 summaries were spot-checked by a second AI review." in out
    assert "Member summaries are withdrawn until they can be rewritten without stance labels." in out
    assert ("We do not publish arguments for or against a bill. An earlier version showed AI-drafted "
            "'supporters say / critics say' bullets; they were unattributed and have been removed "
            "until they can be sourced.") in out
    assert "<h3>Our rules for neutrality</h3>" in out
    assert "We show roll calls voted as a count, never as a grade, and never rank members by it." in out
    assert ("Every vote in our record is in the member's full record below it; Senate votes on "
            "nominations are not in our record yet (see What we cover).") in out
    assert "Every vote is in the member's full record" not in out


def test_methodology_zip_and_ballot_sections():
    out = render.render_methodology(COUNTS, CROSSWALK_SOURCE, render.prompt_rules(SYSTEM_PROMPT), SENATE)
    assert "Public domain (17 U.S.C. §105)" in out
    assert "retrieved September 11, 2026" in out
    assert 'href="https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/"' in out
    assert ("Shares are land area, not population; PO-box-only and business ZIPs are not in the "
            "Census file; a ZIP that crosses a state line is shown with a note.") in out
    assert "at least 5 % of the ZIP's land area" in out
    assert ("we show the match with a note and remember it only if you choose it.") in out
    assert "don't remember it" not in out
    assert ('<p><a class="source-link" href="https://www.house.gov/representatives/find-your-representative" '
            'rel="noopener">Not sure? Look up your district by street address on house.gov →</a></p>') in out
    assert "Every House seat is on the ballot on November 3, 2026." in out
    assert ("Of the eight senators we cover, the Texas seat held by John Cornyn is up for its regular "
            "election and the Florida seat held by Ashley Moody is up in a special election. "
            "Source: senate.gov class lists, retrieved September 19, 2026.") in out
    assert 'href="https://www.senate.gov/senators/Class_II.htm"' in out
    # _source.method (party letters) is never rendered
    assert "(R-TX)" not in out and "Class II page lists" not in out
    assert not re.search(r"\([RDI]-[A-Z]{2}\)", out)
    assert not PARTY_LEAK.search(out)


def test_methodology_links_only_https_sources():
    hostile = {**CROSSWALK_SOURCE, "url": "javascript:alert(1)"}
    senate = {**SENATE, "_source": {**SENATE["_source"], "url": "http://evil.example/x"}}
    out = render.render_methodology(COUNTS, hostile, render.prompt_rules(SYSTEM_PROMPT), senate)
    assert 'href="javascript:' not in out
    assert "evil.example" not in out


def test_methodology_degrades_without_the_sanctioned_files():
    out = render.render_methodology(COUNTS, {}, render.prompt_rules(SYSTEM_PROMPT), {})
    assert 'id="zip"' in out and 'id="ballot"' in out
    assert "Ballot details aren't available right now." in out
    assert "Source:" not in out.split('id="zip"')[1].split("</section>")[0]


def test_not_found_body():
    out = render.render_not_found('<form action="/state"></form>', '<p class="states"></p>')
    assert '<p class="kicker">Not in this edition</p>' in out
    assert "<h1>We don't have that page</h1>" in out
    assert "The link may be old, or the bill or member may be outside our four-state coverage." in out
    assert '<form action="/state"></form><p class="states"></p>' in out
    assert 'href="/"' in out
    assert out.count("<h1") == 1 and "<h2" not in out


def test_sanctioned_sources_default_to_empty_when_files_are_missing(tmp_path):
    from app.services.data_service import DataService
    ds = DataService(tmp_path)
    assert ds._crosswalk_source == {} and ds._senate_file == {}


def test_sanctioned_sources_are_loaded_at_startup_from_the_fixtures():
    from app.services.data_service import DataService
    ds = DataService(FIXTURES)
    assert ds._crosswalk_source["url"].startswith("https://www2.census.gov/")
    assert "_source" not in ds._zip_districts          # T1.5's lookup still skips the block
    assert ds._senate_file["_source"]["retrieved"]
    assert all(isinstance(seat["class"], int) for seat in ds._senate_file["seats"])
    assert set(ds._senate_2026) == {seat["bioguideId"] for seat in ds._senate_file["seats"]}


# --- Routes ---

def test_trust_routes_are_plain_def():
    paths = {"/about", "/methodology", "/privacy"}
    seen = set()
    for route in app.routes:
        if getattr(route, "path", None) in paths:
            seen.add(route.path)
            assert not inspect.iscoroutinefunction(route.endpoint), route.path
    assert seen == paths


async def test_about_page():
    response = await _get("/about")
    assert response.status_code == 200
    html = response.text
    counts = _fixture_counts()
    assert f"{counts['members']:,} members and {counts['bills']:,} bills" in html
    assert "The site is in English only for now." in html
    assert ("ClearVoting is maintained by Joseph Garcia, an independent volunteer. To reach him, use "
            "<em>Report an error</em> at the foot of any page, or the form below.") in html
    assert "Unfunded and not affiliated with any campaign, party or advocacy group." in html
    assert 'id="about-feedback-cta"' in html
    assert "animate-" not in html
    assert "<!--content-->" not in html
    assert "12 strict rules" not in html and "what people are saying" not in html.lower()
    assert 'href="/methodology"' in html and 'href="/privacy"' in html
    outline = _outline(html)
    _assert_h1_then_h2(outline)
    assert outline[0] == (1, "About ClearVoting")


async def test_methodology_page():
    response = await _get("/methodology")
    assert response.status_code == 200
    html = response.text
    counts = _fixture_counts()
    assert "<title>Methodology &amp; Corrections — ClearVoting</title>" in html
    for anchor in ("sources", "freshness", "coverage", "ai", "recent-votes", "counts",
                   "zip", "ballot", "corrections", "report"):
        assert f'id="{anchor}"' in html, anchor
    assert f"ClearVoting holds {counts['bills']:,} bills" in html
    assert f"{counts['shown']:,} of {counts['bills']:,} bills have a plain-English summary." in html
    assert f"{counts['withheld']:,} summaries are withheld" in html
    assert f"the {counts['nominations']:,} Senate votes on nominations" in html
    assert ("Roll calls and bills are synced weekly; the edition line on every page shows the last "
            "sync and the newest roll call.") in html
    assert "No corrections logged yet." in html
    assert "the Texas seat held by John Cornyn is up for its regular election" in html
    assert re.search(r"Of the \w+ senators we cover", html)
    assert not PARTY_LEAK.search(html)
    assert not re.search(r"\([RDI]-[A-Z]{2}\)", html)
    assert 'id="about-feedback-cta"' in html
    outline = _outline(html)
    _assert_h1_then_h2(outline)
    assert outline[0] == (1, "Methodology & Corrections")


async def test_privacy_page():
    response = await _get("/privacy")
    assert response.status_code == 200
    html = response.text
    for sentence in (
        "If the spreadsheet is unavailable, a sign-up may be written to a temporary file on our "
        "server, which is deleted when the server restarts.",
        "To have your email deleted, send a request through the feedback form with the address to remove.",
        "We remember where you live, never how you look.",
        "The ZIP you type becomes part of the page address, so it appears in our hosts' request logs "
        "along with your IP address.",
        "This site makes no third-party requests except member photos from congress.gov, which "
        "receives only our site's address as the referrer.",
        "No cookies, no analytics scripts.",
        "Whether you revealed party labels is kept only for this browsing session in this tab. "
        "Showing them asks our server for the party field, so that request appears in our hosts' "
        "request logs like any page address.",
    ):
        assert sentence in html, sentence
    assert "never sent to us" not in html
    for processor in ("Google (Sheets)", "Render (hosting)", "Cloudflare (network)"):
        assert processor in html
    assert "<code>cv-home</code>" in html
    outline = _outline(html)
    _assert_h1_then_h2(outline)
    assert outline[0] == (1, "Privacy")


async def test_unknown_path_serves_the_not_in_this_edition_page():
    response = await _get("/no-such-page")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "Not in this edition" in html
    assert "The link may be old, or the bill or member may be outside our four-state coverage." in html
    assert 'action="/state"' in html and 'name="zip"' in html
    assert "Find your representatives instead" in html
    assert "/state?code=FL" in html
    assert 'href="/"' in html
    assert _outline(html) == [(1, "We don't have that page")]


# --- Error state (spec §4 "Common to every page", §7.6) ---

def _broken_counts():
    raise RuntimeError("votes index unavailable")


@pytest.mark.parametrize("path, h1", [("/about", "About ClearVoting"),
                                      ("/methodology", "Methodology & Corrections")])
async def test_trust_page_error_state_when_counts_fail(path, h1):
    with patch("app.main._trust_counts", side_effect=_broken_counts):
        response = await _get(path)
    assert response.status_code == 503
    html = response.text
    assert render.PAGE_ERROR_SENTENCE in html
    assert html.count("<h1") == 1
    assert _outline(html)[0] == (1, h1)
    assert "<!--content-->" not in html


async def test_404_survives_a_member_count_failure():
    from app.services.data_service import DataService
    with patch.object(DataService, "get_member_counts", side_effect=RuntimeError("members unavailable")):
        response = await _get("/no-such-page")
    assert response.status_code == 404
    html = response.text
    assert "Not in this edition" in html
    for code in ("CA", "FL", "NY", "TX"):
        assert f"/state?code={code}" in html, code


# --- Shells ---

TRUST_SHELLS = ["about.html", "methodology.html", "privacy.html", "404.html"]


@pytest.mark.parametrize("name", TRUST_SHELLS)
def test_trust_shell_contract(name):
    text = (STATIC / name).read_text()
    assert text.lstrip().startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in text                                   # §8 item 9 (3.1.1)
    assert '<a href="#main-content" class="skip-link">' in text         # §8 item 7 (2.4.1)
    assert '<header class="masthead">' in text and "<nav" in text and "<footer" in text   # §8 item 2
    assert re.search(r"<title>[^<]+</title>", text)
    assert "</head>" in text
    assert "/static/css/site.css" in text
    assert "styles.css" not in text and "broadsheet.css" not in text
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", text), "inline script"
    assert not re.search(r"\son[a-z]+\s*=", text), "inline handler"
    assert "innerHTML" not in text
    assert "animate-" not in text
    for hook in ('id="feedback-modal"', 'id="feedback-open"', 'id="feedback-form"',
                 'id="feedback-message"', 'id="feedback-status"', 'id="data-freshness"',
                 'href="/methodology"', 'href="/privacy"', 'href="/about"'):
        assert hook in text, hook
    assert '<main id="main-content" tabindex="-1">' in text


@pytest.mark.parametrize("name", ["about.html", "methodology.html", "404.html"])
def test_server_filled_shells_carry_the_content_marker(name):
    assert (STATIC / name).read_text().count("<!--content-->") == 1


def test_feedback_context_names_the_trust_pages():
    js = (STATIC / "js" / "feedback.js").read_text()
    assert "path === '/methodology'" in js and "path === '/privacy'" in js


def test_product_strategy_states_the_four_covered_states():
    text = (REPO / "docs" / "product-strategy.md").read_text()
    assert "50 states" not in text


def test_product_strategy_cites_no_rule_count():
    # F18: the prompt's rule lists live on /methodology; a hand-typed count goes stale.
    text = (REPO / "docs" / "product-strategy.md").read_text()
    assert not re.search(r"\b\d+ (neutrality )?(guardrails|rules)\b", text)
