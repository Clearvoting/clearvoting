import copy
from fastapi import APIRouter, HTTPException
from app.dependencies import get_congress_client, get_senate_vote_service

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.get("/house/{congress}/{session}")
async def list_house_votes(congress: int, session: int):
    client = get_congress_client()
    try:
        return await client.get_house_votes(congress, session)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/house/{congress}/{session}/{vote_number}")
async def get_house_vote(congress: int, session: int, vote_number: int, show_party: bool = False):
    client = get_congress_client()
    try:
        vote = await client.get_house_vote_detail(congress, session, vote_number)
        members = await client.get_house_vote_members(congress, session, vote_number)
        if not show_party:
            members = _strip_party_from_votes(members)
        return {"vote": vote, "members": members}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/senate/{congress}/{session}/{vote_number}")
async def get_senate_vote(congress: int, session: int, vote_number: int, show_party: bool = False):
    service = get_senate_vote_service()
    try:
        data = await service.get_vote(congress, session, vote_number)
        if not show_party:
            data = copy.deepcopy(data)
            for member in data.get("members", []):
                member.pop("party", None)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


def _strip_party_from_votes(data: dict) -> dict:
    stripped = copy.deepcopy(data)
    if isinstance(stripped, dict):
        for member in stripped.get("members", []):
            if isinstance(member, dict):
                for key in ["partyName", "party", "partyCode"]:
                    member.pop(key, None)
    return stripped
