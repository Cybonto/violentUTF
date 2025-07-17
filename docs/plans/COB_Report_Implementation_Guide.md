# COB Report Enhancement Implementation Guide

## 1. Implementation Overview

This guide provides detailed technical implementation steps for enhancing the COB report system with template-driven architecture, AI analysis, and multiple export formats.

## 2. Project Structure

```
violentutf/
├── core/
│   └── reports/
│       ├── __init__.py
│       ├── templates/
│       │   ├── base.py          # Base template classes
│       │   ├── blocks.py         # Block implementations
│       │   ├── parser.py         # Template parser
│       │   └── validator.py      # Template validation
│       ├── analysis/
│       │   ├── ai_analyzer.py   # AI analysis integration
│       │   ├── prompts.py        # Prompt templates
│       │   └── processors.py     # Output processors
│       ├── export/
│       │   ├── base_exporter.py  # Base exporter class
│       │   ├── pdf_exporter.py   # PDF export
│       │   ├── json_exporter.py  # JSON export
│       │   ├── excel_exporter.py # Excel export
│       │   └── html_exporter.py  # HTML export
│       └── scheduler/
│           ├── scheduler.py      # Report scheduling
│           └── distribution.py   # Report distribution
├── api/
│   └── endpoints/
│       └── cob_reports.py        # API endpoints
├── pages/
│   └── 5_Dashboard.py            # Updated dashboard
└── utils/
    └── report_helpers.py         # Helper functions
```

## 3. Core Components Implementation

### 3.1 Scheduling System (PRIORITY FEATURE)

The scheduling system is the most critical component of the COB report enhancement, enabling automated report generation at configured intervals.

```python
# violentutf/core/reports/scheduler/scheduler.py

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from ...database import get_async_session
from ..generator import ReportGenerator
from ...utils.logger import get_logger
from ...utils.security import SecureConfig

logger = get_logger(__name__)

# Initialize APScheduler with PostgreSQL job store
jobstores = {
    'default': SQLAlchemyJobStore(
        url=SecureConfig.get_database_url(),
        tableschema='cob_reports',
        tablename='apscheduler_jobs'
    )
}

executors = {
    'default': AsyncIOExecutor(),
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults={
        'coalesce': True,
        'max_instances': 3,
        'misfire_grace_time': 30
    },
    timezone=pytz.UTC
)

class ReportScheduler:
    """Manages scheduled report generation"""
    
    def __init__(self):
        self.db = get_db()
        self.generator = ReportGenerator()
        self._update_celery_schedule()
    
    async def create_schedule(
        self,
        template_id: str,
        frequency: str,
        time: str,
        timezone: str = 'UTC',
        parameters: Dict[str, Any] = None,
        export_formats: List[str] = None,
        distribution: Dict[str, List[str]] = None,
        user_id: str = None
    ) -> str:
        """Create a new report schedule"""
        # Validate timezone
        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {timezone}")
        
        # Parse time
        hour, minute = map(int, time.split(':'))
        
        # Create schedule record
        schedule_data = {
            'template_id': template_id,
            'frequency': frequency,
            'schedule_time': f"{hour:02d}:{minute:02d}:00",
            'timezone': timezone,
            'parameters': parameters or {},
            'export_formats': export_formats or ['markdown', 'pdf'],
            'distribution_config': distribution or {},
            'is_active': True,
            'created_by': user_id,
            'next_run_at': self._calculate_next_run(frequency, hour, minute, tz)
        }
        
        # Insert into database
        async with self.db.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO cob_report_schedules 
                (template_id, frequency, schedule_time, timezone, parameters,
                 export_formats, distribution_config, is_active, created_by, next_run_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                schedule_data['template_id'],
                schedule_data['frequency'],
                schedule_data['schedule_time'],
                schedule_data['timezone'],
                schedule_data['parameters'],
                schedule_data['export_formats'],
                schedule_data['distribution_config'],
                schedule_data['is_active'],
                schedule_data['created_by'],
                schedule_data['next_run_at']
            )
            
            schedule_id = str(result['id'])
        
        # Update Celery beat schedule
        self._update_celery_schedule()
        
        logger.info(f"Created schedule {schedule_id} for template {template_id}")
        return schedule_id
    
    def _calculate_next_run(self, frequency: str, hour: int, minute: int, 
                           tz: timezone) -> datetime:
        """Calculate next run time based on frequency"""
        now = datetime.now(tz)
        
        if frequency == 'daily':
            # Next occurrence of the specified time
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif frequency == 'weekly':
            # Next Monday at specified time
            days_ahead = 0 - now.weekday()  # Monday is 0
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        elif frequency == 'monthly':
            # First day of next month at specified time
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1,
                                     hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1,
                                     hour=hour, minute=minute, second=0, microsecond=0)
        
        return next_run.astimezone(pytz.UTC)
    
    def _update_celery_schedule(self):
        """Update Celery beat schedule with active schedules"""
        # This would be called to refresh the Celery beat schedule
        # Implementation depends on your Celery setup
        pass
    
    async def execute_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a scheduled report generation"""
        try:
            # Get schedule details
            async with self.db.pool.acquire() as conn:
                schedule = await conn.fetchrow(
                    """
                    SELECT s.*, t.name as template_name
                    FROM cob_report_schedules s
                    JOIN cob_report_templates t ON s.template_id = t.id
                    WHERE s.id = $1 AND s.is_active = true
                    """,
                    schedule_id
                )
                
                if not schedule:
                    raise ValueError(f"Schedule {schedule_id} not found or inactive")
            
            # Generate report
            report_date = datetime.now(pytz.timezone(schedule['timezone'])).date()
            
            report_id = await self.generator.generate_report(
                template_id=schedule['template_id'],
                report_date=report_date,
                parameters={
                    **schedule['parameters'],
                    'scheduled': True,
                    'schedule_id': schedule_id
                },
                user_id=schedule['created_by']
            )
            
            # Export in requested formats
            export_results = {}
            for format in schedule['export_formats']:
                try:
                    export_url = await self.generator.export_report(
                        report_id=report_id,
                        format=format
                    )
                    export_results[format] = export_url
                except Exception as e:
                    logger.error(f"Failed to export {format}: {e}")
                    export_results[format] = None
            
            # Distribute report
            if schedule['distribution_config']:
                await self._distribute_report(
                    report_id=report_id,
                    export_results=export_results,
                    distribution_config=schedule['distribution_config'],
                    template_name=schedule['template_name']
                )
            
            # Update schedule execution history
            async with self.db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cob_schedule_executions 
                    (schedule_id, report_id, executed_at, success, execution_time_ms)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    schedule_id,
                    report_id,
                    datetime.now(pytz.UTC),
                    True,
                    0  # Would calculate actual execution time
                )
                
                # Update next run time
                next_run = self._calculate_next_run(
                    schedule['frequency'],
                    schedule['schedule_time'].hour,
                    schedule['schedule_time'].minute,
                    pytz.timezone(schedule['timezone'])
                )
                
                await conn.execute(
                    """
                    UPDATE cob_report_schedules 
                    SET last_run_at = $1, next_run_at = $2
                    WHERE id = $3
                    """,
                    datetime.now(pytz.UTC),
                    next_run,
                    schedule_id
                )
            
            logger.info(f"Successfully executed schedule {schedule_id}, report {report_id}")
            return {
                'success': True,
                'report_id': report_id,
                'exports': export_results
            }
            
        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule_id}: {e}")
            
            # Log failure
            async with self.db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cob_schedule_executions 
                    (schedule_id, executed_at, success, error_message)
                    VALUES ($1, $2, $3, $4)
                    """,
                    schedule_id,
                    datetime.now(pytz.UTC),
                    False,
                    str(e)
                )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _distribute_report(
        self,
        report_id: str,
        export_results: Dict[str, str],
        distribution_config: Dict[str, List[str]],
        template_name: str
    ):
        """Distribute report to configured channels"""
        from .distribution import ReportDistributor
        
        distributor = ReportDistributor()
        
        # Email distribution
        if 'email' in distribution_config:
            pdf_url = export_results.get('pdf')
            if pdf_url:
                await distributor.send_email(
                    recipients=distribution_config['email'],
                    subject=f"COB Report - {template_name} - {datetime.now().strftime('%Y-%m-%d')}",
                    body="Please find attached the daily COB report.",
                    attachment_url=pdf_url
                )
        
        # Slack distribution
        if 'slack' in distribution_config:
            for channel in distribution_config['slack']:
                await distributor.send_slack(
                    channel=channel,
                    message=f"📊 COB Report Generated: {template_name}",
                    report_url=export_results.get('pdf', export_results.get('markdown'))
                )

# Celery tasks
@celery_app.task
def check_and_execute_schedules():
    """Check for schedules that need to be executed"""
    asyncio.run(_check_schedules())

async def _check_schedules():
    """Async function to check and execute due schedules"""
    scheduler = ReportScheduler()
    db = get_db()
    
    async with db.pool.acquire() as conn:
        # Find schedules that are due
        due_schedules = await conn.fetch(
            """
            SELECT id FROM cob_report_schedules
            WHERE is_active = true 
            AND next_run_at <= $1
            """,
            datetime.now(pytz.UTC)
        )
    
    # Execute each due schedule
    for schedule in due_schedules:
        try:
            await scheduler.execute_schedule(str(schedule['id']))
        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule['id']}: {e}")

# Configure Celery beat to check schedules every minute
celery_app.conf.beat_schedule['check_cob_schedules'] = {
    'task': 'check_and_execute_schedules',
    'schedule': crontab(minute='*'),  # Every minute
}
```

### 3.2 Base Template System

```python
# violentutf/core/reports/templates/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import yaml
import jinja2
from pydantic import BaseModel, Field, validator

class TemplateMetadata(BaseModel):
    """Template metadata model"""
    id: str
    name: str
    version: str
    author: Optional[str]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    description: Optional[str]
    tags: List[str] = []
    permissions: Dict[str, List[str]] = {
        "read": ["all_users"],
        "write": ["admin"]
    }

class BlockConfig(BaseModel):
    """Configuration for a report block"""
    id: str
    type: str
    order: int
    title: str
    icon: Optional[str]
    data_sources: Optional[List[str]]
    template: Optional[str]
    config: Dict[str, Any] = {}
    
    @validator('type')
    def validate_block_type(cls, v):
        valid_types = ['data_block', 'analysis_block', 'visualization_block', 
                      'custom_block', 'composite_block']
        if v not in valid_types:
            raise ValueError(f"Invalid block type: {v}")
        return v

class ReportTemplate:
    """Base class for report templates"""
    
    def __init__(self, config: Dict[str, Any]):
        self.metadata = TemplateMetadata(**config.get('metadata', {}))
        self.parameters = config.get('parameters', {})
        self.blocks = [BlockConfig(**block) for block in config.get('blocks', [])]
        self.export_config = config.get('export_config', {})
        self.jinja_env = self._setup_jinja_env()
    
    def _setup_jinja_env(self) -> jinja2.Environment:
        """Setup Jinja2 environment with custom filters"""
        env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            undefined=jinja2.StrictUndefined
        )
        
        # Add custom filters
        env.filters['calculate_change'] = self._calculate_change
        env.filters['format_number'] = self._format_number
        env.filters['trend_indicator'] = self._trend_indicator
        
        return env
    
    @staticmethod
    def _calculate_change(current: float, previous: float) -> str:
        """Calculate percentage change"""
        if previous == 0:
            return "N/A"
        change = ((current - previous) / previous) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"
    
    @staticmethod
    def _format_number(value: float, decimals: int = 0) -> str:
        """Format number with commas"""
        return f"{value:,.{decimals}f}"
    
    @staticmethod
    def _trend_indicator(current: float, previous: float, inverse: bool = False) -> str:
        """Return trend indicator emoji"""
        if current > previous:
            return "📈" if not inverse else "📉"
        elif current < previous:
            return "📉" if not inverse else "📈"
        else:
            return "➡️"
    
    async def render(self, data: Dict[str, Any], parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render the template with data"""
        # Merge parameters
        params = {**self.parameters, **(parameters or {})}
        
        # Render each block
        rendered_blocks = []
        for block in sorted(self.blocks, key=lambda x: x.order):
            renderer = self._get_block_renderer(block.type)
            rendered_block = await renderer.render(block, data, params)
            rendered_blocks.append(rendered_block)
        
        return {
            "metadata": self.metadata.dict(),
            "parameters": params,
            "blocks": rendered_blocks,
            "rendered_at": datetime.now().isoformat()
        }
    
    def _get_block_renderer(self, block_type: str):
        """Get appropriate renderer for block type"""
        from .blocks import (
            DataBlockRenderer,
            AnalysisBlockRenderer,
            VisualizationBlockRenderer,
            CustomBlockRenderer,
            CompositeBlockRenderer
        )
        
        renderers = {
            'data_block': DataBlockRenderer(self.jinja_env),
            'analysis_block': AnalysisBlockRenderer(self.jinja_env),
            'visualization_block': VisualizationBlockRenderer(self.jinja_env),
            'custom_block': CustomBlockRenderer(self.jinja_env),
            'composite_block': CompositeBlockRenderer(self.jinja_env)
        }
        
        return renderers.get(block_type)
```

### 3.2 Block Implementations

```python
# violentutf/core/reports/templates/blocks.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import jinja2
from ..analysis.ai_analyzer import AIAnalyzer
from ...utils.data_extractor import DataExtractor

class BlockRenderer(ABC):
    """Base class for block renderers"""
    
    def __init__(self, jinja_env: jinja2.Environment):
        self.jinja_env = jinja_env
        self.data_extractor = DataExtractor()
    
    @abstractmethod
    async def render(self, block_config: 'BlockConfig', 
                    data: Dict[str, Any], 
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render the block"""
        pass
    
    def extract_data(self, data: Dict[str, Any], paths: List[str]) -> Dict[str, Any]:
        """Extract data from paths"""
        extracted = {}
        for path in paths:
            value = self.data_extractor.get_value(data, path)
            key = path.split('.')[-1]  # Use last part as key
            extracted[key] = value
        return extracted

class DataBlockRenderer(BlockRenderer):
    """Renderer for data blocks"""
    
    async def render(self, block_config: 'BlockConfig', 
                    data: Dict[str, Any], 
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render data block"""
        # Extract required data
        if block_config.data_sources:
            block_data = self.extract_data(data, block_config.data_sources)
        else:
            block_data = data
        
        # Merge with parameters
        context = {**parameters, **block_data}
        
        # Render template
        if block_config.template:
            template = self.jinja_env.from_string(block_config.template)
            rendered_content = template.render(**context)
        else:
            rendered_content = str(block_data)
        
        return {
            "id": block_config.id,
            "type": "data",
            "title": block_config.title,
            "content": rendered_content,
            "data": block_data
        }

class AnalysisBlockRenderer(BlockRenderer):
    """Renderer for AI analysis blocks"""
    
    def __init__(self, jinja_env: jinja2.Environment):
        super().__init__(jinja_env)
        self.ai_analyzer = AIAnalyzer()
    
    async def render(self, block_config: 'BlockConfig', 
                    data: Dict[str, Any], 
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render analysis block with AI"""
        # Extract context data
        context_data = {}
        if block_config.data_dependencies:
            context_data = self.extract_data(data, block_config.data_dependencies)
        
        # Prepare prompt
        prompt_template = block_config.config.get('prompt_template', '')
        template = self.jinja_env.from_string(prompt_template)
        prompt = template.render(**{**parameters, **context_data})
        
        # Call AI model
        analysis_config = {
            'model': block_config.config.get('model', 'gpt-3.5-turbo'),
            'temperature': block_config.config.get('temperature', 0.7),
            'max_tokens': block_config.config.get('max_tokens', 1000),
            'context_window': block_config.config.get('context_window', 4000)
        }
        
        analysis_result = await self.ai_analyzer.analyze(
            prompt=prompt,
            config=analysis_config
        )
        
        # Process output
        output_processor = block_config.config.get('output_processor', 'raw')
        processed_output = self._process_output(analysis_result, output_processor)
        
        return {
            "id": block_config.id,
            "type": "analysis",
            "title": block_config.title,
            "content": processed_output,
            "metadata": {
                "model": analysis_config['model'],
                "tokens_used": analysis_result.get('usage', {}).get('total_tokens', 0)
            }
        }
    
    def _process_output(self, output: str, processor: str) -> str:
        """Process AI output based on processor type"""
        processors = {
            'raw': lambda x: x,
            'structured_markdown': self._structure_markdown,
            'bullet_points': self._extract_bullet_points,
            'json': self._parse_json_output
        }
        
        processor_func = processors.get(processor, lambda x: x)
        return processor_func(output)
    
    def _structure_markdown(self, output: str) -> str:
        """Structure output as clean markdown"""
        # Add logic to clean and structure markdown
        return output
    
    def _extract_bullet_points(self, output: str) -> str:
        """Extract and format bullet points"""
        # Add logic to extract bullet points
        return output
    
    def _parse_json_output(self, output: str) -> str:
        """Parse JSON output from AI"""
        import json
        try:
            parsed = json.loads(output)
            return json.dumps(parsed, indent=2)
        except:
            return output

class VisualizationBlockRenderer(BlockRenderer):
    """Renderer for visualization blocks"""
    
    async def render(self, block_config: 'BlockConfig', 
                    data: Dict[str, Any], 
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render visualization block"""
        chart_type = block_config.config.get('chart_type', 'line')
        chart_data = self._prepare_chart_data(data, block_config.config)
        
        # Generate chart configuration
        chart_config = {
            'type': chart_type,
            'data': chart_data,
            'options': block_config.config.get('options', {}),
            'responsive': True
        }
        
        return {
            "id": block_config.id,
            "type": "visualization",
            "title": block_config.title,
            "chart_config": chart_config,
            "render_type": "chart"
        }
    
    def _prepare_chart_data(self, data: Dict[str, Any], 
                           config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for chart rendering"""
        # Extract and format data based on chart type
        data_source = config.get('data_source', '')
        chart_data = self.data_extractor.get_value(data, data_source)
        
        # Transform data for specific chart types
        chart_type = config.get('chart_type')
        if chart_type == 'line':
            return self._prepare_line_data(chart_data, config)
        elif chart_type == 'heatmap':
            return self._prepare_heatmap_data(chart_data, config)
        # Add more chart type handlers
        
        return chart_data
    
    def _prepare_line_data(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for line chart"""
        # Implementation for line chart data preparation
        return {
            'labels': [],
            'datasets': []
        }
    
    def _prepare_heatmap_data(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for heatmap"""
        # Implementation for heatmap data preparation
        return {
            'x': [],
            'y': [],
            'values': []
        }

class CustomBlockRenderer(BlockRenderer):
    """Renderer for custom script blocks"""
    
    async def render(self, block_config: 'BlockConfig', 
                    data: Dict[str, Any], 
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render custom block by executing script"""
        script = block_config.config.get('script', '')
        
        # Create safe execution environment
        safe_globals = {
            '__builtins__': {
                'len': len,
                'max': max,
                'min': min,
                'sum': sum,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
                'range': range,
                'dict': dict,
                'list': list,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool
            }
        }
        
        # Define the execution namespace
        namespace = {**safe_globals}
        
        try:
            # Execute the script
            exec(script, namespace)
            
            # Call the main function if it exists
            if 'calculate' in namespace:
                result = namespace['calculate'](data)
            elif 'analyze' in namespace:
                result = namespace['analyze'](data)
            else:
                # Look for any defined function
                for name, obj in namespace.items():
                    if callable(obj) and not name.startswith('_'):
                        result = obj(data)
                        break
                else:
                    result = {"error": "No callable function found in script"}
            
            # Render output template if provided
            output_template = block_config.config.get('output_template', '')
            if output_template and isinstance(result, dict):
                template = self.jinja_env.from_string(output_template)
                rendered_content = template.render(**result)
            else:
                rendered_content = str(result)
            
            return {
                "id": block_config.id,
                "type": "custom",
                "title": block_config.title,
                "content": rendered_content,
                "data": result if isinstance(result, dict) else {"result": result}
            }
            
        except Exception as e:
            return {
                "id": block_config.id,
                "type": "custom",
                "title": block_config.title,
                "content": f"Error executing custom script: {str(e)}",
                "error": True
            }

class CompositeBlockRenderer(BlockRenderer):
    """Renderer for composite blocks containing multiple sub-blocks"""
    
    async def render(self, block_config: 'BlockConfig', 
                    data: Dict[str, Any], 
                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render composite block"""
        sub_blocks = block_config.config.get('sub_blocks', [])
        rendered_sub_blocks = []
        
        for sub_block in sub_blocks:
            # Create a temporary block config for sub-block
            sub_config = BlockConfig(
                id=f"{block_config.id}_{sub_block.get('id', 'sub')}",
                type=sub_block.get('type', 'data_block'),
                order=0,
                title=sub_block.get('title', ''),
                **sub_block
            )
            
            # Get appropriate renderer
            renderer = self._get_renderer(sub_config.type)
            rendered = await renderer.render(sub_config, data, parameters)
            rendered_sub_blocks.append(rendered)
        
        return {
            "id": block_config.id,
            "type": "composite",
            "title": block_config.title,
            "sub_blocks": rendered_sub_blocks
        }
    
    def _get_renderer(self, block_type: str):
        """Get renderer instance for block type"""
        renderers = {
            'data_block': DataBlockRenderer(self.jinja_env),
            'analysis_block': AnalysisBlockRenderer(self.jinja_env),
            'visualization_block': VisualizationBlockRenderer(self.jinja_env),
            'custom_block': CustomBlockRenderer(self.jinja_env)
        }
        return renderers.get(block_type, DataBlockRenderer(self.jinja_env))
```

### 3.3 AI Analysis Integration

```python
# violentutf/core/reports/analysis/ai_analyzer.py

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import json
from openai import AsyncOpenAI
import anthropic
from ...utils.cache import AsyncCache
from ...utils.logger import get_logger

logger = get_logger(__name__)

class AIAnalyzer:
    """AI-powered analysis engine for reports"""
    
    def __init__(self):
        self.cache = AsyncCache(ttl=3600)  # 1-hour cache
        self.models = self._initialize_models()
        
    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize AI model clients"""
        models = {}
        
        # OpenAI models
        try:
            models['openai'] = AsyncOpenAI()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI: {e}")
        
        # Anthropic models
        try:
            models['anthropic'] = anthropic.AsyncAnthropic()
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic: {e}")
        
        # GSAi models
        try:
            from ...utils.token_manager import TokenManager
            token_manager = TokenManager()
            gsai_config = token_manager.get_provider_config('gsai-api-1')
            if gsai_config:
                models['gsai'] = {
                    'base_url': gsai_config.get('base_url'),
                    'auth_token': gsai_config.get('auth_token'),
                    'auth_type': gsai_config.get('auth_type', 'bearer')
                }
        except Exception as e:
            logger.warning(f"Failed to initialize GSAi: {e}")
        
        # Custom REST API support
        models['rest_api'] = {}  # Will be configured per request
        
        return models
    
    async def analyze(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform AI analysis based on prompt and configuration"""
        # Generate cache key
        cache_key = self._generate_cache_key(prompt, config)
        
        # Check cache
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Using cached analysis for key: {cache_key}")
            return cached_result
        
        # Perform analysis
        model = config.get('model', 'gpt-3.5-turbo')
        
        try:
            if model.startswith('gpt'):
                result = await self._analyze_openai(prompt, config)
            elif model.startswith('claude'):
                result = await self._analyze_anthropic(prompt, config)
            elif model.startswith('gsai-api-'):
                result = await self._analyze_gsai(prompt, config)
            elif model == 'rest_api':
                result = await self._analyze_rest_api(prompt, config)
            else:
                raise ValueError(f"Unsupported model: {model}")
            
            # Cache result
            await self.cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "content": f"Analysis failed: {str(e)}",
                "error": True,
                "model": model
            }
    
    async def _analyze_openai(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using OpenAI models"""
        client = self.models.get('openai')
        if not client:
            raise ValueError("OpenAI client not initialized")
        
        response = await client.chat.completions.create(
            model=config.get('model', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": "You are a security analyst providing detailed analysis for COB reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 1000),
            top_p=config.get('top_p', 1.0),
            frequency_penalty=config.get('frequency_penalty', 0),
            presence_penalty=config.get('presence_penalty', 0)
        )
        
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "finish_reason": response.choices[0].finish_reason
        }
    
    async def _analyze_anthropic(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using Anthropic models"""
        client = self.models.get('anthropic')
        if not client:
            raise ValueError("Anthropic client not initialized")
        
        response = await client.messages.create(
            model=config.get('model', 'claude-3-haiku-20240307'),
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.get('max_tokens', 1000),
            temperature=config.get('temperature', 0.7)
        )
        
        return {
            "content": response.content[0].text,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "stop_reason": response.stop_reason
        }
    
    async def _analyze_gsai(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using GSAi API models"""
        import aiohttp
        
        gsai_config = self.models.get('gsai', {})
        if not gsai_config:
            raise ValueError("GSAi not configured")
        
        # Extract model name (e.g., "gsai-api-1/llama3211b" -> "llama3211b")
        model_parts = config.get('model', '').split('/')
        model_name = model_parts[1] if len(model_parts) > 1 else model_parts[0]
        
        # Prepare request
        url = f"{gsai_config['base_url']}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add authentication
        if gsai_config['auth_type'] == 'bearer':
            headers["Authorization"] = f"Bearer {gsai_config['auth_token']}"
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a security analyst providing detailed analysis for COB reports."},
                {"role": "user", "content": prompt}
            ],
            "temperature": config.get('temperature', 0.7),
            "max_tokens": config.get('max_tokens', 1000)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data['choices'][0]['message']['content'],
                        "model": model_name,
                        "usage": data.get('usage', {}),
                        "provider": "gsai"
                    }
                else:
                    error_text = await response.text()
                    raise ValueError(f"GSAi API error: {response.status} - {error_text}")
    
    async def _analyze_rest_api(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using custom REST API endpoint"""
        import aiohttp
        from jinja2 import Template
        
        # Get endpoint configuration
        endpoint = config.get('endpoint')
        method = config.get('method', 'POST')
        headers = config.get('headers', {})
        request_template = config.get('request_template', {})
        response_path = config.get('response_path', 'content')
        
        if not endpoint:
            raise ValueError("REST API endpoint not configured")
        
        # Render headers with any template variables
        rendered_headers = {}
        for key, value in headers.items():
            if '{{' in value:
                template = Template(value)
                rendered_headers[key] = template.render(api_token=config.get('api_token', ''))
            else:
                rendered_headers[key] = value
        
        # Prepare request body
        if request_template:
            body = {}
            for key, value in request_template.items():
                if key == 'prompt':
                    body[key] = prompt
                elif '{{' in str(value):
                    template = Template(str(value))
                    body[key] = template.render(prompt=prompt, **config)
                else:
                    body[key] = value
        else:
            body = {"prompt": prompt}
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=endpoint,
                json=body,
                headers=rendered_headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract content from response using path
                    content = data
                    for key in response_path.split('.'):
                        content = content.get(key, content)
                    
                    return {
                        "content": str(content),
                        "model": "custom_rest_api",
                        "provider": "rest_api",
                        "endpoint": endpoint
                    }
                else:
                    error_text = await response.text()
                    raise ValueError(f"REST API error: {response.status} - {error_text}")
    
    def _generate_cache_key(self, prompt: str, config: Dict[str, Any]) -> str:
        """Generate cache key for prompt and config"""
        # Create a deterministic string from prompt and config
        cache_data = {
            "prompt": prompt,
            "model": config.get('model'),
            "temperature": config.get('temperature'),
            "max_tokens": config.get('max_tokens')
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()

class PromptLibrary:
    """Library of reusable prompt templates"""
    
    THREAT_ANALYSIS = """
    Analyze the following security threat data and provide a comprehensive assessment:
    
    {threat_data}
    
    Please provide:
    1. Threat Severity Assessment (Critical/High/Medium/Low) with justification
    2. Top 3 Security Concerns with specific details
    3. Attack Pattern Analysis identifying common techniques
    4. Immediate Mitigation Steps (prioritized list)
    5. Long-term Security Recommendations
    6. Trend Analysis comparing to historical baseline
    
    Format your response in clear sections with markdown headers.
    """
    
    PERFORMANCE_ANALYSIS = """
    Analyze the following system performance metrics:
    
    {performance_data}
    
    Provide insights on:
    1. Overall system health assessment
    2. Performance bottlenecks identified
    3. Resource utilization analysis
    4. Scalability concerns
    5. Optimization recommendations
    6. Predicted performance trends
    
    Include specific metrics and thresholds in your analysis.
    """
    
    EXECUTIVE_SUMMARY = """
    Create an executive summary based on the following operational data:
    
    {operational_data}
    
    The summary should:
    1. Highlight key achievements and positive trends
    2. Identify critical risks requiring leadership attention
    3. Provide 3-5 strategic recommendations
    4. Include business impact assessment
    5. Suggest resource allocation priorities
    
    Keep language non-technical and focus on business outcomes.
    Maximum 3 paragraphs.
    """
    
    INCIDENT_ANALYSIS = """
    Perform root cause analysis on the following incident:
    
    {incident_data}
    
    Your analysis should include:
    1. Root cause identification (ranked by probability)
    2. Contributing factors analysis
    3. Timeline reconstruction
    4. Impact assessment (technical and business)
    5. Remediation steps (immediate and long-term)
    6. Prevention recommendations
    7. Similar incident correlation
    
    Be specific and actionable in your recommendations.
    """
```

### 3.4 Export System

```python
# violentutf/core/reports/export/pdf_exporter.py

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from weasyprint import HTML, CSS
from markupsafe import Markup
import bleach
import markdown
import io
import base64
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .base_exporter import BaseExporter
from ...utils.security import sanitize_user_input

class SecurePDFExporter(BaseExporter):
    """Secure PDF export implementation with sanitization"""
    
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 
        'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img'
    ]
    
    ALLOWED_ATTRIBUTES = {
        '*': ['class', 'id'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan'],
        'img': ['src', 'alt', 'width', 'height']
    }
    
    def __init__(self):
        super().__init__()
        self.template_env = Environment(
            loader=FileSystemLoader('templates/pdf'),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def _setup_custom_styles(self):
        """Setup custom PDF styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=20,
            spaceAfter=12
        ))
        
        # Alert style
        self.styles.add(ParagraphStyle(
            name='Alert',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#e74c3c'),
            backColor=colors.HexColor('#ffe6e6'),
            borderWidth=1,
            borderColor=colors.HexColor('#e74c3c'),
            borderPadding=10
        ))
    
    async def export(self, report_data: Dict[str, Any], 
                    options: Dict[str, Any] = None) -> bytes:
        """Export report to PDF"""
        options = options or {}
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Determine page size
        page_size = A4 if options.get('page_size') == 'A4' else letter
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Add title page
        story.extend(self._create_title_page(report_data))
        
        # Add table of contents if requested
        if options.get('include_toc', True):
            story.append(PageBreak())
            story.extend(self._create_toc(report_data))
        
        # Add report blocks
        for block in report_data.get('blocks', []):
            story.append(PageBreak())
            story.extend(await self._render_block(block, options))
        
        # Add metadata page
        if options.get('include_metadata', True):
            story.append(PageBreak())
            story.extend(self._create_metadata_page(report_data))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_header_footer,
                 onLaterPages=self._add_header_footer)
        
        # Get PDF bytes
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        
        # Add watermark if requested
        if options.get('watermark'):
            pdf_bytes = self._add_watermark(pdf_bytes, options['watermark'])
        
        return pdf_bytes
    
    def _create_title_page(self, report_data: Dict[str, Any]) -> list:
        """Create title page elements"""
        elements = []
        
        # Title
        title = Paragraph(
            "ViolentUTF Security Operations Report",
            self.styles['CustomTitle']
        )
        elements.append(title)
        
        # Subtitle with date
        metadata = report_data.get('metadata', {})
        date = report_data.get('parameters', {}).get('report_date', datetime.now().strftime('%Y-%m-%d'))
        subtitle = Paragraph(
            f"Close of Business Report<br/>{date}",
            self.styles['Title']
        )
        elements.append(subtitle)
        
        elements.append(Spacer(1, 2*inch))
        
        # Report info table
        info_data = [
            ['Report Type:', metadata.get('name', 'COB Report')],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Template Version:', metadata.get('version', '1.0')],
            ['Classification:', options.get('classification', 'CONFIDENTIAL')]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(info_table)
        
        return elements
    
    def _create_toc(self, report_data: Dict[str, Any]) -> list:
        """Create table of contents"""
        elements = []
        
        toc_title = Paragraph("Table of Contents", self.styles['Heading1'])
        elements.append(toc_title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Build TOC entries
        toc_data = []
        page_num = 3  # Starting page after title and TOC
        
        for i, block in enumerate(report_data.get('blocks', [])):
            toc_data.append([
                f"{i+1}. {block.get('title', 'Untitled')}",
                str(page_num)
            ])
            page_num += 1
        
        toc_table = Table(toc_data, colWidths=[5*inch, 1*inch])
        toc_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(toc_table)
        
        return elements
    
    async def _render_block(self, block: Dict[str, Any], 
                           options: Dict[str, Any]) -> list:
        """Render a report block to PDF elements"""
        elements = []
        
        # Block title
        title = Paragraph(block.get('title', ''), self.styles['SectionHeader'])
        elements.append(title)
        
        # Render based on block type
        block_type = block.get('type')
        
        if block_type == 'data':
            elements.extend(self._render_data_block(block))
        elif block_type == 'analysis':
            elements.extend(self._render_analysis_block(block))
        elif block_type == 'visualization':
            if options.get('include_charts', True):
                elements.extend(await self._render_visualization_block(block))
        elif block_type == 'custom':
            elements.extend(self._render_custom_block(block))
        
        return elements
    
    def _render_data_block(self, block: Dict[str, Any]) -> list:
        """Render data block content"""
        elements = []
        
        # Parse content as markdown and convert to PDF elements
        content = block.get('content', '')
        
        # Simple markdown to PDF conversion
        # In production, use a proper markdown parser
        lines = content.split('\n')
        for line in lines:
            if line.startswith('###'):
                para = Paragraph(line[3:].strip(), self.styles['Heading3'])
            elif line.startswith('##'):
                para = Paragraph(line[2:].strip(), self.styles['Heading2'])
            elif line.startswith('#'):
                para = Paragraph(line[1:].strip(), self.styles['Heading1'])
            elif line.strip().startswith('|'):
                # Handle tables
                continue  # Skip for now, would parse table
            else:
                para = Paragraph(line, self.styles['Normal'])
            
            elements.append(para)
            elements.append(Spacer(1, 6))
        
        return elements
    
    def _render_analysis_block(self, block: Dict[str, Any]) -> list:
        """Render analysis block content"""
        elements = []
        
        # Add model info
        metadata = block.get('metadata', {})
        model_info = Paragraph(
            f"<i>Analysis by {metadata.get('model', 'AI Model')}</i>",
            self.styles['Italic']
        )
        elements.append(model_info)
        elements.append(Spacer(1, 12))
        
        # Add analysis content
        content = block.get('content', '')
        para = Paragraph(content.replace('\n', '<br/>'), self.styles['Normal'])
        elements.append(para)
        
        return elements
    
    async def _render_visualization_block(self, block: Dict[str, Any]) -> list:
        """Render visualization block with charts"""
        elements = []
        
        chart_config = block.get('chart_config', {})
        chart_type = chart_config.get('type', 'line')
        
        # Generate chart
        fig, ax = plt.subplots(figsize=(6, 4))
        
        if chart_type == 'line':
            # Sample line chart rendering
            data = chart_config.get('data', {})
            if 'labels' in data and 'datasets' in data:
                for dataset in data['datasets']:
                    ax.plot(data['labels'], dataset['data'], 
                           label=dataset.get('label', ''))
                ax.legend()
        
        # Save chart to buffer
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', dpi=150, bbox_inches='tight')
        chart_buffer.seek(0)
        plt.close()
        
        # Add chart to PDF
        from reportlab.platypus import Image
        chart_image = Image(chart_buffer, width=6*inch, height=4*inch)
        elements.append(chart_image)
        
        return elements
    
    def _render_custom_block(self, block: Dict[str, Any]) -> list:
        """Render custom block content"""
        elements = []
        
        content = block.get('content', '')
        para = Paragraph(content.replace('\n', '<br/>'), self.styles['Normal'])
        elements.append(para)
        
        return elements
    
    def _create_metadata_page(self, report_data: Dict[str, Any]) -> list:
        """Create metadata page"""
        elements = []
        
        title = Paragraph("Report Metadata", self.styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Metadata table
        metadata = report_data.get('metadata', {})
        meta_data = [
            ['Template ID:', metadata.get('id', 'N/A')],
            ['Template Name:', metadata.get('name', 'N/A')],
            ['Version:', metadata.get('version', 'N/A')],
            ['Author:', metadata.get('author', 'N/A')],
            ['Created:', metadata.get('created_at', 'N/A')],
            ['Generated:', report_data.get('rendered_at', 'N/A')],
        ]
        
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        
        elements.append(meta_table)
        
        return elements
    
    def _add_header_footer(self, canvas_obj, doc):
        """Add header and footer to pages"""
        canvas_obj.saveState()
        
        # Header
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawString(inch, letter[1] - 0.5*inch, 
                            "ViolentUTF Security Operations")
        canvas_obj.drawRightString(letter[0] - inch, letter[1] - 0.5*inch,
                                 datetime.now().strftime('%Y-%m-%d'))
        
        # Footer
        canvas_obj.drawString(inch, 0.5*inch, "CONFIDENTIAL")
        canvas_obj.drawRightString(letter[0] - inch, 0.5*inch,
                                 f"Page {doc.page}")
        
        # Line separators
        canvas_obj.line(inch, letter[1] - 0.6*inch, 
                       letter[0] - inch, letter[1] - 0.6*inch)
        canvas_obj.line(inch, 0.7*inch, letter[0] - inch, 0.7*inch)
        
        canvas_obj.restoreState()
    
    def _add_watermark(self, pdf_bytes: bytes, watermark_text: str) -> bytes:
        """Add watermark to PDF pages"""
        # Implementation would use PyPDF2 or similar to add watermark
        # For now, return original bytes
        return pdf_bytes
```

### 3.5 API Endpoints

```python
# violentutf_api/fastapi_app/app/api/endpoints/cob_reports.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
from ....core.reports.templates.base import ReportTemplate
from ....core.reports.templates.manager import TemplateManager
from ....core.reports.generator import ReportGenerator
from ....auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/cob", tags=["cob_reports"])

class TemplateCreate(BaseModel):
    """Template creation request"""
    name: str
    version: str
    description: Optional[str]
    template_config: Dict[str, Any]
    
class TemplateUpdate(BaseModel):
    """Template update request"""
    name: Optional[str]
    version: Optional[str]
    description: Optional[str]
    template_config: Optional[Dict[str, Any]]
    is_active: Optional[bool]

class ReportGenerateRequest(BaseModel):
    """Report generation request"""
    template_id: str
    report_date: date = Field(default_factory=date.today)
    parameters: Dict[str, Any] = {}
    export_formats: List[str] = ["markdown"]
    
class ReportExportRequest(BaseModel):
    """Report export request"""
    format: str
    options: Dict[str, Any] = {}

class ReportScheduleRequest(BaseModel):
    """Report schedule request"""
    template_id: str
    frequency: str = Field(..., regex="^(daily|weekly|monthly)$")
    time: str = Field(..., regex="^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = "UTC"
    parameters: Dict[str, Any] = {}
    export_formats: List[str] = ["markdown", "pdf"]
    distribution: Dict[str, List[str]] = {}

# Template endpoints
@router.post("/templates", response_model=Dict[str, Any])
async def create_template(
    template_data: TemplateCreate,
    current_user = Depends(get_current_user)
):
    """Create a new report template"""
    try:
        template_manager = TemplateManager()
        template = await template_manager.create_template(
            name=template_data.name,
            version=template_data.version,
            description=template_data.description,
            config=template_data.template_config,
            author=current_user["username"]
        )
        return {"id": template.id, "message": "Template created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_templates(
    active_only: bool = True,
    current_user = Depends(get_current_user)
):
    """List available report templates"""
    template_manager = TemplateManager()
    templates = await template_manager.list_templates(active_only=active_only)
    return templates

@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Get specific template details"""
    template_manager = TemplateManager()
    template = await template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()

@router.put("/templates/{template_id}", response_model=Dict[str, Any])
async def update_template(
    template_id: str,
    update_data: TemplateUpdate,
    current_user = Depends(get_current_user)
):
    """Update existing template"""
    template_manager = TemplateManager()
    success = await template_manager.update_template(
        template_id=template_id,
        updates=update_data.dict(exclude_unset=True)
    )
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template updated successfully"}

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Delete template (soft delete)"""
    template_manager = TemplateManager()
    success = await template_manager.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}

@router.post("/templates/{template_id}/clone", response_model=Dict[str, Any])
async def clone_template(
    template_id: str,
    new_name: str,
    current_user = Depends(get_current_user)
):
    """Clone existing template"""
    template_manager = TemplateManager()
    new_template = await template_manager.clone_template(
        template_id=template_id,
        new_name=new_name,
        author=current_user["username"]
    )
    if not new_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": new_template.id, "message": "Template cloned successfully"}

@router.get("/templates/{template_id}/preview", response_model=Dict[str, Any])
async def preview_template(
    template_id: str,
    sample_data: bool = True,
    current_user = Depends(get_current_user)
):
    """Preview template with sample data"""
    template_manager = TemplateManager()
    generator = ReportGenerator()
    
    template = await template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate sample data if requested
    if sample_data:
        data = await generator.generate_sample_data()
    else:
        data = {}
    
    # Render preview
    preview = await template.render(data)
    return preview

# Report generation endpoints
@router.post("/reports/generate", response_model=Dict[str, Any])
async def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Generate a new COB report"""
    try:
        generator = ReportGenerator()
        
        # Generate report
        report_id = await generator.generate_report(
            template_id=request.template_id,
            report_date=request.report_date,
            parameters=request.parameters,
            user_id=current_user["user_id"]
        )
        
        # Queue export tasks
        for format in request.export_formats:
            background_tasks.add_task(
                generator.export_report,
                report_id=report_id,
                format=format
            )
        
        return {
            "report_id": report_id,
            "message": "Report generation started",
            "export_formats": request.export_formats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports", response_model=List[Dict[str, Any]])
async def list_reports(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    template_id: Optional[str] = None,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """List generated reports"""
    generator = ReportGenerator()
    reports = await generator.list_reports(
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        template_id=template_id,
        limit=limit
    )
    return reports

@router.get("/reports/{report_id}", response_model=Dict[str, Any])
async def get_report(
    report_id: str,
    current_user = Depends(get_current_user)
):
    """Get specific report details"""
    generator = ReportGenerator()
    report = await generator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.post("/reports/{report_id}/export", response_model=Dict[str, Any])
async def export_report(
    report_id: str,
    request: ReportExportRequest,
    current_user = Depends(get_current_user)
):
    """Export report in specific format"""
    generator = ReportGenerator()
    
    try:
        export_url = await generator.export_report(
            report_id=report_id,
            format=request.format,
            options=request.options
        )
        
        return {
            "export_url": export_url,
            "format": request.format,
            "expires_at": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/{report_id}/distribute", response_model=Dict[str, Any])
async def distribute_report(
    report_id: str,
    channels: Dict[str, List[str]],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Distribute report to specified channels"""
    generator = ReportGenerator()
    
    # Queue distribution task
    background_tasks.add_task(
        generator.distribute_report,
        report_id=report_id,
        channels=channels,
        user_id=current_user["user_id"]
    )
    
    return {
        "message": "Report distribution started",
        "channels": list(channels.keys())
    }

# Scheduling endpoints
@router.post("/schedules", response_model=Dict[str, Any])
async def create_schedule(
    schedule: ReportScheduleRequest,
    current_user = Depends(get_current_user)
):
    """Create report generation schedule"""
    from ....core.reports.scheduler import ReportScheduler
    
    scheduler = ReportScheduler()
    schedule_id = await scheduler.create_schedule(
        template_id=schedule.template_id,
        frequency=schedule.frequency,
        time=schedule.time,
        timezone=schedule.timezone,
        parameters=schedule.parameters,
        export_formats=schedule.export_formats,
        distribution=schedule.distribution,
        user_id=current_user["user_id"]
    )
    
    return {
        "schedule_id": schedule_id,
        "message": "Schedule created successfully"
    }

@router.get("/schedules", response_model=List[Dict[str, Any]])
async def list_schedules(
    active_only: bool = True,
    current_user = Depends(get_current_user)
):
    """List report schedules"""
    from ....core.reports.scheduler import ReportScheduler
    
    scheduler = ReportScheduler()
    schedules = await scheduler.list_schedules(
        user_id=current_user["user_id"],
        active_only=active_only
    )
    return schedules

@router.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    updates: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """Update report schedule"""
    from ....core.reports.scheduler import ReportScheduler
    
    scheduler = ReportScheduler()
    success = await scheduler.update_schedule(
        schedule_id=schedule_id,
        updates=updates
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"message": "Schedule updated successfully"}

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user = Depends(get_current_user)
):
    """Delete report schedule"""
    from ....core.reports.scheduler import ReportScheduler
    
    scheduler = ReportScheduler()
    success = await scheduler.delete_schedule(schedule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"message": "Schedule deleted successfully"}
```

## 4. Database Migrations

```sql
-- migrations/001_cob_report_tables.sql

-- Create enum types
CREATE TYPE report_export_format AS ENUM ('markdown', 'pdf', 'json');
CREATE TYPE schedule_frequency AS ENUM ('daily', 'weekly', 'monthly');

-- Report templates table
CREATE TABLE IF NOT EXISTS cob_report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    author VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    template_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    permissions JSONB DEFAULT '{"read": ["all_users"], "write": ["admin"]}'::jsonb,
    
    -- Indexes
    CONSTRAINT unique_template_name_version UNIQUE (name, version)
);

CREATE INDEX idx_templates_active ON cob_report_templates(is_active);
CREATE INDEX idx_templates_metadata ON cob_report_templates USING gin(metadata);

-- Template versions for history
CREATE TABLE IF NOT EXISTS cob_template_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES cob_report_templates(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL,
    change_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    -- Ensure unique version numbers per template
    CONSTRAINT unique_template_version UNIQUE (template_id, version_number)
);

-- Generated reports archive
CREATE TABLE IF NOT EXISTS cob_generated_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES cob_report_templates(id),
    template_snapshot JSONB NOT NULL, -- Store template at generation time
    report_date DATE NOT NULL,
    shift_name VARCHAR(100),
    operator VARCHAR(255),
    parameters JSONB DEFAULT '{}'::jsonb,
    report_data JSONB,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generated_by UUID, -- User ID
    processing_time_ms INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    -- Indexes
    INDEX idx_reports_date (report_date DESC),
    INDEX idx_reports_template (template_id),
    INDEX idx_reports_status (status)
);

-- Report exports tracking
CREATE TABLE IF NOT EXISTS cob_report_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES cob_generated_reports(id) ON DELETE CASCADE,
    format report_export_format NOT NULL,
    export_options JSONB DEFAULT '{}'::jsonb,
    file_path TEXT,
    file_size_bytes BIGINT,
    exported_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_exports_report (report_id),
    INDEX idx_exports_expires (expires_at)
);

-- Report schedules
CREATE TABLE IF NOT EXISTS cob_report_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES cob_report_templates(id),
    name VARCHAR(255),
    frequency schedule_frequency NOT NULL,
    schedule_time TIME NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    parameters JSONB DEFAULT '{}'::jsonb,
    export_formats report_export_format[] DEFAULT ARRAY['markdown']::report_export_format[],
    distribution_config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_schedules_active (is_active),
    INDEX idx_schedules_next_run (next_run_at)
);

-- Schedule execution history
CREATE TABLE IF NOT EXISTS cob_schedule_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES cob_report_schedules(id) ON DELETE CASCADE,
    report_id UUID REFERENCES cob_generated_reports(id),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    
    -- Indexes
    INDEX idx_executions_schedule (schedule_id, executed_at DESC)
);

-- Template usage analytics
CREATE TABLE IF NOT EXISTS cob_template_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES cob_report_templates(id) ON DELETE CASCADE,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id UUID,
    action VARCHAR(50), -- 'generate', 'preview', 'export', etc.
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_cob_report_templates_updated_at BEFORE UPDATE
    ON cob_report_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_cob_report_schedules_updated_at BEFORE UPDATE
    ON cob_report_schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/test_cob_template_system.py

import pytest
from datetime import datetime
from violentutf.core.reports.templates.base import ReportTemplate, TemplateMetadata, BlockConfig

class TestReportTemplate:
    """Test report template functionality"""
    
    @pytest.fixture
    def sample_template_config(self):
        return {
            "metadata": {
                "id": "test_template",
                "name": "Test Template",
                "version": "1.0",
                "author": "test_user"
            },
            "parameters": {
                "report_date": {"type": "date", "required": True}
            },
            "blocks": [
                {
                    "id": "test_block",
                    "type": "data_block",
                    "order": 1,
                    "title": "Test Block",
                    "template": "Test: {{value}}"
                }
            ]
        }
    
    def test_template_initialization(self, sample_template_config):
        """Test template initialization"""
        template = ReportTemplate(sample_template_config)
        
        assert template.metadata.name == "Test Template"
        assert len(template.blocks) == 1
        assert template.blocks[0].type == "data_block"
    
    @pytest.mark.asyncio
    async def test_template_rendering(self, sample_template_config):
        """Test template rendering"""
        template = ReportTemplate(sample_template_config)
        
        data = {"value": "Hello World"}
        params = {"report_date": "2024-01-15"}
        
        result = await template.render(data, params)
        
        assert result["metadata"]["name"] == "Test Template"
        assert len(result["blocks"]) == 1
        assert "Hello World" in result["blocks"][0]["content"]

class TestBlockRenderers:
    """Test block renderer implementations"""
    
    @pytest.mark.asyncio
    async def test_data_block_renderer(self):
        """Test data block rendering"""
        from violentutf.core.reports.templates.blocks import DataBlockRenderer
        import jinja2
        
        env = jinja2.Environment()
        renderer = DataBlockRenderer(env)
        
        block_config = BlockConfig(
            id="test",
            type="data_block",
            order=1,
            title="Test Data",
            template="Value: {{test_value}}"
        )
        
        data = {"test_value": 42}
        result = await renderer.render(block_config, data, {})
        
        assert result["type"] == "data"
        assert "Value: 42" in result["content"]
    
    @pytest.mark.asyncio
    async def test_analysis_block_renderer(self, mocker):
        """Test AI analysis block rendering"""
        from violentutf.core.reports.templates.blocks import AnalysisBlockRenderer
        import jinja2
        
        # Mock AI analyzer
        mock_ai_response = {
            "content": "AI analysis result",
            "model": "gpt-3.5-turbo",
            "usage": {"total_tokens": 100}
        }
        
        mocker.patch(
            'violentutf.core.reports.analysis.ai_analyzer.AIAnalyzer.analyze',
            return_value=mock_ai_response
        )
        
        env = jinja2.Environment()
        renderer = AnalysisBlockRenderer(env)
        
        block_config = BlockConfig(
            id="ai_test",
            type="analysis_block",
            order=1,
            title="AI Analysis",
            config={
                "prompt_template": "Analyze: {{data}}",
                "model": "gpt-3.5-turbo"
            }
        )
        
        data = {"data": "test data"}
        result = await renderer.render(block_config, data, {})
        
        assert result["type"] == "analysis"
        assert result["content"] == "AI analysis result"
        assert result["metadata"]["tokens_used"] == 100
```

### 5.2 Integration Tests

```python
# tests/test_cob_integration.py

import pytest
from fastapi.testclient import TestClient
from datetime import date

class TestCOBReportIntegration:
    """Integration tests for COB report system"""
    
    @pytest.fixture
    def client(self):
        from violentutf_api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        # Get auth token
        response = client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_template_lifecycle(self, client, auth_headers):
        """Test complete template lifecycle"""
        # Create template
        template_data = {
            "name": "Integration Test Template",
            "version": "1.0",
            "description": "Test template",
            "template_config": {
                "blocks": [
                    {
                        "id": "test_block",
                        "type": "data_block",
                        "order": 1,
                        "title": "Test",
                        "template": "Test content"
                    }
                ]
            }
        }
        
        response = client.post(
            "/api/v1/cob/templates",
            json=template_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        template_id = response.json()["id"]
        
        # List templates
        response = client.get("/api/v1/cob/templates", headers=auth_headers)
        assert response.status_code == 200
        templates = response.json()
        assert any(t["id"] == template_id for t in templates)
        
        # Get specific template
        response = client.get(
            f"/api/v1/cob/templates/{template_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Integration Test Template"
        
        # Update template
        update_data = {"description": "Updated description"}
        response = client.put(
            f"/api/v1/cob/templates/{template_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Delete template
        response = client.delete(
            f"/api/v1/cob/templates/{template_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_report_generation(self, client, auth_headers):
        """Test report generation and export"""
        # First create a template
        template_response = client.post(
            "/api/v1/cob/templates",
            json={
                "name": "Report Test Template",
                "version": "1.0",
                "template_config": {"blocks": []}
            },
            headers=auth_headers
        )
        template_id = template_response.json()["id"]
        
        # Generate report
        report_data = {
            "template_id": template_id,
            "report_date": str(date.today()),
            "parameters": {"shift": "Day"},
            "export_formats": ["markdown", "pdf"]
        }
        
        response = client.post(
            "/api/v1/cob/reports/generate",
            json=report_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        report_id = response.json()["report_id"]
        
        # Get report
        response = client.get(
            f"/api/v1/cob/reports/{report_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Export report
        export_data = {
            "format": "pdf",
            "options": {"watermark": "TEST"}
        }
        
        response = client.post(
            f"/api/v1/cob/reports/{report_id}/export",
            json=export_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "export_url" in response.json()
```

## 6. UI Implementation Notes

### 6.1 Scheduling Interface (PRIORITY)

The scheduling interface is the most critical UI component:

1. **Schedule Management Dashboard**
   ```python
   # Streamlit UI for schedule management
   st.header("📅 Report Scheduling")
   
   col1, col2 = st.columns([2, 1])
   
   with col1:
       # Active schedules list
       st.subheader("Active Schedules")
       schedules_df = load_active_schedules()
       
       # Display with actions
       for idx, schedule in schedules_df.iterrows():
           with st.expander(f"{schedule['template_name']} - {schedule['frequency']}"):
               st.write(f"**Next Run**: {schedule['next_run_at']}")
               st.write(f"**Time**: {schedule['schedule_time']} {schedule['timezone']}")
               st.write(f"**Formats**: {', '.join(schedule['export_formats'])}")
               
               col_a, col_b, col_c = st.columns(3)
               with col_a:
                   if st.button("⏸️ Pause", key=f"pause_{idx}"):
                       pause_schedule(schedule['id'])
               with col_b:
                   if st.button("▶️ Run Now", key=f"run_{idx}"):
                       execute_schedule_now(schedule['id'])
               with col_c:
                   if st.button("🗑️ Delete", key=f"del_{idx}"):
                       delete_schedule(schedule['id'])
   
   with col2:
       # Quick schedule creation
       st.subheader("Quick Schedule")
       
       template = st.selectbox("Template", available_templates)
       frequency = st.radio("Frequency", ["Daily", "Weekly", "Monthly"])
       
       if frequency == "Daily":
           time = st.time_input("Time", datetime.time(18, 0))
       elif frequency == "Weekly":
           day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", 
                                     "Thursday", "Friday"])
           time = st.time_input("Time", datetime.time(9, 0))
       else:  # Monthly
           day = st.number_input("Day of Month", 1, 28, 1)
           time = st.time_input("Time", datetime.time(9, 0))
       
       timezone = st.selectbox("Timezone", pytz.all_timezones, 
                              index=pytz.all_timezones.index("America/New_York"))
       
       # Distribution
       st.write("**Distribution**")
       send_email = st.checkbox("Email")
       if send_email:
           emails = st.text_area("Recipients (one per line)")
       
       send_slack = st.checkbox("Slack")
       if send_slack:
           channels = st.text_input("Channels (comma-separated)")
       
       if st.button("Create Schedule", type="primary"):
           create_new_schedule(...)
   ```

2. **Schedule History View**
   - Execution history with status
   - Download past reports
   - Error logs and retry options
   - Performance metrics

3. **Schedule Templates**
   - Pre-configured schedule templates
   - "End of Day Report" preset
   - "Weekly Executive Brief" preset
   - "Monthly Compliance Report" preset

### 6.2 Template Builder Interface

The template builder should provide:

1. **Visual Editor**
   - Drag-and-drop block arrangement
   - Block property panels
   - Real-time preview
   - Template validation

2. **Block Library**
   - Pre-built block templates
   - Custom block creation
   - Import/export blocks

3. **Parameter Configuration**
   - Define template parameters
   - Set validation rules
   - Default values

### 6.3 Report Generation UI

Enhanced controls in Dashboard:

1. **Template Selection**
   - Dropdown with template preview
   - Template info display
   - Version selection

2. **Parameter Input**
   - Dynamic form based on template
   - Validation feedback
   - Parameter presets

3. **Export Options**
   - Format selection (Markdown, PDF, JSON)
   - Format-specific options
   - Batch export

4. **Preview & Generate**
   - Live preview
   - Generation progress
   - Download management

## 7. Deployment Considerations

### 7.1 Performance

- Template caching
- Async report generation
- Background export processing
- CDN for static assets

### 7.2 Scalability

- Queue-based processing
- Horizontal scaling for workers
- Database connection pooling
- Redis for caching

### 7.3 Security

- Template sandboxing
- Input validation
- Access control
- Audit logging

## 8. Conclusion

This implementation guide provides a comprehensive framework for enhancing the COB report system with:

- Flexible template-driven architecture
- AI-powered analysis capabilities
- Multiple export formats
- Advanced scheduling and distribution

The phased approach ensures smooth implementation while delivering value at each milestone.