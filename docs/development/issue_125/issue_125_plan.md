# Implementation Plan - ACPBench Dataset Converter

**Issue**: #125 - Implement ACPBench Dataset Converter (JSON to QuestionAnsweringDataset)
**Parent EPIC**: #116 - Integrating Datasets Round 1
**Backend Engineer**: TDD Implementation Plan

## Executive Summary

Implement a comprehensive ACPBench (Action, Change, Planning) dataset converter following Strategy 2 (Reasoning Benchmarks), transforming 3 JSON file types (bool.json, mcq.json, gen.json) into PyRIT QuestionAnsweringDataset format with preserved planning domain context and metadata.

## Technical Architecture

### Core Components

1. **ACPBenchConverter** (main converter class)
   - Extends base converter pattern established in GarakConverter
   - Implements JSON file detection and type-specific processing
   - Coordinates question type handlers and batch processing

2. **Question Type Handlers**
   - `BooleanQuestionHandler` for bool.json files
   - `MultipleChoiceQuestionHandler` for mcq.json files
   - `GenerationQuestionHandler` for gen.json files

3. **Planning Domain Analyzer**
   - Domain classification (logistics, blocks-world, scheduling, etc.)
   - Complexity assessment based on content analysis
   - Metadata extraction for planning scenarios

4. **Batch Processing Engine**
   - Multi-file JSON processing with progress tracking
   - Memory-efficient streaming for large datasets
   - Validation and quality assurance pipeline

### File Structure Implementation

```
violentutf_api/fastapi_app/app/
├── core/converters/
│   └── acpbench_converter.py          # Main converter implementation
├── schemas/
│   └── acpbench_datasets.py           # Pydantic schemas and types
├── services/
│   └── planning_service.py            # Planning domain analysis service
└── utils/
    └── planning_utils.py              # Planning-specific utilities
```

## Detailed Implementation Steps

### Phase 1: Schema and Type Definitions

#### 1.1 Create ACPBench Schemas (`app/schemas/acpbench_datasets.py`)

```python
class PlanningQuestionType(str, Enum):
    """ACPBench question types."""
    BOOLEAN = "boolean"
    MULTIPLE_CHOICE = "multiple_choice"
    GENERATION = "generation"

class PlanningDomain(str, Enum):
    """Planning domains in ACPBench."""
    LOGISTICS = "logistics"
    BLOCKS_WORLD = "blocks_world"
    SCHEDULING = "scheduling"
    GENERAL_PLANNING = "general_planning"

class PlanningComplexity(str, Enum):
    """Planning task complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ACPBenchQuestionAnsweringEntry(BaseModel):
    """ACPBench-specific QuestionAnsweringEntry."""
    question: str
    answer_type: str  # "bool", "int", "str"
    correct_answer: Union[bool, int, str]
    choices: List[str] = []
    metadata: Dict[str, Any]

class PlanningDomainMetadata(BaseModel):
    """Planning domain analysis metadata."""
    domain: PlanningDomain
    complexity: PlanningComplexity
    key_concepts: List[str]
    planning_elements: Dict[str, Any]
    task_characteristics: Dict[str, Any]

class ACPBenchConversionResult(BaseModel):
    """Result of ACPBench conversion process."""
    success: bool
    dataset_name: str
    total_questions: int
    question_breakdown: Dict[str, int]
    conversion_time_seconds: float
    quality_metrics: Dict[str, float]
    error_message: Optional[str] = None
```

#### 1.2 Create Planning Service (`app/services/planning_service.py`)

```python
class PlanningDomainClassifier:
    """Classifies planning domains based on content analysis."""

    def __init__(self):
        self.domain_patterns = {
            PlanningDomain.LOGISTICS: [
                "truck", "package", "location", "deliver", "transport",
                "cargo", "route", "warehouse", "shipping"
            ],
            PlanningDomain.BLOCKS_WORLD: [
                "block", "stack", "clear", "table", "on", "above",
                "tower", "pyramid", "arrange"
            ],
            PlanningDomain.SCHEDULING: [
                "schedule", "time", "resource", "appointment", "slot",
                "calendar", "meeting", "deadline", "priority"
            ],
            PlanningDomain.GENERAL_PLANNING: [
                "action", "goal", "state", "operator", "precondition",
                "effect", "plan", "sequence"
            ]
        }

    def classify_domain(self, context: str, question: str) -> PlanningDomain:
        """Classify planning domain based on content."""
        # Implementation details...

    def assess_complexity(self, context: str, question: str) -> PlanningComplexity:
        """Assess planning task complexity."""
        # Implementation details...
```

### Phase 2: Question Type Handlers

#### 2.1 Boolean Question Handler

```python
class BooleanQuestionHandler:
    """Handles boolean planning questions from bool.json."""

    def create_qa_entry(self, item: Dict) -> ACPBenchQuestionAnsweringEntry:
        full_question = f"Context: {item['context']}\n\nQuestion: {item['question']}"

        return ACPBenchQuestionAnsweringEntry(
            question=full_question,
            answer_type="bool",
            correct_answer=item['correct'],
            choices=[],
            metadata={
                "task_id": item['id'],
                "planning_group": item['group'],
                "question_type": PlanningQuestionType.BOOLEAN,
                "domain": "planning_reasoning",
                "original_context": item['context'],
                "planning_domain_metadata": self.extract_domain_metadata(item)
            }
        )
```

#### 2.2 Multiple Choice Handler

```python
class MultipleChoiceQuestionHandler:
    """Handles multiple choice questions from mcq.json."""

    def create_qa_entry(self, item: Dict) -> ACPBenchQuestionAnsweringEntry:
        choices = item.get('choices', [])
        correct_answer_index = self.find_correct_answer_index(
            item['answer'], choices
        )

        return ACPBenchQuestionAnsweringEntry(
            question=f"Context: {item['context']}\n\nQuestion: {item['question']}",
            answer_type="int",
            correct_answer=correct_answer_index,
            choices=choices,
            metadata={
                "task_id": item['id'],
                "planning_group": item['group'],
                "question_type": PlanningQuestionType.MULTIPLE_CHOICE,
                "choice_count": len(choices),
                "planning_domain_metadata": self.extract_domain_metadata(item)
            }
        )
```

#### 2.3 Generation Question Handler

```python
class GenerationQuestionHandler:
    """Handles generation questions from gen.json."""

    def create_qa_entry(self, item: Dict) -> ACPBenchQuestionAnsweringEntry:
        return ACPBenchQuestionAnsweringEntry(
            question=f"Context: {item['context']}\n\nQuestion: {item['question']}",
            answer_type="str",
            correct_answer=item.get('expected_response', ''),
            choices=[],
            metadata={
                "task_id": item['id'],
                "planning_group": item['group'],
                "question_type": PlanningQuestionType.GENERATION,
                "response_type": "action_sequence",
                "planning_domain_metadata": self.extract_domain_metadata(item)
            }
        )
```

### Phase 3: Main Converter Implementation

#### 3.1 ACPBench Converter Core (`app/core/converters/acpbench_converter.py`)

```python
class ACPBenchConverter:
    """Main converter for ACPBench datasets."""

    def __init__(self):
        self.planning_classifier = PlanningDomainClassifier()
        self.boolean_handler = BooleanQuestionHandler()
        self.mcq_handler = MultipleChoiceQuestionHandler()
        self.gen_handler = GenerationQuestionHandler()

    def convert(self, dataset_path: str) -> QuestionAnsweringDataset:
        """Convert ACPBench dataset to QuestionAnsweringDataset format."""

        all_questions = []
        file_summary = {}

        # Process each JSON file type
        for file_type in ["bool.json", "mcq.json", "gen.json"]:
            file_path = os.path.join(dataset_path, file_type)

            if os.path.exists(file_path):
                questions = self.process_json_file(file_path, file_type)
                all_questions.extend(questions)
                file_summary[file_type] = {
                    "question_count": len(questions),
                    "planning_groups": list(set(
                        q.metadata["planning_group"] for q in questions
                    ))
                }

        return QuestionAnsweringDataset(
            name="ACPBench_Planning_Reasoning",
            version="1.0",
            description="Automated planning and logical reasoning tasks",
            author="IBM Research",
            group="planning_reasoning",
            source="ACPBench-IBM",
            questions=all_questions,
            metadata={
                "total_questions": len(all_questions),
                "question_types": ["boolean", "multiple_choice", "generation"],
                "planning_domains": 7,
                "file_summary": file_summary,
                "conversion_strategy": "strategy_2_reasoning_benchmarks"
            }
        )

    def process_json_file(self, file_path: str, file_type: str) -> List[QuestionAnsweringEntry]:
        """Process a single JSON file by type."""

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        questions = []

        if file_type == "bool.json":
            handler = self.boolean_handler
        elif file_type == "mcq.json":
            handler = self.mcq_handler
        elif file_type == "gen.json":
            handler = self.gen_handler
        else:
            raise ValueError(f"Unknown file type: {file_type}")

        for item in data:
            qa_entry = handler.create_qa_entry(item)
            questions.append(qa_entry)

        return questions
```

## Testing Strategy

### Unit Tests (`tests/test_acpbench_converter.py`)

1. **JSON Parsing Tests**
   - Test each question type parsing (bool, mcq, gen)
   - Test malformed JSON handling
   - Test missing field scenarios

2. **Question Handler Tests**
   - Test boolean question creation
   - Test multiple choice answer mapping
   - Test generation question formatting
   - Test metadata preservation

3. **Planning Domain Tests**
   - Test domain classification accuracy
   - Test complexity assessment
   - Test key concept extraction

4. **Integration Tests**
   - Test complete conversion pipeline
   - Test batch processing across multiple files
   - Test PyRIT format compliance

### Test Data Samples

```json
// bool.json sample
{
    "id": "logistics_1",
    "group": "logistics",
    "context": "In a logistics scenario with trucks and packages...",
    "question": "Can the package be delivered within time constraints?",
    "correct": true
}

// mcq.json sample
{
    "id": "blocks_world_1",
    "group": "blocks_world",
    "context": "Given blocks A, B, C in initial configuration...",
    "question": "What is the optimal action sequence?",
    "choices": ["A) Move A then B", "B) Move B then A", "C) Move C first"],
    "answer": "A) Move A then B"
}

// gen.json sample
{
    "id": "planning_1",
    "group": "general_planning",
    "context": "In a planning scenario with multiple agents...",
    "question": "Generate the complete action sequence.",
    "expected_response": "Step 1: Initialize... Step 2: Execute..."
}
```

## Performance Requirements

### Processing Targets
- **Conversion Speed**: Complete processing <2 minutes for all 3 files
- **Memory Usage**: Peak memory <500MB during batch processing
- **Throughput**: >100 questions per second processing rate

### Quality Metrics
- **Context Preservation**: 100% of planning context maintained
- **Answer Accuracy**: >98% correct answer type assignment
- **Domain Classification**: >95% accuracy in planning domain categorization
- **PyRIT Compliance**: 100% format compatibility

## Error Handling & Edge Cases

### Common Error Scenarios
1. **Malformed JSON**: Graceful handling with error reporting
2. **Missing Fields**: Default value assignment with warnings
3. **Invalid Answer Types**: Type correction with validation
4. **File Access Issues**: Clear error messages and fallback options

### Validation Pipeline
1. **Input Validation**: JSON structure and required fields
2. **Content Validation**: Planning context and question quality
3. **Output Validation**: PyRIT format compliance
4. **Metadata Validation**: Complete planning domain information

## Integration Points

### PyRIT Integration
- Generate QuestionAnsweringDataset compatible with PyRIT workflows
- Ensure proper answer type mapping for evaluation pipelines
- Include comprehensive metadata for planning analysis

### API Integration
- Register ACPBench as planning reasoning dataset type
- Configure domain categories and selection options
- Enable UI integration for dataset management

## Completion Criteria

### Functional Requirements
- [x] All 3 question types (bool, mcq, gen) successfully converted
- [x] Context and planning domain information preserved
- [x] Planning task metadata extracted and categorized
- [x] Batch processing works across multiple JSON files
- [x] Appropriate answer types for each question format
- [x] Validation confirms planning task relationships maintained

### Quality Requirements
- [x] Performance benchmarks met (<2 min processing)
- [x] Integration tests pass with PyRIT evaluation workflows
- [x] Security scan passes without critical issues
- [x] Code review approval with maintainability standards

### Documentation Requirements
- [x] Implementation plan documented
- [x] API documentation updated
- [x] Test coverage reports generated
- [x] Deployment and configuration guides

## Risk Mitigation

### Technical Risks
**Risk**: Complex planning context difficult to preserve accurately
**Mitigation**: Comprehensive context combination with validation testing

**Risk**: Answer type mapping inconsistent across question formats
**Mitigation**: Robust type detection with automated testing suite

**Risk**: Planning domain classification inaccurate
**Mitigation**: Multi-factor classification with expert validation samples

### Performance Risks
**Risk**: Memory usage exceeds limits during batch processing
**Mitigation**: Streaming JSON processing with memory monitoring

**Risk**: Processing time exceeds 2-minute target
**Mitigation**: Parallel processing and performance profiling optimization

## Success Metrics

### Conversion Quality
- Data integrity preservation: 100%
- Planning domain accuracy: >95%
- Answer type mapping: >98%
- PyRIT format compliance: 100%

### Performance Benchmarks
- Conversion time: <2 minutes
- Memory usage: <500MB peak
- Processing throughput: >100 questions/second
- Error rate: <2%

This comprehensive implementation plan ensures systematic development of the ACPBench converter following TDD methodology with rigorous quality assurance and performance optimization.
