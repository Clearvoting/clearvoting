from unittest.mock import MagicMock, patch

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
    mock_ws.append_row.assert_called_once_with(["2026-01-01", "Great!", "/", "home", "", ""])


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
