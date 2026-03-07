import logging
import httpx
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Path, Query, Request
from app.dependencies import get_congress_client, get_ai_summary_service
from app.limiter import limiter
from app.services.mock_data import get_mock_bills, get_mock_bill_detail, get_mock_ai_summary, get_mock_bill_votes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["bills"])

ALLOWED_FETCH_DOMAINS = {"congress.gov", "www.congress.gov", "api.congress.gov"}
VALID_BILL_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}


def _is_demo() -> bool:
    from app.config import CONGRESS_API_KEY
    return not CONGRESS_API_KEY


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
    if _is_demo():
        mock = get_mock_bills()
        bills = mock["bills"][offset:offset + limit]
        return {"bills": bills}

    client = get_congress_client()
    try:
        return await client.get_bills(congress=congress, offset=offset, limit=limit)
    except Exception as e:
        logger.error("Congress API error in list_bills: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    if _is_demo():
        mock = get_mock_bill_detail(congress, bill_type, bill_number)
        if mock:
            result = dict(mock)
            return result
        return {"bill": {"congress": congress, "type": bill_type.upper(), "number": str(bill_number), "title": f"{bill_type.upper()}.{bill_number}", "latestAction": {}, "summaries": []}, "subjects": {"legislativeSubjects": []}}

    client = get_congress_client()
    try:
        bill = await client.get_bill(congress, bill_type.lower(), bill_number)
        subjects = await client.get_bill_subjects(congress, bill_type.lower(), bill_number)
        bill["subjects"] = subjects
        return bill
    except Exception as e:
        logger.error("Congress API error in get_bill: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
@limiter.limit("10/minute")
async def get_ai_summary(request: Request, congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    if _is_demo():
        mock = get_mock_ai_summary(congress, bill_type, bill_number)
        if mock:
            return mock
        return {"provisions": ["No AI summary available in demo mode for this bill."], "impact_categories": []}

    congress_client = get_congress_client()
    ai_service = get_ai_summary_service()
    try:
        bill_data = await congress_client.get_bill(congress, bill_type.lower(), bill_number)
        summary_data = await congress_client.get_bill_summary(congress, bill_type.lower(), bill_number)
        text_data = await congress_client.get_bill_text(congress, bill_type.lower(), bill_number)

        bill = bill_data.get("bill", {})
        title = bill.get("title", "")

        summaries = summary_data.get("summaries", [])
        official_summary = summaries[0].get("text", "") if summaries else ""

        text_versions = text_data.get("textVersions", [])
        bill_text_url = ""
        if text_versions:
            formats = text_versions[0].get("formats", [])
            for fmt in formats:
                if fmt.get("type") == "Formatted Text":
                    bill_text_url = fmt.get("url", "")
                    break

        bill_text_excerpt = ""
        if bill_text_url and _is_safe_url(bill_text_url):
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                resp = await http_client.get(bill_text_url)
                if resp.status_code == 200:
                    bill_text_excerpt = resp.text[:5000]

        bill_id = f"{congress}-{bill_type}-{bill_number}"
        return await ai_service.generate_summary(
            bill_id=bill_id,
            title=title,
            official_summary=official_summary,
            bill_text_excerpt=bill_text_excerpt,
        )
    except Exception as e:
        logger.error("Error generating AI summary: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")


@router.get("/{congress}/{bill_type}/{bill_number}/votes")
async def get_bill_votes(congress: int = Path(ge=1, le=200), bill_type: str = Path(), bill_number: int = Path()):
    _validate_bill_type(bill_type)
    if _is_demo():
        mock = get_mock_bill_votes(congress, bill_type, bill_number)
        if mock:
            return mock
        return {"senate": [], "house": []}

    return {"senate": [], "house": []}
