import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_summary import AISummaryService, IMPACT_CATEGORIES, SYSTEM_PROMPT


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


def test_build_prompt_requests_one_liner():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1."
    )
    assert "one_liner" in prompt


@pytest.mark.asyncio
async def test_generate_summary_includes_one_liner():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Raises the minimum wage to $15"], "impact_categories": ["Wages & Income"], "one_liner": "Raise the federal minimum wage to $15 per hour"}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-1234",
            title="Minimum Wage Act",
            official_summary="A bill to raise the minimum wage.",
            bill_text_excerpt="The minimum wage shall be $15."
        )

    assert "one_liner" in result
    assert result["one_liner"] == "Raise the federal minimum wage to $15 per hour"


@pytest.mark.asyncio
async def test_generate_summary_fallback_when_no_one_liner():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Does something"], "impact_categories": ["Taxes"]}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-999",
            title="Some Act",
            official_summary="Does things.",
            bill_text_excerpt="Text."
        )

    assert "one_liner" in result
    assert result["one_liner"] == "Does something"


@pytest.mark.asyncio
async def test_generate_summary_json_error_includes_one_liner():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='not valid json')]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-bad",
            title="Fallback Title",
            official_summary="Test",
            bill_text_excerpt="Test"
        )

    assert "one_liner" in result
    assert result["one_liner"] == "Fallback Title"


def test_build_prompt_with_grader_feedback():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
        grader_feedback="Use simpler words. Avoid 'appropriations'."
    )
    assert "simpler words" in prompt
    assert "appropriations" in prompt
    assert "PREVIOUS ATTEMPT" in prompt or "feedback" in prompt.lower()


def test_build_prompt_without_grader_feedback():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
    )
    assert "PREVIOUS ATTEMPT" not in prompt


def test_build_prompt_includes_direction_field():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
    )
    assert "direction" in prompt
    assert "strengthens" in prompt
    assert "weakens" in prompt
    assert "neutral" in prompt


def test_build_prompt_includes_policy_area_when_provided():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
        policy_area="Environmental Protection",
    )
    assert "Environmental Protection" in prompt
    assert "Policy Area" in prompt


def test_build_prompt_omits_policy_area_when_none():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1.",
    )
    assert "Policy Area" not in prompt


@pytest.mark.asyncio
async def test_generate_summary_valid_direction_passes_through():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Cancels an EPA rule"], "impact_categories": ["Environment"], "one_liner": "Cancel an EPA rule", "direction": "weakens"}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hjres-20",
            title="CRA Disapproval",
            official_summary="Disapproval of EPA rule.",
            bill_text_excerpt="This joint resolution...",
        )

    assert result["direction"] == "weakens"


@pytest.mark.asyncio
async def test_generate_summary_invalid_direction_defaults_to_neutral():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Does something"], "impact_categories": ["Taxes"], "one_liner": "Do something", "direction": "bogus_value"}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-999",
            title="Test",
            official_summary="Test",
            bill_text_excerpt="Test",
        )

    assert result["direction"] == "neutral"


@pytest.mark.asyncio
async def test_generate_summary_missing_direction_defaults_to_neutral():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Does something"], "impact_categories": ["Taxes"], "one_liner": "Do something"}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-998",
            title="Test",
            official_summary="Test",
            bill_text_excerpt="Test",
        )

    assert result["direction"] == "neutral"


def test_system_prompt_double_negative_rule():
    """System prompt instructs AI to describe the RESULT, not chain of actions."""
    assert "RESULT" in SYSTEM_PROMPT
    assert "stacking negatives" in SYSTEM_PROMPT
