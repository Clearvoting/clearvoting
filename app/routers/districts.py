"""GET /api/districts/{zip}: ZIP → congressional district(s) in the four covered states (spec §5.2).

Used by the bill page's in-place ZIP form and by tests; the /state route calls the same
DataService.lookup_zip in process. The answer changes only when the crosswalk file is
redeployed, so 200s are cacheable for a day."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.dependencies import get_data_service
from app.limiter import limiter
from app.services.data_service import normalize_zip

router = APIRouter(prefix="/api/districts", tags=["districts"])

ZIP_ERROR = "A ZIP code is five digits"
DAY_CACHE = "public, max-age=86400, s-maxage=86400"


@router.get("/{zip_code}")
@limiter.limit("60/minute")
async def get_districts(request: Request, response: Response, zip_code: str):
    zip5 = normalize_zip(zip_code)
    if zip5 is None:
        return JSONResponse(status_code=400, content={"detail": ZIP_ERROR}, headers={"Cache-Control": "no-store"})
    response.headers["Cache-Control"] = DAY_CACHE
    return get_data_service().lookup_zip(zip5)
