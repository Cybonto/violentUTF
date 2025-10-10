# Report Setup Browse Endpoint Troubleshooting

## Issue Description
The Report Setup page was showing "✅ Found 0 scan execution(s)" while the Dashboard showed 2 executions with the same data.

## Root Causes Identified

### 1. INNER JOIN vs LEFT JOIN Issue
**Problem**: The browse endpoint was using an INNER JOIN between `OrchestratorExecution` and `OrchestratorConfiguration` tables.
```python
.join(OrchestratorConfiguration, OrchestratorExecution.orchestrator_id == OrchestratorConfiguration.id)
```

**Impact**: If an execution's `orchestrator_id` didn't match any configuration record, the execution would be excluded from results.

**Solution**: Changed to LEFT JOIN (outerjoin) to include executions even if orchestrator configuration is missing:
```python
.outerjoin(OrchestratorConfiguration, OrchestratorExecution.orchestrator_id == OrchestratorConfiguration.id)
```

### 2. Date Range Filtering Logic Error
**Problem**: The browse endpoint had incorrect date filtering logic:
```python
if request.end_date:
    stmt = stmt.where(OrchestratorExecution.started_at <= request.end_date)
else:
    # This adds a START date constraint when END date is missing!
    stmt = stmt.where(OrchestratorExecution.started_at >= datetime.utcnow() - timedelta(days=30))
```

**Impact**: When no end_date was provided, it incorrectly added another start date constraint instead of setting an end date.

**Solution**: Fixed to use consistent date range logic:
```python
end_date = request.end_date or datetime.utcnow()
start_date = request.start_date or (end_date - timedelta(days=30))

stmt = stmt.where(
    and_(
        OrchestratorExecution.started_at >= start_date,
        OrchestratorExecution.started_at <= end_date
    )
)
```

### 3. Date Range Boundary Issue
**Problem**: Executions created on 2025-07-20 at 00:20:23 were excluded when searching up to 2025-07-20 00:00:00 (midnight).

**Impact**: Any executions created today would not show up in search results.

**Solution**: Updated default date range to include today + 1 day:
```python
"date_range": (datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=1))
```

## Additional Issues Discovered

### 4. Misaligned Data Expectations
**Problem**: The browse endpoint expected rich metadata in scorer results (generators, score categories, etc.) but actual data had minimal metadata.

**Example**:
- Expected: `generator_name` in score metadata
- Actual: Empty metadata `{}`

**Solution**: Made all advanced filters optional and skip filtering when data doesn't contain expected fields:
```python
# Skip generator filtering if no generators found in scores
if request.generators and scores:
    # ... filter logic
    # Only filter if we found generators in the data
    if execution_generators and not any(gen in execution_generators for gen in request.generators):
        continue
```

### 5. Inconsistent Field Names
**Problem**: UI used "Target Models" but Dashboard used "Generators" terminology.

**Solution**: Aligned terminology and removed non-functional filters from UI.

## Debug Process

1. **Compared endpoints**: Dashboard `/summary` vs Report Setup `/browse`
2. **Added debug logging**:
   - Total executions in DB
   - Completed executions count
   - Date ranges being used
   - Query results at each stage
3. **Identified JOIN failure**: 2 executions in DB, 0 after JOIN
4. **Fixed incrementally**:
   - First: Date logic
   - Second: JOIN type
   - Third: Date boundaries

## Lessons Learned

1. **Always check JOIN types**: LEFT JOIN is safer when foreign key relationships might be missing
2. **Date boundary precision matters**: Searching "up to today" should include all of today
3. **Don't assume data richness**: Scorer data might have minimal metadata
4. **Align with working code**: Dashboard worked, so browse should follow its patterns
5. **Progressive debugging**: Add logging at each stage to isolate issues

## Recommended Future Improvements

1. **Data consistency**: Ensure orchestrator configurations exist for all executions
2. **Metadata enrichment**: Populate score metadata during execution for better filtering
3. **Schema documentation**: Document which fields are guaranteed vs optional
4. **Test data**: Create test data that exercises edge cases (missing FKs, minimal metadata)

## Related Files Modified

- `/violentutf_api/fastapi_app/app/api/endpoints/dashboard.py` - Fixed browse endpoint
- `/violentutf_api/fastapi_app/app/schemas/dashboard.py` - Updated field descriptions
- `/violentutf/pages/13_📊_Report_Setup.py` - Fixed date ranges and removed non-functional filters

## Testing Checklist

- [ ] Test with executions that have missing orchestrator configs
- [ ] Test with executions created today
- [ ] Test with executions that have minimal metadata
- [ ] Test with various date ranges
- [ ] Test with all filters cleared
