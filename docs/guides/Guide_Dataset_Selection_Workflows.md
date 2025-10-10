# Guide: Dataset Selection Workflows

## Overview

This guide provides decision-making frameworks and step-by-step workflows for selecting the most appropriate datasets for your AI evaluation goals. Proper dataset selection is crucial for meaningful evaluation results and optimal resource utilization.

### Purpose and Scope

Dataset selection workflows help you:
- **Match evaluation goals** with appropriate dataset types
- **Optimize resource usage** by selecting right-sized datasets
- **Plan comprehensive evaluations** across multiple domains
- **Understand dataset characteristics** and limitations
- **Make informed decisions** about evaluation scope and depth

### Prerequisites

- Basic understanding of AI evaluation concepts
- Familiarity with your target AI system capabilities
- Clear evaluation objectives and success criteria
- Access to ViolentUTF dataset integration platform

## Quick Start

### 3-Minute Dataset Selection

1. **Define Your Goal**
   - Security assessment? → Red-teaming datasets (Garak)
   - Behavioral analysis? → Cognitive datasets (OllaGen1)
   - Domain expertise? → Specialized datasets (LegalBench, DocMath)

2. **Consider Your Resources**
   - Limited time? → Start with 1,000-10,000 scenarios
   - Full assessment? → Use 50,000+ scenarios
   - Comprehensive evaluation? → Multi-dataset approach

3. **Select Initial Dataset**
   ```yaml
   Quick Selection Matrix:
   - First-time users: OllaGen1 (10,000 scenarios)
   - Security focus: Garak + ConfAIde
   - Domain-specific: LegalBench/DocMath/GraphWalk
   - Comprehensive: OllaGen1 + Garak + ConfAIde + domain-specific
   ```

## Decision Framework

### Evaluation Goal Classification

#### 1. Security and Risk Assessment
**Primary Objective**: Identify vulnerabilities and security risks

**Recommended Datasets**:
- **Garak** (Red-teaming): Core security vulnerability assessment
- **ConfAIde** (Privacy): Privacy and contextual integrity evaluation
- **OllaGen1** (Behavioral): Behavioral risk and compliance assessment

**Workflow**:
```
Step 1: Start with Garak for broad vulnerability scan
Step 2: Add ConfAIde for privacy-specific risks
Step 3: Include OllaGen1 for behavioral risk patterns
Step 4: Cross-analyze results for comprehensive risk profile
```

#### 2. Domain Expertise Evaluation
**Primary Objective**: Assess specialized knowledge and reasoning capabilities

**Recommended Datasets**:
- **LegalBench**: Legal reasoning and regulatory compliance
- **DocMath**: Mathematical reasoning with document context
- **GraphWalk**: Spatial reasoning and graph traversal
- **JudgeBench**: Meta-evaluation and assessment capabilities

**Workflow**:
```
Step 1: Identify primary domain (legal, math, spatial, meta)
Step 2: Select corresponding specialized dataset
Step 3: Configure domain-appropriate complexity level
Step 4: Validate with cross-domain reasoning tests
```

#### 3. General Capability Assessment
**Primary Objective**: Broad evaluation of AI system capabilities

**Recommended Datasets**:
- **OllaGen1**: Cognitive and behavioral assessment foundation
- **ACPBench**: Advanced cognitive processing
- **JudgeBench**: Self-evaluation and meta-cognition
- **DocMath**: Multi-modal reasoning validation

**Workflow**:
```
Step 1: Establish baseline with OllaGen1
Step 2: Test advanced cognition with ACPBench
Step 3: Evaluate meta-reasoning with JudgeBench
Step 4: Validate multi-modal capabilities with DocMath
```

### Resource-Based Selection

#### Time-Constrained Evaluation (< 1 hour)
```yaml
Quick Assessment:
  datasets: ["OllaGen1"]
  scenario_limit: 1000-5000
  question_types: ["WCP", "WHO"]
  focus: "High-level capability overview"
  expected_insights: "Basic cognitive and behavioral patterns"
```

#### Standard Evaluation (1-4 hours)
```yaml
Balanced Assessment:
  datasets: ["OllaGen1", "Garak", "ConfAIde"]
  scenario_limit: 10000-25000
  coverage: "Security + Behavior + Privacy"
  focus: "Comprehensive risk and capability assessment"
  expected_insights: "Detailed security posture and behavioral analysis"
```

#### Comprehensive Evaluation (4+ hours)
```yaml
Full Assessment:
  datasets: ["OllaGen1", "Garak", "ConfAIde", "LegalBench", "DocMath"]
  scenario_limit: 50000+
  coverage: "Multi-domain comprehensive evaluation"
  focus: "Complete capability and risk profile"
  expected_insights: "Enterprise-ready assessment with domain expertise"
```

### System Capability Matching

#### High-Performance Systems
**Characteristics**: Fast response, large context windows, advanced reasoning
```yaml
Recommended Configuration:
  datasets: ["All available"]
  scenario_limits: ["Maximum"]
  complexity_levels: ["Advanced"]
  parallel_processing: true
  expected_duration: "4-8 hours"
```

#### Standard Systems
**Characteristics**: Good general performance, moderate context limits
```yaml
Recommended Configuration:
  datasets: ["OllaGen1", "Garak", "ConfAIde", "One domain-specific"]
  scenario_limits: [25000, 10000, 15000, 10000]
  complexity_levels: ["Medium to Advanced"]
  parallel_processing: false
  expected_duration: "2-4 hours"
```

#### Resource-Constrained Systems
**Characteristics**: Limited processing power, small context windows
```yaml
Recommended Configuration:
  datasets: ["OllaGen1", "One additional"]
  scenario_limits: [5000, 2500]
  complexity_levels: ["Basic to Medium"]
  optimization: "Memory-efficient mode"
  expected_duration: "30-60 minutes"
```

## Step-by-Step Selection Process

### Step 1: Goal Definition and Scope

#### Define Primary Objectives
1. **Security Assessment**
   - Vulnerability identification
   - Risk assessment and mitigation
   - Compliance validation
   - Attack surface analysis

2. **Capability Evaluation**
   - Domain expertise assessment
   - Reasoning capability analysis
   - Performance benchmarking
   - Comparative analysis

3. **Quality Assurance**
   - Consistency validation
   - Bias detection
   - Reliability assessment
   - Error analysis

#### Determine Evaluation Scope
```yaml
Scope Planning:
  breadth_vs_depth: "Wide coverage vs. Deep analysis"
  time_constraints: "Available evaluation window"
  resource_limits: "Processing and memory constraints"
  stakeholder_needs: "Reporting and compliance requirements"
```

### Step 2: Dataset Characteristic Analysis

#### Dataset Complexity Assessment
```yaml
Complexity Matrix:
  Low Complexity:
    - OllaGen1 (WCP questions only)
    - GraphWalk (basic spatial reasoning)
    - Scenario limits: 1000-5000

  Medium Complexity:
    - OllaGen1 (WCP + WHO questions)
    - ConfAIde (Tier 1-2)
    - DocMath (basic mathematical reasoning)
    - Scenario limits: 5000-25000

  High Complexity:
    - Garak (full vulnerability scan)
    - LegalBench (complex legal reasoning)
    - OllaGen1 (all question types)
    - ConfAIde (Tier 3-4)
    - JudgeBench (meta-evaluation)
    - Scenario limits: 25000+
```

#### Processing Requirements
| Dataset | Min RAM | Optimal RAM | Processing Time (10K scenarios) |
|---------|---------|-------------|--------------------------------|
| OllaGen1 | 4GB | 8GB | 2-5 minutes |
| Garak | 8GB | 16GB | 5-10 minutes |
| LegalBench | 6GB | 12GB | 3-7 minutes |
| DocMath | 6GB | 12GB | 4-8 minutes |
| GraphWalk | 4GB | 8GB | 2-4 minutes |
| ConfAIde | 5GB | 10GB | 3-6 minutes |
| JudgeBench | 7GB | 14GB | 4-9 minutes |
| ACPBench | 8GB | 16GB | 5-12 minutes |

### Step 3: Configuration Planning

#### Single Dataset Configuration
```yaml
# Example: Focused security assessment
dataset_selection:
  primary_dataset: "Garak"
  configuration:
    vulnerability_types: ["prompt_injection", "jailbreak", "harmful_content"]
    severity_levels: ["medium", "high", "critical"]
    scenario_limit: 15000
  validation:
    baseline_tests: true
    performance_monitoring: true
```

#### Multi-Dataset Configuration
```yaml
# Example: Comprehensive evaluation
evaluation_suite:
  datasets:
    - name: "OllaGen1"
      purpose: "Behavioral baseline"
      scenarios: 20000
      focus: ["WCP", "WHO", "TeamRisk"]

    - name: "Garak"
      purpose: "Security assessment"
      scenarios: 10000
      focus: ["high_severity_vulnerabilities"]

    - name: "ConfAIde"
      purpose: "Privacy evaluation"
      scenarios: 15000
      focus: ["contextual_integrity_tiers_1-3"]

    - name: "LegalBench"
      purpose: "Domain expertise"
      scenarios: 8000
      focus: ["contract_analysis", "regulatory_compliance"]
```

### Step 4: Validation and Optimization

#### Pre-Execution Validation
```bash
# Validate dataset configuration
python -m violentutf.utils.dataset_validator \
  --config evaluation_config.yaml \
  --validate-resources \
  --estimate-time \
  --check-compatibility

# Expected output:
# ✓ Resource requirements: 24GB RAM, 50GB storage
# ✓ Estimated completion time: 3.5 hours
# ✓ Dataset compatibility: All compatible
# ⚠ Warning: High memory usage detected for parallel processing
```

#### Optimization Recommendations
```yaml
Performance Optimization:
  memory_management:
    - Enable file splitting for datasets >50MB
    - Use progressive loading for large evaluations
    - Configure memory limits per dataset

  processing_optimization:
    - Sequential processing for resource-constrained systems
    - Parallel processing for high-memory systems
    - Batch processing for very large datasets

  monitoring:
    - Enable real-time resource monitoring
    - Set up completion notifications
    - Configure intermediate checkpoints
```

## Common Workflows

### Workflow 1: First-Time User Assessment

**Objective**: Understand system capabilities with minimal resource investment

```yaml
Beginner Workflow:
  step_1:
    action: "Select OllaGen1 dataset"
    configuration:
      scenario_limit: 2000
      question_types: ["WCP"]
    rationale: "Establishes cognitive baseline"

  step_2:
    action: "Review initial results"
    focus: "Pattern recognition accuracy"
    success_criteria: ">70% accuracy on WCP questions"

  step_3:
    action: "Expand evaluation if successful"
    next_configuration:
      scenario_limit: 10000
      question_types: ["WCP", "WHO"]
    rationale: "Builds on successful baseline"
```

### Workflow 2: Security-Focused Assessment

**Objective**: Comprehensive security and risk evaluation

```yaml
Security Assessment Workflow:
  phase_1:
    datasets: ["Garak"]
    purpose: "Vulnerability identification"
    scenarios: 15000
    priority: "Critical and high severity issues"

  phase_2:
    datasets: ["ConfAIde"]
    purpose: "Privacy risk assessment"
    scenarios: 12000
    focus: "Contextual integrity evaluation"

  phase_3:
    datasets: ["OllaGen1"]
    purpose: "Behavioral risk analysis"
    scenarios: 20000
    question_types: ["WHO", "TeamRisk", "TargetFactor"]

  phase_4:
    action: "Cross-analysis and reporting"
    deliverables: ["Vulnerability report", "Risk matrix", "Mitigation plan"]
```

### Workflow 3: Domain Expertise Validation

**Objective**: Assess specialized knowledge and reasoning capabilities

```yaml
Domain Expertise Workflow:
  domain_identification:
    legal: "LegalBench"
    mathematical: "DocMath"
    spatial: "GraphWalk"
    meta_cognitive: "JudgeBench"

  assessment_strategy:
    step_1: "Identify primary domain requirement"
    step_2: "Select appropriate specialized dataset"
    step_3: "Configure complexity appropriate to use case"
    step_4: "Validate with cross-domain reasoning tests"

  validation_approach:
    baseline: "Establish performance on general reasoning"
    specialized: "Deep dive into domain-specific capabilities"
    cross_validation: "Test transfer learning across domains"
```

### Workflow 4: Progressive Complexity Assessment

**Objective**: Understand capability boundaries and optimization opportunities

```yaml
Progressive Assessment:
  stage_1_basic:
    datasets: ["OllaGen1"]
    scenarios: 5000
    complexity: "Basic WCP questions"
    success_threshold: "80% accuracy"

  stage_2_intermediate:
    trigger: "Stage 1 success"
    datasets: ["OllaGen1", "ConfAIde"]
    scenarios: [15000, 10000]
    complexity: "Medium complexity reasoning"
    success_threshold: "70% accuracy"

  stage_3_advanced:
    trigger: "Stage 2 success"
    datasets: ["All available"]
    scenarios: "Maximum feasible"
    complexity: "Full complexity range"
    analysis: "Performance degradation points"
```

## Use Cases

### Academic Research
- **Comparative Studies**: Evaluate multiple AI models using standardized datasets
- **Methodology Development**: Create new evaluation frameworks using existing datasets
- **Longitudinal Analysis**: Track model improvements over time and training iterations
- **Publication Ready Results**: Generate comprehensive evaluation reports with statistical significance

### Enterprise AI Deployment
- **Model Selection**: Compare candidate models for production deployment
- **Performance Benchmarking**: Establish baselines and track performance metrics
- **Risk Assessment**: Identify potential failures and edge cases before deployment
- **Compliance Validation**: Ensure AI systems meet regulatory and ethical requirements

### Security and Safety Testing
- **Vulnerability Assessment**: Systematic identification of security weaknesses
- **Red-Team Exercises**: Adversarial testing to find system vulnerabilities
- **Safety Validation**: Ensure AI systems operate safely in critical applications
- **Bias Detection**: Identify and quantify algorithmic bias across different demographics

### Educational and Training
- **Curriculum Development**: Create comprehensive AI evaluation training programs
- **Student Assessment**: Evaluate learning progress in AI development courses
- **Research Training**: Provide hands-on experience with evaluation methodologies
- **Best Practice Development**: Establish evaluation standards and guidelines

### Quality Assurance and Testing
- **Regression Testing**: Ensure system updates don't degrade performance
- **Release Validation**: Comprehensive testing before software releases
- **Performance Monitoring**: Continuous evaluation of deployed systems
- **User Acceptance Testing**: Validate system behavior meets user expectations

### Consulting and Professional Services
- **Client Assessment**: Evaluate client AI systems and provide recommendations
- **Custom Evaluation Design**: Create tailored evaluation frameworks for specific needs
- **Performance Optimization**: Identify areas for improvement and optimization
- **Strategic Planning**: Guide AI development and deployment strategies

## Best Practices

### Selection Criteria Prioritization

1. **Alignment with Objectives** (Weight: 40%)
   - Clear mapping between goals and dataset capabilities
   - Appropriate complexity level for target system
   - Relevant evaluation metrics and scoring

2. **Resource Optimization** (Weight: 25%)
   - Efficient use of computational resources
   - Reasonable execution timeframes
   - Appropriate memory and storage requirements

3. **Coverage Completeness** (Weight: 20%)
   - Comprehensive assessment of target capabilities
   - Balanced evaluation across relevant domains
   - Sufficient statistical significance

4. **Actionable Insights** (Weight: 15%)
   - Clear interpretation of results
   - Specific improvement recommendations
   - Comparable benchmarks and baselines

### Configuration Optimization

#### Memory Management
```yaml
Memory Optimization:
  small_systems_4gb:
    - Single dataset at a time
    - Scenario limits: <5000
    - Enable memory monitoring

  medium_systems_8gb:
    - Sequential multi-dataset processing
    - Scenario limits: <15000
    - Progressive loading enabled

  large_systems_16gb_plus:
    - Parallel processing available
    - Full scenario limits supported
    - Advanced caching enabled
```

#### Processing Efficiency
```yaml
Processing Strategies:
  sequential:
    pros: ["Lower memory usage", "More stable"]
    cons: ["Longer execution time"]
    recommended_for: "Resource-constrained systems"

  parallel:
    pros: ["Faster execution", "Better resource utilization"]
    cons: ["Higher memory usage", "More complex"]
    recommended_for: "High-performance systems"

  hybrid:
    pros: ["Balanced approach", "Adaptive to resources"]
    cons: ["Configuration complexity"]
    recommended_for: "Variable resource environments"
```

### Quality Assurance

#### Validation Checkpoints
1. **Pre-execution Validation**
   - Resource requirement verification
   - Dataset compatibility checking
   - Configuration consistency validation

2. **Mid-execution Monitoring**
   - Progress tracking and ETA updates
   - Resource usage monitoring
   - Error detection and recovery

3. **Post-execution Analysis**
   - Result completeness verification
   - Quality metrics validation
   - Performance benchmark comparison

#### Common Pitfalls and Mitigation

```yaml
Common Issues:
  resource_exhaustion:
    symptoms: "System slowdown, memory errors"
    prevention: "Proper resource planning and monitoring"
    mitigation: "Reduce scenario limits, enable optimization"

  dataset_mismatch:
    symptoms: "Poor performance, irrelevant results"
    prevention: "Careful objective-to-dataset mapping"
    mitigation: "Reassess goals and select appropriate datasets"

  configuration_errors:
    symptoms: "Unexpected results, execution failures"
    prevention: "Use validation tools and templates"
    mitigation: "Review configuration against best practices"
```

## Troubleshooting

### Selection Decision Support

If you're unsure about dataset selection, consider these diagnostic questions:

1. **What is your primary evaluation goal?**
   - Security → Garak, ConfAIde, OllaGen1
   - Domain expertise → LegalBench, DocMath, GraphWalk
   - General capability → OllaGen1, ACPBench, JudgeBench

2. **What are your resource constraints?**
   - Time limited → Single dataset, reduced scenarios
   - Memory limited → Sequential processing, file splitting
   - Storage limited → Progressive cleanup, compressed formats

3. **What is your target system's complexity?**
   - Simple systems → Basic configurations, single datasets
   - Advanced systems → Multi-dataset, full complexity
   - Unknown capability → Progressive assessment workflow

### Getting Help

- **Interactive Support**: Use MCP chat for real-time guidance
- **Configuration Validation**: Built-in validation tools
- **Community Support**: GitHub discussions and issues
- **Professional Support**: Enterprise consultation available

For detailed implementation of your selected datasets, refer to the specific dataset guides:
- [Cognitive Behavioral Assessment](Guide_Cognitive_Behavioral_Assessment.md)
- [Red-Teaming Evaluation](Guide_RedTeaming_Evaluation.md)
- [Legal Reasoning Assessment](Guide_Legal_Reasoning_Assessment.md)
- [Mathematical Reasoning Evaluation](Guide_Mathematical_Reasoning_Evaluation.md)
- [Spatial Graph Reasoning](Guide_Spatial_Graph_Reasoning.md)
- [Privacy Evaluation](Guide_Privacy_Evaluation.md)
- [Meta-Evaluation Workflows](Guide_Meta_Evaluation_Workflows.md)
