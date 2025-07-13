"""Tests for headers manager module."""

from typing import Any

from travessera._internal.headers_manager import HeadersManager
from travessera.types import Headers


class TestHeadersManager:
    """Test the HeadersManager class."""

    def test_init_default(self):
        """Test initialization with defaults."""
        manager = HeadersManager()
        assert manager.static_headers == {}
        assert manager.headers_factory is None

    def test_init_with_static_headers(self):
        """Test initialization with static headers."""
        headers = {"X-API-Key": "test-key", "X-Client": "test"}
        manager = HeadersManager(static_headers=headers)
        assert manager.static_headers == headers

    def test_init_with_headers_factory(self):
        """Test initialization with headers factory."""

        def factory(params: dict[str, Any]) -> Headers:
            return {"X-Request-ID": str(params.get("id", "default"))}

        manager = HeadersManager(headers_factory=factory)
        assert manager.headers_factory is factory

    def test_get_headers_static_only(self):
        """Test getting headers with only static headers."""
        static = {"X-API-Key": "key", "User-Agent": "test"}
        manager = HeadersManager(static_headers=static)

        headers = manager.get_headers()
        assert headers == static
        # Ensure we get a copy, not the original
        assert headers is not manager.static_headers

    def test_get_headers_with_factory(self):
        """Test getting headers with factory."""
        static = {"X-API-Key": "key"}

        def factory(params: dict[str, Any]) -> Headers:
            return {"X-User-ID": str(params["user_id"]), "X-Request-ID": "req-123"}

        manager = HeadersManager(static_headers=static, headers_factory=factory)

        # Test with params
        headers = manager.get_headers({"user_id": 42})
        assert headers == {
            "X-API-Key": "key",
            "X-User-ID": "42",
            "X-Request-ID": "req-123",
        }

    def test_get_headers_factory_overrides_static(self):
        """Test that factory headers override static headers."""
        static = {"X-API-Key": "static-key", "X-Client": "static"}

        def factory(params: dict[str, Any]) -> Headers:
            return {"X-API-Key": "dynamic-key"}  # Override static

        manager = HeadersManager(static_headers=static, headers_factory=factory)
        headers = manager.get_headers({"id": 1})

        assert headers["X-API-Key"] == "dynamic-key"  # Dynamic wins
        assert headers["X-Client"] == "static"  # Static preserved

    def test_get_headers_no_params_with_factory(self):
        """Test get_headers with factory but no params."""
        static = {"X-API-Key": "key"}

        def factory(params: dict[str, Any]) -> Headers:
            return {"X-Dynamic": "value"}

        manager = HeadersManager(static_headers=static, headers_factory=factory)

        # No params passed, factory not called
        headers = manager.get_headers()
        assert headers == static
        assert "X-Dynamic" not in headers

    def test_merge_with_none(self):
        """Test merging with None additional headers."""
        static = {"X-API-Key": "key", "X-Client": "test"}
        manager = HeadersManager(static_headers=static)

        merged = manager.merge_with(None)
        assert merged == static
        assert merged is not manager.static_headers  # Should be a copy

    def test_merge_with_additional(self):
        """Test merging with additional headers."""
        static = {"X-API-Key": "key", "X-Client": "test"}
        manager = HeadersManager(static_headers=static)

        additional = {"X-Extra": "value", "X-Client": "override"}
        merged = manager.merge_with(additional)

        assert merged == {
            "X-API-Key": "key",
            "X-Client": "override",  # Additional wins
            "X-Extra": "value",
        }

    def test_merge_headers_static_method(self):
        """Test static merge_headers method."""
        headers1 = {"X-A": "1", "X-B": "2"}
        headers2 = {"X-B": "3", "X-C": "4"}  # Override X-B
        headers3 = {"X-D": "5"}

        merged = HeadersManager.merge_headers(headers1, headers2, headers3)

        assert merged == {
            "X-A": "1",
            "X-B": "3",  # headers2 wins
            "X-C": "4",
            "X-D": "5",
        }

    def test_merge_headers_with_none(self):
        """Test merge_headers with None values."""
        headers1 = {"X-A": "1"}
        merged = HeadersManager.merge_headers(None, headers1, None)
        assert merged == headers1

    def test_merge_headers_all_none(self):
        """Test merge_headers with all None values."""
        merged = HeadersManager.merge_headers(None, None)
        assert merged == {}

    def test_with_content_type(self):
        """Test with_content_type method."""
        static = {"X-API-Key": "key"}
        manager = HeadersManager(static_headers=static)

        headers = manager.with_content_type("application/json")
        assert headers == {"X-API-Key": "key", "Content-Type": "application/json"}

        # Test override
        static_with_ct = {"X-API-Key": "key", "Content-Type": "text/plain"}
        manager2 = HeadersManager(static_headers=static_with_ct)
        headers2 = manager2.with_content_type("application/json")
        assert headers2["Content-Type"] == "application/json"

    def test_with_accept(self):
        """Test with_accept method."""
        static = {"X-API-Key": "key"}
        manager = HeadersManager(static_headers=static)

        headers = manager.with_accept("application/json")
        assert headers == {"X-API-Key": "key", "Accept": "application/json"}

        # Test override
        static_with_accept = {"X-API-Key": "key", "Accept": "text/html"}
        manager2 = HeadersManager(static_headers=static_with_accept)
        headers2 = manager2.with_accept("application/json")
        assert headers2["Accept"] == "application/json"

    def test_headers_immutability(self):
        """Test that operations don't modify original headers."""
        static = {"X-API-Key": "key"}
        manager = HeadersManager(static_headers=static)

        # Various operations shouldn't modify static_headers
        manager.get_headers()
        manager.merge_with({"X-Extra": "value"})
        manager.with_content_type("application/json")
        manager.with_accept("application/json")

        # Original should be unchanged
        assert manager.static_headers == {"X-API-Key": "key"}

    def test_complex_headers_factory(self):
        """Test complex headers factory scenario."""
        static = {"X-API-Version": "1.0"}

        def factory(params: dict[str, Any]) -> Headers:
            headers = {}
            if "user_id" in params:
                headers["X-User-ID"] = str(params["user_id"])
            if "session_id" in params:
                headers["X-Session-ID"] = params["session_id"]
            if params.get("debug"):
                headers["X-Debug"] = "true"
            return headers

        manager = HeadersManager(static_headers=static, headers_factory=factory)

        # Test with various params
        headers = manager.get_headers(
            {
                "user_id": 123,
                "session_id": "sess-456",
                "debug": True,
                "other": "ignored",
            }
        )

        assert headers == {
            "X-API-Version": "1.0",
            "X-User-ID": "123",
            "X-Session-ID": "sess-456",
            "X-Debug": "true",
        }
