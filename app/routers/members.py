import re
import copy
import logging
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/members", tags=["members"])

BIOGUIDE_PATTERN = re.compile(r"^[A-Z]\d{6}$")


def _validate_bioguide_id(bioguide_id: str) -> None:
    if not BIOGUIDE_PATTERN.match(bioguide_id.upper()):
        raise HTTPException(status_code=400, detail="Invalid member ID format")


def _validate_state_code(state_code: str) -> str:
    if not state_code.isalpha() or len(state_code) != 2:
        raise HTTPException(status_code=400, detail="State code must be 2 letters")
    return state_code.upper()


@router.get("/{bioguide_id}/votes")
async def get_member_votes(
    bioguide_id: str,
    congress: int = Query(119, ge=1, le=200),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    data = data_service.get_member_votes(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    sorted_votes = sorted(data["votes"], key=lambda v: v["date"], reverse=True)
    paginated = sorted_votes[offset:offset + limit]
    return {
        "member_id": data["member_id"],
        "congresses": data.get("congresses", [data["congress"]] if "congress" in data else [119]),
        "stats": data["stats"],
        "scorecard": data.get("scorecard", []),
        "votes": paginated,
        "total_count": len(sorted_votes),
        "policy_areas": data["policy_areas"],
    }


@router.get("/{bioguide_id}/summary")
async def get_member_summary(bioguide_id: str):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    summary = data_service.get_member_vote_summary(bioguide_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Member not found")
    return summary


@router.get("/{state_code}")
async def get_members_by_state(state_code: str):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_state(state_code)
    return _strip_party(data)


@router.get("/detail/{bioguide_id}")
async def get_member_detail(bioguide_id: str, show_party: bool = False):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    data = data_service.get_member_detail(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    return data if show_party else _strip_party(data)


@router.get("/{state_code}/{district}")
async def get_members_by_district(state_code: str, district: int):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_district(state_code, district)
    return _strip_party(data)


def _strip_party(data: dict) -> dict:
    """Remove party information from member data for default display."""
    stripped = copy.deepcopy(data)

    def _remove_party_fields(obj):
        if isinstance(obj, dict):
            for key in ["partyName", "party", "partyCode"]:
                obj.pop(key, None)
            for value in obj.values():
                _remove_party_fields(value)
        elif isinstance(obj, list):
            for item in obj:
                _remove_party_fields(item)

    _remove_party_fields(stripped)
    return stripped
