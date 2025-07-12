"""
Response handler for processing HTTP responses.

This module handles response processing including deserialization,
transformation, and error handling.
"""

from typing import Any

import httpx

from travessera._internal.config_resolver import ResolvedConfig
from travessera._internal.parameter_parser import ParsedSignature
from travessera.exceptions import (
    HTTPError,
    ResponseValidationError,
    raise_for_status,
)


class ResponseHandler:
    """
    Handles HTTP responses.

    This class:
    - Checks response status codes
    - Deserializes response bodies
    - Applies response transformers
    - Maps errors to custom exceptions
    """

    def __init__(
        self,
        config: ResolvedConfig,
        parsed_signature: ParsedSignature,
    ) -> None:
        """
        Initialize the response handler.

        Args:
            config: Resolved endpoint configuration
            parsed_signature: Parsed function signature
        """
        self.config = config
        self.parsed_signature = parsed_signature

    def handle_response(
        self,
        response: httpx.Response,
    ) -> Any:
        """
        Handle an HTTP response.

        Args:
            response: The HTTP response

        Returns:
            The processed response data

        Raises:
            HTTPError: For HTTP errors
            ResponseValidationError: For validation errors
        """
        # Check for custom error mapping first
        if self.config.raises and response.status_code in self.config.raises:
            exception_class = self.config.raises[response.status_code]
            raise exception_class(
                f"HTTP {response.status_code} error",
                request=response.request,
                response=response,
            )

        # Check for standard HTTP errors
        try:
            raise_for_status(response)
        except HTTPError:
            # If we have custom error mapping but didn't match above,
            # re-raise the standard error
            raise

        # Handle successful response
        return self._process_response_body(response)

    def _process_response_body(
        self,
        response: httpx.Response,
    ) -> Any:
        """
        Process the response body.

        Args:
            response: The HTTP response

        Returns:
            The processed response data
        """
        # Handle empty responses
        if not response.content:
            return None

        # Check content type
        content_type = response.headers.get("content-type", "").lower()

        # For now, we only handle JSON responses
        if "application/json" not in content_type:
            # If the return type is None or the response is not JSON,
            # return the raw text
            if self.parsed_signature.return_type is None:
                return response.text
            else:
                raise ResponseValidationError(
                    f"Expected JSON response, got {content_type}",
                    {"content_type": content_type},
                )

        # Deserialize the response
        try:
            deserialized = self.config.serializer.deserialize(
                response.content,
                self.parsed_signature.return_type or dict,
            )
        except ResponseValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise ResponseValidationError(
                f"Failed to deserialize response: {e}", {"error": str(e)}
            ) from e

        # Apply response transformer if configured
        if self.config.response_transformer:
            try:
                deserialized = self.config.response_transformer(deserialized)
            except Exception as e:
                raise ResponseValidationError(
                    f"Response transformer failed: {e}", {"error": str(e)}
                ) from e

        return deserialized

    def handle_error(
        self,
        error: Exception,
    ) -> None:
        """
        Handle errors during request/response processing.

        This method can be used to add logging, monitoring,
        or other error handling logic.

        Args:
            error: The error that occurred
        """
        # For now, just re-raise
        # In the future, this could integrate with monitoring/logging
        raise error
