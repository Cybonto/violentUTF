# ADR-001: Database Technology Choices for ViolentUTF

## Status
**Accepted** - Implementation complete and in production

## Context

ViolentUTF requires a database architecture that supports:
- Multi-user AI security testing operations
- High-volume conversation and test data storage
- Identity and access management integration
- Analytics workloads for security analysis
- User isolation for security and privacy
- Integration with PyRIT framework requirements
- Scalability for enterprise deployments

The system needs to handle different types of data with varying requirements:
1. **Identity Data**: User accounts, roles, permissions (ACID compliance required)
2. **Application Data**: API keys, sessions, audit logs (moderate consistency requirements)
3. **User Configuration Data**: Generators, scorers, datasets (user-specific, analytics-friendly)
4. **Conversation Data**: PyRIT memory, prompt/response pairs (append-heavy, analytics workloads)
5. **Static Data**: Configuration files, datasets, reports (file-based storage)

## Decision

We will implement a **multi-database architecture** using specialized database technologies for different data types:

### 1. PostgreSQL for Identity Management
- **Purpose**: Keycloak SSO identity and access management
- **Rationale**:
  - ACID compliance for critical identity operations
  - Mature ecosystem with excellent Keycloak integration
  - Strong consistency guarantees for user permissions
  - Enterprise-grade security features
  - Proven scalability for identity workloads

### 2. SQLite for Application Data
- **Purpose**: FastAPI backend application state and shared data
- **Rationale**:
  - Lightweight deployment with zero configuration
  - ACID compliance for critical application operations
  - Single-file portability for simplified deployment
  - Excellent performance for moderate workloads
  - No additional infrastructure requirements

### 3. DuckDB for User-Specific Data and Analytics
- **Purpose**: User configurations and PyRIT memory storage
- **Rationale**:
  - Column-oriented storage optimized for analytics workloads
  - Excellent performance for large-scale data analysis
  - User isolation through separate database files
  - Direct integration with PyRIT framework requirements
  - In-process deployment eliminates network overhead
  - Strong SQL support for complex queries

### 4. File System for Static Content
- **Purpose**: Configuration files, datasets, templates, and reports
- **Rationale**:
  - Direct access patterns for configuration management
  - Version control integration for configuration files
  - Simple backup and deployment for static assets
  - MCP resource interface compatibility
  - Operating system-level security and permissions

## Implementation Details

### Database Isolation Strategy
```python
# User-specific DuckDB databases
salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
hashed_username = hashlib.sha256(salt.encode() + username.encode()).hexdigest()
db_path = f"./app_data/violentutf/pyrit_memory_{hashed_username}.db"
```

### Connection Management
- **PostgreSQL**: Keycloak manages connections via HikariCP
- **SQLite**: SQLAlchemy async sessions with connection pooling
- **DuckDB**: Direct Python API with per-user connections
- **File System**: Direct I/O with proper access controls

### Data Consistency Strategy
- **Strong Consistency**: PostgreSQL for identity, SQLite for critical app data
- **Eventual Consistency**: DuckDB for analytics data, acceptable for user configurations
- **File Consistency**: Operating system guarantees for static content

## Consequences

### Positive
- **Performance**: Each database optimized for its specific workload
- **Security**: Strong user isolation and access control
- **Scalability**: Can scale each component independently
- **Flexibility**: Easy to optimize or replace individual components
- **Integration**: Excellent PyRIT framework compatibility
- **Deployment**: Simplified deployment with minimal infrastructure

### Negative
- **Complexity**: Multiple database technologies to manage and monitor
- **Consistency**: Cross-database transactions require careful design
- **Expertise**: Team needs knowledge of multiple database systems
- **Backup**: Multiple backup strategies required
- **Migration**: Data migration between systems can be complex

### Risks and Mitigations

#### Risk: Cross-Database Transaction Complexity
**Mitigation**:
- Implement compensating transaction patterns
- Use application-level consistency where possible
- Audit logging for all cross-database operations

#### Risk: DuckDB Maturity Concerns
**Mitigation**:
- Monitor DuckDB ecosystem development
- Implement migration path to PostgreSQL if needed
- Regular performance and stability testing

#### Risk: Multiple Technology Maintenance
**Mitigation**:
- Comprehensive documentation and runbooks
- Automated backup and monitoring for all databases
- Container-based deployment for consistency

## Alternatives Considered

### Single PostgreSQL Database
**Rejected**: While simpler, PostgreSQL is not optimized for the analytics workloads that dominate user data operations. Performance testing showed 3-5x slower query times for large conversation datasets.

### MongoDB Document Store
**Rejected**: Lack of strong consistency guarantees for identity data, and PyRIT framework has SQL-based requirements that would require significant re-engineering.

### Full Cloud Database Services (RDS, Cloud SQL)
**Deferred**: Chosen architecture supports future cloud migration, but current focus is on-premises and hybrid deployments.

### Redis for Session Management
**Future Enhancement**: Redis caching layer planned for Phase 2 to improve performance, but not critical for initial deployment.

## Compliance and Security Considerations

### Data Protection
- User data isolation prevents cross-user data access
- Hash-based database naming prevents enumeration attacks
- Application-level access controls for all database operations

### Audit Requirements
- All database operations logged in SQLite audit tables
- Cross-database transaction tracking
- Performance metrics collection for optimization

### Backup and Recovery
- Tier-based backup strategy based on data criticality
- Database-specific recovery procedures
- Regular backup testing and validation

## Performance Benchmarks

Initial performance testing results:
- **PostgreSQL**: 1000+ authentication operations/second
- **SQLite**: 500+ API operations/second with WAL mode
- **DuckDB**: 10,000+ analytical queries/second on conversation data
- **File System**: Direct I/O for configuration and dataset access

## Migration Strategy

### Future Migration Paths
1. **DuckDB to PostgreSQL**: Planned evaluation for enterprise scalability
2. **SQLite to PostgreSQL**: Available for high-traffic deployments
3. **Cloud Migration**: Architecture supports cloud database services
4. **Sharding Strategy**: Horizontal scaling approach for large deployments

### Version Compatibility
- Schema versioning for all databases
- Migration scripts for schema evolution
- Backward compatibility requirements

## Related Decisions
- [ADR-002: DuckDB Deprecation Strategy](002-duckdb-deprecation-strategy.md)
- [ADR-003: User Isolation Architecture](003-user-isolation-architecture.md) (Future)
- [ADR-004: Caching Strategy](004-caching-strategy.md) (Future)

## References
- [PyRIT Framework Database Requirements](https://github.com/Azure/PyRIT)
- [Keycloak Database Configuration](https://www.keycloak.org/docs/latest/server_installation/)
- [DuckDB Analytics Performance](https://duckdb.org/docs/guides/performance)
- [ViolentUTF Database Architecture Overview](../database/architecture-overview.md)
