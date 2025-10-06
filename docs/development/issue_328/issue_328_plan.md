# Implementation Plan: Issue #328 - Phase 4.3.7: Production Deployment and Cleanup

## Issue Reference
- **Issue Number**: #328
- **Type**: Task
- **Priority**: High (Priority 1)
- **Parent Issue**: #269 (SQLite Migration)
- **Depends On**: #327 (Comprehensive Testing and Validation) - CLOSED
- **Branch**: issue_328
- **Base Branch**: dev_nightly

## Overview

This issue implements the final phase of the SQLite migration strategy - production deployment and cleanup of DuckDB artifacts. Since there is no separate "production environment" at the moment, this implementation focuses on:

1. Creating deployment automation scripts for health monitoring
2. Implementing comprehensive smoke tests for post-deployment validation
3. Updating documentation to reflect SQLite architecture
4. Providing deployment procedures for future production rollouts

**IMPORTANT**: This is a TDD implementation. All code will have corresponding tests written FIRST, then implementation to pass those tests.

## Current State Analysis

### Completed Prerequisites (Issue #327)
- PyRIT version 0.9.0 installed (pre-0.10.0rc0, close to target)
- All tests passing in development
- Performance validation complete
- Data migration validation complete
- Rollback plan tested and validated

### Existing Infrastructure
- `scripts/migration-management/backup_duckdb_files.sh` - Comprehensive backup script with checksums
- `scripts/migration-management/verify_backup_integrity.sh` - Backup verification with reporting
- `check_services.sh` - Service health checking script
- Docker-compose orchestration for all services
- Comprehensive test suite in `tests/` directory

### What Needs Implementation

#### 1. Production Monitoring Scripts
- `scripts/migration-management/monitor_production_health.sh` - Continuous health monitoring
  - Monitor API response times
  - Track error rates in logs
  - Check database file sizes
  - Monitor memory usage
  - Alert on critical issues

#### 2. Smoke Test Suite
- `tests/smoke_tests/test_api_health.py` - API health validation
- `tests/smoke_tests/test_database_connectivity.py` - Database connectivity validation
- Test key workflows: login, create generator, import dataset, run orchestrator, delete resources

#### 3. Documentation Updates
- Update `docs/adr/002-duckdb-deprecation-strategy.md` - Mark as Superseded
- Create `docs/adr/003-sqlite-alignment-strategy.md` - New ADR for SQLite adoption
- Update `docs/database/architecture-overview.md` - Reflect SQLite architecture
- Create `docs/deployment/sqlite-deployment.md` - Deployment guide
- Update `README.md` - Database technology section

## Test-Driven Development Protocol

### Phase 1: Monitor Script Tests (RED)
**File**: `tests/test_monitor_production_health.sh`

Write tests that verify:
1. Script accepts proper command-line arguments
2. Health check endpoints are queried correctly
3. Error detection logic works (HTTP 500, connection failures)
4. Performance metrics are collected
5. Alert thresholds trigger correctly
6. Log parsing extracts errors
7. Report generation works

**Run tests 3 times to ensure consistency**

### Phase 2: Monitor Script Implementation (GREEN)
**File**: `scripts/migration-management/monitor_production_health.sh`

Implement minimum code to pass all tests:
- Command-line argument parsing
- HTTP health check implementation
- Log monitoring with error pattern matching
- Performance metric collection
- Alert threshold logic
- Report generation

**Run tests 3+ times to validate**

### Phase 3: Monitor Script Refactoring
- Clean up code structure
- Add comprehensive error handling
- Improve logging
- Optimize performance
- Ensure all tests still pass

### Phase 4: Smoke Test Suite Tests (RED)
**File**: `tests/test_smoke_tests.py`

Write tests that verify smoke tests work:
1. Smoke test modules can be imported
2. API health test validates endpoints
3. Database connectivity test validates connections
4. Key workflow tests execute correctly
5. Tests report failures appropriately

**Run tests 3 times to ensure consistency**

### Phase 5: Smoke Test Implementation (GREEN)
**Files**:
- `tests/smoke_tests/__init__.py`
- `tests/smoke_tests/test_api_health.py`
- `tests/smoke_tests/test_database_connectivity.py`

Implement tests for:
- API health endpoint validation
- Database file existence and accessibility
- Key workflow scenarios (login, CRUD operations)
- Error detection and reporting

**Run smoke tests 3+ times to validate**

### Phase 6: Smoke Test Refactoring
- Consolidate common test utilities
- Add parametrized tests for coverage
- Improve error messages
- Ensure 100% pass rate

### Phase 7: Documentation Tests (RED)
**File**: `tests/test_documentation_compliance.py`

Write tests that verify:
1. ADR-002 has Superseded status
2. ADR-003 exists and follows template
3. Architecture docs mention SQLite
4. Deployment guide exists and is complete
5. README.md references SQLite

**Run tests 3 times to ensure consistency**

### Phase 8: Documentation Updates (GREEN)
Update documentation to pass all tests:
- ADR-002: Add Superseded status with date and reason
- ADR-003: Create comprehensive SQLite alignment ADR
- Architecture docs: Update database technology references
- Deployment guide: Create comprehensive deployment procedure
- README.md: Update database section

**Run documentation tests 3+ times to validate**

### Phase 9: Final Validation
- Run complete test suite
- Verify 100% code coverage for new code
- Execute all tests 3+ times for consistency
- Fix any flaky tests
- Generate test results report

## Technical Implementation Details

### 1. Monitor Script Architecture

```bash
#!/usr/bin/env bash
# scripts/migration-management/monitor_production_health.sh

# Features:
# - HTTP health checks with response time tracking
# - Log monitoring with error pattern matching
# - Database file size monitoring
# - Memory usage tracking
# - Alert threshold configuration
# - JSON report generation
# - Continuous monitoring mode

# Usage:
#   ./monitor_production_health.sh [OPTIONS]
#   --interval SECONDS    Monitoring interval (default: 60)
#   --duration MINUTES    Total monitoring duration (default: 1440 = 24 hours)
#   --report FILE         Output report file
#   --alert-email EMAIL   Email for critical alerts
#   --verbose             Verbose output
```

### 2. Smoke Test Structure

```python
# tests/smoke_tests/test_api_health.py

import pytest
import requests
from typing import Dict, List

class TestAPIHealth:
    """Smoke tests for API health validation."""

    def test_health_endpoint(self):
        """Test main API health endpoint responds correctly."""

    def test_api_response_times(self):
        """Test API response times are acceptable."""

    def test_all_endpoints_accessible(self):
        """Test all critical endpoints are accessible."""

    def test_authentication_flow(self):
        """Test authentication workflow."""
```

```python
# tests/smoke_tests/test_database_connectivity.py

import pytest
import sqlite3
from pathlib import Path

class TestDatabaseConnectivity:
    """Smoke tests for database connectivity validation."""

    def test_database_files_exist(self):
        """Test SQLite database files exist."""

    def test_database_accessible(self):
        """Test database files are readable."""

    def test_database_schema(self):
        """Test database schema is correct."""

    def test_pyrit_memory_operations(self):
        """Test PyRIT memory operations work."""
```

### 3. Documentation Structure

#### ADR-003: SQLite Alignment Strategy

```markdown
# ADR-003: SQLite Adoption Strategy for PyRIT Alignment

## Status
**Accepted** - Implemented in production on [DATE]

## Context
PyRIT v0.10.0rc0 introduced a breaking change from DuckDB to SQLite for memory storage.
This ADR documents ViolentUTF's alignment with PyRIT's architectural decision.

## Decision
Adopt SQLite for all PyRIT memory operations, aligning with upstream framework decisions.

## Consequences
[Detailed analysis of positive/negative consequences]

## Implementation
[Technical implementation details]

## Related Decisions
- ADR-001: Database Technology Choices
- ADR-002: DuckDB Deprecation Strategy (Superseded)
```

## Implementation Checklist

### Scripts and Tools
- [ ] Write tests for monitor_production_health.sh
- [ ] Implement monitor_production_health.sh with health monitoring
- [ ] Test script 3+ times to validate reliability
- [ ] Refactor for code quality

### Smoke Tests
- [ ] Write tests for smoke test suite
- [ ] Implement smoke tests (API health, database connectivity)
- [ ] Test smoke tests 3+ times to validate
- [ ] Ensure 100% pass rate

### Documentation
- [ ] Write tests for documentation compliance
- [ ] Update ADR-002 status to 'Superseded'
- [ ] Create ADR-003 for SQLite Alignment Strategy
- [ ] Update docs/database/architecture-overview.md
- [ ] Create docs/deployment/sqlite-deployment.md
- [ ] Update README.md database section
- [ ] Validate all documentation tests pass

### Testing and Validation
- [ ] Run complete test suite
- [ ] Verify 100% code coverage for new code
- [ ] Execute all tests 3+ times for consistency
- [ ] Fix any flaky tests
- [ ] Generate test results in /docs/development/issue_328/testresults.md

### Reporting
- [ ] Generate comprehensive implementation report
- [ ] Comment on GitHub issue with summary
- [ ] Verify all acceptance criteria met

## Acceptance Criteria

As defined in issue #328:

1. **Scripts and Monitoring**
   - [ ] Production health monitoring script implemented and tested
   - [ ] Script provides real-time health metrics
   - [ ] Alert thresholds configurable
   - [ ] Report generation works correctly

2. **Smoke Tests**
   - [ ] Smoke tests implemented for API health
   - [ ] Smoke tests implemented for database connectivity
   - [ ] Key workflow tests execute correctly
   - [ ] 100% pass rate on all smoke tests

3. **Documentation**
   - [ ] ADR-002 marked as Superseded with proper metadata
   - [ ] ADR-003 created and follows ADR template
   - [ ] Database architecture docs updated
   - [ ] Deployment guide created
   - [ ] README.md updated

4. **Quality Standards**
   - [ ] 100% code coverage for new code
   - [ ] All tests pass consistently (3+ runs)
   - [ ] No flaky tests
   - [ ] Code follows KISS and DRY principles
   - [ ] Pre-commit hooks pass

5. **Reporting**
   - [ ] Comprehensive implementation report generated
   - [ ] GitHub issue commented with summary
   - [ ] Test results documented

## Risk Mitigation

### Risk: Flaky Tests
**Mitigation**: Run all tests minimum 3 times, fix any inconsistencies immediately

### Risk: Incomplete Documentation
**Mitigation**: Use documentation compliance tests to verify completeness

### Risk: Monitoring Script Failures
**Mitigation**: Comprehensive unit tests for all script functions

### Risk: Time Constraints
**Mitigation**: Focus on core functionality first, iterate for improvements

## Timeline Estimate

- Phase 1-3 (Monitor Script): 2-3 hours
- Phase 4-6 (Smoke Tests): 2-3 hours
- Phase 7-8 (Documentation): 1-2 hours
- Phase 9 (Validation): 1 hour
- Total: 6-9 hours

## Notes

- No Git commits during implementation - user handles manual commits
- All file paths must be absolute
- Focus on clean, minimal code (no bloat)
- Follow existing ViolentUTF patterns and architecture
- Zero tolerance for masking errors
- Cache files for long operations, clear afterward

## References

- Issue #328: https://github.com/Cybonto/violentUTF/issues/328
- Issue #327: https://github.com/Cybonto/violentUTF/issues/327
- Issue #269: https://github.com/Cybonto/violentUTF/issues/269
- PyRIT Migration Documentation
- ViolentUTF Architecture Documentation
