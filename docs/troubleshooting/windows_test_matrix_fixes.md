# Windows Test Matrix Fixes

## Overview

This document describes the fixes implemented to resolve Windows test failures in the Test Matrix CI/CD job. The main issue was that the workflow used Unix/Linux-specific shell commands that are not compatible with Windows runners.

## Root Cause Analysis

### 1. **Shell Command Incompatibility**
The workflow used bash-specific commands and syntax:
- `find` command for locating files
- `$(...)` command substitution
- `[ -d ... ]` test conditions
- `wc -l` for counting lines
- Unix-style paths with forward slashes

### 2. **Windows vs Unix Path Differences**
- Windows uses backslashes (`\`) for paths
- Windows pip cache is in `~\AppData\Local\pip\Cache` not `~/.cache/pip`
- Different shell environments (cmd.exe vs bash)

### 3. **Shell Script Execution**
- Windows runners don't have bash by default
- Shell scripts with Unix commands fail on Windows

## Implemented Solutions

### 1. **Cross-Platform Python Script**

Created `scripts/run_tests_windows.py` - a Python-based test runner that works on all platforms:

```python
#!/usr/bin/env python3
"""
Cross-platform test runner for ViolentUTF.
Specifically designed to work on Windows, macOS, and Linux.
"""
```

Key features:
- Uses Python's `os.walk()` instead of `find`
- Uses `pathlib` for cross-platform path handling
- Uses `subprocess` for running commands
- Handles Windows-specific paths correctly

### 2. **Updated GitHub Actions Workflow**

#### Before (Unix-only):
```yaml
- name: Install dependencies
  run: |
    for req in $(find . -name "requirements*.txt" -type f); do
      echo "Installing from $req"
      pip install -r "$req" || true
    done

- name: Run tests
  run: |
    if [ -d "tests/unit" ] && [ "$(find tests/unit -name '*.py' -type f | wc -l)" -gt 1 ]; then
      pytest tests/unit -v
    fi
```

#### After (Cross-platform):
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip setuptools wheel
    python scripts/run_tests_windows.py --install-deps || echo "Using fallback"
    python -m pip install pytest pytest-cov pytest-timeout pytest-xdist

- name: Run tests with coverage
  run: |
    python scripts/run_tests_windows.py --test-dir tests/unit
```

### 3. **Cache Path Compatibility**

Updated cache paths to include both Unix and Windows locations:

```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip              # Unix/Linux/macOS
      ~\AppData\Local\pip\Cache # Windows
      .pytest_cache             # Cross-platform
```

### 4. **Test Discovery Improvements**

The Python script handles test discovery properly:
- Finds all `test_*.py` and `*_test.py` files
- Excludes `__init__.py` files
- Handles missing directories gracefully
- Creates empty results if no tests found

## Benefits

### 1. **True Cross-Platform Support**
- Works on Windows, macOS, and Linux
- No shell-specific commands
- Consistent behavior across platforms

### 2. **Better Error Handling**
- Graceful failures with informative messages
- Fallback mechanisms for missing dependencies
- Always produces test results (even if empty)

### 3. **Maintainability**
- Single Python script easier to maintain than platform-specific scripts
- Clear, readable Python code
- Reusable for local development

## Usage

### In CI/CD:
```yaml
- name: Run tests
  run: python scripts/run_tests_windows.py --test-dir tests/unit
```

### Local Development:
```bash
# Install dependencies and run tests
python scripts/run_tests_windows.py --install-deps --test-dir tests/unit

# Run tests without coverage
python scripts/run_tests_windows.py --no-coverage

# Run tests sequentially (no parallel)
python scripts/run_tests_windows.py --no-parallel
```

## Testing the Fix

The fix ensures:
1. ✅ Windows runners can install dependencies
2. ✅ Windows runners can discover test files
3. ✅ Windows runners can execute pytest
4. ✅ Test results are generated in correct format
5. ✅ Coverage reports work on all platforms

## Common Windows-Specific Issues Addressed

1. **Path Separators**: Used `os.path.join()` and `pathlib` for correct separators
2. **File Permissions**: Avoided Unix-specific file permission checks
3. **Shell Environment**: Used Python instead of shell scripts
4. **Package Locations**: Handled Windows-specific pip cache location
5. **Command Execution**: Used `subprocess.run()` with proper Windows support

## Future Considerations

1. **PowerShell Scripts**: Could add PowerShell alternatives for Windows-specific tasks
2. **Conditional Steps**: Use `if: runner.os == 'Windows'` for OS-specific steps
3. **Matrix Exclusions**: Could exclude certain tests from Windows if needed
4. **Performance**: Monitor test execution time on Windows vs Linux

## Troubleshooting

If Windows tests still fail:

1. **Check Python Version**: Ensure Python 3.10+ is available
2. **Check pip Installation**: Verify pip is properly installed
3. **Check Path Length**: Windows has path length limitations (260 chars)
4. **Check Line Endings**: Ensure files use CRLF or LF appropriately
5. **Check Permissions**: Some operations may require admin rights

## Related Files

- `scripts/run_tests_windows.py` - Cross-platform test runner
- `.github/workflows/pr-validation.yml` - Updated workflow
- `scripts/README.md` - Scripts documentation
