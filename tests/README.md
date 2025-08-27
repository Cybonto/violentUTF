# ViolentUTF Test Structure

## Directory Organization

- `tests/unit/` - Unit tests that run quickly without external dependencies
  - Should complete in < 5 seconds per test
  - No network calls, database connections, or Docker containers
  - Mock external dependencies

- `tests/integration/` - Integration tests that require services
  - May require Docker containers (Keycloak, APISIX, etc.)
  - May make network calls to local services
  - Should complete in < 30 seconds per test

- `tests/e2e/` - End-to-end tests
  - Full system tests with all services running
  - May take several minutes to complete

- `tests/api_tests/` - API-specific integration tests
  - Test REST API endpoints
  - Require running API server

- `tests/mcp_tests/` - MCP protocol tests
  - Test Model Context Protocol functionality

## CI/CD Configuration

The CI/CD workflows are configured to run ONLY unit tests by default:
- PR validation: `pytest tests/unit`
- Core unit tests: `pytest tests/unit`

This ensures fast feedback and prevents long-running tests from blocking PRs.

## Running Tests Locally

```bash
# Run only unit tests (fast, no dependencies)
pytest tests/unit -v

# Run integration tests (requires services)
pytest tests/integration -v

# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/unit -v --cov=violentutf --cov=violentutf_api
```

## Test Performance Guidelines

- Unit tests: < 5 seconds per test
- Integration tests: < 30 seconds per test
- E2E tests: < 5 minutes per test

Tests exceeding these limits should be marked with `@pytest.mark.slow` and excluded from PR validation.
