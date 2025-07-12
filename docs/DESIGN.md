# Travessera Design Document

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [API Design](#api-design)
5. [Configuration Hierarchy](#configuration-hierarchy)
6. [Exception Handling](#exception-handling)
7. [Extensibility](#extensibility)
8. [Dependencies](#dependencies)
9. [Usage Examples](#usage-examples)
10. [Implementation Plan](#implementation-plan)

## Overview

Travessera is a Python library that provides an abstraction layer for microservices communication. It allows developers to call external microservices as if they were local functions, handling all the complexities of HTTP communication, serialization, error handling, and retries behind the scenes.

### Key Features
- Decorator-based API for defining service endpoints
- Support for both synchronous and asynchronous calls
- Automatic serialization/deserialization with Pydantic
- Configurable retry logic with exponential backoff
- Three-level configuration hierarchy
- Comprehensive exception handling
- Extensible architecture for future protocols

### Design Philosophy
- **Developer Experience First**: Make microservice calls as simple as local function calls
- **Type Safety**: Leverage Python's type hints and Pydantic for validation
- **Flexibility**: Support various configuration levels and customization options
- **Extensibility**: Design for future support of different protocols and serialization formats
- **Performance**: Minimize overhead while maintaining functionality

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Code                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  @travessera.get("service", "/endpoint/{id}")       │  │
│  │  async def get_resource(id: int) -> Resource:       │  │
│  │      pass                                            │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────┐
│                     Travessera Library                       │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Decorators    │  │ Config       │  │ Serializers  │  │
│  │   @get @post    │  │ Resolver     │  │ JSON/XML     │  │
│  └────────┬────────┘  └──────┬───────┘  └──────┬───────┘  │
│           │                   │                  │          │
│  ┌────────▼─────────────────▼────────────────▼────────┐   │
│  │              Request/Response Pipeline              │   │
│  │  - Parameter parsing                                │   │
│  │  - Request building                                 │   │
│  │  - Response handling                                │   │
│  └────────────────────────┬───────────────────────────┘   │
│                           │                                 │
│  ┌────────────────────────▼───────────────────────────┐   │
│  │                 HTTP Client Layer                   │   │
│  │  - httpx client (sync/async)                       │   │
│  │  - Retry logic (tenacity)                          │   │
│  │  - Connection pooling                              │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure

```
travessera/
├── __init__.py                    # Public API exports
├── core.py                        # Travessera and Service classes
├── decorators.py                  # Endpoint decorator implementations
├── authentication.py              # Authentication strategies
├── exceptions.py                  # Exception hierarchy
├── client.py                      # HTTP client abstraction
├── models.py                      # Pydantic models and config classes
├── types.py                       # Type hints and protocols
├── retry.py                       # Retry configuration and logic
├── serializers/                   # Extensible serialization
│   ├── __init__.py
│   ├── base.py                   # Abstract serializer interface
│   ├── json.py                   # JSON serializer (default)
│   └── xml.py                    # XML serializer (future)
└── _internal/
    ├── __init__.py
    ├── config_resolver.py         # Configuration hierarchy resolution
    ├── request_builder.py         # Request construction logic
    ├── response_handler.py        # Response processing
    ├── parameter_parser.py        # Function signature parsing
    ├── endpoint_registry.py       # Endpoint registration
    └── headers_manager.py         # Dynamic header handling
```

## Core Components

### 1. Travessera Class

The main orchestrator that manages services and provides decorators.

```python
class Travessera:
    def __init__(
        self,
        services: List[Service],
        default_timeout: float = 30.0,
        default_headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[RetryConfig] = None,
        monitor: Optional[Monitor] = None,
        tracer: Optional[Tracer] = None,
    ):
        """Initialize Travessera with services and global defaults."""
```

### 2. Service Class

Configuration for individual microservices.

```python
class Service:
    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: Optional[float] = None,
        authentication: Optional[Authentication] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[RetryConfig] = None,
        cache: Optional[Cache] = None,
    ):
        """Configure a microservice connection."""
```

### 3. Endpoint Decorators

Transform regular functions into HTTP calls.

```python
# Method-specific decorators
@travessera.get(service="users", endpoint="/users/{id}")
@travessera.post(service="users", endpoint="/users")
@travessera.put(service="users", endpoint="/users/{id}")
@travessera.delete(service="users", endpoint="/users/{id}")

# Generic decorator
@travessera.endpoint(
    service="users",
    endpoint="/users/{id}",
    method="PATCH",
    timeout=10.0,
)
```

### 4. Authentication

Pluggable authentication strategies.

```python
class Authentication(Protocol):
    """Base protocol for authentication strategies."""
    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply authentication to the request."""

class ApiKeyAuthentication(Authentication):
    """API key authentication in headers."""
    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name
```

### 5. Serializers

Extensible serialization system.

```python
class Serializer(Protocol):
    """Protocol for serializers."""
    content_type: str
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
    
    def deserialize(self, data: bytes, target_type: Type[T]) -> T:
        """Deserialize bytes to target type."""

class JSONSerializer(Serializer):
    """JSON serialization using Pydantic."""
    content_type = "application/json"
```

### 6. Retry Configuration

Configurable retry logic using tenacity.

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 10.0
    multiplier: float = 2.0
    retry_on: Tuple[Type[Exception], ...] = (NetworkError, ServerError)
    before_retry: Optional[Callable] = None
```

## API Design

### Decorator API

The library provides both generic and method-specific decorators:

```python
# Method-specific decorators (recommended)
@travessera.get("service_name", "/path/{param}")
@travessera.post("service_name", "/path")
@travessera.put("service_name", "/path/{id}")
@travessera.delete("service_name", "/path/{id}")

# Generic decorator
@travessera.endpoint(
    service="service_name",
    endpoint="/path",
    method="GET",
    # Optional parameters
    timeout=30.0,
    headers={"X-Custom": "value"},
    headers_factory=lambda params: {"X-Dynamic": str(params["id"])},
    retry_config=RetryConfig(max_attempts=5),
    request_transformer=lambda data: {"wrapped": data},
    response_transformer=lambda resp: resp["data"],
    raises={404: ResourceNotFound, 403: Forbidden},
)
```

### Function Signature Handling

The decorators analyze function signatures to determine:

1. **Path parameters**: Match placeholders in the endpoint path
2. **Query parameters**: Function arguments not in the path
3. **Request body**: For POST/PUT/PATCH methods

```python
# Path parameters
@travessera.get("users", "/users/{user_id}/posts/{post_id}")
async def get_post(user_id: int, post_id: int) -> Post:
    pass

# Query parameters (implicit)
@travessera.get("users", "/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None
) -> List[User]:
    pass
# Results in: /users?page=1&limit=20&status=active

# Query parameters (explicit)
@travessera.get("users", "/users?status={status}")
async def get_users_by_status(status: str, limit: int = 10) -> List[User]:
    pass

# Request body
@travessera.post("users", "/users")
async def create_user(user: UserCreate) -> User:
    pass
```

### Type Safety with Pydantic

Automatic serialization and deserialization with Pydantic models:

```python
from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

@travessera.get("users", "/users/{id}")
async def get_user(id: int) -> User:
    pass  # Returns validated User instance

@travessera.post("users", "/users")
async def create_user(user: UserCreate) -> User:
    pass  # user is automatically serialized to JSON
```

## Configuration Hierarchy

The library implements a three-level configuration hierarchy where settings cascade from global to specific:

```
Travessera (global) → Service (service-level) → Decorator (endpoint-level)
```

### Configurable Parameters

- `timeout`: Request timeout in seconds
- `headers`: Static HTTP headers
- `retry_config`: Retry behavior configuration
- `authentication`: Authentication strategy
- `request_transformer`: Request data transformation
- `response_transformer`: Response data transformation

### Example

```python
# Global level
travessera = Travessera(
    services=[user_service, order_service],
    default_timeout=30.0,
    default_headers={"X-API-Version": "1.0"},
    retry_config=RetryConfig(max_attempts=3),
)

# Service level
user_service = Service(
    name="users",
    base_url="https://api.users.example.com",
    timeout=60.0,  # Overrides global 30s
    headers={"X-Service": "users"},
)

# Endpoint level
@travessera.get(
    "users",
    "/users/{id}",
    timeout=5.0,  # Overrides service 60s
    headers={"X-Endpoint": "get-user"},
)
async def get_user(id: int) -> User:
    pass
```

### Configuration Resolution

The `ConfigResolver` merges configurations in order:

```python
def resolve_config(travessera_config, service_config, endpoint_config):
    # Start with travessera defaults
    config = travessera_config.copy()
    
    # Override with service settings
    config.update(service_config)
    
    # Override with endpoint settings
    config.update(endpoint_config)
    
    # Merge headers (don't replace, combine)
    config.headers = {
        **travessera_config.headers,
        **service_config.headers,
        **endpoint_config.headers,
    }
    
    return config
```

## Exception Handling

### Exception Hierarchy

```
TravesseraError(Exception)
├── ServiceError
│   ├── ServiceNotFoundError      # Service not registered
│   ├── EndpointNotFoundError     # Endpoint configuration error
│   └── AuthenticationError       # Authentication failure
├── NetworkError
│   ├── ConnectionError           # Cannot connect to service
│   ├── TimeoutError             # Request timed out
│   └── DNSError                 # DNS resolution failed
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
    ├── RequestValidationError    # Invalid request data
    └── ResponseValidationError   # Invalid response format
```

### Custom Exception Mapping

Map HTTP status codes to custom exceptions:

```python
@travessera.get(
    "users",
    "/users/{id}",
    raises={
        404: UserNotFoundError,
        403: InsufficientPermissionsError,
    }
)
async def get_user(id: int) -> User:
    pass
```

### Error Context

Exceptions include context for debugging:

```python
try:
    user = await get_user(123)
except HTTPError as e:
    print(f"Status: {e.status_code}")
    print(f"URL: {e.request.url}")
    print(f"Response: {e.response.text}")
    print(f"Headers: {e.response.headers}")
```

## Extensibility

### Serializer Protocol

Support for different content types:

```python
class XMLSerializer(Serializer):
    content_type = "application/xml"
    
    def serialize(self, data: Any) -> bytes:
        # XML serialization logic
        pass
    
    def deserialize(self, data: bytes, target_type: Type[T]) -> T:
        # XML deserialization logic
        pass

# Usage
@travessera.post(
    "legacy",
    "/soap/endpoint",
    serializer=XMLSerializer(),
)
async def call_soap_service(request: SOAPRequest) -> SOAPResponse:
    pass
```

### Authentication Strategies

Easy to add new authentication methods:

```python
class BearerTokenAuthentication(Authentication):
    def __init__(self, token: str):
        self.token = token
    
    def apply(self, request: httpx.Request) -> httpx.Request:
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request

class OAuth2Authentication(Authentication):
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    def apply(self, request: httpx.Request) -> httpx.Request:
        # OAuth2 flow implementation
        pass
```

### Future Extensions

The architecture supports future additions:

1. **Protocol Support**: gRPC, GraphQL, WebSocket
2. **Caching**: Redis, Memcached integration
3. **Monitoring**: Prometheus, OpenTelemetry
4. **Circuit Breakers**: Advanced failure handling
5. **Service Mesh**: Istio, Linkerd integration

## Dependencies

### Core Dependencies

1. **httpx** (>=0.25.0)
   - Modern HTTP client with sync/async support
   - Better than requests for async, better than aiohttp for sync
   - Excellent timeout and connection pooling

2. **pydantic** (>=2.0)
   - Data validation and serialization
   - Type safety and automatic documentation
   - JSON Schema generation

3. **tenacity** (>=8.2.0)
   - Sophisticated retry logic
   - Works well with httpx
   - Configurable backoff strategies

4. **typing-extensions** (>=4.8.0)
   - Backports of typing features
   - Protocol support for older Python versions

### Development Dependencies

- **pytest** (>=7.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **pytest-httpx** (>=0.28.0): httpx mocking
- **black** (>=23.0): Code formatting
- **mypy** (>=1.0): Static type checking
- **ruff** (>=0.1.0): Fast linting
- **pytest-cov** (>=4.0): Coverage reporting

## Usage Examples

### Basic Usage

```python
from travessera import Travessera, Service, ApiKeyAuthentication
from pydantic import BaseModel
from typing import List, Optional
import os

# Define models
class User(BaseModel):
    id: int
    name: str
    email: str

class UserCreate(BaseModel):
    name: str
    email: str

# Configure services
auth = ApiKeyAuthentication(api_key=os.getenv("API_KEY"))

user_service = Service(
    name="users",
    base_url="https://api.users.example.com",
    timeout=30,
    authentication=auth,
)

# Initialize Travessera
travessera = Travessera(services=[user_service])

# Define endpoints
@travessera.get("users", "/users/{user_id}")
async def get_user(user_id: int) -> User:
    pass

@travessera.post("users", "/users")
async def create_user(user: UserCreate) -> User:
    pass

@travessera.get("users", "/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None
) -> List[User]:
    pass

# Use the functions
async def main():
    # Get a user
    user = await get_user(123)
    print(f"User: {user.name}")
    
    # Create a user
    new_user = await create_user(UserCreate(
        name="John Doe",
        email="john@example.com"
    ))
    print(f"Created: {new_user.id}")
    
    # List users
    users = await list_users(page=2, status="active")
    print(f"Found {len(users)} users")
```

### Advanced Features

```python
# Dynamic headers
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

# Custom retry configuration
@travessera.post(
    "orders",
    "/orders",
    retry_config=RetryConfig(
        max_attempts=5,
        min_wait=2.0,
        max_wait=30.0,
        retry_on=(NetworkError, ServiceUnavailableError),
    )
)
async def create_order(order: OrderCreate) -> Order:
    pass

# Response transformation
@travessera.get(
    "legacy",
    "/old-api/users/{id}",
    response_transformer=lambda resp: resp["data"]["user"],
)
async def get_legacy_user(id: int) -> dict:
    pass

# Custom exception mapping
class UserNotFound(Exception):
    pass

@travessera.get(
    "users",
    "/users/{id}",
    raises={404: UserNotFound},
)
async def get_user_or_fail(id: int) -> User:
    pass
```

### Synchronous Usage

```python
# All decorators work with sync functions too
@travessera.get("users", "/users/{id}")
def get_user_sync(id: int) -> User:
    pass

def main():
    user = get_user_sync(123)
    print(user.name)
```

## Implementation Plan

### Phase 0: Documentation (1 day) ✓
- Create comprehensive design documentation
- Define architecture and API specifications
- Document all design decisions

### Phase 1: Foundation (2 days)
1. Set up project structure
   - Create pyproject.toml with dependencies
   - Set up package structure
   - Configure development tools

2. Implement core types and exceptions
   - Exception hierarchy in `exceptions.py`
   - Type definitions in `types.py`
   - Protocol definitions

3. Create authentication framework
   - Authentication protocol
   - ApiKeyAuthentication implementation
   - Future authentication hooks

4. Define configuration models
   - Pydantic models for configuration
   - RetryConfig dataclass
   - Service and Travessera configs

### Phase 2: Core Infrastructure (3 days)
1. Build configuration resolver
   - Three-level hierarchy logic
   - Configuration merging
   - Validation

2. Create serializer architecture
   - Serializer protocol
   - JSON serializer with Pydantic
   - Extension points for XML/others

3. Implement retry mechanism
   - Tenacity integration
   - Exponential backoff
   - Configurable retry conditions

4. Build headers manager
   - Static headers merging
   - Dynamic headers factory
   - Header precedence

5. Create HTTP client wrapper
   - httpx client management
   - Connection pooling
   - Timeout handling

### Phase 3: Request/Response Pipeline (3 days)
1. Parameter parser
   - Function signature inspection
   - Path parameter extraction
   - Query parameter detection

2. Request builder
   - URL construction
   - Query string building
   - Request body serialization

3. Response handler
   - Status code checking
   - Deserialization
   - Error mapping

4. Validation layer
   - Request validation
   - Response validation
   - Type checking

5. Transformer pipeline
   - Request transformers
   - Response transformers
   - Chaining logic

### Phase 4: Decorator Implementation (2 days)
1. Base decorator logic
   - Function wrapping
   - Async/sync detection
   - Context preservation

2. Method-specific decorators
   - @get, @post, @put, @delete
   - Parameter handling
   - Method-specific logic

3. Endpoint registration
   - Service discovery
   - Endpoint storage
   - Validation

4. Integration
   - Connect all components
   - Error handling
   - Logging hooks

### Phase 5: Testing & Distribution (2 days)
1. Unit tests
   - Component testing
   - Mock HTTP responses
   - Edge cases

2. Integration tests
   - End-to-end scenarios
   - Real-like service mocking
   - Performance tests

3. Documentation
   - API documentation
   - Usage examples
   - Migration guides

4. Packaging
   - PyPI configuration
   - GitHub Actions CI/CD
   - Release automation

### Milestones
- **Day 1**: Design documentation complete
- **Day 3**: Core types and exceptions working
- **Day 6**: HTTP client and retry logic functional
- **Day 9**: Full request/response pipeline
- **Day 11**: Decorators working end-to-end
- **Day 13**: Tests passing, ready for release

### Success Criteria
1. All decorators work for both sync and async functions
2. Type safety with Pydantic models
3. Configurable retry with exponential backoff
4. Three-level configuration hierarchy
5. Comprehensive error handling
6. 90%+ test coverage
7. Documentation and examples
8. Published to PyPI