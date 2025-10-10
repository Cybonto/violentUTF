# Issue #128 Test Documentation: GraphWalk Dataset Converter (480MB File Handling)

## Test Strategy Overview

This document outlines the comprehensive test strategy for implementing the GraphWalk Dataset Converter with massive 480MB file handling capabilities, following strict Test-Driven Development (TDD) methodology.

## Test Categories

### 1. Schema Validation Tests (`TestGraphWalkSchemas`)
**Purpose**: Validate GraphWalk-specific data schemas and structures
- `test_graph_structure_info_schema()`: Graph structure information validation
- `test_chunk_info_schema()`: File chunk information for massive file splitting
- `test_question_answering_entry_with_graph_metadata()`: GraphWalk metadata integration

### 2. Core Converter Tests (`TestGraphWalkConverter`)
**Purpose**: Test GraphWalk converter initialization and core functionality
- `test_graphwalk_converter_initialization()`: Proper component initialization
- `test_memory_monitor_advanced_functionality()`: Advanced memory management
- `test_massive_json_splitter_initialization()`: Massive file splitter setup

### 3. Massive File Processing Tests (`TestMassiveFileProcessing`)
**Purpose**: Validate 480MB file processing capabilities
- `test_file_analysis_for_massive_files()`: File size detection and strategy selection
- `test_processing_strategy_selection_for_massive_files()`: Strategy routing for large files
- `test_massive_json_splitting_with_graph_preservation()`: Graph integrity during splitting
- `test_memory_monitoring_during_massive_processing()`: Memory management under load

### 4. Graph Structure Processing Tests (`TestGraphStructureProcessing`)
**Purpose**: Test graph analysis and spatial reasoning generation
- `test_graph_structure_extraction()`: Graph metadata extraction
- `test_spatial_reasoning_question_generation()`: Question-answer generation
- `test_graph_type_classification()`: Graph type identification
- `test_path_complexity_assessment()`: Complexity analysis for spatial reasoning

### 5. Memory Management Tests (`TestMemoryManagement`)
**Purpose**: Validate memory monitoring and cleanup mechanisms
- `test_memory_threshold_detection()`: Memory threshold monitoring
- `test_progressive_garbage_collection()`: Cleanup mechanism validation
- `test_memory_monitoring_context_manager()`: Context-aware memory management

### 6. Error Handling Tests (`TestErrorHandlingAndRecovery`)
**Purpose**: Test error recovery and checkpoint functionality
- `test_checkpoint_manager_functionality()`: Save/load/clear checkpoint operations
- `test_error_recovery_from_processing_interruption()`: Recovery from failures
- `test_memory_exhaustion_handling()`: Memory pressure response

### 7. Performance Tests (`TestPerformanceRequirements`)
**Purpose**: Validate performance benchmarks and requirements
- `test_processing_speed_benchmark()`: >3000 objects/minute throughput
- `test_memory_usage_stays_under_limit()`: <2GB memory constraint
- `test_chunk_processing_time_limits()`: Individual chunk processing times

### 8. Integration Tests (`TestIntegrationRequirements`)
**Purpose**: Test integration with existing ViolentUTF system
- `test_graphwalk_dataset_creation()`: QuestionAnsweringDataset generation
- `test_api_endpoint_integration_requirements()`: API compatibility

## Performance Test Requirements

### Memory Constraints
- **Maximum Memory Usage**: 2GB throughout processing
- **Memory Monitoring**: Real-time tracking with automatic cleanup
- **Progressive GC**: Triggered cleanup at 80% and 90% thresholds

### Processing Speed Targets
- **Throughput**: >3000 objects per minute for optimal performance
- **Total Processing Time**: <30 minutes for 480MB file
- **Chunk Processing**: <2 minutes per 15MB chunk

### File Handling Requirements
- **Massive File Support**: Handle 480MB train.json files
- **Splitting Strategy**: 15MB chunks with object-boundary preservation
- **Graph Integrity**: 100% structure preservation across splits

## Test Data Requirements

### Synthetic Test Data
All tests use synthetic GraphWalk-compatible data for security compliance:

```python
SAMPLE_GRAPHWALK_OBJECT = {
    "id": "test_graph_123",
    "graph": {
        "nodes": [
            {"id": "start", "pos": [0, 0], "properties": {"type": "start"}},
            {"id": "goal", "pos": [10, 6], "properties": {"type": "goal"}}
        ],
        "edges": [
            {"from": "start", "to": "goal", "weight": 11.66}
        ]
    },
    "question": "What is the shortest path from start to goal?",
    "answer": ["start", "goal"],
    "spatial_context": "2D Euclidean navigation"
}
```

### Test File Sizes
- **Small Files**: <1MB for unit testing
- **Medium Files**: 50MB for integration testing  
- **Large Files**: 480MB simulation for performance testing

## Memory Testing Strategy

### Memory Monitoring Approach
```python
class AdvancedMemoryMonitor:
    - max_usage_gb: 2.0 (hard limit)
    - warning_threshold: 1.6GB (80%)
    - cleanup_threshold: 1.8GB (90%)
    - Progressive cleanup with context management
```

### Memory Pressure Simulation
- Create large data structures to test cleanup
- Validate garbage collection effectiveness
- Test memory exhaustion recovery

## Error Handling Test Scenarios

### Processing Interruption Recovery
1. **Corrupt JSON Lines**: Skip invalid entries, continue processing
2. **Disk Space Exhaustion**: Handle gracefully with cleanup
3. **Memory Pressure**: Automatic cleanup and recovery
4. **Network Interruption**: Checkpoint-based resume capability

### Checkpoint System Testing
- Save processing state every 5000 objects
- Resume from last successful checkpoint
- Clear checkpoints after successful completion

## Graph Integrity Validation

### Structure Preservation Tests
- Node count consistency across splits
- Edge relationships maintained
- Spatial coordinate preservation
- Graph properties validation

### Spatial Reasoning Tests
- Question generation from graph structure
- Path traversal analysis
- Navigation context preservation
- Complexity assessment accuracy

## Integration Testing Requirements

### API Compatibility
The converter must integrate with existing endpoints:
- `POST /api/v1/datasets/convert/graphwalk`
- `GET /api/v1/datasets/graphwalk/status`
- `GET /api/v1/datasets/graphwalk/metrics`

### Schema Compatibility
Must work with existing PyRIT schema patterns:
- `QuestionAnsweringDataset` format
- `QuestionAnsweringEntry` structure  
- Metadata standardization

## Test Execution Strategy

### Phase 1: Red Phase (Failing Tests)
1. Run all tests - should fail initially
2. Validate test coverage of requirements
3. Confirm test infrastructure setup

### Phase 2: Green Phase (Implementation)
1. Implement minimal code to pass tests
2. Focus on core functionality first
3. Iterative development with test validation

### Phase 3: Refactor Phase (Optimization)
1. Optimize for performance requirements
2. Improve memory management
3. Enhanced error handling

## Success Criteria

### Functional Requirements ✅
- [ ] All unit tests pass (100% success rate)
- [ ] Integration tests pass with existing system
- [ ] Memory constraints maintained (<2GB)
- [ ] Performance benchmarks met (>3000 obj/min)
- [ ] Error recovery scenarios validated

### Quality Requirements ✅
- [ ] >99% object processing success rate
- [ ] Graph integrity preservation across all operations
- [ ] Comprehensive error handling coverage
- [ ] Memory usage profiling validates constraints
- [ ] Processing time within 30-minute limit

### Security Requirements ✅
- [ ] All test data is synthetic (no real datasets)
- [ ] No credential or sensitive data exposure
- [ ] Proper input validation and sanitization
- [ ] Error messages don't leak internal details

## Test Environment Setup

### Dependencies
- `pytest`: Test framework
- `psutil`: Memory monitoring
- `tempfile`: Temporary test files
- `unittest.mock`: Mocking for isolation

### Test Data Management
- Automatic cleanup of temporary files
- Memory-efficient test data generation
- Proper resource management in fixtures

### CI/CD Integration
Tests designed for automated pipeline execution:
- Fast unit tests (<5 minutes total)
- Isolated integration tests
- Performance benchmarks with thresholds
- Memory usage validation

---

**Test Priority**: Critical (TDD Phase 1)  
**Coverage Target**: >95% code coverage  
**Execution Time**: <10 minutes for full suite  
**Memory Requirements**: <1GB for test execution  

This test strategy ensures comprehensive validation of the GraphWalk converter implementation while maintaining the strict requirements for 480MB file processing with memory constraints and performance targets.