# Troubleshooting Report Generation

## Overview

This guide helps resolve common issues encountered when using the Report Setup and generation features in ViolentUTF.

## Common Issues and Solutions

### 1. API Connection Issues

#### Problem: "Resource not found" error
**Symptoms:**
- Error message: "Resource not found: http://localhost:9080/api/v1/reports/..."
- API calls failing with 404 errors

**Solutions:**
1. Check APISIX routes are configured:
   ```bash
   cd apisix && ./verify_routes.sh
   ```
2. If routes are missing, run:
   ```bash
   cd apisix && ./configure_routes.sh
   ```
3. Verify the service is running:
   ```bash
   ./check_services.sh
   ```

#### Problem: 401 Unauthorized errors
**Symptoms:**
- API calls rejected with 401 status
- "Invalid or expired token" messages

**Solutions:**
1. Ensure you're logged in through Keycloak
2. Check JWT token expiration
3. Clear browser cache and re-authenticate
4. Verify Keycloak service is running

### 2. Template Issues

#### Problem: No templates showing after initialization
**Symptoms:**
- Empty template list despite clicking "Initialize Default Templates"
- Templates created but not visible

**Solutions:**
1. Check database connection:
   ```bash
   docker exec -it violentutf-postgres psql -U postgres -d violentutf -c "SELECT COUNT(*) FROM report_templates;"
   ```
2. Verify API response:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:9080/api/v1/reports/templates
   ```
3. Check for filter conflicts (e.g., scanner_type filter with no matching templates)

#### Problem: Template compatibility errors
**Symptoms:**
- "Template not compatible with selected data" message
- Templates grayed out in selection

**Solutions:**
1. Ensure selected scan data matches template requirements
2. Check template's `scanner_compatibility` field
3. Verify data has required fields (e.g., severity data for security templates)

### 3. Configuration Tab Issues

#### Problem: AI Model dropdown is empty
**Symptoms:**
- No options in AI Model selection
- Dropdown shows "Loading..." indefinitely

**Solutions:**
1. Verify generator service is accessible:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:9080/api/v1/generators
   ```
2. Check generators are configured in the system
3. Ensure the generator service container is running
4. Look for errors in API logs:
   ```bash
   docker logs violentutf-api --tail 100
   ```

#### Problem: Configuration not saving
**Symptoms:**
- Settings revert after saving
- "Failed to save configuration" error

**Solutions:**
1. Check for validation errors in browser console
2. Ensure all required fields are filled
3. Verify JSON schema compliance for block configs
4. Check API logs for detailed error messages

### 4. Data Selection Issues

#### Problem: No scan data available
**Symptoms:**
- Empty results in Data Selection tab
- "No scans found" message

**Solutions:**
1. Verify PyRIT/Garak executions exist in the database
2. Check date range filters aren't too restrictive
3. Ensure user has permissions to view scan data
4. Run a test scan to generate data:
   ```python
   # From the Orchestrator page, run a simple scan
   ```

#### Problem: Data filtering not working
**Symptoms:**
- Filters don't affect results
- All data shown regardless of filters

**Solutions:**
1. Clear all filters and reapply one at a time
2. Check for conflicting filter combinations
3. Verify date format is correct (ISO 8601)
4. Ensure severity levels match your data

### 5. Generation Issues

#### Problem: Report generation fails
**Symptoms:**
- "Generation failed" error
- Process starts but never completes

**Solutions:**
1. Check AI service availability (for AI Analysis blocks)
2. Verify sufficient system resources
3. Look for timeout errors in logs
4. Try with a smaller dataset first
5. Disable AI Analysis block temporarily to isolate issues

#### Problem: Generated report is empty
**Symptoms:**
- PDF/JSON files are created but contain no data
- Only template structure without content

**Solutions:**
1. Verify selected scan data is accessible
2. Check block configurations are valid
3. Ensure data matches template requirements
4. Review generation logs for data retrieval errors

### 6. Performance Issues

#### Problem: Slow page loading
**Symptoms:**
- Configuration tab takes long to load
- Template selection is sluggish

**Solutions:**
1. Check database query performance
2. Verify API response times
3. Clear browser cache
4. Reduce number of concurrent API calls
5. Check system resource usage

#### Problem: Report generation timeout
**Symptoms:**
- Generation fails after extended time
- Timeout errors in logs

**Solutions:**
1. Increase timeout settings in configuration
2. Reduce report complexity (fewer blocks)
3. Process smaller data batches
4. Check AI model response times
5. Optimize database queries

## Diagnostic Commands

### Check Service Health
```bash
# Overall system health
./check_services.sh

# Individual service logs
docker logs violentutf-api --tail 100
docker logs violentutf-streamlit --tail 100
docker logs violentutf-apisix --tail 100

# Database connection
docker exec -it violentutf-postgres psql -U postgres -d violentutf
```

### API Testing
```bash
# Test authentication
curl -X POST http://localhost:9080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# Test report endpoints (replace $TOKEN)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9080/api/v1/reports/templates

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9080/api/v1/reports/blocks/registry
```

### Database Queries
```sql
-- Check templates
SELECT id, name, category, type FROM report_templates;

-- Check for UUID issues
SELECT id, name FROM report_templates WHERE id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- View block configurations
SELECT name, blocks::text FROM report_templates LIMIT 1;
```

## Error Code Reference

| Error Code | Description | Solution |
|------------|-------------|----------|
| `TEMPLATE_NOT_FOUND` | Template ID doesn't exist | Verify template ID, reinitialize templates |
| `INVALID_UUID` | Malformed UUID in request | Check ID format, use valid UUID |
| `GENERATOR_NOT_FOUND` | AI model/generator not available | Configure generators, check service |
| `DATA_ACCESS_DENIED` | No permission for scan data | Verify user permissions |
| `SCHEMA_VALIDATION_FAILED` | Block config doesn't match schema | Review schema requirements |
| `AI_SERVICE_TIMEOUT` | AI analysis timed out | Increase timeout, check AI service |

## Prevention Tips

1. **Regular Maintenance**
   - Keep services updated
   - Monitor resource usage
   - Clean up old scan data
   - Archive completed reports

2. **Configuration Best Practices**
   - Save working configurations as templates
   - Test with small datasets first
   - Use appropriate AI models for your needs
   - Enable only necessary report blocks

3. **Monitoring**
   - Set up alerts for service failures
   - Monitor API response times
   - Track report generation success rates
   - Review error logs regularly

## Getting Help

If issues persist:

1. **Check Logs**: Always review service logs first
2. **Documentation**: Refer to guides in `/docs/guides/`
3. **GitHub Issues**: Report bugs at https://github.com/anthropics/claude-code/issues
4. **Community**: Ask in the ViolentUTF community forums

Include the following when reporting issues:
- Error messages and codes
- Steps to reproduce
- Service versions
- Relevant log excerpts
- System configuration
