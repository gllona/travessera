# Travessera Development Guide for Claude

This document provides essential information for Claude instances working on the Travessera codebase.

## Project Overview

Travessera is a Python library that abstracts microservice calls as local functions using decorators. It transforms functions into HTTP calls, handling serialization, authentication, retries, and error mapping transparently.

**Key Concept**: Functions decorated with `@travessera.get()`, `@travessera.post()`, etc. become HTTP API calls automatically.

## Essential Commands

### Development Setup
```bash
# Create virtual environment in .venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Before Every Commit
```bash
# Run tests with coverage
pytest tests/ -v --cov=travessera --cov-report=term-missing

# Format code
black .

# Lint code
ruff check . --fix

# Type check (optional - CI allows failures)
mypy travessera --config-file mypy.ini
```

### Build and Distribution
```bash
# Build package
python -m build

# Check package validity
pip install twine
twine check dist/*
```

## Architecture Overview

### Core Components

1. **Decorators** (`decorators.py`): Transform functions into HTTP endpoints
   - Handles sync/async duality
   - Extracts parameters from function signatures
   - Manages request/response cycle

2. **Configuration Hierarchy**: Three-level cascade
   - Travessera (global) → Service (service-level) → Endpoint (decorator-level)
   - Later levels override earlier ones
   - Headers are merged, not replaced

3. **Request Pipeline**:
   ```
   Function Call → Parameter Parser → Request Builder → HTTP Client → Response Handler → Return Value
   ```

4. **Exception Hierarchy**:
   ```
   TravesseraError
   ├── ServiceError (configuration issues)
   ├── NetworkError (connectivity issues)
   ├── HTTPError (4xx/5xx responses)
   └── ValidationError (data validation)
   ```

### Key Design Patterns

1. **Protocol-Based Extensibility**: Authentication, Serializers use Protocol classes
2. **Async-First with Sync Support**: AsyncRetrying for retries, httpx for HTTP
3. **Type Safety**: Pydantic for validation, comprehensive type hints
4. **Pluggable Components**: Custom auth, serializers, transformers

## Technical Details

### Python Version
- **Minimum**: Python 3.10+
- **Reason**: Modern type hints (Union → |, List → list), better async support

### Dependencies
- **httpx**: Modern HTTP client with async/sync support
- **pydantic**: Data validation and serialization
- **tenacity**: Retry logic with exponential backoff
- **typing-extensions**: Type hint backports

### Testing
- **pytest-httpx**: Mock HTTP responses
- **pytest-asyncio**: Test async functions
- **Coverage Target**: 80%+ (currently 88%)

## Common Tasks

### Adding a New Authentication Method
1. Create class implementing `Authentication` protocol in `authentication.py`
2. Implement `apply(request) -> request` method
3. Add tests in `tests/test_authentication.py`

### Adding a New Serializer
1. Create class implementing `Serializer` protocol in `serializers/`
2. Implement `serialize()` and `deserialize()` methods
3. Set `content_type` attribute
4. Add tests in `tests/test_serializers.py`

### Modifying Request/Response Pipeline
1. Key files: `request_builder.py`, `response_handler.py`, `parameter_parser.py`
2. Ensure both sync and async paths work
3. Update integration tests

## Important Patterns

### Async Retry Implementation
```python
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

# Use AsyncRetrying directly, not @retry decorator
async with AsyncRetrying(...) as retry:
    async for attempt in retry:
        with attempt:
            # retry logic
```

### Header Case Sensitivity
- httpx lowercases all headers
- Tests must expect lowercase: `"x-api-key"` not `"X-API-Key"`

### Type Annotations (Python 3.10+)
```python
# Old style (don't use)
from typing import List, Optional, Union
x: Optional[str] = None
y: List[int] = []
z: Union[str, int] = "hello"

# New style (use this)
x: str | None = None
y: list[int] = []
z: str | int = "hello"
```

## CI/CD Configuration

### GitHub Actions
- **Python Versions**: 3.10, 3.11, 3.12
- **Checks**: ruff, black, mypy (non-failing), pytest with coverage
- **Build**: Validates package with twine
- **Publish**: Triggered on release, requires PYPI_API_TOKEN secret

### Pre-commit Hooks
Configure locally with:
```bash
pip install pre-commit
pre-commit install
```

## Project Structure
```
travessera/
├── __init__.py              # Public API exports
├── core.py                  # Travessera and Service classes
├── decorators.py            # Endpoint decorators
├── authentication.py        # Auth strategies
├── exceptions.py            # Exception hierarchy
├── client.py               # HTTP client wrapper
├── models.py               # Pydantic models
├── types.py                # Type definitions
├── retry.py                # Retry logic
├── serializers/            # Serialization plugins
└── _internal/              # Internal implementation
    ├── config_resolver.py  # Config merging
    ├── request_builder.py  # Request construction
    ├── response_handler.py # Response processing
    └── parameter_parser.py # Function introspection
```

## Documentation

- **README.md**: User-facing documentation with examples
- **docs/DESIGN.md**: Comprehensive architecture and design decisions
- **docs/GITHUB_PUSH_CHECKLIST.md**: Pre-push verification steps

## Common Issues and Solutions

### JSON Serialization Spacing
- `json.dumps()` adds spaces after separators by default
- Tests should expect `{"key": "value"}` not `{"key":"value"}`

### Fixture Naming Conflicts
- Avoid test fixture names that match imported modules
- Use descriptive names: `sample_service` not `service`

### Async Testing
- Use `pytest.mark.asyncio` or set `asyncio_mode = "auto"` in pytest config
- Mock async context managers properly with `__aenter__` and `__aexit__`

## Development Philosophy

1. **Type Safety First**: Leverage Pydantic and type hints extensively
2. **Developer Experience**: Make the API intuitive and Pythonic
3. **Fail Fast**: Validate early, provide clear error messages
4. **Test Everything**: Maintain high coverage, test edge cases
5. **Document Thoroughly**: Code should be self-documenting with docstrings

## Quick Reference

### Run Tests for Specific Module
```bash
pytest tests/test_decorators.py -v
```

### Check Coverage for Specific Module
```bash
pytest tests/ --cov=travessera.decorators --cov-report=term-missing
```

### Format Single File
```bash
black travessera/decorators.py
```

### Lint Single File
```bash
ruff check travessera/decorators.py --fix
```

## Notes for Future Development

1. **Service Discovery**: Currently requires manual Service configuration. Future: automatic discovery
2. **Caching**: No built-in caching. Could add Redis/memory cache support
3. **Circuit Breakers**: Basic retry logic exists. Could add circuit breaker pattern
4. **Metrics/Monitoring**: No built-in metrics. Could add OpenTelemetry support
5. **WebSocket/GraphQL**: Currently HTTP-only. Architecture supports protocol extensions

## Development Memory

- All python runs will use a virtualenv in the .venv directory. Remember to activate the virtualenv before running python or using pip.

Remember: Always run black and ruff before committing. The CI will fail otherwise!

## Pre-Commit Checklist

- Remember to run: 1. ruff, 2. black, 3. all tests, before commiting code to git.