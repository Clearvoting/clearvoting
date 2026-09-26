import hashlib
import logging
import mimetypes
import os
import re
from datetime import datetime, timezone
from html import escape
from xml.sax.saxutils import escape as xml_escape
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from pathlib import Path
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# python:3.12-slim has no /etc/mime.types; make sure fonts are served as fonts.
mimetypes.add_type("font/woff2", ".woff2")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

from app.limiter import limiter
from app import render
from app.render import _BILL_TYPE_LABELS, bill_displayable, cut_words, display_name, format_bill_code, render_bill_page
from app.routers.members import router as members_router, BIOGUIDE_PATTERN
from app.routers.bills import router as bills_router, VALID_BILL_TYPES
from app.routers.votes import router as votes_router
from app.routers.search import router as search_router
from app.routers.feedback import router as feedback_router
from app.routers.notify import router as notify_router
from app.routers.districts import router as districts_router
from app.services.ai_summary import SYSTEM_PROMPT

app = FastAPI(title="ClearVoting", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _compute_asset_version(static_root: Path, environ) -> str:
    """Cache-bust token for ?v= links (§9.5).

    RENDER_GIT_COMMIT (first 12 characters) when Render sets it; otherwise a hash
    of the static/ file list with sizes and mtimes, computed once at startup, so an
    idle restart of the same deploy keeps the same ?v= (the old process-start
    timestamp changed it several times a day and defeated the immutable cache).
    """
    commit = str(environ.get("RENDER_GIT_COMMIT") or "").strip()
    if _COMMIT_RE.match(commit):
        return commit[:12].lower()
    digest = hashlib.sha256()
    for path in sorted(p for p in static_root.rglob("*") if p.is_file()):
        stat = path.stat()
        digest.update(f"{path.relative_to(static_root).as_posix()}:{stat.st_size}:{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()[:12]


_asset_version = _compute_asset_version(static_dir, os.environ)


_version_re = re.compile(r'\?v=\d+')

SITE_URL = "https://clearvoting.org"

_title_re = re.compile(r"<title>.*?</title>", re.DOTALL)
_description_re = re.compile(r'<meta\s+name="description"[^>]*>', re.IGNORECASE)
_h1_re = re.compile(r"(<h1\b[^>]*>).*?(</h1>)", re.DOTALL)

_TITLE_SUFFIX = " | ClearVoting"
_OG_TITLE_MAX = 90
_ISO_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _og_title(title: str) -> str:
    """og:title = the page title without ' | ClearVoting', at most 90 characters (§9.2).

    render.cut_words(text, n) can return n + 1 characters (the '…'), so the cut is at 89.
    """
    base = title.removesuffix(_TITLE_SUFFIX)
    return base if len(base) <= _OG_TITLE_MAX else cut_words(base, _OG_TITLE_MAX - 1)


def _normalize_bill_params(congress, bill_type, number) -> tuple[int, str, int] | None:
    """(congress, lower-case type, number) by the rule T7.4's serve_bill applies, or None.

    Used by the sitemap so every bill URL it lists is one serve_bill answers with a 200.
    """
    congress_raw = str(congress if congress is not None else "").strip()
    number_raw = str(number if number is not None else "").strip()
    type_lower = str(bill_type or "").strip().lower()
    if not (congress_raw.isdigit() and number_raw.isdigit()) or type_lower not in VALID_BILL_TYPES:
        return None
    congress_int, number_int = int(congress_raw), int(number_raw)
    if not 1 <= congress_int <= 200 or number_int < 1:
        return None
    return congress_int, type_lower, number_int


def _iso_day(value) -> str | None:
    day = str(value or "")[:10]
    return day if _ISO_DAY_RE.match(day) else None


def _inject_meta(html: str, meta: dict) -> str:
    """Replace the page <title> and inject SEO/social meta tags before </head>.

    Strips any static <meta name="description"> so the dynamic one isn't duplicated.
    Optional keys: og_type, og_title, image {path, width, height, alt},
    canonical (False omits the canonical link and og:url), h1 (replaces the
    text of the shell's first <h1>). Runs before content is injected, so h1
    only ever touches the shell's own heading.
    """
    title = escape(meta["title"])
    html = _title_re.sub(lambda _m: f"<title>{title}</title>", html, count=1)
    html = _description_re.sub("", html, count=1)
    if meta.get("h1"):
        h1_text = escape(meta["h1"])
        html = _h1_re.sub(lambda m: f"{m.group(1)}{h1_text}{m.group(2)}", html, count=1)

    description = escape(meta["description"])
    og_title = escape(meta.get("og_title") or _og_title(meta["title"]))
    og_type = escape(meta.get("og_type", "website"))
    canonical = meta.get("canonical", meta.get("url"))
    image = meta.get("image")
    tags = [
        f'<meta name="description" content="{description}">',
        f'<meta property="og:title" content="{og_title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:type" content="{og_type}">',
    ]
    if canonical:
        tags.append(f'<meta property="og:url" content="{escape(canonical)}">')
    tags.append('<meta property="og:site_name" content="ClearVoting">')
    if image:
        tags += [
            f'<meta property="og:image" content="{escape(SITE_URL + image["path"])}">',
            f'<meta property="og:image:width" content="{int(image.get("width", 1200))}">',
            f'<meta property="og:image:height" content="{int(image.get("height", 630))}">',
            f'<meta property="og:image:alt" content="{escape(image["alt"])}">',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
    else:
        tags.append('<meta name="twitter:card" content="summary">')
    if canonical:
        tags.append(f'<link rel="canonical" href="{escape(canonical)}">')
    block = "\n    " + "\n    ".join(tags) + "\n"
    return html.replace("</head>", block + "</head>", 1)


_freshness_re = re.compile(r'<span id="data-freshness">\s*</span>')


def _freshness_text() -> str:
    """Footer freshness (spec §6.4 footer, §7.4): " · Synced September 5, 2026", or "" when
    last_sync is absent. The separator is inside the span so nothing dangles; no JS writes it."""
    from app.dependencies import get_data_service
    from app.render import format_date
    last_sync = get_data_service().get_sync_metadata().get("last_sync")
    if not last_sync:
        return ""
    try:
        formatted = format_date(str(last_sync)[:10])
    except (TypeError, ValueError, IndexError):
        return ""
    return f" · Synced {escape(formatted)}" if formatted else ""


def _fill_freshness(html: str) -> str:
    return _freshness_re.sub(
        lambda _match: f'<span id="data-freshness">{_freshness_text()}</span>', html, count=1)


def _edition_html() -> str:
    from app.dependencies import get_data_service
    data_service = get_data_service()
    return render.render_edition(
        data_service.get_sync_metadata().get("last_sync"),
        data_service.latest_roll_call_date(),
        datetime.now(timezone.utc),
    )


def _page_content(build, meta: dict) -> tuple[str, int]:
    """Run a page's server renderer. If the data is missing at request time, log it and
    return the spec §4 error state with 503, which the cache rules treat as no-store."""
    try:
        return build(), 200
    except Exception:
        logger.exception("server render failed for %s", meta.get("url"))
        h1 = meta.get("h1") or meta["title"].split(" | ")[0]
        return render.render_error(h1), 503


def _serve_html(filename: str, meta: dict | None = None, content_html: str | None = None, status_code: int = 200) -> HTMLResponse:
    """Serve a shell: cache-bust versions, SEO meta, then the edition line and server-rendered content (plan T3.1)."""
    html = (static_dir / filename).read_text()
    html = _version_re.sub(f"?v={_asset_version}", html)
    html = _fill_freshness(html)
    if meta is not None:
        html = _inject_meta(html, meta)
    if "<!--edition-->" in html:
        html = html.replace("<!--edition-->", _edition_html(), 1)
    # Content last: the ?v= rewrite, <title>/</head> injection and freshness fill never
    # see server-rendered data (spec §9.1, §9.2).
    if content_html is not None:
        html = html.replace("<!--content-->", content_html, 1)
    return HTMLResponse(html, status_code=status_code)

app.include_router(members_router)
app.include_router(bills_router)
app.include_router(votes_router)
app.include_router(search_router)
app.include_router(feedback_router)
app.include_router(notify_router)
app.include_router(districts_router)


CACHE_NO_STORE = "no-store"
CACHE_404 = "public, max-age=60"
CACHE_STATIC = "public, max-age=31536000, immutable"
CACHE_OG = "public, max-age=86400"
CACHE_FAVICON = "public, max-age=31536000"
CACHE_HTML = "public, max-age=0, s-maxage=600, stale-while-revalidate=3600"
CACHE_ZIP_REDIRECT = "public, max-age=0, s-maxage=86400"
CACHE_API = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"

_HTML_ROUTES = frozenset({"/", "/state", "/member", "/bill", "/about", "/methodology", "/privacy"})
_NO_STORE_ROUTES = frozenset({"/api/health", "/api/notify", "/api/feedback"})
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def _cache_control_for(method: str, path: str, query, status: int, existing: str | None) -> str | None:
    """Cache-Control by status first, then by route (spec §9.5).

    Returns the header value to set, or None to leave the response untouched.
    Nothing per-visitor is ever in the HTML (cv-home and the party reveal live in
    the browser), so shells and data are safe to share at the edge.
    """
    if status >= 500 or (400 <= status < 500 and status != 404):
        return CACHE_NO_STORE
    if status == 404:
        return CACHE_404
    if method not in ("GET", "HEAD") or path in _NO_STORE_ROUTES:
        return CACHE_NO_STORE
    if status in _REDIRECT_STATUSES:
        # The ZIP lookup is static per deploy; any other redirect is not cached.
        return CACHE_ZIP_REDIRECT if path == "/state" and "zip" in query else CACHE_NO_STORE
    if status not in (200, 304):
        return existing
    if path.startswith("/static/og/"):
        return CACHE_OG
    if path.startswith("/static/"):
        return CACHE_STATIC
    if path == "/favicon.ico":
        return CACHE_FAVICON
    if path.startswith("/api/"):
        # /api/districts sets its own day-long header (§5.2); keep a route's own value.
        return existing or CACHE_API
    if path in _HTML_ROUTES:
        return CACHE_HTML
    return existing


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' https://www.congress.gov; "
        "script-src 'self'; "
        "connect-src 'self'"
    )
    path = request.url.path
    if path.startswith("/static/") and path.endswith(".html"):
        response.headers["X-Robots-Tag"] = "noindex"
    cache_control = _cache_control_for(
        request.method,
        request.url.path,
        request.query_params,
        response.status_code,
        response.headers.get("cache-control"),
    )
    if cache_control:
        response.headers["Cache-Control"] = cache_control
    return response


@app.get("/api/health")
async def health_check() -> dict:
    from app.dependencies import get_data_service
    data_service = get_data_service()
    metadata = data_service.get_sync_metadata()
    # Record counts from the in-memory stores — a sync that wipes data shows up here
    bills = len(data_service._bills)
    ai_summaries = len(data_service._ai_summaries)
    # Intersected coverage: bills that actually have a summary, precise to 4
    # places so a near-miss (1521/1525) can never round up to a clean 1.0.
    bill_keys = {
        f"{b.get('congress')}-{str(b.get('type', '')).lower()}-{b.get('number')}"
        for b in data_service._bills
    }
    covered = len(bill_keys & set(data_service._ai_summaries))
    return {
        "status": "ok",
        "version": "0.1.0",
        "last_sync": metadata.get("last_sync"),
        "members": len(data_service._members),
        "bills": bills,
        "ai_summaries": ai_summaries,
        "member_summaries": len(data_service._member_summaries),
        "summary_coverage": round(covered / len(bill_keys), 4) if bill_keys else 0,
        "bills_missing_summary": len(bill_keys) - covered,
        # Dated freshness and coverage facts (spec §7.4, §4.6); /about and
        # /methodology read the same coverage_counts().
        "latest_roll_call": data_service.latest_roll_call_date(),
        "ai_summaries_updated": metadata.get("ai_summaries_updated"),
        "coverage": data_service.coverage_counts(),
    }


def _member_meta(member: dict) -> dict:
    """SEO meta for a member page (spec §9.2): 'Charles E. Schumer (NY) — Voting Record | ClearVoting';
    canonical is the upper-case id with every additive param stripped (§3.3)."""
    name = display_name(member.get("name") or "")
    state_code = member.get("stateCode", "")
    state = member.get("state", state_code)
    chamber = member.get("chamber", "Congress")
    return {
        "title": f"{name} ({state_code}) — Voting Record | ClearVoting",
        "description": f"{name}, {chamber} member from {state}. See their voting record on bills before Congress.",
        "og_type": "profile",
        "url": f"{SITE_URL}/member?id={member.get('bioguideId')}",
        "image": _og_image("member", member.get("bioguideId"), alt=f"ClearVoting — {name} · {state} · Voting record"),
    }


def _bill_meta(page: dict) -> dict:
    """SEO meta for a bill page (spec §9.2): the one-liner when displayable, else the official title capped at 70."""
    code = format_bill_code(page["bill_type"], page["number"])
    official = page.get("title") or ""
    if bill_displayable(page):  # the same predicate as the page's H1 (T7.1)
        headline = page["one_liner"]
    else:
        headline = cut_words(official, 70)
    return {
        "title": f"{code} — {headline} | ClearVoting",
        "description": official or headline,
        "og_type": "article",
        "url": f"{SITE_URL}/bill?congress={page['congress']}&type={page['bill_type']}&number={page['number']}",
        "image": _og_image("bill"),
    }


def _state_meta(code: str) -> dict:
    """SEO meta for a delegation page (spec §9.2).

    `code` is a covered, upper-case code: T4.2's serve_state has already turned anything
    else into a 404. district and zip are additive params, so the canonical is always
    /state?code=XX.
    """
    from app.dependencies import get_data_service
    state_name = render.COVERED_STATE_NAMES[code]
    count = len(get_data_service().get_members_by_state(code)["members"])
    return {
        "title": f"{state_name}'s Representatives — Voting Records{_TITLE_SUFFIX}",
        "description": (
            f"Voting records for {count} members of Congress from {state_name}. "
            "See how they vote on bills — facts only, no opinions."
        ),
        "url": f"{SITE_URL}/state?code={code}",
        "image": _og_image("state", code, alt=f"ClearVoting — {state_name} · Voting record"),
    }


def _zip_finder_meta() -> dict:
    """Meta for /state pages without a code (empty form, malformed ZIP, ZIP not found).

    These answer one visitor's query and are not pages to index, so no canonical tag.
    """
    return {
        "title": f"Find your representatives{_TITLE_SUFFIX}",
        "description": (
            "Enter your ZIP code to see how your two senators and your House member voted "
            "— facts only, no opinions."
        ),
        "url": f"{SITE_URL}/state",
        "canonical": False,
        "image": _og_image("state"),
    }


_og_dir = static_dir / "og"


def _scan_og_entities() -> frozenset[str]:
    """Phase B share cards present at startup, as 'member/S000148.png' / 'state/NY.png'.

    The weekly sync writes them (scripts/build_og_cards.py --entities) and the deploy
    restarts the app, so one scan per process is exact. Nothing is rendered per request (C-9).
    """
    found: set[str] = set()
    for kind in ("member", "state"):
        folder = _og_dir / kind
        if folder.is_dir():
            found.update(f"{kind}/{path.name}" for path in folder.glob("*.png"))
    return frozenset(found)


_og_entities = _scan_og_entities()


_OG_CARD_ALT = {
    "default": "ClearVoting — Facts only · No opinions · No spin",
    "member": "ClearVoting — Voting record",
    "bill": "ClearVoting — How Congress voted",
    "state": "ClearVoting — Your representatives",
}


def _og_image(kind: str, key: str | None = None, alt: str | None = None) -> dict:
    """The share card for a page (spec §9.3), as the `image` key _inject_meta reads.

    Phase B: the entity's own card (static/og/{kind}/{key}.png) when the startup scan found
    it, described by `alt`; otherwise the Phase A template card static/og/{kind}.png.
    `path` stays site-relative; _inject_meta makes it absolute.
    """
    if key and f"{kind}/{key}.png" in _og_entities:
        return {"path": f"/static/og/{kind}/{key}.png", "width": 1200, "height": 630,
                "alt": alt or _OG_CARD_ALT[kind]}
    return {"path": f"/static/og/{kind}.png", "width": 1200, "height": 630, "alt": _OG_CARD_ALT[kind]}


def _home_content(data_service) -> str:
    """Home blocks (spec §4.1). The Latest Vote card and the Record each degrade on
    their own (C-11, §4.1 states); the lead always renders."""
    metadata = data_service.get_sync_metadata()
    counts = data_service.get_member_counts()
    coverage = {"members": sum(counts.values()), "since": data_service.earliest_roll_call_date()}
    try:
        vote = data_service.get_latest_vote()
    except Exception:
        logger.exception("home: latest vote unavailable")
        vote = None
    try:
        bills = data_service.get_bills(limit=7)["bills"]
        latest_summary = None
        if bills and not bills[0].get("one_liner"):
            found = data_service.get_bills(summarized_only=True, limit=1)["bills"]
            latest_summary = found[0] if found else None
    except Exception:
        logger.exception("home: recent bills unavailable")
        bills, latest_summary = None, None
    return render.render_home(
        counts, coverage, vote, bills, latest_summary,
        metadata.get("last_sync"), metadata.get("ai_summaries_updated"),
    )


@app.get("/")
def serve_index():
    from app.dependencies import get_data_service
    meta = {
        "title": "ClearVoting — See How Your Representatives Vote",
        "description": "Unbiased congressional voting records. See how your representatives vote on bills — facts only, no opinions.",
        "url": f"{SITE_URL}/",
        "h1": "See how your representatives vote.",
        "image": _og_image("default"),
    }
    content, status = _page_content(lambda: _home_content(get_data_service()), meta)
    return _serve_html("index.html", meta, content, status_code=status)


_RECORD_POSITIONS = frozenset({"yes", "no", "nv"})


@app.get("/member")
def serve_member(request: Request):
    """Server-rendered member page (spec §4.3, §9.1). Plain def: the one member_votes read
    runs in the threadpool. Unknown or malformed ids are real 404s (§9.4); page/topic/
    position/plain are additive, validated here, and never reach the canonical. The
    member_votes read and the render run inside _page_content, so a corrupt file or a
    renderer error is the §4 error state with 503, not a bare 500 (F61)."""
    from app.dependencies import get_data_service
    from app.routers.members import BIOGUIDE_PATTERN

    params = request.query_params
    member_id = (params.get("id") or "").strip().upper()
    if not BIOGUIDE_PATTERN.match(member_id):
        raise StarletteHTTPException(status_code=404)
    data_service = get_data_service()
    detail = data_service.get_member_detail(member_id)      # members.json lookup, in memory
    if detail is None:
        raise StarletteHTTPException(status_code=404)
    try:
        page_no = max(1, int(params.get("page") or 1))
    except ValueError:
        page_no = 1
    topic = (params.get("topic") or "").strip()[:120] or None
    position = params.get("position") if params.get("position") in _RECORD_POSITIONS else None
    plain = params.get("plain") == "1"
    meta = _member_meta(detail["member"])

    def build() -> str:
        page = data_service.get_member_page(member_id, page_no, topic, position, plain)
        if page is None:   # the id vanished between the lookup and the read: treat as a failure
            raise LookupError(f"member {member_id} missing from get_member_page")
        return render.render_member_page(page)

    content, status = _page_content(build, meta)
    return _serve_html("member.html", meta, content, status_code=status)


@app.get("/bill")
def serve_bill(request: Request):
    """Server-rendered bill page (spec §4.4, §9.1). Unknown or malformed bill → 404."""
    from app.dependencies import get_data_service
    params = request.query_params
    bill_type = (params.get("type") or "").strip().lower()
    congress_raw = (params.get("congress") or "").strip()
    number_raw = (params.get("number") or "").strip()
    if not (congress_raw.isdigit() and number_raw.isdigit()) or bill_type not in VALID_BILL_TYPES:
        raise HTTPException(status_code=404)
    congress, number = int(congress_raw), int(number_raw)
    if not 1 <= congress <= 200:
        raise HTTPException(status_code=404)
    data_service = get_data_service()
    page = data_service.get_bill_page(congress, bill_type, number)
    if page is None:
        raise HTTPException(status_code=404)
    meta = _bill_meta(page)
    # T3.1: a render failure (a malformed roll-call file, a formatter exception) returns the §4
    # error state — masthead, the bill code as H1, "We couldn't load this page right now…" — with
    # 503 (no-store), not a bare 500 (F61).
    content, status = _page_content(
        lambda: render_bill_page(page, data_service.get_sync_metadata().get("ai_summaries_updated")),
        {**meta, "h1": format_bill_code(page["bill_type"], page["number"])},
    )
    return _serve_html("bill.html", meta, content, status_code=status)


def _trust_counts() -> dict:
    """Counts for /about and /methodology — the same numbers /api/health reports."""
    from app.dependencies import get_data_service
    ds = get_data_service()
    coverage = ds.coverage_counts()
    return {
        "members": len(ds._members),
        "senators": sum(1 for m in ds._members if m.get("chamber") == "Senate"),
        "bills": coverage["bills"],
        "shown": coverage["shown"],
        "missing": coverage["missing"],
        "withheld": coverage["withheld"],
        "audited": coverage["audited"],
        "nominations": coverage["nominations_excluded"],
        "since": ds.earliest_roll_call_date(),
        "ai_summaries_updated": ds.get_sync_metadata().get("ai_summaries_updated"),
    }


def _trust_block(build) -> tuple[str, int]:
    """Run a trust page's server-filled block (spec §4 "Common to every page").

    T3.1's _page_content can't be used here: render_error emits its own <h1>, and on these
    shells the <!--content--> marker sits under the shell's static h1. So on failure this
    logs and returns only the error sentence, with 503 (no-store under T8.2's rules)."""
    try:
        return build(), 200
    except Exception:
        logger.exception("trust page counts failed")
        return f"<p>{render.PAGE_ERROR_SENTENCE}</p>", 503


@app.get("/about")
def serve_about():
    content, status = _trust_block(lambda: render.render_about_counts(_trust_counts()))
    return _serve_html("about.html", {
        "title": "About — ClearVoting",
        "h1": "About ClearVoting",
        "description": "Who runs ClearVoting, how it is funded, what it covers and what it does not do.",
        "url": f"{SITE_URL}/about",
        "image": _og_image("default"),
    }, content, status_code=status)


@app.get("/methodology")
def serve_methodology():
    from app.dependencies import get_data_service

    def build() -> str:
        ds = get_data_service()
        return render.render_methodology(
            _trust_counts(), ds._crosswalk_source, render.prompt_rules(SYSTEM_PROMPT), ds._senate_file)

    content, status = _trust_block(build)
    return _serve_html("methodology.html", {
        "title": "Methodology & Corrections — ClearVoting",
        "h1": "Methodology & Corrections",
        "description": ("Where ClearVoting's data comes from, what AI writes and the rules it follows, "
                        "what we cover, and a dated corrections log."),
        "url": f"{SITE_URL}/methodology",
        "image": _og_image("default"),
    }, content, status_code=status)


@app.get("/privacy")
def serve_privacy():
    return _serve_html("privacy.html", {
        "title": "Privacy — ClearVoting",
        "h1": "Privacy",
        "description": ("What ClearVoting stores, where and for how long: the notify and feedback forms, "
                        "your browser's storage, logs and the services we use."),
        "url": f"{SITE_URL}/privacy",
        "image": _og_image("default"),
    })


# The lookup is static per deploy, so the edge may keep a ZIP's redirect for a day (§9.5).
_ZIP_REDIRECT_CACHE = "public, max-age=0, s-maxage=86400"
_ZIP_ERROR = "A ZIP code is five digits."
_FINDER_H1 = "Find your representatives"
_YOURS_H1 = "Your representatives"


def _zip_redirect(target: str) -> RedirectResponse:
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": _ZIP_REDIRECT_CACHE})


def _zip_target(result: dict) -> str | None:
    """Where a ZIP lookup sends the reader (§3.1). A single covered match goes to the
    district URL with #mine (site.js writes cv-home from it). A split or partial match goes
    to code + zip, which renders 200 and writes nothing. No match returns None."""
    matches = result.get("matches") or []
    if not matches:
        return None
    first = matches[0]
    if result.get("kind") == "single":
        return f"/state?code={first['state']}&district={int(first['district'])}#mine"
    if result.get("kind") in ("split", "partial"):
        return f"/state?code={first['state']}&zip={result['zip']}"
    return None


def _parse_district(raw: str | None) -> int | None:
    value = (raw or "").strip()
    return int(value) if value.isdigit() and len(value) <= 3 else None


def _serve_state_page(code: str | None, h1: str, build) -> HTMLResponse:
    """One /state page through T3.1's _page_content: `build()` renders the body, and if it
    raises, the §4 error state shows `h1` (the H1 this URL would have had) with a 503."""
    meta = {**(_state_meta(code) if code else _zip_finder_meta()), "h1": h1}
    content, status = _page_content(build, meta)
    return _serve_html("state.html", meta, content, status_code=status)


@app.get("/state")
def serve_state(request: Request):
    """The delegation page and the ZIP form's target (§3.1, §5.3). Plain def: the overview
    read runs in the threadpool."""
    from app.dependencies import get_data_service
    data_service = get_data_service()
    params = request.query_params
    code = (params.get("code") or "").strip().upper()
    if code and code not in render.COVERED_STATE_NAMES:
        raise HTTPException(status_code=404)
    state_h1 = f"{render.COVERED_STATE_NAMES[code]}'s representatives" if code else _FINDER_H1

    raw_zip = (params.get("zip") or "").strip()
    lookup = None
    if raw_zip:
        lookup = data_service.lookup_zip(raw_zip)  # T1.5: None when the input is not a ZIP
        if lookup is None:
            if not code:
                return _serve_state_page(None, _FINDER_H1, lambda: render.render_zip_finder_page(
                    data_service.get_member_counts(), value=raw_zip, error=_ZIP_ERROR))
            return _serve_state_page(code, state_h1, lambda: render.render_state_page(
                data_service.get_state_overview(code, fallback=True), None, None, _ZIP_ERROR,
                ds=data_service, zip_value=raw_zip))
        target = _zip_target(lookup)
        if target is None:
            return _serve_state_page(None, _FINDER_H1, lambda: render.render_zip_not_found(
                lookup["zip"], data_service.get_member_counts()))
        renders_here = (lookup["kind"] in ("split", "partial")
                        and any(m.get("state") == code for m in lookup["matches"]))
        if not renders_here:
            return _zip_redirect(target)

    if not code:
        return _serve_state_page(None, _FINDER_H1, lambda: render.render_zip_finder_page(
            data_service.get_member_counts()))
    district = None if lookup else _parse_district(params.get("district"))
    # The error state's H1 follows the URL shape: district and ZIP URLs lead with "Your representatives".
    h1 = _YOURS_H1 if (lookup is not None or district is not None) else state_h1
    return _serve_state_page(code, h1, lambda: render.render_state_page(
        data_service.get_state_overview(code, fallback=True), district, lookup, "",
        ds=data_service, zip_value=lookup["zip"] if lookup else ""))


_FAVICON_SVG = (static_dir / "favicon.svg").read_bytes()


@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon() -> Response:
    return Response(
        content=_FAVICON_SVG,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=31536000"},
    )


@app.get("/sitemap.xml")
def serve_sitemap() -> Response:
    from app.dependencies import get_data_service
    data_service = get_data_service()
    last_sync = _iso_day(data_service.get_sync_metadata().get("last_sync"))

    entries: list[tuple[str, str | None]] = [
        (f"{SITE_URL}/", last_sync),
        (f"{SITE_URL}/about", last_sync),
        (f"{SITE_URL}/methodology", last_sync),
        (f"{SITE_URL}/privacy", None),
    ]

    # State roster date and each member's lastmod come from T1.6's precomputed
    # delegation files (one cached read per state). A member's lastmod is
    # latest_vote.date, the newest decisive bill vote: the date the page's
    # indexable content last changed (plan T8.1, "Member lastmod source").
    member_last_vote: dict[str, str | None] = {}
    for code in render.COVERED_STATE_NAMES:
        overview = data_service.get_state_overview(code) or {}
        entries.append((f"{SITE_URL}/state?code={code}", _iso_day(overview.get("roster_as_of"))))
        for member in overview.get("senators", []) + overview.get("house", []):
            bioguide = str(member.get("bioguideId") or "").upper()
            member_last_vote[bioguide] = _iso_day((member.get("latest_vote") or {}).get("date"))

    for member in data_service._members:
        bioguide = str(member.get("bioguideId") or "").strip().upper()
        if BIOGUIDE_PATTERN.match(bioguide):
            entries.append((f"{SITE_URL}/member?id={bioguide}", member_last_vote.get(bioguide)))

    index_bills = (data_service._votes_index or {}).get("bills", {})
    for bill in data_service._bills:
        params = _normalize_bill_params(bill.get("congress"), bill.get("type"), bill.get("number"))
        if params is None:
            continue
        congress, bill_type, number = params
        entry = index_bills.get(f"{congress}-{bill_type}-{number}")
        activity = _iso_day(entry.get("activity_date")) if isinstance(entry, dict) else None
        if activity is None:
            activity = _iso_day((bill.get("latestAction") or {}).get("actionDate"))
        entries.append((f"{SITE_URL}/bill?congress={congress}&type={bill_type}&number={number}", activity))

    def url_tag(loc: str, lastmod: str | None) -> str:
        body = f"<loc>{xml_escape(loc)}</loc>"
        if lastmod:
            body += f"<lastmod>{lastmod}</lastmod>"
        return f"<url>{body}</url>"

    urls = "".join(url_tag(loc, lastmod) for loc, lastmod in entries)
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


@app.exception_handler(Exception)
async def server_error_handler(request: Request, exc: Exception) -> PlainTextResponse:
    """Generic 500 that is never cached (§9.5). Starlette still logs the traceback."""
    return PlainTextResponse(
        "Internal Server Error",
        status_code=500,
        headers={"Cache-Control": CACHE_NO_STORE},
    )


@app.exception_handler(StarletteHTTPException)
async def custom_exception_handler(request: Request, exc: StarletteHTTPException):
    """Serve the "Not in this edition" page for page routes; keep JSON for the API."""
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        from app.dependencies import get_data_service
        try:
            member_counts = get_data_service().get_member_counts()
        except Exception:
            # A data failure must not turn every 404 into a 500: the chips lose their counts.
            logger.exception("member counts unavailable for the 404 page")
            member_counts = {}
        content = render.render_not_found(
            render.render_zip_form(label="Find your representatives instead"),
            render.render_state_links(member_counts),
        )
        response = _serve_html("404.html", {
            "title": "Page Not Found — ClearVoting",
            "h1": "We don't have that page",
            "description": "The link may be old, or the bill or member may be outside our four-state coverage.",
            "url": f"{SITE_URL}{request.url.path}",
            "canonical": False,
        }, content)
        response.status_code = 404
        return response
    return await http_exception_handler(request, exc)
