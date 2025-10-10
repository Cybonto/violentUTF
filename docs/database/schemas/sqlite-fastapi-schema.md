# SQLite Database Schema Documentation - FastAPI Application

## Schema Overview

**Database**: `violentutf_api.db`
**Type**: SQLite with async support (aiosqlite)
**Location**: `/app/app_data/violentutf_api.db`
**ORM**: SQLAlchemy with AsyncSession
**Migration Tool**: Alembic
**Owner**: Backend Development Team
**Last Updated**: 2025-09-18

This document provides comprehensive schema documentation for the SQLite database supporting the ViolentUTF FastAPI backend application.

## Database Configuration

### Connection Details
- **Connection String**: `sqlite+aiosqlite:///app/app_data/violentutf_api.db`
- **Engine**: SQLAlchemy AsyncEngine with echo enabled in debug mode
- **Session Management**: AsyncSession with automatic commit/rollback
- **Container Volume**: `fastapi_data:/app/app_data`
- **Backup Strategy**: File-based backups and Docker volume snapshots

### SQLAlchemy Configuration
- **Base Class**: `declarative_base()` from SQLAlchemy
- **Session Factory**: `async_sessionmaker` with `expire_on_commit=False`
- **Transaction Management**: Automatic commit/rollback with exception handling
- **Migration Support**: Alembic for schema versioning and migrations

## Core Tables Overview

### Summary Matrix

| Table | Purpose | Records (Est.) | Growth Pattern | Relationships | Risk Level |
|-------|---------|---------------|----------------|---------------|------------|
| api_keys | API Key Management | 10-100 | Linear | None | High |
| orchestrator_configurations | PyRIT Orchestrator Setup | 20-50 | Slow | → orchestrator_executions | Medium |
| orchestrator_executions | Execution History | 100-1000 | Fast | orchestrator_configurations ← | Medium |
| report_templates | Report Templates | 10-30 | Slow | → generated_reports | Low |
| generated_reports | Generated Reports | 50-500 | Moderate | report_templates ← | Low |
| cob_templates | COB Report Templates | 5-20 | Slow | Multiple → | Low |
| cob_schedules | COB Report Schedules | 5-30 | Slow | cob_templates ← | Low |
| cob_reports | COB Report Instances | 20-200 | Moderate | cob_templates ← | Low |

## 1. Authentication and API Management

### api_keys Table
```sql
CREATE TABLE api_keys (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    key_hash VARCHAR NOT NULL UNIQUE,
    permissions JSON DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    last_used_at DATETIME NULL,
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX ix_api_keys_user_id ON api_keys (user_id);
CREATE UNIQUE INDEX ix_api_keys_key_hash ON api_keys (key_hash);
```

**Purpose**: API key management for service-to-service authentication
**Data Sensitivity**: HIGH - Contains hashed API keys and user associations
**Growth Pattern**: Linear with user adoption
**Retention Policy**: 1 year after expiration

**Columns**:
- `id`: Primary key (STRING, auto-generated UUID)
- `user_id`: User identifier from Keycloak (STRING, NOT NULL, INDEXED)
- `name`: Human-readable name for the API key (STRING, NOT NULL)
- `key_hash`: SHA-256 hash of the actual API key (STRING, NOT NULL, UNIQUE)
- `permissions`: JSON array of permissions (JSON, DEFAULT [])
- `created_at`: Creation timestamp (DATETIME, DEFAULT NOW)
- `expires_at`: Optional expiration date (DATETIME, NULLABLE)
- `last_used_at`: Last usage timestamp (DATETIME, NULLABLE)
- `is_active`: Active status flag (BOOLEAN, DEFAULT TRUE)

**Business Logic**:
- API keys are generated as UUIDs and hashed for storage
- Permissions are stored as JSON arrays for flexible authorization
- Automatic expiration checking through `is_expired()` method
- Usage tracking through `update_last_used()` method

## 2. PyRIT Orchestrator Management

### orchestrator_configurations Table
```sql
CREATE TABLE orchestrator_configurations (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    orchestrator_type VARCHAR(255) NOT NULL,
    description TEXT,
    parameters JSON NOT NULL,
    tags JSON,
    status VARCHAR(50) DEFAULT 'configured',
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    pyrit_identifier JSON,
    instance_active BOOLEAN DEFAULT 0
);

CREATE UNIQUE INDEX ix_orchestrator_configurations_name ON orchestrator_configurations (name);
CREATE INDEX ix_orchestrator_configurations_type ON orchestrator_configurations (orchestrator_type);
CREATE INDEX ix_orchestrator_configurations_status ON orchestrator_configurations (status);
```

**Purpose**: Storage and management of PyRIT orchestrator configurations
**Data Sensitivity**: MEDIUM - Contains system configurations and parameters
**Growth Pattern**: Slow growth with new orchestrator types
**Retention Policy**: Permanent (configuration data)

**Columns**:
- `id`: Primary key (UUID, auto-generated)
- `name`: Unique orchestrator name (VARCHAR(255), NOT NULL, UNIQUE)
- `orchestrator_type`: Type of PyRIT orchestrator (VARCHAR(255), NOT NULL)
- `description`: Human-readable description (TEXT, NULLABLE)
- `parameters`: JSON configuration parameters (JSON, NOT NULL)
- `tags`: JSON array of organizational tags (JSON, NULLABLE)
- `status`: Configuration status (VARCHAR(50), DEFAULT 'configured')
- `created_by`: Username of creator (VARCHAR(255), NULLABLE)
- `created_at`: Creation timestamp (DATETIME, DEFAULT NOW)
- `updated_at`: Last update timestamp (DATETIME, DEFAULT NOW, ON UPDATE NOW)
- `pyrit_identifier`: PyRIT-specific identifier data (JSON, NULLABLE)
- `instance_active`: Whether orchestrator instance is active (BOOLEAN, DEFAULT FALSE)

**Relationships**:
- **One-to-Many** with `orchestrator_executions` (via `orchestrator_id`)

### orchestrator_executions Table
```sql
CREATE TABLE orchestrator_executions (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    orchestrator_id UUID NOT NULL,
    execution_name VARCHAR(255),
    execution_type VARCHAR(50),
    input_data JSON,
    status VARCHAR(50) DEFAULT 'running',
    results JSON,
    execution_summary JSON,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    created_by VARCHAR(255),
    pyrit_memory_session VARCHAR(255),
    conversation_ids JSON,
    FOREIGN KEY (orchestrator_id) REFERENCES orchestrator_configurations (id)
);

CREATE INDEX ix_orchestrator_executions_orchestrator_id ON orchestrator_executions (orchestrator_id);
CREATE INDEX ix_orchestrator_executions_status ON orchestrator_executions (status);
CREATE INDEX ix_orchestrator_executions_created_by ON orchestrator_executions (created_by);
CREATE INDEX ix_orchestrator_executions_started_at ON orchestrator_executions (started_at);
```

**Purpose**: Execution history and results for PyRIT orchestrators
**Data Sensitivity**: MEDIUM to HIGH - Contains security testing results
**Growth Pattern**: Fast growth with active testing
**Retention Policy**: 90 days for execution logs, permanent for summaries

**Columns**:
- `id`: Primary key (UUID, auto-generated)
- `orchestrator_id`: Reference to orchestrator configuration (UUID, NOT NULL, FK)
- `execution_name`: Name of the execution (VARCHAR(255), NULLABLE)
- `execution_type`: Type of execution (VARCHAR(50), NULLABLE)
- `input_data`: JSON input configuration (JSON, NULLABLE)
- `status`: Execution status (VARCHAR(50), DEFAULT 'running')
- `results`: JSON execution results (JSON, NULLABLE)
- `execution_summary`: JSON summary statistics (JSON, NULLABLE)
- `started_at`: Execution start time (DATETIME, DEFAULT NOW)
- `completed_at`: Execution completion time (DATETIME, NULLABLE)
- `created_by`: Username of executor (VARCHAR(255), NULLABLE)
- `pyrit_memory_session`: PyRIT memory session ID (VARCHAR(255), NULLABLE)
- `conversation_ids`: JSON array of conversation IDs (JSON, NULLABLE)

**Business Logic**:
- Tracks complete execution lifecycle from start to completion
- Links to PyRIT memory system through `pyrit_memory_session`
- Supports multiple execution types (prompt_list, dataset, etc.)
- Stores both detailed results and summary statistics

## 3. Report Management System

### report_templates Table
```sql
CREATE TABLE report_templates (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    template_type VARCHAR(20) NOT NULL DEFAULT 'custom',
    sections JSON NOT NULL,
    requirements JSON NOT NULL DEFAULT '{}',
    settings JSON NOT NULL DEFAULT '{}',
    tags JSON NOT NULL DEFAULT '[]',
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(255)
);

CREATE UNIQUE INDEX ix_report_templates_name ON report_templates (name);
CREATE INDEX ix_report_templates_category ON report_templates (category);
CREATE INDEX ix_report_templates_template_type ON report_templates (template_type);
```

**Purpose**: Template definitions for report generation
**Data Sensitivity**: LOW - Contains template structure, no sensitive data
**Growth Pattern**: Slow growth with new template types
**Retention Policy**: Permanent (template definitions)

**Columns**:
- `id`: Primary key (UUID, auto-generated)
- `name`: Unique template name (VARCHAR(100), NOT NULL, UNIQUE)
- `description`: Template description (TEXT, NOT NULL)
- `category`: Template category (VARCHAR(50), NOT NULL)
- `template_type`: Type (builtin/custom) (VARCHAR(20), DEFAULT 'custom')
- `sections`: JSON template structure (JSON, NOT NULL)
- `requirements`: JSON requirements specification (JSON, DEFAULT {})
- `settings`: JSON default settings (JSON, DEFAULT {})
- `tags`: JSON search tags (JSON, DEFAULT [])
- `is_active`: Active status (BOOLEAN, DEFAULT TRUE)
- `created_at`: Creation timestamp (DATETIME, DEFAULT NOW)
- `updated_at`: Update timestamp (DATETIME, DEFAULT NOW, ON UPDATE NOW)
- `created_by`: Creator username (VARCHAR(255), NULLABLE)

### generated_reports Table
```sql
CREATE TABLE generated_reports (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    output_format VARCHAR(20) NOT NULL DEFAULT 'html',
    execution_ids JSON NOT NULL,
    settings JSON NOT NULL,
    file_path TEXT,
    file_size VARCHAR(50),
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at DATETIME,
    created_by VARCHAR(255) NOT NULL,
    FOREIGN KEY (template_id) REFERENCES report_templates (id)
);

CREATE INDEX ix_generated_reports_template_id ON generated_reports (template_id);
CREATE INDEX ix_generated_reports_status ON generated_reports (status);
CREATE INDEX ix_generated_reports_created_by ON generated_reports (created_by);
CREATE INDEX ix_generated_reports_created_at ON generated_reports (created_at);
```

**Purpose**: Instance tracking for generated reports
**Data Sensitivity**: LOW to MEDIUM - Contains report metadata and file paths
**Growth Pattern**: Moderate growth with report generation
**Retention Policy**: 6 months for completed reports

**Relationships**:
- **Many-to-One** with `report_templates` (via `template_id`)

## 4. COB (Chief of Bots) Report System

### cob_templates Table
```sql
CREATE TABLE cob_templates (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    template_config JSON NOT NULL,
    ai_prompts JSON,
    export_formats JSON DEFAULT '["markdown", "pdf", "json"]',
    tags JSON,
    is_active BOOLEAN DEFAULT 1,
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ix_cob_templates_name ON cob_templates (name);
CREATE INDEX ix_cob_templates_is_active ON cob_templates (is_active);
```

**Purpose**: COB report template definitions with AI integration
**Data Sensitivity**: LOW - Template structure and AI prompt configurations
**Growth Pattern**: Slow growth with new COB template types
**Retention Policy**: Permanent (template definitions)

### cob_schedules Table
```sql
CREATE TABLE cob_schedules (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    frequency VARCHAR(20) NOT NULL,
    schedule_time VARCHAR(8) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    days_of_week JSON,
    day_of_month VARCHAR(2),
    ai_model_config JSON,
    export_config JSON,
    is_active BOOLEAN DEFAULT 1,
    next_run_at DATETIME,
    last_run_at DATETIME,
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES cob_templates (id)
);

CREATE INDEX ix_cob_schedules_template_id ON cob_schedules (template_id);
CREATE INDEX ix_cob_schedules_is_active ON cob_schedules (is_active);
CREATE INDEX ix_cob_schedules_next_run_at ON cob_schedules (next_run_at);
```

**Purpose**: Automated scheduling for COB report generation
**Data Sensitivity**: LOW - Scheduling configuration and timing
**Growth Pattern**: Slow growth with automated reporting needs
**Retention Policy**: Permanent (scheduling configuration)

### cob_reports Table
```sql
CREATE TABLE cob_reports (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL,
    schedule_id UUID,
    report_name VARCHAR(255) NOT NULL,
    report_period_start DATETIME,
    report_period_end DATETIME,
    generation_status VARCHAR(50) DEFAULT 'generating',
    content_blocks JSON,
    ai_analysis_results JSON,
    export_results JSON,
    generation_metadata JSON,
    generated_by VARCHAR(255),
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (template_id) REFERENCES cob_templates (id),
    FOREIGN KEY (schedule_id) REFERENCES cob_schedules (id)
);

CREATE INDEX ix_cob_reports_template_id ON cob_reports (template_id);
CREATE INDEX ix_cob_reports_schedule_id ON cob_reports (schedule_id);
CREATE INDEX ix_cob_reports_generation_status ON cob_reports (generation_status);
CREATE INDEX ix_cob_reports_generated_at ON cob_reports (generated_at);
```

**Purpose**: Generated COB report instances with AI analysis
**Data Sensitivity**: MEDIUM - Contains analysis results and generated content
**Growth Pattern**: Moderate growth with scheduled and manual generation
**Retention Policy**: 1 year for report instances

## 5. Extended COB Report Features

### cob_template_versions Table
```sql
CREATE TABLE cob_template_versions (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL,
    version VARCHAR(20) NOT NULL,
    change_notes TEXT,
    snapshot JSON NOT NULL,
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES cob_templates (id)
);

CREATE INDEX ix_cob_template_versions_template_id ON cob_template_versions (template_id);
CREATE INDEX ix_cob_template_versions_version ON cob_template_versions (version);
```

**Purpose**: Version history and change tracking for COB templates
**Data Sensitivity**: LOW - Template versioning information
**Growth Pattern**: Moderate with template modifications
**Retention Policy**: 2 years for version history

### cob_scan_data_cache Table
```sql
CREATE TABLE cob_scan_data_cache (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR UNIQUE,
    scanner_type VARCHAR(50),
    target_model VARCHAR(255),
    scan_date DATETIME,
    score_data JSON,
    raw_results JSON,
    scan_metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
);

CREATE UNIQUE INDEX ix_cob_scan_data_cache_execution_id ON cob_scan_data_cache (execution_id);
CREATE INDEX ix_cob_scan_data_cache_scanner_type ON cob_scan_data_cache (scanner_type);
CREATE INDEX ix_cob_scan_data_cache_expires_at ON cob_scan_data_cache (expires_at);
```

**Purpose**: Cache for scan data used in COB report generation
**Data Sensitivity**: HIGH - Contains security scan results and vulnerabilities
**Growth Pattern**: Fast growth with active scanning
**Retention Policy**: 30 days (cache cleanup based on expires_at)

### cob_report_variables Table
```sql
CREATE TABLE cob_report_variables (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100),
    variable_name VARCHAR(255) UNIQUE,
    description TEXT,
    data_type VARCHAR(50),
    source VARCHAR(50),
    example_value TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ix_cob_report_variables_variable_name ON cob_report_variables (variable_name);
CREATE INDEX ix_cob_report_variables_category ON cob_report_variables (category);
CREATE INDEX ix_cob_report_variables_source ON cob_report_variables (source);
```

**Purpose**: Registry of available variables for COB report templates
**Data Sensitivity**: LOW - Variable definitions and metadata
**Growth Pattern**: Slow growth with new variable types
**Retention Policy**: Permanent (variable registry)

### cob_block_definitions Table
```sql
CREATE TABLE cob_block_definitions (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    block_type VARCHAR(100) UNIQUE,
    display_name VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    configuration_schema JSON,
    default_config JSON,
    supported_formats JSON DEFAULT '["PDF", "JSON", "Markdown"]',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ix_cob_block_definitions_block_type ON cob_block_definitions (block_type);
CREATE INDEX ix_cob_block_definitions_category ON cob_block_definitions (category);
```

**Purpose**: Block type definitions for COB report templates
**Data Sensitivity**: LOW - Block type configurations
**Growth Pattern**: Slow growth with new block types
**Retention Policy**: Permanent (block definitions)

### cob_schedule_executions Table
```sql
CREATE TABLE cob_schedule_executions (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL,
    report_id UUID,
    execution_status VARCHAR(50) DEFAULT 'started',
    execution_log JSON,
    error_details JSON,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    execution_duration_seconds VARCHAR(10),
    FOREIGN KEY (schedule_id) REFERENCES cob_schedules (id),
    FOREIGN KEY (report_id) REFERENCES cob_reports (id)
);

CREATE INDEX ix_cob_schedule_executions_schedule_id ON cob_schedule_executions (schedule_id);
CREATE INDEX ix_cob_schedule_executions_report_id ON cob_schedule_executions (report_id);
CREATE INDEX ix_cob_schedule_executions_execution_status ON cob_schedule_executions (execution_status);
```

**Purpose**: Execution tracking for scheduled COB report generation
**Data Sensitivity**: LOW - Execution metadata and logs
**Growth Pattern**: Moderate with scheduled executions
**Retention Policy**: 90 days for execution logs

## Database Relationships

### Primary Relationships
1. **orchestrator_configurations → orchestrator_executions**: One-to-Many
2. **report_templates → generated_reports**: One-to-Many
3. **cob_templates → cob_schedules**: One-to-Many
4. **cob_templates → cob_reports**: One-to-Many
5. **cob_schedules → cob_reports**: One-to-Many
6. **cob_templates → cob_template_versions**: One-to-Many
7. **cob_schedules → cob_schedule_executions**: One-to-Many
8. **cob_reports → cob_schedule_executions**: One-to-Many

### Foreign Key Constraints
- **CASCADE DELETE**: Template deletion removes associated reports/schedules
- **RESTRICT DELETE**: Prevent deletion of templates with active schedules
- **NULL ON DELETE**: Optional relationships allow orphaned records

## Performance Optimization

### Indexing Strategy
- **Primary Keys**: Automatic clustered indexes on all UUID primary keys
- **Foreign Keys**: Non-clustered indexes on all foreign key columns
- **Search Columns**: Indexes on frequently searched columns (name, status, type)
- **Date Columns**: Indexes on date columns for time-based queries
- **Unique Constraints**: Unique indexes on business keys (name, execution_id)

### Query Optimization Patterns
- **Execution Queries**: Optimized for status-based filtering and date ranges
- **Report Queries**: Optimized for template-based and user-based filtering
- **Template Queries**: Optimized for category and active status filtering
- **Cache Queries**: Optimized for expiration cleanup and execution ID lookup

### Performance Characteristics
- **Read-Heavy Workload**: Most operations are read-heavy (configuration lookup, report viewing)
- **Write Operations**: Moderate write activity for executions and report generation
- **Batch Operations**: Cleanup operations for expired cache entries and old executions
- **Concurrent Access**: Moderate concurrency requirements for multi-user access

## Data Types and JSON Schemas

### JSON Column Schemas

#### orchestrator_configurations.parameters
```json
{
  "target": "string",
  "scoring_methods": ["array", "of", "strings"],
  "prompt_template": "string",
  "max_turns": "integer",
  "custom_settings": {
    "key": "value"
  }
}
```

#### cob_templates.template_config
```json
{
  "blocks": [
    {
      "type": "executive_summary",
      "title": "string",
      "config": {}
    }
  ],
  "layout": "string",
  "styling": {}
}
```

#### cob_scan_data_cache.score_data
```json
{
  "overall_score": "number",
  "category_scores": {
    "category": "number"
  },
  "risk_level": "string",
  "findings_count": "integer"
}
```

## Security Considerations

### Data Protection
- **API Keys**: Stored as SHA-256 hashes, never plain text
- **Sensitive Configuration**: Encryption recommended for sensitive parameters
- **Access Control**: User-based filtering for all queries
- **Audit Trail**: Timestamps and user tracking on all modifications

### Database Security
- **File Permissions**: Database file restricted to container user
- **Connection Security**: Internal container access only
- **Backup Security**: Encrypted backup storage recommended
- **Data Retention**: Automatic cleanup of expired and old data

### Compliance Requirements
- **Audit Logging**: All modifications tracked with user and timestamp
- **Data Retention**: Configurable retention policies for different data types
- **Access Tracking**: Last access timestamps for API keys and reports
- **Data Classification**: Clear sensitivity levels for all table contents

## Maintenance and Operations

### Regular Maintenance Tasks
- **Index Maintenance**: SQLite automatic index optimization
- **Cache Cleanup**: Expired scan data cache cleanup (daily)
- **Execution Cleanup**: Old execution log cleanup (weekly)
- **Statistics Update**: SQLite automatic statistics updates

### Monitoring Points
- **Database Size**: Monitor file size growth and available storage
- **Query Performance**: Monitor slow queries and index usage
- **Cache Hit Rate**: Monitor cache effectiveness for scan data
- **Execution Patterns**: Monitor orchestrator usage and performance

### Backup and Recovery
- **File-Based Backup**: Daily backup of database file
- **Docker Volume Backup**: Container volume snapshots
- **Point-in-Time Recovery**: Transaction log backup (if enabled)
- **Disaster Recovery**: Cross-region backup replication

## Migration and Schema Evolution

### Alembic Integration
- **Migration Scripts**: Located in `alembic/versions/`
- **Schema Versioning**: Automatic version tracking
- **Rollback Support**: Downgrade scripts for rollback capability
- **Environment Configuration**: Multiple environment support (dev/prod)

### Migration Procedures
1. **Development**: Test migrations in development environment
2. **Validation**: Validate data integrity after migration
3. **Production**: Scheduled maintenance window for production migrations
4. **Rollback**: Prepared rollback plan for each migration

### Version Control
- **Schema Tracking**: All schema changes tracked in Git
- **Documentation Updates**: Schema documentation updated with each migration
- **Change Approval**: Migration review process for production changes

## Troubleshooting

### Common Issues
1. **Lock Contention**: SQLite write locks during high concurrency
2. **Storage Space**: Database file size growth beyond available storage
3. **Query Performance**: Slow queries on large execution history tables
4. **JSON Validation**: Invalid JSON data in configuration columns

### Diagnostic Queries
```sql
-- Check database size and table statistics
SELECT name, COUNT(*) as row_count
FROM sqlite_master
WHERE type='table'
GROUP BY name;

-- Check API key usage
SELECT user_id, COUNT(*) as key_count,
       MAX(last_used_at) as last_activity
FROM api_keys
WHERE is_active = 1
GROUP BY user_id;

-- Check orchestrator execution patterns
SELECT orchestrator_id, status, COUNT(*) as execution_count
FROM orchestrator_executions
WHERE started_at > date('now', '-30 days')
GROUP BY orchestrator_id, status;

-- Check report generation status
SELECT template_id, generation_status, COUNT(*) as report_count
FROM cob_reports
WHERE generated_at > date('now', '-7 days')
GROUP BY template_id, generation_status;
```

### Recovery Procedures
1. **Database Corruption**: Restore from backup, run integrity check
2. **Performance Issues**: Analyze query plans, rebuild indexes
3. **Data Inconsistency**: Run foreign key consistency checks
4. **Storage Issues**: Implement cleanup procedures, archive old data

---

**Document Information**
- **Classification**: INTERNAL
- **Review Cycle**: Quarterly
- **Next Review**: 2025-12-18
- **Contact**: Backend Development Team, Database Administrator
- **Related Documents**: Database Inventory, PostgreSQL Schema, Risk Assessment
