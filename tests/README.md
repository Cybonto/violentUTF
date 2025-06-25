# ViolentUTF Test Suite

Comprehensive testing framework for ViolentUTF platform components including API endpoints, authentication, integrations, and security features.

## Quick Start

### Installing Test Dependencies

```bash
# Navigate to the project root
cd /path/to/ViolentUTF

# Install test dependencies
pip install -r tests/requirements-test.txt

# If you encounter version conflicts, use:
# pip install -r tests/requirements-test-minimal.txt

# For running the API (if testing against real API)
pip install -r violentutf_api/fastapi_app/requirements.txt

# For API development tools (optional - includes linting, formatting, debugging)
pip install -r violentutf_api/fastapi_app/requirements-dev.txt
```

### Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit -v

# Run unit tests with coverage report
pytest tests/unit --cov=violentutf --cov=violentutf_api/fastapi_app/app --cov-report=html --cov-report=term

# Run unit tests in parallel (faster execution)
pytest tests/unit -n auto

# Run specific test categories
pytest tests/unit/core -v              # Core security tests
pytest tests/unit/api -v               # API endpoint tests
pytest tests/unit/services -v          # Service layer tests
pytest tests/unit/mcp -v               # MCP server tests
pytest tests/unit/utils -v             # Utility tests

# Run specific test files
pytest tests/unit/core/test_auth.py -v
pytest tests/unit/services/test_pyrit_orchestrator.py -v

# Run tests matching a pattern
pytest tests/unit -k "test_jwt" -v     # All JWT-related tests
pytest tests/unit -k "security" -v     # All security tests
```

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration -v

# Run integration tests (legacy)
./run_tests.sh

# Run enhanced test suite
./run_enhanced_tests.sh

# Run API-specific tests
cd api_tests && ./run_api_tests.sh
```

## Test Structure

```
tests/
├── unit/                      # Unit tests (250+ tests)
│   ├── conftest.py           # Base fixtures and configuration
│   ├── core/                 # Core security components
│   │   ├── test_auth.py      # Authentication tests (25+ tests)
│   │   ├── test_security.py  # Security utilities (20+ tests)
│   │   └── test_password_policy.py  # Password validation (25+ tests)
│   ├── api/                  # API endpoints
│   │   └── endpoints/
│   │       └── test_generators.py  # Generator CRUD (30+ tests)
│   ├── services/             # Service layer
│   │   ├── test_pyrit_orchestrator.py  # PyRIT integration (30+ tests)
│   │   ├── test_keycloak_verification.py  # Keycloak SSO (20+ tests)
│   │   └── test_garak_integration.py  # Garak scanner (15+ tests)
│   ├── mcp/                  # Model Context Protocol
│   │   └── test_server.py    # MCP server (40+ tests)
│   └── utils/                # Utilities
│       ├── test_jwt_manager.py  # JWT management (20+ tests)
│       └── test_data_loaders.py # Data loading (15+ tests)
├── integration/              # Integration tests
├── factories/               # Test data factories
│   ├── generator_factory.py # Generator test data
│   ├── user_factory.py      # User and auth data
│   └── dataset_factory.py   # Dataset test data
└── api_tests/              # Legacy API tests
```

## Coverage Reports

### HTML Coverage Report
```bash
# Generate HTML coverage report
pytest tests/unit --cov=violentutf --cov=violentutf_api/fastapi_app/app --cov-report=html

# View coverage report (opens in browser)
open tests/htmlcov/index.html
```

### Coverage Metrics
- Target: 80% code coverage
- Current: See CI/CD pipeline results
- Excluded: Test files, migrations, virtual environments

## Test Categories

### Unit Tests
- **Core Security** (75+ tests)
  - Authentication and authorization
  - JWT token validation
  - Password policy enforcement
  - Security attack prevention

- **API Endpoints** (30+ tests)
  - CRUD operations
  - Input validation
  - Error handling
  - SQL injection prevention

- **Service Layer** (60+ tests)
  - PyRIT orchestrator lifecycle
  - Keycloak token verification
  - Garak scanner integration

- **MCP Server** (40+ tests)
  - Protocol compliance
  - Tool and resource management
  - Authentication flows

- **Utilities** (30+ tests)
  - JWT token management
  - Data loaders
  - Helper functions

### Integration Tests
- **API Tests** (`api_tests/`): FastAPI endpoint testing with authentication
- **End-to-End Tests**: Complete workflows and service interactions  
- **Authentication Tests**: JWT, Keycloak SSO, and security validation
- **Orchestrator Tests**: PyRIT orchestrator functionality and execution
- **Rate Limiting Tests**: API protection and throttling validation

## Test Configuration

### pytest.ini Configuration
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    security: Security-related tests
```

### Coverage Configuration (.coveragerc)
See `.coveragerc` for detailed coverage settings including:
- Source paths
- Exclusion patterns
- Report formats
- Branch coverage

## Writing Tests

### Test Naming Convention
```python
# File naming: test_<module_name>.py
# Function naming: test_<what_is_being_tested>_<expected_behavior>

def test_jwt_validation_with_valid_token_returns_payload():
    """Test that JWT validation returns payload for valid tokens"""
    pass

def test_generator_create_with_invalid_data_raises_validation_error():
    """Test that creating generator with invalid data raises error"""
    pass
```

### Using Test Factories
```python
from tests.factories import create_test_user, create_test_generator

def test_user_authentication():
    # Create test user with factory
    user = create_test_user(role="admin")
    
    # Create test generator
    generator = create_test_generator(
        type="openai",
        name="Test GPT-4"
    )
```

### Common Test Patterns
```python
# Testing async functions
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None

# Using fixtures
def test_with_auth(authenticated_client):
    response = authenticated_client.get("/api/v1/generators")
    assert response.status_code == 200

# Mocking external services
def test_with_mock(mock_keycloak):
    mock_keycloak.verify_token.return_value = {"sub": "user123"}
    # Test code here
```

## CI/CD Integration

Tests run automatically on:
- Every push to `main`, `develop`, and `dev_tests` branches
- All pull requests
- Can be triggered manually via GitHub Actions

### CI Pipeline Stages
1. **Linting**: flake8, black, isort
2. **Unit Tests**: Multi-Python version testing (3.10, 3.11, 3.12)
3. **Coverage Check**: Minimum 80% coverage required
4. **Integration Tests**: Full service testing
5. **Security Scan**: Bandit and safety checks

## Debugging Tests

### Running Tests with Debugging
```bash
# Run with pytest debugging
pytest tests/unit/core/test_auth.py -v -s --pdb

# Run specific test with debugging
pytest tests/unit/core/test_auth.py::test_jwt_validation -v -s

# Run with logging enabled
pytest tests/unit -v --log-cli-level=DEBUG
```

### Common Issues and Solutions

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/ViolentUTF
   
   # Install in development mode
   pip install -e .
   ```

2. **Fixture Not Found**
   - Check that conftest.py is in the test directory
   - Ensure fixtures are properly imported

3. **Async Test Failures**
   - Use `@pytest.mark.asyncio` decorator
   - Install pytest-asyncio: `pip install pytest-asyncio`

## Test Utilities

- `tests/unit/conftest.py` - Shared fixtures and setup
- `tests/factories/` - Test data generation
- `.coveragerc` - Coverage configuration
- `.github/workflows/ci.yml` - CI/CD pipeline

## Requirements

### Dependency Organization

ViolentUTF uses a clear separation of dependencies:

- **`tests/requirements-test.txt`** - All testing dependencies (pytest, mocking, factories)
- **`violentutf_api/fastapi_app/requirements.txt`** - API runtime dependencies
- **`violentutf_api/fastapi_app/requirements-dev.txt`** - API development tools (formatting, linting)
- **`violentutf/requirements.txt`** - Streamlit app dependencies

### For Unit Tests
- Python 3.10+
- Dependencies from `tests/requirements-test.txt`
- No external services required (all mocked)

### For Integration Tests
- All ViolentUTF services running (API, APISIX, Keycloak)
- Valid test environment configuration
- Authentication tokens and API keys configured
- Docker and docker-compose

## Documentation

For additional testing resources:
- **[API Documentation](../docs/api/)** - API testing guidelines
- **[Development Guide](../docs/DEVELOPMENT.md)** - Development setup
- **[CI/CD Documentation](.github/workflows/README.md)** - CI/CD pipeline details