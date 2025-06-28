# CI/CD Pipeline Guide for ViolentUTF

This guide provides comprehensive documentation for the ViolentUTF CI/CD pipeline implementation, including workflows, best practices, and troubleshooting information.

## Overview

The ViolentUTF CI/CD pipeline is designed to ensure code quality, security, and reliability for an enterprise-grade AI red-teaming platform. The pipeline implements multiple layers of validation including multi-platform testing, security scanning, and integration testing.

## Workflow Structure

### 1. Main CI Pipeline (`ci.yml`)

The primary continuous integration workflow that runs on every push and pull request.

**Triggers:**
- Push to: `main`, `dev_*`, `develop` branches
- Pull requests targeting the above branches
- Manual workflow dispatch with debug option

**Key Features:**
- Multi-platform testing (Ubuntu, macOS, Windows)
- Python version matrix (3.10, 3.11, 3.12)
- Code quality checks (Black, isort, flake8, mypy)
- Security scanning (Bandit, Safety, pip-audit)
- Docker integration testing with DinD
- Comprehensive test coverage reporting
- PR comment integration

**Jobs:**
1. **test-matrix**: Cross-platform Python testing
2. **code-quality**: Linting and formatting validation
3. **dependency-security**: Vulnerability scanning
4. **docker-integration**: Service integration tests
5. **process-results**: Result aggregation and PR comments
6. **ci-status**: Final status check

### 2. PR Quick Checks (`ci-pr.yml`)

Fast validation workflow specifically for pull requests.

**Triggers:**
- Pull request events: opened, synchronize, reopened

**Key Features:**
- PR size labeling (XS, S, M, L, XL)
- File change categorization
- Python formatting suggestions
- Quick security scanning with Trivy
- Minimal test validation
- Docker validation with Hadolint

**Jobs:**
1. **pr-validation**: PR metadata and labeling
2. **python-lint**: Auto-formatting checks
3. **security-scan**: Quick vulnerability scan
4. **quick-test**: Fast unit test subset
5. **docker-lint**: Dockerfile validation
6. **pr-status**: Status summary comment

### 3. Nightly CI (`ci-nightly.yml`)

Comprehensive testing workflow that runs daily.

**Triggers:**
- Schedule: Daily at 2 AM UTC
- Manual workflow dispatch

**Key Features:**
- Extended OS matrix (including older versions)
- Python 3.13-dev testing
- Performance benchmarking
- Comprehensive security analysis (Semgrep, GitLeaks, OWASP)
- Full integration test suite
- Dependency update checking
- Automatic issue creation on failure

**Jobs:**
1. **extended-test-matrix**: Comprehensive platform testing
2. **performance-benchmark**: Performance profiling
3. **comprehensive-security**: Deep security analysis
4. **full-integration-tests**: Complete E2E testing
5. **dependency-updates**: Outdated package detection
6. **nightly-summary**: Failure reporting

## Security Best Practices

### Action Pinning

All GitHub Actions are pinned to specific commit SHAs for security:

```yaml
uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
```

### Minimal Permissions

Workflows use the principle of least privilege:

```yaml
permissions:
  contents: read
  pull-requests: write  # Only when needed
  issues: write        # Only when needed
```

### Secret Management

- No hardcoded secrets in workflows
- Use GitHub Secrets for sensitive data
- AI provider tokens stored as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
- Validate `ai-tokens.env.sample` structure in CI

## Platform-Specific Considerations

### Ubuntu (Linux)
- Primary testing platform for AMD64 containers
- System dependencies: `build-essential`, `libpq-dev`, `libssl-dev`
- Used for Docker integration testing

### macOS
- Apple Silicon (ARM64) compatibility testing
- Homebrew dependencies: `postgresql`, `libpq`
- ARM64 container validation

### Windows
- Enterprise Windows development support
- Cross-compilation validation for Linux containers
- Platform-specific path handling in tests

## Python Version Matrix

- **Python 3.10**: Minimum supported version
- **Python 3.11**: Default/recommended version
- **Python 3.12**: Latest stable support
- **Python 3.13-dev**: Forward compatibility (nightly only)

## Docker Integration

### Docker-in-Docker (DinD)

The CI uses DinD for isolated container testing:

```yaml
services:
  docker:
    image: docker:24-dind
    options: --privileged
```

### Service Health Checks

All services include health checks:
- APISIX: `http://localhost:9080/apisix/admin/routes`
- Keycloak: `http://localhost:8080/health`
- PostgreSQL: `pg_isready -U keycloak`

## Artifact Management

### Test Results
- JUnit XML format for test results
- Coverage reports in XML and HTML formats
- Retention: 7 days for test artifacts, 30 days for security reports

### Performance Reports
- Benchmark results in JSON format
- Memory profiling outputs
- Performance trend analysis
- Retention: 90 days

### Security Reports
- SARIF format for GitHub Security integration
- JSON reports for detailed analysis
- Retention: 30-90 days based on severity

## Troubleshooting

### Common Issues

1. **Service startup failures in CI**
   - Check service logs in artifacts
   - Verify health check endpoints
   - Ensure proper network configuration

2. **Platform-specific test failures**
   - Review platform conditions in workflows
   - Check system dependency installation
   - Verify path handling for the platform

3. **Dependency conflicts**
   - Review pip-compile output
   - Check for version pinning issues
   - Verify PyRIT/Garak compatibility

### Debug Mode

Enable debug mode for interactive troubleshooting:

```bash
# Trigger workflow with debug enabled
gh workflow run ci.yml -f debug_enabled=true
```

This provides tmate session access for debugging failures.

### Viewing Logs

1. **GitHub UI**: Actions tab → Select workflow run → View job logs
2. **CLI**: `gh run view <run-id> --log`
3. **Artifacts**: Download logs from workflow artifacts

## Dependency Management

### Dependabot Configuration

Automated dependency updates are configured for:
- Python packages (weekly)
- Docker base images (weekly)
- GitHub Actions (weekly)

### Security Updates

Security updates are prioritized:
- Critical vulnerabilities: Immediate PR
- High severity: Within 24 hours
- Medium/Low: Weekly batch

## Performance Optimization

### Caching Strategy

1. **Python dependencies**: pip cache based on requirements files
2. **Docker layers**: BuildKit cache mounts
3. **Test results**: Incremental test execution

### Parallel Execution

- Test matrix runs in parallel across platforms
- `pytest-xdist` for parallel test execution
- Independent job execution where possible

## Best Practices for Contributors

### Before Submitting a PR

1. Run local formatting: `black . && isort .`
2. Run local tests: `pytest tests/unit`
3. Check for secrets: `detect-secrets scan`
4. Validate Docker files: `hadolint Dockerfile`

### Writing Tests

1. Mark slow tests: `@pytest.mark.slow`
2. Use fixtures for common setup
3. Ensure tests are platform-agnostic
4. Include integration tests for new features

### CI-Friendly Code

1. Avoid hardcoded paths
2. Use environment variables for configuration
3. Handle platform differences gracefully
4. Include proper error messages

## Monitoring and Metrics

### Success Metrics

- CI pipeline success rate: Target >95%
- Average execution time: Target <15 minutes
- Test coverage: Maintain >80%
- Security vulnerabilities: Zero high-severity

### Tracking

- GitHub Actions insights for trends
- Workflow run duration tracking
- Failure rate monitoring
- Security scan results dashboard

## Future Enhancements

1. **Container Registry Integration**
   - Automated Docker image publishing
   - Multi-architecture image builds
   - Security scanning for published images

2. **Advanced Security**
   - SAST integration with custom rules
   - Container security policy enforcement
   - Supply chain security validation

3. **Performance**
   - Distributed test execution
   - Smart test selection
   - Build cache optimization

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [OWASP CI/CD Security](https://owasp.org/www-project-devsecops-guideline/)