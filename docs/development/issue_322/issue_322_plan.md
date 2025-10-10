# Implementation Plan: Issue #322 - Phase 4.3.1: DuckDB Data Inventory and Backup Strategy

## Overview
This plan details the implementation of a comprehensive DuckDB inventory system and backup strategy as preparation for the DuckDB to SQLite migration (parent issue #269).

## Objectives
1. Create complete inventory of all DuckDB files in the repository
2. Implement automated backup system with checksum verification
3. Establish backup restoration testing procedures
4. Generate detailed inventory reports for migration planning

## Technical Architecture

### Directory Structure
```
scripts/migration-management/
├── analyze_duckdb_inventory.py    # Inventory analysis with DuckDB schema inspection
├── backup_duckdb_files.sh         # Automated backup with SHA256 checksums
├── test_backup_restoration.py     # Restoration validation testing
└── verify_backup_integrity.sh     # Integrity verification utilities
```

### Data Flow
```
1. Inventory Analysis → JSON Report Generation
2. Backup Creation → Checksum Verification
3. Restoration Testing → Integrity Validation
4. Report Generation → Stakeholder Review
```

## Implementation Components

### 1. DuckDB Inventory Analyzer (analyze_duckdb_inventory.py)

**Purpose**: Comprehensive analysis of all DuckDB files in the repository

**Features**:
- Recursive scan of `app_data/violentutf/` and `violentutf/app_data/violentutf/`
- File metadata extraction (size, modification date, permissions)
- DuckDB schema inspection (tables, row counts, column information)
- User hash extraction from filenames (`pyrit_memory_{user_hash}.db`)
- JSON report generation with complete inventory data

**Output Format**:
```json
{
  "scan_timestamp": "ISO-8601 timestamp",
  "total_files": 0,
  "total_size_bytes": 0,
  "files": [
    {
      "path": "absolute path",
      "filename": "pyrit_memory_xxx.db",
      "size_bytes": 0,
      "modified_date": "ISO-8601",
      "user_hash": "extracted hash",
      "schema": {
        "tables": ["table1", "table2"],
        "row_counts": {"table1": 100}
      }
    }
  ],
  "directory_summary": {
    "app_data/violentutf/": {"count": 0, "size_bytes": 0},
    "violentutf/app_data/violentutf/": {"count": 0, "size_bytes": 0}
  }
}
```

**Error Handling**:
- Handle missing directories gracefully
- Skip corrupted DuckDB files with warnings
- Log all errors to `logs/inventory_errors.log`

### 2. Backup Script (backup_duckdb_files.sh)

**Purpose**: Create timestamped backups with integrity verification

**Features**:
- Timestamped backup directories: `backups/duckdb_backup_{YYYYMMDD_HHMMSS}/`
- Copy all DuckDB files preserving directory structure
- Generate SHA256 checksums for each file
- Create backup manifest with file listings
- Implement error detection and rollback

**Backup Structure**:
```
backups/duckdb_backup_20251005_120000/
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

**Manifest Format**:
```json
{
  "backup_timestamp": "2025-10-05T12:00:00Z",
  "source_directories": ["app_data/violentutf/", "violentutf/app_data/violentutf/"],
  "files_backed_up": 10,
  "total_size_bytes": 1024000,
  "backup_location": "absolute path",
  "checksums_verified": true
}
```

### 3. Restoration Testing (test_backup_restoration.py)

**Purpose**: Validate backup integrity through restoration testing

**Features**:
- Create isolated test environment in `/tmp/duckdb_restore_test_{timestamp}/`
- Restore sample backups to test directory
- Verify checksums match original files
- Attempt to open DuckDB files and query basic data
- Test both individual file restoration and full backup restoration
- Clean up test environment after validation

**Test Scenarios**:
1. Single file restoration with checksum verification
2. Full backup restoration preserving directory structure
3. DuckDB connection and basic query execution
4. Schema validation against inventory report

**Validation Criteria**:
- Checksum match: 100%
- DuckDB readable: 100%
- Schema integrity: 100%
- Query execution: Success

### 4. Integrity Verification (verify_backup_integrity.sh)

**Purpose**: Ongoing verification of backup integrity

**Features**:
- Compare checksums between source and backup
- Validate backup manifest completeness
- Check backup file accessibility
- Generate verification reports
- Support for multiple backup versions

**Output**:
```
Backup Integrity Verification Report
=====================================
Backup: backups/duckdb_backup_20251005_120000
Files Verified: 10/10
Checksum Matches: 10/10
Corrupted Files: 0
Status: PASSED
```

## Testing Strategy

### Unit Testing
- Test inventory analyzer with known DuckDB files
- Test backup script with controlled test data
- Test restoration with various backup scenarios
- Test verification script with valid/invalid checksums

### Integration Testing
- End-to-end workflow: Inventory → Backup → Verify → Restore
- Test with production-like data volumes
- Validate JSON report format compliance
- Test error handling and recovery

### Performance Testing
- Measure inventory scan time for large repositories
- Measure backup creation time
- Measure restoration time
- Set performance benchmarks (max 600 seconds as per UAT)

## Completion Criteria

### Technical Deliverables
- ✓ All 4 scripts implemented and tested
- ✓ JSON inventory report generated at `reports/duckdb_inventory.json`
- ✓ Backup created with verified checksums
- ✓ Restoration successfully tested in isolated environment
- ✓ All scripts follow coding standards (Black, isort, flake8, mypy, bandit)

### Documentation Deliverables
- ✓ Implementation plan (this document)
- ✓ Backup procedures documentation
- ✓ Restoration runbook for emergency rollback
- ✓ Test results documentation

### Quality Assurance
- ✓ Pre-commit hooks pass for all Python files
- ✓ No security vulnerabilities (bandit scan clean)
- ✓ Type hints complete (mypy validation)
- ✓ Code coverage reports generated
- ✓ Execution time under 600 seconds

## Risk Mitigation

### Risk 1: Missed DuckDB Files
**Mitigation**:
- Recursive search with glob patterns
- Multiple directory scan locations
- Cross-reference with known file patterns

### Risk 2: Backup Corruption
**Mitigation**:
- SHA256 checksum verification
- Restoration testing before declaring success
- Multiple backup retention strategy

### Risk 3: Insufficient Disk Space
**Mitigation**:
- Pre-calculate required space from inventory
- Check available disk space before backup
- Implement cleanup of old backups if needed

### Risk 4: Production Data Exposure
**Mitigation**:
- All backups stored locally (never committed)
- Add backup directories to `.gitignore`
- Clear documentation on backup security

## Execution Timeline

1. **Setup Phase** (5 mins)
   - Create directory structure
   - Set up logging infrastructure
   - Validate environment

2. **Development Phase** (TDD approach)
   - Write tests for inventory analyzer
   - Implement inventory analyzer
   - Write tests for backup script
   - Implement backup script
   - Write tests for restoration validator
   - Implement restoration validator
   - Write tests for integrity verifier
   - Implement integrity verifier

3. **Testing Phase**
   - Run all unit tests
   - Execute integration tests
   - Performance validation
   - Security scanning

4. **Execution Phase**
   - Run inventory analysis
   - Create backups
   - Verify integrity
   - Test restoration
   - Generate final reports

5. **Documentation Phase**
   - Update GitHub issue with results
   - Create restoration runbook
   - Document backup procedures

## Success Metrics

- **Inventory Completeness**: 100% of DuckDB files catalogued
- **Backup Integrity**: 100% checksum verification pass rate
- **Restoration Success**: 100% of backed up files restorable
- **Code Quality**: All pre-commit hooks pass
- **Performance**: Execution time < 600 seconds
- **Documentation**: Complete runbooks and procedures

## Rollback Plan

This is a read-only analysis task with backup creation. No rollback needed as:
- No production data is modified
- No database schema changes
- No service disruptions
- Backups can be safely deleted if needed

## Dependencies

### Python Libraries
- `duckdb`: For DuckDB file inspection
- `json`: For report generation
- `pathlib`: For file system operations
- `hashlib`: For checksum generation
- `logging`: For error tracking

### System Requirements
- Sufficient disk space for backups (calculated from inventory)
- Read access to `app_data/` directories
- Write access to `backups/` and `reports/` directories

## Post-Implementation

After successful completion:
1. Comment on GitHub issue #322 with results summary
2. Provide inventory report to stakeholders
3. Document backup locations for migration team
4. Prepare for Phase 4.3.2 (SQLite schema design)
5. Archive implementation artifacts in `docs/development/issue_322/`

## Notes

- This implementation follows strict TDD methodology
- All code will adhere to existing code patterns and standards
- No commits will be made during implementation (user handles manual commits)
- Focus on clean, minimal code without bloat
- Comprehensive error handling and logging throughout
