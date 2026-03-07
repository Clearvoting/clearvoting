import copy
import logging
from fastapi import APIRouter, HTTPException, Path
from app.dependencies import get_congress_client, get_senate_vote_service
from app.services.mock_data import get_mock_senate_vote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/votes", tags=["votes"])


def _is_demo() -> bool:
    from app.config import CONGRESS_API_KEY
    return not CONGRESS_API_KEY


@router.get("/house/{congress}/{session}")
async def list_house_votes(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3)):
    client = get_congress_client()
    try:
        return await client.get_house_votes(congress, session)
    except Exception as e:
        logger.error("Congress API error in list_house_votes: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/house/{congress}/{session}/{vote_number}")
async def get_house_vote(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    client = get_congress_client()
    try:
        vote = await client.get_house_vote_detail(congress, session, vote_number)
        members = await client.get_house_vote_members(congress, session, vote_number)
        if not show_party:
            members = _strip_party_from_votes(members)
        return {"vote": vote, "members": members}
    except Exception as e:
        logger.error("Congress API error in get_house_vote: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/senate/{congress}/{session}/{vote_number}")
async def get_senate_vote(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    if _is_demo():
        mock = get_mock_senate_vote(congress, session, vote_number)
        if mock:
            data = copy.deepcopy(mock)
            if not show_party:
                for member in data.get("members", []):
                    member.pop("party", None)
            return data
        raise HTTPException(status_code=404, detail="Vote not found in demo mode")

    service = get_senate_vote_service()
    try:
        data = await service.get_vote(congress, session, vote_number)
        if not show_party:
            data = copy.deepcopy(data)
            for member in data.get("members", []):
                member.pop("party", None)
        return data
    except Exception as e:
        logger.error("Senate vote service error: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


def _strip_party_from_votes(data: dict) -> dict:
    stripped = copy.deepcopy(data)
    if isinstance(stripped, dict):
        for member in stripped.get("members", []):
            if isinstance(member, dict):
                for key in ["partyName", "party", "partyCode"]:
                    member.pop(key, None)
    return stripped
