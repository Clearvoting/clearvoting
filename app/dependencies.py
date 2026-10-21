import threading
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException, Request
from app.config import CONGRESS_API_KEY, ANTHROPIC_API_KEY, CACHE_DIR, CACHE_TTL_SECONDS, BASE_DIR
from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService
from app.services.ai_summary import AISummaryService
from app.services.data_service import DataService


def get_data_dir() -> Path:
    return BASE_DIR / "data" / "synced"


_data_service_lock = threading.Lock()


@lru_cache
def _build_data_service() -> DataService:
    return DataService(data_dir=get_data_dir())


def get_data_service() -> DataService:
    """The one DataService per process. lru_cache alone does not serialize a first call, so
    concurrent cold requests each built their own (~100 MB apiece) until the instance ran
    out of memory (F003); the lock makes every caller wait for the one build. main.py's
    lifespan builds it before the port opens, so requests normally find it ready."""
    with _data_service_lock:
        return _build_data_service()


get_data_service.cache_clear = _build_data_service.cache_clear


@lru_cache
def get_cache() -> CacheService:
    return CacheService(cache_dir=CACHE_DIR, ttl_seconds=CACHE_TTL_SECONDS)


@lru_cache
def get_congress_client() -> CongressAPIClient:
    return CongressAPIClient(api_key=CONGRESS_API_KEY, cache=get_cache())


@lru_cache
def get_senate_vote_service() -> SenateVoteService:
    return SenateVoteService(cache=get_cache())


@lru_cache
def get_ai_summary_service() -> AISummaryService:
    return AISummaryService(api_key=ANTHROPIC_API_KEY, cache=get_cache())


# The site's own pages; local dev and the test clients are allowed too.
_SITE_ORIGINS = frozenset({"https://clearvoting.org", "https://www.clearvoting.org", "http://testserver"})
_DEV_ORIGINS = ("http://localhost", "http://127.0.0.1")


def _is_site_origin(origin: str) -> bool:
    if origin in _SITE_ORIGINS:
        return True
    for base in _DEV_ORIGINS:
        if origin.startswith(base):
            port = origin[len(base):]
            # Any port, but not a look-alike host such as http://localhost.example.com.
            if port == "" or (port[0] == ":" and port[1:].isdigit()):
                return True
    return False


def require_site_json(request: Request) -> None:
    """The write routes take JSON from the site's own pages only (F036).

    A cross-site page can make a visitor's browser POST without a CORS preflight only when
    the body has no Content-Type or a form or text one, and FastAPI parses a body with no
    Content-Type as JSON. Requiring application/json forces the preflight, which fails
    (there is no CORS). A cross-site Sec-Fetch-Site or a foreign Origin is refused outright.
    site.js and feedback.js send application/json from the same origin."""
    if request.headers.get("sec-fetch-site", "").strip().lower() == "cross-site":
        raise HTTPException(status_code=403, detail="Cross-site request refused")
    origin = request.headers.get("origin")
    if origin is not None and not _is_site_origin(origin.strip().lower()):
        raise HTTPException(status_code=403, detail="Cross-site request refused")
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise HTTPException(status_code=415, detail="Send the form as JSON")
