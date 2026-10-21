import re
import copy
import logging
from fastapi import APIRouter, HTTPException, Query, Request
from app import render
from app.dependencies import get_data_service
from app.limiter import limiter

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


_POSITION_PATTERN = "^(yes|no|nv)$"


@router.get("/{bioguide_id}/page")
@limiter.limit("60/minute")
def get_member_page(
    request: Request,
    bioguide_id: str,
    page: int = Query(1, ge=1, le=10000),
    topic: str | None = Query(None, max_length=120),
    position: str | None = Query(None, pattern=_POSITION_PATTERN),
    plain: bool = Query(False),
):
    """The member page payload (spec §10 #8): the same dict the server-rendered page uses."""
    _validate_bioguide_id(bioguide_id)
    result = get_data_service().get_member_page(bioguide_id, page, topic, position, plain)
    if result is None:
        raise HTTPException(status_code=404, detail="Member not found")
    # The record's render tree (plan T10.2) comes from the full page, like the HTML; it holds
    # no party field, no Speaker candidate name and no stance text.
    record = render.record_tree(result)   # {"result": node, "list": node}
    return {**_allowlist_member_payload(result), "record_tree": record}


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


@router.get("/detail/{bioguide_id}")
@limiter.limit("60/minute")
def get_member_detail(request: Request, bioguide_id: str, show_party: bool = False):
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
