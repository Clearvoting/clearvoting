import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from app.config import BASE_DIR, GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEETS_SPREADSHEET_ID
from app.limiter import limiter
from app.render import NOTIFY_STATES
from app.services.sheets import SheetsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notify", tags=["notify"])

# Fallback only: Render's filesystem is ephemeral, so this file does not
# survive deploys. Sheets is the durable store.
NOTIFY_FILE = BASE_DIR / "data" / "notify_signups.jsonl"

_sheets = SheetsService(
    GOOGLE_SHEETS_CREDENTIALS_JSON,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    worksheet_title="Notify Signups",
    headers=["Timestamp", "Email", "State"],
)

# Pragmatic email shape check — we have no email-validator dependency and don't
# need RFC-perfect validation to collect a launch waitlist.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NotifySignup(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    state: str = Field(default="", max_length=50)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        value = value.strip()
        if not _EMAIL_RE.match(value):
            raise ValueError("Invalid email address")
        return value


@router.post("")
@limiter.limit("5/minute")
async def submit_signup(signup: NotifySignup, request: Request) -> dict:
    # Spec §10 #16: the form lists only the 46 uncovered states + DC; anything else
    # (missing, a covered state, a name, a typo) is refused before anything is stored.
    state = signup.state.strip().upper()
    if state not in NOTIFY_STATES:
        raise HTTPException(status_code=400, detail="Choose a state ClearVoting doesn't cover yet")
    timestamp = datetime.now(timezone.utc).isoformat()

    # gspread is synchronous — run it off the event loop.
    if _sheets.is_available and await run_in_threadpool(
        _sheets.append_row, [timestamp, signup.email, state]
    ):
        logger.info("Notify signup saved to Google Sheets: state=%s", state)
        return {"status": "ok"}

    entry = {"timestamp": timestamp, "email": signup.email, "state": state}
    NOTIFY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    # Never log the email (spec §10 #16); the JSONL copy is the fallback record.
    logger.warning("signup saved to fallback, state=%s", state)
    return {"status": "ok"}
