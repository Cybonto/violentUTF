# Dashboard Filtering Functions - Potential Issues Analysis

## Summary
This document identifies potential issues in the dynamic filtering functions and hierarchical metrics code in `/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/pages/5_Dashboard.py`.

## Critical Issues Found

### 1. KeyError Exceptions

#### Issue 1.1: Direct Dictionary Access in `apply_entity_filters` (Lines 449-458)
```python
if executions:
    filtered = [r for r in filtered if r.get("execution_id") in executions or r.get("execution_name") in executions]
```
**Problem**: If `executions` contains None values, the `in` operator will fail.

#### Issue 1.2: Direct Key Access in `apply_result_filters` (Lines 481-487)
```python
if r.get("score_type") == "true_false" and r.get("score_value") is True:
    violation_filtered.append(r)
elif r.get("score_type") == "float_scale" and r.get("score_value", 0) >= 0.6:
    violation_filtered.append(r)
```
**Problem**: The code assumes `score_value` exists and is a valid type. If `score_value` is None or a string, comparisons will fail.

#### Issue 1.3: Score Range Filter (Lines 494-496)
```python
score_val = r.get("score_value", 0)
if score_range["min"] <= score_val <= score_range["max"]:
    range_filtered.append(r)
```
**Problem**: Direct dictionary access `score_range["min"]` and `score_range["max"]` without checking if keys exist.

### 2. Type Comparison Errors

#### Issue 2.1: Timestamp Comparison in `apply_time_filter` (Lines 433-437)
```python
if isinstance(timestamp, str):
    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

if start_time <= timestamp <= end_time:
    filtered.append(r)
```
**Problem**: If timestamp conversion fails or timestamp is None, the comparison will raise an exception.

#### Issue 2.2: Score Value Type Assumptions (Line 484)
```python
elif r.get("score_type") == "float_scale" and r.get("score_value", 0) >= 0.6:
```
**Problem**: Assumes `score_value` is numeric. If it's a string like "0.8" or None, this will fail.

#### Issue 2.3: Severity Map Lambda Functions (Lines 55-72)
```python
"float_scale": lambda val: (
    (
        "critical"
        if float(val) >= 0.8
        # ...
    )
    if val is not None and str(val).replace(".", "").replace("-", "").isdigit()
    else "unknown"
),
```
**Problem**: The `float()` conversion can still fail even after the isdigit() check (e.g., for values like "1.2.3").

### 3. Accessing Attributes on None Values

#### Issue 3.1: Filter State Initialization (Lines 545-567)
```python
fs = st.session_state.filter_state

# Time filter
if fs["time"]["preset"] != "all_time":
    count += 1
```
**Problem**: Direct dictionary access without checking if nested keys exist.

#### Issue 3.2: Custom Time Range (Lines 579)
```python
filtered = apply_time_filter(filtered, fs["time"]["preset"], fs["time"]["custom_start"], fs["time"]["custom_end"])
```
**Problem**: Accessing nested dictionary values without validation.

### 4. List/Set Operations on None Values

#### Issue 4.1: Entity Collection (Lines 516-530)
```python
if r.get("execution_id"):
    exec_set.add(r["execution_id"])  # Direct key access!
if r.get("execution_name"):
    exec_set.add(r["execution_name"])
```
**Problem**: After checking with `.get()`, the code uses direct dictionary access `r["execution_id"]` which could raise KeyError.

#### Issue 4.2: Hierarchical Metrics (Lines 907-924)
```python
batch_idx = r.get("batch_index", 0)
total_b = r.get("total_batches", 1)
# ...
batch_info[batch_key]["scorers"].add(r.get("scorer_name", "Unknown"))
```
**Problem**: If batch_info[batch_key] doesn't exist or "scorers" is None, this will fail.

## Recommended Fixes

### 1. Safe Dictionary Access Pattern
```python
# Instead of:
if fs["time"]["preset"] != "all_time":

# Use:
if fs.get("time", {}).get("preset") != "all_time":
```

### 2. Type-Safe Comparisons
```python
# Instead of:
if r.get("score_value", 0) >= 0.6:

# Use:
score_value = r.get("score_value", 0)
try:
    if isinstance(score_value, (int, float)) and score_value >= 0.6:
        # Process
except (TypeError, ValueError):
    # Handle error
```

### 3. Null-Safe Operations
```python
# Instead of:
exec_set.add(r["execution_id"])

# Use:
exec_id = r.get("execution_id")
if exec_id is not None:
    exec_set.add(exec_id)
```

### 4. Defensive Filter State Access
```python
def get_filter_value(filter_state, *keys, default=None):
    """Safely navigate nested dictionary structure."""
    result = filter_state
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default
        if result is None:
            return default
    return result
```

### 5. Safe Timestamp Handling
```python
def safe_parse_timestamp(timestamp):
    """Safely parse timestamp with error handling."""
    if not timestamp:
        return None
    
    try:
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif isinstance(timestamp, datetime):
            return timestamp
    except (ValueError, AttributeError):
        return None
    
    return None
```

## High-Risk Areas

1. **apply_result_filters** (Lines 463-503): Multiple type assumptions and comparisons
2. **calculate_hierarchical_metrics** (Lines 869-1046): Complex nested data structures with many assumptions
3. **apply_time_filter** (Lines 398-439): Timestamp parsing and comparison
4. **get_unique_entities** (Lines 506-537): Direct dictionary access after .get() checks

## Testing Recommendations

1. Test with None values in all filter fields
2. Test with mixed type score values (strings, None, invalid numbers)
3. Test with missing keys in nested dictionaries
4. Test with empty or malformed timestamps
5. Test with incomplete batch metadata
6. Test with filter state containing unexpected structure

## Priority Fixes

1. **CRITICAL**: Fix direct dictionary access in `get_unique_entities` (Line 519, 521)
2. **HIGH**: Add type checking in `apply_result_filters` before numeric comparisons
3. **HIGH**: Add null checks in `calculate_hierarchical_metrics` for batch operations
4. **MEDIUM**: Improve timestamp parsing with proper error handling
5. **MEDIUM**: Add defensive checks for filter state structure