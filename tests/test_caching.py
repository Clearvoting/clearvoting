"""Cache-Control by status then route (spec §9.5) and the stable asset version."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

import app.main as main
from app.main import app, _cache_control_for, _compute_asset_version
from app.limiter import limiter

FIXTURES = Path(__file__).parent / "fixtures" / "synced"

HTML = "public, max-age=0, s-maxage=600, stale-while-revalidate=3600"
API = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
STATIC = "public, max-age=31536000, immutable"
OG = "public, max-age=86400"
ZIP_REDIRECT = "public, max-age=0, s-maxage=86400"
NOT_FOUND = "public, max-age=60"
DISTRICTS = "public, max-age=86400, s-maxage=86400"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


async def _request(method: str, path: str, **kwargs):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.request(method, path, **kwargs)
    _clear_data_service_cache()
    return response


# --- The rule table, unit level ---

@pytest.mark.parametrize("method,path,query,status,existing,expected", [
    ("GET", "/", {}, 500, None, "no-store"),
    ("GET", "/api/members/NY/overview", {}, 503, None, "no-store"),
    ("GET", "/api/districts/abc", {}, 400, DISTRICTS, "no-store"),
    ("GET", "/api/bills/999/hr/1", {}, 422, None, "no-store"),
    ("GET", "/api/districts/11570", {}, 429, None, "no-store"),
    ("GET", "/member", {"id": "X999999"}, 404, None, NOT_FOUND),
    ("GET", "/static/css/site.css", {"v": "abc"}, 200, None, STATIC),
    ("GET", "/static/fonts/inter-400.woff2", {}, 304, None, STATIC),
    ("GET", "/static/og/member.png", {}, 200, None, OG),
    ("GET", "/favicon.ico", {}, 200, "public, max-age=31536000", "public, max-age=31536000"),
    ("GET", "/", {}, 200, None, HTML),
    ("GET", "/state", {"code": "NY", "district": "4"}, 200, None, HTML),
    ("GET", "/member", {"id": "S000148"}, 200, None, HTML),
    ("GET", "/bill", {"congress": "119", "type": "hr", "number": "1"}, 200, None, HTML),
    ("GET", "/about", {}, 200, None, HTML),
    ("GET", "/methodology", {}, 200, None, HTML),
    ("GET", "/privacy", {}, 200, None, HTML),
    ("GET", "/state", {"zip": "11570"}, 302, None, ZIP_REDIRECT),
    ("GET", "/state", {"code": "TX", "zip": "11570"}, 302, None, ZIP_REDIRECT),
    ("GET", "/api/bills/119/hr/1", {}, 200, None, API),
    ("GET", "/api/members/NY/overview", {"show_party": "true"}, 200, None, API),
    ("GET", "/api/districts/11570", {}, 200, DISTRICTS, DISTRICTS),
    ("GET", "/api/health", {}, 200, None, "no-store"),
    ("POST", "/api/notify", {}, 200, None, "no-store"),
    ("POST", "/api/feedback", {}, 200, None, "no-store"),
    ("GET", "/robots.txt", {}, 200, None, None),
])
def test_cache_control_rule_table(method, path, query, status, existing, expected):
    assert _cache_control_for(method, path, query, status, existing) == expected


# --- Through the app ---

@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/", "/about", "/methodology", "/privacy",
    "/state?code=NY", "/state?code=NY&district=4",
    "/member?id=S000148", "/bill?congress=119&type=hr&number=1",
])
async def test_html_200_is_edge_cacheable(path):
    response = await _request("GET", path)
    assert response.status_code == 200
    assert response.headers["cache-control"] == HTML


@pytest.mark.asyncio
async def test_zip_302_is_cached_at_the_edge_for_a_day():
    response = await _request("GET", "/state?zip=11570")
    assert response.status_code == 302
    assert response.headers["location"].endswith("#mine")
    assert response.headers["cache-control"] == ZIP_REDIRECT


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/member?id=X999999", "/no-such-page", "/api/no-such-endpoint"])
async def test_404_is_cached_for_a_minute(path):
    response = await _request("GET", path)
    assert response.status_code == 404
    assert response.headers["cache-control"] == NOT_FOUND


@pytest.mark.asyncio
async def test_400_and_422_are_never_stored():
    bad_zip = await _request("GET", "/api/districts/abc")
    assert bad_zip.status_code == 400
    assert bad_zip.headers["cache-control"] == "no-store"
    bad_congress = await _request("GET", "/api/bills/999/hr/1")
    assert bad_congress.status_code == 422
    assert bad_congress.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_429_is_never_stored():
    limiter.reset()
    try:
        with _patch_data_dir():
            _clear_data_service_cache()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                limited = None
                for _ in range(80):
                    response = await client.get("/api/districts/11570")
                    if response.status_code == 429:
                        limited = response
                        break
        assert limited is not None, "the 60/minute limit on /api/districts should trip within 80 calls"
        assert limited.headers["cache-control"] == "no-store"
    finally:
        limiter.reset()
        _clear_data_service_cache()


@pytest.mark.asyncio
async def test_site_wide_limit_is_never_stored_and_spares_static_and_health():
    """F007: routes without a limit of their own share one per-client budget of 600 a minute.
    Its 429 is no-store, another client is unaffected, and /static, /favicon.ico, /robots.txt
    and /api/health stay open."""
    limiter.reset()
    try:
        with _patch_data_dir():
            _clear_data_service_cache()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                codes = [(await client.get(("/privacy", "/api/votes/latest")[i % 2])).status_code
                         for i in range(600)]
                limited = await client.get("/about")
                other_client = await client.get("/about", headers={"X-Forwarded-For": "198.51.100.7"})
                exempt = [(await client.get(path)).status_code for path in (
                    f"/static/css/site.css?v={main._asset_version}", "/favicon.ico", "/robots.txt", "/api/health")]
        assert codes == [200] * 600
        assert limited.status_code == 429
        assert limited.headers["cache-control"] == "no-store"
        assert other_client.status_code == 200
        assert exempt == [200] * 4
    finally:
        limiter.reset()
        _clear_data_service_cache()


@pytest.mark.asyncio
async def test_500_is_never_stored():
    with patch(
        "app.services.data_service.DataService.get_sync_metadata",
        side_effect=RuntimeError("boom"),
    ):
        response = await _request("GET", "/sitemap.xml")
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_api_data_and_districts_headers():
    bill = await _request("GET", "/api/bills/119/hr/1")
    assert bill.status_code == 200
    assert bill.headers["cache-control"] == API
    districts = await _request("GET", "/api/districts/11570")
    assert districts.status_code == 200
    assert districts.headers["cache-control"] == DISTRICTS


@pytest.mark.asyncio
async def test_no_store_routes():
    health = await _request("GET", "/api/health")
    assert health.headers["cache-control"] == "no-store"
    feedback = await _request("POST", "/api/feedback", json={})
    assert feedback.headers["cache-control"] == "no-store"
    notify = await _request("POST", "/api/notify", json={})
    assert notify.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_static_assets_are_immutable_and_favicon_is_long_lived():
    css = await _request("GET", f"/static/css/site.css?v={main._asset_version}")
    assert css.status_code == 200
    assert css.headers["cache-control"] == STATIC
    favicon = await _request("GET", "/favicon.ico")
    assert favicon.headers["cache-control"] == "public, max-age=31536000"


# --- Asset version ---

def test_asset_version_uses_the_render_commit_when_set(tmp_path):
    env = {"RENDER_GIT_COMMIT": "0123456789abcdef0123456789abcdef01234567"}
    assert _compute_asset_version(tmp_path, env) == "0123456789ab"


def test_asset_version_ignores_a_malformed_commit(tmp_path):
    (tmp_path / "a.css").write_text("a{}")
    version = _compute_asset_version(tmp_path, {"RENDER_GIT_COMMIT": "not a sha!"})
    assert version == _compute_asset_version(tmp_path, {})
    assert len(version) == 12


def test_asset_version_is_stable_until_a_static_file_changes(tmp_path):
    css = tmp_path / "css" / "site.css"
    css.parent.mkdir()
    css.write_text("a{}")
    first = _compute_asset_version(tmp_path, {})
    second = _compute_asset_version(tmp_path, {})
    assert first == second
    os.utime(css, ns=(css.stat().st_atime_ns, css.stat().st_mtime_ns + 5_000_000_000))
    assert _compute_asset_version(tmp_path, {}) != first


def test_module_asset_version_is_the_static_hash_not_a_clock():
    assert main._asset_version == _compute_asset_version(main.static_dir, os.environ)


@pytest.mark.asyncio
async def test_shells_carry_the_asset_version():
    response = await _request("GET", "/")
    assert f"?v={main._asset_version}" in response.text
