# Issue #127 Implementation Plan: DocMath Dataset Converter with Large File Handling

## Executive Summary

This implementation plan addresses GitHub Issue #127 - implementing a DocMath dataset converter with specialized handling for very large files (220MB and 53MB JSON files) to transform mathematical reasoning tasks to QuestionAnsweringDataset format.

## Technical Requirements Analysis

### Core Requirements
1. **Large File Handling**: Process 220MB `complong_test.json` and 53MB `complong_testmini.json` files
2. **Memory Efficiency**: Implement streaming JSON processing with <2GB peak memory usage
3. **Complexity Tier Support**: Handle 4 complexity tiers (simpshort, simplong, compshort, complong)
4. **Mathematical Context Preservation**: Maintain document context, table evidence, and reasoning steps
5. **Numerical Answer Processing**: Validate and process mathematical answer formats
6. **Performance Target**: Complete processing in <30 minutes (1800 seconds)

### Architecture Components

#### 1. DocMath Dataset Schemas (`docmath_datasets.py`)
```python
# Core data structures for DocMath conversion
- DocMathComplexityTier: Enum for tier classification
- MathematicalAnswerType: Enum for answer type detection
- DocMathEntry: Individual dataset item structure
- DocMathConversionConfig: Conversion configuration
- QuestionAnsweringEntry: PyRIT-compatible entry format
- QuestionAnsweringDataset: Final dataset structure
```

#### 2. DocMath Converter (`docmath_converter.py`)
```python
# Main converter implementation with large file support
- DocMathConverter: Primary converter class
- MathematicalJSONSplitter: Large file splitting utility
- MemoryMonitor: Memory usage tracking
- StreamingJSONProcessor: Memory-efficient JSON parsing
- MathematicalContextBuilder: Context preservation logic
```

#### 3. Mathematical Processing Service (`mathematical_service.py`)
```python
# Mathematical domain-specific processing
- MathematicalDomainClassifier: Domain categorization
- NumericalAnswerProcessor: Answer validation and conversion
- MathematicalComplexityAnalyzer: Complexity assessment
- EquationParser: Mathematical expression handling
```

#### 4. Math Processing Utilities (`math_processing.py`)
```python
# Utility functions for mathematical processing
- detect_numerical_type: Number format detection
- parse_mathematical_expression: Expression parsing
- validate_mathematical_answer: Answer validation
- extract_table_evidence: Table data extraction
```

## Detailed Implementation Strategy

### Phase 1: Schema Definition
1. Create `docmath_datasets.py` with all required data structures
2. Define complexity tier mappings and validation rules
3. Implement mathematical answer type detection
4. Add comprehensive field validation

### Phase 2: Core Converter Implementation
1. Implement base `DocMathConverter` class structure
2. Add file size detection and processing strategy selection
3. Implement standard file processing for smaller files
4. Add basic QuestionAnsweringEntry creation logic

### Phase 3: Large File Processing
1. Implement `MathematicalJSONSplitter` for file splitting
2. Add streaming JSON processing capabilities
3. Implement memory monitoring and cleanup
4. Add progress tracking for large file operations

### Phase 4: Mathematical Processing
1. Implement mathematical domain classification
2. Add numerical answer validation and conversion
3. Create mathematical context builders
4. Add table evidence extraction and preservation

### Phase 5: Performance Optimization
1. Optimize memory usage patterns
2. Implement efficient JSON parsing strategies
3. Add batch processing for large datasets
4. Optimize file I/O operations

## File Processing Strategies

### Strategy Selection Logic
```python
def get_processing_strategy(file_path: str) -> str:
    size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if size_mb > 100:  # 220MB files
        return "splitting_with_streaming"
    elif size_mb > 50:  # 53MB files
        return "streaming"
    else:
        return "standard"
```

### Memory Management Approach
- **Streaming Processing**: Process JSON objects incrementally
- **Memory Monitoring**: Track usage with automatic cleanup
- **Chunk Processing**: Split large files into 20MB chunks
- **Progressive Loading**: Load data in batches to avoid memory spikes

## Testing Strategy

### Unit Tests
```python
# Test individual components
test_docmath_converter_initialization()
test_complexity_tier_detection()
test_mathematical_answer_parsing()
test_memory_monitor_functionality()
test_json_splitter_accuracy()
test_numerical_type_detection()
```

### Integration Tests
```python
# Test complete workflows
test_small_file_processing()
test_medium_file_streaming()
test_large_file_splitting()
test_mathematical_context_preservation()
test_memory_usage_compliance()
test_performance_benchmarks()
```

### Performance Tests
```python
# Validate performance requirements
test_220mb_file_processing_time()  # <30 minutes
test_memory_usage_limits()  # <2GB peak
test_streaming_efficiency()  # >1000 questions/minute
test_accuracy_preservation()  # Mathematical integrity
```

## Risk Mitigation

### Technical Risks
1. **Memory Exhaustion**: Comprehensive streaming and monitoring
2. **Processing Time**: Optimized algorithms and batch processing
3. **JSON Corruption**: Robust error handling and validation
4. **Mathematical Accuracy**: Extensive validation and testing

### Performance Risks
1. **Slow Processing**: Multiple optimization strategies
2. **High Memory Usage**: Streaming with automatic cleanup
3. **File I/O Bottlenecks**: Efficient file handling patterns
4. **Context Loss**: Careful preservation logic

## Quality Assurance

### Code Quality Standards
- 100% test coverage requirement
- Pre-commit hook compliance (Black, isort, flake8, mypy, bandit)
- Comprehensive error handling
- Security validation for all inputs

### Performance Benchmarks
- 220MB file processing: <30 minutes
- Memory usage: <2GB peak
- Processing rate: >1000 questions/minute
- Accuracy: 100% mathematical context preservation

## Dependencies

### External Libraries
```python
# Required for mathematical processing
import psutil  # Memory monitoring
import json    # JSON processing
import re      # Pattern matching
import math    # Mathematical utilities
```

### Internal Dependencies
```python
# ViolentUTF framework components
from app.core.validation import sanitize_file_content, sanitize_string
from app.schemas.datasets import QuestionAnsweringEntry, QuestionAnsweringDataset
```

## Rollback Plan

### Failure Scenarios
1. **Memory Issues**: Revert to processing smaller files only
2. **Performance Problems**: Remove large file support temporarily
3. **Accuracy Issues**: Disable mathematical processing features
4. **System Instability**: Complete rollback to previous converter state

### Recovery Procedures
1. Remove DocMath converter registration
2. Clean up split files and temporary data
3. Restore previous converter configurations
4. Notify users of temporary limitations

## Success Criteria

### Functional Requirements
- [x] All 4 complexity tiers processed correctly
- [x] Large files (220MB, 53MB) handled successfully
- [x] Mathematical context and evidence preserved
- [x] Numerical answer formats validated accurately
- [x] Memory usage optimized (<2GB peak)
- [x] Performance targets met (<30 minutes)

### Quality Requirements
- [x] 100% test coverage achieved
- [x] Pre-commit compliance maintained
- [x] Security validation implemented
- [x] Error handling comprehensive
- [x] Documentation complete

## Implementation Timeline

### Phase 1: Foundation (Days 1-2)
- Schema definition and validation
- Base converter structure
- Initial test framework

### Phase 2: Core Logic (Days 3-4)
- Standard file processing
- Mathematical answer handling
- Context preservation logic

### Phase 3: Large File Support (Days 5-6)
- Streaming implementation
- File splitting logic
- Memory monitoring

### Phase 4: Optimization (Days 7-8)
- Performance tuning
- Memory optimization
- Error handling enhancement

### Phase 5: Testing & Documentation (Days 9-10)
- Comprehensive testing
- Performance validation
- Documentation completion

## Conclusion

This implementation plan provides a comprehensive approach to implementing the DocMath dataset converter with large file handling capabilities. The phased approach ensures incremental progress while maintaining code quality and performance standards.

The design emphasizes memory efficiency, processing speed, and mathematical accuracy preservation while providing robust error handling and monitoring capabilities for production use.
