# CI/CD Regex Pattern Protection Plan

## Problem Statement
During CI/CD security scans or automated code fixes, regex patterns were incorrectly modified by adding spaces within character ranges (e.g., `[A-Z]` became `[A - Z]`), causing runtime failures. This broke JWT authentication and other validation logic.

## Root Cause Analysis
1. **Security scanners** may flag long strings or complex patterns as potential security risks
2. **Auto-formatting tools** may attempt to "improve readability" by adding spaces
3. **Security fix scripts** may incorrectly parse and modify regex patterns
4. **Lack of regex-specific testing** to catch these modifications before deployment

## Prevention Strategy

### 1. Regex Pattern Protection

#### a. Use Raw String Literals with Comments
```python
# SECURITY: DO NOT MODIFY - Regex patterns are security-critical
class ValidationPatterns:
    # fmt: off
    JWT_TOKEN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")  # noqa: E501
    USERNAME = re.compile(r"^[a-zA-Z0-9_-]+$")  # noqa: E501
    # fmt: on
```

#### b. Create a Protected Patterns Module
```python
# violentutf_api/fastapi_app/app/core/regex_patterns.py
"""
CRITICAL: This file contains security-critical regex patterns.
DO NOT modify these patterns without extensive testing.
These patterns are excluded from automatic formatting.
"""

# These patterns are used for input validation and security
PATTERNS = {
    "JWT_TOKEN": r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    "USERNAME": r"^[a-zA-Z0-9_-]+$",
    "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    # ... other patterns
}
```

### 2. CI/CD Pipeline Protection

#### a. Pre-commit Hooks
Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: protect-regex-patterns
        name: Protect Regex Patterns
        entry: python scripts/check_regex_patterns.py
        language: python
        files: '\.(py)$'
        pass_filenames: true
```

#### b. Regex Pattern Validation Script
```python
#!/usr/bin/env python3
# scripts/check_regex_patterns.py
"""
Validates that regex patterns haven't been corrupted by automated tools.
"""
import re
import sys

PROTECTED_PATTERNS = [
    # Pattern, Description
    (r'\[[A-Za-z]-[A-Za-z]\]', 'letter range'),
    (r'\[[0-9]-[0-9]\]', 'digit range'),
    (r'\[[A-Za-z0-9]-[A-Za-z0-9]\]', 'alphanumeric range'),
]

INVALID_PATTERNS = [
    # Invalid pattern that indicates corruption
    r'\[[A-Za-z]\s+-\s+[A-Za-z]\]',  # [A - Z] with spaces
    r'\[[0-9]\s+-\s+[0-9]\]',         # [0 - 9] with spaces
    r'"[^"]+\s+/\s+[^"]+"',           # "text / type" with spaces
    r"'[^']+\s+/\s+[^']+'",           # 'text / type' with spaces
    r'"utf\s+-\s+8"',                 # "utf - 8" with spaces
    r"'utf\s+-\s+8'",                 # 'utf - 8' with spaces
]

def check_file(filepath):
    """Check a file for corrupted regex patterns."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    errors = []
    for pattern in INVALID_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            errors.append(f"Found corrupted pattern in {filepath}: {matches}")
    
    return errors

if __name__ == "__main__":
    errors = []
    for filepath in sys.argv[1:]:
        errors.extend(check_file(filepath))
    
    if errors:
        print("❌ Regex Pattern Validation Failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ All regex patterns are valid")
```

### 3. Exclusion Configuration

#### a. Black (Python Formatter) Configuration
Add to `pyproject.toml`:
```toml
[tool.black]
extend-exclude = '''
(
  app/core/regex_patterns\.py
  | app/core/validation\.py  # If needed
)
'''
```

#### b. Security Scanner Exclusions
Create `.security-scan-exclude`:
```
# Exclude regex pattern files from modification
app/core/regex_patterns.py
app/core/validation.py:ValidationPatterns

# Exclude specific line ranges
app/core/validation.py:45-75  # ValidationPatterns class
```

### 4. Testing Strategy

#### a. Regex Pattern Unit Tests
```python
# tests/test_regex_patterns.py
import pytest
from app.core.validation import ValidationPatterns

class TestRegexPatterns:
    """Test that regex patterns work correctly."""
    
    def test_jwt_token_pattern(self):
        """Test JWT token pattern matches valid tokens."""
        valid_tokens = [
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature",
            "a-b_c.d-e_f.g-h_i",
        ]
        invalid_tokens = [
            "not.a.token",
            "missing-parts",
            "too.many.parts.here",
            "has spaces.in.token",
        ]
        
        pattern = ValidationPatterns.JWT_TOKEN
        for token in valid_tokens:
            assert pattern.match(token), f"Should match: {token}"
        for token in invalid_tokens:
            assert not pattern.match(token), f"Should not match: {token}"
    
    def test_pattern_integrity(self):
        """Test that patterns don't contain spaces in character ranges."""
        import inspect
        import re
        
        # Get all regex patterns
        for name, value in inspect.getmembers(ValidationPatterns):
            if isinstance(value, re.Pattern):
                pattern_str = value.pattern
                # Check for spaces in character ranges
                assert " - " not in pattern_str, \
                    f"Pattern {name} contains spaces in character range: {pattern_str}"
```

#### b. Integration Tests
```python
# tests/test_validation_integration.py
def test_jwt_validation_works():
    """Test that JWT validation works end-to-end."""
    import jwt
    from app.core.validation import validate_jwt_token
    
    # Create a valid token
    token = jwt.encode(
        {"sub": "user", "iat": time.time(), "exp": time.time() + 3600},
        "secret",
        algorithm="HS256"
    )
    
    # Should not raise
    result = validate_jwt_token(token)
    assert result["sub"] == "user"
```

### 5. GitHub Actions Workflow

Create `.github/workflows/regex-protection.yml`:
```yaml
name: Regex Pattern Protection

on:
  pull_request:
    paths:
      - '**.py'
  push:
    branches:
      - main
      - develop

jobs:
  check-regex-patterns:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Check Regex Patterns
        run: |
          python scripts/check_regex_patterns.py $(find . -name "*.py" -type f)
      
      - name: Run Regex Tests
        run: |
          pip install pytest
          pytest tests/test_regex_patterns.py -v
```

### 6. Documentation

#### a. Developer Guidelines
Add to `CONTRIBUTING.md`:
```markdown
## Regex Pattern Guidelines

### CRITICAL: Never Modify Regex Patterns Without Testing

Regex patterns in this codebase are security-critical. Automated tools have previously corrupted these patterns by adding spaces, causing authentication failures.

**DO NOT:**
- Allow auto-formatters to modify regex patterns
- Add spaces within character ranges (e.g., `[A-Z]` not `[A - Z]`)
- Modify patterns without running the full test suite

**DO:**
- Use `# fmt: off` and `# fmt: on` around regex patterns
- Add `# noqa` comments for long lines
- Run `python scripts/check_regex_patterns.py` before committing
- Add tests for any new regex patterns
```

### 7. Monitoring and Alerts

#### a. Runtime Validation
Add startup validation in FastAPI:
```python
# app/main.py
@app.on_event("startup")
async def validate_regex_patterns():
    """Validate critical regex patterns on startup."""
    from app.core.validation import ValidationPatterns
    
    # Test critical patterns
    test_jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
    if not ValidationPatterns.JWT_TOKEN.match(test_jwt):
        logger.error("CRITICAL: JWT regex pattern is corrupted!")
        # Could raise exception to prevent startup
    
    logger.info("Regex pattern validation passed")
```

### 8. Recovery Plan

If patterns are corrupted:

1. **Immediate Rollback**: 
   ```bash
   git checkout <last-known-good-commit> -- app/core/validation.py
   ```

2. **Pattern Reference**:
   Keep a reference file with known-good patterns:
   ```python
   # scripts/known_good_patterns.py
   KNOWN_GOOD = {
       "JWT_TOKEN": r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
       # ... other patterns
   }
   ```

3. **Automated Fix Script**:
   ```python
   # scripts/fix_regex_patterns.py
   """Emergency fix for corrupted regex patterns."""
   
   FIXES = [
       (r'\[([A-Za-z])\s+-\s+([A-Za-z])\]', r'[\1-\2]'),  # [A - Z] -> [A-Z]
       (r'\[([0-9])\s+-\s+([0-9])\]', r'[\1-\2]'),        # [0 - 9] -> [0-9]
       (r'"([^"]+)\s+/\s+([^"]+)"', r'"\1/\2"'),          # "text / type" -> "text/type"
       (r'"utf\s+-\s+8"', r'"utf-8"'),                    # "utf - 8" -> "utf-8"
   ]
   ```

## Implementation Timeline

1. **Immediate** (Day 1):
   - Add `# fmt: off` comments to existing patterns
   - Create known_good_patterns.py reference

2. **Short-term** (Week 1):
   - Implement pre-commit hooks
   - Add regex validation tests
   - Update CI/CD pipeline

3. **Long-term** (Month 1):
   - Full test coverage for all patterns
   - Monitoring and alerting
   - Team training on regex protection

## Success Metrics

1. **Zero regex-related failures** in production
2. **100% of PRs** pass regex validation checks
3. **All regex patterns** have corresponding tests
4. **No spaces in character ranges** detected by automated checks

## Conclusion

This plan provides multiple layers of protection against regex pattern corruption:
- **Prevention**: Formatter exclusions and comments
- **Detection**: Pre-commit hooks and CI/CD checks
- **Testing**: Comprehensive pattern validation
- **Recovery**: Known-good references and fix scripts

By implementing these measures, we can prevent future regex pattern corruption while maintaining code security and functionality.