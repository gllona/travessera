"""
Retry logic implementation for Travessera.

This module provides retry functionality using the tenacity library,
with configuration specific to HTTP requests.
"""

import logging
from collections.abc import Callable
from typing import Any

from tenacity import (
    RetryCallState,
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from travessera.models import RetryConfig

logger = logging.getLogger(__name__)


def create_retry_logic(config: RetryConfig) -> Retrying:
    """
    Create a tenacity Retrying instance from a RetryConfig.

    Args:
        config: The retry configuration

    Returns:
        A configured Retrying instance
    """
    # Build retry condition
    retry_condition = retry_if_exception_type(config.retry_on)

    # Build wait strategy
    wait_strategy = wait_exponential(
        multiplier=config.multiplier,
        min=config.min_wait,
        max=config.max_wait,
    )

    # Build before_sleep callback
    callbacks = []
    if config.before_retry:
        callbacks.append(config.before_retry)

    # Add logging
    callbacks.append(before_sleep_log(logger, logging.WARNING))

    def combined_before_sleep(retry_state: RetryCallState) -> None:
        """Execute all before_sleep callbacks."""
        for callback in callbacks:
            if callback == before_sleep_log(logger, logging.WARNING):
                callback(retry_state)
            else:
                callback(retry_state)

    return Retrying(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_strategy,
        retry=retry_condition,
        before_sleep=combined_before_sleep if callbacks else None,
        reraise=True,
    )


def with_retry(
    func: Callable[..., Any],
    config: RetryConfig | None = None,
) -> Callable[..., Any]:
    """
    Wrap a function with retry logic.

    Args:
        func: The function to wrap
        config: The retry configuration (uses defaults if None)

    Returns:
        The wrapped function
    """
    if config is None:
        config = RetryConfig()

    retry_logic = create_retry_logic(config)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Execute the function with retry logic."""
        return retry_logic(func, *args, **kwargs)

    return wrapper


async def with_retry_async(
    func: Callable[..., Any],
    config: RetryConfig | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Execute an async function with retry logic.

    Args:
        func: The async function to execute
        config: The retry configuration (uses defaults if None)
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The function result
    """
    if config is None:
        config = RetryConfig()

    from tenacity import AsyncRetrying

    # Create async retry logic
    retry_logic = AsyncRetrying(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(
            multiplier=config.multiplier,
            min=config.min_wait,
            max=config.max_wait,
        ),
        retry=retry_if_exception_type(config.retry_on),
        reraise=True,
    )

    # Execute with retry
    return await retry_logic(func, *args, **kwargs)


def should_retry_status_code(status_code: int) -> bool:
    """
    Determine if a status code indicates a retryable error.

    Args:
        status_code: The HTTP status code

    Returns:
        True if the request should be retried
    """
    # Retry on server errors and specific client errors
    retryable_codes = {
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }
    return status_code in retryable_codes
