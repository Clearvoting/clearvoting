import threading
from functools import lru_cache
from pathlib import Path
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
