#!/bin/bash
# Simulate GitHub Actions checks locally

echo "=== Simulating GitHub Actions PR #50 Checks ==="
echo ""

# Simulate merge with main
echo "1. Creating merge simulation..."
git fetch origin main:temp-main 2>/dev/null || echo "Failed to fetch main"
git checkout -b test-pr50 2>/dev/null || git checkout test-pr50
git merge temp-main --no-edit 2>/dev/null || echo "Already up to date with main"

echo ""
echo "2. Installing CI dependencies (matching GitHub Actions)..."
pip install black isort flake8 flake8-docstrings flake8-annotations

echo ""
echo "3. Running Black check (as GitHub Actions does)..."
black --check --diff . --verbose 2>&1 | tee black-check.log
BLACK_EXIT=$?

echo ""
echo "4. Running isort check..."
isort --check-only --diff . --profile black 2>&1 | tee isort-check.log
ISORT_EXIT=$?

echo ""
echo "5. Running flake8..."
flake8 . --count --statistics --show-source 2>&1 | tee flake8-check.log
FLAKE8_EXIT=$?

echo ""
echo "6. Summary:"
echo "Black exit code: $BLACK_EXIT"
echo "isort exit code: $ISORT_EXIT"
echo "flake8 exit code: $FLAKE8_EXIT"

# Show any files that need formatting
echo ""
echo "7. Files needing formatting:"
if [ $BLACK_EXIT -ne 0 ]; then
    echo "Black found issues in:"
    grep "would reformat" black-check.log || echo "No specific files listed"
fi

if [ $ISORT_EXIT -ne 0 ]; then
    echo "isort found issues in:"
    grep "ERROR" isort-check.log || echo "No specific files listed"
fi

# Cleanup
echo ""
echo "8. Cleaning up..."
git checkout dev_nightly 2>/dev/null
git branch -D test-pr50 2>/dev/null || true
git branch -D temp-main 2>/dev/null || true

echo ""
echo "Done! Check the log files for details."