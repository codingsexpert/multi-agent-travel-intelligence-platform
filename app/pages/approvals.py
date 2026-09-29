"""Human-in-the-Loop Approvals Page for Travel Command Center.

Guarantees:
- Read-only intelligence is autonomous
- High-impact transactional actions (bookings, payments, cancellations) require explicit user approval
- Server-side expiry and state-version verification
- Idempotent execution of mock transactional adapters
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime, timezone
from app.state.session import get_current_trip, get_current_user_id
from models.approval import ApprovalDecision, ApprovalStatus, ActionRiskLevel
from services.approval_service import approval_service, ApprovalError, StaleProposalError, InvalidApprovalStateError
from services.action_execution_service import action_execution_service
from repositories.approval_repository import approval_repository


def render_approvals_page():
    """Render the Approvals management page."""
    st.title("🛡️ Action Approvals (Human-in-the-Loop)")
    st.caption("Explicit Human Authorization for Transactional Travel Operations")

    # Safety Notice Banner
    st.info(
        "ℹ️ **Safety Boundary**: The AI agents autonomously perform read-only research, flight comparisons, "
        "and itinerary generation. **Transactional actions** (booking flights, reserving hotels, purchasing tickets, "
        "cancellations) strictly require your explicit approval. All transactions in this environment execute "
        "via safe mock demo providers — zero actual funds are charged.",
        icon="🔒",
    )

    user_id = get_current_user_id()
    current_trip = get_current_trip()
    trip_id = current_trip.get("id") if current_trip else None
    current_version = current_trip.get("itinerary_version", 1) if current_trip else 1

    tab_pending, tab_history, tab_propose = st.tabs(["⏳ Pending Approvals", "📜 Audit & Execution History", "🧪 Create Test Proposal"])

    with tab_pending:
        _render_pending_approvals(user_id=user_id, trip_id=trip_id, current_version=current_version)

    with tab_history:
        _render_approval_history(trip_id=trip_id, user_id=user_id)

    with tab_propose:
        _render_test_proposal_form(user_id=user_id, trip_id=trip_id, current_version=current_version)


def _render_pending_approvals(user_id: str, trip_id: str | None, current_version: int):
    """Render pending approvals list."""
    try:
        pending_requests = approval_service.get_pending_approvals(user_id=user_id, trip_id=trip_id)
    except Exception as e:
        st.error(f"Error fetching pending approvals: {str(e)}")
        pending_requests = []

    if not pending_requests:
        st.success("✅ No pending approval requests. All high-impact operations are cleared.")
        return

    st.subheader(f"Pending Authorizations ({len(pending_requests)})")

    for req in pending_requests:
        try:
            prop = approval_service.get_proposal(req.proposal_id, user_id=user_id)
        except Exception as e:
            st.warning(f"Could not load proposal {req.proposal_id}: {str(e)}")
            continue

        with st.container():
            st.markdown("---")
            risk_color = {
                ActionRiskLevel.LOW: "green",
                ActionRiskLevel.MEDIUM: "blue",
                ActionRiskLevel.HIGH: "orange",
                ActionRiskLevel.CRITICAL: "red",
            }.get(prop.risk_level, "gray")

            col_title, col_risk = st.columns([3, 1])
            with col_title:
                st.markdown(f"### {prop.action_type.replace('_', ' ').title()}")
                st.markdown(f"**Proposal ID:** `{prop.proposal_id}`")
            with col_risk:
                st.markdown(
                    f"<div style='text-align: right;'><span style='background: {risk_color}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>{prop.risk_level.value} RISK</span></div>",
                    unsafe_allow_html=True,
                )

            # Details Breakdown
            st.markdown(f"**Description:** {prop.description}")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Estimated Cost", f"{prop.estimated_cost:,.2f} {prop.currency}")
            with c2:
                st.metric("Target Version", f"v{prop.state_version}")
            with c3:
                st.metric("Current Trip Version", f"v{current_version}")
            with c4:
                expires_str = prop.expires_at.strftime("%Y-%m-%d %H:%M UTC") if prop.expires_at else "Never"
                st.metric("Expires At", expires_str)

            # Clear Mandatory Disclosure
            st.markdown(
                """
                <div style="background: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 6px; margin: 10px 0;">
                    <b>Summary Disclosure:</b><br/>
                    • <b>WHAT WILL HAPPEN:</b> Automated mock execution of transaction adapter<br/>
                    • <b>WHAT IT WILL COST:</b> {cost:,.2f} {currency}<br/>
                    • <b>TARGET TRIP:</b> {trip_id}<br/>
                    • <b>ITINERARY STATE VERSION:</b> v{state_ver}<br/>
                    • <b>EXPIRATION:</b> {expires}
                </div>
                """.format(
                    cost=prop.estimated_cost,
                    currency=prop.currency,
                    trip_id=prop.trip_id,
                    state_ver=prop.state_version,
                    expires=expires_str,
                ),
                unsafe_allow_html=True,
            )

            # High Risk Confirmation Requirement
            can_approve = True
            if prop.risk_level in [ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL]:
                confirmed = st.checkbox(
                    f"I have reviewed the details and explicitly authorize this transaction for {prop.estimated_cost:,.2f} {prop.currency}.",
                    key=f"chk_confirm_{req.approval_id}",
                )
                can_approve = confirmed

            col_btn1, col_btn2 = st.columns([1, 1])

            with col_btn1:
                if st.button("✅ Approve & Execute", key=f"btn_app_{req.approval_id}", disabled=not can_approve, type="primary"):
                    try:
                        approval_service.decide_approval(
                            approval_id=req.approval_id,
                            user_id=user_id,
                            decision=ApprovalDecision.APPROVED,
                            current_trip_version=current_version,
                        )
                        st.info("Executing approved transaction adapter...")
                        exec_res = action_execution_service.execute_proposal(
                            proposal_id=prop.proposal_id,
                            user_id=user_id,
                            current_trip_version=current_version,
                        )
                        if exec_res.status == ApprovalStatus.COMPLETED:
                            st.success(f"🎉 Transaction Confirmed! Confirmation Code: `{exec_res.confirmation_code}` (DEMO / MOCK)")
                        else:
                            st.error(f"❌ Execution failed: {exec_res.error_message}")
                        st.rerun()
                    except StaleProposalError as spe:
                        st.error(f"⚠️ Stale Proposal: {str(spe)}")
                    except Exception as exc:
                        st.error(f"Error approving: {str(exc)}")

            with col_btn2:
                rejection_reason = st.text_input("Rejection Reason (Optional)", key=f"txt_rej_{req.approval_id}", placeholder="e.g. Schedule changed")
                if st.button("❌ Reject Action", key=f"btn_rej_{req.approval_id}"):
                    try:
                        approval_service.decide_approval(
                            approval_id=req.approval_id,
                            user_id=user_id,
                            decision=ApprovalDecision.REJECTED,
                            rejection_reason=rejection_reason or "User rejected proposal",
                            current_trip_version=current_version,
                        )
                        st.warning("Action proposal has been rejected.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error rejecting: {str(exc)}")


def _render_approval_history(trip_id: str | None, user_id: str):
    """Render audit history and execution log."""
    st.subheader("Action Executions & Audit Trail")

    if not trip_id:
        st.info("Select or create an active trip to inspect its audit trail.")
        return

    executions = approval_repository.get_executions_for_trip(trip_id)
    audit_events = approval_repository.get_audit_events_for_trip(trip_id)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Confirmed Transactions")
        if not executions:
            st.caption("No transactional executions recorded for this trip.")
        else:
            for ex in reversed(executions):
                st.markdown(
                    f"""
                    - **Status:** `{ex.get('status')}`
                    - **Confirmation:** `{ex.get('confirmation_code', 'N/A')}`
                    - **Idempotency Key:** `{ex.get('idempotency_key')}`
                    - **Executed At:** {ex.get('executed_at', 'N/A')}
                    - **Provider:** `{ex.get('result_payload', {}).get('provider_type', 'DEMO / MOCK')}`
                    """
                )

    with col2:
        st.markdown("#### Immutable Audit Events")
        if not audit_events:
            st.caption("No audit events recorded.")
        else:
            for ev in reversed(audit_events):
                st.markdown(
                    f"• **`{ev.get('event_type')}`** by `{ev.get('actor')}` at `{ev.get('timestamp')}`"
                )


def _render_test_proposal_form(user_id: str, trip_id: str | None, current_version: int):
    """Render an interactive form to simulate proposing high-impact actions for testing."""
    st.subheader("Simulate Action Proposal")
    st.caption("Test the Human-in-the-Loop workflow by proposing a new high-impact action.")

    effective_trip_id = trip_id or "demo-trip-123"

    with st.form("test_proposal_form"):
        action_type = st.selectbox(
            "Action Type",
            [
                "book_flight",
                "book_hotel",
                "purchase_activity",
                "cancel_flight",
                "cancel_hotel",
                "search_flights",
            ],
        )
        description = st.text_input("Description", value=f"Simulated test {action_type} for vacation")
        cost = st.number_input("Estimated Cost", value=450.0, step=50.0)
        currency = st.selectbox("Currency", ["USD", "EUR", "INR", "GBP"], index=0)
        param_json = st.text_area("Parameters (JSON-like)", value='{"flight_number": "AI-202", "passenger_name": "Traveler"}')

        submitted = st.form_submit_button("Submit Proposal")
        if submitted:
            try:
                import json
                try:
                    params = json.loads(param_json)
                except Exception:
                    params = {"raw": param_json}

                proposal = approval_service.create_proposal(
                    trip_id=effective_trip_id,
                    user_id=user_id,
                    action_type=action_type,
                    description=description,
                    parameters=params,
                    state_version=current_version,
                    estimated_cost=float(cost),
                    currency=currency,
                    proposed_by="test_ui",
                )
                st.success(f"Proposal created! ID: `{proposal.proposal_id}` (Requires Approval: {proposal.requires_approval})")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create proposal: {str(e)}")
