# Contributing to Travessera

Thank you for your interest in contributing to Travessera! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct: be respectful, inclusive, and constructive.

## How to Contribute

### Reporting Issues

- Check if the issue already exists
- Include a clear description and minimal reproduction example
- Include version information and environment details

### Suggesting Features

- Open an issue with the "enhancement" label
- Explain the use case and benefits
- Provide examples of how it would work

### Submitting Code

1. **Fork the repository**

2. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/travessera.git
   cd travessera
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

5. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

6. **Make your changes**
   - Write clear, concise commit messages
   - Add tests for new functionality
   - Update documentation as needed

7. **Run tests**
   ```bash
   pytest tests/
   ```

8. **Run linting and formatting**
   ```bash
   ruff check .
   black .
   mypy travessera
   ```

9. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Development Guidelines

### Code Style

- Follow PEP 8
- Use Black for formatting (configured in pyproject.toml)
- Use type hints for all public APIs
- Write descriptive docstrings

### Testing

- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest for testing
- Mock external services appropriately

### Documentation

- Update docstrings for API changes
- Update README.md for significant features
- Add examples for new functionality

## Project Structure

```
travessera/
├── travessera/          # Main package
│   ├── _internal/       # Internal implementation
│   ├── serializers/     # Serialization modules
│   └── *.py            # Core modules
├── tests/              # Test suite
├── docs/               # Documentation
├── examples/           # Usage examples
└── pyproject.toml      # Project configuration
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a release PR
4. After merge, tag the release
5. GitHub Actions will publish to PyPI

## Questions?

Feel free to open an issue for any questions about contributing!