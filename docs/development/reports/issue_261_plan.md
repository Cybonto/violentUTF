# Issue #261 Implementation Plan: System Architecture Discovery and Documentation

## Executive Summary

This task involves conducting comprehensive system architecture discovery and creating detailed documentation for ViolentUTF's database infrastructure. The goal is to establish a complete understanding of the current architecture and create maintainable documentation that will serve as the foundation for the database audit initiative.

## Project Overview

### Objective
Create comprehensive architectural documentation including C4 model diagrams, data flow maps, and component interaction documentation for ViolentUTF's enterprise AI red-teaming platform.

### Scope
- ViolentUTF Streamlit application
- FastAPI backend service
- Keycloak SSO authentication
- APISIX API Gateway
- PyRIT integration components
- Database systems (PostgreSQL, SQLite, DuckDB)
- Model Context Protocol (MCP) integration

### Key Deliverables
1. Complete C4 architectural diagrams (System, Container, Component, Code levels)
2. Data flow documentation covering all database interactions
3. Component interaction maps including all services and dependencies
4. Updated ADR documentation with database architectural decisions
5. Automated documentation generation setup
6. Version-controlled, maintainable documentation

## Technical Architecture Analysis

### Current Database Components Identified
1. **PostgreSQL** - Keycloak identity management
2. **SQLite** - FastAPI application database
3. **DuckDB** - PyRIT memory storage (being deprecated)
4. **File-based storage** - Configuration, logs, cache files

### Service Architecture Overview
```
User → Streamlit (8501) → APISIX (9080) → FastAPI (8000)
                     ↓
               Keycloak (8080) ← PostgreSQL
                     ↓
              JWT Authentication
                     ↓
            MCP Server (/mcp/sse) → PyRIT → DuckDB
```

## Implementation Phases

### Phase 1: Discovery and Analysis (Current Phase)

#### 1.1 Documentation Survey
- [ ] Review existing docs/ directory structure
- [ ] Analyze all README files across components
- [ ] Check for existing ADRs in the repository
- [ ] Examine Docker compose configurations
- [ ] Review setup scripts (setup_macos_new.sh, etc.)

#### 1.2 Codebase Architecture Analysis
- [ ] Map violentutf_api/fastapi_app/ structure and database connections
- [ ] Analyze Streamlit app architecture in violentutf/ directory
- [ ] Document PyRIT integration patterns and data flows
- [ ] Map APISIX gateway routing and database access patterns
- [ ] Identify authentication and authorization flows

#### 1.3 Service Interaction Mapping
- [ ] Trace complete authentication flow: Streamlit → Keycloak → FastAPI
- [ ] Document API data flow: Streamlit → APISIX → FastAPI → SQLite
- [ ] Map PyRIT orchestrator interactions with database systems
- [ ] Identify file-based storage patterns and configurations
- [ ] Document MCP server integration points

### Phase 2: Diagram Creation

#### 2.1 C4 Model Implementation
- [ ] **System Context Diagram** - ViolentUTF ecosystem overview
- [ ] **Container Diagram** - Services, data stores, and external systems
- [ ] **Component Diagram** - Internal structure of each major service
- [ ] **Code Diagram** - Critical database interaction points

#### 2.2 Data Flow Diagrams
- [ ] Authentication and authorization flows
- [ ] Application data CRUD operations
- [ ] PyRIT memory storage patterns
- [ ] Configuration and logging data flows
- [ ] MCP tool invocation and data handling

#### 2.3 Automated Documentation Setup
- [ ] PlantUML integration for diagram generation
- [ ] Swagger/OpenAPI documentation generation
- [ ] Dependency graph generation
- [ ] CI/CD integration for automated updates

### Phase 3: Documentation Creation

#### 3.1 Architecture Documentation
- [ ] Comprehensive architecture overview document
- [ ] Database technology choices and rationale
- [ ] Performance and scalability considerations
- [ ] Security architecture documentation
- [ ] Deployment and operational considerations

#### 3.2 ADR Management
- [ ] Review existing ADRs for database-related decisions
- [ ] Create new ADRs for undocumented architectural choices
- [ ] Document DuckDB deprecation decision and migration rationale
- [ ] Include security and compliance architectural decisions
- [ ] Create ADR template for future database decisions

### Phase 4: Validation and Maintenance

#### 4.1 Technical Review
- [ ] Team review of architectural documentation
- [ ] Validation of diagrams against actual implementation
- [ ] Cross-reference with deployment configurations
- [ ] Ensure completeness and accuracy

#### 4.2 Documentation Maintenance Setup
- [ ] Version control all documentation assets
- [ ] Establish documentation update procedures
- [ ] Create templates for future architectural documentation
- [ ] Set up automated documentation generation workflows

## Testing Strategy

### Documentation Validation
1. **Accuracy Testing**
   - Cross-reference diagrams with actual code implementation
   - Validate service endpoints and database connections
   - Verify authentication flows match implementation

2. **Completeness Review**
   - Ensure all database components are documented
   - Verify all service interactions are captured
   - Check coverage of all API endpoints

3. **Stakeholder Validation**
   - Review with development team for accuracy
   - Validate against operational knowledge
   - Confirm architectural assumptions

### Tool Validation
1. **PlantUML Rendering**
   - Verify all diagrams render correctly
   - Test diagram updates and regeneration
   - Validate export formats (PNG, SVG, PDF)

2. **Link Validation**
   - Check all internal documentation links
   - Verify external references
   - Test navigation between documents

3. **Automation Testing**
   - Validate automated documentation generation
   - Test CI/CD integration
   - Verify update triggers and workflows

## Risk Management

### Identified Risks and Mitigations

1. **Risk**: Incomplete or inaccurate existing documentation
   - **Mitigation**: Cross-reference multiple sources (code, configs, team knowledge)
   - **Action**: Validate findings with development team

2. **Risk**: Complex architecture difficult to document comprehensively
   - **Mitigation**: Break down into phases, use standard frameworks (C4)
   - **Action**: Collaborate with team members familiar with specific components

3. **Risk**: Documentation becomes outdated quickly
   - **Mitigation**: Integrate updates into development workflow
   - **Action**: Use automated generation, establish regular review cycles

4. **Risk**: Tool dependencies for automated documentation
   - **Mitigation**: Choose widely-supported tools, provide manual alternatives
   - **Action**: Ensure documentation can be maintained without specialized tools

## Success Criteria

### Quality Gates
1. **Completeness**: All database components and interactions documented
2. **Accuracy**: Documentation validated against actual implementation
3. **Maintainability**: Clear update procedures and automation in place
4. **Usability**: Documentation accessible and navigable for development team
5. **Standards Compliance**: Follows established documentation standards and ADR format

### Acceptance Criteria
- [ ] Complete C4 architectural diagrams created and validated
- [ ] Data flow documentation covers all database interactions
- [ ] Component interaction maps include all services and dependencies
- [ ] ADR documentation updated with database architectural decisions
- [ ] Documentation reviewed and approved by development team
- [ ] All diagrams are maintainable and version-controlled

## File Structure

```
docs/
├── architecture/
│   ├── c4-model/
│   │   ├── system-context.puml
│   │   ├── container-diagram.puml
│   │   ├── component-diagrams/
│   │   └── code-diagrams/
│   ├── data-flows/
│   │   ├── authentication-flow.puml
│   │   ├── api-data-flow.puml
│   │   └── pyrit-integration.puml
│   └── overview.md
├── database/
│   ├── architecture-overview.md
│   ├── component-interactions.md
│   └── migration-strategy.md
├── adr/
│   ├── 001-database-technology-choices.md
│   ├── 002-duckdb-deprecation-strategy.md
│   └── template.md
└── development/
    └── issue_261/
        ├── issue_261_plan.md (this file)
        ├── testresults.md
        └── ISSUE_261_development_report.md
```

## Timeline and Dependencies

### Dependencies
- Access to all ViolentUTF services and configuration files
- Development team availability for validation and review
- Tool installation and setup (PlantUML, documentation generators)

### Estimated Timeline
- **Phase 1**: 2-3 days (Discovery and Analysis)
- **Phase 2**: 2-3 days (Diagram Creation)
- **Phase 3**: 2-3 days (Documentation Creation)
- **Phase 4**: 1-2 days (Validation and Maintenance Setup)

**Total Estimated Duration**: 7-11 days

## Conclusion

This comprehensive architecture discovery and documentation initiative will establish a solid foundation for the ViolentUTF database audit. The resulting documentation will be maintainable, version-controlled, and serve as an authoritative reference for the system's architecture and database infrastructure.

The implementation follows Test-Driven Development principles by first establishing clear requirements, validation criteria, and testing strategies before proceeding with implementation. This ensures the documentation will meet all stakeholder needs and maintain accuracy over time.
