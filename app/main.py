import logging
import re
import time
from html import escape
from xml.sax.saxutils import escape as xml_escape
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from pathlib import Path
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

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
from app.routers.notify import router as notify_router

app = FastAPI(title="ClearVoting", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Cache-bust version — changes on every server restart
_asset_version = str(int(time.time()))


_version_re = re.compile(r'\?v=\d+')

SITE_URL = "https://clearvoting.org"

# Title-case bill abbreviations for SEO titles, e.g. "hr" -> "H.R.".
_BILL_TYPE_LABELS = {
    "hr": "H.R.",
    "s": "S.",
    "hjres": "H.J.Res.",
    "sjres": "S.J.Res.",
    "hconres": "H.Con.Res.",
    "sconres": "S.Con.Res.",
    "hres": "H.Res.",
    "sres": "S.Res.",
}

_title_re = re.compile(r"<title>.*?</title>", re.DOTALL)
_description_re = re.compile(r'<meta\s+name="description"[^>]*>', re.IGNORECASE)


def _inject_meta(html: str, meta: dict) -> str:
    """Replace the page <title> and inject SEO/social meta tags before </head>.

    Strips any static <meta name="description"> so the dynamic one isn't duplicated.
    """
    title = escape(meta["title"])
    html = _title_re.sub(f"<title>{title}</title>", html, count=1)
    html = _description_re.sub("", html, count=1)

    description = escape(meta["description"])
    og_title = escape(meta.get("og_title", meta["title"]))
    og_type = meta.get("og_type", "website")
    url = escape(meta["url"])
    tags = [
        f'<meta name="description" content="{description}">',
        f'<meta property="og:title" content="{og_title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:url" content="{url}">',
        '<meta property="og:site_name" content="ClearVoting">',
        '<meta name="twitter:card" content="summary">',
        f'<link rel="canonical" href="{url}">',
    ]
    block = "\n    " + "\n    ".join(tags) + "\n"
    return html.replace("</head>", block + "</head>", 1)


def _serve_html(filename: str, meta: dict | None = None) -> HTMLResponse:
    """Serve an HTML file with dynamic cache-bust versions and optional SEO meta."""
    html = (static_dir / filename).read_text()
    html = _version_re.sub(f"?v={_asset_version}", html)
    if meta is not None:
        html = _inject_meta(html, meta)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

app.include_router(members_router)
app.include_router(bills_router)
app.include_router(votes_router)
app.include_router(search_router)
app.include_router(feedback_router)
app.include_router(notify_router)


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


def _member_meta(member_id: str | None) -> dict:
    """SEO meta for a member page; falls back to generic copy for unknown ids."""
    from app.dependencies import get_data_service
    detail = get_data_service().get_member_detail(member_id) if member_id else None
    if not detail:
        return {
            "title": "Representative — ClearVoting",
            "description": "See how this member of Congress votes on bills — facts only, no opinions.",
            "og_type": "profile",
            "url": f"{SITE_URL}/member",
        }
    member = detail["member"]
    name = member.get("directOrderName") or member.get("name") or "Representative"
    state_code = member.get("stateCode", "")
    state = member.get("state", state_code)
    chamber = member.get("chamber", "Congress")
    title = f"{name} ({state_code}) — Voting Record | ClearVoting"
    return {
        "title": title,
        "description": (
            f"{name}, {chamber} member from {state}. "
            "See their voting record on bills before Congress."
        ),
        "og_type": "profile",
        "url": f"{SITE_URL}/member?id={member.get('bioguideId')}",
    }


def _bill_meta(congress: str | None, bill_type: str | None, number: str | None) -> dict:
    """SEO meta for a bill page; falls back to generic copy for unknown/garbage params."""
    from app.dependencies import get_data_service
    data_service = get_data_service()
    detail = None
    try:
        detail = data_service.get_bill_detail(int(congress), bill_type, int(number))
    except (TypeError, ValueError):
        detail = None
    if not detail:
        return {
            "title": "Bill — ClearVoting",
            "description": "See how Congress voted on this bill — facts only, no opinions.",
            "og_type": "article",
            "url": f"{SITE_URL}/bill",
        }
    bill = detail["bill"]
    title_text = bill.get("title", "Untitled Bill")
    label = _BILL_TYPE_LABELS.get((bill_type or "").lower(), (bill_type or "").upper())
    bill_label = f"{label} {number}"
    summary = data_service.get_ai_summary(int(congress), bill_type, int(number)) or {}
    description = summary.get("one_liner") or title_text
    canonical = f"{SITE_URL}/bill?congress={congress}&type={bill_type}&number={number}"
    return {
        "title": f"{bill_label}: {title_text} | ClearVoting",
        "description": description,
        "og_type": "article",
        "url": canonical,
    }


def _state_meta(code: str | None) -> dict:
    """SEO meta for a state page; falls back to generic copy for unknown codes."""
    from app.dependencies import get_data_service
    if not code:
        return {
            "title": "State Representatives — ClearVoting",
            "description": "See how your state's members of Congress vote — facts only, no opinions.",
            "url": f"{SITE_URL}/state",
        }
    code = code.upper()
    members = get_data_service().get_members_by_state(code)["members"]
    state_name = members[0].get("state", code) if members else code
    count = len(members)
    return {
        "title": f"{state_name} Representatives — Voting Records | ClearVoting",
        "description": (
            f"Voting records for {count} members of Congress from {state_name}. "
            "See how they vote on bills — facts only, no opinions."
        ),
        "url": f"{SITE_URL}/state?code={code}",
    }


@app.get("/")
async def serve_index():
    return _serve_html("index.html", {
        "title": "ClearVoting — See How Your Representatives Vote",
        "description": "Unbiased congressional voting records. See how your representatives vote on bills — facts only, no opinions.",
        "url": f"{SITE_URL}/",
    })


@app.get("/member")
async def serve_member(request: Request):
    return _serve_html("member.html", _member_meta(request.query_params.get("id")))


@app.get("/bill")
async def serve_bill(request: Request):
    params = request.query_params
    return _serve_html("bill.html", _bill_meta(
        params.get("congress"), params.get("type"), params.get("number")))


@app.get("/about")
async def serve_about():
    return _serve_html("about.html", {
        "title": "About — ClearVoting",
        "description": "Why we built ClearVoting and how you can help make congressional voting records accessible to everyone.",
        "url": f"{SITE_URL}/about",
    })


@app.get("/state")
async def serve_state(request: Request):
    return _serve_html("state.html", _state_meta(request.query_params.get("code")))


@app.get("/sitemap.xml")
async def serve_sitemap() -> Response:
    from app.dependencies import get_data_service
    data_service = get_data_service()
    lastmod = (data_service.get_sync_metadata().get("last_sync") or "")[:10]

    def url_tag(loc: str) -> str:
        body = f"<loc>{xml_escape(loc)}</loc>"
        if lastmod:
            body += f"<lastmod>{lastmod}</lastmod>"
        return f"<url>{body}</url>"

    locs = [f"{SITE_URL}/", f"{SITE_URL}/about"]
    locs += [f"{SITE_URL}/state?code={code}" for code in ("CA", "FL", "NY", "TX")]
    for m in data_service._members:
        if m.get("bioguideId"):
            locs.append(f"{SITE_URL}/member?id={m['bioguideId']}")
    for b in data_service._bills:
        bill_type = (b.get("type") or "").lower()
        locs.append(
            f"{SITE_URL}/bill?congress={b.get('congress')}&type={bill_type}&number={b.get('number')}"
        )

    urls = "".join(url_tag(loc) for loc in locs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


@app.get("/robots.txt")
async def serve_robots() -> PlainTextResponse:
    body = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    return PlainTextResponse(body)


@app.exception_handler(StarletteHTTPException)
async def custom_exception_handler(request: Request, exc: StarletteHTTPException):
    """Serve a friendly HTML 404 for page routes; keep JSON for the API."""
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        response = _serve_html("404.html", {
            "title": "Page Not Found — ClearVoting",
            "description": "The page you're looking for doesn't exist.",
            "url": f"{SITE_URL}{request.url.path}",
        })
        response.status_code = 404
        return response
    return await http_exception_handler(request, exc)
