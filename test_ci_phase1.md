# Phase 1 CI/CD Testing Checklist

## 1. Linting Stage Verification

### What to Check:
- [ ] Flake8 runs and reports syntax errors
- [ ] Black checks code formatting
- [ ] isort validates import ordering
- [ ] Cache is properly utilized (check for "Cache hit" in logs)

### Common Issues:
- If flake8 fails: Check for Python syntax errors
- If black fails: Run `black violentutf/ violentutf_api/ tests/` locally
- If isort fails: Run `isort violentutf/ violentutf_api/ tests/` locally

## 2. Test Matrix Verification

### What to Check:
- [ ] Tests run on Python 3.10
- [ ] Tests run on Python 3.11
- [ ] Tests run on Python 3.12
- [ ] PostgreSQL service starts successfully
- [ ] Test databases are created
- [ ] Coverage reports are generated

### Verify Coverage:
- Look for "Coverage: XX%" in the logs
- Should be ≥ 80% to pass
- HTML coverage report uploaded as artifact

### Common Issues:
- If tests fail: Check test output for specific failures
- If coverage < 80%: Add more tests or adjust threshold temporarily

## 3. Integration Test Verification

### What to Check:
- [ ] Keycloak container starts
- [ ] APISIX container starts
- [ ] Services are accessible
- [ ] Integration tests pass
- [ ] Services properly shut down

### Common Issues:
- If services fail to start: Check Docker daemon is running
- If tests timeout: Services may need more startup time

## 4. Security Scan Verification

### What to Check:
- [ ] Bandit completes scanning
- [ ] Safety checks dependencies
- [ ] Security report artifact is generated
- [ ] No high-severity issues block the build

### Common Issues:
- If Bandit fails: Review security issues in the report
- If Safety fails: Update vulnerable dependencies

## 5. PR Testing (Create a Pull Request)

### Steps:
1. Create PR from test branch to main
2. Verify CI runs on the PR
3. Check for status comment on PR

### What to Check:
- [ ] All required checks appear on PR
- [ ] Status comment is posted
- [ ] Merge is blocked until checks pass

## 6. Docker Build Stage (Main Branch Only)

### What to Check:
- [ ] Docker build only runs on main branch pushes
- [ ] Both Streamlit and API images build successfully
- [ ] Build cache is utilized

### To Test:
- This requires merging to main or modifying workflow to test on other branches

## Local Testing Commands

### Run CI checks locally before pushing:

```bash
# Linting
pip install flake8 black isort
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
black --check violentutf/ violentutf_api/ tests/
isort --check-only violentutf/ violentutf_api/ tests/

# Unit tests
cd tests
python -m pytest unit/ -v

# Security
pip install bandit safety
bandit -r violentutf/ violentutf_api/
safety check -r violentutf/requirements.txt -r violentutf_api/fastapi_app/requirements.txt
```

## Success Criteria

Phase 1 is successful when:
- [ ] All CI stages pass on feature branch push
- [ ] PR checks prevent merge of failing code
- [ ] Coverage meets 80% threshold
- [ ] Security scans complete without critical issues
- [ ] Integration tests pass with all services
- [ ] Artifacts (coverage, security reports) are accessible

## Troubleshooting Resources

1. **GitHub Actions Tab**: Check workflow run logs
2. **Artifacts**: Download coverage and security reports
3. **Local Testing**: Run checks locally to debug
4. **Workflow File**: Review `.github/workflows/ci.yml` for configuration

## Next Steps After Success

1. Document any issues encountered
2. Update workflow if adjustments needed
3. Train team on CI process
4. Plan Phase 2 implementation