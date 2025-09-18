# Issue #279 Implementation Plan: Automated Discovery Scripts Development

## Executive Summary

This implementation plan addresses GitHub issue #279 for developing comprehensive automated discovery scripts for database detection across containers, services, file systems, and source code within ViolentUTF's multi-database environment.

## Problem Statement & Analysis

ViolentUTF currently operates a complex multi-database environment including:
- PostgreSQL (Keycloak authentication)
- SQLite (FastAPI application data)
- DuckDB (PyRIT memory storage, being deprecated)
- File-based storage configurations

The current manual database discovery and inventory processes are:
- Time-intensive and error-prone
- Unable to track dynamic container deployments
- Missing security credential exposure risks
- Lacking automated compliance reporting

## Solution Architecture

### 1. Core Discovery Modules

#### Container-Based Discovery (`container_discovery.py`)
- **Docker Compose Analysis**: Parse all `docker-compose*.yml` files
- **Running Container Inspection**: Use python-on-whales for runtime detection
- **Volume and Network Analysis**: Map database storage and connectivity

#### Network-Based Discovery (`network_discovery.py`)
- **Database Port Scanning**: Scan common database ports (5432, 3306, 1433, 27017)
- **Service Fingerprinting**: Identify database types through banners
- **Network Topology Mapping**: Document connectivity patterns

#### File System Discovery (`filesystem_discovery.py`)
- **SQLite Database Discovery**: Scan for `.db`, `.sqlite`, `.sqlite3` files
- **DuckDB File Discovery**: Locate deprecated DuckDB files for migration
- **Configuration File Analysis**: Extract database configs from YAML/JSON/ENV

#### Code-Based Discovery (`code_discovery.py`)
- **AST-Based Pattern Detection**: Parse Python code for database patterns
- **Connection String Extraction**: Identify database connection configurations
- **Import and Dependency Analysis**: Analyze requirements.txt for database deps

#### Security Integration (`security_scanner.py`)
- **detect-secrets Integration**: Scan for database credentials
- **Bandit Security Analysis**: Identify SQL injection vulnerabilities

### 2. Discovery Orchestration System

#### Discovery Orchestrator (`orchestrator.py`)
- Coordinate multi-module execution
- Implement parallel processing for performance
- Handle cross-validation and confidence scoring
- Generate comprehensive reports

#### FastAPI Backend Integration
- New discovery service endpoints in `violentutf_api/fastapi_app/app/services/discovery/`
- SQLAlchemy models for discovery results
- Pydantic schemas for API contracts
- Authentication and authorization integration

### 3. Reporting and Documentation System

#### Machine-Readable Reports
- Standardized JSON format with metadata
- Confidence scoring and validation status
- Incremental and diff reporting capabilities

#### Human-Readable Documentation
- Markdown reports for technical teams
- Executive summaries with key metrics
- Security and operational recommendations

## Technical Implementation Details

### Directory Structure
```
scripts/database-automation/discovery/
├── __init__.py
├── container_discovery.py      # Docker/container analysis
├── network_discovery.py        # Network scanning and fingerprinting
├── filesystem_discovery.py     # File system database detection
├── code_discovery.py          # AST-based code analysis
├── security_scanner.py        # Security and credential scanning
├── orchestrator.py            # Discovery coordination
├── models.py                  # Data models and schemas
├── utils.py                   # Common utilities
└── exceptions.py              # Custom exception classes

violentutf_api/fastapi_app/app/services/discovery/
├── __init__.py
├── discovery_service.py       # Main service implementation
├── validation_service.py      # Result validation logic
└── reporting_service.py       # Report generation

violentutf_api/fastapi_app/app/models/
├── discovery.py               # SQLAlchemy models

violentutf_api/fastapi_app/app/schemas/
├── discovery.py               # Pydantic schemas

tests/
├── test_discovery/
│   ├── test_container_discovery.py
│   ├── test_network_discovery.py
│   ├── test_filesystem_discovery.py
│   ├── test_code_discovery.py
│   ├── test_security_scanner.py
│   ├── test_orchestrator.py
│   └── test_integration.py
└── test_api/
    └── test_discovery_api.py
```

### Required Dependencies
```
# Core discovery libraries
python-on-whales>=0.65.0      # Docker container inspection
python-nmap>=0.7.1             # Network scanning
pathlib                        # File system operations (built-in)
ast                            # Code analysis (built-in)

# Security scanning
detect-secrets>=1.4.0          # Credential detection
bandit>=1.7.5                  # Security analysis

# FastAPI integration
sqlalchemy>=2.0.0              # Database ORM
pydantic>=2.0.0               # Data validation
alembic>=1.12.0               # Database migrations

# Utilities
pyyaml>=6.0                    # YAML parsing
jsonschema>=4.17.0            # JSON validation
click>=8.1.0                  # CLI interface
rich>=13.0.0                  # Enhanced terminal output
```

### Performance Targets
- **Execution Time**: Complete discovery in under 5 minutes
- **Memory Usage**: Maximum 512MB during execution
- **CPU Usage**: Maximum 25% utilization
- **Accuracy**: 95% true positive rate with minimal false positives

### Security Requirements
- Read-only operations only
- Secure handling of discovered credentials
- Integration with existing ViolentUTF authentication
- Comprehensive audit logging

## Implementation Phases

### Phase 1: Core Infrastructure (Days 1-2)
1. Set up project structure and base classes
2. Implement common utilities and exception handling
3. Create SQLAlchemy models and Pydantic schemas
4. Set up basic testing framework

### Phase 2: Discovery Modules (Days 3-5)
1. Implement container discovery with python-on-whales
2. Develop network discovery with nmap integration
3. Create file system discovery for all database types
4. Build AST-based code analysis for database patterns

### Phase 3: Security Integration (Day 6)
1. Integrate detect-secrets for credential scanning
2. Implement bandit security analysis
3. Add security validation and scoring

### Phase 4: Orchestration and API (Days 7-8)
1. Build discovery orchestrator with parallel execution
2. Implement FastAPI service endpoints
3. Create result validation and confidence scoring
4. Add comprehensive error handling and logging

### Phase 5: Reporting and Documentation (Days 9-10)
1. Implement JSON and Markdown report generation
2. Create API documentation and usage guides
3. Write operational procedures and troubleshooting guides
4. Implement GitHub Actions integration

### Phase 6: Testing and Validation (Days 11-12)
1. Complete comprehensive test suite
2. Performance testing and optimization
3. Security testing and validation
4. Integration testing with ViolentUTF environment

## Success Criteria

### Functional Requirements
- ✅ Discovers all 4 known ViolentUTF database systems
- ✅ Completes full environment scan in under 5 minutes
- ✅ Generates machine-readable discovery reports in JSON format
- ✅ Achieves 95% accuracy in database detection
- ✅ Integrates with GitHub Actions for automation
- ✅ Provides comprehensive logging and error handling

### Quality Requirements
- ✅ 85% minimum test coverage
- ✅ Follows ViolentUTF coding standards
- ✅ Security scan compliance
- ✅ Performance targets met
- ✅ Code review approval

### Integration Requirements
- ✅ FastAPI backend integration
- ✅ Authentication and authorization
- ✅ Database model persistence
- ✅ API documentation completion
- ✅ GitHub Actions workflow

## Risk Mitigation

### Technical Risks
- **Docker Access**: Ensure proper permissions for container inspection
- **Network Scanning**: Implement rate limiting to avoid performance impact
- **Security Scanning**: Handle false positives and credential exposure
- **Performance**: Optimize for large codebases and multiple databases

### Operational Risks
- **Service Disruption**: Implement read-only operations and safe scanning
- **Credential Exposure**: Secure handling and storage of discovered secrets
- **Resource Usage**: Monitor and limit CPU/memory consumption
- **Error Handling**: Comprehensive exception handling and recovery

## Testing Strategy

### Unit Testing
- Individual module testing with mock data
- Edge case and error condition testing
- Performance testing for each component
- Security validation testing

### Integration Testing
- Cross-module coordination testing
- FastAPI endpoint integration testing
- Database persistence testing
- Authentication and authorization testing

### End-to-End Testing
- Complete discovery workflow testing
- Report generation and validation
- GitHub Actions integration testing
- Performance and scalability testing

## Documentation Deliverables

### Technical Documentation
- API documentation with OpenAPI specs
- Architecture diagrams and data flow
- Database discovery taxonomy
- Troubleshooting and error resolution guides

### Operational Documentation
- Discovery procedures manual
- Configuration and customization guide
- Report interpretation guide
- Security and compliance procedures

### User Documentation
- Quick start guide
- CLI usage documentation
- Integration examples
- Best practices guide

## Conclusion

This implementation plan provides a comprehensive roadmap for developing automated discovery scripts that meet all requirements of issue #279. The modular architecture ensures maintainability and extensibility, while the focus on security and performance addresses the critical needs of the ViolentUTF platform.

The planned implementation will significantly reduce manual effort in database discovery while improving accuracy and security compliance, directly supporting ViolentUTF's mission as an enterprise-grade AI red-teaming platform.
