import logging
from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from app.dependencies import get_data_service
from app.limiter import limiter
from app.render import sponsor_name
from app.routers.members import _strip_party

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["bills"])

VALID_BILL_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}


def _validate_bill_type(bill_type: str) -> None:
    if bill_type.lower() not in VALID_BILL_TYPES:
        raise HTTPException(status_code=400, detail="Invalid bill type")


def _bill_payload(result: dict) -> dict:
    """Default bill payload: no party anywhere, sponsor fullName rebuilt without "[R-AL-6]" (§10 #9)."""
    payload = _strip_party(result)
    for sponsor in (payload.get("bill") or {}).get("sponsors") or []:
        sponsor["fullName"] = sponsor_name(sponsor)
    return payload


# Fields the home Record and browse panel read, for every bill *list* payload
# (/api/bills and /api/search/bills). Sponsors/cosponsors (party letters, "[R-AL-6]"
# in fullName) never leave in a list (spec §2.2 #10, §10 #9).
LIST_FIELDS = ("congress", "type", "number", "title", "introducedDate", "latestAction",
               "policyArea", "laws", "one_liner", "provisions", "issue_categories",
               "derived_status", "activity_date")


@router.get("")
async def list_bills(
    congress: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    summarized_only: bool = Query(False, description="Only bills with a plain-language AI summary"),
):
    data_service = get_data_service()
    data = data_service.get_bills(
        offset=offset, limit=limit, congress=congress, summarized_only=summarized_only
    )
    return {**data, "bills": [{k: b[k] for k in LIST_FIELDS if k in b} for b in data["bills"]]}


@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_bill_detail(congress, bill_type, bill_number)
    if not result:
        raise HTTPException(status_code=404, detail="Bill not found")
    # The official summary the site shows (spec §10 #10) — Public Law first, else the newest —
    # so bill.js no longer reads summaries[0] (the oldest).
    result = {**result, "official_summary": data_service.official_summary_for(result["bill"])}
    return _bill_payload(result)


@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
@limiter.limit("10/minute")
async def get_ai_summary(request: Request, congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    bill_id = f"{congress}-{bill_type.lower()}-{bill_number}"
    summary = data_service.get_ai_summary(congress, bill_type, bill_number)
    if not summary or not data_service.displayable_summary(bill_id):
        return JSONResponse(status_code=404, content={"available": False})
    return {"one_liner": summary.get("one_liner"), "provisions": summary.get("provisions") or []}


@router.get("/{congress}/{bill_type}/{bill_number}/votes")
def get_bill_votes(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    # Additive per roll call (spec §10 #10): plain_question, seal, outcome, state_tallies on
    # every roll call; covered only on the at most two the bill page renders (§4.4 m3, §9.6).
    return get_data_service().get_bill_votes_payload(congress, bill_type, bill_number)
