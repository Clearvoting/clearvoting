import pytest
import time
from app.services.cache import CacheService


@pytest.fixture
def cache_service(tmp_path):
    return CacheService(cache_dir=tmp_path, ttl_seconds=2)


def test_cache_miss_returns_none(cache_service):
    result = cache_service.get("nonexistent_key")
    assert result is None


def test_cache_set_and_get(cache_service):
    data = {"members": [{"name": "Test"}]}
    cache_service.set("test_key", data)
    result = cache_service.get("test_key")
    assert result == data


def test_cache_expires(cache_service):
    cache_service.set("expiring_key", {"data": True})
    time.sleep(3)
    result = cache_service.get("expiring_key")
    assert result is None


def test_cache_overwrites_existing(cache_service):
    cache_service.set("key", {"v": 1})
    cache_service.set("key", {"v": 2})
    result = cache_service.get("key")
    assert result == {"v": 2}


def test_cache_handles_corrupt_file(cache_service):
    path = cache_service._key_to_path("corrupt_key")
    path.write_text("not valid json")
    result = cache_service.get("corrupt_key")
    assert result is None
