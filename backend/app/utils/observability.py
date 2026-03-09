"""
Observability utilities for Intelli-Credit agents.
Provides @track_agent decorator with timeout, structured logging, and metrics.
"""

import asyncio
import functools
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from app.models.state import AgentMetrics, add_agent_metrics
from app.models.state import AgentMetrics, add_agent_metrics


logger = logging.getLogger(__name__)

# Default agent timeout in seconds
DEFAULT_AGENT_TIMEOUT = 45


class AgentTimeoutError(Exception):
    """Raised when an agent exceeds its allowed execution time."""
    pass


class AgentTimer:
    """Context manager for timing sub-tasks within an agent."""

    def __init__(self, label: str, analysis_id: str = ""):
        self.label = label
        self.analysis_id = analysis_id
        self.start_time: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        logger.info(f"[{self.analysis_id}] ⏱  Starting: {self.label}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self.start_time
        status = "✓" if exc_type is None else "✗"
        logger.info(
            f"[{self.analysis_id}] {status} Completed: {self.label} "
            f"({self.elapsed:.2f}s)"
        )
        return False


def track_agent(timeout: int = DEFAULT_AGENT_TIMEOUT):
    """
    Decorator for LangGraph agent functions.

    Features:
        - Logs entry/exit with analysis_id correlation
        - Measures wall-clock execution time
        - Enforces timeout (async cancellation)
        - Classifies errors as recoverable vs fatal
        - Stores AgentMetrics into state

    Usage:
        @track_agent(timeout=45)
        async def my_agent(state: Dict[str, Any]) -> Dict[str, Any]:
            ...
    """

    def decorator(func: Callable):
        agent_name = func.__name__

        @functools.wraps(func)
        async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            analysis_id = state.get("analysis_id", "unknown")
            started_at = datetime.utcnow()
            start_time = time.perf_counter()

            logger.info(
                f"{'═' * 60}\n"
                f"[{analysis_id}] AGENT START: {agent_name.upper()}\n"
                f"{'═' * 60}"
            )

            metrics = AgentMetrics(
                agent_name=agent_name,
                started_at=started_at,
                status="running",
            )

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(state),
                    timeout=timeout,
                )

                elapsed = time.perf_counter() - start_time
                metrics.finished_at = datetime.utcnow()
                metrics.duration_seconds = round(elapsed, 3)
                metrics.status = "success"

                logger.info(
                    f"[{analysis_id}] AGENT COMPLETE: {agent_name.upper()} "
                    f"({elapsed:.2f}s)"
                )

                # Inject metrics into result state
                result["agent_metrics"] = add_agent_metrics(result, metrics)
                result["updated_at"] = datetime.utcnow().isoformat()


                return result

            except asyncio.TimeoutError:
                elapsed = time.perf_counter() - start_time
                metrics.finished_at = datetime.utcnow()
                metrics.duration_seconds = round(elapsed, 3)
                metrics.status = "timeout"
                metrics.error = f"Agent exceeded {timeout}s timeout"

                logger.error(
                    f"[{analysis_id}] AGENT TIMEOUT: {agent_name.upper()} "
                    f"after {elapsed:.2f}s (limit: {timeout}s)"
                )

                errors = list(state.get("errors", []))
                errors.append(f"{agent_name} timed out after {timeout}s")
                
                result_state = {
                    **state,
                    "status": "failed",
                    "errors": errors,
                    "current_agent": agent_name,
                    "agent_metrics": add_agent_metrics(state, metrics),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                

                return result_state

            except Exception as e:
                elapsed = time.perf_counter() - start_time
                metrics.finished_at = datetime.utcnow()
                metrics.duration_seconds = round(elapsed, 3)
                metrics.status = "failed"
                metrics.error = str(e)

                error_class = _classify_error(e)

                logger.error(
                    f"[{analysis_id}] AGENT FAILED: {agent_name.upper()} "
                    f"({error_class}): {str(e)}"
                )

                errors = list(state.get("errors", []))
                errors.append(f"{agent_name} failed ({error_class}): {str(e)}")

                result_state = {
                    **state,
                    "status": "failed",
                    "errors": errors,
                    "current_agent": agent_name,
                    "agent_metrics": add_agent_metrics(state, metrics),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                

                return result_state

        return wrapper
    return decorator


def _classify_error(error: Exception) -> str:
    """Classify an error as recoverable or fatal."""
    error_type = type(error).__name__
    error_str = str(error).lower()

    # Recoverable errors
    recoverable_keywords = [
        "timeout", "rate_limit", "rate limit", "429",
        "503", "502", "connection", "temporary",
    ]
    for keyword in recoverable_keywords:
        if keyword in error_str or keyword in error_type.lower():
            return "RECOVERABLE"

    # Fatal errors
    fatal_keywords = [
        "auth", "401", "403", "invalid_api_key",
        "permission", "not_found",
    ]
    for keyword in fatal_keywords:
        if keyword in error_str or keyword in error_type.lower():
            return "FATAL"

    return "UNKNOWN"
