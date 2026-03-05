import httpx
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client, get_ai_summary_service
from app.services.mock_data import get_mock_bills, get_mock_bill_detail, get_mock_ai_summary

router = APIRouter(prefix="/api/bills", tags=["bills"])


def _is_demo() -> bool:
    from app.config import CONGRESS_API_KEY
    return not CONGRESS_API_KEY


@router.get("")
async def list_bills(
    congress: int | None = None,
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
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int, bill_type: str, bill_number: int):
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
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{congress}/{bill_type}/{bill_number}/ai-summary")
async def get_ai_summary(congress: int, bill_type: str, bill_number: int):
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
        if bill_text_url:
            async with httpx.AsyncClient() as http_client:
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
        raise HTTPException(status_code=502, detail=str(e))
