from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/bills")
async def search_bills(
    q: str = Query(..., min_length=1),
    congress: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    client = get_congress_client()
    try:
        data = await client.get_bills(congress=congress, offset=offset, limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
