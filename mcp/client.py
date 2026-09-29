"""Standardized MCP Client Gateway providing typed execution, security enforcement, retries, and telemetry."""

import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import ValidationError

from models.mcp import (
    ToolExecutionStatus,
    ToolExecutionError,
    MCPToolCall,
    MCPToolResult,
)
from mcp.registry import MCPToolRegistry
from mcp.security import MCPSecurityManager
from guardrails.tools import ToolGuardrail
from guardrails.security import SecretRedactor
from mcp.providers.base import (
    ProviderError,
    ProviderConfigurationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderNetworkError,
    ProviderResponseValidationError,
    set_execution_mode,
    reset_execution_mode,
)
from utils.logger import logger
from utils.cache import intelligent_cache


class MCPClient:
    """Standardized client gateway connecting reasoning agents to external MCP tools."""

    _recent_calls: List[MCPToolCall] = []

    @classmethod
    def call_tool(
        cls,
        agent_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        is_demo: bool = True,
    ) -> MCPToolResult:
        """Execute an MCP tool on behalf of an agent with permission checking, schema validation, and telemetry.

        Args:
            agent_name: Identity of the invoking agent (e.g. 'flight', 'hotel').
            tool_name: Registered MCP tool name (e.g. 'search_flights').
            arguments: Dictionary of input parameters.
            is_demo: Execution mode flag.

        Returns:
            MCPToolResult containing output data, latency, status, or structured error.
        """
        token = set_execution_mode(is_demo)
        try:
            return cls._call_tool_impl(
                agent_name=agent_name,
                tool_name=tool_name,
                arguments=arguments,
                is_demo=is_demo,
            )
        finally:
            reset_execution_mode(token)

    @classmethod
    def _call_tool_impl(
        cls,
        agent_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        is_demo: bool = True,
    ) -> MCPToolResult:
        exec_id = f"mcp-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        retries_used = 0

        # Sanitize arguments for telemetry audit
        safe_args = SecretRedactor.redact_dict(MCPSecurityManager.sanitize_metadata(arguments))

        logger.info(f"[MCPClient] Agent '{agent_name}' invoking tool '{tool_name}' (ID: {exec_id})")

        # 1. Centralized Tool Guardrail: Authorization, High-Risk Check, Argument Validation, Rate Limiting
        auth_res = ToolGuardrail.authorize(
            agent_role=agent_name,
            tool_name=tool_name,
            arguments=arguments,
            execution_id=exec_id,
        )

        if not auth_res.authorized:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            if auth_res.category in ("HIGH_RISK_BLOCKED", "PERMISSION_DENIED"):
                status = ToolExecutionStatus.UNAUTHORIZED
                error_code = auth_res.category
            elif auth_res.category == "RATE_LIMITED":
                status = ToolExecutionStatus.FAILED
                error_code = "RATE_LIMIT_EXCEEDED"
            else:
                status = ToolExecutionStatus.FAILED
                error_code = "INVALID_ARGUMENTS"

            err_msg = SecretRedactor.redact_text(auth_res.reason or "Tool authorization denied.")
            err = ToolExecutionError(
                tool_name=tool_name,
                error_code=error_code,
                message=err_msg,
                retryable=False,
                execution_id=exec_id,
            )
            cls._record_call(
                exec_id=exec_id,
                tool_name=tool_name,
                agent_name=agent_name,
                status=status,
                duration_ms=duration_ms,
                safe_args=safe_args,
                retries=0,
                error=err_msg,
                mode="DEMO" if is_demo else "LIVE",
            )
            return MCPToolResult(
                success=False,
                tool_name=tool_name,
                error=err,
                latency_ms=duration_ms,
                mode="DEMO" if is_demo else "LIVE",
                demo_data=is_demo,
            )


        # 2. Lookup Tool Descriptor
        descriptor = MCPToolRegistry.get_tool(tool_name)
        if not descriptor:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            err_msg = f"MCP Tool '{tool_name}' is not registered."
            err = ToolExecutionError(
                tool_name=tool_name,
                error_code="TOOL_NOT_FOUND",
                message=err_msg,
                retryable=False,
                execution_id=exec_id,
            )
            cls._record_call(
                exec_id=exec_id,
                tool_name=tool_name,
                agent_name=agent_name,
                status=ToolExecutionStatus.FAILED,
                duration_ms=duration_ms,
                safe_args=safe_args,
                retries=0,
                error=err_msg,
                mode="DEMO" if is_demo else "LIVE",
            )
            return MCPToolResult(
                success=False,
                tool_name=tool_name,
                error=err,
                latency_ms=duration_ms,
                mode="DEMO" if is_demo else "LIVE",
                demo_data=is_demo,
            )

        # 3. Input Schema Validation
        try:
            validated_input = descriptor.input_schema(**arguments)
        except ValidationError as ve:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            err_msg = f"Invalid arguments for tool '{tool_name}': {str(ve)}"
            err = ToolExecutionError(
                tool_name=tool_name,
                error_code="INVALID_ARGUMENTS",
                message=err_msg,
                retryable=False,
                execution_id=exec_id,
            )
            cls._record_call(
                exec_id=exec_id,
                tool_name=tool_name,
                agent_name=agent_name,
                status=ToolExecutionStatus.FAILED,
                duration_ms=duration_ms,
                safe_args=safe_args,
                retries=0,
                error=err_msg,
                mode="DEMO" if is_demo else "LIVE",
            )
            return MCPToolResult(
                success=False,
                tool_name=tool_name,
                error=err,
                latency_ms=duration_ms,
                mode="DEMO" if is_demo else "LIVE",
                demo_data=is_demo,
            )

        # 3.5 Intelligent Cache Lookup (Duplicate call prevention & cost/latency optimization)
        cache_domain = f"{agent_name}:{'demo' if is_demo else 'live'}"
        cached_result = intelligent_cache.get(domain=cache_domain, operation=tool_name, params=arguments)
        if cached_result is not None:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            cls._record_call(
                exec_id=exec_id,
                tool_name=tool_name,
                agent_name=agent_name,
                status=ToolExecutionStatus.SUCCESS,
                duration_ms=duration_ms,
                safe_args=safe_args,
                retries=0,
                mode=cached_result.mode if isinstance(cached_result, MCPToolResult) else ("DEMO" if is_demo else "LIVE"),
                provider=getattr(cached_result, "provider", None) if isinstance(cached_result, MCPToolResult) else None,
            )
            if isinstance(cached_result, MCPToolResult):
                return cached_result
            return MCPToolResult(
                success=True,
                tool_name=tool_name,
                data=cached_result,
                latency_ms=duration_ms,
                mode="DEMO" if is_demo else "LIVE",
                demo_data=is_demo,
            )

        # 4. Tool Execution with Retry Policy
        last_exception: Optional[Exception] = None
        max_attempts = descriptor.max_retries + 1

        for attempt in range(max_attempts):
            try:
                # Execute tool handler
                output_model = descriptor.handler(validated_input)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                provider_name = getattr(output_model, "provider", None)
                data_mode = getattr(output_model, "data_mode", "DEMO" if is_demo else "LIVE")

                cls._record_call(
                    exec_id=exec_id,
                    tool_name=tool_name,
                    agent_name=agent_name,
                    status=ToolExecutionStatus.SUCCESS,
                    duration_ms=duration_ms,
                    safe_args=safe_args,
                    retries=attempt,
                    mode=data_mode,
                    provider=provider_name,
                )

                result_obj = MCPToolResult(
                    success=True,
                    tool_name=tool_name,
                    data=output_model.model_dump(),
                    latency_ms=duration_ms,
                    mode=data_mode,
                    provider=provider_name,
                    demo_data=getattr(output_model, "demo_data", is_demo),
                )
                # Store in cache if non-transactional
                intelligent_cache.set(
                    domain=cache_domain,
                    operation=tool_name,
                    params=arguments,
                    value=result_obj,
                )
                return result_obj
            except TimeoutError as te:
                last_exception = te
                retries_used = attempt
                logger.warning(f"[MCPClient] Attempt {attempt + 1} timed out for tool '{tool_name}'")
            except ProviderRateLimitError as rle:
                last_exception = rle
                retries_used = attempt
                logger.warning(f"[MCPClient] Rate limit on attempt {attempt + 1} for '{tool_name}': {str(rle)}")
            except ProviderConfigurationError as pce:
                # Non-retryable configuration failure (e.g. missing API keys in LIVE mode)
                last_exception = pce
                retries_used = attempt
                logger.error(f"[MCPClient] Configuration error for '{tool_name}': {str(pce)}")
                break
            except ProviderAuthenticationError as pae:
                # Non-retryable auth failure
                last_exception = pae
                retries_used = attempt
                logger.error(f"[MCPClient] Authentication error for '{tool_name}': {str(pae)}")
                break
            except Exception as e:
                last_exception = e
                retries_used = attempt
                logger.warning(f"[MCPClient] Attempt {attempt + 1} failed for tool '{tool_name}': {str(e)}")

        # 5. Handle Failure / Retry Exhaustion
        duration_ms = round((time.time() - start_time) * 1000, 2)
        err_msg = f"Execution failed for tool '{tool_name}': {str(last_exception)}"

        # Classify structured error codes
        if isinstance(last_exception, (TimeoutError, ProviderTimeoutError)):
            status = ToolExecutionStatus.TIMED_OUT
            error_code = "TIMEOUT"
            retryable = True
        elif isinstance(last_exception, ProviderConfigurationError):
            status = ToolExecutionStatus.FAILED
            error_code = "PROVIDER_CONFIGURATION_ERROR"
            retryable = False
        elif isinstance(last_exception, ProviderAuthenticationError):
            status = ToolExecutionStatus.UNAUTHORIZED
            error_code = "PROVIDER_AUTHENTICATION_ERROR"
            retryable = False
        elif isinstance(last_exception, ProviderRateLimitError):
            status = ToolExecutionStatus.FAILED
            error_code = "RATE_LIMIT_EXCEEDED"
            retryable = True
        elif isinstance(last_exception, ProviderResponseValidationError):
            status = ToolExecutionStatus.FAILED
            error_code = "PROVIDER_RESPONSE_VALIDATION_ERROR"
            retryable = False
        elif isinstance(last_exception, ProviderNetworkError):
            status = ToolExecutionStatus.FAILED
            error_code = "PROVIDER_NETWORK_ERROR"
            retryable = True
        else:
            status = ToolExecutionStatus.FAILED
            error_code = "EXECUTION_FAILED"
            retryable = False

        failed_provider = getattr(last_exception, "provider", None)

        err = ToolExecutionError(
            tool_name=tool_name,
            error_code=error_code,
            message=err_msg,
            retryable=retryable,
            execution_id=exec_id,
        )

        cls._record_call(
            exec_id=exec_id,
            tool_name=tool_name,
            agent_name=agent_name,
            status=status,
            duration_ms=duration_ms,
            safe_args=safe_args,
            retries=retries_used,
            error=str(last_exception),
            mode="DEMO" if is_demo else "LIVE",
            provider=failed_provider,
        )

        return MCPToolResult(
            success=False,
            tool_name=tool_name,
            error=err,
            latency_ms=duration_ms,
            mode="DEMO" if is_demo else "LIVE",
            provider=failed_provider,
            demo_data=is_demo,
        )

    @classmethod
    def _record_call(
        cls,
        exec_id: str,
        tool_name: str,
        agent_name: str,
        status: ToolExecutionStatus,
        duration_ms: float,
        safe_args: Dict[str, Any],
        retries: int,
        error: Optional[str] = None,
        mode: str = "DEMO",
        provider: Optional[str] = None,
    ) -> None:
        """Append to in-memory recent calls audit trail."""
        call_rec = MCPToolCall(
            execution_id=exec_id,
            tool_name=tool_name,
            agent_name=agent_name,
            status=status,
            duration_ms=duration_ms,
            input_metadata=safe_args,
            retries=retries,
            mode=mode,
            provider=provider,
            error=error,
        )
        cls._recent_calls.append(call_rec)
        if len(cls._recent_calls) > 200:
            cls._recent_calls.pop(0)

        try:
            from services.observability_service import observability_service
            observability_service.trace_mcp_tool(
                tool_name=tool_name,
                agent_name=agent_name,
                arguments=safe_args,
                duration_ms=duration_ms,
                success=(status == ToolExecutionStatus.SUCCESS),
                provider=provider or ("demo" if mode == "DEMO" else "live"),
                retries=retries,
                error=error,
            )
        except Exception as e:
            logger.debug(f"[MCPClient] Non-blocking observability trace skipped: {e}")

    @classmethod
    def get_recent_calls(cls) -> List[MCPToolCall]:
        """Retrieve recent tool call execution history for UI telemetry."""
        return list(cls._recent_calls)

    @classmethod
    def clear_history(cls) -> None:
        """Clear recorded tool calls."""
        cls._recent_calls.clear()
