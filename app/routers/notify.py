import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from app.config import BASE_DIR
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notify", tags=["notify"])

NOTIFY_FILE = BASE_DIR / "data" / "notify_signups.jsonl"

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
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": signup.email,
        "state": signup.state,
    }
    NOTIFY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info("Notify signup saved: state=%s", signup.state or "(unspecified)")
    return {"status": "ok"}
