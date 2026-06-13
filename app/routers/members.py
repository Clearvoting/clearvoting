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


@router.get("/{bioguide_id}/votes")
async def get_member_votes(
    bioguide_id: str,
    congress: int | None = Query(None, ge=1, le=200),
    limit: int = Query(20, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    data = data_service.get_member_votes(bioguide_id)
    if not data:
        raise HTTPException(status_code=404, detail="Member not found")
    votes = data["votes"]
    if congress is not None:
        votes = [v for v in votes if v.get("congress") == congress]
    sorted_votes = sorted(votes, key=lambda v: v["date"], reverse=True)
    paginated = sorted_votes[offset:offset + limit]
    return {
        "member_id": data["member_id"],
        "congresses": data.get("congresses", [data["congress"]] if "congress" in data else [119]),
        "stats": data["stats"],
        "scorecard": data.get("scorecard", []),
        "votes": paginated,
        "total_count": len(sorted_votes),
        "policy_areas": data["policy_areas"],
        "categories": data.get("categories", []),
    }


@router.get("/{bioguide_id}/summary")
async def get_member_summary(bioguide_id: str):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    summary = data_service.get_member_vote_summary(bioguide_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Member not found")

    # Include AI narrative if available
    narrative = data_service.get_member_narrative(bioguide_id)
    if narrative:
        summary["narrative"] = narrative.get("narrative", "")
        summary["narrative_top_areas"] = narrative.get("top_areas", [])

    # Include issue scorecard from member votes
    votes_data = data_service.get_member_votes(bioguide_id)
    if votes_data:
        summary["issue_scorecard"] = votes_data.get("scorecard", [])

    return summary


@router.get("/counts")
async def get_member_counts():
    """Members synced per state — powers the homepage state cards with real
    numbers rather than theoretical seat totals."""
    data_service = get_data_service()
    return {"counts": data_service.get_member_counts()}


@router.get("/{state_code}/overview")
async def get_state_overview(state_code: str, show_party: bool = False):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    members_data = data_service.get_members_by_state(state_code)
    members = members_data.get("members", [])

    enriched = []
    total_participation = 0.0
    total_support = 0.0
    total_votes_all = 0
    count_with_stats = 0

    for m in members:
        bio_id = m.get("bioguideId", "")
        votes_data = data_service.get_member_votes(bio_id)
        stats = votes_data.get("stats", {}) if votes_data else {}
        narrative_data = data_service.get_member_narrative(bio_id)
        narrative_snippet = ""
        if narrative_data:
            full = narrative_data.get("narrative", "")
            narrative_snippet = full[:150] + "..." if len(full) > 150 else full

        participation = stats.get("participation_rate", 0)
        yea = stats.get("yea_count", 0)
        nay = stats.get("nay_count", 0)
        total_v = stats.get("total_votes", 0)
        support_rate = round(yea / (yea + nay) * 100) if (yea + nay) > 0 else 0

        enriched.append({
            **m,
            "participation_rate": participation,
            "support_rate": support_rate,
            "total_votes": total_v,
            "yea_count": yea,
            "nay_count": nay,
            "narrative_snippet": narrative_snippet,
        })

        if total_v > 0:
            total_participation += participation
            total_support += support_rate
            total_votes_all += total_v
            count_with_stats += 1

    avg_participation = round(total_participation / count_with_stats) if count_with_stats else 0
    avg_support = round(total_support / count_with_stats) if count_with_stats else 0

    result = {
        "members": enriched,
        "aggregate": {
            "total_members": len(members),
            "avg_participation": avg_participation,
            "avg_support_rate": avg_support,
            "total_votes": total_votes_all,
        },
    }
    return result if show_party else _strip_party(result)


@router.get("/{state_code}")
async def get_members_by_state(
    state_code: str,
    include_stats: bool = Query(False, description="Include vote stats and narrative snippet per member"),
):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_state(state_code)
    if include_stats:
        for m in data.get("members", []):
            bio_id = m.get("bioguideId", "")
            votes_data = data_service.get_member_votes(bio_id)
            if votes_data:
                m["stats"] = votes_data.get("stats", {})
            narrative_data = data_service.get_member_narrative(bio_id)
            if narrative_data:
                full = narrative_data.get("narrative", "")
                m["narrative_snippet"] = full[:150] + "..." if len(full) > 150 else full
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
async def get_members_by_district(
    state_code: str,
    district: int,
    include_stats: bool = Query(False, description="Include vote stats and narrative snippet per member"),
):
    state_code = _validate_state_code(state_code)
    data_service = get_data_service()
    data = data_service.get_members_by_district(state_code, district)
    if include_stats:
        for m in data.get("members", []):
            bio_id = m.get("bioguideId", "")
            votes_data = data_service.get_member_votes(bio_id)
            if votes_data:
                m["stats"] = votes_data.get("stats", {})
            narrative_data = data_service.get_member_narrative(bio_id)
            if narrative_data:
                full = narrative_data.get("narrative", "")
                m["narrative_snippet"] = full[:150] + "..." if len(full) > 150 else full
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
