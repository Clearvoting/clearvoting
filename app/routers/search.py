import logging
from fastapi import APIRouter, Query
from app.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

# Map user-friendly category names to policyArea values in the data
CATEGORY_MAP: dict[str, list[str]] = {
    "cost of living": ["economics and public finance", "commerce"],
    "healthcare": ["health"],
    "jobs & workers": ["labor and employment"],
    "taxes": ["taxation"],
    "safety & crime": ["crime and law enforcement"],
    "education": ["education"],
    "money in politics": ["government operations and politics"],
    "housing": ["housing and community development"],
    "immigration": ["immigration"],
    "environment & energy": ["environmental protection", "energy"],
    "veterans & military": ["armed forces and national security"],
    "social security & retirement": ["social welfare"],
}


def _bill_matches(bill: dict, q_lower: str) -> bool:
    """Check if a bill matches the query against title, policyArea, and subjects."""
    # Check title
    if q_lower in bill.get("title", "").lower():
        return True
    # Check the plain-language one-liner ("stablecoin" should find the GENIUS Act)
    if q_lower in bill.get("one_liner", "").lower():
        return True
    # Check policyArea name
    policy_area = bill.get("policyArea", {})
    if policy_area and q_lower in policy_area.get("name", "").lower():
        return True
    # Check mapped category
    mapped_areas = CATEGORY_MAP.get(q_lower, [])
    if mapped_areas:
        pa_name = policy_area.get("name", "").lower() if policy_area else ""
        if pa_name in mapped_areas:
            return True
    return False


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
    filtered = [b for b in all_bills["bills"] if _bill_matches(b, q_lower)]
    paginated = filtered[offset:offset + limit]
    return {"bills": paginated, "total": len(filtered)}
