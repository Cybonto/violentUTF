# Scorer Full Execution Timeout Optimization

## Problem Statement
The full execution of scorers was timing out after 30 seconds for most batches, with only a 20% success rate (only batch 2 succeeded out of 5 batches).

## Root Cause Analysis
1. **Default timeout too short**: The API request timeout was hardcoded to 30 seconds
2. **Batch size too large**: Processing 10 prompts per batch exceeded the 30-second timeout
3. **No timeout customization**: The `api_request` function didn't support custom timeouts
4. **No failure recovery**: Consecutive failures weren't handled, leading to wasted processing

## Solution Implemented

### 1. Customizable Timeout Support
Modified `api_request` function to accept custom timeout parameter:
```python
def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    # Allow custom timeout for long-running operations
    timeout = kwargs.pop('timeout', 30)
```

### 2. Reduced Batch Size
Changed batch processing from 10 to 5 prompts per batch:
```python
# Before: batch_size = 10
batch_size = 5  # Process 5 prompts at a time to avoid timeout
```

### 3. Increased Timeouts for Long Operations
- Batch execution: Increased from 30s to 60s
- Test execution: Increased from 30s to 45s
- Orchestrator test mode: Reduced batch size from 5 to 3

### 4. Consecutive Failure Handling
Added early termination if too many batches fail consecutively:
```python
consecutive_failures = 0
max_consecutive_failures = 3  # Stop if 3 batches fail in a row

# In execution loop:
if consecutive_failures >= max_consecutive_failures:
    st.error(f"❌ Stopping execution: {consecutive_failures} consecutive batches failed")
    break
```

## Performance Impact

### Before Changes
- Batch size: 10 prompts
- Timeout: 30 seconds
- Expected processing: 70 seconds (7s per prompt average)
- Result: 80% failure rate due to timeouts

### After Changes
- Batch size: 5 prompts
- Timeout: 60 seconds for batches, 45 seconds for tests
- Expected processing: 35 seconds (7s per prompt average)
- Safety margin: 25 seconds
- Result: Should achieve >95% success rate

## Testing Recommendations

1. **Test with small datasets first**: Start with 10-20 prompts to verify the fix
2. **Monitor batch execution times**: Log actual processing times to fine-tune batch sizes
3. **Consider async execution**: For very large datasets (>100 prompts), consider implementing async execution with status polling

## Future Improvements

1. **Dynamic batch sizing**: Adjust batch size based on average processing time
2. **Parallel batch processing**: Execute multiple batches concurrently
3. **Progressive timeout**: Increase timeout based on dataset size
4. **Background execution**: Implement true async execution with progress tracking

## Files Modified
- `/violentutf/pages/4_Configure_Scorers.py`: Main implementation changes
  - Line 125: Added configurable timeout support
  - Line 1097: Reduced batch size from 10 to 5
  - Line 341: Reduced test batch size from 5 to 3
  - Line 441: Increased test execution timeout to 45s
  - Line 1188: Increased batch execution timeout to 60s
  - Lines 1104-1225: Added consecutive failure handling