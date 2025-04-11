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
##### Model Card
- **Description:**
- A Model Card is a standardized documentation that provides essential information about a specific machine learning model. It focuses on the model's technical properties, performance characteristics, intended use cases, and limitations.
- **Key Components:**
  - Model architecture and version
  - Training data characteristics (without revealing sensitive details)
  - Performance metrics across different demographics and conditions
  - Model limitations and failure modes
  - Intended use cases and restrictions
  - Model sensitivity and robustness measures
  - Ethical considerations specific to the model
- **Resources:**
  - [Systematic analysis of 32,111 AI model cards characterizes documentation practice in AI](https://www.nature.com/articles/s42256-024-00857-z) (Nature-JUN2024)
  - [Automatic Generation of Model and Data Cards: A Step Towards Responsible AI](https://arxiv.org/abs/2405.06258) (Arxiv-MAY2024)
  - [Sample: Amazon's Guide to Creating a Model Card](https://docs.aws.amazon.com/sagemaker/latest/dg/model-cards-create.html) (APR2025)
  - tba
 
##### System Card
- **Description:**
  - A System Card documents the entire AI system that may employ one or more models. It focuses on the broader deployment context, integration aspects, data flows, user interactions, and system-wide risks and mitigations.
- **Key Components:**
  - System architecture overview and components
  - Data flows and storage practices
  - Underlying infrastructure and dependencies
  - Human oversight mechanisms
  - Integration with other systems
  - Risk assessment and mitigation strategies
  - User interaction patterns
  - Monitoring and maintenance procedures
  - Compliance with regulations
- **Resources:**
  - [OpenAI o1 System Card](https://arxiv.org/abs/2412.16720) (Arxiv-DEC2024)
  - [AI Risk Profiles: A Standards Proposal for Pre-deployment AI Risk Disclosures](https://ojs.aaai.org/index.php/AAAI/article/view/30348) (AAAI2024)
  - [AI Cards: Towards an Applied Framework for Machine-Readable AI and Risk Documentation Inspired by the EU AI Act](https://link.springer.com/chapter/10.1007/978-3-031-68024-3_3) (SpringerNatureLink-AUG2024)
  - [Use case cards: a use case reporting framework inspired by the European AI Act](https://link.springer.com/article/10.1007/s10676-024-09757-7) (SpringerNatureLink-MAR2024)
  - tba

##### Addendum Process
- **Resources:**
  - [Model Card Addendum: Claude 3.5 Haiku and Upgraded Claude 3.5 Sonnet](https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf) (OCT2024)
  - [Addendum to GPT-4o System Card: Native image generation](https://cdn.openai.com/11998be9-5319-4302-bfbf-1167e093f1fb/Native_Image_Generation_System_Card.pdf) (MAR2025)

##### Standard Information Gathering (SIG) Lite questionnaire
A streamlined version of the Shared Assessments SIG questionnaire that collects essential information about an organization's security controls, risk management practices, and compliance posture. The SIG Lite focuses on critical security domains with fewer questions than the comprehensive SIG, making it more accessible for AI vendors while still providing meaningful security assurance. It covers areas such as information security policies, access controls, data protection, and incident management specific to AI systems.
- **Resources**:
  - [What is the SIG questionnaire?](https://www.vanta.com/collection/trust/sig-questionnaire) (Vanta-APR2025)
  - tba

##### Consensus Assessments Initiative Questionnaire (CAIQ) Lite questionnaire
Developed by the Cloud Security Alliance (CSA), the CAIQ Lite is a condensed version of the full CAIQ designed to assess the security capabilities of cloud service providers and AI systems. This questionnaire maps to the CSA Cloud Controls Matrix (CCM) and focuses on key security principles relevant to AI deployments, including data security, application security, and compliance. CAIQ Lite enables AI vendors to demonstrate their security posture without the extensive overhead of the full CAIQ, making it suitable for rapid vendor risk assessments.
- **Resources**:
  - [What is the CAIQ (Consensus Assessment Initiative Questionnaire)?](https://www.vanta.com/collection/trust/caiq) (Vanta-APR2025)
  - tba

##### Vendor Security Alliance (VSA) Core questionnaire
The VSA Core questionnaire is a standardized security assessment tool developed by the Vendor Security Alliance to evaluate third-party vendor security practices, with specific considerations for AI systems. This questionnaire focuses on fundamental security controls across domains including data protection, access management, vulnerability management, and incident response. The VSA Core is designed to provide objective security assessment metrics while minimizing the burden on AI vendors, facilitating more efficient security reviews and enabling better comparison between different AI solution providers.
- **Resources**:
  - [What is the VSAQ (Vendor Security Alliance Questionnaire)?](https://www.vanta.com/collection/trust/vendor-security-alliance-questionnaire) (Vanta-APR2025)
  - tba
    
#### SOC 2 Type 1
Point-in-time assessment of an organization's system and suitability of control design related to security, availability, processing integrity, confidentiality, and privacy.
- **Resources:**
  - [How to incorporate AI considerations into your SOC2 examination](https://www.schellman.com/blog/soc-examinations/how-to-incorporate-ai-into-your-soc-2-examination#:~:text=While%20the%20SOC%202%20trust,Availability;)
  - [SOC 2 Type 1 vs Type 2](https://secureframe.com/hub/soc-2/type-1-vs-type-2)
#### SOC 2 Type 2
Comprehensive assessment of control effectiveness over an extended period (typically 6-12 months), providing higher assurance levels than Type 1.
- **SOC 2 Type 2 Report**
  - A detailed audit report conducted by an independent third-party auditor that evaluates the effectiveness of an organization's controls over a 6-12 month period against the AICPA Trust Services Criteria. For AI systems, this report includes specific attestations about data processing integrity, model governance, and security controls protecting AI operations and data. The report contains control descriptions, test procedures, and results demonstrating sustained compliance.
- **CSA STAR Report**
  - A specialized attestation report that combines SOC 2 examination with the Cloud Security Alliance's Cloud Controls Matrix, providing additional cloud-specific security assurances relevant to AI deployments. This report addresses cloud security controls specifically relevant to AI systems, such as secure model storage, training environment security, and data protection in distributed computing environments. It offers enhanced transparency about cloud security practices supporting AI operations.
- **Resources:**
  - [A Survey of Major Cybersecurity Compliance Frameworks](https://ieeexplore.ieee.org/abstract/document/10565236) (IEEE-BidDataSecurity-2024)
  - [STAR Program for AI](https://e.cloudsecurityalliance.org/STAR_AI) (CSA-APR2025)
  - [Securing the Future of AI: A Deep Compliance Review of Anthropic, Google DeepMind, and OpenAI Under SOC 2, ISO 27001, and NIST](https://www.tdcommons.org/dpubs_series/7951/) (TDcommons-APR2025)
  - tba
#### ISO 27001:2022
International standard for information security management systems (ISMS), with specific considerations for AI systems.
- **Statement of Applicability**
  - A formal document that identifies which controls from ISO 27001 Annex A are applicable to the organization's AI systems and explains the rationale for including or excluding specific controls. For AI systems, this typically includes specialized controls addressing model security, data protection during training and inference, and access controls for AI development environments. The document serves as the foundation for ISMS implementation and auditing.
- **ISO 27001 Certificate**
  - The official certification document issued by an accredited certification body confirming that the organization's information security management system has been audited and meets all ISO 27001:2022 requirements. The certificate includes the certification scope specifically detailing AI-related activities covered, validity period (typically three years), and the issuing certification body's accreditation information. This certificate provides formal validation of the organization's security practices for AI systems.
- **Resources:**
  - [Managing Security and AI: The Role of ISO 27001 & 42001](https://www.ccsrisk.com/iso27001-iso42001#:~:text=In%20summary%2C%20ISO%2027001:2022,associated%20risks%20and%20negative%20impacts.)
  - [Impact of Artificial Intelligence on Enterprise Information Security Management in the Context of ISO 27001 and 27002: A Tertiary Systematic Review and Comparative Analysis](https://link.springer.com/chapter/10.1007/978-3-031-52272-7_1) (SpringerNatureLink-APR2024)
#### ISO/IEC 42001:2023
The recently established international standard specifically addressing AI management systems and governance frameworks.
- **Resources:**
  - [Comparison and Analysis of 3 Key AI Documents: EU’s Proposed AI Act, Assessment List for Trustworthy AI (ALTAI), and ISO/IEC 42001 AI Management System](https://link.springer.com/chapter/10.1007/978-3-031-26438-2_15) (AICS2022)
  - [ISO/IEC quality standards for AI engineering](https://www.sciencedirect.com/science/article/abs/pii/S1574013724000650) (ComputerScienceReview-NOV2024)

#### Domain-specific Compliance: Finance
- **Financial AI Risk Assessment**
  - Documentation evaluating AI systems against financial regulatory requirements including model risk management guidelines (SR 11-7), consumer protection regulations, and anti-discrimination laws. This assessment identifies risks specific to AI use in financial decision-making and describes implemented controls.
- **Model Governance Documentation**
  - Formal documentation detailing model development, validation, implementation, and ongoing monitoring procedures in accordance with financial regulatory expectations, particularly focused on model explainability and auditability.
- **Resources:**
  - [Federal Reserve Guidance on Model Risk Management](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
  - [Financial Stability Board's Artificial Intelligence and Machine Learning in Financial Services](https://www.fsb.org/work-of-the-fsb/financial-innovation-and-structural-change/artificial-intelligence-and-machine-learning-in-financial-services/)
  - [FINRA AI Report: Considerations for Use of Artificial Intelligence in the Securities Industry](https://www.finra.org/rules-guidance/key-topics/artificial-intelligence)

#### Domain-specific Compliance: Healthcare
##### HIPAA
Requirements specific to healthcare AI applications, focusing on protecting personal health information (PHI) in accordance with Health Insurance Portability and Accountability Act standards.
- **Annual HIPAA SCA Report**
  - A formal security compliance assessment report that documents an organization's adherence to HIPAA Security, Privacy, and Breach Notification Rules in the context of AI systems handling PHI. The report evaluates controls protecting patient data throughout the AI lifecycle, including data collection, processing, model training, and inference. It contains detailed findings on administrative, physical, and technical safeguards implemented to protect the confidentiality, integrity, and availability of PHI processed by AI systems, along with any required remediation actions.
- **Resources:**
  - [AI in Healthcare: HIPAA Compliance Considerations](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/index.html)
  - [OCR Guidance on AI and Machine Learning in Healthcare](https://www.healthit.gov/topic/scientific-initiatives/artificial-intelligence-healthcare)
##### Other healthcare
- **AI Medical Device Documentation**
  - For AI systems classified as medical devices, documentation demonstrating compliance with FDA requirements including pre-market submissions (510(k), De Novo, or PMA), quality system regulations, and post-market surveillance commitments.
- **Clinical Validation Reports**
  - Documentation of clinical validation studies demonstrating the safety and efficacy of AI applications in healthcare contexts, including statistical analyses, performance metrics, and testing across diverse patient populations.
- **Resources:**
  - [FDA Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan](https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-software-medical-device)
  - [Good Machine Learning Practice for Medical Device Development](https://www.fda.gov/medical-devices/software-medical-device-samd/good-machine-learning-practice-medical-device-development-guiding-principles)

#### Domain-specific Compliance: Critical Infrastructure
- **Critical Infrastructure Protection Plan**
  - Documentation detailing how AI systems in critical infrastructure comply with relevant frameworks such as NIST Cybersecurity Framework, IEC 62443, or sector-specific guidelines. This includes security controls, resilience measures, and contingency planning.
- **Operational Technology Security Assessment**
  - Formal assessment of security controls protecting AI systems integrated with operational technology environments, including segmentation strategies, monitoring capabilities, and incident response procedures specific to industrial control systems.
- **Resources:**
  - [NIST Cybersecurity Framework for Critical Infrastructure](https://www.nist.gov/cyberframework)
  - [CISA Artificial Intelligence and Critical Infrastructure Security](https://www.cisa.gov/topics/artificial-intelligence-critical-infrastructure-security)
  - [IEC 62443 - Industrial Automation and Control Systems Security](https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards)

#### Domain-specific Compliance: Defense
- **Classification Compliance Documentation**
  - Documentation demonstrating that AI systems processing classified information adhere to relevant security classification guidelines, including data handling procedures, access controls, and security clearance requirements.
- **Defense Acquisition Compliance Report**
  - For AI systems developed for defense applications, documentation showing compliance with relevant defense acquisition regulations such as DFARS, including cybersecurity requirements, supply chain risk management, and testing procedures.
- **Resources:**
  - [DoD Artificial Intelligence Strategy](https://www.defense.gov/Innovation/AI-Engineering/)
  - [Defense Innovation Board AI Principles](https://innovation.defense.gov/ai/)
  - [National Security Commission on Artificial Intelligence Final Report](https://www.nscai.gov/report)
  - [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

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
- **Resources:**
  - [Coordinated Flaw Disclosure for AI: Beyond Security Vulnerabilities](https://dl.acm.org/doi/10.5555/3716662.3716686) (AAAI2024)

#### S3\.b Threat Hunting
Proactive approaches to identifying potential adversarial activities targeting AI systems before they manifest as security incidents.
- Red teaming for AI systems
- Prompt injection
- Membership inference
- Model inversion
- Backdoor vulnerabilities
- Data poisoning
- Model manipulation

- **Resources:**
  - [OpenAI's Approach to External Red Teaming for AI Models and Systems](https://arxiv.org/abs/2503.16431) (Arxiv-JAN2025)
- Tools for threat hunting
- 

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
