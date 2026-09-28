"""Unit tests for the deterministic Budget Engine."""

import pytest
from pydantic import ValidationError
from models.budget import (
    BudgetItemCategory,
    BudgetItem,
    BudgetStatus,
    BudgetSummary,
)
from engines.budget_engine import BudgetEngine


def test_budget_within_budget():
    """Test standard budget scenario where total cost is under limit."""
    items = [
        BudgetItem(category=BudgetItemCategory.FLIGHTS, description="Flight", amount=500.0, currency="USD", quantity=1),
        BudgetItem(category=BudgetItemCategory.HOTELS, description="Hotel", amount=400.0, currency="USD", quantity=1),
        BudgetItem(category=BudgetItemCategory.ACTIVITIES, description="Activity", amount=100.0, currency="USD", quantity=1),
    ]
    summary = BudgetEngine.calculate_budget(total_budget=2000.0, currency="USD", items=items)

    assert summary.total_budget == 2000.0
    assert summary.total_estimated_cost == 1000.0
    assert summary.remaining_budget == 1000.0
    assert summary.utilization_percentage == 50.0
    assert summary.within_budget is True
    assert summary.status == BudgetStatus.WITHIN_BUDGET
    assert len(summary.warnings) == 0


def test_budget_exactly_at_budget():
    """Test exact budget match scenario."""
    items = [
        BudgetItem(category=BudgetItemCategory.FLIGHTS, description="Flight", amount=1000.0, currency="USD", quantity=1),
        BudgetItem(category=BudgetItemCategory.HOTELS, description="Hotel", amount=500.0, currency="USD", quantity=1),
    ]
    summary = BudgetEngine.calculate_budget(total_budget=1500.0, currency="USD", items=items)

    assert summary.total_estimated_cost == 1500.0
    assert summary.remaining_budget == 0.0
    assert summary.utilization_percentage == 100.0
    assert summary.within_budget is True
    assert summary.status == BudgetStatus.EXACT


def test_budget_over_budget():
    """Test strict budget mode when estimated cost exceeds budget limit."""
    items = [
        BudgetItem(category=BudgetItemCategory.FLIGHTS, description="Flight", amount=1200.0, currency="USD", quantity=1),
        BudgetItem(category=BudgetItemCategory.HOTELS, description="Hotel", amount=800.0, currency="USD", quantity=1),
    ]
    summary = BudgetEngine.calculate_budget(total_budget=1500.0, currency="USD", items=items)

    assert summary.total_estimated_cost == 2000.0
    assert summary.remaining_budget == -500.0
    assert summary.utilization_percentage == 133.33
    assert summary.within_budget is False
    assert summary.status == BudgetStatus.OVER_BUDGET
    assert any("OVER_BUDGET" in w for w in summary.warnings)
    assert any("500.00 above budget" in w for w in summary.warnings)


def test_budget_zero_budget():
    """Test zero budget allocation behavior."""
    items = [
        BudgetItem(category=BudgetItemCategory.ACTIVITIES, description="Museum", amount=50.0, currency="USD", quantity=1),
    ]
    summary = BudgetEngine.calculate_budget(total_budget=0.0, currency="USD", items=items)

    assert summary.total_budget == 0.0
    assert summary.total_estimated_cost == 50.0
    assert summary.remaining_budget == -50.0
    assert summary.within_budget is False
    assert summary.status == BudgetStatus.OVER_BUDGET


def test_budget_negative_cost_raises_validation_error():
    """Test that negative line item cost is strictly rejected by Pydantic."""
    with pytest.raises(ValidationError):
        BudgetItem(
            category=BudgetItemCategory.FLIGHTS,
            description="Illegal Negative Flight",
            amount=-250.0,
            currency="USD",
        )


def test_budget_negative_total_budget_raises_error():
    """Test that negative total budget cap raises ValueError."""
    with pytest.raises(ValueError, match="Total budget cannot be negative"):
        BudgetEngine.calculate_budget(total_budget=-500.0, currency="USD", items=[])


def test_budget_multiple_categories_aggregation():
    """Test aggregation across all distinct expense categories."""
    items = [
        BudgetItem(category=BudgetItemCategory.FLIGHTS, description="Flight", amount=600.0, currency="USD"),
        BudgetItem(category=BudgetItemCategory.HOTELS, description="Hotel", amount=400.0, currency="USD"),
        BudgetItem(category=BudgetItemCategory.ACTIVITIES, description="Tour", amount=150.0, currency="USD"),
        BudgetItem(category=BudgetItemCategory.FOOD, description="Dining", amount=200.0, currency="USD"),
        BudgetItem(category=BudgetItemCategory.TRANSPORT, description="Metro", amount=50.0, currency="USD"),
        BudgetItem(category=BudgetItemCategory.MISCELLANEOUS, description="SIM Card", amount=30.0, currency="USD"),
    ]
    summary = BudgetEngine.calculate_budget(total_budget=2000.0, currency="USD", items=items)

    assert summary.breakdown.flights == 600.0
    assert summary.breakdown.hotels == 400.0
    assert summary.breakdown.activities == 150.0
    assert summary.breakdown.food == 200.0
    assert summary.breakdown.transport == 50.0
    assert summary.breakdown.miscellaneous == 30.0
    assert summary.total_estimated_cost == 1430.0
    assert summary.remaining_budget == 570.0


def test_budget_quantity_based_cost_calculation():
    """Test that item quantity properly scales total cost."""
    item = BudgetItem(
        category=BudgetItemCategory.ACTIVITIES,
        description="Theme Park Ticket",
        amount=75.0,
        currency="USD",
        quantity=4,
    )
    assert item.total_cost == 300.0

    summary = BudgetEngine.calculate_budget(total_budget=500.0, currency="USD", items=[item])
    assert summary.total_estimated_cost == 300.0
    assert summary.remaining_budget == 200.0


def test_budget_currency_mismatch_warning():
    """Test that differing currencies produce explicit warnings rather than silent conversion."""
    items = [
        BudgetItem(category=BudgetItemCategory.FLIGHTS, description="International Flight", amount=500.0, currency="EUR"),
        BudgetItem(category=BudgetItemCategory.HOTELS, description="Local Hotel", amount=300.0, currency="USD"),
    ]
    summary = BudgetEngine.calculate_budget(total_budget=1000.0, currency="USD", items=items)

    assert any("Currency mismatch" in w for w in summary.warnings)
    assert any("Currency conversion will be implemented when the Currency MCP/API is introduced" in w for w in summary.warnings)
