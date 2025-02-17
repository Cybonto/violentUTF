# Guideline on the Red Teaming of Generative AI Systems

# Guideline on the Red Teaming of Generative AI Systems

- [1. Target System Description](#1-target-system-description)
    - [1. System Architecture](#1-system-architecture)
        - [System Flows](#system-flows)
        - [Model Type and Architecture](#model-type-and-architecture)
        - [Training Data and Preprocessing](#training-data-and-preprocessing)
        - [Deployment Environment and Infrastructure](#deployment-environment-and-infrastructure)
    - [2. Functionality and Use Cases](#2-functionality-and-use-cases)
        - [Intended Use Cases](#intended-use-cases)
        - [User Personas](#user-personas)
        - [Input and Output](#input-and-output)
        - [User Roles and Access Controls](#user-roles-and-access-controls)
    - [3. Data Security and Privacy](#3-data-security-and-privacy)
        - [Data Handling Procedures](#data-handling-procedures)
        - [Privacy Measures](#privacy-measures)
        - [Compliance Requirements](#compliance-requirements)
    - [4. Security Measures](#4-security-measures)
        - [Authentication and Authorization](#authentication-and-authorization)
        - [Vulnerability Management](#vulnerability-management)
        - [Incident Response Plan](#incident-response-plan)
    - [5. Third-Party Dependencies](#5-third-party-dependencies)
        - [External APIs and Libraries](#external-apis-and-libraries)
        - [Vendor Risk Management](#vendor-risk-management)
- [2. Target AI Model Description](#2-target-ai-model-description)
    - [2a. Core Model Information](#2a-core-model-information)
        - [1. Model Name and Version](#1-model-name-and-version)
        - [2. Provider/Developer](#2-providerdeveloper)
        - [3. Model Type](#3-model-type)
        - [4. Release Date](#4-release-date)
        - [5. Intended Use Cases (as stated by the provider)](#5-intended-use-cases-as-stated-by-the-provider)
        - [6. Out-of-Scope Use Cases (as stated by the provider, *and* as inferred by you)](#6-out-of-scope-use-cases-as-stated-by-the-provider-and-as-inferred-by-you)
        - [7. Data Summary (High-Level)](#7-data-summary-high-level)
            - [Training Data Source Description (if available)](#training-data-source-description-if-available)
            - [Data Collection Period (if available)](#data-collection-period-if-available)
            - [Data Preprocessing Description (if available)](#data-preprocessing-description-if-available)
            - [Known Data Limitations (as stated, *and* as inferred)](#known-data-limitations-as-stated-and-as-inferred)
    - [2b. Performance and Evaluation](#2b-performance-and-evaluation)
        - [8. Performance Metrics (as reported by the provider)](#8-performance-metrics-as-reported-by-the-provider)
        - [9. Evaluation Datasets (as described by the provider)](#9-evaluation-datasets-as-described-by-the-provider)
        - [10. Benchmark Comparisons (if available)](#10-benchmark-comparisons-if-available)
        - [11. Independent Evaluations (if available)](#11-independent-evaluations-if-available)
        - [12. Known Limitations (Performance-related)](#12-known-limitations-performance-related)
        - [13. Uncertainty Quantification (if applicable)](#13-uncertainty-quantification-if-applicable)
    - [2c. Safety, Bias, and Alignment](#2c-safety-bias-and-alignment)
        - [14. Bias Mitigation Strategies (as claimed by the provider)](#14-bias-mitigation-strategies-as-claimed-by-the-provider)
        - [15. Safety Evaluations (as described by the provider)](#15-safety-evaluations-as-described-by-the-provider)
        - [16. Alignment Efforts (as claimed by the provider)](#16-alignment-efforts-as-claimed-by-the-provider)
        - [17. Known Biases (as reported *and* as inferred)](#17-known-biases-as-reported-and-as-inferred)
        - [18. Potential Harms and Misuse](#18-potential-harms-and-misuse)
        - [19. Red Teaming Results (if available)](#19-red-teaming-results-if-available)
        - [20. Content Policies and Usage Guidelines](#20-content-policies-and-usage-guidelines)
    - [2d. Access and Usage](#2d-access-and-usage)
        - [21. Access Method](#21-access-method)
        - [22. Terms of Service](#22-terms-of-service)
        - [23. Pricing Model](#23-pricing-model)
        - [24. Monitoring and Auditing (as claimed by the provider)](#24-monitoring-and-auditing-as-claimed-by-the-provider)
        - [25. User Feedback Mechanisms](#25-user-feedback-mechanisms)
    - [2e. Caveats and Limitations](#2e-caveats-and-limitations)
        - [26. Transparency Limitations](#26-transparency-limitations)
        - [27. Unverified Claims](#27-unverified-claims)
        - [28. Open Questions and Concerns](#28-open-questions-and-concerns)
- [3. The Threat Model](#3-the-threat-model)
    - [3a. Key Assumptions](#3a-key-assumptions)
        - [Common Assumptions](#common-assumptions)
        - [Unique Assumptions](#unique-assumptions)
    - [3b. Pre LLM Inference Phase](#3b-pre-llm-inference-phase)
        - [Attack Vectors](#attack-vectors)
        - [Tactics, Techniques, and Procedures (TTPs)](#tactics-techniques-and-procedures-ttps)
        - [Risks](#risks)
    - [3c. LLM Inference Phase](#3c-llm-inference-phase)
        - [Attack Vectors](#attack-vectors-1)
        - [Tactics, Techniques, and Procedures (TTPs)](#tactics-techniques-and-procedures-ttps-1)
        - [Risks](#risks-1)
    - [3d. Post LLM Inference Phase](#3d-post-llm-inference-phase)
        - [Attack Vectors](#attack-vectors-2)
        - [Tactics, Techniques, and Procedures (TTPs)](#tactics-techniques-and-procedures-ttps-2)
        - [Risks](#risks-2)
- [4. Scoping](#4-scoping)
    - [4a. Risk Prioritization](#4a-risk-prioritization)
    - [4b. Constraints](#4b-constraints)
    - [4c. Red Teaming Methodologies](#4c-red-teaming-methodologies)
    - [4d. Success Criteria](#4d-success-criteria)
- [5. The Main Pipeline](#5-the-main-pipeline)
    - [5a. Initialization](#5a-initialization)
    - [5b. Dataset Selection/Creation](#5b-dataset-selectioncreation)
    - [5c. Prompt Conversion (Optional)](#5c-prompt-conversion-optional)
    - [5d. Prompt Sending](#5d-prompt-sending)
    - [5e. Scoring](#5e-scoring)
    - [5f. Iteration and Refinement](#5f-iteration-and-refinement)
    - [5g. Reporting](#5g-reporting)
- [6. Operational Details](#6-operational-details)
    - [6a. Tracing and Logging](#6a-tracing-and-logging)
    - [6b. Automation](#6b-automation)
        - [Schedules](#schedules)
        - [Triggers](#triggers)
    - [6c. Reports and Dashboards](#6c-reports-and-dashboards)
    - [6d. Integration](#6d-integration)
    
## 1. Target System Description
To effectively describe a production Generative AI system for risk assessment and penetration testing, we first need to understand the basics of the system.
- **1. System Architecture:**
  - **System Flows:** Present a diagram of the system flows. 
  - **Model Type and Architecture:** Specify the type of Generative AI model used (e.g., LLM, GAN) and its architecture, including the number of layers, parameters, and any specific design choices.
  - **Training Data and Preprocessing:** Describe the data used to train the model, including its source, size, and any preprocessing steps.
  - **Deployment Environment and Infrastructure:** Describe the infrastructure and environment where the model is deployed (e.g., cloud platform, on-premises servers).
- **2. Functionality and Use Cases:**
  - **Intended Use Cases:** Clearly define the intended applications and functionalities of the AI system.
  - **User Personas:** Define representative user personas. Adversarial testing should consider how different users (with varying intentions, technical skills, and backgrounds) might try to misuse the system.
  - **Input and Output:** Describe the types of inputs the system accepts and the outputs it generates.
  - **User Roles and Access Controls:** Specify different user roles and their access permissions within the system.
- **3. Data Security and Privacy:**
  - **Data Handling Procedures:** Detail how the system handles sensitive data, including storage, processing, and access controls.
  - **Privacy Measures:** Describe any privacy-preserving techniques employed, such as data anonymization or differential privacy.
  - **Compliance Requirements:** Specify any relevant data privacy regulations the system must comply with (e.g., GDPR, CCPA).
- **4. Security Measures:**
  - **Authentication and Authorization:** Describe the mechanisms used to verify user identities and control access to the system.
  - **Vulnerability Management:** Detail the processes for identifying, assessing, and mitigating security vulnerabilities.
  - **Incident Response Plan:** Outline the procedures for responding to security incidents and breaches.
- **5. Third-Party Dependencies:**
  - **External APIs and Libraries:** List any third-party APIs or libraries used by the system .
  - **Vendor Risk Management:** Describe any processes for assessing and managing risks associated with third-party vendors .

## 2. Target AI Model Description
This section assumes you are dealing with proprietary models you *don't* own (and therefore have limited direct access to).  This is a crucial distinction, as your ability to assess and document will be constrained. The focus shifts from direct testing and internal details to a combination of publicly available information, vendor-provided documentation, and critical analysis of claims. If you leverage more than one model in your system, repeate the below sections for each model.
### 2a. Core Model Information:
1.  **Model Name and Version:**  The specific, official name and version number. This is essential for tracking and referencing.
2.  **Provider/Developer:**  The company or organization that created and maintains the model.  This helps with accountability and finding further information.
3.  **Model Type:** (e.g., Large Language Model, Image Recognition, Recommendation System, etc.) - Be specific (e.g., "Transformer-based LLM," "Convolutional Neural Network for Image Classification").
4.  **Release Date:**  When was the model version released?  Helps assess its age and potential for obsolescence or known issues.
5.  **Intended Use Cases (as stated by the provider):** What applications does the provider *claim* the model is designed for?  This is your starting point for evaluating appropriate use.
6.  **Out-of-Scope Use Cases (as stated by the provider, *and* as inferred by you):**  What uses does the provider explicitly *discourage*?  Equally important, what uses might be technically possible but ethically or practically problematic, even if the provider doesn't mention them?  This is where your critical analysis comes in.  Think about potential misuse.
7.  **Data Summary (High-Level):**
  - **Training Data Source Description (if available):** What *type* of data was used (text, images, audio, etc.)?  What are the *claimed* sources (e.g., "publicly available web data," "proprietary customer data")? Be skeptical and note if the description is vague.
  - **Data Collection Period (if available):**  When was the training data collected? This is important for identifying potential biases related to outdated information.
  - **Data Preprocessing Description (if available):**  How was the data cleaned, filtered, or transformed? Look for mentions of bias mitigation techniques.  Lack of detail here is a red flag.
  - **Known Data Limitations (as stated, *and* as inferred):**  Does the provider acknowledge any limitations of the training data?  What biases might be present based on the data source description (e.g., overrepresentation of certain demographics, languages, or viewpoints)? This is a key area for safety and alignment.
### 2b. Performance and Evaluation
8.  **Performance Metrics (as reported by the provider):** What metrics are used to evaluate performance (e.g., accuracy, precision, recall, F1-score, BLEU score, ROUGE score)?  Are these metrics appropriate for the intended use cases?
9.  **Evaluation Datasets (as described by the provider):**  What datasets were used to evaluate the model?  Are these datasets publicly available, or are they proprietary?  Are they representative of real-world scenarios?  Lack of transparency here is a major concern.
10. **Benchmark Comparisons (if available):**  How does the model's performance compare to other models (including open-source models, if relevant)?  Are these comparisons fair and objective?  Be wary of cherry-picked benchmarks.
11. **Independent Evaluations (if available):**  Have any third-party organizations evaluated the model?  What were their findings?  This is crucial for verifying provider claims.  Search for academic papers, industry reports, and reputable news articles.
12. **Known Limitations (Performance-related):**  What are the *acknowledged* performance limitations of the model?  Under what conditions does it perform poorly?  What types of inputs is it known to struggle with?
13. **Uncertainty Quantification (if applicable):** Does the model provide any measure of uncertainty or confidence in its outputs?  If so, how is this measured and reported? This is particularly important for high-stakes applications.
### 2c. Safety, Bias, and Alignment
14. **Bias Mitigation Strategies (as claimed by the provider):**  What steps, if any, does the provider claim to have taken to mitigate bias in the model?  (e.g., data augmentation, adversarial training, fairness-aware algorithms).  Be skeptical and look for concrete details, not just vague statements.
15. **Safety Evaluations (as described by the provider):**  What safety evaluations have been performed?  (e.g., red teaming, adversarial robustness testing).  What were the results?  Look for specifics, not just assurances.
16. **Alignment Efforts (as claimed by the provider):** What efforts, if any, have been made to align the model with human values and intentions? (e.g., reinforcement learning from human feedback, constitutional AI).  This is often the least transparent area, so critical analysis is essential.
17. **Known Biases (as reported *and* as inferred):**  What biases have been identified in the model, either by the provider or by independent researchers?  What are the potential consequences of these biases?  This requires active searching and critical thinking. Consider:
  - **Demographic biases:**  Does the model perform differently for different demographic groups (e.g., race, gender, age)?
  - **Linguistic biases:**  Does the model favor certain languages or dialects?
  - **Cultural biases:**  Does the model reflect the values or perspectives of a particular culture?
  - **Confirmation bias:**  Does the model tend to reinforce existing beliefs or stereotypes?
18. **Potential Harms and Misuse:**  What are the potential harms that could result from the use of the model, even if used as intended?  What are the potential ways the model could be misused?  This is a crucial thought exercise.  Consider:
  - **Disinformation and propaganda:**  Could the model be used to generate fake news or manipulate public opinion?
  - **Discrimination and unfairness:**  Could the model be used to make decisions that unfairly disadvantage certain groups?
  - **Privacy violations:**  Could the model be used to infer sensitive information about individuals?
  - **Security vulnerabilities:**  Could the model be exploited by malicious actors?
19. **Red Teaming Results (if available):** If the provider mentions red teaming, what were the specific findings and how were they addressed?  Lack of detail here is a significant warning sign.
20. **Content Policies and Usage Guidelines:** Does the provider have clear content policies and usage guidelines that restrict harmful or unethical uses of the model? Are these guidelines enforceable?
### 2d. Access and Usage
21. **Access Method:**  How is the model accessed (e.g., API, cloud service, downloadable software)?
22. **Terms of Service:**  What are the terms of service for using the model?  Do these terms address safety, bias, and misuse?  Do they limit liability for the provider?
23. **Pricing Model:** How is the usage model related with price?
24. **Monitoring and Auditing (as claimed by the provider):**  Does the provider monitor the use of the model for misuse?  Are there any auditing mechanisms in place?  This is often difficult to verify.
25. **User Feedback Mechanisms:**  Is there a way for users to report problems or concerns about the model?
#### 2e. Caveats and Limitations
26. **Transparency Limitations:**  Explicitly state the limitations of your assessment due to your lack of direct access to the model and its internal workings.  Acknowledge that your information is based on publicly available data and provider claims.
27. **Unverified Claims:**  Clearly identify any claims made by the provider that you were unable to verify independently.
28. **Open Questions and Concerns:**  List any remaining questions or concerns you have about the model's safety, bias, and alignment.  This is where you highlight areas that require further investigation.

## 3. The Threat Model
This section outlines a structured approach to building a threat model specific to your Generative AI system.  It emphasizes a phased approach, aligning with the lifecycle of an AI model's interaction with input and output.
### 3a. Key Assumptions
This subsection is *critical*.  It defines the boundaries of your threat model.  You're explicitly stating what you *assume* to be true, which helps focus your efforts and clarifies limitations.
#### Common Assumptions
These are assumptions likely to be shared across many Generative AI systems.
- **System Access:**
  - Who has legitimate access to the system (users, administrators, developers)?  What are their roles and corresponding privileges? Are there different levels of access (e.g., read-only, query, modify)?
  - Refer to Section 1 of your guideline (Target System Description), especially "User Roles and Access Controls." Assume these controls are *correctly implemented* for the purpose of this threat model (though you might red-team their implementation separately).
  - Example: "We assume that users can only interact with the system through the defined API endpoints, and cannot directly access the underlying model or training data."
- **Attacker Knowledge:**
  - What level of knowledge does the attacker have about the system?  Is it a black-box (no internal knowledge), grey-box (partial knowledge, e.g., API documentation), or white-box (full access to model architecture, weights, etc.) scenario?
  - This is crucial.  Consider different attacker profiles. A script kiddie has different capabilities than a nation-state actor.  Reference MITRE ATLAS's "ML Model Access" tactic (AML.TA0000) and its techniques.
  - Example: "We assume a black-box attack scenario where the attacker has access to the public API but no internal knowledge of the model."  OR  "We assume a grey-box scenario where the attacker has access to the API documentation and published research papers describing the model type."
- **Attacker Capabilities:**
  - What resources does the attacker have?  Can they generate a large number of queries?  Do they have access to specialized hardware or software?  Can they collude with other attackers?
  - Think about computational power, budget, technical expertise, and access to datasets.  Consider limitations imposed by rate limiting or other system defenses (even if imperfect).
  - Example: "We assume the attacker has access to moderate computational resources (e.g., a standard desktop computer with a GPU) and can make up to 1000 queries per day." OR "We assume the attacker is a well-resourced state actor with access to significant computational power."
- **Data Integrity (Initial):**
  - Do you assume the initial training data is "clean" (free from intentional poisoning or significant unintentional bias)?
  - This is a common starting point, but it's important to acknowledge.  If you *don't* assume clean data, this significantly expands your threat model.
  - Example: "We assume the model was initially trained on a curated dataset that, while not perfectly unbiased, was not intentionally poisoned."
- **System Security (Non-AI Specific):**
  - Are you assuming the underlying infrastructure (servers, networks, databases) is secure, or are you including traditional cybersecurity threats in your AI-specific threat model?
  - It's often best to *separate* these concerns. Focus this section on threats *specific* to the AI system. Reference relevant MITRE ATT&CK techniques if necessary, but don't duplicate a full cybersecurity threat model.
  - Example: "We assume standard cybersecurity best practices are in place, and this threat model focuses on threats specific to the AI/ML components."
#### Unique Assumptions
    These are assumptions specific to *your* system and its context.
  - **Model-Specific Behavior:**
    - Are there any known, expected behaviors of your specific model that could be exploited?  (e.g., a known bias, a tendency to hallucinate in certain domains, sensitivity to specific input types).
    - This is where your understanding of *your* model (Section 2 of your guideline) is vital.  Document known limitations.
    - Example: "We assume the model may exhibit [specific known bias] due to limitations in the training data, and this bias could be exploited."
  - **Deployment Environment:**
    - Are there any specific aspects of your deployment environment that create unique vulnerabilities? (e.g., running on edge devices with limited security, interacting with a specific third-party API).
    - Consider the entire system flow (Section 1).
    - Example: "We assume the model is deployed on a cloud platform with standard security measures, but the API is publicly accessible."
  - **Intended Use & Misuse:**
    - What are the *intended* uses, and what are the most likely or impactful *unintended* uses (misuse)?
    - Think creatively about how the system *could* be abused, even if it's not designed for that.  Consider the "Potential Harms and Misuse" section (point 18) from your model description.
    - Example: "We assume the system is intended for [intended use], but could be misused to generate [specific type of harmful content]."
  - **Data Sensitivity**
    - What data will be used as an input? Is this data sensitive? Are there any PII that will be used?
    - Review section 1.3.
    - Example: "The model may receive sensitive data through user inputs. The model should handle this information according to established security procedures".
  - **Mitigation Measures in Place**
    - What security and prevention protocols are assumed to be in place already?
    - Review section 1.4.
    - Example: "The model will have authentication protocols in place to verify the user's identity."
### 3b. Pre LLM Inference Phase
This phase focuses on threats *before* the user input reaches the core LLM.
- **Attack Vectors**
  - How can an attacker interact with the system *before* the LLM processes the input?  What are the entry points?
  - Consider data input mechanisms (API, web form, file upload), any pre-processing steps, and any connected systems.
  - Examples:
    - Malicious file upload (if the system accepts files).
    - Tampering with data in transit (if data is fetched from an external source).
    - Compromising a third-party component used in pre-processing.
    - Exploiting vulnerabilities in the API gateway.
    - Data poisoning attacks (if the system continuously learns or uses user-provided data for training).  Reference MITRE ATLAS techniques like "Poison Data" (AML.T0015).
- **Tactics, Techniques, and Procedures (TTPs)**
  - What specific MITRE ATLAS and ATT&CK techniques are relevant to this phase?  How might an attacker carry them out against *your* system?
  - Focus on techniques related to:
  - Reconnaissance: Learning about the system (e.g., "Victim Research" - AML.T0007 in ATLAS).
  - Resource Development: Preparing for the attack (e.g., "Acquire ML Artifacts" - AML.T0009, "Develop Adversarial ML Capabilities" - AML.T0001 in ATLAS).
  - Initial Access: Gaining a foothold (e.g., "Supply Chain Compromise" - AML.T0010 in ATLAS, or various ATT&CK Initial Access techniques).
  - Data Collection/Staging
  - Example: An attacker might use "Supply Chain Compromise" (AML.T0010) by injecting malicious code into a library used by your pre-processing pipeline.
- **Risks**
  - What are the potential *consequences* if an attacker succeeds in this phase?  What's the impact on confidentiality, integrity, and availability?
  - Consider the impact on the model, the data, the system, and the users.  Think about both short-term and long-term effects. Reference the NIST AI RMF's discussion of risks.
  - Examples:
  - Data Poisoning: The model's accuracy and reliability are degraded over time.
  - Data Leakage: Sensitive information used in pre-processing is exposed.
  - System Compromise: The attacker gains control of the system or parts of it.
  - Denial of Service: The pre-processing pipeline is overloaded or disabled.
### 3c. LLM Inference Phase
This phase focuses on threats *during* the LLM's processing of the input.
- **Attack Vectors**
  - How can an attacker influence the LLM's output *during* inference?
  - This is primarily about *prompt manipulation*.
  - Examples:
  - Prompt Injection: Crafting prompts that cause the LLM to ignore its instructions or produce unintended outputs. (e.g., "Ignore previous instructions and...")
  - Prompt Leaking: Extracting the original prompt or system instructions.
  - Jailbreaking: Bypassing safety filters or restrictions.
  - Token Smuggling: Encoding malicious instructions in a way that bypasses input filters.
  - Indirect Prompt Injection: Affecting the model with data from external source (e.g., website).
  - Excessive Resource Consumption: (e.g. token usage, memory and compute)
- **Tactics, Techniques, and Procedures (TTPs)**
  - What specific techniques might an attacker use to manipulate the prompt or the LLM's internal state?
  - Refer to MITRE ATLAS techniques related to:
  - "ML Model Access" (AML.TA0000) and "ML Attack Staging" (AML.TA0001), but focus on those relevant to *inference*, not training.
  - "Craft Adversarial Examples (Black Box)" (AML.T0005) - Very relevant to prompt injection.
  - "Discover Model Ontology" (AML.T0017) - Relevant to understanding how to craft effective prompts.
  - Examples:
    - An attacker might use carefully crafted prefixes or suffixes to their prompt to influence the LLM's output.
    - An attacker might try to inject special characters or escape sequences to bypass input sanitization.
    - An attacker might try few-shot prompting with malicious examples.
- **Risks**
  - What are the consequences of successful prompt manipulation?
  - Think about the types of harmful output the LLM could generate.
  - Examples:
  - Generation of Harmful Content: Toxic language, hate speech, misinformation, etc.
  - Exposure of Sensitive Information: Revealing private data from the training set or system prompts.
  - Violation of System Policies: Generating outputs that violate content guidelines or terms of service.
  - Reputational Damage: Eroding trust in the system and its provider.
  - System Resource Exhaustion
### 3d. Post LLM Inference Phase
This phase focuses on threats *after* the LLM has generated its output, but *before* it's presented to the user or used by downstream systems.
- **Attack Vectors**
  - How can an attacker interfere with the output *after* it's generated by the LLM?
  - Consider output handling, filtering, logging, and any post-processing steps.
  - Examples:
    - Tampering with the output in transit (if it's sent over a network).
    - Exploiting vulnerabilities in the output display mechanism (e.g., cross-site scripting).
    - Compromising a logging system to inject false information or delete evidence.
    - Manipulating any post-processing steps (e.g., sentiment analysis, summarization).
- **Tactics, Techniques, and Procedures (TTPs)**
  - What techniques might an attacker use to modify or misuse the LLM's output?
  -  Think about techniques related to:
  - Defense Evasion: Bypassing output filters.
  - Exfiltration: Stealing the output.
  - Impact: Causing harm with the modified output.
    - Example: An attacker might use "code injection" (if the output is used to generate code) or "cross-site scripting" (if the output is displayed in a web application). Refer to relevant MITRE ATT&CK techniques.
- **Risks**
  - What are the consequences of successful output manipulation?
  - Similar to the previous phase, but now consider the impact of the *modified* output.
  - Examples:
  - Dissemination of Harmful Content:**  Even if the LLM *didn't* generate it, the modified output could be harmful.
  - Incorrect Decisions:**  If the output is used to make decisions, those decisions could be wrong.
  - System Instability:**  Malicious code in the output could crash or compromise downstream systems.
  - Loss of Auditability:**  If logs are tampered with, it becomes difficult to track down the source of problems.

## 4. Scoping
This section guides the process of narrowing down the broad threat landscape identified in Section 3 (The Threat Model) into a manageable and impactful scope for your red teaming exercise.  It covers prioritizing risks, defining the boundaries of the engagement, selecting appropriate methodologies, and establishing clear success criteria.
### 4a. Risk Prioritization
This subsection focuses on identifying and prioritizing the most critical risks to your Generative AI system.  It's impossible to test *everything*, so prioritization is essential. The output of this subsection should be a prioritized list of 3-5 top-priority threat scenarios. These will be the focus of your red teaming exercise.
1.  **Leverage the Threat Model (Section 3):**
  - Review the "Risks" subsections (3b, 3c, 3d) within your threat model.  These sections should have already identified potential consequences of various attacks.
  - Consider the "Key Assumptions" (3a).  Are there any assumptions that, if violated, would lead to particularly severe consequences?
2.  **Risk Assessment Matrix (Probability x Impact):**
  - Create a risk assessment matrix. This is a standard tool for prioritizing risks.
  - For each risk identified in your threat model, assess:
  - **Probability:** How likely is this attack to be attempted AND succeed, given your assumptions about attacker capabilities and existing security measures? Consider using a scale (e.g., Very Low, Low, Medium, High, Very High).
  - **Impact:** If this attack succeeds, what is the severity of the consequences? Consider impacts on:
      - **Confidentiality:** Exposure of sensitive data (user data, training data, model internals).
      - **Integrity:** Corruption of the model, data, or outputs.
      - **Availability:** Disruption of service, denial of access.
      - **Reputation:** Damage to the organization's brand and user trust.
      - **Financial:** Direct monetary losses, fines, legal costs.
      - **Legal/Compliance:** Violation of regulations (GDPR, CCPA, etc.).
      - **Safety:** Physical harm or endangerment (if the AI system controls physical devices or influences real-world actions).
        - Use a similar scale (e.g., Very Low, Low, Medium, High, Very High).
  - Plot each risk on the matrix. Risks in the high-probability, high-impact quadrant should be your top priorities.
3.  **Consider AI RMF Characteristics:**
  - Refer back to the NIST AI RMF trustworthiness characteristics (Valid & Reliable, Safe, Secure & Resilient, Accountable & Transparent, Explainable and Interpretable, Privacy-enhanced, Fair with harmful bias managed).
  - Which of these characteristics are *most critical* for *your specific* AI system and its intended use cases?  A failure in which characteristic would be most damaging?
  - For example, a medical diagnosis system would prioritize "Safe," "Valid & Reliable," and "Explainable."  A content moderation system might prioritize "Fair" and "Accountable & Transparent."
4.  **Consider OECD AI Principles:**
  - Similar to the NIST framework, consider which of the OECD AI Principles are most relevant to your system.  A violation of which principle would be most problematic?
5.  **Prioritize Based on Specific Threat Scenarios:**
  - Don't just list abstract risks (e.g., "data poisoning").  Develop *concrete threat scenarios* based on your threat model.  Examples:
  - **Scenario 1:** "An attacker uses prompt injection to bypass content filters and cause the chatbot to generate racist and offensive content, leading to reputational damage and user complaints." (High Impact, Medium Probability)
  - **Scenario 2:** "An attacker uses a model inversion attack to extract snippets of copyrighted material from the training data, leading to legal action." (Medium Impact, Low Probability)
  - **Scenario 3:** "An attacker floods the system with malicious prompts designed to consume excessive resources, causing a denial of service." (High Impact, High Probability)
  - Prioritize these scenarios based on your risk assessment matrix.
6.  **Document Your Prioritization Rationale:**
  - Clearly explain *why* you prioritized certain risks over others.  This documentation is essential for justifying your scoping decisions and for future reference.
### 4b. Constraints
This subsection defines the limitations and boundaries of your red teaming exercise.  It's about being realistic and upfront about what you *can't* test. The output of this subsection should be a clear and concise list of constraints that define the boundaries of the red teaming exercise.
1.  **Time Constraints:**
  - How much time is allocated for the red teaming exercise? This is a major limiting factor.  A week-long engagement will have a much narrower scope than a month-long one.
  - Be realistic about what can be achieved within the given timeframe.
2.  **Budgetary Constraints:**
  - What is the budget for the exercise? This impacts the resources available (personnel, tools, cloud computing costs).
  - Will you need to purchase specialized tools or services?
  - Are there limits on the number of API calls you can make to a paid service?
3.  **Personnel Constraints:**
  - How many people are on the red team? What are their skill sets and expertise (e.g., prompt engineering, reverse engineering, machine learning, cybersecurity)?
  - Do you have access to individuals with specialized knowledge of the target AI system?
4.  **Legal and Ethical Constraints:**
  - What are the legal and ethical boundaries of the exercise?
  - Are there restrictions on the types of attacks you can perform (e.g., no social engineering, no attacks on production systems)?
  - Do you need to obtain consent from users or stakeholders before testing?
  - Are there any data privacy regulations that limit your access to data or the types of analysis you can perform?
  - Will you need to anonymize or redact any data collected during the exercise?
  - **IMPORTANT:** Always prioritize ethical considerations.  The goal is to improve security, not to cause harm.
5.  **Technical Constraints:**
  - What are the technical limitations of the testing environment?
  - Do you have access to the same infrastructure and resources as the production system?  If not, how will this affect your testing?
  - Are there any limitations on the tools or techniques you can use? (e.g., restrictions on network traffic, inability to install certain software).
  - Are there any rate limits or other restrictions on API calls?
6. **Scope of Access Limitations:**
    * What elements are considered out of scope for the purposes of this specific exercise?
    * Are there any specific components or functionalities of the AI system that are *off-limits* for testing? (e.g., a critical database, a third-party service).
  - Clearly define what is *in scope* and *out of scope*.
### 4c. Red Teaming Methodologies
This subsection focuses on selecting the specific *methods* you'll use to test the prioritized risks within the defined constraints. The output of this subsection should be a detailed plan outlining *how* you will test each of your prioritized threat scenarios, including specific methodologies, tools, and resources.
1.  **Match Methodologies to Risks:**
  - For each of your top-priority threat scenarios (from 4a), select one or more red teaming methodologies that are best suited to test that scenario.
  - Consider the attack vectors and TTPs identified in your threat model (Section 3).
2.  **Consider Different Testing Types:**
  - **Black-Box Testing:** Appropriate for scenarios where you assume the attacker has no internal knowledge of the model. Focuses on input manipulation and output analysis.
  - **Grey-Box Testing:** Appropriate if the attacker has some knowledge (e.g., API documentation, published research). Allows for more targeted testing.
  - **White-Box Testing:** *Generally not applicable* in your scenario (proprietary models you don't own), but included for completeness.
3.  **Example Methodologies:**
  - **Prompt Injection:**
    - Craft various prompt injection attacks (direct, indirect, jailbreaking, token smuggling) to bypass filters, elicit unintended outputs, or extract information.
    - Use libraries and tools designed for prompt injection testing (e.g., PromptInject, promptfoo).
  - **Adversarial Example Generation:**
    - If applicable (e.g., for image or text classification), create adversarial examples to test the model's robustness. Even without white-box access, you can try black-box techniques (e.g., iteratively modifying inputs and observing outputs).
  - **Data Poisoning Simulation:**
    - *If* your threat model includes data poisoning, simulate this by creating a small, poisoned dataset and assessing its potential impact (this is difficult without training access).
  - **Model Extraction/Inversion (Limited):**
    - Attempt to extract *some* information about the model through repeated querying. This is unlikely to be highly successful without white-box access, but you might be able to infer some characteristics.
  - **Membership Inference (Limited):**
    - Try to determine if specific data points were used in training (again, limited success expected without internal access).
  - **Manual Analysis and Exploration:**
    - Spend time interacting with the system, trying different inputs, and looking for unexpected behavior, biases, or vulnerabilities. This is a crucial part of any black-box or grey-box assessment.
    *  **Fuzzing:**
    - Provide a large number of randomly generated inputs, to see how it performs.
    * **Regression testing:**
        * If you had the capability to add examples to be tested in a regression suite, define a set of scenarios, to which the model should not be vulnerable.
    * **Scanning open-source components:**
    - If the threat model allows to assume code access, scan for known vulnerabilities in the system dependencies.
### 4d. Success Criteria
This subsection defines what constitutes a "successful" red teaming exercise.  It's not just about finding vulnerabilities; it's also about providing actionable insights.
1.  **Quantitative Metrics (Measurable Outcomes):**
  - Define specific, measurable metrics that will indicate the success or failure of each attack scenario.
  - Examples:
  - **Prompt Injection Success Rate:**  "The red team will successfully bypass content filters and elicit harmful outputs in X% of attempts."
  - **Adversarial Example Success Rate:**  "The red team will generate adversarial examples that cause misclassifications with a success rate of Y%."
  - **Data Extraction Rate:** "The red team will successfully extract Z data points from the model using model inversion techniques." (Likely to be low in a black-box scenario).
  - **Resource Consumption:** "The red team can successfully consume resources and prevent model availability."
  - **Number of Vulnerabilities Found:**  "The red team will identify at least N distinct vulnerabilities related to [specific risk area]."
    - *Crucially, set realistic targets.*  You're not aiming for 100% success in every attack; the goal is to uncover vulnerabilities and weaknesses.
2.  **Qualitative Metrics (Observable Outcomes):**
  - Define qualitative criteria that will help assess the *impact* and *implications* of your findings.
  - Examples:
  - **Severity of Vulnerabilities:**  "The red team will categorize identified vulnerabilities based on their severity (e.g., using a standard scoring system like CVSS)."
  - **Clarity of Exploitation:** "The red team will demonstrate *how* each vulnerability can be exploited in a realistic attack scenario."
  - **Impact on Trustworthiness:** "The red team will assess how each vulnerability impacts the trustworthiness characteristics of the AI system (validity, reliability, safety, security, etc.)."
  - **Actionable Recommendations:** "The red team will provide specific, actionable recommendations for mitigating each identified vulnerability."
        *  **Coverage Assessment:** Provide a statement on the comprehensiveness of the Red Teaming, and areas of further work.
3.  **Overall Success Definition:**
  - Combine your quantitative and qualitative metrics to define the overall success criteria for the red teaming exercise.
  - Example: "The red teaming exercise will be considered successful if the team identifies at least three high-severity vulnerabilities related to prompt injection, demonstrates a clear exploitation path for each vulnerability, and provides actionable recommendations for mitigation, all within the defined time and budget constraints."

## 5. The Main Pipeline
This section will bridge the gap between the theoretical (threat modeling, scoping) and the practical. It will focus on how to structure the red teaming process itself as a repeatable pipeline. Violent UTF streamlines the PyRIT piplines and enhance it with other tools. For simplicity, the below subsections will only target Microsoft PyRIT as the tool of choice. The pipeline consists of the following key stages:
1.  **Initialization:** Setting up the environment and configuring PyRIT (or your chosen toolset).
2.  **Dataset Selection/Creation:** Choosing or building the initial set of prompts or inputs.
3.  **Prompt Conversion (Optional):** Applying transformations to the prompts to create variations or adversarial examples.
4.  **Prompt Sending:** Interacting with the target AI system.
5.  **Scoring:** Evaluating the responses from the target system.
6.  **Iteration and Refinement:** Analyzing results, updating the dataset or converters, and repeating the process.
7.  **Reporting:** Documenting findings and recommendations.
### 5a. Initialization
This stage prepares the environment for the red teaming exercise.
- **Environment Setup:**
  - Have you installed PyRIT (or your chosen red teaming tool) and its dependencies? (Refer to your installation instructions).
  - Have you configured your environment variables (e.g., API keys, connection strings) correctly? (Refer to the "Populating Secrets" section).
  - Do you have a dedicated environment (e.g., a conda environment, a virtual machine) for the red teaming exercise to avoid conflicts with other projects?
  - Do you have the dependencies installed for all parts of the system?
- **PyRIT Configuration (if using PyRIT):**
  - Have you initialized PyRIT's memory (using `initialize_pyrit`)?  Which memory type are you using (In-Memory, DuckDB, Azure SQL)?  Is this appropriate for your needs (e.g., persistence, collaboration)?
  - Have you selected and configured your `PromptTarget` (the AI system you're testing)?  This is *critical*.  Ensure you have the correct API endpoints, authentication credentials, and any necessary model-specific parameters.
  - Have you selected and configured any `Scorer` instances you plan to use upfront? (You may add more later).
  - Have you selected an `Orchestrator`? Does your red team plan fit the orchestrator's requirements?
  - Do you have the necessary access permissions?
- **Baseline Establishment (Optional but Recommended):**
  - Before launching attacks, it's often helpful to establish a baseline.  Send a set of *benign* prompts to the target system and record the responses. This provides a point of comparison for later analysis.
  - Consider storing these baseline responses in PyRIT's memory for easy retrieval.
### 5b. Dataset Selection/Creation
This stage involves choosing or creating the initial set of prompts (or other inputs, like images for multimodal models) that you'll use to probe the AI system.
- **Leverage Existing Datasets:**
  - Does PyRIT (or another tool) provide pre-built datasets relevant to your target system or threat scenarios? (Refer to PyRIT's dataset documentation).  Examples:
    - Datasets of harmful prompts (e.g., for testing content filters).
    - Datasets of prompts designed to elicit specific biases.
    - Datasets for specific tasks (e.g., question answering, summarization).
  - Are there publicly available datasets (e.g., on Kaggle, Hugging Face Datasets) that you can adapt or use as inspiration?
- **Create Custom Datasets:**
  - If existing datasets don't fully meet your needs, create your own.
  - **Systematic Prompt Engineering:** Don't just randomly write prompts.  Use a systematic approach, guided by your threat model. Consider:
  - **Harm Categories:** What types of harm are you trying to elicit (e.g., toxicity, misinformation, PII disclosure)?  Create prompts specifically targeting these categories.
  - **Attack Techniques:**  What attack techniques are you focusing on (e.g., prompt injection, jailbreaking)?  Design prompts that attempt these techniques.
  - **User Personas:**  Create prompts that reflect the different user personas you defined in your system description (Section 1).  How might different users try to misuse the system?
  - **Input Types:**  If your system accepts multiple input types (text, images, audio), create prompts for each type.
  - **Edge Cases:**  Include prompts that test the boundaries of the system's capabilities and limitations.
  - **Use Templates:**  Create prompt templates with placeholders (e.g., `{{topic}}`, `{{name}}`) to generate variations of prompts systematically.  PyRIT's `SeedPrompt` class supports this.
  - **Data Augmentation:**  Consider techniques to automatically expand your dataset (e.g., paraphrasing, back-translation).
- **Data Format and Structure:**
  - Ensure your dataset is in a format compatible with PyRIT (or your chosen tool).  PyRIT's `SeedPromptDataset` provides a standardized structure.
  - Include metadata (e.g., `harm_categories`, `attack_type`) with your prompts to facilitate filtering and analysis.
- **Design Guidance:**
  - **Diversity:** Aim for a diverse dataset that covers a wide range of potential inputs and attack scenarios.
  - **Realism:**  Create prompts that are realistic and representative of how users (or attackers) might interact with the system.
  - **Iterative Approach:**  Start with a small dataset and expand it iteratively as you learn more about the system's vulnerabilities.
### 5c. Prompt Conversion (Optional)
This stage involves transforming the initial prompts using PyRIT's `Converter` classes. This is where you might apply techniques like jailbreaks, paraphrasing, or adding adversarial perturbations.
- **Do you need converters?**
  - Not all red teaming exercises require prompt conversion.  If your initial dataset is already designed to test specific vulnerabilities, you might skip this stage.
  - However, converters are often essential for:
  - **Jailbreaking:** Applying techniques to bypass safety filters.
  - **Adversarial Attacks:**  Generating adversarial examples (e.g., adding subtle perturbations to images).
  - **Data Augmentation:** Creating variations of prompts to increase the diversity of your test set.
  - **Cross-Domain Attacks:**  Converting prompts from one format to another (e.g., text to a Word document, text to an image).
- **Select Appropriate Converters:**
  - PyRIT provides a range of built-in converters.  Choose the ones that are relevant to your threat scenarios.
  - Examples:
    - `JailbreakConverter`:  Applies various jailbreaking techniques.
    - `ParaphraseConverter`:  Generates paraphrased versions of prompts.
    - `TextToImageConverter`:  Converts text prompts into images (for multimodal models).
    - `SearchReplaceConverter`:  Replaces specific words or phrases in prompts.
- **Stack Converters:**
  - You can chain multiple converters together to create complex transformations.  For example, you might first paraphrase a prompt and then apply a jailbreak.
- **Custom Converters:**
  - If PyRIT doesn't have a converter that meets your needs, you can create your own by subclassing the `PromptConverter` class.
- **Design Guidance:**
  - **Experimentation:**  Experiment with different converters and combinations of converters to see what works best against your target system.
  - **Targeted Transformations:**  Choose converters that are specifically designed to exploit the vulnerabilities you're targeting.
  - **Efficiency:**  Consider the computational cost of converters.  Some converters (e.g., those that use LLMs) can be expensive to run.
### 5d. Prompt Sending
This stage involves sending the prompts (or other inputs) to the target AI system and receiving the responses.
- **Use PyRIT's `PromptTarget` (or equivalent):**
  - This handles the interaction with the target system's API (or other interface).
  - It also manages conversation history (for `PromptChatTarget` instances).
  - It automatically stores the prompts and responses in PyRIT's memory.
- **Orchestrator Selection:**
  - Choose an appropriate `Orchestrator` to manage the prompt sending process.
    - `PromptSendingOrchestrator`: For sending a batch of prompts.
    - `MultiTurnOrchestrator`: For multi-turn conversations.
    - `CrescendoOrchestrator`, `PairOrchestrator`, `TreeOfAttacksWithPruningOrchestrator`: For specific attack strategies.
- **Error Handling:**
  - Implement robust error handling to deal with issues like API timeouts, rate limits, and unexpected responses.  PyRIT's exception handling (see Contributing Guidelines) should be used.
- **Asynchronous Operations:**
  - Use asynchronous operations (e.g., `asyncio`) to send prompts concurrently and improve efficiency.  PyRIT's orchestrators and targets are designed to support this.
- **Monitoring:**
  - Monitor the prompt sending process to ensure it's working as expected.  Check for errors, unexpected delays, or other anomalies.
- **Design Guidance:**
  - **Scalability:**  Design your pipeline to handle a large number of prompts efficiently.
  - **Reproducibility:**  Ensure that the prompt sending process is reproducible.  Use consistent settings and parameters.
  - **Respect API Limits:**  Be mindful of any rate limits or usage restrictions imposed by the target system's API.
### 5e. Scoring
This stage involves evaluating the responses from the target system to determine if they exhibit harmful, undesirable, or unexpected behavior.
- **Select Appropriate Scorers:**
  - PyRIT provides a variety of built-in scorers.  Choose the ones that are relevant to your threat scenarios and the types of harm you're trying to detect.
  - Examples:
    - `ToxicityScorer`:  Measures the toxicity of the response.
    - `PIIScorer`:  Detects the presence of personally identifiable information.
    - `StereotypeScorer`:  Identifies stereotypical or biased language.
    - `RefusalScorer`:  Checks if the model refused to answer the prompt.
    - `SelfAskTrueFalseScorer`:  Uses an LLM to evaluate whether a statement is true or false.
        * `HITLScorer`: Allows for manual scoring (Human-in-the-Loop).
- **Combine Scorers:**
  - You can use multiple scorers to evaluate different aspects of the response.  For example, you might use both a toxicity scorer and a PII scorer.
- **Custom Scorers:**
  - If PyRIT doesn't have a scorer that meets your needs, you can create your own by subclassing the `PromptScorer` class.
- **Thresholds and Interpretation:**
  - Define clear thresholds for each scorer.  What score constitutes a "failure" or a "red flag"?
  - Consider how you will interpret the scores.  Are some scores more important than others?
- **Automated vs. Manual Scoring:**
  - Automated scorers (like those using LLMs) can process large volumes of responses quickly.
  - Manual scoring (using `HITLScorer`) provides more nuanced judgment but is slower and more resource-intensive.  Consider using a combination of both.
- **Design Guidance:**
  - **Comprehensive Evaluation:**  Use a variety of scorers to evaluate different aspects of the responses.
  - **Contextual Interpretation:**  Interpret scores in the context of the prompt and the intended use case of the AI system.
  - **False Positives/Negatives:**  Be aware of the potential for false positives and false negatives.  Fine-tune your scorers and thresholds accordingly.
### 5f. Iteration and Refinement
This stage involves analyzing the results, updating the dataset or converters, and repeating the process. Red teaming is rarely a one-shot process; it's an iterative cycle of testing, learning, and improving.
- **Analyze Results:**
  - Review the prompts, responses, and scores.  Identify patterns, trends, and areas of concern.
  - Which prompts were most successful in eliciting harmful or undesirable behavior?
  - Which scorers were most effective in detecting these issues?
  - Were there any unexpected results or surprising vulnerabilities?
- **Refine Dataset:**
  - Based on your analysis, update your dataset:
    - Add new prompts that target newly discovered vulnerabilities.
    - Modify existing prompts to make them more effective.
    - Remove prompts that are consistently ineffective.
- **Refine Converters:**
  - Adjust the parameters of your converters, or try different combinations of converters.
  - If you're using custom converters, consider modifying their logic based on your findings.
- **Refine Scorers:**
  - Adjust the thresholds of your scorers, or try different scorers.
  - If you're using custom scorers, consider modifying their logic.
- **Repeat the Pipeline:**
  - Run the pipeline again with the updated dataset, converters, and scorers.
  - Continue iterating until you've achieved your success criteria (Section 4d) or reached the limits of your constraints (Section 4b).
**Design Guidance:**
  - **Systematic Iteration:**  Make small, incremental changes and track the impact of each change.
  - **Documentation:**  Carefully document your findings and the changes you make during each iteration.
  - **Collaboration:**  Share your findings with other red team members and with the developers of the AI system.
### 5g. Reporting
This final stage involves documenting your findings and recommendations in a clear and actionable report.
- **Target Audience:**  Who is the intended audience for your report? (Developers, security engineers, product managers, executives).  Tailor the level of detail and technical jargon accordingly.
- **Report Structure:**
  - **Executive Summary:**  A concise overview of the key findings and recommendations.
  - **Methodology:**  A description of the red teaming process, including the scope, constraints, methodologies, and tools used.
  - **Findings:**  A detailed presentation of the identified vulnerabilities, including:
  - **Description:**  A clear explanation of each vulnerability.
  - **Severity:**  An assessment of the severity of each vulnerability (e.g., using CVSS or a similar scoring system).
  - **Examples:**  Concrete examples of successful attacks (prompts, responses, scores).
  - **Impact:**  An explanation of the potential consequences of each vulnerability.
  - **Recommendations:**  Specific, actionable recommendations for mitigating each vulnerability.  These should be prioritized based on severity and feasibility.
  - **Appendices (Optional):**  Include any additional information, such as detailed logs, scripts, or datasets.
- **Visualizations:**  Use charts, graphs, and tables to present your findings clearly and effectively.
- **Actionable Insights:**  Focus on providing actionable insights that can be used to improve the security and safety of the AI system.
- **Review Cycle** Have the report reviewed by stakeholders to provide comments.
- **Design Guidance:**
  - **Clarity and Conciseness:**  Write clearly and concisely, avoiding unnecessary technical jargon.
  - **Objectivity:**  Present your findings objectively and avoid hyperbole.
  - **Constructive Tone:**  Maintain a constructive and collaborative tone.  The goal is to help improve the system, not to criticize.
  - **Prioritization:** Clearly communicate the relative priority of different recommendations.

Okay, let's build out Section 6: "Operational Details." This section moves from the *what* and *how* of the red teaming process (covered in previous sections) to the practical *when*, *where*, and *with whom* – essentially, how to integrate red teaming into an ongoing operational workflow.

## 6. Operational Details
This section describes the practical aspects of operationalizing the red teaming pipeline for Generative AI systems. It covers logging, automation, reporting, and integration with existing systems.
### 6a. Tracing and Logging
Robust tracing and logging are *essential* for effective red teaming. They enable you to:
  - Debug the pipeline: Identify and troubleshoot issues with your scripts, tools, and configurations.
  - Reproduce results: Track the exact sequence of steps that led to a particular outcome.
  - Analyze attack success: Understand *why* certain attacks succeeded or failed.
  - Monitor system behavior: Detect anomalies and unexpected responses from the target AI system.
  - Provide evidence: Document your findings for reporting and remediation.
  - Improve the red teaming process: Learn from past exercises and refine your techniques.
- **What to Log:**
  - **Inputs:**  Log all prompts (and other inputs) sent to the target system. Include any metadata (e.g., prompt ID, source dataset, converter applied).
  - **Outputs:** Log all responses received from the target system. Include raw responses, as well as any processed or filtered outputs.
  - **Scores:** Log all scores generated by your scorers. Include the scorer name, score value, and any rationale or metadata.
  - **Timestamps:** Log timestamps for all key events (prompt sending, response receiving, scoring). This is crucial for performance analysis and debugging.
  - **Errors:** Log all errors encountered during the pipeline, including stack traces and error messages.
  - **Configuration:** Log the configuration of all components (PyRIT settings, API keys, model versions). This is crucial for reproducibility.
  - **Orchestrator Actions:**  Log the actions taken by the orchestrator (e.g., "Selected prompt X," "Applied converter Y," "Sent prompt to target Z").
  - **Memory Operations (if applicable):** Log interactions with PyRIT's memory (e.g., "Stored prompt in memory," "Retrieved conversation history").
- **Logging Levels:**
  - Use appropriate logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) to categorize log messages.
  - Configure your logging system to capture the desired level of detail.  You might use DEBUG for development and troubleshooting, and INFO or WARNING for routine operations.
- **Log Format:**
  - Use a structured log format (e.g., JSON) to make it easier to parse and analyze logs.
  - Include consistent fields in your log messages (e.g., timestamp, event type, component name, prompt ID, score).
- **Log Storage:**
  - Where will you store your logs?  Consider options like:
    - Local files (for small-scale exercises).
    - A centralized logging system (e.g., Elasticsearch, Splunk, Azure Monitor).
    - PyRIT's memory (DuckDB or Azure SQL) – convenient for integrating with the rest of the pipeline.
  - Ensure your log storage solution is secure and has sufficient capacity.
- **Log Rotation and Retention:**
  - Implement a log rotation policy to prevent logs from consuming excessive disk space.
  - Define a log retention policy to determine how long logs should be kept.  This may be influenced by legal or compliance requirements.
- **PyRIT Integration:**
  - PyRIT's built-in components (targets, scorers, orchestrators) should automatically log key events to PyRIT's memory (if configured).
  - You can also use Python's standard `logging` module to add custom log messages within your scripts.
- **Tracing:**
  - Consider using a tracing library (e.g., OpenTelemetry) to track the flow of requests through the pipeline. This can be helpful for understanding the interactions between different components. This provides *distributed tracing* capabilities, useful if your pipeline involves multiple services or microservices.
- **Design Guidance:**
  - **Start with verbose logging:**  During development and initial testing, log everything.  You can always filter logs later.
  - **Use structured logging:**  This makes it much easier to query and analyze logs.
  - **Centralize logs:**  If possible, send logs to a central location for easier management and analysis.
  - **Automate log analysis:**  Use tools to automatically analyze logs and identify anomalies or patterns.
### 6b. Automation
Automation is key to making red teaming efficient and repeatable.  This section covers how to automate the execution of the pipeline.
#### Schedules
- **Frequency:** How often should the red teaming pipeline be executed?
  - **Continuous:**  Run the pipeline continuously (or very frequently, e.g., every few hours).  This is ideal for monitoring for regressions and detecting new vulnerabilities quickly.
  - **Periodic:**  Run the pipeline on a regular schedule (e.g., daily, weekly, monthly).  This is suitable for less critical systems or when continuous testing is not feasible.
  - **On-Demand:**  Run the pipeline manually when needed (e.g., after a code change or before a release).
- **Scheduling Tools:**
  - **Cron (Linux):**  A standard tool for scheduling tasks on Linux systems.
  - **Windows Task Scheduler:**  The equivalent of cron on Windows.
  - **CI/CD Pipelines (e.g., GitHub Actions, Azure Pipelines):**  Integrate the red teaming pipeline into your existing CI/CD workflow.  This is highly recommended for continuous testing.
  - **Cloud Schedulers (e.g., Azure Logic Apps, AWS Step Functions):**  Use cloud-based services to schedule and orchestrate the pipeline.
- **Resource Management:**
  - Consider the resource requirements of the pipeline (CPU, memory, API calls).  Schedule the pipeline to run during off-peak hours or use auto-scaling resources to avoid impacting production systems.
- **Dependencies:**
     * Are there any data dependencies?
     * Are the attack vectors dependent on the current date or time?
- **Failure Handling:**
  - What happens if the pipeline fails?  How will you be notified?  Will the pipeline automatically retry?
- **Design Guidance:**
  - **Start with on-demand execution:**  Before automating the pipeline, ensure it runs reliably manually.
  - **Use a CI/CD pipeline:**  This provides version control, automated testing, and a clear audit trail.
  - **Monitor scheduled runs:**  Track the success/failure rate of scheduled runs and investigate any failures.
#### Triggers
- **What events should trigger the red teaming pipeline?**
  - **Code Changes:**  Run the pipeline whenever new code is committed to the repository (or a specific branch). This is a core principle of continuous security testing.
  - **Model Updates:**  Run the pipeline whenever a new version of the AI model is deployed.
  - **Data Updates:**  Run the pipeline whenever the training data is updated (if applicable).
  - **Configuration Changes:**  Run the pipeline whenever the configuration of the AI system or its environment changes.
  - **Security Events:**  Trigger the pipeline in response to specific security events (e.g., a detected intrusion attempt).
  - **Manual Trigger:**  Allow red team members to manually trigger the pipeline at any time.
- **Trigger Mechanisms:**
  - **Webhooks:**  Use webhooks to trigger the pipeline from external systems (e.g., GitHub, Azure DevOps).
  - **Event Subscriptions (e.g., Azure Event Grid, AWS EventBridge):**  Subscribe to events from cloud services and trigger the pipeline accordingly.
  - **API Calls:**  Expose an API endpoint that can be called to trigger the pipeline.
- **Filtering:**
  - Implement filtering logic to avoid running the pipeline unnecessarily.  For example, you might only run the pipeline if the code changes affect the AI model or its related components.
- **Design Guidance:**
  - **Prioritize code and model changes:** These are the most common and important triggers.
  - **Use webhooks for CI/CD integration:** This is the most efficient way to trigger the pipeline from code repositories.
  - **Implement robust error handling:** Ensure that the pipeline handles trigger failures gracefully.
### 6c. Reports and Dashboards
Effective reporting is crucial for communicating findings, tracking progress, and demonstrating the value of red teaming.
- **Report Content:**
  - **Summary Statistics:**  Include metrics like the number of prompts sent, the number of vulnerabilities found, the success rate of different attack types, and the distribution of scores.
  - **Vulnerability Details:**  Provide detailed information about each vulnerability found, including:
    - Description:  A clear explanation of the vulnerability.
    - Severity:  An assessment of the severity (e.g., using CVSS).
    - Examples:  Concrete examples of successful attacks (prompts and responses).
    - Mitigation Recommendations:  Specific steps to fix the vulnerability.
  - **Trends Over Time:**  Track metrics over time to show progress in improving the security of the AI system.
  - **Comparison to Baseline:**  Compare the results to the baseline established during initialization (if applicable).
- **Report Format:**
  - **Static Reports (e.g., PDF, HTML):**  Suitable for sharing with stakeholders who don't need interactive access to the data.
  - **Interactive Dashboards (e.g., using tools like Power BI, Tableau, or Streamlit):**  Allow for dynamic exploration of the data and filtering by different criteria.
  - **Jupyter Notebooks:**  Can be used for both reporting and interactive analysis.
- **Audience:**
  - Tailor the report to the intended audience.  Executives might need a high-level summary, while developers need detailed technical information.
- **Automation:**
  - Automate the generation of reports and dashboards.  This saves time and ensures consistency. PyRIT's memory can be easily queried to extract data for reports.
- **PyRIT Integration:**
   * How does PyRIT save its content, and how can reports be generated?
   * Can we provide sample scripts which generate reports?
- **Design Guidance:**
  - **Focus on actionable insights:**  The report should clearly communicate the most important findings and recommendations.
  - **Use visualizations:**  Charts and graphs can make the data more understandable.
  - **Keep it concise:**  Avoid unnecessary detail and focus on the key information.
  - **Regular Reporting Cadence:** Reports should be sent out at regular intervals or after major updates.
### 6d. Integration
This section describes how to integrate the red teaming pipeline with other systems and workflows.
- **CI/CD Integration:**
  - Integrate the red teaming pipeline into your CI/CD pipeline to automatically test for vulnerabilities whenever code or model changes are made.  This is the *most important* integration point.
  - Use webhooks or other trigger mechanisms to initiate the pipeline from your CI/CD system.
  - Configure the pipeline to report results back to the CI/CD system (e.g., by failing the build if vulnerabilities are found).
- **Vulnerability Management System:**
  - Integrate the pipeline with your vulnerability management system (e.g., Jira, ServiceNow) to automatically create tickets for identified vulnerabilities.
  - This ensures that vulnerabilities are tracked and remediated in a consistent manner.
- **Security Information and Event Management (SIEM) System:**
  - Send logs from the red teaming pipeline to your SIEM system to correlate red teaming activity with other security events.
  - This can help identify potential attacks in progress and improve incident response.
- **Threat Intelligence Platforms:**
  - Share findings from the red teaming exercise with threat intelligence platforms to improve the overall security posture of the organization.
- **Collaboration Platforms (e.g., Slack, Microsoft Teams):**
  - Send notifications to collaboration platforms to alert team members about new vulnerabilities or significant events.
- **Other AI Systems**
    * Can PyRIT outputs be consumed by other AI systems?
- **Design Guidance:**
  - **Prioritize CI/CD integration:** This is the most impactful integration for continuous security testing.
  - **Use standard APIs and protocols:** This makes it easier to integrate with different systems.
  - **Automate as much as possible:** Reduce manual effort and ensure consistency.

[](The End)