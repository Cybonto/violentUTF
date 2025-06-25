# GitHub Directory Structure Implementation Plan

## Objective
Create a complete `.github` directory structure for ViolentUTF repository following GitHub best practices.

## Pre-Implementation Checklist
- [ ] Ensure you have write access to the repository
- [ ] Back up any existing GitHub-related files
- [ ] Review current branch structure
- [ ] Coordinate with team on timing

## Step-by-Step Execution Plan

### Step 1: Create Base Directory Structure
```bash
# Create the main .github directory
mkdir -p .github

# Create subdirectories
mkdir -p .github/workflows
mkdir -p .github/ISSUE_TEMPLATE
```

### Step 2: Create Workflow Files

#### 2.1 Continuous Integration Workflow
Create `.github/workflows/ci.yml`:
```bash
touch .github/workflows/ci.yml
```

Content from improvement_github.md (lines 52-96) with these adjustments:
- Update Python versions if needed based on project requirements
- Verify paths to requirements.txt files
- Add any project-specific test commands

#### 2.2 Docker Publishing Workflow
Create `.github/workflows/docker-publish.yml`:
```bash
touch .github/workflows/docker-publish.yml
```

Content from improvement_github.md (lines 98-144) with adjustments:
- Update Docker context paths for ViolentUTF
- Add multiple image builds for different services

#### 2.3 Security Scanning Workflow
Create `.github/workflows/security.yml`:
```bash
touch .github/workflows/security.yml
```

Content from improvement_github.md (lines 146-187) with adjustments:
- Add paths to ignore (e.g., test data, documentation)
- Configure Bandit to skip false positives

#### 2.4 Release Automation Workflow
Create `.github/workflows/release.yml`:
```bash
touch .github/workflows/release.yml
```

Use the release workflow template from improvement_github.md with project-specific release steps.

### Step 3: Create Issue Templates

#### 3.1 Bug Report Template
Create `.github/ISSUE_TEMPLATE/bug_report.yml`:
```bash
touch .github/ISSUE_TEMPLATE/bug_report.yml
```

Use the template structure from improvement_github.md with ViolentUTF-specific fields:
- Add fields for affected components (PyRIT, Garak, IronUTF, etc.)
- Include AI provider information
- Add Docker/container environment details

#### 3.2 Feature Request Template
Create `.github/ISSUE_TEMPLATE/feature_request.yml`:
```bash
touch .github/ISSUE_TEMPLATE/feature_request.yml
```

Customize for ViolentUTF:
- Add security testing use case fields
- Include integration requirements
- Add performance considerations

#### 3.3 Security Vulnerability Template
Create `.github/ISSUE_TEMPLATE/security_vulnerability.yml`:
```bash
touch .github/ISSUE_TEMPLATE/security_vulnerability.yml
```

Important: This should include clear warnings about responsible disclosure.

#### 3.4 Issue Template Configuration
Create `.github/ISSUE_TEMPLATE/config.yml`:
```yaml
blank_issues_enabled: false
contact_links:
  - name: Security Issues
    url: mailto:security@example.com
    about: Please report security vulnerabilities via email
  - name: Documentation
    url: https://github.com/cybonto/ViolentUTF/tree/main/docs
    about: Check our documentation for common questions
```

### Step 4: Create Pull Request Template
Create `.github/PULL_REQUEST_TEMPLATE.md`:
```bash
touch .github/PULL_REQUEST_TEMPLATE.md
```

Use template from improvement_github.md with additions:
- Security review checklist
- API compatibility check
- Docker image update requirements

### Step 5: Create Automation Configuration Files

#### 5.1 Dependabot Configuration
Create `.github/dependabot.yml`:
```bash
touch .github/dependabot.yml
```

Use configuration from improvement_github.md with all Python requirement paths.

#### 5.2 CODEOWNERS File
Create `.github/CODEOWNERS`:
```bash
touch .github/CODEOWNERS
```

Replace generic teams with actual GitHub usernames/teams.

#### 5.3 Labels Configuration
Create `.github/labels.yml`:
```yaml
# Priority
- name: "priority: critical"
  color: "ff0000"
  description: "Critical priority issue"
- name: "priority: high"
  color: "ff6600"
  description: "High priority issue"
- name: "priority: medium"
  color: "ffcc00"
  description: "Medium priority issue"
- name: "priority: low"
  color: "33cc33"
  description: "Low priority issue"

# Type
- name: "type: bug"
  color: "d73a4a"
  description: "Something isn't working"
- name: "type: feature"
  color: "0075ca"
  description: "New feature or request"
- name: "type: security"
  color: "ff0000"
  description: "Security related issue"
- name: "type: documentation"
  color: "0052cc"
  description: "Documentation improvements"

# Component
- name: "component: pyrit"
  color: "5319e7"
  description: "PyRIT integration"
- name: "component: garak"
  color: "5319e7"
  description: "Garak integration"
- name: "component: api"
  color: "5319e7"
  description: "API related"
- name: "component: ui"
  color: "5319e7"
  description: "Streamlit UI"
```

### Step 6: Create Optional Files

#### 6.1 Funding Configuration (Optional)
Create `.github/FUNDING.yml`:
```yaml
# These are supported funding model platforms
github: [cybonto]
custom: ["https://example.com/donate"]
```

### Step 7: Verify and Test

#### 7.1 File Structure Verification
```bash
# Verify directory structure
tree .github/

# Expected output:
# .github/
# ├── workflows/
# │   ├── ci.yml
# │   ├── docker-publish.yml
# │   ├── security.yml
# │   └── release.yml
# ├── ISSUE_TEMPLATE/
# │   ├── bug_report.yml
# │   ├── feature_request.yml
# │   ├── security_vulnerability.yml
# │   └── config.yml
# ├── PULL_REQUEST_TEMPLATE.md
# ├── dependabot.yml
# ├── CODEOWNERS
# ├── labels.yml
# └── FUNDING.yml
```

#### 7.2 Workflow Syntax Validation
```bash
# Install act for local GitHub Actions testing
brew install act  # macOS
# or
# sudo apt install act  # Linux

# Validate workflow syntax
act -l
```

#### 7.3 YAML Validation
```bash
# Install yamllint
pip install yamllint

# Validate all YAML files
yamllint .github/
```

### Step 8: Commit and Push

```bash
# Stage all new files
git add .github/

# Commit with descriptive message
git commit -m "feat: Add GitHub directory structure and workflows

- Add CI/CD workflows for testing, Docker, and security
- Add issue and PR templates
- Configure Dependabot for dependency management
- Add CODEOWNERS file
- Set up release automation"

# Push to feature branch
git checkout -b feature/github-structure
git push origin feature/github-structure
```

### Step 9: Post-Implementation Tasks

1. **Create Pull Request**
   - Use the new PR template
   - Request review from team members

2. **Configure Repository Settings**
   - Enable GitHub Actions
   - Configure secrets (if needed)
   - Set up branch protection rules

3. **Test Workflows**
   - Create a test PR to trigger CI
   - Verify all checks pass
   - Test issue templates

4. **Documentation Updates**
   - Update README.md to mention CI/CD
   - Add workflow status badges
   - Document contribution process

## Timeline
- **Day 1**: Create directory structure and workflow files
- **Day 2**: Create templates and configuration files
- **Day 3**: Test and validate all files
- **Day 4**: Submit PR and gather feedback
- **Day 5**: Address feedback and merge

## Success Criteria
- [ ] All workflow files pass syntax validation
- [ ] CI workflow runs successfully on PR
- [ ] Issue templates appear correctly in GitHub
- [ ] PR template loads automatically
- [ ] Team approves structure and content

## Rollback Plan
If issues arise:
1. Remove `.github` directory: `rm -rf .github`
2. Restore from backup if any files were overwritten
3. Document lessons learned
4. Revise approach based on feedback

## Notes
- Start with minimal workflows and expand based on needs
- Monitor GitHub Actions usage to stay within limits
- Regular review and updates of workflows quarterly
- Consider adding workflow dispatch for manual triggers