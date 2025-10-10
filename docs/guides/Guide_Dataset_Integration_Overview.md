# Guide: Dataset Integration Overview

## Overview

ViolentUTF Dataset Integration provides a comprehensive framework for evaluating AI models using diverse security and reasoning datasets. This system supports 8+ dataset types across multiple domains including cognitive behavioral assessment, red-teaming security evaluation, legal reasoning, mathematical reasoning, spatial reasoning, privacy evaluation, and meta-evaluation workflows.

### Purpose and Scope

The dataset integration system enables:
- **Multi-domain AI security evaluation** across cognitive, behavioral, legal, and privacy domains
- **Standardized evaluation workflows** with consistent metrics and reporting
- **Performance optimization** for large-scale dataset processing
- **Enterprise-grade security testing** with PyRIT and Garak integration
- **Cross-domain comparative analysis** for comprehensive model assessment

### Prerequisites

- ViolentUTF platform installation with Docker services running
- Access to dataset files (local or remote sources)
- Basic understanding of AI evaluation methodologies
- Familiarity with PyRIT framework concepts

### Expected Outcomes

After completing this overview, users will understand:
- Available dataset types and their evaluation domains
- Basic workflow for dataset selection and configuration
- Integration with PyRIT orchestrators and scorers
- Performance considerations for different dataset sizes
- Next steps for detailed configuration

## Quick Start

### First Dataset Evaluation in 5 Minutes

1. **Access the Platform**
   ```bash
   # Ensure services are running
   ./check_services.sh

   # Access Streamlit interface
   open http://localhost:8501
   ```

2. **Select Your First Dataset**
   - Navigate to **Dataset Configuration** tab
   - Choose **OllaGen1** for cognitive behavioral assessment (recommended for beginners)
   - Set scenario limit to **1,000** for quick testing

3. **Configure Basic Evaluation**
   ```yaml
   dataset_type: "OllaGen1"
   scenario_limit: 1000
   question_types: ["WCP", "WHO"]
   evaluation_mode: "quick_assessment"
   ```

4. **Run Evaluation**
   - Click **Apply Configuration**
   - Monitor progress in the **Execution Status** panel
   - Review results in **Results Dashboard**

5. **Understand Results**
   - **Accuracy Metrics**: Model performance on cognitive pattern recognition
   - **Risk Assessment**: Behavioral risk identification capabilities
   - **Consistency Scores**: Stable performance across cognitive constructs

### Understanding Your First Results

- **Cognitive Pattern Recognition**: How well the model identifies behavioral patterns
- **Risk Calibration**: Appropriateness of risk level assessments
- **Performance Metrics**: Processing time and resource usage
- **Recommendations**: Suggested next steps based on results

## Dataset Categories

### Cognitive & Behavioral Assessment

**OllaGen1 Dataset**: 169,999 cognitive behavioral scenarios with 679,996 Q&A pairs
- **Purpose**: Security compliance and behavioral risk assessment
- **Question Types**: WCP, WHO, TeamRisk, TargetFactor
- **Use Cases**: Security compliance evaluation, behavioral risk analysis
- **Complexity**: Medium to High
- **Guide**: [Cognitive Behavioral Assessment](Guide_Cognitive_Behavioral_Assessment.md)

### AI Red-Teaming & Security

**Garak Integration**: LLM security vulnerability scanning
- **Purpose**: Identify AI model vulnerabilities and attack vectors
- **Coverage**: Jailbreaks, prompt injections, harmful content generation
- **Use Cases**: Security hardening, vulnerability assessment
- **Complexity**: High
- **Guide**: [Red-Teaming Evaluation](Guide_RedTeaming_Evaluation.md)

### Legal & Regulatory Reasoning

**LegalBench Dataset**: Legal reasoning and compliance evaluation
- **Purpose**: Legal domain expertise and regulatory compliance
- **Coverage**: Contract analysis, regulatory interpretation, legal precedent
- **Use Cases**: Legal AI systems, compliance automation
- **Complexity**: High
- **Guide**: [Legal Reasoning Assessment](Guide_Legal_Reasoning_Assessment.md)

### Mathematical & Document Reasoning

**DocMath Dataset**: Mathematical reasoning with document context
- **Purpose**: Mathematical problem-solving with contextual understanding
- **Coverage**: Multi-step reasoning, formula interpretation, context preservation
- **Use Cases**: Educational AI, technical documentation processing
- **Complexity**: Medium to High
- **Guide**: [Mathematical Reasoning Evaluation](Guide_Mathematical_Reasoning_Evaluation.md)

### Spatial & Graph Reasoning

**GraphWalk Dataset**: Spatial navigation and graph traversal
- **Purpose**: Spatial reasoning and graph-based problem solving
- **Coverage**: Path finding, spatial relationships, graph algorithms
- **Use Cases**: Navigation systems, spatial AI applications
- **Complexity**: Medium
- **Guide**: [Spatial Graph Reasoning](Guide_Spatial_Graph_Reasoning.md)

### Privacy & Contextual Integrity

**ConfAIde Dataset**: Privacy evaluation based on Contextual Integrity Theory
- **Purpose**: Privacy-aware AI system evaluation
- **Coverage**: Privacy tier assessment, contextual appropriateness
- **Use Cases**: Privacy-preserving AI, data protection compliance
- **Complexity**: Medium to High
- **Guide**: [Privacy Evaluation](Guide_Privacy_Evaluation.md)

### Meta-Evaluation & Judge Assessment

**JudgeBench Dataset**: AI judge and evaluation system assessment
- **Purpose**: Evaluate AI systems that judge other AI systems
- **Coverage**: Evaluation consistency, bias detection, reliability
- **Use Cases**: AI evaluation platforms, automated assessment systems
- **Complexity**: High
- **Guide**: [Meta-Evaluation Workflows](Guide_Meta_Evaluation_Workflows.md)

### Additional Specialized Datasets

**ACPBench**: Advanced cognitive processing benchmarks
- **Purpose**: Advanced cognitive task evaluation
- **Coverage**: Complex reasoning, multi-modal processing
- **Use Cases**: Advanced AI system evaluation

## Common Workflows

### Single Dataset Evaluation

**Best for**: Initial assessment, domain-specific evaluation, performance testing
1. **Dataset Selection**: Choose appropriate dataset for evaluation domain
2. **Configuration**: Set parameters based on evaluation goals
3. **Execution**: Run evaluation with monitoring
4. **Analysis**: Review results and generate reports

### Cross-Domain Comparison

**Best for**: Comprehensive model assessment, capability analysis
1. **Multi-Dataset Setup**: Configure 3-5 datasets across different domains
2. **Standardized Metrics**: Ensure comparable evaluation criteria
3. **Batch Execution**: Run evaluations with consistent parameters
4. **Comparative Analysis**: Generate cross-domain performance reports

### Progressive Complexity Assessment

**Best for**: Model capability boundaries, performance optimization
1. **Baseline Establishment**: Start with basic dataset configurations
2. **Complexity Scaling**: Gradually increase difficulty and scope
3. **Performance Monitoring**: Track degradation points and bottlenecks
4. **Optimization**: Apply performance improvements at critical points

### Comprehensive Security Evaluation

**Best for**: Security-focused assessment, vulnerability analysis
1. **Multi-Vector Assessment**: Combine red-teaming, privacy, and behavioral datasets
2. **Attack Surface Mapping**: Identify potential vulnerabilities across domains
3. **Defense Testing**: Validate security measures and safeguards
4. **Risk Assessment**: Generate comprehensive security posture report

## Integration Architecture

### PyRIT Framework Integration

ViolentUTF integrates with Microsoft's PyRIT framework for:
- **Orchestrator Management**: Automated evaluation workflow execution
- **Scorer Integration**: Standardized metrics and assessment criteria
- **Memory Management**: Persistent storage of evaluation results
- **Target Configuration**: Custom target systems for specialized evaluations

### System Components

```yaml
Dataset Integration Stack:
  - Dataset Converters: Transform various formats to PyRIT-compatible structures
  - Configuration Manager: Handle dataset-specific parameters and settings
  - Execution Engine: Process evaluations with resource management
  - Results Processing: Generate metrics, reports, and visualizations
  - API Integration: RESTful endpoints for programmatic access
```

### Performance Considerations

- **Memory Management**: Automatic file splitting for datasets >50MB
- **Concurrent Processing**: Parallel evaluation for independent tasks
- **Caching Strategy**: Intelligent caching of converted datasets and results
- **Resource Monitoring**: Real-time tracking of CPU, memory, and storage usage

## Configuration Overview

### Basic Configuration Pattern

```yaml
# Standard dataset configuration
dataset_config:
  type: "dataset_name"
  source: "local_path_or_url"
  parameters:
    scenario_limit: 10000
    question_types: ["type1", "type2"]
    performance_mode: "balanced"
  validation:
    enabled: true
    strict_mode: false
```

### Advanced Configuration Options

- **Performance Tuning**: Memory limits, parallel processing, caching
- **Output Customization**: Report formats, metric selection, visualization
- **Integration Settings**: API endpoints, webhook notifications, external storage
- **Security Configuration**: Access controls, data encryption, audit logging

## Use Cases

### Research and Development
- **AI Model Evaluation**: Compare model performance across multiple benchmarks
- **Capability Assessment**: Evaluate specific cognitive abilities and reasoning skills
- **Longitudinal Studies**: Track model performance over time and training iterations
- **Comparative Analysis**: Benchmark against established baselines and competitors

### Enterprise Deployment
- **Pre-deployment Testing**: Validate AI system readiness for production environments
- **Compliance Verification**: Ensure models meet regulatory and ethical standards
- **Performance Monitoring**: Continuous evaluation of deployed systems
- **Risk Assessment**: Identify potential failure modes and edge cases

### Educational and Training
- **Student Assessment**: Evaluate learning progress in AI development courses
- **Curriculum Development**: Design comprehensive evaluation frameworks
- **Research Training**: Provide hands-on experience with evaluation methodologies
- **Benchmarking Standards**: Establish consistent evaluation practices

### Security and Red-teaming
- **Vulnerability Assessment**: Identify weaknesses in AI system behavior
- **Adversarial Testing**: Evaluate robustness against malicious inputs
- **Safety Evaluation**: Assess potential risks and harmful outputs
- **Bias Detection**: Systematic identification of unfair or discriminatory behavior

### Quality Assurance
- **Release Testing**: Comprehensive evaluation before software releases
- **Regression Testing**: Ensure new changes don't degrade performance
- **Performance Validation**: Verify system meets specified requirements
- **User Acceptance Testing**: Validate system behavior from user perspective

## Performance Expectations

### Processing Benchmarks

| Dataset Size | Processing Time | Memory Usage | Recommended Hardware |
|--------------|-----------------|--------------|---------------------|
| 1,000 scenarios | <30 seconds | <100MB | Standard laptop |
| 10,000 scenarios | 2-5 minutes | <500MB | 8GB RAM recommended |
| 50,000 scenarios | 5-15 minutes | <1GB | 16GB RAM recommended |
| 100,000+ scenarios | 15-30 minutes | <2GB | 32GB RAM, SSD storage |

### Optimization Strategies

1. **Dataset Sampling**: Use representative subsets for initial evaluation
2. **Progressive Loading**: Load data in chunks to manage memory usage
3. **Parallel Processing**: Utilize multiple cores for independent evaluations
4. **Caching**: Store converted datasets and intermediate results
5. **Resource Monitoring**: Track usage and adjust parameters dynamically

## Next Steps

### For New Users
- **Start Here**: [Dataset Selection Workflows](Guide_Dataset_Selection_Workflows.md)
- **Choose Domain**: Select appropriate dataset guide from categories above
- **First Evaluation**: Follow Quick Start guide for hands-on experience

### For Advanced Users
- **Performance Optimization**: [Performance Optimization Guide](../plans/Performance_Optimization_Guide.md)
- **Custom Integration**: [Advanced Evaluation Methodologies](../plans/Advanced_Evaluation_Methodologies.md)
- **Troubleshooting**: [Dataset Integration Troubleshooting](../troubleshooting/Troubleshooting_Dataset_Integration.md)

### For Developers
- **API Documentation**: Programmatic access to dataset integration features
- **Extension Development**: Creating custom dataset converters and evaluations
- **Architecture Details**: Deep dive into system components and integration points

### For Administrators
- **System Configuration**: Enterprise deployment and configuration management
- **Performance Monitoring**: System health and optimization procedures
- **Maintenance Procedures**: Regular maintenance and update protocols

## Support and Resources

### Documentation Hierarchy
- **Guides**: Step-by-step instructions for specific tasks
- **Troubleshooting**: Common issues and resolution procedures
- **Plans**: Best practices and advanced methodologies
- **API Reference**: Technical specifications and endpoint documentation

### Getting Help
- **Interactive Support**: Use the MCP chat integration for real-time guidance
- **Documentation Search**: Search across all guides and references
- **Community Resources**: GitHub issues and discussion forums
- **Professional Support**: Enterprise support options and consultation

### Feedback and Improvement
We continuously improve this documentation based on user feedback. To contribute:
- **Report Issues**: Use GitHub issues for documentation problems
- **Suggest Improvements**: Submit pull requests for content enhancements
- **Share Use Cases**: Help us understand your evaluation workflows
- **Request Features**: Suggest new dataset types or evaluation methods

This overview provides the foundation for understanding ViolentUTF's dataset integration capabilities. Choose your specific domain guide to begin detailed configuration and evaluation workflows.
