"""
Decorator implementations for Travessera.

This module contains the actual decorator logic that transforms
regular functions into HTTP API calls.
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Dict, TypeVar

from travessera._internal.config_resolver import ConfigResolver
from travessera._internal.parameter_parser import ParameterParser
from travessera._internal.request_builder import RequestBuilder
from travessera._internal.response_handler import ResponseHandler
from travessera.core import Service
from travessera.serializers import Serializer
from travessera.types import EndpointConfig, EndpointFunction, HTTPMethod

T = TypeVar("T")


class EndpointDecorator:
    """
    The main decorator implementation that transforms functions into API calls.

    This class handles both sync and async functions, managing the entire
    request/response lifecycle.
    """

    def __init__(
        self,
        service: Service,
        endpoint_path: str,
        method: HTTPMethod,
        config: EndpointConfig,
        travessera_config: Dict[str, Any],
        default_serializer: Serializer,
    ) -> None:
        """
        Initialize the endpoint decorator.

        Args:
            service: The service this endpoint belongs to
            endpoint_path: The endpoint path template
            method: The HTTP method
            config: Endpoint-specific configuration
            travessera_config: Global Travessera configuration
            default_serializer: Default serializer to use
        """
        self.service = service
        self.endpoint_path = endpoint_path
        self.method = method
        self.endpoint_config = config
        self.travessera_config = travessera_config
        self.default_serializer = default_serializer

    def __call__(self, func: EndpointFunction) -> EndpointFunction:
        """
        Decorate the function.

        Args:
            func: The function to decorate

        Returns:
            The decorated function
        """
        # Parse the function signature
        parsed_signature = ParameterParser.parse_function(
            func,
            self.endpoint_path,
            self.method,
        )

        # Resolve configuration
        resolved_config = ConfigResolver.resolve(
            self.travessera_config,
            self.service.get_config(),
            self.endpoint_config.model_dump(exclude_none=True),
            self.default_serializer,
        )

        # Create request builder and response handler
        request_builder = RequestBuilder(
            resolved_config,
            parsed_signature,
            self.service.authentication,
        )
        response_handler = ResponseHandler(
            resolved_config,
            parsed_signature,
        )

        # Check if the function is async
        if asyncio.iscoroutinefunction(func):
            return self._create_async_wrapper(
                func,
                request_builder,
                response_handler,
            )
        else:
            return self._create_sync_wrapper(
                func,
                request_builder,
                response_handler,
            )

    def _create_async_wrapper(
        self,
        func: Callable,
        request_builder: RequestBuilder,
        response_handler: ResponseHandler,
    ) -> Callable:
        """Create an async wrapper for the function."""

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Convert args to kwargs based on function signature
            call_kwargs = self._args_to_kwargs(func, args, kwargs)

            # Build the request
            request_kwargs = request_builder.build_request_kwargs(
                self.method,
                self.endpoint_path,
                call_kwargs,
            )

            # Apply authentication
            request_kwargs = request_builder.apply_authentication(request_kwargs)

            # Make the request
            response = await self.service.client.arequest(**request_kwargs)

            # Handle the response
            return response_handler.handle_response(response)

        return async_wrapper

    def _create_sync_wrapper(
        self,
        func: Callable,
        request_builder: RequestBuilder,
        response_handler: ResponseHandler,
    ) -> Callable:
        """Create a sync wrapper for the function."""

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Convert args to kwargs based on function signature
            call_kwargs = self._args_to_kwargs(func, args, kwargs)

            # Build the request
            request_kwargs = request_builder.build_request_kwargs(
                self.method,
                self.endpoint_path,
                call_kwargs,
            )

            # Apply authentication
            request_kwargs = request_builder.apply_authentication(request_kwargs)

            # Make the request
            response = self.service.client.request(**request_kwargs)

            # Handle the response
            return response_handler.handle_response(response)

        return sync_wrapper

    def _args_to_kwargs(
        self,
        func: Callable,
        args: tuple,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert positional arguments to keyword arguments.

        Args:
            func: The original function
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            All arguments as keyword arguments
        """
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Remove 'self' or 'cls' if present
        result = dict(bound_args.arguments)
        result.pop("self", None)
        result.pop("cls", None)

        return result


def create_endpoint_decorator(
    travessera: Any,  # Avoid circular import
    service_name: str,
    endpoint_path: str,
    method: HTTPMethod,
    **kwargs: Any,
) -> Callable[[EndpointFunction], EndpointFunction]:
    """
    Create an endpoint decorator.

    This is the main entry point for creating decorators from the
    Travessera class.

    Args:
        travessera: The Travessera instance
        service_name: The service name
        endpoint_path: The endpoint path
        method: The HTTP method
        **kwargs: Additional endpoint configuration

    Returns:
        The decorator function
    """
    # Get the service
    service = travessera.get_service(service_name)

    # Create endpoint config
    endpoint_config = EndpointConfig(
        service=service_name,
        endpoint=endpoint_path,
        method=method,
        **kwargs,
    )

    # Create and return the decorator
    decorator = EndpointDecorator(
        service=service,
        endpoint_path=endpoint_path,
        method=method,
        config=endpoint_config,
        travessera_config=travessera.get_config(),
        default_serializer=travessera.default_serializer,
    )

    # Create the actual decorator function
    def decorator_func(func: EndpointFunction) -> EndpointFunction:
        # Register the endpoint
        endpoint_key = f"{service_name}.{func.__name__}"
        travessera._endpoints[endpoint_key] = {
            "service": service_name,
            "endpoint": endpoint_path,
            "method": method,
            "function": func,
            **kwargs,
        }

        # Apply the decorator
        return decorator(func)

    return decorator_func
