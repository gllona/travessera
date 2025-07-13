"""
HTTP client wrapper for Travessera.

This module provides an abstraction over httpx to handle both sync and async
HTTP requests with connection pooling, timeouts, and error handling.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx

from travessera.exceptions import (
    ConnectionError as TravesseraConnectionError,
)
from travessera.exceptions import (
    DNSError,
    NetworkError,
    ServerError,
)
from travessera.exceptions import (
    TimeoutError as TravesseraTimeoutError,
)
from travessera.models import ConnectionConfig, RetryConfig
from travessera.retry import should_retry_status_code
from travessera.types import Headers


class HTTPClient:
    """
    Wrapper around httpx for making HTTP requests.

    This class provides both sync and async interfaces with connection
    pooling, retry logic, and proper error handling.
    """

    def __init__(
        self,
        base_url: str | None = None,
        headers: Headers | None = None,
        timeout: float = 30.0,
        connection_config: ConnectionConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for all requests
            headers: Default headers to include with all requests
            timeout: Default timeout in seconds
            connection_config: Connection pool configuration
            retry_config: Retry behavior configuration
        """
        self.base_url = base_url
        self.headers = headers or {}
        self.timeout = timeout
        self.connection_config = connection_config or ConnectionConfig()
        self.retry_config = retry_config or RetryConfig()

        # Create transport with connection pooling
        limits = httpx.Limits(
            max_connections=self.connection_config.pool_maxsize,
            max_keepalive_connections=self.connection_config.max_keepalive_connections,
            keepalive_expiry=self.connection_config.keepalive_expiry,
        )

        # Initialize clients (created lazily)
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._limits = limits

    @property
    def sync_client(self) -> httpx.Client:
        """Get or create the synchronous HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                limits=self._limits,
                follow_redirects=True,
            )
        return self._sync_client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create the asynchronous HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                limits=self._limits,
                follow_redirects=True,
            )
        return self._async_client

    def close(self) -> None:
        """Close all HTTP clients and release resources."""
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None
        if self._async_client is not None:
            # If we're in an async context, we need to handle this differently
            try:
                loop = asyncio.get_running_loop()
                if loop and not loop.is_closed():
                    loop.create_task(self._async_client.aclose())
                else:
                    # Loop is closed, skip async cleanup
                    pass
            except RuntimeError:
                # No running loop, we're in sync context
                try:
                    asyncio.run(self._async_client.aclose())
                except RuntimeError:
                    # Event loop is gone during shutdown, skip cleanup
                    import warnings

                    warnings.warn(
                        "HTTPClient async cleanup skipped: event loop unavailable",
                        ResourceWarning,
                        stacklevel=2,
                    )
            self._async_client = None

    async def aclose(self) -> None:
        """Async version of close."""
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self) -> "HTTPClient":
        """Enter sync context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit sync context manager."""
        self.close()

    async def __aenter__(self) -> "HTTPClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.aclose()

    def __del__(self) -> None:
        """Cleanup clients on deletion."""
        try:
            # Only attempt cleanup if clients exist
            if hasattr(self, "_sync_client") and self._sync_client:
                self._sync_client.close()
            # For async client, just warn if not properly cleaned up
            if hasattr(self, "_async_client") and self._async_client:
                import warnings

                warnings.warn(
                    "HTTPClient was not properly closed. "
                    "Use 'with client:' or 'async with client:' or call 'await client.aclose()'",
                    ResourceWarning,
                    stacklevel=2,
                )
        except Exception:
            # Ignore all errors during cleanup in __del__
            # This prevents the AsyncLibraryNotFoundError during shutdown
            pass

    @contextmanager
    def _handle_request_errors(self) -> Iterator[None]:
        """Context manager to handle common HTTP errors."""
        try:
            yield
        except httpx.ConnectError as e:
            # DNS resolution failures
            if "Name or service not known" in str(
                e
            ) or "nodename nor servname provided" in str(e):
                raise DNSError(str(e.request.url).split("/")[2].split(":")[0]) from e
            raise TravesseraConnectionError(str(e.request.url), e) from e
        except httpx.TimeoutException as e:
            raise TravesseraTimeoutError(str(e.request.url), self.timeout) from e
        except httpx.NetworkError as e:
            raise TravesseraConnectionError(str(e.request.url), e) from e

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: Any | None = None,
        headers: Headers | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make a synchronous HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL path (will be joined with base_url if relative)
            params: Query parameters
            json: JSON data to send
            data: Form data to send
            headers: Additional headers
            timeout: Override default timeout
            **kwargs: Additional arguments passed to httpx

        Returns:
            The HTTP response

        Raises:
            Various TravesseraError subclasses for different error conditions
        """
        with self._handle_request_errors():
            # Merge headers
            request_headers = {**self.headers, **(headers or {})}

            # Use provided timeout or default
            request_timeout = timeout if timeout is not None else self.timeout

            # Make the request
            response = self.sync_client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=request_headers,
                timeout=request_timeout,
                **kwargs,
            )

            # Don't check for HTTP errors here - let the response handler do it
            return response

    async def arequest(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: Any | None = None,
        headers: Headers | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an asynchronous HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL path (will be joined with base_url if relative)
            params: Query parameters
            json: JSON data to send
            data: Form data to send
            headers: Additional headers
            timeout: Override default timeout
            **kwargs: Additional arguments passed to httpx

        Returns:
            The HTTP response

        Raises:
            Various TravesseraError subclasses for different error conditions
        """
        with self._handle_request_errors():
            # Merge headers
            request_headers = {**self.headers, **(headers or {})}

            # Use provided timeout or default
            request_timeout = timeout if timeout is not None else self.timeout

            # Make the request
            response = await self.async_client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=request_headers,
                timeout=request_timeout,
                **kwargs,
            )

            # Don't check for HTTP errors here - let the response handler do it
            return response

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a synchronous GET request."""
        return self.request("GET", url, **kwargs)

    async def aget(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make an asynchronous GET request."""
        return await self.arequest("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a synchronous POST request."""
        return self.request("POST", url, **kwargs)

    async def apost(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make an asynchronous POST request."""
        return await self.arequest("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a synchronous PUT request."""
        return self.request("PUT", url, **kwargs)

    async def aput(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make an asynchronous PUT request."""
        return await self.arequest("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a synchronous DELETE request."""
        return self.request("DELETE", url, **kwargs)

    async def adelete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make an asynchronous DELETE request."""
        return await self.arequest("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a synchronous PATCH request."""
        return self.request("PATCH", url, **kwargs)

    async def apatch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make an asynchronous PATCH request."""
        return await self.arequest("PATCH", url, **kwargs)


class RetryableHTTPClient(HTTPClient):
    """HTTP client with automatic retry logic."""

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make a request with retry logic."""

        def make_request() -> httpx.Response:
            return super(RetryableHTTPClient, self).request(method, url, **kwargs)

        # Check if we should retry this request
        if self.retry_config and self.retry_config.max_attempts > 1:
            # Create a wrapper that checks status codes
            def request_with_status_check() -> httpx.Response:
                response = make_request()
                # Only retry on specific status codes, don't raise for all errors
                if should_retry_status_code(response.status_code):
                    # Create a temporary error to trigger retry
                    if 500 <= response.status_code < 600:
                        raise ServerError(
                            f"Server error: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    else:
                        raise NetworkError(f"Retryable error: {response.status_code}")
                return response

            # Apply retry logic
            from tenacity import (
                retry,
                retry_if_exception,
                stop_after_attempt,
                wait_exponential,
            )

            retry_decorator = retry(
                stop=stop_after_attempt(self.retry_config.max_attempts),
                wait=wait_exponential(
                    multiplier=self.retry_config.multiplier,
                    min=self.retry_config.min_wait,
                    max=self.retry_config.max_wait,
                ),
                retry=retry_if_exception(
                    lambda e: isinstance(e, self.retry_config.retry_on)
                    or (
                        hasattr(e, "response")
                        and should_retry_status_code(e.response.status_code)
                    )
                ),
                reraise=True,
            )

            return retry_decorator(request_with_status_check)()
        else:
            return make_request()

    async def arequest(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make an async request with retry logic."""

        async def make_request() -> httpx.Response:
            return await super(RetryableHTTPClient, self).arequest(
                method, url, **kwargs
            )

        # Check if we should retry this request
        if self.retry_config and self.retry_config.max_attempts > 1:
            # Create a wrapper that checks status codes
            async def request_with_status_check() -> httpx.Response:
                response = await make_request()
                # Only retry on specific status codes, don't raise for all errors
                if should_retry_status_code(response.status_code):
                    # Create a temporary error to trigger retry
                    if 500 <= response.status_code < 600:
                        raise ServerError(
                            f"Server error: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    else:
                        raise NetworkError(f"Retryable error: {response.status_code}")
                return response

            # Apply retry logic
            from tenacity import (
                retry,
                retry_if_exception,
                stop_after_attempt,
                wait_exponential,
            )

            retry_decorator = retry(
                stop=stop_after_attempt(self.retry_config.max_attempts),
                wait=wait_exponential(
                    multiplier=self.retry_config.multiplier,
                    min=self.retry_config.min_wait,
                    max=self.retry_config.max_wait,
                ),
                retry=retry_if_exception(
                    lambda e: isinstance(e, self.retry_config.retry_on)
                    or (
                        hasattr(e, "response")
                        and should_retry_status_code(e.response.status_code)
                    )
                ),
                reraise=True,
            )

            return await retry_decorator(request_with_status_check)()
        else:
            return await make_request()
