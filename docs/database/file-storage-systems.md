# File-Based Storage Systems Documentation

## Executive Summary

**Document Version**: 1.0
**Last Updated**: 2025-09-18
**Scope**: ViolentUTF file-based storage systems and patterns
**Owner**: DevOps Team
**Review Date**: 2025-12-18

This document provides comprehensive documentation of all file-based storage systems, configurations, and data patterns within the ViolentUTF platform. The analysis encompasses 7 major file storage categories, 15+ configuration file types, and multiple log and cache systems supporting the platform's distributed architecture.

## Storage Systems Overview

### Summary Matrix

| Storage Category | File Types | Location | Purpose | Data Sensitivity | Growth Pattern | Risk Level |
|------------------|------------|----------|---------|------------------|----------------|------------|
| Configuration Files | YAML, JSON | Multiple | Service Config | INTERNAL | Slow | Medium |
| Environment Files | .env | Service Dirs | Secrets/Config | RESTRICTED | Slow | High |
| Application Logs | .log, .txt | violentutf_logs/ | Audit/Debug | INTERNAL-CONF | Fast | Medium |
| Cache Storage | Various | app_data/ | Temporary Data | INTERNAL | Fast | Low |
| PyRIT Parameters | YAML | parameters/ | AI Config | INTERNAL | Moderate | Medium |
| Docker Volumes | N/A | Docker | Persistent Data | VARIES | Moderate | Medium |
| SSL Certificates | .pem, .crt | certs/ | Security | RESTRICTED | Slow | High |

## 1. Configuration File Systems

### YAML Configuration Files

#### PyRIT Parameters Directory
**Location**: `violentutf/parameters/`
**Purpose**: PyRIT orchestrator and scorer configurations
**Data Sensitivity**: INTERNAL
**Access Method**: File system read/write during orchestrator initialization

**File Structure**:
```
violentutf/parameters/
├── default_parameters.yaml          # Default PyRIT configuration
├── orchestrator_configs/
│   ├── red_team_orchestrator.yaml  # Red team configuration
│   ├── multi_turn_orchestrator.yaml # Multi-turn conversation config
│   └── custom_orchestrator.yaml    # Custom orchestrator settings
├── scorer_configs/
│   ├── azure_content_safety.yaml   # Azure safety scorer config
│   ├── openai_content_moderation.yaml # OpenAI moderation config
│   └── custom_scorers.yaml         # Custom scoring configurations
└── target_configs/
    ├── openai_targets.yaml          # OpenAI API target configurations
    ├── anthropic_targets.yaml       # Anthropic API target configurations
    └── local_model_targets.yaml     # Local model configurations
```

**Data Patterns**:
```yaml
# Example: default_parameters.yaml
orchestrator:
  max_turns: 10
  conversation_memory: true
  target_model: "gpt-3.5-turbo"

scoring:
  enabled_scorers:
    - "azure_content_safety"
    - "self_ask_refusal"
  scoring_threshold: 0.7

security:
  content_filters: true
  prompt_injection_detection: true
  output_validation: true
```

**Usage Patterns**:
- Read during orchestrator initialization
- Modified through Streamlit configuration interface
- Versioned through Git for tracking changes
- Validated against JSON schema for correctness

#### Service Configuration Files
**Locations**: `apisix/conf/`, `keycloak/`, service-specific directories
**Purpose**: Service-specific configuration and route definitions
**Data Sensitivity**: INTERNAL

**APISIX Configuration**:
```
apisix/conf/
├── config.yaml                     # Main APISIX configuration
├── dashboard.yaml                  # Dashboard configuration
├── prometheus.yml                  # Monitoring configuration
└── routes/
    ├── api_routes.yaml             # API route definitions
    ├── auth_routes.yaml            # Authentication routes
    └── mcp_routes.yaml             # MCP server routes
```

**Keycloak Configuration**:
```
keycloak/
├── realm-export.json              # Realm configuration export
├── custom-themes/                 # UI customization
└── extensions/                    # Custom extensions
```

### JSON Configuration Files

#### Application Configuration
**Purpose**: Runtime configuration for various services
**Data Sensitivity**: INTERNAL to CONFIDENTIAL (depending on content)

**Common JSON Configuration Types**:
- **Route Definitions**: APISIX route configurations
- **Realm Settings**: Keycloak realm and client configurations
- **Feature Flags**: Application feature toggles
- **UI Settings**: Streamlit interface configurations
- **Integration Settings**: Third-party service configurations

**Example Structures**:
```json
{
  "apisix_routes": {
    "api_v1": {
      "uri": "/api/v1/*",
      "upstream": "violentutf_api",
      "plugins": ["jwt-auth", "rate-limit"]
    }
  },
  "feature_flags": {
    "enable_garak_integration": true,
    "enable_advanced_reporting": true,
    "enable_mcp_tools": true
  }
}
```

## 2. Environment Configuration

### Environment Files (.env)

#### Distribution and Locations
```
Environment Files Discovered:
├── ai-tokens.env                   # AI provider API keys (RESTRICTED)
├── ai-tokens.env.sample           # Template for AI tokens (PUBLIC)
├── apisix/.env                     # APISIX admin credentials (RESTRICTED)
├── violentutf_api/fastapi_app/.env # API configuration (RESTRICTED)
├── violentutf_api/fastapi_app/.env.template # Template (PUBLIC)
├── violentutf_api/fastapi_app/.env.backup # Backup configuration (RESTRICTED)
├── violentutf/.env                 # Streamlit configuration (INTERNAL)
└── keycloak/.env                   # Database credentials (RESTRICTED)
```

#### Security Classification by File

##### RESTRICTED Level (.env files with credentials)
**Files**: `ai-tokens.env`, `apisix/.env`, `keycloak/.env`, `violentutf_api/fastapi_app/.env`
**Content Types**:
- API keys and tokens
- Database passwords
- Admin credentials
- Encryption keys
- Service secrets

**Example Content Patterns** (sanitized):
```bash
# ai-tokens.env
OPENAI_API_KEY=sk-***redacted***
ANTHROPIC_API_KEY=sk-ant-***redacted***
AZURE_OPENAI_KEY=***redacted***

# keycloak/.env
POSTGRES_PASSWORD=***redacted***
KEYCLOAK_ADMIN_PASSWORD=***redacted***

# apisix/.env
APISIX_ADMIN_KEY=***redacted***
ETCD_AUTH_TOKEN=***redacted***
```

##### INTERNAL Level (.env files with configuration)
**Files**: `violentutf/.env`
**Content Types**:
- Service URLs
- Feature flags
- Non-sensitive configuration
- Debug settings

**Security Measures**:
- Never committed to version control
- Restricted file permissions (600)
- Container-level access control
- Automatic rotation for API keys
- Backup encryption

### Environment File Management

#### Template System
**Purpose**: Provide secure templates for environment configuration
**Files**: `.env.template`, `.env.sample`
**Usage**: Safe to commit to version control, contain placeholder values

**Template Example**:
```bash
# .env.template
OPENAI_API_KEY=your_openai_key_here
POSTGRES_PASSWORD=your_secure_password
DEBUG_MODE=false
LOG_LEVEL=INFO
```

#### Version Control Security
- **Gitignore Rules**: All `.env` files excluded from version control
- **Pre-commit Hooks**: Scan for accidentally committed secrets
- **Secret Detection**: Automated scanning for exposed credentials
- **Rotation Procedures**: Regular rotation of API keys and passwords

## 3. Application Logs

### Log Directory Structure
```
violentutf_logs/
├── application/
│   ├── streamlit.log              # Streamlit application logs
│   ├── fastapi.log                # FastAPI backend logs
│   └── authentication.log         # Auth-specific logs
├── security/
│   ├── pyrit_executions.log       # PyRIT execution logs
│   ├── security_events.log        # Security event logs
│   └── audit_trail.log            # Audit and compliance logs
├── system/
│   ├── docker_compose.log         # Container orchestration logs
│   ├── apisix_access.log          # API gateway access logs
│   └── performance.log            # Performance monitoring logs
└── archived/
    ├── 2025-01/                   # Monthly archived logs
    └── 2025-02/
```

### Log Categories and Characteristics

#### Application Logs
**Purpose**: Application events, errors, and debugging information
**Data Sensitivity**: INTERNAL to CONFIDENTIAL
**Retention**: 30 days active, 6 months archived
**Format**: Structured JSON logging with timestamps

**Log Entry Example**:
```json
{
  "timestamp": "2025-09-18T10:30:45.123Z",
  "level": "INFO",
  "service": "violentutf_api",
  "module": "orchestrator_service",
  "message": "Orchestrator execution started",
  "user_id": "violentutf.web",
  "execution_id": "uuid-here",
  "metadata": {
    "orchestrator_type": "red_team",
    "target_model": "gpt-3.5-turbo"
  }
}
```

#### Security Logs
**Purpose**: Security events, testing results, and compliance auditing
**Data Sensitivity**: CONFIDENTIAL
**Retention**: 90 days active, 7 years archived (compliance)
**Special Handling**: Encrypted storage, access controls

#### Audit Logs
**Purpose**: Compliance and regulatory audit trails
**Data Sensitivity**: CONFIDENTIAL
**Retention**: 7 years (regulatory requirement)
**Immutability**: Write-once, tamper-evident storage

### Log Management

#### Rotation Policies
- **Daily Rotation**: Active logs rotated daily at midnight UTC
- **Size Limits**: Individual log files limited to 100MB
- **Compression**: Archived logs compressed with gzip
- **Cleanup**: Automated cleanup based on retention policies

#### Monitoring and Alerting
- **Error Rate Monitoring**: Alerts on error threshold breaches
- **Disk Usage**: Monitoring for log directory disk usage
- **Log Parsing**: Automated parsing for security events
- **Compliance Reporting**: Regular compliance status reports

## 4. Cache and Temporary Storage

### Application Cache Directory
```
violentutf/app_data/
├── violentutf/
│   ├── pyrit_memory_*.db          # PyRIT memory files (deprecated)
│   ├── conversation_cache/        # Conversation caches
│   ├── model_cache/               # AI model response caches
│   └── session_data/              # User session temporary data
├── reports/
│   ├── generated/                 # Generated report files
│   ├── templates/                 # Cached report templates
│   └── exports/                   # Report export files
└── uploads/
    ├── datasets/                  # Uploaded dataset files
    ├── configurations/            # Uploaded config files
    └── temporary/                 # Temporary upload storage
```

### Cache Characteristics

#### Performance Cache
**Purpose**: Application performance optimization
**Data Types**: API responses, computation results, rendered content
**Lifecycle**: Memory-based with file backup, cleared on restart
**Size Management**: LRU eviction, 1GB size limit

#### Session Cache
**Purpose**: User session state and temporary data
**Data Types**: User preferences, form data, navigation state
**Lifecycle**: Session-based, cleared on logout
**Security**: User-isolated storage, automatic cleanup

#### File Upload Cache
**Purpose**: Temporary storage for user uploads
**Data Types**: Dataset files, configuration uploads, report exports
**Lifecycle**: 24-hour retention, automatic cleanup
**Validation**: File type validation, virus scanning, size limits

### Cache Management

#### Cleanup Procedures
```python
# Example cache cleanup logic
def cleanup_cache_directories():
    """Clean up expired cache files"""
    cache_dirs = [
        "violentutf/app_data/violentutf/conversation_cache",
        "violentutf/app_data/reports/generated",
        "violentutf/app_data/uploads/temporary"
    ]

    for cache_dir in cache_dirs:
        cleanup_expired_files(cache_dir, max_age_hours=24)
```

## 5. Docker Volume Storage

### Volume Configuration
```yaml
# From docker-compose analysis
volumes:
  postgres_data:              # PostgreSQL database storage
    driver: local
  fastapi_data:              # FastAPI application data
    driver: local
  fastapi_config:            # FastAPI configuration
    driver: local
  apisix_config:             # APISIX configuration
    driver: local
```

### Volume Mount Patterns

#### Persistent Data Volumes
**Purpose**: Database and application state persistence
**Characteristics**: Survive container restarts, require backup
**Examples**: PostgreSQL data, SQLite databases, user uploads

**Mount Examples**:
```yaml
# PostgreSQL data persistence
- postgres_data:/var/lib/postgresql/data

# FastAPI application data
- fastapi_data:/app/app_data
- fastapi_config:/app/config

# Cross-service data sharing
- ../violentutf/app_data/violentutf:/app/app_data/violentutf
```

#### Configuration Volumes
**Purpose**: Configuration file injection into containers
**Characteristics**: Read-only mounts, version-controlled sources
**Examples**: APISIX config, SSL certificates, service configs

### Volume Management

#### Backup Strategies
- **Database Volumes**: Daily snapshots with retention policy
- **Application Volumes**: File-level backup with incremental changes
- **Configuration Volumes**: Git-based versioning and backup
- **Cross-Region Replication**: Available for disaster recovery

#### Monitoring and Maintenance
- **Usage Monitoring**: Track volume size growth and utilization
- **Performance Monitoring**: I/O performance and latency tracking
- **Health Checks**: Volume integrity and accessibility checks
- **Cleanup Procedures**: Automated cleanup of temporary data

## 6. SSL Certificate Storage

### Certificate Directory Structure
```
certs/
├── ca/
│   ├── ca-cert.pem                # Certificate Authority certificate
│   └── ca-key.pem                 # CA private key (RESTRICTED)
├── server/
│   ├── server-cert.pem            # Server certificate
│   ├── server-key.pem             # Server private key (RESTRICTED)
│   └── server-csr.pem             # Certificate signing request
├── client/
│   ├── client-cert.pem            # Client certificate
│   └── client-key.pem             # Client private key (RESTRICTED)
└── zscaler/
    ├── zscaler-root-ca.pem        # Zscaler root CA (if applicable)
    └── zscaler-intermediate.pem   # Zscaler intermediate CA
```

### Certificate Management

#### Certificate Types and Usage
- **Server Certificates**: HTTPS/TLS for external communications
- **Client Certificates**: Mutual TLS authentication
- **CA Certificates**: Certificate authority for internal PKI
- **Proxy Certificates**: Corporate proxy/firewall certificates

#### Security Measures
- **Private Key Protection**: 400 permissions, encrypted storage
- **Certificate Rotation**: Automated renewal before expiration
- **Revocation Lists**: CRL and OCSP for certificate validation
- **Backup and Recovery**: Secure backup of private keys

## 7. Storage Performance and Optimization

### Performance Characteristics

#### Read-Heavy Workloads
- **Configuration Files**: Cached in memory after initial read
- **Log Files**: Primarily write operations with occasional read
- **Cache Files**: Optimized for fast read access
- **Certificate Files**: Read during service initialization

#### Write Patterns
- **Log Files**: High-frequency append operations
- **Cache Files**: Frequent write/update operations
- **Configuration Files**: Infrequent update operations
- **Database Files**: Managed by database engines

### Optimization Strategies

#### File System Optimization
- **SSD Storage**: Fast storage for frequently accessed files
- **File System Tuning**: Optimized for workload patterns
- **Compression**: Automatic compression for archived data
- **Indexing**: File system indexing for fast searches

#### Caching Strategies
- **Memory Caching**: Frequently accessed files in memory
- **Application Caching**: Application-level caching layers
- **CDN Integration**: Content delivery for static assets
- **Database Caching**: Query result caching

## 8. Security and Compliance

### Access Control

#### File System Permissions
```bash
# Example permission structure
/app/app_data/                     # 755 (rwxr-xr-x)
├── violentutf/                   # 755 (rwxr-xr-x)
│   ├── *.db                      # 644 (rw-r--r--)
│   └── cache/                    # 755 (rwxr-xr-x)
├── .env                          # 600 (rw-------)
├── logs/                         # 755 (rwxr-xr-x)
│   └── *.log                     # 644 (rw-r--r--)
└── certs/
    ├── *.pem (public)            # 644 (rw-r--r--)
    └── *-key.pem (private)       # 400 (r--------)
```

#### Container-Level Security
- **User Isolation**: Non-root container users
- **Volume Mounting**: Selective volume mounting with restrictions
- **Network Isolation**: Container network segregation
- **Resource Limits**: Memory and CPU limits for containers

### Data Protection

#### Encryption
- **At-Rest Encryption**: File system level encryption
- **In-Transit Encryption**: TLS for network communications
- **Application Encryption**: Sensitive data encryption
- **Key Management**: Secure key storage and rotation

#### Backup and Recovery
- **Automated Backups**: Scheduled backup procedures
- **Version Control**: Configuration file versioning
- **Disaster Recovery**: Cross-region backup replication
- **Testing**: Regular backup restoration testing

### Compliance

#### Audit Requirements
- **File Access Logging**: Audit trails for file access
- **Change Tracking**: Version control for configuration changes
- **Retention Policies**: Compliance-based data retention
- **Access Reviews**: Regular access permission reviews

#### Data Classification
- **PUBLIC**: Documentation, templates, samples
- **INTERNAL**: Application configurations, logs
- **CONFIDENTIAL**: Security logs, user data
- **RESTRICTED**: Credentials, private keys, tokens

## 9. Monitoring and Alerting

### File System Monitoring

#### Disk Usage Monitoring
```python
# Example monitoring script
def monitor_storage_usage():
    """Monitor storage usage across file systems"""
    monitored_paths = [
        "/app/app_data",
        "/var/log",
        "/app/config",
        "/tmp"
    ]

    alerts = []
    for path in monitored_paths:
        usage = get_disk_usage(path)
        if usage.percent > 85:
            alerts.append(f"High disk usage on {path}: {usage.percent}%")

    return alerts
```

#### Performance Monitoring
- **I/O Performance**: Read/write latency and throughput
- **File System Health**: File system integrity checks
- **Cache Hit Rates**: Application cache effectiveness
- **Log Growth Rates**: Log file growth monitoring

### Alerting Thresholds
- **Disk Usage**: Alert at 85%, critical at 95%
- **Log Growth**: Alert on unusual growth patterns
- **File Access**: Alert on unauthorized access attempts
- **Cache Performance**: Alert on degraded cache performance

## 10. Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks
- **Log Rotation**: Rotate and compress log files
- **Cache Cleanup**: Remove expired cache files
- **Backup Validation**: Verify backup completion
- **Security Scan**: Scan for exposed credentials

#### Weekly Tasks
- **Storage Analysis**: Analyze storage usage patterns
- **Performance Review**: Review file system performance
- **Configuration Audit**: Audit configuration changes
- **Access Review**: Review file access patterns

#### Monthly Tasks
- **Archive Management**: Archive old logs and data
- **Certificate Review**: Check certificate expiration
- **Capacity Planning**: Plan for storage growth
- **Disaster Recovery Test**: Test backup restoration

### Automation Scripts

#### Cleanup Automation
```bash
#!/bin/bash
# automated_cleanup.sh
# Automated file system cleanup script

# Clean up temporary files older than 24 hours
find /app/app_data/uploads/temporary -type f -mtime +1 -delete

# Clean up log files older than 30 days
find /var/log/violentutf -name "*.log" -mtime +30 -delete

# Clean up cache files older than 7 days
find /app/app_data/*/cache -type f -mtime +7 -delete

# Compress log files older than 1 day
find /var/log/violentutf -name "*.log" -mtime +1 -exec gzip {} \;
```

## Conclusion

The ViolentUTF file-based storage systems provide a comprehensive foundation for configuration management, logging, caching, and data persistence. The documented patterns and procedures ensure secure, efficient, and maintainable storage operations across the platform's distributed architecture.

Regular monitoring, automated maintenance, and adherence to security best practices maintain system reliability and compliance with enterprise standards.

---

**Document Information**
- **Classification**: INTERNAL
- **Distribution**: DevOps Team, Security Team, Platform Administrators
- **Review Cycle**: Quarterly
- **Next Review**: 2025-12-18
- **Version Control**: Git repository under docs/database/
- **Related Documents**: Database Inventory, Security Procedures, Monitoring Guidelines
