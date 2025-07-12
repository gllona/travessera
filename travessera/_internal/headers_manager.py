"""
Headers management for Travessera.

This module handles static and dynamic headers, merging them
appropriately for each request.
"""

from typing import Any, Dict, Optional

from travessera.types import Headers, HeadersFactory


class HeadersManager:
    """
    Manages headers for HTTP requests.

    This class handles:
    - Static headers from configuration
    - Dynamic headers from factory functions
    - Merging headers from different sources
    """

    def __init__(
        self,
        static_headers: Optional[Headers] = None,
        headers_factory: Optional[HeadersFactory] = None,
    ) -> None:
        """
        Initialize the headers manager.

        Args:
            static_headers: Static headers to include with all requests
            headers_factory: Function to generate dynamic headers
        """
        self.static_headers = static_headers or {}
        self.headers_factory = headers_factory

    def get_headers(self, request_params: Optional[Dict[str, Any]] = None) -> Headers:
        """
        Get the complete headers for a request.

        This merges static headers with dynamic headers generated
        by the factory function.

        Args:
            request_params: Parameters available to the headers factory
                           (e.g., path parameters, query parameters)

        Returns:
            The complete headers dictionary
        """
        # Start with static headers
        headers = self.static_headers.copy()

        # Add dynamic headers if factory is provided
        if self.headers_factory and request_params:
            dynamic_headers = self.headers_factory(request_params)
            headers.update(dynamic_headers)

        return headers

    def merge_with(self, additional_headers: Optional[Headers]) -> Headers:
        """
        Merge current headers with additional headers.

        Args:
            additional_headers: Additional headers to merge

        Returns:
            Merged headers dictionary
        """
        if not additional_headers:
            return self.static_headers.copy()

        headers = self.static_headers.copy()
        headers.update(additional_headers)
        return headers

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

    def with_content_type(self, content_type: str) -> Headers:
        """
        Get headers with a specific content type.

        Args:
            content_type: The content type to set

        Returns:
            Headers with Content-Type set
        """
        headers = self.static_headers.copy()
        headers["Content-Type"] = content_type
        return headers

    def with_accept(self, accept: str) -> Headers:
        """
        Get headers with a specific Accept header.

        Args:
            accept: The Accept header value

        Returns:
            Headers with Accept set
        """
        headers = self.static_headers.copy()
        headers["Accept"] = accept
        return headers
