import json
import pytest
from unittest.mock import patch
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.data_service import DataService

FIXTURES = Path(__file__).parent / "fixtures" / "synced"


def _patch_data_dir(data_dir=FIXTURES):
    """Patch data dir to use test fixtures and reset the DataService singleton."""
    return patch("app.dependencies.get_data_dir", return_value=data_dir)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_record_counts():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    members = json.loads((FIXTURES / "members.json").read_text())["members"]
    bills = json.loads((FIXTURES / "bills.json").read_text())["bills"]
    summaries = json.loads((FIXTURES / "ai_summaries.json").read_text())
    bill_keys = {f"{b['congress']}-{b['type'].lower()}-{b['number']}" for b in bills}
    covered = len(bill_keys & set(summaries))
    assert data["members"] == len(members)
    assert data["bills"] == len(bills)
    assert data["ai_summaries"] == len(summaries)
    assert data["member_summaries"] == 1
    # Coverage is intersected (bills that actually have a summary) and precise
    # enough that 1521/1525 can never read as 1.0 again.
    assert 0 < covered < len(bill_keys)
    assert data["summary_coverage"] == round(covered / len(bill_keys), 4)
    assert data["bills_missing_summary"] == len(bill_keys) - covered


@pytest.mark.asyncio
async def test_health_check_zero_bills_coverage(tmp_path):
    with _patch_data_dir(tmp_path):
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["members"] == 0
    assert data["bills"] == 0
    assert data["summary_coverage"] == 0


# --- Freshness and coverage facts (spec §7.4, §4.6, §10 #11; plan T1.10) ---

def _bill_ids(data_dir):
    bills = json.loads((data_dir / "bills.json").read_text())["bills"]
    return [f"{b['congress']}-{str(b['type']).lower()}-{b['number']}" for b in bills]


def _expected_coverage(data_dir):
    """Recount the §4.6 numbers straight from the files, independent of DataService."""
    ids = _bill_ids(data_dir)
    summaries = json.loads((data_dir / "ai_summaries.json").read_text())
    grades_path = data_dir / "audit_grades.json"
    grades = json.loads(grades_path.read_text()) if grades_path.exists() else {}
    index = json.loads((data_dir / "votes_index.json").read_text())
    shown = sum(1 for i in ids if i in summaries and summaries[i].get("needs_review") is not True)
    withheld = sum(1 for i in ids if i in summaries and summaries[i].get("needs_review") is True)
    return {
        "bills": len(ids),
        "shown": shown,
        "missing": len(ids) - shown - withheld,
        "withheld": withheld,
        "audited": sum(1 for i in ids if i in grades),
        "nominations_excluded": sum(
            1 for key, rc in index["roll_calls"].items()
            if key.startswith("senate/") and str(rc.get("document") or "").strip().startswith(("PN", "P.N."))
        ),
    }


@pytest.mark.asyncio
async def test_health_reports_freshness_and_coverage():
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

    _clear_data_service_cache()
    assert response.status_code == 200
    data = response.json()
    metadata = json.loads((FIXTURES / "sync_metadata.json").read_text())
    index = json.loads((FIXTURES / "votes_index.json").read_text())
    assert data["ai_summaries_updated"] == metadata.get("ai_summaries_updated")
    assert data["latest_roll_call"] == max(rc["date"][:10] for rc in index["roll_calls"].values())
    assert data["coverage"] == _expected_coverage(FIXTURES)
    # Additive: every key the old footer and ops checks read is still there
    for key in ("status", "version", "last_sync", "members", "bills", "ai_summaries",
                "member_summaries", "summary_coverage", "bills_missing_summary"):
        assert key in data


def test_coverage_counts_from_synthetic_data(tmp_path):
    (tmp_path / "bills.json").write_text(json.dumps({"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Shown"},
        {"congress": 119, "type": "HR", "number": "2", "title": "Withheld"},
        {"congress": 119, "type": "S", "number": "3", "title": "Missing one"},
        {"congress": 118, "type": "HRES", "number": "4", "title": "Missing two"},
    ]}))
    (tmp_path / "ai_summaries.json").write_text(json.dumps({
        "119-hr-1": {"one_liner": "Shown headline", "provisions": ["§ One."]},
        "119-hr-2": {"one_liner": "Withheld headline", "needs_review": True},
    }))
    (tmp_path / "audit_grades.json").write_text(json.dumps({
        "119-hr-1": {"grade": "A", "passed": True},
        "117-hr-9": {"grade": "B", "passed": True},   # not a bill we hold: not counted
    }))

    def rc(document, date):
        return {"question": "On the Motion to Proceed", "plain": "Vote to take it up", "class": "P",
                "result": "Motion Agreed to", "counts": {"yeas": 51, "nays": 47, "present": 0, "absent": 2},
                "date": date, "document": document, "bill": None, "parent": None, "threshold": None,
                "tallies": {}}

    (tmp_path / "votes_index.json").write_text(json.dumps({"roll_calls": {
        "senate/119_2_00100": rc("PN80", "2026-08-01"),
        "senate/119_2_00101": rc("PN11-16", "2026-08-02"),
        "senate/119_2_00102": rc("S. 3", "2026-08-03"),
        "house/119_2_00295": rc("H.R. 1", "2026-09-03"),
    }, "bills": {}, "generated_at": "2026-09-19T00:00:00Z"}))
    service = DataService(data_dir=tmp_path)
    assert service.coverage_counts() == {"bills": 4, "shown": 1, "missing": 2, "withheld": 1,
                                         "audited": 1, "nominations_excluded": 2}
    assert service.latest_roll_call_date() == "2026-09-03"


def test_coverage_counts_with_no_data(tmp_path):
    service = DataService(data_dir=tmp_path)
    assert service.coverage_counts() == {"bills": 0, "shown": 0, "missing": 0, "withheld": 0,
                                         "audited": 0, "nominations_excluded": 0}
    assert service.latest_roll_call_date() is None
