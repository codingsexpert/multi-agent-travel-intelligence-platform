"""Pydantic schemas for Planner Agent structured reasoning and extraction output."""

from typing import List, Optional
from pydantic import BaseModel, Field


class NormalizedTravelRequest(BaseModel):
    """Normalized travel parameters extracted from user natural-language input."""

    origin: Optional[str] = Field(default=None, description="Departure city or airport code")
    destination: Optional[str] = Field(default=None, description="Destination city, region, or country")
    start_date: Optional[str] = Field(default=None, description="Start date in ISO format YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="End date in ISO format YYYY-MM-DD")
    duration: Optional[int] = Field(default=None, description="Trip duration in calendar days")
    travelers: Optional[int] = Field(default=None, description="Total number of travelers")
    budget: Optional[float] = Field(default=None, description="Total budget limit")
    currency: Optional[str] = Field(default="USD", description="Currency symbol or 3-letter ISO code")
    interests: List[str] = Field(default_factory=list, description="Travel interests (e.g. food, culture, nature)")
    travel_style: Optional[str] = Field(default=None, description="Pacing and style (e.g. Budget, Balanced, Luxury)")
    accommodation_preference: Optional[str] = Field(default=None, description="Preferred lodging category")
    food_preferences: List[str] = Field(default_factory=list, description="Dietary preferences and dining interests")
    constraints: List[str] = Field(default_factory=list, description="Hard constraints (e.g. direct flights only)")
    additional_requirements: Optional[str] = Field(default=None, description="Free-text notes or special requests")


class ClarificationRequest(BaseModel):
    """Structured questions required when critical trip parameters are absent."""

    required: bool = Field(default=False, description="Whether clarification from user is required")
    missing_fields: List[str] = Field(default_factory=list, description="List of essential missing fields")
    questions: List[str] = Field(default_factory=list, description="User-facing numbered clarification questions")


class PlannerResult(BaseModel):
    """Comprehensive validated structured output from the Planner Agent reasoning node."""

    extracted_requirements: NormalizedTravelRequest = Field(
        description="Structured extraction of user travel specifications"
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Core requirements missing before specialized agents can begin (origin, destination, dates/duration, travelers, budget)",
    )
    conflicts: List[str] = Field(
        default_factory=list,
        description="Identified conflicting constraints (e.g. start date after end date, non-positive duration)",
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Safe defaults or assumptions made during parsing",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Advisory notes for the traveler or subsequent agents",
    )
    clarification_required: bool = Field(
        default=False,
        description="True if missing fields or unresolvable conflicts block planning",
    )
    clarification_questions: List[str] = Field(
        default_factory=list,
        description="Numbered clarification questions presented to traveler",
    )
    is_demo: bool = Field(
        default=False,
        description="True if output was produced via deterministic mock engine in DEMO_MODE",
    )
