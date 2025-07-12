# Travessera

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-88%25-green)](tests/)

A Python library that abstracts microservice calls as local functions, handling all the complexities of HTTP communication behind the scenes.

## Key Features

- 🎯 **Simple Decorator API**: Call remote services like local functions
- 🔄 **Async/Sync Support**: Works with both async and sync functions
- 🏗️ **Type Safety**: Full Pydantic integration for request/response validation
- 🔁 **Smart Retries**: Configurable exponential backoff for transient failures
- 🎚️ **Flexible Configuration**: Three-level hierarchy (global → service → endpoint)
- 🔐 **Authentication**: Built-in API Key, Bearer Token, Basic Auth, and custom strategies
- 🚨 **Comprehensive Error Handling**: Detailed exception hierarchy with custom mapping
- 🔌 **Extensible**: Support for custom serializers, transformers, and authentication
- 🎭 **Request/Response Transformers**: Transform data before sending or after receiving
- 📊 **Connection Pooling**: Efficient connection management with httpx

## Installation

```bash
pip install travessera
```

## Quick Start

```python
from travessera import Travessera, Service, ApiKeyAuthentication
from pydantic import BaseModel
import os

# Define your models
class User(BaseModel):
    id: int
    name: str
    email: str

# Configure service
auth = ApiKeyAuthentication(api_key=os.getenv("API_KEY"))
user_service = Service(
    name="users",
    base_url="https://api.example.com",
    authentication=auth,
)

# Initialize Travessera
travessera = Travessera(services=[user_service])

# Define endpoints as simple functions
@travessera.get("users", "/users/{user_id}")
async def get_user(user_id: int) -> User:
    pass

# Use it like a normal function!
async def main():
    user = await get_user(123)
    print(f"Hello, {user.name}!")
```

## Advanced Usage

### Query Parameters

```python
@travessera.get("users", "/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    status: str = "active"
) -> List[User]:
    pass

# Calls: GET /users?page=2&limit=50&status=active
users = await list_users(page=2, limit=50)
```

### Dynamic Headers

```python
@travessera.get(
    "users",
    "/users/{id}",
    headers_factory=lambda params: {
        "X-Request-ID": str(uuid.uuid4()),
        "X-User-ID": str(params["id"]),
    }
)
async def get_user_with_tracking(id: int) -> User:
    pass
```

### Custom Retry Configuration

```python
from travessera import RetryConfig

@travessera.post(
    "orders",
    "/orders",
    retry_config=RetryConfig(
        max_attempts=5,
        min_wait=2.0,
        max_wait=30.0,
    )
)
async def create_order(order: OrderCreate) -> Order:
    pass
```

### Error Handling

```python
from travessera.exceptions import NotFoundError

try:
    user = await get_user(999)
except NotFoundError as e:
    print(f"User not found: {e}")
```

## Configuration Hierarchy

Travessera uses a three-level configuration hierarchy where settings cascade from global to specific:

```python
# Global level
travessera = Travessera(
    services=[...],
    default_timeout=30.0,
    default_headers={"X-API-Version": "1.0"},
)

# Service level
service = Service(
    name="api",
    base_url="https://api.example.com",
    timeout=60.0,  # Overrides global
)

# Endpoint level
@travessera.get(
    "api",
    "/endpoint",
    timeout=5.0,  # Overrides service
)
```

## Advanced Features

### Custom Error Mapping

Map HTTP status codes to custom exceptions:

```python
class UserNotFound(Exception):
    pass

@travessera.get(
    "users",
    "/users/{id}",
    raises={404: UserNotFound}
)
async def get_user_with_custom_errors(id: int) -> User:
    pass

try:
    user = await get_user_with_custom_errors(999)
except UserNotFound:
    print("User not found!")
```

### Request/Response Transformers

Transform data before sending or after receiving:

```python
# Transform request data
@travessera.post(
    "legacy",
    "/old-api/users",
    request_transformer=lambda data: {"payload": data, "version": "1.0"}
)
async def create_legacy_user(user: UserCreate) -> dict:
    pass

# Transform response data
@travessera.get(
    "legacy",
    "/old-api/users/{id}",
    response_transformer=lambda resp: resp["data"]["user"]
)
async def get_legacy_user(id: int) -> dict:
    pass
```

### Multiple Services

```python
# Configure multiple services
user_service = Service(name="users", base_url="https://users.api.com")
order_service = Service(name="orders", base_url="https://orders.api.com")
payment_service = Service(name="payments", base_url="https://payments.api.com")

travessera = Travessera(services=[user_service, order_service, payment_service])

# Use different services
@travessera.get("users", "/users/{id}")
async def get_user(id: int) -> User:
    pass

@travessera.post("orders", "/orders")
async def create_order(order: OrderCreate) -> Order:
    pass

@travessera.post("payments", "/payments")
async def process_payment(payment: PaymentRequest) -> PaymentResult:
    pass
```

## Authentication Methods

### API Key Authentication

```python
from travessera import ApiKeyAuthentication

auth = ApiKeyAuthentication(api_key="your-key", header_name="X-API-Key")
```

### Bearer Token Authentication

```python
from travessera import BearerTokenAuthentication

auth = BearerTokenAuthentication(token="your-bearer-token")
```

### Basic Authentication

```python
from travessera import BasicAuthentication

auth = BasicAuthentication(username="user", password="pass")
```

### Custom Authentication

```python
from travessera.authentication import Authentication

class CustomAuth(Authentication):
    def apply(self, request):
        request.headers["X-Custom-Auth"] = self.generate_token()
        return request
```

## Exception Hierarchy

```
TravesseraError
├── ServiceError
│   ├── ServiceNotFoundError
│   └── AuthenticationError
├── NetworkError
│   ├── ConnectionError
│   ├── TimeoutError
│   └── DNSError
├── HTTPError
│   ├── ClientError (4xx)
│   │   ├── BadRequestError (400)
│   │   ├── UnauthorizedError (401)
│   │   ├── ForbiddenError (403)
│   │   ├── NotFoundError (404)
│   │   └── ConflictError (409)
│   └── ServerError (5xx)
│       ├── InternalServerError (500)
│       ├── BadGatewayError (502)
│       └── ServiceUnavailableError (503)
└── ValidationError
    ├── RequestValidationError
    └── ResponseValidationError
```

## Complete Example

```python
from travessera import Travessera, Service, ApiKeyAuthentication
from travessera.models import RetryConfig
from travessera.exceptions import NotFoundError
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import os

# Models
class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True

class UserCreate(BaseModel):
    name: str
    email: str

# Configure service
auth = ApiKeyAuthentication(api_key=os.getenv("API_KEY"))

user_service = Service(
    name="users",
    base_url="https://api.example.com",
    timeout=30,
    authentication=auth,
    retry_config=RetryConfig(max_attempts=3),
)

travessera = Travessera(
    services=[user_service],
    default_headers={"X-Client": "my-app"}
)

# Define endpoints
@travessera.get("users", "/users/{user_id}")
async def get_user(user_id: int) -> User:
    """Get a user by ID."""
    pass

@travessera.post("users", "/users")
async def create_user(user: UserCreate) -> User:
    """Create a new user."""
    pass

@travessera.get("users", "/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None
) -> List[User]:
    """List users with pagination and filtering."""
    pass

@travessera.put("users", "/users/{user_id}")
async def update_user(user_id: int, user: User) -> User:
    """Update an existing user."""
    pass

@travessera.delete("users", "/users/{user_id}")
async def delete_user(user_id: int) -> None:
    """Delete a user."""
    pass

# Usage
async def main():
    try:
        # Create a user
        new_user = await create_user(UserCreate(
            name="Jane Doe",
            email="jane@example.com"
        ))
        print(f"Created user: {new_user.id}")
        
        # Get the user
        user = await get_user(new_user.id)
        print(f"Retrieved: {user.name}")
        
        # List all active users
        users = await list_users(status="active")
        print(f"Active users: {len(users)}")
        
        # Update the user
        user.email = "jane.doe@example.com"
        updated = await update_user(user.id, user)
        print(f"Updated email: {updated.email}")
        
        # Delete the user
        await delete_user(user.id)
        print("User deleted")
        
    except NotFoundError as e:
        print(f"User not found: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing

When testing code that uses Travessera, you can mock the HTTP transport:

```python
import httpx
import pytest
from travessera import Travessera, Service

@pytest.fixture
def mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/123":
            return httpx.Response(
                200,
                json={"id": 123, "name": "Test User", "email": "test@example.com"}
            )
        return httpx.Response(404)
    
    return httpx.MockTransport(handler)

@pytest.fixture
def travessera_test(mock_transport):
    # Configure service with mock transport
    # See tests/test_integration.py for complete example
    pass
```

## Documentation

For more detailed documentation, see the [docs/](docs/) directory:
- [Design Document](docs/DESIGN.md) - Architecture and design decisions
- [API Reference](docs/API.md) - Complete API documentation
- [Examples](docs/examples/) - More usage examples

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.