"""Tests for the models module."""

import pytest

from travessera.exceptions import NetworkError, ServerError
from travessera.models import (
    CacheConfig,
    ConnectionConfig,
    MonitorConfig,
    RetryConfig,
    TracerConfig,
)


def test_retry_config_defaults():
    """Test RetryConfig with default values."""
    config = RetryConfig()

    assert config.max_attempts == 3
    assert config.min_wait == 1.0
    assert config.max_wait == 10.0
    assert config.multiplier == 2.0
    assert config.retry_on == (NetworkError, ServerError)
    assert config.before_retry is None


def test_retry_config_custom():
    """Test RetryConfig with custom values."""

    def custom_callback(state):
        pass

    config = RetryConfig(
        max_attempts=5,
        min_wait=2.0,
        max_wait=30.0,
        multiplier=3.0,
        retry_on=(ValueError, TypeError),
        before_retry=custom_callback,
    )

    assert config.max_attempts == 5
    assert config.min_wait == 2.0
    assert config.max_wait == 30.0
    assert config.multiplier == 3.0
    assert config.retry_on == (ValueError, TypeError)
    assert config.before_retry == custom_callback


def test_retry_config_validation():
    """Test RetryConfig validation."""
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        RetryConfig(max_attempts=0)

    with pytest.raises(ValueError, match="min_wait must be non-negative"):
        RetryConfig(min_wait=-1)

    with pytest.raises(
        ValueError, match="max_wait must be greater than or equal to min_wait"
    ):
        RetryConfig(min_wait=10, max_wait=5)

    with pytest.raises(ValueError, match="multiplier must be at least 1"):
        RetryConfig(multiplier=0.5)


def test_cache_config_defaults():
    """Test CacheConfig with default values."""
    config = CacheConfig()

    assert config.ttl == 300
    assert config.key_prefix == "travessera"
    assert config.include_headers is False
    assert config.include_body is True


def test_cache_config_validation():
    """Test CacheConfig validation."""
    with pytest.raises(ValueError, match="ttl must be non-negative"):
        CacheConfig(ttl=-1)


def test_monitor_config_defaults():
    """Test MonitorConfig with default values."""
    config = MonitorConfig()

    assert config.enabled is True
    assert config.include_request_body is False
    assert config.include_response_body is False
    assert config.sample_rate == 1.0


def test_monitor_config_validation():
    """Test MonitorConfig validation."""
    with pytest.raises(ValueError, match="sample_rate must be between 0.0 and 1.0"):
        MonitorConfig(sample_rate=1.5)

    with pytest.raises(ValueError, match="sample_rate must be between 0.0 and 1.0"):
        MonitorConfig(sample_rate=-0.1)


def test_tracer_config_defaults():
    """Test TracerConfig with default values."""
    config = TracerConfig()

    assert config.enabled is True
    assert config.service_name == "travessera"
    assert config.propagate_headers is True
    assert config.sample_rate == 1.0


def test_tracer_config_validation():
    """Test TracerConfig validation."""
    with pytest.raises(ValueError, match="sample_rate must be between 0.0 and 1.0"):
        TracerConfig(sample_rate=2.0)


def test_connection_config_defaults():
    """Test ConnectionConfig with default values."""
    config = ConnectionConfig()

    assert config.pool_connections == 10
    assert config.pool_maxsize == 10
    assert config.max_keepalive_connections == 20
    assert config.keepalive_expiry == 5.0


def test_connection_config_validation():
    """Test ConnectionConfig validation."""
    with pytest.raises(ValueError, match="pool_connections must be at least 1"):
        ConnectionConfig(pool_connections=0)

    with pytest.raises(ValueError, match="pool_maxsize must be at least 1"):
        ConnectionConfig(pool_maxsize=0)

    with pytest.raises(
        ValueError, match="max_keepalive_connections must be non-negative"
    ):
        ConnectionConfig(max_keepalive_connections=-1)

    with pytest.raises(ValueError, match="keepalive_expiry must be non-negative"):
        ConnectionConfig(keepalive_expiry=-1)
