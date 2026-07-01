import json
import logging

logger = logging.getLogger(__name__)


class SheetsService:
    """Append rows to a Google Sheet worksheet. Degrades gracefully if unconfigured.

    By default writes to the spreadsheet's first worksheet with the feedback
    headers. Pass worksheet_title/headers to target a dedicated tab (created on
    first use), e.g. the notify-signups waitlist.
    """

    _HEADERS = ["Timestamp", "Message", "Page URL", "Page Type", "Context ID", "Context Label"]

    def __init__(
        self,
        credentials_json: str,
        spreadsheet_id: str,
        worksheet_title: str | None = None,
        headers: list[str] | None = None,
    ) -> None:
        self._worksheet = None
        headers = headers or self._HEADERS
        if not credentials_json or not spreadsheet_id:
            return
        try:
            import gspread
            creds_dict = json.loads(credentials_json)
            gc = gspread.service_account_from_dict(creds_dict)
            sheet = gc.open_by_key(spreadsheet_id)
            if worksheet_title:
                try:
                    self._worksheet = sheet.worksheet(worksheet_title)
                except gspread.WorksheetNotFound:
                    self._worksheet = sheet.add_worksheet(
                        title=worksheet_title, rows=1000, cols=len(headers)
                    )
            else:
                self._worksheet = sheet.sheet1
            # Auto-insert header row if sheet is empty
            if not self._worksheet.row_values(1):
                self._worksheet.append_row(headers)
            logger.info("Google Sheets storage initialized (%s)", worksheet_title or "sheet1")
        except Exception:
            logger.warning("Google Sheets unavailable — will use JSONL fallback", exc_info=True)
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
            logger.warning("Failed to write row to Google Sheets", exc_info=True)
            return False
