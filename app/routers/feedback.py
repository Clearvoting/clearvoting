import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import BASE_DIR, GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEETS_SPREADSHEET_ID
from app.limiter import limiter
from app.services.sheets import SheetsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

FEEDBACK_FILE = BASE_DIR / "data" / "feedback.jsonl"

_sheets = SheetsService(GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEETS_SPREADSHEET_ID)


class FeedbackSubmission(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    page_url: str = Field(..., max_length=500)
    page_type: str = Field(..., max_length=50)
    context_id: str = Field(default="", max_length=200)
    context_label: str = Field(default="", max_length=500)


@router.post("")
@limiter.limit("5/minute")
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

    if _sheets.is_available and _sheets.append_row(row):
        logger.info("Feedback saved to Google Sheets: page_type=%s", feedback.page_type)
    else:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("Feedback saved to JSONL: page_type=%s", feedback.page_type)

    return {"status": "ok"}


@router.get("/debug-sheets")
async def debug_sheets(request: Request) -> dict:
    """Temporary diagnostic — remove after confirming Sheets works."""
    return {
        "sheets_available": _sheets.is_available,
        "has_credentials": bool(GOOGLE_SHEETS_CREDENTIALS_JSON),
        "credentials_length": len(GOOGLE_SHEETS_CREDENTIALS_JSON),
        "has_spreadsheet_id": bool(GOOGLE_SHEETS_SPREADSHEET_ID),
        "spreadsheet_id_length": len(GOOGLE_SHEETS_SPREADSHEET_ID),
    }
