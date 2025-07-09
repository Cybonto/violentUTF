# Code Style Decisions for ViolentUTF

## Important: F-String Formatting

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