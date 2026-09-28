"""Unit tests for Pydantic travel data models and validation rules."""

from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
    TripMetadata,
)


def test_valid_travel_request():
    """Verify that a valid TravelRequest instantiates with correct defaults and fields."""
    start = date(2026, 10, 1)
    end = date(2026, 10, 8)
    req = TravelRequest(
        origin="SFO",
        destination="Tokyo",
        start_date=start,
        end_date=end,
        travelers=2,
        budget=5000.0,
        currency="usd",  # Should be normalized to uppercase
        preferences=TravelerPreferences(
            interests=["Culinary", "Culture"],
            pace="relaxed",
        ),
        constraints=TripConstraints(
            direct_flights_only=True,
            kid_friendly=False,
        ),
    )

    assert req.origin == "SFO"
    assert req.destination == "Tokyo"
    assert req.travelers == 2
    assert req.budget == 5000.0
    assert req.currency == "USD"
    assert req.duration_days == 8
    assert req.preferences.pace == "relaxed"
    assert req.constraints.direct_flights_only is True
    assert req.metadata.status == "DRAFT"
    assert req.metadata.version == 1


def test_invalid_travel_dates():
    """Verify that an end_date prior to start_date raises a validation error."""
    start = date(2026, 10, 10)
    end = date(2026, 10, 5)  # Invalid: ends before it starts

    with pytest.raises(ValidationError) as exc_info:
        TravelRequest(
            origin="JFK",
            destination="London",
            start_date=start,
            end_date=end,
            travelers=1,
            budget=2000.0,
        )

    assert "end_date" in str(exc_info.value)
    assert "must be on or after start_date" in str(exc_info.value)


def test_invalid_travelers_count():
    """Verify that zero or negative travelers count raises a validation error."""
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)

    with pytest.raises(ValidationError) as exc_zero:
        TravelRequest(
            origin="LAX",
            destination="Rome",
            start_date=start,
            end_date=end,
            travelers=0,  # Invalid: minimum is 1
            budget=3000.0,
        )

    assert "travelers" in str(exc_zero.value)

    with pytest.raises(ValidationError) as exc_neg:
        TravelRequest(
            origin="LAX",
            destination="Rome",
            start_date=start,
            end_date=end,
            travelers=-2,  # Invalid: negative
            budget=3000.0,
        )

    assert "travelers" in str(exc_neg.value)


def test_invalid_budget():
    """Verify that zero or negative budget raises a validation error."""
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)

    with pytest.raises(ValidationError) as exc_zero:
        TravelRequest(
            origin="ORD",
            destination="Paris",
            start_date=start,
            end_date=end,
            travelers=1,
            budget=0.0,  # Invalid: must be gt 0
        )

    assert "budget" in str(exc_zero.value)

    with pytest.raises(ValidationError) as exc_neg:
        TravelRequest(
            origin="ORD",
            destination="Paris",
            start_date=start,
            end_date=end,
            travelers=1,
            budget=-1000.0,  # Invalid: negative
        )

    assert "budget" in str(exc_neg.value)


def test_empty_locations():
    """Verify that whitespace-only origin or destination fails validation."""
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)

    with pytest.raises(ValidationError):
        TravelRequest(
            origin="   ",
            destination="Tokyo",
            start_date=start,
            end_date=end,
            travelers=1,
            budget=2000.0,
        )
