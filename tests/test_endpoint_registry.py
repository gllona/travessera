"""Tests for endpoint registry module."""

from unittest.mock import Mock

import pytest

from travessera._internal.endpoint_registry import EndpointRegistry, RegisteredEndpoint
from travessera.types import EndpointConfig


class TestEndpointRegistry:
    """Test the EndpointRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return EndpointRegistry()

    @pytest.fixture
    def sample_function(self):
        """Create a sample function for testing."""

        def get_user(user_id: int) -> dict:
            return {"id": user_id}

        return get_user

    @pytest.fixture
    def sample_config(self):
        """Create a sample endpoint config."""
        return EndpointConfig(
            service="users",
            endpoint="/users/{user_id}",
            method="GET",
            timeout=30.0,
        )

    def test_init(self, registry):
        """Test registry initialization."""
        assert registry._endpoints == {}
        assert registry._function_index == {}

    def test_register_endpoint(self, registry, sample_function, sample_config):
        """Test registering an endpoint."""
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=sample_function,
            config=sample_config,
        )

        # Check that endpoint was registered
        assert "users.get_user" in registry._endpoints
        assert sample_function in registry._function_index

        # Verify endpoint details
        endpoint = registry._endpoints["users.get_user"]
        assert isinstance(endpoint, RegisteredEndpoint)
        assert endpoint.service_name == "users"
        assert endpoint.endpoint_path == "/users/{user_id}"
        assert endpoint.method == "GET"
        assert endpoint.function is sample_function
        assert endpoint.config == sample_config

    def test_get_by_key(self, registry, sample_function, sample_config):
        """Test getting endpoint by key."""
        # Register endpoint
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=sample_function,
            config=sample_config,
        )

        # Get by key
        endpoint = registry.get_by_key("users.get_user")
        assert endpoint is not None
        assert endpoint.function is sample_function

        # Test non-existent key
        assert registry.get_by_key("users.non_existent") is None

    def test_get_by_function(self, registry, sample_function, sample_config):
        """Test getting endpoint by function."""
        # Register endpoint
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=sample_function,
            config=sample_config,
        )

        # Get by function
        endpoint = registry.get_by_function(sample_function)
        assert endpoint is not None
        assert endpoint.service_name == "users"

        # Test non-registered function
        def other_function():
            pass

        assert registry.get_by_function(other_function) is None

    def test_list_endpoints(self, registry, sample_function, sample_config):
        """Test listing all endpoints."""

        # Register multiple endpoints
        def create_user(user: dict) -> dict:
            return user

        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=sample_function,
            config=sample_config,
        )

        create_config = EndpointConfig(
            service="users",
            endpoint="/users",
            method="POST",
        )

        registry.register(
            service_name="users",
            function_name="create_user",
            endpoint_path="/users",
            method="POST",
            function=create_user,
            config=create_config,
        )

        # List endpoints
        endpoints = registry.list_endpoints()
        assert len(endpoints) == 2
        assert "users.get_user" in endpoints
        assert "users.create_user" in endpoints

        # Verify it returns a copy
        endpoints.clear()
        assert len(registry._endpoints) == 2

    def test_clear(self, registry, sample_function, sample_config):
        """Test clearing the registry."""
        # Register endpoint
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=sample_function,
            config=sample_config,
        )

        # Verify it was registered
        assert len(registry._endpoints) == 1
        assert len(registry._function_index) == 1

        # Clear registry
        registry.clear()

        # Verify it's empty
        assert len(registry._endpoints) == 0
        assert len(registry._function_index) == 0
        assert registry.get_by_key("users.get_user") is None
        assert registry.get_by_function(sample_function) is None

    def test_multiple_services(self, registry):
        """Test registering endpoints from multiple services."""

        def get_user(user_id: int) -> dict:
            return {"id": user_id}

        def get_order(order_id: int) -> dict:
            return {"id": order_id}

        # Register user endpoint
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=get_user,
            config=EndpointConfig(
                service="users", endpoint="/users/{user_id}", method="GET"
            ),
        )

        # Register order endpoint
        registry.register(
            service_name="orders",
            function_name="get_order",
            endpoint_path="/orders/{order_id}",
            method="GET",
            function=get_order,
            config=EndpointConfig(
                service="orders", endpoint="/orders/{order_id}", method="GET"
            ),
        )

        # Verify both are registered
        assert registry.get_by_key("users.get_user") is not None
        assert registry.get_by_key("orders.get_order") is not None

        # Verify they're different
        user_endpoint = registry.get_by_key("users.get_user")
        order_endpoint = registry.get_by_key("orders.get_order")
        assert user_endpoint.service_name == "users"
        assert order_endpoint.service_name == "orders"

    def test_overwrite_endpoint(self, registry, sample_function):
        """Test that registering with same key overwrites."""
        config1 = EndpointConfig(
            service="users", endpoint="/v1/users/{id}", method="GET"
        )
        config2 = EndpointConfig(
            service="users", endpoint="/v2/users/{id}", method="GET"
        )

        # Register first version
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/v1/users/{id}",
            method="GET",
            function=sample_function,
            config=config1,
        )

        # Register second version (overwrites)
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/v2/users/{id}",
            method="GET",
            function=sample_function,
            config=config2,
        )

        # Verify it was overwritten
        endpoint = registry.get_by_key("users.get_user")
        assert endpoint.endpoint_path == "/v2/users/{id}"
        assert endpoint.config == config2

    def test_parsed_signature_field(self, registry, sample_function, sample_config):
        """Test that parsed_signature can be set."""
        registry.register(
            service_name="users",
            function_name="get_user",
            endpoint_path="/users/{user_id}",
            method="GET",
            function=sample_function,
            config=sample_config,
        )

        endpoint = registry.get_by_key("users.get_user")
        assert endpoint.parsed_signature is None

        # Set parsed signature
        mock_signature = Mock()
        endpoint.parsed_signature = mock_signature
        assert endpoint.parsed_signature is mock_signature
