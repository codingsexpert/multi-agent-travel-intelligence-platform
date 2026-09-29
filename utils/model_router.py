"""Centralized Model Router and Task Complexity Policy Engine.

Enforces deterministic model tier selection:
- SIMPLE: extraction, classification, normalization, formatting -> model_simple (e.g. gpt-4o-mini)
- MEDIUM: research synthesis, constraint analysis, selection reasoning -> model_medium (e.g. gpt-4o-mini)
- COMPLEX: multi-constraint trip planning, dynamic replanning, conflict resolution -> model_complex (e.g. gpt-4o)
- PYTHON: deterministic calculations (budget, validation rules) -> pure Python, 0 LLM tokens

Provides:
- Deterministic routing policy controlled by application logic (never delegated to LLM discretion)
- Safe fallback strategy on model failure (MEDIUM/COMPLEX -> configured fallback without loops)
- Workflow cost budget enforcement before expensive reasoning
- Integration with CostTracker and ObservabilityService
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, Union

from config.settings import Settings, get_settings
from utils.cost import cost_tracker
from utils.exceptions import ServiceError

logger = logging.getLogger("travel_platform.model_router")

T = TypeVar("T")


class WorkflowBudgetExceededError(ServiceError):
    """Raised when workflow cost, token, or model call ceiling is exceeded."""
    pass


class ModelTier(str, Enum):
    """Categorical complexity tiers for LLM task assignment."""
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"
    PYTHON = "PYTHON"


class TaskType(str, Enum):
    """Recognized travel intelligence operational task types."""
    INPUT_EXTRACTION = "input_extraction"
    EXTRACTION = "input_extraction"
    PLANNER = "planner"
    FLIGHT_REASONING = "flight_reasoning"
    FLIGHT_SELECTION = "flight_reasoning"
    HOTEL_REASONING = "hotel_reasoning"
    HOTEL_SELECTION = "hotel_reasoning"
    ACTIVITY_REASONING = "activity_reasoning"
    ACTIVITY_SELECTION = "activity_reasoning"
    WEATHER_NORMALIZATION = "weather_normalization"
    RESEARCH_SYNTHESIS = "research_synthesis"
    BUDGET_CALCULATION = "budget_calculation"
    VALIDATION_RULES = "validation_rules"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DYNAMIC_REPLANNING = "dynamic_replanning"
    CLARIFICATION = "clarification"
    SUMMARIZATION = "summarization"
    ITINERARY_SYNTHESIS = "itinerary_synthesis"


# Deterministic application routing policy: TaskType -> (ModelTier, Reason)
ROUTING_POLICY: Dict[TaskType, Tuple[ModelTier, str]] = {
    TaskType.INPUT_EXTRACTION: (ModelTier.SIMPLE, "Structured JSON extraction and entity normalization"),
    TaskType.WEATHER_NORMALIZATION: (ModelTier.SIMPLE, "Meteorological range normalization and alert categorization"),
    TaskType.CLARIFICATION: (ModelTier.SIMPLE, "Targeted question formulation for missing travel parameters"),
    TaskType.SUMMARIZATION: (ModelTier.SIMPLE, "Concise summary generation of verified travel components"),
    TaskType.FLIGHT_REASONING: (ModelTier.MEDIUM, "Schedule trade-offs and cabin constraint filtering"),
    TaskType.HOTEL_REASONING: (ModelTier.MEDIUM, "Neighborhood trade-offs and guest capacity alignment"),
    TaskType.ACTIVITY_REASONING: (ModelTier.MEDIUM, "Pacing-aware daily experience and dining curation"),
    TaskType.RESEARCH_SYNTHESIS: (ModelTier.MEDIUM, "Hybrid RAG and fresh web source reconciliation"),
    TaskType.PLANNER: (ModelTier.COMPLEX, "Multi-constraint travel requirement decomposition and strategy"),
    TaskType.DYNAMIC_REPLANNING: (ModelTier.COMPLEX, "Disruption impact analysis and selective state replanning"),
    TaskType.CONFLICT_RESOLUTION: (ModelTier.COMPLEX, "Complex constraint reconciliation across multi-city schedules"),
    TaskType.ITINERARY_SYNTHESIS: (ModelTier.COMPLEX, "Final cohesive day-by-day itinerary synthesis"),
    TaskType.BUDGET_CALCULATION: (ModelTier.PYTHON, "Deterministic financial arithmetic (zero LLM math)"),
    TaskType.VALIDATION_RULES: (ModelTier.PYTHON, "Deterministic temporal and logistical constraint checks"),
}


class ModelRouter:
    """Centralized Model Router governing tier assignment, fallback paths, and cost budgets."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    @staticmethod
    def get_tier_for_task(task_type: Union[TaskType, str]) -> ModelTier:
        """Deterministically resolve model tier from task type."""
        if isinstance(task_type, str):
            try:
                task_enum = TaskType(task_type.lower())
            except ValueError:
                # Default unknown tasks safely based on naming
                if "extract" in task_type or "simple" in task_type:
                    return ModelTier.SIMPLE
                if "plan" in task_type or "replan" in task_type:
                    return ModelTier.COMPLEX
                return ModelTier.MEDIUM
        else:
            task_enum = task_type

        tier, _ = ROUTING_POLICY.get(task_enum, (ModelTier.MEDIUM, "Default medium complexity"))
        return tier

    @staticmethod
    def get_model_for_tier(tier: ModelTier, settings: Optional[Settings] = None) -> str:
        """Resolve the configured model identifier for a complexity tier."""
        cfg = settings or get_settings()
        if tier == ModelTier.SIMPLE:
            return cfg.model_simple
        elif tier == ModelTier.MEDIUM:
            return cfg.model_medium
        elif tier == ModelTier.COMPLEX:
            return cfg.model_complex
        elif tier == ModelTier.PYTHON:
            return "python_deterministic"
        return cfg.model_medium

    @staticmethod
    def get_fallback_model_for_tier(tier: ModelTier, settings: Optional[Settings] = None) -> str:
        """Resolve configured fallback model to prevent runaway expensive model loops."""
        cfg = settings or get_settings()
        if tier == ModelTier.SIMPLE:
            return cfg.model_simple_fallback
        elif tier == ModelTier.MEDIUM:
            return cfg.model_medium_fallback
        elif tier == ModelTier.COMPLEX:
            return cfg.model_complex_fallback
        elif tier == ModelTier.PYTHON:
            return "python_deterministic"
        return cfg.model_medium_fallback

    def route_task(self, task_type: Union[TaskType, str]) -> Dict[str, Any]:
        """Return routing decision metadata including tier, primary model, fallback model, and rationale."""
        tier = self.get_tier_for_task(task_type)
        primary_model = self.get_model_for_tier(tier, self.settings)
        fallback_model = self.get_fallback_model_for_tier(tier, self.settings)

        task_enum = TaskType(task_type) if isinstance(task_type, str) and task_type in TaskType._value2member_map_ else None
        reason = ROUTING_POLICY.get(task_enum, (tier, "Configured task assignment"))[1] if task_enum else "Heuristic task assignment"

        return {
            "task_type": task_type if isinstance(task_type, str) else task_type.value,
            "tier": tier.value,
            "model": primary_model,
            "fallback_model": fallback_model,
            "routing_reason": reason,
            "is_deterministic": (tier == ModelTier.PYTHON),
        }

    def check_workflow_budget(
        self,
        workflow_id: Optional[str] = None,
        max_cost: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_calls: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify whether workflow remains within configured cost, token, and call limits."""
        effective_cost = max_cost if max_cost is not None else self.settings.max_workflow_cost
        effective_tokens = max_tokens if max_tokens is not None else self.settings.max_total_tokens
        effective_calls = max_calls if max_calls is not None else self.settings.max_model_calls

        return cost_tracker.check_budget(
            workflow_id=workflow_id,
            max_cost=effective_cost,
            max_tokens=effective_tokens,
            max_calls=effective_calls,
        )

    def execute_with_routing(
        self,
        task_type: Union[TaskType, str],
        executable_fn: Optional[Callable[[str], T]] = None,
        agent_name: str = "agent",
        workflow_id: Optional[str] = None,
        max_retries: int = 1,
        executor_fn: Optional[Callable[[str], T]] = None,
    ) -> T:
        """Execute task callable using routed model tier with budget checks and safe fallback."""
        fn = executor_fn or executable_fn
        if fn is None:
            raise ValueError("execute_with_routing requires an executable callable.")

        route_meta = self.route_task(task_type)
        primary_model = route_meta["model"]
        fallback_model = route_meta["fallback_model"]
        tier = route_meta["tier"]

        # 1. Budget Verification
        is_ok, reason = self.check_workflow_budget(workflow_id)
        if not is_ok:
            logger.warning(f"[ModelRouter] Budget ceiling reached for workflow '{workflow_id}': {reason}")
            raise WorkflowBudgetExceededError(reason or "Workflow cost budget exceeded.")

        # 2. Primary Model Execution
        start_time = time.time()
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                result = fn(primary_model)
                latency_ms = round((time.time() - start_time) * 1000, 2)
                logger.info(
                    f"[ModelRouter] {agent_name} succeeded on tier {tier} ({primary_model}) in {latency_ms}ms"
                )
                return result
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"[ModelRouter] Attempt {attempt} failed on {primary_model} for task {task_type}: {exc}"
                )

        # 3. Controlled Fallback Execution (if primary model fails and fallback is distinct)
        if fallback_model and fallback_model != primary_model:
            logger.info(
                f"[ModelRouter] Engaging configured fallback model '{fallback_model}' for task {task_type} "
                f"(primary {primary_model} failed: {last_exception})"
            )
            # Track fallback event on primary model
            cost_tracker.record_usage(
                model_name=primary_model,
                input_tokens=0,
                output_tokens=0,
                agent_name=agent_name,
                workflow_id=workflow_id,
                latency_ms=0.0,
                success=False,
                is_fallback=True,
            )
            fallback_start = time.time()
            try:
                result = fn(fallback_model)
                latency_ms = round((time.time() - fallback_start) * 1000, 2)
                # Track fallback execution in cost tracker
                cost_tracker.record_usage(
                    model_name=fallback_model,
                    input_tokens=0,
                    output_tokens=0,
                    agent_name=agent_name,
                    workflow_id=workflow_id,
                    latency_ms=latency_ms,
                    success=True,
                    is_fallback=False,
                )
                return result
            except Exception as fb_exc:
                logger.error(
                    f"[ModelRouter] Fallback model '{fallback_model}' also failed for task {task_type}: {fb_exc}"
                )
                raise fb_exc from last_exception

        if last_exception:
            raise last_exception
        raise ServiceError(f"Model execution failed for task {task_type}")


# Global singleton instance
model_router = ModelRouter()
