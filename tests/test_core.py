"""Tests for the core module."""

import pytest

from travessera import ApiKeyAuthentication, Service, Travessera
from travessera.exceptions import ServiceNotFoundError
from travessera.models import RetryConfig


def test_service_initialization():
    """Test Service initialization."""
    auth = ApiKeyAuthentication("test-key")
    retry_config = RetryConfig(max_attempts=5)

    service = Service(
        name="test-service",
        base_url="https://api.example.com/",
        timeout=60.0,
        authentication=auth,
        headers={"X-Custom": "value"},
        retry_config=retry_config,
    )

    assert service.name == "test-service"
    assert service.base_url == "https://api.example.com"  # Trailing slash removed
    assert service.timeout == 60.0
    assert service.authentication == auth
    assert service.headers == {"X-Custom": "value"}
    assert service.retry_config == retry_config


def test_service_get_config():
    """Test Service.get_config method."""
    service = Service(
        name="test-service",
        base_url="https://api.example.com",
    )

    config = service.get_config()
    assert config["name"] == "test-service"
    assert config["base_url"] == "https://api.example.com"
    assert config["timeout"] is None
    assert config["headers"] == {}


def test_travessera_initialization():
    """Test Travessera initialization."""
    service1 = Service("service1", "https://api1.example.com")
    service2 = Service("service2", "https://api2.example.com")

    travessera = Travessera(
        services=[service1, service2],
        default_timeout=45.0,
        default_headers={"X-Global": "header"},
    )

    assert len(travessera.services) == 2
    assert travessera.default_timeout == 45.0
    assert travessera.default_headers == {"X-Global": "header"}


def test_travessera_get_service():
    """Test Travessera.get_service method."""
    service = Service("test", "https://api.example.com")
    travessera = Travessera(services=[service])

    # Get existing service
    retrieved = travessera.get_service("test")
    assert retrieved == service

    # Get non-existent service
    with pytest.raises(ServiceNotFoundError) as exc_info:
        travessera.get_service("nonexistent")

    assert exc_info.value.service_name == "nonexistent"


def test_travessera_decorators():
    """Test Travessera decorator methods."""
    service = Service("api", "https://api.example.com")
    travessera = Travessera(services=[service])

    # Test @endpoint decorator
    @travessera.endpoint("api", "/users/{id}", "GET")
    def get_user(id: int):
        pass

    # Test @get decorator
    @travessera.get("api", "/users")
    def list_users():
        pass

    # Test @post decorator
    @travessera.post("api", "/users")
    def create_user(name: str):
        pass

    # Check that endpoints are registered
    assert "api.get_user" in travessera._endpoints
    assert "api.list_users" in travessera._endpoints
    assert "api.create_user" in travessera._endpoints

    # Check endpoint configuration
    get_user_config = travessera._endpoints["api.get_user"]
    assert get_user_config["service"] == "api"
    assert get_user_config["endpoint"] == "/users/{id}"
    assert get_user_config["method"] == "GET"

    create_user_config = travessera._endpoints["api.create_user"]
    assert create_user_config["method"] == "POST"


def test_travessera_decorator_with_options():
    """Test Travessera decorator with additional options."""
    service = Service("api", "https://api.example.com")
    travessera = Travessera(services=[service])

    @travessera.get(
        "api",
        "/users/{id}",
        timeout=5.0,
        headers={"X-Custom": "header"},
        retry_config=RetryConfig(max_attempts=2),
    )
    def get_user(id: int):
        pass

    config = travessera._endpoints["api.get_user"]
    assert config["timeout"] == 5.0
    assert config["headers"] == {"X-Custom": "header"}
    assert config["retry_config"].max_attempts == 2


def test_travessera_context_manager():
    """Test Travessera as context manager."""
    service = Service("api", "https://api.example.com")

    with Travessera(services=[service]) as travessera:
        assert "api" in travessera.services

    # After exiting, services should be closed
    # (We can't easily test this without mocking the HTTP client)


def test_travessera_invalid_service_in_decorator():
    """Test decorator with invalid service name."""
    service = Service("api", "https://api.example.com")
    travessera = Travessera(services=[service])

    with pytest.raises(ServiceNotFoundError):

        @travessera.get("nonexistent", "/users")
        def get_users():
            pass
