# Module 1: Foundations of AI Security and Red Teaming

## Learning Objectives
- Understand the unique security challenges posed by generative AI systems
- Identify key differences between traditional cybersecurity and AI security
- Apply industry-standard frameworks for AI risk assessment
- Configure and navigate the ViolentUTF platform for AI red teaming
- Analyze AI system architectures to identify attack surfaces

## 1.1 Introduction to AI Security Landscape (2 hours)

### The Evolution of AI Threats

#### Traditional Cybersecurity vs. AI-Specific Risks

**Traditional Cybersecurity Model:**
- Well-defined perimeters and boundaries
- Static attack surfaces with known vulnerabilities
- Deterministic system behaviors
- Established defense mechanisms (firewalls, IDS/IPS, antivirus)
- Clear audit trails and forensic capabilities

**AI Security Challenges:**
- **Dynamic Attack Surfaces:** AI models can be influenced by any input, creating virtually unlimited attack vectors
- **Emergent Behaviors:** AI systems may exhibit unexpected behaviors not explicitly programmed
- **Adversarial Inputs:** Subtle input modifications can dramatically change AI outputs
- **Black Box Complexity:** Understanding why an AI system made a specific decision is often difficult
- **Scale and Speed:** AI systems can be attacked and compromised at machine speed

#### Real-World AI Security Incidents

**Case Study 1: Tay Chatbot (Microsoft, 2016)**
- **Incident:** Twitter users coordinated to teach Microsoft's Tay chatbot to produce offensive content
- **Attack Vector:** Coordinated adversarial training through public interaction
- **Impact:** Chatbot taken offline within 24 hours due to inappropriate responses
- **Lessons:** Need for robust content filtering and adversarial input detection

**Case Study 2: GPT-4 Early Jailbreaks (OpenAI, 2023)**
- **Incident:** Various prompt injection techniques bypassed safety guardrails
- **Attack Vector:** Crafted prompts using roleplay, hypotheticals, and encoding
- **Impact:** Generation of harmful content despite safety training
- **Lessons:** Importance of continuous red teaming and safety evaluation

**Case Study 3: Adversarial Patches (Physical World)**
- **Incident:** Small stickers on stop signs caused misclassification by autonomous vehicles
- **Attack Vector:** Adversarial examples in computer vision systems
- **Impact:** Critical safety implications for autonomous systems
- **Lessons:** Multi-modal attacks require comprehensive security assessment

### AI Risk Taxonomy

#### NIST AI Risk Management Framework (AI RMF)

The NIST AI RMF provides a comprehensive structure for managing AI risks across four core functions:

**1. Govern (Functions and Structures)**
- AI governance and risk management culture
- Policies, processes, and procedures for AI risk management
- Human oversight and approval processes
- Regular assessment and continuous improvement

**2. Map (Context and Risks)**
- AI system categorization and impact assessment
- Risk identification and analysis
- Stakeholder involvement and feedback mechanisms
- Legal and regulatory requirement mapping

**3. Measure (AI System Assessment)**
- AI system performance and reliability metrics
- Bias and fairness evaluation measures
- Security and robustness testing protocols
- Human-AI interaction assessment

**4. Manage (Response and Recovery)**
- Risk response and treatment strategies
- Incident response and recovery procedures
- Continuous monitoring and updating
- Third-party risk management

#### OWASP Top 10 for LLM Applications

**LLM01: Prompt Injection**
- Manipulating LLM via crafted inputs
- Can override system instructions
- Direct and indirect injection variants

**LLM02: Insecure Output Handling**
- Insufficient validation of LLM outputs
- Can lead to XSS, CSRF, SSRF attacks
- Backend system compromise risk

**LLM03: Training Data Poisoning**
- Manipulation of training or fine-tuning data
- Can introduce backdoors or biases
- Supply chain security implications

**LLM04: Model Denial of Service**
- Resource exhaustion attacks
- High-cost query exploitation
- Variable-length input vulnerabilities

**LLM05: Supply Chain Vulnerabilities**
- Third-party dataset and model risks
- Plugin and integration vulnerabilities
- Dependency and infrastructure security

**LLM06: Sensitive Information Disclosure**
- Revealing confidential data from training
- PII extraction and memorization
- System prompt and configuration exposure

**LLM07: Insecure Plugin Design**
- Insufficient input validation in plugins
- Inappropriate access controls
- Plugin-to-plugin security boundaries

**LLM08: Excessive Agency**
- LLM systems with too much autonomy
- Insufficient oversight mechanisms
- Unintended action execution

**LLM09: Overreliance**
- Excessive dependence on LLM outputs
- Insufficient human oversight
- Critical decision automation risks

**LLM10: Model Theft**
- Unauthorized access to proprietary models
- Model extraction and replication
- Intellectual property violations

#### MITRE ATLAS Framework

**Tactics and Techniques for AI/ML Systems:**

**Initial Access (TA0001)**
- ML Supply Chain Compromise
- Valid Accounts
- Public-Facing Application exploitation

**ML Model Access (TA0000)**
- Full ML Model Access
- ML Model Inference API Access
- Physical Environment access

**Reconnaissance (TA0043)**
- Victim Organization research
- ML Model discovery
- Data source identification

**Resource Development (TA0042)**
- Acquire ML Artifacts
- Develop ML Attack capabilities
- Obtain adversarial ML tools

**Persistence (TA0003)**
- Backdoor ML Models
- Valid Account maintenance
- Create ML Model accounts

### Practical Exercise 1.1: ViolentUTF Platform Setup

#### Environment Configuration

**Prerequisites:**
- Docker and Docker Compose installed
- Python 3.9+ environment
- API keys for OpenAI, Anthropic, or other LLM providers
- Git for repository management

**Step-by-Step Setup:**

1. **Clone ViolentUTF Repository**
```bash
git clone https://github.com/cybonto/ViolentUTF.git
cd ViolentUTF
```

2. **Configure API Keys**
```bash
cp ai-tokens.env.sample ai-tokens.env
# Edit ai-tokens.env with your API keys
```

3. **Run Setup Script**
```bash
./setup_macos_new.sh --verbose
```

4. **Verify Services**
```bash
./check_services.sh
```

**Expected Services:**
- Streamlit Dashboard: http://localhost:8501
- FastAPI Backend: http://localhost:9080/api/v1
- API Documentation: http://localhost:9080/docs
- MCP Server: http://localhost:9080/mcp/sse
- Keycloak SSO: http://localhost:8080

#### Platform Navigation

**Dashboard Overview:**
- Authentication and user management
- Target configuration and selection
- Campaign creation and management
- Result analysis and reporting

**Key Features:**
- PyRIT orchestrator integration
- Garak probe execution
- Custom scorer development
- Automated pipeline execution

---

## 1.2 Understanding Generative AI Architecture (2 hours)

### LLM Architecture Deep Dive

#### Transformer Architecture Components

**Attention Mechanisms:**
- Self-attention for input token relationships
- Multi-head attention for diverse feature capture
- Positional encoding for sequence understanding
- Attention weights as interpretability aids

**Model Layers:**
- Embedding layers for token representation
- Transformer blocks with attention and feedforward networks
- Normalization layers for training stability
- Output projection for next-token prediction

**Training Process:**
1. **Pre-training:** Large-scale self-supervised learning on diverse text
2. **Fine-tuning:** Task-specific adaptation with supervised learning
3. **Alignment:** RLHF for human preference optimization
4. **Safety Training:** Additional fine-tuning for harmlessness

#### Attack Surface Analysis

**Pre-training Vulnerabilities:**
- **Data Poisoning:** Malicious content in training data
- **Backdoor Insertion:** Trigger-response patterns
- **Bias Amplification:** Societal biases in training data
- **Memorization:** Verbatim recall of sensitive information

**Inference-Time Vulnerabilities:**
- **Prompt Injection:** Malicious instructions in user input
- **Jailbreaking:** Bypassing safety guidelines
- **Adversarial Examples:** Inputs designed to cause misclassification
- **Context Manipulation:** Exploiting conversation history

**Post-processing Vulnerabilities:**
- **Output Filtering Bypass:** Evading content moderation
- **Integration Exploits:** Vulnerabilities in downstream systems
- **API Abuse:** Rate limiting and resource exhaustion
- **Data Leakage:** Sensitive information in responses

### Multi-Modal AI Security

#### Vision-Language Models

**Architecture Components:**
- **Vision Encoder:** CNN or Vision Transformer for image processing
- **Language Model:** Transformer for text understanding
- **Cross-Modal Attention:** Linking visual and textual information
- **Fusion Mechanisms:** Combining modalities for unified understanding

**Attack Vectors:**
- **Adversarial Images:** Visually imperceptible perturbations
- **Image-Text Misalignment:** Exploiting modality gaps
- **OCR-based Injection:** Text within images to bypass filters
- **Cross-Modal Consistency Attacks:** Contradictory information across modalities

#### Code Generation Models

**Unique Characteristics:**
- **Syntax Awareness:** Understanding of programming language structures
- **Context Completion:** Intelligent code completion and generation
- **Multi-Language Support:** Polyglot programming capabilities
- **Documentation Integration:** Code comments and documentation generation

**Security Concerns:**
- **Malicious Code Injection:** Generation of harmful code patterns
- **Vulnerability Introduction:** Creating insecure code constructs
- **License Violations:** Reproducing copyrighted code snippets
- **Supply Chain Risks:** Dependencies and package suggestions

### Practical Exercise 1.2: Target System Analysis

#### ViolentUTF System Profiling

**Target Selection:**
```python
# Example target configuration in ViolentUTF
target_config = {
    "name": "gpt-4-demo",
    "type": "OpenAI",
    "model": "gpt-4",
    "api_key": "${OPENAI_API_KEY}",
    "temperature": 0.7,
    "max_tokens": 1024
}
```

**System Fingerprinting:**
1. **Model Identification:** Determine exact model version and capabilities
2. **Safety Mechanisms:** Identify implemented guardrails and filters
3. **Context Limits:** Test maximum context window and handling
4. **Response Patterns:** Analyze typical output formats and structures

**Architecture Mapping:**
- API endpoint analysis
- Authentication mechanisms
- Rate limiting detection
- Integration points identification

**Vulnerability Surface Assessment:**
- Input validation testing
- Output sanitization analysis
- Error handling evaluation
- Resource consumption patterns

---

## 1.3 AI Red Teaming Methodologies (2 hours)

### Red Teaming vs. Traditional Penetration Testing

#### Methodological Differences

**Traditional Penetration Testing:**
- **Scope:** Well-defined network and application boundaries
- **Objectives:** Identify known vulnerability classes
- **Tools:** Standardized scanning and exploitation tools
- **Timeline:** Fixed engagement duration
- **Reporting:** Technical vulnerability reports

**AI Red Teaming:**
- **Scope:** Dynamic interaction space with emergent behaviors
- **Objectives:** Discover novel failure modes and unsafe behaviors
- **Tools:** Custom prompts, adversarial examples, behavioral analysis
- **Timeline:** Iterative campaigns with continuous discovery
- **Reporting:** Behavioral analysis and safety recommendations

#### Human-in-the-Loop vs. Automated Testing

**Human-in-the-Loop Advantages:**
- Creative and contextual attack development
- Domain expertise for specialized attacks
- Nuanced evaluation of AI responses
- Ethical judgment in attack selection

**Automated Testing Benefits:**
- Scale and coverage across attack vectors
- Consistent and reproducible results
- Rapid iteration and refinement
- Cost-effective for routine assessments

**Hybrid Approaches:**
- Human-designed attacks with automated execution
- AI-assisted attack generation with human validation
- Automated screening with human deep-dive analysis
- Continuous automated monitoring with periodic human review

### Industry Frameworks and Best Practices

#### Microsoft AI Red Team Approach

**Organizational Structure:**
- Dedicated AI Red Team (AIRT) established in 2018
- Integration with product development lifecycle
- Cross-functional collaboration with engineering teams
- Executive sponsorship and organizational commitment

**Methodology Components:**
1. **Threat Modeling:** Systematic identification of AI-specific risks
2. **Attack Development:** Creative and technical attack creation
3. **Automated Execution:** PyRIT framework for scalable testing
4. **Impact Assessment:** Business and safety impact evaluation
5. **Remediation Support:** Collaborative vulnerability mitigation

**Key Insights:**
- Efficiency gains of 10x through automation (PyRIT)
- Coverage of 15+ harm categories in Phi-3 assessment
- Integration with 100+ AI products at Microsoft
- Continuous improvement of attack techniques

#### Anthropic's Constitutional AI

**Core Principles:**
- **Constitutional Training:** Teaching AI systems to follow principles
- **Harmlessness and Helpfulness:** Balancing safety with utility
- **Transparency:** Clear reasoning about AI decisions
- **Iterative Improvement:** Continuous refinement of safety measures

**Red Teaming Integration:**
- Adversarial testing throughout development
- Constitutional violation detection
- Human feedback incorporation
- Safety evaluation benchmarks

### Case Study: Microsoft Phi-3 Model Red Teaming

#### Project Overview
- **Objective:** Safety assessment for open-source model release
- **Scope:** Text and vision model variants
- **Timeline:** Multi-week comprehensive assessment
- **Team:** Cross-functional AI red team

#### Methodology
1. **Harm Category Definition:** 15 distinct categories identified
2. **Attack Generation:** Thousands of adversarial prompts created
3. **Automated Execution:** PyRIT framework for scalable testing
4. **Scoring and Analysis:** Automated and human evaluation
5. **Comparative Analysis:** Benchmarking against state-of-the-art models

#### Key Findings
- Identification of model-specific vulnerabilities
- Comparative safety analysis across model families
- Effectiveness validation of safety training methods
- Recommendations for deployment safeguards

#### Lessons Learned
- Importance of diverse attack perspectives
- Value of automated testing at scale
- Need for continuous safety evaluation
- Integration of red teaming with development

---

## 1.4 Legal and Ethical Considerations (2 hours)

### Responsible AI Testing

#### Ethical Guidelines and Boundaries

**Core Ethical Principles:**
1. **Beneficence:** Testing should improve AI safety and security
2. **Non-maleficence:** Avoid causing harm through testing activities
3. **Autonomy:** Respect user privacy and consent
4. **Justice:** Fair and unbiased assessment across all user groups

**Testing Boundaries:**
- **Prohibited Content:** No generation of illegal or extremely harmful content
- **Privacy Respect:** Avoid extracting personal information without consent
- **Resource Respect:** Minimize unnecessary system resource consumption
- **Professional Conduct:** Maintain high standards of professional ethics

#### Responsible Disclosure Framework

**Disclosure Timeline:**
1. **Initial Discovery:** Document and verify vulnerability
2. **Vendor Notification:** Coordinate disclosure with AI provider
3. **Negotiated Timeline:** Agree on reasonable remediation period
4. **Public Disclosure:** Share findings with community (if appropriate)

**Disclosure Components:**
- **Technical Details:** Sufficient information for reproduction
- **Impact Assessment:** Clear explanation of potential harm
- **Mitigation Strategies:** Suggested approaches for remediation
- **Timeline Documentation:** Clear record of disclosure process

### Regulatory Compliance

#### GDPR Implications for AI Testing

**Data Protection Requirements:**
- **Lawful Basis:** Legitimate interest in AI safety research
- **Data Minimization:** Collect only necessary data for testing
- **Purpose Limitation:** Use data only for stated testing purposes
- **Storage Limitation:** Retain data only as long as necessary

**Individual Rights:**
- **Right to Information:** Transparent testing processes
- **Right of Access:** Ability to access collected data
- **Right to Rectification:** Correction of inaccurate data
- **Right to Erasure:** Deletion of unnecessary data

#### Industry-Specific Requirements

**Healthcare AI:**
- HIPAA compliance for health information
- FDA requirements for medical device software
- Clinical trial protocols for AI evaluation
- Patient safety and informed consent

**Financial Services:**
- SOX compliance for financial reporting AI
- Fair Credit Reporting Act for credit decisions
- Anti-discrimination laws for lending AI
- Privacy requirements for financial data

**Critical Infrastructure:**
- NERC CIP for electrical grid AI systems
- Transportation safety regulations
- Industrial control system security
- National security considerations

### Documentation and Audit Trails

#### Comprehensive Documentation Requirements

**Testing Documentation:**
1. **Test Plan:** Objectives, scope, and methodology
2. **Execution Logs:** Detailed records of all testing activities
3. **Results Analysis:** Findings, impact assessment, and recommendations
4. **Remediation Tracking:** Status of vulnerability mitigation efforts

**Legal Protection Documentation:**
- **Authorization:** Clear permission for testing activities
- **Scope Agreement:** Defined boundaries and limitations
- **Disclosure Agreements:** Confidentiality and non-disclosure terms
- **Insurance Coverage:** Professional liability and cyber insurance

### Workshop: Developing Organizational AI Red Teaming Policies

#### Policy Framework Development

**Organizational Policy Components:**
1. **Purpose and Scope:** Clear articulation of red teaming objectives
2. **Roles and Responsibilities:** Definition of team roles and accountabilities
3. **Methodology Standards:** Standardized approaches and procedures
4. **Approval Processes:** Authorization requirements for testing activities
5. **Reporting Requirements:** Internal and external communication protocols

**Risk Management Integration:**
- **Risk Assessment:** Integration with enterprise risk management
- **Business Impact Analysis:** Understanding of testing impact on operations
- **Incident Response:** Procedures for handling discovered vulnerabilities
- **Continuous Improvement:** Regular review and update of policies

#### Practical Exercise: Policy Development

**Small Group Activity:**
1. **Scenario Assignment:** Each group receives a specific industry scenario
2. **Policy Development:** Create comprehensive red teaming policy
3. **Peer Review:** Groups review and provide feedback on policies
4. **Class Discussion:** Share insights and best practices

**Deliverables:**
- Written policy document
- Implementation timeline
- Risk mitigation strategies
- Success metrics and KPIs

---

## Module 1 Assessment

### Knowledge Check Questions

1. **Compare and contrast traditional cybersecurity threats with AI-specific security risks. Provide three key differences and explain their implications.**

2. **Explain the NIST AI RMF four core functions. How would you apply each function in planning an AI red teaming engagement?**

3. **Analyze the OWASP Top 10 for LLM Applications. Select the three most critical risks for a customer service chatbot and justify your selection.**

4. **Describe the ethical considerations unique to AI red teaming. How do these differ from traditional penetration testing ethics?**

### Practical Assessment

**ViolentUTF Platform Proficiency:**
- Successfully configure and navigate the ViolentUTF platform
- Complete target system profiling for assigned AI system
- Demonstrate understanding of key platform components
- Execute basic vulnerability scanning using integrated tools

**Documentation Exercise:**
- Create threat model for simple AI chatbot scenario
- Develop testing scope and boundaries document
- Draft responsible disclosure communication template

### Reflection Questions

1. What aspects of AI security surprised you most in this module?
2. How will you apply these concepts in your current role?
3. What additional preparation do you need for advanced modules?
4. Which industry frameworks seem most relevant to your organization?

---

## Module 1 Resources

### Required Readings
- NIST AI Risk Management Framework (AI RMF 1.0)
- OWASP Top 10 for Large Language Model Applications
- MITRE ATLAS Framework for AI/ML Security
- Microsoft PyRIT Research Paper

### Supplementary Materials
- "Adversarial Machine Learning" by Biggio & Roli
- "The Alignment Problem" by Brian Christian
- OpenAI Red Teaming Documentation
- Anthropic Constitutional AI Papers

### Tools and Platforms
- ViolentUTF Platform (provided in course)
- PyRIT Framework (Microsoft)
- Garak LLM Vulnerability Scanner (NVIDIA)
- Jupyter Notebooks for exercises

### Community Resources
- AI Security Research Communities
- Professional AI Security Groups
- Academic Research Repositories
- Industry Working Groups

This completes Module 1 of the AI Red Teaming course, providing comprehensive foundation knowledge for advanced practical modules that follow.
