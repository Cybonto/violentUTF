# COB Endpoints Consolidation Analysis

## Current State

### `/api/v1/cob/` Endpoints
The `/api/v1/cob/` endpoints are currently only used in:
1. **cob_reports.py** - The endpoint definitions themselves
2. **setup_cob_cron.sh** - A cron job that calls `/api/v1/cob/internal/check-schedules`
3. **Documentation files** - Various planning and guide documents

### No External Usage Found
- No Streamlit pages use `/api/v1/cob/` endpoints
- The retired COB (Close of Business) Reports tab in Dashboard did NOT use these endpoints
- Only internal references within the cob_reports.py file itself

## Current Endpoint Structure

### `/api/v1/cob/` (cob_reports.py)
```
Templates:
- GET/POST /api/v1/cob/templates
- GET/PUT/DELETE /api/v1/cob/templates/{id}
- POST /api/v1/cob/templates/{id}/clone
- GET /api/v1/cob/templates/{id}/preview

Schedules:
- GET/POST /api/v1/cob/schedules
- GET/PUT/DELETE /api/v1/cob/schedules/{id}
- GET /api/v1/cob/schedules/{id}/executions

Reports:
- POST /api/v1/cob/reports/generate
- GET /api/v1/cob/reports
- GET /api/v1/cob/reports/{id}
- GET /api/v1/cob/reports/{id}/export/pdf

System:
- GET /api/v1/cob/system/status
- POST /api/v1/cob/internal/check-schedules

Export:
- POST /api/v1/cob/export
- GET /api/v1/cob/exports/{export_id}/status
- GET /api/v1/cob/exports/{export_id}/download
```

### `/api/v1/reports/` (reports.py)
```
Templates:
- POST /api/v1/reports/templates
- GET /api/v1/reports/templates
- GET /api/v1/reports/templates/search
- GET /api/v1/reports/templates/recommend
- GET/PUT/DELETE /api/v1/reports/templates/{id}
- POST /api/v1/reports/templates/{id}/validate
- GET /api/v1/reports/templates/{id}/variables
- POST /api/v1/reports/templates/initialize

Template Versions:
- POST /api/v1/reports/templates/{id}/versions
- GET /api/v1/reports/templates/{id}/versions
- POST /api/v1/reports/templates/{id}/versions/{version_id}/restore

Report Generation:
- POST /api/v1/reports/generate
- POST /api/v1/reports/preview
- GET /api/v1/reports/status/{report_id}
- GET /api/v1/reports/download/{report_id}/{format}
- GET /api/v1/reports/download/{report_id}
- POST /api/v1/reports/generate/batch

Data Browsing:
- POST /api/v1/reports/scan-data/browse

Block/Variable Management:
- GET /api/v1/reports/blocks
- GET /api/v1/reports/blocks/registry
- GET /api/v1/reports/variables
- GET /api/v1/reports/variables/categories
```

## Analysis

### Overlap and Differences

1. **Template Management**
   - Both have CRUD operations for templates
   - `/api/v1/reports/` has more features: search, recommend, validate, versioning
   - `/api/v1/cob/` has clone and preview operations

2. **Report Generation**
   - Both can generate reports
   - `/api/v1/reports/` has batch generation and multiple download formats
   - `/api/v1/cob/` has PDF-specific export

3. **Unique to `/api/v1/cob/`**
   - Schedule management (cron-based report generation)
   - System status endpoint
   - Internal check-schedules endpoint (used by cron)

4. **Unique to `/api/v1/reports/`**
   - Template versioning and restoration
   - Data browsing capabilities
   - Block and variable management
   - Multiple output formats

## Recommendation

### Option 1: Complete Consolidation (Recommended)
Merge `/api/v1/cob/` endpoints into `/api/v1/reports/` with the following structure:

```
/api/v1/reports/
├── templates/          # Existing + clone/preview from COB
├── schedules/          # Move from COB
├── generate/           # Existing
├── export/             # Move from COB
├── system/             # Move from COB
└── internal/           # Move from COB
```

**Advantages:**
- Single, unified API surface for all reporting needs
- Eliminates confusion between two similar endpoints
- Easier to maintain and document
- Better aligns with the Report Setup page requirements

**Implementation Steps:**
1. Copy schedule-related endpoints from cob_reports.py to reports.py
2. Copy export endpoints from cob_reports.py to reports.py
3. Copy system/internal endpoints from cob_reports.py to reports.py
4. Update cron job to use new endpoint path
5. Update route registration in routes.py
6. Remove cob_reports.py and its route registration

### Option 2: Keep Separate (Not Recommended)
Keep both endpoints but clarify their purposes:
- `/api/v1/reports/` - Interactive report generation
- `/api/v1/cob/` - Scheduled/automated reporting

**Disadvantages:**
- Maintains confusion with duplicate functionality
- Requires maintaining two similar codebases
- No clear benefit to separation

## Impact Assessment

### Breaking Changes
- **Cron Job**: Need to update `setup_cob_cron.sh` to use new endpoint
- **Documentation**: Update all references in documentation

### No Impact On
- Streamlit pages (none currently use `/api/v1/cob/`)
- Dashboard (already removed COB Reports tab)
- External integrations (none found)

## Conclusion

**Recommendation**: Proceed with Option 1 - Complete Consolidation

The `/api/v1/cob/` endpoints should be consolidated under `/api/v1/reports/` because:
1. No external code depends on the current `/api/v1/cob/` paths
2. Both serve the same purpose (report generation)
3. Consolidation eliminates naming confusion
4. Single API surface is easier to maintain and extend
5. The Report Setup page already uses `/api/v1/reports/`

The only required change is updating the cron job endpoint path, which is a trivial modification.
