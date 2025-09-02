# COB Systems Analysis

## Update (December 2024)

**The COB (Close of Business) Reports tab has been retired from the Dashboard.** All report functionality has been consolidated under the new Report Setup feature (`/violentutf/pages/13_📊_Report_Setup.py`). The COB (Configurable Output Block) system remains active as the underlying report generation engine.

## Summary of Findings

There are two separate systems using "COB" abbreviation:

### 1. COB (Close of Business) Reports - RETIRED ✓
- **Former Location**: Dashboard page - "COB Reports" tab
- **Purpose**: Daily operations reports for security teams at shift end
- **Status**: Removed from codebase
- **Migration**: Functionality replaced by Report Setup with scheduling features

### 2. COB (Configurable Output Block) - ACTIVE
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

## Current Status

### Completed Actions:
1. **Retired COB (Close of Business) Reports tab** from Dashboard
2. **Consolidated all endpoints** under `/api/v1/reports/`
3. **Implemented Report Setup page** with full template management
4. **Updated AI Analysis block** to use real data from generators

### API Structure:
- All report-related endpoints now use `/api/v1/reports/` prefix
- The Configurable Output Block system powers the backend
- No more confusion between the two COB systems
- Template management fully integrated in Report Setup

### Migration Path:
Users who previously used COB (Close of Business) Reports should:
1. Use the new Report Setup feature at "13_📊_Report_Setup"
2. Configure scheduling in the Configuration tab
3. Leverage templates for more flexible reporting
