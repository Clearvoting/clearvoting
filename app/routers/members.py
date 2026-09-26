import re
import copy
import logging
from fastapi import APIRouter, HTTPException, Query
from app import render
from app.dependencies import get_data_service
from app.services.data_service import RECORD_API_MAX_GROUPS

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


@router.get("/{bioguide_id}/donations")
async def get_member_donations(bioguide_id: str):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    donations = data_service.get_member_donations(bioguide_id)
    if not donations:
        raise HTTPException(status_code=404, detail="Donation data not available for this member")
    return donations


@router.get("/{bioguide_id}/sponsored")
async def get_member_sponsored_bills(bioguide_id: str):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    bills = data_service.get_bills_by_sponsor(bioguide_id)
    return {"bills": bills, "count": len(bills)}


_POSITION_PATTERN = "^(yes|no|nv)$"


@router.get("/{bioguide_id}/votes")
async def get_member_votes(
    bioguide_id: str,
    congress: int | None = Query(None, ge=1, le=200),
    limit: int = Query(20, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    group: str | None = Query(None, pattern="^bill$", description="'bill' returns the record grouped by bill (at most 50 groups)"),
    plain: bool = Query(False, description="Only votes on bills with a plain-English summary"),
    policy_area: str | None = Query(None, max_length=120),
    position: str | None = Query(None, pattern=_POSITION_PATTERN),
    show_party: bool = Query(False, description="Include party labels and Speaker candidate names"),
):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    if group == "bill":
        record = data_service.get_member_record(
            bioguide_id, topic=policy_area, position=position, plain=plain, congress=congress)
        if record is None:
            raise HTTPException(status_code=404, detail="Member not found")
        page_size = min(limit, RECORD_API_MAX_GROUPS)
        return _allowlist_member_payload({
            "member_id": bioguide_id.upper(),
            "groups": record["groups"][offset:offset + page_size],
            "total_groups": record["total_groups"],
            "matching_bills": record["matching_bills"],
            "limit": page_size,
            "offset": offset,
            "topic": record["topic"],
            "position": record["position"],
            "plain": record["plain"],
            "policy_areas": record["policy_areas"],
            "plain_bills": record["plain_bills"],
            "total_bills": record["total_bills"],
        }, show_party)
    data = data_service.get_member_votes(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    votes = data["votes"]
    if congress is not None:
        votes = [v for v in votes if v.get("congress") == congress]
    if policy_area or position or plain:
        votes = data_service.filter_member_votes(votes, policy_area, position, plain)
    sorted_votes = sorted(votes, key=lambda v: v["date"], reverse=True)
    paginated = sorted_votes[offset:offset + limit]
    return _allowlist_member_payload({
        "member_id": data["member_id"],
        "congresses": data.get("congresses", [data["congress"]] if "congress" in data else [119]),
        "stats": data["stats"],
        "votes": paginated,
        "total_count": len(sorted_votes),
        "policy_areas": data["policy_areas"],
        "categories": data.get("categories", []),
    }, show_party)


@router.get("/{bioguide_id}/page")
def get_member_page(
    bioguide_id: str,
    page: int = Query(1, ge=1, le=10000),
    topic: str | None = Query(None, max_length=120),
    position: str | None = Query(None, pattern=_POSITION_PATTERN),
    plain: bool = Query(False),
):
    """The member page payload (spec §10 #8): the same dict the server-rendered page uses.
    Registered before /{state_code}/{district}, which would otherwise capture /S000148/page."""
    _validate_bioguide_id(bioguide_id)
    result = get_data_service().get_member_page(bioguide_id, page, topic, position, plain)
    if result is None:
        raise HTTPException(status_code=404, detail="Member not found")
    # The record's render tree (plan T10.2) comes from the full page, like the HTML; it holds
    # no party field, no Speaker candidate name and no stance text.
    record = render.record_tree(result)   # {"result": node, "list": node}
    return {**_allowlist_member_payload(result), "record_tree": record}


@router.get("/counts")
async def get_member_counts():
    """Members synced per state — powers the homepage state cards with real
    numbers rather than theoretical seat totals."""
    data_service = get_data_service()
    return {"counts": data_service.get_member_counts()}


@router.get("/{state_code}/overview")
def get_state_overview(
    state_code: str,
    show_party: bool = Query(False, description="Include party labels (hidden by default)"),
):
    """One state's delegation for the home block, the bill slot and the party reveal:
    one cached file read, no per-member vote files (F05)."""
    state_code = _validate_state_code(state_code)
    if state_code not in render.COVERED_STATE_NAMES:
        raise HTTPException(status_code=404, detail="State not covered")
    data_service = get_data_service()
    # The committed file; if it is missing, T1.6's members.json roster without signal lines.
    overview = data_service.get_state_overview(state_code, fallback=True) or {}
    payload = {
        "state": overview.get("state") or state_code,
        "state_name": overview.get("state_name"),
        "roster_as_of": overview.get("roster_as_of"),
        "generated_at": overview.get("generated_at"),
        "districts_expected": overview.get("districts_expected"),
        "senators": [render.overview_member_fields(m, data_service) for m in overview.get("senators") or []],
        "house": [render.overview_member_fields(m, data_service) for m in overview.get("house") or []],
    }
    return payload if show_party else _strip_party(payload)


@router.get("/{state_code}")
async def get_members_by_state(
    state_code: str,
    show_party: bool = Query(False, description="Include party labels (hidden by default)"),
):
    state_code = _validate_state_code(state_code)
    data = get_data_service().get_members_by_state(state_code)
    return data if show_party else _strip_party(data)


@router.get("/detail/{bioguide_id}")
async def get_member_detail(bioguide_id: str, show_party: bool = False):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    data = data_service.get_member_detail(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    if not show_party:
        return _allowlist_member_payload(data)
    # The party reveal (§4.3) also fills each Speaker row's "Voted for {Name}".
    return _allowlist_member_payload(
        {**data, "speaker_votes": data_service.get_speaker_votes(bioguide_id)}, show_party=True)


@router.get("/{state_code}/{district}")
async def get_members_by_district(state_code: str, district: int):
    state_code = _validate_state_code(state_code)
    data = get_data_service().get_members_by_district(state_code, district)
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


# Member payloads carry no scores, stance labels or cost figures, and no party cue unless
# the reader asked (spec §10 #9). Position strings that are not a candidate name:
_KNOWN_POSITIONS = frozenset({
    "Yea", "Aye", "Nay", "No", "Not Voting", "Present", "Present, Giving Live Pair",
    "Guilty", "Not Guilty", "yes", "no",
})
_MEMBER_PAYLOAD_DROP = frozenset({
    "scorecard", "issue_scorecard", "direction", "participation_rate", "narrative", "narrative_top_areas",
})
_PARTY_KEYS = frozenset({"party", "partyName", "partyCode"})


def _allowlist_member_payload(data: dict, show_party: bool = False) -> dict:
    """Copy of a member payload without scorecard/direction/participation_rate/cbo_* and,
    unless show_party, without party keys and Speaker-election candidate names (a vote for
    a party's nominee is a party cue): the position becomes 'Voted' and the result
    'Speaker elected'."""
    cleaned = copy.deepcopy(data)

    def walk(obj):
        if isinstance(obj, dict):
            for key in list(obj):
                if (key in _MEMBER_PAYLOAD_DROP or key.startswith("cbo_")
                        or (key in _PARTY_KEYS and not show_party)):
                    del obj[key]
            if not show_party:
                vote = obj.get("vote")
                if isinstance(vote, str) and vote not in _KNOWN_POSITIONS:
                    obj["vote"] = "Voted"
                    if "result" in obj:
                        obj["result"] = "Speaker elected"
                if obj.get("question") == "Election of the Speaker" and "result" in obj:
                    obj["result"] = "Speaker elected"
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(cleaned)
    return cleaned
