# Test Suite Specification - Issue #125: ACPBench Dataset Converter

**Issue**: #125 - Implement ACPBench Dataset Converter (JSON to QuestionAnsweringDataset)  
**Testing Strategy**: Test-Driven Development (TDD)  
**Coverage Target**: 100% for all converter components

## Test Categories Overview

### 1. Unit Tests - Core Components

#### 1.1 ACPBench Schema Validation Tests
- **File**: `test_acpbench_schemas.py`
- **Purpose**: Validate Pydantic schemas and type definitions

**Test Cases:**
```python
def test_planning_question_type_enum():
    """Test PlanningQuestionType enum values."""

def test_planning_domain_enum():
    """Test PlanningDomain enum classifications."""

def test_acpbench_qa_entry_validation():
    """Test ACPBenchQuestionAnsweringEntry validation."""

def test_planning_domain_metadata_structure():
    """Test PlanningDomainMetadata schema."""

def test_acpbench_conversion_result_schema():
    """Test ACPBenchConversionResult validation."""
```

#### 1.2 JSON File Processing Tests
- **File**: `test_acpbench_json_processing.py`
- **Purpose**: Test JSON parsing and validation

**Test Cases:**
```python
def test_parse_bool_json_valid():
    """Test parsing valid bool.json structure."""

def test_parse_mcq_json_valid():
    """Test parsing valid mcq.json structure."""

def test_parse_gen_json_valid():
    """Test parsing valid gen.json structure."""

def test_handle_malformed_json():
    """Test graceful handling of malformed JSON."""

def test_handle_missing_required_fields():
    """Test handling of missing required fields."""

def test_json_file_type_detection():
    """Test automatic detection of JSON file types."""
```

#### 1.3 Question Type Handler Tests
- **File**: `test_acpbench_question_handlers.py`
- **Purpose**: Test question type-specific processing

**Boolean Handler Tests:**
```python
def test_boolean_handler_create_qa_entry():
    """Test boolean question QuestionAnsweringEntry creation."""

def test_boolean_handler_context_preservation():
    """Test context information preservation."""

def test_boolean_handler_metadata_extraction():
    """Test metadata extraction for boolean questions."""

def test_boolean_handler_answer_type_validation():
    """Test answer_type is correctly set to 'bool'."""
```

**Multiple Choice Handler Tests:**
```python
def test_mcq_handler_create_qa_entry():
    """Test MCQ QuestionAnsweringEntry creation."""

def test_mcq_handler_choice_extraction():
    """Test choice option extraction and formatting."""

def test_mcq_handler_correct_answer_mapping():
    """Test correct answer index mapping."""

def test_mcq_handler_invalid_choices():
    """Test handling of malformed choice options."""
```

**Generation Handler Tests:**
```python
def test_gen_handler_create_qa_entry():
    """Test generation question QuestionAnsweringEntry creation."""

def test_gen_handler_expected_response_extraction():
    """Test expected_response field handling."""

def test_gen_handler_action_sequence_metadata():
    """Test action sequence metadata tagging."""
```

#### 1.4 Planning Domain Classification Tests
- **File**: `test_acpbench_planning_domain.py`
- **Purpose**: Test planning domain analysis and classification

**Test Cases:**
```python
def test_logistics_domain_classification():
    """Test logistics domain pattern recognition."""

def test_blocks_world_domain_classification():
    """Test blocks-world domain pattern recognition."""

def test_scheduling_domain_classification():
    """Test scheduling domain pattern recognition."""

def test_general_planning_domain_classification():
    """Test general planning domain classification."""

def test_planning_complexity_assessment():
    """Test complexity level assessment (low/medium/high)."""

def test_key_concept_extraction():
    """Test extraction of planning-specific concepts."""

def test_domain_classification_edge_cases():
    """Test edge cases and ambiguous domain content."""
```

### 2. Integration Tests - Complete Workflows

#### 2.1 Single File Conversion Tests
- **File**: `test_acpbench_single_file_conversion.py`
- **Purpose**: Test complete single file conversion workflows

**Test Cases:**
```python
def test_convert_bool_json_file():
    """Test complete bool.json file conversion."""

def test_convert_mcq_json_file():
    """Test complete mcq.json file conversion."""

def test_convert_gen_json_file():
    """Test complete gen.json file conversion."""

def test_single_file_error_handling():
    """Test error handling during single file conversion."""

def test_single_file_performance_metrics():
    """Test performance tracking for single file conversion."""
```

#### 2.2 Batch Processing Tests
- **File**: `test_acpbench_batch_processing.py`
- **Purpose**: Test multi-file batch processing

**Test Cases:**
```python
def test_batch_convert_all_file_types():
    """Test batch conversion of all 3 file types together."""

def test_batch_processing_progress_tracking():
    """Test progress tracking during batch processing."""

def test_batch_processing_memory_management():
    """Test memory usage during large batch processing."""

def test_batch_processing_partial_failures():
    """Test handling of partial failures in batch mode."""

def test_batch_processing_performance():
    """Test batch processing performance benchmarks."""
```

#### 2.3 PyRIT Format Compliance Tests
- **File**: `test_acpbench_pyrit_compliance.py`
- **Purpose**: Test PyRIT QuestionAnsweringDataset format compliance

**Test Cases:**
```python
def test_pyrit_dataset_structure_compliance():
    """Test generated dataset matches PyRIT structure."""

def test_pyrit_qa_entry_format_compliance():
    """Test QuestionAnsweringEntry format compliance."""

def test_pyrit_metadata_format_compliance():
    """Test metadata structure compliance."""

def test_pyrit_answer_type_compliance():
    """Test answer type compliance (bool, int, str)."""

def test_pyrit_evaluation_workflow_integration():
    """Test integration with PyRIT evaluation workflows."""
```

### 3. Performance Tests

#### 3.1 Performance Benchmarks
- **File**: `test_acpbench_performance.py`
- **Purpose**: Test performance requirements compliance

**Test Cases:**
```python
def test_conversion_time_under_2_minutes():
    """Test complete conversion finishes within 2 minutes."""

def test_memory_usage_under_500mb():
    """Test peak memory usage stays under 500MB."""

def test_throughput_over_100_questions_per_second():
    """Test processing throughput exceeds 100 q/s."""

def test_large_dataset_scalability():
    """Test scalability with large datasets."""

def test_concurrent_processing_performance():
    """Test concurrent processing capabilities."""
```

### 4. Quality Assurance Tests

#### 4.1 Data Integrity Tests
- **File**: `test_acpbench_data_integrity.py`
- **Purpose**: Test data preservation and integrity

**Test Cases:**
```python
def test_context_preservation_100_percent():
    """Test 100% context information preservation."""

def test_planning_metadata_completeness():
    """Test completeness of planning metadata."""

def test_answer_accuracy_over_98_percent():
    """Test answer mapping accuracy >98%."""

def test_domain_classification_over_95_percent():
    """Test domain classification accuracy >95%."""

def test_no_data_loss_during_conversion():
    """Test zero data loss during conversion process."""
```

#### 4.2 Validation Pipeline Tests
- **File**: `test_acpbench_validation.py`
- **Purpose**: Test validation and quality checks

**Test Cases:**
```python
def test_input_validation_pipeline():
    """Test input JSON validation pipeline."""

def test_content_quality_validation():
    """Test planning content quality validation."""

def test_output_format_validation():
    """Test PyRIT format validation."""

def test_metadata_completeness_validation():
    """Test metadata completeness validation."""

def test_conversion_quality_metrics():
    """Test quality metric calculation and reporting."""
```

### 5. Error Handling Tests

#### 5.1 Error Scenario Tests
- **File**: `test_acpbench_error_handling.py`
- **Purpose**: Test error handling and recovery

**Test Cases:**
```python
def test_malformed_json_handling():
    """Test graceful handling of malformed JSON files."""

def test_missing_file_handling():
    """Test handling of missing JSON files."""

def test_insufficient_memory_handling():
    """Test behavior under memory constraints."""

def test_invalid_planning_content_handling():
    """Test handling of invalid planning scenarios."""

def test_partial_conversion_failure_recovery():
    """Test recovery from partial conversion failures."""
```

### 6. API Integration Tests

#### 6.1 Dataset API Integration
- **File**: `test_acpbench_api_integration.py`
- **Purpose**: Test API integration for ACPBench datasets

**Test Cases:**
```python
def test_acpbench_dataset_creation_via_api():
    """Test creating ACPBench datasets via API."""

def test_acpbench_dataset_listing():
    """Test listing ACPBench datasets in API."""

def test_acpbench_dataset_metadata_retrieval():
    """Test retrieving ACPBench metadata via API."""

def test_acpbench_dataset_conversion_endpoint():
    """Test conversion endpoint functionality."""
```

## Test Data Requirements

### Sample Test Data Structure

```
tests/test_data/acpbench/
├── sample_bool.json          # Sample boolean questions
├── sample_mcq.json           # Sample multiple choice questions  
├── sample_gen.json           # Sample generation questions
├── malformed_samples/        # Invalid/malformed test cases
│   ├── invalid_bool.json
│   ├── invalid_mcq.json
│   └── invalid_gen.json
├── large_dataset/            # Performance testing data
│   ├── large_bool.json
│   ├── large_mcq.json
│   └── large_gen.json
└── edge_cases/               # Edge case test data
    ├── edge_bool.json
    ├── edge_mcq.json
    └── edge_gen.json
```

### Sample Test Data Content

**sample_bool.json:**
```json
[
    {
        "id": "logistics_test_1",
        "group": "logistics",
        "context": "In a logistics scenario with 2 trucks, 3 packages, and 4 locations, truck1 is at location A with package1, and truck2 is at location B. Package2 is at location C and package3 is at location D. The goal is to deliver all packages to location A within 3 time units.",
        "question": "Can all packages be delivered to location A within the time constraint?",
        "correct": true
    },
    {
        "id": "blocks_world_test_1", 
        "group": "blocks_world",
        "context": "In a blocks world scenario, there are 3 blocks: A, B, and C. Initially, block A is on the table, block B is on block A, and block C is on the table. The goal is to have block C on top of block B.",
        "question": "Is it possible to achieve the goal state in 2 moves?",
        "correct": false
    }
]
```

**sample_mcq.json:**
```json
[
    {
        "id": "blocks_world_mcq_1",
        "group": "blocks_world", 
        "context": "Given blocks A, B, C where A is on table, B is on A, C is on table. Goal: C on B.",
        "question": "What is the optimal action sequence?",
        "choices": [
            "A) Move C to B directly",
            "B) Move B to table, then C to B", 
            "C) Move A away, then B to table, then C to B",
            "D) The goal cannot be achieved"
        ],
        "answer": "B) Move B to table, then C to B"
    }
]
```

**sample_gen.json:**
```json
[
    {
        "id": "planning_gen_1",
        "group": "general_planning",
        "context": "In a planning scenario with multiple agents, agent1 can move and pick objects, agent2 can only move. There are 3 objects at different locations that need to be collected at a central location.",
        "question": "Generate the complete action sequence for both agents.",
        "expected_response": "Step 1: agent1 moves to object1 location, picks object1. Step 2: agent2 moves to help position. Step 3: agent1 moves to object2, picks object2. Step 4: agent1 moves to central location, drops objects. Step 5: agent1 moves to object3, picks object3. Step 6: agent1 returns to central location, drops object3."
    }
]
```

## Test Execution Requirements

### Pre-Test Setup
1. Create test data files in required structure
2. Set up test database and clean state
3. Configure test environment variables
4. Initialize PyRIT test environment

### Test Execution Order
1. **Unit Tests First** - Component validation
2. **Integration Tests** - Workflow validation  
3. **Performance Tests** - Benchmark validation
4. **Quality Tests** - Data integrity validation
5. **Error Handling** - Edge case validation
6. **API Integration** - End-to-end validation

### Success Criteria
- **Unit Test Coverage**: 100% for all converter components
- **Integration Test Success**: All workflows pass
- **Performance Benchmarks**: Meet all timing and memory requirements
- **Quality Metrics**: Achieve >95% accuracy across all metrics
- **Error Handling**: Graceful handling of all error scenarios
- **API Integration**: Full compatibility with existing API structure

## Test Documentation Requirements

### Test Result Documentation
- **Test Coverage Report**: Line and branch coverage metrics
- **Performance Benchmark Results**: Timing and memory usage data
- **Quality Assurance Metrics**: Accuracy and integrity measurements  
- **Error Scenario Results**: Edge case and error handling verification
- **Integration Test Results**: End-to-end workflow validation

### Continuous Integration Requirements
- All tests must pass before code merge
- Performance benchmarks must be met
- Quality metrics must exceed thresholds
- Security scans must pass without critical issues
- Code review approval required for all test changes

This comprehensive test specification ensures thorough validation of the ACPBench Dataset Converter following TDD methodology with complete coverage of functionality, performance, and quality requirements.