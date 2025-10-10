#!/usr/bin/env bash
#
# DuckDB Backup Script for ViolentUTF Migration
# Issue: #322 - Phase 4.3.1: DuckDB Data Inventory and Backup Strategy
#
# This script creates timestamped backups of all DuckDB files with:
# - Preservation of directory structure
# - SHA256 checksum generation and verification
# - Backup manifest with metadata
# - Error detection and rollback capabilities
#
# Usage:
#   ./backup_duckdb_files.sh [OPTIONS]
#
# Options:
#   --verify-checksums    Verify checksums after backup (default: enabled)
#   --no-verify          Skip checksum verification
#   --backup-dir DIR     Custom backup directory (default: backups/)
#   --verbose            Enable verbose output
#   --help               Show this help message
#

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_BASE_DIR="${REPO_ROOT}/backups"
BACKUP_DIR="${BACKUP_BASE_DIR}/duckdb_backup_${TIMESTAMP}"
LOG_FILE="${REPO_ROOT}/logs/backup_${TIMESTAMP}.log"
VERIFY_CHECKSUMS=true
VERBOSE=false

# Source directories to backup
SOURCE_DIRS=(
    "app_data/violentutf"
    "violentutf/app_data/violentutf"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Usage information
show_usage() {
    cat << EOF
DuckDB Backup Script for ViolentUTF Migration

Usage: $0 [OPTIONS]

Options:
    --verify-checksums    Verify checksums after backup (default: enabled)
    --no-verify          Skip checksum verification
    --backup-dir DIR     Custom backup directory (default: backups/)
    --verbose            Enable verbose output
    --help               Show this help message

Examples:
    $0                           # Standard backup with verification
    $0 --verbose                 # Verbose backup with verification
    $0 --no-verify               # Backup without verification
    $0 --backup-dir /tmp/backup  # Custom backup location

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verify-checksums)
                VERIFY_CHECKSUMS=true
                shift
                ;;
            --no-verify)
                VERIFY_CHECKSUMS=false
                shift
                ;;
            --backup-dir)
                BACKUP_BASE_DIR="$2"
                BACKUP_DIR="${BACKUP_BASE_DIR}/duckdb_backup_${TIMESTAMP}"
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

# Initialize backup environment
initialize_backup() {
    log_info "Initializing backup environment"

    # Create logs directory
    mkdir -p "${REPO_ROOT}/logs"

    # Create backup directory
    mkdir -p "${BACKUP_DIR}"

    log_info "Backup location: ${BACKUP_DIR}"
    log_info "Log file: ${LOG_FILE}"
}

# Check if source directories exist
check_source_directories() {
    log_info "Checking source directories..."

    local dirs_exist=0
    for source_dir in "${SOURCE_DIRS[@]}"; do
        local full_path="${REPO_ROOT}/${source_dir}"
        if [[ -d "${full_path}" ]]; then
            log_debug "Found directory: ${full_path}"
            ((dirs_exist++))
        else
            log_warn "Directory does not exist: ${full_path}"
        fi
    done

    if [[ ${dirs_exist} -eq 0 ]]; then
        log_error "No source directories found. Nothing to backup."
        return 1
    fi

    log_info "Found ${dirs_exist} source directories"
    return 0
}

# Find all DuckDB files
find_duckdb_files() {
    local source_dir=$1
    local full_path="${REPO_ROOT}/${source_dir}"

    if [[ ! -d "${full_path}" ]]; then
        return
    fi

    find "${full_path}" -type f -name "*.db" 2>/dev/null || true
}

# Backup a single file
backup_file() {
    local source_file=$1
    local relative_path="${source_file#${REPO_ROOT}/}"
    local dest_file="${BACKUP_DIR}/${relative_path}"
    local dest_dir=$(dirname "${dest_file}")

    log_debug "Backing up: ${relative_path}"

    # Create destination directory
    mkdir -p "${dest_dir}"

    # Copy file
    if cp -p "${source_file}" "${dest_file}"; then
        log_debug "✓ Copied: ${relative_path}"
        echo "${source_file}" >> "${BACKUP_DIR}/.backup_files_list"
        return 0
    else
        log_error "✗ Failed to copy: ${relative_path}"
        return 1
    fi
}

# Generate checksums for all backed up files
generate_checksums() {
    log_info "Generating SHA256 checksums..."

    local checksum_file="${BACKUP_DIR}/checksums.sha256"

    # Change to backup directory for relative paths in checksum file
    pushd "${BACKUP_DIR}" > /dev/null

    # Find all .db files and generate checksums
    local file_count=0
    while IFS= read -r -d '' file; do
        local relative_file="${file#./}"
        log_debug "Checksum: ${relative_file}"
        shasum -a 256 "${relative_file}" >> "${checksum_file}"
        ((file_count++))
    done < <(find . -type f -name "*.db" -print0)

    popd > /dev/null

    log_info "Generated checksums for ${file_count} files"

    if [[ ${file_count} -eq 0 ]]; then
        log_warn "No files found for checksum generation"
        return 1
    fi

    return 0
}

# Verify checksums
verify_checksums() {
    log_info "Verifying checksums..."

    local checksum_file="${BACKUP_DIR}/checksums.sha256"

    if [[ ! -f "${checksum_file}" ]]; then
        log_error "Checksum file not found: ${checksum_file}"
        return 1
    fi

    pushd "${BACKUP_DIR}" > /dev/null

    if shasum -a 256 -c "${checksum_file}" > /dev/null 2>&1; then
        log_info "✓ All checksums verified successfully"
        popd > /dev/null
        return 0
    else
        log_error "✗ Checksum verification failed"
        popd > /dev/null
        return 1
    fi
}

# Generate backup manifest
generate_manifest() {
    log_info "Generating backup manifest..."

    local manifest_file="${BACKUP_DIR}/backup_manifest.json"
    local file_count=0
    local total_size=0

    # Count files and calculate total size
    if [[ -f "${BACKUP_DIR}/.backup_files_list" ]]; then
        file_count=$(wc -l < "${BACKUP_DIR}/.backup_files_list")
        while IFS= read -r file; do
            if [[ -f "${file}" ]]; then
                local size=$(stat -f%z "${file}" 2>/dev/null || stat -c%s "${file}" 2>/dev/null || echo 0)
                total_size=$((total_size + size))
            fi
        done < "${BACKUP_DIR}/.backup_files_list"
    fi

    # Create JSON manifest
    cat > "${manifest_file}" << EOF
{
  "backup_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_directories": [
$(printf '    "%s"' "${SOURCE_DIRS[0]}"; printf ',\n    "%s"' "${SOURCE_DIRS[@]:1}")
  ],
  "files_backed_up": ${file_count},
  "total_size_bytes": ${total_size},
  "backup_location": "${BACKUP_DIR}",
  "checksums_verified": ${VERIFY_CHECKSUMS}
}
EOF

    log_info "Manifest created: ${manifest_file}"
    log_info "Files backed up: ${file_count}"
    log_info "Total size: $(numfmt --to=iec-i --suffix=B ${total_size} 2>/dev/null || echo ${total_size} bytes)"
}

# Cleanup on error
cleanup_on_error() {
    log_error "Backup failed. Cleaning up partial backup..."

    if [[ -d "${BACKUP_DIR}" ]]; then
        rm -rf "${BACKUP_DIR}"
        log_info "Removed incomplete backup: ${BACKUP_DIR}"
    fi
}

# Main backup process
perform_backup() {
    log_info "Starting DuckDB backup process"
    log_info "Timestamp: ${TIMESTAMP}"

    local total_files=0
    local failed_files=0

    # Backup files from each source directory
    for source_dir in "${SOURCE_DIRS[@]}"; do
        log_info "Processing directory: ${source_dir}"

        while IFS= read -r db_file; do
            if backup_file "${db_file}"; then
                ((total_files++))
            else
                ((failed_files++))
            fi
        done < <(find_duckdb_files "${source_dir}")
    done

    log_info "Backup copy completed: ${total_files} files, ${failed_files} failures"

    if [[ ${total_files} -eq 0 ]]; then
        log_warn "No DuckDB files found to backup"
        return 1
    fi

    if [[ ${failed_files} -gt 0 ]]; then
        log_error "Some files failed to backup"
        return 1
    fi

    # Generate checksums
    if ! generate_checksums; then
        log_error "Checksum generation failed"
        return 1
    fi

    # Verify checksums if requested
    if [[ "${VERIFY_CHECKSUMS}" == "true" ]]; then
        if ! verify_checksums; then
            log_error "Checksum verification failed"
            return 1
        fi
    fi

    # Generate manifest
    generate_manifest

    log_info "✓ Backup completed successfully"
    log_info "Backup location: ${BACKUP_DIR}"

    return 0
}

# Main script execution
main() {
    echo "DuckDB Backup Script - ViolentUTF Migration"
    echo "============================================"
    echo ""

    # Parse arguments
    parse_arguments "$@"

    # Initialize
    initialize_backup

    # Check source directories
    if ! check_source_directories; then
        exit 1
    fi

    # Perform backup
    if perform_backup; then
        echo ""
        echo "============================================"
        echo "Backup completed successfully!"
        echo "Location: ${BACKUP_DIR}"
        echo "============================================"
        exit 0
    else
        cleanup_on_error
        echo ""
        echo "============================================"
        echo "Backup failed. Check log: ${LOG_FILE}"
        echo "============================================"
        exit 1
    fi
}

# Run main function
main "$@"
