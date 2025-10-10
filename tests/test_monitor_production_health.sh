#!/usr/bin/env bash
#
# Test Suite for monitor_production_health.sh
# Issue: #328 - Phase 4.3.7: Production Deployment and Cleanup
#
# This test suite validates the production health monitoring script
# following TDD principles - these tests are written BEFORE implementation.
#

set -euo pipefail

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MONITOR_SCRIPT="${REPO_ROOT}/scripts/migration-management/monitor_production_health.sh"
TEST_REPORT_DIR="${REPO_ROOT}/tests/test_reports/monitor_health"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Setup test environment
setup_test_env() {
    echo "Setting up test environment..."
    mkdir -p "${TEST_REPORT_DIR}"
    mkdir -p "${REPO_ROOT}/logs"
}

# Cleanup test environment
cleanup_test_env() {
    echo "Cleaning up test environment..."
    # Clean up any test artifacts if needed
}

# Test result reporting
report_test() {
    local test_name=$1
    local result=$2

    ((TESTS_RUN++))

    if [[ "${result}" == "PASS" ]]; then
        echo -e "${GREEN}✓${NC} ${test_name}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} ${test_name}"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Script file exists
test_script_exists() {
    if [[ -f "${MONITOR_SCRIPT}" ]]; then
        report_test "Script file exists" "PASS"
        return 0
    else
        report_test "Script file exists" "FAIL"
        return 1
    fi
}

# Test 2: Script is executable
test_script_executable() {
    if [[ -x "${MONITOR_SCRIPT}" ]]; then
        report_test "Script is executable" "PASS"
        return 0
    else
        report_test "Script is executable" "FAIL"
        return 1
    fi
}

# Test 3: Script accepts --help flag
test_help_flag() {
    if "${MONITOR_SCRIPT}" --help &> /dev/null; then
        report_test "Script accepts --help flag" "PASS"
        return 0
    else
        report_test "Script accepts --help flag" "FAIL"
        return 1
    fi
}

# Test 4: Script accepts --interval argument
test_interval_argument() {
    # Test with a short interval for quick validation
    if "${MONITOR_SCRIPT}" --interval 5 --duration 0 --dry-run &> /dev/null; then
        report_test "Script accepts --interval argument" "PASS"
        return 0
    else
        report_test "Script accepts --interval argument" "FAIL"
        return 1
    fi
}

# Test 5: Script accepts --duration argument
test_duration_argument() {
    if "${MONITOR_SCRIPT}" --duration 1 --dry-run &> /dev/null; then
        report_test "Script accepts --duration argument" "PASS"
        return 0
    else
        report_test "Script accepts --duration argument" "FAIL"
        return 1
    fi
}

# Test 6: Script accepts --report argument
test_report_argument() {
    local test_report="${TEST_REPORT_DIR}/test_report_${TIMESTAMP}.json"
    if "${MONITOR_SCRIPT}" --report "${test_report}" --dry-run &> /dev/null; then
        report_test "Script accepts --report argument" "PASS"
        return 0
    else
        report_test "Script accepts --report argument" "FAIL"
        return 1
    fi
}

# Test 7: Script accepts --verbose flag
test_verbose_flag() {
    if "${MONITOR_SCRIPT}" --verbose --dry-run &> /dev/null; then
        report_test "Script accepts --verbose flag" "PASS"
        return 0
    else
        report_test "Script accepts --verbose flag" "FAIL"
        return 1
    fi
}

# Test 8: Script performs health check
test_health_check_execution() {
    local test_output="${TEST_REPORT_DIR}/health_check_${TIMESTAMP}.txt"

    # Run a quick health check
    if "${MONITOR_SCRIPT}" --duration 0 --check-once > "${test_output}" 2>&1; then
        # Verify output contains health check results
        if grep -q "health" "${test_output}" || grep -q "status" "${test_output}"; then
            report_test "Script performs health check" "PASS"
            return 0
        fi
    fi

    report_test "Script performs health check" "FAIL"
    return 1
}

# Test 9: Script generates JSON report
test_json_report_generation() {
    local test_report="${TEST_REPORT_DIR}/json_report_${TIMESTAMP}.json"

    # Run monitoring with report generation
    "${MONITOR_SCRIPT}" --duration 0 --check-once --report "${test_report}" &> /dev/null || true

    # Verify JSON report was created and is valid
    if [[ -f "${test_report}" ]]; then
        if python3 -c "import json; json.load(open('${test_report}'))" 2>/dev/null; then
            report_test "Script generates valid JSON report" "PASS"
            return 0
        fi
    fi

    report_test "Script generates valid JSON report" "FAIL"
    return 1
}

# Test 10: Script monitors API endpoint
test_api_endpoint_monitoring() {
    local test_output="${TEST_REPORT_DIR}/api_monitoring_${TIMESTAMP}.txt"

    # Run API monitoring check
    "${MONITOR_SCRIPT}" --check-api --duration 0 > "${test_output}" 2>&1 || true

    # Verify API endpoint was checked
    if grep -q "localhost:9080\|API\|endpoint" "${test_output}"; then
        report_test "Script monitors API endpoint" "PASS"
        return 0
    fi

    report_test "Script monitors API endpoint" "FAIL"
    return 1
}

# Test 11: Script monitors logs for errors
test_log_error_monitoring() {
    local test_output="${TEST_REPORT_DIR}/log_monitoring_${TIMESTAMP}.txt"

    # Run log monitoring check
    "${MONITOR_SCRIPT}" --check-logs --duration 0 > "${test_output}" 2>&1 || true

    # Verify logs were checked
    if grep -q "log\|error\|exception" "${test_output}"; then
        report_test "Script monitors logs for errors" "PASS"
        return 0
    fi

    report_test "Script monitors logs for errors" "FAIL"
    return 1
}

# Test 12: Script checks database files
test_database_file_monitoring() {
    local test_output="${TEST_REPORT_DIR}/db_monitoring_${TIMESTAMP}.txt"

    # Run database file monitoring
    "${MONITOR_SCRIPT}" --check-database --duration 0 > "${test_output}" 2>&1 || true

    # Verify database files were checked
    if grep -q "database\|\.db\|SQLite" "${test_output}"; then
        report_test "Script checks database files" "PASS"
        return 0
    fi

    report_test "Script checks database files" "FAIL"
    return 1
}

# Test 13: Script handles missing arguments gracefully
test_missing_arguments_handling() {
    # Script should handle missing optional arguments
    if "${MONITOR_SCRIPT}" --dry-run &> /dev/null; then
        report_test "Script handles missing arguments gracefully" "PASS"
        return 0
    else
        report_test "Script handles missing arguments gracefully" "FAIL"
        return 1
    fi
}

# Test 14: Script exits with proper status code
test_exit_status_code() {
    # Test successful execution
    if "${MONITOR_SCRIPT}" --dry-run &> /dev/null; then
        local exit_code=$?
        if [[ ${exit_code} -eq 0 ]]; then
            report_test "Script exits with proper status code" "PASS"
            return 0
        fi
    fi

    report_test "Script exits with proper status code" "FAIL"
    return 1
}

# Test 15: Script creates log file
test_log_file_creation() {
    # Run script and check if log file is created
    "${MONITOR_SCRIPT}" --duration 0 --check-once &> /dev/null || true

    # Check if any monitoring log was created recently
    if find "${REPO_ROOT}/logs" -name "monitor_*.log" -mmin -1 | grep -q .; then
        report_test "Script creates log file" "PASS"
        return 0
    fi

    report_test "Script creates log file" "FAIL"
    return 1
}

# Main test execution
main() {
    echo "========================================"
    echo "Monitor Production Health Script Tests"
    echo "Issue: #328 - TDD Implementation"
    echo "========================================"
    echo ""

    setup_test_env

    # Run all tests
    test_script_exists

    # Only run remaining tests if script exists
    if [[ -f "${MONITOR_SCRIPT}" ]]; then
        test_script_executable
        test_help_flag
        test_interval_argument
        test_duration_argument
        test_report_argument
        test_verbose_flag
        test_health_check_execution
        test_json_report_generation
        test_api_endpoint_monitoring
        test_log_error_monitoring
        test_database_file_monitoring
        test_missing_arguments_handling
        test_exit_status_code
        test_log_file_creation
    else
        echo ""
        echo -e "${YELLOW}Script not found. Skipping execution tests.${NC}"
        echo "This is expected for TDD - implement the script to pass these tests."
        # Mark remaining tests as skipped
        TESTS_RUN=$((TESTS_RUN + 13))
    fi

    cleanup_test_env

    # Print summary
    echo ""
    echo "========================================"
    echo "Test Summary"
    echo "========================================"
    echo "Tests Run:    ${TESTS_RUN}"
    echo "Tests Passed: ${TESTS_PASSED}"
    echo "Tests Failed: ${TESTS_FAILED}"
    echo "========================================"

    if [[ ${TESTS_FAILED} -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        exit 1
    fi
}

# Run main
main "$@"
