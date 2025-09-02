#!/bin/bash
# Script to verify CI implementation locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ViolentUTF CI Implementation Verification ===${NC}\n"

# Track overall status
ALL_PASSED=true

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a check
run_check() {
    local name=$1
    local command=$2

    echo -n "Checking $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        ALL_PASSED=false
        return 1
    fi
}

# 1. Check GitHub Actions workflow syntax
echo -e "${YELLOW}1. Validating GitHub Actions Workflow Syntax${NC}"
echo "-------------------------------------------"

if command_exists actionlint; then
    for workflow in .github/workflows/*.yml; do
        if [ -f "$workflow" ]; then
            echo -n "  Validating $(basename $workflow)... "
            if actionlint "$workflow" 2>&1 | grep -q "no problem found"; then
                echo -e "${GREEN}✓${NC}"
            else
                echo -e "${RED}✗${NC}"
                actionlint "$workflow"
                ALL_PASSED=false
            fi
        fi
    done
else
    echo "  actionlint not installed. Install with: brew install actionlint"
    echo "  Fallback: Checking YAML syntax..."

    for workflow in .github/workflows/*.yml; do
        if [ -f "$workflow" ]; then
            run_check "$(basename $workflow)" "python -c \"import yaml; yaml.safe_load(open('$workflow'))\""
        fi
    done
fi

echo ""

# 2. Check Python code quality tools
echo -e "${YELLOW}2. Testing Code Quality Tools${NC}"
echo "------------------------------"

# Create a temporary Python file for testing
TEMP_PY=$(mktemp /tmp/test_code.XXXXXX.py)
cat > "$TEMP_PY" << 'EOF'
import os
import sys

def test_function():
    x = 1
    y = 2
    return x + y

if __name__ == "__main__":
    result = test_function()
    print(f"Result: {result}")
EOF

# Test Black
run_check "Black formatter" "black --check $TEMP_PY"

# Test isort
run_check "isort" "isort --check-only $TEMP_PY"

# Test flake8
run_check "flake8" "flake8 $TEMP_PY"

# Test mypy
run_check "mypy" "mypy $TEMP_PY"

# Test bandit
run_check "bandit" "bandit -r $TEMP_PY"

rm -f "$TEMP_PY"
echo ""

# 3. Check configuration files
echo -e "${YELLOW}3. Validating Configuration Files${NC}"
echo "---------------------------------"

run_check ".flake8 configuration" "test -f .flake8 && flake8 --help > /dev/null"
run_check "pyproject.toml" "test -f pyproject.toml && python -c 'import toml; toml.load(\"pyproject.toml\")'"
run_check ".gitignore" "test -f .gitignore"
run_check "dependabot.yml" "test -f .github/dependabot.yml"

echo ""

# 4. Check Docker environment
echo -e "${YELLOW}4. Checking Docker Environment${NC}"
echo "------------------------------"

run_check "Docker installed" "docker --version"
run_check "Docker Compose" "docker compose version"
run_check "Docker daemon running" "docker ps"

echo ""

# 5. Validate Python dependencies
echo -e "${YELLOW}5. Checking Python Dependencies${NC}"
echo "--------------------------------"

run_check "requirements.txt exists" "test -f requirements.txt"
run_check "violentutf requirements" "test -f violentutf/requirements.txt"
run_check "API requirements" "test -f violentutf_api/fastapi_app/requirements.txt"

# Check if we can install dependencies in a test environment
echo -n "  Testing dependency installation... "
if python -m venv /tmp/test_venv 2>/dev/null; then
    source /tmp/test_venv/bin/activate 2>/dev/null || . /tmp/test_venv/Scripts/activate 2>/dev/null
    if pip install --dry-run -r requirements.txt > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo "    Some dependencies may have issues"
        ALL_PASSED=false
    fi
    deactivate 2>/dev/null || true
    rm -rf /tmp/test_venv
else
    echo -e "${YELLOW}⚠${NC} (Could not create test venv)"
fi

echo ""

# 6. Test workflow execution locally
echo -e "${YELLOW}6. Local Workflow Simulation${NC}"
echo "----------------------------"

# Check if act is installed for local GitHub Actions testing
if command_exists act; then
    echo "  act is installed. You can test workflows locally with:"
    echo "    act -l                    # List all workflows"
    echo "    act -j test-matrix -P ubuntu-22.04=ghcr.io/catthehacker/ubuntu:act-22.04"
else
    echo "  act not installed. Install with: brew install act"
    echo "  This allows local testing of GitHub Actions"
fi

echo ""

# 7. Check for common issues
echo -e "${YELLOW}7. Checking for Common Issues${NC}"
echo "-----------------------------"

# Check for hardcoded secrets
echo -n "  Scanning for hardcoded secrets... "
if grep -r "api_key\|password\|secret\|token" .github/workflows/ | grep -v "GITHUB_TOKEN\|secrets\." | grep -v "^#" > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Found potential hardcoded secrets!"
    ALL_PASSED=false
else
    echo -e "${GREEN}✓${NC}"
fi

# Check for unpinned actions
echo -n "  Checking for unpinned actions... "
if grep -r "uses:.*@main\|uses:.*@master\|uses:.*@v[0-9]" .github/workflows/ > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} Found unpinned actions (should use SHA)"
else
    echo -e "${GREEN}✓${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo "---------------"

if $ALL_PASSED; then
    echo -e "${GREEN}All checks passed! The CI implementation appears to be correctly configured.${NC}"
    echo ""
    echo "Next steps to fully verify:"
    echo "1. Commit and push these changes to trigger the workflows"
    echo "2. Create a test PR to see PR checks in action"
    echo "3. Monitor the Actions tab in GitHub for results"
else
    echo -e "${RED}Some checks failed. Please review the issues above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "1. Install missing tools: pip install black isort flake8 mypy bandit safety"
    echo "2. Install actionlint: brew install actionlint (macOS) or check GitHub"
    echo "3. Ensure Docker is running"
    echo "4. Fix any syntax errors in workflow files"
fi

echo ""
echo "To test workflows without pushing to GitHub:"
echo "  - Use 'act' for local GitHub Actions testing"
echo "  - Run individual components: black ., flake8 ., pytest tests/"
