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
