# Issue #126 Test Plan - LegalBench Dataset Converter (TSV to QuestionAnsweringDataset)

## Test Coverage Requirements

This document outlines the comprehensive test plan for implementing the LegalBench converter following Test-Driven Development (TDD) methodology. All tests must be written BEFORE implementation and must initially fail (RED phase).

## Test Structure

### Unit Tests (`test_issue_126_legalbench_converter.py`)

#### 1. LegalBenchConverter Core Tests
- `test_converter_initialization()` - Basic converter initialization with legal classification config
- `test_tsv_row_parsing()` - TSV row parsing with legal domain field detection
- `test_directory_traversal()` - 166 legal task directory discovery and processing
- `test_legal_category_classification()` - Legal domain classification (contract, regulatory, judicial, etc.)
- `test_professional_validation_metadata()` - Professional validation metadata preservation
- `test_conversion_error_handling()` - Error recovery for malformed directories and TSV files

#### 2. Legal Domain Classification Tests
- `test_contract_category_detection()` - Contract law task identification
- `test_regulatory_category_detection()` - Regulatory compliance task identification
- `test_judicial_category_detection()` - Judicial reasoning task identification
- `test_civil_category_detection()` - Civil law task identification
- `test_criminal_category_detection()` - Criminal law task identification
- `test_constitutional_category_detection()` - Constitutional law task identification
- `test_corporate_category_detection()` - Corporate law task identification
- `test_ip_category_detection()` - Intellectual property law task identification
- `test_specialization_mapping()` - Legal specialization sub-categorization

#### 3. TSV Processing Tests
- `test_tsv_format_detection()` - Auto-detect TSV delimiter and field structure
- `test_train_test_split_parsing()` - Separate train.tsv and test.tsv processing
- `test_flexible_field_mapping()` - Varying TSV column structures handling
- `test_legal_question_format_detection()` - Legal reasoning question type identification
- `test_answer_format_handling()` - Multiple choice vs. open-ended answer processing

#### 4. QuestionAnsweringEntry Generation Tests
- `test_legal_qa_entry_creation()` - Legal Q&A entry creation with domain metadata
- `test_legal_context_preservation()` - Legal case/statute context preservation
- `test_train_test_split_metadata()` - Train/test split information preservation
- `test_professional_validation_tags()` - Professional validation metadata inclusion
- `test_legal_complexity_scoring()` - Legal complexity assessment integration

#### 5. Performance and Quality Tests
- `test_directory_processing_performance()` - Speed benchmarks (<10 minutes for 166 directories)
- `test_memory_usage_scaling()` - Memory consumption during large-scale processing
- `test_batch_processing_efficiency()` - Parallel directory processing where safe
- `test_legal_classification_accuracy()` - >90% legal category classification accuracy
- `test_split_preservation_integrity()` - 100% train/test split preservation

### Integration Tests (`test_issue_126_integration.py`)

#### 1. End-to-End Conversion Pipeline
- `test_full_legalbench_conversion()` - Complete LegalBench dataset processing across all directories
- `test_multi_directory_processing()` - Batch processing of 166 task directories
- `test_legal_domain_aggregation()` - Legal category aggregation and reporting
- `test_progress_tracking_directories()` - Real-time progress across directory processing

#### 2. Legal Classification Integration
- `test_legal_categorization_service()` - Legal classification service integration
- `test_professional_validation_service()` - Professional validation metadata service
- `test_legal_complexity_assessment()` - Legal complexity scoring integration
- `test_specialization_mapping_service()` - Legal specialization mapping service

#### 3. Data Quality and Validation Tests
- `test_legal_question_format_validation()` - Legal reasoning question format compliance
- `test_answer_type_validation()` - Answer format validation for legal questions
- `test_metadata_completeness()` - Professional validation metadata completeness
- `test_legal_domain_accuracy()` - Manual verification of legal domain classification

#### 4. Service Integration Tests
- `test_api_endpoint_integration()` - FastAPI service integration for LegalBench
- `test_database_persistence_legal()` - Legal dataset storage with domain metadata
- `test_validation_framework_legal()` - Legal domain validation framework integration
- `test_error_recovery_directories()` - Directory-level failure recovery mechanisms

### Performance Tests (`test_issue_126_performance.py`)

#### 1. Directory Processing Performance
- `test_single_directory_processing_time()` - Individual directory processing speed
- `test_batch_directory_processing()` - 166 directory batch processing performance
- `test_memory_scaling_directories()` - Memory usage across increasing directory count
- `test_parallel_processing_safety()` - Safe parallel directory processing validation

#### 2. Legal Classification Performance
- `test_classification_speed()` - Legal category classification speed per task
- `test_specialization_mapping_performance()` - Specialization detection performance
- `test_professional_validation_processing()` - Professional validation metadata processing speed
- `test_bulk_classification_efficiency()` - Bulk legal domain classification performance

#### 3. Data Quality Metrics
- `test_tsv_parsing_accuracy()` - TSV parsing accuracy across varying formats
- `test_legal_content_preservation()` - Legal content and context preservation rates
- `test_split_preservation_accuracy()` - Train/test split preservation accuracy
- `test_professional_metadata_completeness()` - Professional validation metadata completeness rates

### Manual Validation Tests

#### 1. Legal Domain Accuracy Validation
- Sample manual review of 50 legal tasks for correct category assignment
- Expert validation of legal specialization mappings
- Professional validation metadata accuracy verification
- Legal complexity scoring accuracy assessment

#### 2. Content Quality Validation
- Legal reasoning question format correctness review
- Legal context and case reference preservation verification
- Answer format appropriateness for legal domain questions
- Professional validation methodology accuracy verification

## Test Data Requirements

### Mock LegalBench Directory Structure
```
test_legalbench/
├── contract_analysis_basic/
│   ├── train.tsv
│   └── test.tsv
├── regulatory_compliance_financial/
│   ├── train.tsv
│   └── test.tsv
├── judicial_reasoning_civil/
│   ├── train.tsv
│   └── test.tsv
├── criminal_procedure_evidence/
│   ├── train.tsv
│   └── test.tsv
└── constitutional_rights_analysis/
    ├── train.tsv
    └── test.tsv
```

### Sample TSV Content Formats
```python
# Contract analysis TSV format
SAMPLE_CONTRACT_TSV = '''
text	question	answer	label	case_reference
"The agreement states that Party A shall deliver goods within 30 days of signed contract..."	"What is the delivery timeline for Party A?"	"30 days"	"delivery_obligation"	"Commercial_Contract_001"
'''

# Regulatory compliance TSV format
SAMPLE_REGULATORY_TSV = '''
regulation_text	scenario	question	answer	explanation	regulation_reference
"Section 12.3 of the CFR requires quarterly reporting..."	"Company X files reports monthly..."	"Is this compliant?"	"Yes"	"Monthly exceeds quarterly requirements"	"CFR_12.3"
'''

# Judicial reasoning TSV format
SAMPLE_JUDICIAL_TSV = '''
case_facts	legal_question	answer	reasoning	precedent_reference
"Plaintiff sued for breach of contract claiming..."	"What is the likely outcome?"	"Defendant liable"	"Clear breach with damages..."	"Smith_v_Jones_2020"
'''
```

### Legal Classification Test Data
```python
LEGAL_CATEGORY_TEST_CASES = {
    "contract": ["cuad_", "contract_", "agreement_", "lease_", "nda_"],
    "regulatory": ["regulatory_", "compliance_", "cfr_", "regulation_"],
    "judicial": ["judicial_", "court_", "decision_", "opinion_", "ruling_"],
    "civil": ["civil_", "tort_", "liability_", "damages_", "negligence_"],
    "criminal": ["criminal_", "penal_", "prosecution_", "defense_", "evidence_"],
    "constitutional": ["constitutional_", "rights_", "amendment_", "due_process_"],
    "corporate": ["corporate_", "business_", "entity_", "governance_", "securities_"],
    "intellectual_property": ["ip_", "patent_", "trademark_", "copyright_", "trade_secret_"]
}
```

## Success Criteria

### Functional Requirements
- ✅ All 166 directories processed successfully (>95% success rate)
- ✅ Legal domain categorization working accurately (>90% accuracy)
- ✅ Train/test splits preserved correctly (100% preservation)
- ✅ Professional validation metadata preserved (100% coverage)
- ✅ Legal reasoning task types properly categorized
- ✅ TSV parsing handles varying formats correctly

### Performance Requirements
- ✅ Complete processing of 166 directories in <10 minutes
- ✅ Peak memory usage <1GB during processing
- ✅ Individual directory processing <5 seconds average
- ✅ Legal classification processing <1 second per task

### Quality Requirements
- ✅ 100% test coverage for all converter components
- ✅ All tests pass consistently
- ✅ Pre-commit hooks pass (black, isort, flake8, mypy, bandit)
- ✅ No security vulnerabilities (bandit scan clean)
- ✅ Professional validation metadata 100% complete

### Integration Requirements
- ✅ FastAPI service integration working
- ✅ Database persistence with legal metadata
- ✅ Validation framework integration
- ✅ Error recovery and logging functional

## Implementation Notes

### TDD Protocol
1. **RED Phase**: Write failing tests first, verify they fail
2. **GREEN Phase**: Implement minimum code to make tests pass  
3. **REFACTOR Phase**: Improve code quality while maintaining passing tests

### Test Execution Order
1. Unit tests for core converter functionality
2. Legal classification and domain mapping tests
3. TSV processing and QuestionAnsweringEntry generation tests
4. Integration tests for full pipeline
5. Performance tests for scalability validation
6. Manual validation for accuracy verification

### Coverage Requirements
- 100% line coverage for all new code
- 100% branch coverage for critical paths
- Edge case coverage for error handling
- Performance regression testing