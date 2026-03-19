import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.bill_arguments import BillArgumentsService, SYSTEM_PROMPT


def test_system_prompt_requires_attribution():
    assert "Supporters say" in SYSTEM_PROMPT or "attributed" in SYSTEM_PROMPT.lower()


def test_system_prompt_requires_both_sides():
    assert "Both sides" in SYSTEM_PROMPT


def test_system_prompt_no_adjectives():
    assert "adjective" in SYSTEM_PROMPT.lower()


def test_build_prompt_contains_bill_info():
    service = BillArgumentsService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Minimum Wage Act",
        official_summary="Raises the minimum wage.",
        provisions=["Raises the minimum wage from $7.25 to $15.00 per hour"],
    )
    assert "Minimum Wage Act" in prompt
    assert "$7.25" in prompt
    assert "supporters" in prompt.lower()
    assert "critics" in prompt.lower()


def test_build_prompt_handles_empty_provisions():
    service = BillArgumentsService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill.",
        provisions=[],
    )
    assert "No AI provisions available" in prompt


def test_build_prompt_with_grader_feedback():
    service = BillArgumentsService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill.",
        provisions=["Does something"],
        grader_feedback="Arguments are too generic. Reference specific dollar amounts.",
    )
    assert "PREVIOUS ATTEMPT" in prompt
    assert "generic" in prompt


def test_build_prompt_without_grader_feedback():
    service = BillArgumentsService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill.",
        provisions=["Does something"],
    )
    assert "PREVIOUS ATTEMPT" not in prompt


@pytest.mark.asyncio
async def test_generate_arguments_returns_expected_structure():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = BillArgumentsService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"supporters": ["Supporters say this would raise wages for 30 million workers"], "critics": ["Critics say the $15 rate could cut 1.4 million jobs"]}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_arguments(
            bill_id="119-hr-1234",
            title="Minimum Wage Act",
            official_summary="Raises the minimum wage.",
            provisions=["Raises the minimum wage from $7.25 to $15.00"],
        )

    assert "supporters" in result
    assert "critics" in result
    assert len(result["supporters"]) > 0
    assert len(result["critics"]) > 0


@pytest.mark.asyncio
async def test_generate_arguments_uses_cache():
    cached = {"supporters": ["Cached supporter"], "critics": ["Cached critic"]}
    mock_cache = MagicMock()
    mock_cache.get.return_value = cached
    service = BillArgumentsService(api_key="test", cache=mock_cache)

    result = await service.generate_arguments(
        bill_id="119-hr-999",
        title="Cached",
        official_summary="Cached",
        provisions=["Cached"],
    )
    assert result["supporters"][0] == "Cached supporter"


@pytest.mark.asyncio
async def test_generate_arguments_skips_cache_on_retry():
    mock_cache = MagicMock()
    mock_cache.get.return_value = {"supporters": ["Old"], "critics": ["Old"]}
    service = BillArgumentsService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"supporters": ["New supporter"], "critics": ["New critic"]}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_arguments(
            bill_id="119-hr-999",
            title="Test",
            official_summary="Test",
            provisions=["Test"],
            grader_feedback="Be more specific.",
        )

    assert result["supporters"][0] == "New supporter"


@pytest.mark.asyncio
async def test_generate_arguments_handles_invalid_json():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = BillArgumentsService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='not valid json')]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_arguments(
            bill_id="119-hr-bad",
            title="Test",
            official_summary="Test",
            provisions=["Test"],
        )

    assert result == {"supporters": [], "critics": []}


@pytest.mark.asyncio
async def test_generate_arguments_validates_structure():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = BillArgumentsService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"supporters": "not a list", "critics": null}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_arguments(
            bill_id="119-hr-struct",
            title="Test",
            official_summary="Test",
            provisions=["Test"],
        )

    assert isinstance(result["supporters"], list)
    assert isinstance(result["critics"], list)
