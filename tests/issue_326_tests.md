# Issue #326 Test Plan: Import Migration from DuckDB to SQLite

## Test Objective
Verify all service imports have been successfully migrated from `get_duckdb_manager` to `get_sqlite_manager` and PyRIT dependencies are updated to v0.10.0rc0.

## Test Categories

### 1. Import Statement Tests
**Objective**: Verify no DuckDB imports remain in codebase

**Test Cases**:
- TC-326-001: Verify converters.py uses sqlite_manager import
- TC-326-002: Verify datasets.py uses sqlite_manager import
- TC-326-003: Verify generators.py uses sqlite_manager import
- TC-326-004: Verify scorers.py uses sqlite_manager import
- TC-326-005: Verify sessions.py uses sqlite_manager import
- TC-326-006: Verify no get_duckdb_manager references exist in API endpoints

### 2. Function Call Tests
**Objective**: Verify all function calls use get_sqlite_manager

**Test Cases**:
- TC-326-101: Verify converters.py uses get_sqlite_manager (7 occurrences)
- TC-326-102: Verify datasets.py uses get_sqlite_manager (6 occurrences)
- TC-326-103: Verify generators.py uses get_sqlite_manager (4 occurrences)
- TC-326-104: Verify scorers.py uses get_sqlite_manager (6 occurrences)
- TC-326-105: Verify sessions.py uses get_sqlite_manager (3 occurrences)

### 3. Requirements Tests
**Objective**: Verify PyRIT version updated in requirements files

**Test Cases**:
- TC-326-201: Verify violentutf/requirements.txt contains pyrit>=0.10.0rc0
- TC-326-202: Verify violentutf_api/fastapi_app/requirements.txt contains pyrit>=0.10.0rc0

### 4. Integration Tests
**Objective**: Verify all services work with new SQLite manager

**Test Cases**:
- TC-326-301: Test generator creation and retrieval
- TC-326-302: Test dataset creation and retrieval
- TC-326-303: Test converter creation and retrieval
- TC-326-304: Test scorer creation and retrieval
- TC-326-305: Test session save and retrieval

### 5. Service Startup Tests
**Objective**: Verify services start without import errors

**Test Cases**:
- TC-326-401: Import all endpoint modules successfully
- TC-326-402: Verify no ImportError exceptions
- TC-326-403: Verify API health check passes

## Expected Test Results

All tests should PASS with the following criteria:
- Zero references to `get_duckdb_manager` in endpoint files
- Zero imports from `app.db.duckdb_manager` in endpoint files
- All function calls use `get_sqlite_manager(user_id)` pattern
- PyRIT version is `>=0.10.0rc0` in both requirements files
- All API endpoints can be imported without errors
- Database operations complete successfully with SQLite backend

## Test Execution Order

1. Static code analysis (import verification)
2. Requirements file validation
3. Module import tests
4. Integration tests with database operations
5. Full service startup test
