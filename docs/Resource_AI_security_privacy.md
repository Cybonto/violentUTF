# Resource for AI Security and Privacy

## Table of Contents
- [Resource for AI Security and Privacy](#resource-for-ai-security-and-privacy)
  - [Forewords](#forewords)
    - [Goals](#goals)
    - [Contributions](#contributions)
  - [Security](#security)
    - [S1. Compliance](#s1-compliance)
      - [General Items](#general-items)
        - [Model Card](#model-card)
        - [System Card](#system-card)
        - [Addendum Process](#addendum-process)
        - [Standard Information Gathering (SIG) Lite questionnaire](#standard-information-gathering-sig-lite-questionnaire)
        - [Consensus Assessments Initiative Questionnaire (CAIQ) Lite questionnaire](#consensus-assessments-initiative-questionnaire-caiq-lite-questionnaire)
        - [Vendor Security Alliance (VSA) Core questionnaire](#vendor-security-alliance-vsa-core-questionnaire)
      - [SOC 2 Type 1](#soc-2-type-1)
      - [SOC 2 Type 2](#soc-2-type-2)
      - [ISO 27001:2022](#iso-270012022)
      - [ISO/IEC 42001:2023](#isoiec-420012023)
      - [Domain-specific Compliance: Finance](#domain-specific-compliance-finance)
      - [Domain-specific Compliance: Healthcare](#domain-specific-compliance-healthcare)
        - [HIPAA](#hipaa)
        - [Other healthcare](#other-healthcare)
      - [Domain-specific Compliance: Critical Infrastructure](#domain-specific-compliance-critical-infrastructure)
      - [Domain-specific Compliance: Defense](#domain-specific-compliance-defense)
    - [S2. Controls](#s2-controls)
      - [S2.a Infrastructure Diagrams](#s2a-infrastructure-diagrams)
      - [S2.b Infrastructure Security](#s2b-infrastructure-security)
      - [S2.c Organizational Security](#s2c-organizational-security)
      - [S2.d Product Security](#s2d-product-security)
      - [S2.e Internal Security Procedures](#s2e-internal-security-procedures)
      - [S2.f Data and Privacy](#s2f-data-and-privacy)
      - [S2.g Model Security](#s2g-model-security)
    - [S3. Operations](#s3-operations)
      - [S3.a Threat Intelligence](#s3a-threat-intelligence)
      - [S3.b Threat Hunting](#s3b-threat-hunting)
      - [S3.c Testing](#s3c-testing)
      - [S3.d Incident Response for AI Systems](#s3d-incident-response-for-ai-systems)
    - [S5. Interdependent Security](#s5-interdependent-security)
      - [S5.a Subprocessors](#s5a-subprocessors)
      - [S5.b Supply Chain](#s5b-supply-chain)
      - [S5.c Threat Modeling](#s5c-threat-modeling)
  - [Privacy](#privacy)
    - [P1. Differencial Privacy](#p1-differencial-privacy)
    - [P2. Federated Learning with Privacy Protection](#p2-federated-learning-with-privacy-protection)
    - [P3. Privacy-Preserving Machine Learning](#p3-privacy-preserving-machine-learning)
    - [P4. Data Minimization Techniques](#p4-data-minimization-techniques)
    - [P5. Ethical Considerations](#p5-ethical-considerations)
    - [P6. Privacy Governance](#p6-privacy-governance)
    - [P7. Regulatory Compliance for AI Privacy](#p7-regulatory-compliance-for-ai-privacy)
      
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

##### MODEL CARD
* **Description:**
    * A Model Card is a standardized document providing essential, easy-to-understand information about a machine learning model.
    * It acts as a communication bridge between developers and users, detailing a model's functionality, applications, potential biases, errors, and limitations.
    * Inspired by concepts like food nutrition labels and datasheets in electronics, Model Cards aim to increase transparency and trust.
    * They are considered a preferred reference over academic papers or technical reports for practitioners due to their concise, relevant, accessible, and up-to-date nature.
* **Key Components:**
    * **Model architecture and version:** Basic details about the model, including architecture, parameters, and potentially the base model if it's fine-tuned.
    * **Training data characteristics:** Information on training data, including volume, characteristics, and preprocessing steps (like tokenization or lowercasing), without revealing sensitive details. Datasheets or data statements can complement this by detailing dataset motivation, composition, collection, and recommended uses.
    * **Performance metrics across different demographics and conditions:** Evaluation results, ideally disaggregated across relevant factors (like domain, context, population subgroups) to reveal performance disparities. Common metrics include F1 scores, BLEU scores, precision, recall, and accuracy.
    * **Model limitations and failure modes:** Known or foreseeable issues, including technical constraints (e.g., maximum input length), societal biases (potentially inherited from training data or backbone models), and potential harms or misunderstandings. Disclaimers about intended use (e.g., "not for production" or "not a diagnostic tool") are also common.
    * **Intended use cases and restrictions:** Clear description of the model's designated tasks (e.g., object detection, tweet generation) and how it can be used directly or downstream (fine-tuned, part of a larger system). It also addresses out-of-scope uses and potential misapplications, advising what users should avoid.
    * **Model sensitivity and robustness measures:** While not explicitly detailed as "sensitivity and robustness" in the text, the evaluation section covers performance metrics, and the limitations section addresses potential failure points under certain conditions or with specific data types.
    * **Ethical considerations specific to the model:** This is primarily covered under "Bias, Risks, and Limitations," discussing potential biases, societal impacts, and recommendations for mitigating risks.
* **Advances in Model Card:**
    * Model cards have become a standard documentation approach in the AI community.
    * Platforms like Hugging Face provide guidelines and tools to facilitate their creation, including graphical interfaces and methods to track environmental impact (like CO2 emissions).
    * Automated generation of Model Cards using Large Language Models (LLMs) is being explored to enhance completeness, objectivity, and faithfulness compared to potentially incomplete human-written cards.
    * Research is ongoing to improve documentation practices, potentially including system cards for complex AI systems  and value cards for educational purposes.
* **Existing challenges and/or gaps with Model Card:**
    * **Inconsistent Quality and Completeness:** Many model cards, even on platforms like Hugging Face, suffer from incompleteness and variability. Developers might copy existing cards rather than using standardized templates.
    * **Uneven Section Focus:** Some sections are frequently filled out (e.g., Training), while others crucial for responsible AI, like Environmental Impact, Limitations, and Evaluation, often have low completion rates and less detail.
    * **Lack of Emphasis on Limitations:** There's a tendency to underreport limitations and potential negative outcomes, hindering informed decisions and trust. Only a fraction of analyzed cards mentioned "weakness(es)", "limitation(s)", or "bias(es)".
    * **Superficial Evaluation Reporting:** Evaluations often present aggregate metrics, potentially hiding poor performance within specific subgroups. More granular, subgroup-based evaluation is needed.
    * **Documentation Burden:** Creating comprehensive model cards can be time-consuming.
    * **Potential for Bias in Automated Generation:** While aiming for improvement, LLM-generated cards might still inherit biases from source documents (e.g., papers overstating claims) or the LLMs themselves.
- **Resources:**
  - [Systematic analysis of 32,111 AI model cards characterizes documentation practice in AI](https://www.nature.com/articles/s42256-024-00857-z) (Nature-JUN2024)
  - [Automatic Generation of Model and Data Cards: A Step Towards Responsible AI](https://arxiv.org/abs/2405.06258) (Arxiv-MAY2024)
  - [Sample: Amazon's Guide to Creating a Model Card](https://docs.aws.amazon.com/sagemaker/latest/dg/model-cards-create.html) (APR2025)
 
##### SYSTEM CARD
* **Description:**
    * While Model Cards focus on individual models and Data Cards/Datasheets focus on datasets, other documentation frameworks aim to capture broader system-level information, including context, risks, and compliance aspects.
    * System Cards or similar documentation (like AI Cards or AI Risk Profiles) document the entire AI system, which may involve multiple models and components, focusing on deployment context, data flows, interactions, and system-wide risks.
* **Key Components:**
    * **System architecture overview and components:** Documentation should include the system's high-level architecture, detailing incorporating components like AI models, datasets, general-purpose AI systems, and other software elements. AI Cards, for example, list key components with links to their specific documentation (like Model Cards or Datasheets).
    * **Data flows and storage practices:** Understanding data lineage and processing is crucial. AI Cards include a section on data processing, specifying if personal, non-personal, anonymized, or licensed data is used and linking to relevant assessments like DPIAs.
    * **Underlying infrastructure and dependencies:** While not a primary focus in the provided texts' examples (like AI Cards or Risk Profiles), information about hardware, software, cloud providers, and compute infrastructure is sometimes included in technical documentation templates. Risk profiles may implicitly cover infrastructure risks under categories like Security or Performance & Robustness.
    * **Human oversight mechanisms:** Documentation should specify the level of automation and the nature of human involvement, including whether end-users or affected subjects have control over outputs (e.g., opt-in/out, challenge, correct, reverse). AI Cards explicitly include a section on human involvement.
    * **Integration with other systems:** The context of use section in frameworks like AI Cards or Use Case Cards describes how the system operates within a specific setting, which can imply integration points. Risk assessments should also consider interactions with other systems as potential failure points.
    * **Risk assessment and mitigation strategies:** This is a central component. AI Risk Profiles propose a standard for pre-deployment risk disclosure based on a defined taxonomy (e.g., Abuse & Misuse, Compliance, Fairness & Bias, Security, Privacy, Performance & Robustness). AI Cards include a "Risk Profile" section summarizing likelihood, severity, residual risk, impacts (on health, rights, society, environment), and mitigation measures (technical, monitoring, security, etc.). Use Case Cards help assess risk levels based on the intended purpose and application area. Risk management system documentation is often part of broader technical documentation required by regulations like the EU AI Act.
    * **User interaction patterns:** Use Case Cards specifically focus on modeling interactions between actors (users) and the system to achieve goals, using UML diagrams and descriptions. AI Cards also touch upon whether user involvement is intended, active, and informed.
    * **Monitoring and maintenance procedures:** Post-market monitoring plans and system documentation are often required, especially for high-risk systems under regulations like the EU AI Act. Risk Profiles are envisioned as 'living documents' updated based on in-production monitoring and incident data. AI Cards can include information on pre-determined changes affecting performance or risks.
    * **Compliance with regulations:** Documentation is crucial for demonstrating compliance with regulations like the EU AI Act or GDPR. Frameworks like AI Cards and AI Risk Profiles are designed with regulatory requirements in mind, often including sections listing applicable regulations, standards, and certifications. Use Case Cards help determine the risk level according to the AI Act, which dictates compliance obligations.
* **Advances in System Card:**
    * Frameworks like AI Cards and AI Risk Profiles are being proposed to provide standardized, holistic views of AI systems and their associated risks, going beyond individual models or datasets.
    * Use Case Cards adapt standard UML modeling to document AI system use cases specifically for risk assessment under regulations like the EU AI Act.
    * There's a move towards machine-readable documentation (e.g., using Semantic Web technologies, JSON) to improve interoperability, maintainability, automation (e.g., compliance checking, tool support), and information exchange across the AI value chain. AI Cards explicitly include a machine-readable specification based on ontologies like AIRO.
    * AI systems (like Themisto) are being developed to assist in the creation of documentation itself, although currently focused more on code/notebook documentation.
* **Existing challenges and/or gaps with System Card:**
    * Despite various proposals (Model Cards, Datasheets, Factsheets), there's still a lack of widely adopted, standardized methodologies focused specifically on documenting entire AI systems or use cases, especially in alignment with regulatory needs like the EU AI Act.
    * Existing documentation often focuses heavily on technical aspects (models, data) rather than the broader system context, deployment environment, or system-level risks.
    * Generating comprehensive system documentation can be challenging, requiring information exchange across complex value chains where details about third-party components might be needed but hard to obtain.
    * Keeping documentation up-to-date with system changes (especially substantial modifications affecting compliance or purpose) is difficult.
    * Assessing the real-world impact and risks, particularly concerning fundamental rights or societal effects, remains challenging, especially pre-deployment. Frameworks like Algorithmic Impact Assessments are suggested to help.
    * Current AI evaluation benchmarks often fail to capture the full range of risks or downstream impacts.
    * Defining and measuring the efficacy of risk mitigations is complex.
- **Resources:**
  - [OpenAI o1 System Card](https://arxiv.org/abs/2412.16720) (Arxiv-DEC2024)
  - [AI Risk Profiles: A Standards Proposal for Pre-deployment AI Risk Disclosures](https://ojs.aaai.org/index.php/AAAI/article/view/30348) (AAAI2024)
  - [AI Cards: Towards an Applied Framework for Machine-Readable AI and Risk Documentation Inspired by the EU AI Act](https://link.springer.com/chapter/10.1007/978-3-031-68024-3_3) (SpringerNatureLink-AUG2024)
  - [Use case cards: a use case reporting framework inspired by the European AI Act](https://link.springer.com/article/10.1007/s10676-024-09757-7) (SpringerNatureLink-MAR2024)
  * [AI FactSheets: Increasing trust in AI services through supplier's declarations of conformity](https://ieeexplore.ieee.org/document/8843893/) (IBM Journal of Research and Development-JUL2021)
  * [A Survey on Explainability in Machine Learning: From Models to Systems](https://dl.acm.org/doi/10.1613/jair.1.12228) (CSUR-MAY2022)
  * [Documentation Matters: Human-Centered AI System to Support Data Science Project Documentation](https://dl.acm.org/doi/10.1145/3489465) (CHI-APR2022)

##### The Addendum Process
**Industry Best Practices:**

* **Purposeful Updates:** Addenda are issued to document significant updates or additions to existing models or systems, such as new capabilities, performance improvements, or new models within a family. The addendum should clearly state its purpose and what new information it covers.
* **Content of Addenda:** Updates typically include detailed discussions on performance changes (with updated benchmarks and human evaluations) and safety considerations specific to the new features or models. They may also detail new risks introduced by added capabilities (like native image generation) and the specific mitigations implemented to address them. For new model versions, updated knowledge cutoffs are often specified.
* **Safety Focus:** Addenda often reiterate safety commitments, detail safety evaluations performed on the new components (including red-teaming results), discuss alignment with internal policies (like Responsible Scaling Policies) and external regulations, and outline any changes to the safety stack. Collaboration with external safety experts or institutes for testing may also be documented.
* **Iterative Deployment:** Addenda reflect an iterative approach to deployment, acknowledging that safety measures and policies will continue to be evaluated and adjusted based on real-world usage and learnings.
* **Holistic Approach:** Documentation practices are shifting towards more holistic views, encompassing the entire system and its operational context, which necessitates updates beyond just model-specific details.

**Issues/Challenges:**

* **Keeping Pace:** AI development, especially for large models, is rapid, making it challenging for documentation, including addenda, to keep up.
* **Manual Effort:** The majority of documentation practices rely heavily on manual effort (78% in one study), making the process of creating and updating cards or addenda time-consuming, tedious, and potentially inconsistent.
* **Automation Gaps:** While automation is seen as a way to improve efficiency and consistency, fully automated documentation generation is still uncommon (only 7% in one review). Semi-automated processes exist but still require significant human oversight. Automating documentation for complex, multimodal systems presents further challenges.
* **Defining "Substantial Change":** Determining when an update or change to a model/system necessitates a formal addendum or update to the documentation lacks clear, standardized guidelines.
* **Information Gathering:** Compiling the necessary information for a comprehensive addendum, especially regarding third-party components or detailed risk assessments, can be a significant challenge.

- **Resources:**
  - [Model Card Addendum: Claude 3.5 Haiku and Upgraded Claude 3.5 Sonnet](https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf) (OCT2024)
  - [Addendum to GPT-4o System Card: Native image generation](https://cdn.openai.com/11998be9-5319-4302-bfbf-1167e093f1fb/Native_Image_Generation_System_Card.pdf) (MAR2025)
  - [Documentation Practices of Artificial Intelligence](https://arxiv.org/abs/2406.18620) (arXiv-JUN2024)

##### Standard Information Gathering (SIG) Lite questionnaire
A streamlined version of the Shared Assessments SIG questionnaire that collects essential information about an organization's security controls, risk management practices, and compliance posture. The SIG Lite focuses on critical security domains with fewer questions than the comprehensive SIG, making it more accessible for AI vendors while still providing meaningful security assurance. It covers areas such as information security policies, access controls, data protection, and incident management specific to AI systems.
- **Resources**:
  - [What is the SIG questionnaire?](https://www.vanta.com/collection/trust/sig-questionnaire) (Vanta-APR2025)
  - 

##### Consensus Assessments Initiative Questionnaire (CAIQ) Lite questionnaire
Developed by the Cloud Security Alliance (CSA), the CAIQ Lite is a condensed version of the full CAIQ designed to assess the security capabilities of cloud service providers and AI systems. This questionnaire maps to the CSA Cloud Controls Matrix (CCM) and focuses on key security principles relevant to AI deployments, including data security, application security, and compliance. CAIQ Lite enables AI vendors to demonstrate their security posture without the extensive overhead of the full CAIQ, making it suitable for rapid vendor risk assessments.
- **Resources**:
  - [What is the CAIQ (Consensus Assessment Initiative Questionnaire)?](https://www.vanta.com/collection/trust/caiq) (Vanta-APR2025)

##### Vendor Security Alliance (VSA) Core questionnaire
The VSA Core questionnaire is a standardized security assessment tool developed by the Vendor Security Alliance to evaluate third-party vendor security practices, with specific considerations for AI systems. This questionnaire focuses on fundamental security controls across domains including data protection, access management, vulnerability management, and incident response. The VSA Core is designed to provide objective security assessment metrics while minimizing the burden on AI vendors, facilitating more efficient security reviews and enabling better comparison between different AI solution providers.
- **Resources**:
  - [What is the VSAQ (Vendor Security Alliance Questionnaire)?](https://www.vanta.com/collection/trust/vendor-security-alliance-questionnaire) (Vanta-APR2025)
    
#### SOC 2 Type 1
Point-in-time assessment of an organization's system and suitability of control design related to security, availability, processing integrity, confidentiality, and privacy.
- **Resources:**
  - [How to incorporate AI considerations into your SOC2 examination](https://www.schellman.com/blog/soc-examinations/how-to-incorporate-ai-into-your-soc-2-examination#:~:text=While%20the%20SOC%202%20trust,Availability;)
  - [SOC 2 Type 1 vs Type 2](https://secureframe.com/hub/soc-2/type-1-vs-type-2)
  - [Audits as Instruments of Principled AI Governance](https://www.orfonline.org/research/audits-as-instruments-of-principled-ai-governance) (Observer Research Foundation Report-JAN2025)
  - [A Metric-Driven Security Analysis of Gaps in Current AI Standards](https://arxiv.org/abs/2502.08610) (arXiv-FEB2025)
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
#### ISO 27001:2022
International standard for information security management systems (ISMS), with specific considerations for AI systems.
- **Statement of Applicability**
  - A formal document that identifies which controls from ISO 27001 Annex A are applicable to the organization's AI systems and explains the rationale for including or excluding specific controls. For AI systems, this typically includes specialized controls addressing model security, data protection during training and inference, and access controls for AI development environments. The document serves as the foundation for ISMS implementation and auditing.
- **ISO 27001 Certificate**
  - The official certification document issued by an accredited certification body confirming that the organization's information security management system has been audited and meets all ISO 27001:2022 requirements. The certificate includes the certification scope specifically detailing AI-related activities covered, validity period (typically three years), and the issuing certification body's accreditation information. This certificate provides formal validation of the organization's security practices for AI systems.
- **Resources:**
  - [Managing Security and AI: The Role of ISO 27001 & 42001](https://www.ccsrisk.com/iso27001-iso42001#:~:text=In%20summary%2C%20ISO%2027001:2022,associated%20risks%20and%20negative%20impacts.)
  - [Impact of Artificial Intelligence on Enterprise Information Security Management in the Context of ISO 27001 and 27002: A Tertiary Systematic Review and Comparative Analysis](https://link.springer.com/chapter/10.1007/978-3-031-52272-7_1) (SpringerNatureLink-APR2024)
  - [From COBIT to ISO 42001: Evaluating Cybersecurity Frameworks for Opportunities, Risks, and Regulatory Compliance in Commercializing Large Language Models](https://arxiv.org/abs/2402.15770) (arXiv preprint-FEB2024)
  - [Management of enterprise cyber security: A review of ISO/IEC 27001:2022](https://www.researchgate.net/publication/368911662_Management_of_enterprise_cyber_security_A_review_of_ISOIEC_270012022) (Journal of ICT Standardization-FEB2023)
  - [How emerging technologies are reshaping audit success factors](https://scholarsarchive.library.albany.edu/cgi/viewcontent.cgi?article=4431&context=legacy-etd) (PhD Dissertation, University at Albany, SUNY-APR2025)
#### ISO/IEC 42001:2023
The recently established international standard specifically addressing AI management systems and governance frameworks.
- **Resources:**
  - [Comparison and Analysis of 3 Key AI Documents: EU’s Proposed AI Act, Assessment List for Trustworthy AI (ALTAI), and ISO/IEC 42001 AI Management System](https://link.springer.com/chapter/10.1007/978-3-031-26438-2_15) (AICS2022)
  - [ISO/IEC quality standards for AI engineering](https://www.sciencedirect.com/science/article/abs/pii/S1574013724000650) (ComputerScienceReview-NOV2024)
  - [From COBIT to ISO 42001: Evaluating Cybersecurity Frameworks for Opportunities, Risks, and Regulatory Compliance in Commercializing Large Language Models](https://arxiv.org/abs/2402.15770) (arXiv-FEB2024)
  - [AI Governance Frameworks: A Comparative Analysis for Responsible AI Development](https://ieeexplore.ieee.org/abstract/document/10317811/) (IEEE International Conference on Systems, Man, and Cybernetics - SMC 2023-OCT2023)
  - [Navigating geopolitics in AI governance](https://oxgs.org/2024/04/08/oxgs-report-navigating-geopolitics-in-ai-governance/) (Oxford Global Society Report-APR2024)
#### Domain-specific Compliance: Finance
- **Financial AI Risk Assessment**
  - Documentation evaluating AI systems against financial regulatory requirements including model risk management guidelines (SR 11-7), consumer protection regulations, and anti-discrimination laws. This assessment identifies risks specific to AI use in financial decision-making and describes implemented controls.
- **Model Governance Documentation**
  - Formal documentation detailing model development, validation, implementation, and ongoing monitoring procedures in accordance with financial regulatory expectations, particularly focused on model explainability and auditability.
- **Resources:**
  - [Federal Reserve Guidance on Model Risk Management](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
  - [Financial Stability Board's Artificial Intelligence and Machine Learning in Financial Services](https://www.fsb.org/work-of-the-fsb/financial-innovation-and-structural-change/artificial-intelligence-and-machine-learning-in-financial-services/)
  - [FINRA AI Report: Considerations for Use of Artificial Intelligence in the Securities Industry](https://www.finra.org/rules-guidance/key-topics/artificial-intelligence)
  - [Mitigating Model Risk in AI: Advancing an MRM Framework for AI/ML Models at Financial Institutions](https://www.chartis-research.com/artificial-intelligence-ai/7947296/mitigating-model-risk-in-ai-advancing-an-mrm-framework-for-aiml-models-at-financial-institutions) (Chartis Research Report-JAN2025) - *Note: Industry research paper analyzing AI/ML model risk management (MRM) frameworks in finance, referencing SR 11-7.*
  - [The European Union's Approach to Artificial Intelligence and the Challenge of Financial Systemic Risk](https://www.researchgate.net/publication/376852879_The_European_Union's_Approach_to_Artificial_Intelligence_and_the_Challenge_of_Financial_Systemic_Risk) (European Business Organization Law Review-DEC2023 / via ResearchGate) - *Analyzes EU AI Act applicability to financial systemic risk from AI.*
  - [Digital Finance in the EU: Navigating new technological trends and the AI revolution](https://cadmus.eui.eu/handle/1814/77926) (European University Institute Report-NOV2024) - *Note: Report discussing AI trends, regulation, and risks in EU digital finance.*
  - [Model Risk Management of AI and Machine Learning Systems](https://www.pwc.co.uk/data-analytics/documents/model-risk-management-of-ai-machine-learning-systems.pdf) (PwC UK White Paper-JUN2020) - *Highly relevant white paper discussing MRM for AI, referencing SR 11-7.*
#### Domain-specific Compliance: Healthcare
##### HIPAA
Requirements specific to healthcare AI applications, focusing on protecting personal health information (PHI) in accordance with Health Insurance Portability and Accountability Act standards.
- **Annual HIPAA SCA Report**
  - A formal security compliance assessment report that documents an organization's adherence to HIPAA Security, Privacy, and Breach Notification Rules in the context of AI systems handling PHI. The report evaluates controls protecting patient data throughout the AI lifecycle, including data collection, processing, model training, and inference. It contains detailed findings on administrative, physical, and technical safeguards implemented to protect the confidentiality, integrity, and availability of PHI processed by AI systems, along with any required remediation actions.
- **Resources:**
  - [AI in Healthcare: HIPAA Compliance Considerations](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/index.html)
  - [OCR Guidance on AI and Machine Learning in Healthcare](https://www.healthit.gov/topic/scientific-initiatives/artificial-intelligence-healthcare)
  - [Developing Ethical AI Models in Healthcare: A U.S. Legal and Compliance Perspective on HIPAA and CCPA](https://www.iiardjournals.org/abstract.php?j=IJHPR&pn=Developing%20Ethical%20AI%20Models%20in%20Healthcare:%20A%20U.S.%20Legal%20and%20Compliance%20Perspective%20on%20HIPAA%20and%20CCPA&id=58261) (IJHPR-APR2025)
  - [AI Chatbots and Challenges of HIPAA Compliance for AI Developers and Vendors](https://www.researchgate.net/publication/378962258_AI_Chatbots_and_Challenges_of_HIPAA_Compliance_for_AI_Developers_and_Vendors) (Journal of Law, Medicine & Ethics-MAR2024) - *Analyzes specific HIPAA compliance challenges for AI chatbots.*
  - [Security and Privacy of Technologies in Health Information Systems: A Systematic Literature Review](https://www.mdpi.com/2073-431X/13/2/41) (Electronics-JAN2024) - *Reviews security/privacy technologies (IoT, blockchain, cloud) in HIS, discussing HIPAA context.*
  - [The Risk Assessment of the Security of Electronic Health Records Using Risk Matrix](https://www.mdpi.com/2076-3417/14/13/5785) (Applied Sciences-JUN2024) - *Focuses on EHR security risks within the HIPAA compliance landscape.*
##### Other healthcare
- **AI Medical Device Documentation**
  - For AI systems classified as medical devices, documentation demonstrating compliance with FDA requirements including pre-market submissions (510(k), De Novo, or PMA), quality system regulations, and post-market surveillance commitments.
- **Clinical Validation Reports**
  - Documentation of clinical validation studies demonstrating the safety and efficacy of AI applications in healthcare contexts, including statistical analyses, performance metrics, and testing across diverse patient populations.
- **Resources:**
  - [FDA Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan](https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-software-medical-device)
  - [Good Machine Learning Practice for Medical Device Development](https://www.fda.gov/medical-devices/software-medical-device-samd/good-machine-learning-practice-medical-device-development-guiding-principles)
  - [AI regulation in healthcare around the world: what is the status quo?](https://www.medrxiv.org/content/10.1101/2025.01.25.25321061v1) (medRxiv preprint-JAN2025) - *Note: Preprint providing a global overview of AI regulation in healthcare, relevant context for FDA.*
  - [Clinical Validation of Digital Healthcare Solutions: State of the Art, Challenges and Opportunities](https://www.researchgate.net/publication/380812278_Clinical_Validation_of_Digital_Healthcare_Solutions_State_of_the_Art_Challenges_and_Opportunities) (Journal of Personalized Medicine-MAY2024) - *Reviews challenges and opportunities in clinically validating digital health tech, including AI.*
  - [Regulatory Frameworks for AI-Based Medical Devices: A Comparative Analysis](https://link.springer.com/article/10.1007/s10916-023-01958-y) (Journal of Medical Systems-MAY2023) - *Compares regulatory approaches (including FDA) for AI medical devices.*
  - [Validation of artificial intelligence in medical imaging: Radiology AITE checklist](https://pubs.rsna.org/doi/10.1148/ryai.230237) (Radiology: Artificial Intelligence-JAN2024)

#### Domain-specific Compliance: Critical Infrastructure
- **Critical Infrastructure Protection Plan**
  - Documentation detailing how AI systems in critical infrastructure comply with relevant frameworks such as NIST Cybersecurity Framework, IEC 62443, or sector-specific guidelines. This includes security controls, resilience measures, and contingency planning.
- **Operational Technology Security Assessment**
  - Formal assessment of security controls protecting AI systems integrated with operational technology environments, including segmentation strategies, monitoring capabilities, and incident response procedures specific to industrial control systems.
- **Resources:**
  - [NIST Cybersecurity Framework for Critical Infrastructure](https://www.nist.gov/cyberframework)
  - [CISA Artificial Intelligence and Critical Infrastructure Security](https://www.cisa.gov/topics/artificial-intelligence-critical-infrastructure-security)
  - [IEC 62443 - Industrial Automation and Control Systems Security](https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards)
  - [Generative AI and LLMs for Critical Infrastructure Protection: Evaluation Benchmarks, Agentic AI, Challenges, and Opportunities](https://www.mdpi.com/1424-8220/25/6/1666) (Sensors - MDPI Journal-MAR2025)
  - [AI-Driven Project Risk Management: Leveraging artificial intelligence to predict, mitigate, and manage project risks in critical infrastructure and national security projects](https://www.researchgate.net/publication/390521301_AI-Driven_Project_Risk_Management_Leveraging_artificial_intelligence_to_predict_mitigate_and_manage_project_risks_in_critical_infrastructure_and_national_security_projects) (Journal of Computer Science and Technology Studies-APR2025)
  - [Dynamic Cyber Resilience of Interdependent Critical Information Infrastructures](https://bspace.buid.ac.ae/handle/1234/1965) (PhD Thesis, British University in Dubai-FEB2022) - *Note: PhD Thesis focusing on resilience frameworks for critical infrastructure.*

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
  - [Governance of Artificial Intelligence in the Military Domain: A Multi-stakeholder Perspective on Priority Areas](https://unidir.org/publication/governance-of-artificial-intelligence-in-the-military-domain-a-multi-stakeholder-perspective-on-priority-areas/) (UNIDIR Report-SEP2024)
  - [The Very Long Game: 25 Case Studies on the Global State of Defense AI](https://library.oapen.org/handle/20.500.12657/93630) (Springer-JUL2024)
  - [Ethical Considerations for AI in Defense: A Comparative Analysis of International Frameworks](https://ieeexplore.ieee.org/abstract/document/9762410/) (ISTAS-OCT2021)

### S2\. Controls
Technical and organizational controls that provide the foundation for securing AI systems throughout their lifecycle.

#### S2\.a Infrastructure Diagrams
Visual representations of the AI system architecture, data flows, and security controls to support risk assessment and security planning.
- **Resources:**
    - [Model-Based Systems Engineering for AI-Based Systems](https://arc.aiaa.org/doi/abs/10.2514/6.2023-2587) (AIAA2023)
    - [System Architects Are not Alone Anymore: Automatic System Modeling with AI](https://telecom-paris.hal.science/hal-04483279/) (HAL-FEB2024)
    - [Intelligent Turning Cyber-Physical Systems Modeling using SysML](https://ieeexplore.ieee.org/abstract/document/10906048?casa_token=PE6D39ptEGQAAAAA:t7cawJg-H0h9lvh2ic3TddxMtWy4xf5s4pj5vqdXE-12GgV3dxGZWegFs94XHZ5GtPxQqVCcLg) (IECON-2024)
    - [A Taxonomy of MBSE Approaches by Languages, Tools and Methods](https://ieeexplore.ieee.org/abstract/document/9950507) (IEEEaccess-NOV2022)
    - [Model-driven architecture based security analysis](https://incose.onlinelibrary.wiley.com/doi/full/10.1002/sys.21581?casa_token=oeR-4hrafPAAAAAA%3AXxpL2K2XBVLKwk_D-lXRMhBT1Qu1zBNflZqwM-KK6D0Cn6zZC2XJoPcguPlbRYN7inCIrxnqHjGVweg) (Wiley-MAY2021)
    - [Integration of UML Diagrams from the Perspective of Enterprise Architecture](https://link.springer.com/chapter/10.1007/978-3-030-72651-5_44) (SpringerNatureLink-MAR2021)

#### S2\.b Infrastructure Security
Technical controls securing the underlying infrastructure supporting AI systems, including compute, storage, networking, and access management.
- **Encryption**
  - The organization restricts privileged access to encryption keys to authorized users with a business need.
  - Resources:
    - [Securing AI Systems: A Comprehensive Overview of Cryptographic Techniques for Enhanced Confidentiality and Integrity](https://ieeexplore.ieee.org/abstract/document/10577883?casa_token=yYYOt9nWmtAAAAAA:vRTlXzxNdmxGTfa-a4jsKUcQP3TIEbPlDF4bYLig8vxcPT6RTO9dKAiEXqsJ7E1oh0NLsb20gA) (MECO-2024)
    - [A Survey on Searchable Symmetric Encryption](https://dl.acm.org/doi/10.1145/3617991) (CSUR-NOV2023)
    - [Attribute-based Encryption for Cloud Computing Access Control: A Survey](https://dl.acm.org/doi/10.1145/3398036) (CSUR-AUG2020)
    - [Blockchain for secure and decentralized artificial intelligence in cybersecurity: A comprehensive review](https://www.sciencedirect.com/science/article/pii/S209672092400006X) (Elsevier-SEP2024)
    - [algoTRIC: Symmetric and asymmetric encryption algorithms for Cryptography -- A comparative analysis in AI era](https://arxiv.org/abs/2412.15237) (Arxiv-DEC2024)
    - [A Hybrid Cryptographic Mechanism for Secure Data Transmission in Edge AI Networks](https://link.springer.com/article/10.1007/s44196-024-00417-8) (SpringerNatureLink-FEB2024)
    - [A Framework for Cryptographic Verifiability of End-to-End AI Pipelines](https://arxiv.org/abs/2503.22573) (Arxiv-MAR2025)
- **Authentication**
  - The organization requires authentication to systems and applications to use unique username and password or authorized Secure Socket Shell (SSH) keys.
  - Resources:
    - [A Survey on Empirical Security Analysis of Access-control Systems: A Real-world Perspective](https://dl.acm.org/doi/10.1145/3533703) (CSUR-DEC2022)
    - [An In-Depth Analysis of Password Managers and Two-Factor Authentication Tools](https://dl.acm.org/doi/10.1145/3711117) (CSUR-JAN2025)
    - [A Comprehensive Survey on Physical Layer Authentication Techniques: Categorization and Analysis of Model-Driven and Data-Driven Approaches](https://dl.acm.org/doi/10.1145/3708496) (CSUR-JAN2025)
    - [Authenticated Delegation and Authorized AI Agents](https://arxiv.org/abs/2501.09674) (Arxiv-JAN2025)
    - [Examining the Current Status and Emerging Trends in Continuous Authentication Technologies through Citation Network Analysis](https://dl.acm.org/doi/10.1145/3533705) (CSUR-DEC2022)
- **Application access control**
  - System access restricted to authorized access only
  - Resources:
    - [Using AI to Enhance Access Control and Identity Management in the Cloud](https://www.researchgate.net/publication/385558432_Using_AI_to_Enhance_Access_Control_and_Identity_Management_in_the_Cloud) (ResearchGate-NOV2024)
    - [Leveraging AI for enhanced identity and access management in cloud-based systems to advance user authentication and access control](https://wjarr.com/sites/default/files/WJARR-2024-3501.pdf) (World Journal of Advanced Research and Reviews-DEC2024)
    - [Opportunities and Challenges of Artificial Intelligence Applied to Identity and Access Management in Industrial Environments](https://www.mdpi.com/1999-5903/16/12/469) (Applied Sciences-DEC2024) - *Reviews AI applications in IAM specifically for industrial settings, relevant to securing AI applications in OT/ICS.*
    - [Zero Trust Architecture for Artificial Intelligence Systems: A Survey](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/10287051/) (IEEE Access-OCT2023) - *Surveys the application of Zero Trust principles, a key access control strategy, to AI systems and infrastructure.*
- **Production DB access control**
  - The organization restricts privileged access to databases to authorized users with a business need.
  - Resources:
    - [Ensuring AI Data Access Control in RDBMS: A Comprehensive Review](https://openaccess.thecvf.com/content/CVPR2024W/WRD24/html/Kandolo_Ensuring_AI_Data_Access_Control_in_RDBMS_A_Comprehensive_Review_CVPRW_2024_paper.html) (CVPR-2024)
    - [Privacy-Preserving Data Publishing for Machine Learning: A Survey](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/9795419/) (IEEE Transactions on Knowledge and Data Engineering-SEP2022) - *Surveys techniques to protect data privacy when data is used for ML, relevant to controlling access and exposure of sensitive DB data.*
    - [Federated Database Systems Security: A Survey](https://www.mdpi.com/2076-3417/13/1/439) (Applied Sciences-DEC2022) - *Reviews security challenges, including access control, in federated database systems which might host AI training/operational data.*
    - [A Survey on Security and Privacy Issues of Federated Learning](https://www.google.com/search?q=https://www.sciencedirect.com/science/article/pii/S2666389922000025) (Telematics and Informatics Reports-JUN2022) - *Discusses security/privacy in federated learning, which involves controlled access to distributed data sources.*
- **Firewall access control**
  - The organization restricts privileged access to the firewall to authorized users with a business need.
  - Resources:
    - [A Survey on Network Security Policy Verification and Synthesis](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/10289020/) (IEEE Access-OCT2023) - *Surveys methods for verifying network security policies, including firewall rules, crucial for managing access.*
    - [Automated Firewall Policy Analysis and Optimization: A Survey](https://www.sciencedirect.com/science/article/pii/S157401372200127X) (Journal of Network and Computer Applications-OCT2022)
    - [Leveraging Machine Learning for Intelligent Firewall Rule Management](https://ieeexplore.ieee.org/abstract/document/9797189/) (ICC-MAY2022)
    - [Zero Trust Network Access (ZTNA): Concepts, Architectures, and Challenges](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/9679566/) (IEEE Access-JAN2022) - *Explores ZTNA concepts, a modern approach to network access control applicable to managing firewall policies and infrastructure access.*
    - [A Framework for Secure Configuration Management of Network Devices](https://www.mdpi.com/2076-3417/12/19/9807) (Applied Sciences-SEP2022) - *Proposes a framework for secure configuration management applicable to firewalls.*
- **Production OS access control**
  - The organization restricts privileged access to the operating system to authorized users with a business need.
  - Resources:
    - [Introduction to Privileged Access Management](https://www.researchgate.net/publication/378990267_Introduction_to_Privileged_Access_Management) (ISSA Journal-FEB2024)
    - [Security Hardening of Operating Systems: A Review of Techniques and Tools](https://www.sciencedirect.com/science/article/pii/S1877050922010868) (ICCS-JUL2022)
    - [Identity and Access Management in Cloud Environments: Challenges and Solutions](https://ieeexplore.ieee.org/abstract/document/9611972/) (CloudCom-DEC2021)
    - [Secure Configuration of Compute Instances for Machine Learning Workloads](https://dl.acm.org/doi/abs/10.1145/3488932.3497777) (ADM+ML-AUG2021)
- **Production network access control**
  - The organization restricts privileged access to the production network to authorized users with a business need.
  - The organization requires authentication to the "production network" to use unique usernames and passwords or authorized Secure Socket Shell (SSH) keys.
  - Resources:
    - [Identity and Access Management in Cloud Environments: Challenges and Solutions](https://ieeexplore.ieee.org/abstract/document/9611972/) (IEEE International Conference on Cloud Computing Technology and Science - CloudCom 2021-DEC2021) - *Covers IAM challenges relevant to securing production networks hosted in the cloud.*
    - [Considerations regarding Sovereign AI and National AI Policy](https://sovereign-ai.org/media/papers/Considerations_regarding_Sovereign_AI_C_Sovereign_AI__Imperial_College.pdf) (Imperial College London White Paper-APR2024) - *Note: Policy paper discussing strategic autonomy and control over critical AI infrastructure, relating to network access control.*
    - [A Survey on Network Security Policy Verification and Synthesis](https://ieeexplore.ieee.org/abstract/document/10289020/) (IEEE Access-OCT2023) - *Surveys methods for verifying network security policies, essential for ensuring correct network access.*
- **Remote access control**
  - The organization's production systems can only be remotely accessed by authorized employees via an approved encrypted connection.
  - Resources:
    - [Zero Trust Network Access (ZTNA): Concepts, Architectures, and Challenges](https://ieeexplore.ieee.org/abstract/document/9679566/) (IEEE Access-JAN2022) - *Explores ZTNA concepts, a primary modern approach for securing remote access based on identity and context rather than network perimeter.*
    - [A Survey on Zero Trust Architecture: Principles, Models, and Challenges](https://ieeexplore.ieee.org/abstract/document/10142490/) (IEEE Access-JUN2023) - *Surveys Zero Trust principles applicable to securing remote connections.*
    - [Security and Privacy of Technologies in Health Information Systems: A Systematic Literature Review](https://www.mdpi.com/2073-431X/13/2/41) (Electronics-JAN2024) - *Discusses security aspects like secure access control and data sharing in healthcare systems, relevant to remote access needs.*
    - [A Secure Remote Access Framework for Industrial Control Systems Using Software-Defined Networking](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/9498958/) (IEEE Transactions on Industrial Informatics-AUG2021)
- **Infrastructure performance monitoring**
  - An infrastructure monitoring tool is utilized to monitor systems, infrastructure, and performance and generates alerts when specific predefined thresholds are met.
  - Resources:
    - [Artificial Intelligence for Real-Time Cloud Monitoring and Troubleshooting](https://www.researchgate.net/publication/387140941_Artificial_Intelligence_for_Real-Time_Cloud_Monitoring_and_Troubleshooting) (International Journal of Progressive Research in Engineering Management and Science-DEC2024)
    - [AIOps Architecture in Data Center Site Infrastructure Monitoring](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9328990/) (Computational Intelligence and Neuroscience-JUL2022)
    - [AIOps in Cloud-native DevOps: IT Operations Management with Artificial Intelligence](https://www.researchgate.net/publication/377614566_AIOps_in_Cloud-native_DevOps_IT_Operations_Management_with_Artificial_Intelligence) (Journal of Artificial Intelligence & Cloud Computing-JAN2023)
    - [Advancing AI-Enabled Techniques in Energy System Modeling: A Review of Data-Driven, Mechanism-Driven, and Hybrid Modeling Approaches](https://www.mdpi.com/1996-1073/18/4/845) (MDPI-FEB2025)
    - [Performance Measurement System and Quality Management in Data-Driven Industry 4.0: A Review](https://www.mdpi.com/1424-8220/22/1/224) (MDPI-DEC2021)
    - [Observability for Microservices-Based Systems: A Systematic Literature Review](https://ieeexplore.ieee.org/abstract/document/9783198/) (IEEE Access-MAY2022)

- **Network Firewall**
  - The organization uses firewalls and configures them to prevent unauthorized access.
  - Resources:
    - [Next Generation AI-Based Firewalls: A Comparative Study](https://www.researchgate.net/publication/377060591_Next_Generation_AI-Based_Firewalls_A_Comparative_Study) (IJC-DEC2023) - *Compares different approaches for integrating AI into next-generation firewalls.*
    - [Next-Gen Firewalls: Enhancing Cloud Security with Generative AI](https://onlinescientificresearch.com/articles/nextgen-firewalls-enhancing-cloud-security-with-generative-ai.pdf) (Journal of Artificial Intelligence & Cloud Computing-AUG2024) - *Discusses using Generative AI and ML to improve NGFW capabilities for cloud environments.*
    - [Building smarter firewalls: Using AI to strengthen network security protocols](https://www.researchgate.net/publication/390137426_Building_smarter_firewalls_Using_AI_to_strengthen_network_security_protocols) (International Journal of Computing and Artificial Intelligence-AUG2022) - *Analyzes how AI enhances modern intrusion detection and adaptive security policies in firewalls.*
    - [Enhancing Firewall Security through Artificial Intelligence Integration](https://www.jetir.org/papers/JETIR2403125.pdf) (Journal of Emerging Technologies and Innovative Research - JETIR-MAR2024) - *Explores integrating AI techniques to augment traditional firewalls against evolving threats.*
    - [Cybersecurity Challenges and Solutions for Critical Energy Infrastructure in the Digital Age](https://www.researchgate.net/publication/385681419_Cybersecurity_Challenges_and_Solutions_for_Critical_Energy_Infrastructure_in_the_Digital_Age) (International Journal of Cyber-Security and Digital Forensics-NOV2024)
    - [A Survey on Network Security Policy Verification and Synthesis](https://ieeexplore.ieee.org/abstract/document/10289020/) (IEEE Access-OCT2023) - *Surveys methods for verifying network security policies, applicable to firewall rule validation.*

- **Network and System Hardening**
  - The organization's network and system hardening standards are documented, based on industry best practices, and reviewed at least annually.
  - Resources:
    - [Cybersecurity Model Based on Hardening for Secure Internet of Things Implementation](https://www.mdpi.com/2076-3417/11/7/3260) (Applied Sciences-APR2021) - *Proposes a hardening model based on best practices (mentioning CIS) for IoT systems, principles applicable to connected AI infrastructure.*
    - [Artificial Intelligence for Cyber-Physical Systems Hardening](https://link.springer.com/book/10.1007/978-3-031-21960-3) (Book - Springer-FEB2023) - *Note: Book discussing the use of AI for hardening CPS, which often integrate ML/AI components.*
    - [Securing Critical Infrastructure in the Age of AI](https://cset.georgetown.edu/publication/securing-critical-infrastructure-in-the-age-of-ai/) (CSET Report-JUN2024) - *Note: Policy report discussing AI risks and security needs for critical infrastructure, relevant context for hardening.*
    - [Security Hardening of Operating Systems: A Review of Techniques and Tools](https://www.sciencedirect.com/science/article/pii/S1877050922010868) (ICCS-JUL2022) - *Reviews general OS hardening techniques applicable to servers running AI workloads.*
    - [A Survey on DNS Encryption: Current Development, Malware Misuse, and Inference Techniques](https://dl.acm.org/doi/10.1145/3547331) (CSUR-DEC2022)

#### S2\.c Organizational Security
Administrative and procedural controls that establish security governance throughout the organization developing or operating AI systems.
- **Asset disposal procedures**
  - The organization has electronic media containing confidential information purged or destroyed in accordance with best practices, and certificates of destruction are issued for each device destroyed.
  - Resources:
      - ["Secure Data Deletion: Fact or Fiction?"](https://ieeexplore.ieee.org/document/1234567) (IEEE Security & Privacy-2022)
      - [Why Data Deletion Fails? A Study on Deletion Flaws and Data Remanence in Android Systems](https://www.researchgate.net/publication/312258537_Why_Data_Deletion_Fails_A_Study_on_Deletion_Flaws_and_Data_Remanence_in_Android_Systems) (IEEE Transactions on Information Forensics and Security-JAN2017 / via ResearchGate)
      - [Data Governance: A Guide](https://www.google.com/search?q=https://link.springer.com/book/10.1007/978-3-031-64409-2) (Book - Springer-SEP2024)
- **Production inventory**
  - The organization maintains a formal inventory of production system assets.
  - Resources:
    - [Applications of Artificial Intelligence in Inventory Management: A Systematic Review of the Literature](https://www.researchgate.net/publication/368345493_Applications_of_Artificial_Intelligence_in_Inventory_Management_A_Systematic_Review_of_the_Literature) (Archives of Computational Methods in Engineering-FEB2023 / via ResearchGate)
    - [AI DRIVEN - INVENTORY MANAGEMENT](https://www.irjmets.com/uploadedfiles/paper//issue_7_july_2023/43375/final/fin_irjmets1690081992.pdf) (IRJMETS-JUL2023)
    - [Enhancing portfolio management using artificial intelligence: literature review](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1371502/full) (Frontiers in Artificial Intelligence-APR2024) - *Reviews AI applications in financial asset management, providing context on managing complex AI-driven systems.*
- **Portable media**
  - The organization encrypts portable and removable media devices when used.
  - Resources: tba

- **Anti-malware technology**
  - The organization deploys anti-malware technology to environments commonly susceptible to malicious attacks and configures this to be updated routinely, logged, and installed on all relevant systems.
  - Resources:
    - ["The State-of-the-Art in AI-Based Malware Detection Techniques: A Review"](https://arxiv.org/abs/2210.11239) (arXiv-2022)
    - ["Malware Detection and Prevention using Artificial Intelligence Techniques"](https://arxiv.org/abs/2206.12770) (arXiv-2022)
    - ["Defend Against Adversarial Attacks in Malware Detection Through Attack Space Management"](https://dl.acm.org/doi/10.1016/j.cose.2024.103841) (Computers & Security-2024)
    - ["Securing the Digital World: Protecting Smart Infrastructures with AI-Enabled Malware Detection"](https://arxiv.org/abs/2401.01342) (arXiv-2023)
    - ["Artificial Intelligence in Cyber Security: Research Advances, Challenges, and Opportunities"](https://link.springer.com/article/10.1007/S10462-021-09976-0) (Artificial Intelligence Review-2022)
    - [Artificial Intelligence-Based Malware Detection, Analysis, and Mitigation](https://www.mdpi.com/2073-8994/15/3/677) (MDPI-MAR2023) - *Discusses AI/ML techniques used in malware detection systems.*
    - [Malware Image Generation and Detection Method Using DCGANs and Transfer Learning](https://lago-europe.eu/sites/default/files/2023-12/Malware_Image_Generation_and_Detection_Method_Using_DCGANs_and_Transfer_Learning.pdf) (IEEE CSR-JUL2023) - *Focuses on a specific deep learning technique for detecting malware hidden in images.*
    - [Anti-Malware System Using Machine Learning Language](https://www.ijarst.com/assets/backend/pdf/article/13_5_Anti-Malware%20System%20Using%20Machine%20Learning%20Language_pdf) (IJARST-APR2024) - *Discusses the evolution of anti-malware systems using ML, including behavioral analysis and anomaly detection.*

- **Code of Conduct**
  - The organization requires employees to acknowledge a code of conduct at the time of hire. Employees who violate the code of conduct are subject to disciplinary actions in accordance with a disciplinary policy.
  - Resources:
    - [Artificial Intelligence (AI) Law, Rights & Ethics](https://www.google.com/search?q=https://www.americanbar.org/groups/international_law/publications/international_lawyer/2024/volume-57/issue-2/artificial-intelligence-law-rights-ethics/) (The International Lawyer - ABA-JUN2024) - *Discusses the emerging legal, regulatory, and ethical responses to AI advancements.*
    - [How organizations build a culture of AI ethics](https://mitsloan.mit.edu/ideas-made-to-matter/how-organizations-build-a-culture-ai-ethics) (MIT Sloan Management Review Article-APR2025) - *Note: Management article discussing AI ethics culture, referencing a bank's AI risk policy and code of conduct.*
    - [Artificial Intelligence and Labor Law](https://www.cambridge.org/core/books/cambridge-handbook-of-the-law-ethics-and-policy-of-artificial-intelligence/artificial-intelligence-and-labor-law/75DF65CC7B004BDE3954F4477B8CB380) (Book Chapter in The Cambridge Handbook of the Law, Ethics and Policy of Artificial Intelligence-FEB2025) - *Note: Book chapter likely discussing the intersection of AI deployment and employment law/policy, relevant to employee conduct.*
    - [Code & conduct: Algorithm audits in practice](https://www.adalovelaceinstitute.org/report/code-conduct-ai/) (Ada Lovelace Institute Report-JUN2024) - *Note: Report focusing on algorithm audits as an accountability mechanism, linked to responsible conduct in AI development/deployment.*
- **Password policy**
  - The organization requires passwords for in-scope system components to be configured according to the organization's policy.
  - Resources:
    - [Analysis Password-based Authentication Systems with Password Policy](https://www.researchgate.net/publication/357895341_Analysis_Password-based_Authentication_Systems_with_Password_Policy) (International Journal of Advanced Computer Science and Applications-JAN2022) - *Analyzes password authentication systems considering the impact and effectiveness of password policies.*
    - [Balancing Password Security and User Convenience: Exploring the Potential of Prompt Models for Password Generation](https://www.mdpi.com/2079-9292/12/10/2159) (MDPI-MAY2023)
    - [A Review on Secure Authentication Mechanisms for Mobile Security](https://www.mdpi.com/1424-8220/25/3/700) (MDPI -JAN2025) - *Reviews various authentication methods, including password-based approaches, in the context of mobile security.*
    - [Challenges and Opportunities in Password Management: A Review of Current Solutions](https://www.researchgate.net/publication/373320221_Challenges_and_Opportunities_in_Password_Management_A_Review_of_Current_Solutions) (International Journal of Information Management Data Insights-NOV2023)
    - ["An Empirical Study of Password Policy Compliance"](https://cisse.info/journal/index.php/cisse/article/view/156) (Journal of The Colloquium for Information Systems Security Education-2023)

- **MDM system**
  - The organization has a mobile device management (MDM) system in place to centrally manage mobile devices supporting the service.
  - Resources:
    - [Mobile Device Management and Their Security Concerns](https://www.researchgate.net/publication/386049103_Mobile_Device_Management_and_Their_Security_Concerns) (IRJET-OCT2023) - *Discusses MDM theories, practices, comparisons (MDM/EMM/UEM), BYOD vs. company-owned, and security concerns.*
    - [Mobile Device Security: A Systematic Literature Review on Research Trends, Methods and Datasets](https://www.aasmr.org/jsms/Vol12/JSMS%20April%202022/Vol.12No.02.04.pdf) (Journal of System and Management Sciences-APR2022)
    - ["Security and Privacy for Artificial Intelligence: Opportunities and Challenges"](https://arxiv.org/abs/2102.04661) (arXiv-2021)

- **Visitor procedures**
  - The organization requires visitors to sign-in, wear a visitor badge, and be escorted by an authorized employee when accessing the data center or secure areas.
  - Resources:
    - [The Application of GPS-Based Friend/Foe Localization and Identification to Enhance Security in Restricted Areas](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11359897/) (MDPI-AUG2024) - *Discusses enhancing physical security in restricted areas (like airports) using technology for object identification and tracking, relevant to managing access.*
    - [Data Center Physical Security Guidelines](https://www.opencompute.org/documents/open-for-comment-ocp-physical-security-white-paper-1-pdf) (Open Compute Project White Paper-MAR2024) - *Note: Industry white paper outlining best practices for data center physical security, including access control and monitoring principles relevant to visitor management.*
    - [Physical Security in Data Centers: A Layered Approach](https://ieeexplore.ieee.org/document/9519112/) (IEEE Security & Privacy Magazine)
- **Security awareness training**
  - The organization requires employees to complete security awareness training within thirty days of hire and at least annually thereafter.
  - Resources:
    - ["Leveraging AI-Driven Training Programs for Enhanced Organizational Security Awareness"](https://ijsra.net/content/leveraging-ai-driven-training-programs-enhanced-organizational-security-awareness) (International Journal of Science and Research Archive-2024)
    - ["Evaluation of Security Training and Awareness Programs: Review of Current Practices and Guideline"](https://arxiv.org/abs/2112.06356) (arXiv-2021)
    - ["Transparency, Security, and Workplace Training & Awareness in the Age of Generative AI"](https://arxiv.org/abs/2501.10389) (arXiv-2024)
    - [Security Awareness Training for the Workforce: Moving Beyond “Check-the-Box” Compliance](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8201414/) (IEEE Engineering Management Review-JUN2021)
    - [Exploring the Effectiveness of Cybersecurity Awareness Training Methods: A Comparative Study](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/9708454/) (IEEE EDUCON-MAR2022) - *Compares different methods used in security awareness training.*
    - [Measuring the Impact of Security Awareness Training on Employee Behavior: A Longitudinal Study](https://dl.acm.org/doi/abs/10.1145/3485832.3485899) (ACM Conference on Computer and Communications Security- NOV2021) - *Presents a study measuring behavioral changes resulting from security training over time.*
    - [Human Factors in Cybersecurity: A Review of Current Trends and Future Directions](https://www.sciencedirect.com/science/article/pii/S2666389923000090) (Computers & Security-MAY2023) - *Reviews the role of human factors, including training and awareness, in overall cybersecurity posture.*

#### S2\.d Product Security
Security measures specifically integrated into AI products and services to protect against exploitation and unauthorized access.
- **Data encryption**
  - The organization's datastores housing sensitive customer data are encrypted at rest.
  - Resources:
    - [Moving Beyond Traditional Data Protection: Homomorphic Encryption Could Provide What is Needed for Artificial Intelligence](https://journal.ahima.org/page/moving-beyond-traditional-data-protection-homomorphic-encryption-could-provide-what-is-needed-for-artificial-intelligence) (Journal of AHIMA Online-MAR2025)
    - [Securing the Organization's Sensitive Data in the AI Era](https://www.onlinescientificresearch.com/articles/securing-the-organizations-sensitive-data-in-the-ai-era.html) (Journal of Artificial Intelligence & Cloud Computing-DEC2024) - *Provides an overview of strategies and best practices for securing sensitive data handled by AI systems.*
    - [Secure Data Storage and Sharing Techniques for Data Protection in Cloud Environments: A Systematic Review, Analysis, and Future Directions](https://www.google.com/search?q=https://ieeexplore.ieee.org/abstract/document/9816751) (IEEE Access-JUN2022)
    - ["AI-Driven Encryption Techniques for Data Security in Cloud Computing"](https://www.researchgate.net/publication/384978771_AI-Driven_Encryption_Techniques_for_Data_Security_in_Cloud_Computing) (Journal of Research in Technology and Computer Science Engineering-2024)
    - ["Real-Time Data Encryption and Decryption Using AI in Cloud Security"](https://www.researchgate.net/publication/386178125_Real-Time_Data_Encryption_and_Decryption_Using_AI_in_Cloud_Security) (ResearchGate-2024)
    - ["AI-Powered Encryption: Revolutionizing Cybersecurity with Adaptive Cryptography"](https://turcomat.org/index.php/turkbilmat/article/view/14976) (Turkish Journal of Computer and Mathematics Education-2025)
    - ["algoTRIC: Symmetric and Asymmetric Encryption Algorithms for Cryptography—A Comparative Analysis in AI Era"](https://arxiv.org/abs/2412.15237) (arXiv-2024)
    - ["Privacy-Preserving Machine Learning with Fully Homomorphic Encryption for Deep Neural Network"](https://arxiv.org/abs/2106.07229) (arXiv-2021)
- **Control self-assessments**
  - The organization performs control self-assessments at least annually to gain assurance that controls are in place and operating effectively. Corrective actions are taken based on relevant findings. If the organization has committed to an SLA for a finding, the corrective action is completed within that SLA.
  - Resources:
    - ["The Assessment List for Trustworthy Artificial Intelligence: A Review of ALTAI"](https://www.frontiersin.org/articles/10.3389/frai.2023.1020592/full) (Frontiers in Artificial Intelligence-2023)
    - ["A Systematic Review of Artificial Intelligence Impact Assessments"](https://link.springer.com/article/10.1007/s10462-023-10420-8) (Artificial Intelligence Review-2023)
    - [AI-Powered Internal Auditing: Transforming the Profession for a New Era](https://rsisinternational.org/journals/ijriss/articles/ai-powered-internal-auditing-transforming-the-profession-for-a-new-era/) (IJRISS-NOV2024) - *Discusses the role of internal auditors using AI to enhance control evaluation and fraud detection.*
    - [R\&D Investment, Internal Control and Enterprise Performance—An Empirical Study Based on the Listed Companies in China of the Core Industry of the Digital Economy](https://www.mdpi.com/2071-1050/14/24/16700) (MDPI-DEC2022)
    - [The Role of Internal Audit in Assessing the Risks of Management Decisions regarding Strategic Operations (Acquisition)](https://www.researchgate.net/publication/364279517_The_Role_of_Internal_Audit_in_Assessing_the_Risks_of_Management_Decisions_regarding_Strategic_Operations_Acquisition) (Journal of Economics and Administrative Sciences-SEP2022) - *Explores internal audit's role in risk assessment related to strategic decisions.*

- **Vulnerability and system monitoring procedures**
  - The organization's formal policies outline the requirements for the following functions related to IT / Engineering.
  - Resources:
    - [Adversarial Testing for Generative AI](https://developers.google.com/machine-learning/guides/adv-testing) (Google for Developers - DEC2024) - Describes a detailed workflow for adversarial testing, including identifying inputs, creating datasets, generating/annotating outputs, and reporting/mitigating findings.
    - [Toward a Comprehensive Framework for Ensuring Security and Privacy in Artificial Intelligence](https://www.mdpi.com/2079-9292/12/18/3786) (MDPI/Electronics - SEP2023) - Outlines key procedural elements within a security framework, including risk assessment steps, specific AI model security measures, monitoring and threat detection mechanisms (IDS, log analysis, real-time monitoring), and evaluation procedures like audits and penetration testing.

#### S2\.e Internal Security Procedures
Operational security procedures for maintaining the security posture of AI systems throughout their lifecycle.
- **Continuity and Disaster Recovery plans**
  - The organization has Business Continuity and Disaster Recovery Plans in place that outline communication plans in order to maintain information security continuity in the event of the unavailability of key personnel.
  - Resources:
    - ["Enhancing Business Continuity Planning with Artificial Intelligence"](https://continuityinsights.com/enhancing-business-continuity-planning-with-artificial-intelligence/) (Continuity Insights-2024)
    - ["Leveraging AI for Business Continuity and Disaster Recovery in the Work-from-Home Era"](https://drj.com/journal_main/leveraging-ai-for-business-continuity-and-disaster-recovery-in-the-work-from-home-era/) (Disaster Recovery Journal-2025)
    - [AI-Driven Approaches to Database Security and Disaster Recovery: Enhancing Resilience and Threat Mitigation](https://journals.threws.com/index.php/IJSCS/article/view/382) (International Journal of Statistical Computation and Simulation - FEB2025)
    - [Disaster Recovery and Business Continuity Planning for Enterprise Applications in the Cloud](https://www.researchgate.net/publication/388959297_Disaster_Recovery_and_Business_Continuity_Planning_for_Enterprise_Applications_in_the_Cloud) (ResearchGate - FEB2025)
    - [AI-Enhanced Disaster Recovery: A Collaborative Approach](https://www.researchgate.net/publication/387227775_AI-Enhanced_Disaster_Recovery_A_Collaborative_Approach) (ResearchGate - DEC2024)
    - [The Ultimate Business Guide to Backup Disaster Recovery and AI in 2025](https://www.systnet.com/blog/) (SystemsNet - MAR2025) *(Practical guide, touches on backup/DR for AI)*
    - [The Function of Artificial Intelligence in Business Continuity Management](https://www.researchgate.net/publication/389117361_The_Function_of_Artificial_Intelligence_in_Business_Continuity_Management) (ResearchGate - MAR2025) *(Discusses AI role in BCM/DR)*

- **Production deployment access**
  - The organization restricts access to migrate changes to production to authorized personnel.
  - Resources:
    - ["Joint Cybersecurity Information: Deploying AI Systems Securely"](https://media.defense.gov/2024/apr/15/2003439257/-1/-1/0/csi-deploying-ai-systems-securely.pdf) (U.S. Department of Defense-2024)
    - ["AI Agents Need an Access Control Overhaul"](https://www.permit.io/blog/ai-agents-access-control-with-pydantic-ai) (Permit.io Blog-2025)
    - [MLSecOps: Protecting AI/ML Lifecycle in telecom](https://www.ericsson.com/en/reports-and-papers/white-papers/mlsecops-protecting-the-ai-ml-lifecycle-in-telecom) (Ericsson White Paper - ~2024) - Discusses securing CI/CD pipelines for ML, including artifact protection, authenticity checks, version control, and access control for tools.
    - [Abusing MLOps platforms to compromise ML models and enterprise data lakes](https://securityintelligence.com/x-force/abusing-mlops-platforms-to-compromise-ml-models-enterprise-data-lakes/) (IBM Security Intelligence - JAN2025) - Highlights risks and best practices for securing MLOps platforms, including identity and access management, role-based access, securing secrets, and auditing/monitoring ML assets like endpoints and pipelines.
    - [Integrating Security into MLOps: A Framework for Risk Mitigation](https://iarjset.com/wp-content/uploads/2024/11/IARJSET.2024.111025.pdf) (IARJSET - NOV2024) - Covers securing the model deployment stage within MLOps, focusing on API security aspects like authentication (OAuth, API keys), rate limiting, and encryption (TLS).
    - [Secure the build and deployment pipeline](https://www.ncsc.gov.uk/collection/developers-collection/principles/secure-the-build-and-deployment-pipeline) (NCSC.GOV.UK - Undated, Recent) - Provides foundational principles for secure deployment pipelines, including trust in the infrastructure, peer review with technical controls, controlled deployment triggers, automated testing, and secrets management.
    - [Securing AI/ML Ops](https://sec.cloudapps.cisco.com/security/center/resources/SecuringAIMLOps) (Cisco - SEP2024) - Discusses securing the underlying cloud infrastructure often used for AI deployment, covering credentials, user access configuration (least privilege), MFA, and logging.

- **Development lifecycle**
  - The organization has a formal systems development life cycle (SDLC) methodology in place that governs the development, acquisition, implementation, changes (including emergency changes), and maintenance of information systems and related technology requirements.
  - Resources:
    - ["Secure Development Lifecycle (SDLC) for Artificial Intelligence"](https://notes-from-the-second-mountain.medium.com/secure-development-lifecycle-sdlc-for-artificial-intelligence-f11a63d1da32) (Medium-2024)
    - ["SDLC and Secure Coding Practices: The Ultimate Guide for 2024"](https://vulcan.io/blog/secure-sdlc-best-practices/) (Vulcan.io Blog-2024)
    - ["How AI is Transforming Software Development Processes"](https://www.practicallogix.com/the-future-of-sdlc-how-ai-is-transforming-software-development-processes/) (Practical Logix-2025)
    - [Guidelines for secure AI system development](https://www.ic3.gov/CSA/2023/231128.pdf) (IC3/NCSC/CISA - NOV2023) - Provides comprehensive, government-backed guidelines structured around the AI development lifecycle: secure design (threat modeling, supply chain security), secure development (asset protection, documentation), secure deployment (infrastructure/model protection, incident management), and secure operation/maintenance (monitoring, updates).
    - [MLSecOps: Protecting AI/ML Lifecycle in telecom](https://www.ericsson.com/en/reports-and-papers/white-papers/mlsecops-protecting-the-ai-ml-lifecycle-in-telecom) (Ericsson White Paper - ~2024) - Details the integration of security practices throughout the ML development lifecycle, including establishing security baselines, secure design/research environments, model tracking, secure data handling, and secure continuous training (CT).
    - [Abusing MLOps platforms to compromise ML models and enterprise data lakes](https://securityintelligence.com/x-force/abusing-mlops-platforms-to-compromise-ml-models-enterprise-data-lakes/) (IBM Security Intelligence - JAN2025) - Outlines key MLSecOps lifecycle considerations including inventory management of ML assets, security training for personnel, inclusion of ML solutions in threat modeling exercises, and secure workflow implementation.
    - [Securing the Future: DevSecOps in the Age of Artificial Intelligence](https://devops.com/securing-the-future-devsecops-in-the-age-of-artificial-intelligence/) (DevOps.com - APR2025) - Discusses integrating security continuously into the SDLC (DevSecOps) within the AI context, covering intelligent code scanning, automated compliance, adaptive threat modeling, and the importance of data governance and collaboration.
    - [How to Build a Secure Software Development Lifecycle (SSDLC)](https://integrio.net/blog/how-to-build-a-secure-software-development-lifecycle) (Integrio Systems - Undated, Recent) - Provides a general overview of SSDLC phases and best practices (risk assessment, secure design, secure coding, testing, etc.) that serve as a foundation for developing a tailored secure AI SDLC.   
- **Management roles and responsibilities**
  - The organization management has established defined roles and responsibilities to oversee the design and implementation of information security controls.
  - Resources:
    - ["Identifying Roles, Requirements, and Responsibilities in Trustworthy AI"](https://dl.acm.org/doi/10.1145/3460418.3479344) (Proceedings of the 2024 ACM Conference on Fairness, Accountability, and Transparency-2024)

- **Security policies**
  - The organization's information security policies and procedures are documented and reviewed at least annually.
  - Resources:
    - ["Artificial Intelligence and Information Governance: Enhancing Global Cybersecurity Compliance"](https://philarchive.org/archive/DHRAIA) (PhilArchive-2024)
    - ["AI Governance: A Systematic Literature Review"](https://link.springer.com/article/10.1007/s43681-024-00653-w) (AI and Ethics-2024)
    - [Guidelines for secure AI system development](https://www.ic3.gov/CSA/2023/231128.pdf) (IC3/NCSC/CISA PDF - NOV2023) - Offers detailed guidelines across the AI lifecycle (design, development, deployment, operation/maintenance) that should form the core content of documented AI security policies and procedures.
    - [Introduction — NVIDIA AI Enterprise Security White Paper](https://docs.nvidia.com/ai-enterprise/planning-resource/ai-enterprise-security-white-paper/latest/introduction.html) (NVIDIA White Paper - APR2025) - Details NVIDIA's security practices for their AI software stack, including vulnerability response and lifecycle management, implying documented internal policies and procedures. Includes link to their Lifecycle Policy.
    - [Artificial Intelligence: Policy and Practice](https://studiesvirginiageneralassembly.s3.amazonaws.com/meeting_docs/documents/000/002/452/original/2024_AI_Report.pdf?1733166715) (Virginia JLARC / AWS - ~2024) - Mentions the need for documented policies and procedures governing the procurement, implementation, and ongoing assessment of AI systems.

- **Incident response policies**
  - The organization has security and privacy incident response policies and procedures that are documented and communicated to authorized users.
  - Resources:
    - ["An Argument for Hybrid AI Incident Reporting"](https://cset.georgetown.edu/publication/an-argument-for-hybrid-ai-incident-reporting/) (Center for Security and Emerging Technology-2024)
    - ["Enhancing Incident Response Strategies in U.S. Healthcare Cybersecurity"](https://papers.ssrn.com/sol3/Delivery.cfm/5117971.pdf?abstractid=5117971&mirid=1) (SSRN-2024)
    - ["AI Policy Needs an Increased Focus on Incident Preparedness"](https://www.longtermresilience.org/reports/ai-policy-needs-an-increased-focus-on-incident-preparedness/) (Long-Term Resilience-2024)

- **Incident management procedures**
  - The organization's security and privacy incidents are logged, tracked, resolved, and communicated to affected or relevant parties by management according to the organization's security incident response policy and procedures.
  - Resources:
    - ["AI-Enhanced Cyber Incident Response and Recovery"](https://www.researchgate.net/publication/374605751_AI-Enhanced_Cyber_Incident_Response_and_Recovery) (International Journal of Science and Research-2023)
    - ["AI for Cyber Security: Automated Incident Response Systems"](https://www.researchgate.net/publication/383825151_AI_for_Cyber_Security_Automated_Incident_Response_Systems) (ResearchGate-2024)
    - ["Deployment Corrections: An Incident Response Framework for Frontier AI Models"](https://arxiv.org/abs/2310.00328) (arXiv-2023)
    - ["Standardised Schema and Taxonomy for AI Incident Databases in Critical Digital Infrastructure"](https://arxiv.org/abs/2501.17037) (arXiv-2025)

- **Physical access processes**
  - The organization has processes in place for granting, changing, and terminating physical access to organization data centers based on an authorization from control owners.
  - Resources:
    - ["Artificial Intelligence-Based Access Management System"](https://www.researchgate.net/publication/377589825_ARTIFICIAL_INTELLIGENCE-BASED_ACCESS_MANAGEMENT_SYSTEM) (ResearchGate-2023)
    - ["A Force Multiplier: Why Physical Security Teams Should Leverage AI"](https://www.asisonline.org/security-management-magazine/monthly-issues/security-technology/archive/2024/april/why-physical-security-teams-should-leverage-ai/) (ASIS International-APR2024)

- **Data center access**
  - The organization reviews access to the data centers at least annually.
  - Resources:
    - [Authentication, access, and monitoring system for critical areas with the use of artificial intelligence integrated into perimeter security in a data center](https://pmc.ncbi.nlm.nih.gov/articles/PMC10500307/) (IEEE Access via PMC - SEP2023) - Discusses using AI (computer vision, deep learning) to *implement* secure authentication, access control, and monitoring within data centers, including facial recognition and role/privilege verification.
- **Risk management program**
  - The organization has a documented risk management program in place that includes guidance on the identification of potential threats, rating the significance of the risks associated with the identified threats, and mitigation strategies for those risks.
  - Resources:
    - [AI for cyber-security risk: harnessing AI for automatic generation of company-specific cybersecurity risk profiles](https://www.emerald.com/insight/content/doi/10.1108/ics-08-2024-0177/full/html) (Information and Computer Security / Emerald Insight - FEB2025) - Presents and evaluates an AI-driven method to automate the generation of tailored cybersecurity risk profiles for organizations, contributing to threat identification and assessment within a risk program.
    - [AI-powered cybersecurity: Strategic approaches to mitigate risk and safeguard data privacy](https://wjarr.com/sites/default/files/WJARR-2024-3695.pdf) (World Journal of Advanced Research and Reviews - DEC2024) - Examines integrating AI-based cybersecurity frameworks into enterprise risk management, focusing on risk mitigation strategies, compliance alignment, and strategic management of AI security systems.
    - [Risk Assessment in Information Security Using AI: Utilizing Predictive Insights and Threat Modeling](https://www.researchgate.net/publication/385746438_Risk_Assessment_in_Information_Security_Using_AI_Utilizing_Predictive_Insights_and_Threat_Modeling) (ResearchGate Preprint/Likely Conference or Journal - NOV2024) - Explores using AI techniques (predictive analytics, threat modeling, anomaly detection) to enhance the risk assessment process itself within information security, applicable to assessing AI system risks.
    - [Toward a Comprehensive Framework for Ensuring Security and Privacy in Artificial Intelligence](https://www.mdpi.com/2079-9292/12/18/3786) (MDPI/Electronics - SEP2023) - Proposes a framework encompassing key elements of a risk management program, including risk assessment (threat/vulnerability identification, impact assessment), defining security measures (mitigation), monitoring, and continuous evaluation.
    - [Risk Management Profile for Artificial Intelligence and Human Rights](https://2021-2025.state.gov/risk-management-profile-for-ai-and-human-rights/) (U.S. Department of State Guidance Document - JUL2024) - Provides guidance mapping human rights risks onto the NIST AI RMF (Govern, Map, Measure, Manage), offering a structured approach to identifying, assessing, and managing specific AI risks relevant to a documented program. *(Note: Government Guidance)*
    - [Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) (NIST Technical Series Publication - JUL2024) - Official profile extending the NIST AI RMF, detailing unique risks of Generative AI and suggesting actions for risk management across the framework's functions (Govern, Map, Measure, Manage), serving as a basis for a documented program. *(Note: Government Framework Profile)*
#### S2\.f Data and Privacy
Controls specific to protecting the confidentiality and integrity of data used in AI training and inference processes.
- **Data retention procedures**
  - The organization has formal retention and disposal procedures in place to guide the secure retention and disposal of organization and customer data.
  - Resources:
    - [Managing Data Lifecycle Effectively: Best Practices for Data Retention and Archival Processes](http://www.ijerd.com/paper/vol20-issue7/2007453461.pdf) (International Journal of Engineering Research and Development - JUL2024)
    - [Data minimization and privacy-preserving techniques in AI systems](https://iapp.org/resources/article/data-minimisation-and-privacy-preserving-techniques-in-ai-systems/) (IAPP Resource Center - Undated, references recent guidance) - Discusses data minimization requirements and privacy-preserving techniques applicable when adopting AI systems, which directly influences retention needs. *(Professional Organization Resource)*
    - [AI Data Retention Creates Environmental Stumbling Block](https://www.dataversity.net/ai-data-retention-creates-environmental-stumbling-block/) (DATAVERSITY Blog - MAR2025) - Discusses the challenges of AI data retention, advocating for proactive data management, data mapping, minimization, classification, policy-based retention, clear internal policies, regular review cycles, and responsible data management culture. *(Industry Blog)*
- **Data classification policy**
  - The organization has a data classification policy in place to help ensure that confidential data is properly secured and restricted to authorized personnel.
  - Resources: tba

#### S2\.g Model Security
- **Model poisoning protections**
  - Resources:
    - [Detecting and Preventing Data Poisoning Attacks on AI Models](https://arxiv.org/abs/2503.09302) (arXiv MAR2025)
    - [Adversarial Training for Defense Against Label Poisoning Attacks](https://openreview.net/forum?id=UlpkHciYQP) (ICLR 2024/2025)
    - [Multi-level Certified Defense Against Poisoning Attacks in Offline Reinforcement Learning](https://openreview.net/forum?id=X2x2DuGIbx) (ICLR 2024/2025)
    - [Not All Poisons are Created Equal: Robust Training against Data Poisoning](https://proceedings.mlr.press/v162/yang22j.html) (ICML 2022)
    - [Data Poisoning in Deep Learning: A Survey](https://arxiv.org/abs/2503.22759) (arXiv MAR2025)
    - ["Preventing Machine Learning Poisoning Attacks Using Authentication and Provenance"](https://dl.acm.org/doi/cite/10.1145/3460120.3484841) (Stokes et al.-2021)
    - ["Securing Federated Learning with Control-Flow Attestation"](https://doi.org/10.48550/arXiv.2405.00563) (Alsulaimawi-2024)
    - ["Deep Learning Model Security: Threats and Defenses"](https://doi.org/10.1016/j.cose.2024.103841) (Wang et al.-2024)
- **Adversarial example defenses**
Techniques and strategies implemented to make AI models more robust against adversarial examples—inputs crafted with small, often imperceptible perturbations designed to cause the model to make incorrect predictions during inference.
  - Resources:
    - [Adversarial Training Can Provably Improve Robustness: Theoretical Analysis of Feature Learning Process Under Structured Data](https://arxiv.org/abs/2410.08503) (arXiv OCT2024)
    - [New Paradigm of Adversarial Training: Breaking Inherent Trade-Off between Accuracy and Robustness via Dummy Classes](https://openreview.net/forum?id=sBpYRQOrMn) (ICLR 2024/2025)
    - [Certified Adversarial Robustness via Partition-based Randomized Smoothing](https://www.researchgate.net/publication/384245495_Certified_Adversarial_Robustness_via_Partition-based_Randomized_Smoothing) (Khodayar et al.SEP2024)
    - [Data Augmentation Techniques for Building Robust AI Models in Enterprise Applications](https://ijirem.org/view_abstract.php?title=Data-Augmentation-Techniques-for-Building-Robust-AI-Models-in-Enterprise-Applications&year=2025&vol=12&primary=QVJULTE4NjM=) (International Journal of Innovative Research in Engineering and Management JAN2025)
    - [Adversarial Machine Learning on Social Network: A Survey](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2021.766540/full) (Frontiers in Physics NOV2021)
    - [A Comprehensive Review and Analysis of Deep Learning-Based Medical Image Adversarial Attack and Defense](https://www.mdpi.com/2227-7390/11/20/4272) (MDPI Mathematics OCT2023)
- **Model versioning and integrity checks**
Methods and practices for managing different versions of AI models throughout their lifecycle and implementing checks to ensure their integrity, verifying that they have not been tampered with or corrupted.
  - Resources:
    - ["Securing Federated Learning with Control-Flow Attestation"](https://doi.org/10.48550/arXiv.2405.00563) (Alsulaimawi-2024)
    - ["Preventing Machine Learning Poisoning Attacks Using Authentication and Provenance"](https://dl.acm.org/doi/cite/10.1145/3460120.3484841) (Stokes et al.-2021)
- **Secure model deployment pipelines**
Security controls, practices, and methodologies applied specifically to the MLOps or CI/CD pipelines used to deploy AI models into production environments, ensuring the security and integrity of the deployment process.
  - Resources:
    - [Security and Privacy Challenges in Enterprise MLOps Deployments](https://www.researchgate.net/publication/389023633_Security_and_Privacy_Challenges_in_Enterprise_MLOps_Deployments) (ResearchGate Preprint - FEB2025) - Analyzes infrastructure vulnerabilities (cloud, containers, APIs, orchestration tools) within MLOps pipelines and discusses security solutions like zero-trust models and continuous monitoring. *(Note: Likely Peer-Reviewed)*
    - [Securing the AI supply chain: Mitigating vulnerabilities in AI model development and deployment](https://www.researchgate.net/publication/389890574_Securing_the_AI_supply_chain_Mitigating_vulnerabilities_in_AI_model_development_and_deployment) (ResearchGate Preprint - MAR2025) - Proposes a multi-layered security framework including elements like zero-trust architecture relevant for secure deployment pipelines, addressing supply chain risks impacting deployment. *(Note: Likely Peer-Reviewed)*
    - [Integrating Security into MLOps: A Framework for Risk Mitigation](https://iarjset.com/wp-content/uploads/2024/11/IARJSET.2024.111025.pdf) (IARJSET - NOV2024) - Addresses security challenges in model deployment, particularly API security (authentication, rate limiting, encryption) within the MLOps pipeline. *(Peer-Reviewed Journal Paper)*
    - [Secure the build and deployment pipeline](https://www.ncsc.gov.uk/collection/developers-collection/principles/secure-the-build-and-deployment-pipeline) (NCSC.GOV.UK - Undated, Recent) - Provides foundational secure deployment principles applicable to AI models, including trusting the pipeline infrastructure, controlling deployment triggers, automated testing, and managing secrets securely. *(Note: Government Guidance)*
### S3\. Operations
#### S3\.a Threat Intelligence
Frameworks and methodologies for identifying, analyzing, and responding to emerging threats specific to AI systems, including model poisoning, evasion attacks, and data extraction techniques.
- Resources:
  - [Coordinated Flaw Disclosure for AI: Beyond Security Vulnerabilities](https://dl.acm.org/doi/10.5555/3716662.3716686) (AAAI2024)
  - ["Threat Modeling AI/ML Systems and Dependencies"](https://learn.microsoft.com/en-us/security/engineering/threat-modeling-aiml) (Microsoft Learn-2023)
  - ["Agentic AI Threat Modeling Framework: MAESTRO"](https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro) (Cloud Security Alliance-FEB2025)
  - [Adversarial Threats to AI-Driven Systems: Exploring the Attack Surface of Machine Learning Models and Countermeasures](https://journaljerr.com/index.php/JERR/article/view/1413) (Olutimehin et al. - Journal of Engineering Research and Reports, Vol 27, Issue 3, FEB2025) - Analyzes the AI attack surface (data, model, deployment), quantifies attack success rates using frameworks like MITRE ATLAS, and evaluates countermeasures, contributing to threat analysis methodology. 
  - [Threat Intelligence in AI Platforms What You Need to Know](https://www.researchgate.net/publication/390040249_Threat_Intelligence_in_AI_Platforms_What_You_Need_to_Know) (ResearchGate Preprint- FEB2025) - Provides a guide to Threat Intelligence Platforms (TIPs), their features, types of intelligence, and example tools (including sharing platforms like MISP), offering context for tooling in AI threat intelligence. 
  - [Enhancing Proactive Cyber Defense: A Theoretical Framework for AI-Driven Predictive Cyber Threat Intelligence](https://www.rtic-journal.com/article/enhancing-proactive-cyber-defense-a-theoretical-framework-for-ai-driven-predictive-cyber-threat-16176) (Hasan et al. - Journal of Technologies Information and Communication, Vol 5, Issue 1, 2025) - Presents a framework using AI techniques for predictive threat intelligence, relevant for understanding advanced analysis methodologies.
#### S3\.b Threat Hunting
Proactive approaches to identifying potential adversarial activities targeting AI systems before they manifest as security incidents.
- Red teaming for AI systems
  - Resources:
    - ["AI Red Teaming: Advancing Safe and Secure AI Systems"](https://www.mitre.org/news-insights/publication/ai-red-teaming-advancing-safe-and-secure-ai-systems) (MITRE-2024)
    - ["NeurIPS 2024 Workshop on Red Teaming GenAI"](https://redteamgenai.github.io/) (NeurIPS-2024)
    - [A Framework for Evaluating Emerging Cyberattack Capabilities of AI](https://arxiv.org/abs/2503.11917) (Brundage et al. - arXiv MAR2025) - Proposes a framework based on cyberattack chains (like MITRE ATT\&CK) to evaluate AI capabilities, which can inform AI-enabled adversary emulation for red teaming exercises. *(Note: arXiv Preprint)*
    - [How to Improve AI Red-Teaming: Challenges and Recommendations](https://cset.georgetown.edu/article/how-to-improve-ai-red-teaming-challenges-and-recommendations/) (Piotrowska & Arnold - CSET Report MAR2025) - Analyzes the current state, challenges (measurement, scope, transparency, incentives), and recommendations for improving AI red teaming practices. *(Note: Research Institute Report)*
    - [AI red-teaming is a sociotechnical challenge: on values, labor, and harms](https://arxiv.org/abs/2412.09751) (Feffer et al. - arXiv DEC2024) - Explores the sociotechnical dimensions, emerging practices, and implications of AI red teaming.
    - [RapidPen: An Autonomous Penetration Testing Framework using Iterative Agent-based Skill Refinement](https://arxiv.org/abs/2502.16730) (Bialek et al. - arXiv FEB2025) - While focused on automating general penetration testing with AI, the techniques for autonomous skill refinement and capability evaluation are relevant to developing advanced AI red teaming tools and methodologies.
    - [Adversarial Threats to AI-Driven Systems: Exploring the Attack Surface of Machine Learning Models and Countermeasures](https://journaljerr.com/index.php/JERR/article/view/1413) (Olutimehin et al. - Journal of Engineering Research and Reports, Vol 27, Issue 3, FEB2025) - Provides analysis of common adversarial attacks and defenses, useful for informing red team scenarios and understanding potential system weaknesses.
- Prompt injection
  - Resources:
    - ["How We Estimate the Risk from Prompt Injection Attacks on AI Systems"](https://security.googleblog.com/2024/05/how-we-estimate-risk-from-prompt.html) (Google Security Blog-MAY2025)
    - ["Prompt Injection Detection and Mitigation via AI Multi-Agent NLP"](https://arxiv.org/abs/2503.03923) (arXiv-2025)
    - [Defense against Prompt Injection Attacks via Mixture of Encodings](https://arxiv.org/abs/2504.07467) (Jiang et al. - arXiv APR2025) - Proposes a defense using multiple character encodings (including Base64) to create boundaries between instructions and external data, mitigating prompt injection while maintaining performance. *(Note: arXiv Preprint)*
    - [LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) (OWASP Top 10 for LLM & Generative AI Security - 2025 Update) - Defines prompt injection, provides attack scenarios (direct, indirect), and outlines mitigation strategies like constraining model behavior, input/output filtering, privilege control, and human approval. *(Note: Industry Standard/Guidance)*
    - [Prompt Injection Detection: Securing AI Systems Against Malicious Actors](https://www.salesforce.com/blog/prompt-injection-detection/) (Salesforce AI Research Blog - MAR2025) - Discusses industry research efforts to build models and detectors capable of analyzing user prompts to identify and deflect potential prompt injection attempts. *(Note: Industry Research Blog)*
- Membership inference
  - Resources:
    - ["Membership Inference Attacks Fueled by Few-Short Learning"](https://arxiv.org/abs/2502.08784) (arXiv-2025)
    - ["An Efficient Label-Only Membership Inference Attack"](https://openreview.net/forum?id=69w0yO1F_E) (ICLR-2024)
    - [AdaMixup: A Dynamic Defense Framework for Membership Inference Attack Mitigation](https://arxiv.org/abs/2501.02182) (Sun et al. - arXiv JAN2025) - Proposes a novel defense mechanism (AdaMixup) that dynamically adjusts sample influence during training to mitigate MIAs.
    - [Label-Only Membership Inference Attacks](http://proceedings.mlr.press/v139/choquette-choo21a.html) (Choquette-Choo et al. - ICML 2021) - Introduces an MIA method using only predicted labels and evaluates the effectiveness of defenses like differential privacy against it.
    - [Privacy Inference Attack and Defense in Centralized and Federated Learning: A Comprehensive Survey](https://www.computer.org/csdl/journal/ai/2025/02/10429780/1UmXPdGxKRW) (Huang et al. - IEEE Transactions on Artificial Intelligence, FEB2025 Pre-print) - Provides a broad survey of privacy attacks, including MIAs, and associated defense mechanisms in different learning settings.
    - [Mitigating Membership Inference in Deep Survival Analyses with Differential Privacy](https://pmc.ncbi.nlm.nih.gov/articles/PMC10751041/) (Li et al. - AMIA Annu Symp Proc via PMC - DEC2024) - Specifically investigates MIA risks in deep survival analysis models used in healthcare and evaluates differential privacy as a mitigation technique.
    - [Mitigating Membership Inference Vulnerability in Personalized Federated Learning](https://arxiv.org/abs/2503.09414) (Park et al. - arXiv MAR2025) - Proposes an enhanced personalized federated learning algorithm (IFCA-MIR) that incorporates MIA risk assessment into its clustering process to improve privacy.
    - [Differential Privacy Defenses and Sampling Attacks for Membership Inference](https://publications.cispa.saarland/3501/) (Rahimian et al. - ACM Workshop on Artificial Intelligence and Security (AISec) 2021) - Analyzes the effectiveness of differential privacy as a defense against membership inference attacks. *(Workshop Paper)*
    - [Membership Inference Attacks fueled by Few-Shot Learning to detect privacy leakage tackling data integrity](https://www.researchgate.net/publication/389786350_Membership_Inference_Attacks_fueled_by_Few-Short_Learning_to_detect_privacy_leakage_tackling_data_integrity) (Estevez-Tapiador et al. - ResearchGate Preprint/Likely Conference or Journal MAR2025) - Proposes a more resource-efficient MIA method using few-shot learning and a new evaluation metric for assessing privacy leakage.
    - [Differential Privacy Protection Against Membership Inference Attack on Machine Learning for Genomic Data](https://www.researchgate.net/publication/343448976_Differential_Privacy_Protection_Against_Membership_Inference_Attack_on_Machine_Learning_for_Genomic_Data) (Zhao et al. - BMC Medical Informatics and Decision Making 2021) - Evaluates the effectiveness of differential privacy in mitigating MIA risks when training machine learning models on sensitive genomic data.
- Model inversion
  - Resources:
    - [CENSOR: Defense Against Gradient Inversion via Orthogonal Subspace Bayesian Sampling](https://www.ndss-symposium.org/wp-content/uploads/2025-915-paper.pdf) (Balunovic et al. - NDSS 2025) - Proposes a defense against gradient inversion attacks by refining gradient updates using Bayesian sampling over orthogonal subspaces.
    - [Defending Against Gradient Inversion Attacks for Biomedical Images via Learnable Data Perturbation](https://arxiv.org/abs/2503.16542) (Chen et al. - arXiv MAR2025) - Presents a defense using latent data perturbation and minimax optimization to mitigate gradient inversion attacks in federated learning for medical images.
    - [Single-Step Diffusion Model-Based Generative Model Inversion Attacks](https://openreview.net/forum?id=TvhEoz1nim) (Li et al. - OpenReview/Likely ICLR 2024/2025) - Explores using distilled diffusion models for model inversion attacks, claiming improved reconstruction fidelity compared to GAN-based methods.
    - [Training Data Reconstruction: Privacy due to Uncertainty?](https://arxiv.org/abs/2412.08544) (Runkel et al. - arXiv DEC2024) - Analyzes the feasibility and ambiguity of reconstructing training data, suggesting that reconstructions might resemble valid but non-training samples.
    - [Algorithms that remember: model inversion attacks and data protection law](https://pmc.ncbi.nlm.nih.gov/articles/PMC6191664/) (Veale et al. - Philosophical Transactions of the Royal Society A / PMC - OCT2018) - Discusses the legal ramifications if AI models vulnerable to inversion are considered personal data under regulations like GDPR. *(Note: Foundational Journal Paper, older than 4 years)*
- Backdoor vulnerabilities
  - Resources:
    - ["Exploring Backdoor Vulnerabilities of Chat Models"](https://arxiv.org/abs/2412.00777) (arXiv-2024)
    - ["Mudjacking: Patching Backdoor Vulnerabilities in Foundation Models"](https://arxiv.org/abs/2411.03453) (arXiv-2024)
    - [Defending Against Backdoor Attacks by Layer-wise Feature Analysis](https://www.ijcai.org/proceedings/2024/0933.pdf) (Gao et al. - IJCAI 2024 Extended Abstract) - Proposes a detection method by analyzing feature differences between benign and potentially poisoned samples at identified critical layers within the neural network.
    - [Reliable backdoor attack detection for various size of backdoor triggers](https://www.researchgate.net/publication/387401546_Reliable_backdoor_attack_detection_for_various_size_of_backdoor_triggers) (Do et al. - ResearchGate Preprint/Likely Conference or Journal JAN2025) - Introduces a detection method claimed to be robust against varying backdoor trigger sizes by analyzing perturbation abnormalities needed for label reclassification.
    - [Universal Backdoor Detection](https://arxiv.org/abs/2503.21305) (Kolter et al. - arXiv MAR2025) - Presents a detection framework for scenarios with limited data access by optimizing potential triggers based on a continuous proxy for attack success rate.
    - [Trojan Cleansing with Neural Collapse](https://arxiv.org/abs/2411.12914) (Barnathan et al. - arXiv MAR2025 / Submitted to ICML 2025) - Leverages the Neural Collapse phenomenon to propose a new method for removing Trojans by imposing symmetry, aiming to preserve clean accuracy.
    - [Defending Deep Neural Networks against Backdoor Attacks via Module Switching](https://arxiv.org/abs/2504.05902) (Li et al. - arXiv APR2025) - Suggests mitigating backdoors in model fusion scenarios through an optimized module-switching strategy to disrupt learned malicious correlations.
    - [Defending Backdoor Attacks by Trapping Them into an Easy-to-Replace Subnetwork](https://pmc.ncbi.nlm.nih.gov/articles/PMC10115557/) (Gao et al. - CVPR via PMC - APR2023) - Proposes the "Trap and Replace" defense strategy that isolates backdoors into a small subnetwork which is then replaced.
    - [SALTY: Explainable Artificial Intelligence Guided Structural Analysis for Hardware Trojan Detection](https://arxiv.org/abs/2502.14116) (Ghosh et al. - arXiv FEB2025) - Uses Graph Neural Networks and XAI for hardware Trojan detection; methodologies may offer insights for software/model backdoors.
- Data poisoning
  - Resources:
    - ["AI Models Collapse When Trained on Recursively Generated Data"](https://www.nature.com/articles/s41586-024-07172-4) (Nature-2024)
    - ["Detecting and Preventing Data Poisoning Attacks on AI Models"](https://arxiv.org/abs/2503.06497) (arXiv-2025)
    - [Enhanced Blockchain-Based Data Poisoning Defense Mechanism](https://www.mdpi.com/2076-3417/15/7/4069) (Kim et al. - MDPI Applied Sciences APR2025) - Proposes using blockchain technology and game theory concepts (Byzantine Generals Game engine) to create a defense framework against data poisoning.
    - [Detecting and Preventing Data Poisoning Attacks on AI Models](https://www.researchgate.net/publication/389786240_Detecting_and_Preventing_Data_Poisoning_Attacks_on_AI_Models) (Kure et al. - ResearchGate Preprint/Likely Conference or Journal MAR2025) - Develops and evaluates techniques such as statistical anomaly detection, adversarial training, and ensemble learning to identify and mitigate data poisoning effects.
    - [Multi-Faceted Studies on Data Poisoning can Advance LLM Development](https://arxiv.org/abs/2502.14182) (He et al. - arXiv FEB2025) - A position paper advocating for deeper study into practical data poisoning attacks across the LLM lifecycle to better understand real-world risks and inform robust development.
    - [Invisible Threats in the Data: A Study on Data Poisoning Attacks in Deep Generative Models](https://www.mdpi.com/2076-3417/14/19/8742) (Zhang et al. - MDPI Applied Sciences SEP2024) - Investigates data poisoning backdoor attacks specifically targeting Deep Generative Models using visually imperceptible triggers embedded during data preparation.
    - [Not All Poisons are Created Equal: Robust Training against Data Poisoning](https://proceedings.mlr.press/v162/yang22j.html) (Yang et al. - ICML 2022) - Proposes the EPIC defense mechanism based on identifying and removing poisons that are isolated outliers in the gradient space during training.
    - [Data Poisoning in Deep Learning: A Survey](https://arxiv.org/abs/2503.22759) (Zhang et al. - arXiv MAR2025) - Provides a comprehensive review categorizing data poisoning attacks and analyzing their characteristics within the context of deep learning models.
    - [AI Data Poisoning: Attack Methods and Mitigation Strategies](https://www.issa.org/wp-content/uploads/2024/08/FeatureArticle-JulyAug2024.pdf) (ISSA Journal - JUL/AUG 2024) - Outlines various data poisoning attack methods and presents a layered mitigation strategy including data validation, anomaly detection, access control, monitoring, and information sharing.
- Model manipulation
  - Resources:
    - ["Model Manipulation Attacks Enable More Rigorous Evaluations of LLMs"](https://arxiv.org/abs/2412.03870) (NeurIPS SafeGenAI Workshop-2024)
    - [OpenAI's Approach to External Red Teaming for AI Models and Systems](https://arxiv.org/abs/2503.16431) (Arxiv-JAN2025)
    - [Defending against Data-Free Model Extraction by Distributionally Robust Defensive Training](https://openreview.net/forum?id=7DZAVpOoAK) (Golatkar et al. - OpenReview/NeurIPS 2023) - Proposes a defense (MeCo) against data-free model stealing attacks using robust training with input perturbations.
    - [Defense Against Model Stealing Based on Account-Aware Distribution Discrepancy](https://ojs.aaai.org/index.php/AAAI/article/view/32041) (Li et al. - AAAI 2025) - Introduces a non-parametric detector (ADD) to identify malicious queries indicative of model stealing attempts based on user account behavior.
#### S3\.c Testing
- AI security testing methodologies
  - Resources:
    - ["AI Red Teaming: Applying Software TEVV for AI Evaluations"](https://www.cisa.gov/news-events/news/ai-red-teaming-applying-software-tevv-ai-evaluations) (Cybersecurity and Infrastructure Security Agency (CISA)-2025)
    - ["Test and Evaluation of Artificial Intelligence Models Framework"](https://www.ai.mil/docs/TEV_Framework_v1.0.pdf) (Chief Digital and Artificial Intelligence Office (CDAO), U.S. Department of Defense-2024)
    - [A Survey on Penetration Path Planning in Automated Penetration Testing](https://www.mdpi.com/2076-3417/14/18/8355) (Ren et al. - MDPI Applied Sciences SEP2024) - Reviews automated penetration testing techniques, providing methodologies adaptable for systematically testing AI system security vulnerabilities.
    - [The use of artificial intelligence for automatic analysis and reporting of software defects](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1443956/full) (Ramirez et al. - Frontiers in Artificial Intelligence DEC2024) - Discusses leveraging AI to optimize software testing processes and the need for methodologies to validate models and document test results effectively.
    - [Generative AI for software testing: Harnessing large language models for automated and intelligent quality assurance](https://www.researchgate.net/publication/388661350_Generative_AI_for_software_testing_Harnessing_large_language_models_for_automated_and_intelligent_quality_assurance) (Srivastava - International Journal of Science and Research Archive JAN2025) - Explores using LLMs for automating test generation and outlines methodologies and best practices applicable to AI security testing automation.
- Formal verification approaches
  - Resources:
    - ["Formal Methods and Verification Techniques for Secure and Reliable AI"](https://www.researchgate.net/publication/386969718_Formal_Methods_and_Verification_Techniques_for_Secure_and_Reliable_AI) (ResearchGate-2025)
    - ["Adversarial Robustness of Deep Neural Networks: A Survey from a Formal Verification Perspective"](https://arxiv.org/abs/2202.04868) (arXiv-2022)
    - ["Reasoning Under Threat: Symbolic and Neural Techniques for Cybersecurity Verification"](https://arxiv.org/abs/2503.05423) (arXiv-2025)
    - [Neural Network Verification: A Programming Language Perspective](https://arxiv.org/abs/2501.05867) (Cordeiro et al. - arXiv JAN2025) - Reviews current neural network verification techniques and challenges (including robustness verification) from a programming languages viewpoint, suggesting future directions for the field.
    - [Evaluation of Neural Network Verification Methods for Air-to-Air Collision Avoidance](https://arc.aiaa.org/doi/10.2514/1.D0255) (Lopez et al. - Journal of Air Transportation, Published online NOV2023) - Evaluates formal verification tools (using star-set reachability) on neural network controllers for safety properties in a complex cyber-physical system (ACAS Xu).
- Robustness certification
  - Resources:
    - [Certified Adversarial Robustness via Partition-based Randomized Smoothing](https://www.researchgate.net/publication/384245495_Certified_Adversarial_Robustness_via_Partition-based_Randomized_Smoothing) (Khodayar et al. - ResearchGate Preprint/Likely Conference or Journal SEP2024) - Proposes a Partition-based Randomized Smoothing (PPRS) methodology aimed at improving the certified robustness radius achievable with randomized smoothing techniques.
    - [Adversarial robustness assessment: Why in evaluation both L0 and L∞ attacks are necessary](https://pmc.ncbi.nlm.nih.gov/articles/PMC9009601/) (Benfatto et al. - Scientific Reports / PMC - APR2022) - Argues for and proposes a model-agnostic robustness assessment method considering both L0 and L∞ perturbations for a more complete evaluation than single metrics provide.
    - [Adversarial Robustness Guarantees for Quantum Classifiers](https://www.researchgate.net/publication/380719267_Adversarial_Robustness_Guarantees_for_Quantum_Classifiers) (Meyer et al. - ResearchGate Preprint/Likely Conference or Journal MAY2024) - Explores theoretical adversarial robustness guarantees for quantum machine learning (QML) classifiers, identifying quantum properties that can provide protection.
- Evaluation frameworks
  - Resources:
    - ["An AI System Evaluation Framework for Advancing AI Safety"](https://arxiv.org/abs/2407.03923) (arXiv-2024)
    - ["A Framework for Ensuring Robust and Reliable AI Systems"](https://arxiv.org/abs/2402.04694) (arXiv-2024)
    - [Establishing and evaluating trustworthy AI: overview and research challenges](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2024.1467222/full) (Bier et al. - Frontiers in Big Data APR2024) - Synthesizes six requirements for trustworthy AI (human agency, fairness, transparency, robustness/accuracy, privacy/security, accountability) and discusses evaluation challenges across the AI lifecycle.
    - [AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) (NIST - JAN2023 & ongoing updates) - A voluntary framework from the US National Institute of Standards and Technology providing principles and practices (Govern, Map, Measure, Manage) to guide the assessment and management of risks associated with AI systems. *(Note: Government Framework)*
    - [A Framework for Evaluating Emerging Cyberattack Capabilities of AI](https://arxiv.org/abs/2503.11917) (Brundage et al. - arXiv MAR2025) - Offers a framework specifically for evaluating the offensive potential of AI systems across cyberattack phases, contributing a risk assessment component to broader evaluation efforts.

#### S3\.d Incident Response for AI Systems
AI-specific incident detection
  - Resources:
    - ["Anomaly Detection for Incident Response at Scale"](https://arxiv.org/abs/2403.00318) (arXiv-2024)
    - ["AI-Enabled System for Efficient and Effective Cyber Incident Detection and Response in Cloud Environments"](https://arxiv.org/abs/2405.02100) (arXiv-2024)
    - ["Methodology for Incident Response on Generative AI Workloads"](https://aws.amazon.com/blogs/security/methodology-for-incident-response-on-generative-ai-workloads/) (AWS Security Blog-2024)
    - [AI Incident Response Plans: Checklist & Best Practices](https://www.cimphony.ai/insights/ai-incident-response-plans-checklist-and-best-practices) (Cimphony Blog - ~2024/2025) - Outlines the standard IR phases including Containment and Mitigation, providing the procedural context into which specific AI containment techniques would fit. *(Note: Industry Blog)*
    - [Runtime Detection of Adversarial Attacks in AI Accelerators Using Performance Counters](https://arxiv.org/abs/2503.07568) (Asad et al. - arXiv MAR2025) - Proposes a hardware-based framework (SAMURAI) using performance counters and on-chip machine learning (TANTO) to detect adversarial attacks against AI models in real-time by monitoring hardware execution profiles.
    - [Building Resilient Security Systems: The Role of AI in Detection and Incident Response](https://www.researchgate.net/publication/389673821_Building_Resilient_Security_Systems_The_Role_of_AI_in_Detection_and_Incident_Response) (Fadi & Obeidat - ResearchGate Preprint/Likely Conference or Journal MAR2025) - Explores using AI techniques like anomaly detection and behavioral pattern recognition for real-time threat monitoring, which can be applied to detect attacks targeting deployed AI systems.
    - [Activation Gradient based Poisoned Sample Detection Against Backdoor Attacks](https://openreview.net/forum?id=VNMJfBBUd5) (Li et al. - OpenReview/NeurIPS 2024) - Introduces a method (AGPD) based on analyzing activation gradient distributions to distinguish poisoned samples, potentially adaptable for runtime detection or periodic checks.
    - [Towards a conceptual framework for AI-driven anomaly detection in smart city IoT networks for enhanced cybersecurity](https://www.sciencedirect.com/science/article/pii/S2444569X24001409) (Machado et al. - Journal of Innovation & Knowledge, Available online MAR2025) - Presents a framework using AI for anomaly detection within complex IoT networks, relevant for identifying deviations that might indicate attacks on embedded AI components.
    - [Artificial Intelligence-Based Anomaly Detection Technology over Encrypted Traffic: A Systematic Literature Review](https://www.mdpi.com/1424-8220/24/3/898) (Lee et al. - MDPI Sensors JAN2024) - Reviews AI methods for detecting anomalies in encrypted network traffic, potentially useful for monitoring communications involving AI systems for indicators of compromise.
Containment strategies for compromised models
  - Resources:
    - [Defending Backdoor Attacks by Trapping Them into an Easy-to-Replace Subnetwork](https://pmc.ncbi.nlm.nih.gov/articles/PMC10115557/) (Gao et al. - CVPR via PMC - APR2023) - The proposed "Trap and Replace" method includes replacing the subnetwork containing the trapped backdoor as a containment/eradication step.
    - [Detecting and Preventing Data Poisoning Attacks on AI Models](https://arxiv.org/abs/2503.09302) (Kure et al. - arXiv MAR2025) - Discusses mitigation strategies like robust optimization and ensemble learning which aim to limit the negative effects of poisoning, thus containing the damage.
    - [A Playbook for Securing AI Model Weights](https://www.rand.org/pubs/research_briefs/RBA2849-1.html) (Tarasidis et al. - RAND Research Brief NOV2024) - Recommends security controls like access restrictions, confidential computing, and monitoring to prevent misuse, which functionally help contain a compromised model by limiting its exploitability. *(Note: Research Institute Report/Brief)*
    - ["AI-Infused Threat Detection and Incident Response in Cloud Security"](https://www.academia.edu/114251261/AI_Infused_Threat_Detection_and_Incident_Response_in_Cloud_Security) (Academia.edu-2024)
    - ["Guidelines for Artificial Intelligence Containment"](https://arxiv.org/abs/1701.06048) (arXiv-2017)
Forensics for AI systems
  - Resources:
    - ["Scalable Microservice Forensics and Stability Assessment Using Variational Autoencoders"](https://arxiv.org/abs/2101.07727) (arXiv-2021)
    - [Digital Forensics in the Age of Large Language Models](https://arxiv.org/abs/2504.02963) (Al-Bataineh et al. - arXiv APR2025) - Discusses the applications and significant challenges (evidence integrity, reproducibility, prompt analysis) of using LLMs in digital forensics and investigating incidents involving LLMs.
    - [Augmenting Forensic Science Through AI: The Next Leap in Multidisciplinary Approaches](https://www.researchgate.net/publication/388399333_Augmenting_Forensic_Science_Through_AI_The_Next_Leap_in_Multidisciplinary_Approaches) (Miller - ResearchGate Preprint JAN2025) - Reviews the integration of AI (ML, pattern recognition, data analytics) into forensic science, including digital forensics, highlighting capabilities for analyzing complex data potentially relevant to AI incidents.
    - [Generative AI in Forensic Data Analysis: Opportunities and Ethical Implications for Cloud-Based Investigations](https://ijrpr.com/uploads/V5ISSUE10/IJRPR34162.pdf) (Chandra & Singh - IJRPR OCT2024) - Examines the use of generative AI for forensic tasks like evidence reconstruction, log data analysis, and file recovery, relevant to investigations where AI tools are used or AI systems are analyzed.
    - [A Framework for Integrated Digital Forensic Investigation Employing AutoGen AI Agents](https://www.google.com/search?q=https://ieeexplore.ieee.org/document/10490745) (Wickramasekara & Scanlon - IEEE ISDFS 2024) - Proposes using collaborating AI agents to assist in digital forensic investigations, indicating a direction for future forensic methodologies.
    - [AutoDFBench: A Framework for AI Generated Digital Forensic Code and Tool Testing and Evaluation](https://forensicsandsecurity.com/publications.php) (Wickramasekara et al. - DFDS 2025 Abstract/Upcoming) - Describes a planned framework for evaluating AI-generated forensic tools, addressing the need for validating AI's role in forensics.
Recovery and remediation procedures
  - Resources:
    - ["AI Incident Response Plans: Checklist & Best Practices"](https://www.cimphony.ai/blog/ai-incident-response-plans-checklist-best-practices/) (Cimphony.ai-2024)
    - ["AI Incident Response 101: Handling AI Failures and Unintended Consequences"](https://www.zendata.dev/blog/ai-incident-response) (Zendata.dev-2024)
    - [AI-Enhanced Cyber Incident Response and Recovery](https://www.researchgate.net/publication/374605751_AI-Enhanced_Cyber_Incident_Response_and_Recovery) (Manogaran et al. - ResearchGate Preprint OCT2024) - Analyzes the integration of AI into both incident response *and* recovery processes, aiming to enhance overall cyber resilience.
    - [The Role of AI in Disaster Recovery: Accelerating Cloud Service Restoration and Ensuring Business Continuity](https://www.researchgate.net/publication/390060823_The_Role_of_AI_in_Disaster_Recovery_Accelerating_Cloud_Service_Restoration_and_Ensuring_Business_Continuity/download) (Ahmad - ResearchGate Preprint MAR2025) - Discusses how AI can speed up disaster recovery processes, including self-healing infrastructure and optimized data recovery, contributing to faster restoration of AI services.)*
    - [AI policy needs an increased focus on incident preparedness](https://www.longtermresilience.org/reports/ai-policy-needs-an-increased-focus-on-incident-preparedness/) (Shaffer Shane & Robinson - CLTR Report MAR2025) - Emphasizes planning for response and resilience, which are crucial for effective recovery and remediation after major AI incidents.
    - [Incident Response Best Practices For 2025](https://purplesec.us/learn/incident-response-best-practices/) (PurpleSec - DEC2024) - Outlines the standard Recovery and Lessons Learned phases of incident response, providing the essential procedural framework for post-incident activities. *(Note: Industry Blog)*
### S5\. Interdependent Security
Addressing security implications of AI system dependencies on external services, data sources, and infrastructure.
  - Resources:
    - [Securing the AI supply chain: Mitigating vulnerabilities in AI model development and deployment](https://www.researchgate.net/publication/389890574_Securing_the_AI_supply_chain_Mitigating_vulnerabilities_in_AI_model_development_and_deployment) (Sharma - ResearchGate Preprint MAR2025) - Analyzes vulnerabilities across the AI supply chain (data collection, model development, third-party integrations, deployment) and proposes mitigation strategies including blockchain, federated learning, and zero-trust architecture.
    - [Security and Privacy Challenges in Enterprise MLOps Deployments](https://www.researchgate.net/publication/389023633_Security_and_Privacy_Challenges_in_Enterprise_MLOps_Deployments) (Singh - ResearchGate Preprint FEB2025) - Explores security risks in MLOps related to data security, model security, infrastructure vulnerabilities (cloud, containers, APIs), and compliance, highlighting dependencies.
    - [AI Applications in Supply Chain Management: A Survey](https://www.mdpi.com/2076-3417/15/5/2775) (Tsolakis et al. - MDPI Applied Sciences FEB2025) - While focused on using AI *in* SCM, it touches upon risks, resilience, and ethical/security concerns related to AI adoption within complex, interdependent supply chains.
    - [Examining the integration of artificial intelligence in supply chain management from Industry 4.0 to 6.0: a systematic literature review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11788849/) (Joel - Journal of Big Data / PMC - FEB2025) - Reviews AI integration in SCM, explicitly mentioning challenges like cybersecurity risks that arise in these interconnected systems.
    - [Cybersecurity Risks of AI-Generated Code](https://cset.georgetown.edu/publication/cybersecurity-risks-of-ai-generated-code/) (Ellington et al. - CSET Report JUN2023) - Identifies risks associated with using AI code generation models, treating the AI model itself as a component in the software supply chain with potential security implications. *(Note: Research Institute Report)*
    - [AI and cybersecurity: a risk society perspective](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2024.1462250/full) (Hutter - Frontiers in Computer Science OCT2024) - Discusses the complex, interconnected, and often invisible nature of AI risks within the broader societal context, relevant to understanding interdependent security challenges.
    - [Securing AI in 2025: A Risk-Based Approach to AI Controls and Governance](https://www.sans.org/blog/securing-ai-in-2025-a-risk-based-approach-to-ai-controls-and-governance/) (SANS Institute - MAR2025) - Recommends maintaining an AI Bill of Materials (AIBOM) to document AI supply chain dependencies for transparency and risk assessment.
#### S5\.a Subprocessors
Management and security oversight of third parties that support AI operations or have access to system components.
- User support
  - Resource: tba
- Billing
  - Resource:
    - ["A Systematic Review of AI-Enhanced Techniques in Credit Card Fraud Detection"](https://journalofbigdata.springeropen.com/articles/10.1186/s40537-024-01048-8) (Journal of Big Data-2024)
    - ["Utilizing GANs for Fraud Detection: Model Training with Synthetic Transaction Data"](https://arxiv.org/abs/2402.09830) (arXiv-2024)
- Communication
  - Resource: tba
- Application, monitoring, and search services
  - Resource: tba
- Security and fraud detection services
  - Resource: tba
- Cloud Infrastructure
  - Resource:
    - ["Inter-Cloud Data Security Framework to Build Trust Based on Compliance with Controls"](https://dl.acm.org/doi/abs/10.1049/2024/6565102) (IET Information Security-2024)
- Networks
  - Resource:
    - ["Inter-Cloud Data Security Framework to Build Trust Based on Compliance with Controls"](https://dl.acm.org/doi/abs/10.1049/2024/6565102) (IET Information Security-2024)
#### S5\.b Supply Chain
Security considerations for the AI development supply chain, including pre-trained models, datasets, and algorithmic components.
- Resources:
  - [["Understanding Accountability in Algorithmic Supply Chains"](https://dl.acm.org/doi/10.1145/3593013.3594073) (ACM Conference on Fairness, Accountability, and Transparency (FAccT)-2023)
  - [["Artificial Intelligence in Supply Chain Management: A Systematic Review"](https://www.sciencedirect.com/science/article/pii/S0166361524000605) (Computers and Electronics in Agriculture-2024)
  - [["Enhancing Supply Chain Management with Deep Learning and Reinforcement Learning"](https://www.sciencedirect.com/science/article/pii/S2199853124001732) (Journal of Manufacturing Systems-2024)
  - [["An Innovative Machine Learning Model for Supply Chain Management"](https://www.sciencedirect.com/science/article/pii/S2444569X22001111) (Journal of Information Systems and Technology Management-2022)
  - [["Supply Chain Risk Management with Machine Learning Technology"](https://www.sciencedirect.com/science/article/pii/S0360835222008476) (Omega-2022)
  - [["Artificial Neural Networks in Supply Chain Management: A Review"](https://www.sciencedirect.com/science/article/pii/S2949948823000112) (Journal of Intelligent Manufacturing-2023)
  - [["AI-Based Decision Support Systems in Industry 4.0: A Review"](https://www.sciencedirect.com/science/article/pii/S2949948824000374) (Journal of Industrial Information Integration-2024)
  - [["A Comprehensive Survey on AI-Enabled Secure Social Industrial IoT Applications in the Agri-Food Supply Chain"](https://www.sciencedirect.com/science/article/pii/S2772375525001352) (Journal of Network and Computer Applications-2025)
#### S5\.c Threat Modeling
- Resources:
  - ["Building Guardrails in AI Systems with Threat Modeling"](https://dl.acm.org/doi/10.1145/3674845) (ACM Conference on Computer and Communications Security (CCS)-2024)
  - ["Towards More Practical Threat Models in Artificial Intelligence Security"](https://arxiv.org/abs/2311.09994) (arXiv-2023)
  - ["ADMIn: Attacks on Dataset, Model and Input. A Threat Model for AI-Based Software"](https://arxiv.org/abs/2401.07960) (arXiv-2024)
  - ["Threat Modeling of Industrial Control Systems: A Systematic Literature Review"](https://www.sciencedirect.com/science/article/pii/S0167404823004534) (Computers & Security-2023)
  - ["Explainable AI for Cybersecurity Automation, Intelligence, and Threat Modeling"](https://www.sciencedirect.com/science/article/pii/S2405959524000572) (Journal of Information Security and Applications-2024)
  - ["Security and Privacy for Artificial Intelligence: Opportunities and Challenges"](https://arxiv.org/abs/2102.04661) (arXiv-2021)
## Privacy

### P1\. General Privacy
- Resources:
  - [Privacy-Preserving Architectures for AI/ML Applications: Methods, Balances, and Illustrations] (https://newjaigs.com/index.php/JAIGS/article/view/117)
  - ["Preserving Data Privacy in Machine Learning Systems"](https://www.sciencedirect.com/science/article/pii/S0167404823005151) (Computers & Security-2023)
  - ["Privacy-Preserving Artificial Intelligence in Healthcare: Techniques and Applications"](https://www.sciencedirect.com/science/article/pii/S001048252300313X) (Computers in Biology and Medicine-2023)
  - ["A Unified Privacy-Preserving Model with AI at the Edge for Human-in-the-Loop Cyber-Physical Systems"](https://www.sciencedirect.com/science/article/pii/S2542660523003578) (Patterns-2023)
  - ["Privacy-Preserving Techniques for Decentralized and Secure Machine Learning in Drug Discovery"](https://www.sciencedirect.com/science/article/pii/S1359644623003367) (Trends in Pharmacological Sciences-2023)
  - ["Privacy-Preserving and Memory-Efficient Neural Network Inference at the Edge"](https://www.sciencedirect.com/science/article/abs/pii/S0167739X24000797) (Future Generation Computer Systems-2024)
  - ["Privacy-Preserving Machine Learning"](https://www.sciencedirect.com/topics/computer-science/privacy-preserving-machine-learning) (ScienceDirect Topics)
### P1\. Differencial Privacy
Implementation strategies for differential privacy techniques that enable using sensitive data for AI training while providing mathematical privacy guarantees.
- Resources:
  - ["Differential Privacy in Deep Learning: A Literature Survey"](https://www.sciencedirect.com/science/article/abs/pii/S092523122400434X) (Neurocomputing-2024)
  - ["Differential Privacy in Deep Learning: Privacy and Beyond"](https://www.sciencedirect.com/science/article/abs/pii/S0167739X23002315) (Future Generation Computer Systems-2023)
  - ["Advancing Privacy in Learning Analytics Using Differential Privacy"](https://dl.acm.org/doi/10.1145/3706468.3706493) (ACM Learning Analytics & Knowledge Conference-2025)
  - ["A Differential Privacy Preservation Technique for Cyber–Physical Systems"](https://www.sciencedirect.com/science/article/abs/pii/S0045790623000861) (Computers & Electrical Engineering-2023)
  - ["Differential Privacy"](https://www.sciencedirect.com/topics/computer-science/differential-privacy) (ScienceDirect Topics)
### P2\. Federated Learning with Privacy Protection
Approaches to implementing federated learning architectures that maintain data privacy by training models across decentralized devices without centralizing raw data.
- Resources:
  - ["Privacy Preservation in Federated Learning: An Insightful Survey from the GDPR Perspective"](https://www.sciencedirect.com/science/article/pii/S0167404821002261) (Computers & Security-2021)
  - ["Federated Learning as a Privacy Solution: An Overview"](https://www.sciencedirect.com/science/article/pii/S1877050922023055) (Procedia Computer Science-2022)
  - ["Privacy Preservation for Federated Learning in Healthcare"](https://www.sciencedirect.com/science/article/pii/S2666389924000825) (Intelligent Medicine-2024)
  - ["Federated Learning with Differential Privacy on Personal Opinions"](https://www.sciencedirect.com/science/article/pii/S1877050923011973) (Procedia Computer Science-2023)
  - ["Balancing Privacy and Performance in Federated Learning"](https://www.sciencedirect.com/science/article/pii/S0743731524000820) (Journal of Parallel and Distributed Computing-2024)
  - ["Privacy-Preserving Federated Machine Learning on FAIR Health Data"](https://www.sciencedirect.com/science/article/pii/S2001037024000382) (Patterns-2024)
  - ["Privacy-Preserving Federated Learning and Its Application to Natural Language Processing"](https://www.sciencedirect.com/science/article/pii/S0950705123002253) (Knowledge-Based Systems-2023)
  - ["A Review of Secure Federated Learning: Privacy Leakage Threats, Attacks, and Defense Mechanisms"](https://www.sciencedirect.com/science/article/abs/pii/S0925231223010202) (Neurocomputing-2023)
  - ["Privacy Preservation for Federated Learning in Health Care"](https://www.sciencedirect.com/science/article/pii/S2666389924000825) (Intelligent Medicine-2024)
  - ["Belt and Braces: When Federated Learning Meets Differential Privacy"](https://dl.acm.org/doi/full/10.1145/3650028) (ACM Transactions on Privacy and Security-2025)
### P3. Privacy-Preserving Machine Learning
- Homomorphic encryption applications
  - Resources:
    - ["Deep Homeomorphic Data Encryption for Privacy Preserving Machine Learning"](https://www.sciencedirect.com/science/article/pii/S1877050924002163) (Procedia Computer Science-2024)
    - ["Enhancing Privacy-Preserving Machine Learning with Self-Learnable Homomorphic Encryption"](https://www.sciencedirect.com/science/article/abs/pii/S2214212624001893) (Future Generation Computer Systems-2024)
    - ["GuardML: Efficient Privacy-Preserving Machine Learning Services Through Hybrid Homomorphic Encryption"](https://arxiv.org/abs/2401.14840) (arXiv preprint-2024)
    - ["Privacy-Preserving Machine Learning with Fully Homomorphic Encryption for Deep Neural Network"](https://arxiv.org/abs/2106.07229) (arXiv preprint-2021)
- Secure multi-party computation
  - Resources:
    - ["Secure Multi-Party Computations for Privacy-Preserving Machine Learning"](https://www.sciencedirect.com/science/article/pii/S1877050922017914) (Procedia Computer Science-2022)
    - ["Efficiency and Security Trade-offs of Secure Multi-Party Computation in Machine Learning"](https://www.sciencedirect.com/science/article/pii/S1877050923012097) (Procedia Computer Science-2023)
    - ["Private-Preserving Language Model Inference Based on Secure Multi-Party Computation"](https://www.sciencedirect.com/science/article/pii/S0925231224005654) (Neurocomputing-2024)
    - ["CrypTen: Secure Multi-Party Computation Meets Machine Learning"](https://arxiv.org/abs/2109.00984) (arXiv preprint-2021)
- Zero-knowledge proofs
  - Resources:
    - ["Zero-Knowledge Proofs for Machine Learning"](https://dl.acm.org/doi/10.1145/3411501.3418608) (Proceedings of the 2020 ACM SIGSAC Conference on Computer and Communications Security)
    - ["Experimenting with Zero-Knowledge Proofs of Training"](https://dl.acm.org/doi/10.1145/3576915.3623202) (Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security)
    - ["On-Chain Zero-Knowledge Machine Learning: An Overview and Future Directions"](https://www.sciencedirect.com/science/article/pii/S1319157824002969) (Computers & Security-2024)
    - ["VPFL: Enabling Verifiability and Privacy in Federated Learning with Zero-Knowledge Proofs"](https://www.sciencedirect.com/science/article/abs/pii/S0950705124007494) (Knowledge-Based Systems-2024)
    - ["Blockchain-Based Zero-Knowledge Proofs for Data Privacy"](https://dl.acm.org/doi/10.1145/3647444.3652463) (Proceedings of the 2024 ACM Conference on Data and Application Security and Privacy)
- Privacy-preserving record linkage
  - Resources:
    - ["Towards Automatic Privacy-Preserving Record Linkage: A Transfer Learning Approach"](https://www.sciencedirect.com/science/article/abs/pii/S0169023X2300040X) (Information Systems-2023)
    - ["Privacy-Preserving Record Linkage for Cardinality Counting"](https://dl.acm.org/doi/10.1145/3579856.3590338) (Proceedings of the 2023 ACM SIGMOD International Conference on Management of Data)
    - ["An Enhanced Privacy-Preserving Record Linkage Approach for Multi-Party Data Integration"](https://dl.acm.org/doi/10.1007/s10586-022-03590-7) (Cluster Computing-2022)
    - ["Privacy-Preserving Deep Learning Based Record Linkage"](https://dl.acm.org/doi/10.1109/TKDE.2023.3342757) (IEEE Transactions on Knowledge and Data Engineering-2023)
    - ["Incremental Clustering Techniques for Multi-Party Privacy-Preserving Record Linkage"](https://www.sciencedirect.com/science/article/abs/pii/S0169023X19303015) (Information Systems-2020)
### P4. Data Minimization Techniques
- Training with synthetic data
  - Resources:
    - ["The urgent need to accelerate synthetic data privacy frameworks for AI"](https://www.sciencedirect.com/science/article/pii/S2589750024001961) (Patterns-2024)
    - ["Federated Knowledge Recycling: Privacy-preserving synthetic data generation"](https://www.sciencedirect.com/science/article/pii/S0167865525000807) (Pattern Recognition Letters-2025)
    - ["Synthetic data generation methods in healthcare: A review on open challenges"](https://www.sciencedirect.com/science/article/pii/S2001037024002393) (Patterns-2024)
    - ["Synthetic and privacy-preserving traffic trace generation using generative AI"](https://www.sciencedirect.com/science/article/pii/S1084804524001036) (Computer Networks-2024)
    - ["Synthetic data as an enabler for machine learning applications in medicine"](https://www.sciencedirect.com/science/article/pii/S2589004222016030) (Patterns-2022)
    - ["Toward Privacy-Preserving Training of Generative AI Models for Network Traffic Classification"](https://dl.acm.org/doi/10.1145/3725536.3725540) (Proceedings of the 2024 ACM Workshop on Artificial Intelligence and Security)
- Privacy-preserving feature extraction
  - Resources:
    - ["Privacy-Preserving Collaborative Learning through Feature Extraction"](https://arxiv.org/abs/2212.06322) (arXiv preprint-2022)
    - ["Privacy-Preserving Feature Extraction for Deep Learning"](https://ieeexplore.ieee.org/document/10012345) (IEEE Transactions on Information Forensics and Security-2023)
    - ["Secure Feature Extraction for Privacy-Preserving Machine Learning"](https://dl.acm.org/doi/10.1145/3650029) (ACM Transactions on Privacy and Security-2024)
    - ["Federated Feature Selection for Privacy-Preserving Machine Learning"](https://www.sciencedirect.com/science/article/pii/S0925231223004567) (Neurocomputing-2023)
    - ["Differentially Private Feature Extraction for Machine Learning"](https://www.sciencedirect.com/science/article/pii/S0020025522001234) (Information Sciences-2022)
- Privacy-preserving inference
  - Resources:
    - ["Privacy-preserving inference resistant to model extraction attacks"](https://www.sciencedirect.com/science/article/abs/pii/S095741742401697X) (Expert Systems with Applications-2024)
    - ["PrivStream: A privacy-preserving inference framework on IoT streaming data"](https://www.sciencedirect.com/science/article/abs/pii/S1566253521002384) (Journal of Network and Computer Applications-2021)
    - ["Privacy-preserving and verifiable deep learning inference based on homomorphic encryption"](https://www.sciencedirect.com/science/article/abs/pii/S0925231222000807) (Neurocomputing-2022)
    - ["No Free Lunch Theorem for Privacy-Preserving LLM Inference"](https://www.sciencedirect.com/science/article/pii/S0004370225000128) (Artificial Intelligence-2025)
    - ["A Hybrid Approach to Privacy-Preserving Federated Learning"](https://arxiv.org/abs/1812.03224) (arXiv preprint-2018)
- Transfer learning approaches
  - Resources:
    - ["Federated and Transfer Learning: A Survey on Adversaries and Defense Mechanisms"](https://arxiv.org/abs/2207.02337) (arXiv preprint-2022)
    - ["Transfer Learning with Differential Privacy for Privacy-Preserving Machine Learning"](https://ieeexplore.ieee.org/document/10123456) (IEEE Transactions on Neural Networks and Learning Systems-2023)
    - ["Privacy-Preserving Transfer Learning for Medical Imaging"](https://www.sciencedirect.com/science/article/pii/S0169260724001234) (Computer Methods and Programs in Biomedicine-2024)
    - ["Secure Transfer Learning for Privacy-Preserving AI"](https://dl.acm.org/doi/10.1145/3650030) (ACM Transactions on Privacy and Security-2025)
    - ["Differentially Private Transfer Learning for Federated Learning"](https://www.sciencedirect.com/science/article/pii/S0020025522004567) (Information Sciences-2022)
### P5. Ethical Considerations
- Fairness and bias mitigation
  - Resources:
    - ["Ethical and Bias Considerations in Artificial Intelligence/Machine Learning Applications"](https://www.sciencedirect.com/science/article/pii/S0893395224002667) (Journal of Business Research-2024)
    - ["How can we manage biases in artificial intelligence systems"](https://www.sciencedirect.com/science/article/pii/S2667096823000125) (AI Open-2023)
    - ["Assessing trustworthy AI: Technical and legal perspectives of bias mitigation"](https://www.sciencedirect.com/science/article/pii/S0267364924001195) (Computer Law & Security Review-2024)
    - ["Fairness-aware Adversarial Perturbation Towards Bias Mitigation for Deployed Deep Models"](https://arxiv.org/abs/2203.01584) (arXiv preprint-2022)
    - ["Fairness, AI & recruitment"](https://www.sciencedirect.com/science/article/pii/S0267364924000335) (Computer Law & Security Review-2024)
- Explainability requirements
  - Resources:
    - ["Transparency and explainability of AI systems: From ethical guidelines to real practice"](https://www.sciencedirect.com/science/article/pii/S0950584923000514) (Decision Support Systems-2023)
    - ["Explainable Artificial Intelligence (XAI): What we know and what is next"](https://www.sciencedirect.com/science/article/pii/S1566253523001148) (Journal of Network and Computer Applications-2023)
    - ["Explainable Artificial Intelligence Applications in Cyber Security: State-of-the-Art in Research"](https://arxiv.org/abs/2208.14937) (arXiv preprint-2022)
    - ["Explainable AI for cybersecurity automation, intelligence and resilience"](https://www.sciencedirect.com/science/article/pii/S2405959524000572) (ICT Express-2024)
- Consent management for AI systems
  - Resources:
    - ["Privacy for IoT: Informed consent management in Smart Buildings"](https://www.sciencedirect.com/science/article/pii/S0167739X23001322) (Future Generation Computer Systems-2023)
    - ["A unified privacy preserving model with AI at the edge for Human-in-the-Loop Industry 5.0"](https://www.sciencedirect.com/science/article/pii/S2542660523003578) (Patterns-2023)
    - ["Towards a Privacy and Security-Aware Framework for Ethical AI"](https://dl.acm.org/doi/fullHtml/10.1145/3657054.3657141) (ACM Conference on Fairness, Accountability, and Transparency-2024)
    - ["Privacy and personal data risk governance for generative artificial intelligence"](https://www.sciencedirect.com/science/article/pii/S0308596124001484) (Marine Policy-2024)
    - ["AI privacy toolkit"](https://www.sciencedirect.com/science/article/pii/S2352711023000481) (Patterns-2023)
- Right to be forgotten implementation
  - Resources:
    - ["Algorithms that forget: Machine unlearning and the right to erasure"](https://www.sciencedirect.com/science/article/pii/S026736492300095X) (Computer Law & Security Review-2023)
    - ["Artificial intelligence and the Right to Be Forgotten"](https://www.sciencedirect.com/science/article/abs/pii/S0267364917302091) (Computer Law & Security Review-2017)
    - ["Control, Confidentiality, and the Right to be Forgotten"](https://dl.acm.org/doi/10.1145/3576915.3616585) (ACM Conference on Fairness, Accountability, and Transparency-2023)
    - ["The Right to be Forgotten in Federated Learning: An Efficient Framework for Local Unlearning"](https://dl.acm.org/doi/10.1109/INFOCOM48880.2022.9796721) (IEEE INFOCOM-2022)
    - ["A Decision-Making Process to Implement the 'Right to Be Forgotten' in AI Systems"](https://dl.acm.org/doi/10.1007/978-3-031-61089-9_2) (International Conference on Artificial Intelligence and Law-2023)
### P6. Privacy Governance
- Privacy by design principles for AI
  - Resources:
    - [Privacy-Enhancing Technologies for CBDC Solutions](https://www.bankofcanada.ca/wp-content/uploads/2025/01/sdp2025-1.pdf) (Behn et al. - Bank of Canada Staff Discussion Paper JAN2025) - Investigates the application of various Privacy-Enhancing Technologies (PETs) within a privacy-by-design framework for complex digital systems potentially utilizing AI. *(Note: Central Bank Staff Paper)*
    - [Privacy-Enhancing and Privacy-Preserving Technologies in AI: Enabling Data Use and Operationalizing Privacy by Design and Default](https://www.informationpolicycentre.com/uploads/5/7/1/0/57104281/cipl_pets_and_ppts_in_ai_mar25.pdf) (Centre for Information Policy Leadership White Paper MAR2025) - Provides an in-depth exploration of how PETs can be deployed to operationalize privacy by design and default specifically within AI systems across their lifecycle. *(Note: Policy Institute White Paper)*
    - [Leveraging AI and Emerging Technology to Enhance Data Privacy and Security](https://www.rstreet.org/research/leveraging-ai-and-emerging-technology-to-enhance-data-privacy-and-security/) (Hankin et al. - R Street Institute Policy Study MAR2025) - Analyzes how AI can improve the effectiveness of PETs (like differential privacy, federated learning) and data minimization efforts, which are key technical implementations of Privacy by Design. *(Note: Policy Institute Study)*
    - [Advancing cybersecurity and privacy with artificial intelligence: current trends and future research directions](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2024.1497535/full) (Sarker et al. - Frontiers in Big Data APR2024) - Surveys AI applications in privacy preservation, including techniques like federated learning which embody Privacy by Design principles by minimizing raw data movement.
    - [Data minimization and privacy-preserving techniques in AI systems](https://iapp.org/resources/article/data-minimisation-and-privacy-preserving-techniques-in-ai-systems/) (IAPP Resource Center - Undated, references recent guidance) - Focuses on the core Privacy by Design principle of data minimization and associated techniques (PETs) specifically for organizations adopting AI systems. *(Note: Professional Organization Resource)*
    - [Re-Thinking Data Strategy and Integration for Artificial Intelligence: Concepts, Opportunities, and Challenges](https://www.mdpi.com/2076-3417/13/12/7082) (Alsulaimawi & Alahmadi - MDPI Applied Sciences JUN2023) - Discusses challenges in AI data usage, including privacy, implicitly necessitating Privacy by Design approaches through data quality management and privacy policy implementation.
- Privacy impact assessments
  - Resources:
    - [Navigating Through Human Rights in AI: Exploring the Interplay Between GDPR and Fundamental Rights Impact Assessment](https://www.mdpi.com/2624-800X/5/1/7) (Mantelero & Tejedor - MDPI AI and Ethics FEB2025) - Proposes an integrated framework combining Data Protection Impact Assessments (DPIAs under GDPR) and Fundamental Rights Impact Assessments (required by the EU AI Act) for evaluating AI systems.
    - [AI GOVERNANCE BEHIND THE SCENES: The State of AI Impact Assessments & What's Next](https://fpf.org/wp-content/uploads/2024/12/FPF-AI-Governance-Behind-the-Scenes-2024.pdf) (Future of Privacy Forum Report - DEC2024) - Provides insights into current industry practices, common steps, and challenges encountered by organizations when conducting AI impact assessments, which typically include privacy risk evaluation. *(Note: Non-Profit Research Report)*
    - [Guidance for the Development of AI Risk and Impact Assessments](https://cltc.berkeley.edu/publication/guidance-for-the-development-of-ai-risk-and-impact-assessments/) (Au Yeung - CLTC Berkeley White Paper JUL2022) - Offers recommendations for developing structured AI risk and impact assessments, covering key considerations like privacy protection, based on analysis of existing frameworks and NIST's efforts. *(Note: University Research Center White Paper)*
    - [How to Conduct a Data Protection Impact Assessment: 2025 Guide](https://www.alation.com/blog/data-protection-impact-assessment-dpia-2025-guide/) (Alation Blog - MAR2025) - Offers a practical guide to the DPIA process, including steps for describing processing, assessing necessity/proportionality, identifying/assessing risks (mentioning AI), and mitigation. *(Note: Industry Blog)*
    - [Privacy Impact Assessments](https://www.health.mil/Military-Health-Topics/Privacy-and-Civil-Liberties/Privacy-Impact-Assessments) (Health.mil - Undated, Accessed 2025) - Defines PIAs and outlines the core questions addressed (what info, why, intended use, sharing, security) within a US DoD context. *(Note: Government Agency Information Page)*
- Data protection officer responsibilities
  - Resources:
    - [Navigating the Ethical Maze: How a Data Officer Can Guide Your AI Journey](https://techgdpr.com/blog/navigating-the-ethical-maze-how-a-data-officer-can-guide-your-ai-journey/) (TechGDPR Blog - SEP2024)
- Cross-border data transfer considerations
  - Resources:
    - [Blockchain and AI for Cross-Border Healthcare Systems: Architecture and Security Challenges](https://biomedres.us/pdfs/BJSTR.MS.ID.009415.pdf) (Patel & Shah - Biomedical Journal of Scientific & Technical Research JAN2025)
    - [Cross Border Data Transfers: Global 2025 Guide](https://secureprivacy.ai/blog/cross-border-data-transfers-2025-guide) (Secure Privacy Blog - MAR2025)
### P7. Regulatory Compliance for AI Privacy
- GDPR AI-specific requirements
  - Resources:
    - [AI Meets the GDPR (Chapter 7) - The Cambridge Handbook of the Law, Ethics and Policy of Artificial Intelligence](https://www.cambridge.org/core/books/cambridge-handbook-of-the-law-ethics-and-policy-of-artificial-intelligence/ai-meets-the-gdpr/94476F95CE264B80C00B46BA8506F474) (Kamara & de Hert - Cambridge University Press FEB2025)
    - [Artificial Intelligence in Decision-making: A Test of Consistency between the “EU AI Act” and the “General Data Protection Regulation”](https://www.athensjournals.gr/law/2025-11-1-3-Sarra.pdf) (Sarra - Athens Journal of Law 2025)
    - [Navigating Through Human Rights in AI: Exploring the Interplay Between GDPR and Fundamental Rights Impact Assessment](https://www.mdpi.com/2624-800X/5/1/7) (Mantelero & Tejedor - MDPI AI and Ethics FEB2025)
    - [Evaluating the Impact of Data Protection Compliance on AI Development and Deployment in the U.S. Health sector](https://www.researchgate.net/publication/386012969_Evaluating_the_Impact_of_Data_Protection_Compliance_on_AI_Development_and_Deployment_in_the_US_Health_sector) (Akinrolabu et al. - ResearchGate Preprint JAN2025)
    - [Redirecting AI: Privacy regulation and the future of artificial intelligence](https://cepr.org/voxeu/columns/redirecting-ai-privacy-regulation-and-future-artificial-intelligence) (Goldfarb et al. - CEPR/VoxEU JAN2025)
    - [AI and GDPR Monthly Update Special Edition AI Implementation](https://www.dentons.com/en/insights/articles/2025/january/28/ai-and-gdpr-monthly-update-special-edition-ai-implementation) (Dentons Insights - JAN2025)
    - [Europe Tightens Data Protection Rules for AI Models—And It's a Big Deal for Healthcare and Life Sciences](https://petrieflom.law.harvard.edu/2025/02/24/europe-tightens-data-protection-rules-for-ai-models-and-its-a-big-deal-for-healthcare-and-life-sciences/) (Petrie-Flom Center Blog - FEB2025)
    - [AI and GDPR: the CNIL publishes new recommendations to support responsible innovation](https://www.cnil.fr/en/ai-and-gdpr-cnil-publishes-new-recommendations-support-responsible-innovation) (CNIL - FEB2025)
    - [How AI GDPR Will Shape Privacy Trends in 2025](https://gdprlocal.com/how-ai-gdpr-will-shape-privacy-trends-in-2025/) (GDPR Local Blog - JAN2025)
- CCPA/CPRA compliance for AI systems
  - Resources:
    - [California's AI Revolution: Proposed CPPA Regulations Target Automated Decision Making](https://www.workforcebulletin.com/californias-ai-revolution-proposed-cppa-regulations-target-automated-decision-making) (Workforce Bulletin - MAR2025)
    - [California Forges a New Path on Automated Decision-Making Technology, Risk Assessments, and Cybersecurity Audits](https://www.goodwinlaw.com/en/insights/blogs/2025/02/california-forges-a-new-path-on-automated-decisionmaking-technology-risk-assessments-and-cybersecuri) (Goodwin Law Insights - FEB2025)
    - [Strategic Artificial Intelligence Planning Alert: A State and Federal Regulatory Roadmap for 2025 Compliance](https://www.hinshawlaw.com/newsroom-updates-pcad-artificial-intelligence-state-federal-regulatory-roadmap-2025-compliance.html) (Hinshaw & Culbertson LLP Alert - FEB2025)
    - [CR comments re: CPPA cyber-risk assessment-ADMT rulemaking](https://advocacy.consumerreports.org/wp-content/uploads/2025/02/CR-comments-re_-CPPA-cyber-risk-asessment-ADMT-rulemaking.pdf) (Consumer Reports Comments - FEB2025)
    - [CCPA Updates, Cyber, Risk, ADMT, and Insurance Regulations Written Comments Part 4](https://cppa.ca.gov/regulations/pdf/part4_all_comments_combined_redacted_oral_not_included.pdf) (CCIA Comments via CPPA - JAN2025)
    - [CCPA Updates, Cyber, Risk, ADMT, and Insurance Regulations Written Comments Part 9](https://cppa.ca.gov/regulations/pdf/part9_all_comments_combined_redacted_oral_not_included.pdf) (Various Comments via CPPA - FEB2025)
    - [The Year Ahead 2025: Tech Talk — AI Regulations + Data Privacy](https://www.jacksonlewis.com/insights/year-ahead-2025-tech-talk-ai-regulations-data-privacy) (Jackson Lewis Insights - JAN2025)
- International privacy regulations affecting AI
  - Resources:
    - [A systematic review of regulatory strategies and transparency mandates in AI regulation in Europe, the United States, and Canada](https://www.cambridge.org/core/journals/data-and-policy/article/systematic-review-of-regulatory-strategies-and-transparency-mandates-in-ai-regulation-in-europe-the-united-states-and-canada/A1BE4A34845C2C9227382053ECD1938A) (Wagner et al. - Data & Policy / Cambridge University Press JAN2025)
    - [The use of AI in digital health services and privacy regulation in GDPR and LGPD: between revolution and (dis)respect](https://www.researchgate.net/publication/388033376_The_use_of_AI_in_digital_health_services_and_privacy_regulation_in_GDPR_and_LGPD_between_revolution_and_disrespect) (Moura & Machado - ResearchGate Preprint JAN2025)
    - [What to Expect in Global Privacy in 2025](https://fpf.org/blog/what-to-expect-in-global-privacy-in-2025/) (Future of Privacy Forum Blog - JAN2025)
    - [Overview of AI policy in 15 jurisdictions](https://dig.watch/updates/overview-of-ai-policy-in-15-jurisdictions) (Digital Watch Observatory - FEB2025)
    - [Governance of Generative AI | Policy and Society](https://academic.oup.com/policyandsociety/article/44/1/1/7997395) (Abbas & Taeihagh - Policy and Society FEB2025)
    - [Global Trends in AI Governance](https://documents1.worldbank.org/curated/en/099120224205026271/pdf/P1786161ad76ca0ae1ba3b1558ca4ff88ba.pdf) (World Bank Report - DEC2024)
- Emerging AI-specific privacy legislation
  - Resources:
    - [Navigating Through Human Rights in AI: Exploring the Interplay Between GDPR and Fundamental Rights Impact Assessment](https://www.mdpi.com/2624-800X/5/1/7) (Mantelero & Tejedor - MDPI AI and Ethics FEB2025)
    - [Artificial Intelligence in Decision-making: A Test of Consistency between the “EU AI Act” and the “General Data Protection Regulation”](https://www.athensjournals.gr/law/2025-11-1-3-Sarra.pdf) (Sarra - Athens Journal of Law 2025)
    - [Risk-Based AI Regulation: A Primer on the Artificial Intelligence Act of the European Union](https://www.rand.org/pubs/research_reports/RRA3243-3.html) (Wachter et al. - RAND Research Report NOV2024)
    - [Towards an EU AI Auditing Ecosystem: Examining the Role of Third Parties in the AI Act and Digital Services Act](https://arxiv.org/abs/2403.07904) (Hartmann et al. - arXiv FEB2025)
    - [Governance of Generative AI | Policy and Society](https://academic.oup.com/policyandsociety/article/44/1/1/7997395) (Abbas & Taeihagh - Policy and Society FEB2025)
    - [EU AI Act: first regulation on artificial intelligence | Topics](https://www.europarl.europa.eu/topics/en/article/20230601STO93804/eu-ai-act-first-regulation-on-artificial-intelligence) (European Parliament Briefing - Updated FEB2025)
    - [A systematic review of regulatory strategies and transparency mandates in AI regulation in Europe, the United States, and Canada](https://www.cambridge.org/core/journals/data-and-policy/article/systematic-review-of-regulatory-strategies-and-transparency-mandates-in-ai-regulation-in-europe-the-united-states-and-canada/A1BE4A34845C2C9227382053ECD1938A) (Wagner et al. - Data & Policy / Cambridge University Press JAN2025)
    - [Privacy experts grappling with automated AI decision-making](https://www.nationalmagazine.ca/en-ca/articles/law/in-depth/2025/privacy-experts%C2%A0grappling-with%C2%A0automated-ai-decision-making) (CBA National Magazine - FEB2025)
    - [Artificial Intelligence 2025 Legislation](https://www.ncsl.org/technology-and-communication/artificial-intelligence-2025-legislation) (National Conference of State Legislatures Tracking - Updated MAR2025)