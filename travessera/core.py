"""
Core classes for Travessera.

This module contains the main Service and Travessera classes that form
the foundation of the library.
"""

from collections.abc import Callable
from typing import Any

from travessera.authentication import Authentication
from travessera.client import RetryableHTTPClient
from travessera.exceptions import ServiceNotFoundError
from travessera.models import RetryConfig
from travessera.serializers import JSONSerializer, Serializer
from travessera.types import (
    Cache,
    EndpointFunction,
    Headers,
    HeadersFactory,
    HTTPMethod,
    Monitor,
    Tracer,
)


class Service:
    """
    Configuration for a microservice.

    This class holds all the configuration needed to connect to
    and communicate with a specific microservice.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: float | None = None,
        authentication: Authentication | None = None,
        headers: Headers | None = None,
        retry_config: RetryConfig | None = None,
        cache: Cache | None = None,
    ) -> None:
        """
        Initialize a Service.

        Args:
            name: The service name (used in decorators)
            base_url: The base URL for the service
            timeout: Default timeout for requests to this service
            authentication: Authentication strategy for this service
            headers: Default headers for requests to this service
            retry_config: Retry configuration for this service
            cache: Cache implementation for this service
        """
        self.name = name
        self.base_url = base_url.rstrip("/")  # Remove trailing slash
        self.timeout = timeout
        self.authentication = authentication
        self.headers = headers or {}
        self.retry_config = retry_config
        self.cache = cache

        # Create HTTP client for this service
        self._client: RetryableHTTPClient | None = None

    @property
    def client(self) -> RetryableHTTPClient:
        """Get or create the HTTP client for this service."""
        if self._client is None:
            self._client = RetryableHTTPClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout or 30.0,
                retry_config=self.retry_config,
            )
        return self._client

    def get_config(self) -> dict[str, Any]:
        """Get the service configuration as a dictionary."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "authentication": self.authentication,
            "headers": self.headers,
            "retry_config": self.retry_config,
            "cache": self.cache,
        }

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None

    async def aclose(self) -> None:
        """Async version of close."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def __enter__(self) -> "Service":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    async def __aenter__(self) -> "Service":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.aclose()


class Travessera:
    """
    Main orchestrator for microservice communication.

    This class manages services and provides decorators for defining
    endpoints that communicate with those services.
    """

    def __init__(
        self,
        services: list[Service],
        default_timeout: float = 30.0,
        default_headers: Headers | None = None,
        retry_config: RetryConfig | None = None,
        monitor: Monitor | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        """
        Initialize Travessera.

        Args:
            services: List of services to manage
            default_timeout: Default timeout for all requests
            default_headers: Default headers for all requests
            retry_config: Default retry configuration
            monitor: Monitoring implementation
            tracer: Distributed tracing implementation
        """
        self.services = {service.name: service for service in services}
        self.default_timeout = default_timeout
        self.default_headers = default_headers or {}
        self.retry_config = retry_config
        self.monitor = monitor
        self.tracer = tracer

        # Default serializer
        self.default_serializer = JSONSerializer()

        # Endpoint registry
        self._endpoints: dict[str, dict[str, Any]] = {}

    def get_service(self, name: str) -> Service:
        """
        Get a service by name.

        Args:
            name: The service name

        Returns:
            The service instance

        Raises:
            ServiceNotFoundError: If the service is not found
        """
        if name not in self.services:
            raise ServiceNotFoundError(name)
        return self.services[name]

    def get_config(self) -> dict[str, Any]:
        """Get the Travessera configuration as a dictionary."""
        return {
            "default_timeout": self.default_timeout,
            "default_headers": self.default_headers,
            "retry_config": self.retry_config,
            "monitor": self.monitor,
            "tracer": self.tracer,
        }

    def endpoint(
        self,
        service: str,
        endpoint: str,
        method: HTTPMethod = "GET",
        *,
        timeout: float | None = None,
        headers: Headers | None = None,
        headers_factory: HeadersFactory | None = None,
        retry_config: RetryConfig | None = None,
        request_transformer: Callable[[Any], Any] | None = None,
        response_transformer: Callable[[Any], Any] | None = None,
        raises: dict[int, type[Exception]] | None = None,
        serializer: Serializer | None = None,
    ) -> Callable[[EndpointFunction], EndpointFunction]:
        """
        Decorator for defining an endpoint.

        Args:
            service: The service name
            endpoint: The endpoint path (can include {placeholders})
            method: The HTTP method
            timeout: Override timeout for this endpoint
            headers: Additional headers for this endpoint
            headers_factory: Function to generate dynamic headers
            retry_config: Override retry config for this endpoint
            request_transformer: Transform request data before sending
            response_transformer: Transform response data after receiving
            raises: Map status codes to custom exceptions
            serializer: Override serializer for this endpoint

        Returns:
            The decorator function
        """
        from travessera.decorators import create_endpoint_decorator

        return create_endpoint_decorator(
            self,
            service,
            endpoint,
            method,
            timeout=timeout,
            headers=headers,
            headers_factory=headers_factory,
            retry_config=retry_config,
            request_transformer=request_transformer,
            response_transformer=response_transformer,
            raises=raises,
            serializer=serializer,
        )

    def get(
        self,
        service: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Callable[[EndpointFunction], EndpointFunction]:
        """Shortcut for GET endpoints."""
        return self.endpoint(service, endpoint, "GET", **kwargs)

    def post(
        self,
        service: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Callable[[EndpointFunction], EndpointFunction]:
        """Shortcut for POST endpoints."""
        return self.endpoint(service, endpoint, "POST", **kwargs)

    def put(
        self,
        service: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Callable[[EndpointFunction], EndpointFunction]:
        """Shortcut for PUT endpoints."""
        return self.endpoint(service, endpoint, "PUT", **kwargs)

    def delete(
        self,
        service: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Callable[[EndpointFunction], EndpointFunction]:
        """Shortcut for DELETE endpoints."""
        return self.endpoint(service, endpoint, "DELETE", **kwargs)

    def patch(
        self,
        service: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Callable[[EndpointFunction], EndpointFunction]:
        """Shortcut for PATCH endpoints."""
        return self.endpoint(service, endpoint, "PATCH", **kwargs)

    def close(self) -> None:
        """Close all services and release resources."""
        for service in self.services.values():
            service.close()

    async def aclose(self) -> None:
        """Async version of close."""
        for service in self.services.values():
            await service.aclose()

    def __enter__(self) -> "Travessera":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    async def __aenter__(self) -> "Travessera":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.aclose()
