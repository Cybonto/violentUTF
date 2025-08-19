# Advanced Dashboard Report Setup - Revised Implementation Plan

## Executive Summary

This revised implementation plan organizes the Report Setup feature development around the tab-based UI structure, emphasizes real data usage (no mocks), and includes careful migration strategies to avoid breaking existing systems.

## Tab-Based Feature Organization

### 1. Data Selection Tab (First Implementation Priority)

#### 1.1 Purpose
Enable users to browse and select real scan data from PyRIT and Garak executions for report generation.

#### 1.2 Data Sources
- **PyRIT Data**: Access via existing orchestrator_executions table and DuckDB memory
- **Garak Data**: Access via garak scan results stored in the system
- **Compatibility Matrix Results**: Leverage existing dashboard data structures

#### 1.3 Implementation Components

##### Backend Services
```python
# Data Browsing Service
class ScanDataBrowserService:
    """Browse and aggregate scan data from multiple sources"""
    
    async def browse_pyrit_data(
        self,
        user_context: str,
        filters: Dict[str, Any],
        pagination: PaginationParams
    ) -> List[PyRITScanSummary]:
        """Query orchestrator_executions and aggregate results"""
        
    async def browse_garak_data(
        self,
        user_context: str,
        filters: Dict[str, Any],
        pagination: PaginationParams
    ) -> List[GarakScanSummary]:
        """Query garak scan results"""
        
    async def get_scan_details(
        self,
        scan_id: str,
        scan_type: str
    ) -> ScanDetails:
        """Get detailed information about a specific scan"""
```

##### API Endpoints
```python
# New endpoints under /api/v1/report-setup/
@router.post("/data/browse")
async def browse_scan_data(
    request: DataBrowseRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
) -> DataBrowseResponse:
    """Browse available scan data with filters"""

@router.get("/data/{scan_type}/{scan_id}")
async def get_scan_details(
    scan_type: str,
    scan_id: str,
    current_user = Depends(get_current_user)
) -> ScanDetailsResponse:
    """Get detailed scan information"""
```

##### Frontend Implementation
- **Scan Browser Component**: Grid/list view with filtering
- **Filter Panel**: Scanner type, date range, model, severity
- **Scan Preview**: Expandable details showing key metrics
- **Selection Management**: Multi-select with visual feedback

### 2. Template Selection Tab

#### 2.1 Purpose
Provide intelligent template recommendations based on selected scan data and allow manual template selection.

#### 2.2 Template Categories
- **Security Assessment Templates**: For vulnerability analysis
- **Safety Evaluation Templates**: For toxicity and bias testing
- **Compliance Reports**: For framework alignment
- **Custom Analysis**: User-defined templates

#### 2.3 Implementation Components

##### Template Recommendation Engine
```python
class TemplateRecommendationEngine:
    """Recommend templates based on scan data characteristics"""
    
    def analyze_scan_data(
        self,
        selected_scans: List[ScanSummary]
    ) -> DataCharacteristics:
        """Analyze selected data to determine characteristics"""
        
    def recommend_templates(
        self,
        characteristics: DataCharacteristics,
        user_preferences: Optional[Dict]
    ) -> List[TemplateRecommendation]:
        """Generate template recommendations with scores"""
```

##### Template Storage
```python
# New template model extending existing COBTemplate
class ReportTemplate(Base):
    __tablename__ = "report_templates"
    
    id = Column(UUID, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    
    # Template structure
    blocks = Column(JSON)  # Block configuration
    variables = Column(JSON)  # Required variables
    
    # Metadata for recommendations
    data_requirements = Column(JSON)  # What data the template needs
    scoring_categories = Column(JSON)  # Which score types it handles
    
    # Versioning
    version = Column(String(20), default="1.0.0")
    parent_version_id = Column(UUID, nullable=True)
    
    # Audit
    created_by = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 3. Configuration Tab

#### 3.1 Purpose
Allow users to configure report parameters, AI settings, and output formats.

#### 3.2 Configuration Options
- **Report Metadata**: Title, description, period
- **AI Analysis Settings**: Provider, model, prompts
- **Output Formats**: PDF, JSON, Markdown (multi-select)
- **Block-specific Settings**: Per-block configuration

#### 3.3 Implementation Components

##### Configuration Schema
```python
class ReportConfiguration(BaseModel):
    # Basic settings
    title: str
    description: Optional[str]
    report_period: DateRange
    
    # AI settings
    ai_provider: str = "openai"
    ai_model: str = "gpt-4"
    analysis_depth: str = "standard"  # quick, standard, detailed
    
    # Output settings
    formats: List[str] = ["pdf", "json"]
    pdf_style: str = "professional"
    
    # Block configurations
    block_configs: Dict[str, Dict[str, Any]]
    
    # Advanced options
    include_raw_data: bool = False
    anonymize_data: bool = False
```

### 4. Preview Tab

#### 4.1 Purpose
Generate and display a preview of the report before final generation.

#### 4.2 Preview Features
- **Live Preview**: Real-time preview with sample data
- **Block Preview**: Preview individual blocks
- **Variable Resolution**: Show resolved variables
- **Format Preview**: Preview different output formats

#### 4.3 Implementation Components

##### Preview Engine
```python
class ReportPreviewEngine:
    """Generate report previews with partial data"""
    
    async def generate_preview(
        self,
        template: ReportTemplate,
        config: ReportConfiguration,
        sample_data: Dict[str, Any],
        preview_blocks: Optional[List[str]] = None
    ) -> PreviewResult:
        """Generate preview with sample or partial data"""
```

### 5. Generate Tab

#### 5.1 Purpose
Execute report generation with progress tracking and multi-format output.

#### 5.2 Generation Pipeline
1. Data aggregation from selected scans
2. Template processing with variable substitution
3. AI analysis execution (if configured)
4. Multi-format rendering
5. Output delivery

#### 5.3 Implementation Components

##### Report Generation Service
```python
class ReportGenerationService:
    """Orchestrate report generation process"""
    
    async def generate_report(
        self,
        template_id: str,
        scan_data_ids: List[str],
        configuration: ReportConfiguration,
        user_context: str
    ) -> ReportGenerationResult:
        """Generate report with progress tracking"""
        
    async def track_progress(
        self,
        job_id: str
    ) -> GenerationProgress:
        """Get real-time generation progress"""
```

### 6. Template Management Tab

#### 6.1 Purpose
Create, edit, version, and organize report templates.

#### 6.2 Management Features
- **Template Editor**: Visual block-based editor
- **Version Control**: Simple versioning system
- **Template Gallery**: Browse and search templates
- **Import/Export**: Share templates

#### 6.3 Implementation Components

##### Template Editor
```python
class TemplateEditorService:
    """Manage template creation and editing"""
    
    async def create_template(
        self,
        template_data: TemplateCreate,
        user_id: str
    ) -> ReportTemplate:
        """Create new template with validation"""
        
    async def create_version(
        self,
        template_id: str,
        changes: TemplateUpdate,
        version_type: str  # major, minor, patch
    ) -> ReportTemplate:
        """Create new version of template"""
```

## Database Migration Strategy

### 1. Migration Principles
- **Zero Downtime**: Migrations must not break existing functionality
- **Backward Compatible**: Support existing data structures
- **Incremental**: Add new tables/columns without modifying existing ones
- **Reversible**: Include rollback procedures

### 2. Migration Implementation

#### 2.1 New Tables (Safe to Add)
```sql
-- Report templates table (new)
CREATE TABLE IF NOT EXISTS report_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    blocks JSONB NOT NULL,
    variables JSONB,
    data_requirements JSONB,
    scoring_categories JSONB,
    version VARCHAR(20) DEFAULT '1.0.0',
    parent_version_id UUID REFERENCES report_templates(id),
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Report generation jobs (new)
CREATE TABLE IF NOT EXISTS report_generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES report_templates(id),
    configuration JSONB NOT NULL,
    scan_data_ids JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    results JSONB,
    error_details JSONB,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Generated reports (new)
CREATE TABLE IF NOT EXISTS generated_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES report_generation_jobs(id),
    template_id UUID REFERENCES report_templates(id),
    title VARCHAR(500),
    formats JSONB,
    file_paths JSONB,
    metadata JSONB,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2 Migration Script
```python
# migrations/add_report_setup_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add report setup tables"""
    
    # Create new tables
    op.create_table(
        'report_templates',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        # ... other columns
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes
    op.create_index('idx_report_templates_category', 'report_templates', ['category'])
    op.create_index('idx_report_templates_created_by', 'report_templates', ['created_by'])

def downgrade():
    """Remove report setup tables"""
    op.drop_table('generated_reports')
    op.drop_table('report_generation_jobs')
    op.drop_table('report_templates')
```

### 3. Setup Script Updates

#### 3.1 Conditional Migration
```bash
# In setup script, check if tables exist before running migration
check_report_tables() {
    # Check if report_templates table exists
    table_exists=$(docker exec -i violentutf-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='report_templates'")
    
    if [ -z "$table_exists" ]; then
        echo "Running report setup migration..."
        docker exec -i violentutf-api python -m alembic upgrade head
    else
        echo "Report tables already exist, skipping migration"
    fi
}
```

#### 3.2 Feature Flag for Gradual Rollout
```python
# In config.py
REPORT_SETUP_ENABLED = os.getenv("REPORT_SETUP_ENABLED", "false").lower() == "true"

# In Streamlit navigation
if settings.REPORT_SETUP_ENABLED:
    pages.append("13_📊_Report_Setup.py")
```

## Documentation Updates

### 1. Documentation Structure
```
docs/
├── plans/
│   └── Report_Setup_Implementation_Plan_Revised.md (this file)
├── guides/
│   ├── Guide_Report_Setup_Overview.md
│   ├── Guide_Report_Template_Creation.md
│   ├── Guide_Report_Generation.md
│   └── Guide_Report_Scheduling.md
├── api/
│   └── API_Report_Setup_Endpoints.md
└── troubleshooting/
    └── Troubleshooting_Report_Generation.md
```

### 2. Documentation Timeline
- **Phase 1**: Update API documentation as endpoints are created
- **Phase 2**: Create user guides during UI implementation
- **Phase 3**: Add troubleshooting guides based on testing
- **Phase 4**: Create video tutorials for complex features

## Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
1. Database schema and migrations
2. Base API structure
3. Core service classes
4. Basic Streamlit page structure

### Phase 2: Data Selection (Weeks 5-6)
1. Data browsing service implementation
2. API endpoints for data access
3. Frontend data browser UI
4. Integration with existing PyRIT/Garak data

### Phase 3: Template System (Weeks 7-10)
1. Template data model
2. Template recommendation engine
3. Template editor backend
4. Template gallery UI
5. Version control implementation

### Phase 4: Report Generation (Weeks 11-14)
1. Report generation pipeline
2. Block processing system
3. AI integration
4. Multi-format output
5. Progress tracking

### Phase 5: Advanced Features (Weeks 15-18)
1. Preview functionality
2. Scheduling system
3. Export and distribution
4. Performance optimization

### Phase 6: Polish and Testing (Weeks 19-20)
1. UI/UX refinements
2. Integration testing
3. Performance testing
4. Documentation completion

## Risk Mitigation

### 1. Database Risks
- **Risk**: Breaking existing tables
- **Mitigation**: Only add new tables, never modify existing ones
- **Validation**: Run migration tests on copy of production database

### 2. Performance Risks
- **Risk**: Report generation blocking API
- **Mitigation**: Async processing with background jobs
- **Monitoring**: Add performance metrics from day one

### 3. Integration Risks
- **Risk**: PyRIT/Garak API changes
- **Mitigation**: Abstract data access layer
- **Testing**: Comprehensive integration tests

## Success Criteria

1. **Functional**: All 6 tabs fully operational with real data
2. **Performance**: Report generation < 30 seconds for standard reports
3. **Reliability**: No impact on existing dashboard functionality
4. **Usability**: Intuitive UI requiring minimal training
5. **Scalability**: Support 100+ concurrent users
