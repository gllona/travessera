"""
Exception hierarchy for Travessera.

This module defines all exceptions that can be raised by the library,
organized in a clear hierarchy for easy handling.
"""

from typing import Any, Dict, Optional

import httpx


class TravesseraError(Exception):
    """Base exception for all Travessera errors."""

    pass


class ServiceError(TravesseraError):
    """Base exception for service-related errors."""

    pass


class ServiceNotFoundError(ServiceError):
    """Raised when a service is not registered with Travessera."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' not found")


class EndpointNotFoundError(ServiceError):
    """Raised when an endpoint configuration is invalid."""

    def __init__(self, endpoint: str, reason: str) -> None:
        self.endpoint = endpoint
        self.reason = reason
        super().__init__(f"Invalid endpoint '{endpoint}': {reason}")


class AuthenticationError(ServiceError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class NetworkError(TravesseraError):
    """Base exception for network-related errors."""

    pass


class ConnectionError(NetworkError):
    """Raised when unable to connect to the service."""

    def __init__(self, url: str, cause: Optional[Exception] = None) -> None:
        self.url = url
        self.cause = cause
        message = f"Failed to connect to {url}"
        if cause:
            message += f": {cause}"
        super().__init__(message)


class TimeoutError(NetworkError):
    """Raised when a request times out."""

    def __init__(self, url: str, timeout: float) -> None:
        self.url = url
        self.timeout = timeout
        super().__init__(f"Request to {url} timed out after {timeout}s")


class DNSError(NetworkError):
    """Raised when DNS resolution fails."""

    def __init__(self, hostname: str) -> None:
        self.hostname = hostname
        super().__init__(f"Failed to resolve hostname: {hostname}")


class HTTPError(TravesseraError):
    """Base exception for HTTP-related errors."""

    def __init__(
        self,
        message: str,
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message)
        self.request = request
        self.response = response
        self.status_code = response.status_code if response else None

    @property
    def request_info(self) -> Dict[str, Any]:
        """Get request information for debugging."""
        if not self.request:
            return {}
        return {
            "method": self.request.method,
            "url": str(self.request.url),
            "headers": dict(self.request.headers),
        }

    @property
    def response_info(self) -> Dict[str, Any]:
        """Get response information for debugging."""
        if not self.response:
            return {}
        return {
            "status_code": self.response.status_code,
            "headers": dict(self.response.headers),
            "content": (
                self.response.text
                if len(self.response.text) < 1000
                else self.response.text[:1000] + "..."
            ),
        }


class ClientError(HTTPError):
    """Base exception for 4xx HTTP errors."""

    pass


class BadRequestError(ClientError):
    """Raised for 400 Bad Request responses."""

    def __init__(
        self,
        message: str = "Bad request",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class UnauthorizedError(ClientError):
    """Raised for 401 Unauthorized responses."""

    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class ForbiddenError(ClientError):
    """Raised for 403 Forbidden responses."""

    def __init__(
        self,
        message: str = "Forbidden",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class NotFoundError(ClientError):
    """Raised for 404 Not Found responses."""

    def __init__(
        self,
        message: str = "Not found",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class ConflictError(ClientError):
    """Raised for 409 Conflict responses."""

    def __init__(
        self,
        message: str = "Conflict",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class ServerError(HTTPError):
    """Base exception for 5xx HTTP errors."""

    pass


class InternalServerError(ServerError):
    """Raised for 500 Internal Server Error responses."""

    def __init__(
        self,
        message: str = "Internal server error",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class BadGatewayError(ServerError):
    """Raised for 502 Bad Gateway responses."""

    def __init__(
        self,
        message: str = "Bad gateway",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class ServiceUnavailableError(ServerError):
    """Raised for 503 Service Unavailable responses."""

    def __init__(
        self,
        message: str = "Service unavailable",
        *,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message, request=request, response=response)


class ValidationError(TravesseraError):
    """Base exception for validation errors."""

    pass


class RequestValidationError(ValidationError):
    """Raised when request data fails validation."""

    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.errors = errors or {}


class ResponseValidationError(ValidationError):
    """Raised when response data fails validation."""

    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.errors = errors or {}


HTTP_STATUS_TO_EXCEPTION: Dict[int, type[HTTPError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    500: InternalServerError,
    502: BadGatewayError,
    503: ServiceUnavailableError,
}


def raise_for_status(response: httpx.Response) -> None:
    """
    Raise an appropriate exception for HTTP error responses.

    Args:
        response: The HTTP response to check

    Raises:
        HTTPError: If the response indicates an error
    """
    if response.is_success:
        return

    status_code = response.status_code
    exception_class = HTTP_STATUS_TO_EXCEPTION.get(status_code)

    if exception_class:
        raise exception_class(request=response.request, response=response)
    elif 400 <= status_code < 500:
        raise ClientError(
            f"Client error: {status_code}",
            request=response.request,
            response=response,
        )
    elif 500 <= status_code < 600:
        raise ServerError(
            f"Server error: {status_code}",
            request=response.request,
            response=response,
        )
    else:
        raise HTTPError(
            f"HTTP error: {status_code}",
            request=response.request,
            response=response,
        )
