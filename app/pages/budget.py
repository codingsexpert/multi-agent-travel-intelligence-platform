"""Budget breakdown and financial optimization page."""

import streamlit as st
from app.state.session import get_current_trip


def render_budget_page() -> None:
    """Render budget structure and empty-state allocation metrics."""
    st.title("Trip Budget & Financial Allocation")
    st.markdown("Deterministic budget tracking, category ceilings, and financial feasibility enforcement.")

    st.markdown("---")

    active_trip = get_current_trip()

    if not active_trip:
        st.info("ℹ️ No active trip found. Visit the **New Trip** page to define a budget limit.")
        return

    # Total Budget Metric Card
    total_budget = active_trip.budget
    currency = active_trip.currency

    st.subheader(f"Total Budget Cap: {currency} {total_budget:,.2f}")

    # Notice of empty state
    st.info(
        "ℹ️ **Budget Engine Empty State**: Itemized cost calculations and constraint verification will be performed deterministically by the pure Python Budget Engine in Phase 6. No fake calculations are performed."
    )

    # Budget Categories Grid Structure
    st.markdown("### Expense Category Allocations")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="✈️ Flights", value="Pending", delta=None)
        st.caption("Flight Agent estimation (Phase 5)")

    with c2:
        st.metric(label="🏨 Hotels", value="Pending", delta=None)
        st.caption("Hotel Agent estimation (Phase 5)")

    with c3:
        st.metric(label="🎯 Activities", value="Pending", delta=None)
        st.caption("Activity Agent curation (Phase 5)")

    with c4:
        st.metric(label="🚆 Local Transport", value="Pending", delta=None)
        st.caption("Transit passes & fares (Phase 6)")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric(label="🍱 Food & Dining", value="Pending", delta=None)
        st.caption("Per diem dining allowance")

    with c6:
        st.metric(label="📦 Miscellaneous", value="Pending", delta=None)
        st.caption("Buffer & unexpected expenses")

    with c7:
        st.metric(label="🛡️ Contingency Reserve", value="Pending", delta=None)
        st.caption("Recommended 10% reserve")

    with c8:
        st.metric(label="💵 Remaining Budget", value=f"{currency} {total_budget:,.2f}", delta="100% Unallocated")
        st.caption("Awaiting plan synthesis")

    st.markdown("---")
    st.markdown("### Cost Breakdown Rules (Target Engine Behavior)")
    st.markdown(
        """
        - **Deterministic Math**: Executed in pure Python with exact floating-point precision (zero LLM arithmetic).
        - **Hard Budget Ceilings**: If total expenditure exceeds the allocated budget cap, the system triggers the Replanning Router.
        - **Currency Handling**: Normalized to ISO 4217 standard currency codes.
        """
    )
