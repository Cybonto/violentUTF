# Plan: Investigating Scorer Result Inconsistencies in ViolentUTF Dashboard

## Executive Summary

This plan outlines a systematic approach to identify and resolve inconsistencies between actual scorer results generated during orchestrator execution and the results displayed on the ViolentUTF Dashboard. The investigation will trace data flow through multiple systems and identify potential points of failure or transformation.

## Background

The ViolentUTF platform uses a complex data pipeline:
1. **PyRIT Framework** executes scorers and stores results in DuckDB (temporary)
2. **Orchestrator Service** collects PyRIT results and stores them in SQLite (persistent)
3. **Dashboard** queries SQLite and displays aggregated results

Inconsistencies may arise at any stage of this pipeline due to:
- Data transformation errors
- Timing issues between systems
- Schema mismatches
- Incomplete data capture
- Display logic errors

## Investigation Phases

### Phase 1: Data Flow Mapping and Documentation

**Objective**: Create a complete map of how scorer data flows through the system

**Tasks**:
1. **Document PyRIT Scorer Execution**
   - Review scorer implementation in PyRIT framework
   - Identify exact data structures returned by each scorer type
   - Document DuckDB schema for scorer results
   - Trace scorer result storage in PyRIT memory

2. **Analyze Orchestrator Data Collection**
   - Review orchestrator execution code
   - Identify how PyRIT results are retrieved
   - Document transformation logic applied to scorer results
   - Analyze SQLite storage schema and procedures

3. **Examine Dashboard Query Logic**
   - Review Dashboard data retrieval queries
   - Document any aggregation or transformation logic
   - Identify filtering and grouping mechanisms
   - Analyze display formatting and presentation logic

**Deliverables**:
- Data flow diagram showing all transformation points
- Schema comparison document (DuckDB vs SQLite vs Display)
- List of identified transformation functions

### Phase 2: Inspection Tool Development

**Objective**: Create tools to compare data at each stage of the pipeline

**Tools to Develop**:

1. **PyRIT Memory Inspector**
   ```python
   # Tool to directly query PyRIT DuckDB and export raw scorer results
   - Connect to user-specific PyRIT memory database
   - Query all scorer results for a given execution
   - Export results in standardized JSON format
   - Capture exact data types (boolean, int, float, string)
   ```

2. **SQLite Result Validator**
   ```python
   # Tool to validate orchestrator execution results in SQLite
   - Query orchestrator_executions table
   - Parse stored JSON results
   - Validate schema compliance
   - Check for data completeness
   - Track data type transformations
   ```

3. **Cross-System Comparator**
   ```python
   # Tool to compare results between PyRIT and SQLite
   - Match executions by timestamp/ID
   - Compare scorer counts
   - Identify missing or transformed data
   - Generate discrepancy reports
   - Flag data type changes (True → "true" → 1)
   ```

4. **Dashboard Query Replicator**
   ```python
   # Tool to replicate Dashboard queries and compare results
   - Execute same queries as Dashboard
   - Compare raw query results with displayed data
   - Identify display logic issues
   - Verify aggregation calculations
   ```

5. **Interpretation Validator**
   ```python
   # Tool to validate score interpretation consistency
   - Track score value transformations through pipeline
   - Verify boolean interpretation (True/False → Pass/Fail)
   - Validate scale normalizations (1-5 → 0-1)
   - Check category name preservation
   - Compare severity thresholds across systems
   ```

6. **Aggregation Auditor**
   ```python
   # Tool to audit aggregation calculations
   - Recalculate statistics from raw data
   - Compare with stored/displayed aggregates
   - Verify:
     * Pass/fail rate calculations
     * Average/median/percentile calculations
     * Batch grouping logic
     * Time-based aggregations
   - Flag calculation method differences
   ```

7. **Semantic Consistency Checker**
   ```python
   # Tool to verify semantic meaning preservation
   - Map score meanings across scorer types
   - Verify consistent success/failure definitions
   - Check category hierarchies
   - Validate threshold interpretations
   - Track context preservation in aggregations
   ```

### Phase 3: Systematic Testing

**Objective**: Execute controlled tests to identify specific inconsistency patterns

**Test Scenarios**:

1. **Single Scorer Test**
   - Execute one scorer type at a time
   - Trace results through entire pipeline
   - Document any transformations or losses

2. **Multi-Scorer Test**
   - Execute multiple scorer types simultaneously
   - Verify all results are captured and displayed
   - Check for scorer type confusion

3. **High-Volume Test**
   - Execute large batches of scorers
   - Check for data truncation or timeouts
   - Verify pagination and aggregation accuracy

4. **Edge Case Test**
   - Test with null/empty results
   - Test with very long text responses
   - Test with special characters and Unicode
   - Test with concurrent executions

5. **Interpretation Accuracy Test**
   - **Boolean Interpretation**: Run True/False scorers and verify:
     - Raw PyRIT: True/False
     - SQLite storage: true/false or 1/0
     - Dashboard display: "Pass"/"Fail" or percentage
   - **Scale Interpretation**: Run Likert scorers and verify:
     - Consistent scale ranges (1-5 vs 0-1 normalized)
     - Average calculations across different scales
     - Severity threshold interpretations
   - **Category Mapping**: Run category scorers and verify:
     - Category names preserved exactly
     - No unintended category merging
     - Hierarchical categories maintained

6. **Aggregation Validation Test**
   - **Batch Statistics**: For each batch, verify:
     - Total count matches sum of all scorer results
     - Pass/fail rate calculation method consistent
     - No double-counting of composite scorer sub-results
   - **Time-based Aggregation**: Test aggregations by:
     - Hour/Day/Week with timezone considerations
     - Overlapping time windows
     - Incomplete time periods
   - **Scorer Type Aggregation**: Verify:
     - Grouping by scorer type preserves all types
     - Mixed scorer type statistics calculated correctly
     - Percentage calculations use correct denominators

7. **Statistical Consistency Test**
   - **Average Calculations**: Compare averages calculated at:
     - PyRIT level (raw scores)
     - SQLite level (stored aggregates)
     - Dashboard level (display calculations)
   - **Distribution Metrics**: Verify consistency of:
     - Median values across mixed data types
     - Percentile calculations (25th, 75th, 95th)
     - Standard deviation for severity scores
   - **Success Rate Definitions**: Test different interpretations:
     - True = Success vs False = Success
     - Threshold-based success (score > X)
     - Category-based success (specific categories only)

**Test Matrix**:
| Scorer Type | Single Execution | Batch Execution | Edge Cases | Known Issues |
|-------------|------------------|-----------------|------------|--------------|
| SubStringScorer | ✓ | ✓ | ✓ | ? |
| SelfAskTrueFalseScorer | ✓ | ✓ | ✓ | ? |
| SelfAskLikertScorer | ✓ | ✓ | ✓ | ? |
| SelfAskCategoryScorer | ✓ | ✓ | ✓ | ? |
| CompositeScorer | ✓ | ✓ | ✓ | ? |

### Phase 4: Common Inconsistency Patterns

**Objective**: Document and categorize common inconsistency types

**Expected Patterns**:

1. **Data Loss Patterns**
   - Missing scorer results
   - Incomplete prompt/response capture
   - Lost metadata fields

2. **Transformation Errors**
   - Boolean to string conversion issues
   - Float precision problems
   - Category name mismatches

3. **Timing Issues**
   - Race conditions in data capture
   - Asynchronous execution problems
   - Incomplete result aggregation

4. **Display Logic Errors**
   - Incorrect filtering
   - Wrong aggregation logic
   - Timezone/date formatting issues

5. **Interpretation and Aggregation Inconsistencies**
   - **Score Interpretation Errors**
     - True/False scorers displayed as 1/0 or "true"/"false" strings
     - Likert scale values interpreted differently (1-5 vs 0-4 vs percentages)
     - Category scorer results mapped to wrong display categories
     - Threshold scorer boolean results misinterpreted as pass/fail
   
   - **Aggregation Logic Issues**
     - Incorrect calculation of pass/fail rates (e.g., counting null as fail)
     - Wrong grouping of results by batch or scorer type
     - Duplicate counting in composite scorer results
     - Missing results in percentage calculations (denominator errors)
   
   - **Statistical Calculation Errors**
     - Average severity calculations including/excluding zeros differently
     - Median calculations on mixed data types
     - Percentile calculations with inconsistent sorting
     - Success rate calculations with different definitions of "success"
   
   - **Batch and Grouping Problems**
     - Batch identification logic extracting wrong patterns from execution names
     - Results from multiple batches incorrectly merged
     - Partial batch results displayed as complete
     - Time-based grouping using different timezone interpretations

6. **Semantic Inconsistencies**
   - **Score Meaning Variations**
     - Same score value meaning different things for different scorer types
     - Context-dependent interpretation not preserved
     - Scorer rationale not considered in aggregation
   
   - **Result Categorization Issues**
     - Auto-categorization overriding scorer-specified categories
     - Display categories not matching scorer output categories
     - Hierarchical categories flattened incorrectly

### Phase 5: Root Cause Analysis

**Objective**: Identify specific code locations causing inconsistencies

**Analysis Steps**:

1. **Code Review Checklist**
   - [ ] PyRIT scorer result serialization
   - [ ] Orchestrator result collection logic
   - [ ] SQLite storage procedures
   - [ ] Dashboard query construction
   - [ ] Result transformation functions
   - [ ] Display formatting logic

2. **Data Validation Points**
   - [ ] PyRIT → Orchestrator data transfer
   - [ ] Orchestrator → SQLite storage
   - [ ] SQLite → Dashboard query
   - [ ] Query result → Display transformation

3. **Error Handling Review**
   - [ ] Silent failure identification
   - [ ] Partial result handling
   - [ ] Exception logging adequacy

## Implementation Timeline

### Week 1: Data Flow Mapping
- Days 1-2: Document PyRIT scorer implementation
- Days 3-4: Analyze orchestrator collection logic
- Day 5: Review Dashboard query mechanisms

### Week 2: Tool Development
- Days 1-2: Build PyRIT Memory Inspector
- Day 3: Create SQLite Result Validator
- Days 4-5: Develop Cross-System Comparator

### Week 3: Testing and Analysis
- Days 1-3: Execute systematic test scenarios
- Days 4-5: Analyze results and document patterns

### Week 4: Resolution
- Days 1-3: Implement fixes for identified issues
- Days 4-5: Validate fixes and document solutions

## Success Metrics

1. **Identification Metrics**
   - Number of inconsistency types identified
   - Percentage of test cases revealing issues
   - Code coverage of inspection tools

2. **Resolution Metrics**
   - Percentage of inconsistencies resolved
   - Reduction in user-reported issues
   - Improvement in data accuracy

3. **Prevention Metrics**
   - Automated validation tests implemented
   - Monitoring alerts configured
   - Documentation completeness

## Risk Mitigation

1. **Data Integrity Risks**
   - Create backups before any modifications
   - Test fixes in isolated environment
   - Implement gradual rollout

2. **Performance Risks**
   - Monitor query performance impact
   - Optimize inspection tools for production
   - Implement caching where appropriate

3. **Compatibility Risks**
   - Ensure backward compatibility
   - Version all schema changes
   - Maintain migration scripts

## Next Steps

1. **Immediate Actions**
   - Review and approve this plan
   - Allocate resources for implementation
   - Set up development environment

2. **Communication**
   - Notify stakeholders of investigation
   - Create progress tracking dashboard
   - Schedule regular update meetings

3. **Documentation**
   - Create investigation wiki
   - Document all findings
   - Maintain decision log

## Appendix: Quick Investigation Commands

```bash
# Check PyRIT memory databases
ls -la ./violentutf/app_data/violentutf/pyrit_memory_*.db

# Inspect SQLite orchestrator results
docker exec violentutf_api sqlite3 /app/app_data/violentutf.db \
  "SELECT COUNT(*) FROM orchestrator_executions WHERE results IS NOT NULL;"

# Sample scorer results from SQLite
docker exec violentutf_api python3 -c "
import sqlite3
import json
conn = sqlite3.connect('/app/app_data/violentutf.db')
cursor = conn.cursor()
cursor.execute('SELECT results FROM orchestrator_executions LIMIT 1')
result = cursor.fetchone()
if result and result[0]:
    data = json.loads(result[0])
    print(json.dumps(data, indent=2))
"

# Compare Dashboard query with direct query
# (Execute same query Dashboard uses and compare results)

# === INTERPRETATION AND AGGREGATION CHECKS ===

# Check boolean score interpretations
docker exec violentutf_api python3 -c "
import sqlite3
import json
conn = sqlite3.connect('/app/app_data/violentutf.db')
cursor = conn.cursor()
cursor.execute('SELECT results FROM orchestrator_executions WHERE results IS NOT NULL LIMIT 5')
for row in cursor.fetchall():
    data = json.loads(row[0])
    for score in data.get('scores', []):
        if score.get('scorer_class_name') == 'SelfAskTrueFalseScorer':
            print(f\"Value: {score.get('score_value')} (type: {type(score.get('score_value')).__name__})\")"

# Verify aggregation calculations
docker exec violentutf_api python3 -c "
import sqlite3
import json
conn = sqlite3.connect('/app/app_data/violentutf.db')
cursor = conn.cursor()
cursor.execute('SELECT execution_name, results FROM orchestrator_executions WHERE results IS NOT NULL')
batch_stats = {}
for row in cursor.fetchall():
    exec_name = row[0]
    batch_id = exec_name.split('_')[1] if '_' in exec_name else 'unknown'
    data = json.loads(row[1])
    scores = data.get('scores', [])
    
    if batch_id not in batch_stats:
        batch_stats[batch_id] = {'total': 0, 'pass': 0, 'fail': 0}
    
    for score in scores:
        batch_stats[batch_id]['total'] += 1
        if score.get('score_value') in [True, 'true', 'True', 1, '1']:
            batch_stats[batch_id]['pass'] += 1
        else:
            batch_stats[batch_id]['fail'] += 1

for batch, stats in batch_stats.items():
    pass_rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
    print(f\"Batch {batch}: Total={stats['total']}, Pass={stats['pass']}, Fail={stats['fail']}, PassRate={pass_rate:.1f}%\")"

# Check scale score ranges and averages
docker exec violentutf_api python3 -c "
import sqlite3
import json
import statistics
conn = sqlite3.connect('/app/app_data/violentutf.db')
cursor = conn.cursor()
cursor.execute('SELECT results FROM orchestrator_executions WHERE results IS NOT NULL')
likert_scores = []
for row in cursor.fetchall():
    data = json.loads(row[0])
    for score in data.get('scores', []):
        if 'Likert' in score.get('scorer_class_name', ''):
            value = score.get('score_value')
            if isinstance(value, (int, float)):
                likert_scores.append(value)
                
if likert_scores:
    print(f\"Likert Scores - Count: {len(likert_scores)}, Min: {min(likert_scores)}, Max: {max(likert_scores)}, Avg: {statistics.mean(likert_scores):.2f}\")"

# Verify category preservation
docker exec violentutf_api python3 -c "
import sqlite3
import json
from collections import Counter
conn = sqlite3.connect('/app/app_data/violentutf.db')
cursor = conn.cursor()
cursor.execute('SELECT results FROM orchestrator_executions WHERE results IS NOT NULL')
categories = Counter()
for row in cursor.fetchall():
    data = json.loads(row[0])
    for score in data.get('scores', []):
        if 'Category' in score.get('scorer_class_name', ''):
            cat = score.get('score_category', 'unknown')
            categories[cat] += 1
            
print('Category Distribution:')
for cat, count in categories.most_common():
    print(f\"  {cat}: {count}\")"
```

This plan provides a structured approach to identifying and resolving scorer result inconsistencies. The phased implementation allows for systematic investigation while maintaining system stability.