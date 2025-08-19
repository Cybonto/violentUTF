# Report Setup - Data Selection Implementation (Updated)

## Overview

This updated implementation plan aligns with existing ViolentUTF patterns, reuses existing API endpoints where possible, and follows the authentication/routing architecture already in place.

## Key Learnings from Dashboard Analysis

### 1. Authentication Pattern
```python
# From Dashboard - Using jwt_manager for automatic token refresh
def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    token = jwt_manager.get_valid_token()
    
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json", 
        "X-API-Gateway": "APISIX"
    }
    
    # Add APISIX API key for AI model access
    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY")
    if apisix_api_key:
        headers["apikey"] = apisix_api_key
        
    return headers
```

### 2. API Request Pattern
```python
# Standard API request function from Dashboard
def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()
    response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    # ... error handling
```

### 3. Existing Endpoints We Can Reuse

From the Dashboard implementation, these endpoints are already available:

1. **Dashboard Summary** - `/api/v1/dashboard/summary`
   - Returns aggregated execution data
   - Includes filtering by days_back and test mode
   - Already handles user context

2. **Dashboard Scores** - `/api/v1/dashboard/scores`
   - Paginated score results
   - Supports filtering by execution_id
   - Includes metadata about scorers, generators, datasets

3. **Orchestrator Executions** - `/api/v1/orchestrators/executions`
   - List all executions
   - Can be filtered and paginated

4. **Execution Results** - `/api/v1/orchestrators/executions/{execution_id}/results`
   - Detailed results for specific execution

## Updated Implementation Plan

### 1. Backend Implementation

#### Option A: Extend Existing Dashboard Endpoints (Recommended)

Instead of creating entirely new endpoints, we can extend the dashboard endpoints with additional query parameters:

```python
# In app/api/endpoints/dashboard.py

@router.get("/browse", summary="Browse scan data for report generation")
async def browse_scan_data(
    start_date: datetime = Query(None, description="Start date filter"),
    end_date: datetime = Query(None, description="End date filter"),
    scanner_type: Optional[str] = Query(None, description="Scanner type filter"),
    orchestrator_types: Optional[List[str]] = Query(None, description="Orchestrator types filter"),
    target_models: Optional[List[str]] = Query(None, description="Target model filter"),
    min_severity: Optional[str] = Query(None, description="Minimum severity filter"),
    score_categories: Optional[List[str]] = Query(None, description="Score categories filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    include_test: bool = Query(False, description="Include test executions"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Browse available scan data with enhanced filtering for report generation"""
    # Implementation similar to get_dashboard_summary but with more filters
```

#### Option B: Create Report-Specific Endpoints

If we need report-specific functionality, create minimal new endpoints:

```python
# In app/api/endpoints/reports.py (new file)
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from datetime import datetime

router = APIRouter()

@router.post("/data/browse", summary="Browse scan data for reports")
async def browse_report_data(
    request: DataBrowseRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Browse scan data with report-specific enhancements"""
    # Internally call dashboard service but add report-specific logic
    from app.api.endpoints.dashboard import get_dashboard_scores
    
    # Reuse existing logic
    base_data = await get_dashboard_scores(
        days_back=30,
        page=request.page,
        page_size=request.page_size,
        include_test=request.include_test,
        db=db,
        current_user=current_user
    )
    
    # Add report-specific enhancements
    enhanced_data = enhance_for_reports(base_data, request)
    return enhanced_data
```

### 2. Route Configuration

Add report routes to APISIX by extending `configure_routes.sh`:

```bash
# Add to configure_routes.sh or create configure_report_routes.sh

# Report endpoints (if using Option B)
create_route "report-data-browse" "/api/v1/reports/data/browse" '["POST"]' "Report data browsing" 10
create_route "report-data-details" "/api/v1/reports/data/*" '["GET"]' "Report data details" 10
create_route "report-templates" "/api/v1/reports/templates/*" '["GET","POST","PUT","DELETE"]' "Report templates" 10
create_route "report-generate" "/api/v1/reports/generate" '["POST"]' "Report generation" 10
```

### 3. Frontend Implementation

#### Reuse Dashboard Patterns

```python
# In violentutf/pages/13_📊_Report_Setup.py

import streamlit as st
from utils.auth_utils import handle_authentication_and_sidebar
from utils.jwt_manager import jwt_manager

# Reuse API configuration from Dashboard
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080").rstrip("/api").rstrip("/")

API_ENDPOINTS = {
    # Reuse existing endpoints
    "dashboard_summary": f"{API_BASE_URL}/api/v1/dashboard/summary",
    "dashboard_scores": f"{API_BASE_URL}/api/v1/dashboard/scores",
    
    # Add report-specific endpoints (if Option B)
    "report_data_browse": f"{API_BASE_URL}/api/v1/reports/data/browse",
    "report_templates": f"{API_BASE_URL}/api/v1/reports/templates",
    "report_generate": f"{API_BASE_URL}/api/v1/reports/generate",
}

# Reuse authentication headers function
def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers - same as Dashboard"""
    token = jwt_manager.get_valid_token()
    # ... same implementation as Dashboard

# Reuse API request function
def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Make authenticated API request - same as Dashboard"""
    # ... same implementation as Dashboard
```

#### Data Browser Component

```python
@st.cache_data(ttl=60)  # Same caching strategy as Dashboard
def load_scan_data_for_reports(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load scan data using existing dashboard endpoints"""
    
    # Option A: Use dashboard endpoint with filters
    params = {
        "days_back": 30,  # Calculate from date range
        "include_test": filters.get("include_test", False),
        "page": 1,
        "page_size": 100
    }
    
    response = api_request("GET", API_ENDPOINTS["dashboard_scores"], params=params)
    
    # Process and filter client-side if needed
    if response:
        scores = response.get("scores", [])
        return filter_scores_for_reports(scores, filters)
    
    return []
```

### 4. OpenAPI Compliance

Ensure all new endpoints follow OpenAPI standards:

```python
# Pydantic models for OpenAPI documentation
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DataBrowseRequest(BaseModel):
    """Request model for browsing scan data"""
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    scanner_types: Optional[List[str]] = Field(None, description="Filter by scanner types")
    orchestrator_types: Optional[List[str]] = Field(None, description="Filter by orchestrator types")
    target_models: Optional[List[str]] = Field(None, description="Filter by target models")
    min_severity: Optional[str] = Field(None, description="Minimum severity level")
    score_categories: Optional[List[str]] = Field(None, description="Filter by score categories")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=200, description="Items per page")
    include_test: bool = Field(False, description="Include test executions")
    
    class Config:
        schema_extra = {
            "example": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "scanner_types": ["pyrit"],
                "orchestrator_types": ["RedTeamingOrchestrator"],
                "min_severity": "medium",
                "page": 1,
                "page_size": 50
            }
        }

class DataBrowseResponse(BaseModel):
    """Response model for scan data browsing"""
    results: List[ScanDataSummary]
    total_count: int
    page: int
    page_size: int
    has_more: bool
```

### 5. Integration with Existing Services

#### Reuse PyRIT Orchestrator Service

```python
# In report data service, reuse existing orchestrator service
from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service

async def get_execution_details_for_report(
    execution_id: str,
    user_context: str
) -> Dict[str, Any]:
    """Get execution details using existing service"""
    
    # Use existing service method
    execution = await pyrit_orchestrator_service.get_execution(
        execution_id,
        user_context
    )
    
    # Enhance for report needs
    if execution:
        # Add report-specific calculations
        execution["severity_distribution"] = calculate_severity_distribution(
            execution.get("scores", [])
        )
        execution["key_findings"] = extract_key_findings(
            execution.get("scores", [])
        )
    
    return execution
```

### 6. Summary of Changes

#### Minimal New Code Required:

1. **Backend**:
   - Option A: Add query parameters to existing dashboard endpoints
   - Option B: Create thin wrapper endpoints that reuse dashboard logic
   - Add to `app/api/routes.py` if creating new router

2. **Frontend**:
   - Reuse all authentication and API patterns from Dashboard
   - Use same caching strategy
   - Follow same error handling patterns

3. **Routing**:
   - Add routes to APISIX configuration
   - Follow existing route patterns with JWT validation

4. **Database**:
   - NO changes to existing tables
   - Read-only access to orchestrator_executions
   - Use existing user context filtering

This approach minimizes new code, maximizes reuse of existing patterns, and maintains consistency with the Dashboard implementation.

## Implementation Results (Completed)

### What Was Actually Implemented

We went with **Option A** - extending the dashboard endpoints. Here's what was done:

#### 1. Backend Changes

**New Browse Endpoint** (`/api/v1/dashboard/browse`):
- Created a POST endpoint that accepts DataBrowseRequest
- Used LEFT JOIN (outerjoin) to handle missing orchestrator configurations
- Fixed date filtering logic to match Dashboard behavior
- Made all advanced filters optional to handle minimal metadata

**Key Code Changes**:
```python
# Fixed JOIN to handle missing configs
.outerjoin(OrchestratorConfiguration, OrchestratorExecution.orchestrator_id == OrchestratorConfiguration.id)

# Fixed date filtering
end_date = request.end_date or datetime.utcnow()
start_date = request.start_date or (end_date - timedelta(days=30))

# Made filters flexible
if request.generators and scores:  # Only filter if data exists
    # ... filtering logic
```

#### 2. Frontend Changes

**Report Setup Page Updates**:
- Simplified filters to only include what works with current data
- Changed default date range to include today + 1 day
- Removed non-functional filters (generators, score categories)
- Added info message about current data limitations

#### 3. Schema Changes

**Created Pydantic Models**:
- `DataBrowseRequest`: Request model with optional filters
- `DataBrowseResponse`: Response with results and pagination
- `ScanDataSummary`: Summary of each scan execution

### Issues Encountered and Resolved

1. **INNER JOIN Problem**: Executions were excluded if orchestrator config was missing
   - **Solution**: Changed to LEFT JOIN

2. **Date Logic Error**: Incorrect date filtering when end_date not provided
   - **Solution**: Fixed to use consistent date range logic

3. **Date Boundary Issue**: Executions created today were excluded
   - **Solution**: Extended default end date to tomorrow

4. **Metadata Expectations**: Code expected rich metadata that didn't exist
   - **Solution**: Made all advanced filters optional

### Current Status

✅ **Data Selection Tab**: Fully functional
- Users can search and filter scan data
- Multi-selection works properly
- Results display correctly
- Pagination implemented

⏳ **Remaining Tabs**: Show "coming soon" placeholder
- Template Selection
- Configuration
- Preview
- Generate

### Lessons Learned

1. **Start with working code**: Dashboard worked, so we should have started by copying its exact patterns
2. **Check data reality**: Don't assume rich metadata exists
3. **Debug systematically**: Add logging at each stage to isolate issues
4. **Test edge cases**: Missing foreign keys, date boundaries, empty metadata

### Next Steps

1. Implement remaining tabs following the same patterns
2. Consider enriching scorer metadata for better filtering
3. Add comprehensive tests for edge cases
4. Document expected vs optional fields in scorer data