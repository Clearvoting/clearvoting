import logging
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import get_congress_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/bills")
async def search_bills(
    q: str = Query(..., min_length=1),
    congress: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    # TODO: q parameter is accepted but not passed to Congress API — search
    # currently returns unfiltered bills. Client-side filtering in app.js
    # handles the search logic for now. This should be fixed when implementing
    # real full-text search.
    logger.warning("Search query '%s' accepted but not used — results are unfiltered", q)
    client = get_congress_client()
    try:
        data = await client.get_bills(congress=congress, offset=offset, limit=limit)
        return data
    except Exception as e:
        logger.error("Congress API error in search_bills: %s", e)
        raise HTTPException(status_code=502, detail="External service temporarily unavailable")
