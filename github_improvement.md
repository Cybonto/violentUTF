# GitHub Repository Standards Improvement Plan for ViolentUTF

## Executive Summary

This document outlines a comprehensive plan to bring the ViolentUTF repository up to GitHub best practices and industry standards. The improvements focus on automation, collaboration, security, and developer experience.

## Current State Assessment

### ✅ Existing Strengths
- **Documentation**: Well-structured README with clear setup instructions
- **License**: MIT license properly included
- **Version Control**: Proper .gitignore files excluding sensitive data
- **Architecture**: Clean project structure with Docker containerization
- **Platform Support**: Cross-platform setup scripts (macOS, Linux, Windows)

### ❌ Missing GitHub Standards
- No `.github` directory structure
- No CI/CD workflows (GitHub Actions)
- No issue or pull request templates
- Missing `CONTRIBUTING.md` (referenced but not present)
- No `CODE_OF_CONDUCT.md`
- No `SECURITY.md` policy
- No automated dependency management
- No branch protection rules or CODEOWNERS

## Detailed Implementation Plan

### 1. GitHub Directory Structure (High Priority)

Create the following directory structure:

```
.github/
├── workflows/                    # CI/CD pipelines
│   ├── ci.yml                   # Continuous Integration
│   ├── docker-publish.yml       # Docker image publishing
│   ├── security.yml             # Security scanning
│   └── release.yml              # Release automation
├── ISSUE_TEMPLATE/              # Issue templates
│   ├── bug_report.yml           # Bug report form
│   ├── feature_request.yml      # Feature request form
│   └── security_vulnerability.yml # Security issue form
├── PULL_REQUEST_TEMPLATE.md     # PR template
├── dependabot.yml               # Dependency updates
├── CODEOWNERS                   # Code ownership
├── FUNDING.yml                  # Sponsorship (optional)
└── labels.yml                   # Label configuration
```

### 2. CI/CD Workflows (High Priority)

#### a. Continuous Integration Workflow (`.github/workflows/ci.yml`)
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r violentutf/requirements.txt
        pip install -r violentutf_api/fastapi_app/requirements.txt
    
    - name: Run linting
      run: |
        pip install flake8 black isort
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        black --check .
        isort --check-only .
    
    - name: Run tests
      run: |
        cd tests
        python -m pytest -v
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
```

#### b. Docker Build and Publish (`.github/workflows/docker-publish.yml`)
```yaml
name: Docker

on:
  push:
    branches: [ main ]
    tags: [ 'v*.*.*' ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Log in to the Container registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
```

#### c. Security Scanning (`.github/workflows/security.yml`)
```yaml
name: Security

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0'  # Weekly scan

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
    
    - name: Run Bandit security linter
      run: |
        pip install bandit
        bandit -r violentutf/ violentutf_api/ -f json -o bandit-results.json
    
    - name: Upload Bandit results
      uses: actions/upload-artifact@v3
      with:
        name: bandit-results
        path: bandit-results.json
```

### 3. Community Standards Files (High Priority)

#### a. CONTRIBUTING.md
```markdown
# Contributing to ViolentUTF

Thank you for your interest in contributing to ViolentUTF! This document provides guidelines for contributing to the project.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/cybonto/ViolentUTF/issues)
2. If not, create a new issue using the bug report template
3. Include detailed steps to reproduce, expected behavior, and actual behavior
4. Add relevant logs, screenshots, or error messages

### Suggesting Features

1. Check if the feature has already been requested
2. Create a new issue using the feature request template
3. Explain the use case and how it benefits users
4. Be open to discussion and feedback

### Submitting Pull Requests

1. Fork the repository
2. Create a new branch from `main`: `git checkout -b feature/your-feature-name`
3. Make your changes following our coding standards
4. Write or update tests as needed
5. Update documentation if required
6. Commit with clear, descriptive messages
7. Push to your fork and submit a pull request

### Development Setup

See the main [README.md](README.md) for setup instructions.

### Coding Standards

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for all functions and classes
- Keep functions focused and single-purpose
- Add tests for new functionality

### Testing

- Run tests locally before submitting PR: `pytest tests/`
- Ensure all tests pass
- Add new tests for new features
- Maintain or improve code coverage

### Documentation

- Update README.md if adding new features
- Add docstrings to new functions/classes
- Update API documentation if changing endpoints
- Include examples where helpful

## Review Process

1. All submissions require review before merging
2. Reviewers will provide feedback within 3-5 business days
3. Address feedback and push updates to your PR branch
4. Once approved, maintainers will merge your contribution

## Recognition

Contributors will be recognized in our [Contributors](https://github.com/cybonto/ViolentUTF/graphs/contributors) page.

Thank you for helping make ViolentUTF better!
```

#### b. CODE_OF_CONDUCT.md
```markdown
# Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, color, religion, or sexual identity and orientation.

## Our Standards

Examples of behavior that contributes to a positive environment:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior:

* The use of sexualized language or imagery, and sexual attention or advances
* Trolling, insulting or derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information without explicit permission
* Other conduct which could reasonably be considered inappropriate

## Enforcement Responsibilities

Project maintainers are responsible for clarifying and enforcing our standards of acceptable behavior and will take appropriate and fair corrective action in response to any behavior that they deem inappropriate, threatening, offensive, or harmful.

## Scope

This Code of Conduct applies within all community spaces, and also applies when an individual is officially representing the community in public spaces.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the community leaders responsible for enforcement at [INSERT CONTACT EMAIL].

All complaints will be reviewed and investigated promptly and fairly.

## Enforcement Guidelines

Community leaders will follow these guidelines in determining consequences:

### 1. Correction
**Community Impact**: Use of inappropriate language or other behavior deemed unprofessional.
**Consequence**: A private, written warning providing clarity around the nature of the violation.

### 2. Warning
**Community Impact**: A violation through a single incident or series of actions.
**Consequence**: A warning with consequences for continued behavior.

### 3. Temporary Ban
**Community Impact**: A serious violation of community standards.
**Consequence**: A temporary ban from any sort of interaction or public communication with the community.

### 4. Permanent Ban
**Community Impact**: Demonstrating a pattern of violation of community standards.
**Consequence**: A permanent ban from any sort of public interaction within the community.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 2.1, available at [https://www.contributor-covenant.org/version/2/1/code_of_conduct.html][v2.1].

[homepage]: https://www.contributor-covenant.org
[v2.1]: https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
```

#### c. SECURITY.md
```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

We take the security of ViolentUTF seriously. If you have discovered a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Security vulnerabilities should not be reported through public GitHub issues.

### 2. Report Privately

Please report security vulnerabilities by emailing: [INSERT SECURITY EMAIL]

Include the following information:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue

### 3. Response Timeline

- We will acknowledge receipt within 48 hours
- We will provide a detailed response within 7 days
- We will work on a fix and coordinate disclosure

### 4. Disclosure Policy

- We follow responsible disclosure practices
- We will credit researchers who report valid vulnerabilities
- We request 90 days before public disclosure to allow patching

## Security Best Practices

When using ViolentUTF:

1. **API Keys**: Never commit API keys to the repository
2. **Environment Variables**: Use `.env` files for sensitive configuration
3. **Authentication**: Always use strong passwords and enable 2FA where possible
4. **Updates**: Keep all dependencies up to date
5. **Network**: Use HTTPS for all communications
6. **Logging**: Ensure logs don't contain sensitive information

## Security Features

ViolentUTF includes several security features:

- JWT-based authentication
- Keycloak SSO integration
- API rate limiting
- Input validation and sanitization
- Secure session management
- Encrypted communications

## Contact

For security concerns, contact: [INSERT SECURITY EMAIL]

For general support, see our [support documentation](docs/README.md).
```

### 4. Issue and PR Templates (Medium Priority)

#### a. Bug Report (`.github/ISSUE_TEMPLATE/bug_report.yml`)
```yaml
name: Bug Report
description: File a bug report
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: A clear and concise description of what the bug is.
      placeholder: Tell us what you see!
    validations:
      required: true
  
  - type: dropdown
    id: version
    attributes:
      label: Version
      description: What version of ViolentUTF are you running?
      options:
        - 0.2 (Latest)
        - 0.1
        - Development (main branch)
    validations:
      required: true
  
  - type: dropdown
    id: os
    attributes:
      label: Operating System
      options:
        - macOS
        - Linux
        - Windows
        - Docker
    validations:
      required: true
  
  - type: textarea
    id: reproduce
    attributes:
      label: Steps to Reproduce
      description: Steps to reproduce the behavior
      value: |
        1. 
        2. 
        3. 
    validations:
      required: true
  
  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: What did you expect to happen?
    validations:
      required: true
  
  - type: textarea
    id: logs
    attributes:
      label: Relevant Logs
      description: Please copy and paste any relevant log output.
      render: shell
```

#### b. Feature Request (`.github/ISSUE_TEMPLATE/feature_request.yml`)
```yaml
name: Feature Request
description: Suggest an idea for ViolentUTF
title: "[Feature]: "
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for suggesting a feature for ViolentUTF!
  
  - type: textarea
    id: problem
    attributes:
      label: Problem Description
      description: Is your feature request related to a problem?
      placeholder: A clear description of the problem...
    validations:
      required: true
  
  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
      description: Describe the solution you'd like
    validations:
      required: true
  
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives
      description: Describe alternatives you've considered
  
  - type: dropdown
    id: importance
    attributes:
      label: Importance
      options:
        - Critical for my use case
        - Would significantly improve my workflow
        - Nice to have
        - Just an idea
```

#### c. Pull Request Template (`.github/PULL_REQUEST_TEMPLATE.md`)
```markdown
## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Related Issues

Fixes #(issue number)

## Changes Made

- 
- 
- 

## Testing

- [ ] I have tested these changes locally
- [ ] All existing tests pass
- [ ] I have added tests for new functionality
- [ ] I have tested edge cases

## Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Screenshots (if applicable)

Add screenshots to help explain your changes.

## Additional Notes

Add any additional notes or context about the PR here.
```

### 5. Automation Configuration (Medium Priority)

#### a. Dependabot (`.github/dependabot.yml`)
```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/violentutf"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "python"
  
  - package-ecosystem: "pip"
    directory: "/violentutf_api/fastapi_app"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "python"
      - "api"
  
  # Docker dependencies
  - package-ecosystem: "docker"
    directory: "/violentutf"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"
  
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "github-actions"
```

#### b. CODEOWNERS (`.github/CODEOWNERS`)
```
# Global owners
* @cybonto/core-team

# Documentation
/docs/ @cybonto/docs-team
*.md @cybonto/docs-team

# API
/violentutf_api/ @cybonto/api-team

# Security-critical files
/violentutf/scorers/ @cybonto/security-team
/violentutf/orchestrators/ @cybonto/security-team
SECURITY.md @cybonto/security-team

# CI/CD
/.github/ @cybonto/devops-team

# Core application
/violentutf/ @cybonto/core-team
```

### 6. Branch Protection Rules (To be configured in GitHub settings)

Configure the following for the `main` branch:

- **Require pull request reviews**: 2 approvals required
- **Dismiss stale pull request approvals**
- **Require review from CODEOWNERS**
- **Require status checks to pass**: CI, Security, Docker
- **Require branches to be up to date**
- **Include administrators**
- **Restrict who can push**: Only maintainers
- **Do not allow force pushes**
- **Do not allow deletions**

### 7. Release Automation (Low Priority)

#### Release Workflow (`.github/workflows/release.yml`)
```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Generate changelog
      id: changelog
      uses: conventional-changelog-action@v3
      with:
        github-token: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref_name }}
        release_name: Release ${{ github.ref_name }}
        body: ${{ steps.changelog.outputs.clean_changelog }}
        draft: false
        prerelease: false
```

## Implementation Timeline

### Phase 1 (Week 1-2)
- Create `.github` directory structure
- Implement basic CI workflow
- Add CONTRIBUTING.md, CODE_OF_CONDUCT.md, and SECURITY.md

### Phase 2 (Week 3-4)
- Set up Docker publishing workflow
- Add security scanning
- Create issue and PR templates

### Phase 3 (Week 5-6)
- Configure Dependabot
- Set up CODEOWNERS
- Implement branch protection rules

### Phase 4 (Week 7-8)
- Add release automation
- Set up changelog generation
- Fine-tune all workflows based on team feedback

## Success Metrics

- **CI/CD**: All PRs must pass automated checks
- **Security**: Weekly vulnerability scans with < 24h response time
- **Community**: 50% reduction in incomplete issue reports
- **Automation**: 80% reduction in manual release work
- **Quality**: Maintain > 80% test coverage

## Maintenance Plan

- **Weekly**: Review Dependabot PRs
- **Monthly**: Update security policies and dependencies
- **Quarterly**: Review and update workflows
- **Annually**: Major template and process review

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)

---

*This document should be reviewed and updated regularly to ensure it reflects current best practices and project needs.*