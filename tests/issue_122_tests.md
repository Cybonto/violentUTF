# Issue #122 - OllaGen1 Data Splitter Tests

## Test Plan for OllaGen1 Data Splitter Implementation

This document outlines the comprehensive test strategy for implementing the OllaGen1 Data Splitter following Test-Driven Development (TDD) methodology.

## Test Categories

### 1. Unit Tests
- OllaGen1Splitter initialization and configuration
- CSV structure analysis and validation
- Scenario-aware splitting logic
- Manifest generation with OllaGen1-specific metadata
- Data integrity validation and checksum verification
- Progress tracking functionality

### 2. Integration Tests  
- Complete split/merge cycle with test data
- Integration with base FileSplitter framework
- Manifest-based reconstruction
- Performance benchmarking

### 3. Performance Tests
- Splitting speed benchmarks (<5 minutes for 25MB file)
- Memory usage monitoring (<1GB peak)
- Reconstruction speed validation

### 4. Data Integrity Tests
- Complete preservation of 169,999 scenarios
- Column schema consistency across splits
- Q&A pair count validation (679,996 total)
- Checksum verification for all operations

## Implementation Status

- [ ] Test suite created (RED phase)
- [ ] OllaGen1Splitter implementation (GREEN phase) 
- [ ] Refactoring and optimization (REFACTOR phase)
- [ ] Performance validation
- [ ] Final integration testing

## Expected Test Files

1. `/tests/test_ollegen1_splitter.py` - Main test suite
2. `/tests/fixtures/ollegen1_test_data.csv` - Test data fixture
3. `/tests/performance/test_ollegen1_performance.py` - Performance tests
4. `/tests/integration/test_ollegen1_integration.py` - Integration tests

## Test Execution Commands

```bash
# Run all OllaGen1 tests
pytest tests/test_ollegen1_splitter.py -v

# Run with coverage
pytest tests/test_ollegen1_splitter.py --cov=violentutf_api.fastapi_app.app.core.splitters --cov-report=html

# Run performance tests
pytest tests/performance/test_ollegen1_performance.py -v

# Run integration tests
pytest tests/integration/test_ollegen1_integration.py -v
```

## Test Data Requirements

The test suite uses a scaled-down version of the OllaGen1 dataset structure:
- 1,000 test scenarios (vs 169,999 production)
- All 22 columns preserved
- 4 Q&A pairs per scenario
- UTF-8 encoding
- Approximately 150KB test file size

This allows for comprehensive testing without requiring the full 25MB dataset during development.