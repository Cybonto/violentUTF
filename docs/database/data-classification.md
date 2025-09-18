# Data Classification Matrix - ViolentUTF Platform

## Executive Summary

**Document Version**: 1.0
**Last Updated**: 2025-09-18
**Classification Framework**: Enterprise Security Classification
**Compliance Standards**: GDPR, SOC 2 Type II, NIST Cybersecurity Framework
**Owner**: Security Team & Data Protection Officer
**Review Date**: 2025-12-18

This document establishes the comprehensive data classification matrix for the ViolentUTF platform, defining sensitivity levels, handling requirements, and compliance mappings for all data types across database systems and file storage.

## Classification Framework

### Sensitivity Levels

#### PUBLIC
- **Definition**: Information intended for public consumption with no restrictions
- **Impact of Disclosure**: No adverse impact to organization or individuals
- **Examples**: Public documentation, marketing materials, open-source code
- **Handling Requirements**: Standard IT controls, no special restrictions

#### INTERNAL
- **Definition**: Information intended for internal use within the organization
- **Impact of Disclosure**: Minor adverse impact, potential competitive disadvantage
- **Examples**: Internal procedures, system configurations, operational logs
- **Handling Requirements**: Access controls, employee-only access

#### CONFIDENTIAL
- **Definition**: Sensitive information requiring protection from unauthorized disclosure
- **Impact of Disclosure**: Significant adverse impact, regulatory violations possible
- **Examples**: Security testing results, user data, business intelligence
- **Handling Requirements**: Strict access controls, encryption, audit logging

#### RESTRICTED
- **Definition**: Highly sensitive information requiring maximum protection
- **Impact of Disclosure**: Severe adverse impact, legal/regulatory violations certain
- **Examples**: Credentials, private keys, financial data, personal identifiers
- **Handling Requirements**: Multi-factor authentication, encryption, segregated storage

### Compliance Mappings

#### GDPR (General Data Protection Regulation)
- **Personal Data**: Any information relating to identified or identifiable individuals
- **Special Categories**: Health data, biometric data, data concerning security
- **Processing Requirements**: Lawful basis, consent, data minimization
- **Retention Limits**: Purpose limitation, storage limitation principles

#### SOC 2 Type II (Service Organization Control 2)
- **Security**: Protection against unauthorized access
- **Availability**: System operation and accessibility
- **Processing Integrity**: System processing accuracy and completeness
- **Confidentiality**: Information designated as confidential protection
- **Privacy**: Personal information collection, use, retention, disclosure

#### NIST Cybersecurity Framework
- **Identify**: Asset management, data categorization, risk assessment
- **Protect**: Access control, data security, protective technology
- **Detect**: Anomaly detection, security monitoring, detection processes
- **Respond**: Response planning, incident response, analysis
- **Recover**: Recovery planning, improvements, communications

## Database Classification Matrix

### PostgreSQL Database (Keycloak SSO)

#### Core Authentication Data

| Data Element | Table | Classification | GDPR Category | Retention Period | Justification |
|--------------|-------|----------------|---------------|------------------|---------------|
| User IDs | user_entity | RESTRICTED | Personal Data | 2 years post-deletion | Unique identifiers |
| Email Addresses | user_entity | RESTRICTED | Personal Data | 2 years post-deletion | Contact information |
| Password Hashes | credential | RESTRICTED | Personal Data | 2 years post-deletion | Authentication data |
| Session Tokens | user_session | RESTRICTED | Personal Data | 30 days | Active session data |
| Login Events | event_entity | CONFIDENTIAL | Personal Data | 7 years | Audit requirements |
| Admin Actions | admin_event_entity | CONFIDENTIAL | Personal Data | 7 years | Compliance audit |
| Client Secrets | client | RESTRICTED | N/A | Permanent | Service authentication |
| Role Assignments | user_role_mapping | CONFIDENTIAL | Personal Data | 2 years post-deletion | Authorization data |

#### Session and Audit Data

| Data Element | Classification | Compliance Impact | Access Controls | Encryption Required |
|--------------|----------------|-------------------|-----------------|-------------------|
| Active Sessions | RESTRICTED | High | Multi-factor auth | Yes - in transit & rest |
| Failed Login Attempts | CONFIDENTIAL | Medium | Role-based access | Yes - in transit |
| Configuration Changes | CONFIDENTIAL | High | Admin-only access | Yes - audit trail |
| API Access Logs | CONFIDENTIAL | Medium | Security team access | Yes - log integrity |

### SQLite Database (FastAPI Application)

#### API Management Data

| Data Element | Table | Classification | Business Impact | Technical Controls |
|--------------|-------|----------------|-----------------|-------------------|
| API Key Hashes | api_keys | RESTRICTED | Critical | SHA-256 hashing, unique constraints |
| User Associations | api_keys | CONFIDENTIAL | High | User-based access control |
| Permission Sets | api_keys | CONFIDENTIAL | Medium | JSON validation, access logging |
| Usage Timestamps | api_keys | INTERNAL | Low | Automatic timestamping |

#### Orchestrator Configuration Data

| Data Element | Table | Classification | AI Security Impact | Protection Requirements |
|--------------|-------|----------------|-------------------|-------------------------|
| Orchestrator Parameters | orchestrator_configurations | CONFIDENTIAL | High | Parameter validation, access control |
| Target Model Configuration | orchestrator_configurations | CONFIDENTIAL | High | Secure configuration storage |
| PyRIT Identifiers | orchestrator_configurations | CONFIDENTIAL | Medium | Unique identifier protection |
| Execution Results | orchestrator_executions | CONFIDENTIAL | High | Result data encryption |
| Security Testing Data | orchestrator_executions | CONFIDENTIAL | Critical | Compartmentalized access |

#### Report System Data

| Data Element | Table | Classification | Business Value | Retention Requirements |
|--------------|-------|----------------|----------------|------------------------|
| Report Templates | report_templates | INTERNAL | Medium | Permanent (business assets) |
| Generated Reports | generated_reports | CONFIDENTIAL | High | 1 year operational |
| COB Analysis Results | cob_reports | CONFIDENTIAL | High | 2 years compliance |
| AI Analysis Data | cob_reports | CONFIDENTIAL | High | Secured AI result storage |

### DuckDB Files (PyRIT Memory - DEPRECATED)

#### Security Testing Conversation Data

| Data Type | Current Classification | Migration Impact | Protection During Migration |
|-----------|----------------------|------------------|---------------------------|
| Conversation Threads | CONFIDENTIAL | High risk data loss | Complete backup required |
| Attack Scenarios | CONFIDENTIAL | High business impact | Encrypted export required |
| Vulnerability Data | CONFIDENTIAL | Compliance impact | Audit trail required |
| Scoring Results | CONFIDENTIAL | Analytics impact | Data validation required |

## File-Based Storage Classification

### Configuration Files

#### Environment Files (.env)

| File Category | Examples | Classification | Risk Level | Protection Measures |
|---------------|----------|----------------|------------|-------------------|
| API Credentials | ai-tokens.env | RESTRICTED | Critical | 600 permissions, no VCS |
| Database Credentials | keycloak/.env | RESTRICTED | Critical | Container isolation |
| Service Secrets | apisix/.env | RESTRICTED | High | Secret management |
| Application Config | violentutf/.env | INTERNAL | Medium | Access controls |

#### YAML/JSON Configuration

| Configuration Type | Location | Classification | Change Control | Backup Requirements |
|-------------------|----------|----------------|----------------|-------------------|
| PyRIT Parameters | violentutf/parameters/ | INTERNAL | Git versioning | Regular backups |
| Service Configuration | apisix/conf/ | INTERNAL | Configuration management | Version control |
| Route Definitions | apisix/routes/ | INTERNAL | Change approval | Automated backup |

### Log Files

#### Application Logs

| Log Category | Classification | Compliance Requirement | Retention Period | Access Controls |
|--------------|----------------|------------------------|------------------|-----------------|
| Authentication Events | CONFIDENTIAL | SOC 2, GDPR | 7 years | Security team only |
| API Access Logs | CONFIDENTIAL | Audit requirements | 2 years | Admin access |
| Security Testing Logs | CONFIDENTIAL | Compliance audit | 7 years | Security analyst access |
| System Performance | INTERNAL | Operational | 90 days | Operations team |
| Error Logs | INTERNAL | Troubleshooting | 1 year | Development team |

#### Audit Logs

| Audit Category | Classification | Regulatory Requirement | Immutability | Monitoring |
|----------------|----------------|------------------------|--------------|------------|
| User Actions | CONFIDENTIAL | GDPR Article 30 | Required | Real-time |
| Data Access | CONFIDENTIAL | SOC 2 CC6.1 | Required | Automated alerts |
| Configuration Changes | CONFIDENTIAL | Change management | Required | Approval workflow |
| Security Events | CONFIDENTIAL | Incident response | Required | 24/7 monitoring |

### Cache and Temporary Storage

#### Application Cache

| Cache Type | Classification | Data Lifecycle | Cleanup Requirements | Security Controls |
|------------|----------------|----------------|---------------------|------------------|
| API Response Cache | INTERNAL | 24 hours | Automatic | Access isolation |
| Session Data | CONFIDENTIAL | Session lifetime | Logout cleanup | User isolation |
| Report Cache | CONFIDENTIAL | 7 days | Scheduled cleanup | Role-based access |
| File Upload Cache | INTERNAL | 24 hours | Automatic purge | Virus scanning |

### SSL Certificates and Keys

#### Certificate Classification

| Certificate Type | Classification | Critical Level | Rotation Period | Backup Requirements |
|------------------|----------------|----------------|-----------------|-------------------|
| Private Keys | RESTRICTED | Critical | Annual | Encrypted backup |
| Server Certificates | CONFIDENTIAL | High | Annual | Secure storage |
| CA Certificates | CONFIDENTIAL | High | 3 years | Multiple copies |
| Client Certificates | CONFIDENTIAL | Medium | 2 years | Access controlled |

## Data Handling Requirements by Classification

### RESTRICTED Data Handling

#### Access Controls
- **Multi-Factor Authentication**: Required for all access
- **Role-Based Access**: Minimum necessary principle
- **Session Management**: Automatic timeout, secure sessions
- **Audit Logging**: All access attempts logged

#### Technical Controls
- **Encryption at Rest**: AES-256 minimum
- **Encryption in Transit**: TLS 1.3 minimum
- **Key Management**: Hardware Security Modules (HSM) preferred
- **Backup Encryption**: Encrypted backups with separate key storage

#### Procedural Controls
- **Access Reviews**: Monthly access certification
- **Incident Response**: 15-minute response time
- **Data Breach Notification**: Immediate notification required
- **Destruction Procedures**: Cryptographic erasure required

### CONFIDENTIAL Data Handling

#### Access Controls
- **Authentication**: Strong authentication required
- **Authorization**: Business need basis
- **Network Controls**: VPN or equivalent required
- **Device Controls**: Managed devices only

#### Technical Controls
- **Encryption at Rest**: AES-128 minimum
- **Encryption in Transit**: TLS 1.2 minimum
- **Database Security**: Column-level encryption for sensitive fields
- **Log Protection**: Tamper-evident logging

#### Procedural Controls
- **Access Reviews**: Quarterly access certification
- **Training Requirements**: Annual security training
- **Incident Response**: 1-hour response time
- **Data Retention**: Automated retention policy enforcement

### INTERNAL Data Handling

#### Access Controls
- **Authentication**: Standard organizational authentication
- **Authorization**: Department-based access
- **Network Controls**: Corporate network access
- **Guest Access**: Prohibited for internal data

#### Technical Controls
- **Encryption in Transit**: TLS 1.2 for external communications
- **Access Logging**: Standard access logging
- **Backup Protection**: Standard backup procedures
- **Version Control**: Change tracking required

### PUBLIC Data Handling

#### Access Controls
- **No Special Restrictions**: Standard IT controls
- **Version Control**: Public repository acceptable
- **Distribution**: No distribution restrictions

#### Quality Controls
- **Content Review**: Editorial review process
- **Accuracy Verification**: Fact-checking required
- **Brand Compliance**: Marketing approval required

## Compliance Mapping Matrix

### GDPR Compliance Requirements

| Data Processing Activity | Legal Basis | Data Subject Rights | Technical Measures | Organizational Measures |
|-------------------------|-------------|-------------------|-------------------|----------------------|
| User Authentication | Legitimate Interest | Access, Rectification, Erasure | Encryption, Access Controls | Privacy Policy, Training |
| Security Testing | Legitimate Interest | Access, Portability | Pseudonymization | Data Protection Impact Assessment |
| Audit Logging | Legal Obligation | Access (limited) | Integrity Protection | Retention Policies |
| Performance Analytics | Legitimate Interest | Objection | Aggregation | Consent Management |

### SOC 2 Control Mapping

| Control Category | ViolentUTF Implementation | Data Classification Impact | Evidence Collection |
|------------------|---------------------------|---------------------------|-------------------|
| Access Controls (CC6.1) | JWT authentication, RBAC | All classifications | Access logs, user reviews |
| Logical Security (CC6.2) | Network segmentation | RESTRICTED/CONFIDENTIAL | Network monitoring |
| Data Protection (CC6.7) | Encryption, key management | RESTRICTED/CONFIDENTIAL | Encryption verification |
| Change Management (CC8.1) | Git versioning, approval workflow | All classifications | Change logs, approvals |

### Data Retention Schedule

#### Retention Periods by Classification

| Classification | Standard Retention | Compliance Extensions | Destruction Method |
|----------------|-------------------|----------------------|-------------------|
| RESTRICTED | Business need + 90 days | GDPR: Right to erasure | Cryptographic erasure |
| CONFIDENTIAL | 3 years | Audit: 7 years | Secure deletion |
| INTERNAL | 5 years | N/A | Standard deletion |
| PUBLIC | Permanent | N/A | N/A |

#### Specific Data Retention

| Data Type | Retention Period | Compliance Driver | Automated Cleanup |
|-----------|------------------|-------------------|------------------|
| User Authentication Data | 2 years post-deletion | GDPR | Yes |
| Security Testing Results | 7 years | Audit requirements | No |
| Access Logs | 7 years | SOC 2 | Yes |
| API Keys | 1 year post-revocation | Security best practice | Yes |
| Configuration History | Permanent | Business continuity | No |

## Risk Assessment by Classification

### Risk Matrix

| Classification | Confidentiality Risk | Integrity Risk | Availability Risk | Overall Risk Score |
|----------------|---------------------|----------------|-------------------|-------------------|
| RESTRICTED | Critical (9) | Critical (9) | High (7) | Critical (25) |
| CONFIDENTIAL | High (7) | High (7) | Medium (5) | High (19) |
| INTERNAL | Medium (5) | Medium (5) | Medium (5) | Medium (15) |
| PUBLIC | Low (1) | Medium (5) | Low (3) | Low (9) |

### Threat Assessment

#### RESTRICTED Data Threats
- **Insider Threats**: Privileged user misuse
- **External Attacks**: Targeted attacks on credentials
- **Data Breaches**: Unauthorized access or disclosure
- **Regulatory Violations**: Non-compliance penalties

#### CONFIDENTIAL Data Threats
- **Business Espionage**: Competitive intelligence gathering
- **Reputation Damage**: Unauthorized disclosure impact
- **Operational Disruption**: System compromise effects
- **Compliance Issues**: Audit finding consequences

## Implementation Guidelines

### Technical Implementation

#### Database Level Controls
```sql
-- Example: Row-level security for user data isolation
CREATE POLICY user_isolation_policy ON user_data
    FOR ALL TO application_role
    USING (user_id = current_setting('app.current_user_id'));

-- Example: Column encryption for sensitive data
CREATE TABLE sensitive_data (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    encrypted_data BYTEA,  -- AES-256 encrypted
    data_hash VARCHAR(64)  -- Integrity verification
);
```

#### Application Level Controls
```python
# Example: Data classification decorator
def classified_data(classification_level):
    """Decorator for data classification enforcement"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Verify user clearance level
            if not verify_clearance(get_current_user(), classification_level):
                raise PermissionError("Insufficient clearance level")

            # Log access attempt
            audit_log.info(f"Accessing {classification_level} data",
                          user=get_current_user(),
                          function=func.__name__)

            return func(*args, **kwargs)
        return wrapper
    return decorator

@classified_data("RESTRICTED")
def get_user_credentials(user_id):
    """Access RESTRICTED user credential data"""
    pass
```

### Operational Implementation

#### Access Control Procedures
1. **Classification Assignment**: Data owners assign classification levels
2. **Access Provisioning**: IT implements technical controls
3. **Regular Reviews**: Quarterly access certification
4. **Violation Response**: Incident response procedures

#### Training and Awareness
- **Initial Training**: New employee security orientation
- **Annual Refresher**: Updated classification guidelines
- **Role-Specific Training**: Specialized training for data handlers
- **Incident Training**: Response procedures for data breaches

### Monitoring and Compliance

#### Automated Monitoring
```python
# Example: Data classification monitoring
class DataClassificationMonitor:
    def __init__(self):
        self.violation_thresholds = {
            'RESTRICTED': 0,  # Zero tolerance for violations
            'CONFIDENTIAL': 5,  # 5 violations per month threshold
            'INTERNAL': 20,  # 20 violations per month threshold
        }

    def monitor_access_patterns(self):
        """Monitor data access for classification violations"""
        for classification in self.violation_thresholds:
            violations = self.detect_violations(classification)
            if violations > self.violation_thresholds[classification]:
                self.trigger_alert(classification, violations)
```

#### Compliance Reporting
- **Monthly Reports**: Classification compliance status
- **Quarterly Reviews**: Data inventory and classification updates
- **Annual Audit**: External compliance verification
- **Incident Reports**: Classification violation incidents

## Conclusion

The ViolentUTF data classification matrix provides a comprehensive framework for protecting data assets across all sensitivity levels. Implementation of these classification standards ensures compliance with regulatory requirements while maintaining operational efficiency and security.

Regular review and updates of this classification matrix ensure continued alignment with evolving business needs, regulatory requirements, and threat landscapes.

---

**Document Information**
- **Classification**: INTERNAL
- **Distribution**: Security Team, Data Protection Officer, Department Heads
- **Review Cycle**: Quarterly
- **Next Review**: 2025-12-18
- **Approval**: Chief Information Security Officer, Data Protection Officer
- **Related Documents**: Risk Assessment, Security Procedures, Compliance Framework
