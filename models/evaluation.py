"""Evaluation Models and Schema Definitions for Travel Intelligence Platform.

Phase 16: Comprehensive Testing & Evaluation Framework.
Provides Pydantic models for:
- Synthetic evaluation scenarios
- Deterministic and qualitative evaluation metrics
- Critical failure tracking and policy enforcement
- Standardized scenario results and aggregate evaluation reports
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScenarioCategory(str, Enum):
    """Category of evaluation scenarios."""
    NORMAL_TRAVEL = "normal_travel"
    ADVERSARIAL_AND_INJECTION = "adversarial_and_injection"
    DYNAMIC_REPLANNING = "dynamic_replanning"
    SECURITY_AND_HITL = "security_and_hitl"


class CriticalFailureType(str, Enum):
    """Categorization of critical safety or integrity violations."""
    UNAUTHORIZED_BOOKING = "unauthorized_booking"
    PAYMENT_WITHOUT_APPROVAL = "payment_without_approval"
    SECRET_LEAKAGE = "secret_leakage"
    CROSS_USER_DATA_EXPOSURE = "cross_user_data_exposure"
    ARBITRARY_CODE_EXECUTION = "arbitrary_code_execution"
    APPROVAL_BYPASS = "approval_bypass"
    DUPLICATE_TRANSACTIONAL_EXECUTION = "duplicate_transactional_execution"
    SSRF_EXPLOIT = "ssrf_exploit"


class CriticalFailure(BaseModel):
    """Structured record of a critical failure that triggers overall evaluation run failure."""
    scenario_id: str = Field(..., description="ID of the scenario where the violation occurred")
    failure_type: CriticalFailureType = Field(..., description="Type of critical security or integrity breach")
    description: str = Field(..., description="Detailed description of the violation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = Field(default=None, description="Observability trace ID if available")


class MetricScore(BaseModel):
    """Individual metric evaluation score."""
    name: str = Field(..., description="Standard metric name (e.g. BUDGET_ADHERENCE)")
    score: float = Field(..., description="Numeric score or rate (0.0 to 1.0 or actual value)")
    passed: bool = Field(..., description="Whether the metric satisfied its threshold")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic details or breakdown")


class ScenarioEvaluationResult(BaseModel):
    """Result of evaluating a single scenario."""
    scenario_id: str
    scenario_title: str
    category: ScenarioCategory
    passed: bool
    critical_failures: List[CriticalFailure] = Field(default_factory=list)
    metrics: Dict[str, MetricScore] = Field(default_factory=dict)
    duration_ms: float = 0.0
    failure_reason: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    trace_id: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class LLMJudgeResult(BaseModel):
    """Structured result from an LLM-as-a-judge qualitative evaluation."""
    judge_model: str = Field(default="gpt-4o-mini", description="Model used as judge")
    rubric_version: str = Field(default="1.0.0", description="Evaluation rubric version")
    metric_name: str = Field(..., description="Name of qualitative metric evaluated")
    score: float = Field(..., ge=1.0, le=5.0, description="Qualitative rating on 1-5 scale")
    passed: bool = Field(..., description="Whether score meets minimum passing threshold")
    reasoning_summary: str = Field(..., description="Explanation of judge reasoning")


class EvaluationReport(BaseModel):
    """Standardized summary report of an entire evaluation suite run."""
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_scenarios: int = 0
    passed_count: int = 0
    failed_count: int = 0
    critical_failure_count: int = 0
    is_passed: bool = False

    # AI Quality Metrics (0.0 to 100.0 percent)
    budget_adherence_rate: float = 0.0
    constraint_satisfaction_rate: float = 0.0
    itinerary_validity_rate: float = 0.0
    tool_selection_accuracy: float = 0.0
    source_quality_rate: float = 0.0
    source_attribution_rate: float = 0.0
    hallucination_rate: float = 0.0

    # Reliability & Safety Metrics (0.0 to 100.0 percent)
    prompt_injection_block_rate: float = 0.0
    security_test_pass_rate: float = 0.0
    failure_recovery_rate: float = 0.0
    replan_success_rate: float = 0.0
    replan_selectivity: float = 0.0
    approval_enforcement_rate: float = 0.0
    duplicate_execution_rate: float = 0.0

    # Efficiency Metrics
    average_latency_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    average_tokens: float = 0.0
    average_cost_usd: float = 0.0
    cache_hit_rate: float = 0.0
    duplicate_call_prevention_rate: float = 0.0

    # Individual Scenario Results & Critical Failures
    scenario_results: List[ScenarioEvaluationResult] = Field(default_factory=list)
    critical_failures: List[CriticalFailure] = Field(default_factory=list)
