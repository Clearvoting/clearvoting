import json
import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

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


class FeedbackSubmission(BaseModel):
    # feedback.js sends exactly these five fields; anything else is refused (F004).
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=2000)
    page_url: str = Field(..., max_length=500)
    page_type: str = Field(..., max_length=50)
    context_id: str = Field(default="", max_length=200)
    context_label: str = Field(default="", max_length=500)


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
        logger.info("Feedback saved to Google Sheets: page_type=%s", feedback.page_type)
    else:
        await run_in_threadpool(_save_to_file, entry)
        # WARNING: the file does not survive a deploy, so this needs to be seen (F031).
        logger.warning("Feedback saved to JSONL fallback: page_type=%s", feedback.page_type)

    return {"status": "ok"}
