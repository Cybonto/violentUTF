#!/bin/bash
# Quick script to run the main code quality checks from GitHub Actions

echo "========================================="
echo "Running Code Quality Checks (GitHub CI)"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
ALL_PASSED=true

echo -e "\n${YELLOW}1. Running Black formatter check...${NC}"
if black --check --diff . --verbose; then
    echo -e "${GREEN}✓ Black check passed${NC}"
else
    echo -e "${RED}✗ Black check failed${NC}"
    echo -e "${YELLOW}Fix with: black .${NC}"
    ALL_PASSED=false
fi

echo -e "\n${YELLOW}2. Running isort import check...${NC}"
if isort --check-only --diff . --profile black; then
    echo -e "${GREEN}✓ isort check passed${NC}"
else
    echo -e "${RED}✗ isort check failed${NC}"
    echo -e "${YELLOW}Fix with: isort . --profile black${NC}"
    ALL_PASSED=false
fi

echo -e "\n${YELLOW}3. Running flake8 linter...${NC}"
if flake8 . --count --statistics --show-source; then
    echo -e "${GREEN}✓ Flake8 check passed${NC}"
else
    echo -e "${RED}✗ Flake8 check failed${NC}"
    ALL_PASSED=false
fi

echo -e "\n${YELLOW}4. Running Bandit security scan...${NC}"
bandit -r . -f json -o bandit-report.json
if [ -f bandit-report.json ]; then
    ISSUES=$(python -c "import json; print(len(json.load(open('bandit-report.json'))['results']))")
    echo "Security issues found: $ISSUES"
    if [ "$ISSUES" -gt 0 ]; then
        echo -e "${YELLOW}Top 5 security issues:${NC}"
        python -c "
import json
data = json.load(open('bandit-report.json'))
for i, issue in enumerate(data['results'][:5]):
    print(f\"  {i+1}. {issue['test_name']} - {issue['filename']}:{issue['line_number']}\")
    print(f\"     Severity: {issue['issue_severity']} | {issue['issue_text'][:60]}...\")
"
    else
        echo -e "${GREEN}✓ No security issues found${NC}"
    fi
fi

echo -e "\n${YELLOW}5. Running dependency security check...${NC}"
safety check --json --output safety-report.json || true
if [ -f safety-report.json ]; then
    VULNS=$(python -c "import json; print(len(json.load(open('safety-report.json')).get('vulnerabilities', [])))")
    if [ "$VULNS" -gt 0 ]; then
        echo -e "${RED}Vulnerable dependencies: $VULNS${NC}"
        python -c "
import json
data = json.load(open('safety-report.json'))
for i, vuln in enumerate(data.get('vulnerabilities', [])[:5]):
    print(f\"  - {vuln['package_name']}=={vuln['analyzed_version']}\")
"
        ALL_PASSED=false
    else
        echo -e "${GREEN}✓ No vulnerable dependencies found${NC}"
    fi
fi

# Summary
echo -e "\n========================================="
if [ "$ALL_PASSED" = true ]; then
    echo -e "${GREEN}All checks passed! 🎉${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed!${NC}"
    echo -e "${YELLOW}To fix formatting issues, run:${NC}"
    echo "  black ."
    echo "  isort . --profile black"
    exit 1
fi