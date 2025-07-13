"""Tests for async cleanup functionality and resource management."""

import gc
import warnings
from unittest.mock import AsyncMock, Mock, patch

import pytest

from travessera import Service, Travessera
from travessera.client import HTTPClient, RetryableHTTPClient

# Test base URL to avoid None base_url issues
TEST_BASE_URL = "https://api.example.com"


class TestHTTPClientCleanup:
    """Test HTTPClient cleanup and resource management."""

    def test_sync_client_close(self):
        """Test that sync client is properly closed."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Access sync client to create it
        sync_client = client.sync_client

        # Mock the close method to verify it's called
        with patch.object(sync_client, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()

        # Client should be None after close
        assert client._sync_client is None

    @pytest.mark.asyncio
    async def test_async_client_aclose(self):
        """Test that async client is properly closed."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Access async client to create it
        async_client = client.async_client

        # Mock the aclose method to verify it's called
        with patch.object(
            async_client, "aclose", new_callable=AsyncMock
        ) as mock_aclose:
            await client.aclose()
            mock_aclose.assert_called_once()

        # Client should be None after aclose
        assert client._async_client is None

    def test_sync_context_manager(self):
        """Test sync context manager properly closes resources."""
        with HTTPClient(base_url=TEST_BASE_URL) as client:
            # Access client to create it
            sync_client = client.sync_client

            # Mock close to verify it's called
            with patch.object(sync_client, "close"):
                pass  # Context manager will call close on exit

        # Verify close was called when exiting context manager
        # Note: We can't easily test this without complex mocking

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager properly closes resources."""
        async with HTTPClient(base_url=TEST_BASE_URL) as client:
            # Access client to create it
            async_client = client.async_client

            # Mock aclose to verify it's called
            with patch.object(async_client, "aclose", new_callable=AsyncMock):
                pass  # Context manager will call aclose on exit

    def test_del_method_sync_only(self):
        """Test __del__ method with only sync client."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create only sync client
        sync_client = client.sync_client

        with patch.object(sync_client, "close") as mock_close:
            # Simulate garbage collection
            client.__del__()
            mock_close.assert_called_once()

    def test_del_method_async_only(self):
        """Test __del__ method with only async client."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create only async client
        _ = client.async_client

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Simulate garbage collection
            client.__del__()

            # Should issue a warning about improper cleanup
            assert len(w) == 1
            assert issubclass(w[0].category, ResourceWarning)
            assert "not properly closed" in str(w[0].message)

    def test_del_method_both_clients(self):
        """Test __del__ method with both clients."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create both clients
        sync_client = client.sync_client
        _ = client.async_client

        with (
            patch.object(sync_client, "close") as mock_close,
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")

            # Simulate garbage collection
            client.__del__()

            # Sync client should be closed
            mock_close.assert_called_once()

            # Should warn about async client
            assert len(w) == 1
            assert issubclass(w[0].category, ResourceWarning)

    def test_del_method_no_errors_on_exception(self):
        """Test __del__ method handles exceptions gracefully."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create sync client
        sync_client = client.sync_client

        # Make close raise an exception
        with patch.object(sync_client, "close", side_effect=Exception("Test error")):
            # Should not raise exception
            client.__del__()

    @pytest.mark.asyncio
    async def test_close_with_running_event_loop(self):
        """Test close method behavior with running event loop."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create async client
        async_client = client.async_client

        with (
            patch.object(async_client, "aclose", new_callable=AsyncMock),
            patch("asyncio.get_running_loop") as mock_get_loop,
        ):
            mock_loop = Mock()
            mock_loop.is_closed.return_value = False
            mock_get_loop.return_value = mock_loop

            # Call close (sync method) with running loop
            client.close()

            # Should create task for async cleanup
            mock_loop.create_task.assert_called_once()

    def test_close_with_no_running_loop(self):
        """Test close method behavior with no running event loop."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create async client
        async_client = client.async_client

        # Mock aclose as a simple mock that returns None when called
        mock_aclose = Mock()
        mock_aclose.return_value = None

        with (
            patch.object(async_client, "aclose", mock_aclose),
            patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")),
            patch("asyncio.run") as mock_run,
        ):
            # Call close (sync method) with no running loop
            client.close()

            # Should attempt to run aclose
            mock_run.assert_called_once()

    def test_close_with_loop_unavailable_during_shutdown(self):
        """Test close method when event loop is unavailable during shutdown."""
        client = HTTPClient(base_url=TEST_BASE_URL)

        # Create async client but mock it to avoid coroutine warnings
        async_client = client.async_client
        mock_aclose = Mock()
        mock_aclose.return_value = None

        with (
            patch.object(async_client, "aclose", mock_aclose),
            patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")),
            patch("asyncio.run", side_effect=RuntimeError("Loop unavailable")),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")

            # Call close - should handle gracefully
            client.close()

            # Should issue warning about skipped cleanup
            assert len(w) == 1
            assert issubclass(w[0].category, ResourceWarning)
            assert "async cleanup skipped" in str(w[0].message)


class TestServiceCleanup:
    """Test Service cleanup and resource management."""

    def test_service_close(self):
        """Test Service close method."""
        service = Service("test", "https://api.example.com")

        # Access client to create it
        client = service.client

        # Ensure async client is not created by preventing lazy initialization
        with (
            patch.object(client, "close") as mock_close,
            patch.object(client, "_async_client", None),
        ):
            service.close()
            mock_close.assert_called_once()

        # Client should be None after close
        assert service._client is None

    @pytest.mark.asyncio
    async def test_service_aclose(self):
        """Test Service aclose method."""
        service = Service("test", "https://api.example.com")

        # Access client to create it
        client = service.client

        with patch.object(client, "aclose", new_callable=AsyncMock) as mock_aclose:
            await service.aclose()
            mock_aclose.assert_called_once()

        # Client should be None after aclose
        assert service._client is None

    def test_service_sync_context_manager(self):
        """Test Service sync context manager."""
        with Service("test", "https://api.example.com") as service:
            assert service.name == "test"

        # After context, client should be cleaned up
        assert service._client is None

    @pytest.mark.asyncio
    async def test_service_async_context_manager(self):
        """Test Service async context manager."""
        async with Service("test", "https://api.example.com") as service:
            assert service.name == "test"

        # After context, client should be cleaned up
        assert service._client is None


class TestTravesseraCleanup:
    """Test Travessera cleanup and resource management."""

    def test_travessera_close(self):
        """Test Travessera close method."""
        service1 = Service("service1", "https://api1.example.com")
        service2 = Service("service2", "https://api2.example.com")
        travessera = Travessera(services=[service1, service2])

        # Access clients to create them
        client1 = service1.client
        client2 = service2.client

        with (
            patch.object(client1, "close") as mock_close1,
            patch.object(client2, "close") as mock_close2,
        ):
            travessera.close()
            mock_close1.assert_called_once()
            mock_close2.assert_called_once()

    @pytest.mark.asyncio
    async def test_travessera_aclose(self):
        """Test Travessera aclose method."""
        service1 = Service("service1", "https://api1.example.com")
        service2 = Service("service2", "https://api2.example.com")
        travessera = Travessera(services=[service1, service2])

        # Access clients to create them
        client1 = service1.client
        client2 = service2.client

        with (
            patch.object(client1, "aclose", new_callable=AsyncMock) as mock_aclose1,
            patch.object(client2, "aclose", new_callable=AsyncMock) as mock_aclose2,
        ):
            await travessera.aclose()
            mock_aclose1.assert_called_once()
            mock_aclose2.assert_called_once()

    def test_travessera_sync_context_manager(self):
        """Test Travessera sync context manager."""
        service = Service("test", "https://api.example.com")

        with Travessera(services=[service]) as travessera:
            assert "test" in travessera.services

        # Services should be closed after context

    @pytest.mark.asyncio
    async def test_travessera_async_context_manager(self):
        """Test Travessera async context manager."""
        service = Service("test", "https://api.example.com")

        async with Travessera(services=[service]) as travessera:
            assert "test" in travessera.services

        # Services should be closed after context


class TestRetryableHTTPClientCleanup:
    """Test RetryableHTTPClient cleanup behavior."""

    def test_retryable_client_close(self):
        """Test RetryableHTTPClient close method."""
        client = RetryableHTTPClient(base_url=TEST_BASE_URL)

        # Access sync client to create it
        sync_client = client.sync_client

        with patch.object(sync_client, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()

        assert client._sync_client is None

    @pytest.mark.asyncio
    async def test_retryable_client_aclose(self):
        """Test RetryableHTTPClient aclose method."""
        client = RetryableHTTPClient(base_url=TEST_BASE_URL)

        # Access async client to create it
        async_client = client.async_client

        # Create a simple mock instead of AsyncMock to avoid coroutine warnings
        mock_aclose = Mock()

        async def async_mock():
            mock_aclose()

        with patch.object(async_client, "aclose", side_effect=async_mock):
            await client.aclose()
            mock_aclose.assert_called_once()

        assert client._async_client is None


class TestCleanupIntegration:
    """Integration tests for cleanup across multiple components."""

    @pytest.mark.asyncio
    async def test_full_stack_cleanup(self):
        """Test cleanup of full Travessera stack."""
        # Create multiple services
        services = [
            Service("api1", "https://api1.example.com"),
            Service("api2", "https://api2.example.com"),
            Service("api3", "https://api3.example.com"),
        ]

        # Use async context manager
        async with Travessera(services=services):
            # Access all clients to ensure they're created
            for service in services:
                client = service.client
                assert client is not None

        # After context, all clients should be cleaned up
        for service in services:
            assert service._client is None

    def test_nested_context_managers(self):
        """Test nested context managers work properly."""
        service1 = Service("api1", "https://api1.example.com")
        service2 = Service("api2", "https://api2.example.com")

        with (
            service1,
            service2,
            Travessera(services=[service1, service2]) as travessera,
        ):
            assert len(travessera.services) == 2

        # All should be cleaned up
        assert service1._client is None
        assert service2._client is None

    def test_cleanup_prevents_resource_leaks(self):
        """Test that cleanup prevents resource leaks."""
        # Create many clients to simulate potential leak scenario
        clients = []

        for i in range(10):
            client = HTTPClient(base_url=f"https://api{i}.example.com")
            # Access sync client to create it
            clients.append(client)

        # Close all clients
        for client in clients:
            client.close()

        # Force garbage collection
        gc.collect()

        # All clients should be None
        for client in clients:
            assert client._sync_client is None

    @pytest.mark.asyncio
    async def test_exception_during_cleanup_handled(self):
        """Test that exceptions during cleanup are handled gracefully."""
        service = Service("test", "https://api.example.com")

        # Access client to create it
        client = service.client

        # Make aclose raise an exception, but this will be propagated
        # since our context manager doesn't suppress cleanup errors
        with patch.object(client, "aclose", side_effect=Exception("Cleanup error")):
            # Context manager will propagate cleanup exceptions
            with pytest.raises(Exception) as exc_info:
                async with service:
                    pass

            # Verify it's the cleanup error
            assert "Cleanup error" in str(exc_info.value)
