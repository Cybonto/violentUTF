# Issue #123 Test Plan - OllaGen1 Converter (QuestionAnsweringDataset)

## Test Coverage Requirements

This document outlines the comprehensive test plan for implementing the OllaGen1 converter following Test-Driven Development (TDD) methodology. All tests must be written BEFORE implementation and must initially fail (RED phase).

## Test Structure

### Unit Tests (`test_issue_123_ollagen1_converter.py`)

#### 1. OllaGen1DatasetConverter Core Tests
- `test_converter_initialization()` - Basic converter initialization
- `test_csv_row_parsing()` - CSV row parsing with 22 columns
- `test_manifest_file_processing()` - Manifest-based split file support
- `test_question_type_identification()` - WCP, WHO, TeamRisk, TargetFactor detection
- `test_metadata_extraction()` - Person profile and scenario metadata extraction
- `test_conversion_error_handling()` - Error recovery and validation

#### 2. Multiple Choice Parser Tests
- `test_multiple_choice_extraction()` - Standard format extraction
- `test_malformed_choice_patterns()` - Non-standard format handling
- `test_answer_index_mapping()` - Answer text to index mapping
- `test_choice_validation()` - Choice completeness validation

#### 3. QuestionAnsweringEntry Generation Tests
- `test_qa_entry_creation()` - Single Q&A entry creation from CSV row
- `test_batch_qa_generation()` - 1 CSV row -> 4 Q&A entries conversion
- `test_metadata_preservation()` - Complete metadata preservation
- `test_pyrit_format_compliance()` - PyRIT format validation

#### 4. Performance and Quality Tests
- `test_conversion_performance()` - Speed benchmarks (<10 minutes for full dataset)
- `test_memory_usage()` - Memory consumption (<2GB peak)
- `test_data_integrity()` - 100% data preservation validation
- `test_accuracy_metrics()` - >95% choice extraction accuracy

### Integration Tests (`test_issue_123_integration.py`)

#### 1. End-to-End Conversion Pipeline
- `test_full_dataset_conversion()` - Complete OllaGen1 dataset processing
- `test_split_file_processing()` - Manifest-based file reconstruction
- `test_batch_processing()` - Large dataset streaming processing
- `test_progress_tracking()` - Real-time progress reporting

#### 2. Service Integration Tests
- `test_api_endpoint_integration()` - FastAPI service integration
- `test_database_persistence()` - Converted dataset storage
- `test_validation_framework()` - Validation service integration
- `test_error_recovery()` - Failure recovery mechanisms

### API Tests (`test_issue_123_api.py`)

#### 1. Converter Service Endpoints
- `test_converter_list_endpoint()` - GET /api/v1/converters (includes OllaGen1)
- `test_converter_info_endpoint()` - GET /api/v1/converters/ollagen1
- `test_conversion_initiate()` - POST /api/v1/converters/ollagen1/convert
- `test_conversion_status()` - GET /api/v1/converters/ollegen1/status/{job_id}
- `test_conversion_results()` - GET /api/v1/converters/ollegen1/results/{job_id}

#### 2. Dataset Management Integration
- `test_converted_dataset_registration()` - Dataset registry integration
- `test_dataset_validation()` - Validation service integration
- `test_dataset_export()` - Export functionality
- `test_dataset_metadata()` - Metadata access and querying

## Test Data Requirements

### Sample OllaGen1 Data Structure
```csv
ID,P1_name,P1_cogpath,P1_profile,P1_risk_score,P1_risk_profile,P2_name,P2_cogpath,P2_profile,P2_risk_score,P2_risk_profile,shared_risk_factor,targetted_factor,combined_risk_score,WCP_Question,WCP_Answer,WHO_Question,WHO_Answer,TeamRisk_Question,TeamRisk_Answer,TargetFactor_Question,TargetFactor_Answer
SC001,Alice,analytical,high-stress,85.5,critical-thinker,Bob,intuitive,collaborative,72.3,team-player,communication-breakdown,decision-making,91.2,"What cognitive path best describes Alice's approach? (a) Analytical systematic (b) Intuitive rapid (c) Collaborative consensus (d) Emotional reactive","(option a) - Analytical systematic","Which person has higher compliance risk? (a) Alice with 85.5 score (b) Bob with 72.3 score (c) Both equal risk (d) Cannot determine","(option a) - Alice with 85.5 score","What is the primary team risk factor? (a) Skill mismatch (b) Communication breakdown (c) Authority conflicts (d) Resource constraints","(option b) - Communication breakdown","What intervention should target decision-making issues? (a) Training programs (b) Process changes (c) Team restructuring (d) Technology solutions","(option b) - Process changes"
```

### Expected QuestionAnsweringEntry Output
```json
[
  {
    "question": "What cognitive path best describes Alice's approach? (a) Analytical systematic (b) Intuitive rapid (c) Collaborative consensus (d) Emotional reactive",
    "answer_type": "int",
    "correct_answer": 0,
    "choices": ["Analytical systematic", "Intuitive rapid", "Collaborative consensus", "Emotional reactive"],
    "metadata": {
      "scenario_id": "SC001",
      "question_type": "WCP",
      "category": "cognitive_assessment",
      "person_1": {"name": "Alice", "cognitive_path": "analytical", "profile": "high-stress", "risk_score": 85.5, "risk_profile": "critical-thinker"},
      "person_2": {"name": "Bob", "cognitive_path": "intuitive", "profile": "collaborative", "risk_score": 72.3, "risk_profile": "team-player"},
      "shared_risk_factor": "communication-breakdown",
      "targeted_factor": "decision-making",
      "combined_risk_score": 91.2,
      "conversion_timestamp": "2025-01-XX",
      "conversion_strategy": "strategy_1_cognitive_assessment"
    }
  }
]
```

## Performance Test Requirements

### Conversion Speed Targets
- **Full Dataset**: 169,999 scenarios in <10 minutes (600 seconds)
- **Throughput**: >300 scenarios per second
- **Memory Usage**: <2GB peak memory consumption
- **Progress Tracking**: Real-time ETA and completion percentage

### Accuracy Requirements
- **Multiple Choice Extraction**: >95% accuracy rate
- **Answer Index Mapping**: >98% correct mapping
- **Data Preservation**: 100% scenario metadata preservation
- **Q&A Count**: Exactly 679,996 entries (4 per scenario)

## Quality Assurance Tests

### Data Integrity Validation
- **Schema Compliance**: All QuestionAnsweringEntry objects meet PyRIT specifications
- **Metadata Completeness**: All required metadata fields present
- **Answer Type Consistency**: All answer_type fields set to "int"
- **Choice Array Validation**: All choices arrays properly formatted

### Edge Case Handling
- **Malformed Multiple Choice**: Non-standard choice formats
- **Missing Data Fields**: Incomplete person profiles or scenario data
- **File Processing Errors**: Corrupted or missing split files
- **Memory Constraints**: Large dataset processing efficiency

## Test Execution Order (TDD Protocol)

1. **RED Phase**: Write all failing tests
2. **GREEN Phase**: Implement minimum code to pass tests
3. **REFACTOR Phase**: Improve code quality while maintaining test passage
4. **VALIDATION Phase**: Run complete test suite and verify requirements

## Test Files to Create

1. `tests/test_issue_123_ollegen1_converter.py` - Unit tests
2. `tests/test_issue_123_integration.py` - Integration tests  
3. `tests/api_tests/test_issue_123_api.py` - API endpoint tests
4. `tests/test_data/ollegen1_sample.csv` - Sample test data
5. `tests/test_data/ollegen1_manifest.json` - Test manifest file

## Success Criteria

All tests must pass with:
- ✅ 100% test coverage for new code
- ✅ Performance benchmarks met
- ✅ Data integrity validation passed
- ✅ PyRIT format compliance verified
- ✅ API integration functional
- ✅ Error handling comprehensive

This test plan ensures comprehensive coverage of the OllaGen1 converter implementation following strict TDD methodology.