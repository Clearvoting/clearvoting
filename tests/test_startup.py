"""Startup load (F003, F072, F030): one DataService per process, built before the port opens,
and a data file that cannot be loaded fails startup instead of 500ing every request."""
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import dependencies
from app.dependencies import get_data_service
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir(data_dir=FIXTURES):
    return patch("app.dependencies.get_data_dir", return_value=data_dir)


def test_concurrent_first_calls_build_one_data_service():
    builds = []

    def slow_build(data_dir):
        builds.append(data_dir)
        time.sleep(0.05)   # every thread reaches get_data_service() while this build runs
        return object()

    threads_n = 8
    barrier = threading.Barrier(threads_n)
    results = []

    def first_call():
        barrier.wait()
        results.append(get_data_service())

    with _patch_data_dir(), patch("app.dependencies.DataService", side_effect=slow_build):
        threads = [threading.Thread(target=first_call) for _ in range(threads_n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

    assert len(builds) == 1
    assert len(results) == threads_n
    assert len({id(result) for result in results}) == 1


def test_cache_clear_still_resets_the_singleton():
    with _patch_data_dir():
        first = get_data_service()
        assert get_data_service() is first
        get_data_service.cache_clear()
        assert get_data_service() is not first


def test_lifespan_loads_the_data_before_serving_and_freezes_it():
    with _patch_data_dir(), patch("app.main.gc.freeze") as freeze:
        with TestClient(app) as client:
            # Loaded by startup, before any request arrives.
            assert dependencies._build_data_service.cache_info().currsize == 1
            freeze.assert_called_once_with()
            assert client.get("/api/health").status_code == 200
            assert dependencies._build_data_service.cache_info().misses == 1


@pytest.mark.parametrize("filename, text", [
    ("members.json", '{"members": [{"bioguideId": "S000148"'),   # truncated
    ("bills.json", '{"bills": null}'),
    ("votes_index.json", "<<<<<<< HEAD\n{}"),                    # merge markers
])
def test_lifespan_fails_startup_when_a_core_file_cannot_load(tmp_path, filename, text):
    (tmp_path / filename).write_text(text)
    with _patch_data_dir(tmp_path), patch("app.main.gc.freeze"):
        with pytest.raises((ValueError, TypeError, AttributeError)):
            with TestClient(app):
                pass
