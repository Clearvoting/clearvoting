import logging
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Path, Query, Request
from app.dependencies import get_data_service
from app.limiter import limiter

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


@router.get("")
async def list_bills(
    congress: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    data_service = get_data_service()
    return data_service.get_bills(offset=offset, limit=limit)


@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_bill_detail(congress, bill_type, bill_number)
    if not result:
        return {
            "bill": {"congress": congress, "type": bill_type.upper(), "number": str(bill_number),
                     "title": f"{bill_type.upper()}.{bill_number}", "latestAction": {}, "summaries": []},
            "subjects": {"legislativeSubjects": []}
        }
    return result


@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
@limiter.limit("10/minute")
async def get_ai_summary(request: Request, congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_ai_summary(congress, bill_type, bill_number)
    if result:
        return result
    return {"provisions": ["Summary pending — will be available after the next sync."], "impact_categories": []}


@router.get("/{congress}/{bill_type}/{bill_number}/votes")
async def get_bill_votes(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    data_service = get_data_service()
    result = data_service.get_bill_votes(congress, bill_type, bill_number)
    if result:
        return result
    return {"senate": [], "house": []}
