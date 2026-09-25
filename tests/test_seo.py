import json
import xml.etree.ElementTree as ET
from html import escape

import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.render import cut_words

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


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
    assert '<meta property="og:title" content="Rick Scott (FL) — Voting Record | ClearVoting">' in html
    assert '<meta property="og:description"' in html
    assert '<meta property="og:type" content="profile">' in html
    assert '<meta property="og:url" content="https://clearvoting.org/member?id=S001217">' in html
    assert '<meta name="twitter:card" content="summary">' in html
    assert '<link rel="canonical" href="https://clearvoting.org/member?id=S001217">' in html


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
    assert f'<meta property="og:title" content="{escape(cut_words(f"H.R. 1 — {headline}", 90))}">' in html
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
    assert len(meta["og_title"]) <= 91
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
    response = await _get("/state?code=FL")
    assert response.status_code == 200
    html = response.text
    assert "<title>Florida Representatives — Voting Records | ClearVoting</title>" in html
    assert "2 members of Congress from Florida" in html
    assert '<link rel="canonical" href="https://clearvoting.org/state?code=FL">' in html


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
async def test_sitemap_contains_all_page_types_and_parses():
    response = await _get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers["content-type"]
    root = ET.fromstring(response.text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [el.text for el in root.findall(".//sm:loc", ns)]
    assert "https://clearvoting.org/" in locs
    assert "https://clearvoting.org/about" in locs
    assert "https://clearvoting.org/member?id=S001217" in locs
    assert "https://clearvoting.org/bill?congress=119&type=hr&number=1" in locs
    assert "https://clearvoting.org/state?code=FL" in locs
    # lastmod comes from sync metadata
    lastmods = [el.text for el in root.findall(".//sm:lastmod", ns)]
    assert "2026-03-07" in lastmods


# --- robots.txt ---

@pytest.mark.asyncio
async def test_robots_txt():
    response = await _get("/robots.txt")
    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Sitemap: https://clearvoting.org/sitemap.xml" in response.text


# --- 404 handling ---

@pytest.mark.asyncio
async def test_404_returns_html_for_non_api_paths():
    response = await _get("/no-such-page")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "ClearVoting" in html
    assert 'href="/"' in html


@pytest.mark.asyncio
async def test_404_stays_json_for_api_paths():
    response = await _get("/api/no-such-endpoint")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}
