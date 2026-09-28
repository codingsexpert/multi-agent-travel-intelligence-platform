"""Deterministic Budget Engine for Travel Intelligence Platform.

Performs pure Python financial arithmetic with strict constraints,
zero LLM arithmetic hallucination, category breakdowns, and currency consistency checks.
"""

from typing import List, Dict, Any, Optional
from models.budget import (
    BudgetItemCategory,
    BudgetItem,
    BudgetBreakdown,
    BudgetStatus,
    BudgetSummary,
)
from utils.logger import logger


# Deterministic standard daily allowances normalized by currency
DAILY_FOOD_RATES: Dict[str, float] = {
    "USD": 50.0,
    "EUR": 45.0,
    "GBP": 40.0,
    "INR": 1500.0,
    "JPY": 6000.0,
    "AUD": 70.0,
    "CAD": 65.0,
}

DAILY_TRANSPORT_RATES: Dict[str, float] = {
    "USD": 20.0,
    "EUR": 18.0,
    "GBP": 16.0,
    "INR": 600.0,
    "JPY": 2500.0,
    "AUD": 28.0,
    "CAD": 25.0,
}

DAILY_MISC_RATES: Dict[str, float] = {
    "USD": 15.0,
    "EUR": 14.0,
    "GBP": 12.0,
    "INR": 500.0,
    "JPY": 2000.0,
    "AUD": 20.0,
    "CAD": 18.0,
}


class BudgetEngine:
    """Deterministic calculation engine for trip budgeting, line-item auditing, and variance analysis."""

    CURRENCY_DISCLAIMER = (
        "Currency conversion will be implemented when the Currency MCP/API is introduced. "
        "All figures are currently assumed normalized to the trip base currency."
    )

    @staticmethod
    def calculate_budget(
        total_budget: float,
        currency: str = "USD",
        items: Optional[List[BudgetItem]] = None,
        duration_days: int = 1,
        travelers: int = 1,
    ) -> BudgetSummary:
        """Calculate aggregate budget summary deterministically from line items.

        Args:
            total_budget: Overall spending cap specified by the traveler.
            currency: Target ISO currency code.
            items: Explicit list of BudgetItem records.
            duration_days: Length of trip in days.
            travelers: Headcount of travelers.

        Returns:
            Validated BudgetSummary instance.
        """
        if total_budget < 0:
            raise ValueError(f"Total budget cannot be negative: {total_budget}")

        line_items = items or []
        warnings: List[str] = []

        cat_totals: Dict[BudgetItemCategory, float] = {cat: 0.0 for cat in BudgetItemCategory}

        # Audit items, detect currency mismatches, and sum categories
        for item in line_items:
            item_total = item.total_cost
            cat_totals[item.category] = round(cat_totals[item.category] + item_total, 2)

            if item.currency.upper() != currency.upper():
                rate_str = ""
                try:
                    from mcp.client import MCPClient
                    fx_res = MCPClient.call_tool(
                        agent_name="budget",
                        tool_name="get_exchange_rate",
                        arguments={"base_currency": item.currency, "target_currency": currency},
                    )
                    if fx_res.success and fx_res.data:
                        rate = fx_res.data.get("exchange_rate", 1.0)
                        rate_str = f" (Benchmark Rate: 1 {item.currency.upper()} = {rate} {currency.upper()})"
                except Exception:
                    pass

                warning_msg = (
                    f"Currency mismatch detected for '{item.description}': "
                    f"item currency is '{item.currency}' but trip currency is '{currency}'.{rate_str} "
                    f"{BudgetEngine.CURRENCY_DISCLAIMER}"
                )
                warnings.append(warning_msg)
                logger.warning(f"[BudgetEngine] {warning_msg}")

        # Compute totals
        total_estimated = round(sum(cat_totals.values()), 2)
        remaining = round(total_budget - total_estimated, 2)

        if total_budget > 0:
            utilization = round((total_estimated / total_budget) * 100, 2)
        else:
            utilization = 0.0 if total_estimated == 0 else 100.0

        # Enforce STRICT budget strategy
        if total_estimated > total_budget:
            within_budget = False
            status = BudgetStatus.OVER_BUDGET
            overage = round(total_estimated - total_budget, 2)
            budget_warning = (
                f"OVER_BUDGET: {currency} {overage:,.2f} above budget "
                f"({utilization}% utilized, estimated: {currency} {total_estimated:,.2f}, budget: {currency} {total_budget:,.2f})."
            )
            warnings.append(budget_warning)
            logger.info(f"[BudgetEngine] {budget_warning}")
        elif total_estimated == total_budget:
            within_budget = True
            status = BudgetStatus.EXACT
        else:
            within_budget = True
            status = BudgetStatus.WITHIN_BUDGET

        breakdown = BudgetBreakdown(
            flights=cat_totals[BudgetItemCategory.FLIGHTS],
            hotels=cat_totals[BudgetItemCategory.HOTELS],
            activities=cat_totals[BudgetItemCategory.ACTIVITIES],
            food=cat_totals[BudgetItemCategory.FOOD],
            transport=cat_totals[BudgetItemCategory.TRANSPORT],
            miscellaneous=cat_totals[BudgetItemCategory.MISCELLANEOUS],
        )

        return BudgetSummary(
            total_budget=round(total_budget, 2),
            total_estimated_cost=total_estimated,
            remaining_budget=remaining,
            utilization_percentage=utilization,
            within_budget=within_budget,
            status=status,
            currency=currency.upper(),
            breakdown=breakdown,
            items=line_items,
            warnings=warnings,
            demo_data=all(item.demo_data for item in line_items) if line_items else True,
        )

    @classmethod
    def calculate_from_state(cls, state: Dict[str, Any]) -> BudgetSummary:
        """Extract domain agent deliverables from TravelState and calculate structured budget.

        Builds line items from flights, hotels, activities, and standard deterministic food/transport allowances.
        """
        currency = str(state.get("currency") or "USD").upper()
        total_budget = float(state.get("budget") or 0.0)
        duration_days = max(int(state.get("duration") or 1), 1)
        travelers = max(int(state.get("travelers") or 1), 1)

        items: List[BudgetItem] = []

        # 1. Flights line item (take primary recommended option)
        flight_options = state.get("flight_options") or []
        if flight_options:
            primary_flight = flight_options[0]
            flight_price = float(primary_flight.get("price") or 0.0)
            flight_currency = str(primary_flight.get("currency") or currency).upper()
            airline = primary_flight.get("airline", "Airline")
            flight_num = primary_flight.get("flight_number", "FL-101")
            items.append(
                BudgetItem(
                    category=BudgetItemCategory.FLIGHTS,
                    description=f"{airline} Flight ({flight_num}) - {primary_flight.get('stops', 0)} stop(s)",
                    amount=flight_price,
                    currency=flight_currency,
                    quantity=1,
                    source=primary_flight.get("source", "[DEMO_DATA] Mock Airline Service"),
                    demo_data=primary_flight.get("demo_data", True),
                )
            )

        # 2. Hotels line item (take primary lodging option)
        hotel_options = state.get("hotel_options") or []
        if hotel_options:
            primary_hotel = hotel_options[0]
            hotel_price = float(primary_hotel.get("total_price") or 0.0)
            hotel_currency = str(primary_hotel.get("currency") or currency).upper()
            hotel_name = primary_hotel.get("name", "Hotel Accommodation")
            items.append(
                BudgetItem(
                    category=BudgetItemCategory.HOTELS,
                    description=f"{hotel_name} ({duration_days} nights)",
                    amount=hotel_price,
                    currency=hotel_currency,
                    quantity=1,
                    source=primary_hotel.get("source", "[DEMO_DATA] Mock Hotel Service"),
                    demo_data=primary_hotel.get("demo_data", True),
                )
            )

        # 3. Activities line items
        activities = state.get("activities") or []
        for act in activities:
            act_cost = float(act.get("estimated_cost") or 0.0)
            act_currency = str(act.get("currency") or currency).upper()
            act_name = act.get("name", "Local Experience")
            items.append(
                BudgetItem(
                    category=BudgetItemCategory.ACTIVITIES,
                    description=act_name,
                    amount=act_cost,
                    currency=act_currency,
                    quantity=travelers,
                    source=act.get("source", "[DEMO_DATA] Mock Activity Service"),
                    demo_data=act.get("demo_data", True),
                )
            )

        # 4. Deterministic Food estimate
        daily_food = DAILY_FOOD_RATES.get(currency, 50.0)
        items.append(
            BudgetItem(
                category=BudgetItemCategory.FOOD,
                description=f"Estimated Dining & Food ({travelers} traveler(s) × {duration_days} day(s))",
                amount=daily_food,
                currency=currency,
                quantity=travelers * duration_days,
                source="[DETERMINISTIC] Daily Meal Model",
                demo_data=True,
            )
        )

        # 5. Deterministic Local Transport estimate
        daily_trans = DAILY_TRANSPORT_RATES.get(currency, 20.0)
        items.append(
            BudgetItem(
                category=BudgetItemCategory.TRANSPORT,
                description=f"Local Public Transit & Transfers ({travelers} traveler(s) × {duration_days} day(s))",
                amount=daily_trans,
                currency=currency,
                quantity=travelers * duration_days,
                source="[DETERMINISTIC] Local Transit Model",
                demo_data=True,
            )
        )

        # 6. Deterministic Miscellaneous Buffer
        daily_misc = DAILY_MISC_RATES.get(currency, 15.0)
        items.append(
            BudgetItem(
                category=BudgetItemCategory.MISCELLANEOUS,
                description=f"Incidental & Connectivity Buffer ({duration_days} day(s))",
                amount=daily_misc,
                currency=currency,
                quantity=duration_days,
                source="[DETERMINISTIC] Incidental Model",
                demo_data=True,
            )
        )

        return cls.calculate_budget(
            total_budget=total_budget,
            currency=currency,
            items=items,
            duration_days=duration_days,
            travelers=travelers,
        )
