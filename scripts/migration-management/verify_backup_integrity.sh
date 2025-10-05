#!/usr/bin/env bash
#
# DuckDB Backup Integrity Verification Script
# Issue: #322 - Phase 4.3.1: DuckDB Data Inventory and Backup Strategy
#
# This script verifies the integrity of DuckDB backups by:
# - Comparing checksums between source and backup
# - Validating backup manifest completeness
# - Checking backup file accessibility
# - Generating verification reports
# - Supporting multiple backup versions
#
# Usage:
#   ./verify_backup_integrity.sh [OPTIONS]
#
# Options:
#   --backup-dir DIR     Backup directory to verify (default: latest)
#   --all                Verify all backups in backups/ directory
#   --report FILE        Output verification report (default: reports/backup_verification.txt)
#   --verbose            Enable verbose output
#   --help               Show this help message
#

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_BASE_DIR="${REPO_ROOT}/backups"
BACKUP_DIR=""
VERIFY_ALL=false
REPORT_FILE="${REPO_ROOT}/reports/backup_verification.txt"
VERBOSE=false
LOG_FILE="${REPO_ROOT}/logs/verification_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

log_pass() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "${LOG_FILE}"
}

log_fail() {
    echo -e "${RED}✗${NC} $1" | tee -a "${LOG_FILE}"
}

# Usage information
show_usage() {
    cat << EOF
DuckDB Backup Integrity Verification Script

Usage: $0 [OPTIONS]

Options:
    --backup-dir DIR     Backup directory to verify (default: latest)
    --all                Verify all backups in backups/ directory
    --report FILE        Output verification report
    --verbose            Enable verbose output
    --help               Show this help message

Examples:
    $0                                    # Verify latest backup
    $0 --all                              # Verify all backups
    $0 --backup-dir backups/duckdb_backup_20251005_120000
    $0 --verbose --report my_report.txt   # Verbose with custom report

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --all)
                VERIFY_ALL=true
                shift
                ;;
            --report)
                REPORT_FILE="$2"
                shift 2
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

# Initialize verification environment
initialize_verification() {
    log_info "Initializing verification environment"

    # Create logs and reports directories
    mkdir -p "${REPO_ROOT}/logs"
    mkdir -p "$(dirname "${REPORT_FILE}")"

    log_info "Log file: ${LOG_FILE}"
    log_info "Report file: ${REPORT_FILE}"
}

# Find latest backup directory
find_latest_backup() {
    if [[ ! -d "${BACKUP_BASE_DIR}" ]]; then
        log_error "Backup directory does not exist: ${BACKUP_BASE_DIR}"
        return 1
    fi

    local latest_backup=$(find "${BACKUP_BASE_DIR}" -maxdepth 1 -type d -name "duckdb_backup_*" | sort -r | head -n 1)

    if [[ -z "${latest_backup}" ]]; then
        log_error "No backups found in ${BACKUP_BASE_DIR}"
        return 1
    fi

    echo "${latest_backup}"
    return 0
}

# Verify backup directory structure
verify_backup_structure() {
    local backup_dir=$1
    local required_files=("checksums.sha256" "backup_manifest.json")
    local missing_files=0

    log_info "Verifying backup structure: ${backup_dir}"

    for file in "${required_files[@]}"; do
        if [[ -f "${backup_dir}/${file}" ]]; then
            log_debug "Found: ${file}"
        else
            log_fail "Missing required file: ${file}"
            ((missing_files++))
        fi
    done

    if [[ ${missing_files} -eq 0 ]]; then
        log_pass "Backup structure complete"
        return 0
    else
        log_fail "Backup structure incomplete (${missing_files} missing files)"
        return 1
    fi
}

# Verify checksums
verify_checksums() {
    local backup_dir=$1
    local checksum_file="${backup_dir}/checksums.sha256"

    log_info "Verifying checksums..."

    if [[ ! -f "${checksum_file}" ]]; then
        log_fail "Checksum file not found"
        return 1
    fi

    pushd "${backup_dir}" > /dev/null

    local total_files=0
    local verified_files=0
    local failed_files=0

    while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        ((total_files++))
    done < "${checksum_file}"

    if shasum -a 256 -c "${checksum_file}" > /dev/null 2>&1; then
        verified_files=${total_files}
        log_pass "All checksums verified (${verified_files}/${total_files})"
        popd > /dev/null
        return 0
    else
        # Count failures
        while IFS= read -r line; do
            if ! echo "${line}" | shasum -a 256 -c - > /dev/null 2>&1; then
                ((failed_files++))
            fi
        done < "${checksum_file}"

        verified_files=$((total_files - failed_files))
        log_fail "Checksum verification failed (${verified_files}/${total_files} passed)"
        popd > /dev/null
        return 1
    fi
}

# Verify manifest
verify_manifest() {
    local backup_dir=$1
    local manifest_file="${backup_dir}/backup_manifest.json"

    log_info "Verifying backup manifest..."

    if [[ ! -f "${manifest_file}" ]]; then
        log_fail "Manifest file not found"
        return 1
    fi

    # Check if JSON is valid
    if python3 -c "import json; json.load(open('${manifest_file}'))" 2>/dev/null; then
        log_pass "Manifest is valid JSON"

        # Extract key information
        local files_backed_up=$(python3 -c "import json; print(json.load(open('${manifest_file}'))['files_backed_up'])")
        local total_size=$(python3 -c "import json; print(json.load(open('${manifest_file}'))['total_size_bytes'])")
        local timestamp=$(python3 -c "import json; print(json.load(open('${manifest_file}'))['backup_timestamp'])")

        log_debug "  Files backed up: ${files_backed_up}"
        log_debug "  Total size: ${total_size} bytes"
        log_debug "  Timestamp: ${timestamp}"

        return 0
    else
        log_fail "Manifest JSON is invalid"
        return 1
    fi
}

# Count actual files in backup
count_backup_files() {
    local backup_dir=$1
    local file_count=$(find "${backup_dir}" -type f -name "*.db" | wc -l | tr -d ' ')
    echo "${file_count}"
}

# Verify file accessibility
verify_file_accessibility() {
    local backup_dir=$1

    log_info "Verifying file accessibility..."

    local total_files=0
    local accessible_files=0
    local inaccessible_files=0

    while IFS= read -r -d '' db_file; do
        ((total_files++))

        if [[ -r "${db_file}" ]]; then
            ((accessible_files++))
            log_debug "Accessible: $(basename "${db_file}")"
        else
            ((inaccessible_files++))
            log_fail "Inaccessible: $(basename "${db_file}")"
        fi
    done < <(find "${backup_dir}" -type f -name "*.db" -print0)

    if [[ ${inaccessible_files} -eq 0 ]]; then
        log_pass "All files accessible (${accessible_files}/${total_files})"
        return 0
    else
        log_fail "Some files inaccessible (${inaccessible_files}/${total_files})"
        return 1
    fi
}

# Verify a single backup
verify_single_backup() {
    local backup_dir=$1
    local backup_name=$(basename "${backup_dir}")

    echo ""
    echo "========================================"
    echo "Verifying Backup: ${backup_name}"
    echo "========================================"
    echo ""

    local tests_passed=0
    local tests_failed=0

    # Test 1: Backup structure
    if verify_backup_structure "${backup_dir}"; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Test 2: Checksums
    if verify_checksums "${backup_dir}"; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Test 3: Manifest
    if verify_manifest "${backup_dir}"; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Test 4: File accessibility
    if verify_file_accessibility "${backup_dir}"; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Summary
    echo ""
    echo "----------------------------------------"
    echo "Verification Summary: ${backup_name}"
    echo "----------------------------------------"
    echo "Tests Passed: ${tests_passed}"
    echo "Tests Failed: ${tests_failed}"

    if [[ ${tests_failed} -eq 0 ]]; then
        echo -e "Status: ${GREEN}PASSED${NC}"
        echo "----------------------------------------"
        return 0
    else
        echo -e "Status: ${RED}FAILED${NC}"
        echo "----------------------------------------"
        return 1
    fi
}

# Generate verification report
generate_report() {
    local backup_dir=$1
    local status=$2

    cat >> "${REPORT_FILE}" << EOF

======================================
Backup Integrity Verification Report
======================================

Backup Directory: ${backup_dir}
Verification Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Status: ${status}

----------------------------------------
Details:
EOF

    # Add manifest info if available
    local manifest_file="${backup_dir}/backup_manifest.json"
    if [[ -f "${manifest_file}" ]]; then
        cat >> "${REPORT_FILE}" << EOF

Backup Metadata:
  Timestamp: $(python3 -c "import json; print(json.load(open('${manifest_file}'))['backup_timestamp'])" 2>/dev/null || echo "N/A")
  Files: $(python3 -c "import json; print(json.load(open('${manifest_file}'))['files_backed_up'])" 2>/dev/null || echo "N/A")
  Size: $(python3 -c "import json; print(json.load(open('${manifest_file}'))['total_size_bytes'])" 2>/dev/null || echo "N/A") bytes

EOF
    fi

    # Add file count
    local file_count=$(count_backup_files "${backup_dir}")
    cat >> "${REPORT_FILE}" << EOF
Actual File Count: ${file_count}

======================================

EOF

    log_info "Report appended to: ${REPORT_FILE}"
}

# Main verification process
main() {
    echo "DuckDB Backup Integrity Verification"
    echo "======================================"
    echo ""

    # Parse arguments
    parse_arguments "$@"

    # Initialize
    initialize_verification

    # Clear report file
    > "${REPORT_FILE}"

    local overall_status=0

    if [[ "${VERIFY_ALL}" == "true" ]]; then
        # Verify all backups
        log_info "Verifying all backups in ${BACKUP_BASE_DIR}"

        local backup_count=0
        local passed_count=0
        local failed_count=0

        while IFS= read -r -d '' backup_dir; do
            ((backup_count++))

            if verify_single_backup "${backup_dir}"; then
                ((passed_count++))
                generate_report "${backup_dir}" "PASSED"
            else
                ((failed_count++))
                generate_report "${backup_dir}" "FAILED"
                overall_status=1
            fi
        done < <(find "${BACKUP_BASE_DIR}" -maxdepth 1 -type d -name "duckdb_backup_*" -print0)

        echo ""
        echo "========================================"
        echo "Overall Verification Summary"
        echo "========================================"
        echo "Total Backups: ${backup_count}"
        echo "Passed: ${passed_count}"
        echo "Failed: ${failed_count}"
        echo "========================================"

    else
        # Verify single backup
        if [[ -z "${BACKUP_DIR}" ]]; then
            log_info "No backup directory specified, finding latest..."
            BACKUP_DIR=$(find_latest_backup)
            if [[ $? -ne 0 ]]; then
                exit 1
            fi
            log_info "Using latest backup: ${BACKUP_DIR}"
        fi

        if [[ ! -d "${BACKUP_DIR}" ]]; then
            log_error "Backup directory not found: ${BACKUP_DIR}"
            exit 1
        fi

        if verify_single_backup "${BACKUP_DIR}"; then
            generate_report "${BACKUP_DIR}" "PASSED"
            overall_status=0
        else
            generate_report "${BACKUP_DIR}" "FAILED"
            overall_status=1
        fi
    fi

    echo ""
    echo "Verification report saved: ${REPORT_FILE}"
    echo ""

    exit ${overall_status}
}

# Run main function
main "$@"
