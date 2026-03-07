from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.routers.members import router as members_router
from app.routers.bills import router as bills_router
from app.routers.votes import router as votes_router
from app.routers.search import router as search_router

app = FastAPI(title="ClearVote", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(members_router)
app.include_router(bills_router)
app.include_router(votes_router)
app.include_router(search_router)


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
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def serve_index():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/member")
async def serve_member():
    return FileResponse(str(static_dir / "member.html"))


@app.get("/bill")
async def serve_bill():
    return FileResponse(str(static_dir / "bill.html"))
