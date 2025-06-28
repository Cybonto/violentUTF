# Guide: Testing CI Implementation

This guide explains how to verify that the CI implementation works without errors.

## Quick Verification (Local)

Run the quick check script:
```bash
./scripts/quick_ci_check.sh
```

This verifies:
- ✅ All workflow files exist and have valid YAML
- ✅ Configuration files are in place
- ✅ No hardcoded secrets in workflows
- ✅ All GitHub Actions are pinned to SHA commits
- ✅ Code quality tools work correctly

## Full Verification Process

### Step 1: Commit and Push

```bash
# Add all CI files
git add .github/ docs/guides/Guide_CI* docs/plans/CI_* scripts/ .flake8 pyproject.toml .gitignore

# Commit
git commit -m "Add comprehensive CI/CD workflows

- Multi-platform testing (Ubuntu, macOS, Windows)
- Python 3.10-3.12 version matrix
- Code quality checks (Black, isort, flake8, mypy)
- Security scanning (Bandit, Safety, pip-audit)
- Docker integration testing
- PR automation and comments
- Nightly comprehensive testing"

# Push to your branch
git push origin dev_test
```

### Step 2: Check GitHub Actions

1. Go to: `https://github.com/Cybonto/ViolentUTF/actions`
2. You should see "CI Pipeline" workflow running
3. Click on the workflow run to see details
4. Monitor each job:
   - `test-matrix`: Should run 9 jobs (3 OS × 3 Python versions)
   - `code-quality`: Linting and formatting checks
   - `dependency-security`: Vulnerability scanning
   - `docker-integration`: Service testing
   - `process-results`: Result aggregation
   - `ci-status`: Final status check

### Step 3: Create a Test PR

```bash
# Create a test branch from dev_test
git checkout -b test/ci-validation

# Make a small change
echo "# CI Test File" > ci-test.md
git add ci-test.md
git commit -m "Test CI validation"
git push origin test/ci-validation
```

Then:
1. Go to GitHub and create a PR from `test/ci-validation` to `dev_test`
2. Watch for:
   - "PR Quick Checks" workflow to start
   - PR labels being added (size/XS, etc.)
   - PR comment with check results
   - Status checks appearing on the PR

### Step 4: Test Manual Triggers

Via GitHub UI:
1. Go to Actions → CI Pipeline
2. Click "Run workflow"
3. Select your branch
4. Optionally enable debug mode
5. Click "Run workflow"

Via CLI:
```bash
# Install GitHub CLI if needed
brew install gh  # macOS

# Authenticate
gh auth login

# Trigger workflow
gh workflow run ci.yml --ref dev_test
```

## Expected Results

### Successful CI Run
- All jobs show green checkmarks ✅
- Test results appear in artifacts
- No security vulnerabilities in dependencies
- Code passes all quality checks

### PR Automation
- PR receives automatic labels
- Comment appears with test summary
- Status checks show on PR
- Can't merge until checks pass (if branch protection enabled)

### Artifacts Generated
- Test results (JUnit XML)
- Coverage reports
- Security scan results
- Docker service logs

## Common Issues and Solutions

### 1. Workflows Not Appearing

**Issue**: Workflows don't show in Actions tab

**Solution**:
- Ensure you pushed to a branch that matches trigger patterns
- Check if Actions are enabled in repository settings
- Verify workflow files are in `.github/workflows/`

### 2. Permission Errors

**Issue**: "Resource not accessible by integration"

**Solution**:
- Check repository Settings → Actions → General
- Enable "Read and write permissions"
- Ensure workflow has correct permissions block

### 3. Test Failures

**Issue**: Tests fail in CI but pass locally

**Common causes**:
- Missing environment variables
- Different Python/OS versions
- Timing issues in integration tests
- Docker service not ready

**Debug steps**:
1. Download artifacts from failed run
2. Check logs for specific error
3. Enable debug mode and rerun
4. Use tmate for interactive debugging

### 4. Docker Service Issues

**Issue**: Docker services fail health checks

**Solution**:
- Check service logs in artifacts
- Increase health check timeouts
- Verify no port conflicts
- Check Docker compose syntax

## Monitoring CI Performance

### Execution Time
- Target: <15 minutes for standard CI
- Check Actions → Workflow → Timing

### Success Rate
- Target: >95% success rate
- Monitor trends in Insights → Actions

### Common Bottlenecks
1. Dependency installation (use caching)
2. Docker image pulls (use lighter images)
3. Test execution (use parallel testing)

## Next Steps After Verification

1. **Enable Branch Protection**
   ```
   Settings → Branches → Add rule
   - Require status checks
   - Require branches to be up to date
   - Include administrators
   ```

2. **Set up Notifications**
   - Personal: Settings → Notifications → Actions
   - Team: Use GitHub webhooks or integrations

3. **Optimize Performance**
   - Review slow steps in timing graphs
   - Optimize Docker layer caching
   - Use matrix strategy effectively

4. **Document Issues**
   - Create troubleshooting guide for team
   - Document project-specific quirks
   - Share debug techniques

## Verification Complete! 🎉

When you see:
- ✅ Green workflow runs
- ✅ PR automation working
- ✅ Artifacts being generated
- ✅ Security scans running

Your CI implementation is working correctly!

## Need Help?

- Check workflow logs for detailed errors
- Use debug mode for more verbose output
- Review the [CI/CD Guide](./Guide_CI_CD.md)
- Check GitHub Actions documentation
- Ask in team chat with workflow run link