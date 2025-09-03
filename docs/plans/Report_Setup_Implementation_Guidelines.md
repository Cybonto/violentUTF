# Report Setup Implementation Guidelines

## Architecture Patterns to Follow

### 1. Authentication & Authorization

**Pattern from Dashboard:**
```python
# Always use jwt_manager for token management
from utils.jwt_manager import jwt_manager

def get_auth_headers() -> Dict[str, str]:
    token = jwt_manager.get_valid_token()  # Handles refresh automatically

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-API-Gateway": "APISIX"  # Required header
    }

    # Add APISIX API key if available
    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY")
    if apisix_api_key:
        headers["apikey"] = apisix_api_key

    return headers
```

**Key Points:**
- All API requests MUST go through APISIX Gateway (port 9080)
- Never call FastAPI directly (port 8000)
- JWT tokens are validated by APISIX before reaching FastAPI
- User context is automatically extracted from JWT

### 2. API Endpoint Structure

**Existing Structure:**
```
/api/v1/
├── auth/           # Authentication
├── dashboard/      # Dashboard data
├── orchestrators/  # PyRIT orchestrator management
├── scorers/        # Scorer configuration
├── generators/     # Generator configuration
├── datasets/       # Dataset management
├── cob/           # COB reports (existing)
└── reports/       # NEW: Advanced reports
```

**New Report Endpoints:**
```python
# In app/api/endpoints/reports.py
router = APIRouter()

# Follow OpenAPI standards with proper models
@router.post("/data/browse", response_model=DataBrowseResponse)
@router.get("/templates", response_model=List[TemplateResponse])
@router.post("/generate", response_model=GenerationJobResponse)
```

### 3. APISIX Routing

**Add to Route Configuration:**
```bash
# In configure_routes.sh or new configure_report_routes.sh

# Report endpoints with proper priority
create_route "report-api" "/api/v1/reports/*" \
    '["GET","POST","PUT","DELETE","OPTIONS"]' \
    "Report Setup API endpoints" \
    10  # Priority
```

**Route Requirements:**
- All routes must be registered with APISIX
- Use wildcard patterns for flexibility
- Set appropriate priority (10 for specific routes)
- Include CORS headers
- Enable JWT validation plugin

### 4. Database Access Patterns

**Read-Only Access to Existing Data:**
```python
# Always use async sessions
from app.db.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession

async def get_execution_data(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # User context filtering is automatic
    stmt = select(OrchestratorExecution).where(
        OrchestratorExecution.user_context == current_user.username
    )
```

**New Tables (Separate Migration):**
```python
# Only create new tables, never modify existing ones
class ReportTemplate(Base):
    __tablename__ = "report_templates"  # New table
    # ... fields
```

### 5. Frontend Patterns

**Streamlit Page Structure:**
```python
# Standard imports
import streamlit as st
from utils.auth_utils import handle_authentication_and_sidebar
from utils.jwt_manager import jwt_manager

# Page config
st.set_page_config(
    page_title="Report Setup",
    page_icon="📊",
    layout="wide"
)

# Authentication check
username = handle_authentication_and_sidebar()
if not username:
    st.stop()

# API configuration (reuse pattern)
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = API_BASE_URL.rstrip("/api").rstrip("/")
```

**Caching Strategy:**
```python
# Use same caching as Dashboard
@st.cache_data(ttl=60)  # 1-minute cache
def load_data_with_cache(params: Dict) -> List[Dict]:
    return api_request("GET", endpoint, params=params)
```

### 6. Error Handling

**Consistent Error Pattern:**
```python
def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    try:
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"API Error {response.status_code}: {url}")

            # User-friendly error in Streamlit
            if response.status_code == 401:
                st.error("🔐 Authentication expired. Please refresh the page.")
            elif response.status_code == 403:
                st.error("🚫 Access denied.")
            else:
                st.error(f"❌ API Error: {response.status_code}")

            return None
    except Exception as e:
        logger.error(f"Request failed: {e}")
        st.error("❌ Connection error. Please check if services are running.")
        return None
```

### 7. Data Flow

**Existing Data Access:**
```
Streamlit → APISIX Gateway → FastAPI → Database
    ↓           ↓                ↓
  JWT Token   Validate      User Context
              & Route        Filtering
```

**Report Generation Flow:**
```
1. Browse Data (reuse dashboard endpoints)
2. Select Template (new report_templates table)
3. Configure (in-memory)
4. Generate (background job)
5. Download (file storage)
```

### 8. Service Integration

**Reuse Existing Services:**
```python
# In new report services
from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service
from app.api.endpoints.dashboard import get_dashboard_scores

# Build on existing functionality
async def get_report_data(params):
    # Reuse dashboard logic
    base_data = await get_dashboard_scores(...)

    # Add report-specific enhancements
    return enhance_for_reports(base_data)
```

### 9. Testing Approach

**API Testing:**
```python
# Test through APISIX like real clients
def test_report_endpoints():
    headers = {"Authorization": f"Bearer {test_token}"}
    response = requests.get(
        "http://localhost:9080/api/v1/reports/templates",
        headers=headers
    )
    assert response.status_code == 200
```

**Frontend Testing:**
```python
# Manual testing checklist
- [ ] Authentication works
- [ ] Data loads properly
- [ ] Filters apply correctly
- [ ] Navigation between tabs
- [ ] Error states handled
```

### 10. Development Workflow

1. **Backend First:**
   - Create/extend API endpoints
   - Add OpenAPI models
   - Test with curl/Postman through APISIX

2. **Update Routes:**
   - Add to configure_routes.sh
   - Run route configuration
   - Verify with verify_routes.sh

3. **Frontend Development:**
   - Follow Dashboard patterns
   - Use existing utilities
   - Test with real data

4. **Integration Testing:**
   - Test full flow through APISIX
   - Verify JWT handling
   - Check user context isolation

## Common Pitfalls to Avoid

1. **DON'T** call FastAPI directly - always use APISIX
2. **DON'T** modify existing database tables
3. **DON'T** create new authentication mechanisms
4. **DON'T** bypass user context filtering
5. **DON'T** hardcode API URLs or tokens

## Checklist for New Features

- [ ] API endpoint follows OpenAPI standards
- [ ] Route added to APISIX configuration
- [ ] Authentication uses jwt_manager
- [ ] Database queries filter by user context
- [ ] Frontend follows Dashboard patterns
- [ ] Error handling is consistent
- [ ] Caching strategy implemented
- [ ] No breaking changes to existing code
- [ ] Documentation updated
- [ ] Tested through APISIX Gateway
