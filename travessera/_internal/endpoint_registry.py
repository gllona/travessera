"""
Endpoint registry for managing registered endpoints.

This module provides a registry for storing and retrieving
endpoint configurations.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from travessera.types import EndpointConfig, HTTPMethod


@dataclass
class RegisteredEndpoint:
    """Information about a registered endpoint."""

    service_name: str
    endpoint_path: str
    method: HTTPMethod
    function: Callable
    config: EndpointConfig
    parsed_signature: Optional[Any] = None  # Will be ParsedSignature when available


class EndpointRegistry:
    """
    Registry for managing endpoints.

    This registry stores endpoint configurations and provides
    methods for registering and retrieving endpoints.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        # Key format: "service_name.function_name"
        self._endpoints: Dict[str, RegisteredEndpoint] = {}

        # Additional index by function object
        self._function_index: Dict[Callable, RegisteredEndpoint] = {}

    def register(
        self,
        service_name: str,
        function_name: str,
        endpoint_path: str,
        method: HTTPMethod,
        function: Callable,
        config: EndpointConfig,
    ) -> None:
        """
        Register an endpoint.

        Args:
            service_name: Name of the service
            function_name: Name of the function
            endpoint_path: Endpoint path template
            method: HTTP method
            function: The actual function
            config: Endpoint configuration
        """
        key = f"{service_name}.{function_name}"

        endpoint = RegisteredEndpoint(
            service_name=service_name,
            endpoint_path=endpoint_path,
            method=method,
            function=function,
            config=config,
        )

        self._endpoints[key] = endpoint
        self._function_index[function] = endpoint

    def get_by_key(self, key: str) -> Optional[RegisteredEndpoint]:
        """
        Get an endpoint by its key.

        Args:
            key: The endpoint key (service.function)

        Returns:
            The registered endpoint or None
        """
        return self._endpoints.get(key)

    def get_by_function(self, function: Callable) -> Optional[RegisteredEndpoint]:
        """
        Get an endpoint by its function.

        Args:
            function: The function object

        Returns:
            The registered endpoint or None
        """
        return self._function_index.get(function)

    def list_endpoints(self) -> Dict[str, RegisteredEndpoint]:
        """
        List all registered endpoints.

        Returns:
            Dictionary of all endpoints
        """
        return self._endpoints.copy()

    def clear(self) -> None:
        """Clear all registered endpoints."""
        self._endpoints.clear()
        self._function_index.clear()
