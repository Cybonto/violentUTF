# Issue #270 Test Documentation: Database Performance Monitoring

## Test Overview

This document describes the comprehensive test suite for Issue #270: Database Performance Monitoring implementation. The tests follow Test-Driven Development (TDD) principles with the RED-GREEN-REFACTOR cycle.

## Test Categories

### 1. Unit Tests - PostgreSQL Metrics Collection

#### 1.1 PostgresMetricsCollector Tests
- **Test Connection Pool Metrics Collection**: Validate active, idle, and waiting connection counts
- **Test Query Performance Metrics**: Verify query execution time tracking and slow query detection
- **Test Database Size Metrics**: Test database and table size measurement
- **Test Cache Hit Ratio Calculation**: Verify buffer cache hit ratio calculation
- **Test Transaction Rate Metrics**: Validate transaction per second measurement
- **Test Replication Status Check**: Test replication lag and status monitoring
- **Test Connection Failure Handling**: Verify graceful handling of connection failures
- **Test Metric Timestamp Accuracy**: Ensure timestamps are correct and timezone-aware
- **Test Metric Value Validation**: Verify metric values are within expected ranges
- **Test Async Collection**: Test asynchronous metric collection performance

**Success Criteria**:
- All metrics collected successfully from live PostgreSQL instance
- Collection completes within 2 seconds
- No connection leaks after collection
- Metrics have correct units and data types
- Error handling doesn't crash the collector

#### 1.2 PostgreSQL Connection Pool Tests
- **Test Connection Acquisition**: Verify connection pool can acquire connections
- **Test Connection Release**: Test proper connection release after metric collection
- **Test Connection Pool Exhaustion**: Test behavior when pool is exhausted
- **Test Connection Timeout Handling**: Verify timeout configuration works
- **Test Connection Health Check**: Test connection validation before use

### 2. Unit Tests - SQLite Metrics Collection

#### 2.1 SQLiteMetricsCollector Tests
- **Test Database File Size Measurement**: Validate accurate file size reporting
- **Test File Growth Rate Calculation**: Verify growth rate calculation over time
- **Test Query Execution Time Tracking**: Test query performance measurement
- **Test Lock Contention Detection**: Validate lock timeout and contention tracking
- **Test WAL Mode Status**: Test WAL/journal mode detection
- **Test WAL File Size Monitoring**: Verify WAL file size tracking
- **Test Checkpoint Frequency**: Test checkpoint operation monitoring
- **Test Concurrent Access Patterns**: Validate concurrent connection tracking
- **Test Backup Operation Status**: Test backup completion monitoring
- **Test File Access Performance**: Verify I/O latency measurement

**Success Criteria**:
- All file-based metrics accurate to within 1%
- Collection works with database in use
- No database locks during collection
- Handles missing database file gracefully
- Metrics update frequency matches configuration

#### 2.2 SQLite WAL Mode Tests
- **Test WAL Mode Detection**: Verify correct journal mode identification
- **Test WAL Checkpoint Metrics**: Test checkpoint duration and frequency
- **Test WAL Size Thresholds**: Validate WAL size alert threshold checking

### 3. Unit Tests - DatabasePerformanceMonitor

#### 3.1 Performance Monitor Integration Tests
- **Test measure_database_performance Implementation**: Verify method no longer raises NotImplementedError
- **Test PostgreSQL Performance Measurement**: Test integration with PostgresMetricsCollector
- **Test SQLite Performance Measurement**: Test integration with SQLiteMetricsCollector
- **Test Multiple Database Types**: Verify concurrent monitoring of different database types
- **Test Metric Aggregation**: Validate metric aggregation across collection cycles
- **Test Performance Summary Generation**: Test summary statistics calculation
- **Test Historical Data Tracking**: Verify historical metric storage and retrieval

**Success Criteria**:
- Method implemented and functional
- Returns valid PerformanceMetrics dict
- Handles both PostgreSQL and SQLite
- No performance degradation on monitored databases
- Thread-safe for concurrent access

### 4. Unit Tests - Baseline Analyzer

#### 4.1 Baseline Calculation Tests
- **Test Statistical Baseline Calculation**: Verify mean, std dev, min, max calculation
- **Test Rolling Window Baseline**: Test 7-day rolling average calculation
- **Test Baseline with Insufficient Data**: Handle cases with < 100 samples
- **Test Outlier Filtering**: Verify outlier removal before baseline calculation
- **Test Baseline Update Logic**: Test baseline recalculation triggers
- **Test Multi-Metric Baseline**: Validate baseline for multiple metric types
- **Test Database-Specific Baselines**: Ensure separate baselines per database

**Success Criteria**:
- Baseline calculations mathematically correct
- Handles edge cases (no data, single data point, all identical values)
- Baseline updates don't overwrite unnecessarily
- Performance: baseline calculation < 5 seconds for 10,000 samples

#### 4.2 Normal Range Determination Tests
- **Test Normal Range Calculation**: Verify ±2σ normal range determination
- **Test Percentile-Based Range**: Test P5-P95 range calculation
- **Test Range for Skewed Distributions**: Handle non-normal distributions
- **Test Range Validation**: Ensure ranges are logical (min < max)

### 5. Unit Tests - Anomaly Detector

#### 5.1 Anomaly Detection Algorithm Tests
- **Test Z-Score Anomaly Detection**: Verify z-score threshold detection
- **Test IQR Anomaly Detection**: Test interquartile range method
- **Test Sudden Spike Detection**: Validate immediate threshold breach detection
- **Test Gradual Degradation Detection**: Test trend-based degradation detection
- **Test False Positive Reduction**: Verify anomalies require multiple consecutive violations
- **Test Recovery Detection**: Test return-to-normal detection
- **Test Sensitivity Levels**: Validate low/medium/high sensitivity configurations

**Success Criteria**:
- True positive rate > 90% for known anomalies
- False positive rate < 5% for normal data
- Detection latency < 30 seconds
- Configurable sensitivity works correctly

#### 5.2 Anomaly Alert Generation Tests
- **Test Alert Creation on Anomaly**: Verify alert generated when anomaly detected
- **Test Alert Severity Assignment**: Test correct severity based on anomaly magnitude
- **Test Alert Deduplication**: Prevent duplicate alerts for same issue
- **Test Alert Metadata**: Verify alert contains metric value, baseline, deviation

### 6. Unit Tests - Alert Rules

#### 6.1 Alert Rule Processing Tests
- **Test Connection Pool Alert Rule**: Verify >80% usage triggers alert
- **Test Query Latency Alert Rule**: Test >500ms latency alert
- **Test Database Size Alert Rule**: Validate >1GB size alert for SQLite
- **Test Lock Timeout Alert Rule**: Test lock timeout detection alert
- **Test Storage Capacity Alert Rule**: Verify >90% disk usage alert
- **Test Rule Configuration Loading**: Test YAML rule file parsing
- **Test Rule Threshold Customization**: Verify custom threshold support

**Success Criteria**:
- All defined rules trigger correctly
- Rules load from configuration file
- Custom thresholds override defaults
- Multiple rules can trigger simultaneously
- Rules are database-type aware

#### 6.2 Alert Integration Tests
- **Test MonitoringService Integration**: Verify alerts stored via existing service
- **Test Alert Status Lifecycle**: Test active -> acknowledged -> resolved flow
- **Test Alert Notification**: Verify notification creation for critical alerts
- **Test Alert Suppression**: Test maintenance window alert suppression

### 7. Unit Tests - API Endpoints

#### 7.1 Database Overview Endpoint Tests
- **Test GET /monitoring/database/overview**: Verify endpoint returns all database health
- **Test Response Schema Validation**: Validate response matches expected schema
- **Test Multi-Database Response**: Test response includes PostgreSQL and SQLite
- **Test Health Status Calculation**: Verify status is calculated correctly
- **Test Empty Database Case**: Handle no databases configured
- **Test Authentication Required**: Verify JWT authentication enforced

**Expected Response Structure**:
```json
{
  "databases": [
    {
      "db_id": "postgres-keycloak",
      "db_type": "postgresql",
      "status": "healthy",
      "key_metrics": {
        "connection_pool_usage": 45.5,
        "avg_query_latency_ms": 15.2,
        "cache_hit_ratio": 0.98
      },
      "last_updated": "2025-10-06T12:00:00Z"
    },
    {
      "db_id": "sqlite-fastapi",
      "db_type": "sqlite",
      "status": "healthy",
      "key_metrics": {
        "database_size_mb": 48.5,
        "avg_query_time_ms": 8.3,
        "wal_size_mb": 2.1
      },
      "last_updated": "2025-10-06T12:00:00Z"
    }
  ],
  "overall_status": "healthy",
  "timestamp": "2025-10-06T12:00:00Z"
}
```

#### 7.2 Database Metrics Endpoint Tests
- **Test GET /monitoring/database/{db_type}/metrics**: Verify detailed metrics retrieval
- **Test Query Parameter Filtering**: Test hours_back, metric_types parameters
- **Test Aggregation Support**: Verify time-based aggregation works
- **Test Pagination**: Test skip/limit for large result sets
- **Test Invalid Database Type**: Test 404 for unknown database type
- **Test Time Range Validation**: Verify hours_back constraints

**Expected Response Structure**:
```json
{
  "db_type": "postgresql",
  "metrics": [
    {
      "timestamp": "2025-10-06T12:00:00Z",
      "metric_type": "connection_pool_usage",
      "value": 45.5,
      "unit": "percent"
    }
  ],
  "count": 100,
  "time_range_hours": 24
}
```

#### 7.3 Baselines Endpoint Tests
- **Test GET /monitoring/database/baselines**: Verify baseline data retrieval
- **Test Database Type Filtering**: Test db_type parameter
- **Test Metric Type Filtering**: Test metric_types parameter
- **Test Baseline Validity**: Verify only valid baselines returned
- **Test No Baseline Case**: Handle when baselines not yet established

**Expected Response Structure**:
```json
{
  "baselines": [
    {
      "db_type": "postgresql",
      "metric_type": "avg_query_latency_ms",
      "baseline_value": 15.5,
      "std_deviation": 3.2,
      "normal_range": {
        "min": 9.1,
        "max": 21.9
      },
      "sample_size": 10080,
      "calculation_window_hours": 168,
      "valid_until": "2025-10-13T12:00:00Z"
    }
  ]
}
```

#### 7.4 Baseline Recalculation Endpoint Tests
- **Test POST /monitoring/database/baselines/recalculate**: Verify async job creation
- **Test Job ID Generation**: Validate unique job ID returned
- **Test Job Status Tracking**: Verify job status can be queried
- **Test Concurrent Recalculation**: Test only one recalculation runs at a time
- **Test Authorization**: Verify only admin users can trigger recalculation

#### 7.5 Enhanced Dashboard Endpoint Tests
- **Test GET /monitoring/dashboard Database Section**: Verify database metrics included
- **Test Dashboard Performance**: Ensure response time < 200ms
- **Test Data Freshness**: Verify metrics are recent (< 1 minute old)

### 8. Integration Tests - End-to-End Flows

#### 8.1 Metrics Collection Flow Tests
- **Test Complete Collection Cycle**: PostgreSQL collection → Storage → Retrieval
- **Test SQLite Collection Cycle**: SQLite collection → Storage → Retrieval
- **Test Concurrent Collection**: Both databases collected simultaneously
- **Test Collection Error Recovery**: System recovers from transient failures
- **Test Metrics Persistence**: Verify metrics survive service restart

#### 8.2 Baseline Establishment Flow Tests
- **Test Initial Baseline Creation**: Fresh system establishes baselines after 7 days
- **Test Baseline Update Flow**: Existing baselines updated on schedule
- **Test Baseline API Integration**: Baselines accessible via API after calculation

#### 8.3 Anomaly Detection Flow Tests
- **Test Anomaly Detection → Alert → Notification**: Complete flow
- **Test Alert Acknowledgment Flow**: User acknowledges alert via API
- **Test Alert Resolution Flow**: User resolves alert, system clears anomaly

#### 8.4 Performance Monitoring Flow Tests
- **Test High Load Scenario**: Monitor databases under 80% load
- **Test Connection Pool Exhaustion**: Monitor during pool exhaustion event
- **Test Slow Query Detection**: Capture and alert on slow queries
- **Test Storage Growth**: Monitor and alert on rapid storage growth

### 9. Performance Tests

#### 9.1 Collection Overhead Tests
- **Test PostgreSQL Collection Overhead**: Measure monitoring impact on PostgreSQL
- **Test SQLite Collection Overhead**: Measure monitoring impact on SQLite
- **Test Target: < 5% Overhead**: Verify overhead within acceptable range
- **Test High-Frequency Collection**: Test 10-second interval performance
- **Test Concurrent Query Impact**: Measure impact during high query load

**Performance Targets**:
- PostgreSQL collection: < 50ms per cycle
- SQLite collection: < 30ms per cycle
- CPU overhead: < 2% additional CPU usage
- Memory overhead: < 50MB additional RAM

#### 9.2 API Performance Tests
- **Test Dashboard Endpoint Performance**: Verify < 200ms response time
- **Test Metrics Endpoint with Large Dataset**: Test 10,000+ metrics query
- **Test Concurrent API Requests**: Test 100 concurrent dashboard requests
- **Test Database Query Efficiency**: Verify optimal database queries used

#### 9.3 Scalability Tests
- **Test Long-Running Collection**: Monitor for 24 hours without degradation
- **Test Metric Storage Growth**: Project storage requirements over time
- **Test Baseline Calculation Scalability**: Test with 100,000+ metric samples

### 10. Error Handling and Edge Case Tests

#### 10.1 Database Connection Error Tests
- **Test PostgreSQL Unavailable**: Handle PostgreSQL connection failure gracefully
- **Test SQLite File Missing**: Handle missing database file
- **Test Database Read-Only**: Handle read-only database scenarios
- **Test Network Timeout**: Handle network timeouts to PostgreSQL
- **Test Credential Failure**: Handle authentication failures

**Expected Behavior**:
- Errors logged but don't crash monitoring service
- Service continues monitoring other databases
- Alerts generated for connection failures
- Automatic retry with exponential backoff

#### 10.2 Data Quality Tests
- **Test Invalid Metric Values**: Handle NULL or negative values
- **Test Extreme Values**: Handle very large or very small metric values
- **Test Missing Timestamps**: Handle metrics without timestamps
- **Test Duplicate Metrics**: Deduplicate identical metric records

#### 10.3 Configuration Error Tests
- **Test Missing Configuration File**: Handle missing alert_rules.yaml
- **Test Invalid YAML**: Handle malformed configuration files
- **Test Invalid Threshold Values**: Validate threshold value ranges
- **Test Missing Required Config**: Handle incomplete configuration

### 11. Security and Compliance Tests

#### 11.1 Authentication Tests
- **Test JWT Required**: All endpoints require valid JWT token
- **Test Invalid Token Rejection**: Reject expired or invalid tokens
- **Test Authorization Levels**: Admin-only endpoints enforce permissions

#### 11.2 Data Privacy Tests
- **Test No Credential Exposure**: Verify credentials not logged or exposed
- **Test Query Content Privacy**: Don't log query content with sensitive data
- **Test Metric Data Retention**: Verify retention policies enforced

### 12. Monitoring Service Tests

#### 12.1 Service Lifecycle Tests
- **Test Service Startup**: Verify service starts successfully
- **Test Graceful Shutdown**: Test clean shutdown on termination signal
- **Test Configuration Reload**: Test configuration changes without restart
- **Test Service Health Check**: Verify service reports health status

#### 12.2 Continuous Collection Tests
- **Test 10-Second Collection Interval**: Verify consistent timing
- **Test Collection Failure Recovery**: Recover from failed collection attempts
- **Test Service Restart Recovery**: Resume monitoring after service restart
- **Test Metric Gap Handling**: Handle and document gaps in metric collection

#### 12.3 Resource Management Tests
- **Test Memory Leak Prevention**: Monitor for memory leaks over 24 hours
- **Test Connection Cleanup**: Verify database connections properly closed
- **Test Thread/Process Management**: Verify no zombie processes or threads
- **Test Log File Rotation**: Verify logs rotate and don't fill disk

## Test Execution Strategy

### Phase 1: Unit Test Development (RED Phase)
1. Write all unit tests for PostgreSQL metrics collector
2. Run tests - expect failures (RED)
3. Write all unit tests for SQLite metrics collector
4. Run tests - expect failures (RED)
5. Write all unit tests for baseline analyzer
6. Run tests - expect failures (RED)
7. Write all unit tests for anomaly detector
8. Run tests - expect failures (RED)
9. Write all unit tests for API endpoints
10. Run tests - expect failures (RED)

### Phase 2: Implementation (GREEN Phase)
1. Implement PostgresMetricsCollector until tests pass
2. Implement SQLiteMetricsCollector until tests pass
3. Implement BaselineAnalyzer until tests pass
4. Implement AnomalyDetector until tests pass
5. Implement API endpoints until tests pass

### Phase 3: Integration Testing (GREEN Phase)
1. Write integration tests
2. Run integration tests - fix failures
3. Verify all tests pass

### Phase 4: Performance Testing (GREEN Phase)
1. Write performance tests
2. Run performance tests - optimize if needed
3. Verify performance targets met

### Phase 5: Refactoring (REFACTOR Phase)
1. Review code quality
2. Apply DRY principles
3. Improve error handling
4. Add documentation
5. Run all tests - ensure still passing

## Test Data Requirements

### PostgreSQL Test Database
- Running PostgreSQL instance accessible for testing
- Test database with known schema
- Ability to simulate load for testing
- Connection credentials in test configuration

### SQLite Test Database
- Test SQLite database file with known size
- Ability to create temporary test databases
- WAL mode enabled for testing
- Test data for query performance testing

### Baseline Test Data
- Synthetic metric data with known statistics
- Normal distribution data for baseline calculation
- Anomaly data for detection testing
- Historical data spanning 7+ days

## Success Criteria

### Test Coverage
- **Line Coverage**: > 95% for all new code
- **Branch Coverage**: > 90% for all new code
- **Function Coverage**: 100% for all public functions

### Test Reliability
- **Flaky Test Rate**: 0% - all tests must be deterministic
- **Test Execution Time**: Complete test suite < 5 minutes
- **Parallel Execution**: Tests can run in parallel without conflicts

### Quality Gates
- All tests must pass 3+ consecutive times
- No test warnings or errors in output
- Pre-commit hooks pass (black, isort, flake8, mypy, bandit)
- No security issues detected by bandit
- Type checking passes with no mypy errors

## Test Environment Setup

### Prerequisites
```bash
# Activate virtual environment
source .vitutf/bin/activate

# Ensure services are running
./check_services.sh

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Set test environment variables
export TEST_POSTGRES_URL="postgresql://keycloak:test@localhost:5432/keycloak"
export TEST_SQLITE_DB="/tmp/test_violentutf.db"
```

### Running Tests
```bash
# Run all issue #270 tests
pytest tests/test_issue_270_*.py -v

# Run with coverage
pytest tests/test_issue_270_*.py --cov=app/monitoring --cov-report=html

# Run specific test category
pytest tests/test_issue_270_postgres_metrics.py -v

# Run performance tests
pytest tests/test_issue_270_performance.py -v --performance
```

## Test Deliverables

1. **Unit Test Files**:
   - `tests/test_issue_270_postgres_metrics.py`
   - `tests/test_issue_270_sqlite_metrics.py`
   - `tests/test_issue_270_baseline_analyzer.py`
   - `tests/test_issue_270_anomaly_detector.py`
   - `tests/test_issue_270_api_endpoints.py`

2. **Integration Test Files**:
   - `tests/test_issue_270_integration.py`
   - `tests/test_issue_270_end_to_end.py`

3. **Performance Test Files**:
   - `tests/test_issue_270_performance.py`

4. **Test Documentation**:
   - This file: `tests/issue_270_tests.md`
   - Test results: `docs/development/issue_270/testresults.md`

## Test Maintenance

### Adding New Tests
- Follow existing test patterns and naming conventions
- Add test documentation to this file
- Ensure new tests are included in CI/CD pipeline
- Update test coverage requirements if needed

### Updating Tests
- Document reason for test changes
- Verify test still validates intended behavior
- Check for impact on other tests
- Re-run entire test suite after updates

---

**Document Version**: 1.0
**Created**: 2025-10-06
**Last Updated**: 2025-10-06
**Status**: Active - Ready for Implementation
