"""
Report generation engine for creating reports from templates
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import markdown
from app.db.database import get_session
from app.models.cob_models import COBReport, COBTemplate
from app.models.orchestrator import OrchestratorExecution

# Import extended models and services
from app.models.report_system.report_models import COBScanDataCache
from app.schemas.report_system.report_schemas import (
    OutputFormat,
    PreviewRequest,
    PreviewResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
    ReportStatus,
)
from app.services.storage_service import StorageService
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from .block_base import BaseReportBlock, block_registry
from .block_implementations import register_all_blocks
from .template_service import TemplateService

logger = logging.getLogger(__name__)

# Register all block types
register_all_blocks(block_registry)


class ReportGenerationEngine:
    """Engine for generating reports from templates"""

    def __init__(self, db: AsyncSession, storage_service: StorageService):
        self.db = db
        self.storage = storage_service
        self.template_service = TemplateService(db)
        self._jinja_env = self._setup_jinja_env()
        self._font_config = FontConfiguration()

        # Report generation queue (in production, use Redis or similar)
        self._generation_queue = asyncio.Queue()
        self._active_generations = {}

    def _setup_jinja_env(self) -> Environment:
        """Setup Jinja2 environment"""
        # In production, templates would be in a proper directory
        env = Environment(autoescape=select_autoescape(["html", "xml"]))

        # Add custom filters
        env.filters["format_date"] = lambda d: d.strftime("%B %d, %Y") if d else ""
        env.filters["format_number"] = lambda n, d=1: f"{n:.{d}f}" if isinstance(n, (int, float)) else str(n)
        env.filters["severity_color"] = self._get_severity_color

        return env

    async def generate_report(self, request: ReportGenerationRequest, user_id: str) -> ReportGenerationResponse:
        """Generate a report based on request"""
        try:
            # Validate template exists
            template = self.template_service.get_template(request.template_id)

            # Validate scan data exists
            scan_data = await self._load_scan_data(request.scan_data_ids)
            if not scan_data:
                raise HTTPException(status_code=400, detail="No valid scan data found")

            # Create report record
            report_id = str(uuid.uuid4())
            report = COBReport(
                id=report_id,
                name=request.report_name or f"Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                template_id=request.template_id,
                config={
                    "scan_data_ids": request.scan_data_ids,
                    "output_formats": [f.value for f in request.output_formats],
                    "configuration_overrides": request.configuration_overrides,
                },
                created_by=user_id,
                status="pending" if not request.preview_mode else "preview",
            )

            self.db.add(report)
            self.db.commit()

            # Queue generation task
            generation_task = {
                "report_id": report_id,
                "template": template.dict(),
                "scan_data": scan_data,
                "output_formats": request.output_formats,
                "configuration_overrides": request.configuration_overrides,
                "preview_mode": request.preview_mode,
                "user_id": user_id,
            }

            if request.preview_mode:
                # For preview, generate synchronously
                await self._process_report_generation(generation_task)
                estimated_time = 5
            else:
                # Queue for async processing
                await self._generation_queue.put(generation_task)
                estimated_time = self._estimate_generation_time(template, scan_data)

            return ReportGenerationResponse(
                report_id=report_id,
                status="pending" if not request.preview_mode else "processing",
                estimated_time=estimated_time,
                preview_mode=request.preview_mode,
                queue_position=self._generation_queue.qsize() if not request.preview_mode else None,
                created_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error initiating report generation: {str(e)}")
            raise

    async def generate_preview(self, request: PreviewRequest, user_id: str) -> PreviewResponse:
        """Generate a preview of a single block or template"""
        try:
            start_time = datetime.now()

            # Create temporary template config
            if request.block_id:
                # Preview single block
                blocks = [b for b in request.template_config.get("blocks", []) if b.get("id") == request.block_id]
                if not blocks:
                    raise HTTPException(status_code=400, detail=f"Block not found: {request.block_id}")
                template_config = {"blocks": blocks}
            else:
                template_config = request.template_config

            # Process blocks
            rendered_blocks = []
            warnings = []

            for block_config in template_config.get("blocks", []):
                try:
                    block = self._create_block_instance(block_config)

                    # Render block
                    if request.output_format == OutputFormat.HTML:
                        content = block.render("HTML", request.sample_data)
                    else:
                        content = block.render("Markdown", request.sample_data)

                    rendered_blocks.append(content)

                except Exception as e:
                    logger.warning(f"Error rendering block {block_config.get('id')}: {str(e)}")
                    warnings.append(f"Block '{block_config.get('id')}' rendering error: {str(e)}")

            # Combine rendered content
            if request.output_format == OutputFormat.HTML:
                combined_content = self._combine_html_blocks(rendered_blocks)
                estimated_pages = self._estimate_pdf_pages(combined_content)
            else:
                combined_content = "\n\n".join(rendered_blocks)
                estimated_pages = max(1, len(combined_content) // 3000)  # Rough estimate

            processing_time = (datetime.now() - start_time).total_seconds()

            return PreviewResponse(
                html_content=combined_content if request.output_format == OutputFormat.HTML else None,
                markdown_content=combined_content if request.output_format != OutputFormat.HTML else None,
                estimated_pages=estimated_pages,
                warnings=warnings,
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            raise

    async def get_report_status(self, report_id: str) -> ReportStatus:
        """Get the status of a report generation"""
        report = self.db.query(COBReport).filter(COBReport.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")

        # Get generation progress if active
        progress_info = self._active_generations.get(report_id, {})

        outputs = None
        if report.status == "completed":
            # Get output file info
            outputs = {}
            for format_type in report.config.get("output_formats", []):
                file_key = f"reports/{report_id}/{report_id}.{format_type.lower()}"
                if self.storage.file_exists(file_key):
                    outputs[format_type] = {
                        "url": self.storage.get_download_url(file_key),
                        "size": self.storage.get_file_size(file_key),
                    }

        return ReportStatus(
            report_id=report_id,
            status=report.status,
            progress=progress_info.get("progress", 0),
            current_stage=progress_info.get("stage"),
            error_message=report.error_message if hasattr(report, "error_message") else None,
            outputs=outputs,
            completed_at=report.updated_at if report.status == "completed" else None,
        )

    async def _process_report_generation(self, task: Dict[str, Any]) -> None:
        """Process a report generation task"""
        report_id = task["report_id"]

        try:
            # Update status
            self._update_report_status(report_id, "processing", 0, "Initializing")

            # Load template and create blocks
            template = task["template"]
            blocks = self._create_report_blocks(template["config"], task.get("configuration_overrides"))

            # Merge scan data
            merged_data = self._merge_scan_data(task["scan_data"])

            # Add report metadata
            merged_data.update(
                {"report_date": datetime.now(), "report_id": report_id, "template_name": template["name"]}
            )

            # Process each output format
            outputs = {}
            total_formats = len(task["output_formats"])

            for idx, output_format in enumerate(task["output_formats"]):
                progress = 20 + (60 * idx // total_formats)
                self._update_report_status(report_id, "processing", progress, f"Generating {output_format.value}")

                # Generate report in format
                output_path = await self._generate_format(report_id, blocks, merged_data, output_format, template)

                outputs[output_format.value] = output_path

            # Upload to storage
            self._update_report_status(report_id, "processing", 85, "Uploading files")

            for format_type, file_path in outputs.items():
                if file_path and os.path.exists(file_path):
                    storage_key = f"reports/{report_id}/{report_id}.{format_type.lower()}"
                    await self.storage.upload_file_async(file_path, storage_key)

                    # Clean up temp file
                    os.remove(file_path)

            # Update report status
            self._update_report_status(report_id, "completed", 100, "Report generation complete")

            # Update usage statistics
            self._update_template_usage(template["id"])

        except Exception as e:
            logger.error(f"Error processing report {report_id}: {str(e)}")
            self._update_report_status(report_id, "failed", 0, f"Generation failed: {str(e)}")
            raise
        finally:
            # Clean up active generation tracking
            if report_id in self._active_generations:
                del self._active_generations[report_id]

    def _create_report_blocks(self, template_config: Dict, overrides: Optional[Dict] = None) -> List[BaseReportBlock]:
        """Create block instances from template configuration"""
        blocks = []

        for block_config in template_config.get("blocks", []):
            # Apply overrides if provided
            if overrides and block_config["id"] in overrides:
                config_copy = block_config.copy()
                config_copy["configuration"].update(overrides[block_config["id"]])
                block_config = config_copy

            block = self._create_block_instance(block_config)
            blocks.append(block)

        # Sort by order
        blocks.sort(key=lambda b: getattr(b, "_order", 999))

        return blocks

    def _create_block_instance(self, block_config: Dict) -> BaseReportBlock:
        """Create a single block instance"""
        block_type = block_config.get("type")
        if not block_type:
            raise HTTPException(status_code=400, detail="Block configuration missing 'type'")

        block = block_registry.create_block(
            block_type=block_type,
            block_id=block_config.get("id", f"{block_type}_{uuid.uuid4().hex[:8]}"),
            title=block_config.get("title", ""),
            configuration=block_config.get("configuration", {}),
        )

        # Store order for sorting
        block._order = block_config.get("order", 999)

        return block

    async def _generate_format(
        self,
        report_id: str,
        blocks: List[BaseReportBlock],
        data: Dict[str, Any],
        output_format: OutputFormat,
        template: Dict,
    ) -> Optional[str]:
        """Generate report in specific format"""
        temp_dir = tempfile.mkdtemp()

        try:
            if output_format == OutputFormat.PDF:
                return await self._generate_pdf(report_id, blocks, data, template, temp_dir)
            elif output_format == OutputFormat.JSON:
                return await self._generate_json(report_id, blocks, data, template, temp_dir)
            elif output_format == OutputFormat.MARKDOWN:
                return await self._generate_markdown(report_id, blocks, data, template, temp_dir)
            elif output_format == OutputFormat.HTML:
                return await self._generate_html(report_id, blocks, data, template, temp_dir)
            else:
                logger.warning(f"Unsupported format: {output_format}")
                return None

        except Exception as e:
            logger.error(f"Error generating {output_format} for report {report_id}: {str(e)}")
            raise

    async def _generate_pdf(
        self, report_id: str, blocks: List[BaseReportBlock], data: Dict, template: Dict, temp_dir: str
    ) -> str:
        """Generate PDF report"""
        # First generate HTML
        html_content = await self._generate_html_content(blocks, data, template)

        # Apply CSS styling
        css = self._get_report_css()

        # Generate PDF
        output_path = os.path.join(temp_dir, f"{report_id}.pdf")

        HTML(string=html_content, base_url=temp_dir).write_pdf(
            output_path, stylesheets=[CSS(string=css)], font_config=self._font_config
        )

        return output_path

    async def _generate_html(
        self, report_id: str, blocks: List[BaseReportBlock], data: Dict, template: Dict, temp_dir: str
    ) -> str:
        """Generate HTML report"""
        html_content = await self._generate_html_content(blocks, data, template)

        # Add inline CSS
        css = self._get_report_css()
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{template.get('name', 'Report')} - {report_id}</title>
            <style>{css}</style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        output_path = os.path.join(temp_dir, f"{report_id}.html")
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(full_html)

        return output_path

    async def _generate_html_content(self, blocks: List[BaseReportBlock], data: Dict, template: Dict) -> str:
        """Generate HTML content from blocks"""
        html_parts = []

        # Header
        html_parts.append(
            f"""
        <div class="report-header">
            <h1>{template.get('name', 'Report')}</h1>
            <div class="report-meta">
                <span>Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}</span>
                <span>Report ID: {data.get('report_id', 'N/A')}</span>
            </div>
        </div>
        """
        )

        # Render each block
        for block in blocks:
            try:
                content = block.render("HTML", data)
                html_parts.append(f'<div class="report-block">{content}</div>')
            except Exception as e:
                logger.error(f"Error rendering block {block.block_id}: {str(e)}")
                html_parts.append(
                    f"""
                <div class="report-block error">
                    <h3>Error rendering {block.title or block.block_id}</h3>
                    <p>An error occurred while generating this section.</p>
                </div>
                """
                )

        # Footer
        html_parts.append(
            """
        <div class="report-footer">
            <p>This report was generated automatically by ViolentUTF Report System</p>
        </div>
        """
        )

        return "\n".join(html_parts)

    async def _generate_markdown(
        self, report_id: str, blocks: List[BaseReportBlock], data: Dict, template: Dict, temp_dir: str
    ) -> str:
        """Generate Markdown report"""
        md_parts = []

        # Header
        md_parts.append(f"# {template.get('name', 'Report')}\n")
        md_parts.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}  ")
        md_parts.append(f"**Report ID:** {report_id}\n")
        md_parts.append("---\n")

        # Render each block
        for block in blocks:
            try:
                content = block.render("Markdown", data)
                md_parts.append(content)
                md_parts.append("\n---\n")
            except Exception as e:
                logger.error(f"Error rendering block {block.block_id}: {str(e)}")
                md_parts.append(f"### Error: {block.title or block.block_id}\n")
                md_parts.append("An error occurred while generating this section.\n")

        # Footer
        md_parts.append("\n---")
        md_parts.append("*This report was generated automatically by ViolentUTF Report System*")

        output_path = os.path.join(temp_dir, f"{report_id}.md")
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write("\n".join(md_parts))

        return output_path

    async def _generate_json(
        self, report_id: str, blocks: List[BaseReportBlock], data: Dict, template: Dict, temp_dir: str
    ) -> str:
        """Generate JSON report"""
        report_data = {
            "report_id": report_id,
            "template": {"id": template.get("id"), "name": template.get("name"), "version": template.get("version")},
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "scan_data_count": len(data.get("scan_data_ids", [])),
                "scanner_type": data.get("scanner_type"),
                "target_model": data.get("target_model"),
            },
            "blocks": [],
        }

        # Render each block
        for block in blocks:
            try:
                block_data = block.render("JSON", data)
                report_data["blocks"].append(block_data)
            except Exception as e:
                logger.error(f"Error rendering block {block.block_id}: {str(e)}")
                report_data["blocks"].append({"block_id": block.block_id, "error": str(e)})

        output_path = os.path.join(temp_dir, f"{report_id}.json")
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(report_data, indent=2, default=str))

        return output_path

    async def _load_scan_data(self, scan_data_ids: List[str]) -> List[Dict]:
        """Load scan data from OrchestratorExecution or cache"""
        scan_data = []

        for scan_id in scan_data_ids:
            # First check cache for pre-processed data
            cached = self.db.query(COBScanDataCache).filter(COBScanDataCache.execution_id == scan_id).first()

            if cached:
                data = {
                    "execution_id": cached.execution_id,
                    "scanner_type": cached.scanner_type,
                    "target_model": cached.target_model,
                    "scan_date": cached.scan_date,
                    **cached.score_data,
                }

                # Include raw results if available
                if cached.raw_results:
                    data.update(cached.raw_results)

                scan_data.append(data)
            else:
                # Try to load from OrchestratorExecution
                execution = self.db.query(OrchestratorExecution).filter(OrchestratorExecution.id == scan_id).first()

                if execution and execution.status == "completed":
                    # Process execution results
                    processed_data = self._process_execution_results(execution)
                    if processed_data:
                        scan_data.append(processed_data)
                        # Cache for future use
                        self._cache_execution_data(execution, processed_data)
                else:
                    logger.warning(f"Scan data not found: {scan_id}")

        return scan_data

    def _merge_scan_data(self, scan_data_list: List[Dict]) -> Dict[str, Any]:
        """Merge multiple scan data into single dataset"""
        if not scan_data_list:
            return {}

        if len(scan_data_list) == 1:
            return scan_data_list[0]

        # Merge multiple scans
        merged = {
            "scan_data_ids": [d.get("execution_id") for d in scan_data_list],
            "scanner_types": list(set(d.get("scanner_type") for d in scan_data_list)),
            "target_models": list(set(d.get("target_model") for d in scan_data_list)),
            "scan_dates": [d.get("scan_date") for d in scan_data_list],
            "earliest_scan": min(d.get("scan_date") for d in scan_data_list if d.get("scan_date")),
            "latest_scan": max(d.get("scan_date") for d in scan_data_list if d.get("scan_date")),
        }

        # Aggregate numeric metrics
        numeric_fields = [
            "total_tests",
            "successful_attacks",
            "failure_rate",
            "risk_score",
            "compliance_score",
            "total_vulnerabilities",
            "critical_count",
            "high_count",
            "medium_count",
            "low_count",
        ]

        for field in numeric_fields:
            values = [d.get(field, 0) for d in scan_data_list if field in d]
            if values:
                merged[field] = sum(values) / len(values)  # Average
                merged[f"{field}_min"] = min(values)
                merged[f"{field}_max"] = max(values)

        # Merge score summaries
        score_categories = ["toxicity", "bias", "jailbreak", "prompt_injection"]
        merged_scores = {}

        for category in score_categories:
            all_values = []
            for data in scan_data_list:
                if "score_summary" in data and category in data["score_summary"]:
                    summary = data["score_summary"][category]
                    if "mean" in summary and summary["mean"] > 0:
                        all_values.extend([summary["mean"]] * summary.get("count", 1))

            if all_values:
                merged_scores[category] = {
                    "mean": sum(all_values) / len(all_values),
                    "max": max(all_values),
                    "min": min(all_values),
                    "count": len(all_values),
                }
            else:
                merged_scores[category] = {"mean": 0, "max": 0, "min": 0, "count": 0}

        merged["score_summary"] = merged_scores

        # Combine lists
        list_fields = ["vulnerabilities", "findings", "attack_patterns"]
        for field in list_fields:
            merged[field] = []
            for d in scan_data_list:
                if field in d:
                    merged[field].extend(d[field])

        # Use first scan's data as primary
        merged.update(
            {
                "scanner_type": scan_data_list[0].get("scanner_type"),
                "target_model": scan_data_list[0].get("target_model"),
                "scan_date": scan_data_list[0].get("scan_date"),
            }
        )

        return merged

    def _update_report_status(self, report_id: str, status: str, progress: int, message: str) -> None:
        """Update report generation status"""
        # Update in database
        report = self.db.query(COBReport).filter(COBReport.id == report_id).first()

        if report:
            report.status = status
            if hasattr(report, "progress"):
                report.progress = progress
            if status == "failed" and hasattr(report, "error_message"):
                report.error_message = message
            report.updated_at = datetime.utcnow()
            self.db.commit()

        # Update active generation tracking
        self._active_generations[report_id] = {"progress": progress, "stage": message, "updated_at": datetime.utcnow()}

    def _update_template_usage(self, template_id: str) -> None:
        """Update template usage statistics"""
        template = self.db.query(COBTemplate).filter(COBTemplate.id == template_id).first()

        if template and template.metadata:
            metadata = template.metadata.copy()
            metadata["usage_count"] = metadata.get("usage_count", 0) + 1
            metadata["last_used"] = datetime.utcnow().isoformat()
            template.metadata = metadata
            self.db.commit()

    def _estimate_generation_time(self, template: Any, scan_data: List[Dict]) -> int:
        """Estimate report generation time in seconds"""
        base_time = 10  # Base processing time

        # Add time based on template complexity
        metadata = template.metadata if hasattr(template, "metadata") else {}
        complexity = metadata.get("complexity_level", "Intermediate")

        complexity_multiplier = {"Basic": 1, "Intermediate": 1.5, "Advanced": 2}.get(complexity, 1.5)

        # Add time based on data size
        data_size_factor = len(scan_data) * 2

        # Add time based on output formats
        format_time = len(template.config.get("output_formats", [])) * 5

        estimated = int(base_time * complexity_multiplier + data_size_factor + format_time)

        return min(estimated, 300)  # Cap at 5 minutes

    def _estimate_pdf_pages(self, html_content: str) -> int:
        """Estimate number of PDF pages from HTML content"""
        # Rough estimation based on content length and structure
        content_length = len(html_content)

        # Count major sections
        h2_count = html_content.count("<h2")
        table_count = html_content.count("<table")

        # Base calculation
        pages = 1 + (content_length // 5000)  # ~5000 chars per page
        pages += h2_count * 0.3  # New sections may cause page breaks
        pages += table_count * 0.5  # Tables take more space

        return max(1, int(pages))

    def _combine_html_blocks(self, blocks: List[str]) -> str:
        """Combine HTML blocks with proper structure"""
        return f"""
        <div class="report-preview">
            {''.join(f'<div class="preview-block">{block}</div>' for block in blocks)}
        </div>
        """

    def _get_severity_color(self, score: float) -> str:
        """Get color based on severity score"""
        if score >= 9.0:
            return "#d32f2f"
        elif score >= 7.0:
            return "#f57c00"
        elif score >= 4.0:
            return "#fbc02d"
        else:
            return "#388e3c"

    def _get_report_css(self) -> str:
        """Get CSS styles for reports"""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .report-header {
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .report-header h1 {
            margin: 0;
            color: #1976d2;
        }
        
        .report-meta {
            margin-top: 10px;
            color: #666;
            font-size: 0.9em;
        }
        
        .report-meta span {
            margin-right: 20px;
        }
        
        .report-block {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .executive-summary {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
        }
        
        .summary-components {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-card h3 {
            margin: 0 0 10px 0;
            font-size: 1.1em;
            color: #666;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .metric-label {
            font-size: 0.9em;
            color: #666;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background-color: #f5f5f5;
            font-weight: 600;
        }
        
        .risk-heatmap td {
            text-align: center;
            font-weight: bold;
        }
        
        .severity-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            color: white;
            font-size: 0.85em;
            margin-right: 10px;
        }
        
        .top-findings {
            margin-top: 30px;
        }
        
        .top-findings ul {
            list-style: none;
            padding: 0;
        }
        
        .top-findings li {
            margin-bottom: 10px;
            padding: 10px;
            background: #f9f9f9;
            border-left: 4px solid #1976d2;
        }
        
        .ai-analysis-block {
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
        }
        
        .analysis-section {
            margin-top: 20px;
        }
        
        .analysis-section h3 {
            color: #1976d2;
            margin-bottom: 10px;
        }
        
        .analysis-content {
            line-height: 1.8;
        }
        
        .compliance-matrix {
            margin-top: 20px;
        }
        
        .compliance-framework {
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .compliance-framework h4 {
            margin: 0 0 10px 0;
            color: #333;
        }
        
        .compliance-framework ul {
            margin: 0;
            padding-left: 20px;
        }
        
        .requirement-pass {
            color: #4caf50;
        }
        
        .requirement-partial {
            color: #ff9800;
        }
        
        .requirement-fail {
            color: #f44336;
        }
        
        .toxicity-heatmap {
            margin: 20px 0;
        }
        
        .heatmap-legend {
            margin-top: 10px;
            font-size: 0.9em;
        }
        
        .legend-item {
            display: inline-block;
            padding: 4px 8px;
            margin: 0 5px;
            color: white;
            border-radius: 4px;
        }
        
        .custom-content-block {
            padding: 20px;
            background: white;
        }
        
        .custom-content-block.methodology {
            background: #f0f7ff;
            border-left: 4px solid #1976d2;
        }
        
        .custom-content-block.disclaimer {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
        }
        
        .report-footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        
        @media print {
            .report-block {
                page-break-inside: avoid;
            }
            
            .report-header {
                page-break-after: avoid;
            }
        }
        """

    async def start_processing_queue(self):
        """Start processing the report generation queue"""
        while True:
            try:
                task = await self._generation_queue.get()
                asyncio.create_task(self._process_report_generation(task))
            except Exception as e:
                logger.error(f"Error in queue processor: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    def _process_execution_results(self, execution: OrchestratorExecution) -> Optional[Dict[str, Any]]:
        """Process OrchestratorExecution results into report data format"""
        try:
            results = execution.results or {}
            scores = results.get("scores", [])
            execution_summary = results.get("execution_summary", {})
            metadata = execution_summary.get("metadata", {})

            # Determine scanner type from metadata
            orchestrator_type = metadata.get("orchestrator_type", "pyrit")
            scanner_type = "pyrit" if "pyrit" in orchestrator_type.lower() else "garak"

            # Process scores
            total_scores = len(scores)
            vulnerabilities = []
            score_summary = {
                "toxicity": {"mean": 0, "max": 0, "min": 0, "count": 0},
                "bias": {"mean": 0, "max": 0, "min": 0, "count": 0},
                "jailbreak": {"mean": 0, "max": 0, "min": 0, "count": 0},
                "prompt_injection": {"mean": 0, "max": 0, "min": 0, "count": 0},
            }

            # Aggregate scores by type
            score_types = {}
            for score in scores:
                score_type = score.get("score_type", "unknown")
                score_value = score.get("score_value")

                if score_type not in score_types:
                    score_types[score_type] = []

                if score_value is not None:
                    score_types[score_type].append(score_value)

                # Check for vulnerabilities (failed scores)
                if score.get("score_type") == "true_false" and score_value is False:
                    vuln = {
                        "type": score.get("score_category", "Unknown"),
                        "severity": self._determine_severity(score),
                        "description": score.get("score_rationale", ""),
                        "timestamp": score.get("timestamp"),
                    }
                    vulnerabilities.append(vuln)

            # Calculate aggregated scores
            for category in score_summary:
                if category in score_types and score_types[category]:
                    values = score_types[category]
                    score_summary[category] = {
                        "mean": sum(values) / len(values),
                        "max": max(values),
                        "min": min(values),
                        "count": len(values),
                    }

            # Build processed data
            processed_data = {
                "execution_id": str(execution.id),
                "scanner_type": scanner_type,
                "target_model": metadata.get("target_model", "Unknown"),
                "scan_date": execution.started_at,
                "total_tests": total_scores,
                "successful_attacks": len(vulnerabilities),
                "failure_rate": (len(vulnerabilities) / total_scores * 100) if total_scores > 0 else 0,
                "score_summary": score_summary,
                "vulnerabilities": vulnerabilities,
                "severity_distribution": self._calculate_severity_distribution(vulnerabilities),
                "metadata": {
                    "orchestrator_type": orchestrator_type,
                    "execution_name": execution.execution_name,
                    "dataset_name": metadata.get("dataset_name", "Unknown"),
                    "test_mode": metadata.get("test_mode", "full_execution"),
                },
            }

            return processed_data

        except Exception as e:
            logger.error(f"Error processing execution results: {str(e)}")
            return None

    def _cache_execution_data(self, execution: OrchestratorExecution, processed_data: Dict[str, Any]) -> None:
        """Cache processed execution data"""
        try:
            cache_entry = COBScanDataCache(
                execution_id=str(execution.id),
                scanner_type=processed_data["scanner_type"],
                target_model=processed_data["target_model"],
                scan_date=processed_data["scan_date"],
                score_data={
                    "total_tests": processed_data["total_tests"],
                    "successful_attacks": processed_data["successful_attacks"],
                    "failure_rate": processed_data["failure_rate"],
                    "score_summary": processed_data["score_summary"],
                    "severity_distribution": processed_data["severity_distribution"],
                },
                raw_results=processed_data,
                metadata=processed_data["metadata"],
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            self.db.add(cache_entry)
            self.db.commit()

        except Exception as e:
            logger.error(f"Error caching execution data: {str(e)}")
            self.db.rollback()

    def _determine_severity(self, score: Dict[str, Any]) -> str:
        """Determine severity from score"""
        score_type = score.get("score_type", "")
        score_value = score.get("score_value")
        score_category = score.get("score_category", "").lower()

        # Critical categories
        if any(term in score_category for term in ["injection", "jailbreak", "critical"]):
            return "Critical"

        # High severity categories
        if any(term in score_category for term in ["toxicity", "harmful", "bias", "high"]):
            return "High"

        # Medium severity categories
        if any(term in score_category for term in ["quality", "medium"]):
            return "Medium"

        # Default based on score type
        if score_type == "true_false":
            return "High" if score_value is False else "Low"
        elif score_type == "float_scale" and isinstance(score_value, (int, float)):
            if score_value >= 0.8:
                return "Critical"
            elif score_value >= 0.6:
                return "High"
            elif score_value >= 0.4:
                return "Medium"
            else:
                return "Low"

        return "Medium"

    def _calculate_severity_distribution(self, vulnerabilities: List[Dict]) -> Dict[str, int]:
        """Calculate severity distribution"""
        distribution = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Informational": 0}

        for vuln in vulnerabilities:
            severity = vuln.get("severity", "Medium")
            if severity in distribution:
                distribution[severity] += 1

        return distribution
