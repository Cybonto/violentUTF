# ViolentUTF Test Suite

Comprehensive testing framework for ViolentUTF platform components including API endpoints, authentication, integrations, and security features.

## Quick Start

```bash
# Run all tests
./run_tests.sh

# Run enhanced test suite
./run_enhanced_tests.sh

# Run API-specific tests
cd api_tests && ./run_api_tests.sh

# Run specific test files
pytest test_authentication_flow.py -v
pytest test_orchestrator_integration.py -v
```

## Test Categories

- **API Tests** (`api_tests/`): FastAPI endpoint testing with authentication
- **Integration Tests**: End-to-end workflows and service interactions  
- **Authentication Tests**: JWT, Keycloak SSO, and security validation
- **Orchestrator Tests**: PyRIT orchestrator functionality and execution
- **Rate Limiting Tests**: API protection and throttling validation

## Key Test Files

- `test_authentication_flow.py` - JWT and Keycloak authentication
- `test_orchestrator_integration.py` - PyRIT orchestrator testing
- `test_rate_limiting.py` - API rate limit validation
- `test_keycloak_verification_fix.py` - SSO integration tests
- `conftest.py` - Shared fixtures and setup

## Test Utilities

- `utils/keycloak_auth.py` - Authentication helpers
- `run_tests.sh` - Main test execution script
- `pytest.ini` - Test configuration and markers

## Documentation

For detailed testing guidelines, setup instructions, authentication configuration, and troubleshooting, see:

**📚 [Complete Testing Documentation](../docs/api/)**

## Requirements

- All ViolentUTF services running (API, APISIX, Keycloak)
- Valid test environment configuration
- Authentication tokens and API keys configured