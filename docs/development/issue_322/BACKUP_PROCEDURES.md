# DuckDB Backup and Restoration Procedures

**Issue**: #322 - Phase 4.3.1: DuckDB Data Inventory and Backup Strategy
**Date**: 2025-10-05
**Status**: Completed

## Overview

This document provides comprehensive procedures for backing up and restoring DuckDB files in the ViolentUTF repository. These procedures are critical for the DuckDB to SQLite migration (parent issue #269).

## Table of Contents

1. [Quick Start](#quick-start)
2. [Inventory Analysis](#inventory-analysis)
3. [Creating Backups](#creating-backups)
4. [Verifying Backups](#verifying-backups)
5. [Restoring Backups](#restoring-backups)
6. [Emergency Rollback](#emergency-rollback)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Standard Backup Workflow

```bash
# 1. Analyze current DuckDB inventory
python3 scripts/migration-management/analyze_duckdb_inventory.py \
    --comprehensive \
    --output reports/duckdb_inventory.json

# 2. Create verified backup
scripts/migration-management/backup_duckdb_files.sh --verify-checksums

# 3. Verify backup integrity
scripts/migration-management/verify_backup_integrity.sh --verbose

# 4. Test restoration (optional but recommended)
python3 scripts/migration-management/test_backup_restoration.py --validate
```

## Inventory Analysis

### Purpose
Generate comprehensive inventory of all DuckDB files before migration.

### Command

```bash
python3 scripts/migration-management/analyze_duckdb_inventory.py \
    --comprehensive \
    --output reports/duckdb_inventory.json
```

### Options

- `--comprehensive`: Perform full schema analysis (default: True)
- `--scan-only`: Quick scan without schema analysis
- `--output FILE`: Output JSON report path (default: reports/duckdb_inventory.json)
- `--base-path DIR`: Base directory for scanning (default: current directory)
- `--verbose`: Enable verbose logging

### Output

The script generates a JSON report with:
- Total file count and size
- File-by-file metadata (size, modification date, permissions)
- User hash extraction from filenames
- DuckDB schema information (tables, row counts, columns)
- Directory-level summaries

### Example Output

```json
{
  "scan_timestamp": "2025-10-05T14:08:19.584002",
  "total_files": 15,
  "total_size_mb": 3.18,
  "files": [
    {
      "path": "app_data/violentutf/pyrit_memory_32a1d...db",
      "filename": "pyrit_memory_32a1d...db",
      "size_bytes": 274432,
      "user_hash": "32a1ddee5ff4c1d...",
      "schema": {
        "tables": ["converters", "datasets", "scorers"],
        "row_counts": {"converters": 0, "datasets": 0}
      }
    }
  ]
}
```

## Creating Backups

### Purpose
Create timestamped, verified backups of all DuckDB files.

### Command

```bash
scripts/migration-management/backup_duckdb_files.sh --verify-checksums
```

### Options

- `--verify-checksums`: Verify checksums after backup (default: enabled)
- `--no-verify`: Skip checksum verification (not recommended)
- `--backup-dir DIR`: Custom backup directory (default: backups/)
- `--verbose`: Enable verbose output
- `--help`: Show help message

### Backup Structure

```
backups/duckdb_backup_YYYYMMDD_HHMMSS/
├── app_data/
│   └── violentutf/
│       └── pyrit_memory_*.db
├── violentutf/
│   └── app_data/
│       └── violentutf/
│           └── pyrit_memory_*.db
├── checksums.sha256
└── backup_manifest.json
```

### Backup Manifest

Each backup includes a `backup_manifest.json` with:

```json
{
  "backup_timestamp": "2025-10-05T18:09:30Z",
  "source_directories": ["app_data/violentutf/", "violentutf/app_data/violentutf/"],
  "files_backed_up": 15,
  "total_size_bytes": 3330048,
  "backup_location": "/path/to/backup",
  "checksums_verified": true
}
```

### Checksum Verification

All backups include SHA256 checksums in `checksums.sha256`:

```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  app_data/violentutf/pyrit_memory_user_0.db
...
```

## Verifying Backups

### Purpose
Verify backup integrity without restoring files.

### Command

```bash
# Verify latest backup
scripts/migration-management/verify_backup_integrity.sh

# Verify specific backup
scripts/migration-management/verify_backup_integrity.sh \
    --backup-dir backups/duckdb_backup_20251005_140928

# Verify all backups
scripts/migration-management/verify_backup_integrity.sh --all
```

### Options

- `--backup-dir DIR`: Specific backup directory to verify
- `--all`: Verify all backups in backups/ directory
- `--report FILE`: Output verification report (default: reports/backup_verification.txt)
- `--verbose`: Enable verbose output
- `--help`: Show help message

### Verification Tests

The script performs four verification tests:

1. **Backup Structure**: Verifies required files exist (checksums.sha256, backup_manifest.json)
2. **Checksums**: Verifies all file checksums match stored values
3. **Manifest**: Validates backup manifest JSON format and content
4. **File Accessibility**: Verifies all backup files are readable

### Example Output

```
========================================
Verifying Backup: duckdb_backup_20251005_140928
========================================

✓ Backup structure complete
✓ All checksums verified (15/15)
✓ Manifest is valid JSON
✓ All files accessible (15/15)

----------------------------------------
Verification Summary: duckdb_backup_20251005_140928
----------------------------------------
Tests Passed: 4
Tests Failed: 0
Status: PASSED
----------------------------------------
```

## Restoring Backups

### Purpose
Test backup restoration in isolated environment.

### Command

```bash
# Test restoration with latest backup
python3 scripts/migration-management/test_backup_restoration.py --validate

# Test specific backup
python3 scripts/migration-management/test_backup_restoration.py \
    --backup-dir backups/duckdb_backup_20251005_140928 \
    --validate
```

### Options

- `--validate`: Run complete validation test suite
- `--backup-dir DIR`: Specific backup directory to test
- `--full-test`: Run full test suite (same as --validate)
- `--output FILE`: Output JSON results (default: reports/restoration_test_results.json)
- `--verbose`: Enable verbose logging

### Restoration Tests

The script performs five comprehensive tests:

1. **Backup Structure**: Verifies backup directory structure
2. **Load Manifest**: Loads and validates backup manifest
3. **Verify Checksums**: Verifies all file checksums
4. **Full Restoration**: Restores all files to temporary directory
5. **Database Accessibility**: Tests DuckDB file accessibility and queries

### Test Environment

- Restoration tests run in isolated `/tmp/duckdb_restore_test_YYYYMMDD_HHMMSS/` directory
- Test environment is automatically cleaned up after completion
- No impact on production data

### Example Output

```
==================================================
Test Results Summary
==================================================
Tests Passed: 5
Tests Failed: 0
Overall: ✓ PASSED
==================================================

✓ All restoration tests passed successfully
```

## Emergency Rollback

### When to Use
If migration fails or data corruption occurs, use these procedures to restore from backup.

### Pre-Rollback Checklist

1. Stop all services accessing DuckDB files
2. Identify the backup to restore (verify integrity first)
3. Create backup of current state (even if corrupted)
4. Document the reason for rollback

### Rollback Procedure

```bash
# 1. Stop services
cd apisix && docker compose down
cd ../keycloak && docker compose down
cd ../violentutf_api && docker compose down

# 2. Verify backup integrity
scripts/migration-management/verify_backup_integrity.sh \
    --backup-dir backups/duckdb_backup_YYYYMMDD_HHMMSS \
    --verbose

# 3. Backup current state (even if corrupted)
mv app_data/violentutf app_data/violentutf_before_rollback_$(date +%Y%m%d_%H%M%S)
mv violentutf/app_data/violentutf violentutf/app_data/violentutf_before_rollback_$(date +%Y%m%d_%H%M%S)

# 4. Restore from backup
cp -r backups/duckdb_backup_YYYYMMDD_HHMMSS/app_data/violentutf app_data/
cp -r backups/duckdb_backup_YYYYMMDD_HHMMSS/violentutf/app_data/violentutf violentutf/app_data/

# 5. Verify restoration
ls -lh app_data/violentutf/*.db
ls -lh violentutf/app_data/violentutf/*.db

# 6. Test a sample DuckDB file
python3 -c "import duckdb; conn = duckdb.connect('app_data/violentutf/pyrit_memory_user_0.db', read_only=True); print('✓ Database accessible'); conn.close()"

# 7. Restart services
cd apisix && docker compose up -d
cd ../keycloak && docker compose up -d
cd ../violentutf_api && docker compose up -d

# 8. Verify services
./check_services.sh
```

### Post-Rollback Verification

1. Check all DuckDB files are present
2. Test database connectivity
3. Verify data integrity
4. Run application smoke tests
5. Monitor logs for errors

## Troubleshooting

### Issue: No DuckDB files found

**Symptoms**: Inventory analysis reports 0 files

**Solutions**:
1. Verify scan directories exist: `ls -ld app_data/violentutf violentutf/app_data/violentutf`
2. Check file permissions: `find app_data -name "*.db" -ls`
3. Verify you're in the repository root directory

### Issue: Checksum verification failed

**Symptoms**: Backup verification reports checksum mismatches

**Solutions**:
1. Check for file corruption during backup
2. Verify disk integrity: `df -h` and check disk health
3. Re-run backup with `--verify-checksums` flag
4. If persistent, investigate hardware issues

### Issue: Restoration test fails

**Symptoms**: Test reports failures in restoration or accessibility

**Solutions**:
1. Check disk space: `df -h /tmp`
2. Verify DuckDB library: `python3 -c "import duckdb; print(duckdb.__version__)"`
3. Review test logs: `cat logs/restoration_test.log`
4. Re-run with `--verbose` flag for detailed output

### Issue: Backup takes too long

**Symptoms**: Backup script times out or runs very slowly

**Solutions**:
1. Check disk I/O: `iostat -x 1`
2. Verify available disk space
3. Consider excluding large test files
4. Run during off-peak hours

### Issue: Permission denied errors

**Symptoms**: Scripts report permission errors

**Solutions**:
1. Make scripts executable: `chmod +x scripts/migration-management/*.sh`
2. Check file ownership: `ls -l scripts/migration-management/`
3. Verify read access to source files: `ls -l app_data/violentutf/*.db`
4. Verify write access to backup directory: `ls -ld backups/`

## Best Practices

1. **Regular Backups**: Create backups before any migration work
2. **Verify Always**: Always verify backups immediately after creation
3. **Test Restoration**: Periodically test restoration procedures
4. **Keep Multiple Backups**: Maintain at least 3 recent backups
5. **Document Changes**: Log all backup and restoration activities
6. **Monitor Disk Space**: Ensure sufficient space for backups
7. **Secure Backups**: Store backups in secure location (not in git)
8. **Version Control**: Never commit backup files to repository

## Integration with Migration Pipeline

These backup procedures are part of the DuckDB to SQLite migration (issue #269):

1. **Phase 4.3.1** (Current): Inventory and backup strategy ✓
2. **Phase 4.3.2**: SQLite schema design (pending)
3. **Phase 4.3.3**: Data migration implementation (pending)
4. **Phase 4.3.4**: Testing and validation (pending)

## Support

For issues or questions:

1. Check logs in `logs/` directory
2. Review generated reports in `reports/` directory
3. Consult this documentation
4. Reference parent issue #269 for migration context
5. Reference implementation plan: `docs/development/issue_322/issue_322_plan.md`

## Files and Locations

### Scripts
- `scripts/migration-management/analyze_duckdb_inventory.py`
- `scripts/migration-management/backup_duckdb_files.sh`
- `scripts/migration-management/verify_backup_integrity.sh`
- `scripts/migration-management/test_backup_restoration.py`

### Reports
- `reports/duckdb_inventory.json`
- `reports/backup_verification.txt`
- `reports/restoration_test_results.json`

### Logs
- `logs/inventory_analysis.log`
- `logs/backup_YYYYMMDD_HHMMSS.log`
- `logs/verification_YYYYMMDD_HHMMSS.log`
- `logs/restoration_test.log`

### Backups
- `backups/duckdb_backup_YYYYMMDD_HHMMSS/`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-05
**Maintained By**: Backend Engineering Team
