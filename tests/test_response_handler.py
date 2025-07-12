"""Tests for the response handler module."""

import httpx
import pytest
from pydantic import BaseModel

from travessera._internal.config_resolver import ResolvedConfig
from travessera._internal.parameter_parser import ParameterParser
from travessera._internal.response_handler import ResponseHandler
from travessera.exceptions import (
    NotFoundError,
    ResponseValidationError,
)
from travessera.serializers import JSONSerializer


class ResponseTestModel(BaseModel):
    """Test model."""

    id: int
    message: str


def test_handle_successful_response():
    """Test handling successful JSON response."""

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    # Create mock response
    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=b'{"key": "value"}',
        request=request,
    )

    result = handler.handle_response(response)
    assert result == {"key": "value"}


def test_handle_response_with_pydantic_model():
    """Test handling response with Pydantic model return type."""

    def get_model() -> ResponseTestModel:
        pass

    parsed = ParameterParser.parse_function(get_model, "/model", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/model")
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=b'{"id": 123, "message": "Hello"}',
        request=request,
    )

    result = handler.handle_response(response)
    assert isinstance(result, ResponseTestModel)
    assert result.id == 123
    assert result.message == "Hello"


def test_handle_response_with_transformer():
    """Test handling response with transformer."""

    def response_transformer(data):
        return data["wrapped"]

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=response_transformer,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=b'{"wrapped": {"key": "value"}}',
        request=request,
    )

    result = handler.handle_response(response)
    assert result == {"key": "value"}


def test_handle_empty_response():
    """Test handling empty response."""

    def get_data() -> None:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        204,  # No Content
        headers={},
        content=b"",
        request=request,
    )

    result = handler.handle_response(response)
    assert result is None


def test_handle_http_error():
    """Test handling HTTP error response."""

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        404,
        headers={"content-type": "application/json"},
        content=b'{"error": "Not found"}',
        request=request,
    )

    with pytest.raises(NotFoundError) as exc_info:
        handler.handle_response(response)

    assert exc_info.value.status_code == 404


def test_handle_custom_error_mapping():
    """Test handling response with custom error mapping."""

    class CustomNotFound(Exception):
        def __init__(self, message, request, response):
            super().__init__(message)
            self.request = request
            self.response = response

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises={404: CustomNotFound},
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        404,
        headers={"content-type": "application/json"},
        content=b'{"error": "Not found"}',
        request=request,
    )

    with pytest.raises(CustomNotFound) as exc_info:
        handler.handle_response(response)

    assert exc_info.value.response.status_code == 404


def test_handle_non_json_response():
    """Test handling non-JSON response when JSON is expected."""

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        200,
        headers={"content-type": "text/html"},
        content=b"<html>Not JSON</html>",
        request=request,
    )

    with pytest.raises(ResponseValidationError) as exc_info:
        handler.handle_response(response)

    assert "Expected JSON response" in str(exc_info.value)


def test_handle_invalid_json():
    """Test handling invalid JSON response."""

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=b"{invalid json}",
        request=request,
    )

    with pytest.raises(ResponseValidationError) as exc_info:
        handler.handle_response(response)

    assert "Failed to parse JSON" in str(exc_info.value)


def test_handle_transformer_error():
    """Test handling error in response transformer."""

    def bad_transformer(data):
        raise ValueError("Transform failed")

    def get_data() -> dict:
        pass

    parsed = ParameterParser.parse_function(get_data, "/data", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=bad_transformer,
        raises=None,
    )

    handler = ResponseHandler(config, parsed)

    request = httpx.Request("GET", "https://api.example.com/data")
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=b'{"key": "value"}',
        request=request,
    )

    with pytest.raises(ResponseValidationError) as exc_info:
        handler.handle_response(response)

    assert "Response transformer failed" in str(exc_info.value)
