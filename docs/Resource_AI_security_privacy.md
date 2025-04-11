# Resource for AI Security and Privacy

## Forewords
This document serves as a resource guide for addressing security and privacy concerns in artificial intelligence systems. It outlines frameworks, controls, and best practices to help organizations implement robust AI security measures and privacy protections.

### Goals
To provide a structured, research-based approach for organizations to assess, implement, and maintain security and privacy safeguards specific to AI systems, ensuring compliance with regulatory requirements while protecting sensitive data and models.

### Contributions
This resource represents collaborative input from security professionals, AI experts, and privacy advocates to create a holistic framework addressing the unique challenges of securing AI systems and protecting data privacy.

## Security
### S1\. Compliance
This section outlines and provides resources related to the regulatory frameworks, certifications, and compliance requirements applicable to AI systems across various industries and jurisdictions.

#### General Items
- **Model Card**
- **System Card**
- **Addendum Process**
- SIG Lite questionaires
- CAIQ Lite questionaires
- VSA Core questionaires

#### SOC 2 Type 1
Point-in-time assessment of an organization's system and suitability of control design related to security, availability, processing integrity, confidentiality, and privacy.

#### SOC 2 Type 2
Comprehensive assessment of control effectiveness over an extended period (typically 6-12 months), providing higher assurance levels than Type 1.
- **SOC 2 Type 2 Report**
  - 
- **CSA STAR Report**
  - 
#### ISO 27001:2022
International standard for information security management systems (ISMS), with specific considerations for AI systems.
- **Statement of Applicability**
  - 
- **ISO 27001 Certificate**
  - 
#### ISO/IEC 42001:2023
The recently established international standard specifically addressing AI management systems and governance frameworks.

#### Domain-specific Compliance: Finance

#### Domain-specific Compliance: Healthcare
##### HIPAA
Requirements specific to healthcare AI applications, focusing on protecting personal health information (PHI) in accordance with Health Insurance Portability and Accountability Act standards.
- **Annual HIPAA SCA Report**

#### Domain-specific Compliance: Critical Infrastructure

#### Domain-specific Compliance: Defense


### S2\. Controls
Technical and organizational controls that provide the foundation for securing AI systems throughout their lifecycle.

#### S2\.a Infrastructure Diagrams
Visual representations of the AI system architecture, data flows, and security controls to support risk assessment and security planning.

#### S2\.b Infrastructure Security
Technical controls securing the underlying infrastructure supporting AI systems, including compute, storage, networking, and access management.
- **Encryption key access**
  - The organization restricts privileged access to encryption keys to authorized users with a business need.
- **Authentication**
  - The organization requires authentication to systems and applications to use unique username and password or authorized Secure Socket Shell (SSH) keys.
- **Application access**
  - System access restricted to authorized access only
- **Production DB access**
  - The organization restricts privileged access to databases to authorized users with a business need.
- **Firewall access**
  - The organization restricts privileged access to the firewall to authorized users with a business need.
- **Production OS access**
  - The organization restricts privileged access to the operating system to authorized users with a business need.
- **Production network access**
  - The organization restricts privileged access to the production network to authorized users with a business need.
  - The organization requires authentication to the "production network" to use unique usernames and passwords or authorized Secure Socket Shell (SSH) keys.
- **Remote access**
  - The organization's production systems can only be remotely accessed by authorized employees via an approved encrypted connection.
- **Infrastructure performance monitoring**
  - An infrastructure monitoring tool is utilized to monitor systems, infrastructure, and performance and generates alerts when specific predefined thresholds are met.
- **Network Firewall**
  - The organization uses firewalls and configures them to prevent unauthorized access.
- **Network and System Hardening**
  - The organization's network and system hardening standards are documented, based on industry best practices, and reviewed at least annually.

#### S2\.c Organizational Security
Administrative and procedural controls that establish security governance throughout the organization developing or operating AI systems.
- **Asset disposal procedures**
  - The organization has electronic media containing confidential information purged or destroyed in accordance with best practices, and certificates of destruction are issued for each device destroyed.

- **Production inventory**
  - The organization maintains a formal inventory of production system assets.

- **Portable media**
  - The organization encrypts portable and removable media devices when used.

- **Anti-malware technology**
  - The organization deploys anti-malware technology to environments commonly susceptible to malicious attacks and configures this to be updated routinely, logged, and installed on all relevant systems.

- **Code of Conduct**
  - The organization requires employees to acknowledge a code of conduct at the time of hire. Employees who violate the code of conduct are subject to disciplinary actions in accordance with a disciplinary policy.

- **Password policy**
  - The organization requires passwords for in-scope system components to be configured according to the organization's policy.

- **MDM system**
  - The organization has a mobile device management (MDM) system in place to centrally manage mobile devices supporting the service.

- **Visitor procedures**
  - The organization requires visitors to sign-in, wear a visitor badge, and be escorted by an authorized employee when accessing the data center or secure areas.

- **Security awareness training**
  - The organization requires employees to complete security awareness training within thirty days of hire and at least annually thereafter.

#### S2\.d Product Security
Security measures specifically integrated into AI products and services to protect against exploitation and unauthorized access.
- **Data encryption**
  - The organization's datastores housing sensitive customer data are encrypted at rest.

- **Control self-assessments**
  - The organization performs control self-assessments at least annually to gain assurance that controls are in place and operating effectively. Corrective actions are taken based on relevant findings. If the organization has committed to an SLA for a finding, the corrective action is completed within that SLA.

- **Vulnerability and system monitoring procedures**
  - The organization's formal policies outline the requirements for the following functions related to IT / Engineering:

vulnerability management;
system monitoring.

#### S2\.e Internal Security Procedures
Operational security procedures for maintaining the security posture of AI systems throughout their lifecycle.
- **Continuity and Disaster Recovery plans**
  - The organization has Business Continuity and Disaster Recovery Plans in place that outline communication plans in order to maintain information security continuity in the event of the unavailability of key personnel.

- **Production deployment access**
  - The organization restricts access to migrate changes to production to authorized personnel.

- **Development lifecycle**
  - The organization has a formal systems development life cycle (SDLC) methodology in place that governs the development, acquisition, implementation, changes (including emergency changes), and maintenance of information systems and related technology requirements.

- **Management roles and responsibilities**
  - The organization management has established defined roles and responsibilities to oversee the design and implementation of information security controls.

- **Security policies**
  - The organization's information security policies and procedures are documented and reviewed at least annually.

- **Incident response policies**
  - The organization has security and privacy incident response policies and procedures that are documented and communicated to authorized users.

- **Incident management procedures**
  - The organization's security and privacy incidents are logged, tracked, resolved, and communicated to affected or relevant parties by management according to the organization's security incident response policy and procedures.

- **Physical access processes**
  - The organization has processes in place for granting, changing, and terminating physical access to organization data centers based on an authorization from control owners.

- **Data center access**
  - The organization reviews access to the data centers at least annually.

- **Risk management program**
  - The organization has a documented risk management program in place that includes guidance on the identification of potential threats, rating the significance of the risks associated with the identified threats, and mitigation strategies for those risks.

#### S2\.f Data and Privacy
Controls specific to protecting the confidentiality and integrity of data used in AI training and inference processes.
- **Data retention procedures**
  - The organization has formal retention and disposal procedures in place to guide the secure retention and disposal of organization and customer data.

- **Data classification policy**
  - The organization has a data classification policy in place to help ensure that confidential data is properly secured and restricted to authorized personnel.

#### S2\.g Model Security
- **Model poisoning protections**
- **Adversarial example defenses**
- **Model versioning and integrity checks**
- **Secure model deployment pipelines**

### S3\. Operations
#### S3\.a Threat Intelligence
Frameworks and methodologies for identifying, analyzing, and responding to emerging threats specific to AI systems, including model poisoning, evasion attacks, and data extraction techniques.
- tools for threat intel

#### S3\.b Threat Hunting
Proactive approaches to identifying potential adversarial activities targeting AI systems before they manifest as security incidents.
- Red teaming for AI systems
- Prompt injection
- Membership inference
- Model inversion
- Backdoor vulnerabilities
- Data poisoning
- Model manipulation

- Tools for threat hunting

#### S3\.c Testing
- AI security testing methodologies
- Formal verification approaches
- Robustness certification
- Evaluation frameworks

#### S3\.d Incident Response for AI Systems
AI-specific incident detection
Containment strategies for compromised models
Forensics for AI systems
Recovery and remediation procedures

### S5\. Interdependent Security
Addressing security implications of AI system dependencies on external services, data sources, and infrastructure.
#### S5\.a Subprocessors
Management and security oversight of third parties that support AI operations or have access to system components.
- User support
- Billing
- Communication
- Application, monitoring, and search services
- Security and fraud detection services
- Cloud Infrastructure
- Networks
#### S5\.b Supply Chain
Security considerations for the AI development supply chain, including pre-trained models, datasets, and algorithmic components.
- tba
#### S5\.c Threat Modeling
- tba


## Privacy

### P1\. Differencial Privacy
Implementation strategies for differential privacy techniques that enable using sensitive data for AI training while providing mathematical privacy guarantees.

### P2\. Federated Learning with Privacy Protection
Approaches to implementing federated learning architectures that maintain data privacy by training models across decentralized devices without centralizing raw data.

### P3. Privacy-Preserving Machine Learning
- Homomorphic encryption applications
- Secure multi-party computation
- Zero-knowledge proofs
- Privacy-preserving record linkage

### P4. Data Minimization Techniques
- Training with synthetic data
- Privacy-preserving feature extraction
- Privacy-preserving inference
- Transfer learning approaches

### P5. Ethical Considerations
- Fairness and bias mitigation
- Explainability requirements
- Consent management for AI systems
- Right to be forgotten implementation

### P6. Privacy Governance
- Privacy by design principles for AI
- Privacy impact assessments
- Data protection officer responsibilities
- Cross-border data transfer considerations

### P7. Regulatory Compliance for AI Privacy
- GDPR AI-specific requirements
- CCPA/CPRA compliance for AI systems
- International privacy regulations affecting AI
- Emerging AI-specific privacy legislation