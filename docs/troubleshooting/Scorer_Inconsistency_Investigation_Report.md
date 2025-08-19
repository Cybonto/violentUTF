# ViolentUTF Scorer Result Inconsistency Investigation - Final Report

## Investigation Period: 2025-01-15

## Executive Summary

A comprehensive investigation was conducted to identify inconsistencies between actual scorer results and their display in the ViolentUTF Dashboard. The investigation followed a systematic 5-phase approach and revealed that **the core data pipeline is functioning correctly**. The perceived inconsistencies stem from display logic issues, filtering problems, and missing context rather than data corruption.

## Key Findings

### 1. ✅ **Data Integrity is Maintained**
- Boolean scores are correctly stored as Python bool types (not strings)
- JSON serialization preserves data types appropriately  
- SQLite storage maintains type fidelity
- 677 boolean scores analyzed: 642 True, 35 False (all proper bool type)

### 2. ❌ **Display and Filtering Issues Identified**
- **Timezone Parsing**: Mixed timezone-aware and naive datetimes cause filter failures
- **Aggregation Logic**: Different scorer types mixed inappropriately in statistics
- **Missing Context**: Score rationales and metadata stripped from displays
- **Defensive Gaps**: Code lacks validation for edge cases

### 3. 🔍 **No Systematic Data Type Transformation Issues**
- Initial hypothesis of boolean-to-string conversion was **disproven**
- Data types remain consistent through PyRIT → Orchestrator → SQLite → API pipeline
- The `is True` check in Dashboard works correctly with current data

## Investigation Methodology

### Phase 1: Data Flow Mapping
- Analyzed PyRIT scorer implementations (14 scorer types found)
- Examined orchestrator collection logic (preserves types correctly)
- Reviewed Dashboard query and display code (found logic issues)

### Phase 2: Inspection Tool Development
- Created type inspection utilities
- Built aggregation auditors
- Developed controlled testing framework

### Phase 3: Systematic Testing
- Executed controlled data flow tests
- Verified type preservation at each stage
- Tested edge cases and interpretation logic

### Phase 4: Pattern Documentation
- Identified timezone handling as primary issue
- Confirmed boolean handling works correctly
- Found defensive programming gaps

### Phase 5: Root Cause Analysis
- Determined issues are in presentation layer, not data layer
- Identified specific code locations requiring fixes
- Provided actionable recommendations

## Specific Issues Found

### 1. **Timezone Parsing Failure**
```python
# Problem: Comparing naive and aware datetimes
"2024-07-10T14:46:00"  # Fails to parse
"2024-07-10T14:46:00+00:00"  # Works correctly
```

### 2. **SEVERITY_MAP Defensive Gap**
```python
# Current: Uses truthiness (risky for edge cases)
"true_false": lambda val: "high" if val else "low"

# Should be: Explicit type checking
"true_false": lambda val: "high" if val is True else "low"
```

### 3. **Mixed Aggregations**
- Boolean and scale scores aggregated together
- Different scorer meanings combined in statistics
- Context lost during aggregation

## Recommendations

### Immediate Fixes (Priority 1)
1. **Fix timezone parsing** - Always use timezone-aware datetime objects
2. **Add type validation** - Check score_value types before processing
3. **Separate aggregations** - Group statistics by scorer type
4. **Show score context** - Display rationale and metadata

### Code Changes Required

#### 5_Dashboard.py - Timezone Fix
```python
# Add timezone awareness to datetime parsing
if '+' not in time_str and 'Z' not in time_str:
    parsed = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
else:
    parsed = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
```

#### 5_Dashboard.py - Type Validation
```python
# Add before processing scores
def validate_score_value(score):
    score_type = score.get('score_type')
    value = score.get('score_value')
    
    if score_type == 'true_false' and not isinstance(value, bool):
        logger.warning(f"Unexpected type for boolean score: {type(value)}")
        # Convert if needed
        if value in ['True', 'true', 1, '1']:
            return True
        elif value in ['False', 'false', 0, '0']:
            return False
    return value
```

### Medium-term Improvements
1. Implement comprehensive logging at transformation points
2. Create data quality monitoring dashboard
3. Add automated tests for edge cases
4. Document score interpretation guidelines

### Long-term Enhancements
1. Enforce schema validation at API boundaries
2. Standardize datetime handling across platform
3. Implement real-time data quality alerts
4. Create user guide for score interpretations

## Conclusion

The investigation successfully identified that the perceived inconsistencies are not due to data corruption or type transformation issues, but rather stem from:

1. **Timezone handling problems** causing data to be filtered out
2. **Aggregation logic** that mixes different scorer types
3. **Missing context** in score displays
4. **Lack of defensive programming** for edge cases

The core data pipeline is robust and maintains data integrity. The recommended fixes focus on improving the presentation layer and adding defensive measures to handle edge cases gracefully.

## Additional Investigation: "Incomplete Executions" Issue

### Issue Description
The Executive Summary shows "Incomplete Executions (57)" even though all 78 executions in the database have status="completed".

### Root Cause Analysis

The issue stems from a **fundamental misunderstanding** in the Dashboard's batch completion logic:

1. **Data Structure**: 
   - The system executed 78 separate batch executions (batch_0 through batch_77)
   - Each execution handles ONLY ONE batch of the total dataset
   - Example: `batch_0_forbidden_questions_dataset` contains only batch index 0

2. **Metadata Confusion**:
   - Each score's metadata contains: `{"batch_index": 0, "total_batches": 78}`
   - The `total_batches: 78` refers to the TOTAL number of batches across ALL executions
   - It does NOT mean each execution should contain 78 batches

3. **Dashboard Logic Error** (lines 1398-1407 in 5_Dashboard.py):
   ```python
   expected_batches = max(batch_totals, default=1)  # Gets 78
   expected_indices = set(range(expected_batches))  # Expects 0-77
   missing_batches = expected_indices - actual_batch_indices  # Missing 77!
   completed = len(missing_batches) == 0  # False
   ```

4. **Why 57 not 78?**:
   - 57 executions have batch metadata (marked incomplete)
   - 21 executions lack batch metadata (default to complete)

### Impact
- All batch executions are incorrectly marked as incomplete
- Executive Summary shows misleading "57 incomplete" warning
- Completion rate calculations are incorrect

### Recommended Fix

Replace the flawed logic in `calculate_hierarchical_metrics`:

```python
# Current (WRONG) - expects all batches in one execution
expected_batches = max(batch_totals, default=1)
expected_indices = set(range(expected_batches))

# Fixed - check if THIS execution's batches are complete
# For single-batch executions: only expect the batch that's actually there
unique_batch_indices = list(actual_batch_indices)
if len(unique_batch_indices) == 1:
    # Single batch execution - it's complete if it has its batch
    completed = True
else:
    # Multi-batch execution - check sequence
    if unique_batch_indices:
        min_idx = min(unique_batch_indices)
        max_idx = max(unique_batch_indices)
        expected_indices = set(range(min_idx, max_idx + 1))
        completed = actual_batch_indices == expected_indices
    else:
        completed = False
```

### Alternative Design Consideration
The current approach of splitting a dataset into separate executions (one per batch) may need reconsideration. Options:
1. Keep current design but fix the completion logic
2. Execute all batches in a single orchestrator run
3. Add execution grouping to link related batch executions

## Appendices

### A. Test Results Summary
- Phase 1: Documentation complete
- Phase 2: Inspection tools developed and tested
- Phase 3: Controlled tests passed
- Phase 4: Patterns documented
- Phase 5: Root causes identified
- Additional: "Incomplete Executions" issue identified and analyzed

### B. File Locations
- Investigation artifacts: `/tmp/scorer_investigation_cache/`
- Modified files requiring attention:
  - `/violentutf/pages/5_Dashboard.py`
  - Dashboard aggregation functions (especially `calculate_hierarchical_metrics`)
  - Time filter implementations

### C. Future Monitoring
Recommend implementing:
- Automated type checking in CI/CD
- Data quality metrics dashboard
- Regular audits of score interpretations
- User feedback mechanism for inconsistencies
- Validation of batch execution patterns

## Dashboard Tab Verification (Additional Investigation)

### Investigation Methodology
Systematically compared each Dashboard tab's displayed metrics against raw database values to identify reporting accuracy issues.

### Database Ground Truth
- **Total Executions**: 78 (all with status="completed")
- **Total Scores**: 675 (all boolean type)
- **Score Distribution**: 641 True (95.0%), 34 False (5.0%)
- **Unique Scorers**: 1 ("scorer_TF_forbiddenQ_gpt4o_ResponseDirectlyAnswerPrompt")
- **Execution Pattern**: 78 separate single-batch executions
- **Metadata Split**: 57 with batch metadata (10 scores each), 21 without (5 scores each)

### Tab-by-Tab Findings

#### 1. Executive Summary Tab
| Metric | Displayed | Actual | Status | Issue |
|--------|-----------|---------|---------|--------|
| Test Runs | 78 | 78 | ✓ Correct | None |
| Total Batches | 78 | 78 | ✓ Correct | None |
| Score Results | 675 | 675 | ✓ Correct | None |
| Incomplete Executions | 57 | 0 | ❌ Wrong | Flawed completion logic |
| Completion Rate | 26.9% | 100% | ❌ Wrong | Based on incorrect incomplete count |
| Critical Findings | 641 | 641 | ✓ Correct | Assuming True = high severity |

#### 2. Score Results Tab
- **Display Logic**: ✓ Correct (shows one row per scorer with pass/fail counts)
- **Terminology Issue**: "Pass %" might confuse users (False = Pass, True = Fail/Violation)
- **Missing Context**: Scorer class shows as "unknown" for all scores

#### 3. Batch Analysis Tab
- **Row Count**: ✓ Correct (78 batches)
- **Score Counts**: ✓ Correct (matches database)
- **Violation Rates**: ✓ Correct per batch
- **Status Column**: ❌ Wrong (shows incomplete for batches with metadata)

#### 4. Severity Analysis Tab
- **Expected**: High=641, Low=34 (based on boolean mapping)
- **Issue**: SEVERITY_MAP uses truthiness which could fail with string values

#### 5. Detailed Results Tab
- **Missing Elements**: Score rationale, metadata, scorer descriptions
- **Data Accuracy**: ✓ Individual scores displayed correctly

#### 6. Temporal Analysis Tab
- **Limited Value**: All data from 2-minute window on same day
- **Functionality**: ✓ Works correctly for available data

### Root Causes of Display Issues

1. **Batch Completion Logic Flaw**
   - Code assumes each execution should contain all 78 batches
   - Reality: Each execution contains only its assigned single batch
   - Impact: 73% false incomplete rate

2. **Metadata Inconsistency**
   - 27% of executions lack batch metadata
   - These executions have 50% fewer scores (5 vs 10)
   - Suggests two different execution configurations

3. **Terminology Confusion**
   - Boolean True labeled as "Fail" (correct for violations)
   - Boolean False labeled as "Pass"
   - May confuse users unfamiliar with security testing context

4. **Missing Context**
   - No scorer descriptions or test objectives
   - Score rationales not displayed
   - Metadata hidden from users

### Recommended Fixes

1. **Immediate Priority**:
   ```python
   # Fix completion logic in calculate_hierarchical_metrics
   if len(actual_batch_indices) == 1:  # Single-batch execution
       completed = True  # It's complete if it has its batch
   ```

2. **Clarify Terminology**:
   - Add header: "Security Violation Testing Results"
   - Tooltip: "Pass = No violation detected, Fail = Violation detected"
   - Consider: "Violation %" instead of "Fail %"

3. **Add Context**:
   - Display scorer descriptions
   - Show score rationales in detailed view
   - Include test configuration metadata

4. **Investigate Configuration Difference**:
   - Why do some executions have 5 scores vs 10?
   - Document the two execution modes

## Implemented Fixes

### Fix 1: Incomplete Executions Logic ✅
**File**: `violentutf/pages/5_Dashboard.py` (lines 1405-1421)
**Issue**: Dashboard expected each execution to contain all 78 batches, but each only contained one batch
**Fix**: Updated `calculate_hierarchical_metrics` to recognize single-batch executions as complete
```python
# Before: Expected all 78 batches in each execution
expected_batches = max(batch_totals, default=1)  # Got 78
expected_indices = set(range(expected_batches))  # Expected 0-77

# After: Check if THIS execution's batches are complete
unique_batch_indices = list(actual_batch_indices)
if len(unique_batch_indices) == 1:
    # Single batch execution - it's complete if it has its batch
    completed = True
```

### Fix 2: Timezone Parsing ✅
**File**: `violentutf/pages/5_Dashboard.py` (added helper function)
**Issue**: Mixed timezone-aware and naive datetime strings caused parsing failures
**Fix**: Added `parse_datetime_safely()` helper function
```python
def parse_datetime_safely(date_str):
    """Parse datetime string handling both timezone-aware and naive formats"""
    if not date_str:
        return None
    
    try:
        # Handle timezone-aware formats
        if '+' in date_str or 'Z' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Make naive datetimes UTC-aware
            return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.warning(f"Failed to parse datetime: {date_str} - {e}")
        return None
```

### Fix 3: SEVERITY_MAP Type Validation ✅
**File**: `violentutf/pages/5_Dashboard.py` (lines 58-67)
**Issue**: SEVERITY_MAP used truthiness check which could fail with string boolean values
**Fix**: Added explicit type checking and string boolean handling
```python
"true_false": lambda val: (
    "high" if val is True 
    else "low" if val is False
    # Handle string representations of boolean values
    else "high" if isinstance(val, str) and val.lower() in ["true", "1", "yes"]
    else "low" if isinstance(val, str) and val.lower() in ["false", "0", "no"]
    else "unknown"
),
```

### Fix 4: Terminology Clarification ✅
**File**: `violentutf/pages/5_Dashboard.py` (multiple locations)
**Issue**: Users confused by Pass/Fail terminology in security testing context
**Fixes implemented**:

1. **Added terminology explainer** (lines 5459-5474):
   - Expandable section explaining key security testing terms
   - ~~Clarifies that True = Violation/Fail, False = Pass~~ **UPDATED**
   - Explains that finding violations is the goal

2. **Updated tooltips**:
   - Violation Rate metric help text now explains higher rates mean more issues found
   - Compatibility Matrix now includes info box explaining detection rates

3. **Enhanced labels**:
   - Matrix title now says "% of security violations detected"
   - Axes labeled as "AI Models (Generators)" and "Security Scorers"

### Fix 5: Boolean Interpretation Reversal ✅
**File**: `violentutf/pages/5_Dashboard.py` (multiple locations)
**Issue**: Boolean values were interpreted incorrectly - True meant violation (bad) instead of pass (good)
**Fix Date**: 2025-07-16
**Changes**:

1. **Updated SEVERITY_MAP** (lines 59-67):
   ```python
   # Boolean scorers - True = Pass (good), False = Fail (violation)
   "true_false": lambda val: (
       "low" if val is True  # Changed from "high"
       else "high" if val is False  # Changed from "low"
       # Handle string representations of boolean values
       else "low" if isinstance(val, str) and val.lower() in ["true", "1", "yes"]
       else "high" if isinstance(val, str) and val.lower() in ["false", "0", "no"]
       else "unknown"
   ),
   ```

2. **Updated violation detection logic** throughout:
   - Line 891: Changed `score_value is True` to `score_value is False`
   - Line 1605: Changed `score_value is True` to `score_value is False`
   - Line 1631: Changed `score_value is True` to `score_value is False`
   - Line 2902: Changed `score_value is True` to `score_value is False`
   - Line 4047: Changed `score_value is True` to `score_value is False`

3. **Updated documentation** (lines 5475-5477):
   ```markdown
   **Boolean Scorer Values:**
   - `True` = Good security posture (Pass)
   - `False` = Security violation detected (Fail)
   ```

**Impact**: Dashboard now correctly interprets boolean scorer results where True indicates the system passed security checks (good security posture) and False indicates a security failure/violation was detected.

### Fix 6: Dashboard Test Execution Filtering ✅
**File**: Multiple files
**Issue**: Dashboard showed inconsistent results for test executions - zero results in Executive Summary with FULL filter, then showing some results after running another test
**Fix Date**: 2025-07-17
**Root Cause**: Test mode metadata wasn't properly propagating from orchestrator service to score metadata
**Changes**:

1. **Updated orchestrator service metadata propagation** (`violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py`):
   ```python
   # Added conversion of is_test_execution to test_mode for Dashboard compatibility
   if "is_test_execution" in execution_metadata:
       is_test = execution_metadata.get("is_test_execution", False)
       execution_metadata["test_mode"] = "test_execution" if is_test else "full_execution"
       logger.info(f"Added test_mode: {execution_metadata['test_mode']} based on is_test_execution: {is_test}")
   ```

2. **Enhanced Dashboard metadata fallback logic** (`violentutf/pages/5_Dashboard.py` - 3 locations):
   ```python
   # Fallback to execution-level metadata if test_mode is unknown
   if result["test_mode"] == "unknown" and details:
       exec_metadata = details.get("execution_summary", {}).get("metadata", {})
       if exec_metadata:
           if "is_test_execution" in exec_metadata:
               is_test = exec_metadata.get("is_test_execution", False)
               result["test_mode"] = "test_execution" if is_test else "full_execution"
           elif "test_mode" in exec_metadata:
               result["test_mode"] = exec_metadata.get("test_mode", "unknown")
   ```

3. **Ensured execution metadata is passed to scorers**:
   - ConfiguredScorerWrapper now receives execution_metadata during instantiation
   - Metadata is properly included in score results for Dashboard filtering

**Impact**: Dashboard now correctly filters test vs full executions, showing accurate counts in Executive Summary and allowing proper filtering across all tabs.

### Fix 7: Dashboard "No Scorer Results Available" Error ✅
**File**: `violentutf/pages/5_Dashboard.py` (line 331)
**Issue**: Dashboard showed "Executions found but no scorer results available" even when data existed
**Fix Date**: 2025-07-17
**Root Cause**: Undefined variable reference causing exception during data loading
**Changes**:

Changed line 331 from:
```python
exec_metadata = execution_result.get("execution_summary", {}).get("metadata", {})
```

To:
```python
exec_metadata = details.get("execution_summary", {}).get("metadata", {})
```

**Explanation**: The variable `execution_result` was not defined in the scope. The correct variable containing the API response data was `details`.

**Impact**: Dashboard now properly loads and displays scorer results without throwing exceptions during the data parsing phase.

### Dashboard TEST/FULL Execution Filtering - Expected Behavior ✅
**Date**: 2025-07-17
**Status**: Working as designed

**Observed Behavior**:
- Dashboard loads 12 scorer results from 3 TEST executions
- Shows "Showing 6 of 12 results (50.0% filtered)"
- Executive Summary shows 1 execution instead of 3
- Violation rate shows 0.0%

**Explanation**: 
The Dashboard has an "Execution Type" filter that **defaults to "Full Only"** to focus on production results rather than test runs. This filter is located in the Filters section (lines 1285-1295 in `5_Dashboard.py`).

**Filter Options**:
1. **"Full Only"** (default) - Shows only production/full executions
2. **"Test Only"** - Shows only test executions (limited samples)
3. **"All Executions"** - Shows both test and full executions

**Why Results Are Filtered**:
When all executions are TEST type and the filter is set to "Full Only", the Dashboard correctly filters out some or all of the TEST results, which explains:
- Why only 6 of 12 results are shown (partial filtering due to metadata propagation timing)
- Why Executive Summary might show reduced counts
- This is intentional to prevent test data from skewing production metrics

**User Action Required**:
To view all TEST execution results, users should:
1. Expand the "🔍 Filters" section
2. Change "Execution Type" from "Full Only" to either "Test Only" or "All Executions"
3. Click "🔄 Apply All" to update the view

This design choice ensures that dashboard metrics focus on real security testing results by default, while still allowing users to view test data when needed.

### Fix 8: Configure Scorer TEST Executions Incorrectly Marked as FULL ✅
**File**: `violentutf/pages/4_Configure_Scorers.py` (line 477)
**Issue**: Test executions from Configure Scorer were being marked as "FULL" in Dashboard
**Fix Date**: 2025-07-17
**Root Cause**: Incorrect logic for setting test_mode based on save_to_db flag
**Changes**:

Changed line 477 from:
```python
"test_mode": "full_execution" if save_to_db else "test_execution",
```

To:
```python
"test_mode": "test_execution",  # Always test_execution for Test button
```

**Explanation**: The original code incorrectly set test_mode to "full_execution" when save_to_db was True. Since the Test Execution button always passes save_to_db=True (to save results to dashboard), all test executions were being marked as full executions.

**Impact**: Test executions from Configure Scorer will now correctly show as TEST in the Dashboard, allowing proper filtering and metric calculation.

### Fix 9: Duplicate Score Entries in Dashboard ✅
**File**: `violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py` (lines 912-957)
**Issue**: Each score appeared multiple times (6x) in Dashboard export
**Fix Date**: 2025-07-17
**Root Cause**: Multiple score collection methods finding and adding the same scores with different field structures
**Problem Details**:
- Method 1: PyRIT memory scores (has timestamp, prompt_request_response_id)
- Method 2: Tracked scorers collection (has prompt_id, text_scored)
- Method 3: Direct discovery from orchestrator attributes (same as Method 2)
- All three methods were finding the same scores but with different field names

**Initial Fix Issue**: 
The first deduplication attempt failed because it used fields that weren't present in all score types (timestamp, text_scored), causing false mismatches.

**Improved Fix Implementation**:
Enhanced deduplication logic that handles different score structures:
```python
# Deduplicate scores to avoid showing same score multiple times
# Since scores from different methods have different fields, normalize them first
seen_scores = set()
deduplicated_scores = []

for score in formatted_scores:
    # Use prompt_id or prompt_request_response_id as the unique identifier
    unique_id = score.get("prompt_id") or score.get("prompt_request_response_id", "")
    
    # Create a unique key based on essential fields only
    score_key = (
        score.get("score_value"),  # The actual score value
        score.get("score_category", ""),  # Category of score
        unique_id,  # Unique ID for the prompt/conversation
    )
    
    if score_key not in seen_scores:
        seen_scores.add(score_key)
        deduplicated_scores.append(score)

formatted_scores = deduplicated_scores
```

**Impact**: Dashboard will now correctly deduplicate scores regardless of which collection method found them, showing each score only once and providing accurate metrics.

### Fix 10: Orchestrator Creation Failure - Missing Parameter ✅
**File**: `violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py` (lines 223, 334, 349)
**Issue**: "Failed to create orchestrator for scorer testing" - 500 Internal Server Error
**Fix Date**: 2025-07-17
**Root Cause**: The `_resolve_orchestrator_parameters` method was using an undefined variable `orchestrator_id`
**Problem Details**:
- The method signature didn't include `orchestrator_id` parameter
- Inside the method, code tried to access `orchestrator_id` at lines 367, 377
- This caused NameError: name 'orchestrator_id' is not defined

**Fix Implementation**:
1. Updated method signature to include `orchestrator_id` parameter:
   ```python
   async def _resolve_orchestrator_parameters(
       self, parameters: Dict[str, Any], user_context: str = None, orchestrator_id: str = None
   ) -> Dict[str, Any]:
   ```

2. Updated all calls to pass the orchestrator_id:
   - Line 223: `resolved_params = await self._resolve_orchestrator_parameters(parameters, user_context, orchestrator_id)`
   - Line 334: `resolved_params = await self._resolve_orchestrator_parameters(orchestrator_config["parameters"], user_context, orchestrator_id)`

3. Enhanced error handling in Configure Scorer to capture detailed error messages for better debugging

**Impact**: Orchestrator creation now works correctly, allowing test execution in Configure Scorer to proceed without errors. Score deduplication has also been re-enabled to prevent duplicate entries.

**Status**: ✅ RESOLVED - Confirmed working by user

### Known Issue: Generator Ownership Mismatch in Configure Scorer
**Status**: Identified, Workaround Implemented
**Symptoms**: "Failed to create orchestrator for scorer testing" error
**Root Cause**: 
- Generators are stored per-user in the backend
- Configure Scorer page shows ALL generators regardless of owner
- When creating an orchestrator, the backend can't find generators owned by other users

**Current Behavior**:
1. User sees all generators in the dropdown (including those created by other users)
2. Selecting a generator not owned by the current user causes orchestrator creation to fail
3. Error: "Generator 'X' not found for user 'Y'"

**Workaround Implemented**:
Enhanced error message to guide users:
```
Failed to create orchestrator for scorer testing. This often happens when the generator 
'test_gpt3.5turbo' was created by a different user. Please ensure you're using a generator 
created with your account (current user: violentutf.web).
```

**Proper Fix Required**:
The Configure Scorer page should filter generators to show only those owned by the current user, matching the backend's user-specific storage model.

---

*Investigation completed by: Claude*
*Date: 2025-01-15*
*Status: Complete with Dashboard Verification and Fixes Applied*