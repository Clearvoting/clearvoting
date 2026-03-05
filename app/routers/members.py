import copy
from fastapi import APIRouter, HTTPException
from app.dependencies import get_congress_client

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("/{state_code}")
async def get_members_by_state(state_code: str):
    state_code = state_code.upper()
    if len(state_code) != 2:
        raise HTTPException(status_code=400, detail="State code must be 2 letters")
    client = get_congress_client()
    try:
        data = await client.get_members_by_state(state_code)
        return _strip_party(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Congress API error: {str(e)}")


@router.get("/detail/{bioguide_id}")
async def get_member_detail(bioguide_id: str, show_party: bool = False):
    client = get_congress_client()
    try:
        data = await client.get_member(bioguide_id)
        if not show_party:
            data = _strip_party(data)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Congress API error: {str(e)}")


@router.get("/{state_code}/{district}")
async def get_members_by_district(state_code: str, district: int):
    state_code = state_code.upper()
    client = get_congress_client()
    try:
        data = await client.get_members_by_district(state_code, district)
        return _strip_party(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Congress API error: {str(e)}")


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
