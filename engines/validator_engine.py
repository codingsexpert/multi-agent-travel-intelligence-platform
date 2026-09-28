"""Deterministic Validator Engine for Travel Intelligence Platform.

Validates travel constraints, budget feasibility, temporal sequences,
travel-time conflicts, and specialized agent outputs with zero LLM hallucinations.
"""

from datetime import datetime, date, time
import re
from typing import List, Dict, Any, Optional

from models.validation import (
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
)
from models.budget import BudgetSummary, BudgetStatus
from utils.logger import logger


class ValidatorEngine:
    """Deterministic validation engine for travel planning integrity and feasibility."""

    @classmethod
    def validate_plan(
        cls,
        state: Dict[str, Any],
        budget_summary: Optional[BudgetSummary] = None,
    ) -> ValidationResult:
        """Execute exhaustive deterministic checks on the TravelState and BudgetSummary.

        Args:
            state: Active TravelState containing planning fields and agent deliverables.
            budget_summary: Optional pre-calculated BudgetSummary.

        Returns:
            ValidationResult with issues categorized into INFO, WARNING, and ERROR.
        """
        issues: List[ValidationIssue] = []

        # 1. Travelers Validation
        travelers = state.get("travelers")
        if travelers is None or travelers <= 0:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_TRAVELER_COUNT",
                    message=f"Traveler count must be a positive integer (found: {travelers}).",
                    component="travelers",
                    field="travelers",
                )
            )

        # 2. Dates Validation
        start_date_str = state.get("start_date")
        end_date_str = state.get("end_date")
        duration = state.get("duration")
        start_dt: Optional[date] = None
        end_dt: Optional[date] = None

        if start_date_str:
            try:
                start_dt = datetime.strptime(str(start_date_str)[:10], "%Y-%m-%d").date()
            except ValueError:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_DATE_FORMAT",
                        message=f"Start date '{start_date_str}' is not in valid YYYY-MM-DD format.",
                        component="dates",
                        field="start_date",
                    )
                )
        elif not duration:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_START_DATE",
                    message="Trip start date or duration is required.",
                    component="dates",
                    field="start_date",
                )
            )
        else:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="FLEXIBLE_DATES",
                    message=f"Trip has a duration of {duration} day(s) but calendar dates are not locked. Operating in flexible date mode.",
                    component="dates",
                    field="start_date",
                )
            )

        if end_date_str:
            try:
                end_dt = datetime.strptime(str(end_date_str)[:10], "%Y-%m-%d").date()
            except ValueError:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_DATE_FORMAT",
                        message=f"End date '{end_date_str}' is not in valid YYYY-MM-DD format.",
                        component="dates",
                        field="end_date",
                    )
                )
        elif start_dt and not duration:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_END_DATE",
                    message="Trip end date or duration is required.",
                    component="dates",
                    field="end_date",
                )
            )

        if start_dt and end_dt:
            if end_dt < start_dt:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_DATE_ORDER",
                        message=f"Trip end date ({end_dt}) cannot be before start date ({start_dt}).",
                        component="dates",
                        field="end_date",
                    )
                )

        # 3. Budget Validation
        budget = state.get("budget")
        if budget is not None and budget < 0:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="NEGATIVE_BUDGET",
                    message=f"Budget cannot be negative (found: {budget}).",
                    component="budget",
                    field="budget",
                )
            )

        if budget_summary is not None:
            if not budget_summary.within_budget:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="BUDGET_EXCEEDED",
                        message=(
                            f"Total estimated cost ({budget_summary.currency} {budget_summary.total_estimated_cost:,.2f}) "
                            f"exceeds traveler budget ({budget_summary.currency} {budget_summary.total_budget:,.2f}) "
                            f"by {budget_summary.currency} {abs(budget_summary.remaining_budget):,.2f}."
                        ),
                        component="budget",
                        field="total_budget",
                    )
                )
            for w in budget_summary.warnings:
                if "Currency mismatch" in w:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="CURRENCY_MISMATCH",
                            message=w,
                            component="budget",
                            field="currency",
                        )
                    )

        # 4. Flights Validation
        flight_options = state.get("flight_options") or []
        origin = state.get("origin")
        destination = state.get("destination")

        is_distant_trip = (
            origin
            and destination
            and origin.strip().lower() != destination.strip().lower()
        )

        if is_distant_trip and not flight_options:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_FLIGHT_OPTIONS",
                    message=f"No flight options found for route from {origin} to {destination}.",
                    component="flights",
                    field="flight_options",
                )
            )

        for flight in flight_options:
            dep_str = flight.get("departure", "")
            arr_str = flight.get("arrival", "")
            dep_time = cls._parse_iso_or_clock(dep_str)
            arr_time = cls._parse_iso_or_clock(arr_str)

            if dep_time and arr_time:
                # If flight departs and arrives on same date or datetime, verify departure < arrival
                if arr_time <= dep_time:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="FLIGHT_SCHEDULE_INCONSISTENCY",
                            message=(
                                f"Flight {flight.get('flight_number', '')} departure ({dep_str}) "
                                f"is at or after arrival ({arr_str})."
                            ),
                            component="flights",
                            field="departure",
                        )
                    )

        # 5. Hotels Validation
        hotel_options = state.get("hotel_options") or []
        duration = state.get("duration") or 1
        if duration >= 1 and not hotel_options:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_HOTEL_OPTIONS",
                    message="No lodging options available for the requested destination stay.",
                    component="hotels",
                    field="hotel_options",
                )
            )

        for hotel in hotel_options:
            price_per_night = hotel.get("price_per_night", 0)
            total_price = hotel.get("total_price", 0)
            if price_per_night < 0 or total_price < 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="NEGATIVE_HOTEL_PRICE",
                        message=f"Hotel '{hotel.get('name')}' contains negative pricing.",
                        component="hotels",
                        field="price_per_night",
                    )
                )

        # 6. Activities Validation
        activities = state.get("activities") or []
        seen_names = set()
        duplicate_names = set()

        for act in activities:
            name = act.get("name", "").strip().lower()
            if name:
                if name in seen_names:
                    duplicate_names.add(act.get("name"))
                seen_names.add(name)

            cost = act.get("estimated_cost", 0)
            if cost < 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="NEGATIVE_ACTIVITY_COST",
                        message=f"Activity '{act.get('name')}' has negative cost: {cost}.",
                        component="activities",
                        field="estimated_cost",
                    )
                )

        if duplicate_names:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DUPLICATE_ACTIVITIES",
                    message=f"Duplicate activity recommendations identified: {', '.join(duplicate_names)}.",
                    component="activities",
                    field="activities",
                )
            )

        # 7. Travel-Time Conflict Detection
        # If flight arrives around the time an activity is scheduled to start
        if flight_options and activities:
            first_flight = flight_options[0]
            arr_time = cls._parse_iso_or_clock(first_flight.get("arrival", ""))
            if arr_time:
                for act in activities:
                    time_slot = act.get("best_time", "")
                    conflict_found = cls._check_travel_time_conflict(
                        flight_arrival=arr_time,
                        activity_time_str=time_slot,
                    )
                    if conflict_found:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                code="POSSIBLE_TIME_CONFLICT",
                                message=(
                                    f"Activity '{act.get('name')}' scheduled for '{time_slot}' "
                                    f"may conflict with flight arrival at {first_flight.get('arrival')}. "
                                    f"Insufficient transfer buffer from airport to venue."
                                ),
                                component="activities",
                                field="best_time",
                            )
                        )

        # 8. Weather Validation (Partial agent failure detection)
        weather_list = state.get("weather")
        if not weather_list:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="WEATHER_UNAVAILABLE",
                    message=(
                        "Climatological forecast context is unavailable. Specialized Weather Agent "
                        "did not return observation data. No weather claims fabricated."
                    ),
                    component="weather",
                    field="weather",
                )
            )
        else:
            # Check weather date range coverage if available
            if isinstance(weather_list, list) and start_dt:
                weather_dates = []
                for obs in weather_list:
                    if isinstance(obs, dict) and "date" in obs:
                        try:
                            weather_dates.append(datetime.strptime(str(obs["date"])[:10], "%Y-%m-%d").date())
                        except ValueError:
                            pass
                if weather_dates and start_dt not in weather_dates:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            code="WEATHER_DATE_MISMATCH",
                            message="Weather forecast dates partially diverge from trip start date.",
                            component="weather",
                            field="date",
                        )
                    )

        # 9. General Demo Mode / Origin Requirements
        if not origin:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_ORIGIN",
                    message="Travel origin is mandatory for logistics validation.",
                    component="general",
                    field="origin",
                )
            )

        if not destination:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_DESTINATION",
                    message="Travel destination is mandatory for itinerary validation.",
                    component="general",
                    field="destination",
                )
            )

        if state.get("is_demo", False):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="DEMO_DATA_ACTIVE",
                    message="All pricing, flight schedules, and weather models utilize synthetic DEMO_DATA benchmarks.",
                    component="general",
                    field="is_demo",
                )
            )

        result = ValidationResult.from_issues(issues)
        logger.info(
            f"[ValidatorEngine] Validation completed: valid={result.valid}, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}, status={result.status}"
        )
        return result

    @classmethod
    def _parse_iso_or_clock(cls, time_str: str) -> Optional[datetime]:
        """Attempt to parse ISO datetime or HH:MM clock string into a comparable datetime object."""
        if not time_str:
            return None

        # Try full ISO datetime: 2026-10-15 11:45 or 2026-10-15T11:45
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                pass

        # Try 24-hr clock HH:MM: e.g. 10:00 or 11:45
        match = re.search(r"(\d{1,2}):(\d{2})", time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            today = date.today()
            return datetime.combine(today, time(hour, minute))

        return None

    @classmethod
    def _check_travel_time_conflict(
        cls,
        flight_arrival: datetime,
        activity_time_str: str,
    ) -> bool:
        """Detect temporal conflict between flight landing and scheduled activity start.

        Flags conflict if activity is explicitly in the Morning and flight lands after 10:00,
        or if activity clock time is within 90 minutes of flight arrival.
        """
        arrival_minutes = flight_arrival.hour * 60 + flight_arrival.minute

        # Check explicit clock in activity string: e.g., "10:15"
        act_clock = cls._parse_iso_or_clock(activity_time_str)
        if act_clock:
            act_minutes = act_clock.hour * 60 + act_clock.minute
            # Conflict if activity starts before flight arrival OR within 90 minutes after landing
            if act_minutes < arrival_minutes:
                return True
            if 0 <= (act_minutes - arrival_minutes) <= 90:
                return True

        # Check categorical time slots
        lower_slot = activity_time_str.lower()
        if "morning" in lower_slot and arrival_minutes >= 11 * 60:
            # Arriving at 11:00 or later conflicts with morning activities
            return True

        return False
