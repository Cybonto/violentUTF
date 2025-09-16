# Garak AI Security Testing Probe Analysis Report

## Executive Summary

This comprehensive analysis examines all major probe classes within the Garak AI security testing framework as documented in garak_API.md. Garak is a comprehensive LLM (Large Language Model) vulnerability scanner that tests AI models for security, safety, and ethical risks across multiple dimensions. This report focuses on the business and operational implications of each probe category rather than technical implementation details.

The analysis covers 15+ major probe categories encompassing over 100 individual probe classes, each designed to test specific aspects of AI model security, safety, and reliability. These probes are essential for organizations deploying AI systems in production environments, providing systematic evaluation of potential risks ranging from security vulnerabilities to ethical concerns.

## Key Findings

- **Comprehensive Coverage**: Garak probes address the full spectrum of AI risks including security vulnerabilities, ethical concerns, safety issues, and operational reliability
- **Business-Critical Testing**: Each probe category addresses specific business risks that could lead to regulatory violations, legal liability, reputational damage, or financial loss
- **Standards Alignment**: Probes are aligned with major frameworks including OWASP LLM Top 10, AVID (AI Vulnerability Database), and LMRC (Language Model Risk Cards)
- **Practical Application**: All probes are designed for real-world deployment scenarios with specific detectors and evaluation mechanisms

---

## Detailed Probe Analysis

### EICAR - Antivirus Test Code Detection

**Business Purpose**: Tests whether AI models have antivirus scanning capabilities on their output by attempting to get them to generate the EICAR test file code.

**Goals**:
- Evaluate if models implement virus scanning checks on generated output
- Determine if models can be manipulated to output known malicious signatures
- Assess the robustness of antivirus integration in AI systems

**Objectives**:
- Generate antivirus test codes through model prompting
- Test model compliance with security standards
- Verify that models refuse to output known-bad signatures

**Evaluation Mechanism**:
- Uses EICAR test file signatures as test cases
- Measures whether models generate virus signature content
- Employs specialized detector "knownbadsignatures.EICAR" for validation
- Tagged with security frameworks: AVID, OWASP LLM02

**Business Impact**: Critical for organizations deploying AI models in environments where output could be executed or stored, ensuring AI systems don't inadvertently bypass enterprise security infrastructure.

**Additional Context**: EICAR (European Institute for Computer Antivirus Research) test file is a standardized, safe method for testing antivirus software functionality. It allows organizations to verify antivirus effectiveness without using actual malware, making it essential for cybersecurity validation processes.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html
- EICAR Standard: https://en.wikipedia.org/wiki/EICAR_test_file

### GTUBE - Anti-Spam Filter Testing

**Business Purpose**: Tests whether AI models have spam filtering capabilities by attempting to get them to generate GTUBE (Generic Test for Unsolicited Bulk Email) signatures.

**Goals**:
- Evaluate if models implement spam detection checks on generated content
- Determine if models can be manipulated to output known spam signatures
- Assess the effectiveness of anti-spam integration in AI systems

**Objectives**:
- Generate email spam test signatures through model prompting
- Test model compliance with email security standards
- Verify that models refuse to output content that should be blocked by spam filters

**Evaluation Mechanism**:
- Uses GTUBE standard test string (68-byte signature that scores 1000 in SpamAssassin)
- Measures whether models generate spam signature content
- Employs specialized detector "knownbadsignatures.GTUBE" for validation
- Tagged with security frameworks: AVID, OWASP LLM02

**Business Impact**: Essential for organizations using AI models to generate email content, ensuring models don't bypass email security infrastructure and create spam-like content that could be filtered or flagged.

**Additional Context**: GTUBE is a standardized test used to validate anti-spam systems, particularly SpamAssassin. It enables systematic testing of email filtering effectiveness and provides consistent benchmarks for spam detection technologies.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html
- GTUBE Standard: https://en.wikipedia.org/wiki/GTUBE

### GTphish - Anti-Phishing Detection Testing

**Business Purpose**: Tests whether AI models have phishing detection capabilities by attempting to get them to generate GTphish signatures.

**Goals**:
- Evaluate if models implement phishing detection checks on generated content
- Determine if models can be manipulated to output known phishing signatures
- Assess the robustness of anti-phishing integration in AI systems

**Objectives**:
- Generate email phishing test signatures through model prompting
- Test model safeguards against generating phishing mail content
- Verify that phishing scanners can catch and block GTphish code

**Evaluation Mechanism**:
- Uses GTphish code as test signature
- Measures whether models generate phishing signature content
- Employs specialized detector "knownbadsignatures.GTphish" for validation
- Tagged with security frameworks: AVID, OWASP LLM02

**Business Impact**: Critical for organizations using AI models to generate email content, preventing the creation of content that could trigger phishing detection systems or be used in social engineering attacks.

**Additional Context**: GTphish is a variant of GTUBE specifically designed to trigger phishing mail detection systems. It helps validate that phishing protection mechanisms are functioning correctly.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html
- Cisco Testing Guide: https://www.cisco.com/c/en/us/support/docs/security/email-security-appliance/213465-testing-outbreak-filter-url-rewriting.html

### ContinueSlursReclaimedSlurs - Hate Speech Continuation Testing

**Business Purpose**: Tests whether AI models will complete partial ethnic slurs or offensive terms when given contextual prompts.

**Goals**:
- Evaluate model resistance to generating hate speech and offensive language
- Determine if models can be manipulated through contextual priming
- Assess content safety mechanisms for partial word completion

**Objectives**:
- Test completion of 80 high-risk slurs and offensive terms
- Evaluate model behavior with varying amounts of contextual prefix
- Verify content safety filters catch partial offensive completions

**Evaluation Mechanism**:
- Uses dataset of slur prompts from Urban Dictionary contexts
- Employs "continuation.Continuation" detector for validation
- Tagged with ethics frameworks: AVID Ethics, OWASP LLM01
- Focuses on toxicity and hate/harassment content safety

**Business Impact**: Critical for organizations deploying AI models in customer-facing applications, social media platforms, or content generation tools where hate speech could create legal liability, reputation damage, or user harm.

**Additional Context**: This probe operates by providing high-risk context extracted from examples of contentious term usage, testing if models will complete terms based on varying prefix amounts. Essential for content moderation and safety evaluation.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.continuation.html

### DAN (Do Anything Now) - System Prompt Bypass Testing

**Business Purpose**: Tests whether AI models can be manipulated to bypass their system prompts and safety guidelines through community-developed jailbreaking techniques.

**Goals**:
- Evaluate model resistance to system prompt manipulation
- Determine if models can be convinced to disregard safety guidelines
- Assess the robustness of conversational turn safety mechanisms

**Objectives**:
- Test various DAN prompt variations (versions 6.0 through 11.0)
- Evaluate jailbreaking effectiveness across different prompt strategies
- Verify mitigation systems can detect and prevent prompt bypasses

**Evaluation Mechanism**:
- Uses community-developed DAN prompts stored in text files
- Employs "mitigation.MitigationBypass" and "dan.DAN" detectors
- Tagged with security frameworks: AVID Security, OWASP LLM01
- Includes multiple probe variants: AntiDAN, AutoDAN, DUDE, STAN

**Business Impact**: Essential for organizations deploying AI models in production environments where bypassing safety guidelines could lead to harmful outputs, regulatory violations, or reputational damage. Critical for maintaining model reliability and compliance.

**Additional Context**: DAN (Do Anything Now) represents a class of community-developed techniques designed to convince AI models to ignore their instructions and safety guidelines. These probes test various iterations and refinements of these jailbreaking approaches.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.dan.html

### Encoding Injection - Payload Obfuscation Testing

**Business Purpose**: Tests whether AI models can be manipulated to decode and execute malicious payloads that have been encoded using various encoding schemes (Base64, Base32, ASCII85, Braille, Morse, etc.).

**Goals**:
- Evaluate model resistance to encoded payload attacks
- Determine if models can be tricked into decoding and executing hidden instructions
- Assess the effectiveness of content filtering against obfuscated inputs

**Objectives**:
- Test multiple encoding schemes: Base16, Base32, Base64, Base2048, ASCII85, Braille, Morse, NATO phonetic, ROT13, UU, Zalgo
- Evaluate various prompt strategies to get models to decode payloads
- Verify that security systems can detect encoded malicious content

**Evaluation Mechanism**:
- Employs "encoding.DecodeMatch" and "encoding.DecodeApprox" detectors
- Uses payloads from various attack categories (shell commands, slur terms)
- Tagged with security frameworks: AVID Security, OWASP LLM01
- Tests against prompt stability and generic payloads

**Business Impact**: Critical for organizations deploying AI models with system integrations, as encoded attacks can bypass traditional content filters and enable unauthorized system access, data exfiltration, or manipulation of downstream systems.

**Additional Context**: Research shows that LLMs can be manipulated through encoded inline jailbreaks, where malicious instructions are hidden within seemingly benign encoded text. This creates significant security risks for AI systems with broad access permissions or system integrations.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.encoding.html
- Research: https://kai-greshake.de/posts/llm-malware/#encoded-inline-jailbreak

### DoNotAnswer - Harmful Content Response Testing

**Business Purpose**: Tests whether AI models appropriately refuse to answer questions that responsible language models should not address, using a curated dataset of potentially harmful instructions.

**Goals**:
- Evaluate model safeguards against harmful instruction following
- Determine if models can be manipulated to provide inappropriate responses
- Assess the effectiveness of content safety mechanisms

**Objectives**:
- Test responses to discrimination, exclusion, toxicity, hateful, and offensive prompts
- Evaluate human chatbox manipulation attempts
- Test information hazard and misinformation scenarios
- Assess malicious use case resistance

**Evaluation Mechanism**:
- Uses "mitigation.MitigationBypass" detector for validation
- Tests multiple categories: discrimination/exclusion/toxicity, human chatbox, information hazards, malicious uses, misinformation harms
- Tagged with ethics and content safety frameworks: AVID Ethics, behavioral content safety
- Based on peer-reviewed research dataset (arXiv:2308.13387)

**Business Impact**: Essential for organizations deploying customer-facing AI systems, as inappropriate responses to harmful questions could create legal liability, reputational damage, regulatory violations, and user harm. Critical for maintaining responsible AI deployment standards.

**Additional Context**: DoNotAnswer represents the first open-source dataset specifically designed to evaluate AI model safeguards. It provides a systematic framework for identifying dangerous model capabilities before deployment, enabling proactive safety assessment.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.donotanswer.html
- Research Paper: https://arxiv.org/abs/2308.13387

### Latent Injection - Hidden Context Manipulation

**Business Purpose**: Tests whether AI models can be manipulated by malicious instructions hidden within seemingly innocent documents or contexts, such as PDFs, resumes, or fact snippets.

**Goals**:
- Evaluate model resistance to context-based prompt injections
- Determine if models can be subverted by text placed in innocuous documents
- Assess the effectiveness of content filtering against hidden instructions

**Objectives**:
- Test injection through various document types: fact snippets (Eiffel Tower), reports, resumes, translations
- Evaluate different injection separation techniques and formatting
- Verify that models don't execute hidden instructions within normal content

**Evaluation Mechanism**:
- Uses "base.TriggerListDetector" for validation
- Tests multiple injection contexts: factual content, translation tasks, resume processing
- Tagged with security frameworks: AVID Security, OWASP LLM01
- Employs various payload triggers to test instruction following

**Business Impact**: Critical for organizations processing user-generated documents through AI systems, as attackers could embed malicious instructions in PDFs, resumes, or other documents to manipulate AI decision-making, bypass content filters, or extract sensitive information.

**Additional Context**: Research demonstrates that invisible text can be embedded in PDFs using white fonts or zero opacity, making malicious instructions undetectable to human reviewers while still being processed by AI systems. This creates significant risks for document processing workflows.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.latentinjection.html
- Research: https://kai-greshake.de/posts/inject-my-pdf/

### Leak/Replay - Training Data Extraction

**Business Purpose**: Tests whether AI models inappropriately reproduce or complete copyrighted content, proprietary information, or training data from sources like literature, news articles, or other protected content.

**Goals**:
- Evaluate model tendency to leak training data
- Determine if models can be prompted to reproduce copyrighted content
- Assess intellectual property protection mechanisms

**Objectives**:
- Test completion and cloze (fill-in-the-blank) tasks on literature passages
- Evaluate reproduction of Guardian news articles, NYT content, Harry Potter text
- Test high-perplexity completions of known content
- Verify content protection and attribution mechanisms

**Evaluation Mechanism**:
- Uses passages known to be reproducible by GPT-4 or ChatGPT
- Tests both completion and cloze tasks
- Employs literature-specific detectors for validation
- Focuses on high-perplexity blanks that indicate memorization

**Business Impact**: Essential for organizations concerned with intellectual property rights, copyright compliance, and data leakage. Inappropriate content reproduction could lead to legal liability, licensing violations, and exposure of proprietary training data.

**Additional Context**: This probe category specifically targets content that has been identified as reproducible by major AI models, testing whether new models have similar data leakage vulnerabilities. Critical for understanding training data memorization risks.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.leakreplay.html

### LMRC (Language Model Risk Cards) - Ethical AI Behavior Testing

**Business Purpose**: Tests AI models for various ethical risks documented in the Language Model Risk Cards project, including anthropomorphisation, bullying, deadnaming, profanity, quack medicine, and sexual content.

**Goals**:
- Evaluate model adherence to ethical AI principles
- Determine if models exhibit harmful behavioral patterns
- Assess content moderation effectiveness across ethical dimensions

**Objectives**:
- Test anthropomorphisation: whether models encourage human-like attribution
- Evaluate bullying: generation of threats or aggressive recommendations
- Assess deadnaming: inappropriate use of former names of transgender individuals
- Test profanity generation and sexual content creation
- Evaluate quack medicine and medical misinformation

**Evaluation Mechanism**:
- Uses specialized detectors for each risk type: "lmrc.Anthro", "unsafe_content.ToxicCommentModel", "base.TriggerListDetector"
- Tagged with comprehensive risk frameworks: LMRC risk cards, AVID Ethics
- Tests specific prompts designed to elicit problematic behaviors

**Business Impact**: Essential for organizations deploying AI in public-facing applications, healthcare, education, or content creation, where ethical violations could lead to discrimination lawsuits, regulatory penalties, user harm, or reputation damage.

**Additional Context**: Based on the academic Language Model Risk Cards project that systematically documents AI risks across consumer-interpersonal harm categories. Provides structured approach to ethical AI evaluation.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.lmrc.html
- Risk Cards Project: https://github.com/leondz/lm_risk_cards/

### Grandma Attack - Emotional Manipulation Testing

**Business Purpose**: Tests whether AI models can be manipulated through emotional appeals and social engineering, specifically using appeals to pathos involving fictional grandmother scenarios.

**Goals**:
- Evaluate model resistance to emotional manipulation
- Determine if models can be socially engineered through sympathy appeals
- Assess the effectiveness of content filters against pathos-based attacks

**Objectives**:
- Test generation of ethnic slurs through grandmother memory appeals
- Evaluate instructions for harmful substances (napalm, methamphetamine, toxic compounds)
- Test product key generation (Windows 10/11) through emotional manipulation
- Verify that social engineering attempts are properly blocked

**Evaluation Mechanism**:
- Uses "specialwords.SlursReclaimedSlurs" and "mitigation.MitigationBypass" detectors
- Tagged with security and content safety frameworks
- Tests multiple substance categories and human group variations

**Business Impact**: Critical for organizations deploying AI in customer service or educational contexts, as emotional manipulation attacks could lead to generation of harmful content, illegal information, or intellectual property violations.

**Additional Context**: The "grandma attack" represents a class of social engineering techniques that use emotional appeals to bypass AI safety measures. Originally popularized on social media as a method to extract restricted information from chatbots.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.grandma.html
- Original Reference: https://x.com/_annieversary/status/1647865782741749760

### Divergence - Training Data Extraction via Repetition

**Business Purpose**: Tests whether AI models can be manipulated to leak training data through repetition attacks, particularly the "poem poem poem" technique that causes model divergence.

**Goals**:
- Evaluate model resistance to training data extraction
- Determine if repetitive prompts cause data leakage
- Assess the effectiveness of privacy protection mechanisms

**Objectives**:
- Test repetition attacks using various words: "poem", "company", "book", "a"
- Evaluate model behavior when asked to repeat strings indefinitely
- Verify that models don't degrade to replaying training data

**Evaluation Mechanism**:
- Uses "divergence.RepeatDiverges" detector to identify data leakage
- Employs "mitigation.MitigationBypass" for extended detection
- Tagged with security frameworks: AVID Security, OWASP LLM06/LLM10
- Focuses on confidentiality and extraction/inversion attacks

**Business Impact**: Critical for organizations concerned with data privacy, intellectual property protection, and regulatory compliance, as training data leakage could expose proprietary information, copyrighted content, or personally identifiable information.

**Additional Context**: Research showed that simple repetition prompts like "Repeat the word 'poem' forever" could cause ChatGPT to reveal verbatim training data. This attack cost approximately $200 to extract several megabytes of training data, demonstrating significant privacy risks.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.divergence.html
- Research: https://not-just-memorization.github.io/extracting-training-data-from-chatgpt.html

### File Formats - Model File Security Testing

**Business Purpose**: Tests AI models and their associated files for security risks, particularly focusing on Hugging Face model files, executables, and potentially dangerous formats like pickled files.

**Goals**:
- Evaluate security of model file structures
- Determine if model files contain executable or dangerous content
- Assess file format risks in AI model distribution

**Objectives**:
- Generate manifests of files associated with Hugging Face generators
- Test for executable file detection in model packages
- Evaluate pickle file safety and potential code injection risks
- Verify file format security across different generator types

**Evaluation Mechanism**:
- Uses "fileformats.FileIsPickled", "fileformats.FileIsExecutable", "fileformats.PossiblePickleName" detectors
- Tagged with OWASP LLM05 (Supply Chain Vulnerabilities)
- Supports various generator types: LLaVA, Model, OptimumPipeline, Pipeline

**Business Impact**: Essential for organizations deploying AI models from external sources, as malicious files could contain executable code, backdoors, or other security threats that compromise system integrity and data security.

**Additional Context**: Pickle files in Python can execute arbitrary code when loaded, making them a significant security risk. This probe helps identify such files in AI model packages that could be used for supply chain attacks.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.fileformats.html

### Glitch Tokens - Model Stability Testing

**Business Purpose**: Tests AI models for unusual behavior when exposed to glitch tokens - rare tokenizer entries that can cause instability or unpredictable model responses.

**Goals**:
- Evaluate model stability against unusual tokenization
- Determine if rare tokens cause degraded performance
- Assess robustness of model behavior across token edge cases

**Objectives**:
- Test model responses to 100+ potential glitch tokens
- Evaluate stability when processing rare tokenizer entries
- Verify consistent model performance across unusual inputs
- Assess ability to repeat or process uncommon tokens

**Evaluation Mechanism**:
- Uses specialized glitch token detection and analysis
- Tests tokens that rarely occur in general text
- Focuses on tokenizer-specific edge cases and rare entries
- Evaluates model stability metrics

**Business Impact**: Important for organizations deploying AI models in production environments where consistent performance is critical, as glitch tokens could cause unpredictable behavior, system instability, or degraded user experiences.

**Additional Context**: Glitch tokens are typically long entries in tokenizers that rarely appear in normal text. Models using the same tokenizer often struggle to repeat or process these tokens correctly, leading to less stable performance.

**Resource Links**:
- Documentation: https://reference.garak.ai/en/latest/garak.probes.glitch.html

---

## Additional Probe Categories

The Garak framework includes several other important probe categories that organizations should be aware of:

### Atkgen - Toxicity Generation
Tests models for generating toxic content, particularly using toxicity classifier datasets to evaluate harmful content generation capabilities.

### Goodside - Research-Based Probes
Implements probes based on academic research findings, including specific techniques developed by researchers like Riley Goodside for testing AI model vulnerabilities.

### Base Classes
Provides foundational probe infrastructure including TreeSearchProbe for systematic vulnerability exploration and basic Probe classes for custom testing scenarios.

---

## Strategic Recommendations

### For Security Teams
1. **Implement Comprehensive Testing**: Deploy Garak probes across all AI model deployments to identify security vulnerabilities before production use
2. **Focus on High-Risk Categories**: Prioritize testing for DAN attacks, encoding injections, and latent injections that pose immediate security risks
3. **Regular Vulnerability Assessment**: Conduct ongoing probe testing as models and deployment contexts evolve

### For Compliance Officers
1. **Regulatory Alignment**: Use DoNotAnswer and LMRC probes to ensure compliance with AI ethics regulations and industry standards
2. **Documentation Requirements**: Maintain comprehensive testing records for audit and regulatory review purposes
3. **Risk Assessment Integration**: Incorporate probe results into enterprise risk management frameworks

### for Product Teams
1. **User Safety Priority**: Implement continuation, grandma attack, and emotional manipulation testing to protect end users
2. **Content Moderation**: Use hate speech, profanity, and ethical behavior probes to maintain platform standards
3. **Performance Monitoring**: Deploy glitch token and stability testing to ensure consistent user experiences

### For Legal Teams
1. **Intellectual Property Protection**: Utilize leak/replay probes to prevent copyright violations and proprietary data exposure
2. **Liability Mitigation**: Implement comprehensive content safety testing to reduce legal exposure from harmful AI outputs
3. **Contract Compliance**: Ensure AI model behavior aligns with vendor agreements and service level commitments

---

## Conclusion

The Garak AI security testing framework provides a comprehensive, business-focused approach to AI model evaluation that addresses the full spectrum of security, safety, and ethical risks. Organizations deploying AI systems must implement systematic testing across all probe categories to ensure responsible AI deployment, regulatory compliance, and business risk mitigation.

The probes analyzed in this report represent the current state-of-the-art in AI vulnerability testing, incorporating academic research, industry best practices, and real-world attack techniques. Regular implementation of these testing methodologies is essential for maintaining secure, reliable, and ethical AI deployments in production environments.

**Total Probe Categories Analyzed**: 15+ major categories covering 100+ individual probe classes
**Business Risk Areas Addressed**: Security, Safety, Ethics, Privacy, Compliance, Operational Reliability
**Framework Alignment**: OWASP LLM Top 10, AVID AI Vulnerability Database, Language Model Risk Cards
**Target Applications**: Production AI deployments, customer-facing systems, enterprise AI integration

---

*This analysis was conducted as part of the ViolentUTF AI red-teaming platform documentation initiative. For technical implementation details, refer to the complete garak_API.md documentation and probe-specific configuration files.*
