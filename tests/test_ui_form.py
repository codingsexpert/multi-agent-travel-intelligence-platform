"""Unit tests for travel request form processing and validation rules."""

from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from models.travel_request import (
    TravelRequest,
    TravelerPreferences,
    TripConstraints,
)


def create_form_payload(
    origin="Delhi",
    destination="Japan",
    start_offset=15,
    end_offset=25,
    travelers=2,
    budget=3500.0,
    currency="USD",
    interests=None,
    style="Balanced",
    accommodation="4 Star",
    direct_flights=False,
    kid_friendly=False,
    notes="Need authentic ramen experiences",
):
    """Helper mimicking the form submission payload builder in app/pages/new_trip.py."""
    today = date(2026, 10, 1)
    start_d = today + timedelta(days=start_offset)
    end_d = today + timedelta(days=end_offset)

    style_pace_map = {
        "Budget": "moderate",
        "Balanced": "moderate",
        "Premium": "relaxed",
        "Luxury": "relaxed",
    }
    pace = style_pace_map.get(style, "moderate")
    interests_list = interests if interests is not None else ["Food", "Culture"]

    must_include = [notes.strip()] if notes.strip() else []

    return TravelRequest(
        origin=origin,
        destination=destination,
        start_date=start_d,
        end_date=end_d,
        travelers=travelers,
        budget=budget,
        currency=currency,
        preferences=TravelerPreferences(
            interests=interests_list,
            pace=pace,
            accommodation_type=accommodation.lower(),
            cabin_class="economy" if style in ["Budget", "Balanced"] else "premium_economy",
        ),
        constraints=TripConstraints(
            direct_flights_only=direct_flights,
            kid_friendly=kid_friendly,
            must_include=must_include,
        ),
    )


def test_valid_form_submission():
    """Verify that a standard user form submission validates into a valid TravelRequest."""
    req = create_form_payload(
        origin="Delhi",
        destination="Japan",
        travelers=2,
        budget=3500.0,
        currency="USD",
        interests=["Food", "Culture", "History"],
        style="Balanced",
        accommodation="4 Star",
        direct_flights=True,
        kid_friendly=False,
    )

    assert req.origin == "Delhi"
    assert req.destination == "Japan"
    assert req.travelers == 2
    assert req.budget == 3500.0
    assert req.currency == "USD"
    assert req.preferences.pace == "moderate"
    assert req.preferences.interests == ["Food", "Culture", "History"]
    assert req.preferences.accommodation_type == "4 star"
    assert req.constraints.direct_flights_only is True
    assert req.constraints.kid_friendly is False
    assert len(req.constraints.must_include) == 1


def test_invalid_dates_in_form():
    """Verify that form validation catches return date prior to departure date."""
    with pytest.raises(ValidationError) as exc:
        create_form_payload(start_offset=20, end_offset=10)

    assert "end_date" in str(exc.value)
    assert "must be on or after start_date" in str(exc.value)


def test_invalid_traveler_count_in_form():
    """Verify that form validation catches zero or negative travelers."""
    with pytest.raises(ValidationError) as exc_zero:
        create_form_payload(travelers=0)
    assert "travelers" in str(exc_zero.value)

    with pytest.raises(ValidationError) as exc_neg:
        create_form_payload(travelers=-3)
    assert "travelers" in str(exc_neg.value)


def test_invalid_budget_in_form():
    """Verify that form validation catches zero or negative budget."""
    with pytest.raises(ValidationError) as exc_zero:
        create_form_payload(budget=0.0)
    assert "budget" in str(exc_zero.value)

    with pytest.raises(ValidationError) as exc_neg:
        create_form_payload(budget=-500.0)
    assert "budget" in str(exc_neg.value)


def test_preference_and_style_mappings():
    """Verify that different travel style choices map properly to preferences."""
    luxury_req = create_form_payload(
        style="Luxury",
        accommodation="5 Star",
        interests=["Shopping", "Photography", "Relaxation"],
    )
    assert luxury_req.preferences.pace == "relaxed"
    assert luxury_req.preferences.cabin_class == "premium_economy"
    assert luxury_req.preferences.accommodation_type == "5 star"
    assert "Shopping" in luxury_req.preferences.interests

    budget_req = create_form_payload(
        style="Budget",
        accommodation="Hostel",
        interests=["Adventure", "Nature"],
    )
    assert budget_req.preferences.pace == "moderate"
    assert budget_req.preferences.cabin_class == "economy"
    assert budget_req.preferences.accommodation_type == "hostel"
