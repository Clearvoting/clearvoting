import json
import logging
import threading
import time

logger = logging.getLogger(__name__)

# A cell starting with one of these is run as a formula when the sheet is exported to CSV
# and opened in Excel or LibreOffice (=HYPERLINK, =WEBSERVICE, +cmd|...). A leading
# apostrophe keeps it text; under RAW it is stored as typed and survives the export (F046).
_FORMULA_STARTS = ("=", "+", "-", "@")
_CONTROL_STARTS = ("\t", "\r")


def _neutralize(cell):
    if isinstance(cell, str) and (cell.startswith(_CONTROL_STARTS)
                                  or cell.lstrip().startswith(_FORMULA_STARTS)):
        return "'" + cell
    return cell


class SheetsService:
    """Append rows to a Google Sheet worksheet. Degrades gracefully if unconfigured.

    By default writes to the spreadsheet's first worksheet with the feedback
    headers. Pass worksheet_title/headers to target a dedicated tab (created on
    first use), e.g. the notify-signups waitlist.

    A failed connect is retried from append_row, which the routes run in the
    threadpool, at most once per _RETRY_SECONDS. Before, one Google blip at boot
    sent every report to the JSONL fallback until the next deploy (F031).
    """

    _HEADERS = ["Timestamp", "Message", "Page URL", "Page Type", "Context ID", "Context Label"]
    # (connect, read) seconds for every Google call. gspread's default is no timeout, so a
    # stalled Google held the import, or a threadpool slot, indefinitely (F005, F031).
    _TIMEOUT = (5, 10)
    _RETRY_SECONDS = 60

    def __init__(
        self,
        credentials_json: str,
        spreadsheet_id: str,
        worksheet_title: str | None = None,
        headers: list[str] | None = None,
    ) -> None:
        self._worksheet = None
        self._credentials_json = credentials_json
        self._spreadsheet_id = spreadsheet_id
        self._worksheet_title = worksheet_title
        self._headers = headers or self._HEADERS
        self._lock = threading.Lock()
        self._last_attempt: float | None = None
        if not credentials_json or not spreadsheet_id:
            return
        self._connect()

    def _connect(self) -> None:
        self._last_attempt = time.monotonic()
        try:
            import gspread
            creds_dict = json.loads(self._credentials_json)
            gc = gspread.service_account_from_dict(creds_dict)
            gc.set_timeout(self._TIMEOUT)
            sheet = gc.open_by_key(self._spreadsheet_id)
            if self._worksheet_title:
                try:
                    worksheet = sheet.worksheet(self._worksheet_title)
                except gspread.WorksheetNotFound:
                    worksheet = sheet.add_worksheet(
                        title=self._worksheet_title, rows=1000, cols=len(self._headers)
                    )
            else:
                worksheet = sheet.sheet1
            # Auto-insert header row if sheet is empty
            if not worksheet.row_values(1):
                worksheet.append_row(self._headers)
            self._worksheet = worksheet
            logger.info("Google Sheets storage initialized (%s)", self._worksheet_title or "sheet1")
        except Exception:
            logger.warning("Google Sheets unavailable — will use JSONL fallback", exc_info=True)
            self._worksheet = None

    def _retry_due(self) -> bool:
        # _last_attempt stays None when credentials or the spreadsheet ID are missing,
        # so an unconfigured service (local dev) never retries.
        return (
            self._worksheet is None
            and self._last_attempt is not None
            and time.monotonic() - self._last_attempt >= self._RETRY_SECONDS
        )

    @property
    def is_available(self) -> bool:
        # Also True once a failed connect is due its retry: the routes only call
        # append_row (where the retry runs, off the event loop) when this is True.
        return self._worksheet is not None or self._retry_due()

    def append_row(self, row: list[str]) -> bool:
        # One thread retries; any other caller falls back at once rather than hold a
        # threadpool slot waiting behind a slow Google.
        if self._retry_due() and self._lock.acquire(blocking=False):
            try:
                if self._retry_due():
                    self._connect()
            finally:
                self._lock.release()
        worksheet = self._worksheet
        if worksheet is None:
            return False
        try:
            worksheet.append_row([_neutralize(cell) for cell in row], value_input_option="RAW")
            return True
        except Exception:
            logger.warning("Failed to write row to Google Sheets", exc_info=True)
            return False
