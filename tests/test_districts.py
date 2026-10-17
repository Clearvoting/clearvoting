"""ZIP → congressional district (spec §5.1, §5.2, §3.2) and the per-client rate-limit key (§10 #18)."""
import json
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


@pytest.mark.parametrize("raw", ["", "abc", "1157", "115700", "11570-12", "11570--1234", "_source", None])
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
                                             headers={"CF-Connecting-IP": f"203.0.113.{i % 2}"})).status_code
                           for i in range(100)]
    get_data_service.cache_clear()
    limiter.reset()
    assert one_client[:60] == [200] * 60
    assert one_client[60] == 429
    assert two_clients == [200] * 100  # 50 each: separate buckets per client (§10 #18)


# --- limiter key (§10 #18) ---

def _request(headers: dict, client=("10.0.0.1", 1234)) -> Request:
    return Request({
        "type": "http", "method": "GET", "path": "/", "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
    })


def test_client_key_prefers_cf_connecting_ip():
    request = _request({"CF-Connecting-IP": "203.0.113.9", "X-Forwarded-For": "198.51.100.1, 10.0.0.2"})
    assert client_key(request) == "203.0.113.9"


def test_client_key_uses_the_first_forwarded_for_entry():
    assert client_key(_request({"X-Forwarded-For": "198.51.100.1, 10.0.0.2"})) == "198.51.100.1"


def test_client_key_falls_back_to_the_peer():
    assert client_key(_request({})) == "10.0.0.1"
    assert client_key(_request({}, client=None)) == "127.0.0.1"
