"""
Retry utilities for Intelli-Credit.
Exponential backoff with jitter and circuit breaker for external API calls.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Tuple, Type

logger = logging.getLogger(__name__)


# ─── Circuit Breaker ──────────────────────────────────────────────────────────

class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is in OPEN state."""
    pass


class CircuitBreaker:
    """
    Simple circuit breaker.
    After `failure_threshold` consecutive failures, the circuit opens
    and fast-fails for `recovery_timeout` seconds.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} consecutive failures. "
                f"Will retry after {self.recovery_timeout}s."
            )

    def can_proceed(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker HALF_OPEN — allowing one test request")
                return True
            return False
        # HALF_OPEN — allow one test
        return True


# Global circuit breakers per service
_circuit_breakers = {}


def _get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker()
    return _circuit_breakers[name]


# ─── Retry Decorator ─────────────────────────────────────────────────────────

def with_retry(
    max_retries: int = 3,
    backoff_base: float = 2.0,
    max_backoff: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    circuit_breaker_name: str = "",
):
    """
    Async retry decorator with exponential backoff + jitter.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_base: Base for exponential backoff (seconds)
        max_backoff: Maximum wait time between retries
        retryable_exceptions: Tuple of exception types that trigger retry
        circuit_breaker_name: If set, uses a named circuit breaker
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cb = _get_circuit_breaker(circuit_breaker_name) if circuit_breaker_name else None

            last_exception = None

            for attempt in range(max_retries + 1):
                # Check circuit breaker
                if cb and not cb.can_proceed():
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{circuit_breaker_name}' is OPEN. "
                        f"Request rejected."
                    )

                try:
                    result = await func(*args, **kwargs)
                    if cb:
                        cb.record_success()
                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Exponential backoff with jitter
                        wait = min(
                            backoff_base ** attempt + random.uniform(0, 1),
                            max_backoff,
                        )
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: "
                            f"{type(e).__name__}: {str(e)[:100]}. "
                            f"Waiting {wait:.1f}s..."
                        )
                        await asyncio.sleep(wait)
                    else:
                        if cb:
                            cb.record_failure()
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}: "
                            f"{type(e).__name__}: {str(e)[:200]}"
                        )

                except Exception as e:
                    # Non-retryable exception — fail immediately
                    if cb:
                        cb.record_failure()
                    logger.error(
                        f"Non-retryable error in {func.__name__}: "
                        f"{type(e).__name__}: {str(e)[:200]}"
                    )
                    raise

            raise last_exception

        return wrapper
    return decorator
