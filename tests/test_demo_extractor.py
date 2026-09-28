"""Unit tests for deterministic requirement extraction in DEMO_MODE."""

from services.llm_service import DemoPlannerExtractor


def test_complete_travel_request_hinglish():
    """Verify parsing of arbitrary Hinglish travel request with currency conversion."""
    text = "Delhi se Japan 7 days ka trip plan karo, budget ₹1.5 lakh hai, 2 log hain, food + culture + nature pasand hai."
    result = DemoPlannerExtractor.extract(text)

    req = result.extracted_requirements
    assert req.origin == "Delhi"
    assert req.destination == "Japan"
    assert req.duration == 7
    assert req.travelers == 2
    assert req.budget == 150000.0
    assert req.currency == "INR"
    assert "food" in req.interests
    assert "culture" in req.interests
    assert "nature" in req.interests
    assert result.clarification_required is False
    assert result.is_demo is True
    assert len(result.assumptions) > 0


def test_complete_travel_request_english():
    """Verify parsing of clean English request with ISO dates."""
    text = "Trip from NYC to London from 2026-12-01 to 2026-12-10 for 2 people with a budget of $5000."
    result = DemoPlannerExtractor.extract(text)

    req = result.extracted_requirements
    assert req.origin == "Nyc"
    assert req.destination == "London"
    assert req.start_date == "2026-12-01"
    assert req.end_date == "2026-12-10"
    assert req.duration == 10
    assert req.travelers == 2
    assert req.budget == 5000.0
    assert req.currency == "USD"
    assert result.clarification_required is False


def test_missing_destination():
    """Verify missing destination is identified and clarification questions generated."""
    text = "Plan a 7-day trip from San Francisco for 2 people, budget $4000."
    result = DemoPlannerExtractor.extract(text)

    assert "destination" in result.missing_fields
    assert result.clarification_required is True
    assert any("Where would you like to travel" in q for q in result.clarification_questions)


def test_missing_origin():
    """Verify missing origin is identified."""
    text = "Trip to Tokyo for 10 days, 1 traveler, budget $3000."
    result = DemoPlannerExtractor.extract(text)

    assert "origin" in result.missing_fields
    assert result.clarification_required is True
    assert any("departing from" in q for q in result.clarification_questions)


def test_missing_dates_and_duration():
    """Verify missing schedule triggers clarification."""
    text = "Fly from London to Rome for 2 people with 1500 EUR budget."
    result = DemoPlannerExtractor.extract(text)

    assert "dates_or_duration" in result.missing_fields
    assert result.clarification_required is True


def test_missing_budget():
    """Verify missing budget triggers clarification."""
    text = "Trip from Seattle to Vancouver for 4 days, 2 travelers."
    result = DemoPlannerExtractor.extract(text)

    assert "budget" in result.missing_fields
    assert result.clarification_required is True
    assert any("budget and currency" in q for q in result.clarification_questions)


def test_minimal_incomplete_request():
    """Verify 'Japan trip plan karo' identifies all 4 missing critical fields."""
    text = "Japan trip plan karo."
    result = DemoPlannerExtractor.extract(text)

    assert result.extracted_requirements.destination == "Japan"
    assert "origin" in result.missing_fields
    assert "dates_or_duration" in result.missing_fields
    assert "travelers" in result.missing_fields
    assert "budget" in result.missing_fields
    assert result.clarification_required is True
    assert len(result.clarification_questions) >= 4


def test_conflicting_dates_end_before_start():
    """Verify conflict detected when end date is chronologically before start date."""
    text = "Trip from Paris to Berlin from 2026-10-15 to 2026-10-10, budget 2000 EUR, 1 traveler."
    result = DemoPlannerExtractor.extract(text)

    assert result.clarification_required is True
    assert any("End date" in c and "before start date" in c for c in result.conflicts)


def test_conflicting_invalid_date_format():
    """Verify handling of invalid dates."""
    text = "Trip from Paris to Berlin from 2026-99-99 to 2026-99-99, budget $2000, 1 traveler."
    result = DemoPlannerExtractor.extract(text)
    # The regex \b\d{4}-\d{2}-\d{2}\b matches, but date validation flags conflict
    assert result.clarification_required is True
    assert any("Invalid date format" in c for c in result.conflicts)


def test_invalid_traveler_count():
    """Verify non-positive travelers are detected as a conflict."""
    text = "Trip from Rome to Madrid for 0 travelers for 5 days with budget $1000."
    result = DemoPlannerExtractor.extract(text)
    assert result.clarification_required is True
    assert any("travelers must be at least 1" in c.lower() for c in result.conflicts)


def test_invalid_duration_zero():
    """Verify zero or negative duration is detected as a conflict."""
    text = "Trip from Rome to Madrid for 2 travelers for 0 days with budget $1000."
    result = DemoPlannerExtractor.extract(text)
    assert result.clarification_required is True
    assert any("duration must be at least 1" in c.lower() for c in result.conflicts)


def test_conflicting_negative_budget():
    """Verify negative budget is detected as a conflict."""
    text = "Trip from Rome to Madrid for 2 travelers for 5 days with budget -$500."
    result = DemoPlannerExtractor.extract(text)
    assert result.clarification_required is True
    assert any("budget cannot be negative" in c.lower() for c in result.conflicts)

