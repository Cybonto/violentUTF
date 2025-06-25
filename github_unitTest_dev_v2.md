# Unit Testing Development Plan for ViolentUTF (Version 2)

## Executive Summary

This enhanced plan addresses unit test development for ViolentUTF using a feature branch strategy (`dev_tests`). The plan incorporates security testing, performance benchmarking, and progressive integration to minimize disruption to the main branch.

## Branching Strategy Assessment

### Recommended Approach: Feature Branch (`dev_tests`)

**Advantages:**
- ✅ Isolated development without affecting `main`
- ✅ Allows iterative testing and refinement
- ✅ Easy rollback if issues arise
- ✅ Enables parallel development
- ✅ Clear PR review process

**Best Practices for `dev_tests` Branch:**
1. **Regular syncing**: Merge `main` into `dev_tests` weekly to avoid conflicts
2. **Incremental merging**: Submit smaller PRs for completed test modules
3. **CI validation**: Ensure all tests pass before merging
4. **Feature flags**: Use pytest markers to disable incomplete tests

### Alternative Approaches (Not Recommended)
- **Direct to main**: Too risky, may break existing workflows
- **Multiple feature branches**: Adds complexity, coordination overhead
- **Long-lived test branch**: Risk of significant drift from main

## Enhanced Implementation Plan

### Phase 0: Pre-Development Setup (Week 0)

#### Branch Setup and Configuration
```bash
# Create and configure dev_tests branch
git checkout -b dev_tests
git push -u origin dev_tests

# Configure branch protection for main (GitHub settings)
# - Require PR reviews
# - Require status checks (tests must pass)
# - Require up-to-date branch
```

#### Test Environment Configuration
```yaml
# .github/workflows/test-branch-ci.yml
name: Test Branch CI

on:
  push:
    branches: [ dev_tests ]
  pull_request:
    branches: [ main ]
    paths:
      - 'tests/**'
      - '**/test_*.py'
      - '**/*_test.py'

jobs:
  validate-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate test structure
        run: |
          # Check for test naming conventions
          find tests/unit -name "*.py" | grep -E "(test_|_test\.py$)" || exit 1
      - name: Check test isolation
        run: |
          # Ensure no hardcoded paths or credentials
          grep -r "localhost:8" tests/unit && exit 1 || true
```

### Phase 1: Enhanced Foundation (Week 1)

#### 1.1 Extended Testing Infrastructure
```bash
# requirements-test.txt (more comprehensive)
# Core testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-env>=0.8.0
pytest-xdist>=3.3.0
pytest-timeout>=2.1.0      # Prevent hanging tests
pytest-benchmark>=4.0.0    # Performance testing

# Mocking and fakes
factory-boy>=3.3.0
faker>=19.0.0
responses>=0.23.0
freezegun>=1.2.0
aioresponses>=0.7.4       # Mock async HTTP
pytest-httpx>=0.21.0      # HTTPX mocking

# Security testing
bandit>=1.7.5
safety>=2.3.0

# Code quality
pytest-black>=0.3.12
pytest-isort>=3.1.0
pytest-flake8>=1.1.1
pytest-mypy>=0.10.0

# Reporting
pytest-html>=3.2.0
pytest-json-report>=1.5.0
allure-pytest>=2.13.0
```

#### 1.2 Enhanced Directory Structure
```
tests/
├── unit/
│   ├── __init__.py
│   ├── conftest.py
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── test_generators.py
│   │   │   ├── test_orchestrators.py
│   │   │   └── test_error_handling.py
│   │   └── middleware/
│   │       ├── test_auth_middleware.py
│   │       └── test_rate_limiting.py
│   ├── core/
│   │   ├── test_auth.py
│   │   ├── test_security.py
│   │   ├── test_password_policy.py
│   │   └── test_input_validation.py
│   ├── services/
│   │   ├── test_pyrit_orchestrator.py
│   │   ├── test_garak_integration.py
│   │   ├── test_keycloak_verification.py
│   │   └── test_circuit_breaker.py
│   ├── mcp/
│   │   ├── test_protocol_compliance.py
│   │   ├── test_server.py
│   │   ├── test_tools.py
│   │   └── test_error_recovery.py
│   ├── security/
│   │   ├── test_injection_prevention.py
│   │   ├── test_rate_limiting.py
│   │   └── test_authentication_bypass.py
│   └── performance/
│       ├── test_response_times.py
│       ├── test_memory_usage.py
│       └── test_concurrent_requests.py
├── fixtures/
│   ├── __init__.py
│   ├── auth.py
│   ├── models.py
│   ├── mocks.py
│   └── security.py
├── factories/
│   └── ... (as before)
└── benchmarks/
    ├── __init__.py
    ├── test_api_performance.py
    └── test_database_performance.py
```

#### 1.3 Enhanced Base Configuration
```python
# tests/unit/conftest.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from contextlib import contextmanager
import tempfile
import os

# Configure async test handling
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def isolated_filesystem():
    """Provide isolated filesystem for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)

@pytest.fixture
def mock_env_vars():
    """Mock environment variables"""
    env_vars = {
        "JWT_SECRET_KEY": "test-secret-key",
        "VIOLENTUTF_API_KEY": "test-api-key",
        "KEYCLOAK_URL": "http://mock-keycloak:8080",
        "APISIX_ADMIN_KEY": "test-admin-key"
    }
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env_vars.items():
            mp.setenv(key, value)
        yield env_vars

@pytest.fixture
def security_headers():
    """Standard security headers for testing"""
    return {
        "X-Request-ID": "test-request-123",
        "X-Forwarded-For": "127.0.0.1",
        "X-Real-IP": "127.0.0.1",
        "User-Agent": "pytest/test"
    }

# Performance benchmarking fixtures
@pytest.fixture
def benchmark_threshold():
    """Performance thresholds for different operations"""
    return {
        "api_response": 100,  # ms
        "database_query": 50,  # ms
        "jwt_validation": 10,  # ms
        "mcp_tool_execution": 200  # ms
    }
```

### Phase 2: Security-Focused Testing (Week 2)

#### 2.1 Security Test Suite
```python
# tests/unit/security/test_injection_prevention.py
import pytest
from app.core.validation import sanitize_input

class TestInjectionPrevention:
    @pytest.mark.parametrize("malicious_input,expected_safe", [
        # SQL Injection attempts
        ("'; DROP TABLE users; --", "DROP TABLE users"),
        ("1' OR '1'='1", "1 OR 11"),
        
        # NoSQL Injection attempts
        ('{"$ne": null}', "ne null"),
        ('{"$gt": ""}', "gt"),
        
        # Command Injection attempts
        ("; ls -la", "ls la"),
        ("| cat /etc/passwd", "cat etcpasswd"),
        
        # Path Traversal attempts
        ("../../../etc/passwd", "etcpasswd"),
        ("..\\..\\windows\\system32", "windowssystem32"),
        
        # XSS attempts
        ("<script>alert('xss')</script>", "scriptalertxssscript"),
        ("javascript:alert(1)", "javascriptalert1"),
    ])
    def test_input_sanitization(self, malicious_input, expected_safe):
        """Test that malicious inputs are properly sanitized"""
        result = sanitize_input(malicious_input)
        assert expected_safe in result
        assert "<" not in result
        assert ">" not in result
        assert ";" not in result

# tests/unit/security/test_authentication_bypass.py
class TestAuthenticationBypass:
    @pytest.mark.asyncio
    async def test_jwt_algorithm_confusion(self, auth_middleware):
        """Test protection against JWT algorithm confusion attacks"""
        # Create token with 'none' algorithm
        malicious_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9."
        
        with pytest.raises(HTTPException) as exc:
            await auth_middleware.verify_jwt_token(malicious_token)
        assert exc.value.status_code == 401
        assert "Invalid algorithm" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    async def test_jwt_key_confusion(self, auth_middleware):
        """Test protection against key confusion attacks"""
        # Token signed with wrong key
        wrong_key_token = create_token_with_key({"sub": "admin"}, "wrong-key")
        
        with pytest.raises(HTTPException) as exc:
            await auth_middleware.verify_jwt_token(wrong_key_token)
        assert exc.value.status_code == 401
```

### Phase 3: Performance Testing (Week 3)

#### 3.1 Performance Benchmarks
```python
# tests/benchmarks/test_api_performance.py
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

class TestAPIPerformance:
    @pytest.mark.benchmark(group="api")
    def test_generator_creation_performance(self, benchmark, mock_db_session):
        """Benchmark generator creation endpoint"""
        def create_generator():
            return create_generator_sync({
                "name": "perf-test",
                "model": "gpt-4",
                "provider": "openai"
            }, mock_db_session)
        
        result = benchmark(create_generator)
        assert result["id"] is not None
        assert benchmark.stats["mean"] < 0.05  # 50ms threshold
    
    @pytest.mark.benchmark(group="api")
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, benchmark):
        """Test API performance under concurrent load"""
        async def handle_concurrent_requests():
            tasks = []
            for i in range(100):
                task = asyncio.create_task(
                    list_generators(db=mock_db_session)
                )
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        results = await benchmark.pedantic(
            handle_concurrent_requests,
            rounds=5,
            iterations=1
        )
        assert len(results) == 100
        assert benchmark.stats["mean"] < 1.0  # 1 second for 100 requests
```

### Phase 4: Progressive Integration Strategy (Week 4-5)

#### 4.1 Test Categorization with Markers
```python
# pytest.ini additions
[tool:pytest]
markers =
    unit: Pure unit tests (no external dependencies)
    integration: Tests requiring service integration
    security: Security-focused tests
    performance: Performance benchmarks
    slow: Tests taking > 1 second
    critical: Tests for critical paths
    wip: Work in progress (skip in CI)
    requires_auth: Tests requiring authentication setup
    requires_docker: Tests requiring Docker services

# Usage in tests
@pytest.mark.unit
@pytest.mark.critical
def test_jwt_creation():
    pass

@pytest.mark.integration
@pytest.mark.requires_docker
async def test_keycloak_integration():
    pass
```

#### 4.2 Progressive Merge Strategy
```yaml
# .github/workflows/progressive-merge.yml
name: Progressive Test Integration

on:
  pull_request:
    branches: [ main ]
    types: [ opened, synchronize ]

jobs:
  test-impact-analysis:
    runs-on: ubuntu-latest
    steps:
      - name: Analyze test coverage delta
        run: |
          # Compare coverage before and after
          coverage_delta=$(git diff origin/main...HEAD --stat -- 'tests/unit/**')
          echo "Coverage Delta: $coverage_delta"
      
      - name: Run affected tests only
        run: |
          # Identify changed files
          changed_files=$(git diff origin/main...HEAD --name-only | grep -E '\\.py$')
          # Run tests for changed modules
          pytest --testmon --testmon-cov
      
      - name: Validate no regression
        run: |
          # Run critical path tests
          pytest -m critical --fail-fast
```

### Phase 5: Test Quality Assurance (Week 6)

#### 5.1 Test Quality Metrics
```python
# tests/quality/test_quality_metrics.py
import ast
import os

class TestQualityChecker:
    def test_no_hardcoded_credentials(self):
        """Ensure no hardcoded credentials in tests"""
        test_files = []
        for root, dirs, files in os.walk("tests/unit"):
            for file in files:
                if file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
        
        for test_file in test_files:
            with open(test_file, 'r') as f:
                content = f.read()
                assert "password=" not in content.lower()
                assert "api_key=" not in content.lower()
                assert "secret=" not in content.lower()
    
    def test_proper_mocking(self):
        """Ensure external dependencies are mocked"""
        violations = []
        for test_file in self.get_test_files():
            tree = ast.parse(open(test_file).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if hasattr(node.func, 'attr'):
                        # Check for direct HTTP calls
                        if node.func.attr in ['get', 'post', 'put', 'delete']:
                            if 'mock' not in test_file:
                                violations.append(f"{test_file}: Direct HTTP call")
        
        assert not violations, f"Unmocked external calls: {violations}"
```

#### 5.2 Test Documentation
```python
# tests/unit/README.md
# Unit Test Guide for ViolentUTF

## Test Organization
- Each module has corresponding test file
- Tests grouped by functionality
- Clear naming: test_<action>_<condition>_<expected>

## Running Tests
```bash
# Run all unit tests
pytest tests/unit -v

# Run specific category
pytest tests/unit -m security

# Run with coverage
pytest tests/unit --cov=app --cov-report=html

# Run in parallel
pytest tests/unit -n auto

# Run only fast tests
pytest tests/unit -m "not slow"
```

## Writing New Tests
1. Check existing patterns in similar tests
2. Use appropriate fixtures from conftest.py
3. Mock all external dependencies
4. Add appropriate markers
5. Ensure test isolation

## Common Patterns
See tests/patterns.md for common testing patterns
```

### Phase 6: Continuous Improvement (Ongoing)

#### 6.1 Test Metrics Dashboard
```yaml
# .github/workflows/test-metrics.yml
name: Test Metrics

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  collect-metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Generate test report
        run: |
          pytest --json-report --json-report-file=report.json
          python scripts/generate_test_dashboard.py report.json
      
      - name: Update metrics
        run: |
          echo "## Test Metrics $(date)" >> TEST_METRICS.md
          echo "- Total Tests: $(jq '.summary.total' report.json)" >> TEST_METRICS.md
          echo "- Pass Rate: $(jq '.summary.passed' report.json)%" >> TEST_METRICS.md
          echo "- Coverage: $(coverage report | grep TOTAL | awk '{print $4}')" >> TEST_METRICS.md
```

## Migration Path from `dev_tests` to `main`

### Step 1: Initial Foundation (Week 1)
```bash
# On dev_tests branch
git add tests/unit/conftest.py tests/fixtures tests/factories
git commit -m "test: Add unit test infrastructure foundation"
git push origin dev_tests

# Create PR to main with just infrastructure (no breaking changes)
```

### Step 2: Core Tests (Week 2-3)
```bash
# Add core component tests in batches
git add tests/unit/core tests/unit/api/endpoints/test_generators.py
git commit -m "test: Add unit tests for core components"

# Ensure CI passes on dev_tests before PR
```

### Step 3: Progressive Integration (Week 4-5)
```bash
# Merge main into dev_tests regularly
git checkout dev_tests
git merge main --no-ff
git push origin dev_tests

# Submit smaller PRs for completed modules
```

### Step 4: Final Integration (Week 6)
```bash
# Final comprehensive PR
git checkout -b feature/complete-unit-tests
git merge dev_tests
git push origin feature/complete-unit-tests

# Create PR with full test suite
```

## Risk Mitigation

### Potential Risks and Mitigations

1. **Test Flakiness**
   - Mitigation: Strict mocking, fixed random seeds, retry mechanisms
   
2. **Performance Degradation**
   - Mitigation: Parallel execution, test optimization, selective running
   
3. **Merge Conflicts**
   - Mitigation: Regular syncing, smaller PRs, clear communication
   
4. **Breaking Existing Tests**
   - Mitigation: Run full test suite before each PR, gradual integration

## Success Criteria (Enhanced)

### Coverage Targets
- **Overall**: 85% (increased from 80%)
- **Critical paths**: 98% (increased from 95%)
- **Security components**: 100%
- **New code**: 95% (increased from 90%)

### Quality Targets
- **No flaky tests**: 0 tolerance
- **Test execution time**: < 3 minutes (improved from 5)
- **Security vulnerabilities**: 0 in test code
- **Documentation coverage**: 100% of test patterns

## Conclusion

This enhanced plan provides:
1. **Robust branching strategy** using `dev_tests` with progressive integration
2. **Security-focused testing** to ensure safety of AI red-teaming platform
3. **Performance benchmarking** for critical paths
4. **Quality assurance** mechanisms
5. **Clear migration path** from development to production

The `dev_tests` branch approach is indeed the best strategy as it allows isolated development while maintaining stability of the main branch.