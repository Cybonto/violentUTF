# Retry Mechanism Implementation for 429 Rate Limiting

**Date**: July 17, 2025
**Author**: Implementation Team
**Purpose**: Implement comprehensive retry mechanisms for handling 429 throttling errors in both TEST and FULL executions

## Problem Analysis

### Original Issue
Tests and executions were failing with:
```
API Error: 429 - {"detail":"ThrottlingException: Too many requests, please wait before trying again."}
```

### Root Cause Analysis
1. **TokenManager has retry logic** (✅ works at API level)
   - 3 retries with exponential backoff
   - Handles 429 errors properly
   - Network error retry

2. **PyRIT Orchestrator lacks retry** (❌ problem)
   - No retry wrapper around orchestrator.send_prompts_async()
   - Failed prompts marked as errors instead of retrying
   - No delay between prompt batches

3. **No execution-type differentiation** (❌ problem)
   - TEST and FULL executions use same retry strategy
   - No adaptive rate limiting

## Implementation Details

### 1. Retry Decorator (`with_retry_logic`)

**Location**: `violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py:22-70`

```python
def with_retry_logic(max_retries: int = 3, base_delay: float = 1.0, exponential_backoff: bool = True):
    """Decorator to add retry logic with exponential backoff for orchestrator operations."""
```

**Features**:
- ✅ Exponential backoff: 1s → 2s → 4s → 8s
- ✅ Retriable error detection: 429, throttling, timeout, network errors
- ✅ Non-retriable error pass-through: Authentication, validation errors
- ✅ Comprehensive logging for debugging

### 2. Orchestrator Retry Methods

#### Dataset Prompt Execution
**Method**: `_send_prompts_with_retry()` (lines 1008-1034)
- Wraps `orchestrator.send_prompts_async()` with retry logic
- Applies execution-specific retry configuration
- Includes inter-prompt delay option

#### Direct Prompt List Execution
**Method**: `_send_prompt_list_with_retry()` (lines 1036-1061)
- Handles direct prompt list scenarios
- Same retry logic as dataset execution
- Preserves metadata and memory labels

### 3. Adaptive Retry Configuration

**Method**: `_get_retry_config()` (lines 1063-1084)

#### TEST Execution Strategy
```python
{
    "max_retries": 2,
    "base_delay": 0.5,
    "exponential_backoff": True,
    "inter_prompt_delay": 0.2
}
```
- **Fast feedback**: Shorter delays for rapid testing
- **Reduced retries**: 2 attempts to avoid long test waits
- **Light throttling**: 0.2s between prompts

#### FULL Execution Strategy
```python
{
    "max_retries": 5,
    "base_delay": 2.0,
    "exponential_backoff": True,
    "inter_prompt_delay": 0.5
}
```
- **Robust recovery**: 5 retry attempts for production runs
- **Conservative delays**: 2s base delay for stability
- **Rate limiting**: 0.5s between prompts to prevent overwhelming APIs

## Error Handling Flow

### Before Implementation
1. Orchestrator → Target → TokenManager gets 429
2. TokenManager retries 3x and returns None
3. Target creates error response
4. Orchestrator continues with error response ❌

### After Implementation
1. Orchestrator → Retry wrapper detects retriable error
2. Exponential backoff delay (0.5s-2s based on execution type)
3. Orchestrator retries entire prompt batch
4. TokenManager provides additional retry layer
5. Success or fail after max retries ✅

## Integration Points

### Modified Execution Calls

**Dataset Execution** (line 553-556):
```python
# OLD: Direct call
results = await orchestrator.send_prompts_async(...)

# NEW: With retry wrapper
results = await self._send_prompts_with_retry(
    orchestrator, dataset_prompts, memory_labels, execution_config
)
```

**Prompt List Execution** (line 504-507):
```python
# OLD: Direct call
results = await orchestrator.send_prompts_async(...)

# NEW: With retry wrapper
results = await self._send_prompt_list_with_retry(
    orchestrator, prompt_list, prompt_type, memory_labels, metadata, execution_config
)
```

## Benefits

### Reliability Improvements
- ✅ **Automatic recovery** from rate limiting errors
- ✅ **Reduced false failures** in high-load scenarios
- ✅ **Graceful degradation** with exponential backoff

### Performance Optimization
- ✅ **Fast TEST execution** with minimal delays
- ✅ **Robust FULL execution** with comprehensive retry
- ✅ **Inter-prompt delays** to prevent rate limit hits

### Monitoring & Debugging
- ✅ **Detailed retry logging** for troubleshooting
- ✅ **Error classification** (retriable vs non-retriable)
- ✅ **Execution type awareness** for different strategies

## Testing Recommendations

### TEST Execution Verification
```bash
# Should complete quickly with 2 retries max
curl -X POST /api/orchestrators/{id}/execute \
  -d '{"execution_type": "dataset", "input_data": {"metadata": {"is_test_execution": true}}}'
```

### FULL Execution Verification
```bash
# Should be more resilient with 5 retries max
curl -X POST /api/orchestrators/{id}/execute \
  -d '{"execution_type": "dataset", "input_data": {"metadata": {"is_test_execution": false}}}'
```

### Rate Limiting Simulation
```bash
# Run multiple concurrent executions to trigger 429s
for i in {1..10}; do
  curl -X POST /api/orchestrators/{id}/execute &
done
```

## Future Enhancements

### Circuit Breaker Pattern
- Implement provider-level failure detection
- Temporary provider disabling after repeated failures
- Automatic recovery after cool-down period

### Adaptive Rate Limiting
- Dynamic delay adjustment based on response times
- Provider-specific rate limiting policies
- Queue-based retry for failed prompts

### Advanced Monitoring
- Retry success/failure metrics
- Provider health dashboard
- Automated alerting for high failure rates

## Configuration Options

### Environment Variables (Future)
```bash
# Override default retry settings
PYRIT_TEST_MAX_RETRIES=3
PYRIT_FULL_MAX_RETRIES=7
PYRIT_BASE_DELAY=1.5
PYRIT_INTER_PROMPT_DELAY=0.3
```

### Per-Provider Settings (Future)
```yaml
retry_policies:
  openai:
    max_retries: 5
    base_delay: 2.0
  anthropic:
    max_retries: 3
    base_delay: 1.0
  gsai:
    max_retries: 7
    base_delay: 3.0
```

## Summary

The retry mechanism implementation provides:

1. **Multi-layer retry protection**: Orchestrator + TokenManager levels
2. **Execution-aware strategies**: Different configs for TEST vs FULL
3. **Intelligent error handling**: Retry only recoverable errors
4. **Performance optimization**: Minimal delays for testing, robust for production
5. **Comprehensive logging**: Full visibility into retry behavior

This solves the 429 throttling issue while maintaining fast test execution and robust production reliability.
