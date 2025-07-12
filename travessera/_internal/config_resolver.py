"""
Configuration resolver for Travessera.

This module implements the three-level configuration hierarchy where
settings cascade from global (Travessera) to service to endpoint level.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type

from travessera.models import RetryConfig
from travessera.types import Headers, HeadersFactory, Serializer


@dataclass
class ResolvedConfig:
    """
    Resolved configuration after merging all levels.

    This represents the final configuration that will be used
    for a specific endpoint call.
    """

    # Connection settings
    base_url: str
    timeout: float

    # Headers
    headers: Headers
    headers_factory: Optional[HeadersFactory]

    # Authentication (handled separately by Service)
    # authentication: Optional[Authentication]

    # Retry configuration
    retry_config: Optional[RetryConfig]

    # Serialization
    serializer: Serializer

    # Transformers
    request_transformer: Optional[Callable[[Any], Any]]
    response_transformer: Optional[Callable[[Any], Any]]

    # Error mapping
    raises: Optional[Dict[int, Type[Exception]]]


class ConfigResolver:
    """
    Resolves configuration by merging three levels:
    1. Travessera (global defaults)
    2. Service (service-specific)
    3. Endpoint (endpoint-specific)

    Endpoint config overrides Service config, which overrides Travessera config.
    Headers are merged (not replaced) across levels.
    """

    @staticmethod
    def merge_headers(*header_dicts: Optional[Headers]) -> Headers:
        """
        Merge multiple header dictionaries.

        Later dictionaries override earlier ones.

        Args:
            *header_dicts: Header dictionaries to merge

        Returns:
            Merged headers
        """
        result = {}
        for headers in header_dicts:
            if headers:
                result.update(headers)
        return result

    @staticmethod
    def resolve(
        travessera_config: Dict[str, Any],
        service_config: Dict[str, Any],
        endpoint_config: Dict[str, Any],
        default_serializer: Serializer,
    ) -> ResolvedConfig:
        """
        Resolve configuration by merging all three levels.

        Args:
            travessera_config: Global Travessera configuration
            service_config: Service-level configuration
            endpoint_config: Endpoint-specific configuration
            default_serializer: Default serializer to use

        Returns:
            Resolved configuration
        """
        # Start with defaults and override in order

        # Base URL (must come from service)
        base_url = service_config.get("base_url", "")
        if not base_url:
            raise ValueError("Service must have a base_url")

        # Timeout - cascade through levels
        timeout = endpoint_config.get("timeout")
        if timeout is None:
            timeout = service_config.get("timeout")
        if timeout is None:
            timeout = travessera_config.get("default_timeout", 30.0)

        # Headers - merge all levels
        headers = ConfigResolver.merge_headers(
            travessera_config.get("default_headers"),
            service_config.get("headers"),
            endpoint_config.get("headers"),
        )

        # Headers factory - endpoint only
        headers_factory = endpoint_config.get("headers_factory")

        # Retry config - cascade through levels
        retry_config = endpoint_config.get("retry_config")
        if retry_config is None:
            retry_config = service_config.get("retry_config")
        if retry_config is None:
            retry_config = travessera_config.get("retry_config")

        # Serializer - endpoint or default
        serializer = endpoint_config.get("serializer", default_serializer)

        # Transformers - endpoint only
        request_transformer = endpoint_config.get("request_transformer")
        response_transformer = endpoint_config.get("response_transformer")

        # Error mapping - endpoint only
        raises = endpoint_config.get("raises")

        return ResolvedConfig(
            base_url=base_url,
            timeout=timeout,
            headers=headers,
            headers_factory=headers_factory,
            retry_config=retry_config,
            serializer=serializer,
            request_transformer=request_transformer,
            response_transformer=response_transformer,
            raises=raises,
        )

    @staticmethod
    def merge_configs(
        base: Dict[str, Any],
        override: Dict[str, Any],
        merge_keys: Optional[set[str]] = None,
    ) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Configuration to override with
            merge_keys: Keys that should be merged instead of replaced

        Returns:
            Merged configuration
        """
        merge_keys = merge_keys or {"headers"}
        result = base.copy()

        for key, value in override.items():
            if value is not None:
                if key in merge_keys and key in result:
                    # Merge these keys
                    if isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = {**result[key], **value}
                    else:
                        result[key] = value
                else:
                    # Replace
                    result[key] = value

        return result
