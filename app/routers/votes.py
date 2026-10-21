import copy
import logging
from fastapi import APIRouter, HTTPException, Path, Request
from app.dependencies import get_data_service
from app.limiter import limiter
from app.routers.members import _KNOWN_POSITIONS
from app.services.data_service import SPEAKER_QUESTION

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/votes", tags=["votes"])


def _hide_party(data: dict) -> None:
    """The default roll-call payload (spec §10 #9), in place: no members[].party and, on a
    Speaker election, no candidate name (a vote for a party's nominee is a party cue). A name
    becomes 'Voted' ('Present' and 'Not Voting' stay as recorded) and the result, the
    winner's name, becomes 'Speaker elected'. Other roll calls keep every position as filed."""
    speaker = str(data.get("question") or "").startswith(SPEAKER_QUESTION)
    if speaker:
        data["result"] = "Speaker elected"
    for member in data.get("members", []):
        member.pop("party", None)
        if speaker and member.get("vote") not in _KNOWN_POSITIONS:
            member["vote"] = "Voted"


@router.get("/latest")
def get_latest_vote():
    data_service = get_data_service()
    vote = data_service.get_latest_vote()
    if not vote:
        raise HTTPException(status_code=404, detail="No recent vote available")
    return vote


@router.get("/senate/{congress}/{session}/{vote_number}")
@limiter.limit("60/minute")
def get_senate_vote(request: Request, congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    data_service = get_data_service()
    data = data_service.get_senate_vote(congress, session, vote_number)
    if not data:
        raise HTTPException(status_code=404, detail="Vote not found")
    data = copy.deepcopy(data)  # the cached file is never mutated
    if not show_party:
        _hide_party(data)
    data_service.annotate_roll_call_members(data.get("members", []), senate=True, congress=congress)
    return data


@router.get("/house/{congress}/{session}/{vote_number}")
@limiter.limit("60/minute")
def get_house_vote(request: Request, congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    data_service = get_data_service()
    data = data_service.get_house_vote(congress, session, vote_number)
    if not data:
        raise HTTPException(status_code=404, detail="Vote not found")
    data = copy.deepcopy(data)  # the cached file is never mutated
    if not show_party:
        _hide_party(data)
    data_service.annotate_roll_call_members(data.get("members", []), senate=False, congress=congress)
    return data
