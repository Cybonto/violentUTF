# ADR-004: Change Management Framework

## Status
**Accepted** - Operational since 2025-10-11

## Context

As ViolentUTF's database infrastructure has matured with multiple data stores (PostgreSQL for Keycloak, SQLite for API and PyRIT memory), the need for structured change management has become critical. The absence of formal change procedures has led to:

- Untracked database schema changes
- Insufficient risk assessment before changes
- Lack of approval workflows
- No standardized rollback procedures
- Difficulty coordinating changes across multiple databases

### Problem Statement

How do we implement a change management framework that balances development velocity with operational safety, provides appropriate oversight based on risk, and maintains auditability of all database changes?

### Requirements

- Risk-based change classification (emergency, standard, normal, major)
- Automated approval routing based on change type and risk
- Pre-change validation and dependency analysis
- Maintenance window coordination
- Change tracking and audit trail
- Integration with existing CI/CD workflows

### Constraints

- Must not significantly slow down development velocity
- Must work with existing Docker Compose infrastructure
- Must integrate with current Keycloak, APISIX, and FastAPI stack
- Must support both PostgreSQL and SQLite databases
- Must be compatible with PyRIT v0.10.0rc0 (SQLite-based memory)

## Decision

Implement a comprehensive change management framework with four-tier classification system and risk-based approval workflows.

### Solution Overview

1. **Change Classification System**:
   - **Emergency**: Immediate execution, post-review required
   - **Standard**: Pre-approved procedures, automated execution
   - **Normal**: Single approver, standard workflow
   - **Major**: Multiple approvers, ADR required, extended testing

2. **Approval Workflow**:
   - Automated routing to appropriate stakeholders based on risk/impact
   - Configurable approval matrix in `workflows/change-approval/approval_matrix.yml`
   - Stakeholder registry with notification preferences
   - Maintenance window coordination

3. **Pre-Change Validation**:
   - Schema validation for database changes
   - Configuration syntax checking
   - Dependency conflict detection
   - Disk space and resource verification

4. **Change Tracking**:
   - Unique change request IDs (CR-YYYY-NNN format)
   - Full audit trail in Git and change log database
   - Integration with GitHub Issues/PRs
   - ADR creation for architectural changes

### Implementation Details

```python
# scripts/change-management/core/change_classifier.py
class ChangeType(Enum):
    EMERGENCY = "emergency"  # Production incidents
    STANDARD = "standard"    # Pre-approved tasks
    NORMAL = "normal"        # Regular changes
    MAJOR = "major"          # Architecture impact

# Approval requirements by change type
APPROVAL_MATRIX = {
    "emergency": {
        "approvers_required": 0,
        "post_review": True,
        "notification": ["oncall", "dba_team"]
    },
    "normal": {
        "approvers_required": 1,
        "approver_roles": ["dba", "tech_lead"],
        "notification": ["dba_team", "submitter"]
    },
    "major": {
        "approvers_required": 2,
        "approver_roles": ["dba", "tech_lead", "architect"],
        "additional_requirements": ["adr", "testing_plan"]
    }
}
```

### CLI Interface

```bash
# Submit change request
python3 scripts/change-management/change_cli.py request create \
  --type normal \
  --title "Add user preferences table" \
  --database postgresql \
  --risk medium

# Execute approved change
python3 scripts/change-management/change_cli.py execute CR-2025-001 \
  --snapshot \
  --validate
```

## Consequences

### Positive

- **Improved Safety**: Risk assessment and approval reduce chance of errors
- **Better Tracking**: Full audit trail of all database changes
- **Faster Recovery**: Automated rollback procedures
- **Compliance**: Meets audit requirements for change management
- **Coordination**: Prevents conflicting changes and coordinates maintenance windows
- **Knowledge Transfer**: ADRs document major decisions

### Negative

- **Additional Overhead**: Extra steps for submitting and approving changes
- **Process Complexity**: Team must learn new procedures
- **Potential Delays**: Approval process may slow urgent changes
- **Maintenance Burden**: System requires ongoing configuration updates

### Risks and Mitigations

#### Risk: Change process becomes bottleneck
**Mitigation**:
- Streamlined approval for low-risk changes
- Pre-approved standard procedures
- Emergency fast-track for critical fixes
- Regular review of process efficiency

#### Risk: Developers bypass process
**Mitigation**:
- Training and documentation
- CI/CD enforcement of change validation
- Automated detection of unapproved changes
- Clear emergency procedures

#### Risk: Approval matrix becomes outdated
**Mitigation**:
- Quarterly review of approval requirements
- Feedback collection from team
- Metrics tracking approval delays
- Automated stakeholder validation

## Alternatives Considered

### Alternative 1: No Formal Process
**Description**: Continue with informal change management
**Rejected because**:
- Insufficient for production system
- No audit trail
- High risk of errors
- Doesn't scale with team growth

### Alternative 2: Heavyweight ITIL Process
**Description**: Implement full ITIL change management
**Rejected because**:
- Too much overhead for team size
- Reduces development velocity significantly
- Overkill for current scale
- Tool licensing costs

### Alternative 3: GitHub-Only Process
**Description**: Use only GitHub Issues and PRs for change management
**Rejected because**:
- Insufficient structure for database changes
- No risk assessment automation
- Limited approval workflow capabilities
- Poor integration with operations

## Implementation Plan

### Phase 1: Core Framework (Week 1)
- [x] Change classification system
- [x] Approval workflow implementation
- [x] Pre-change validation
- [x] Change tracking database

### Phase 2: Integration (Week 2)
- [x] CLI interface
- [x] GitHub Actions integration
- [x] Notification system
- [x] Documentation and training

## Success Criteria

- [x] Change classification automated
- [x] Approval workflows operational
- [x] Pre-change validation prevents errors
- [x] All database changes tracked with CR IDs
- [x] Team trained and process documented
- [x] Integration with CI/CD complete

## Rollback Strategy

If change management framework proves problematic:

1. Disable automated enforcement (manual process)
2. Simplify approval matrix (reduce required approvers)
3. Create more pre-approved standard procedures
4. Provide emergency bypass mechanism with audit
5. Return to GitHub-only for non-critical changes

## Related Decisions

- [ADR-001: Database Technology Choices](001-database-technology-choices.md)
- [ADR-002: DuckDB Deprecation Strategy](002-duckdb-deprecation-strategy.md)
- [ADR-003: SQLite Alignment Strategy](003-sqlite-alignment-strategy.md)
- [ADR-005: Automated Rollback Strategy](005-automated-rollback-strategy.md)
- [ADR-006: Incident Response Procedures](006-incident-response-procedures.md)

## References

- [Change Management Best Practices - ITIL Foundation](https://www.axelos.com/certifications/itil-service-management)
- [Database Change Management - Liquibase](https://www.liquibase.org/get-started/best-practices)
- [Generalized Database Audit Plan](../plans/generalized-database-audit-plan.md)
- Issue #274: Phase 7 Change Management Implementation

---

**Author**: Backend-Engineer_vSEP25
**Date**: 2025-10-11
**Last Updated**: 2025-10-11
**Review Date**: 2026-01-11 (Quarterly review)
