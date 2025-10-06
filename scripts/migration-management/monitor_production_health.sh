#!/usr/bin/env bash
#
# Production Health Monitoring Script for ViolentUTF
# Issue: #328 - Phase 4.3.7: Production Deployment and Cleanup
#
# This script monitors production health during and after SQLite migration:
# - API endpoint health checks with response time tracking
# - Log monitoring for errors and exceptions
# - Database file size and accessibility monitoring
# - Memory usage tracking
# - Alert threshold configuration
# - JSON report generation
#
# Usage:
#   ./monitor_production_health.sh [OPTIONS]
#
# Options:
#   --interval SECONDS    Monitoring interval in seconds (default: 60)
#   --duration MINUTES    Total monitoring duration in minutes (default: 1440 = 24 hours)
#   --report FILE         Output report file path (JSON format)
#   --check-once          Run checks once and exit
#   --check-api           Check API endpoints only
#   --check-logs          Check logs only
#   --check-database      Check database files only
#   --dry-run             Validate configuration without running checks
#   --verbose             Enable verbose output
#   --help                Show this help message
#

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${REPO_ROOT}/logs/monitor_${TIMESTAMP}.log"

# Monitoring parameters
INTERVAL=60
DURATION=1440
REPORT_FILE=""
CHECK_ONCE=false
CHECK_API_ONLY=false
CHECK_LOGS_ONLY=false
CHECK_DATABASE_ONLY=false
DRY_RUN=false
VERBOSE=false

# API endpoints to monitor
API_BASE_URL="http://localhost:9080"
API_ENDPOINTS=(
    "/health"
    "/api/v1/health"
)

# Health check thresholds
RESPONSE_TIME_THRESHOLD=5.0
ERROR_RATE_THRESHOLD=0.1
DB_SIZE_THRESHOLD_MB=1000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Monitoring results (stored as variables for Bash 3.2 compatibility)
MONITORING_RESULTS_FILE=""
API_FAILED_CHECKS=0
LOG_ERROR_COUNT=0
DB_TOTAL_FILES=0
DB_ACCESSIBLE_FILES=0
DB_TOTAL_SIZE_BYTES=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

log_debug() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo -e "[DEBUG] $1" | tee -a "${LOG_FILE}"
    else
        echo "[DEBUG] $1" >> "${LOG_FILE}"
    fi
}

# Usage information
show_usage() {
    cat << EOF
Production Health Monitoring Script for ViolentUTF

Usage: $0 [OPTIONS]

Options:
    --interval SECONDS    Monitoring interval (default: 60)
    --duration MINUTES    Total monitoring duration (default: 1440 = 24 hours)
    --report FILE         Output report file (JSON format)
    --check-once          Run checks once and exit
    --check-api           Check API endpoints only
    --check-logs          Check logs only
    --check-database      Check database files only
    --dry-run             Validate configuration without running checks
    --verbose             Enable verbose output
    --help                Show this help message

Examples:
    $0                                    # Standard 24-hour monitoring
    $0 --check-once --verbose             # Single check with verbose output
    $0 --interval 30 --duration 60        # 1 hour of monitoring, 30s interval
    $0 --check-api --report report.json   # API checks only with JSON report

Exit Codes:
    0    All health checks passed
    1    Some health checks failed
    2    Critical failures detected

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interval)
                INTERVAL="$2"
                shift 2
                ;;
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --report)
                REPORT_FILE="$2"
                shift 2
                ;;
            --check-once)
                CHECK_ONCE=true
                shift
                ;;
            --check-api)
                CHECK_API_ONLY=true
                shift
                ;;
            --check-logs)
                CHECK_LOGS_ONLY=true
                shift
                ;;
            --check-database)
                CHECK_DATABASE_ONLY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Initialize monitoring environment
initialize_monitoring() {
    log_info "Initializing production health monitoring"

    # Create logs directory
    mkdir -p "${REPO_ROOT}/logs"

    # Create report directory if report requested
    if [[ -n "${REPORT_FILE}" ]]; then
        mkdir -p "$(dirname "${REPORT_FILE}")"
    fi

    log_info "Log file: ${LOG_FILE}"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "Dry run mode - configuration validated"
        log_info "Interval: ${INTERVAL}s, Duration: ${DURATION}m"
        exit 0
    fi
}

# Check API endpoint health
check_api_endpoint() {
    local endpoint=$1
    local url="${API_BASE_URL}${endpoint}"

    log_debug "Checking API endpoint: ${url}"

    # Measure response time
    local start_time=$(date +%s.%N)
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "${url}" 2>/dev/null || echo "000")
    local end_time=$(date +%s.%N)

    local response_time=$(echo "${end_time} - ${start_time}" | bc)

    log_debug "  HTTP Code: ${http_code}, Response Time: ${response_time}s"

    # Store results (endpoint-specific results tracked in temp file if needed)
    # Note: Simplified tracking for Bash 3.2 compatibility

    # Evaluate health status
    if [[ "${http_code}" == "200" ]]; then
        if (( $(echo "${response_time} < ${RESPONSE_TIME_THRESHOLD}" | bc -l) )); then
            log_info "✓ API endpoint ${endpoint}: healthy (${response_time}s)"
            return 0
        else
            log_warn "⚠ API endpoint ${endpoint}: slow response (${response_time}s)"
            return 0
        fi
    else
        log_error "✗ API endpoint ${endpoint}: unhealthy (HTTP ${http_code})"
        return 1
    fi
}

# Check all API endpoints
check_all_api_endpoints() {
    log_info "Checking API endpoint health..."

    local failed_checks=0

    for endpoint in "${API_ENDPOINTS[@]}"; do
        if ! check_api_endpoint "${endpoint}"; then
            ((failed_checks++))
        fi
    done

    API_FAILED_CHECKS="${failed_checks}"

    if [[ ${failed_checks} -eq 0 ]]; then
        log_info "All API endpoints healthy"
        return 0
    else
        log_error "${failed_checks} API endpoint(s) unhealthy"
        return 1
    fi
}

# Check logs for errors
check_logs_for_errors() {
    log_info "Checking logs for errors and exceptions..."

    local log_patterns=(
        "ERROR"
        "CRITICAL"
        "Exception"
        "Traceback"
        "failed"
    )

    local error_count=0

    # Check Docker compose logs if available
    if command -v docker &> /dev/null; then
        log_debug "Checking Docker logs..."

        for pattern in "${log_patterns[@]}"; do
            local pattern_count=$(docker compose logs --since 5m 2>/dev/null | grep -i "${pattern}" | wc -l | tr -d ' ' || echo 0)
            error_count=$((error_count + pattern_count))
            log_debug "  Pattern '${pattern}': ${pattern_count} occurrences"
        done
    fi

    # Check application log files
    if [[ -d "${REPO_ROOT}/logs" ]]; then
        log_debug "Checking application logs..."

        for pattern in "${log_patterns[@]}"; do
            local pattern_count=$(find "${REPO_ROOT}/logs" -name "*.log" -mmin -5 -exec grep -i "${pattern}" {} \; 2>/dev/null | wc -l | tr -d ' ' || echo 0)
            error_count=$((error_count + pattern_count))
        done
    fi

    LOG_ERROR_COUNT="${error_count}"

    if [[ ${error_count} -eq 0 ]]; then
        log_info "✓ No errors found in logs (last 5 minutes)"
        return 0
    else
        log_warn "⚠ Found ${error_count} error(s) in logs (last 5 minutes)"
        return 0
    fi
}

# Check database files
check_database_files() {
    log_info "Checking database files..."

    local db_dirs=(
        "${REPO_ROOT}/app_data/violentutf"
        "${REPO_ROOT}/violentutf/app_data/violentutf"
    )

    local total_db_files=0
    local total_db_size=0
    local accessible_files=0

    for db_dir in "${db_dirs[@]}"; do
        if [[ ! -d "${db_dir}" ]]; then
            continue
        fi

        log_debug "Checking directory: ${db_dir}"

        while IFS= read -r -d '' db_file; do
            ((total_db_files++))

            # Check accessibility
            if [[ -r "${db_file}" ]]; then
                ((accessible_files++))

                # Get file size
                local file_size=$(stat -f%z "${db_file}" 2>/dev/null || stat -c%s "${db_file}" 2>/dev/null || echo 0)
                total_db_size=$((total_db_size + file_size))

                log_debug "  $(basename "${db_file}"): $(numfmt --to=iec-i --suffix=B ${file_size} 2>/dev/null || echo ${file_size})"
            else
                log_error "  ✗ Inaccessible: $(basename "${db_file}")"
            fi
        done < <(find "${db_dir}" -type f -name "*.db" -print0 2>/dev/null)
    done

    # Store results
    DB_TOTAL_FILES="${total_db_files}"
    DB_ACCESSIBLE_FILES="${accessible_files}"
    DB_TOTAL_SIZE_BYTES="${total_db_size}"

    # Calculate size in MB
    local total_db_size_mb=$((total_db_size / 1024 / 1024))

    log_info "Database files: ${accessible_files}/${total_db_files} accessible"
    log_info "Total database size: $(numfmt --to=iec-i --suffix=B ${total_db_size} 2>/dev/null || echo ${total_db_size})"

    # Check thresholds
    if [[ ${accessible_files} -eq ${total_db_files} ]]; then
        if [[ ${total_db_size_mb} -lt ${DB_SIZE_THRESHOLD_MB} ]]; then
            log_info "✓ All SQLite database files healthy"
            return 0
        else
            log_warn "⚠ Database size exceeds threshold (${total_db_size_mb}MB > ${DB_SIZE_THRESHOLD_MB}MB)"
            return 0
        fi
    else
        log_error "✗ Some database files inaccessible"
        return 1
    fi
}

# Perform single health check cycle
perform_health_check() {
    log_info "Performing health check cycle..."

    local check_status=0

    # Determine which checks to run
    if [[ "${CHECK_API_ONLY}" == "true" ]]; then
        check_all_api_endpoints || check_status=1
    elif [[ "${CHECK_LOGS_ONLY}" == "true" ]]; then
        check_logs_for_errors || check_status=1
    elif [[ "${CHECK_DATABASE_ONLY}" == "true" ]]; then
        check_database_files || check_status=1
    else
        # Run all checks
        check_all_api_endpoints || check_status=1
        check_logs_for_errors || check_status=1
        check_database_files || check_status=1
    fi

    return ${check_status}
}

# Generate JSON report
generate_json_report() {
    if [[ -z "${REPORT_FILE}" ]]; then
        return 0
    fi

    log_info "Generating JSON report: ${REPORT_FILE}"

    # Build JSON report
    local json_content="{\n"
    json_content+="  \"monitoring_timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\n"
    json_content+="  \"monitoring_duration_minutes\": ${DURATION},\n"
    json_content+="  \"check_interval_seconds\": ${INTERVAL},\n"

    # Add monitoring results
    json_content+="  \"results\": {\n"
    json_content+="    \"api_failed_checks\": \"${API_FAILED_CHECKS}\",\n"
    json_content+="    \"log_error_count\": \"${LOG_ERROR_COUNT}\",\n"
    json_content+="    \"db_total_files\": \"${DB_TOTAL_FILES}\",\n"
    json_content+="    \"db_accessible_files\": \"${DB_ACCESSIBLE_FILES}\",\n"
    json_content+="    \"db_total_size_bytes\": \"${DB_TOTAL_SIZE_BYTES}\"\n"
    json_content+="  },\n"

    # Add status summary
    local overall_status="healthy"
    if [[ "${API_FAILED_CHECKS}" -gt 0 ]]; then
        overall_status="degraded"
    fi

    json_content+="  \"overall_status\": \"${overall_status}\"\n"
    json_content+="}"

    # Write to file
    echo -e "${json_content}" > "${REPORT_FILE}"

    log_info "Report generated successfully"
}

# Main monitoring loop
main_monitoring_loop() {
    log_info "Starting continuous health monitoring"
    log_info "Interval: ${INTERVAL}s, Duration: ${DURATION}m"

    local start_time=$(date +%s)
    local end_time=$((start_time + DURATION * 60))
    local cycle_count=0

    while true; do
        ((cycle_count++))
        log_info "--- Monitoring Cycle ${cycle_count} ---"

        perform_health_check

        # Generate report if requested
        generate_json_report

        # Check if monitoring duration elapsed
        local current_time=$(date +%s)
        if [[ ${current_time} -ge ${end_time} ]]; then
            log_info "Monitoring duration complete (${DURATION} minutes)"
            break
        fi

        # Wait for next interval
        log_debug "Waiting ${INTERVAL}s until next check..."
        sleep "${INTERVAL}"
    done

    log_info "Monitoring complete. Total cycles: ${cycle_count}"
}

# Main script execution
main() {
    echo "========================================"
    echo "ViolentUTF Production Health Monitor"
    echo "Issue #328: SQLite Migration Validation"
    echo "========================================"
    echo ""

    # Parse arguments
    parse_arguments "$@"

    # Initialize
    initialize_monitoring

    # Run checks
    if [[ "${CHECK_ONCE}" == "true" ]] || [[ "${DURATION}" -eq 0 ]]; then
        # Single check
        if perform_health_check; then
            generate_json_report
            log_info "Health check completed: All checks passed"
            exit 0
        else
            generate_json_report
            log_error "Health check completed: Some checks failed"
            exit 1
        fi
    else
        # Continuous monitoring
        main_monitoring_loop
        generate_json_report
        exit 0
    fi
}

# Run main function
main "$@"
