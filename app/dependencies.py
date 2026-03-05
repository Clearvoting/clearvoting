from functools import lru_cache
from app.config import CONGRESS_API_KEY, ANTHROPIC_API_KEY, CACHE_DIR, CACHE_TTL_SECONDS
from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from app.services.senate_votes import SenateVoteService
from app.services.ai_summary import AISummaryService


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
