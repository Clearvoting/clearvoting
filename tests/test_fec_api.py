import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.fec_api import FECClient


@pytest.mark.asyncio
async def test_search_candidate_returns_match():
    client = FECClient(api_key="test")

    mock_data = {
        "results": [
            {
                "candidate_id": "S8NY00082",
                "name": "SCHUMER, CHARLES E.",
                "office_full": "Senate",
                "state": "NY",
                "party_full": "DEMOCRATIC PARTY",
            }
        ]
    }

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.search_candidate("Schumer", "NY", "S")

    assert result is not None
    assert result["candidate_id"] == "S8NY00082"
    assert result["state"] == "NY"


@pytest.mark.asyncio
async def test_search_candidate_returns_none_when_not_found():
    client = FECClient(api_key="test")

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.search_candidate("Nonexistent", "ZZ")

    assert result is None


@pytest.mark.asyncio
async def test_get_principal_committee():
    client = FECClient(api_key="test")

    mock_data = {
        "results": [{"committee_id": "C00346312", "name": "FRIENDS OF SCHUMER"}]
    }

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.get_principal_committee("S8NY00082")

    assert result == "C00346312"


@pytest.mark.asyncio
async def test_get_principal_committee_none():
    client = FECClient(api_key="test")

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.get_principal_committee("INVALID")

    assert result is None


@pytest.mark.asyncio
async def test_get_top_employers_filters_noise():
    client = FECClient(api_key="test")

    mock_data = {
        "results": [
            {"employer": "NOT EMPLOYED", "total": 500000, "count": 10000},
            {"employer": "SELF-EMPLOYED", "total": 100000, "count": 2000},
            {"employer": "GOOGLE", "total": 19000, "count": 380},
            {"employer": "MICROSOFT", "total": 7000, "count": 163},
            {"employer": "COLUMBIA UNIVERSITY", "total": 5800, "count": 126},
        ]
    }

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.get_top_employers("C00639591")

    # Should filter out NOT EMPLOYED and SELF-EMPLOYED
    assert len(result) == 3
    assert result[0]["org_name"] == "GOOGLE"
    assert result[0]["total"] == 19000
    assert result[1]["org_name"] == "MICROSOFT"


@pytest.mark.asyncio
async def test_get_top_occupations():
    client = FECClient(api_key="test")

    mock_data = {
        "results": [
            {"occupation": "NOT EMPLOYED", "total": 2000000, "count": 60000},
            {"occupation": "ATTORNEY", "total": 126000, "count": 2378},
            {"occupation": "PHYSICIAN", "total": 114000, "count": 2324},
        ]
    }

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.get_top_occupations("C00639591")

    assert len(result) == 2
    assert result[0]["industry_name"] == "Attorney"
    assert result[0]["total"] == 126000


@pytest.mark.asyncio
async def test_get_donation_size_breakdown():
    client = FECClient(api_key="test")

    mock_data = {
        "results": [
            {"size": 0, "total": 13000000, "count": None},
            {"size": 200, "total": 571000, "count": 2247},
            {"size": 500, "total": 354000, "count": 697},
        ]
    }

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.get_donation_size_breakdown("C00639591")

    assert len(result) == 3
    # Should be sorted by total descending
    assert result[0]["size"] == 0
    assert result[0]["total"] == 13000000


@pytest.mark.asyncio
async def test_get_committee_totals():
    client = FECClient(api_key="test")

    mock_data = {
        "results": [
            {
                "receipts": 5000000,
                "disbursements": 4500000,
                "individual_contributions": 3000000,
                "other_political_committee_contributions": 500000,
            }
        ]
    }

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client.get_committee_totals("C00346312")

    assert result["total_receipts"] == 5000000
    assert result["total_individual"] == 3000000
    assert result["total_pac"] == 500000


@pytest.mark.asyncio
async def test_retry_on_rate_limit():
    """Verify _fetch retries on 429 and succeeds on subsequent attempt."""
    client = FECClient(api_key="test")

    mock_429 = MagicMock()
    mock_429.status_code = 429

    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.json.return_value = {"results": [{"candidate_id": "H8FL07072"}]}
    mock_ok.raise_for_status = MagicMock()

    with patch("app.services.fec_api.httpx.AsyncClient") as mock_http, \
         patch("app.services.fec_api.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [mock_429, mock_ok]
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client_instance

        result = await client._fetch("/candidates/search/", {"name": "Scott, Rick"})

    assert result["results"][0]["candidate_id"] == "H8FL07072"
    mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second backoff
