# ViolentUTF Scripts

This directory contains utility scripts for development, testing, and CI/CD operations.

## Available Scripts

### Docker Validation
- **`validate_docker_builds.sh`** - Validates Docker builds locally (mimics CI/CD process)
  ```bash
  ./scripts/validate_docker_builds.sh [--cleanup] [--help]
  ```

### CI/CD Helpers
- **`ci_docker_helper.sh`** - Helper script for CI/CD Docker operations
- **`quick_ci_check.sh`** - Quick CI validation check
- **`final_ci_check.sh`** - Final CI validation check
- **`fix_ci_issues.sh`** - Fixes common CI issues
- **`verify_ci_implementation.sh`** - Verifies CI implementation

### Code Quality
- **`check_regex_patterns.py`** - Checks regex patterns in code
- **`fix_regex_patterns.py`** - Fixes regex pattern issues
- **`fix_github_actions_yaml.py`** - Fixes GitHub Actions YAML files

### Reporting
- **`generate_dependency_report.py`** - Generates dependency reports
- **`generate_performance_report.py`** - Generates performance reports

### Service Management
- **`wait-for-services.sh`** - Waits for services to be ready

## Usage Examples

### Docker Build Validation
```bash
# Run Docker validation with cleanup
./scripts/validate_docker_builds.sh --cleanup

# Run Docker validation without cleanup
./scripts/validate_docker_builds.sh

# Get help
./scripts/validate_docker_builds.sh --help
```

### CI/CD Pipeline Testing
```bash
# Quick CI check
./scripts/quick_ci_check.sh

# Full CI verification
./scripts/verify_ci_implementation.sh

# Fix CI issues
./scripts/fix_ci_issues.sh
```

### Code Quality Checks
```bash
# Check regex patterns
python scripts/check_regex_patterns.py

# Fix regex patterns
python scripts/fix_regex_patterns.py

# Fix GitHub Actions YAML
python scripts/fix_github_actions_yaml.py
```

## Script Dependencies

Most scripts require:
- Docker and Docker Compose
- Python 3.11+
- Bash shell
- Common Unix utilities (grep, sed, awk, etc.)

Some scripts may require additional dependencies:
- **Docker validation**: trivy (optional, for security scanning)
- **Python scripts**: Various Python packages (see individual scripts)

## Development Guidelines

When adding new scripts:
1. Make scripts executable: `chmod +x script_name.sh`
2. Add appropriate shebang: `#!/bin/bash` or `#!/usr/bin/env python3`
3. Include help/usage information
4. Add error handling and logging
5. Update this README with script documentation

## CI/CD Integration

These scripts are designed to work both locally and in CI/CD pipelines:
- **Local development**: For testing and validation before commits
- **GitHub Actions**: Integrated into `.github/workflows/` for automated testing
- **Docker builds**: For container validation and security scanning

## Security Considerations

All scripts follow security best practices:
- No hardcoded secrets or credentials
- Proper error handling and cleanup
- Secure temporary file handling
- Input validation where applicable
