import copy
import logging
from fastapi import APIRouter, HTTPException, Path
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.get("/senate/{congress}/{session}/{vote_number}")
async def get_senate_vote(congress: int = Path(ge=1, le=200), session: int = Path(ge=1, le=3), vote_number: int = Path(), show_party: bool = False):
    data_service = get_data_service()
    data = data_service.get_senate_vote(congress, session, vote_number)
    if not data:
        raise HTTPException(status_code=404, detail="Vote not found")
    if not show_party:
        data = copy.deepcopy(data)
        for member in data.get("members", []):
            member.pop("party", None)
    return data
