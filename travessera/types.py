"""
Type definitions and protocols for Travessera.

This module defines type aliases, protocols, and other type-related
utilities used throughout the library.
"""

from collections.abc import Awaitable, Callable
from typing import (
    Any,
    Literal,
    Protocol,
    TypeVar,
    runtime_checkable,
)

import httpx
from pydantic import BaseModel

T = TypeVar("T")
P = TypeVar("P")

# HTTP method types
HTTPMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

# Type for headers
Headers = dict[str, str]

# Type for query parameters
QueryParams = dict[str, str | list[str] | None]

# Type for JSON-serializable data
JSONData = None | bool | int | float | str | list["JSONData"] | dict[str, "JSONData"]

# Type for request/response transformers
RequestTransformer = Callable[[Any], Any]
ResponseTransformer = Callable[[Any], Any]

# Type for headers factory
HeadersFactory = Callable[[dict[str, Any]], Headers]

# Type for endpoint functions
EndpointFunction = Callable[..., T] | Callable[..., Awaitable[T]]


@runtime_checkable
class Serializer(Protocol):
    """Protocol for serializers that convert between Python objects and bytes."""

    content_type: str

    def serialize(self, data: Any) -> bytes:
        """
        Serialize Python data to bytes.

        Args:
            data: The data to serialize

        Returns:
            The serialized bytes

        Raises:
            ValidationError: If the data cannot be serialized
        """
        ...

    def deserialize(self, data: bytes, target_type: type[T]) -> T:
        """
        Deserialize bytes to a Python object.

        Args:
            data: The bytes to deserialize
            target_type: The expected type of the result

        Returns:
            The deserialized object

        Raises:
            ValidationError: If the data cannot be deserialized
        """
        ...


@runtime_checkable
class Authentication(Protocol):
    """Protocol for authentication strategies."""

    def apply(self, request: httpx.Request) -> httpx.Request:
        """
        Apply authentication to an HTTP request.

        Args:
            request: The request to authenticate

        Returns:
            The authenticated request
        """
        ...


@runtime_checkable
class Cache(Protocol):
    """Protocol for cache implementations."""

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found
        """
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds (optional)
        """
        ...

    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.

        Args:
            key: The cache key
        """
        ...


@runtime_checkable
class Monitor(Protocol):
    """Protocol for monitoring implementations."""

    def record_request(
        self,
        service: str,
        endpoint: str,
        method: str,
        duration: float,
        status_code: int | None = None,
        error: Exception | None = None,
    ) -> None:
        """
        Record metrics for a request.

        Args:
            service: The service name
            endpoint: The endpoint path
            method: The HTTP method
            duration: The request duration in seconds
            status_code: The HTTP status code (if available)
            error: Any error that occurred
        """
        ...


@runtime_checkable
class Tracer(Protocol):
    """Protocol for distributed tracing implementations."""

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        """
        Start a new tracing span.

        Args:
            name: The span name
            attributes: Optional span attributes

        Returns:
            A span context manager
        """
        ...


class EndpointConfig(BaseModel):
    """Configuration for an endpoint."""

    service: str
    endpoint: str
    method: HTTPMethod
    timeout: float | None = None
    headers: Headers | None = None
    headers_factory: HeadersFactory | None = None
    retry_config: Any | None = None  # Will be RetryConfig when defined
    request_transformer: RequestTransformer | None = None
    response_transformer: ResponseTransformer | None = None
    raises: dict[int, type[Exception]] | None = None
    serializer: Serializer | None = None

    model_config = {"arbitrary_types_allowed": True}


class ServiceConfig(BaseModel):
    """Configuration for a service."""

    name: str
    base_url: str
    timeout: float | None = None
    authentication: Authentication | None = None
    headers: Headers | None = None
    retry_config: Any | None = None  # Will be RetryConfig when defined
    cache: Cache | None = None

    model_config = {"arbitrary_types_allowed": True}


class TravesseraConfig(BaseModel):
    """Global configuration for Travessera."""

    default_timeout: float = 30.0
    default_headers: Headers | None = None
    retry_config: Any | None = None  # Will be RetryConfig when defined
    monitor: Monitor | None = None
    tracer: Tracer | None = None

    model_config = {"arbitrary_types_allowed": True}
