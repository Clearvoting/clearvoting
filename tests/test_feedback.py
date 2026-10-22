import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_data_service
from app.limiter import limiter


def _make_unavailable_sheets():
    """Create a mock SheetsService that is unavailable (forces JSONL fallback)."""
    mock = MagicMock()
    mock.is_available = False
    return mock


@pytest.fixture(autouse=True)
def _use_tmp_feedback_file(tmp_path):
    """Redirect feedback writes to a temp file, disable Sheets, and reset rate limiter."""
    tmp_file = tmp_path / "feedback.jsonl"
    limiter.reset()
    with patch("app.routers.feedback.FEEDBACK_FILE", tmp_file), \
         patch("app.routers.feedback._sheets", _make_unavailable_sheets()):
        yield tmp_file


def _post_feedback(client, headers=None, **overrides):
    payload = {
        "message": "Great tool!",
        "page_url": "http://test/",
        "page_type": "home",
        "context_id": "",
        "context_label": "",
    }
    payload.update(overrides)
    return client.post("/api/feedback", json=payload, headers=headers)


# --- Happy path ---

@pytest.mark.asyncio
async def test_submit_feedback_success(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_feedback_written_to_file(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _post_feedback(client, message="Hello from test")

    lines = _use_tmp_feedback_file.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["message"] == "Hello from test"
    assert entry["page_type"] == "home"
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_feedback_with_member_context(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(
            client,
            message="Data looks wrong",
            page_url="http://test/member?id=S001217",
            page_type="member",
            context_id="S001217",
            context_label="Rick Scott",
        )
    assert resp.status_code == 200
    entry = json.loads(_use_tmp_feedback_file.read_text().strip())
    assert entry["context_id"] == "S001217"
    assert entry["context_label"] == "Rick Scott"
    assert entry["page_type"] == "member"


@pytest.mark.asyncio
async def test_feedback_with_bill_context(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(
            client,
            page_type="bill",
            context_id="hr1",
            context_label="One Big Beautiful Bill Act",
        )
    assert resp.status_code == 200
    entry = json.loads(_use_tmp_feedback_file.read_text().strip())
    assert entry["page_type"] == "bill"
    assert entry["context_id"] == "hr1"


@pytest.mark.asyncio
async def test_multiple_submissions_append(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _post_feedback(client, message="First")
        await _post_feedback(client, message="Second")

    lines = _use_tmp_feedback_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["message"] == "First"
    assert json.loads(lines[1])["message"] == "Second"


@pytest.mark.asyncio
async def test_feedback_max_length_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, message="x" * 2000)
    assert resp.status_code == 200


# --- Validation errors ---

@pytest.mark.asyncio
async def test_empty_message_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, message="")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_message_too_long_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, message="x" * 2001)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_required_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/feedback", json={"message": "hello"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_page_url_too_long_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, page_url="http://x" + "x" * 500)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_page_type_too_long_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, page_type="x" * 51)
    assert resp.status_code == 422


# --- Untrusted fields: page_type allowlist, site-only page_url, no control characters (F045) ---

async def _stored_entry(tmp_file, **overrides) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await _post_feedback(client, **overrides)
    assert resp.status_code == 200
    return json.loads(tmp_file.read_text().strip())


@pytest.mark.asyncio
@pytest.mark.parametrize("sent,kept", [
    ("member", "member"), ("cheatsheet", "cheatsheet"), ("privacy", "privacy"), ("<b>x</b>", "other"),
    ("home\n2026-10-21 ERROR app.main: sync FAILED", "other"), ("Home", "other"), ("", "other"),
])
async def test_page_type_is_one_the_site_sends_or_other(_use_tmp_feedback_file, sent, kept):
    assert (await _stored_entry(_use_tmp_feedback_file, page_type=sent))["page_type"] == kept


@pytest.mark.asyncio
@pytest.mark.parametrize("url,kept", [
    ("https://clearvoting.org/member?id=S000148", True), ("https://www.clearvoting.org/", True),
    ("javascript:alert(1)", False), ("http://clearvoting.org/", False), ("http://test/", False),
    ("https://clearvoting.org.evil.example/", False), ("https://evil.example/?https://clearvoting.org", False),
    ("https://user@clearvoting.org/", False), ("https://clearvoting.org:8443/", False),
    ("https://clearvoting.org/\nERROR", False), ("https://clearvoting.org\\@evil.example/", False),
    ("https://[clearvoting.org/", False),
])
async def test_page_url_is_kept_only_as_an_https_link_to_this_site(_use_tmp_feedback_file, url, kept):
    assert (await _stored_entry(_use_tmp_feedback_file, page_url=url))["page_url"] == (url if kept else "")


@pytest.mark.asyncio
async def test_free_text_loses_control_characters_and_the_message_keeps_its_lines(_use_tmp_feedback_file):
    entry = await _stored_entry(_use_tmp_feedback_file, message="line one\nline\ttwo\x07\x00",
                                context_id="a\x00b\r\nc", context_label="x\x1b[31mred\u2028y\x85")
    assert entry["message"] == "line one\nline\ttwo  "
    assert entry["context_id"] == "a b  c"
    assert entry["context_label"] == "x [31mred y "


@pytest.mark.asyncio
async def test_a_forged_page_type_cannot_write_a_log_line_of_its_own(_use_tmp_feedback_file, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="app.routers.feedback"):
        await _stored_entry(_use_tmp_feedback_file, page_type="home\n2026-10-21 ERROR app.main: sync FAILED")
    messages = [record.getMessage() for record in caplog.records]
    assert messages == ["Feedback saved to JSONL fallback: page_type='other'"]


def test_every_page_type_feedback_js_sends_is_allowlisted():
    from app.routers.feedback import PAGE_TYPES
    js = (STATIC / "js" / "feedback.js").read_text()
    sent = set(re.findall(r"page_type: '([a-z]+)'", js))
    sliced = re.search(r"if \(([^)]*)\) \{\s*return \{ page_type: path\.slice\(1\)", js)
    assert sliced, "feedback.js no longer derives page_type from the path"
    sent |= set(re.findall(r"path === '/([a-z]+)'", sliced.group(1)))
    assert {"home", "member", "bill", "state", "about"} <= sent <= PAGE_TYPES


# --- Google Sheets integration ---

@pytest.mark.asyncio
async def test_feedback_writes_to_sheets_when_available(tmp_path):
    """When Sheets is available, feedback goes to Sheets (not JSONL)."""
    tmp_file = tmp_path / "feedback.jsonl"
    mock_sheets = MagicMock()
    mock_sheets.is_available = True
    mock_sheets.append_row.return_value = True
    limiter.reset()

    with patch("app.routers.feedback.FEEDBACK_FILE", tmp_file), \
         patch("app.routers.feedback._sheets", mock_sheets):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _post_feedback(client, message="Sheets feedback")

    assert resp.status_code == 200
    mock_sheets.append_row.assert_called_once()
    row = mock_sheets.append_row.call_args[0][0]
    assert row[1] == "Sheets feedback"
    assert row[3] == "home"
    # JSONL should NOT have been written
    assert not tmp_file.exists()


@pytest.mark.asyncio
async def test_feedback_falls_back_on_sheets_failure(tmp_path):
    """When Sheets append fails, feedback falls back to JSONL."""
    tmp_file = tmp_path / "feedback.jsonl"
    mock_sheets = MagicMock()
    mock_sheets.is_available = True
    mock_sheets.append_row.return_value = False  # simulate failure
    limiter.reset()

    with patch("app.routers.feedback.FEEDBACK_FILE", tmp_file), \
         patch("app.routers.feedback._sheets", mock_sheets):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _post_feedback(client, message="Fallback feedback")

    assert resp.status_code == 200
    assert tmp_file.exists()
    entry = json.loads(tmp_file.read_text().strip())
    assert entry["message"] == "Fallback feedback"


@pytest.mark.asyncio
async def test_feedback_jsonl_fallback_when_no_credentials(tmp_path):
    """When Sheets has no credentials, feedback goes to JSONL."""
    tmp_file = tmp_path / "feedback.jsonl"
    mock_sheets = MagicMock()
    mock_sheets.is_available = False
    limiter.reset()

    with patch("app.routers.feedback.FEEDBACK_FILE", tmp_file), \
         patch("app.routers.feedback._sheets", mock_sheets):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _post_feedback(client, message="No creds feedback")

    assert resp.status_code == 200
    assert tmp_file.exists()
    entry = json.loads(tmp_file.read_text().strip())
    assert entry["message"] == "No creds feedback"


# --- Rate limits (F011, F085) ---

def _ready_sheets():
    mock = MagicMock()
    mock.is_available = True
    mock.append_row.return_value = True
    return mock


@pytest.mark.asyncio
async def test_sixth_feedback_from_one_client_is_refused_before_any_write():
    sheets = _ready_sheets()
    with patch("app.routers.feedback._sheets", sheets):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = [await _post_feedback(client) for _ in range(6)]
            other_client = await _post_feedback(client, headers={"X-Forwarded-For": "198.51.100.7"})
    assert [r.status_code for r in responses] == [200] * 5 + [429]
    assert responses[5].headers["cache-control"] == "no-store"
    assert other_client.status_code == 200
    assert sheets.append_row.call_count == 6  # five from the first client, one from the second


@pytest.mark.asyncio
async def test_feedback_cap_is_shared_by_every_client():
    """F011: 25 a minute in all, however many addresses send them."""
    sheets = _ready_sheets()
    with patch("app.routers.feedback._sheets", sheets):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = [await _post_feedback(client, headers={"X-Forwarded-For": f"198.51.100.{i}"})
                         for i in range(1, 27)]
    assert [r.status_code for r in responses] == [200] * 25 + [429]
    assert responses[25].headers["cache-control"] == "no-store"
    assert sheets.append_row.call_count == 25


# --- Hooks, dialog and server-filled freshness (plan T2.4; spec §2.2 #5, C-7, §6.4, §6.6, §10 #17) ---

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
FIXTURES = ROOT / "tests" / "fixtures" / "synced"


def test_feedback_js_reads_the_promoted_h1_headers():
    js = (STATIC / "js" / "feedback.js").read_text()
    assert "document.querySelector('.member-header h1')" in js
    assert "document.querySelector('.bill-header h1')" in js
    assert "document.querySelector('.state-header h1')" in js
    assert ".member-header h2" not in js and ".bill-header h2" not in js


def test_old_member_script_renders_the_name_as_h1_inside_member_header():
    js = (STATIC / "js" / "member.js").read_text()
    if "member-header-info" not in js:
        pytest.skip("member header is server-rendered (T6.3 asserts .member-header h1 in the HTML)")
    assert re.search(r"el\('div', \{ className: 'member-header-info' \},\s*el\('h1', null, name\)", js)
    assert "el('div', { className: 'member-header' }, photoEl, headerInfo)" in js


def test_old_bill_script_renders_the_title_as_h1_inside_bill_header():
    js = (STATIC / "js" / "bill.js").read_text()
    if "className: 'bill-header'" not in js:
        pytest.skip("bill header is server-rendered (T7.4 asserts .bill-header h1 in the HTML)")
    assert re.search(r"el\('div', \{ className: 'bill-header' \},\s*el\('span', \{ className: 'bill-number' \}[^\n]*\n\s*el\('h1', null, title\)", js)


def test_old_stylesheets_style_the_h1_headers():
    for name in ("styles.css", "broadsheet.css"):
        path = STATIC / "css" / name
        if not path.exists():
            continue  # retired in T9.1
        css = path.read_text()
        assert ".member-header h2" not in css and ".bill-header h2" not in css, name
        assert ".member-header h1" in css and ".bill-header h1" in css, name


def test_feedback_js_uses_the_native_dialog_and_owns_its_copy():
    js = (STATIC / "js" / "feedback.js").read_text()
    for present in ("modal.showModal()", "modal.close()", "'Thanks — sent.'",
                    "\"We couldn't send that. Please try again in a few minutes.\"",
                    "document.querySelectorAll('.feedback-btn')", "getElementById('about-feedback-cta')",
                    "addEventListener('close'", "opener.focus()",
                    "[data-feedback-open]", "data-context-label"):
        assert present in js, present
    for gone in ("IntersectionObserver", "ClearVotingAnimate", "/api/health", "animate-in",
                 "modal.hidden", "setTimeout", "innerHTML", "data-freshness",
                 "e.target === modal"):  # no backdrop-click close: a padding click would discard a draft
        assert gone not in js, gone


# F070: feedback.js run under node with a stand-in DOM; the page URL carries a long ?q=, a
# tracking parameter and a fragment, and the server answers with the given status.
_FEEDBACK_SUBMIT_SCRIPT = r"""
function elem() {
  return { value: '', textContent: '', hidden: false, disabled: false, open: false, listeners: {},
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    addEventListener(type, fn) { this.listeners[type] = fn; }, focus() {}, setAttribute() {},
    showModal() { this.open = true; }, close() { this.open = false; } };
}
const ids = {};
['feedback-modal', 'feedback-open', 'feedback-cancel', 'feedback-overlay', 'feedback-form', 'feedback-message',
 'feedback-submit', 'feedback-status', 'feedback-context'].forEach((id) => { ids[id] = elem(); });
globalThis.window = { location: { origin: 'https://clearvoting.org', pathname: '/',
  search: '?q=' + 'x'.repeat(600) + '&fbclid=IwAR0abc', hash: '#browse',
  href: 'https://clearvoting.org/?q=' + 'x'.repeat(600) + '&fbclid=IwAR0abc#browse' } };
globalThis.document = { getElementById: (id) => ids[id] || null, querySelector: () => null,
  querySelectorAll: () => [], addEventListener() {}, activeElement: null, body: { contains: () => true } };
let sent = null;
const status = Number(process.argv[2]);
globalThis.fetch = async (url, options) => { sent = JSON.parse(options.body); return { ok: status < 300, status }; };
require(process.argv[1]);
ids['feedback-message'].value = 'The date on this page is wrong.';
ids['feedback-form'].listeners.submit({ preventDefault() {} });
setTimeout(() => process.stdout.write(JSON.stringify({ sent, status: ids['feedback-status'].textContent,
  disabled: ids['feedback-submit'].disabled })), 20);
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed (CI runs without it)")
@pytest.mark.parametrize("status, shown", [
    (200, "Thanks — sent."),
    (422, "We couldn't accept that message. Please shorten it and try again."),
    (429, "We couldn't send that. Please try again in a few minutes."),
    (503, "We couldn't send that. Please try again in a few minutes."),
])
def test_feedback_js_sends_a_bounded_page_url_and_names_a_refusal(status, shown):
    done = subprocess.run([shutil.which("node"), "-e", _FEEDBACK_SUBMIT_SCRIPT, str(STATIC / "js" / "feedback.js"),
                           str(status)], capture_output=True, text=True, check=True, timeout=60)
    out = json.loads(done.stdout)
    page_url = out["sent"]["page_url"]
    # Origin + path + query, cut to the server's 500 characters; never the #fragment.
    assert page_url == ("https://clearvoting.org/?q=" + "x" * 600)[:500]
    assert "#" not in page_url
    assert out["status"] == shown and out["disabled"] is False


def test_nothing_waits_for_an_entrance_animation():
    about = (STATIC / "about.html").read_text()
    assert "animate-in" not in about and "animate-scale" not in about
    styles = STATIC / "css" / "styles.css"
    if styles.exists():
        css = styles.read_text()
        for gone in (".animate-in", ".animate-scale", ".stagger-children", ".hero-animate"):
            assert gone not in css, gone


async def _get_page(path: str, metadata: dict | None = None):
    from app.dependencies import get_data_service
    patches = [patch("app.dependencies.get_data_dir", return_value=FIXTURES)]
    if metadata is not None:
        patches.append(patch("app.services.data_service.DataService.get_sync_metadata", return_value=metadata))
    for p in patches:
        p.start()
    get_data_service.cache_clear()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(path)
    finally:
        for p in patches:
            p.stop()
        get_data_service.cache_clear()


@pytest.mark.parametrize("path", ["/", "/about", "/no-such-page"])
async def test_footer_freshness_is_filled_by_the_server(path):
    from app.render import format_date
    last_sync = json.loads((FIXTURES / "sync_metadata.json").read_text())["last_sync"]
    response = await _get_page(path)
    expected = f'<span id="data-freshness"> · Synced {format_date(last_sync[:10])}</span>'
    assert expected in response.text
    assert re.search(r"·\s*<span id=\"data-freshness\">", response.text) is None  # separator lives inside the span


async def test_footer_freshness_is_empty_without_last_sync():
    response = await _get_page("/about", metadata={})
    assert '<span id="data-freshness"></span>' in response.text
    assert "Synced" not in response.text


# --- The sanctioned hook change (spec §2.2 #5, C-7) resolves on the server HTML ---

import re as _re_hook
from pathlib import Path as _HookPath

_HOOK_FIXTURES = _HookPath(__file__).parent / "fixtures" / "synced"
_HOOK_STATIC = _HookPath(__file__).parent.parent / "static"


@pytest.mark.asyncio
async def test_member_header_h1_hook_resolves_on_the_ssr_html():
    """feedback.js reads document.querySelector('.member-header h1'); the server HTML must satisfy it."""
    from app.dependencies import get_data_service
    with patch("app.dependencies.get_data_dir", return_value=_HOOK_FIXTURES):
        get_data_service.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/member?id=S000148")
    get_data_service.cache_clear()
    match = _re_hook.search(r'<header class="member-header"[^>]*>((?:(?!</header>).)*?)<h1>([^<]+)</h1>',
                            response.text, _re_hook.S)
    assert match and match.group(2) == "Charles E. Schumer"
    js = (_HOOK_STATIC / "js" / "feedback.js").read_text()
    assert ".member-header h1" in js
    assert ".member-header h2" not in js


# --- Hook contract: the bill page renders .bill-header h1 (plan T7.4, spec §2.3 C-7) ---

@pytest.mark.asyncio
async def test_bill_page_renders_the_bill_header_h1_hook():
    fixtures = Path(__file__).parent / "fixtures" / "synced"
    with patch("app.dependencies.get_data_dir", return_value=fixtures):
        get_data_service.cache_clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/bill?congress=119&type=hr&number=1")
    get_data_service.cache_clear()
    assert response.status_code == 200
    header = response.text.split('<header class="bill-header">', 1)[1].split("</header>", 1)[0]
    assert re.search(r"<h1[ >]", header)
    feedback_js = (Path(__file__).parent.parent / "static" / "js" / "feedback.js").read_text()
    assert ".bill-header h1" in feedback_js
    assert ".bill-header h2" not in feedback_js
