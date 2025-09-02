#!/bin/bash
set -e

echo "🔍 Running LOCAL PR validation checks (matches GitHub exactly)"
echo "=============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
FAILED_CHECKS=0

echo ""
echo -e "${BLUE}1. Black formatter${NC}"
echo "Running: black --check --diff . --verbose"
if black --check --diff . --verbose; then
    echo -e "${GREEN}✓ Black formatting passed${NC}"
else
    echo -e "${RED}✗ Black formatting failed${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""
echo -e "${BLUE}2. isort import sorting${NC}"
echo "Running: isort --check-only --diff . --profile black"
if isort --check-only --diff . --profile black; then
    echo -e "${GREEN}✓ isort passed${NC}"
else
    echo -e "${RED}✗ isort failed${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""
echo -e "${BLUE}3. Comprehensive flake8${NC}"
echo "Running: flake8 . --count --statistics --show-source --config=.flake8"
if flake8 . --count --statistics --show-source --config=.flake8; then
    echo -e "${GREEN}✓ Flake8 passed${NC}"
else
    echo -e "${RED}✗ Flake8 failed${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""
echo -e "${BLUE}4. PyLint (continues on error like GitHub)${NC}"
echo "Running: find . -name \"*.py\" -not -path \"./tests/*\" | xargs pylint --rcfile=.pylintrc || true"
if find . -name "*.py" -not -path "./tests/*" | xargs pylint --rcfile=.pylintrc || true; then
    echo -e "${YELLOW}⚠ PyLint completed (continues on error)${NC}"
else
    echo -e "${YELLOW}⚠ PyLint had issues but continues${NC}"
fi

echo ""
echo -e "${BLUE}5. MyPy type checking (continues on error like GitHub)${NC}"
echo "Running: mypy --install-types --non-interactive --explicit-package-bases . || true"
MYPY_ERRORS=$(mypy --install-types --non-interactive --explicit-package-bases . 2>/dev/null | tail -n 1 | grep -o '[0-9]\+' | head -n 1 || echo "0")
echo -e "${YELLOW}⚠ MyPy completed with ${MYPY_ERRORS} errors (continues on error)${NC}"

echo ""
echo -e "${BLUE}6. Security scan with bandit${NC}"
echo "Running: bandit -r . -f json -o bandit-report.json"
if timeout 60s bandit -r . -f json -o bandit-report.json 2>/dev/null; then
    SECURITY_ISSUES=$(python3 -c "
import json
try:
    data = json.load(open('bandit-report.json'))
    issues = data.get('results', [])
    print(len(issues))
except:
    print('0')
    " 2>/dev/null || echo "0")
    echo -e "${GREEN}✓ Bandit scan completed: ${SECURITY_ISSUES} security issues found${NC}"
    if [ "$SECURITY_ISSUES" -gt "0" ]; then
        echo -e "${YELLOW}⚠ Review bandit-report.json for security issues${NC}"
    fi
else
    echo -e "${RED}✗ Bandit scan failed or timed out${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""
echo "=============================================================="
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical checks passed! PR ready for validation.${NC}"
    exit 0
else
    echo -e "${RED}❌ ${FAILED_CHECKS} critical check(s) failed. Fix issues before PR.${NC}"
    exit 1
fi
