"""Tests for the parameter parser module."""


import pytest
from pydantic import BaseModel

from travessera._internal.parameter_parser import ParameterParser


class UserModel(BaseModel):
    """Test model."""

    name: str
    email: str


def test_parse_endpoint_path():
    """Test parsing parameter names from endpoint paths."""
    # Simple path
    params = ParameterParser.parse_endpoint_path("/users/{user_id}")
    assert params == {"user_id"}

    # Multiple parameters
    params = ParameterParser.parse_endpoint_path("/users/{user_id}/posts/{post_id}")
    assert params == {"user_id", "post_id"}

    # No parameters
    params = ParameterParser.parse_endpoint_path("/users")
    assert params == set()

    # Complex path
    params = ParameterParser.parse_endpoint_path(
        "/api/v1/{version}/users/{id}/action/{action}"
    )
    assert params == {"version", "id", "action"}


def test_parse_function_get_request():
    """Test parsing function for GET request."""

    def get_user(user_id: int, include_posts: bool = False) -> dict:
        pass

    parsed = ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")

    assert len(parsed.parameters) == 2
    assert parsed.path_params == ["user_id"]
    assert parsed.query_params == ["include_posts"]
    assert parsed.body_param is None
    assert parsed.return_type == dict

    # Check user_id parameter
    user_id_param = parsed.parameters["user_id"]
    assert user_id_param.annotation == int
    assert not user_id_param.has_default
    assert user_id_param.is_path_param

    # Check include_posts parameter
    include_posts_param = parsed.parameters["include_posts"]
    assert include_posts_param.annotation == bool
    assert include_posts_param.has_default
    assert include_posts_param.default is False
    assert include_posts_param.is_query_param


def test_parse_function_post_request():
    """Test parsing function for POST request."""

    def create_user(user: UserModel, notify: bool = True) -> UserModel:
        pass

    parsed = ParameterParser.parse_function(create_user, "/users", "POST")

    assert len(parsed.parameters) == 2
    assert parsed.path_params == []
    assert parsed.query_params == ["notify"]
    assert parsed.body_param == "user"
    assert parsed.return_type == UserModel

    # Check user parameter
    user_param = parsed.parameters["user"]
    assert user_param.annotation == UserModel
    assert user_param.is_body_param

    # Check notify parameter
    notify_param = parsed.parameters["notify"]
    assert notify_param.annotation == bool
    assert notify_param.is_query_param


def test_parse_function_mixed_params():
    """Test parsing function with mixed parameter types."""

    def update_user(
        user_id: int, user: UserModel, version: str, force: bool = False
    ) -> UserModel:
        pass

    parsed = ParameterParser.parse_function(update_user, "/users/{user_id}", "PUT")

    assert parsed.path_params == ["user_id"]
    assert parsed.query_params == ["version", "force"]
    assert parsed.body_param == "user"


def test_parse_function_list_body():
    """Test parsing function with list as body."""

    def create_users(users: list[UserModel]) -> list[UserModel]:
        pass

    parsed = ParameterParser.parse_function(create_users, "/users/batch", "POST")

    assert parsed.body_param == "users"
    assert parsed.parameters["users"].annotation == list[UserModel]


def test_parse_function_dict_body():
    """Test parsing function with dict as body."""

    def update_settings(settings: dict) -> dict:
        pass

    parsed = ParameterParser.parse_function(update_settings, "/settings", "POST")

    assert parsed.body_param == "settings"


def test_parse_function_no_annotations():
    """Test parsing function without type annotations."""

    def get_data(id, name="default"):
        pass

    parsed = ParameterParser.parse_function(get_data, "/data/{id}", "GET")

    assert parsed.path_params == ["id"]
    assert parsed.query_params == ["name"]
    assert parsed.return_type is None


def test_parse_function_missing_path_param():
    """Test parsing function with missing path parameter."""

    def get_user(name: str) -> dict:
        pass

    with pytest.raises(ValueError) as exc_info:
        ParameterParser.parse_function(get_user, "/users/{user_id}", "GET")

    assert "Path parameters {'user_id'} not found" in str(exc_info.value)


def test_extract_path_values():
    """Test extracting path values from kwargs."""

    def get_post(user_id: int, post_id: int) -> dict:
        pass

    parsed = ParameterParser.parse_function(
        get_post, "/users/{user_id}/posts/{post_id}", "GET"
    )

    path, remaining = ParameterParser.extract_path_values(
        "/users/{user_id}/posts/{post_id}",
        parsed,
        {"user_id": 123, "post_id": 456, "other": "value"},
    )

    assert path == "/users/123/posts/456"
    assert remaining == {"other": "value"}


def test_extract_query_params():
    """Test extracting query parameters."""

    def search_users(
        name: str, age: int | None = None, active: bool = True
    ) -> list[dict]:
        pass

    parsed = ParameterParser.parse_function(search_users, "/users/search", "GET")

    # Test with all params provided
    query_params = ParameterParser.extract_query_params(
        parsed, {"name": "John", "age": 30, "active": False}
    )
    assert query_params == {"name": "John", "age": 30, "active": False}

    # Test with optional param as None (should be excluded)
    query_params = ParameterParser.extract_query_params(
        parsed, {"name": "John", "age": None}
    )
    assert query_params == {"name": "John", "active": True}

    # Test with missing optional params
    query_params = ParameterParser.extract_query_params(parsed, {"name": "John"})
    assert query_params == {"name": "John", "active": True}


def test_extract_body_data():
    """Test extracting body data."""

    def create_user(user: UserModel) -> UserModel:
        pass

    parsed = ParameterParser.parse_function(create_user, "/users", "POST")

    user_data = UserModel(name="John", email="john@example.com")
    body = ParameterParser.extract_body_data(parsed, {"user": user_data})

    assert body == user_data

    # Test with no body param in kwargs
    body = ParameterParser.extract_body_data(parsed, {})
    assert body is None
