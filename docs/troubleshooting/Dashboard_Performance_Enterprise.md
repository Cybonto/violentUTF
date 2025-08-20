# Dashboard Performance Issues in Enterprise Environments

## Issue Description
When running ViolentUTF in enterprise environments with large datasets (7000+ prompts), the Dashboard may experience:
- Slow loading times
- 500 Internal Server errors from the API
- "No scorer executions found" message despite having data

## Root Cause
The original Dashboard implementation made cascading API calls:
1. Get ALL orchestrators
2. For EACH orchestrator → Get ALL executions
3. For EACH execution → Get ALL results/scores

With thousands of prompts, this creates hundreds of API calls causing timeouts and server errors.

## Solutions Implemented

### 1. New Optimized API Endpoints
Created dedicated Dashboard endpoints that consolidate data retrieval:

**New endpoints added:**
- `/api/v1/dashboard/summary` - Get aggregated execution data in one call
- `/api/v1/dashboard/scores` - Get paginated score results

**Benefits:**
- Reduces API calls from O(n²) to O(1)
- Server-side data aggregation
- Built-in pagination support
- Respects execution type filters

### 2. Dashboard Code Updates
The Dashboard now:
- Uses optimized endpoints by default
- Falls back to legacy method if new endpoints aren't available
- Implements proper error handling
- Supports pagination for large datasets

### 3. API Pagination
Added pagination to the orchestrator list endpoint:
- Default limit: 100 orchestrators
- Configurable via query parameters
- Consistent ordering for reliable pagination

## Applying the Fixes

### For New Deployments
The fixes are already included. No action needed.

### For Existing Deployments

1. **Update the API container:**
   ```bash
   docker-compose -f apisix/docker-compose.yml build violentutf_api
   docker-compose -f apisix/docker-compose.yml up -d violentutf_api
   ```

2. **Clear Dashboard cache:**
   - In the Dashboard, click the menu (⋮) in the top right
   - Select "Clear cache"
   - Refresh the page

3. **Verify the fix:**
   ```bash
   # Check if new endpoints are available
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:9080/api/v1/dashboard/summary?days_back=7
   ```

## Performance Tuning

### For Very Large Datasets (10,000+ scores)

1. **Adjust page size in Dashboard code:**
   ```python
   # In load_dashboard_data_optimized function
   page_size = 1000  # Increase from 500 if your server can handle it
   ```

2. **Enable result caching:**
   ```python
   # Increase cache TTL for stable data
   @st.cache_data(ttl=300)  # 5 minutes instead of 1
   ```

3. **Database indexing (if not already present):**
   ```sql
   -- For SQLite
   CREATE INDEX idx_orchestrator_execution_created_at
   ON orchestrator_executions(created_at);

   CREATE INDEX idx_orchestrator_execution_status
   ON orchestrator_executions(status);
   ```

### For Limited Memory Environments

1. **Reduce batch size:**
   ```python
   page_size = 100  # Smaller batches
   ```

2. **Enable streaming results:**
   Set environment variable:
   ```bash
   DASHBOARD_STREAMING_MODE=true
   ```

## Monitoring Dashboard Performance

### Check API response times:
```bash
# Monitor API endpoint performance
docker logs violentutf_api --tail 100 | grep "dashboard" | grep "ms"
```

### Database query performance:
```bash
# Check slow queries
docker exec violentutf_api sqlite3 /app/app_data/violentutf.db \
  "SELECT sql, COUNT(*) as count, AVG(elapsed) as avg_ms
   FROM query_log
   WHERE elapsed > 1000
   GROUP BY sql
   ORDER BY avg_ms DESC;"
```

## Troubleshooting

### Issue: Still getting 500 errors
1. Check API memory usage:
   ```bash
   docker stats violentutf_api
   ```

2. Increase container memory if needed:
   ```yaml
   # In docker-compose.yml
   services:
     violentutf_api:
       mem_limit: 4g  # Increase from default
   ```

### Issue: Dashboard shows old data
1. Clear Streamlit cache:
   - Click menu (⋮) → Clear cache

2. Clear browser cache:
   - Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

### Issue: Partial data loading
Check execution type filter:
- Default is "Full Only" which excludes test executions
- Change to "All Executions" to see everything

## Prevention

### Best Practices for Large Datasets

1. **Use batch executions wisely:**
   - Limit batch size to 100-500 prompts
   - Run multiple smaller batches instead of one large batch

2. **Regular cleanup:**
   ```bash
   # Archive old executions
   ./scripts/archive_old_executions.sh --days 30
   ```

3. **Monitor growth:**
   ```bash
   # Check database size
   du -h violentutf_api/fastapi_app/app_data/violentutf.db
   du -h violentutf/app_data/violentutf/*.db
   ```

## Related Documentation
- [Data Storage Locations Guide](../guides/Guide_Data_Storage_Locations.md)
- [Enterprise Duplicate AppData Fix](./Enterprise_Duplicate_AppData_Fix.md)
- [Scorer Inconsistency Investigation Report](./Scorer_Inconsistency_Investigation_Report.md)
