# Dashboard Prompt and Response Columns Fix

## Issue
The Prompt and Response columns in the Dashboard (5_Dashboard.py) were showing empty values even though the data was being returned from the API.

## Root Cause
The API returns prompt/response data in a nested structure:
```json
{
  "prompt_request_responses": [
    {
      "request": {
        "prompt": "actual prompt text",
        "conversation_id": "..."
      },
      "response": {
        "content": "actual response text",
        "role": "assistant"
      },
      "metadata": {...}
    }
  ]
}
```

However, the Dashboard expected a simpler structure:
```json
{
  "prompt_response": {
    "prompt": "actual prompt text",
    "response": "actual response text"
  }
}
```

## Solution
Modified the `match_scores_to_responses` function in `/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/pages/5_Dashboard.py` to:

1. Transform the nested API response structure to the expected format
2. Improved matching logic to handle cases where:
   - Responses use `conversation_id` instead of `batch_index`
   - Fallback to index-based matching when other methods fail
3. Added debug logging to help diagnose data structure issues

### Key Changes:
1. **Data transformation**: When assigning prompt_response, extract the nested fields:
   ```python
   matched_score["prompt_response"] = {
       "prompt": response.get("request", {}).get("prompt", ""),
       "response": response.get("response", {}).get("content", ""),
   }
   ```

2. **Enhanced matching**: Added multiple matching strategies:
   - Primary: Match by `batch_index`
   - Secondary: Match by `conversation_id`
   - Fallback: Match by array index position

3. **Debug logging**: Added logging to understand the data structure being received from the API

## Testing
To verify the fix:
1. Run an orchestrator execution that generates scores
2. Navigate to the Dashboard
3. Check that the Prompt and Response columns now display the actual text content
4. Verify that the detailed view (when expanding a result) shows the full prompt and response

## Related Files
- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/pages/5_Dashboard.py` - Main dashboard file with the fix
- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py` - Service that formats the API response
- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/api/endpoints/orchestrators.py` - API endpoint that returns execution results