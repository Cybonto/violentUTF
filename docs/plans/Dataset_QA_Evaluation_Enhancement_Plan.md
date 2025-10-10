# Dataset Configuration Enhancement Plan for Q&A Evaluation Support

**Document Type:** Planning Document - CORRECTED VERSION
**Date:** August 15, 2025
**Author:** System Analysis (Updated after PyRIT API Review)
**Purpose:** Comprehensive analysis and CORRECTED recommendations for enhancing dataset configuration to support Question/Answer evaluation workflows

## Executive Summary - CORRECTED

This report provides a **corrected analysis** after discovering that PyRIT already has comprehensive Q&A support through `QuestionAnsweringDataset`, `QuestionAnsweringEntry`, and specialized scorers. The original enhancement plan significantly overestimated the work required because ViolentUTF already has extensive PyRIT integration infrastructure.

**Key Correction:** Instead of building new Q&A infrastructure from scratch, we need to enable and integrate PyRIT's existing Q&A capabilities into ViolentUTF's current robust architecture.

**Primary Discoveries:**
- ✅ PyRIT has native `QuestionAnsweringDataset` with full multi-choice support
- ✅ PyRIT provides `QuestionAnswerScorer` and `SelfAskQuestionAnswerScorer`
- ✅ ViolentUTF already has comprehensive PyRIT integration (orchestrators, scorers, memory)
- ❌ ViolentUTF is NOT using PyRIT's Q&A features (converts to text prompts, loses structure)
- ❌ WMDP dataset is disabled despite PyRIT support

## 1. Corrected System Analysis

### 1.1 PyRIT's Actual Q&A Capabilities (DISCOVERED)

**Native Q&A Support:**
```python
# PyRIT has complete Q&A infrastructure:
class QuestionAnsweringDataset(
    *, name: str, version: str, description: str,
    author: str, group: str, source: str,
    questions: list[QuestionAnsweringEntry]
)

class QuestionAnsweringEntry(
    *, question: str,
    answer_type: Literal['int', 'float', 'str', 'bool'],
    correct_answer: int | str | float,
    choices: list[QuestionChoice]
)

class QuestionChoice(*, index: int, text: str)
```

**Native Q&A Datasets:**
- `fetch_wmdp_dataset()` → Returns `QuestionAnsweringDataset` (not SeedPromptDataset!)
- Multiple choice questions with proper answer indexing
- Support for different answer types (int, float, str, bool)

**Native Q&A Scoring:**
- `QuestionAnswerScorer` - Direct Q&A evaluation
- `SelfAskQuestionAnswerScorer` - LLM-based Q&A evaluation
- Integration with `Score` class and memory system

### 1.2 ViolentUTF's Current PyRIT Integration (STRONG)

**Existing Infrastructure:**
- ✅ `PyRITOrchestratorService` - Full orchestrator management
- ✅ 15+ PyRIT scorers integrated (SubString, SelfAsk family, Azure, etc.)
- ✅ Complete scorer configuration UI (`4_Configure_Scorers.py`)
- ✅ Comprehensive scorer REST API (`/api/v1/scorers`)
- ✅ PyRIT `CentralMemory` integration for persistent storage
- ✅ `PromptSendingOrchestrator` with scorer support
- ✅ Score storage and retrieval system

**Critical Gap Identified:**
ViolentUTF has the infrastructure but is missing the Q&A-specific components:
```python
# Current Issue in ViolentUTF:
# data_loaders.py line 66:
# 'wmdp': fetch_wmdp_dataset,  # COMMENTED OUT!

# Current Issue in dataset endpoints:
elif dataset_type == "wmdp":
    # Loses Q&A structure - extracts only text!
    for question in dataset.questions:
        prompts.append(question.question)  # Loses choices & answers!
```

## 2. Corrected Gap Analysis

### 2.1 Real vs. Assumed Gaps

**❌ ASSUMED Gaps (Not Actually Missing):**
- ~~Need to build Q&A evaluation infrastructure~~ → **EXISTS in PyRIT**
- ~~Need to create scoring mechanisms~~ → **EXISTS in PyRIT**
- ~~Need to build orchestrator integration~~ → **EXISTS in ViolentUTF**
- ~~Need to create memory storage~~ → **EXISTS in ViolentUTF**

**✅ REAL Gaps (Actually Missing):**
1. **Q&A Dataset Type Support**: `QuestionAnsweringDataset` not supported in dataset pipeline
2. **Missing Q&A Scorers**: `QuestionAnswerScorer` and `SelfAskQuestionAnswerScorer` not integrated
3. **WMDP Dataset Disabled**: Available in PyRIT but commented out in ViolentUTF
4. **Q&A Structure Loss**: Converting Q&A data to simple text prompts
5. **Q&A Workflows**: No specialized Q&A evaluation templates

### 2.2 Sample Dataset Compatibility

**OllaGen1-QA-full.csv Analysis:**
- Format: 4 Q&A types with multiple choice questions
- Compatible with PyRIT `QuestionAnsweringEntry` structure:
  ```python
  # OllaGen1 can map to:
  QuestionAnsweringEntry(
      question="Which cognitive construct...",
      answer_type="int",  # Index of correct option
      correct_answer=1,   # (option b) = index 1
      choices=[
          QuestionChoice(index=0, text="['Intent', 'Group norms', ...]"),
          QuestionChoice(index=1, text="['Group norms', 'Subjective norms', ...]"),
          # etc.
      ]
  )
  ```

## 3. Simplified Enhancement Strategy

### 3.1 Leverage Existing Infrastructure

**Instead of Building New:**
- ✅ Use existing PyRIT `QuestionAnsweringDataset`
- ✅ Use existing PyRIT Q&A scorers
- ✅ Use existing ViolentUTF orchestrator system
- ✅ Use existing ViolentUTF scorer configuration UI
- ✅ Use existing ViolentUTF memory integration

**Focus Areas:**
1. Enable PyRIT Q&A features in ViolentUTF
2. Add missing PyRIT scorers to ViolentUTF
3. Create Q&A dataset import/export workflows
4. Preserve Q&A structure in dataset pipeline

### 3.2 Architecture Approach

**Minimal Changes, Maximum Impact:**
```
Existing ViolentUTF → Add Q&A Support → Enhanced ViolentUTF
     ↓                        ↓                    ↓
[PyRIT Integration]  →  [Enable Q&A Types]  →  [Q&A Evaluation]
[Scorer Infrastructure] → [Add Q&A Scorers] → [Q&A Testing]
[Dataset Pipeline]   →  [Support QADataset] → [Q&A Import/Export]
```

## 4. Corrected Implementation Plan

### 4.1 Phase 1: Enable PyRIT Q&A Features (Sprint 1)

**Week 1-2: Enable WMDP and Q&A Dataset Support**

```python
# 1. Uncomment WMDP in data_loaders.py
PYRIT_DATASETS = {
    "wmdp": fetch_wmdp_dataset,  # ENABLE THIS!
    # ... existing datasets
}

# 2. Add to NATIVE_DATASET_TYPES in datasets.py
"wmdp": {
    "name": "wmdp",
    "description": "WMDP Dataset - Weapons of Mass Destruction Proxy",
    "category": "qa_evaluation",
    "config_required": True,
    "available_configs": {
        "category": ["bio", "chem", "cyber", None]
    },
    "returns_qa_dataset": True  # NEW FIELD
}
```

**Week 3-4: Add Missing PyRIT Scorers**

```python
# Add to scorer categories in scorers.py
"Question Answering Scorers": {
    "description": "Specialized scorers for Q&A dataset evaluation",
    "scorers": [
        "QuestionAnswerScorer",          # MISSING - ADD THIS
        "SelfAskQuestionAnswerScorer"    # MISSING - ADD THIS
    ]
}
```

### 4.2 Phase 2: Q&A Dataset Pipeline (Sprint 2)

**Week 5-6: Preserve Q&A Structure**

```python
# Modified dataset handling to preserve Q&A structure
async def _load_real_pyrit_dataset(dataset_type: str, config: Dict[str, Any]):
    if dataset_type == "wmdp":
        dataset = fetch_wmdp_dataset(**config)
        # PRESERVE Q&A structure instead of converting to text
        return {
            "type": "question_answering",
            "dataset": dataset,
            "questions": dataset.questions,
            "total_questions": len(dataset.questions)
        }

    # Handle other Q&A datasets
    if hasattr(dataset, 'questions'):
        return preserve_qa_structure(dataset)

    # Standard SeedPromptDataset handling
    return standard_dataset_handling(dataset)
```

**Week 7-8: Q&A Import/Export**

```python
# Support importing external Q&A datasets like OllaGen1-QA-full.csv
class QADatasetConverter:
    def csv_to_question_answering_dataset(self, csv_path: str) -> QuestionAnsweringDataset:
        df = pd.read_csv(csv_path)
        questions = []

        # Detect Q&A column patterns (_Question/_Answer)
        qa_pairs = self.detect_qa_columns(df)

        for _, row in df.iterrows():
            for qa_pair in qa_pairs:
                question_text = row[qa_pair.question_col]
                answer_text = row[qa_pair.answer_col]

                # Parse multiple choice format
                choices = self.parse_choices(question_text)
                correct_answer = self.extract_correct_answer(answer_text)

                questions.append(QuestionAnsweringEntry(
                    question=question_text,
                    answer_type="int",
                    correct_answer=correct_answer,
                    choices=choices
                ))

        return QuestionAnsweringDataset(
            name="Imported Q&A Dataset",
            questions=questions
        )
```

### 4.3 Phase 3: Enhanced Q&A Workflows (Sprint 3)

**Week 9-10: Q&A Evaluation Templates**

```python
# Create Q&A-specific orchestrator templates
class QAEvaluationTemplate:
    def create_qa_orchestrator(self, qa_dataset: QuestionAnsweringDataset, generator_config: Dict):
        # Use existing PyRIT orchestrator infrastructure
        orchestrator = PromptSendingOrchestrator(
            objective_target=self.create_generator(generator_config),
            scorers=[
                QuestionAnswerScorer(),  # Direct Q&A accuracy
                SelfAskQuestionAnswerScorer(
                    chat_target=self.get_llm_target(),
                    question_path="qa_evaluation_template.yaml"
                )
            ]
        )
        return orchestrator

    def execute_qa_evaluation(self, orchestrator, qa_dataset):
        # Convert Q&A dataset to prompts for orchestrator
        prompts = [q.question for q in qa_dataset.questions]

        # Execute using existing infrastructure
        results = await orchestrator.send_prompts_async(prompts)

        # Post-process with Q&A-specific analysis
        return self.analyze_qa_results(results, qa_dataset)
```

### 4.4 Phase 4: UI Integration (Sprint 4)

**Week 11-12: Enhanced Dataset Configuration UI**

```python
# Update 2_Configure_Datasets.py to support Q&A datasets
def handle_qa_dataset_selection():
    if st.session_state.get('selected_dataset_type') in ['wmdp']:
        st.info("🎯 This is a Question & Answer dataset with evaluation capabilities")

        # Show Q&A-specific configuration options
        with st.expander("📊 Q&A Dataset Configuration"):
            eval_mode = st.selectbox(
                "Evaluation Mode",
                ["accuracy", "detailed_analysis", "comparative"]
            )

            include_explanations = st.checkbox(
                "Include Answer Explanations",
                value=True
            )

        # Show Q&A preview instead of text preview
        if st.button("Preview Q&A Structure"):
            show_qa_preview(dataset)
```

**Week 13-14: Q&A Testing Integration**

```python
# Enhanced testing for Q&A datasets in existing UI
def qa_dataset_testing():
    if is_qa_dataset(st.session_state.dataset):
        st.subheader("🎯 Q&A Evaluation Testing")

        # Use existing generator selection UI
        selected_generator = st.selectbox("Select Generator", get_generators())

        # Q&A-specific testing options
        eval_sample_size = st.slider("Questions to Test", 1, 20, 5)

        if st.button("Run Q&A Evaluation Test"):
            # Use existing orchestrator infrastructure
            results = run_qa_test_evaluation(
                qa_dataset=st.session_state.dataset,
                generator=selected_generator,
                sample_size=eval_sample_size
            )

            # Display Q&A-specific results
            display_qa_test_results(results)
```

## 5. Technical Specifications (Corrected)

### 5.1 Minimal Database Changes

**No New Tables Required** - Use existing PyRIT memory and ViolentUTF dataset storage:

```sql
-- Just add Q&A metadata to existing dataset table
ALTER TABLE datasets ADD COLUMN is_qa_dataset BOOLEAN DEFAULT FALSE;
ALTER TABLE datasets ADD COLUMN qa_questions_count INTEGER DEFAULT 0;
ALTER TABLE datasets ADD COLUMN qa_metadata JSON DEFAULT '{}';
```

### 5.2 Minimal API Changes

**Extend Existing Endpoints** instead of creating new ones:

```python
# Extend existing /datasets endpoints
@router.get("/datasets/types", response_model=DatasetTypesResponse)
async def get_dataset_types():
    # Add qa_evaluation category to existing types

@router.post("/datasets", response_model=DatasetCreateResponse)
async def create_dataset():
    # Add QuestionAnsweringDataset support to existing creation logic

# Extend existing /scorers endpoints
@router.get("/scorers/types", response_model=ScorerTypesResponse)
async def get_scorer_types():
    # Add QuestionAnswerScorer and SelfAskQuestionAnswerScorer
```

### 5.3 Configuration Extensions

**Minimal Environment Variables:**

```bash
# Q&A Feature Toggles
ENABLE_QA_DATASETS=true
ENABLE_QA_SCORERS=true
WMDP_DATASET_ENABLED=true

# Use existing PyRIT configurations
PYRIT_MEMORY_ENABLED=true  # Already exists
ORCHESTRATOR_SCORING_ENABLED=true  # Already exists
```

## 6. Benefits and Expected Outcomes (Corrected)

### 6.1 Immediate Benefits (Much Simpler Implementation)

**Leveraging Existing Infrastructure:**
- ✅ 80% of needed infrastructure already exists
- ✅ No new databases, APIs, or major UI changes needed
- ✅ Reuse existing PyRIT memory, scoring, and orchestration
- ✅ Add Q&A support in weeks, not months

**Enhanced Dataset Capabilities:**
- ✅ Native PyRIT `QuestionAnsweringDataset` support
- ✅ WMDP dataset availability for weapons proxy evaluation
- ✅ Multi-choice question processing with answer validation
- ✅ Structured Q&A evaluation workflows

### 6.2 Long-term Value

**Research and Development:**
- 📊 Standardized Q&A evaluation using proven PyRIT framework
- 📊 Benchmark datasets for cognitive behavioral analysis (OllaGen1)
- 📊 Comparative model performance analysis with existing tools
- 📊 Historical trend analysis using existing memory system

**Enterprise Security Applications:**
- 🔒 Cognitive behavioral risk assessment with Q&A datasets
- 🔒 Information security compliance evaluation using PyRIT scorers
- 🔒 Team dynamics analysis through multi-choice questionnaires
- 🔒 Targeted intervention recommendations using existing analytics

## 7. Risk Mitigation (Lower Risk Profile)

### 7.1 Technical Risks (Reduced)

**Complexity Management:**
- Risk: REDUCED - Building on existing infrastructure vs. creating new
- Mitigation: Incremental enhancement of proven components
- Monitoring: Existing performance metrics and user feedback systems

**Performance Impact:**
- Risk: MINIMAL - Q&A processing uses existing PyRIT optimizations
- Mitigation: Leverage existing async processing and memory management
- Monitoring: Existing response time metrics and resource utilization

### 7.2 User Experience Risks (Lower)

**Learning Curve:**
- Risk: REDUCED - Q&A features integrate into existing familiar UI
- Mitigation: Extend existing workflows rather than creating new ones
- Monitoring: Existing user completion rates and support ticket systems

**Data Quality:**
- Risk: MITIGATED - PyRIT's proven Q&A validation and error handling
- Mitigation: Use PyRIT's built-in Q&A data validation
- Monitoring: Existing dataset validation metrics and user feedback

## 8. Success Metrics (Adjusted)

### 8.1 Adoption Metrics

- **Q&A Dataset Creation**: Target 10+ Q&A datasets per month (vs. original 20+)
- **WMDP Usage**: Target 50+ WMDP evaluations per month (new metric)
- **Q&A Scorer Usage**: Target 80% adoption of Q&A scorers (leveraging existing scorer UI)
- **Feature Integration**: Target >90% compatibility with existing workflows

### 8.2 Performance Metrics

- **Q&A Processing**: Target <1 second Q&A schema detection (using PyRIT optimizations)
- **Evaluation Speed**: Target <3 minutes Q&A evaluation for 50 questions (using existing orchestrator)
- **Accuracy**: Target >98% Q&A answer extraction accuracy (PyRIT proven performance)
- **System Stability**: Target zero breaking changes to existing dataset workflows

## 9. Implementation Timeline (Accelerated)

### 9.1 Revised Timeline

**Total Duration: 8 weeks** (vs. original 16 weeks)

**Sprint 1 (Weeks 1-2): Enable PyRIT Q&A Features**
- Uncomment and enable WMDP dataset
- Add missing PyRIT Q&A scorers to configuration
- Test basic Q&A dataset loading

**Sprint 2 (Weeks 3-4): Q&A Pipeline Integration**
- Preserve Q&A structure in dataset processing
- Create Q&A dataset conversion utilities (OllaGen1 support)
- Integrate Q&A datasets with existing memory system

**Sprint 3 (Weeks 5-6): Q&A Evaluation Workflows**
- Create Q&A evaluation templates using existing orchestrators
- Integrate Q&A scorers with evaluation pipeline
- Add Q&A-specific result analytics

**Sprint 4 (Weeks 7-8): UI Integration & Testing**
- Enhance existing dataset configuration UI for Q&A
- Add Q&A testing capabilities to existing test framework
- Create Q&A evaluation examples and documentation

## 10. Conclusion (Corrected)

The original enhancement plan significantly overestimated the complexity required to add Q&A evaluation capabilities to ViolentUTF. After reviewing PyRIT's actual API and ViolentUTF's existing integration, the solution is much simpler:

**Key Insight:** ViolentUTF already has 80% of the required infrastructure through its comprehensive PyRIT integration. We need to enable and connect PyRIT's existing Q&A capabilities rather than build new systems from scratch.

**Corrected Approach:**
1. **Enable Existing PyRIT Q&A Features** (WMDP, Q&A scorers)
2. **Preserve Q&A Structure** in existing dataset pipeline
3. **Extend Existing UI** to support Q&A workflows
4. **Create Q&A Templates** using existing orchestrator system

**Major Benefits:**
- ⚡ **8 weeks vs. 16 weeks** implementation time
- 🏗️ **Minimal architectural changes** required
- 🔧 **Leverage proven PyRIT Q&A infrastructure**
- 📈 **Build on existing robust ViolentUTF platform**

The OllaGen1-QA-full.csv sample dataset is perfectly compatible with PyRIT's `QuestionAnsweringDataset` format, providing an excellent validation use case for the enhanced capabilities.

**Next Steps:**
1. Sprint planning with development team based on corrected timeline
2. Enable WMDP dataset and missing Q&A scorers (Week 1)
3. Test Q&A dataset processing with OllaGen1 sample (Week 2)
4. Create Q&A evaluation workflow templates (Week 3-4)
5. User acceptance testing with Q&A datasets (Week 5-6)

---

*This document reflects accurate understanding of PyRIT's capabilities and ViolentUTF's existing infrastructure after comprehensive API analysis and code review.*
