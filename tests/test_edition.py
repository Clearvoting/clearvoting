"""Edition line (spec §7.4), the SSR markers in _serve_html (§9.1), the page error
state (§4 common) and the shared blocks several pages render (§3.2 ZIP form, state
links, §4.1 m2 notify disclosure)."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

from app import main, render

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REPO = Path(__file__).parent.parent
LA = ZoneInfo("America/Los_Angeles")
NEW_YORK = ZoneInfo("America/New_York")
HONOLULU = ZoneInfo("Pacific/Honolulu")
SEP_22 = datetime(2026, 9, 22, 12, 0, tzinfo=LA)


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- Edition line (§7.4) ---

def test_edition_matches_the_spec_example():
    html = render.render_edition("2026-09-05T06:00:00Z", "2026-09-03", SEP_22)
    assert html == (
        '<p class="edition"><span>Data synced September 5, 2026</span>'
        '<span class="edition-mid"> · Latest roll call September 3</span>'
        '<span> · Election Day is Tuesday, November 3 — 42 days away</span></p>'
    )


def test_countdown_on_november_2_is_one_day():
    html = render.render_edition(None, None, datetime(2026, 11, 2, 12, 0, tzinfo=LA))
    assert "Election Day is Tuesday, November 3 — 1 day away" in html


@pytest.mark.parametrize("now", [
    datetime(2026, 11, 3, 0, 0, tzinfo=HONOLULU),   # 05:00 in New York
    datetime(2026, 11, 3, 12, 0, tzinfo=LA),
    datetime(2026, 11, 3, 20, 59, tzinfo=LA),       # 23:59 in New York, after California polls close
])
def test_election_day_is_today_while_new_york_to_honolulu_share_the_date(now):
    html = render.render_edition(None, None, now)
    assert "<span>Election Day is today</span>" in html
    assert "away" not in html


# G1-024: one cached line serves every reader. While New York, Los Angeles and Honolulu are on
# different dates, any count or "today" is false somewhere, so the line names the date alone.
@pytest.mark.parametrize("now", [
    datetime(2026, 10, 22, 0, 30, tzinfo=NEW_YORK),  # the Pacific count (13) is 12 by Eastern time
    datetime(2026, 11, 3, 0, 30, tzinfo=NEW_YORK),   # was "1 day away" on Election Day
    datetime(2026, 11, 3, 2, 59, tzinfo=NEW_YORK),
    datetime(2026, 11, 2, 22, 30, tzinfo=HONOLULU),  # was "Election Day is today" on Nov 2
    datetime(2026, 11, 2, 23, 30, tzinfo=ZoneInfo("America/Anchorage")),
    datetime(2026, 11, 3, 21, 0, tzinfo=LA),         # midnight in New York
    datetime(2026, 11, 4, 0, 0, tzinfo=LA),          # 22:00 on Nov 3 in Honolulu
])
def test_countdown_names_only_the_date_while_the_zones_disagree(now):
    html = render.render_edition(None, None, now)
    assert html == '<p class="edition"><span>Election Day is Tuesday, November 3</span></p>'


def test_countdown_converts_utc_to_each_zone():
    def line(hour, minute, day):
        return render.render_edition(None, None, datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc))
    # 10:00 UTC on November 3 is midnight in Honolulu: every zone is on Election Day.
    assert "today" not in line(9, 59, 3) and "Election Day is Tuesday, November 3" in line(9, 59, 3)
    assert "Election Day is today" in line(10, 0, 3)
    # 05:00 UTC on November 4 is midnight in New York (EST after November 1).
    assert "Election Day is today" in line(4, 59, 4)
    assert "today" not in line(5, 0, 4) and "Election Day is Tuesday, November 3" in line(5, 0, 4)
    # 10:00 UTC on November 4 is midnight in Honolulu: the line is omitted.
    assert "Election Day is Tuesday, November 3" in line(9, 59, 4)
    assert "Election Day" not in line(10, 0, 4)


def test_election_line_omitted_once_honolulu_reaches_november_4():
    html = render.render_edition("2026-11-02T06:00:00Z", None, datetime(2026, 11, 4, 0, 0, tzinfo=HONOLULU))
    assert html == '<p class="edition"><span>Data synced November 2, 2026</span></p>'


def test_edition_without_sync_has_no_leading_separator():
    html = render.render_edition(None, None, SEP_22)
    assert html == '<p class="edition"><span>Election Day is Tuesday, November 3 — 42 days away</span></p>'


def test_edition_is_empty_when_nothing_is_known():
    assert render.render_edition(None, None, datetime(2026, 11, 10, 12, 0, tzinfo=LA)) == ""


@pytest.mark.parametrize("last_sync", [20261001, 2026.5, ["2026-10-01"], {"at": "2026-10-01"}, "garbage"])
def test_edition_drops_a_last_sync_that_is_not_a_date(last_sync):
    # F067: an int last_sync raised in format_date and 500ed every page, 404s included; a
    # string that is not a date printed as "Data synced garbage". Both now drop the part.
    html = render.render_edition(last_sync, "2026-09-03", SEP_22)
    assert "Data synced" not in html
    assert "Latest roll call September 3" in html


def test_edition_failure_drops_only_the_line():
    with _patch_data_dir(), patch("app.render.render_edition", side_effect=RuntimeError("boom")):
        assert main._edition_html() == ""


@pytest.mark.parametrize("metadata", ['{"last_sync": 20261001}', "[]", '"2026-10-01"', "{not json"])
def test_pages_survive_a_malformed_sync_metadata_file(tmp_path, metadata):
    from fastapi.testclient import TestClient
    for entry in FIXTURES.iterdir():
        if entry.name != "sync_metadata.json":
            (tmp_path / entry.name).symlink_to(entry)
    (tmp_path / "sync_metadata.json").write_text(metadata)
    client = TestClient(main.app)
    with patch("app.dependencies.get_data_dir", return_value=tmp_path):
        for path, status in (("/about", 200), ("/privacy", 200), ("/state?code=NY", 200),
                             ("/no-such-page", 404), ("/api/health", 200)):
            response = client.get(path)
            assert response.status_code == status, path
            assert "Data synced" not in response.text


def test_countdown_without_a_tz_database(monkeypatch):
    def _missing(name):
        raise ZoneInfoNotFoundError(name)

    hours = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(366 * 24)]
    real = [[render._zone_today(t, zone) for zone in render._EDITION_ZONES] for t in hours]
    monkeypatch.setattr(render, "ZoneInfo", _missing)
    # The fallback's US DST rule gives each zone's date at every hour of 2026, both switches included.
    assert [[render._zone_today(t, zone) for zone in render._EDITION_ZONES] for t in hours] == real
    assert "Election Day is today" in render.render_edition(
        None, None, datetime(2026, 11, 4, 4, 59, tzinfo=timezone.utc))
    assert "Election Day" not in render.render_edition(
        None, None, datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc))
    # September is EDT (UTC-4): 03:59 UTC on Sep 23 is still Sep 22 in New York.
    assert "42 days away" in render.render_edition(
        None, None, datetime(2026, 9, 23, 3, 59, tzinfo=timezone.utc))
    assert "away" not in render.render_edition(
        None, None, datetime(2026, 9, 23, 4, 0, tzinfo=timezone.utc))


def test_election_day_matches_the_sanctioned_seats_file():
    seats = json.loads((REPO / "data" / "synced" / "senate_2026.json").read_text())
    assert seats["election_day"] == render.ELECTION_DAY.isoformat()


# --- After Election Day: one request clock for the edition line and the ballot copy (F066) ---

@pytest.mark.parametrize("now, up, today", [
    (datetime(2026, 11, 2, 12, 0, tzinfo=LA), True, False),
    (datetime(2026, 11, 3, 12, 0, tzinfo=LA), True, True),
    (datetime(2026, 11, 3, 23, 59, tzinfo=LA), True, False),   # November 4 in New York (G1-024)
    (datetime(2026, 11, 4, 0, 0, tzinfo=LA), False, False),
    (datetime(2026, 11, 20, 12, 0, tzinfo=LA), False, False),
])
def test_pages_stop_announcing_the_ballot_after_election_day(now, up, today):
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    with _patch_data_dir(), patch("app.main._now", return_value=now):
        _clear_data_service_cache()
        member = client.get("/member?id=G000602").text
        state = client.get("/state?code=NY").text
        overview = client.get("/api/members/NY/overview").json()
        methodology = client.get("/methodology").text
    _clear_data_service_cache()
    assert ("Election Day is today" in member) is today
    assert ("This seat is on the ballot Nov 3, 2026" in member) is up
    assert ("Seat up Nov 3" in state) is up
    assert ("seal--ballot" in state) is up
    gillen = next(m for m in overview["house"] if m["bioguideId"] == "G000602")
    assert gillen["seat_seal"] == ("Seat up Nov 3" if up else "")
    verb = "is" if up else "was"
    assert f"Every House seat {verb} on the ballot on November 3, 2026." in methodology


# --- Error state (§4 common) ---

def test_render_error_uses_the_spec_sentence():
    html = render.render_error("Your representatives")
    assert "<h1>Your representatives</h1>" in html
    assert ("We couldn't load this page right now. Please try again in a moment, "
            "or use <em>Report an error</em> below to tell us.") in html
    assert "Congress.gov" not in html


# --- ZIP form (§3.2) ---

def test_zip_form_is_a_plain_get_to_state():
    html = render.render_zip_form()
    assert '<form class="zip-form" id="find" method="get" action="/state">' in html
    assert '<label class="zip-label" for="zip">Where do you live?</label>' in html
    for attr in ('id="zip"', 'name="zip"', 'inputmode="numeric"', 'autocomplete="postal-code"',
                 'maxlength="10"', " required", r'pattern="\s*[0-9]{5}([\-\s]?[0-9]{4})?\s*"'):
        assert attr in html
    assert '<button class="btn" type="submit">Find my representatives</button>' in html
    assert "aria-invalid" not in html
    assert "value=" not in html


def test_zip_form_says_it_wants_a_zip_when_the_label_does_not():
    # QA 2026-09-26: "Where do you live?" alone gave no hint that the field wants a ZIP, and a
    # typed city met only the browser's generic "match the requested format" message.
    html = render.render_zip_form()
    assert ('<label class="zip-label" for="zip">Where do you live?</label>'
            '<p class="meta zip-hint" id="zip-hint">5-digit ZIP code</p>') in html
    assert 'aria-describedby="zip-hint"' in html
    assert 'title="A ZIP code is five digits."' in html
    # A label that already names the ZIP needs no hint (bill page, delegation footer).
    labelled = render.render_zip_form(form_id="reps-zip-form",
                                      label="Enter your ZIP to see how your representatives voted")
    assert "zip-hint" not in labelled
    assert "aria-describedby" not in labelled
    assert 'title="A ZIP code is five digits."' in labelled


def test_zip_form_error_replaces_the_hint_as_the_description():
    html = render.render_zip_form(compact=True, value="Brooklyn", error="A ZIP code is five digits.",
                                  form_id="zip-top")
    assert 'aria-describedby="zip-top-field-error" aria-invalid="true"' in html
    assert "zip-top-field-hint" not in html.split("<input", 1)[1].split(">", 1)[0]
    assert '<p class="meta zip-hint" id="zip-top-field-hint">5-digit ZIP code</p>' in html


def test_zip_form_error_keeps_the_typed_value_and_describes_the_field():
    html = render.render_zip_form(compact=True, value="abc", error="A ZIP code is five digits.",
                                  form_id="state-zip")
    assert '<form class="zip-form zip-form--compact" id="state-zip" method="get" action="/state">' in html
    assert 'id="state-zip-field"' in html
    assert 'value="abc"' in html
    assert 'aria-describedby="state-zip-field-error" aria-invalid="true"' in html
    assert '<p class="field-error" id="state-zip-field-error">A ZIP code is five digits.</p>' in html


# --- State links (§4.1 fold) ---

def test_state_links_show_real_counts_in_fixed_order():
    html = render.render_state_links({"CA": 54, "FL": 29, "NY": 28, "TX": 39})
    assert re.findall(r'href="/state\?code=([A-Z]{2})"', html) == ["CA", "FL", "NY", "TX"]
    assert '<li><a class="state-link" href="/state?code=NY">New York · 28</a></li>' in html
    assert html.startswith('<ul class="state-links">')


def test_state_link_without_a_count_shows_the_name_only():
    html = render.render_state_links({"NY": 1})
    assert '<a class="state-link" href="/state?code=CA">California</a>' in html
    assert '<a class="state-link" href="/state?code=NY">New York · 1</a>' in html


# --- Notify disclosure (§4.1 m2) ---

def test_notify_disclosure_lists_only_uncovered_states_and_dc():
    html = render.render_notify_disclosure()
    values = re.findall(r'<option value="([A-Z]{2})">', html)
    assert len(values) == 47 == len(render.NOTIFY_STATES)
    assert "DC" in values
    assert not {"CA", "FL", "NY", "TX"} & set(values)
    assert '<option value="">Choose your state</option>' in html
    assert "<summary>Somewhere else?</summary>" in html
    assert '<select id="notify-state" name="state" required>' in html
    assert 'id="notify-email" name="email" type="email" autocomplete="email"' in html
    assert '<button class="btn" type="submit" id="notify-submit">Notify me</button>' in html
    assert ('<p class="meta">We store your email, your state and the time you signed up. '
            '<a href="/privacy">Privacy →</a></p>') in html
    assert '<p class="notify-status" id="notify-status" role="status" tabindex="-1"></p>' in html
    assert '<noscript><p class="meta">Signing up needs JavaScript.</p></noscript>' in html


def test_notify_form_cannot_submit_without_js():
    html = render.render_notify_disclosure()
    form_tag = re.search(r"<form[^>]*>", html).group(0)
    assert "action=" not in form_tag and "method=" not in form_tag
    assert '<fieldset class="notify-fields" disabled>' in html


# --- _serve_html markers (§9.1) ---

SHELL = ('<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body>'
         '<header class="masthead"><!--edition--></header>'
         '<main id="main-content" tabindex="-1"><!--content--></main></body></html>')
META = {"title": "Test | ClearVoting", "description": "d", "url": "https://clearvoting.org/t"}


def _serve(tmp_path, filename, *args, **kwargs):
    with patch("app.main.static_dir", tmp_path), _patch_data_dir():
        _clear_data_service_cache()
        response = main._serve_html(filename, *args, **kwargs)
    _clear_data_service_cache()
    return response


def test_serve_html_fills_content_and_edition_markers(tmp_path):
    (tmp_path / "t.html").write_text(SHELL)
    content = '<p>Hello <a href="/static/x.css?v=1">x</a></p>'
    response = _serve(tmp_path, "t.html", META, content)
    html = response.body.decode()
    # Content goes in after the ?v= rewrite and the meta injection, untouched.
    assert f'<main id="main-content" tabindex="-1">{content}</main>' in html
    assert '<header class="masthead"><p class="edition">' in html
    assert "<!--content-->" not in html and "<!--edition-->" not in html
    assert "<title>Test | ClearVoting</title>" in html
    assert response.status_code == 200


def test_serve_html_passes_the_status_code(tmp_path):
    (tmp_path / "t.html").write_text(SHELL)
    assert _serve(tmp_path, "t.html", META, "<p>x</p>", status_code=503).status_code == 503


def test_shell_without_markers_is_unaffected(tmp_path):
    (tmp_path / "plain.html").write_text(
        "<html><head><title>P</title></head><body><main>x</main></body></html>")
    html = _serve(tmp_path, "plain.html", META).body.decode()
    assert '<p class="edition">' not in html
    assert "<main>x</main>" in html


# --- Page-level error fallback (§4 common) ---

def test_page_content_returns_rendered_html():
    assert main._page_content(lambda: "<p>ok</p>", META) == ("<p>ok</p>", 200)


def test_page_content_falls_back_to_the_error_state():
    def boom():
        raise OSError("votes_index.json missing")

    html, status = main._page_content(boom, {**META, "h1": "Your representatives"})
    assert status == 503
    assert "<h1>Your representatives</h1>" in html
    assert render.PAGE_ERROR_SENTENCE in html


def test_page_content_h1_defaults_to_the_title_without_the_site_name():
    html, _ = main._page_content(lambda: 1 / 0, META)
    assert "<h1>Test</h1>" in html
