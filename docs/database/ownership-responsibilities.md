# Database Ownership and Responsibility Matrix

## Executive Summary

**Document Version**: 1.0
**Last Updated**: 2025-09-18
**Purpose**: Define ownership, responsibilities, and escalation procedures
**Scope**: All database systems and data storage components
**Authority**: Chief Information Officer, Database Management Committee
**Review Date**: 2025-12-18

This document establishes clear ownership, operational responsibilities, and escalation procedures for all database systems within the ViolentUTF platform. It defines accountability for 4 primary database systems, 7 file storage mechanisms, and associated operational processes across infrastructure, development, and security teams.

## Organizational Structure

### Database Management Committee
- **Chair**: Chief Information Officer (CIO)
- **Members**: Database Administrator, Security Officer, DevOps Lead, Backend Lead
- **Meeting Frequency**: Monthly, emergency as needed
- **Responsibilities**: Strategic decisions, policy approval, escalation resolution

### Primary Team Roles

#### Database Administration Team
- **Lead**: Senior Database Administrator
- **Team Size**: 2 FTE
- **Primary Responsibilities**: Database operations, performance, backup/recovery
- **On-Call Rotation**: 24/7 coverage for critical issues

#### Infrastructure Team
- **Lead**: Infrastructure Manager
- **Team Size**: 3 FTE
- **Primary Responsibilities**: Hardware, networking, container orchestration
- **On-Call Rotation**: 24/7 coverage for infrastructure issues

#### Backend Development Team
- **Lead**: Senior Backend Engineer
- **Team Size**: 4 FTE
- **Primary Responsibilities**: Application database integration, schema changes
- **On-Call Rotation**: Business hours, escalation for critical issues

#### DevOps Team
- **Lead**: DevOps Engineer
- **Team Size**: 2 FTE
- **Primary Responsibilities**: CI/CD, automation, configuration management
- **On-Call Rotation**: Business hours, escalation for deployment issues

#### Security Team
- **Lead**: Information Security Officer
- **Team Size**: 2 FTE
- **Primary Responsibilities**: Security monitoring, compliance, incident response
- **On-Call Rotation**: 24/7 coverage for security incidents

## Database System Ownership Matrix

### PostgreSQL Database (Keycloak SSO)

#### Primary Ownership
- **System Owner**: Infrastructure Team
- **Data Owner**: Security Team (authentication data)
- **Technical Owner**: Database Administration Team
- **Business Owner**: Platform Operations Manager

#### Responsibility Breakdown

| Responsibility Area | Primary Owner | Secondary Owner | Escalation Contact |
|-------------------|---------------|-----------------|-------------------|
| **Database Operations** | DB Admin Team | Infrastructure Team | DB Admin Lead |
| **Performance Tuning** | DB Admin Team | Backend Team | Infrastructure Manager |
| **Backup & Recovery** | DB Admin Team | Infrastructure Team | CIO |
| **Security Monitoring** | Security Team | DB Admin Team | Security Officer |
| **Access Management** | Security Team | DB Admin Team | Security Officer |
| **Schema Changes** | Backend Team | DB Admin Team | Backend Lead |
| **Capacity Planning** | Infrastructure Team | DB Admin Team | Infrastructure Manager |
| **Compliance Audit** | Security Team | DB Admin Team | Security Officer |

#### Operational Procedures

##### Daily Operations
- **Health Monitoring**: DB Admin Team (automated alerts)
- **Performance Review**: DB Admin Team (daily dashboard review)
- **Security Monitoring**: Security Team (real-time monitoring)
- **Backup Verification**: DB Admin Team (automated verification)

##### Weekly Operations
- **Performance Analysis**: DB Admin Team + Backend Team
- **Capacity Review**: Infrastructure Team + DB Admin Team
- **Security Review**: Security Team
- **Change Review**: DB Admin Team + Backend Team

##### Monthly Operations
- **Compliance Audit**: Security Team + DB Admin Team
- **Disaster Recovery Test**: DB Admin Team + Infrastructure Team
- **Performance Optimization**: DB Admin Team + Backend Team
- **Access Review**: Security Team

#### Contact Information
- **Primary On-Call**: db-admin@violentutf.local
- **Secondary On-Call**: infrastructure@violentutf.local
- **Security Escalation**: security@violentutf.local
- **Executive Escalation**: cio@violentutf.local

### SQLite Database (FastAPI Application)

#### Primary Ownership
- **System Owner**: Backend Development Team
- **Data Owner**: Backend Development Team
- **Technical Owner**: Backend Development Team
- **Business Owner**: Product Manager

#### Responsibility Breakdown

| Responsibility Area | Primary Owner | Secondary Owner | Escalation Contact |
|-------------------|---------------|-----------------|-------------------|
| **Application Integration** | Backend Team | DevOps Team | Backend Lead |
| **Schema Management** | Backend Team | DB Admin Team | Backend Lead |
| **Performance Optimization** | Backend Team | DB Admin Team | Backend Lead |
| **Backup Procedures** | DevOps Team | Backend Team | DevOps Lead |
| **Security Implementation** | Backend Team | Security Team | Security Officer |
| **Monitoring & Alerting** | DevOps Team | Backend Team | DevOps Lead |
| **Migration Management** | Backend Team | DB Admin Team | Backend Lead |
| **Code Quality** | Backend Team | Quality Assurance | Backend Lead |

#### Operational Procedures

##### Daily Operations
- **Application Monitoring**: DevOps Team (automated monitoring)
- **Error Tracking**: Backend Team (log analysis)
- **Performance Monitoring**: Backend Team (metrics review)
- **Backup Verification**: DevOps Team (automated checks)

##### Weekly Operations
- **Performance Review**: Backend Team
- **Code Review**: Backend Team + Quality Assurance
- **Security Scan**: Security Team + Backend Team
- **Capacity Planning**: Backend Team + Infrastructure Team

##### Monthly Operations
- **Schema Review**: Backend Team + DB Admin Team
- **Performance Optimization**: Backend Team
- **Security Assessment**: Security Team + Backend Team
- **Disaster Recovery Test**: Backend Team + DevOps Team

#### Contact Information
- **Primary On-Call**: backend@violentutf.local
- **Secondary On-Call**: devops@violentutf.local
- **Schema Changes**: backend-lead@violentutf.local
- **Executive Escalation**: product-manager@violentutf.local

### DuckDB Files (PyRIT Memory - DEPRECATED)

#### Migration Ownership
- **Migration Lead**: Backend Development Team
- **Migration Coordinator**: Database Administration Team
- **Data Validation**: Quality Assurance Team
- **Business Approval**: Product Manager

#### Responsibility Breakdown During Migration

| Phase | Primary Owner | Secondary Owner | Escalation Contact |
|-------|---------------|-----------------|-------------------|
| **Migration Planning** | Backend Team | DB Admin Team | Backend Lead |
| **Data Export** | Backend Team | QA Team | Backend Lead |
| **Data Validation** | QA Team | Backend Team | QA Lead |
| **System Cutover** | Backend Team | DevOps Team | Backend Lead |
| **Post-Migration Support** | Backend Team | DB Admin Team | Backend Lead |
| **Legacy Cleanup** | DevOps Team | Backend Team | DevOps Lead |

#### Migration Timeline Ownership
- **Week 1-2**: Backend Team (export procedures)
- **Week 3-4**: Backend Team + DB Admin Team (schema implementation)
- **Week 5-6**: Backend Team + QA Team (migration execution)
- **Week 7-8**: DevOps Team + Backend Team (cleanup)

#### Contact Information
- **Migration Lead**: migration-lead@violentutf.local
- **Migration Coordinator**: db-admin@violentutf.local
- **Business Stakeholder**: product-manager@violentutf.local
- **Executive Sponsor**: cio@violentutf.local

### File-Based Storage Systems

#### Primary Ownership
- **System Owner**: DevOps Team
- **Configuration Owner**: DevOps Team
- **Security Owner**: Security Team
- **Compliance Owner**: Security Team

#### Responsibility Breakdown by Storage Type

##### Environment Files (.env)
| Responsibility | Primary Owner | Secondary Owner | Approval Required |
|----------------|---------------|-----------------|-------------------|
| **Creation** | DevOps Team | Backend Team | Security Team |
| **Modification** | DevOps Team | Authorized Teams | Security Team |
| **Rotation** | Security Team | DevOps Team | Security Officer |
| **Audit** | Security Team | DevOps Team | Security Officer |

##### Configuration Files (YAML/JSON)
| Responsibility | Primary Owner | Secondary Owner | Approval Required |
|----------------|---------------|-----------------|-------------------|
| **Template Management** | DevOps Team | Backend Team | DevOps Lead |
| **Service Configuration** | Service Owner | DevOps Team | Service Lead |
| **Version Control** | DevOps Team | Development Teams | DevOps Lead |
| **Validation** | DevOps Team | Service Owner | DevOps Lead |

##### Log Files
| Responsibility | Primary Owner | Secondary Owner | Escalation Contact |
|----------------|---------------|-----------------|-------------------|
| **Collection** | DevOps Team | Infrastructure Team | DevOps Lead |
| **Retention** | Security Team | DevOps Team | Security Officer |
| **Analysis** | Security Team | Service Owners | Security Officer |
| **Archival** | DevOps Team | Infrastructure Team | DevOps Lead |

##### SSL Certificates
| Responsibility | Primary Owner | Secondary Owner | Approval Required |
|----------------|---------------|-----------------|-------------------|
| **Generation** | Security Team | Infrastructure Team | Security Officer |
| **Installation** | Infrastructure Team | DevOps Team | Infrastructure Manager |
| **Renewal** | Security Team | Infrastructure Team | Security Officer |
| **Revocation** | Security Team | Infrastructure Team | Security Officer |

## Escalation Procedures

### Escalation Matrix

#### Level 1: Service Team (0-15 minutes)
- **Scope**: Routine operations, known issues, standard procedures
- **Response Time**: 15 minutes during business hours, 30 minutes off-hours
- **Authority**: Service configuration changes, standard troubleshooting
- **Escalation Trigger**: Unable to resolve within SLA, unknown issue

#### Level 2: Team Lead (15-30 minutes)
- **Scope**: Complex technical issues, cross-service problems
- **Response Time**: 30 minutes
- **Authority**: Service restart, emergency configuration changes
- **Escalation Trigger**: Service impact, potential data loss, security concern

#### Level 3: Department Manager (30-60 minutes)
- **Scope**: Service outages, data integrity issues, security incidents
- **Response Time**: 60 minutes
- **Authority**: Resource allocation, emergency procedures, external vendor contact
- **Escalation Trigger**: Business impact, compliance violation, critical system failure

#### Level 4: Executive Team (60+ minutes)
- **Scope**: Business continuity threats, major security breaches, regulatory issues
- **Response Time**: 2 hours
- **Authority**: Executive decisions, regulatory notification, public communication
- **Escalation Trigger**: Platform-wide outage, data breach, regulatory violation

### Escalation Contact Methods

#### Primary Contacts
```
Level 1 (Service Teams):
- Database Admin: +1-XXX-XXX-XXXX (24/7)
- Backend Team: +1-XXX-XXX-XXXX (Business hours)
- DevOps Team: +1-XXX-XXX-XXXX (Business hours)
- Security Team: +1-XXX-XXX-XXXX (24/7)

Level 2 (Team Leads):
- DB Admin Lead: +1-XXX-XXX-XXXX
- Backend Lead: +1-XXX-XXX-XXXX
- DevOps Lead: +1-XXX-XXX-XXXX
- Security Officer: +1-XXX-XXX-XXXX

Level 3 (Managers):
- Infrastructure Manager: +1-XXX-XXX-XXXX
- Development Manager: +1-XXX-XXX-XXXX
- Security Manager: +1-XXX-XXX-XXXX

Level 4 (Executives):
- CIO: +1-XXX-XXX-XXXX
- CTO: +1-XXX-XXX-XXXX
- CISO: +1-XXX-XXX-XXXX
```

#### Communication Channels
- **Immediate**: Phone call + SMS
- **Urgent**: Slack alert + email
- **Standard**: Email + ticket system
- **Documentation**: Incident tracking system

## Change Management Procedures

### Change Categories

#### Standard Changes (Pre-approved)
- **Definition**: Low-risk, routine changes with established procedures
- **Examples**: Log rotation, standard backups, routine maintenance
- **Approval**: Automated approval through established procedures
- **Notification**: Service team + immediate supervisor

#### Normal Changes (CAB Approval)
- **Definition**: Medium-risk changes requiring Change Advisory Board approval
- **Examples**: Schema updates, configuration changes, software updates
- **Approval**: Change Advisory Board (CAB) review and approval
- **Notification**: Stakeholders + affected teams + management

#### Emergency Changes (Executive Approval)
- **Definition**: High-risk changes required for immediate business continuity
- **Examples**: Security patches, critical bug fixes, disaster recovery
- **Approval**: Executive sponsor + security officer approval
- **Notification**: All stakeholders + executive team + audit trail

### Change Request Process

#### 1. Change Initiation
- **Requestor**: Service owner or authorized personnel
- **Documentation**: Change request form with impact assessment
- **Review**: Team lead review for completeness and feasibility
- **Classification**: Determine change category and approval requirements

#### 2. Impact Assessment
- **Technical Impact**: Service owners assess technical implications
- **Business Impact**: Business stakeholders assess operational impact
- **Security Impact**: Security team reviews security implications
- **Compliance Impact**: Compliance team reviews regulatory implications

#### 3. Approval Process
- **Standard**: Automated approval with notification
- **Normal**: CAB review, stakeholder approval, implementation planning
- **Emergency**: Executive approval, immediate implementation, post-change review

#### 4. Implementation
- **Preparation**: Implementation team prepares environment
- **Execution**: Implementation according to approved plan
- **Verification**: Testing and validation of change implementation
- **Documentation**: Update of system documentation and procedures

#### 5. Post-Implementation Review
- **Validation**: Confirm change objectives met
- **Monitoring**: Enhanced monitoring during stabilization period
- **Documentation**: Update operational procedures
- **Lessons Learned**: Document issues and improvements for future changes

## Performance and Service Level Management

### Service Level Agreements (SLAs)

#### Database Availability SLAs
| Database System | Availability Target | Maximum Downtime/Month | Response Time |
|-----------------|-------------------|----------------------|---------------|
| PostgreSQL (Keycloak) | 99.9% | 43 minutes | 15 minutes |
| SQLite (FastAPI) | 99.5% | 3.6 hours | 30 minutes |
| File Storage | 99.8% | 1.4 hours | 30 minutes |

#### Performance SLAs
| Metric | Target | Measurement | Escalation Threshold |
|--------|--------|-------------|-------------------|
| Database Response Time | <100ms average | Real-time monitoring | >200ms for 5 minutes |
| Backup Success Rate | 99.9% | Daily verification | <99% for 1 week |
| Recovery Time Objective | <4 hours | Disaster recovery tests | >4 hours actual |
| Recovery Point Objective | <1 hour | Backup frequency | >1 hour data loss |

### Performance Monitoring Responsibilities

#### Real-Time Monitoring
- **Database Performance**: DB Admin Team (24/7 automated monitoring)
- **Application Performance**: Backend Team (business hours + alerts)
- **Infrastructure Performance**: Infrastructure Team (24/7 monitoring)
- **Security Monitoring**: Security Team (24/7 monitoring)

#### Regular Reporting
- **Daily**: Performance dashboard review (service teams)
- **Weekly**: Performance trend analysis (team leads)
- **Monthly**: SLA compliance report (managers)
- **Quarterly**: Capacity planning review (executive team)

## Training and Knowledge Management

### Training Requirements

#### New Team Members
- **Week 1**: ViolentUTF architecture overview, security training
- **Week 2**: Database systems deep dive, access provisioning
- **Week 3**: Operational procedures, escalation training
- **Week 4**: Hands-on training with mentorship

#### Ongoing Training
- **Monthly**: Security awareness updates
- **Quarterly**: Technology update training
- **Annual**: Comprehensive system review, disaster recovery drills
- **Ad-hoc**: New technology introduction, incident post-mortems

### Knowledge Management

#### Documentation Responsibilities
- **System Documentation**: Technical owners maintain architecture docs
- **Operational Procedures**: Operations teams maintain runbooks
- **Security Procedures**: Security team maintains security documentation
- **Change History**: DevOps team maintains change logs

#### Knowledge Sharing
- **Weekly Tech Talks**: Teams share knowledge across disciplines
- **Monthly Architecture Reviews**: System architecture updates
- **Quarterly All-Hands**: Company-wide technology updates
- **Annual Tech Summit**: External speakers, technology roadmap

## Audit and Compliance Responsibilities

### Internal Audit
- **Monthly**: Security team conducts access reviews
- **Quarterly**: Operations teams conduct procedure compliance audits
- **Annual**: Executive team sponsors comprehensive security audit

### External Audit
- **SOC 2**: Annual third-party audit coordinated by security team
- **Penetration Testing**: Bi-annual testing coordinated by security team
- **Compliance Assessment**: Ongoing compliance monitoring by security team

### Audit Responsibilities
| Audit Type | Coordinator | Participants | Reporting |
|------------|-------------|--------------|-----------|
| Access Review | Security Team | All service owners | Security Officer |
| Change Management | DevOps Team | All technical teams | DevOps Lead |
| Data Classification | Security Team | Data owners | Security Officer |
| Disaster Recovery | DB Admin Team | All operational teams | Infrastructure Manager |

## Conclusion

This ownership and responsibility matrix establishes clear accountability for all database systems and operational processes within ViolentUTF. Regular review and updates ensure alignment with organizational changes and evolving system requirements.

Success depends on clear communication, proper training, and commitment to established procedures. Regular audits and assessments validate the effectiveness of the ownership model and identify areas for improvement.

---

**Document Information**
- **Classification**: INTERNAL
- **Distribution**: All Team Leads, Managers, Executive Team
- **Review Cycle**: Quarterly
- **Next Review**: 2025-12-18
- **Approval**: Chief Information Officer, Database Management Committee
- **Related Documents**: Database Inventory, Risk Assessment, Operational Procedures
