# COB Systems Analysis

## Summary of Findings

There are two separate systems using "COB" abbreviation:

### 1. COB (Close of Business) Reports - To be retired
- **Location**: Dashboard page - "COB Reports" tab
- **Purpose**: Daily operations reports for security teams at shift end
- **Implementation**: 
  - UI: `/violentutf/pages/5_Dashboard.py` (lines 4100-5710)
  - Classes: `COBDataCollector`, `COBReportGenerator`
  - No dedicated API endpoints - uses existing orchestrator endpoints

### 2. COB (Configurable Output Block) - To be kept
- **Location**: FastAPI backend report system
- **Purpose**: Template-driven report generation system
- **API Base**: `/api/v1/cob/`
- **Implementation**:
  - Endpoints: `/violentutf_api/fastapi_app/app/api/endpoints/cob_reports.py`
  - Models: Uses COBTemplate, COBSchedule, COBReport schemas
  - Features: Templates, scheduling, PDF export

## API Endpoints Used

### Close of Business Reports (Dashboard Tab)
Uses existing orchestrator endpoints:
- `GET /api/v1/orchestrators` - List orchestrators
- `GET /api/v1/orchestrators/executions` - Get executions
- `GET /api/v1/orchestrators/executions/{id}/results` - Get execution results

No dedicated COB endpoints - generates reports client-side.

### Configurable Output Block System
Dedicated endpoints under `/api/v1/cob/`:
- Templates:
  - `GET/POST /api/v1/cob/templates`
  - `GET/PUT/DELETE /api/v1/cob/templates/{id}`
- Schedules:
  - `GET/POST /api/v1/cob/schedules`
  - `GET/PUT/DELETE /api/v1/cob/schedules/{id}`
- Reports:
  - `GET/POST /api/v1/cob/reports`
  - `GET /api/v1/cob/reports/{id}/export/pdf`
- System:
  - `GET /api/v1/cob/system/status`

## Confusion Points

1. **Same abbreviation**: Both systems use "COB" but mean different things
2. **Different purposes**: 
   - Close of Business = shift handover reports
   - Configurable Output Block = flexible report templates
3. **Different architectures**:
   - Close of Business = client-side generation
   - Configurable Output Block = server-side with database

## Recommendation

For the Report Setup page:
- We should use the `/api/v1/reports/` endpoints (not `/api/v1/cob/`)
- These use the Configurable Output Block system internally
- Avoids confusion with the Close of Business reports
- Already has template management, which is what we need

The `/api/v1/reports/templates` endpoints are the right choice for the Template Selection tab.