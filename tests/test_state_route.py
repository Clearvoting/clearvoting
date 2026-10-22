"""/state: ZIP normalization, the 302s, the not-found and malformed states, the code/zip
mismatch, invalid codes, district URLs, and the new shell and thin enhancers
(plan T4.2; spec §3.1, §3.2, §4.2, §5.3, §10 #5)."""
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.data_service import DataService

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
STATIC = Path(__file__).parent.parent / "static"
NY_OVERVIEW = json.loads((FIXTURES / "state_overview" / "NY.json").read_text())
ZIP_REDIRECT_CACHE = "public, max-age=0, s-maxage=86400"


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


def _section(markup: str, opening: str) -> str:
    return markup.split(opening, 1)[1].split("</section>", 1)[0]


# --- ZIP → 302 ---

@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["11570", "11570-1234", "11570 1234", " 11570 ", "11570%201234"])
async def test_single_match_redirects_to_the_district_with_mine(raw):
    response = await _get(f"/state?zip={raw}")
    assert response.status_code == 302
    assert response.headers["location"] == "/state?code=NY&district=4#mine"
    assert response.headers["cache-control"] == ZIP_REDIRECT_CACHE


@pytest.mark.asyncio
async def test_split_zip_redirects_to_code_and_zip_without_mine():
    response = await _get("/state?zip=11201")
    assert response.status_code == 302
    assert response.headers["location"] == "/state?code=NY&zip=11201"
    assert response.headers["cache-control"] == ZIP_REDIRECT_CACHE


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,code", [("73949", "TX"), ("89019", "CA"), ("97635", "CA")])
async def test_partial_zip_redirects_to_code_and_zip_without_mine(raw, code):
    response = await _get(f"/state?zip={raw}")
    assert response.status_code == 302
    assert response.headers["location"] == f"/state?code={code}&zip={raw}"


@pytest.mark.asyncio
async def test_code_zip_mismatch_redirects_to_the_zips_state():
    single = await _get("/state?code=CA&zip=11570")
    assert single.status_code == 302
    assert single.headers["location"] == "/state?code=NY&district=4#mine"
    split = await _get("/state?code=TX&zip=11201")
    assert split.status_code == 302
    assert split.headers["location"] == "/state?code=NY&zip=11201"


# --- ZIP pages rendered in place ---

@pytest.mark.asyncio
async def test_split_zip_page_offers_each_district():
    response = await _get("/state?code=NY&zip=11201")
    assert response.status_code == 200
    html = response.text
    assert "<h1>Your representatives</h1>" in html
    assert ("ZIP 11201 spans two House districts — about 72 % of the ZIP's land area "
            "(not its residents) is in District 10 and 28 % in District 7.") in html
    assert html.count("This is my district →") == 2
    assert 'href="/state?code=NY&amp;district=10#mine"' in html
    assert 'href="/state?code=NY&amp;district=7#mine"' in html
    assert "https://www.house.gov/representatives/find-your-representative" in html
    assert 'id="remember-district"' not in html
    assert '<section class="senate"' not in html


@pytest.mark.asyncio
async def test_partial_zip_page_notes_the_share_outside_our_states():
    response = await _get("/state?code=TX&zip=73949")
    assert response.status_code == 200
    assert ("About 86 % of ZIP 73949's land area is outside California, Florida, New York and Texas; "
            "if you live in that part, we don't cover your state yet.") in response.text
    assert "spans two House districts" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["44101", "88430"])
async def test_unmatched_zip_renders_not_found_in_place(raw):
    response = await _get(f"/state?zip={raw}")
    assert response.status_code == 200
    html = response.text
    assert (f"We couldn't match ZIP {raw} to a congressional district in California, Florida, "
            "New York or Texas — the four states ClearVoting covers.") in html
    for code in ("CA", "FL", "NY", "TX"):
        assert f'href="/state?code={code}"' in html


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["abc", "1157", "115701", "11570-12"])
async def test_malformed_zip_renders_the_error_and_keeps_the_value(raw):
    response = await _get(f"/state?zip={raw}")
    assert response.status_code == 200
    html = response.text
    assert "<h1>Find your representatives</h1>" in html
    assert '<p class="field-error" id="zip-top-field-error">A ZIP code is five digits.</p>' in html
    assert f'value="{raw}"' in html
    assert 'aria-describedby="zip-top-field-error"' in html


@pytest.mark.asyncio
async def test_malformed_zip_on_a_state_url_keeps_the_roster():
    response = await _get("/state?code=NY&zip=abc")
    assert response.status_code == 200
    assert "<h1>New York's representatives</h1>" in response.text
    assert '<p class="field-error" id="zip-top-field-error">A ZIP code is five digits.</p>' in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/state?zip=", "/state?code=NY&zip="])
async def test_a_malformed_zip_is_echoed_only_up_to_the_fields_maxlength(path):
    """F041: a crafted link cannot put its own sentence into the ZIP box; the field takes 10."""
    response = await _get(path + "Qqqqqzzzzz%20Wwwww%20vote%20Wednesday")
    assert response.status_code == 200
    assert 'value="Qqqqqzzzzz"' in response.text
    assert "Wwwww" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/state", "/state?zip=", "/state?zip=%20%20"])
async def test_finder_page_without_code_or_zip(path):
    response = await _get(path)
    assert response.status_code == 200
    assert "<h1>Find your representatives</h1>" in response.text
    assert "field-error" not in response.text


# --- codes and districts ---

@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/state?code=ZZ", "/state?code=oh", "/state?code=NY1", "/state?code=ZZ&zip=11570"])
async def test_invalid_code_is_404(path):
    response = await _get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_plain_state_url_lists_senate_then_house_by_district():
    response = await _get("/state?code=NY")
    assert response.status_code == 200
    html = response.text
    assert "<h1>New York's representatives</h1>" in html
    assert re.search(r'<section class="state-header" data-state="NY"[^>]*>.*?<h1>', html, re.DOTALL)
    assert html.index('<h2 id="senate-h">U.S. Senate</h2>') < html.index('<h2 id="house-h">The House, by district</h2>')
    assert "Both represent all of New York" in html
    assert f"By district, 1–{NY_OVERVIEW['districts_expected']}" in html
    assert "<details>" not in _section(html, '<section class="house"')


@pytest.mark.asyncio
async def test_lowercase_code_renders_the_same_page():
    response = await _get("/state?code=ny")
    assert response.status_code == 200
    assert 'data-state="NY"' in response.text


@pytest.mark.asyncio
async def test_district_url_shows_your_representatives_first():
    house4 = [m["bioguideId"] for m in NY_OVERVIEW["house"] if m.get("district") == 4]
    assert house4 == ["G000602"]
    response = await _get("/state?code=NY&district=4")
    assert response.status_code == 200
    html = response.text
    assert "<h1>Your representatives</h1>" in html
    assert "New York, District 4 · " in html
    assert "Remember District 4 as mine</button>" in html
    yours = _section(html, '<section class="yours"')
    for member in NY_OVERVIEW["senators"]:
        assert f'data-bioguide="{member["bioguideId"]}"' in yours
        assert html.count(f'data-bioguide="{member["bioguideId"]}"') == 1
    assert 'data-bioguide="G000602"' in yours
    assert '<section class="senate"' not in html
    expected = NY_OVERVIEW["districts_expected"]
    assert f"<details><summary>All {expected} New York House districts</summary>" in html


@pytest.mark.asyncio
async def test_vacant_district_is_named_with_a_correction_link():
    assert not [m for m in NY_OVERVIEW["house"] if m.get("district") == 3]
    response = await _get("/state?code=NY&district=3")
    yours = _section(response.text, '<section class="yours"')
    assert "District 3 — vacant in our data</span> · <button" in yours
    assert "data-feedback-open>Tell us if this is wrong</button>" in yours


@pytest.mark.asyncio
@pytest.mark.parametrize("district", ["40", "0"])
async def test_out_of_range_district_is_named_above_the_roster(district):
    response = await _get(f"/state?code=NY&district={district}")
    assert response.status_code == 200
    assert f"We don't have a District {district} in New York" in response.text
    assert "<h1>New York's representatives</h1>" in response.text


@pytest.mark.asyncio
async def test_non_numeric_district_is_ignored():
    response = await _get("/state?code=NY&district=abc")
    assert response.status_code == 200
    assert "<h1>New York's representatives</h1>" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["NY", "CA"])
@pytest.mark.parametrize("junk", ["%C2%B2", "%D9%A3", "%E2%91%A0"])   # "²", Arabic-Indic 3, "①"
async def test_non_ascii_digit_district_is_ignored_like_any_junk(code, junk):
    """"²".isdigit() is True but int("²") raises: the district parse must treat it as junk, not 500."""
    plain = await _get(f"/state?code={code}")
    other = await _get(f"/state?code={code}&district=abc")
    response = await _get(f"/state?code={code}&district={junk}")
    assert response.status_code == other.status_code == plain.status_code
    assert response.text == other.text == plain.text


@pytest.mark.asyncio
async def test_state_page_reads_no_member_vote_files():
    with patch.object(DataService, "get_member_votes", side_effect=AssertionError("request-path scan")):
        response = await _get("/state?code=NY&district=4")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_render_failure_shows_the_error_state_with_the_page_h1():
    # Spec §4 "Error state": the masthead, the page's own H1, the one sentence, 503 (no-store).
    with patch("app.render.render_state_page", side_effect=RuntimeError("malformed overview")):
        response = await _get("/state?code=NY&district=4")
    assert response.status_code == 503
    assert "<h1>Your representatives</h1>" in response.text
    assert "We couldn't load this page right now." in response.text
    assert '<header class="masthead' in response.text


# --- shell and thin enhancers ---

STATE_SHELL = (STATIC / "state.html").read_text()
INDEX_SHELL = (STATIC / "index.html").read_text()


def _chrome(markup: str) -> tuple[str, str]:
    markup = markup.replace(' aria-current="page"', "")
    header = re.search(r'<header\b[^>]*class="masthead[^"]*".*?</header>', markup, re.DOTALL).group(0)
    footer = re.search(r'<footer\b[^>]*class="site-footer[^"]*".*?</footer>', markup, re.DOTALL).group(0)
    return header, footer


def test_state_shell_contract():
    assert re.search(r"<title>[^<]+</title>", STATE_SHELL)
    assert "</head>" in STATE_SHELL
    assert '<main id="main-content" tabindex="-1"><!--content--></main>' in STATE_SHELL
    assert "/static/css/site.css?v=" in STATE_SHELL
    assert "styles.css" not in STATE_SHELL and "broadsheet.css" not in STATE_SHELL
    assert STATE_SHELL.index("/static/js/site.js?v=") < STATE_SHELL.index("/static/js/state.js?v=")
    assert STATE_SHELL.index("/static/js/state.js?v=") < STATE_SHELL.index("/static/js/feedback.js?v=")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", STATE_SHELL)
    assert not re.search(r"\son[a-z]+\s*=", STATE_SHELL)
    assert '<dialog id="feedback-modal"' in STATE_SHELL
    assert 'id="feedback-open"' in STATE_SHELL
    assert 'id="data-freshness"' in STATE_SHELL


def test_state_shell_chrome_matches_the_home_shell():
    assert _chrome(STATE_SHELL) == _chrome(INDEX_SHELL)


def test_state_js_is_a_thin_enhancer():
    js = (STATIC / "js" / "state.js").read_text()
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js
    assert "document.title" not in js
    # The reveal is site.js initPartyToggle() over the toggle's data-party-url (T2.3); the
    # feedback triggers are feedback.js's (T2.4); cv-home goes through site.js readHome().
    assert "initPartyToggle()" in js
    assert "fetch(" not in js and "/overview" not in js
    assert "rememberedLine(" in js and "readHome()" in js
    for duplicate in ("function revealParty", "function hideParty", "function initFeedbackTriggers",
                      "function readRememberedHome", "localStorage", "getElementById('feedback-open')"):
        assert duplicate not in js
    for retired in ("support_rate", "participation", "aggregate", "narrative"):
        assert retired not in js


def test_home_js_renders_your_representatives_from_the_overview():
    js = (STATIC / "js" / "app.js").read_text()
    assert "function initYourRepresentatives" in js
    assert "initYourRepresentatives();" in js
    assert "remembered from your last visit" in js
    assert "Remembered from your last visit: " in js
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js
    # Same component as the delegation page (§4.1 m4): site.js personRow, not a copy.
    assert "personRow(" in js and "readHome()" in js
    for duplicate in ("function homePersonRow", "function homeSignalLine", "function readRememberedHome",
                      "HOME_STATE_NAMES", "function focusHomeFinder"):
        assert duplicate not in js
    # Mounted in T3.2's #home-reps below the finder, never next to the form (no fold shift).
    assert "getElementById('home-reps')" in js
    assert ".after(" not in js
