import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.congress_api import CongressAPIClient


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get.return_value = None
    return cache


@pytest.fixture
def client(mock_cache):
    return CongressAPIClient(api_key="test_key", cache=mock_cache)


@pytest.mark.asyncio
async def test_get_members_by_state(client):
    mock_response = {
        "members": [
            {"bioguideId": "T000001", "name": "Test Senator", "state": "FL"}
        ]
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_members_by_state("FL")
    assert len(result["members"]) == 1
    assert result["members"][0]["state"] == "FL"


@pytest.mark.asyncio
async def test_get_members_by_state_follows_pagination(client):
    """Members beyond the first page must be fetched via pagination.next.

    Regression: the default page size (20) silently dropped senators and most
    House members for large states.
    """
    page1 = {
        "members": [{"bioguideId": f"P{i:03d}", "state": "CA"} for i in range(250)],
        "pagination": {
            "next": "https://api.congress.gov/v3/member/CA?offset=250&limit=250&currentMember=true&format=json"
        },
    }
    page2 = {
        "members": [{"bioguideId": "P250", "state": "CA"}],
        "pagination": {},
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, side_effect=[page1, page2]) as mock_fetch:
        result = await client.get_members_by_state("CA")

    assert len(result["members"]) == 251
    # First request asks for the max page size
    first_path, first_params = mock_fetch.await_args_list[0].args
    assert first_path == "/member/CA"
    assert first_params["limit"] == "250"
    assert first_params["currentMember"] == "true"
    # Next page re-issued through _fetch (API key stays in headers), not a raw GET
    second_path, second_params = mock_fetch.await_args_list[1].args
    assert second_path == "/member/CA"
    assert second_params["offset"] == "250"


@pytest.mark.asyncio
async def test_get_members_by_state_ignores_offsite_pagination(client):
    """A pagination.next URL outside the Congress.gov API must not be followed."""
    page1 = {
        "members": [{"bioguideId": "P000", "state": "CA"}],
        "pagination": {"next": "https://evil.example.com/v3/member/CA?offset=250"},
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, side_effect=[page1]) as mock_fetch:
        result = await client.get_members_by_state("CA")

    assert len(result["members"]) == 1
    assert mock_fetch.await_count == 1


@pytest.mark.asyncio
async def test_get_members_by_state_uses_cache(client, mock_cache):
    cached_data = {"members": [{"bioguideId": "C001", "name": "Cached"}]}
    mock_cache.get.return_value = cached_data
    result = await client.get_members_by_state("FL")
    assert result["members"][0]["name"] == "Cached"


@pytest.mark.asyncio
async def test_get_bill_detail(client):
    mock_response = {
        "bill": {"number": "1234", "title": "Test Bill", "congress": 119}
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_bill(119, "hr", 1234)
    assert result["bill"]["number"] == "1234"


@pytest.mark.asyncio
async def test_get_member_detail(client):
    mock_response = {
        "member": {"bioguideId": "T001", "firstName": "Test", "lastName": "Member"}
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_member("T001")
    assert result["member"]["bioguideId"] == "T001"


@pytest.mark.asyncio
async def test_get_house_vote_members(client):
    mock_response = {
        "members": [{"name": "Rep Test", "vote": "Yea"}]
    }
    with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_house_vote_members(119, 2, 1)
    assert len(result["members"]) == 1


@pytest.mark.asyncio
async def test_fetch_caches_response(client, mock_cache):
    mock_json = {"data": "test"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_json
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_resp
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        MockAsyncClient.return_value = mock_http

        result = await client._fetch("/test/path")

    assert result == mock_json
    mock_cache.set.assert_called_once()
