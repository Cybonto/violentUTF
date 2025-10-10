# Issue #265 Implementation Plan: Database Configuration Baseline and Drift Detection

## Executive Summary

This implementation plan addresses GitHub issue #265, which requires establishing database configuration baseline documentation and implementing automated drift detection for all ViolentUTF database configurations including PostgreSQL (Keycloak), SQLite/DuckDB (FastAPI), and application configuration files.

## Problem Analysis

### Current State
- Multiple database systems: PostgreSQL (Keycloak SSO), SQLite (FastAPI app data), DuckDB (PyRIT memory)
- Configuration scattered across Docker Compose files, environment variables, and application configs
- No centralized configuration monitoring or drift detection
- Manual configuration management without automated validation

### Target State
- Documented configuration baselines for all database systems
- Automated configuration drift detection and alerting
- Configuration validation integrated into CI/CD pipelines
- Configuration change tracking with audit logging
- Backup and restoration procedures for all configuration types

## Technical Architecture

### 1. Configuration Monitoring Service
**Location**: `violentutf_api/fastapi_app/app/services/config_monitoring.py`

#### Core Components:
- **ConfigurationBaseline**: Data models for storing baseline configurations
- **DriftDetector**: Algorithms for detecting configuration changes
- **AlertManager**: Notification system for configuration drift
- **ValidationEngine**: Schema-based configuration validation
- **AuditLogger**: Change tracking and audit logging

#### Database Schema:
```sql
-- Configuration baselines table
CREATE TABLE config_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name VARCHAR(100) NOT NULL,
    config_type VARCHAR(50) NOT NULL,  -- postgresql, sqlite, duckdb, application
    config_path VARCHAR(500) NOT NULL,
    baseline_hash VARCHAR(64) NOT NULL,
    baseline_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configuration drift history
CREATE TABLE config_drift_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_id INTEGER REFERENCES config_baselines(id),
    drift_type VARCHAR(50) NOT NULL,  -- added, removed, modified
    field_path VARCHAR(500),
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(20) DEFAULT 'medium'  -- low, medium, high, critical
);

-- Configuration validation results
CREATE TABLE config_validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_id INTEGER REFERENCES config_baselines(id),
    validation_status VARCHAR(20) NOT NULL,  -- passed, failed, warning
    validation_errors TEXT,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Configuration Baseline Documentation
**Location**: `docs/database/configuration-baselines.md`

#### Baseline Categories:
1. **PostgreSQL (Keycloak)**
   - `postgresql.conf` settings
   - `pg_hba.conf` authentication
   - Database-specific configurations
   - Connection pooling parameters

2. **SQLite (FastAPI)**
   - SQLAlchemy engine configurations
   - Connection string parameters
   - Transaction isolation settings
   - Backup configurations

3. **DuckDB (PyRIT Memory)**
   - Database file locations
   - Connection parameters
   - Performance tuning settings
   - Memory management

4. **Application Configurations**
   - Environment variables
   - YAML/JSON configuration files
   - Docker container configurations
   - Service-specific settings

### 3. Drift Detection Implementation
**Location**: `scripts/config-management/`

#### Detection Algorithms:
- **Hash-based detection**: Quick identification of file changes
- **Semantic comparison**: Deep comparison of configuration values
- **Schema validation**: Ensure configurations meet defined standards
- **Threshold monitoring**: Detect parameter values outside acceptable ranges

#### Alert Thresholds:
- **Critical**: Security-related configuration changes
- **High**: Performance-impacting changes
- **Medium**: Non-critical functional changes
- **Low**: Documentation or comment changes

### 4. CI/CD Integration
**Location**: `.github/workflows/config-validation.yml`

#### Pipeline Stages:
1. **Configuration extraction**: Pull current configurations from services
2. **Baseline comparison**: Compare against documented baselines
3. **Validation**: Run schema and policy validation
4. **Drift reporting**: Generate drift detection reports
5. **Approval gates**: Require approval for critical configuration changes

## Implementation Tasks

### Phase 1: Foundation (Day 1-2)
1. **Database Schema Setup**
   - Create configuration monitoring tables
   - Set up migration scripts
   - Implement data models

2. **Core Service Development**
   - Implement ConfigurationBaseline class
   - Create basic CRUD operations
   - Set up logging and error handling

### Phase 2: Configuration Discovery (Day 3-4)
1. **PostgreSQL Configuration Discovery**
   - Extract Keycloak PostgreSQL settings
   - Document connection parameters
   - Capture security configurations

2. **SQLite/DuckDB Configuration Discovery**
   - Extract FastAPI database configurations
   - Document PyRIT memory database settings
   - Capture performance parameters

3. **Application Configuration Discovery**
   - Extract environment variables
   - Document Docker configurations
   - Capture service-specific settings

### Phase 3: Drift Detection (Day 5-6)
1. **Drift Detection Engine**
   - Implement hash-based change detection
   - Create semantic comparison algorithms
   - Build alerting mechanisms

2. **Validation Framework**
   - Create configuration schemas
   - Implement validation rules
   - Build compliance checking

### Phase 4: Integration (Day 7-8)
1. **CI/CD Integration**
   - Create GitHub Actions workflow
   - Implement pre-deployment validation
   - Set up automated reporting

2. **API Integration**
   - Create REST endpoints for configuration management
   - Implement authentication and authorization
   - Build configuration dashboard endpoints

### Phase 5: Testing and Documentation (Day 9-10)
1. **Comprehensive Testing**
   - Unit tests for all components
   - Integration tests with real configurations
   - Performance testing for monitoring overhead

2. **Documentation and Training**
   - Complete baseline documentation
   - Create operational procedures
   - Build troubleshooting guides

## Test-Driven Development Approach

### Test Categories:

#### 1. Unit Tests
- **ConfigurationBaseline** class methods
- **DriftDetector** algorithms
- **ValidationEngine** rule processing
- **AlertManager** notification logic

#### 2. Integration Tests
- Database configuration extraction
- End-to-end drift detection workflows
- CI/CD pipeline integration
- API endpoint functionality

#### 3. Performance Tests
- Configuration scanning performance
- Drift detection algorithm efficiency
- Database query optimization
- Alert processing throughput

#### 4. Security Tests
- Configuration data protection
- Access control validation
- Sensitive data masking
- Audit trail integrity

## File Structure

```
violentutf_api/fastapi_app/app/services/
├── config_monitoring.py              # Main monitoring service
├── config_baseline.py                # Baseline management
├── config_drift_detector.py          # Drift detection algorithms
├── config_validator.py               # Configuration validation
└── config_alert_manager.py           # Alert and notification management

scripts/config-management/
├── extract_postgresql_config.py      # PostgreSQL configuration extraction
├── extract_sqlite_config.py          # SQLite configuration extraction
├── extract_docker_config.py          # Docker configuration extraction
├── baseline_generator.py             # Baseline documentation generator
├── drift_scanner.py                  # Scheduled drift scanning
└── config_backup.py                  # Configuration backup utilities

docs/database/
├── configuration-baselines.md        # Main baseline documentation
├── postgresql-baseline.md            # PostgreSQL specific baselines
├── sqlite-baseline.md                # SQLite/DuckDB baselines
├── application-baseline.md           # Application configuration baselines
└── drift-detection-procedures.md     # Operational procedures

.github/workflows/
└── config-validation.yml             # CI/CD configuration validation

tests/
├── test_config_monitoring.py         # Unit tests for monitoring service
├── test_drift_detection.py           # Drift detection tests
├── test_config_validation.py         # Validation framework tests
└── test_integration_config.py        # Integration tests
```

## Success Criteria

### Technical Validation
- [ ] All database configurations documented with version control
- [ ] Automated drift detection operational with <5 minute detection time
- [ ] Configuration validation integrated with <2% pipeline overhead
- [ ] Change tracking captures 100% of configuration modifications
- [ ] Backup and restore procedures tested with <5 minute recovery time
- [ ] Compliance reporting provides real-time visibility

### Performance Criteria
- [ ] Configuration scanning completes within 30 seconds
- [ ] Drift detection accuracy >95% with <1% false positives
- [ ] Alert delivery within 2 minutes of detection
- [ ] System overhead <2% of baseline performance

### Security Criteria
- [ ] All sensitive configuration data encrypted at rest
- [ ] Access controls prevent unauthorized configuration access
- [ ] Audit logs capture all configuration access and changes
- [ ] Configuration drift alerts include security impact assessment

## Risk Mitigation

### High-Impact Risks
1. **Configuration monitoring exposes sensitive data**
   - **Mitigation**: Implement data masking and encryption
   - **Testing**: Security audit of all exposed configuration data

2. **False positive alerts cause alert fatigue**
   - **Mitigation**: Implement intelligent filtering and severity levels
   - **Testing**: Extended monitoring with threshold tuning

3. **Performance impact on production systems**
   - **Mitigation**: Asynchronous monitoring with configurable intervals
   - **Testing**: Load testing with monitoring enabled

### Medium-Impact Risks
1. **Configuration changes break existing functionality**
   - **Mitigation**: Comprehensive validation before deployment
   - **Testing**: Integration tests with configuration scenarios

2. **Drift detection misses critical changes**
   - **Mitigation**: Multiple detection algorithms with redundancy
   - **Testing**: Comprehensive test scenarios for all change types

## Rollback Plan

### Immediate Rollback (< 5 minutes)
1. Disable automated configuration monitoring
2. Remove CI/CD validation gates
3. Revert to manual configuration management
4. Preserve audit logs for analysis

### Data Recovery (< 15 minutes)
1. Restore configuration baseline data from backups
2. Rebuild configuration monitoring database
3. Re-import historical configuration data
4. Validate restored data integrity

### Service Recovery (< 30 minutes)
1. Restart configuration monitoring services
2. Re-enable drift detection with conservative thresholds
3. Gradually restore CI/CD integration
4. Monitor system performance and stability

## Dependencies

### Internal Dependencies
- Issue #262: Prerequisites for configuration access
- Parent Issue #260: Overall database management framework

### External Dependencies
- PostgreSQL (Keycloak) access for configuration extraction
- Docker API access for container configuration monitoring
- GitHub Actions permissions for CI/CD integration
- APISIX configuration access for gateway settings

### Technical Dependencies
- SQLAlchemy for database operations
- Pydantic for configuration validation schemas
- APScheduler for scheduled monitoring tasks
- Jinja2 for configuration templating

## Completion Timeline

**Total Estimated Time**: 10 working days
**Target Completion**: 2 weeks from start date
**Milestone Reviews**: After Phase 2, Phase 4, and Phase 5
**Go-Live Date**: Subject to successful testing and validation

This implementation plan provides a comprehensive roadmap for establishing database configuration baselines and implementing automated drift detection across the ViolentUTF platform, ensuring robust configuration management with proper monitoring, validation, and alerting capabilities.
