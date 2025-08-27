# Pre-commit Hooks Improvement Plan for ViolentUTF

## Executive Summary
This plan outlines comprehensive improvements to the pre-commit hook system to prevent file path issues, enforce code quality standards, and ensure cross-platform compatibility, particularly for Windows systems.

## Current Issues Identified
1. Files with spaces in names causing Windows checkout failures
2. Sensitive files (like `.env copy`) being accidentally committed
3. No automated checks for path compatibility
4. Limited code quality enforcement

## Proposed Pre-commit Hook Architecture

### 1. Core Infrastructure
```yaml
# .pre-commit-config.yaml
default_language_version:
  python: python3.11

repos:
  # 1. Path and Filename Validation
  - repo: local
    hooks:
      - id: check-filenames
        name: Check for problematic filenames
        entry: scripts/check_filenames.py
        language: python
        pass_filenames: true

      - id: check-path-length
        name: Check for excessively long paths
        entry: scripts/check_path_length.py
        language: python
        pass_filenames: true

  # 2. Security and Sensitive Data
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: local
    hooks:
      - id: check-env-files
        name: Prevent .env file commits
        entry: scripts/check_env_files.py
        language: python
        files: '\.(env|env\..*)$'

  # 3. Code Quality - Python
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
        args: ['--line-length=120']

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ['--profile', 'black', '--line-length', '120']

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        additional_dependencies:
          - flake8-docstrings
          - flake8-annotations
        args: ['--max-line-length=120', '--extend-ignore=E203,W503']

  # 4. Security Scanning
  - repo: https://github.com/pycqa/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-r', '.', '-ll', '-i', '-x', 'tests']

  # 5. YAML/JSON Validation
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-xml
      - id: pretty-format-json
        args: ['--autofix', '--indent=2']

  # 6. General File Checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-symlinks
      - id: destroyed-symlinks
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: mixed-line-ending
        args: ['--fix=lf']

  # 7. Commit Message Validation
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen
        stages: [commit-msg]

  # 8. Docker and Infrastructure
  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint-docker
        entry: hadolint/hadolint:v2.12.0 hadolint
        language: docker_image
        types: [dockerfile]

  # 9. Shell Script Validation
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.9.0.6
    hooks:
      - id: shellcheck

  # 10. Markdown Linting
  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: v0.38.0
    hooks:
      - id: markdownlint
        args: ['--fix']
```

### 2. Custom Scripts

#### scripts/check_filenames.py
```python
#!/usr/bin/env python3
"""Check for problematic filenames that could cause issues on different platforms."""

import sys
import re
from pathlib import Path

# Patterns that cause issues
PROBLEMATIC_PATTERNS = [
    (r'[ ]{2,}', 'Multiple consecutive spaces'),
    (r'[ ]/|/[ ]', 'Spaces around path separators'),
    (r'^[ ]|[ ]$', 'Leading or trailing spaces'),
    (r'[<>:|?*"]', 'Windows-incompatible characters'),
    (r'[\x00-\x1f\x7f]', 'Control characters'),
    (r'\.{2,}', 'Multiple consecutive dots'),
    (r'[ ]\.(py|json|yaml|yml|txt|csv|md)$', 'Space before file extension'),
]

# Reserved Windows filenames
WINDOWS_RESERVED = [
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
]

def check_file(filepath):
    """Check a single file for naming issues."""
    path = Path(filepath)
    issues = []

    # Check filename
    filename = path.name

    # Check for problematic patterns
    for pattern, description in PROBLEMATIC_PATTERNS:
        if re.search(pattern, filename):
            issues.append(f"{description}: {filename}")

    # Check for Windows reserved names
    name_without_ext = path.stem.upper()
    if name_without_ext in WINDOWS_RESERVED:
        issues.append(f"Windows reserved filename: {filename}")

    # Check full path for spaces
    if ' /' in str(path) or '/ ' in str(path):
        issues.append(f"Spaces around path separator in: {path}")

    return issues

def main():
    """Main function to check all provided files."""
    files = sys.argv[1:]
    all_issues = []

    for filepath in files:
        issues = check_file(filepath)
        if issues:
            all_issues.extend([(filepath, issue) for issue in issues])

    if all_issues:
        print("❌ Filename validation failed!\n")
        for filepath, issue in all_issues:
            print(f"  {filepath}: {issue}")
        print("\nPlease rename these files to be cross-platform compatible.")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

#### scripts/check_path_length.py
```python
#!/usr/bin/env python3
"""Check for excessively long file paths."""

import sys
from pathlib import Path

# Maximum path lengths
MAX_PATH_WINDOWS = 260
MAX_PATH_RECOMMENDED = 200  # Leave buffer for operations

def main():
    """Check all provided files for path length issues."""
    files = sys.argv[1:]
    issues = []

    for filepath in files:
        path_length = len(str(Path(filepath).absolute()))

        if path_length > MAX_PATH_WINDOWS:
            issues.append((filepath, path_length, "exceeds Windows limit"))
        elif path_length > MAX_PATH_RECOMMENDED:
            issues.append((filepath, path_length, "close to Windows limit"))

    if issues:
        print("⚠️  Path length issues detected!\n")
        for filepath, length, reason in issues:
            print(f"  {filepath} ({length} chars) - {reason}")
        print(f"\nWindows max: {MAX_PATH_WINDOWS} chars")
        print(f"Recommended max: {MAX_PATH_RECOMMENDED} chars")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

#### scripts/check_env_files.py
```python
#!/usr/bin/env python3
"""Prevent accidental commits of .env files and their variants."""

import sys
from pathlib import Path

ALLOWED_ENV_FILES = [
    '.env.example',
    '.env.template',
    '.env.sample',
    'env.sample',
]

def main():
    """Check for .env files that shouldn't be committed."""
    files = sys.argv[1:]
    blocked_files = []

    for filepath in files:
        path = Path(filepath)
        if path.name not in ALLOWED_ENV_FILES:
            blocked_files.append(filepath)

    if blocked_files:
        print("🚫 Environment files cannot be committed!\n")
        for filepath in blocked_files:
            print(f"  ❌ {filepath}")
        print("\nThese files may contain sensitive credentials.")
        print("Use .env.example or .env.template for templates.")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3. Implementation Steps

1. **Phase 1: Initial Setup (Week 1)**
   - Install pre-commit framework: `pip install pre-commit`
   - Create `.pre-commit-config.yaml` with basic hooks
   - Create custom scripts directory
   - Test with existing codebase

2. **Phase 2: Custom Scripts (Week 2)**
   - Implement filename validation script
   - Implement path length checker
   - Implement .env file blocker
   - Add regex pattern validation script

3. **Phase 3: Integration (Week 3)**
   - Configure all hooks in `.pre-commit-config.yaml`
   - Run on entire codebase and fix issues
   - Update CI/CD to run pre-commit checks
   - Document for developers

4. **Phase 4: Team Adoption (Week 4)**
   - Training session for development team
   - Create troubleshooting guide
   - Set up automatic installation in development setup
   - Monitor and adjust based on feedback

### 4. CI/CD Integration

Add to `.github/workflows/pr-validation.yml`:
```yaml
  pre-commit:
    name: Pre-commit Checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run pre-commit
        uses: pre-commit/action@v3.0.0
```

### 5. Developer Setup

Add to setup scripts:
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

### 6. Benefits

1. **Prevents Windows Compatibility Issues**
   - Blocks files with spaces and special characters
   - Enforces cross-platform naming conventions
   - Catches issues before they reach the repository

2. **Improves Code Quality**
   - Automatic formatting with Black and isort
   - Consistent code style across the team
   - Early detection of code issues

3. **Enhances Security**
   - Prevents credential leaks
   - Scans for security vulnerabilities
   - Blocks sensitive file patterns

4. **Reduces CI/CD Failures**
   - Catches issues locally before push
   - Reduces failed builds
   - Saves developer time

### 7. Success Metrics

- 90% reduction in Windows-related CI/CD failures
- 0 credential leaks in commits
- 50% reduction in code review comments about formatting
- 100% adoption rate among developers

### 8. Maintenance

- Monthly review of hook effectiveness
- Quarterly update of hook versions
- Continuous improvement based on team feedback
- Regular training for new team members

## Conclusion

This comprehensive pre-commit hook system will significantly improve code quality, prevent platform-specific issues, and enhance security. The investment in setup time will be quickly recovered through reduced debugging and failed builds.
