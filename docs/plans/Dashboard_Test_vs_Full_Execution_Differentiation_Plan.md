# Dashboard Test vs Full Execution Differentiation Plan

## Executive Summary

The Dashboard currently cannot visually distinguish between test executions and full executions from Configure Scorer, despite the underlying data infrastructure already supporting this differentiation. This document analyzes the current state and proposes multiple implementation options to improve the situation.

## Current State Analysis

### Data Infrastructure (Already in Place)

1. **Configure Scorer Implementation**
   - Test executions: Use prefix `"test_"` in execution names
   - Full executions: Use prefix `"full_exec_"` in execution names
   - Both types save `test_mode` in metadata: `"test_execution"` or `"full_execution"`
   - Full executions include additional tags: `["full_execution", "batch_processing"]`

2. **Metadata Storage**
   ```python
   "metadata": {
       "test_mode": "full_execution" | "test_execution",
       "execution_timestamp": "ISO timestamp",
       "batch_index": 1,  # Only for full executions
       "total_batches": 5,  # Only for full executions
       # ... other fields
   }
   ```

3. **Dashboard Data Processing**
   - Dashboard extracts `test_mode` from score metadata
   - The field is available but not currently displayed or used for filtering

### Gap Analysis

The Dashboard lacks:
- Visual indicators for execution type
- Filter options to show only test or full executions
- Separate statistics for test vs full executions
- Clear labeling in execution lists and result tables

## Proposed Implementation Options

### Option 1: Minimal Visual Indicators (Quick Win)

**Effort**: Low (1-2 hours)
**Impact**: Medium

Add visual badges/labels to existing displays:

1. **Execution Filter Dropdown**
   - Append `[TEST]` or `[FULL]` to execution names
   - Example: `"full_exec_safety_dataset_2025 [FULL]"`

2. **Summary Cards**
   - Add execution type indicator to the "Selected Execution" info
   - Use different colors: 🧪 for test, 🚀 for full

3. **Implementation**
   ```python
   # In Dashboard.py format_execution_name()
   def format_execution_name(exec_name, metadata):
       test_mode = metadata.get("test_mode", "unknown")
       badge = " [TEST]" if test_mode == "test_execution" else " [FULL]"
       return f"{exec_name}{badge}"
   ```

### Option 2: Enhanced Filtering System (Recommended)

**Effort**: Medium (3-4 hours)
**Impact**: High

Add dedicated filtering capabilities:

1. **New Filter Control**
   - Add "Execution Type" dropdown in sidebar: All / Test Only / Full Only
   - Filter executions based on `test_mode` metadata

2. **Separate Statistics**
   - Split summary cards: "Test Executions" vs "Full Executions"
   - Show counts and pass rates separately

3. **Visual Differentiation**
   - Use different background colors in tables
   - Add icon prefixes: 🧪 (test) vs 🚀 (full)

4. **Implementation Approach**
   ```python
   # Add to sidebar filters
   execution_type_filter = st.selectbox(
       "Execution Type",
       ["All", "Test Executions", "Full Executions"]
   )

   # Filter logic
   if execution_type_filter == "Test Executions":
       filtered_data = data[data["test_mode"] == "test_execution"]
   elif execution_type_filter == "Full Executions":
       filtered_data = data[data["test_mode"] == "full_execution"]
   ```

### Option 3: Comprehensive Dashboard Redesign

**Effort**: High (1-2 days)
**Impact**: Very High

Create separate views for test and full executions:

1. **Tabbed Interface**
   - Tab 1: "Full Executions" - Production results
   - Tab 2: "Test Executions" - Quick validation results
   - Tab 3: "All Executions" - Combined view

2. **Execution Type Specific Features**
   - Test Executions: Show sample size, quick validation metrics
   - Full Executions: Show batch progress, comprehensive statistics

3. **Advanced Analytics**
   - Progression tracking: Test → Full execution performance
   - Comparison view: Test vs Full for same dataset/scorer

4. **Batch Progress Visualization** (Full executions only)
   - Progress bar showing `batch_index / total_batches`
   - Estimated completion time based on batch performance

### Option 4: Metadata-Driven Smart Display

**Effort**: Medium-High (4-6 hours)
**Impact**: High

Intelligently adapt display based on execution type:

1. **Smart Summary Cards**
   - Test: Show "Quick Validation Results" with sample size
   - Full: Show "Production Results" with total coverage

2. **Contextual Information**
   - Test: Highlight this is preliminary/validation data
   - Full: Show comprehensive metrics and confidence levels

3. **Warning System**
   - Alert when viewing test results: "⚠️ Test execution with limited samples"
   - Prevent accidental comparison of test vs full results

## Recommended Implementation Path

### Phase 1: Quick Wins (Implement Immediately)
1. Add `[TEST]`/`[FULL]` badges to execution names (Option 1)
2. Add execution type to the displayed metadata
3. Use different icons in the execution selector

### Phase 2: Core Functionality (Next Sprint)
1. Implement execution type filter (Option 2)
2. Add separate summary statistics
3. Visual differentiation with colors/icons

### Phase 3: Advanced Features (Future Enhancement)
1. Tabbed interface for execution types
2. Batch progress tracking for full executions
3. Test-to-full progression analytics

## Technical Implementation Details

### Required Changes

1. **Dashboard.py modifications**:
   ```python
   # Add to parse_datetime_safely function area
   def get_execution_type_badge(metadata):
       test_mode = metadata.get("test_mode", "unknown")
       if test_mode == "test_execution":
           return "🧪 TEST"
       elif test_mode == "full_execution":
           return "🚀 FULL"
       return "❓ UNKNOWN"
   ```

2. **Filter Implementation**:
   ```python
   # In sidebar
   col1, col2 = st.columns(2)
   with col1:
       execution_name_filter = st.selectbox(...)
   with col2:
       execution_type_filter = st.selectbox(
           "Type",
           ["All", "Test", "Full"],
           help="Filter by execution type"
       )
   ```

3. **Data Filtering Logic**:
   ```python
   # Apply execution type filter
   if execution_type_filter != "All":
       filter_value = "test_execution" if execution_type_filter == "Test" else "full_execution"
       filtered_scores = [
           s for s in filtered_scores
           if s.score_metadata_dict.get("test_mode") == filter_value
       ]
   ```

## Success Metrics

1. **User Clarity**: Users can immediately identify execution type
2. **Filtering Efficiency**: Users can filter to see only relevant execution type
3. **Reduced Confusion**: No accidental comparison of test vs full results
4. **Improved Workflow**: Clear progression from test to full execution

## Risks and Mitigations

1. **Risk**: Backward compatibility with existing executions
   - **Mitigation**: Default to "unknown" for executions without test_mode

2. **Risk**: UI clutter with additional information
   - **Mitigation**: Use subtle visual cues and progressive disclosure

3. **Risk**: Performance impact with additional filtering
   - **Mitigation**: Leverage existing data structures, no additional queries

## Conclusion

The infrastructure for distinguishing test and full executions already exists. The recommended approach is to start with Option 1 (minimal visual indicators) for immediate improvement, then implement Option 2 (enhanced filtering) for a comprehensive solution. This phased approach provides quick wins while building toward a more sophisticated execution management system.
