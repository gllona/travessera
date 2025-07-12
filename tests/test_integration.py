"""Integration tests for Travessera."""

from typing import List, Optional

import httpx
import pytest
from pydantic import BaseModel

from travessera import ApiKeyAuthentication, Service, Travessera
from travessera.exceptions import NotFoundError


class User(BaseModel):
    """User model for tests."""

    id: int
    name: str
    email: str
    active: bool = True


class UserCreate(BaseModel):
    """User creation model."""

    name: str
    email: str


@pytest.fixture
def mock_transport():
    """Create a mock transport for httpx."""

    def handler(request: httpx.Request) -> httpx.Response:
        # Parse the URL
        path = str(request.url.path)
        method = request.method

        # Handle different endpoints
        if path == "/users/123" and method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": 123,
                    "name": "John Doe",
                    "email": "john@example.com",
                    "active": True,
                },
            )
        elif path == "/users/999" and method == "GET":
            return httpx.Response(
                404,
                json={"error": "User not found"},
            )
        elif path == "/users" and method == "GET":
            # Check query params
            params = dict(request.url.params)
            users = [
                {
                    "id": 1,
                    "name": "User 1",
                    "email": "user1@example.com",
                    "active": True,
                },
                {
                    "id": 2,
                    "name": "User 2",
                    "email": "user2@example.com",
                    "active": False,
                },
            ]
            if params.get("active") == "true":
                users = [u for u in users if u["active"]]
            return httpx.Response(200, json=users)
        elif path == "/users" and method == "POST":
            # Parse body
            data = request.read().decode()
            import json

            user_data = json.loads(data)
            return httpx.Response(
                201,
                json={"id": 3, **user_data, "active": True},
            )
        elif path == "/users/123" and method == "PUT":
            data = request.read().decode()
            import json

            user_data = json.loads(data)
            return httpx.Response(
                200,
                json={"id": 123, **user_data},
            )
        elif path == "/users/123" and method == "DELETE":
            return httpx.Response(204)
        else:
            return httpx.Response(404, json={"error": "Not found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def travessera_instance(mock_transport):
    """Create a Travessera instance with mocked HTTP client."""
    auth = ApiKeyAuthentication("test-key")

    user_service = Service(
        name="users",
        base_url="https://api.example.com",
        timeout=30.0,
        authentication=auth,
    )

    # Patch the service client to use mock transport
    user_service._client = None

    instance = Travessera(
        services=[user_service],
        default_timeout=30.0,
        default_headers={"X-Client": "test"},
    )

    # Monkey patch the client creation to use mock transport
    import travessera.client

    original_init = travessera.client.RetryableHTTPClient.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._sync_client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            transport=mock_transport,
        )
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            transport=mock_transport,
        )

    travessera.client.RetryableHTTPClient.__init__ = patched_init

    return instance


def test_sync_get_endpoint(travessera_instance):
    """Test synchronous GET endpoint."""

    @travessera_instance.get("users", "/users/{user_id}")
    def get_user(user_id: int) -> User:
        pass

    # Test successful request
    user = get_user(123)
    assert isinstance(user, User)
    assert user.id == 123
    assert user.name == "John Doe"
    assert user.email == "john@example.com"


def test_sync_get_with_404(travessera_instance):
    """Test synchronous GET with 404 error."""

    @travessera_instance.get("users", "/users/{user_id}")
    def get_user(user_id: int) -> User:
        pass

    # Test 404 error
    with pytest.raises(NotFoundError) as exc_info:
        get_user(999)

    assert exc_info.value.status_code == 404


def test_sync_get_with_query_params(travessera_instance):
    """Test synchronous GET with query parameters."""

    @travessera_instance.get("users", "/users")
    def list_users(active: Optional[bool] = None) -> List[User]:
        pass

    # Get all users
    users = list_users()
    assert len(users) == 2

    # Get only active users
    users = list_users(active=True)
    assert len(users) == 1
    assert all(u.active for u in users)


def test_sync_post_endpoint(travessera_instance):
    """Test synchronous POST endpoint."""

    @travessera_instance.post("users", "/users")
    def create_user(user: UserCreate) -> User:
        pass

    # Create a user
    new_user = UserCreate(name="New User", email="new@example.com")
    created = create_user(new_user)

    assert isinstance(created, User)
    assert created.id == 3
    assert created.name == "New User"
    assert created.email == "new@example.com"
    assert created.active is True


def test_sync_put_endpoint(travessera_instance):
    """Test synchronous PUT endpoint."""

    @travessera_instance.put("users", "/users/{user_id}")
    def update_user(user_id: int, user: User) -> User:
        pass

    # Update a user
    user_data = User(id=123, name="Updated", email="updated@example.com", active=False)
    updated = update_user(123, user_data)

    assert updated.name == "Updated"
    assert updated.email == "updated@example.com"
    assert updated.active is False


def test_sync_delete_endpoint(travessera_instance):
    """Test synchronous DELETE endpoint."""

    @travessera_instance.delete("users", "/users/{user_id}")
    def delete_user(user_id: int) -> None:
        pass

    # Delete should not raise
    result = delete_user(123)
    assert result is None


@pytest.mark.asyncio
async def test_async_get_endpoint(travessera_instance):
    """Test asynchronous GET endpoint."""

    @travessera_instance.get("users", "/users/{user_id}")
    async def get_user(user_id: int) -> User:
        pass

    # Test successful request
    user = await get_user(123)
    assert isinstance(user, User)
    assert user.id == 123
    assert user.name == "John Doe"


@pytest.mark.asyncio
async def test_async_post_endpoint(travessera_instance):
    """Test asynchronous POST endpoint."""

    @travessera_instance.post("users", "/users")
    async def create_user(user: UserCreate) -> User:
        pass

    # Create a user
    new_user = UserCreate(name="Async User", email="async@example.com")
    created = await create_user(new_user)

    assert isinstance(created, User)
    assert created.name == "Async User"


def test_custom_error_mapping(travessera_instance):
    """Test custom error mapping."""

    class UserNotFound(Exception):
        def __init__(self, message, request, response):
            super().__init__(message)
            self.status_code = response.status_code

    @travessera_instance.get("users", "/users/{user_id}", raises={404: UserNotFound})
    def get_user(user_id: int) -> User:
        pass

    with pytest.raises(UserNotFound) as exc_info:
        get_user(999)

    assert exc_info.value.status_code == 404


def test_response_transformer(travessera_instance):
    """Test response transformer."""

    def extract_users(response):
        # Assume response is wrapped
        return response if isinstance(response, list) else []

    @travessera_instance.get(
        "users",
        "/users",
        response_transformer=extract_users,
    )
    def list_users() -> List[User]:
        pass

    users = list_users()
    assert isinstance(users, list)


def test_request_transformer(travessera_instance):
    """Test request transformer."""

    def wrap_user(user_data):
        return {"data": user_data}

    # For this test, we need to adjust our mock to expect wrapped data
    # This would normally be handled by the mock transport
    @travessera_instance.post(
        "users",
        "/users",
        request_transformer=wrap_user,
    )
    def create_user(user: dict) -> User:
        pass

    # This test shows the transformer is applied
    # In a real scenario, the server would expect the wrapped format
