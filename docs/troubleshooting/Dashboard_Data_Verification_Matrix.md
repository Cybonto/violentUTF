# Dashboard Data Verification Matrix

## Purpose
This document verifies that the new optimized API endpoints provide all data required by each Dashboard component.

## Data Structure Comparison

### Original Data Loading (Multiple API Calls)
```
1. GET /api/v1/orchestrators → List of orchestrators
2. For each orchestrator:
   - GET /api/v1/orchestrators/{id}/executions → Executions
3. For each execution:
   - GET /api/v1/orchestrators/executions/{id}/results → Scores
```

### New Optimized Endpoints (2 API Calls)
```
1. GET /api/v1/dashboard/summary → Execution summaries
2. GET /api/v1/dashboard/scores → Paginated score results
```

## Required Fields by Dashboard Component

### 1. Executive Summary Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| execution_id | Counting executions | execution.id | ✅ Yes |
| test_mode | Filtering test/full | metadata.test_mode | ✅ Yes |
| score_value | Critical findings count | score.score_value | ✅ Yes |
| severity | Severity breakdown | Calculated from score | ✅ Yes (calculated) |
| timestamp | Date filtering | score.timestamp | ✅ Yes |
| batch_index | Completion tracking | metadata.batch_index | ✅ Yes |
| total_batches | Completion rate | metadata.total_batches | ✅ Yes |

### 2. Score Results Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| scorer_name | Grouping by scorer | metadata.scorer_name | ✅ Yes |
| score_value | Pass/fail counts | score.score_value | ✅ Yes |
| score_type | Type display | score.score_type | ✅ Yes |
| execution_id | Linking to execution | execution.id | ✅ Yes |
| execution_name | Display name | execution.name | ✅ Yes |

### 3. Batch Analysis Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| batch_index | Batch identification | metadata.batch_index | ✅ Yes |
| dataset_name | Dataset display | metadata.dataset_name | ✅ Yes |
| score_value | Violation rate | score.score_value | ✅ Yes |
| severity | Severity counts | Calculated | ✅ Yes |
| execution_id | Grouping | execution.id | ✅ Yes |

### 4. Severity Analysis Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| severity | Distribution chart | Calculated | ✅ Yes |
| score_value | Severity calculation | score.score_value | ✅ Yes |
| score_type | Severity logic | score.score_type | ✅ Yes |
| scorer_name | Breakdown by scorer | metadata.scorer_name | ✅ Yes |
| generator_name | Affected models | metadata.generator_name | ✅ Yes |

### 5. Detailed Results Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| All score fields | Table display | Various | ✅ Yes |
| score_rationale | Rationale display | score.score_rationale | ✅ Yes |
| prompt_response | Evidence display | Matched from responses | ✅ Yes (when include_responses=true) |
| response_insights | Analysis | Calculated | ✅ Yes (when include_responses=true) |

### 6. Temporal Analysis Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| timestamp | Time series | score.timestamp | ✅ Yes |
| severity | Trend analysis | Calculated | ✅ Yes |
| score_value | Score trends | score.score_value | ✅ Yes |
| execution_name | Timeline | execution.name | ✅ Yes |

### 7. Compatibility Matrix Tab
| Field | Used For | Original Source | New Endpoint Provides |
|-------|----------|-----------------|----------------------|
| scorer_name | Matrix rows | metadata.scorer_name | ✅ Yes |
| generator_name | Matrix columns | metadata.generator_name | ✅ Yes |
| score_value | Cell values | score.score_value | ✅ Yes |
| dataset_name | Alternative matrix | metadata.dataset_name | ✅ Yes |

### 8. COB Reports Tab
This tab doesn't use execution/score data - it uses separate COB report endpoints.

## Additional Data Requirements

### Enhanced Evidence Mode
When `include_responses=true`:
- `prompt_response.prompt` - The prompt text
- `prompt_response.response` - The response text
- `response_insights` - Analysis of response content

### Filtering Support
- `test_mode` - Properly set to "test_execution" or "full_execution"
- `timestamp` - ISO format for date filtering
- All metadata fields for entity filtering

## API Response Validation

### Dashboard Summary Endpoint Response
```json
{
  "total_executions": 78,
  "total_scores": 675,
  "date_range": {
    "start": "2024-12-18T00:00:00",
    "end": "2025-01-18T00:00:00",
    "days": 30
  },
  "executions": [
    {
      "id": "uuid",
      "name": "execution_name",
      "orchestrator_name": "orchestrator_name",
      "orchestrator_type": "PromptSendingOrchestrator",
      "status": "completed",
      "created_at": "2025-01-17T10:00:00",
      "score_count": 10,
      "test_mode": "full_execution",
      "metadata": {}
    }
  ]
}
```

### Dashboard Scores Endpoint Response
```json
{
  "scores": [
    {
      "execution_id": "uuid",
      "execution_name": "name",
      "orchestrator_name": "name",
      "score_value": false,
      "score_type": "true_false",
      "score_category": "security",
      "score_rationale": "Detected violation...",
      "timestamp": "2025-01-17T10:00:00",
      "scorer_type": "SelfAskTrueFalseScorer",
      "scorer_name": "custom_scorer",
      "generator_name": "gpt-4",
      "generator_type": "AI Gateway",
      "dataset_name": "security_test",
      "test_mode": "full_execution",
      "batch_index": 0,
      "total_batches": 1,
      "severity": "high",
      "prompt_response": {
        "prompt": "...",
        "response": "...",
        "conversation_id": "uuid",
        "timestamp": "..."
      },
      "response_insights": {
        "contains_code": false,
        "contains_url": false,
        "contains_instruction": true,
        "length": 256,
        "prompt_type": "general"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 100,
    "total_count": 675,
    "total_pages": 7
  }
}
```

## Conclusion

✅ **All Dashboard components receive the required data from the new endpoints**

The new optimized endpoints provide:
1. All fields required by every Dashboard tab
2. Proper data types and formats
3. Calculated fields (severity)
4. Optional enhanced data (prompt/response)
5. Pagination support for large datasets
6. Test mode filtering

The implementation successfully maintains backward compatibility while significantly improving performance for enterprise environments with large datasets.