"""Budget breakdown and deterministic financial calculation page."""

import streamlit as st
from app.state.session import get_current_trip
from engines.budget_engine import BudgetEngine


def render_budget_page() -> None:
    """Render deterministic budget calculations, line items, and financial utilization."""
    st.title("Trip Budget & Financial Allocation")
    st.markdown("Deterministic budget tracking, category ceilings, and financial feasibility enforcement.")

    st.markdown("---")

    active_trip = get_current_trip()
    travel_state = st.session_state.get("travel_state", {})
    budget_data = travel_state.get("budget_breakdown") if travel_state else None

    # If no state breakdown yet, but an active trip exists, calculate on demand
    if not budget_data and active_trip:
        state_mock = {
            "budget": active_trip.budget,
            "currency": active_trip.currency,
            "travelers": active_trip.travelers,
            "duration": (active_trip.end_date - active_trip.start_date).days if active_trip.end_date and active_trip.start_date else 1,
            "origin": active_trip.origin,
            "destination": active_trip.destination,
            "flight_options": travel_state.get("flight_options", []),
            "hotel_options": travel_state.get("hotel_options", []),
            "activities": travel_state.get("activities", []),
        }
        try:
            summary = BudgetEngine.calculate_from_state(state_mock)
            budget_data = summary.model_dump()
        except Exception:
            budget_data = None

    if not active_trip and not budget_data:
        st.info("ℹ️ No active trip found. Visit the **New Trip** page to define travel requirements and budget.")
        return

    currency = budget_data.get("currency", active_trip.currency if active_trip else "USD")
    total_budget = float(budget_data.get("total_budget", active_trip.budget if active_trip else 0.0))
    total_estimated = float(budget_data.get("total_estimated_cost", 0.0))
    remaining = float(budget_data.get("remaining_budget", total_budget - total_estimated))
    utilization = float(budget_data.get("utilization_percentage", 0.0))
    within_budget = budget_data.get("within_budget", total_estimated <= total_budget)
    status_str = budget_data.get("status", "WITHIN_BUDGET" if within_budget else "OVER_BUDGET")

    # Status Notification Banner
    if not within_budget:
        overage = abs(remaining)
        st.error(
            f"🚨 **STRICT BUDGET ALERT — OVER BUDGET**: Estimated expenses exceed your limit by "
            f"**{currency} {overage:,.2f}** ({utilization}% utilized). Replanning or manual trim required."
        )
    else:
        st.success(
            f"✅ **BUDGET VERIFIED**: Total estimated expenses are within your limit "
            f"({utilization}% utilized, {currency} {remaining:,.2f} remaining buffer)."
        )

    # Top Metric KPI Bar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Total Budget Limit", value=f"{currency} {total_budget:,.2f}")
    with c2:
        st.metric(
            label="Estimated Total Cost",
            value=f"{currency} {total_estimated:,.2f}",
            delta=f"{utilization}% Utilized",
            delta_color="inverse" if not within_budget else "normal",
        )
    with c3:
        st.metric(
            label="Remaining Variance",
            value=f"{currency} {remaining:,.2f}",
            delta="Buffer" if remaining >= 0 else "Deficit",
            delta_color="normal" if remaining >= 0 else "inverse",
        )
    with c4:
        status_label = "🟢 Within Budget" if within_budget else "🔴 Over Budget"
        st.metric(label="Feasibility Status", value=status_label)

    st.caption("ℹ️ *Currency conversion will be implemented when the Currency MCP/API is introduced. All figures are currently normalized to the trip base currency.*")

    st.markdown("---")

    # Category Breakdown
    st.subheader("Category Cost Breakdown")
    breakdown = budget_data.get("breakdown") or {}
    b_flights = float(breakdown.get("flights", 0.0))
    b_hotels = float(breakdown.get("hotels", 0.0))
    b_activities = float(breakdown.get("activities", 0.0))
    b_food = float(breakdown.get("food", 0.0))
    b_trans = float(breakdown.get("transport", 0.0))
    b_misc = float(breakdown.get("miscellaneous", 0.0))

    cat_cols = st.columns(6)
    with cat_cols[0]:
        st.metric("✈️ Flights", f"{currency} {b_flights:,.2f}")
    with cat_cols[1]:
        st.metric("🏨 Hotels", f"{currency} {b_hotels:,.2f}")
    with cat_cols[2]:
        st.metric("🎯 Activities", f"{currency} {b_activities:,.2f}")
    with cat_cols[3]:
        st.metric("🍱 Dining", f"{currency} {b_food:,.2f}")
    with cat_cols[4]:
        st.metric("🚆 Transit", f"{currency} {b_trans:,.2f}")
    with cat_cols[5]:
        st.metric("📦 Misc Buffer", f"{currency} {b_misc:,.2f}")

    # Itemized Table
    st.markdown("---")
    st.subheader("Itemized Financial Audit Log")

    items = budget_data.get("items") or []
    if items:
        table_rows = []
        for it in items:
            table_rows.append({
                "Category": it.get("category"),
                "Description": it.get("description"),
                "Unit Rate": f"{it.get('currency', currency)} {it.get('amount', 0):,.2f}",
                "Qty": it.get("quantity", 1),
                "Total Amount": f"{it.get('currency', currency)} {(it.get('amount', 0) * it.get('quantity', 1)):,.2f}",
                "Source": it.get("source", "[DEMO_DATA]"),
            })
        st.dataframe(table_rows, use_container_width=True)
    else:
        st.info("No itemized entries found. Run Travel Planning to generate domain quotes.")

    # Any warnings
    warnings = budget_data.get("warnings") or []
    if warnings:
        st.markdown("### Budget Warnings & Notices")
        for w in warnings:
            st.warning(f"⚠️ {w}")
