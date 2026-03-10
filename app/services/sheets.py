import json
import logging

logger = logging.getLogger(__name__)


class SheetsService:
    """Append feedback rows to a Google Sheet. Degrades gracefully if unconfigured."""

    _HEADERS = ["Timestamp", "Message", "Page URL", "Page Type", "Context ID", "Context Label"]

    def __init__(self, credentials_json: str, spreadsheet_id: str) -> None:
        self._worksheet = None
        if not credentials_json or not spreadsheet_id:
            return
        try:
            import gspread
            creds_dict = json.loads(credentials_json)
            gc = gspread.service_account_from_dict(creds_dict)
            sheet = gc.open_by_key(spreadsheet_id)
            self._worksheet = sheet.sheet1
            # Auto-insert header row if sheet is empty
            if not self._worksheet.row_values(1):
                self._worksheet.append_row(self._HEADERS)
            logger.info("Google Sheets feedback storage initialized")
        except Exception:
            logger.warning("Google Sheets unavailable — feedback will use JSONL fallback", exc_info=True)
            self._worksheet = None

    @property
    def is_available(self) -> bool:
        return self._worksheet is not None

    def append_row(self, row: list[str]) -> bool:
        if not self.is_available:
            return False
        try:
            self._worksheet.append_row(row)
            return True
        except Exception:
            logger.warning("Failed to write feedback to Google Sheets", exc_info=True)
            return False
