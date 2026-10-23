import pytest


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """Every test starts and ends with an empty rate-limit bucket and no cached DataService.

    Both are process-global, so without this a test's outcome depended on which tests ran
    before it (a targeted pick of a routers test plus the rate-limit test failed 9 == 10),
    and a test that failed before its own cache_clear() left a fixtures-backed DataService
    behind for unrelated tests."""
    from app.dependencies import get_data_service
    from app.limiter import limiter
    limiter.reset()
    get_data_service.cache_clear()
    yield
    limiter.reset()
    get_data_service.cache_clear()
