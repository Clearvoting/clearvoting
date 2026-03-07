import re
import copy
import logging
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client
from app.services.mock_data import get_mock_members, get_mock_member_detail, get_mock_member_votes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/members", tags=["members"])

BIOGUIDE_PATTERN = re.compile(r"^[A-Z]\d{6}$")


def _is_demo() -> bool:
    from app.config import CONGRESS_API_KEY
    return not CONGRESS_API_KEY


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
    if _is_demo():
        if congress != 119:
            raise HTTPException(status_code=400, detail="Demo mode only supports the 119th Congress")
        mock = get_mock_member_votes(bioguide_id)
        if not mock:
            raise HTTPException(status_code=404, detail="Member not found")
        sorted_votes = sorted(mock["votes"], key=lambda v: v["date"], reverse=True)
        paginated = sorted_votes[offset:offset + limit]
        return {
            "member_id": mock["member_id"],
            "congress": mock["congress"],
            "stats": mock["stats"],
            "scorecard": mock.get("scorecard", []),
            "votes": paginated,
            "total_count": len(sorted_votes),
            "policy_areas": mock["policy_areas"],
        }

    # Real mode: TODO — fetch from Congress API + Senate XML
    raise HTTPException(status_code=501, detail="Real-mode voting records not yet implemented")


@router.get("/{state_code}")
async def get_members_by_state(state_code: str):
    state_code = _validate_state_code(state_code)

    if _is_demo():
        mock = get_mock_members(state_code)
        if mock:
            return _strip_party(mock)
        return {"members": []}

    client = get_congress_client()
    try:
        data = await client.get_members_by_state(state_code)
        return _strip_party(data)
    except Exception as e:
        logger.error("Congress API error in get_members_by_state: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/detail/{bioguide_id}")
async def get_member_detail(bioguide_id: str, show_party: bool = False):
    _validate_bioguide_id(bioguide_id)
    if _is_demo():
        mock = get_mock_member_detail(bioguide_id)
        if mock:
            return mock if show_party else _strip_party(mock)
        raise HTTPException(status_code=404, detail="Member not found")

    client = get_congress_client()
    try:
        data = await client.get_member(bioguide_id)
        if not show_party:
            data = _strip_party(data)
        return data
    except Exception as e:
        logger.error("Congress API error in get_member_detail: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/{state_code}/{district}")
async def get_members_by_district(state_code: str, district: int):
    state_code = _validate_state_code(state_code)

    if _is_demo():
        mock = get_mock_members(state_code)
        if mock:
            filtered = [m for m in mock["members"] if m.get("district") == district or m.get("district") is None]
            return _strip_party({"members": filtered})
        return {"members": []}

    client = get_congress_client()
    try:
        data = await client.get_members_by_district(state_code, district)
        return _strip_party(data)
    except Exception as e:
        logger.error("Congress API error in get_members_by_district: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


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
