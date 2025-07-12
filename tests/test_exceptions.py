"""Tests for the exceptions module."""

import httpx
import pytest

from travessera.exceptions import (
    HTTP_STATUS_TO_EXCEPTION,
    HTTPError,
    ServiceNotFoundError,
    TravesseraError,
    raise_for_status,
)


def test_service_not_found_error():
    """Test ServiceNotFoundError."""
    error = ServiceNotFoundError("test-service")
    assert str(error) == "Service 'test-service' not found"
    assert error.service_name == "test-service"
    assert isinstance(error, TravesseraError)


def test_http_error_with_response():
    """Test HTTPError with request and response."""
    request = httpx.Request("GET", "https://example.com/test")
    response = httpx.Response(
        404,
        headers={"content-type": "application/json"},
        content=b'{"error": "Not found"}',
        request=request,
    )

    error = HTTPError("Test error", request=request, response=response)

    assert error.status_code == 404
    assert error.request_info["method"] == "GET"
    assert error.request_info["url"] == "https://example.com/test"
    assert error.response_info["status_code"] == 404
    assert "Not found" in error.response_info["content"]


def test_raise_for_status_success():
    """Test raise_for_status with successful response."""
    request = httpx.Request("GET", "https://example.com/test")
    response = httpx.Response(200, request=request)

    # Should not raise
    raise_for_status(response)


def test_raise_for_status_known_error():
    """Test raise_for_status with known error codes."""
    request = httpx.Request("GET", "https://example.com/test")

    for status_code, exception_class in HTTP_STATUS_TO_EXCEPTION.items():
        response = httpx.Response(status_code, request=request)

        with pytest.raises(exception_class) as exc_info:
            raise_for_status(response)

        assert exc_info.value.status_code == status_code
        assert exc_info.value.request == request
        assert exc_info.value.response == response


def test_raise_for_status_unknown_client_error():
    """Test raise_for_status with unknown client error."""
    request = httpx.Request("GET", "https://example.com/test")
    response = httpx.Response(418, request=request)  # I'm a teapot

    with pytest.raises(HTTPError) as exc_info:
        raise_for_status(response)

    assert "Client error: 418" in str(exc_info.value)
    assert exc_info.value.status_code == 418
