# ADR-002: DuckDB Deprecation Strategy for User Data Storage

## Status
**Proposed** - Under evaluation for implementation in Q2 2025

## Context

ViolentUTF currently uses DuckDB for user-specific data storage, including:
- Generator configurations
- Dataset metadata and prompts
- Scorer configurations
- Converter settings
- User session data
- PyRIT memory storage (conversations, embeddings)

While DuckDB has served the platform well for analytics workloads, several factors are driving a reconsideration:

### Current Challenges with DuckDB
1. **Enterprise Integration**: Limited enterprise tooling and monitoring support
2. **Backup Complexity**: User-specific database files complicate backup strategies
3. **Scaling Limitations**: File-based approach limits horizontal scaling options
4. **Operational Overhead**: Multiple database files increase operational complexity
5. **Team Expertise**: Limited DuckDB expertise in enterprise environments
6. **Tool Ecosystem**: Fewer third-party tools for monitoring and management

### Platform Evolution Drivers
1. **Enterprise Adoption**: Growing enterprise customer base requires enterprise-grade data solutions
2. **Compliance Requirements**: Audit and compliance tools favor traditional RDBMS
3. **Scaling Demands**: Multi-tenant deployments require centralized data management
4. **Operational Simplification**: Reducing operational complexity for production deployments

### PyRIT Framework Considerations
The PyRIT framework has specific requirements:
- Conversation memory storage for multi-turn interactions
- Embedding storage for similarity matching
- High-performance read/write for conversation data
- Analytics queries for security analysis

## Decision

We will implement a **phased migration strategy** from DuckDB to PostgreSQL for user data storage, while maintaining PyRIT memory functionality through an abstraction layer.

### Phase 1: Database Abstraction Layer (Q1 2025)
Create database abstraction layer to support multiple backends:
```python
class UserDataManager(ABC):
    @abstractmethod
    async def create_generator(self, user_id: str, config: dict) -> str:
        pass

    @abstractmethod
    async def get_conversation_history(self, user_id: str, filters: dict) -> List[dict]:
        pass

class DuckDBUserDataManager(UserDataManager):
    # Current implementation

class PostgreSQLUserDataManager(UserDataManager):
    # New implementation
```

### Phase 2: Parallel Implementation (Q2 2025)
Implement PostgreSQL backend while maintaining DuckDB compatibility:
- PostgreSQL schema design optimized for user data patterns
- Migration utilities for existing DuckDB data
- A/B testing framework for performance comparison
- Feature parity validation

### Phase 3: Gradual Migration (Q3 2025)
Migrate users to PostgreSQL backend:
- Opt-in migration for willing users
- Performance monitoring and validation
- Rollback capability to DuckDB if needed
- Data validation and integrity checks

### Phase 4: DuckDB Deprecation (Q4 2025)
Complete migration and remove DuckDB dependency:
- Migrate remaining users
- Remove DuckDB code paths
- Update documentation and deployment guides
- Archive DuckDB backup data

## Implementation Details

### PostgreSQL Schema Design
```sql
-- User isolation through schema-based approach
CREATE SCHEMA user_{user_id_hash};

-- Generator configurations
CREATE TABLE user_{user_id_hash}.generators (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'ready',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation memory (PyRIT compatibility)
CREATE TABLE user_{user_id_hash}.conversations (
    id UUID PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    turn_number INTEGER NOT NULL,
    request_text TEXT,
    response_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings storage
CREATE TABLE user_{user_id_hash}.embeddings (
    id UUID PRIMARY KEY,
    conversation_id VARCHAR(255),
    embedding_type VARCHAR(100),
    embedding_vector VECTOR(1536), -- Using pgvector extension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Data Migration Strategy
```python
class DuckDBToPostgreSQLMigrator:
    async def migrate_user_data(self, user_id: str) -> MigrationResult:
        # 1. Create PostgreSQL user schema
        await self.create_user_schema(user_id)

        # 2. Migrate configuration data
        await self.migrate_generators(user_id)
        await self.migrate_datasets(user_id)
        await self.migrate_scorers(user_id)

        # 3. Migrate conversation data
        await self.migrate_conversations(user_id)
        await self.migrate_embeddings(user_id)

        # 4. Validate data integrity
        return await self.validate_migration(user_id)
```

### Performance Optimization
- **Indexing Strategy**: Optimized indexes for common query patterns
- **Partitioning**: Time-based partitioning for conversation data
- **Connection Pooling**: Efficient connection management
- **Query Optimization**: Specific optimization for analytics workloads

### PyRIT Integration
Maintain PyRIT compatibility through adapter pattern:
```python
class PostgreSQLPyRITMemory(MemoryInterface):
    def __init__(self, user_id: str, connection: AsyncSession):
        self.user_id = user_id
        self.connection = connection
        self.schema = f"user_{hash(user_id)}"

    async def add_conversation_turn(self, conversation: ConversationTurn):
        # Implementation using PostgreSQL
        pass
```

## Consequences

### Positive
- **Enterprise Readiness**: PostgreSQL is enterprise-standard with extensive tooling
- **Operational Simplification**: Single database technology for all persistent data
- **Scaling Capability**: Better support for horizontal scaling and replication
- **Backup Strategy**: Unified backup approach for all user data
- **Monitoring**: Comprehensive monitoring and alerting capabilities
- **Compliance**: Better audit trail and compliance tool support

### Negative
- **Migration Complexity**: Significant engineering effort for migration
- **Performance Risk**: Potential performance regression for analytics workloads
- **Data Loss Risk**: Migration process introduces data loss possibilities
- **Downtime Requirements**: Some downtime required for migration
- **Resource Requirements**: Higher memory and storage requirements for PostgreSQL

### Risk Mitigation Strategies

#### Risk: Performance Degradation
**Mitigation**:
- Comprehensive performance testing before migration
- PostgreSQL-specific optimizations (indexing, partitioning)
- Fallback to DuckDB if performance unacceptable
- Gradual migration with A/B testing

#### Risk: Data Loss During Migration
**Mitigation**:
- Comprehensive backup strategy before migration
- Data validation at each migration step
- Rollback procedures for failed migrations
- Parallel running of both systems during transition

#### Risk: PyRIT Compatibility Issues
**Mitigation**:
- Maintain PyRIT memory interface compatibility
- Extensive testing with PyRIT framework
- Direct collaboration with PyRIT maintainers
- Custom PyRIT memory provider if needed

#### Risk: Increased Infrastructure Costs
**Mitigation**:
- Right-sizing PostgreSQL deployment
- Efficient schema design to minimize storage
- Connection pooling to reduce resource usage
- Cost monitoring and optimization

## Alternatives Considered

### Continue with DuckDB
**Rejected**: While technically feasible, growing enterprise requirements and operational complexity make this unsustainable long-term.

### Hybrid Approach (DuckDB + PostgreSQL)
**Deferred**: Considered keeping DuckDB for analytics and PostgreSQL for configuration. Rejected due to increased complexity and minimal benefits.

### MongoDB Document Store
**Rejected**: PyRIT framework requirements heavily favor SQL-based approaches, and document model doesn't align with conversation data patterns.

### Cloud-Native Solutions (AWS RDS, Google Cloud SQL)
**Future Enhancement**: PostgreSQL migration enables future cloud deployment, but current focus is on-premises compatibility.

## Migration Timeline and Milestones

### Q1 2025: Foundation
- [ ] Complete database abstraction layer
- [ ] Implement PostgreSQL user data manager
- [ ] Create migration utilities and validation tools
- [ ] Performance benchmarking and optimization

### Q2 2025: Implementation
- [ ] Deploy PostgreSQL backend in production
- [ ] Implement A/B testing framework
- [ ] Migrate pilot users and validate functionality
- [ ] Performance monitoring and optimization

### Q3 2025: Migration
- [ ] Begin gradual user migration
- [ ] Monitor performance and stability
- [ ] Address issues and optimize as needed
- [ ] Migrate majority of active users

### Q4 2025: Completion
- [ ] Complete migration of all users
- [ ] Remove DuckDB dependencies from codebase
- [ ] Update documentation and deployment guides
- [ ] Archive DuckDB data and celebrate success

## Success Criteria

### Technical Success
- [ ] Zero data loss during migration
- [ ] Performance within 10% of DuckDB baseline
- [ ] 100% PyRIT functionality maintained
- [ ] All automated tests passing

### Operational Success
- [ ] Reduced backup complexity
- [ ] Improved monitoring and alerting
- [ ] Simplified deployment procedures
- [ ] Enhanced audit and compliance capabilities

### User Success
- [ ] No user-visible downtime during migration
- [ ] Maintained or improved application performance
- [ ] All user data and configurations preserved
- [ ] Positive user feedback on stability

## Rollback Strategy

### Immediate Rollback (Within Migration Window)
1. Stop PostgreSQL data writes
2. Restore from DuckDB backup
3. Revert application configuration
4. Validate DuckDB functionality

### Long-term Rollback (After Migration Complete)
1. Maintain DuckDB backup data for 90 days
2. Export PostgreSQL data to DuckDB format if needed
3. Revert codebase to DuckDB implementation
4. Restore user configurations and data

## Related Decisions
- [ADR-001: Database Technology Choices](001-database-technology-choices.md)
- [ADR-003: User Isolation Architecture](003-user-isolation-architecture.md) (Future)
- [ADR-005: PostgreSQL Optimization Strategy](005-postgresql-optimization-strategy.md) (Future)

## References
- [PostgreSQL Performance Documentation](https://www.postgresql.org/docs/current/performance-tips.html)
- [PyRIT Memory Interface](https://github.com/Azure/PyRIT/blob/main/pyrit/memory/)
- [pgvector Extension for Embeddings](https://github.com/pgvector/pgvector)
- [Database Migration Best Practices](https://martinfowler.com/articles/evodb.html)
