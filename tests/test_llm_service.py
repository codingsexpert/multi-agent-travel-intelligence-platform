"""Unit tests for LLM abstraction, retries, and fallback behavior."""

from unittest.mock import MagicMock, patch
from config.settings import Settings
from services.llm_service import LLMService, MAX_PLANNER_RETRIES
from models.planner import PlannerResult, NormalizedTravelRequest


def test_llm_service_demo_mode_execution():
    """Verify LLMService defaults to deterministic extractor when demo_mode is True."""
    settings = Settings(_env_file=None, demo_mode=True)
    svc = LLMService(settings=settings)

    assert svc.is_live_configured is False
    res = svc.extract_plan("Delhi se Japan 7 days ka trip plan karo, budget ₹1.5 lakh hai, 2 log hain.")
    assert res.is_demo is True
    assert res.extracted_requirements.destination == "Japan"


def test_llm_service_retry_and_graceful_fallback_on_failure():
    """Verify that when live LLM parsing continuously fails, retry count is respected and fallback is used."""
    settings = Settings(
        _env_file=None,
        demo_mode=False,
        openai_api_key="sk-mock-key-for-test",
    )
    svc = LLMService(settings=settings)
    assert svc.is_live_configured is True

    # Simulate ChatOpenAI failing with parsing error
    with patch("langchain_openai.ChatOpenAI") as mock_chat_class:
        mock_chat_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = RuntimeError("OpenAI rate limit or parsing failure")
        mock_chat_instance.with_structured_output.return_value = mock_structured
        mock_chat_class.return_value = mock_chat_instance

        # Execute extraction
        res = svc.extract_plan("Trip from NYC to London for 7 days, 2 people, budget $4000")

        # Verify it retried MAX_PLANNER_RETRIES + 1 times (initial + retries)
        assert mock_structured.invoke.call_count == MAX_PLANNER_RETRIES + 1
        # Fallback was invoked gracefully
        assert res.is_demo is True
        assert res.extracted_requirements.destination == "London"
        assert any("fallback" in w.lower() for w in res.warnings)


def test_deterministic_validation_detects_post_parsing_inconsistencies():
    """Verify deterministic validation corrects and marks unflagged missing items."""
    result = PlannerResult(
        extracted_requirements=NormalizedTravelRequest(
            origin="London",
            destination=None,  # missing destination
            duration=5,
            travelers=2,
            budget=2000.0,
        ),
        missing_fields=[],
        conflicts=[],
        clarification_required=False,
    )

    LLMService._validate_result_deterministically(result)
    assert "destination" in result.missing_fields
    assert result.clarification_required is True
    assert len(result.clarification_questions) > 0
