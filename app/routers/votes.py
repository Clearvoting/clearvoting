import copy
import logging
from fastapi import APIRouter, HTTPException, Path
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.get("/latest")
async def get_latest_vote():
    data_service = get_data_service()
    vote = data_service.get_latest_vote()
    if not vote:
        raise HTTPException(status_code=404, detail="No recent vote available")
    return vote


@router.get("/senate/{congress}/{session}/{vote_number}")
async def get_senate_vote(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    data_service = get_data_service()
    data = data_service.get_senate_vote(congress, session, vote_number)
    if not data:
        raise HTTPException(status_code=404, detail="Vote not found")
    data = copy.deepcopy(data)  # the cached file is never mutated
    if not show_party:
        for member in data.get("members", []):
            member.pop("party", None)
    data_service.annotate_roll_call_members(data.get("members", []), senate=True, congress=congress)
    return data


@router.get("/house/{congress}/{session}/{vote_number}")
async def get_house_vote(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    data_service = get_data_service()
    data = data_service.get_house_vote(congress, session, vote_number)
    if not data:
        raise HTTPException(status_code=404, detail="Vote not found")
    data = copy.deepcopy(data)  # the cached file is never mutated
    if not show_party:
        for member in data.get("members", []):
            member.pop("party", None)
    data_service.annotate_roll_call_members(data.get("members", []), senate=False, congress=congress)
    return data
