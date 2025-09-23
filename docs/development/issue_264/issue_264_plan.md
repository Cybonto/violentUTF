# Issue #264 Implementation Plan: Database Dependency Mapping and Impact Analysis System

## Executive Summary

This implementation plan outlines the development of a comprehensive database dependency mapping and impact analysis system for ViolentUTF. The system will automatically discover, map, and analyze dependencies across the database ecosystem including SQLite, DuckDB, PostgreSQL (Keycloak), and service-level relationships.

## Problem Analysis

ViolentUTF's complex architecture includes multiple database systems:
1. **SQLite** - FastAPI primary data storage (`violentutf_api.db`)
2. **DuckDB** - PyRIT memory storage (per-user databases)
3. **PostgreSQL** - Keycloak authentication database
4. **In-memory stores** - Session data, caches, configuration

Current challenges:
- No centralized dependency tracking
- Manual change impact assessment
- Risk of unplanned outages during updates
- Lack of rollback procedures considering dependencies

## Technical Architecture

### Core Components

#### 1. Dependency Discovery Service (`violentutf_api/fastapi_app/app/services/dependency_mapping.py`)
```python
class DependencyMappingService:
    - discover_code_dependencies()      # Static code analysis
    - discover_runtime_dependencies()   # Runtime tracing
    - map_service_dependencies()        # Service-to-database mapping
    - update_dependency_matrix()        # Maintain dependency state
```

#### 2. Dependency Models (`violentutf_api/fastapi_app/app/models/dependency.py`)
```python
class DatabaseDependency:
    - source_service: str
    - target_database: str
    - dependency_type: DependencyType
    - criticality: CriticalityLevel
    - discovery_method: str
    - last_updated: datetime

class ServiceDependency:
    - service_name: str
    - dependent_services: List[str]
    - database_connections: List[str]
    - health_check_url: str
```

#### 3. Impact Analysis Engine (`violentutf_api/fastapi_app/app/services/impact_analysis.py`)
```python
class ImpactAnalysisService:
    - analyze_change_impact()
    - generate_rollback_plan()
    - calculate_risk_score()
    - create_deployment_sequence()
```

#### 4. Visualization API (`violentutf_api/fastapi_app/app/api/endpoints/dependencies.py`)
```python
# Endpoints:
# GET /api/v1/dependencies/matrix
# GET /api/v1/dependencies/graph
# GET /api/v1/dependencies/impact-analysis
# POST /api/v1/dependencies/analyze-change
```

## Implementation Strategy

### Phase 1: Dependency Discovery Foundation

#### 1.1 Code-based Dependency Analysis
- Scan Python imports for database libraries
- Parse SQLAlchemy models and configurations
- Analyze DuckDB connection patterns
- Map API endpoints to database operations

#### 1.2 Runtime Dependency Tracing
- Implement database connection monitoring
- Trace PyRIT orchestrator database usage
- Monitor Keycloak authentication flows
- Record transaction patterns

#### 1.3 Service-level Mapping
- Map Streamlit → FastAPI dependencies
- Document APISIX → service routing
- Track Keycloak authentication dependencies
- Identify MCP server database usage

### Phase 2: Impact Analysis Framework

#### 2.1 Change Impact Templates
```yaml
# Database Schema Change Template
schema_change:
  affected_tables: []
  breaking_changes: []
  migration_required: boolean
  estimated_downtime: duration
  affected_services: []
  rollback_complexity: low|medium|high

# Service Configuration Change Template
service_change:
  service_name: str
  configuration_changes: []
  restart_required: boolean
  dependent_services: []
  database_impact: []
```

#### 2.2 Automated Impact Analysis
- Dependency graph traversal algorithms
- Ripple effect calculation
- Risk scoring methodology
- Deployment sequence optimization

### Phase 3: Visualization and Documentation

#### 3.1 Dependency Visualization
- Interactive dependency graphs using D3.js/Cytoscape
- Real-time dependency status dashboard
- Drill-down capability for detailed analysis
- Mobile-responsive design

#### 3.2 Documentation Automation
- Auto-generated dependency matrix
- Change impact assessment reports
- Rollback procedure documentation
- Version-controlled dependency snapshots

## Database Schema Design

### Dependency Mapping Tables

```sql
-- Core dependency relationships
CREATE TABLE dependency_relationships (
    id TEXT PRIMARY KEY,
    source_service TEXT NOT NULL,
    target_service TEXT,
    target_database TEXT,
    dependency_type TEXT NOT NULL, -- 'database', 'service', 'api', 'authentication'
    criticality TEXT NOT NULL,     -- 'critical', 'high', 'medium', 'low'
    discovery_method TEXT NOT NULL, -- 'code_analysis', 'runtime_trace', 'manual'
    connection_string TEXT,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                 -- JSON for additional properties
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Service health and status tracking
CREATE TABLE service_health (
    id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL,
    health_status TEXT NOT NULL,   -- 'healthy', 'degraded', 'down'
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    error_message TEXT,
    dependencies_status TEXT       -- JSON of dependency health
);

-- Change impact analysis history
CREATE TABLE impact_analyses (
    id TEXT PRIMARY KEY,
    change_description TEXT NOT NULL,
    proposed_changes TEXT NOT NULL, -- JSON
    impact_assessment TEXT NOT NULL, -- JSON
    risk_score INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    implemented BOOLEAN DEFAULT FALSE,
    implementation_date TIMESTAMP
);
```

## API Endpoint Specifications

### Dependency Management Endpoints

```python
# GET /api/v1/dependencies/matrix
@router.get("/matrix")
async def get_dependency_matrix() -> DependencyMatrix:
    """Return complete dependency matrix"""

# GET /api/v1/dependencies/graph
@router.get("/graph")
async def get_dependency_graph() -> DependencyGraph:
    """Return dependency graph for visualization"""

# POST /api/v1/dependencies/discover
@router.post("/discover")
async def trigger_dependency_discovery() -> DiscoveryResult:
    """Trigger dependency discovery process"""

# POST /api/v1/dependencies/analyze-change
@router.post("/analyze-change")
async def analyze_change_impact(change: ChangeRequest) -> ImpactAnalysis:
    """Analyze impact of proposed changes"""

# GET /api/v1/dependencies/health
@router.get("/health")
async def get_system_health() -> SystemHealthStatus:
    """Get overall system dependency health"""
```

## Testing Strategy

### Unit Tests
- Dependency discovery accuracy validation
- Impact analysis algorithm testing
- Graph traversal functionality
- API endpoint response validation

### Integration Tests
- End-to-end dependency discovery
- Cross-service dependency verification
- Database connection testing
- Real-time health monitoring

### Performance Tests
- Large dependency graph handling
- Discovery process performance
- Visualization rendering speed
- Concurrent analysis requests

## Implementation Timeline

### Week 1: Foundation
- [ ] Create database schema and models
- [ ] Implement basic dependency discovery
- [ ] Set up core API endpoints
- [ ] Basic unit tests

### Week 2: Discovery Engine
- [ ] Code-based dependency analysis
- [ ] Runtime dependency tracing
- [ ] Service mapping implementation
- [ ] Discovery validation tests

### Week 3: Impact Analysis
- [ ] Impact analysis algorithms
- [ ] Risk scoring implementation
- [ ] Change impact templates
- [ ] Integration testing

### Week 4: Visualization & Documentation
- [ ] Dependency visualization API
- [ ] Documentation generation
- [ ] Performance optimization
- [ ] Comprehensive testing

## Security Considerations

### Data Protection
- Secure storage of dependency metadata
- Access control for sensitive dependency information
- Audit logging for dependency changes
- Encryption of connection strings

### Operational Security
- Rate limiting for discovery operations
- Authentication for administrative endpoints
- Monitoring for anomalous dependency patterns
- Secure handling of database credentials

## Risk Mitigation

### Technical Risks
- **Complex dependencies may be missed**: Use multiple discovery methods, manual validation
- **Performance impact**: Implement sampling, configurable intensity
- **False positives**: Validation mechanisms, confidence scoring

### Operational Risks
- **Service disruption**: Non-intrusive discovery, read-only operations
- **Data corruption**: Backup mechanisms, rollback procedures
- **Security exposure**: Minimal permissions, encrypted storage

## Success Metrics

### Functional Metrics
- Dependency discovery accuracy: >95%
- Change impact prediction accuracy: >90%
- System coverage: All critical dependencies mapped
- Response time: <2s for matrix queries

### Operational Metrics
- Reduced unplanned outages
- Faster change deployment cycles
- Improved rollback success rate
- Decreased dependency-related incidents

## Rollback Plan

### Implementation Rollback
1. Disable dependency discovery automation
2. Remove dependency tracking endpoints
3. Revert to manual dependency management
4. Restore original database schema

### Data Recovery
- Backup dependency data before major changes
- Version control for dependency configurations
- Export mechanisms for dependency matrices
- Recovery procedures for corrupted data

## Dependencies and Prerequisites

### Required Libraries
- `sqlparse`: SQL query parsing
- `ast`: Python AST analysis
- `networkx`: Graph algorithms
- `pydantic`: Data validation
- `asyncio`: Async operations

### Infrastructure Requirements
- Database schema migration capability
- Background task processing
- Real-time monitoring hooks
- Visualization framework integration

## Conclusion

This comprehensive dependency mapping and impact analysis system will provide ViolentUTF with the visibility and control needed to manage its complex database ecosystem safely and efficiently. The phased implementation approach ensures minimal disruption while delivering incremental value throughout the development process.
