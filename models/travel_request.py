"""Pydantic models for travel requirements and user preferences."""

from datetime import date, datetime, timezone
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator


class TravelerPreferences(BaseModel):
    """Traveler style and qualitative preferences."""

    interests: List[str] = Field(
        default_factory=list,
        description="Key interests (e.g., culinary, history, nature, shopping)",
    )
    pace: str = Field(
        default="moderate",
        description="Travel pace: relaxed, moderate, or fast-paced",
    )
    accommodation_type: str = Field(
        default="hotel",
        description="Lodging preference (e.g., hotel, boutique, resort, apartment)",
    )
    cabin_class: str = Field(
        default="economy",
        description="Flight cabin class: economy, premium_economy, business, first",
    )
    dietary_restrictions: List[str] = Field(
        default_factory=list,
        description="Dietary requirements (e.g., vegetarian, halal, gluten-free)",
    )


class TripConstraints(BaseModel):
    """Hard constraints and requirements governing trip feasibility."""

    must_include: List[str] = Field(
        default_factory=list,
        description="Mandatory landmarks or experiences",
    )
    avoid: List[str] = Field(
        default_factory=list,
        description="Areas, activities, or airlines to exclude",
    )
    direct_flights_only: bool = Field(
        default=False,
        description="Require non-stop flights only",
    )
    kid_friendly: bool = Field(
        default=False,
        description="Ensure pacing and venues are suitable for children",
    )
    max_transit_hours: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum acceptable one-way transit duration in hours",
    )


class TripMetadata(BaseModel):
    """Operational metadata tracking trip entity lifecycle."""

    trip_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the trip record",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    status: str = Field(
        default="DRAFT",
        description="Lifecycle status (DRAFT, PLANNING, APPROVED, CANCELLED)",
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Revision version number for replanning history",
    )


class TravelRequest(BaseModel):
    """Core structured travel request schema."""

    origin: str = Field(
        ...,
        min_length=2,
        description="Departure city or IATA airport code (e.g., 'SFO' or 'San Francisco')",
    )
    destination: str = Field(
        ...,
        min_length=2,
        description="Destination city or region (e.g., 'Tokyo' or 'Paris')",
    )
    start_date: date = Field(
        ...,
        description="Trip departure date (YYYY-MM-DD)",
    )
    end_date: date = Field(
        ...,
        description="Trip return date (YYYY-MM-DD)",
    )
    travelers: int = Field(
        default=1,
        ge=1,
        description="Number of travelers (minimum 1)",
    )
    budget: float = Field(
        ...,
        gt=0.0,
        description="Total allocated budget limit (must be strictly positive)",
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Three-letter ISO currency code (e.g., USD, EUR, JPY)",
    )
    preferences: TravelerPreferences = Field(
        default_factory=TravelerPreferences,
        description="Qualitative traveler preferences",
    )
    constraints: TripConstraints = Field(
        default_factory=TripConstraints,
        description="Hard operational constraints",
    )
    metadata: TripMetadata = Field(
        default_factory=TripMetadata,
        description="Trip metadata and state tracking",
    )

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Ensure currency is uppercase 3-letter code."""
        return v.strip().upper()

    @field_validator("origin", "destination")
    @classmethod
    def strip_locations(cls, v: str) -> str:
        """Strip extra whitespace from locations."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Location cannot be empty or blank")
        return cleaned

    @model_validator(mode="after")
    def validate_dates(self) -> "TravelRequest":
        """Verify return date is on or after departure date."""
        if self.end_date < self.start_date:
            raise ValueError(
                f"end_date ({self.end_date}) must be on or after start_date ({self.start_date})"
            )
        return self

    @property
    def duration_days(self) -> int:
        """Calculate total trip duration in days (inclusive of travel day)."""
        return (self.end_date - self.start_date).days + 1
