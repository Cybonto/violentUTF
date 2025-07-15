# Dashboard Issues Fix Plan

## Overview
This document outlines the plan to fix three critical issues in the ViolentUTF Dashboard:
1. Batch tracking inconsistency
2. Time filter and evaluation type filter not working
3. Missing generator responses in Detailed Results table

## Issue Analysis

### Issue 1: Batch Tracking Inconsistency
**Problem**: Dashboard shows 73 incomplete executions while the actual execution completed all 390 prompts in 78 batches with 109 successful (27.9% success rate).

**Potential Causes**:
- Batch completion status not being properly updated in DuckDB
- Race condition between batch processing and status updates
- Incorrect query logic for counting incomplete batches
- Missing or delayed status updates for completed batches

### Issue 2: Filter Options Not Working
**Problem**: Time range filter (e.g., last 4 hours) and evaluation type filter (True/False) show no results.

**Potential Causes**:
- Timezone mismatch between stored timestamps and filter logic
- Incorrect date/time format conversion
- Filter query logic errors
- Missing or incorrect column mappings for evaluation types

### Issue 3: Missing Generator Responses
**Problem**: Detailed Results table does not display generator responses.

**Potential Causes**:
- Column not included in query
- UI component not configured to display the column
- Data not being properly stored in the database
- Column name mismatch between database and UI

## Investigation Plan

### Step 1: Database Schema Analysis
- Check DuckDB schema for batch tracking tables
- Verify column names and data types
- Check indexes and constraints

### Step 2: Data Integrity Check
- Query sample data to verify batch statuses
- Check timestamp formats and timezones
- Verify generator response storage

### Step 3: Code Analysis
- Review Dashboard.py query logic
- Check filter implementation
- Analyze batch status update logic
- Review data display components

### Step 4: Testing
- Create test data with known values
- Test each filter independently
- Verify batch status updates in real-time

## Implementation Plan

### Phase 1: Fix Batch Tracking (Priority: High)
1. Identify batch status tracking mechanism
2. Fix status update logic
3. Add proper error handling
4. Implement batch reconciliation logic
5. Add logging for debugging

### Phase 2: Fix Filter Options (Priority: High)
1. Standardize timezone handling
2. Fix date/time conversion logic
3. Correct filter query generation
4. Test with various filter combinations
5. Add debug logging for filters

### Phase 3: Fix Generator Response Display (Priority: Medium)
1. Verify response storage in database
2. Update query to include response column
3. Configure UI to display responses
4. Handle long responses gracefully
5. Add response preview/expansion feature

### Phase 4: Testing & Validation
1. Create comprehensive test suite
2. Test with various datasets
3. Verify performance with large datasets
4. Document any limitations

## Success Criteria
- Batch counts match actual execution results
- All filters work correctly and show appropriate data
- Generator responses are visible in Detailed Results
- Dashboard performance remains acceptable
- No regression in existing functionality

## Timeline
- Investigation: 30 minutes
- Phase 1 Implementation: 45 minutes
- Phase 2 Implementation: 45 minutes
- Phase 3 Implementation: 30 minutes
- Testing & Validation: 30 minutes
- Total: ~3 hours

## Files to Modify
1. `/violentutf/pages/5_Dashboard.py` - Main dashboard logic
2. `/violentutf/utils/db_utils.py` - Database query utilities
3. `/violentutf/orchestrators/orchestrator_utils.py` - Batch status updates
4. `/violentutf/scorers/scorer_utils.py` - Score result storage

## Risk Mitigation
- Create backups before making changes
- Test in isolation before integration
- Add comprehensive logging
- Implement gradual rollout if possible