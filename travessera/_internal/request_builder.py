"""
Request builder for constructing HTTP requests.

This module builds HTTP requests from function calls, handling
path parameters, query parameters, headers, and request bodies.
"""

from typing import Any

from travessera._internal.config_resolver import ResolvedConfig
from travessera._internal.headers_manager import HeadersManager
from travessera._internal.parameter_parser import ParameterParser, ParsedSignature
from travessera.authentication import Authentication
from travessera.types import Headers


class RequestBuilder:
    """
    Builds HTTP requests from function calls.

    This class handles:
    - URL construction with path parameters
    - Query parameter encoding
    - Request body serialization
    - Header management
    - Authentication
    """

    def __init__(
        self,
        config: ResolvedConfig,
        parsed_signature: ParsedSignature,
        authentication: Authentication | None = None,
    ) -> None:
        """
        Initialize the request builder.

        Args:
            config: Resolved endpoint configuration
            parsed_signature: Parsed function signature
            authentication: Optional authentication strategy
        """
        self.config = config
        self.parsed_signature = parsed_signature
        self.authentication = authentication
        self.headers_manager = HeadersManager(
            static_headers=config.headers,
            headers_factory=config.headers_factory,
        )

    def build_url(
        self,
        endpoint_template: str,
        kwargs: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """
        Build the complete URL with path parameters.

        Args:
            endpoint_template: Endpoint template like "/users/{id}"
            kwargs: Function arguments

        Returns:
            Tuple of (url, query_params)
        """
        # Extract and format path parameters
        path, remaining_kwargs = ParameterParser.extract_path_values(
            endpoint_template,
            self.parsed_signature,
            kwargs,
        )

        # Extract query parameters
        query_params = ParameterParser.extract_query_params(
            self.parsed_signature,
            remaining_kwargs,
        )

        # Build full URL
        url = self.config.base_url + path

        return url, query_params

    def build_headers(
        self,
        kwargs: dict[str, Any],
        content_type: str | None = None,
    ) -> Headers:
        """
        Build request headers.

        Args:
            kwargs: Function arguments (for dynamic headers)
            content_type: Optional content type to set

        Returns:
            Complete headers dictionary
        """
        # Get base headers (static + dynamic)
        headers = self.headers_manager.get_headers(kwargs)

        # Add content type if provided
        if content_type:
            headers["Content-Type"] = content_type

        # Add Accept header for JSON by default
        if "Accept" not in headers:
            headers["Accept"] = "application/json"

        return headers

    def build_body(
        self,
        kwargs: dict[str, Any],
    ) -> bytes | None:
        """
        Build request body.

        Args:
            kwargs: Function arguments

        Returns:
            Serialized body data or None
        """
        # Extract body data
        body_data = ParameterParser.extract_body_data(
            self.parsed_signature,
            kwargs,
        )

        if body_data is None:
            return None

        # Apply request transformer if configured
        if self.config.request_transformer:
            body_data = self.config.request_transformer(body_data)

        # Serialize the data
        return self.config.serializer.serialize(body_data)

    def build_request_kwargs(
        self,
        method: str,
        endpoint_template: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build complete kwargs for httpx request.

        Args:
            method: HTTP method
            endpoint_template: Endpoint template
            kwargs: Function arguments

        Returns:
            Dictionary of arguments for httpx request
        """
        # Build URL and extract query params
        url, query_params = self.build_url(endpoint_template, kwargs)

        # Start with base request kwargs
        request_kwargs = {
            "method": method,
            "url": url,
            "timeout": self.config.timeout,
        }

        # Add query parameters
        if query_params:
            request_kwargs["params"] = query_params

        # Add body if needed
        if method in ("POST", "PUT", "PATCH"):
            body = self.build_body(kwargs)
            if body is not None:
                request_kwargs["content"] = body
                headers = self.build_headers(
                    kwargs,
                    content_type=self.config.serializer.content_type,
                )
            else:
                headers = self.build_headers(kwargs)
        else:
            headers = self.build_headers(kwargs)

        request_kwargs["headers"] = headers

        return request_kwargs

    def apply_authentication(
        self,
        request_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply authentication to request.

        Args:
            request_kwargs: Request kwargs

        Returns:
            Updated request kwargs
        """
        if self.authentication:
            # Create a mock request object for authentication
            import httpx

            mock_request = httpx.Request(
                method=request_kwargs["method"],
                url=request_kwargs["url"],
                headers=request_kwargs.get("headers", {}),
                params=request_kwargs.get("params"),
                content=request_kwargs.get("content"),
            )

            # Apply authentication (modifies headers in-place)
            self.authentication.apply(mock_request)

            # Update headers from the modified request
            request_kwargs["headers"] = dict(mock_request.headers)

        return request_kwargs
