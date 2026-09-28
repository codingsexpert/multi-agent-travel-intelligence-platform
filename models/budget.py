"""Pydantic v2 models for deterministic travel budget calculations."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class BudgetItemCategory(str, Enum):
    """Categorical classification for trip budget items."""

    FLIGHTS = "FLIGHTS"
    HOTELS = "HOTELS"
    ACTIVITIES = "ACTIVITIES"
    FOOD = "FOOD"
    TRANSPORT = "TRANSPORT"
    MISCELLANEOUS = "MISCELLANEOUS"


class BudgetItem(BaseModel):
    """Individual line item in the travel budget estimation."""

    category: BudgetItemCategory
    description: str
    amount: float = Field(ge=0.0, description="Unit cost in trip currency. Must be non-negative.")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code.")
    quantity: int = Field(default=1, ge=1, description="Quantity or count of units.")
    source: str = Field(default="[DEMO_DATA] Deterministic Cost Model", description="Attribution or engine source.")
    demo_data: bool = Field(default=True, description="Explicit indicator for synthetic/demo data.")

    @property
    def total_cost(self) -> float:
        """Calculate total line item cost accounting for quantity."""
        return round(self.amount * self.quantity, 2)


class BudgetBreakdown(BaseModel):
    """Aggregated financial breakdown by category."""

    flights: float = Field(default=0.0, ge=0.0)
    hotels: float = Field(default=0.0, ge=0.0)
    activities: float = Field(default=0.0, ge=0.0)
    food: float = Field(default=0.0, ge=0.0)
    transport: float = Field(default=0.0, ge=0.0)
    miscellaneous: float = Field(default=0.0, ge=0.0)


class BudgetStatus(str, Enum):
    """Financial feasibility status."""

    WITHIN_BUDGET = "WITHIN_BUDGET"
    EXACT = "EXACT"
    OVER_BUDGET = "OVER_BUDGET"


class BudgetSummary(BaseModel):
    """Comprehensive deterministic budget calculation result."""

    total_budget: float = Field(ge=0.0, description="Total traveler spending limit.")
    total_estimated_cost: float = Field(ge=0.0, description="Sum of all category estimated expenses.")
    remaining_budget: float = Field(description="Remaining budget variance (can be negative if over budget).")
    utilization_percentage: float = Field(ge=0.0, description="Percentage of total budget allocated (e.g., 85.5%).")
    within_budget: bool = Field(description="True if total estimated cost <= total budget.")
    status: BudgetStatus = Field(description="Categorical budget health status.")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    breakdown: BudgetBreakdown
    items: List[BudgetItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    demo_data: bool = Field(default=True)

    @field_validator("total_budget")
    @classmethod
    def validate_positive_budget(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Budget must be non-negative.")
        return round(v, 2)
