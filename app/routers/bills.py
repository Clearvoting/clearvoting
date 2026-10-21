import logging
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Path, Query, Request
from app.dependencies import get_data_service
from app.limiter import limiter
from app.render import sponsor_name
from app.routers.members import _strip_party

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["bills"])

ALLOWED_FETCH_DOMAINS = {"congress.gov", "www.congress.gov", "api.congress.gov"}
VALID_BILL_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_FETCH_DOMAINS
        and "@" not in url
    )


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
def list_bills(
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
@limiter.limit("60/minute")
def get_bill(request: Request, congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_bill_detail(congress, bill_type, bill_number)
    if not result:
        raise HTTPException(status_code=404, detail="Bill not found")
    # The official summary the site shows (spec §10 #10) — Public Law first, else the newest —
    # so bill.js no longer reads summaries[0] (the oldest).
    result = {**result, "official_summary": data_service.official_summary_for(result["bill"])}
    return _bill_payload(result)
