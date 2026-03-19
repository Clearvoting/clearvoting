import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


MOCK_DONATIONS = {
    "fec_candidate_id": "S8NY00082",
    "committee_id": "C00346312",
    "cycle": "2024",
    "last_updated": "2026-03-17T00:00:00Z",
    "top_contributors": [
        {"org_name": "Google", "total": 19000, "pacs": 0, "individuals": 19000},
        {"org_name": "Microsoft", "total": 7000, "pacs": 0, "individuals": 7000},
    ],
    "top_industries": [
        {"industry_name": "Attorney", "total": 126000, "pacs": 0, "individuals": 126000},
    ],
    "totals": {"total_receipts": 5000000, "total_disbursements": 4500000, "total_individual": 3000000, "total_pac": 500000},
}


def test_get_member_donations_success(client):
    with patch("app.routers.members.get_data_service") as mock_ds:
        mock_service = MagicMock()
        mock_service.get_member_donations.return_value = MOCK_DONATIONS
        mock_ds.return_value = mock_service

        response = client.get("/api/members/S001217/donations")
        assert response.status_code == 200
        data = response.json()
        assert data["fec_candidate_id"] == "S8NY00082"
        assert len(data["top_contributors"]) == 2
        assert data["top_contributors"][0]["org_name"] == "Google"


def test_get_member_donations_not_found(client):
    with patch("app.routers.members.get_data_service") as mock_ds:
        mock_service = MagicMock()
        mock_service.get_member_donations.return_value = None
        mock_ds.return_value = mock_service

        response = client.get("/api/members/S001217/donations")
        assert response.status_code == 404


def test_get_member_donations_invalid_id(client):
    response = client.get("/api/members/invalid/donations")
    assert response.status_code == 400


def test_get_member_donations_case_insensitive(client):
    with patch("app.routers.members.get_data_service") as mock_ds:
        mock_service = MagicMock()
        mock_service.get_member_donations.return_value = MOCK_DONATIONS
        mock_ds.return_value = mock_service

        response = client.get("/api/members/s001217/donations")
        assert response.status_code == 200
        mock_service.get_member_donations.assert_called_with("s001217")
