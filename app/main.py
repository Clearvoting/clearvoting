import logging
import re
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from slowapi.middleware import SlowAPIMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.limiter import limiter
from app.routers.members import router as members_router
from app.routers.bills import router as bills_router
from app.routers.votes import router as votes_router
from app.routers.search import router as search_router
from app.routers.feedback import router as feedback_router

app = FastAPI(title="ClearVoting", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Cache-bust version — changes on every server restart
_asset_version = str(int(time.time()))


_version_re = re.compile(r'\?v=\d+')


def _serve_html(filename: str) -> HTMLResponse:
    """Serve an HTML file with dynamic cache-bust versions on static assets."""
    html = (static_dir / filename).read_text()
    html = _version_re.sub(f"?v={_asset_version}", html)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

app.include_router(members_router)
app.include_router(bills_router)
app.include_router(votes_router)
app.include_router(search_router)
app.include_router(feedback_router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https://www.congress.gov; "
        "script-src 'self'; "
        "connect-src 'self'"
    )
    return response


@app.get("/api/health")
async def health_check() -> dict:
    from app.dependencies import get_data_service
    data_service = get_data_service()
    metadata = data_service.get_sync_metadata()
    # Record counts from the in-memory stores — a sync that wipes data shows up here
    bills = len(data_service._bills)
    ai_summaries = len(data_service._ai_summaries)
    return {
        "status": "ok",
        "version": "0.1.0",
        "last_sync": metadata.get("last_sync"),
        "members": len(data_service._members),
        "bills": bills,
        "ai_summaries": ai_summaries,
        "member_summaries": len(data_service._member_summaries),
        "summary_coverage": round(ai_summaries / bills, 2) if bills else 0,
    }


@app.get("/")
async def serve_index():
    return _serve_html("index.html")


@app.get("/member")
async def serve_member():
    return _serve_html("member.html")


@app.get("/bill")
async def serve_bill():
    return _serve_html("bill.html")


@app.get("/about")
async def serve_about():
    return _serve_html("about.html")


@app.get("/state")
async def serve_state():
    return _serve_html("state.html")
