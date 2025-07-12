"""
Travessera - A Python library for abstracting microservice calls as local functions.

This library provides decorators that transform regular functions into HTTP calls,
handling serialization, deserialization, retries, and error handling automatically.
"""

from travessera.authentication import ApiKeyAuthentication, Authentication
from travessera.core import Service, Travessera
from travessera.exceptions import (
    BadRequestError,
    ClientError,
    ConnectionError,
    DNSError,
    ForbiddenError,
    HTTPError,
    InternalServerError,
    NetworkError,
    NotFoundError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    TravesseraError,
    UnauthorizedError,
    ValidationError,
)
from travessera.models import RetryConfig

__version__ = "0.1.0"

__all__ = [
    # Core classes
    "Travessera",
    "Service",
    # Authentication
    "Authentication",
    "ApiKeyAuthentication",
    # Configuration
    "RetryConfig",
    # Exceptions
    "TravesseraError",
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    "DNSError",
    "HTTPError",
    "ClientError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ServerError",
    "InternalServerError",
    "ServiceUnavailableError",
    "ValidationError",
]
