# ViolentUTF Database Inventory

## Executive Summary

**Document Version**: 1.0
**Last Updated**: 2025-09-18
**Created By**: Database Audit Team (Issue #262)
**Review Date**: 2025-12-18

This document provides a comprehensive inventory of all database systems, data storage mechanisms, and data repositories within the ViolentUTF enterprise AI red-teaming platform. The inventory encompasses 4 primary database systems, 7 storage mechanisms, and multiple file-based data repositories supporting the platform's multi-service architecture.

### Key Findings
- **4 Primary Database Systems** identified and cataloged
- **2 Active Production Databases** (PostgreSQL, SQLite)
- **1 Deprecated Database System** (DuckDB - migration required)
- **7 File-Based Storage Mechanisms** documented
- **3 High-Risk Data Classification Areas** identified
- **2 Critical Database Dependencies** for platform operation

## Database Systems Overview

### Summary Matrix

| System | Type | Purpose | Status | Risk Level | Data Sensitivity | Compliance Impact |
|--------|------|---------|---------|------------|-----------------|-------------------|
| PostgreSQL (Keycloak) | Relational DB | Authentication/SSO | Production | High | Restricted | Critical |
| SQLite (FastAPI) | Embedded DB | Application Data | Production | Medium | Confidential | High |
| DuckDB (PyRIT) | Analytics DB | Memory Storage | Deprecated | High | Confidential | Medium |
| File Storage | File System | Config/Logs | Production | Medium | Internal | Medium |

## 1. PostgreSQL Database (Keycloak SSO)

### System Information
- **Database Type**: PostgreSQL 15
- **Location**: Docker container `postgres` in `keycloak` service stack
- **Container Image**: `postgres:15`
- **Network**: `postgres-network`, `vutf-network`
- **Data Volume**: `postgres_data:/var/lib/postgresql/data`
- **Database Name**: `keycloak`
- **Default User**: `keycloak`

### Access Configuration
- **Port**: 5432 (internal), not exposed externally
- **Connection Method**: JDBC from Keycloak service
- **Authentication**: Username/password from environment variables
- **SSL/TLS**: Configured for internal communications
- **Backup Location**: Docker volume (`postgres_data`)

### Purpose and Usage
- **Primary Function**: User authentication and authorization for ViolentUTF platform
- **Data Types**: User credentials, session tokens, realm configurations, role assignments
- **Transaction Volume**: Medium (authentication events, session management)
- **Growth Pattern**: Linear growth with user base
- **Dependencies**: Critical dependency for all platform authentication

### Service Integration
- **Consuming Services**: Keycloak SSO service
- **Dependent Services**: All ViolentUTF services requiring authentication
- **API Access**: Through Keycloak REST API and admin console
- **Monitoring**: Health checks via PostgreSQL native commands

### Data Sensitivity
- **Classification Level**: RESTRICTED
- **Data Types**: User credentials, authentication tokens, session data
- **Compliance Requirements**: GDPR (Article 32), SOC 2 Type II
- **Retention Policy**: User data retained per GDPR requirements
- **Encryption**: At-rest encryption via Docker volume encryption

### Operational Characteristics
- **Estimated Size**: < 100MB (current), grows with user base
- **Performance Profile**: Low-latency read/write operations
- **Peak Usage**: During authentication events and session validation
- **Backup Strategy**: Docker volume snapshots, database dumps
- **Recovery Time Objective (RTO)**: 15 minutes
- **Recovery Point Objective (RPO)**: 1 hour

## 2. SQLite Database (FastAPI Application)

### System Information
- **Database Type**: SQLite with async support (aiosqlite)
- **Location**: FastAPI container filesystem at `/app/app_data/violentutf_api.db`
- **Container**: `violentutf_api` (FastAPI service)
- **ORM**: SQLAlchemy with async session management
- **Migration Tool**: Alembic (configured)

### Access Configuration
- **Connection String**: `sqlite+aiosqlite:///app/app_data/violentutf_api.db`
- **Session Management**: AsyncSession with automatic commit/rollback
- **Connection Pooling**: SQLAlchemy async session factory
- **File Permissions**: Container user access only
- **Backup Location**: Docker volume `fastapi_data`

### Purpose and Usage
- **Primary Function**: Application data storage for ViolentUTF API
- **Data Types**: Orchestrator configurations, execution logs, system metrics
- **Transaction Volume**: Medium (API operations, configuration changes)
- **Growth Pattern**: Moderate growth with usage and configuration complexity
- **Dependencies**: Non-critical for authentication, critical for orchestrator management

### Schema Overview
**Primary Tables**:
- `orchestrator_configurations`: Orchestrator setup and parameters
- `orchestrator_executions`: Execution history and results
- `database_metadata`: Schema versioning and migrations
- `system_metrics`: Performance and usage statistics

### Service Integration
- **Consuming Services**: FastAPI backend service
- **API Access**: RESTful API endpoints at `/api/v1/`
- **Authentication**: JWT-based authentication via Keycloak integration
- **Monitoring**: Database performance monitoring enabled

### Data Sensitivity
- **Classification Level**: CONFIDENTIAL
- **Data Types**: System configurations, operational logs, execution results
- **Compliance Requirements**: SOC 2 Type II, audit logging requirements
- **Retention Policy**: 90 days for execution logs, permanent for configurations
- **Encryption**: File-level encryption via container security

### Operational Characteristics
- **Estimated Size**: < 50MB (current), moderate growth expected
- **Performance Profile**: Fast local file access, optimized for read operations
- **Peak Usage**: During orchestrator execution and API operations
- **Backup Strategy**: File-based backups, Docker volume snapshots
- **Recovery Time Objective (RTO)**: 5 minutes
- **Recovery Point Objective (RPO)**: 30 minutes

## 3. DuckDB Storage (PyRIT Memory - DEPRECATED)

### System Information
- **Database Type**: DuckDB (columnar analytics database)
- **Location**: File system at `/app/app_data/violentutf/`
- **File Pattern**: `pyrit_memory_[hash].db`
- **Status**: DEPRECATED - Migration to new storage required
- **Migration Timeline**: Q1 2025

### Current Usage
- **Purpose**: PyRIT conversation memory and attack scenario storage
- **Access Method**: Direct file access through PyRIT SDK
- **File Management**: User-specific database files with hash-based naming
- **Data Retention**: Persistent storage of security testing conversations

### Deprecation Details
- **Reason**: Performance limitations and scaling issues
- **Impact**: Historical data migration required
- **Migration Target**: Enhanced SQLite integration or cloud storage
- **Timeline**: Complete migration by Q1 2025
- **Risk**: Data loss if migration not completed

### Current File Inventory
```
violentutf/app_data/violentutf/pyrit_memory_ffb7bf7b42c725c17f1e2b1c6ebc9df67678d75552527bddc4eb02188b89505d.db
```

### Data Sensitivity
- **Classification Level**: CONFIDENTIAL
- **Data Types**: Security testing conversations, attack patterns, vulnerability data
- **Compliance Requirements**: Audit logging, data retention for security analysis
- **Retention Policy**: 6 months for active testing, archive for compliance
- **Migration Priority**: HIGH (critical for platform continuity)

## 4. File-Based Storage Systems

### Configuration Storage

#### YAML Configuration Files
- **Location**: `violentutf/parameters/`
- **Purpose**: PyRIT orchestrator and scorer configurations
- **File Types**: `.yaml`, `.yml`
- **Access Method**: File system read/write
- **Data Sensitivity**: INTERNAL
- **Examples**:
  - `default_parameters.yaml`: Default PyRIT configuration
  - Orchestrator-specific parameter files
  - Scorer configuration templates

#### JSON Configuration Files
- **Location**: Multiple directories (`apisix/conf/`, `keycloak/`)
- **Purpose**: Service configuration and route definitions
- **File Types**: `.json`
- **Access Method**: Application-specific configuration loading
- **Data Sensitivity**: INTERNAL

### Environment Configuration
- **File Pattern**: `.env`, `.env.*`
- **Locations**: Service-specific directories
- **Purpose**: Environment variables, secrets, service configuration
- **Data Sensitivity**: RESTRICTED (contains credentials and secrets)
- **Security**: Never committed to version control
- **Examples**:
  - `keycloak/.env`: Database credentials
  - `apisix/.env`: Admin credentials
  - `violentutf_api/fastapi_app/.env`: API configuration
  - `ai-tokens.env`: AI provider API keys

### Log Storage

#### Application Logs
- **Location**: `violentutf_logs/`, container-specific log directories
- **Purpose**: Application events, error tracking, audit trails
- **File Types**: `.log`, `.txt`
- **Rotation**: Daily rotation, 30-day retention
- **Data Sensitivity**: INTERNAL to CONFIDENTIAL (depending on content)

#### Security Testing Logs
- **Location**: Service-specific app_data directories
- **Purpose**: PyRIT execution logs, security testing results
- **Access Method**: Application-generated, file system storage
- **Data Sensitivity**: CONFIDENTIAL (security testing data)

### Cache and Temporary Storage

#### Application Cache
- **Location**: `violentutf/app_data/`, `violentutf_api/fastapi_app/app_data/`
- **Purpose**: Temporary data, session storage, computation caches
- **Lifecycle**: Ephemeral, cleared on service restart
- **Data Sensitivity**: INTERNAL
- **Management**: Automatic cleanup, size limits

#### Docker Volumes
- **Volumes**: `fastapi_data`, `fastapi_config`, `postgres_data`
- **Purpose**: Persistent storage for containers
- **Backup**: Docker volume backup procedures
- **Data Sensitivity**: Varies by content (INTERNAL to RESTRICTED)

## Service Dependencies and Data Flow

### Authentication Flow
1. **User Access** → Streamlit UI (Port 8501)
2. **Authentication** → Keycloak SSO (Port 8080) → PostgreSQL Database
3. **JWT Token** → APISIX Gateway (Port 9080) → FastAPI Backend
4. **API Access** → SQLite Database → Response

### Data Storage Flow
1. **User Inputs** → Streamlit UI
2. **Configuration** → File-based storage (YAML/JSON)
3. **Execution Data** → SQLite Database (FastAPI)
4. **Memory Storage** → DuckDB Files (PyRIT - deprecated)
5. **Logs** → File-based storage (multiple locations)

### Inter-Service Communication
- **Keycloak ↔ PostgreSQL**: Direct database connection
- **FastAPI ↔ SQLite**: Direct database connection via SQLAlchemy
- **PyRIT ↔ DuckDB**: Direct file access (deprecated)
- **All Services ↔ File Storage**: Direct file system access

## Security and Access Control

### Database Access Security
- **PostgreSQL**: Network isolation, credential-based access
- **SQLite**: File system permissions, container isolation
- **DuckDB**: File system permissions (deprecated)
- **File Storage**: Container-level security, mount restrictions

### Network Security
- **Internal Networks**: `postgres-network`, `apisix_network`, `vutf-network`
- **External Access**: Only through APISIX gateway (Port 9080)
- **SSL/TLS**: Configured for external communications
- **Firewall**: Container-level network isolation

### Authentication and Authorization
- **Primary Method**: Keycloak SSO with JWT tokens
- **API Security**: JWT validation on all endpoints
- **Database Security**: Service-specific credentials
- **File Security**: Container-level permissions

## Performance and Scalability

### Current Performance Characteristics
- **PostgreSQL**: Optimized for authentication workloads
- **SQLite**: Fast local access, suitable for current scale
- **DuckDB**: Performance issues identified (reason for deprecation)
- **File Storage**: Direct file system access, minimal overhead

### Scalability Considerations
- **PostgreSQL**: Can scale with Keycloak clustering
- **SQLite**: Limited to single-node, suitable for current requirements
- **File Storage**: Scales with container storage allocation
- **Network**: Current architecture supports moderate scaling

### Performance Monitoring
- **Database Metrics**: Connection counts, query performance
- **File System**: Storage utilization, I/O performance
- **Application Metrics**: Response times, error rates
- **Resource Usage**: CPU, memory, disk utilization

## Compliance and Audit Requirements

### Data Protection Compliance
- **GDPR**: User data in PostgreSQL, retention policies established
- **SOC 2 Type II**: Audit logging across all systems
- **Security Standards**: Encryption at rest and in transit
- **Access Controls**: Role-based access, audit trails

### Audit Trail Requirements
- **Authentication Events**: Logged in Keycloak/PostgreSQL
- **API Access**: Logged in FastAPI/SQLite
- **Configuration Changes**: Logged in application logs
- **Security Testing**: Logged in PyRIT memory and execution logs

### Retention Policies
- **User Data**: GDPR-compliant retention (2 years max)
- **Audit Logs**: 7 years retention for compliance
- **Application Logs**: 90 days retention
- **Security Testing Data**: 6 months active, archive as needed

## Risk Assessment Summary

### Critical Risks
1. **Single Point of Failure**: PostgreSQL for authentication
2. **Data Migration Risk**: DuckDB deprecation and migration
3. **Backup Dependencies**: Docker volume backup procedures

### Medium Risks
1. **SQLite Scaling**: Single-node limitations
2. **File Storage Security**: Credential exposure in environment files
3. **Network Dependencies**: Service interdependencies

### Low Risks
1. **Performance Degradation**: Under current usage patterns
2. **Storage Capacity**: Current storage requirements well within limits
3. **Version Compatibility**: Database version management

## Recommendations

### Immediate Actions (30 Days)
1. **Implement PostgreSQL Backup**: Automated database backups
2. **Plan DuckDB Migration**: Detailed migration strategy and timeline
3. **Enhance Monitoring**: Database performance monitoring
4. **Document Recovery Procedures**: Disaster recovery procedures

### Short-term Actions (90 Days)
1. **Complete DuckDB Migration**: Migrate to new storage system
2. **Implement High Availability**: PostgreSQL clustering options
3. **Enhanced Security**: Encryption at rest implementation
4. **Compliance Audit**: Third-party security assessment

### Long-term Actions (6 Months)
1. **Architecture Review**: Database architecture optimization
2. **Performance Optimization**: Query optimization and indexing
3. **Scaling Preparation**: Prepare for increased usage
4. **Advanced Monitoring**: Comprehensive monitoring and alerting

## Maintenance and Operations

### Regular Maintenance Tasks
- **Daily**: Health checks, log rotation
- **Weekly**: Database optimization, backup verification
- **Monthly**: Security updates, performance review
- **Quarterly**: Capacity planning, architecture review

### Emergency Procedures
- **Database Failure**: Recovery procedures documented
- **Data Corruption**: Backup restoration procedures
- **Security Incident**: Incident response plan
- **Service Outage**: Service restoration procedures

## Contact Information

### Database Ownership
- **PostgreSQL (Keycloak)**: Infrastructure Team
- **SQLite (FastAPI)**: Backend Development Team
- **File Storage**: DevOps Team
- **Overall Coordination**: Database Audit Team

### Escalation Procedures
- **Level 1**: Service-specific teams
- **Level 2**: Infrastructure team
- **Level 3**: Platform architecture team
- **Emergency**: On-call rotation

---

**Document Information**
- **Classification**: INTERNAL
- **Distribution**: Database Team, Infrastructure Team, Security Team
- **Review Cycle**: Quarterly
- **Next Review**: 2025-12-18
- **Version Control**: Git repository under docs/database/
- **Related Documents**: Risk Assessment, Data Classification Matrix, Schema Documentation
