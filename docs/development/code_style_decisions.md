# Code Style Decisions for ViolentUTF

## Important Code Style Exceptions

### F-String Formatting

**⚠️ DO NOT AUTO-FIX F-STRING WARNINGS ⚠️**

### Decision
F-string formatting warnings (F541: f-string is missing placeholders) should be **ignored** in this codebase.

### Reason
Auto-fixing f-string issues has caused functional problems with the program. Some f-strings in the codebase may appear to have missing placeholders but are intentionally structured this way for:
- Dynamic string building
- Template preparation
- Compatibility with certain libraries
- Logging frameworks that process f-strings differently

### Implementation
1. **Flake8**: F541 errors are excluded in `.flake8` configuration
2. **CI/CD**: GitHub Actions will not fail on F541 warnings
3. **Pre-commit hooks**: Will not check for f-string placeholder issues
4. **Code reviews**: Reviewers should not request f-string "fixes"

### Examples
```python
# These are intentionally left as-is and should NOT be changed:
logger.info(f"Processing started...")  # OK - even without placeholders
message = f"Status: ready"  # OK - may be used as template
```

### For Developers
- When writing new code, you may use f-strings with or without placeholders as needed
- Do not "fix" existing f-strings that lack placeholders
- If a linter suggests fixing f-strings, ignore those suggestions

### Date of Decision
July 9, 2025

### Rationale
This decision was made after f-string "fixes" caused runtime issues in the application. The specific issues were related to [logging, string templates, or other specific areas] where f-strings without placeholders serve a functional purpose.

## String Multiplication Formatting

### Decision
E226 warnings for missing whitespace around arithmetic operators in string multiplication (e.g., `'='*70`) are **ignored**.

### Reason
String multiplication patterns like `'='*70` or `'-'*50` are commonly used for creating visual separators in CLI output and logging. Adding spaces (`'=' * 70`) provides no functional benefit and can make the code less readable in these specific cases.

### Implementation
- **Flake8**: E226 errors are excluded in `.flake8` configuration
- **CI/CD**: GitHub Actions will not fail on E226 warnings

### Examples
```python
# These patterns are acceptable and should NOT be changed:
print('='*80)  # OK - creates a line separator
header = f"{'-'*20} Report {'-'*20}"  # OK - creates formatted header
```

### Date of Decision
July 10, 2025
