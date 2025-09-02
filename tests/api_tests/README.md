# ViolentUTF API Tests

Comprehensive test suite for the ViolentUTF API endpoints with authentication, validation, and integration testing.

## Quick Start

```bash
# Run all API tests
./run_api_tests.sh

# Run specific test categories
pytest test_converter_apply.py -v
pytest test_generator_functionality.py -v
pytest test_dataset_prompt_format.py -v
```

## Test Categories

- **Authentication Tests**: JWT token validation and Keycloak integration
- **Endpoint Tests**: CRUD operations for generators, datasets, converters, scorers
- **Integration Tests**: End-to-end workflows and orchestrator functionality
- **Security Tests**: Rate limiting, input validation, and access control

## Test Configuration

- `conftest.py` - Shared fixtures and authentication setup
- `pytest.ini` - Test configuration and markers
- Authentication uses JWT tokens matching FastAPI service SECRET_KEY

## Test Structure

```
api_tests/
├── test_converter_*.py     # Converter endpoint tests
├── test_dataset_*.py       # Dataset management tests
├── test_generator_*.py     # Generator configuration tests
├── test_parameter_*.py     # Parameter validation tests
└── run_api_tests.sh       # Test execution script
```

## Documentation

For detailed testing guidelines, authentication setup, and troubleshooting, see:

**📚 [Complete Testing Documentation](../../docs/api/)**

## Requirements

- API services running (FastAPI + APISIX)
- Valid authentication tokens
- Test environment configuration in `.env`
