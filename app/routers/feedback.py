import json
import logging
import re
import threading
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import BASE_DIR, GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEETS_SPREADSHEET_ID
from app.dependencies import require_site_json
from app.limiter import all_clients, limiter
from app.services.sheets import SheetsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

FEEDBACK_FILE = BASE_DIR / "data" / "feedback.jsonl"

_sheets = SheetsService(GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEETS_SPREADSHEET_ID)

# The fallback write runs in threadpool threads (F005); the lock keeps two lines
# written at once from interleaving.
_file_lock = threading.Lock()


def _save_to_file(entry: dict) -> None:
    with _file_lock:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# Every page_type feedback.js sends, on this branch and the cheat-sheet one; anything else is
# stored as "other" (F045), so a crafted value cannot write its own text into the logs or Sheet.
PAGE_TYPES = frozenset({"home", "member", "bill", "state", "cheatsheet", "about", "methodology", "privacy"})
_SITE_HOSTS = frozenset({"clearvoting.org", "www.clearvoting.org"})
# C0 and C1 controls plus the Unicode line/paragraph separators (F045). The message keeps tab
# and newline, which a reader types into the textarea.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
_MESSAGE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")
_URL_UNSAFE = re.compile(r"[\s\\\x00-\x1f\x7f-\x9f]")


class FeedbackSubmission(BaseModel):
    # feedback.js sends exactly these five fields; anything else is refused (F004).
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=2000)
    page_url: str = Field(..., max_length=500)
    page_type: str = Field(..., max_length=50)
    context_id: str = Field(default="", max_length=200)
    context_label: str = Field(default="", max_length=500)

    @field_validator("page_type")
    @classmethod
    def _known_page_type(cls, value: str) -> str:
        return value if value in PAGE_TYPES else "other"

    @field_validator("page_url")
    @classmethod
    def _site_url_only(cls, value: str) -> str:
        """Kept only as an https link to this site; anything else (javascript:, another host,
        a lookalike login page) is stored as "" rather than refused, so the message still lands."""
        try:
            parts = urlsplit(value)
        except ValueError:
            return ""
        if parts.scheme != "https" or parts.netloc not in _SITE_HOSTS or _URL_UNSAFE.search(value):
            return ""
        return value

    @field_validator("context_id", "context_label")
    @classmethod
    def _strip_controls(cls, value: str) -> str:
        return _CONTROL_CHARS.sub(" ", value)

    @field_validator("message")
    @classmethod
    def _strip_message_controls(cls, value: str) -> str:
        return _MESSAGE_CONTROL_CHARS.sub(" ", value)


@router.post("", dependencies=[Depends(require_site_json)])
@limiter.limit("25/minute", key_func=all_clients)  # every client together (F011)
@limiter.limit("5/minute")  # per client, checked first: a refused client spends none of the cap
async def submit_feedback(feedback: FeedbackSubmission, request: Request) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = {
        "timestamp": timestamp,
        "message": feedback.message,
        "page_url": feedback.page_url,
        "page_type": feedback.page_type,
        "context_id": feedback.context_id,
        "context_label": feedback.context_label,
    }

    row = [timestamp, feedback.message, feedback.page_url,
           feedback.page_type, feedback.context_id, feedback.context_label]

    # gspread and the file write are synchronous — run them off the event loop (F005).
    if _sheets.is_available and await run_in_threadpool(_sheets.append_row, row):
        logger.info("Feedback saved to Google Sheets: page_type=%r", feedback.page_type)
    else:
        await run_in_threadpool(_save_to_file, entry)
        # WARNING: the file does not survive a deploy, so this needs to be seen (F031).
        # %r, not %s: a logged value can never start a forged log line of its own (F045).
        logger.warning("Feedback saved to JSONL fallback: page_type=%r", feedback.page_type)

    return {"status": "ok"}
