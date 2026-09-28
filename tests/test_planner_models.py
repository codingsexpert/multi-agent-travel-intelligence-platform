"""Unit tests for Planner Agent Pydantic structured output models."""

import pytest
from pydantic import ValidationError
from models.planner import (
    NormalizedTravelRequest,
    ClarificationRequest,
    PlannerResult,
)


def test_normalized_travel_request_valid():
    """Verify instantiation of valid NormalizedTravelRequest."""
    req = NormalizedTravelRequest(
        origin="SFO",
        destination="Tokyo",
        start_date="2026-11-01",
        end_date="2026-11-10",
        duration=10,
        travelers=2,
        budget=4500.0,
        currency="USD",
        interests=["food", "culture"],
        travel_style="Balanced",
    )
    assert req.origin == "SFO"
    assert req.destination == "Tokyo"
    assert req.duration == 10
    assert req.travelers == 2
    assert req.budget == 4500.0
    assert req.currency == "USD"
    assert "food" in req.interests


def test_normalized_travel_request_handles_numerical_values():
    """Verify NormalizedTravelRequest accepts extracted numeric parameters."""
    req = NormalizedTravelRequest(duration=7, travelers=3, budget=1500.0)
    assert req.duration == 7
    assert req.travelers == 3
    assert req.budget == 1500.0


def test_clarification_request_model():
    """Verify ClarificationRequest model structure."""
    clarification = ClarificationRequest(
        required=True,
        missing_fields=["origin", "budget"],
        questions=["1. Where are you departing from?", "2. What is your budget?"],
    )
    assert clarification.required is True
    assert len(clarification.missing_fields) == 2
    assert len(clarification.questions) == 2


def test_planner_result_model():
    """Verify PlannerResult complete model and serialization."""
    req = NormalizedTravelRequest(
        origin="Delhi",
        destination="Japan",
        duration=7,
        travelers=2,
        budget=150000.0,
        currency="INR",
        interests=["food", "culture", "nature"],
    )
    result = PlannerResult(
        extracted_requirements=req,
        missing_fields=[],
        conflicts=[],
        assumptions=["[DEMO_MODE] Deterministic pattern extraction utilized."],
        warnings=[],
        clarification_required=False,
        clarification_questions=[],
        is_demo=True,
    )
    dumped = result.model_dump()
    assert dumped["is_demo"] is True
    assert dumped["extracted_requirements"]["destination"] == "Japan"
    assert dumped["extracted_requirements"]["currency"] == "INR"
    assert dumped["clarification_required"] is False
