"""Tests for the request builder module."""

from pydantic import BaseModel

from travessera._internal.config_resolver import ResolvedConfig
from travessera._internal.parameter_parser import ParameterParser
from travessera._internal.request_builder import RequestBuilder
from travessera.authentication import ApiKeyAuthentication
from travessera.serializers import JSONSerializer


class UserTestModel(BaseModel):
    """Test model."""

    name: str
    email: str


def test_build_url_simple():
    """Test building URL with simple path parameters."""

    def get_user(user_id: int) -> dict:
        pass

    parsed = ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")
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

    builder = RequestBuilder(config, parsed)
    url, query_params = builder.build_url("/users/{user_id}", {"user_id": 123})

    assert url == "https://api.example.com/users/123"
    assert query_params == {}


def test_build_url_with_query_params():
    """Test building URL with query parameters."""

    def list_users(page: int = 1, limit: int = 20, active: bool = True) -> list:
        pass

    parsed = ParameterParser.parse_function(list_users, "/users", "GET")
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

    builder = RequestBuilder(config, parsed)
    url, query_params = builder.build_url(
        "/users", {"page": 2, "limit": 50, "active": False}
    )

    assert url == "https://api.example.com/users"
    assert query_params == {"page": 2, "limit": 50, "active": False}


def test_build_headers_basic():
    """Test building basic headers."""

    def get_user(user_id: int) -> dict:
        pass

    parsed = ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={"X-API-Version": "1.0"},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    builder = RequestBuilder(config, parsed)
    headers = builder.build_headers({"user_id": 123})

    assert headers["X-API-Version"] == "1.0"
    assert headers["Accept"] == "application/json"


def test_build_headers_with_factory():
    """Test building headers with dynamic factory."""

    def get_user(user_id: int) -> dict:
        pass

    def headers_factory(params):
        return {"X-User-ID": str(params["user_id"])}

    parsed = ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={"X-Static": "value"},
        headers_factory=headers_factory,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    builder = RequestBuilder(config, parsed)
    headers = builder.build_headers({"user_id": 123})

    assert headers["X-Static"] == "value"
    assert headers["X-User-ID"] == "123"


def test_build_body_pydantic_model():
    """Test building body with Pydantic model."""

    def create_user(user: UserTestModel) -> UserTestModel:
        pass

    parsed = ParameterParser.parse_function(create_user, "/users", "POST")
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

    builder = RequestBuilder(config, parsed)
    user_data = UserTestModel(name="John", email="john@example.com")
    body = builder.build_body({"user": user_data})

    assert body == b'{"name":"John","email":"john@example.com"}'


def test_build_body_with_transformer():
    """Test building body with request transformer."""

    def create_user(user: dict) -> dict:
        pass

    def request_transformer(data):
        return {"wrapped": data}

    parsed = ParameterParser.parse_function(create_user, "/users", "POST")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=request_transformer,
        response_transformer=None,
        raises=None,
    )

    builder = RequestBuilder(config, parsed)
    body = builder.build_body({"user": {"name": "John"}})

    assert body == b'{"wrapped": {"name": "John"}}'  # JSON with spaces


def test_build_request_kwargs_get():
    """Test building complete request kwargs for GET."""

    def get_user(user_id: int, include_posts: bool = False) -> dict:
        pass

    parsed = ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")
    config = ResolvedConfig(
        base_url="https://api.example.com",
        timeout=30.0,
        headers={"X-API-Key": "secret"},
        headers_factory=None,
        retry_config=None,
        serializer=JSONSerializer(),
        request_transformer=None,
        response_transformer=None,
        raises=None,
    )

    builder = RequestBuilder(config, parsed)
    kwargs = builder.build_request_kwargs(
        "GET", "/users/{user_id}", {"user_id": 123, "include_posts": True}
    )

    assert kwargs["method"] == "GET"
    assert kwargs["url"] == "https://api.example.com/users/123"
    assert kwargs["params"] == {"include_posts": True}
    assert kwargs["timeout"] == 30.0
    assert kwargs["headers"]["X-API-Key"] == "secret"
    assert "content" not in kwargs


def test_build_request_kwargs_post():
    """Test building complete request kwargs for POST."""

    def create_user(user: UserTestModel) -> UserTestModel:
        pass

    parsed = ParameterParser.parse_function(create_user, "/users", "POST")
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

    builder = RequestBuilder(config, parsed)
    user_data = UserTestModel(name="John", email="john@example.com")
    kwargs = builder.build_request_kwargs("POST", "/users", {"user": user_data})

    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://api.example.com/users"
    assert kwargs["content"] == b'{"name":"John","email":"john@example.com"}'
    assert kwargs["headers"]["Content-Type"] == "application/json"


def test_apply_authentication():
    """Test applying authentication to request."""

    def get_user(user_id: int) -> dict:
        pass

    parsed = ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")
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

    auth = ApiKeyAuthentication("my-secret-key")
    builder = RequestBuilder(config, parsed, authentication=auth)

    request_kwargs = {
        "method": "GET",
        "url": "https://api.example.com/users/123",
        "headers": {"Accept": "application/json"},
    }

    authenticated_kwargs = builder.apply_authentication(request_kwargs)

    assert (
        authenticated_kwargs["headers"]["x-api-key"] == "my-secret-key"
    )  # httpx lowercases headers
    assert authenticated_kwargs["headers"]["accept"] == "application/json"
