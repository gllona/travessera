"""
Type definitions and protocols for Travessera.

This module defines type aliases, protocols, and other type-related
utilities used throughout the library.
"""

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

import httpx
from pydantic import BaseModel

T = TypeVar("T")
P = TypeVar("P")

# HTTP method types
HTTPMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

# Type for headers
Headers = Dict[str, str]

# Type for query parameters
QueryParams = Dict[str, Union[str, List[str], None]]

# Type for JSON-serializable data
JSONData = Union[None, bool, int, float, str, List["JSONData"], Dict[str, "JSONData"]]

# Type for request/response transformers
RequestTransformer = Callable[[Any], Any]
ResponseTransformer = Callable[[Any], Any]

# Type for headers factory
HeadersFactory = Callable[[Dict[str, Any]], Headers]

# Type for endpoint functions
EndpointFunction = Union[
    Callable[..., T],
    Callable[..., Awaitable[T]],
]


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

    def deserialize(self, data: bytes, target_type: Type[T]) -> T:
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

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found
        """
        ...

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
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
        status_code: Optional[int] = None,
        error: Optional[Exception] = None,
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

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
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
    timeout: Optional[float] = None
    headers: Optional[Headers] = None
    headers_factory: Optional[HeadersFactory] = None
    retry_config: Optional[Any] = None  # Will be RetryConfig when defined
    request_transformer: Optional[RequestTransformer] = None
    response_transformer: Optional[ResponseTransformer] = None
    raises: Optional[Dict[int, Type[Exception]]] = None
    serializer: Optional[Serializer] = None

    model_config = {"arbitrary_types_allowed": True}


class ServiceConfig(BaseModel):
    """Configuration for a service."""

    name: str
    base_url: str
    timeout: Optional[float] = None
    authentication: Optional[Authentication] = None
    headers: Optional[Headers] = None
    retry_config: Optional[Any] = None  # Will be RetryConfig when defined
    cache: Optional[Cache] = None

    model_config = {"arbitrary_types_allowed": True}


class TravesseraConfig(BaseModel):
    """Global configuration for Travessera."""

    default_timeout: float = 30.0
    default_headers: Optional[Headers] = None
    retry_config: Optional[Any] = None  # Will be RetryConfig when defined
    monitor: Optional[Monitor] = None
    tracer: Optional[Tracer] = None

    model_config = {"arbitrary_types_allowed": True}
