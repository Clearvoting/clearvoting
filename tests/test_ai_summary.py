import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_summary import AISummaryService, IMPACT_CATEGORIES


def test_impact_categories_defined():
    assert "Wages & Income" in IMPACT_CATEGORIES
    assert "Healthcare" in IMPACT_CATEGORIES
    assert "Housing" in IMPACT_CATEGORIES
    assert "Small Business" in IMPACT_CATEGORIES
    assert "Taxes" in IMPACT_CATEGORIES


def test_build_prompt_contains_no_bias_instructions():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1. The minimum wage shall be raised to $15."
    )
    assert "Test Bill" in prompt
    assert "adjective" in prompt.lower()
    assert "Impact Categories" in prompt or "impact_categories" in prompt


def test_build_prompt_includes_bill_content():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Minimum Wage Act",
        official_summary="Raises the minimum wage.",
        bill_text_excerpt="The wage floor increases to $15."
    )
    assert "Minimum Wage Act" in prompt
    assert "Raises the minimum wage" in prompt
    assert "$15" in prompt


@pytest.mark.asyncio
async def test_generate_summary_returns_expected_structure():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Raises the federal minimum wage from $7.25 to $15.00 per hour"], "impact_categories": ["Wages & Income", "Small Business"]}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-1234",
            title="Minimum Wage Act",
            official_summary="A bill to raise the minimum wage.",
            bill_text_excerpt="The minimum wage shall be $15."
        )

    assert "provisions" in result
    assert "impact_categories" in result
    assert len(result["provisions"]) > 0
    assert "Wages & Income" in result["impact_categories"]


@pytest.mark.asyncio
async def test_generate_summary_filters_invalid_categories():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Test provision"], "impact_categories": ["Healthcare", "Fake Category", "Taxes"]}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-5678",
            title="Test",
            official_summary="Test",
            bill_text_excerpt="Test"
        )

    assert "Fake Category" not in result["impact_categories"]
    assert "Healthcare" in result["impact_categories"]
    assert "Taxes" in result["impact_categories"]


@pytest.mark.asyncio
async def test_generate_summary_uses_cache():
    cached = {"provisions": ["Cached provision"], "impact_categories": ["Housing"]}
    mock_cache = MagicMock()
    mock_cache.get.return_value = cached
    service = AISummaryService(api_key="test", cache=mock_cache)

    result = await service.generate_summary(
        bill_id="119-hr-999",
        title="Cached",
        official_summary="Cached",
        bill_text_excerpt="Cached"
    )
    assert result["provisions"][0] == "Cached provision"
