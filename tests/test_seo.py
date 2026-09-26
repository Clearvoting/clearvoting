import json
import re
import struct
from html import escape

import pytest
from unittest.mock import patch
from pathlib import Path
from defusedxml.ElementTree import fromstring as parse_xml
from httpx import AsyncClient, ASGITransport
from app.main import app, _inject_meta, _normalize_bill_params, _og_title

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
STATIC = Path(__file__).parent.parent / "static"
SITE = "https://clearvoting.org"


def _fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def _patch_data_dir():
    """Patch data dir to use test fixtures and reset the DataService singleton."""
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


# --- Member page meta ---

@pytest.mark.asyncio
async def test_member_page_meta_injected():
    response = await _get("/member?id=S001217")
    assert response.status_code == 200
    html = response.text
    assert "<title>Rick Scott (FL) — Voting Record | ClearVoting</title>" in html
    assert '<meta name="description" content="Rick Scott, Senate member from Florida.' in html
    assert '<meta property="og:title" content="Rick Scott (FL) — Voting Record">' in html
    assert '<meta property="og:description"' in html
    assert '<meta property="og:type" content="profile">' in html
    assert f'<meta property="og:url" content="{SITE}/member?id=S001217">' in html
    assert '<meta name="twitter:card" content="summary_large_image">' in html
    assert f'<link rel="canonical" href="{SITE}/member?id=S001217">' in html
    assert html.count("<title>") == 1


@pytest.mark.asyncio
async def test_member_page_title_uses_display_name():
    # members.json has no directOrderName; the title is built from "Schumer, Charles E.".
    response = await _get("/member?id=S000148")
    assert response.status_code == 200
    assert "<title>Charles E. Schumer (NY) — Voting Record | ClearVoting</title>" in response.text


@pytest.mark.asyncio
async def test_member_page_unknown_id_is_404():
    response = await _get("/member?id=X999999")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_member_page_no_id_is_404():
    response = await _get("/member")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_member_title_uses_the_display_name_and_canonical_strips_params():
    response = await _get("/member?id=s000148&page=2&topic=Health")
    assert response.status_code == 200
    html = response.text
    assert "<title>Charles E. Schumer (NY) — Voting Record | ClearVoting</title>" in html
    assert '<link rel="canonical" href="https://clearvoting.org/member?id=S000148">' in html


# --- Bill page meta ---

@pytest.mark.asyncio
async def test_bill_page_meta_injected():
    response = await _get("/bill?congress=119&type=hr&number=1")
    assert response.status_code == 200
    html = response.text
    entry = json.loads((FIXTURES / "ai_summaries.json").read_text()).get("119-hr-1") or {}
    if entry.get("one_liner") and not entry.get("needs_review"):
        headline = entry["one_liner"]
    else:
        headline = "One Big Beautiful Bill Act"
    assert f"<title>{escape(f'H.R. 1 — {headline} | ClearVoting')}</title>" in html
    assert '<meta name="description" content="One Big Beautiful Bill Act">' in html
    assert f'<meta property="og:title" content="{escape(_og_title(f"H.R. 1 — {headline} | ClearVoting"))}">' in html
    # Query-string ampersands must be escaped inside HTML attributes
    assert ('<link rel="canonical" href="https://clearvoting.org/bill'
            '?congress=119&amp;type=hr&amp;number=1">') in html


def test_bill_meta_caps_official_title_at_70_and_og_title_at_90():
    from app.main import _bill_meta
    title = " ".join(["Providing for consideration of the bill"] * 10)
    meta = _bill_meta({"bill_type": "hres", "number": 1499, "congress": 119, "title": title,
                       "has_summary": False, "one_liner": None})
    headline = meta["title"].removeprefix("H.Res. 1499 — ").removesuffix(" | ClearVoting")
    assert headline.endswith("…") and len(headline) <= 71
    assert "og_title" not in meta  # _inject_meta derives it (spec §9.2)
    og_title = _og_title(meta["title"])
    assert len(og_title) <= 90
    assert "ClearVoting" not in og_title
    assert meta["description"] == title
    assert meta["url"] == "https://clearvoting.org/bill?congress=119&type=hres&number=1499"


@pytest.mark.asyncio
async def test_bill_page_unknown_bill_is_404():
    response = await _get("/bill?congress=119&type=hr&number=999999")
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/bill?congress=abc&type=hr&number=xyz",
    "/bill?congress=119&type=zz&number=1",
    "/bill?congress=0&type=hr&number=1",
    "/bill",
])
async def test_bill_page_garbage_params_are_404(path):
    response = await _get(path)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bill_page_type_is_case_normalized():
    response = await _get("/bill?congress=119&type=HR&number=1")
    assert response.status_code == 200
    assert '?congress=119&amp;type=hr&amp;number=1">' in response.text


# --- State page meta ---

@pytest.mark.asyncio
async def test_state_page_meta_injected():
    response = await _get("/state?code=NY")
    assert response.status_code == 200
    html = response.text
    ny_count = sum(1 for m in _fixture("members.json")["members"] if m.get("stateCode") == "NY")
    assert "<title>New York&#x27;s Representatives — Voting Records | ClearVoting</title>" in html
    assert '<meta property="og:title" content="New York&#x27;s Representatives — Voting Records">' in html
    assert f"{ny_count} members of Congress from New York" in html
    assert f'<link rel="canonical" href="{SITE}/state?code=NY">' in html


@pytest.mark.asyncio
async def test_state_page_unknown_code_is_404():
    for path in ("/state?code=ZZ", "/state?code=OH", "/state?code=N1"):
        response = await _get(path)
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_state_page_lowercase_code_is_normalized():
    response = await _get("/state?code=fl")
    assert response.status_code == 200
    assert '<link rel="canonical" href="https://clearvoting.org/state?code=FL">' in response.text


# --- Home and about static og tags ---

@pytest.mark.asyncio
async def test_home_page_has_og_tags_and_canonical():
    response = await _get("/")
    assert response.status_code == 200
    html = response.text
    assert '<meta property="og:title"' in html
    assert '<meta property="og:site_name" content="ClearVoting">' in html
    assert '<link rel="canonical" href="https://clearvoting.org/">' in html


@pytest.mark.asyncio
async def test_about_page_has_og_tags_and_canonical():
    response = await _get("/about")
    assert response.status_code == 200
    html = response.text
    assert '<meta property="og:title" content="About — ClearVoting">' in html
    assert '<link rel="canonical" href="https://clearvoting.org/about">' in html
    # Original static description tag is replaced, not duplicated
    assert html.count('<meta name="description"') == 1


# --- Sitemap ---

@pytest.mark.asyncio
async def test_sitemap_lists_trust_pages_and_per_url_lastmod():
    response = await _get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers["content-type"]
    root = parse_xml(response.text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries = {}
    for url in root.findall("sm:url", ns):
        lastmod = url.find("sm:lastmod", ns)
        entries[url.find("sm:loc", ns).text] = lastmod.text if lastmod is not None else None

    last_sync = _fixture("sync_metadata.json")["last_sync"][:10]
    assert entries[f"{SITE}/"] == last_sync
    assert entries[f"{SITE}/about"] == last_sync
    assert entries[f"{SITE}/methodology"] == last_sync
    assert f"{SITE}/privacy" in entries
    for code in ("CA", "FL", "NY", "TX"):
        assert f"{SITE}/state?code={code}" in entries
    assert f"{SITE}/member?id=S001217" in entries
    assert f"{SITE}/bill?congress=119&type=hr&number=1" in entries

    # Member lastmod = T1.6's latest_vote.date (newest decisive bill vote); none when null.
    ny = _fixture("state_overview/NY.json")
    assert entries[f"{SITE}/state?code=NY"] == ny["roster_as_of"][:10]
    for member in ny["senators"] + ny["house"]:
        latest = (member.get("latest_vote") or {}).get("date")
        assert entries[f"{SITE}/member?id={member['bioguideId']}"] == (latest[:10] if latest else None)

    index_bills = _fixture("votes_index.json")["bills"]
    checked = 0
    for bill in _fixture("bills.json")["bills"]:
        bill_type = str(bill["type"]).lower()
        entry = index_bills.get(f"{bill['congress']}-{bill_type}-{bill['number']}")
        if isinstance(entry, dict) and entry.get("activity_date"):
            loc = f"{SITE}/bill?congress={bill['congress']}&type={bill_type}&number={bill['number']}"
            assert entries[loc] == entry["activity_date"][:10]
            checked += 1
    assert checked >= 1

    for loc, lastmod in entries.items():
        assert lastmod is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod), loc
        assert "district=" not in loc and "zip=" not in loc


# --- robots.txt ---

@pytest.mark.asyncio
async def test_robots_txt():
    response = await _get("/robots.txt")
    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Sitemap: https://clearvoting.org/sitemap.xml" in response.text


# --- 404 handling ---

@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/no-such-page",
    "/member?id=X999999",
    "/member",
    "/member?id=not-an-id",
    "/bill",
    "/bill?congress=119&type=hr&number=999999",
    "/bill?congress=abc&type=hr&number=xyz",
    "/bill?congress=119&type=zz&number=1",
    "/bill?congress=0&type=hr&number=1",
    "/state?code=ZZ",
    "/state?code=OH",
    "/state?code=N1",
])
async def test_unknown_pages_are_real_404s_without_canonical(path):
    response = await _get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert 'rel="canonical"' not in html
    assert "og:url" not in html
    assert 'href="/"' in html
    assert html.count("<title>") == 1


@pytest.mark.asyncio
async def test_404_stays_json_for_api_paths():
    response = await _get("/api/no-such-endpoint")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}


# --- T8.1: og:title, _inject_meta keys, bill titles, state/finder canonicals, favicon, noindex ---

def test_og_title_drops_the_suffix_and_caps_at_90():
    assert _og_title("Charles E. Schumer (NY) — Voting Record | ClearVoting") == (
        "Charles E. Schumer (NY) — Voting Record"
    )
    assert _og_title("ClearVoting — See How Your Representatives Vote") == (
        "ClearVoting — See How Your Representatives Vote"
    )
    exactly_90 = "H.R. 1 — " + "x" * 81
    assert len(exactly_90) == 90
    assert _og_title(exactly_90 + " | ClearVoting") == exactly_90
    long_title = "H.R. 1 — " + "word " * 40 + "| ClearVoting"
    result = _og_title(long_title)
    assert len(result) <= 90
    assert result.endswith("…")
    assert "ClearVoting" not in result


def test_normalize_bill_params_follows_the_bill_route_rule():
    assert _normalize_bill_params("119", "HCONRES", "5") == (119, "hconres", 5)
    assert _normalize_bill_params(119, "hr", 1) == (119, "hr", 1)
    assert _normalize_bill_params("abc", "hr", "1") is None
    assert _normalize_bill_params("119", "zz", "1") is None
    assert _normalize_bill_params("119", "hr", "0") is None
    assert _normalize_bill_params("0", "hr", "1") is None
    assert _normalize_bill_params(None, None, None) is None


def test_inject_meta_image_canonical_and_h1_keys():
    shell = "<html><head><title>Old</title>\n</head><body><h1 class=\"err\">Old heading</h1></body></html>"
    html = _inject_meta(shell, {
        "title": "T | ClearVoting",
        "description": "D",
        "url": f"{SITE}/x",
        "image": {"path": "/static/og/member.png", "width": 1200, "height": 630,
                  "alt": "ClearVoting — Voting record"},
        "h1": "We don't have that page",
    })
    assert "<title>T | ClearVoting</title>" in html
    assert '<meta property="og:title" content="T">' in html
    assert f'<meta property="og:image" content="{SITE}/static/og/member.png">' in html
    assert '<meta property="og:image:width" content="1200">' in html
    assert '<meta property="og:image:height" content="630">' in html
    assert '<meta property="og:image:alt" content="ClearVoting — Voting record">' in html
    assert '<meta name="twitter:card" content="summary_large_image">' in html
    assert f'<link rel="canonical" href="{SITE}/x">' in html
    assert '<h1 class="err">We don&#x27;t have that page</h1>' in html

    bare = _inject_meta(shell, {"title": "T", "description": "D", "url": f"{SITE}/x", "canonical": False})
    assert 'rel="canonical"' not in bare
    assert "og:url" not in bare
    assert "og:image" not in bare
    assert '<meta name="twitter:card" content="summary">' in bare
    assert "<h1 class=\"err\">Old heading</h1>" in bare


def test_bill_title_prefers_the_displayable_one_liner():
    from app.main import _bill_meta
    official = "An Act to amend the Richard B. Russell National School Lunch Act"
    meta = _bill_meta({"bill_type": "hr", "number": 4795, "congress": 119, "title": official,
                       "has_summary": True, "one_liner": "Sets a national standard for school lunches"})
    assert meta["title"] == "H.R. 4795 — Sets a national standard for school lunches | ClearVoting"
    assert meta["description"] == official


@pytest.mark.asyncio
async def test_withheld_summary_never_reaches_the_title():
    summaries = _fixture("ai_summaries.json")
    bills = {
        f"{b['congress']}-{str(b['type']).lower()}-{b['number']}": b
        for b in _fixture("bills.json")["bills"]
    }
    withheld = [
        (key, entry["one_liner"]) for key, entry in summaries.items()
        if entry.get("needs_review") is True and entry.get("one_liner") and key in bills
    ]
    assert withheld, "fixture must hold a needs_review summary with a one_liner for a bill in bills.json (T1.1)"
    for key, one_liner in withheld:
        congress, bill_type, number = key.split("-")
        response = await _get(f"/bill?congress={congress}&type={bill_type}&number={number}")
        assert response.status_code == 200
        title = re.search(r"<title>(.*?)</title>", response.text).group(1)
        assert escape(one_liner) not in title


@pytest.mark.asyncio
async def test_bill_title_escapes_markup_characters():
    hostile = [b for b in _fixture("bills.json")["bills"] if "<b>" in str(b.get("title"))]
    assert hostile, "fixture must hold a bill titled with <b>&\"' characters (T1.1)"
    bill = hostile[0]
    response = await _get(
        f"/bill?congress={bill['congress']}&type={str(bill['type']).lower()}&number={bill['number']}"
    )
    assert response.status_code == 200
    title = re.search(r"<title>(.*?)</title>", response.text).group(1)
    assert "<b>" not in title
    assert "&lt;b&gt;" in title


@pytest.mark.asyncio
async def test_member_canonical_strips_every_additive_param():
    response = await _get("/member?id=s000148&page=2&topic=Health&position=no&plain=1")
    assert response.status_code == 200
    html = response.text
    assert f'<link rel="canonical" href="{SITE}/member?id=S000148">' in html
    assert f'<meta property="og:url" content="{SITE}/member?id=S000148">' in html


@pytest.mark.asyncio
async def test_state_canonical_uppercases_and_strips_district():
    response = await _get("/state?code=ny&district=4")
    assert response.status_code == 200
    assert "<title>New York&#x27;s Representatives — Voting Records | ClearVoting</title>" in response.text
    assert f'<link rel="canonical" href="{SITE}/state?code=NY">' in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/state", "/state?zip=abc", "/state?zip=44101"])
async def test_zip_finder_pages_have_no_canonical(path):
    response = await _get(path)
    assert response.status_code == 200
    html = response.text
    assert "<title>Find your representatives | ClearVoting</title>" in html
    assert 'rel="canonical"' not in html
    assert "og:url" not in html


@pytest.mark.asyncio
async def test_favicon_ico_serves_the_svg_with_a_long_cache():
    response = await _get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.content == (STATIC / "favicon.svg").read_bytes()
    assert response.headers["cache-control"] == "public, max-age=31536000"


@pytest.mark.asyncio
async def test_static_html_is_noindex():
    response = await _get("/static/index.html")
    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == "noindex"
    page = await _get("/")
    assert "x-robots-tag" not in page.headers


# --- og:image Phase A (T8.4) ---

OG_PAGES = [
    ("/", "default"),
    ("/about", "default"),
    ("/methodology", "default"),
    ("/privacy", "default"),
    ("/member?id=S000148", "member"),
    ("/bill?congress=119&type=hr&number=1", "bill"),
    ("/state?code=NY", "state"),
]
OG_ALT = {
    "default": "ClearVoting — Facts only · No opinions · No spin",
    "member": "ClearVoting — Voting record",
    "bill": "ClearVoting — How Congress voted",
    "state": "ClearVoting — Your representatives",
}
_OG_IMAGE_RE = re.compile(r'<meta property="og:image" content="([^"]+)">')


@pytest.mark.asyncio
@pytest.mark.parametrize("path,card", OG_PAGES)
async def test_og_image_points_at_a_committed_card(path, card):
    response = await _get(path)
    assert response.status_code == 200
    html = response.text
    match = _OG_IMAGE_RE.search(html)
    assert match, path
    assert match.group(1) == f"{SITE}/static/og/{card}.png"
    data = (STATIC / "og" / f"{card}.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (1200, 630)
    assert '<meta property="og:image:width" content="1200">' in html
    assert '<meta property="og:image:height" content="630">' in html
    assert f'<meta property="og:image:alt" content="{OG_ALT[card]}">' in html
    assert '<meta name="twitter:card" content="summary_large_image">' in html


def test_og_image_path_is_site_relative_and_takes_an_entity_key():
    from app.main import _og_image
    # X999999 names no member, so this holds after T10.1's Phase B scan too.
    assert _og_image("member", "X999999") == {
        "path": "/static/og/member.png", "width": 1200, "height": 630, "alt": OG_ALT["member"],
    }
    for kind in OG_ALT:
        assert _og_image(kind)["path"] == f"/static/og/{kind}.png"


@pytest.mark.asyncio
async def test_404_carries_no_share_card():
    response = await _get("/no-such-page")
    assert response.status_code == 404
    assert "og:image" not in response.text


@pytest.mark.asyncio
async def test_og_cards_are_cached_for_a_day_not_immutable():
    response = await _get("/static/og/default.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "public, max-age=86400"
