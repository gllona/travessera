"""
Configuration models for Travessera.

This module defines Pydantic models used for configuration throughout
the library.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from travessera.exceptions import NetworkError, ServerError


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Args:
        max_attempts: Maximum number of attempts (including the initial request)
        min_wait: Minimum wait time between retries in seconds
        max_wait: Maximum wait time between retries in seconds
        multiplier: Multiplier for exponential backoff
        retry_on: Tuple of exception types to retry on
        before_retry: Optional callback to execute before each retry
    """

    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 10.0
    multiplier: float = 2.0
    retry_on: tuple[type[Exception], ...] = field(
        default_factory=lambda: (NetworkError, ServerError)
    )
    before_retry: Callable[[Any], None] | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.min_wait < 0:
            raise ValueError("min_wait must be non-negative")
        if self.max_wait < self.min_wait:
            raise ValueError("max_wait must be greater than or equal to min_wait")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1")


@dataclass
class CacheConfig:
    """
    Configuration for caching behavior.

    Args:
        ttl: Default time-to-live for cache entries in seconds
        key_prefix: Prefix to add to all cache keys
        include_headers: Whether to include headers in cache key
        include_body: Whether to include request body in cache key
    """

    ttl: int = 300  # 5 minutes default
    key_prefix: str = "travessera"
    include_headers: bool = False
    include_body: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.ttl < 0:
            raise ValueError("ttl must be non-negative")


@dataclass
class MonitorConfig:
    """
    Configuration for monitoring behavior.

    Args:
        enabled: Whether monitoring is enabled
        include_request_body: Whether to include request body in monitoring
        include_response_body: Whether to include response body in monitoring
        sample_rate: Sampling rate for monitoring (0.0-1.0)
    """

    enabled: bool = True
    include_request_body: bool = False
    include_response_body: bool = False
    sample_rate: float = 1.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")


@dataclass
class TracerConfig:
    """
    Configuration for distributed tracing.

    Args:
        enabled: Whether tracing is enabled
        service_name: Name of the service for tracing
        propagate_headers: Whether to propagate trace headers
        sample_rate: Sampling rate for tracing (0.0-1.0)
    """

    enabled: bool = True
    service_name: str = "travessera"
    propagate_headers: bool = True
    sample_rate: float = 1.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")


@dataclass
class ConnectionConfig:
    """
    Configuration for HTTP connection behavior.

    Args:
        pool_connections: Number of connection pools to cache
        pool_maxsize: Maximum number of connections to save in the pool
        max_keepalive_connections: Maximum number of keepalive connections
        keepalive_expiry: Time in seconds to keep connections alive
    """

    pool_connections: int = 10
    pool_maxsize: int = 10
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.pool_connections < 1:
            raise ValueError("pool_connections must be at least 1")
        if self.pool_maxsize < 1:
            raise ValueError("pool_maxsize must be at least 1")
        if self.max_keepalive_connections < 0:
            raise ValueError("max_keepalive_connections must be non-negative")
        if self.keepalive_expiry < 0:
            raise ValueError("keepalive_expiry must be non-negative")
