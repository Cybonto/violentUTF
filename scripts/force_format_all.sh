#!/bin/bash
# Force format all Python files to ensure consistency

echo "=== Force Formatting All Python Files ==="
echo "This will ensure all files match Black and isort standards"
echo ""

# Install specific versions to match CI
echo "1. Installing specific tool versions..."
pip install black==24.3.0 isort==5.13.2

echo ""
echo "2. Running Black formatter..."
black violentutf/ violentutf_api/ tests/ scripts/ --line-length 120 --target-version py310 --target-version py311 --target-version py312

echo ""
echo "3. Running isort formatter..."
isort violentutf/ violentutf_api/ tests/ scripts/ --profile black --line-length 120

echo ""
echo "4. Checking results..."
black --check violentutf/ violentutf_api/ tests/ scripts/
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✓ All files properly formatted!"
else
    echo "✗ Some files still need formatting"
fi

echo ""
echo "5. Files changed:"
git status --porcelain | grep "\.py$" | head -20

echo ""
echo "Done!"
