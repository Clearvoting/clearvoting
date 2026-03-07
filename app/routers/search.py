import logging
from fastapi import APIRouter, Query
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/bills")
async def search_bills(
    q: str = Query(..., min_length=1),
    congress: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    data_service = get_data_service()
    all_bills = data_service.get_bills(offset=0, limit=10000)
    q_lower = q.lower()
    filtered = [b for b in all_bills["bills"] if q_lower in b.get("title", "").lower()]
    paginated = filtered[offset:offset + limit]
    return {"bills": paginated}
