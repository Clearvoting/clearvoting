"""ZIP → congressional district (spec §5.1, §5.2, §3.2) and the per-client rate-limit key (§10 #18)."""
import json
import logging
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from starlette.requests import Request

from app.limiter import client_key, limiter
from app.main import app
from app.services.data_service import DataService, normalize_zip

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REAL = Path(__file__).parent.parent / "data" / "synced"
DAY_CACHE = "public, max-age=86400, s-maxage=86400"


@pytest.fixture
def ds():
    return DataService(data_dir=FIXTURES)


def _fixture_members() -> list[dict]:
    return json.loads((FIXTURES / "members.json").read_text())["members"]


def _house_ids(state: str, district: int) -> list[str]:
    return sorted(m["bioguideId"] for m in _fixture_members()
                  if m.get("stateCode") == state and "Senate" not in (m.get("chamber") or "")
                  and m.get("district") == district)


def _senator_ids(state: str) -> list[str]:
    return sorted(m["bioguideId"] for m in _fixture_members()
                  if m.get("stateCode") == state and "Senate" in (m.get("chamber") or ""))


# --- lookup_zip (§5.1) ---

def test_single_district_zip(ds):
    result = ds.lookup_zip("11570")
    assert result["zip"] == "11570"
    assert result["kind"] == "single"
    assert result["covered_share"] == 1.0
    match = result["matches"][0]
    assert (match["state"], match["state_name"], match["district"], match["share"]) == ("NY", "New York", 4, 1.0)
    assert match["member_ids"] == _house_ids("NY", 4)
    assert "G000602" in match["member_ids"]
    assert match["senator_ids"] == _senator_ids("NY")
    assert "S000148" in match["senator_ids"]


def test_split_zip_lists_districts_by_land_share(ds):
    result = ds.lookup_zip("11201")
    assert result["kind"] == "split"
    assert result["covered_share"] == 1.0
    assert [(m["district"], m["share"]) for m in result["matches"]] == [(10, 0.7216), (7, 0.2784)]


@pytest.mark.parametrize("zip5, state, district, covered", [
    ("73949", "TX", 13, 0.1367),
    ("89019", "CA", 23, 0.2153),
    ("97635", "CA", 1, 0.9282),
])
def test_cross_state_zip_is_partial(ds, zip5, state, district, covered):
    result = ds.lookup_zip(zip5)
    assert result["kind"] == "partial"
    assert result["covered_share"] == covered
    assert [(m["state"], m["district"]) for m in result["matches"]] == [(state, district)]


@pytest.mark.parametrize("zip5", ["88430", "44101"])
def test_no_match(ds, zip5):
    # 88430 is listed with a 2.65 % sliver of TX-13, under the 5 % match floor; 44101 is not listed.
    assert ds.lookup_zip(zip5) == {"zip": zip5, "kind": "none", "matches": []}


def test_member_ids_come_from_the_roster(ds):
    result = ds.lookup_zip("10001")
    assert result["kind"] == "single"
    assert result["matches"][0]["district"] == 12
    assert result["matches"][0]["member_ids"] == _house_ids("NY", 12)


@pytest.mark.parametrize("raw", ["11570-1234", "115701234", "11570 1234", " 11570 ", "\t11570-1234\n"])
def test_zip_plus_four_and_spaces_normalize_to_five_digits(ds, raw):
    assert normalize_zip(raw) == "11570"
    assert ds.lookup_zip(raw)["zip"] == "11570"


@pytest.mark.parametrize("raw", ["", "abc", "1157", "115700", "11570-12", "11570--1234", "_source", None,
                                 "١١٥٧٠", "１１５７０", "11570-١٢٣٤"])   # other scripts' digits (F044)
def test_malformed_input_is_rejected(ds, raw):
    assert normalize_zip(raw) is None
    assert ds.lookup_zip(raw) is None


def test_crosswalk_loader_skips_underscore_keys(ds):
    raw = json.loads((FIXTURES / "zip_districts.json").read_text())
    assert "_source" in raw
    assert "_source" not in ds._zip_districts
    assert set(ds._zip_districts) == {key for key in raw if not key.startswith("_")}


def test_districts_expected_is_the_crosswalk_maximum(ds):
    expected: dict[str, int] = {}
    for key, rows in json.loads((FIXTURES / "zip_districts.json").read_text()).items():
        if key.startswith("_"):
            continue
        for row in rows:
            expected[row["state"]] = max(expected.get(row["state"], 0), row["district"])
    for code in ("CA", "FL", "NY", "TX"):
        assert ds.districts_expected(code) == expected.get(code, 0)
    assert ds.districts_expected("OH") == 0


@pytest.mark.skipif(not (REAL / "zip_districts.json").exists(), reason="real crosswalk not present")
def test_real_crosswalk_counts():
    real = DataService(data_dir=REAL)
    assert {c: real.districts_expected(c) for c in ("CA", "FL", "NY", "TX")} == {"CA": 52, "FL": 28, "NY": 26, "TX": 38}
    kinds: dict[str, int] = {}
    for zip5 in real._zip_districts:
        kind = real.lookup_zip(zip5)["kind"]
        kinds[kind] = kinds.get(kind, 0) + 1
    # §5.1: 1,226 split, 6 partial, 4 cross-state ZCTAs with no match (88430, 89010, 89060, 89061).
    assert kinds["split"] == 1226 and kinds["partial"] == 6 and kinds["none"] == 4
    assert [real.lookup_zip(z)["kind"] for z in ("88430", "89010", "89060", "89061")] == ["none"] * 4


# --- GET /api/districts/{zip} (§5.2) ---

async def _get(path: str, **kwargs):
    from app.dependencies import get_data_service
    limiter.reset()
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(path, **kwargs)
    get_data_service.cache_clear()
    return response


@pytest.mark.asyncio
async def test_api_single_zip_contract_and_header():
    response = await _get("/api/districts/11570")
    assert response.status_code == 200
    assert response.headers["cache-control"] == DAY_CACHE
    body = response.json()
    assert set(body) == {"zip", "kind", "covered_share", "matches"}
    assert body["kind"] == "single"
    assert set(body["matches"][0]) == {"state", "state_name", "district", "share", "member_ids", "senator_ids"}


@pytest.mark.asyncio
async def test_api_split_zip():
    body = (await _get("/api/districts/11201")).json()
    assert body["kind"] == "split"
    assert [m["district"] for m in body["matches"]] == [10, 7]


@pytest.mark.asyncio
async def test_api_no_match_contract():
    response = await _get("/api/districts/44101")
    assert response.status_code == 200
    assert response.json() == {"zip": "44101", "kind": "none", "matches": []}


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["11570-1234", "%2011570%20"])
async def test_api_normalizes_zip_plus_four_and_spaces(raw):
    response = await _get(f"/api/districts/{raw}")
    assert response.status_code == 200
    assert response.json()["zip"] == "11570"


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["abc", "1157", "115700"])
async def test_api_malformed_zip_is_400(raw):
    response = await _get(f"/api/districts/{raw}")
    assert response.status_code == 400
    assert response.json() == {"detail": "A ZIP code is five digits"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_api_rate_limit_is_60_per_minute_per_client():
    from app.dependencies import get_data_service
    limiter.reset()
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            one_client = [(await client.get("/api/districts/11570")).status_code for _ in range(61)]
            limiter.reset()
            two_clients = [(await client.get("/api/districts/11570",
                                             headers=_via_cloudflare(f"203.0.113.{i % 2}"))).status_code
                           for i in range(100)]
    get_data_service.cache_clear()
    limiter.reset()
    assert one_client[:60] == [200] * 60
    assert one_client[60] == 429
    assert two_clients == [200] * 100  # 50 each: separate buckets per client (§10 #18)


@pytest.mark.asyncio
async def test_api_rate_limit_holds_across_zip_variants():
    """One bucket per route, not per URL (F062): ZIP+4 suffixes, other ZIPs and bad input share it."""
    from app.dependencies import get_data_service
    limiter.reset()
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            variants = [(await client.get(f"/api/districts/11570-{i:04d}")).status_code for i in range(60)]
            after = [(await client.get(path)).status_code
                     for path in ("/api/districts/11570-9999", "/api/districts/11201", "/api/districts/abc")]
    get_data_service.cache_clear()
    limiter.reset()
    assert variants == [200] * 60
    assert after == [429, 429, 429]


@pytest.mark.asyncio
async def test_rate_limit_log_names_neither_the_address_nor_the_zip(caplog):
    """F054: the refusal is logged with a salted hash of the client and the route's name."""
    from app.dependencies import get_data_service
    limiter.reset()
    with patch("app.dependencies.get_data_dir", return_value=FIXTURES), \
         caplog.at_level(logging.WARNING, logger="slowapi"):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            codes = [(await client.get("/api/districts/11570", headers=_via_cloudflare("203.0.113.77"))).status_code
                     for _ in range(62)]
    get_data_service.cache_clear()
    limiter.reset()
    assert codes.count(429) == 2
    lines = [r.getMessage() for r in caplog.records if r.name == "slowapi"]
    assert len(lines) == 2 and lines[0] == lines[1]
    assert re.fullmatch(r"ratelimit 60 per 1 minute \(client [0-9a-f]{10}\) exceeded at endpoint: "
                        r"app\.routers\.districts\.get_districts", lines[0])
    assert "203.0.113.77" not in caplog.text and "11570" not in caplog.text


# --- limiter key (§10 #18, F011) ---

CF_EDGE = "172.70.12.34"  # inside Cloudflare's 172.64.0.0/13


def _via_cloudflare(ip: str) -> dict:
    """Headers as they reach the app through Cloudflare and Render's proxy."""
    return {"CF-Connecting-IP": ip, "X-Forwarded-For": f"{ip}, {CF_EDGE}"}


def _request(headers, client=("10.0.0.1", 1234)) -> Request:
    pairs = headers.items() if isinstance(headers, dict) else headers
    return Request({
        "type": "http", "method": "GET", "path": "/", "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in pairs],
        "client": client,
    })


def test_client_key_trusts_a_valid_cf_connecting_ip_whatever_x_forwarded_for_holds():
    """Cloudflare overwrites CF-Connecting-IP, so it is the visitor whichever proxy hops sit
    between Cloudflare and the app (F011)."""
    assert client_key(_request(_via_cloudflare("203.0.113.9"))) == "203.0.113.9"
    # A Render-internal hop last in X-Forwarded-For does not fold two visitors into one bucket.
    assert client_key(_request({"CF-Connecting-IP": "203.0.113.9",
                                "X-Forwarded-For": f"203.0.113.9, {CF_EDGE}, 10.204.5.6"})) == "203.0.113.9"
    assert client_key(_request({"CF-Connecting-IP": "198.51.100.77",
                                "X-Forwarded-For": f"198.51.100.77, {CF_EDGE}, 10.204.5.6"})) == "198.51.100.77"
    # Nor does a hop with a port, a hop outside Cloudflare's ranges, or no X-Forwarded-For at all.
    assert client_key(_request({"CF-Connecting-IP": "203.0.113.9",
                                "X-Forwarded-For": f"203.0.113.9, {CF_EDGE}:443"})) == "203.0.113.9"
    assert client_key(_request({"CF-Connecting-IP": "203.0.113.9", "X-Forwarded-For": "198.51.100.7"})) == "203.0.113.9"
    assert client_key(_request({"CF-Connecting-IP": "203.0.113.9"})) == "203.0.113.9"


def test_client_key_uses_the_rightmost_forwarded_for_entry():
    """With no CF-Connecting-IP, the entry the nearest proxy appended; everything to its left is
    written by the client (F011)."""
    assert client_key(_request({"X-Forwarded-For": "198.51.100.1, 203.0.113.2"})) == "203.0.113.2"
    # Two header lines read as one list, in order.
    assert client_key(_request([("X-Forwarded-For", "198.51.100.1"), ("X-Forwarded-For", "203.0.113.3")])) == "203.0.113.3"


def test_client_key_skips_values_that_are_not_ip_addresses():
    # A CF-Connecting-IP that is not an address falls through to the last X-Forwarded-For entry.
    assert client_key(_request({"CF-Connecting-IP": "lol-1", "X-Forwarded-For": "1.2.3.4, 198.51.100.7"})) == "198.51.100.7"
    assert client_key(_request({"CF-Connecting-IP": "lol-1"})) == "10.0.0.1"
    assert client_key(_request({"X-Forwarded-For": "198.51.100.1, garbage"})) == "10.0.0.1"
    assert client_key(_request({"X-Forwarded-For": "198.51.100.1, 198.51.100.7:443"})) == "10.0.0.1"
    assert client_key(_request({}, client=("testclient", 50000))) == "testclient"


def test_client_key_buckets_ipv6_by_64_and_unmaps_ipv4():
    def key(ip: str) -> str:
        return client_key(_request(_via_cloudflare(ip)))
    assert key("2001:db8:1:2::1") == key("2001:db8:1:2:ffff:ffff:ffff:fffe") == "2001:db8:1:2::/64"
    assert key("2001:db8:1:3::1") == "2001:db8:1:3::/64"
    assert key("::ffff:203.0.113.9") == "203.0.113.9"
    assert client_key(_request({"X-Forwarded-For": "::ffff:198.51.100.7"})) == "198.51.100.7"
    assert client_key(_request({}, client=("2001:db8:9::5", 1234))) == "2001:db8:9::/64"


def test_client_key_falls_back_to_the_peer():
    assert client_key(_request({})) == "10.0.0.1"
    assert client_key(_request({}, client=None)) == "127.0.0.1"


def test_site_limit_reads_cv_site_rate_limit_and_ignores_garbage(caplog):
    """F007: the site-wide per-client limit; a value the limiter cannot parse falls back to the default."""
    from app.limiter import DEFAULT_SITE_LIMIT, _site_limit
    assert DEFAULT_SITE_LIMIT == "600/minute"
    assert _site_limit(None) == _site_limit("") == _site_limit("  ") == "600/minute"
    assert _site_limit(" 1200/minute ") == "1200/minute"
    with caplog.at_level(logging.ERROR, logger="app.limiter"):
        assert _site_limit("lots") == "600/minute"
    assert "CV_SITE_RATE_LIMIT" in caplog.text
