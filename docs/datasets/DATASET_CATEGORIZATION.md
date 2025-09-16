# Dataset Categorization System

ViolentUTF implements a purpose-driven categorization system for its 18 datasets (10 PyRIT + 8 ViolentUTF specialized), organizing them by their actual functionality and intended use in AI security evaluation workflows.

## Category Overview

### 1. AI Safety & Harm Evaluation
**Focus**: General AI safety, harmful behavior detection, and security vulnerabilities

**Datasets**:
- `harmbench` - Standardized harmful behavior evaluation benchmark
- `adv_bench` - Adversarial attack evaluation (jailbreak resistance)
- `forbidden_questions` - Testing responses to prohibited queries
- `pku_safe_rlhf` - Safety-oriented reinforcement learning evaluation

**Use Cases**:
- Basic AI safety testing
- Harmful content detection
- Security vulnerability assessment
- Model alignment verification

### 2. Bias & Fairness Testing
**Focus**: Detecting demographic bias, stereotyping, and fairness issues

**Datasets**:
- `decoding_trust_stereotypes` - Stereotype detection and bias evaluation
- `seclists_bias_testing` - Systematic bias testing with demographic variations
- `aya_redteaming` - Multilingual bias and harm evaluation

**Use Cases**:
- Demographic bias detection
- Fairness evaluation across populations
- Stereotype identification
- Cross-cultural bias assessment

### 3. Jailbreaking & Attack Resistance
**Focus**: Testing model robustness against sophisticated prompt attacks

**Datasets**:
- `many_shot_jailbreaking` - Multi-shot jailbreaking attack patterns
- `xstest` - Exaggerated safety testing and over-refusal detection

**Use Cases**:
- Jailbreak resistance testing
- Prompt injection detection
- Attack pattern evaluation
- Safety mechanism validation

### 4. Privacy & Contextual Integrity
**Focus**: Privacy sensitivity, contextual awareness, and data protection

**Datasets**:
- `confaide_privacy` - Privacy evaluation using Contextual Integrity Theory (4-tier complexity)

**Use Cases**:
- Privacy sensitivity assessment
- Contextual integrity evaluation
- Data protection compliance
- Privacy framework testing

### 5. Cognitive & Behavioral Assessment
**Focus**: Cognitive abilities, behavioral patterns, and compliance evaluation

**Datasets**:
- `ollgen1_cognitive` - Cognitive and behavioral assessment scenarios
- `judgelm_evaluation` - Meta-evaluation and judgment assessment capabilities

**Use Cases**:
- Cognitive capability evaluation
- Behavioral pattern analysis
- Decision-making assessment
- Meta-evaluation testing

### 6. Domain-Specific Reasoning
**Focus**: Specialized knowledge domains and professional reasoning

**Datasets**:
- `acpbench_planning` - Automated planning and meta-evaluation capabilities
- `docmath_mathematical` - Document-based mathematical reasoning and problem solving
- `wmdp` - Weapons of mass destruction knowledge evaluation (cyber/bio/chem)
- `mathbench_reasoning` - Advanced mathematical reasoning and proof validation

**Use Cases**:
- Domain expertise evaluation
- Professional knowledge testing
- Specialized reasoning assessment
- Technical capability validation

### 7. Specialized Security & Compliance
**Focus**: Specialized security testing and regulatory compliance

**Datasets**:
- `legalbench_professional` - Legal reasoning and regulatory compliance evaluation

**Use Cases**:
- Regulatory compliance testing
- Legal reasoning evaluation
- Security policy assessment
- Compliance framework validation

## Implementation

### UI Interface
The Configure Datasets page now uses a two-stage selection process:
1. **Category Selection**: Users first select from the 7 purpose-driven categories
2. **Dataset Selection**: Within the chosen category, users select specific datasets

### API Endpoints
- `/api/v1/datasets/categories` - Retrieve all categories with their datasets
- `/api/v1/datasets/types` - Retrieve individual dataset information (maintained for compatibility)

### Benefits
1. **Purpose-Driven**: Categories reflect actual dataset intentions
2. **User-Oriented**: Security professionals can quickly identify relevant datasets
3. **Scalable**: New datasets can be easily categorized based on primary purpose
4. **Workflow-Aligned**: Categories align with typical AI red-teaming workflows

## Migration Notes
- Backward compatibility maintained for existing dataset references
- Category mapping implemented in `violentutf_api/fastapi_app/app/api/endpoints/datasets.py`
- UI updated in `violentutf/pages/2_Configure_Datasets.py`
- Deprecated configuration files removed:
  - `2_Configure_Datasets_option1_fullwidth.py`
  - `2_Configure_Datasets_option2_tabs.py`
