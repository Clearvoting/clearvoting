import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import BASE_DIR
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

FEEDBACK_FILE = BASE_DIR / "data" / "feedback.jsonl"


class FeedbackSubmission(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    page_url: str = Field(..., max_length=500)
    page_type: str = Field(..., max_length=50)
    context_id: str = Field(default="", max_length=200)
    context_label: str = Field(default="", max_length=500)


@router.post("")
@limiter.limit("5/minute")
async def submit_feedback(feedback: FeedbackSubmission, request: Request) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": feedback.message,
        "page_url": feedback.page_url,
        "page_type": feedback.page_type,
        "context_id": feedback.context_id,
        "context_label": feedback.context_label,
    }

    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    logger.info("Feedback received: page_type=%s", feedback.page_type)
    return {"status": "ok"}
