"""Tests for the authentication module."""

import httpx

from travessera.authentication import (
    ApiKeyAuthentication,
    BasicAuthentication,
    BearerTokenAuthentication,
    ChainAuthentication,
    HeaderAuthentication,
    NoAuthentication,
)


def test_api_key_authentication():
    """Test ApiKeyAuthentication."""
    auth = ApiKeyAuthentication("test-key", "X-Custom-Key")
    request = httpx.Request("GET", "https://example.com")

    auth.apply(request)

    assert request.headers["X-Custom-Key"] == "test-key"


def test_api_key_authentication_default_header():
    """Test ApiKeyAuthentication with default header name."""
    auth = ApiKeyAuthentication("test-key")
    request = httpx.Request("GET", "https://example.com")

    auth.apply(request)

    assert request.headers["X-API-Key"] == "test-key"


def test_bearer_token_authentication():
    """Test BearerTokenAuthentication."""
    auth = BearerTokenAuthentication("test-token")
    request = httpx.Request("GET", "https://example.com")

    auth.apply(request)

    assert request.headers["Authorization"] == "Bearer test-token"


def test_basic_authentication():
    """Test BasicAuthentication."""
    auth = BasicAuthentication("user", "pass")
    request = httpx.Request("GET", "https://example.com")

    auth.apply(request)

    # Base64 of "user:pass" is "dXNlcjpwYXNz"
    assert request.headers["Authorization"] == "Basic dXNlcjpwYXNz"


def test_header_authentication():
    """Test HeaderAuthentication."""
    headers = {
        "X-Custom-1": "value1",
        "X-Custom-2": "value2",
    }
    auth = HeaderAuthentication(headers)
    request = httpx.Request("GET", "https://example.com")

    auth.apply(request)

    assert request.headers["X-Custom-1"] == "value1"
    assert request.headers["X-Custom-2"] == "value2"


def test_no_authentication():
    """Test NoAuthentication."""
    auth = NoAuthentication()
    request = httpx.Request("GET", "https://example.com")
    original_headers = dict(request.headers)

    auth.apply(request)

    assert dict(request.headers) == original_headers


def test_chain_authentication():
    """Test ChainAuthentication."""
    auth1 = ApiKeyAuthentication("key1", "X-Key-1")
    auth2 = HeaderAuthentication({"X-Custom": "value"})
    auth3 = BearerTokenAuthentication("token")

    chain = ChainAuthentication(auth1, auth2, auth3)
    request = httpx.Request("GET", "https://example.com")

    chain.apply(request)

    assert request.headers["X-Key-1"] == "key1"
    assert request.headers["X-Custom"] == "value"
    assert request.headers["Authorization"] == "Bearer token"
