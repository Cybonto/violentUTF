# CI Implementation Verification Checklist

This document provides a comprehensive checklist to verify that the CI implementation works without errors.

## Pre-Push Verification (Local Testing)

### 1. Syntax Validation ✓

Run the verification script:
```bash
./scripts/verify_ci_implementation.sh
```

Or manually check:

#### GitHub Actions Workflow Syntax
```bash
# Install actionlint
brew install actionlint  # macOS
# or download from https://github.com/rhysd/actionlint

# Validate all workflows
actionlint .github/workflows/*.yml
```

#### YAML Syntax Check
```bash
# Alternative Python-based check
python3 -c "
import yaml
import glob
for file in glob.glob('.github/workflows/*.yml'):
    with open(file) as f:
        yaml.safe_load(f)
    print(f'{file}: OK')
"
```

### 2. Code Quality Tools ✓

Test each tool locally:

```bash
# Install tools
pip install black isort flake8 mypy bandit safety pip-audit

# Test Black formatting
black --check violentutf/ violentutf_api/ tests/

# Test isort
isort --check-only violentutf/ violentutf_api/ tests/

# Test flake8
flake8 violentutf/ violentutf_api/ tests/

# Test mypy (may show some errors due to missing type stubs)
mypy violentutf/ violentutf_api/

# Test bandit security scanning
bandit -r violentutf/ violentutf_api/

# Test dependency scanning
safety check
pip-audit
```

### 3. Docker Environment ✓

```bash
# Verify Docker is installed and running
docker --version
docker compose version
docker ps

# Test Docker Compose configuration
docker compose -f docker-compose.yml config > /dev/null
echo "Docker Compose configuration is valid"
```

### 4. Local GitHub Actions Testing with `act` ✓

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or see https://github.com/nektos/act

# List available workflows and jobs
act -l

# Test specific jobs locally (requires Docker)
# Note: Use smaller images for faster testing
act -j code-quality -P ubuntu-22.04=ghcr.io/catthehacker/ubuntu:act-22.04

# Dry run to see what would execute
act -n
```

## Post-Push Verification (GitHub Testing)

### 1. Initial Push Testing

After pushing to your branch:

```bash
# Push to your branch
git add .
git commit -m "Add CI/CD workflows"
git push origin dev_test
```

Check GitHub Actions tab:
1. Go to: `https://github.com/Cybonto/ViolentUTF/actions`
2. Look for workflows running on your branch
3. Verify each workflow shows up:
   - CI Pipeline
   - PR Quick Checks (only on PRs)
   - Nightly CI (only on schedule)

### 2. Create a Test PR

```bash
# Create a test branch
git checkout -b test/ci-verification
echo "# CI Test" > test-ci.md
git add test-ci.md
git commit -m "Test CI workflows"
git push origin test/ci-verification
```

Then create a PR and verify:
- [ ] PR Quick Checks workflow triggers
- [ ] PR receives size label
- [ ] PR comment with check results appears
- [ ] All status checks show in PR

### 3. Manual Workflow Trigger

Test manual workflow dispatch:

```bash
# Using GitHub CLI
gh workflow run ci.yml --ref dev_test

# With debug enabled
gh workflow run ci.yml --ref dev_test -f debug_enabled=true
```

Or via GitHub UI:
1. Go to Actions tab
2. Select "CI Pipeline"
3. Click "Run workflow"
4. Select branch and options

## Common Issues and Solutions

### Issue 1: Workflow Not Triggering

**Symptoms**: Workflows don't appear in Actions tab

**Solutions**:
- Verify workflows are in `.github/workflows/` directory
- Check branch protection rules
- Ensure workflows are on default branch or explicitly configured branch
- Check workflow triggers match your branch name pattern

### Issue 2: Permission Errors

**Symptoms**: Workflows fail with permission denied

**Solutions**:
- Check repository Settings → Actions → General
- Ensure "Read and write permissions" is enabled
- Verify GITHUB_TOKEN permissions in workflow

### Issue 3: Python Dependencies Fail

**Symptoms**: pip install fails in CI

**Solutions**:
- Test installation locally first
- Check for platform-specific dependencies
- Verify all requirements files exist
- Consider using pip-compile for locked dependencies

### Issue 4: Docker Service Failures

**Symptoms**: Docker services don't start or health checks fail

**Solutions**:
- Increase health check timeouts
- Check service logs in workflow artifacts
- Verify port conflicts
- Test docker-compose locally

### Issue 5: Test Failures

**Symptoms**: Tests pass locally but fail in CI

**Solutions**:
- Check for hardcoded paths
- Verify environment variables
- Look for timing/race conditions
- Check platform-specific issues

## Verification Commands Summary

```bash
# Quick local verification
./scripts/verify_ci_implementation.sh

# Manual workflow syntax check
for f in .github/workflows/*.yml; do
  echo "Checking $f..."
  python3 -c "import yaml; yaml.safe_load(open('$f'))"
done

# Test Python tools
black --check . && echo "Black: OK"
isort --check-only . && echo "isort: OK"
flake8 . && echo "flake8: OK"

# Check for secrets
grep -r "api_key\|password\|secret\|token" .github/workflows/ | \
  grep -v "GITHUB_TOKEN\|secrets\." | \
  grep -v "^#" || echo "No hardcoded secrets found"

# Verify all workflows are pinned
grep -r "uses:.*@" .github/workflows/ | \
  grep -v "@[a-f0-9]\{40\}" || echo "All actions properly pinned"
```

## Success Indicators

When everything is working correctly, you should see:

1. **Green checkmarks** on all workflow runs in Actions tab
2. **PR comments** automatically added with test results
3. **Status checks** showing on PRs
4. **Artifacts** available for download (test results, coverage reports)
5. **Security alerts** in Security tab if vulnerabilities found
6. **Dependabot PRs** appearing weekly for updates

## Next Steps After Verification

1. **Monitor Initial Runs**: Watch the first few workflow runs carefully
2. **Review Logs**: Check workflow logs for any warnings
3. **Optimize Performance**: Identify slow steps and optimize
4. **Set Branch Protection**: Require CI checks to pass before merging
5. **Document Issues**: Create troubleshooting docs for team

## Support Resources

- GitHub Actions Documentation: https://docs.github.com/actions
- GitHub Actions Status: https://www.githubstatus.com/
- Community Forum: https://github.community/c/code-to-cloud/github-actions/
- ViolentUTF CI Guide: `/docs/guides/Guide_CI_CD.md`