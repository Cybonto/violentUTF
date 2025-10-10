# ViolentUTF Configuration Baselines Documentation

## Overview

This document establishes configuration baselines for all ViolentUTF database systems and provides automated drift detection capabilities. This is part of Issue #265 implementation for database configuration monitoring.

## Configuration Monitoring Architecture

### Components

1. **Configuration Baseline Service** - Stores and manages configuration baselines
2. **Drift Detection Engine** - Detects changes between baseline and current configurations
3. **Alert Manager** - Sends notifications when critical configuration changes are detected
4. **Validation Engine** - Validates configurations against security and performance requirements

### Database Schema

The configuration monitoring system uses the following database tables:

```sql
-- Configuration baselines table
CREATE TABLE config_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_id VARCHAR(100) UNIQUE NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    config_path VARCHAR(500) NOT NULL,
    baseline_hash VARCHAR(64) NOT NULL,
    baseline_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configuration drift history
CREATE TABLE config_drift_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_id VARCHAR(100) NOT NULL,
    drift_type VARCHAR(50) NOT NULL,
    field_path VARCHAR(500),
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(20) DEFAULT 'medium'
);
```

## Configuration Baselines by Service

### 1. Keycloak (PostgreSQL)

**Service Name**: `keycloak`
**Configuration Type**: `postgresql`
**Configuration Path**: `/keycloak/docker-compose.yml`

#### Baseline Configuration

```yaml
postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: keycloak
    POSTGRES_USER: keycloak
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
    interval: 10s
    timeout: 5s
    retries: 5

keycloak:
  environment:
    KC_DB: postgres
    KC_DB_URL_HOST: postgres
    KC_DB_URL_PORT: 5432
    KC_DB_URL_DATABASE: keycloak
    KC_DB_USERNAME: keycloak
    KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
    KC_HOSTNAME: localhost
    KC_HTTP_ENABLED: true
    KC_HTTP_PORT: 8080
    KC_PROXY: edge
    KC_PROXY_HEADERS: xforwarded
    KC_HOSTNAME_STRICT: false
    KC_HOSTNAME_STRICT_HTTPS: false
    KC_HEALTH_ENABLED: true
    KC_METRICS_ENABLED: true
```

#### Security Configuration Requirements

- `POSTGRES_PASSWORD` must be strong (minimum 16 characters, mixed case, numbers, symbols)
- `KC_DB_PASSWORD` must match `POSTGRES_PASSWORD`
- `KC_PROXY` should be `edge` for production with reverse proxy
- `KC_HEALTH_ENABLED` and `KC_METRICS_ENABLED` should be `true` for monitoring

#### Performance Configuration Requirements

- `KC_DB_URL_PORT` must be `5432` for PostgreSQL
- Health check interval should be between 5-30 seconds
- Health check timeout should be less than interval
- Health check retries should be 3-10

### 2. FastAPI (SQLite)

**Service Name**: `fastapi`
**Configuration Type**: `sqlite`
**Configuration Path**: `/violentutf_api/fastapi_app/app/db/database.py`

#### Baseline Configuration

```python
# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./app_data/violentutf_api.db"

# SQLAlchemy engine settings
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True only in development
    future=True
)

# Session configuration
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

#### Application Configuration

```python
# Core settings
PROJECT_NAME: str = "ViolentUTF API"
ENVIRONMENT: str = "development"
DEBUG: bool = True
SECRET_KEY: str = "auto-generated"
JWT_SECRET_KEY: str = "auto-generated"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Database settings
DATABASE_URL: Optional[str] = None
APP_DATA_DIR: Path = Path("./app_data")
CONFIG_DIR: Path = Path("./config")

# External services
KEYCLOAK_URL: str = "http://localhost:8080"
KEYCLOAK_REALM: str = "ViolentUTF"
APISIX_BASE_URL: str = "http://localhost:9080"
APISIX_ADMIN_URL: str = "http://localhost:9180"
```

#### Security Configuration Requirements

- `SECRET_KEY` must be at least 32 characters
- `JWT_SECRET_KEY` must be different from `SECRET_KEY`
- `DEBUG` must be `False` in production
- `ACCESS_TOKEN_EXPIRE_MINUTES` should be 15-60 minutes
- All passwords and keys must be loaded from environment variables

#### Performance Configuration Requirements

- `echo` should be `False` in production to reduce logging overhead
- `expire_on_commit` should be `False` for async operations
- Database file should be on local SSD for best performance

### 3. PyRIT (DuckDB)

**Service Name**: `pyrit`
**Configuration Type**: `duckdb`
**Configuration Path**: `/violentutf_api/fastapi_app/app/db/duckdb_manager.py`

#### Baseline Configuration

```python
# DuckDB Manager configuration
PYRIT_MEMORY_DB_PATH: str = "/app/app_data/violentutf"
PYRIT_DB_SALT: str = "default_salt_2025"

# Database settings
db_path_pattern = "pyrit_memory_{hashed_username}.db"
app_data_dir = "./app_data/violentutf"

# Security settings
ALLOWED_UPDATE_COLUMNS = {
    "parameters", "status", "test_results", "updated_at",
    "name", "type", "config"
}

ALLOWED_TABLES = {
    "generators", "scorers", "datasets", "conversations",
    "orchestrator_executions", "orchestrator_results",
    "dataset_prompts", "converters", "user_sessions"
}
```

#### Security Configuration Requirements

- `PYRIT_DB_SALT` must be unique and at least 16 characters
- Database files must be user-specific with hashed usernames
- SQL operations must use parameterized queries only
- Column and table names must be validated against whitelists

#### Performance Configuration Requirements

- Database files should be created in fast storage location
- Connection pooling should be disabled for DuckDB (single-user database)
- Batch operations should be used for large data imports

### 4. APISIX (Gateway Configuration)

**Service Name**: `apisix`
**Configuration Type**: `gateway`
**Configuration Path**: `/apisix/conf/config.yaml`

#### Baseline Configuration

```yaml
etcd:
  timeout: 30
  host:
    - http://etcd:2379
  watch_timeout: 50
  startup_retry: 2
  prefix: /apisix

deployment:
  role: traditional
  config_provider: etcd
  admin:
    admin_key_required: true
    admin_api_version: v3
    enable_admin_cors: true
    admin_key:
      - role: admin
        key: ${APISIX_ADMIN_KEY}
        name: admin
    admin_listen:
      port: 9180
      ip: 0.0.0.0

plugin_attr:
  prometheus:
    enable_export_server: true
    export_uri: /apisix/prometheus/metrics
    export_addr:
      ip: 0.0.0.0
      port: 9091
```

#### Security Configuration Requirements

- `admin_key_required` must be `true`
- Admin key must be strong (minimum 32 characters)
- Admin API should only listen on internal interfaces in production
- CORS should be disabled in production (`enable_admin_cors: false`)

#### Performance Configuration Requirements

- etcd timeout should be 30-60 seconds
- Watch timeout should be greater than etcd timeout
- Prometheus metrics should be enabled for monitoring

## Configuration Change Severity Classification

### Critical Severity
Configuration changes that impact security or cause service failures:
- Password or secret key changes
- Authentication/authorization settings
- SSL/TLS configuration changes
- Database connection credentials

### High Severity
Configuration changes that impact performance or availability:
- Database ports or connection settings
- Timeout values significantly increased/decreased
- Resource limits (memory, connections)
- Service endpoints or URLs

### Medium Severity
Configuration changes that impact functionality:
- Feature flags or enablement settings
- Debug/logging level changes
- Environment-specific settings
- Network configuration

### Low Severity
Configuration changes with minimal impact:
- Documentation or comment changes
- Version numbers or labels
- Non-functional metadata

## Drift Detection Rules

### Automatic Detection
The system automatically detects:
1. **Modified Values** - When existing configuration values change
2. **Added Configuration** - When new configuration keys are added
3. **Removed Configuration** - When configuration keys are deleted
4. **Nested Changes** - When changes occur in nested configuration structures

### Detection Algorithms
1. **Hash-based Detection** - Quick identification using SHA-256 hashing
2. **Deep Comparison** - Recursive comparison of nested structures
3. **Schema Validation** - Ensure configurations meet defined requirements
4. **Security Validation** - Check for security policy violations

### Alert Thresholds
- **Critical**: Immediate alert (< 2 minutes)
- **High**: Alert within 5 minutes
- **Medium**: Alert within 15 minutes
- **Low**: Daily summary report

## Backup and Restoration Procedures

### Configuration Backup
1. **Automated Backup** - Daily backup of all configuration baselines
2. **Change-triggered Backup** - Backup before any configuration change
3. **Version Control** - All baselines stored with version history
4. **Encrypted Storage** - All backups encrypted at rest

### Restoration Process
1. **Immediate Rollback** - Restore previous configuration within 5 minutes
2. **Point-in-time Recovery** - Restore to any previous baseline
3. **Service Validation** - Verify service health after restoration
4. **Change Documentation** - Log all restoration activities

## Usage Examples

### Creating a Configuration Baseline

```python
from violentutf_api.fastapi_app.app.services.config_monitoring import (
    ConfigurationMonitoringService
)

# Initialize service
config_service = ConfigurationMonitoringService()

# Create baseline for Keycloak PostgreSQL configuration
baseline_id = await config_service.create_baseline(
    service_name="keycloak",
    config_type="postgresql",
    config_path="/keycloak/docker-compose.yml",
    config_data={
        "KC_DB": "postgres",
        "KC_DB_URL_HOST": "postgres",
        "KC_DB_URL_PORT": 5432,
        "KC_DB_URL_DATABASE": "keycloak",
        "KC_DB_USERNAME": "keycloak"
    }
)
```

### Detecting Configuration Drift

```python
from violentutf_api.fastapi_app.app.services.config_monitoring import DriftDetector

# Initialize drift detector
detector = DriftDetector()

# Compare configurations
baseline_config = {"host": "postgres", "port": 5432}
current_config = {"host": "postgres", "port": 5433}

drift_result = detector.detect_drift(baseline_config, current_config)

if drift_result.has_drift:
    print(f"Drift detected: {drift_result.severity}")
    for change in drift_result.changes:
        print(f"  {change.change_type}: {change.field_path}")
        print(f"    Old: {change.old_value}")
        print(f"    New: {change.new_value}")
```

## Monitoring and Alerting

### Metrics Collection
- Configuration change frequency
- Drift detection accuracy
- Alert response times
- Baseline coverage percentage

### Alert Channels
- Email notifications for critical changes
- Slack integration for team alerts
- Dashboard notifications for medium/low changes
- Audit log entries for all changes

### Escalation Procedures
1. **Critical Changes** - Immediate notification to security team
2. **Repeated Changes** - Escalate to system administrators
3. **Unauthorized Changes** - Trigger security incident response
4. **Failed Validations** - Block deployment until resolved

## Compliance and Auditing

### Audit Requirements
- All configuration access logged
- Change approval workflows for critical systems
- Regular compliance validation reports
- Retention of configuration history for 1 year

### Compliance Checks
- Security policy adherence
- Performance requirement validation
- Change management process compliance
- Documentation completeness verification

## Future Enhancements

### Planned Features
1. **Machine Learning** - Anomaly detection for configuration patterns
2. **Predictive Analysis** - Forecast configuration issues before they occur
3. **Auto-remediation** - Automatic rollback of problematic changes
4. **Integration** - Enhanced CI/CD pipeline integration
5. **Visualization** - Configuration dependency mapping and visualization

### Integration Points
- CI/CD pipeline integration
- Infrastructure as Code (IaC) validation
- Security scanning integration
- Performance monitoring correlation

## Conclusion

This configuration baseline system provides comprehensive monitoring and drift detection for all ViolentUTF database and service configurations. It ensures system stability, security, and compliance while providing rapid detection and response to configuration changes.

The implementation follows Test-Driven Development practices with comprehensive test coverage and adherence to security best practices for handling sensitive configuration data.
