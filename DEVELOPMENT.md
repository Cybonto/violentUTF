# Development Guide

## Pre-commit Setup (Match GitHub PR Validation)

To ensure your code passes GitHub PR validation checks locally, follow these steps:

### 1. Install Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

### 2. Run Complete PR Validation Locally
```bash
# Run the exact same checks as GitHub PR validation
./run_pr_checks.sh
```

This script runs:
- **Black** formatter check (`--check --diff . --verbose`)
- **isort** import sorting (`--check-only --diff . --profile black`)
- **Flake8** comprehensive linting (`--count --statistics --show-source --config=.flake8`)
- **PyLint** static analysis (continues on error like GitHub)
- **MyPy** type checking (`--install-types --non-interactive --explicit-package-bases .`)
- **Bandit** security scan (`-r . -f json`)

### 3. Run Individual Checks

```bash
# Black formatting
black --check --diff . --verbose

# isort import sorting
isort --check-only --diff . --profile black

# Flake8 linting (uses .flake8 config)
flake8 . --count --statistics --show-source --config=.flake8

# MyPy type checking (uses pyproject.toml config)
mypy --install-types --non-interactive --explicit-package-bases .

# Bandit security scan (uses pyproject.toml config)
bandit -r . -f json -o bandit-report.json

# PyLint static analysis
find . -name "*.py" -not -path "./tests/*" | xargs pylint --rcfile=.pylintrc
```

### 4. Auto-fix Issues

```bash
# Auto-fix Black formatting
black .

# Auto-fix isort import order
isort .

# Auto-fix some flake8 issues
autopep8 --in-place --aggressive --aggressive .
```

### 5. Test Exclusions

All tools exclude test directories to match GitHub PR validation:
- **Flake8**: Configured in `.flake8`
- **MyPy**: Configured in `pyproject.toml`
- **Bandit**: Configured in `pyproject.toml`
- **PyLint**: Uses `find` command to exclude `./tests/*`

### 6. Configuration Files

- `.flake8` - Flake8 linting rules and exclusions
- `pyproject.toml` - MyPy, Bandit, Black, isort configuration
- `.pylintrc` - PyLint configuration
- `.pre-commit-config.yaml` - Pre-commit hooks matching GitHub exactly

## Expected Results

After running `./run_pr_checks.sh`, you should see:
- ✅ **Critical checks** (Black, isort, Flake8) must pass
- ⚠️ **Advisory checks** (PyLint, MyPy) can have issues but continue
- ✅ **Security scan** (Bandit) should complete successfully

The script will exit with code 0 if ready for PR submission, or code 1 if critical issues need fixing.
