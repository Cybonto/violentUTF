# AI Red Teaming Course Materials

This directory contains comprehensive course materials for **Enterprise AI Red Teaming: Security Assessment and Vulnerability Testing for Generative AI Systems** - a professional training program designed around the ViolentUTF platform.

## 📚 Course Materials Overview

### Core Course Documents

| Document | Description | Target Audience | Duration |
|----------|-------------|-----------------|----------|
| **[Course Outline](ai_redteaming_course_outline.md)** | Complete 40-hour curriculum overview with 6 modules | Students & Instructors | N/A |
| **[Module 1: Foundations](course_module1_foundations.md)** | AI security fundamentals, frameworks, and platform setup | Students | 8 hours |
| **[Module 3: Attack Techniques](course_module3_attack_techniques.md)** | Advanced prompt injection, jailbreaking, and adversarial methods | Students | 10 hours |
| **[Practical Exercises](course_practical_exercises.md)** | Hands-on labs with ViolentUTF, PyRIT, and Garak integration | Students | Throughout |
| **[Instructor Guide](instructor_implementation_guide.md)** | Complete implementation guide for course delivery | Instructors | N/A |

### Quick Start Guide

#### For Students
1. **Prerequisites**: Review [Course Outline](ai_redteaming_course_outline.md#course-prerequisites-deep-dive)
2. **Platform Setup**: Follow [Module 1 Setup](course_module1_foundations.md#practical-exercise-11-violentutf-platform-setup)
3. **First Lab**: Complete [Lab 1: System Reconnaissance](course_practical_exercises.md#lab-1-ai-system-reconnaissance-and-profiling)

#### For Instructors
1. **Preparation**: Review [Instructor Implementation Guide](instructor_implementation_guide.md#pre-course-preparation)
2. **Infrastructure**: Set up [Multi-Tenant Environment](instructor_implementation_guide.md#infrastructure-setup)
3. **Content**: Customize [Module Materials](instructor_implementation_guide.md#content-preparation)

## 🎯 Learning Path

The course follows a progressive learning model:

```
Module 1: Foundations (8h)
├── AI Security Landscape
├── Industry Frameworks (NIST, OWASP, MITRE)
├── ViolentUTF Platform Setup
└── Target System Analysis

Module 2: Threat Modeling (6h)
├── AI-Specific Threat Models
├── Risk Assessment
└── Attack Surface Analysis

Module 3: Core Attack Techniques (10h)
├── Prompt Injection & Manipulation
├── Jailbreaking & Safety Bypass
├── Data Extraction & Privacy Attacks
└── Adversarial Examples

Module 4: Advanced Frameworks (8h)
├── PyRIT Deep Dive
├── Garak Vulnerability Scanner
├── Custom Scoring Systems
└── Automation & Scaling

Module 5: Specialized Domains (4h)
├── Multi-Modal AI Security
├── Code Generation Security
├── RAG System Vulnerabilities
└── AI Agent Security

Module 6: Enterprise Implementation (4h)
├── CI/CD Integration
├── Remediation Strategies
└── Defense in Depth
```

## 🛠️ Technical Requirements

### Platform Dependencies
- **ViolentUTF Platform**: Enterprise AI red-teaming platform with PyRIT/Garak integration
- **PyRIT Framework**: Microsoft's Python Risk Identification Toolkit
- **Garak Scanner**: NVIDIA's LLM vulnerability scanner
- **Docker Environment**: Containerized deployment with multi-service orchestration

### Hardware Requirements
- **CPU**: 8+ cores (Intel i7/AMD Ryzen 7 or better)
- **RAM**: 32GB+ (64GB recommended for classroom environments)
- **Storage**: 1TB+ SSD with high IOPS
- **Network**: Gigabit internet connection

### Software Prerequisites
- **Docker Desktop**: 4.0+ with 16GB+ RAM allocation
- **Python**: 3.9+ with virtual environment support
- **API Access**: OpenAI, Anthropic, or Azure OpenAI service keys

## 📋 Assessment Framework

### Continuous Assessment (60%)
- **Lab Exercises**: Hands-on implementation and testing
- **Workshop Participation**: Collaborative problem-solving
- **Peer Review**: Technical evaluation of student work
- **Progressive Skills**: Demonstration of advancing capabilities

### Capstone Project (40%)
- **End-to-End Assessment**: Complete vulnerability assessment of chosen AI system
- **Custom Tool Development**: Novel attack vectors or scoring mechanisms
- **Professional Report**: Executive-ready documentation with remediation recommendations
- **Presentation**: Stakeholder communication and technical demonstration

### Certification Requirements
- Minimum 80% attendance across all modules
- Successful completion of all practical laboratories
- Passing grade on capstone project (≥80%)
- Demonstrated proficiency in core competencies

**Certificate Awarded**: Professional AI Red Teaming Specialist Certification

## 🎓 Learning Objectives

Upon successful completion, participants will be able to:

1. **Understand AI Security Landscape**: Comprehend unique security challenges of generative AI systems
2. **Conduct Systematic Assessments**: Execute comprehensive red teaming using industry frameworks
3. **Master Advanced Tools**: Proficiently use PyRIT, Garak, and ViolentUTF for vulnerability testing
4. **Develop Custom Attacks**: Create novel attack vectors and evasion techniques
5. **Implement Enterprise Solutions**: Build scalable AI security testing pipelines
6. **Communicate Effectively**: Generate professional reports and present findings to stakeholders

## 🔗 Related Resources

### ViolentUTF Platform Documentation
- [Platform Overview](../README.md)
- [API Documentation](../api/README.md)
- [MCP Integration Guide](../mcp/README.md)
- [Troubleshooting Guide](../troubleshooting/)

### Industry Frameworks
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [MITRE ATLAS Framework](https://atlas.mitre.org/)

### Research and Tools
- [Microsoft PyRIT](https://github.com/Azure/PyRIT)
- [NVIDIA Garak](https://github.com/NVIDIA/garak)
- [Anthropic Constitutional AI](https://www.anthropic.com/news/constitutional-ai-harmlessness-from-ai-feedback)

## 🤝 Contributing

This course is designed to evolve with the rapidly advancing field of AI security. Contributions are welcome in the form of:

- **Updated attack techniques** based on latest research
- **New practical exercises** incorporating emerging tools
- **Improved assessment rubrics** for better learning outcomes
- **Additional case studies** from real-world implementations

## 📞 Support

For questions about course materials or implementation:

- **Technical Issues**: See [Troubleshooting Guide](instructor_implementation_guide.md#technology-integration-and-troubleshooting)
- **Content Questions**: Review [Instructor Implementation Guide](instructor_implementation_guide.md)
- **Platform Support**: Consult [ViolentUTF Documentation](../README.md)

---

**Course Version**: 1.0
**Last Updated**: September 2025
**Compatible with**: ViolentUTF v2.0+, PyRIT v0.4+, Garak v0.9+

This comprehensive course represents the current state-of-the-art in AI red teaming education, designed to prepare the next generation of AI security professionals for the challenges of securing generative AI systems in enterprise environments.
