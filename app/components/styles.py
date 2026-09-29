"""Shared Design System & Custom CSS for Travel Command Center.

Phase 17: Production Travel Command Center UI/UX.
Provides enterprise-grade, clean dark theme styles, typography hierarchy,
status badges (DEMO/LIVE, Workflow, Risk), card containers, and responsive layouts.
"""

import streamlit as st


def inject_custom_styles() -> None:
    """Inject centralized CSS design system tokens into the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Base typography & container polish */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        code, pre, .stCodeBlock {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Top header polish */
        .main-header {
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .main-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #F8FAFC;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }

        .main-subtitle {
            font-size: 0.9rem;
            color: #94A3B8;
            line-height: 1.4;
        }

        /* Enterprise Card Container */
        .travel-card {
            background: #111827;
            border: 1px solid #1F2937;
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.2);
            transition: border-color 0.15s ease-in-out;
        }

        .travel-card:hover {
            border-color: #374151;
        }

        .travel-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1F2937;
            padding-bottom: 0.75rem;
            margin-bottom: 0.75rem;
        }

        /* Status & Environment Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.025em;
            text-transform: uppercase;
        }

        .badge-live {
            background: rgba(59, 130, 246, 0.15);
            color: #60A5FA;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .badge-demo {
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-completed {
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-running {
            background: rgba(59, 130, 246, 0.15);
            color: #60A5FA;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .badge-warning {
            background: rgba(245, 158, 11, 0.15);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-failed {
            background: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-approval {
            background: rgba(168, 85, 247, 0.15);
            color: #C084FC;
            border: 1px solid rgba(168, 85, 247, 0.3);
        }

        .badge-rerun {
            background: rgba(249, 115, 22, 0.15);
            color: #FB923C;
            border: 1px solid rgba(249, 115, 22, 0.3);
        }

        .badge-reused {
            background: rgba(14, 165, 233, 0.15);
            color: #38BDF8;
            border: 1px solid rgba(14, 165, 233, 0.3);
        }

        /* Timeline Items for Replanning & Progress */
        .timeline-step {
            position: relative;
            padding-left: 1.75rem;
            margin-bottom: 1.25rem;
            border-left: 2px solid #374151;
        }

        .timeline-step:last-child {
            border-left: 2px solid transparent;
        }

        .timeline-dot {
            position: absolute;
            left: -0.45rem;
            top: 0.15rem;
            width: 0.75rem;
            height: 0.75rem;
            border-radius: 9999px;
            background: #60A5FA;
            border: 2px solid #111827;
        }

        .timeline-dot-completed {
            background: #34D399;
        }

        .timeline-dot-warning {
            background: #FBBF24;
        }

        /* Non-blocking warning boxes */
        .system-warning {
            background: rgba(245, 158, 11, 0.08);
            border-left: 3px solid #F59E0B;
            padding: 0.75rem 1rem;
            border-radius: 0 6px 6px 0;
            color: #FCD34D;
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }

        /* Useful Empty States */
        .empty-state {
            text-align: center;
            padding: 3rem 1.5rem;
            background: #111827;
            border: 1px dashed #374151;
            border-radius: 8px;
            margin: 1.5rem 0;
        }

        .empty-state-icon {
            font-size: 2.25rem;
            color: #64748B;
            margin-bottom: 0.75rem;
        }

        .empty-state-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 0.35rem;
        }

        .empty-state-desc {
            font-size: 0.85rem;
            color: #94A3B8;
            max-width: 420px;
            margin: 0 auto 1.25rem auto;
            line-height: 1.4;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
