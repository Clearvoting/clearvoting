"""Tests for the homepage redesign: state counts, latest vote, bill plain-language
enrichment, and the notify signup endpoint."""
import json
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.limiter import limiter
from app import render
from app.services.data_service import DataService

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


async def _get(path):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    _clear_data_service_cache()
    return response


# --- Member counts ---

def test_member_counts():
    # Real synced members per state — fixtures hold FL x2, NY x4, TX x1.
    assert DataService(FIXTURES).get_member_counts() == {"FL": 2, "NY": 4, "TX": 1}


# --- Latest vote ---

def _bill_id(bill: dict) -> str:
    return f"{bill['congress']}-{str(bill['type']).lower()}-{bill['number']}"


@pytest.mark.asyncio
async def test_latest_vote_is_the_index_hero():
    index = json.loads((FIXTURES / "votes_index.json").read_text())
    held = {_bill_id(b) for b in json.loads((FIXTURES / "bills.json").read_text())["bills"]}
    # F02 rule recomputed from the fixture index: newest date, decisive first within a day,
    # vote number last; only roll calls whose document is a bill we hold.
    candidates = []
    for key, rc in index["roll_calls"].items():
        parsed = DataService._parse_bill_document(rc.get("document") or "")
        congress = int(key.split("/")[1].split("_")[0])
        if parsed and f"{congress}-{parsed[0]}-{parsed[1]}" in held:
            candidates.append(((rc["date"][:10], rc.get("class") == "D", int(key.rsplit("_", 1)[1])), key))
    expected = max(candidates)[1]
    assert index["latest"] == expected

    response = await _get("/api/votes/latest")
    assert response.status_code == 200
    data = response.json()
    rc = index["roll_calls"][expected]
    assert data["rc"] == expected
    assert data["chamber"] == ("Senate" if expected.startswith("senate/") else "House")
    assert data["date_iso"] == rc["date"][:10]
    assert data["date"] == render.format_date(rc["date"][:10])
    assert data["counts"] == rc["counts"]
    assert data["plain_question"] == rc["plain"]
    assert data["state_tallies"] == rc["tallies"]
    assert data["outcome"] == data["seal"] == render.result_phrase(rc, data["chamber"])
    parsed = DataService._parse_bill_document(rc["document"])
    assert (data["bill"]["type"], data["bill"]["number"]) == parsed
    bill_id = f"{data['bill']['congress']}-{parsed[0]}-{parsed[1]}"
    summary = json.loads((FIXTURES / "ai_summaries.json").read_text()).get(bill_id) or {}
    displayable = bool(summary) and summary.get("needs_review") is not True
    assert data["has_summary"] == bool(displayable and summary.get("one_liner"))
    assert data["one_liner"] == (summary["one_liner"] if data["has_summary"] else None)
    for row in data["covered"].values():
        assert set(row) == {"name", "state", "district", "chamber", "position", "relation"}
    assert '"party' not in response.text


# --- Bills plain-language enrichment ---

@pytest.mark.asyncio
async def test_bills_include_plain_language_fields():
    response = await _get("/api/bills?limit=50")
    assert response.status_code == 200
    bills = response.json()["bills"]
    assert bills, "fixture should return bills"
    summaries = json.loads((FIXTURES / "ai_summaries.json").read_text())
    for bill in bills:
        summary = summaries.get(_bill_id(bill)) or {}
        displayable = bool(summary) and summary.get("needs_review") is not True
        # Nullable: missing and withheld summaries both read None (spec §4.1 m5, §2.5 C)
        assert bill["one_liner"] == ((summary.get("one_liner") or None) if displayable else None)
        assert bill["issue_categories"] == ((summary.get("issue_categories") or []) if displayable else [])
        assert isinstance(bill["provisions"], list)
        assert "derived_status" in bill and bill["derived_status"]
        assert "activity_date" in bill


@pytest.mark.asyncio
async def test_summarized_only_excludes_bills_without_one_liner():
    response = await _get("/api/bills?summarized_only=true")
    assert response.status_code == 200
    bills = response.json()["bills"]
    # Every returned bill must carry a usable plain-language headline.
    assert all(b["one_liner"] for b in bills)


# --- Notify signup ---

@pytest.fixture(autouse=True)
def _use_tmp_notify_file(tmp_path):
    tmp_file = tmp_path / "notify_signups.jsonl"
    unavailable_sheets = MagicMock()
    unavailable_sheets.is_available = False
    limiter.reset()
    with patch("app.routers.notify.NOTIFY_FILE", tmp_file), \
         patch("app.routers.notify._sheets", unavailable_sheets):
        yield tmp_file


async def _post_notify(payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/notify", json=payload)


@pytest.mark.asyncio
async def test_notify_accepts_valid_email(_use_tmp_notify_file):
    response = await _post_notify({"email": "voter@example.com", "state": "OH"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    lines = _use_tmp_notify_file.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["email"] == "voter@example.com"
    assert entry["state"] == "OH"
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_notify_rejects_bad_email():
    response = await _post_notify({"email": "not-an-email"})
    assert response.status_code == 422


# --- Server-rendered home (plan T3.3, spec §4.1) ---

@pytest.mark.asyncio
async def test_home_renders_lead_card_and_record_in_the_html():
    response = await _get("/")
    assert response.status_code == 200
    html = response.text
    assert "<!--content-->" not in html and "<!--edition-->" not in html
    assert '<p class="kicker">An independent record of Congress</p>' in html
    assert '<h1 id="home-h1">See how your representatives vote.</h1>' in html
    assert '<form class="zip-form" id="find" method="get" action="/state">' in html
    assert '<h2 class="kicker" id="latest-vote-h">The latest vote</h2>' in html
    assert '<h2 id="record-h">What Congress voted on</h2>' in html
    assert '<header class="masthead">' in html and '<p class="edition">' in html
    assert '<a href="/#find" id="nav-mine">My representatives</a>' in html


@pytest.mark.asyncio
async def test_home_state_links_and_coverage_use_real_counts():
    counts = DataService(FIXTURES).get_member_counts()
    html = (await _get("/")).text
    for code, name in (("CA", "California"), ("FL", "Florida"), ("NY", "New York"), ("TX", "Texas")):
        label = f"{name} · {counts[code]}" if counts.get(code) else name
        assert f'<a class="state-link" href="/state?code={code}">{label}</a>' in html
    assert f"today — {sum(counts.values())} members and every bill that has had a roll-call vote" in html


@pytest.mark.asyncio
async def test_home_record_lists_the_newest_bills_regardless_of_summary():
    bills = DataService(FIXTURES).get_bills(limit=7)["bills"]
    html = (await _get("/")).text
    assert html.count('class="bill-row"') == max(len(bills) - 1, 0)
    lead_code = render.format_bill_code(str(bills[0]["type"]).lower(), bills[0]["number"])
    assert f'<p class="kicker">{lead_code} · ' in html
    assert "<b>&" not in html  # hostile fixture titles arrive escaped


@pytest.mark.asyncio
async def test_home_degrades_by_module_when_data_is_missing():
    with patch("app.services.data_service.DataService.get_latest_vote", return_value=None), \
         patch("app.services.data_service.DataService.get_bills", side_effect=OSError("index missing")):
        response = await _get("/")
    assert response.status_code == 200
    assert '<h1 id="home-h1">See how your representatives vote.</h1>' in response.text
    assert "The latest vote isn't available right now." in response.text
    assert "We couldn't load recent bills right now." in response.text


@pytest.mark.asyncio
async def test_home_error_state_when_the_lead_cannot_render():
    # §4 common: a lead dependency failing is a page failure, not a module one.
    with patch("app.services.data_service.DataService.get_member_counts",
               side_effect=OSError("members.json missing")):
        response = await _get("/")
    assert response.status_code == 503
    assert "<h1>See how your representatives vote.</h1>" in response.text
    assert render.PAGE_ERROR_SENTENCE in response.text
    assert 'id="record-h"' not in response.text


@pytest.mark.asyncio
async def test_every_internal_link_on_home_resolves():
    """§10.3: no commit links to a page that does not exist yet (footer, notify Privacy →,
    state chips, Record rows, the card link)."""
    html = (await _get("/")).text
    paths = sorted({p.replace("&amp;", "&") for p in re.findall(r'href="(/[^"#]*)', html)
                    if not p.startswith("/static/")})
    assert "/about" in paths
    for path in paths:
        assert (await _get(path)).status_code in (200, 302), path


@pytest.mark.asyncio
async def test_home_heading_outline_follows_the_spec():
    """§8 item 2: h1, then h2 "The latest vote", "What Congress voted on", the latest-summary
    block when it renders, "Browse all bills by topic"; the feedback dialog's h2 sits after
    the footer. "Your representatives" is JS-only and absent from the server HTML."""
    html = (await _get("/")).text
    found = re.findall(r"<(h[1-6])\b[^>]*>(.*?)</\1>", html, re.S)
    levels = [level for level, _ in found]
    texts = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip() for _, inner in found]
    latest = [t for t in texts if t.startswith("Most recent plain-English summary")]
    expected = (["See how your representatives vote.", "The latest vote", "What Congress voted on"]
                + latest + ["Browse all bills by topic →", "Send feedback"])
    assert texts == expected
    assert levels == ["h1"] + ["h2"] * (len(expected) - 1)


@pytest.mark.asyncio
async def test_home_drops_the_retired_modules():
    html = (await _get("/")).text
    for gone in ('id="state-grid"', 'id="delegation"', "Updated weekly", "aria-live",
                 "styles.css", "broadsheet.css", "viz.js", "notify-reveal"):
        assert gone not in html


@pytest.mark.asyncio
async def test_home_footer_freshness_is_server_filled():
    metadata = json.loads((FIXTURES / "sync_metadata.json").read_text())
    html = (await _get("/")).text
    synced = render.format_date(metadata["last_sync"][:10])
    assert f'<span id="data-freshness"> · Synced {synced}</span>' in html


@pytest.mark.asyncio
@pytest.mark.parametrize("path, shell", [
    ("/state?code=FL", "state.html"), ("/member?id=S001217", "member.html"),
    ("/bill?congress=119&type=hr&number=1", "bill.html"), ("/about", "about.html"),
])
async def test_other_pages_serve_their_own_shell(path, shell):
    """§10.3: each page switches stylesheet in its own commit. The page links exactly the
    stylesheets its shell on disk links, so this holds unchanged when T4.2, T5.1, T6.3 and
    T7.4 move those shells to site.css (today: still styles.css)."""
    on_disk = (Path(__file__).parent.parent / "static" / shell).read_text()
    response = await _get(path)
    assert response.status_code == 200
    for sheet in ("/static/css/styles.css", "/static/css/broadsheet.css", "/static/css/site.css"):
        assert (sheet in response.text) == (sheet in on_disk), sheet
    assert "/static/css/" in response.text
