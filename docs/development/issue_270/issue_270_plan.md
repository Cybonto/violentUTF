# Issue #270 Implementation Plan: Database Performance Monitoring

## Executive Summary

This plan implements comprehensive database performance monitoring infrastructure for ViolentUTF, focusing on PostgreSQL (Keycloak) and SQLite (FastAPI) databases. The implementation follows TDD principles and integrates with existing monitoring infrastructure.

## Current State Analysis

### Existing Infrastructure
- **Monitoring API**: Complete monitoring API at `/api/v1/monitoring` with events, alerts, metrics endpoints
- **Performance Monitors**: Basic performance monitoring framework exists but `DatabasePerformanceMonitor` is not implemented (raises `NotImplementedError`)
- **Prometheus Integration**: Basic Prometheus configuration exists for APISIX metrics
- **Alert System**: Comprehensive alert management system with acknowledgment and resolution workflows

### Gap Analysis
1. **Database-Specific Metrics Collection**: Not implemented - need real-time metrics for PostgreSQL and SQLite
2. **Performance Baselines**: No baseline establishment or historical analysis
3. **Database Monitoring Dashboard**: No dedicated database performance dashboard
4. **Database-Specific Alerting**: No database performance threshold alerts configured
5. **Prometheus/Grafana Stack**: Not deployed for comprehensive metrics collection

## Implementation Strategy

### Phase 1: Database Metrics Collection Infrastructure (Core)
**Objective**: Implement real-time database metrics collection for PostgreSQL and SQLite

**Components**:
1. **PostgreSQL Metrics Collector** (`app/monitoring/database/postgres_metrics.py`)
   - Connection pool metrics (active, idle, waiting connections)
   - Query performance metrics (execution time, slow queries tracking)
   - Database size and table growth monitoring
   - Cache hit ratios and buffer pool utilization
   - Transaction rates and replication status

2. **SQLite Metrics Collector** (`app/monitoring/database/sqlite_metrics.py`)
   - Database file size and growth rate
   - Query execution time distribution
   - Lock contention and concurrent access patterns
   - Journal/WAL mode performance metrics
   - Backup operation monitoring

3. **Database Performance Monitor Implementation** (`app/monitoring/performance_monitor.py`)
   - Complete implementation of `DatabasePerformanceMonitor` class
   - Integration with PostgreSQL and SQLite collectors
   - Metrics aggregation and storage
   - Performance trend calculation

### Phase 2: Performance Baseline and Analysis
**Objective**: Establish performance baselines and implement anomaly detection

**Components**:
1. **Baseline Analyzer** (`scripts/monitoring-setup/establish_baselines.py`)
   - Historical data analysis from existing metrics
   - Baseline calculation per database and metric type
   - Normal operating range identification
   - Capacity planning thresholds

2. **Anomaly Detection** (`app/monitoring/database/anomaly_detector.py`)
   - Real-time anomaly detection against baselines
   - Statistical anomaly detection (z-score, IQR methods)
   - Performance degradation detection (>2x baseline)
   - Alert generation for anomalies

### Phase 3: Alerting and Notifications
**Objective**: Implement database-specific alerting with configurable thresholds

**Components**:
1. **Alert Rule Definitions** (`configs/monitoring/alert_rules.yaml`)
   - PostgreSQL alert rules (connection pool exhaustion, query latency, replication lag)
   - SQLite alert rules (file size growth, lock timeouts, backup failures)
   - Storage alert rules (disk utilization, I/O latency)
   - Service availability alerts

2. **Alert Integration** (extend existing `MonitoringService`)
   - Database alert generation based on rules
   - Integration with existing alert acknowledgment/resolution workflow
   - Alert escalation for unresolved critical issues

### Phase 4: Dashboard and Visualization (Minimal Implementation)
**Objective**: Create basic database performance visibility through API extensions

**Components**:
1. **Dashboard Data API Extensions** (`app/api/v1/monitoring.py`)
   - New endpoint `/monitoring/database/overview` for database health summary
   - New endpoint `/monitoring/database/{db_type}/metrics` for detailed metrics
   - New endpoint `/monitoring/database/baselines` for baseline data
   - Enhanced `/monitoring/dashboard` to include database metrics

2. **Dashboard Documentation** (`docs/monitoring/database-dashboard.md`)
   - Document API endpoints for dashboard consumption
   - Provide query examples for key metrics
   - Define data structures for visualization
   - Reference implementation for Streamlit dashboard (future work)

### Phase 5: Integration and Automation
**Objective**: Integrate monitoring with existing health checks and deployment

**Components**:
1. **Health Check Integration** (update `check_services.sh`)
   - Add database performance checks to existing health validation
   - Include metrics collection status verification
   - Validate alert system operational status

2. **Monitoring Service** (`scripts/monitoring-setup/monitoring_service.py`)
   - Background service for continuous metrics collection
   - Configurable collection intervals
   - Graceful error handling and retry logic
   - Integration with systemd/Docker for automatic startup

## Technical Specifications

### Database Performance Targets (from inventory.md)

#### PostgreSQL (Keycloak)
- **Target Performance**: 1000+ authentication operations/second
- **Key Metrics**:
  - Connection count (threshold: <80% of max_connections)
  - Authentication latency (alert: >500ms)
  - Session creation time (alert: >200ms)
  - Query execution time (alert: >100ms for auth queries)
- **Monitoring Frequency**: 10-second intervals
- **Baseline Window**: 7-day rolling average

#### SQLite (FastAPI)
- **Target Performance**: 500+ API operations/second with WAL mode
- **Key Metrics**:
  - Query execution time (alert: >100ms)
  - Database file size (alert: >1GB, warning: >500MB)
  - Concurrent access patterns (alert: lock timeouts)
  - WAL checkpoint frequency
- **Monitoring Frequency**: 10-second intervals
- **Baseline Window**: 7-day rolling average

#### File Storage
- **Target Performance**: Direct I/O with <50ms latency
- **Key Metrics**:
  - Disk usage (alert: >90%, warning: >80%)
  - I/O latency (alert: >50ms)
  - File access patterns and frequency
  - Configuration file integrity
- **Monitoring Frequency**: 1-minute intervals

### Data Models

#### Database Metric Record
```python
class DatabaseMetric(BaseModel):
    metric_id: UUID
    asset_id: UUID  # References database asset
    metric_type: str  # connection_count, query_latency, etc.
    metric_value: float
    metric_unit: str  # connections, ms, bytes, etc.
    timestamp: datetime
    metadata: Dict[str, Any]  # Additional context
```

#### Performance Baseline
```python
class PerformanceBaseline(BaseModel):
    baseline_id: UUID
    asset_id: UUID
    metric_type: str
    baseline_value: float
    std_deviation: float
    min_value: float
    max_value: float
    sample_size: int
    calculation_window_hours: int
    created_at: datetime
    valid_until: datetime
```

### API Endpoints

#### New Endpoints
1. `GET /api/v1/monitoring/database/overview`
   - Returns: Database health summary for all monitored databases
   - Response: `{ databases: [{ db_id, db_type, status, key_metrics }] }`

2. `GET /api/v1/monitoring/database/{db_type}/metrics`
   - Parameters: `hours_back`, `metric_types`, `aggregation`
   - Returns: Detailed metrics for specific database type
   - Response: `{ metrics: [{ timestamp, metric_type, value, unit }] }`

3. `GET /api/v1/monitoring/database/baselines`
   - Parameters: `db_type`, `metric_types`
   - Returns: Current performance baselines
   - Response: `{ baselines: [{ metric_type, baseline_value, range }] }`

4. `POST /api/v1/monitoring/database/baselines/recalculate`
   - Triggers baseline recalculation
   - Returns: Job ID for async baseline calculation

#### Enhanced Endpoints
- `GET /api/v1/monitoring/dashboard`: Add database metrics section
- `GET /api/v1/monitoring/alerts`: Include database-specific alerts

## Testing Strategy

### Phase 1: Unit Tests (Priority 1)
**File**: `tests/issue_270_tests.md` (created by QA-Tester_vSEP25)

Test coverage requirements:
1. **PostgreSQL Metrics Collection**: Test all metric collectors with mocked connections
2. **SQLite Metrics Collection**: Test file-based metrics and query performance
3. **Baseline Calculation**: Test statistical calculations with various data distributions
4. **Anomaly Detection**: Test edge cases (sudden spikes, gradual degradation, recovery)
5. **Alert Generation**: Test threshold crossing and alert creation
6. **API Endpoints**: Test new endpoints with various query parameters

### Phase 2: Integration Tests (Priority 2)
1. **End-to-End Metrics Flow**: Collect metrics → Store → Query → Alert
2. **Database Connection**: Test against real PostgreSQL and SQLite instances
3. **Baseline Establishment**: Test with historical data simulation
4. **Alert Workflow**: Test alert creation through resolution

### Phase 3: Performance Tests (Priority 3)
1. **Collection Overhead**: Measure monitoring impact on database performance (<5% overhead target)
2. **Scalability**: Test with high-frequency metric collection (10-second intervals)
3. **Storage Growth**: Validate metric data retention and cleanup

## Implementation Order (TDD Protocol)

### Sprint 1: Core Database Metrics (Days 1-2)
1. **Step 1**: QA-Tester creates tests for PostgreSQL metrics collection
2. **Step 2**: Implement `PostgresMetricsCollector` to pass tests
3. **Step 3**: QA-Tester creates tests for SQLite metrics collection
4. **Step 4**: Implement `SQLiteMetricsCollector` to pass tests
5. **Step 5**: Implement `DatabasePerformanceMonitor` integration

### Sprint 2: Baseline and Anomaly Detection (Days 3-4)
1. **Step 1**: QA-Tester creates tests for baseline calculation
2. **Step 2**: Implement `BaselineAnalyzer` with statistical methods
3. **Step 3**: QA-Tester creates tests for anomaly detection
4. **Step 4**: Implement `AnomalyDetector` with threshold logic
5. **Step 5**: Integration testing with metric collection

### Sprint 3: Alerting and API (Days 5-6)
1. **Step 1**: QA-Tester creates tests for alert rule processing
2. **Step 2**: Implement alert rules and integration
3. **Step 3**: QA-Tester creates tests for new API endpoints
4. **Step 4**: Implement new API endpoints
5. **Step 5**: Update documentation

### Sprint 4: Integration and Validation (Day 7)
1. **Step 1**: Integration with `check_services.sh`
2. **Step 2**: Monitoring service deployment automation
3. **Step 3**: End-to-end testing with real databases
4. **Step 4**: Performance validation (overhead measurement)
5. **Step 5**: Documentation completion

## Configuration Files

### Alert Rules Configuration (`configs/monitoring/alert_rules.yaml`)
```yaml
postgresql_alerts:
  connection_pool_exhaustion:
    metric: connection_pool_usage
    threshold: 80
    operator: greater_than
    severity: critical
    message: "PostgreSQL connection pool usage above 80%"

  query_latency_high:
    metric: avg_query_latency_ms
    threshold: 500
    operator: greater_than
    severity: warning
    message: "PostgreSQL query latency exceeds 500ms"

sqlite_alerts:
  file_size_critical:
    metric: database_file_size_mb
    threshold: 1000
    operator: greater_than
    severity: critical
    message: "SQLite database size exceeds 1GB"

  query_timeout:
    metric: lock_timeout_count
    threshold: 1
    operator: greater_than
    severity: warning
    message: "SQLite lock timeout detected"
```

### Monitoring Configuration (`configs/monitoring/monitoring_config.yaml`)
```yaml
collection:
  postgres:
    enabled: true
    interval_seconds: 10
    connection_string_env: POSTGRES_KEYCLOAK_URL

  sqlite:
    enabled: true
    interval_seconds: 10
    database_path: /app/app_data/violentutf_api.db

baselines:
  calculation_window_hours: 168  # 7 days
  update_frequency_hours: 24
  min_samples: 100

anomaly_detection:
  enabled: true
  sensitivity: medium  # low, medium, high
  z_score_threshold: 3.0
  iqr_multiplier: 1.5
```

## Deployment Considerations

### Minimal Deployment (No Prometheus/Grafana)
- Metrics stored in existing SQLite database
- API-based dashboard data access
- Suitable for current single-node deployment
- Lower operational complexity

### Future: Full Monitoring Stack
- Deploy Prometheus for time-series storage
- Deploy Grafana for advanced visualization
- Implement custom exporters for PostgreSQL and SQLite
- Requires additional Docker containers and resources

**Decision**: Implement minimal deployment for Phase 5.1, document full stack as future enhancement

## Success Criteria

### Functional Requirements
1. Real-time metrics collection operational for PostgreSQL and SQLite
2. Performance baselines established with 7-day historical data
3. Alert system generating database performance alerts
4. API endpoints returning database metrics and dashboard data
5. Integration with `check_services.sh` health validation

### Performance Requirements
1. Monitoring overhead <5% on database performance
2. Metrics collection reliable at 10-second intervals
3. API response time <200ms for dashboard queries
4. Alert generation latency <30 seconds from threshold breach

### Quality Requirements
1. 100% test coverage for all new code
2. All tests passing consistently (3+ runs)
3. No flaky tests in CI/CD pipeline
4. Pre-commit hooks passing (black, isort, flake8, mypy, bandit)

## Risk Mitigation

### Risk 1: Monitoring Overhead
- **Mitigation**: Implement efficient metric collection with connection pooling
- **Validation**: Performance tests measuring overhead
- **Fallback**: Configurable collection intervals, ability to disable collectors

### Risk 2: False Positive Alerts
- **Mitigation**: Careful threshold tuning based on baseline analysis
- **Validation**: Alert validation period with monitoring before notifications
- **Fallback**: Alert suppression capabilities, threshold adjustment API

### Risk 3: Storage Growth
- **Mitigation**: Implement metric retention policies (90 days detailed, 1 year aggregated)
- **Validation**: Storage growth monitoring and projections
- **Fallback**: Metric aggregation, data archival, cleanup jobs

## Deliverables

### Code Deliverables
1. Database metrics collectors (PostgreSQL, SQLite)
2. Baseline analyzer and anomaly detector
3. Alert rules configuration and integration
4. New API endpoints for database monitoring
5. Monitoring service for continuous collection
6. Comprehensive test suite (unit, integration, performance)

### Documentation Deliverables
1. Implementation plan (this document)
2. API endpoint documentation with examples
3. Alert rules reference guide
4. Baseline interpretation guide
5. Troubleshooting guide for monitoring issues
6. Performance characteristics report

### Configuration Deliverables
1. Alert rules configuration file
2. Monitoring configuration file
3. Updated `check_services.sh` with database checks
4. Docker integration for monitoring service

## Timeline

- **Total Estimate**: 7 days (as per issue specification: 4-6 days, with testing 7 days)
- **Sprint 1 (Days 1-2)**: Core metrics collection
- **Sprint 2 (Days 3-4)**: Baseline and anomaly detection
- **Sprint 3 (Days 5-6)**: Alerting and API
- **Sprint 4 (Day 7)**: Integration and validation

## Dependencies

### Internal Dependencies
- Issue #269 (Database integrity checks) - Must be completed for baseline accuracy
- Existing monitoring API infrastructure
- SQLite database for metrics storage
- PostgreSQL Keycloak instance access

### External Dependencies
- `psutil` package for system metrics (already in requirements)
- `psycopg2` or `asyncpg` for PostgreSQL metrics collection
- `aiosqlite` for SQLite metrics (already in use)

## Out of Scope

The following items are explicitly out of scope for Phase 5.1:
1. **Full Prometheus/Grafana deployment** - Documented as future enhancement
2. **Streamlit dashboard implementation** - API provides data, dashboard is future work
3. **DuckDB monitoring** - Database is deprecated, migration in progress
4. **Advanced ML-based anomaly detection** - Statistical methods sufficient for Phase 5.1
5. **Multi-node database clustering monitoring** - Single-node deployment currently

## Approval and Sign-off

This plan will be shared with the GitHub issue #270 as a comment for stakeholder review before implementation begins.
