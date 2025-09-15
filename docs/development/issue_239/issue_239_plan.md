# Issue #239 Implementation Plan: Dataset Access Regression Fix

## Executive Summary
**Objective**: Restore access to 11 missing datasets (61% loss) by integrating the enhanced NativeDatasetSelector component with the complete API dataset catalog.

**Root Cause**: Enhanced components use hardcoded dataset definitions instead of loading from API, causing loss of 10 PyRIT datasets and 4 ViolentUTF dataset name mismatches.

## Problem Analysis

### Current State
- **API**: Contains all 18 datasets properly defined in `NATIVE_DATASET_TYPES`
- **UI Component**: Only shows 7 hardcoded datasets in `NativeDatasetSelector`
- **Impact**: 61% dataset loss affecting all user segments

### Missing Datasets Analysis

#### 10 Missing PyRIT Datasets (lines 253-334 in API):
1. `aya_redteaming` - Multilingual red-teaming (8 languages)
2. `harmbench` - Standard safety benchmarks
3. `adv_bench` - Adversarial testing
4. `many_shot_jailbreaking` - Advanced jailbreaking
5. `decoding_trust_stereotypes` - Bias evaluation
6. `xstest` - Cross-domain safety testing
7. `pku_safe_rlhf` - Safe RLHF testing
8. `wmdp` - Dangerous content testing
9. `forbidden_questions` - Refusal testing
10. `seclists_bias_testing` - Security-focused bias

#### 4 ViolentUTF Name Mismatches:
1. `legalbench_reasoning` → `legalbench_professional`
2. `docmath_evaluation` → `docmath_mathematical`
3. `graphwalk_reasoning` → `graphwalk_spatial`
4. `acpbench_reasoning` → `acpbench_planning`

## Solution Architecture

### Integration Strategy
1. **API-First Approach**: Load dataset categories dynamically from API
2. **Backward Compatibility**: Maintain existing enhanced UI features
3. **Error Handling**: Graceful fallback to existing datasets if API unavailable

### Implementation Components

#### 1. API Integration Layer (`violentutf/utils/dataset_api_client.py`)
- Create API client for dataset type retrieval
- Handle authentication with stored JWT tokens
- Implement caching for performance
- Error handling and retry logic

#### 2. Enhanced Dataset Selector (`violentutf/components/dataset_selector.py`)
- Replace hardcoded categories with API-driven categories
- Maintain enhanced UI features (tabs, previews, configuration)
- Add fallback mechanism for offline operation
- Preserve category organization and icons

#### 3. Category Mapping System
- Map API datasets to logical UI categories
- Handle both PyRIT and ViolentUTF dataset types
- Support dynamic category creation
- Icon and description management

#### 4. Configuration Integration
- Integrate with existing dataset configuration system
- Support per-dataset configuration options from API
- Validate configurations against API schemas

## Implementation Plan

### Phase 1: API Integration Foundation
**Files**: `violentutf/utils/dataset_api_client.py`

1. Create `DatasetAPIClient` class
2. Implement authentication using existing JWT utilities
3. Add dataset types endpoint integration
4. Implement caching and error handling
5. Add configuration validation

### Phase 2: Dynamic Category System
**Files**: `violentutf/components/dataset_selector.py`

1. Replace hardcoded `self.dataset_categories`
2. Add `_load_categories_from_api()` method
3. Implement category mapping logic
4. Add fallback to existing categories
5. Preserve UI enhancements (icons, descriptions)

### Phase 3: Dataset Name Resolution
**Files**: `violentutf/components/dataset_selector.py`

1. Add name mapping for ViolentUTF datasets
2. Support both old and new names for backward compatibility
3. Update category assignments
4. Fix metadata and configuration mappings

### Phase 4: Enhanced Features Integration
**Files**: `violentutf/components/dataset_selector.py`

1. Integrate API-provided configuration options
2. Update preview functionality
3. Enhance metadata display
4. Maintain selection state management

### Phase 5: Testing & Validation
**Files**: `tests/test_issue_239_dataset_access.py`

1. Test all 18 datasets are accessible
2. Validate category organization
3. Test API integration error handling
4. Verify backward compatibility
5. Performance and caching tests

## Technical Specifications

### API Integration
```python
class DatasetAPIClient:
    def __init__(self, base_url: str, auth_token: str)
    async def get_dataset_types(self) -> List[DatasetType]
    async def get_dataset_categories(self) -> Dict[str, CategoryInfo]
    def _handle_api_error(self, error: Exception) -> None
```

### Category Mapping
```python
CATEGORY_MAPPINGS = {
    "redteaming": {
        "pyrit_datasets": ["aya_redteaming", "harmbench", "adv_bench", ...],
        "violentutf_datasets": ["garak_redteaming"],
        "icon": "🔴",
        "description": "AI Red-Teaming & Security Assessment"
    },
    # ... other categories
}
```

### Name Resolution
```python
DATASET_NAME_MAPPINGS = {
    "legalbench_reasoning": "legalbench_professional",
    "docmath_evaluation": "docmath_mathematical",
    "graphwalk_reasoning": "graphwalk_spatial",
    "acpbench_reasoning": "acpbench_planning"
}
```

## Testing Strategy

### Test Coverage Areas
1. **API Integration Tests**
   - Authentication flow
   - Dataset retrieval
   - Error handling and retries
   - Caching behavior

2. **UI Component Tests**
   - All 18 datasets visible
   - Category organization
   - Selection functionality
   - Configuration interfaces

3. **Integration Tests**
   - End-to-end dataset access
   - API failure fallback
   - Performance under load
   - Cache invalidation

4. **Regression Tests**
   - Existing functionality preserved
   - No breaking changes
   - Session state management
   - Configuration persistence

### Test Data
- Mock API responses with all 18 datasets
- Error scenario simulations
- Performance benchmarks
- Cache validation datasets

## Quality Assurance

### Pre-commit Requirements
- Black formatting (max 88 chars)
- isort import sorting
- Flake8 code style compliance
- mypy type checking
- bandit security analysis
- Comprehensive test coverage

### Performance Targets
- API response time: < 2 seconds
- UI rendering: < 1 second
- Cache hit ratio: > 90%
- Memory usage: < 100MB additional

### Security Considerations
- JWT token handling
- API endpoint validation
- Input sanitization
- Error message security
- Cache security

## Rollback Strategy

### Checkpoint System
1. **Checkpoint 1**: API client implementation
2. **Checkpoint 2**: Basic category integration
3. **Checkpoint 3**: Full dataset integration
4. **Checkpoint 4**: Enhanced features

### Fallback Mechanisms
- Graceful degradation to hardcoded datasets
- API timeout handling
- Offline operation mode
- Error boundary implementation

## Success Criteria

### Functional Requirements
- ✅ All 18 datasets accessible via UI
- ✅ Enhanced UI features preserved
- ✅ Existing configurations work
- ✅ No breaking changes
- ✅ Performance maintained

### Technical Requirements
- ✅ 100% test coverage for new code
- ✅ All pre-commit checks pass
- ✅ API integration robust
- ✅ Error handling comprehensive
- ✅ Documentation complete

### User Experience
- ✅ No regression in functionality
- ✅ Improved dataset discovery
- ✅ Consistent UI behavior
- ✅ Clear error messages
- ✅ Fast response times

## Risk Assessment

### High Risk
- API integration complexity
- Backward compatibility issues
- Performance impact

### Medium Risk
- Category mapping accuracy
- Cache invalidation
- Error handling coverage

### Low Risk
- UI styling changes
- Documentation updates
- Test maintenance

## Timeline

### Development Phase (3-4 hours)
1. **Hour 1**: API client and basic integration
2. **Hour 2**: Category system and name resolution
3. **Hour 3**: Enhanced features integration
4. **Hour 4**: Testing and validation

### Testing Phase (1-2 hours)
1. **30 min**: Unit and integration tests
2. **30 min**: End-to-end testing
3. **30 min**: Performance validation
4. **30 min**: Final quality assurance

## Dependencies

### Internal Dependencies
- Existing JWT authentication system
- Current dataset selector component
- API endpoint availability
- Session state management

### External Dependencies
- FastAPI backend running
- APISIX gateway operational
- Network connectivity
- Database availability

## Monitoring & Metrics

### Key Metrics
- Dataset access success rate
- API response times
- UI render performance
- Error rates
- User adoption

### Monitoring Points
- API endpoint health
- Component render times
- Cache performance
- Error frequency
- User interactions

## Conclusion

This implementation plan provides a comprehensive approach to restore access to all 18 datasets while maintaining enhanced UI features and ensuring robust error handling. The phased approach allows for incremental validation and rollback capabilities.

**Expected Outcome**: Users will have access to all 18 datasets (100% recovery from 61% loss) with improved performance and reliability through API-driven dataset discovery.
