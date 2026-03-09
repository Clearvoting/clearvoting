import json
import pytest
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.limiter import limiter


@pytest.fixture(autouse=True)
def _use_tmp_feedback_file(tmp_path):
    """Redirect feedback writes to a temp file and reset rate limiter."""
    tmp_file = tmp_path / "feedback.jsonl"
    limiter.reset()
    with patch("app.routers.feedback.FEEDBACK_FILE", tmp_file):
        yield tmp_file


def _post_feedback(client, **overrides):
    payload = {
        "message": "Great tool!",
        "page_url": "http://test/",
        "page_type": "home",
        "context_id": "",
        "context_label": "",
    }
    payload.update(overrides)
    return client.post("/api/feedback", json=payload)


# --- Happy path ---

@pytest.mark.asyncio
async def test_submit_feedback_success(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_feedback_written_to_file(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _post_feedback(client, message="Hello from test")

    lines = _use_tmp_feedback_file.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["message"] == "Hello from test"
    assert entry["page_type"] == "home"
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_feedback_with_member_context(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(
            client,
            message="Data looks wrong",
            page_url="http://test/member?id=S001217",
            page_type="member",
            context_id="S001217",
            context_label="Rick Scott",
        )
    assert resp.status_code == 200
    entry = json.loads(_use_tmp_feedback_file.read_text().strip())
    assert entry["context_id"] == "S001217"
    assert entry["context_label"] == "Rick Scott"
    assert entry["page_type"] == "member"


@pytest.mark.asyncio
async def test_feedback_with_bill_context(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(
            client,
            page_type="bill",
            context_id="hr1",
            context_label="One Big Beautiful Bill Act",
        )
    assert resp.status_code == 200
    entry = json.loads(_use_tmp_feedback_file.read_text().strip())
    assert entry["page_type"] == "bill"
    assert entry["context_id"] == "hr1"


@pytest.mark.asyncio
async def test_multiple_submissions_append(_use_tmp_feedback_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _post_feedback(client, message="First")
        await _post_feedback(client, message="Second")

    lines = _use_tmp_feedback_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["message"] == "First"
    assert json.loads(lines[1])["message"] == "Second"


@pytest.mark.asyncio
async def test_feedback_max_length_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, message="x" * 2000)
    assert resp.status_code == 200


# --- Validation errors ---

@pytest.mark.asyncio
async def test_empty_message_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, message="")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_message_too_long_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, message="x" * 2001)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_required_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/feedback", json={"message": "hello"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_page_url_too_long_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, page_url="http://x" + "x" * 500)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_page_type_too_long_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _post_feedback(client, page_type="x" * 51)
    assert resp.status_code == 422
