# Report Setup Implementation Details

## Detailed Tab Implementations

### 1. Data Selection Tab - Detailed Implementation

#### 1.1 Backend Data Access Layer

```python
# app/services/report_setup/data_access_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

class ReportDataAccessService:
    """Unified data access for report generation"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pyrit_memory = PyRITMemoryAccess()  # DuckDB access

    async def browse_orchestrator_executions(
        self,
        user_context: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        orchestrator_types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Browse PyRIT orchestrator executions with filtering"""

        # Default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Query orchestrator_executions table
        query = select(OrchestratorExecution).where(
            and_(
                OrchestratorExecution.user_context == user_context,
                OrchestratorExecution.created_at.between(start_date, end_date),
                OrchestratorExecution.status == 'completed'
            )
        )

        if orchestrator_types:
            query = query.where(
                OrchestratorExecution.orchestrator_name.in_(orchestrator_types)
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.db.scalar(count_query)

        # Apply pagination
        query = query.order_by(OrchestratorExecution.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        executions = result.scalars().all()

        # Enrich with PyRIT memory data
        enriched_executions = []
        for execution in executions:
            # Get score details from DuckDB
            scores = await self.pyrit_memory.get_execution_scores(
                execution.execution_id
            )

            enriched_executions.append({
                "execution_id": execution.execution_id,
                "orchestrator_name": execution.orchestrator_name,
                "target_model": execution.target_model,
                "created_at": execution.created_at,
                "duration": execution.duration,
                "total_prompts": execution.prompt_count,
                "score_summary": self._summarize_scores(scores),
                "severity_distribution": self._calculate_severity_distribution(scores),
                "key_findings": self._extract_key_findings(scores)
            })

        return {
            "executions": enriched_executions,
            "total_count": total_count,
            "has_more": (offset + limit) < total_count
        }

    def _summarize_scores(self, scores: List[Dict]) -> Dict[str, Any]:
        """Create summary statistics from scores"""
        if not scores:
            return {
                "total_scores": 0,
                "avg_score": 0,
                "max_score": 0,
                "categories": {}
            }

        # Group by score category
        categories = {}
        for score in scores:
            category = score.get("score_category", "other")
            if category not in categories:
                categories[category] = {
                    "count": 0,
                    "total": 0,
                    "max": 0
                }

            score_value = float(score.get("score_value", 0))
            categories[category]["count"] += 1
            categories[category]["total"] += score_value
            categories[category]["max"] = max(categories[category]["max"], score_value)

        # Calculate averages
        for category in categories.values():
            category["average"] = category["total"] / category["count"] if category["count"] > 0 else 0

        return {
            "total_scores": len(scores),
            "avg_score": sum(float(s.get("score_value", 0)) for s in scores) / len(scores),
            "max_score": max(float(s.get("score_value", 0)) for s in scores),
            "categories": categories
        }
```

#### 1.2 Frontend Data Browser Component

```python
# violentutf/pages/components/data_browser.py
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class ScanDataBrowser:
    """Component for browsing and selecting scan data"""

    def __init__(self, api_client):
        self.api_client = api_client
        self.selected_scans = st.session_state.get("selected_scans", [])

    def render(self):
        """Render the data browser interface"""
        st.header("Select Scan Data")

        # Filters section
        with st.expander("🔍 Filters", expanded=True):
            self._render_filters()

        # Search button
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔄 Search", type="primary", use_container_width=True):
                self._search_data()
        with col2:
            if st.button("🗑️ Clear Selection", use_container_width=True):
                self._clear_selection()

        # Results section
        if "scan_results" in st.session_state:
            self._render_results()

        # Selection summary
        if self.selected_scans:
            self._render_selection_summary()

    def _render_filters(self):
        """Render filter controls"""
        col1, col2, col3 = st.columns(3)

        with col1:
            # Scanner type filter
            scanner_types = ["All", "PyRIT", "Garak"]
            st.selectbox(
                "Scanner Type",
                scanner_types,
                key="filter_scanner_type"
            )

            # Date range
            default_start = datetime.now() - timedelta(days=30)
            default_end = datetime.now()

            st.date_input(
                "Start Date",
                value=default_start,
                key="filter_start_date"
            )

            st.date_input(
                "End Date",
                value=default_end,
                key="filter_end_date"
            )

        with col2:
            # Model filter
            st.text_input(
                "Target Model",
                placeholder="e.g., gpt-4, claude",
                key="filter_model"
            )

            # Orchestrator type
            orchestrator_types = self._get_orchestrator_types()
            st.multiselect(
                "Orchestrator Types",
                orchestrator_types,
                key="filter_orchestrators"
            )

        with col3:
            # Severity filter
            st.select_slider(
                "Minimum Severity",
                options=["Low", "Medium", "High", "Critical"],
                value="Low",
                key="filter_severity"
            )

            # Score categories
            categories = ["toxicity", "bias", "jailbreak", "safety", "compliance"]
            st.multiselect(
                "Score Categories",
                categories,
                key="filter_categories"
            )

    def _render_results(self):
        """Render search results"""
        results = st.session_state.get("scan_results", [])

        if not results:
            st.info("No scan data found matching your criteria")
            return

        st.subheader(f"Found {len(results)} scans")

        # Results grid
        for idx, scan in enumerate(results):
            with st.container():
                self._render_scan_card(scan, idx)

    def _render_scan_card(self, scan: Dict[str, Any], idx: int):
        """Render individual scan card"""
        # Create unique key for this scan
        scan_key = f"scan_{scan['execution_id']}"

        # Card layout
        col1, col2, col3, col4 = st.columns([0.5, 3, 2, 1])

        with col1:
            # Selection checkbox
            selected = st.checkbox(
                "Select",
                key=f"select_{scan_key}",
                value=scan_key in self.selected_scans
            )

            if selected and scan_key not in self.selected_scans:
                self.selected_scans.append(scan_key)
                st.session_state.selected_scans = self.selected_scans
            elif not selected and scan_key in self.selected_scans:
                self.selected_scans.remove(scan_key)
                st.session_state.selected_scans = self.selected_scans

        with col2:
            # Scan info
            st.markdown(f"**{scan['orchestrator_name']}**")
            st.text(f"Target: {scan['target_model']}")
            st.text(f"Date: {scan['created_at'].strftime('%Y-%m-%d %H:%M')}")

        with col3:
            # Metrics
            score_summary = scan.get('score_summary', {})
            st.metric("Tests Run", scan.get('total_prompts', 0))
            st.metric("Avg Score", f"{score_summary.get('avg_score', 0):.2f}")

            # Severity badges
            severity_dist = scan.get('severity_distribution', {})
            if severity_dist.get('critical', 0) > 0:
                st.error(f"🔴 Critical: {severity_dist['critical']}")
            if severity_dist.get('high', 0) > 0:
                st.warning(f"🟠 High: {severity_dist['high']}")

        with col4:
            # Actions
            if st.button("View Details", key=f"details_{scan_key}"):
                self._show_scan_details(scan)
```

### 2. Template Selection Tab - Implementation

#### 2.1 Template Recommendation Service

```python
# app/services/report_setup/template_recommendation_service.py
from typing import List, Dict, Any, Set
from dataclasses import dataclass
from collections import Counter

@dataclass
class DataCharacteristics:
    """Characteristics of selected scan data"""
    scanner_types: Set[str]
    score_categories: Set[str]
    severity_levels: Set[str]
    total_tests: int
    date_range: tuple
    target_models: Set[str]
    has_vulnerabilities: bool
    compliance_frameworks: Set[str]

class TemplateRecommendationService:
    """Recommend templates based on scan data"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recommendations(
        self,
        selected_scans: List[Dict[str, Any]],
        user_preferences: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Get template recommendations for selected scans"""

        # Analyze scan characteristics
        characteristics = self._analyze_scans(selected_scans)

        # Get all active templates
        templates = await self._get_active_templates()

        # Score templates based on match
        scored_templates = []
        for template in templates:
            score = self._calculate_match_score(template, characteristics)
            if score > 0.3:  # Minimum threshold
                scored_templates.append({
                    "template": template,
                    "score": score,
                    "match_reasons": self._get_match_reasons(template, characteristics)
                })

        # Sort by score
        scored_templates.sort(key=lambda x: x["score"], reverse=True)

        # Apply user preferences if provided
        if user_preferences:
            scored_templates = self._apply_preferences(scored_templates, user_preferences)

        return scored_templates[:10]  # Top 10 recommendations

    def _analyze_scans(self, scans: List[Dict[str, Any]]) -> DataCharacteristics:
        """Extract characteristics from scan data"""
        scanner_types = set()
        score_categories = set()
        severity_levels = set()
        target_models = set()
        total_tests = 0
        has_vulnerabilities = False

        for scan in scans:
            # Scanner type
            if "pyrit" in scan.get("orchestrator_name", "").lower():
                scanner_types.add("pyrit")
            elif "garak" in scan.get("scanner_type", "").lower():
                scanner_types.add("garak")

            # Score categories
            categories = scan.get("score_summary", {}).get("categories", {})
            score_categories.update(categories.keys())

            # Severity levels
            severity_dist = scan.get("severity_distribution", {})
            severity_levels.update(k for k, v in severity_dist.items() if v > 0)

            # Other metrics
            target_models.add(scan.get("target_model", "unknown"))
            total_tests += scan.get("total_prompts", 0)

            if severity_dist.get("critical", 0) > 0 or severity_dist.get("high", 0) > 0:
                has_vulnerabilities = True

        return DataCharacteristics(
            scanner_types=scanner_types,
            score_categories=score_categories,
            severity_levels=severity_levels,
            total_tests=total_tests,
            date_range=(min(s["created_at"] for s in scans), max(s["created_at"] for s in scans)),
            target_models=target_models,
            has_vulnerabilities=has_vulnerabilities,
            compliance_frameworks=set()  # TODO: Extract from scan data
        )

    def _calculate_match_score(
        self,
        template: Dict[str, Any],
        characteristics: DataCharacteristics
    ) -> float:
        """Calculate how well a template matches the data"""
        score = 0.0

        # Scanner type match (30% weight)
        template_scanners = set(template.get("data_requirements", {}).get("scanner_types", []))
        if not template_scanners or template_scanners.intersection(characteristics.scanner_types):
            score += 0.3

        # Score category match (30% weight)
        template_categories = set(template.get("scoring_categories", []))
        if template_categories:
            category_overlap = len(template_categories.intersection(characteristics.score_categories))
            score += 0.3 * (category_overlap / len(template_categories))

        # Severity focus match (20% weight)
        if characteristics.has_vulnerabilities and "security" in template.get("category", "").lower():
            score += 0.2
        elif not characteristics.has_vulnerabilities and "compliance" in template.get("category", "").lower():
            score += 0.2

        # Complexity match (20% weight)
        if characteristics.total_tests > 1000 and template.get("complexity", "") == "detailed":
            score += 0.2
        elif characteristics.total_tests < 100 and template.get("complexity", "") == "quick":
            score += 0.2
        elif template.get("complexity", "") == "standard":
            score += 0.1

        return score
```

### 3. Configuration Tab - Implementation

#### 3.1 Configuration Management

```python
# app/services/report_setup/configuration_service.py
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator

class BlockConfiguration(BaseModel):
    """Configuration for a single report block"""
    block_id: str
    enabled: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)

    @validator("settings")
    def validate_settings(cls, v, values):
        """Validate block-specific settings"""
        block_id = values.get("block_id")
        if block_id:
            # Get block definition
            block_def = block_registry.get_block(block_id)
            if block_def:
                # Validate required parameters
                for param in block_def.required_parameters:
                    if param not in v:
                        raise ValueError(f"Missing required parameter: {param}")
        return v

class ReportConfiguration(BaseModel):
    """Complete report configuration"""

    # Basic settings
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)

    # Report period
    report_period_start: datetime
    report_period_end: datetime

    # AI settings
    ai_provider: str = Field("openai", regex="^(openai|anthropic|local|none)$")
    ai_model: str = "gpt-4"
    ai_temperature: float = Field(0.7, ge=0, le=2)
    ai_max_tokens: int = Field(2000, ge=100, le=8000)

    # Output settings
    output_formats: List[str] = Field(["pdf", "json"], min_items=1)
    pdf_style: str = Field("professional", regex="^(professional|compact|detailed)$")
    include_raw_data: bool = False

    # Block configurations
    blocks: List[BlockConfiguration]

    # Data processing
    data_aggregation: str = Field("full", regex="^(full|summary|minimal)$")
    anonymize_data: bool = False

    @validator("report_period_end")
    def validate_period(cls, v, values):
        """Ensure end date is after start date"""
        start = values.get("report_period_start")
        if start and v <= start:
            raise ValueError("End date must be after start date")
        return v

class ConfigurationService:
    """Manage report configurations"""

    def __init__(self):
        self.default_configs = self._load_default_configs()

    def get_template_defaults(self, template_id: str) -> ReportConfiguration:
        """Get default configuration for a template"""
        template = self.template_service.get_template(template_id)

        # Start with base defaults
        config = ReportConfiguration(
            title=f"{template.name} Report",
            report_period_start=datetime.now() - timedelta(days=30),
            report_period_end=datetime.now(),
            blocks=[]
        )

        # Add block configurations from template
        for block in template.blocks:
            block_config = BlockConfiguration(
                block_id=block["id"],
                enabled=block.get("enabled", True),
                settings=block.get("default_settings", {})
            )
            config.blocks.append(block_config)

        return config

    def validate_configuration(
        self,
        config: ReportConfiguration,
        template: ReportTemplate,
        scan_data: List[Dict]
    ) -> List[str]:
        """Validate configuration against template and data"""
        warnings = []

        # Check if all required blocks are present
        template_block_ids = {b["id"] for b in template.blocks if b.get("required", False)}
        config_block_ids = {b.block_id for b in config.blocks if b.enabled}

        missing_blocks = template_block_ids - config_block_ids
        if missing_blocks:
            warnings.append(f"Required blocks missing: {', '.join(missing_blocks)}")

        # Check AI provider if AI blocks are enabled
        ai_blocks = [b for b in config.blocks if "ai" in b.block_id.lower() and b.enabled]
        if ai_blocks and config.ai_provider == "none":
            warnings.append("AI blocks enabled but no AI provider configured")

        # Check data availability
        data_period = (scan_data[0]["created_at"], scan_data[-1]["created_at"])
        if config.report_period_start < data_period[0]:
            warnings.append("Report period starts before available data")

        return warnings
```

### 4. Preview Tab - Implementation

#### 4.1 Preview Generation Service

```python
# app/services/report_setup/preview_service.py
from typing import Dict, Any, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PreviewService:
    """Generate report previews"""

    def __init__(self, template_service, block_processor):
        self.template_service = template_service
        self.block_processor = block_processor
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def generate_preview(
        self,
        template_id: str,
        configuration: ReportConfiguration,
        sample_data: Optional[Dict[str, Any]] = None,
        preview_blocks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate preview of report"""

        # Get template
        template = await self.template_service.get_template(template_id)

        # Use sample data if no real data provided
        if not sample_data:
            sample_data = self._generate_sample_data(template)

        # Filter blocks if specific ones requested
        blocks_to_preview = configuration.blocks
        if preview_blocks:
            blocks_to_preview = [b for b in blocks_to_preview if b.block_id in preview_blocks]

        # Process blocks in parallel
        preview_results = {}
        tasks = []

        for block_config in blocks_to_preview:
            if block_config.enabled:
                task = self._preview_block(
                    block_config,
                    template,
                    configuration,
                    sample_data
                )
                tasks.append(task)

        # Wait for all blocks to complete
        block_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Compile results
        for i, block_config in enumerate(blocks_to_preview):
            if block_config.enabled:
                if isinstance(block_results[i], Exception):
                    preview_results[block_config.block_id] = {
                        "error": str(block_results[i]),
                        "content": None
                    }
                else:
                    preview_results[block_config.block_id] = {
                        "error": None,
                        "content": block_results[i]
                    }

        # Generate preview metadata
        preview_metadata = {
            "generated_at": datetime.utcnow(),
            "is_sample_data": sample_data == self._generate_sample_data(template),
            "blocks_previewed": len(preview_results),
            "total_blocks": len(configuration.blocks),
            "warnings": self._check_preview_warnings(preview_results)
        }

        return {
            "metadata": preview_metadata,
            "blocks": preview_results,
            "variables_used": self._extract_used_variables(preview_results)
        }

    async def _preview_block(
        self,
        block_config: BlockConfiguration,
        template: Dict,
        configuration: ReportConfiguration,
        data: Dict[str, Any]
    ) -> str:
        """Preview a single block"""

        # Get block processor
        processor = self.block_processor.get_processor(block_config.block_id)

        # Process block with timeout
        try:
            result = await asyncio.wait_for(
                processor.process(
                    data=data,
                    config=block_config.settings,
                    ai_settings={
                        "provider": configuration.ai_provider,
                        "model": configuration.ai_model,
                        "temperature": configuration.ai_temperature
                    } if configuration.ai_provider != "none" else None
                ),
                timeout=30.0  # 30 second timeout for preview
            )
            return result
        except asyncio.TimeoutError:
            raise Exception("Block processing timed out")

    def _generate_sample_data(self, template: Dict) -> Dict[str, Any]:
        """Generate sample data based on template requirements"""

        sample_data = {
            "scan_summary": {
                "total_tests": 150,
                "scanner_type": "PyRIT",
                "target_model": "gpt-4-sample",
                "execution_date": datetime.utcnow(),
                "duration": "00:45:32"
            },
            "score_summary": {
                "total_scores": 150,
                "avg_score": 0.65,
                "max_score": 0.95,
                "categories": {
                    "toxicity": {"count": 50, "average": 0.7, "max": 0.95},
                    "bias": {"count": 50, "average": 0.6, "max": 0.85},
                    "jailbreak": {"count": 50, "average": 0.65, "max": 0.9}
                }
            },
            "vulnerabilities": [
                {
                    "id": "VULN-001",
                    "name": "Toxicity Generation",
                    "severity": "high",
                    "category": "toxicity",
                    "description": "Model generated toxic content in response to adversarial prompts",
                    "evidence": "Sample evidence text...",
                    "recommendation": "Implement content filtering"
                },
                {
                    "id": "VULN-002",
                    "name": "Bias in Responses",
                    "severity": "medium",
                    "category": "bias",
                    "description": "Model showed bias in certain demographic contexts",
                    "evidence": "Sample evidence text...",
                    "recommendation": "Enhance bias detection and mitigation"
                }
            ],
            "severity_distribution": {
                "critical": 2,
                "high": 15,
                "medium": 45,
                "low": 88
            }
        }

        return sample_data
```

### 5. Generate Tab - Implementation

#### 5.1 Report Generation Pipeline

```python
# app/services/report_setup/generation_pipeline.py
from typing import Dict, Any, List, Optional
import asyncio
from enum import Enum
from dataclasses import dataclass
import uuid

class GenerationStage(Enum):
    """Stages of report generation"""
    INITIALIZING = "initializing"
    FETCHING_DATA = "fetching_data"
    PROCESSING_BLOCKS = "processing_blocks"
    AI_ANALYSIS = "ai_analysis"
    RENDERING_OUTPUT = "rendering_output"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class GenerationProgress:
    """Track generation progress"""
    job_id: str
    stage: GenerationStage
    progress: int  # 0-100
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ReportGenerationPipeline:
    """Orchestrate report generation process"""

    def __init__(
        self,
        data_service,
        template_service,
        block_processor,
        output_renderer,
        ai_service
    ):
        self.data_service = data_service
        self.template_service = template_service
        self.block_processor = block_processor
        self.output_renderer = output_renderer
        self.ai_service = ai_service
        self.active_jobs = {}

    async def generate_report(
        self,
        template_id: str,
        scan_data_ids: List[str],
        configuration: ReportConfiguration,
        user_context: str
    ) -> str:
        """Start report generation job"""

        # Create job
        job_id = str(uuid.uuid4())
        self.active_jobs[job_id] = GenerationProgress(
            job_id=job_id,
            stage=GenerationStage.INITIALIZING,
            progress=0,
            message="Starting report generation"
        )

        # Start async generation
        asyncio.create_task(
            self._generate_report_async(
                job_id,
                template_id,
                scan_data_ids,
                configuration,
                user_context
            )
        )

        return job_id

    async def _generate_report_async(
        self,
        job_id: str,
        template_id: str,
        scan_data_ids: List[str],
        configuration: ReportConfiguration,
        user_context: str
    ):
        """Async report generation process"""

        try:
            # Stage 1: Initialize
            await self._update_progress(
                job_id,
                GenerationStage.INITIALIZING,
                10,
                "Loading template and validating configuration"
            )

            template = await self.template_service.get_template(template_id)

            # Stage 2: Fetch data
            await self._update_progress(
                job_id,
                GenerationStage.FETCHING_DATA,
                20,
                "Fetching and aggregating scan data"
            )

            scan_data = await self._fetch_and_aggregate_data(
                scan_data_ids,
                user_context
            )

            # Stage 3: Process blocks
            await self._update_progress(
                job_id,
                GenerationStage.PROCESSING_BLOCKS,
                40,
                "Processing report blocks"
            )

            block_results = await self._process_blocks(
                template,
                configuration,
                scan_data,
                job_id
            )

            # Stage 4: AI Analysis (if enabled)
            if configuration.ai_provider != "none":
                await self._update_progress(
                    job_id,
                    GenerationStage.AI_ANALYSIS,
                    60,
                    "Running AI analysis"
                )

                ai_results = await self._run_ai_analysis(
                    block_results,
                    configuration,
                    scan_data
                )

                # Merge AI results into blocks
                block_results.update(ai_results)

            # Stage 5: Render output formats
            await self._update_progress(
                job_id,
                GenerationStage.RENDERING_OUTPUT,
                80,
                "Rendering output formats"
            )

            output_files = await self._render_outputs(
                template,
                configuration,
                block_results,
                scan_data
            )

            # Stage 6: Finalize
            await self._update_progress(
                job_id,
                GenerationStage.FINALIZING,
                95,
                "Saving report"
            )

            report = await self._save_report(
                job_id,
                template_id,
                configuration,
                output_files,
                user_context
            )

            # Complete
            await self._update_progress(
                job_id,
                GenerationStage.COMPLETED,
                100,
                "Report generation completed",
                details={"report_id": report.id, "files": output_files}
            )

        except Exception as e:
            await self._update_progress(
                job_id,
                GenerationStage.FAILED,
                self.active_jobs[job_id].progress,
                "Report generation failed",
                error=str(e)
            )
            raise

    async def _fetch_and_aggregate_data(
        self,
        scan_data_ids: List[str],
        user_context: str
    ) -> Dict[str, Any]:
        """Fetch and aggregate scan data"""

        aggregated_data = {
            "scans": [],
            "summary": {},
            "vulnerabilities": [],
            "metrics": {}
        }

        for scan_id in scan_data_ids:
            # Determine scan type and fetch accordingly
            if scan_id.startswith("pyrit_"):
                scan_data = await self.data_service.get_pyrit_execution(
                    scan_id.replace("pyrit_", ""),
                    user_context
                )
            elif scan_id.startswith("garak_"):
                scan_data = await self.data_service.get_garak_scan(
                    scan_id.replace("garak_", ""),
                    user_context
                )
            else:
                continue

            aggregated_data["scans"].append(scan_data)

        # Aggregate metrics
        aggregated_data["summary"] = self._aggregate_summaries(aggregated_data["scans"])
        aggregated_data["vulnerabilities"] = self._aggregate_vulnerabilities(aggregated_data["scans"])
        aggregated_data["metrics"] = self._calculate_metrics(aggregated_data["scans"])

        return aggregated_data
```

### 6. Template Management Tab - Implementation

#### 6.1 Template Editor Backend

```python
# app/services/report_setup/template_editor_service.py
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

class TemplateEditorService:
    """Manage template creation and editing"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.block_registry = block_registry

    async def create_template(
        self,
        name: str,
        description: str,
        category: str,
        blocks: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        user_id: str
    ) -> ReportTemplate:
        """Create a new report template"""

        # Validate blocks
        for block in blocks:
            if not self.block_registry.validate_block(block["id"]):
                raise ValueError(f"Invalid block type: {block['id']}")

        # Extract variables from blocks
        variables = self._extract_template_variables(blocks)

        # Determine data requirements
        data_requirements = self._analyze_data_requirements(blocks)

        # Create template
        template = ReportTemplate(
            name=name,
            description=description,
            category=category,
            blocks=blocks,
            variables=variables,
            data_requirements=data_requirements,
            scoring_categories=metadata.get("scoring_categories", []),
            created_by=user_id
        )

        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        return template

    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any],
        create_version: bool = True,
        user_id: str = None
    ) -> ReportTemplate:
        """Update an existing template"""

        # Get current template
        current = await self.get_template(template_id)

        if create_version:
            # Create new version
            new_version = self._increment_version(
                current.version,
                updates.get("version_type", "minor")
            )

            # Create new template as version
            new_template = ReportTemplate(
                name=updates.get("name", current.name),
                description=updates.get("description", current.description),
                category=updates.get("category", current.category),
                blocks=updates.get("blocks", current.blocks),
                variables=self._extract_template_variables(
                    updates.get("blocks", current.blocks)
                ),
                data_requirements=updates.get("data_requirements", current.data_requirements),
                scoring_categories=updates.get("scoring_categories", current.scoring_categories),
                version=new_version,
                parent_version_id=current.id,
                created_by=user_id or current.created_by
            )

            self.db.add(new_template)
            await self.db.commit()
            await self.db.refresh(new_template)

            return new_template

        else:
            # Update in place
            for key, value in updates.items():
                if hasattr(current, key) and key not in ["id", "created_at", "created_by"]:
                    setattr(current, key, value)

            current.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(current)

            return current

    def _extract_template_variables(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract all variables used in template blocks"""

        variables = {}

        for block in blocks:
            block_def = self.block_registry.get_block(block["id"])
            if block_def:
                # Add required variables
                for var in block_def.required_variables:
                    variables[var] = {
                        "type": "required",
                        "source": "scan_data",
                        "description": f"Required by {block['id']}"
                    }

                # Add optional variables
                for var in block_def.optional_variables:
                    if var not in variables:
                        variables[var] = {
                            "type": "optional",
                            "source": "scan_data",
                            "description": f"Used by {block['id']}"
                        }

        return variables

    def _increment_version(self, current_version: str, version_type: str) -> str:
        """Increment version number"""

        parts = current_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if version_type == "major":
            return f"{major + 1}.0.0"
        elif version_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
```

## Migration Implementation

### Safe Migration Script

```python
# migrations/001_add_report_setup_tables.py
"""Add report setup tables

This migration adds new tables for the report setup feature without
modifying any existing tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add report setup tables"""

    # Check if tables already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create report_templates table
    if 'report_templates' not in existing_tables:
        op.create_table(
            'report_templates',
            sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text()),
            sa.Column('category', sa.String(100)),
            sa.Column('blocks', postgresql.JSONB(), nullable=False),
            sa.Column('variables', postgresql.JSONB()),
            sa.Column('data_requirements', postgresql.JSONB()),
            sa.Column('scoring_categories', postgresql.JSONB()),
            sa.Column('version', sa.String(20), server_default='1.0.0'),
            sa.Column('parent_version_id', postgresql.UUID()),
            sa.Column('created_by', sa.String(255)),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['parent_version_id'], ['report_templates.id'])
        )

        # Create indexes
        op.create_index('idx_report_templates_name', 'report_templates', ['name'])
        op.create_index('idx_report_templates_category', 'report_templates', ['category'])
        op.create_index('idx_report_templates_created_by', 'report_templates', ['created_by'])

    # Create report_generation_jobs table
    if 'report_generation_jobs' not in existing_tables:
        op.create_table(
            'report_generation_jobs',
            sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('template_id', postgresql.UUID(), nullable=False),
            sa.Column('configuration', postgresql.JSONB(), nullable=False),
            sa.Column('scan_data_ids', postgresql.JSONB(), nullable=False),
            sa.Column('status', sa.String(50), server_default='pending'),
            sa.Column('progress', sa.Integer(), server_default='0'),
            sa.Column('stage', sa.String(50)),
            sa.Column('message', sa.Text()),
            sa.Column('results', postgresql.JSONB()),
            sa.Column('error_details', postgresql.JSONB()),
            sa.Column('created_by', sa.String(255)),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('started_at', sa.TIMESTAMP(timezone=True)),
            sa.Column('completed_at', sa.TIMESTAMP(timezone=True)),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'])
        )

        # Create indexes
        op.create_index('idx_report_generation_jobs_status', 'report_generation_jobs', ['status'])
        op.create_index('idx_report_generation_jobs_created_by', 'report_generation_jobs', ['created_by'])

    # Create generated_reports table
    if 'generated_reports' not in existing_tables:
        op.create_table(
            'generated_reports',
            sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('job_id', postgresql.UUID(), nullable=False),
            sa.Column('template_id', postgresql.UUID(), nullable=False),
            sa.Column('title', sa.String(500)),
            sa.Column('formats', postgresql.JSONB()),
            sa.Column('file_paths', postgresql.JSONB()),
            sa.Column('metadata', postgresql.JSONB()),
            sa.Column('created_by', sa.String(255)),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['job_id'], ['report_generation_jobs.id']),
            sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'])
        )

        # Create indexes
        op.create_index('idx_generated_reports_created_by', 'generated_reports', ['created_by'])
        op.create_index('idx_generated_reports_created_at', 'generated_reports', ['created_at'])

    # Create report_schedules table
    if 'report_schedules' not in existing_tables:
        op.create_table(
            'report_schedules',
            sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('template_id', postgresql.UUID(), nullable=False),
            sa.Column('configuration', postgresql.JSONB(), nullable=False),
            sa.Column('data_selection', postgresql.JSONB(), nullable=False),
            sa.Column('schedule_type', sa.String(50), nullable=False),
            sa.Column('schedule_config', postgresql.JSONB(), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('next_run', sa.TIMESTAMP(timezone=True)),
            sa.Column('last_run', sa.TIMESTAMP(timezone=True)),
            sa.Column('created_by', sa.String(255)),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'])
        )

        # Create indexes
        op.create_index('idx_report_schedules_is_active', 'report_schedules', ['is_active'])
        op.create_index('idx_report_schedules_next_run', 'report_schedules', ['next_run'])

def downgrade():
    """Remove report setup tables"""

    # Drop tables in reverse order due to foreign keys
    op.drop_table('report_schedules')
    op.drop_table('generated_reports')
    op.drop_table('report_generation_jobs')
    op.drop_table('report_templates')
```

## Setup Script Updates

### Updated Setup Script Section

```bash
# In setup_macos_new.sh (and similar for Linux/Windows)

# Function to check and run report setup migration
setup_report_features() {
    echo "Checking report setup features..."

    # Check if report tables exist
    TABLES_EXIST=$(docker exec -i violentutf-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -tAc "
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('report_templates', 'report_generation_jobs', 'generated_reports', 'report_schedules')
    ")

    if [ "$TABLES_EXIST" -eq "0" ]; then
        echo "Setting up report features..."

        # Run migration
        docker exec -i violentutf-api alembic upgrade head

        # Load initial templates
        docker exec -i violentutf-api python scripts/load_initial_templates.py

        echo "Report features setup completed"
    else
        echo "Report features already configured"
    fi
}

# Add to main setup flow
main() {
    # ... existing setup steps ...

    # After database is ready
    setup_report_features

    # Set feature flag
    echo "REPORT_SETUP_ENABLED=true" >> violentutf/.env

    # ... rest of setup ...
}
```

## Testing Strategy

### 1. Unit Tests

```python
# tests/test_report_setup/test_data_browser.py
import pytest
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_browse_orchestrator_executions(data_access_service, sample_executions):
    """Test browsing orchestrator executions"""

    # Test with filters
    results = await data_access_service.browse_orchestrator_executions(
        user_context="test_user",
        start_date=datetime.now() - timedelta(days=7),
        orchestrator_types=["RedTeamingOrchestrator"],
        limit=10
    )

    assert results["total_count"] > 0
    assert len(results["executions"]) <= 10
    assert all(e["orchestrator_name"] == "RedTeamingOrchestrator" for e in results["executions"])

    # Verify enrichment
    first_execution = results["executions"][0]
    assert "score_summary" in first_execution
    assert "severity_distribution" in first_execution
    assert "key_findings" in first_execution
```

### 2. Integration Tests

```python
# tests/test_report_setup/test_generation_pipeline.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_full_report_generation(
    generation_pipeline,
    sample_template,
    sample_scan_data,
    test_configuration
):
    """Test complete report generation pipeline"""

    # Start generation
    job_id = await generation_pipeline.generate_report(
        template_id=sample_template.id,
        scan_data_ids=["pyrit_exec1", "pyrit_exec2"],
        configuration=test_configuration,
        user_context="test_user"
    )

    # Wait for completion
    max_wait = 60  # seconds
    start_time = datetime.now()

    while (datetime.now() - start_time).seconds < max_wait:
        progress = await generation_pipeline.get_progress(job_id)

        if progress.stage == GenerationStage.COMPLETED:
            break
        elif progress.stage == GenerationStage.FAILED:
            pytest.fail(f"Generation failed: {progress.error}")

        await asyncio.sleep(1)

    # Verify results
    assert progress.stage == GenerationStage.COMPLETED
    assert progress.progress == 100
    assert "report_id" in progress.details
    assert "files" in progress.details

    # Verify output files
    files = progress.details["files"]
    assert "pdf" in files
    assert "json" in files
```

## Conclusion

This revised implementation plan provides:

1. **Tab-based organization** matching the UI structure
2. **Real data usage** with no mock data
3. **Safe migration strategy** that won't break existing systems
4. **Incremental setup updates** for gradual rollout
5. **Comprehensive documentation** structure and timeline
6. **Detailed implementation** for each component

The plan emphasizes safety through:
- New tables only (no modifications to existing schema)
- Feature flags for controlled rollout
- Backward compatibility
- Comprehensive testing at each phase
