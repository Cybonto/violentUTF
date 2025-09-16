# Issue #124 Test Plan - Phase 2 Integration Testing - Core Conversions

## Test Coverage Requirements

This document outlines the comprehensive test plan for implementing Phase 2 integration testing covering both Garak and OllaGen1 converters following Test-Driven Development (TDD) methodology. All tests must be written BEFORE implementation and must initially fail (RED phase).

## Test Structure Overview

### Integration Test Framework (`test_issue_124_core_conversions.py`)
- **Integration test base class** with service orchestration
- **Performance monitoring utilities** with memory and time metrics  
- **Data validation framework** for integrity checks
- **Test data management** with cleanup and isolation
- **Error simulation framework** for failure scenario testing

### Garak Integration Tests (`test_issue_124_garak_integration.py`)
- **End-to-end conversion pipeline** testing for all 25+ files
- **Attack type classification validation** with >90% accuracy
- **Template variable extraction testing** with completeness checks
- **API integration testing** with converted Garak datasets
- **Streamlit UI integration** with Garak dataset workflows

### OllaGen1 Integration Tests (`test_issue_124_ollegen1_integration.py`)
- **Complete conversion pipeline** testing (25MB → 679,996 Q&A pairs)
- **Multiple choice extraction validation** with >95% accuracy  
- **Scenario metadata preservation** testing with 100% integrity
- **Performance validation** with large dataset handling
- **Memory usage monitoring** with <2GB peak constraint

### API Integration Tests (`test_issue_124_api_integration.py`)
- **Dataset creation endpoints** for both Garak and OllaGen1
- **Dataset listing and preview** functionality validation
- **Configuration and selection** workflow testing
- **Authentication and authorization** with JWT validation
- **Error handling and recovery** scenario testing

### UI Integration Tests (`test_issue_124_streamlit_integration.py`)
- **Dataset selection interface** validation in 2_Configure_Datasets.py
- **Dataset preview functionality** with performance testing
- **Configuration options testing** for both dataset types
- **User workflow validation** with complete scenarios
- **Performance testing** with large dataset UI responsiveness

### PyRIT Workflow Tests (`test_issue_124_pyrit_integration.py`)
- **SeedPrompt execution** with converted Garak datasets
- **Q&A evaluation pipeline** with OllaGen1 datasets
- **Format compliance validation** with PyRIT requirements
- **Orchestrator integration** testing with both dataset types
- **End-to-end evaluation workflows** validation

### Performance & Stress Tests (`test_issue_124_performance.py`)
- **Conversion speed benchmarking** with defined targets
- **Memory usage monitoring** with resource constraints
- **Concurrent operation testing** with multiple conversions
- **API response time validation** under load
- **UI responsiveness testing** with large datasets

### Error Handling Tests (`test_issue_124_error_scenarios.py`)
- **Source file corruption** handling and recovery
- **Resource constraint scenarios** (memory, disk, network)
- **API failure simulation** with network issues
- **Partial conversion recovery** with checkpoint mechanisms
- **Graceful degradation** under system stress

## Core Integration Test Framework

### Base Test Infrastructure
```python
class TestCoreConversions:
    """Base integration test framework for Phase 2 conversions."""
    
    def test_integration_test_framework_setup(self):
        """Validate integration test framework initialization"""
        
    def test_service_orchestration(self):
        """Test coordination of FastAPI, Streamlit, and external services"""
        
    def test_performance_monitoring_framework(self):
        """Validate performance monitoring with memory and time metrics"""
        
    def test_data_validation_utilities(self):
        """Test data integrity validation framework"""
        
    def test_test_data_management(self):
        """Test data preparation, isolation, and cleanup utilities"""
```

### Service Health and Dependencies
```python
    def test_service_health_validation(self):
        """Validate all required services are running and accessible"""
        
    def test_dependency_chain_validation(self):
        """Test dependency resolution for Issues #121, #122, #123"""
        
    def test_database_connectivity(self):
        """Validate database connections for testing infrastructure"""
        
    def test_authentication_framework(self):
        """Test JWT authentication in testing environment"""
```

## Garak Integration Test Coverage

### Complete Pipeline Testing
```python
class TestGarakIntegration:
    """Comprehensive Garak conversion integration tests."""
    
    def test_complete_garak_conversion_pipeline(self):
        """Test end-to-end Garak conversion for all 25+ files"""
        
    def test_attack_type_classification_accuracy(self):
        """Verify attack classification >90% accuracy across all files"""
        
    def test_template_variable_extraction_completeness(self):
        """Test template variable extraction for all attack types"""
        
    def test_harm_categorization_consistency(self):
        """Verify consistent harm category assignment"""
        
    def test_seedprompt_format_compliance(self):
        """Validate 100% PyRIT SeedPrompt format compliance"""
```

### Garak-Specific File Testing
```python
    def test_dan_variants_conversion(self):
        """Test DAN (Do Anything Now) variant conversions"""
        
    def test_rtp_categories_conversion(self):
        """Test RTP (Red Team Prompts) toxicity classification"""
        
    def test_injection_attacks_conversion(self):
        """Test technical jailbreak categorization"""
        
    def test_jailbreak_prompts_conversion(self):
        """Test template variable handling in jailbreak prompts"""
        
    def test_multilingual_prompt_conversion(self):
        """Test non-English prompt handling and metadata"""
```

### API Integration with Garak Datasets
```python
    def test_garak_dataset_creation_via_api(self):
        """Test API endpoint creation of Garak datasets"""
        
    def test_garak_dataset_listing_performance(self):
        """Test dataset listing with multiple Garak collections"""
        
    def test_garak_dataset_preview_functionality(self):
        """Test preview with sample Garak prompts"""
        
    def test_garak_configuration_options(self):
        """Test Garak-specific configuration parameters"""
        
    def test_garak_metadata_accessibility(self):
        """Test metadata query and filtering for Garak datasets"""
```

## OllaGen1 Integration Test Coverage

### Complete Pipeline Testing
```python
class TestOllaGen1Integration:
    """Comprehensive OllaGen1 conversion integration tests."""
    
    def test_complete_ollegen1_conversion_pipeline(self):
        """Test end-to-end conversion: 169,999 scenarios → 679,996 Q&A pairs"""
        
    def test_multiple_choice_extraction_accuracy(self):
        """Verify choice extraction >95% accuracy with validation"""
        
    def test_scenario_metadata_preservation(self):
        """Test 100% preservation of cognitive framework metadata"""
        
    def test_question_type_categorization(self):
        """Verify WCP/WHO/TeamRisk/TargetFactor categorization accuracy"""
        
    def test_performance_with_large_dataset(self):
        """Test conversion performance with complete 25MB dataset"""
```

### Memory and Performance Validation
```python
    def test_memory_usage_monitoring(self):
        """Validate <2GB peak memory during conversion"""
        
    def test_conversion_speed_benchmarks(self):
        """Test <10 minute conversion time for complete dataset"""
        
    def test_concurrent_conversion_handling(self):
        """Test multiple OllaGen1 conversion operations"""
        
    def test_progress_tracking_accuracy(self):
        """Validate real-time progress reporting accuracy"""
        
    def test_checkpoint_recovery_mechanism(self):
        """Test recovery from interrupted conversions"""
```

### API Integration with OllaGen1 Datasets
```python
    def test_ollegen1_dataset_creation_via_api(self):
        """Test API endpoint creation of large OllaGen1 dataset"""
        
    def test_ollegen1_dataset_streaming_response(self):
        """Test streaming response for large dataset operations"""
        
    def test_ollegen1_preview_with_pagination(self):
        """Test paginated preview of 679K Q&A entries"""
        
    def test_ollegen1_search_functionality(self):
        """Test search and filtering within large dataset"""
        
    def test_ollegen1_export_capabilities(self):
        """Test export functionality for large datasets"""
```

## API Integration Test Scenarios

### Dataset Management Endpoints
```python
class TestDatasetAPIIntegration:
    """API integration tests for both dataset types."""
    
    def test_dataset_creation_authentication(self):
        """Test JWT authentication for dataset creation"""
        
    def test_dataset_creation_garak(self):
        """Test creating Garak datasets through API"""
        
    def test_dataset_creation_ollegen1(self):
        """Test creating OllaGen1 dataset through API"""
        
    def test_dataset_listing_performance(self):
        """Test listing response times with both dataset types"""
        
    def test_dataset_preview_functionality(self):
        """Test preview with sample entries from both types"""
```

### Configuration and Management
```python
    def test_dataset_configuration_validation(self):
        """Test configuration parameter validation"""
        
    def test_dataset_update_operations(self):
        """Test dataset modification and versioning"""
        
    def test_dataset_deletion_with_cleanup(self):
        """Test safe dataset deletion with dependency checks"""
        
    def test_dataset_export_import_cycles(self):
        """Test complete export/import cycles for both types"""
        
    def test_dataset_sharing_permissions(self):
        """Test dataset access control and sharing"""
```

### Error Handling and Recovery
```python
    def test_api_malformed_request_handling(self):
        """Test behavior with invalid API requests"""
        
    def test_api_authentication_failure_handling(self):
        """Test JWT expiration and refresh scenarios"""
        
    def test_api_resource_constraint_handling(self):
        """Test API behavior under memory/disk constraints"""
        
    def test_api_network_failure_recovery(self):
        """Test API resilience during connectivity issues"""
        
    def test_api_concurrent_request_handling(self):
        """Test API behavior with multiple simultaneous requests"""
```

## Streamlit UI Integration Testing

### User Workflow Testing
```python
class TestStreamlitIntegration:
    """Comprehensive Streamlit UI integration tests."""
    
    def test_dataset_selection_workflow_garak(self):
        """Test complete Garak dataset selection in 2_Configure_Datasets.py"""
        
    def test_dataset_selection_workflow_ollegen1(self):
        """Test complete OllaGen1 dataset selection workflow"""
        
    def test_dataset_preview_performance_large(self):
        """Test preview loading with 679K entries"""
        
    def test_configuration_parameter_handling(self):
        """Test configuration forms for both dataset types"""
        
    def test_ui_responsiveness_stress_testing(self):
        """Test UI performance under stress conditions"""
```

### UI Component Validation
```python
    def test_dataset_dropdown_population(self):
        """Test dropdown population with converted datasets"""
        
    def test_preview_component_rendering(self):
        """Test sample data display components"""
        
    def test_configuration_form_validation(self):
        """Test input validation and error display"""
        
    def test_progress_indicator_functionality(self):
        """Test conversion progress display accuracy"""
        
    def test_error_message_display(self):
        """Test user-friendly error message presentation"""
```

### UI Performance and Usability
```python
    def test_ui_load_time_benchmarks(self):
        """Test page load times meet performance targets"""
        
    def test_ui_memory_usage_monitoring(self):
        """Test UI memory consumption with large datasets"""
        
    def test_ui_accessibility_compliance(self):
        """Test UI accessibility features and compliance"""
        
    def test_ui_mobile_responsiveness(self):
        """Test UI functionality on mobile devices"""
        
    def test_ui_browser_compatibility(self):
        """Test UI compatibility across different browsers"""
```

## PyRIT Workflow Integration Testing

### Orchestrator Integration
```python
class TestPyRITIntegration:
    """PyRIT workflow integration tests."""
    
    def test_garak_seedprompt_execution(self):
        """Test PyRIT orchestrator with Garak SeedPrompts"""
        
    def test_ollegen1_qa_evaluation(self):
        """Test PyRIT orchestrator with OllaGen1 Q&A datasets"""
        
    def test_evaluation_pipeline_performance(self):
        """Test end-to-end evaluation performance metrics"""
        
    def test_dataset_format_compliance_validation(self):
        """Verify converted datasets meet PyRIT requirements"""
        
    def test_metadata_accessibility_in_evaluations(self):
        """Test metadata usage within PyRIT evaluations"""
```

### Evaluation Workflow Validation
```python
    def test_multi_orchestrator_support(self):
        """Test multiple orchestrator types with converted datasets"""
        
    def test_scorer_integration_validation(self):
        """Test scorer execution with converted datasets"""
        
    def test_target_integration_testing(self):
        """Test target execution with both dataset types"""
        
    def test_evaluation_result_compilation(self):
        """Test comprehensive evaluation result generation"""
        
    def test_evaluation_export_functionality(self):
        """Test evaluation result export and analysis"""
```

## Performance Benchmarks and Testing

### Conversion Performance Targets
```python
class TestPerformanceBenchmarks:
    """Performance validation and benchmarking tests."""
    
    def test_garak_conversion_speed(self):
        """Target: All 25+ files <30 seconds total"""
        
    def test_ollegen1_conversion_speed(self):
        """Target: Complete dataset <10 minutes"""
        
    def test_memory_usage_garak(self):
        """Target: Garak conversion <500MB peak"""
        
    def test_memory_usage_ollegen1(self):
        """Target: OllaGen1 conversion <2GB peak"""
        
    def test_data_integrity_validation(self):
        """Target: >99% data integrity for both types"""
```

### API Performance Validation
```python
    def test_api_dataset_creation_performance(self):
        """Target: Dataset creation <60 seconds"""
        
    def test_api_dataset_listing_performance(self):
        """Target: Dataset listing <2 seconds"""
        
    def test_api_dataset_preview_performance(self):
        """Target: Dataset preview <5 seconds"""
        
    def test_api_concurrent_request_performance(self):
        """Test API performance with multiple simultaneous requests"""
        
    def test_api_large_dataset_handling(self):
        """Test API performance with OllaGen1 679K entries"""
```

### UI Performance Testing
```python
    def test_ui_component_load_times(self):
        """Target: Dataset selection <3 seconds"""
        
    def test_ui_preview_load_times(self):
        """Target: Dataset preview <5 seconds"""
        
    def test_ui_configuration_responsiveness(self):
        """Target: Configuration forms <2 seconds"""
        
    def test_ui_large_dataset_rendering(self):
        """Test UI performance with 679K entry datasets"""
        
    def test_ui_concurrent_user_simulation(self):
        """Test UI performance with multiple simultaneous users"""
```

## Error Scenarios and Recovery Testing

### Critical Error Scenarios
```python
class TestErrorScenarios:
    """Comprehensive error handling and recovery tests."""
    
    def test_source_file_corruption_handling(self):
        """Test behavior with corrupted Garak/OllaGen1 files"""
        
    def test_memory_exhaustion_recovery(self):
        """Test graceful handling of memory constraints"""
        
    def test_disk_space_constraint_handling(self):
        """Test behavior when disk space insufficient"""
        
    def test_network_failure_resilience(self):
        """Test API resilience during connectivity issues"""
        
    def test_partial_conversion_recovery(self):
        """Test recovery from interrupted conversions"""
```

### Recovery Mechanism Validation
```python
    def test_checkpoint_mechanism_functionality(self):
        """Test ability to resume from last successful step"""
        
    def test_error_reporting_accuracy(self):
        """Validate detailed error logging and user notification"""
        
    def test_rollback_capability_validation(self):
        """Test reverting to previous state on failure"""
        
    def test_graceful_degradation_under_stress(self):
        """Test continued operation with partial failures"""
        
    def test_automatic_retry_mechanisms(self):
        """Test automatic retry with exponential backoff"""
```

## Test Data Requirements

### Garak Test Data Structure
- **Complete Collection**: All 25+ Garak files for comprehensive testing
- **Attack Type Coverage**: DAN variants, RTP categories, injection attacks, jailbreaks
- **Edge Cases**: Files with unusual formatting, multilingual content
- **Performance Test Sets**: Subsets for rapid development iteration
- **Validation Sets**: Manually verified samples for accuracy testing

### OllaGen1 Test Data Structure
- **Full Dataset**: Complete 25MB file (169,999 scenarios → 679,996 Q&A)
- **Sample Sets**: Stratified samples for unit testing and development
- **Edge Case Scenarios**: Unusual data formatting, incomplete records
- **Performance Benchmarks**: Measured samples for accuracy validation
- **Streaming Test Data**: Large chunks for streaming response testing

### Expected Test Outputs
```json
{
  "garak_conversion_results": {
    "total_files_processed": 25,
    "total_prompts_converted": 1500,
    "attack_types_identified": ["dan", "rtp", "injection", "jailbreak"],
    "classification_accuracy": 0.92,
    "format_compliance": 1.0
  },
  "ollegen1_conversion_results": {
    "scenarios_processed": 169999,
    "qa_pairs_generated": 679996,
    "choice_extraction_accuracy": 0.97,
    "metadata_preservation": 1.0,
    "format_compliance": 1.0
  }
}
```

## Performance Testing Metrics

### Conversion Performance Benchmarks
| Dataset Type | Target Time | Target Memory | Data Integrity | Format Compliance |
|--------------|-------------|---------------|----------------|-------------------|
| Garak Collection | <30 seconds | <500MB | >99% | 100% |
| OllaGen1 Full | <10 minutes | <2GB | >99% | 100% |

### API Performance Benchmarks
| Operation | Target Time | Target Memory | Success Rate | Concurrent Users |
|-----------|-------------|---------------|--------------|------------------|
| Dataset Creation | <60 seconds | <1GB | >99% | 5 |
| Dataset Listing | <2 seconds | <100MB | 100% | 20 |
| Dataset Preview | <5 seconds | <200MB | >99% | 10 |

### UI Performance Benchmarks  
| Component | Target Load Time | Target Memory | Responsiveness | User Experience |
|-----------|------------------|---------------|----------------|-----------------|
| Dataset Selection | <3 seconds | <300MB | Excellent | Smooth |
| Dataset Preview | <5 seconds | <500MB | Good | Acceptable |
| Configuration Form | <2 seconds | <100MB | Excellent | Smooth |

## Test Execution Strategy

### TDD Protocol Implementation
1. **RED Phase**: Write all failing integration tests
2. **GREEN Phase**: Implement minimum framework to pass tests  
3. **REFACTOR Phase**: Optimize for performance and maintainability
4. **VALIDATION Phase**: Execute complete suite and verify requirements

### Test Execution Order
1. **Base Framework Tests**: Infrastructure and utilities
2. **Individual Converter Tests**: Garak and OllaGen1 separately
3. **API Integration Tests**: Endpoint and workflow testing
4. **UI Integration Tests**: Streamlit interface validation
5. **PyRIT Workflow Tests**: End-to-end evaluation testing
6. **Performance Tests**: Benchmarking and stress testing
7. **Error Scenario Tests**: Failure handling and recovery

### Continuous Integration
- **Pre-commit Hooks**: Run critical tests before commits
- **Pull Request Validation**: Complete test suite execution
- **Performance Regression**: Monitor benchmark degradation
- **Coverage Requirements**: Maintain >95% test coverage

## Success Criteria Validation

### Functional Requirements Checklist
- [ ] All Garak conversion tests passing (25+ files)
- [ ] All OllaGen1 conversion tests passing (679,996 Q&A pairs)  
- [ ] API integration tests passing for both dataset types
- [ ] Streamlit UI workflows verified and responsive
- [ ] PyRIT orchestrator integration confirmed
- [ ] Performance benchmarks met for all operations
- [ ] Error handling validated for identified edge cases
- [ ] Documentation updated with comprehensive test results

### Quality Requirements Checklist
- [ ] >95% test coverage for integration components
- [ ] >90% accuracy for Garak attack classification
- [ ] >95% accuracy for OllaGen1 choice extraction
- [ ] 100% format compliance with PyRIT requirements
- [ ] Performance targets met across all test scenarios
- [ ] Comprehensive error handling coverage validated
- [ ] Memory usage within defined constraints
- [ ] UI responsiveness meeting usability standards

### Documentation Requirements Checklist
- [ ] Test results and validation reports generated
- [ ] Performance benchmark documentation complete
- [ ] Error scenario and recovery documentation thorough
- [ ] User workflow documentation updated
- [ ] API documentation reflects integration capabilities
- [ ] Troubleshooting guides updated with common issues
- [ ] Developer guides updated with testing procedures

## Test Files Implementation Structure

### Core Integration Tests
1. `tests/integration/test_issue_124_core_conversions.py` - Base framework
2. `tests/integration/test_issue_124_garak_integration.py` - Garak tests  
3. `tests/integration/test_issue_124_ollegen1_integration.py` - OllaGen1 tests

### API and UI Tests  
4. `tests/api_tests/test_issue_124_dataset_endpoints.py` - API integration
5. `tests/ui_tests/test_issue_124_streamlit_workflows.py` - UI validation

### Workflow and Performance Tests
6. `tests/integration/test_issue_124_pyrit_integration.py` - PyRIT workflows
7. `tests/performance/test_issue_124_performance.py` - Performance benchmarks
8. `tests/integration/test_issue_124_error_scenarios.py` - Error handling

### Test Data and Utilities
9. `tests/test_data/issue_124/` - Comprehensive test data directory
10. `tests/fixtures/issue_124_fixtures.py` - Shared test fixtures
11. `tests/utils/issue_124_test_utils.py` - Testing utilities

This comprehensive test plan ensures thorough validation of Phase 2 integration testing with complete coverage of both Garak and OllaGen1 converters across all integration points in the ViolentUTF platform.