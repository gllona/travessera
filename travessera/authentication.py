"""
Authentication strategies for Travessera.

This module provides various authentication methods that can be used
with services to authenticate HTTP requests.
"""

from abc import ABC, abstractmethod

import httpx


class Authentication(ABC):
    """Base class for authentication strategies."""

    @abstractmethod
    def apply(self, request: httpx.Request) -> httpx.Request:
        """
        Apply authentication to an HTTP request.

        Args:
            request: The request to authenticate

        Returns:
            The authenticated request
        """
        pass


class ApiKeyAuthentication(Authentication):
    """
    API key authentication that adds a key to request headers.

    Args:
        api_key: The API key to use
        header_name: The header name for the API key (default: "X-API-Key")
    """

    def __init__(self, api_key: str, header_name: str = "X-API-Key") -> None:
        self.api_key = api_key
        self.header_name = header_name

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Add the API key to the request headers."""
        request.headers[self.header_name] = self.api_key
        return request


class BearerTokenAuthentication(Authentication):
    """
    Bearer token authentication for OAuth2 and similar schemes.

    Args:
        token: The bearer token to use
    """

    def __init__(self, token: str) -> None:
        self.token = token

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Add the bearer token to the Authorization header."""
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class BasicAuthentication(Authentication):
    """
    HTTP Basic authentication.

    Args:
        username: The username
        password: The password
    """

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        # Pre-encode the credentials to avoid doing it on every request
        import base64

        credentials = f"{username}:{password}"
        self.encoded_credentials = base64.b64encode(credentials.encode()).decode()

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Add the Basic auth credentials to the Authorization header."""
        request.headers["Authorization"] = f"Basic {self.encoded_credentials}"
        return request


class HeaderAuthentication(Authentication):
    """
    Generic header-based authentication.

    This can be used for custom authentication schemes that require
    specific headers to be set.

    Args:
        headers: Dictionary of headers to add to requests
    """

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Add the custom headers to the request."""
        request.headers.update(self.headers)
        return request


class NoAuthentication(Authentication):
    """No authentication - passes requests through unchanged."""

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Return the request unchanged."""
        return request


class ChainAuthentication(Authentication):
    """
    Chains multiple authentication methods together.

    This is useful when you need to apply multiple authentication
    strategies to a single request.

    Args:
        authentications: List of authentication strategies to apply in order
    """

    def __init__(self, *authentications: Authentication) -> None:
        self.authentications = authentications

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply all authentication strategies in order."""
        for auth in self.authentications:
            request = auth.apply(request)
        return request
