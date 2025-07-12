"""Tests for retry module."""

from unittest.mock import Mock, patch

import pytest

from travessera.exceptions import NetworkError, ServerError
from travessera.models import RetryConfig
from travessera.retry import (
    create_retry_logic,
    should_retry_status_code,
    with_retry,
    with_retry_async,
)


class TestRetryLogic:
    """Test retry logic creation and configuration."""

    def test_create_retry_logic_default_config(self):
        """Test creating retry logic with default config."""
        config = RetryConfig()
        retry_logic = create_retry_logic(config)

        assert retry_logic is not None
        assert retry_logic.stop.max_attempt_number == 3
        assert retry_logic.wait is not None
        assert retry_logic.retry is not None

    def test_create_retry_logic_custom_config(self):
        """Test creating retry logic with custom config."""
        config = RetryConfig(
            max_attempts=5,
            min_wait=2.0,
            max_wait=30.0,
            multiplier=3.0,
        )
        retry_logic = create_retry_logic(config)

        assert retry_logic.stop.max_attempt_number == 5

    def test_create_retry_logic_with_callback(self):
        """Test creating retry logic with before_retry callback."""
        callback = Mock()
        config = RetryConfig(before_retry=callback)
        retry_logic = create_retry_logic(config)

        assert retry_logic.before_sleep is not None

    def test_with_retry_wrapper(self):
        """Test the with_retry wrapper function."""
        call_count = 0

        @with_retry
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("Network error")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 2

    def test_with_retry_custom_config(self):
        """Test with_retry with custom configuration."""
        config = RetryConfig(max_attempts=2)
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise NetworkError("Always fails")

        wrapped = with_retry(always_fails, config)

        with pytest.raises(NetworkError):
            wrapped()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_async(self):
        """Test async retry wrapper."""
        call_count = 0

        async def async_flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("Network error")
            return "async success"

        result = await with_retry_async(async_flaky_function)
        assert result == "async success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_async_custom_config(self):
        """Test async retry with custom config."""
        config = RetryConfig(max_attempts=3)
        call_count = 0

        async def async_fails():
            nonlocal call_count
            call_count += 1
            raise ServerError("Server error")

        with pytest.raises(ServerError):
            await with_retry_async(async_fails, config)

        assert call_count == 3

    def test_should_retry_status_code(self):
        """Test status code retry logic."""
        # Retryable codes
        assert should_retry_status_code(408) is True  # Request Timeout
        assert should_retry_status_code(429) is True  # Too Many Requests
        assert should_retry_status_code(500) is True  # Internal Server Error
        assert should_retry_status_code(502) is True  # Bad Gateway
        assert should_retry_status_code(503) is True  # Service Unavailable
        assert should_retry_status_code(504) is True  # Gateway Timeout

        # Non-retryable codes
        assert should_retry_status_code(200) is False  # OK
        assert should_retry_status_code(400) is False  # Bad Request
        assert should_retry_status_code(401) is False  # Unauthorized
        assert should_retry_status_code(403) is False  # Forbidden
        assert should_retry_status_code(404) is False  # Not Found

    def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exception types."""
        config = RetryConfig(max_attempts=3, retry_on=(NetworkError,))
        network_calls = 0
        server_calls = 0

        def network_error_function():
            nonlocal network_calls
            network_calls += 1
            raise NetworkError("Network issue")

        def server_error_function():
            nonlocal server_calls
            server_calls += 1
            raise ServerError("Server issue")

        # Should retry NetworkError
        wrapped_network = with_retry(network_error_function, config)
        with pytest.raises(NetworkError):
            wrapped_network()
        assert network_calls == 3

        # Should not retry ServerError (not in retry_on)
        wrapped_server = with_retry(server_error_function, config)
        with pytest.raises(ServerError):
            wrapped_server()
        assert server_calls == 1

    @patch("travessera.retry.logger")
    def test_retry_logging(self, mock_logger):
        """Test that retries are logged."""
        config = RetryConfig(max_attempts=2)
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("Network error")
            return "success"

        wrapped = with_retry(failing_function, config)
        result = wrapped()

        assert result == "success"
        # Logger should have been configured for before_sleep
