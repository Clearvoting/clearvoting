import httpx
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client, get_ai_summary_service

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.get("")
async def list_bills(
    congress: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    client = get_congress_client()
    try:
        return await client.get_bills(congress=congress, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int, bill_type: str, bill_number: int):
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
