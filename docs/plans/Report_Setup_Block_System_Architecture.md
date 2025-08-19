# Report Setup - Block System Architecture

## Overview

The block system is the core of the report generation framework, providing a modular and extensible way to compose reports from reusable components. Each block represents a distinct section of a report with its own data requirements, processing logic, and rendering capabilities.

## Block Architecture

### Base Block Interface

```python
# app/services/report_setup/blocks/base_block.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum

class BlockCategory(str, Enum):
    """Categories of report blocks"""
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    METRICS = "metrics"
    TABLE = "table"
    VISUALIZATION = "visualization"
    CONTENT = "content"
    AI = "ai"

class BlockParameter(BaseModel):
    """Definition of a block parameter"""
    name: str
    type: str  # text, number, boolean, select, multiselect
    description: str
    required: bool = False
    default: Optional[Any] = None
    options: Optional[List[Any]] = None  # For select/multiselect
    validation: Optional[Dict[str, Any]] = None

class BlockDefinition(BaseModel):
    """Metadata definition for a block"""
    id: str
    name: str
    category: BlockCategory
    description: str
    version: str = "1.0.0"
    
    # Parameters that can be configured
    parameters: List[BlockParameter] = []
    
    # Variables this block requires/uses
    required_variables: Set[str] = set()
    optional_variables: Set[str] = set()
    
    # Output variables this block produces
    output_variables: Set[str] = set()
    
    # Supported output formats
    supported_formats: List[str] = ["html", "markdown", "json"]
    
    # Resource requirements
    requires_ai: bool = False
    estimated_processing_time: int = 5  # seconds

class BaseReportBlock(ABC):
    """Abstract base class for all report blocks"""
    
    def __init__(self):
        self.definition = self.get_definition()
        
    @abstractmethod
    def get_definition(self) -> BlockDefinition:
        """Return block metadata definition"""
        pass
        
    @abstractmethod
    async def validate_data(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Validate that required data is available"""
        pass
        
    @abstractmethod
    async def process(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process data and return block content"""
        pass
        
    @abstractmethod
    async def render(
        self,
        processed_data: Dict[str, Any],
        format: str = "html"
    ) -> str:
        """Render processed data to specified format"""
        pass
        
    def extract_variables(self, template: str, data: Dict[str, Any]) -> str:
        """Extract and replace variables in template"""
        import re
        
        # Find all variables in template
        pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            # Navigate through nested data
            value = data
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return f"{{{{ {var_path} }}}}"  # Keep original if not found
                    
            return str(value)
            
        return re.sub(pattern, replace_var, template)
```

## Core Block Implementations

### 1. Executive Summary Block

```python
# app/services/report_setup/blocks/executive_summary_block.py
from typing import Dict, Any, List, Optional
from .base_block import BaseReportBlock, BlockDefinition, BlockCategory, BlockParameter

class ExecutiveSummaryBlock(BaseReportBlock):
    """Generate executive summary from scan data"""
    
    def get_definition(self) -> BlockDefinition:
        return BlockDefinition(
            id="executive_summary",
            name="Executive Summary",
            category=BlockCategory.SUMMARY,
            description="High-level summary of security assessment results",
            parameters=[
                BlockParameter(
                    name="include_recommendations",
                    type="boolean",
                    description="Include top recommendations",
                    default=True
                ),
                BlockParameter(
                    name="severity_threshold",
                    type="select",
                    description="Minimum severity to highlight",
                    options=["critical", "high", "medium", "low"],
                    default="high"
                ),
                BlockParameter(
                    name="max_items",
                    type="number",
                    description="Maximum number of items to show",
                    default=5,
                    validation={"min": 1, "max": 20}
                )
            ],
            required_variables={
                "scan_summary.total_tests",
                "scan_summary.scanner_type",
                "severity_distribution",
                "vulnerabilities"
            },
            optional_variables={
                "scan_summary.target_model",
                "scan_summary.execution_date",
                "compliance_summary"
            },
            output_variables={
                "executive_summary",
                "risk_level",
                "key_findings_count"
            }
        )
        
    async def validate_data(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Validate required data"""
        errors = []
        
        # Check required top-level keys
        if "scan_summary" not in data:
            errors.append("Missing scan_summary data")
        elif "total_tests" not in data["scan_summary"]:
            errors.append("Missing total_tests in scan_summary")
            
        if "severity_distribution" not in data:
            errors.append("Missing severity_distribution data")
            
        if "vulnerabilities" not in data:
            errors.append("Missing vulnerabilities data")
            
        return errors
        
    async def process(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process scan data into executive summary"""
        
        # Extract key metrics
        total_tests = data["scan_summary"]["total_tests"]
        scanner_type = data["scan_summary"]["scanner_type"]
        target_model = data["scan_summary"].get("target_model", "Unknown")
        
        # Calculate risk level
        severity_dist = data["severity_distribution"]
        critical_count = severity_dist.get("critical", 0)
        high_count = severity_dist.get("high", 0)
        
        if critical_count > 0:
            risk_level = "Critical"
            risk_color = "#FF0000"
        elif high_count > 5:
            risk_level = "High"
            risk_color = "#FF6600"
        elif high_count > 0:
            risk_level = "Medium"
            risk_color = "#FFAA00"
        else:
            risk_level = "Low"
            risk_color = "#00AA00"
            
        # Get top vulnerabilities based on threshold
        threshold = parameters.get("severity_threshold", "high")
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        threshold_value = severity_order[threshold]
        
        top_vulnerabilities = [
            v for v in data["vulnerabilities"]
            if severity_order.get(v.get("severity", "low"), 3) <= threshold_value
        ][:parameters.get("max_items", 5)]
        
        # Generate summary text
        summary_text = self._generate_summary_text(
            scanner_type,
            total_tests,
            risk_level,
            severity_dist,
            top_vulnerabilities
        )
        
        # Prepare recommendations if requested
        recommendations = []
        if parameters.get("include_recommendations", True):
            recommendations = self._generate_recommendations(
                risk_level,
                top_vulnerabilities,
                data
            )
            
        return {
            "executive_summary": summary_text,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "key_findings_count": len(top_vulnerabilities),
            "key_findings": top_vulnerabilities,
            "recommendations": recommendations,
            "metrics": {
                "total_tests": total_tests,
                "scanner_type": scanner_type,
                "target_model": target_model,
                "critical_issues": critical_count,
                "high_issues": high_count
            }
        }
        
    async def render(
        self,
        processed_data: Dict[str, Any],
        format: str = "html"
    ) -> str:
        """Render executive summary"""
        
        if format == "html":
            return self._render_html(processed_data)
        elif format == "markdown":
            return self._render_markdown(processed_data)
        elif format == "json":
            return json.dumps(processed_data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _render_html(self, data: Dict[str, Any]) -> str:
        """Render as HTML"""
        html = f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            
            <div class="risk-assessment">
                <div class="risk-level" style="color: {data['risk_color']}">
                    <strong>Overall Risk Level:</strong> {data['risk_level']}
                </div>
            </div>
            
            <div class="summary-text">
                <p>{data['executive_summary']}</p>
            </div>
            
            <div class="key-metrics">
                <h3>Key Metrics</h3>
                <ul>
                    <li><strong>Scanner:</strong> {data['metrics']['scanner_type']}</li>
                    <li><strong>Target Model:</strong> {data['metrics']['target_model']}</li>
                    <li><strong>Total Tests:</strong> {data['metrics']['total_tests']}</li>
                    <li><strong>Critical Issues:</strong> {data['metrics']['critical_issues']}</li>
                    <li><strong>High Issues:</strong> {data['metrics']['high_issues']}</li>
                </ul>
            </div>
        """
        
        if data['key_findings']:
            html += """
            <div class="key-findings">
                <h3>Key Findings</h3>
                <ul>
            """
            for finding in data['key_findings']:
                html += f"""
                    <li>
                        <strong>{finding['name']}</strong> 
                        <span class="severity-{finding['severity']}">[{finding['severity'].upper()}]</span>
                        <p>{finding['description']}</p>
                    </li>
                """
            html += "</ul></div>"
            
        if data['recommendations']:
            html += """
            <div class="recommendations">
                <h3>Recommendations</h3>
                <ol>
            """
            for rec in data['recommendations']:
                html += f"<li>{rec}</li>"
            html += "</ol></div>"
            
        html += "</div>"
        return html
```

### 2. AI Analysis Block

```python
# app/services/report_setup/blocks/ai_analysis_block.py
from typing import Dict, Any, List, Optional
import asyncio
from .base_block import BaseReportBlock, BlockDefinition, BlockCategory, BlockParameter

class AIAnalysisBlock(BaseReportBlock):
    """AI-powered analysis of scan results"""
    
    def get_definition(self) -> BlockDefinition:
        return BlockDefinition(
            id="ai_analysis",
            name="AI Analysis",
            category=BlockCategory.AI,
            description="AI-powered insights and recommendations",
            requires_ai=True,
            estimated_processing_time=30,
            parameters=[
                BlockParameter(
                    name="analysis_focus",
                    type="multiselect",
                    description="Areas to focus analysis on",
                    options=[
                        "vulnerability_patterns",
                        "attack_chains",
                        "defense_recommendations",
                        "compliance_gaps",
                        "risk_prioritization"
                    ],
                    default=["vulnerability_patterns", "defense_recommendations"]
                ),
                BlockParameter(
                    name="analysis_depth",
                    type="select",
                    description="Depth of analysis",
                    options=["quick", "standard", "detailed"],
                    default="standard"
                ),
                BlockParameter(
                    name="custom_prompt",
                    type="text",
                    description="Additional instructions for AI analysis",
                    required=False
                ),
                BlockParameter(
                    name="include_raw_results",
                    type="boolean",
                    description="Include raw scan results in analysis",
                    default=False
                )
            ],
            required_variables={
                "vulnerabilities",
                "scan_summary",
                "severity_distribution"
            },
            optional_variables={
                "scan_results",
                "compliance_data",
                "previous_reports"
            },
            output_variables={
                "ai_insights",
                "pattern_analysis",
                "prioritized_risks",
                "strategic_recommendations"
            }
        )
        
    async def process(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process data with AI analysis"""
        
        # Get AI service from context
        ai_service = context.get("ai_service") if context else None
        if not ai_service:
            raise ValueError("AI service not provided in context")
            
        # Prepare analysis prompts based on focus areas
        focus_areas = parameters.get("analysis_focus", ["vulnerability_patterns"])
        analysis_depth = parameters.get("analysis_depth", "standard")
        
        # Build comprehensive prompt
        prompt = self._build_analysis_prompt(
            data,
            focus_areas,
            analysis_depth,
            parameters.get("custom_prompt")
        )
        
        # Prepare data for AI
        analysis_data = self._prepare_analysis_data(
            data,
            parameters.get("include_raw_results", False)
        )
        
        # Run AI analysis
        try:
            ai_response = await ai_service.analyze(
                prompt=prompt,
                data=analysis_data,
                temperature=0.7,
                max_tokens=self._get_max_tokens(analysis_depth)
            )
            
            # Parse AI response
            parsed_insights = self._parse_ai_response(ai_response, focus_areas)
            
            return {
                "ai_insights": parsed_insights,
                "pattern_analysis": parsed_insights.get("patterns", {}),
                "prioritized_risks": parsed_insights.get("priorities", []),
                "strategic_recommendations": parsed_insights.get("recommendations", []),
                "analysis_metadata": {
                    "model": ai_service.model,
                    "depth": analysis_depth,
                    "focus_areas": focus_areas
                }
            }
            
        except Exception as e:
            # Fallback to basic analysis if AI fails
            return self._generate_fallback_analysis(data, focus_areas)
            
    def _build_analysis_prompt(
        self,
        data: Dict[str, Any],
        focus_areas: List[str],
        depth: str,
        custom_prompt: Optional[str]
    ) -> str:
        """Build comprehensive analysis prompt"""
        
        prompt_parts = [
            "You are an AI security analyst reviewing scan results from a red team assessment.",
            f"Analysis depth: {depth}",
            f"Focus areas: {', '.join(focus_areas)}",
            "",
            "Scan Summary:",
            f"- Scanner: {data['scan_summary']['scanner_type']}",
            f"- Total tests: {data['scan_summary']['total_tests']}",
            f"- Target: {data['scan_summary'].get('target_model', 'Unknown')}",
            "",
            "Severity Distribution:",
        ]
        
        # Add severity breakdown
        for severity, count in data['severity_distribution'].items():
            if count > 0:
                prompt_parts.append(f"- {severity.capitalize()}: {count}")
                
        prompt_parts.extend([
            "",
            "Please provide analysis covering the following:"
        ])
        
        # Add focus-specific instructions
        if "vulnerability_patterns" in focus_areas:
            prompt_parts.append("1. Identify patterns in the vulnerabilities found")
            
        if "attack_chains" in focus_areas:
            prompt_parts.append("2. Describe potential attack chains using these vulnerabilities")
            
        if "defense_recommendations" in focus_areas:
            prompt_parts.append("3. Provide specific defense recommendations")
            
        if "compliance_gaps" in focus_areas:
            prompt_parts.append("4. Identify compliance framework gaps")
            
        if "risk_prioritization" in focus_areas:
            prompt_parts.append("5. Prioritize risks based on exploitability and impact")
            
        # Add custom prompt if provided
        if custom_prompt:
            prompt_parts.extend(["", "Additional instructions:", custom_prompt])
            
        # Add output format instructions
        prompt_parts.extend([
            "",
            "Format your response as structured JSON with clear sections for each focus area."
        ])
        
        return "\n".join(prompt_parts)
```

### 3. Security Metrics Block

```python
# app/services/report_setup/blocks/security_metrics_block.py
from typing import Dict, Any, List, Optional
import json
from collections import Counter, defaultdict
from .base_block import BaseReportBlock, BlockDefinition, BlockCategory, BlockParameter

class SecurityMetricsBlock(BaseReportBlock):
    """Display security metrics and visualizations"""
    
    def get_definition(self) -> BlockDefinition:
        return BlockDefinition(
            id="security_metrics",
            name="Security Metrics",
            category=BlockCategory.METRICS,
            description="Comprehensive security metrics and visualizations",
            parameters=[
                BlockParameter(
                    name="metric_source",
                    type="select",
                    description="Source of metrics",
                    options=["scan_data", "compatibility_matrix", "combined"],
                    default="scan_data"
                ),
                BlockParameter(
                    name="visualizations",
                    type="multiselect",
                    description="Visualizations to include",
                    options=[
                        "metric_cards",
                        "risk_heatmap",
                        "attack_success_chart",
                        "vulnerability_timeline",
                        "compliance_radar",
                        "severity_distribution"
                    ],
                    default=["metric_cards", "severity_distribution", "risk_heatmap"]
                ),
                BlockParameter(
                    name="comparison_enabled",
                    type="boolean",
                    description="Enable comparison with previous scans",
                    default=False
                ),
                BlockParameter(
                    name="thresholds",
                    type="text",
                    description="Custom severity thresholds (JSON)",
                    default='{"critical": 9.0, "high": 7.0, "medium": 4.0}'
                )
            ],
            required_variables={
                "severity_distribution",
                "vulnerabilities",
                "scan_summary"
            },
            optional_variables={
                "compatibility_matrix",
                "previous_scan_data",
                "compliance_scores"
            }
        )
        
    async def process(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process metrics data"""
        
        # Parse thresholds
        try:
            thresholds = json.loads(parameters.get("thresholds", "{}"))
        except:
            thresholds = {"critical": 9.0, "high": 7.0, "medium": 4.0}
            
        # Calculate core metrics
        metrics = {
            "overview": self._calculate_overview_metrics(data),
            "severity": self._calculate_severity_metrics(data, thresholds),
            "categories": self._calculate_category_metrics(data),
            "trends": self._calculate_trends(data, parameters.get("comparison_enabled", False))
        }
        
        # Add source-specific metrics
        source = parameters.get("metric_source", "scan_data")
        if source in ["compatibility_matrix", "combined"] and "compatibility_matrix" in data:
            metrics["compatibility"] = self._calculate_compatibility_metrics(
                data["compatibility_matrix"]
            )
            
        # Generate visualizations data
        visualizations = {}
        requested_viz = parameters.get("visualizations", ["metric_cards"])
        
        for viz_type in requested_viz:
            if viz_type == "metric_cards":
                visualizations["metric_cards"] = self._generate_metric_cards(metrics)
            elif viz_type == "risk_heatmap":
                visualizations["risk_heatmap"] = self._generate_risk_heatmap(data)
            elif viz_type == "attack_success_chart":
                visualizations["attack_success_chart"] = self._generate_attack_chart(data)
            elif viz_type == "vulnerability_timeline":
                visualizations["vulnerability_timeline"] = self._generate_timeline(data)
            elif viz_type == "compliance_radar":
                visualizations["compliance_radar"] = self._generate_compliance_radar(data)
            elif viz_type == "severity_distribution":
                visualizations["severity_distribution"] = self._generate_severity_chart(data)
                
        return {
            "metrics": metrics,
            "visualizations": visualizations,
            "summary_statistics": self._generate_summary_stats(metrics)
        }
        
    def _calculate_overview_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate high-level overview metrics"""
        
        total_tests = data["scan_summary"]["total_tests"]
        vulnerabilities = data.get("vulnerabilities", [])
        severity_dist = data.get("severity_distribution", {})
        
        # Calculate success/failure rates
        total_vulns = sum(severity_dist.values())
        success_rate = ((total_tests - total_vulns) / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "total_vulnerabilities": total_vulns,
            "unique_vulnerabilities": len(set(v["name"] for v in vulnerabilities)),
            "success_rate": round(success_rate, 2),
            "failure_rate": round(100 - success_rate, 2),
            "average_severity": self._calculate_average_severity(severity_dist),
            "risk_score": self._calculate_risk_score(data)
        }
        
    def _generate_metric_cards(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate metric card data"""
        
        overview = metrics["overview"]
        
        cards = [
            {
                "title": "Total Tests",
                "value": overview["total_tests"],
                "icon": "clipboard-check",
                "color": "blue"
            },
            {
                "title": "Vulnerabilities Found",
                "value": overview["total_vulnerabilities"],
                "icon": "shield-alert",
                "color": "red" if overview["total_vulnerabilities"] > 0 else "green",
                "change": metrics["trends"].get("vulnerability_change")
            },
            {
                "title": "Success Rate",
                "value": f"{overview['success_rate']}%",
                "icon": "check-circle",
                "color": "green" if overview["success_rate"] > 80 else "orange"
            },
            {
                "title": "Risk Score",
                "value": f"{overview['risk_score']}/10",
                "icon": "alert-triangle",
                "color": self._get_risk_color(overview["risk_score"]),
                "subtitle": self._get_risk_level(overview["risk_score"])
            }
        ]
        
        return cards
        
    def _generate_risk_heatmap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate risk heatmap data"""
        
        vulnerabilities = data.get("vulnerabilities", [])
        
        # Group by category and severity
        heatmap_data = defaultdict(lambda: defaultdict(int))
        
        for vuln in vulnerabilities:
            category = vuln.get("category", "other")
            severity = vuln.get("severity", "low")
            heatmap_data[category][severity] += 1
            
        # Convert to heatmap format
        categories = sorted(heatmap_data.keys())
        severities = ["critical", "high", "medium", "low"]
        
        matrix = []
        for category in categories:
            row = []
            for severity in severities:
                count = heatmap_data[category][severity]
                row.append({
                    "value": count,
                    "color": self._get_heatmap_color(count, severity)
                })
            matrix.append(row)
            
        return {
            "categories": categories,
            "severities": severities,
            "matrix": matrix,
            "max_value": max(
                max(heatmap_data[cat][sev] for sev in severities)
                for cat in categories
            ) if categories else 0
        }
```

### 4. Attack Results Table Block

```python
# app/services/report_setup/blocks/attack_results_table_block.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_block import BaseReportBlock, BlockDefinition, BlockCategory, BlockParameter

class AttackResultsTableBlock(BaseReportBlock):
    """Display attack results in tabular format"""
    
    def get_definition(self) -> BlockDefinition:
        return BlockDefinition(
            id="attack_results_table",
            name="Attack Results Table",
            category=BlockCategory.TABLE,
            description="Detailed table of attack attempts and results",
            parameters=[
                BlockParameter(
                    name="data_source",
                    type="select",
                    description="Source of attack data",
                    options=["pyrit", "garak", "combined"],
                    default="combined"
                ),
                BlockParameter(
                    name="columns",
                    type="multiselect",
                    description="Columns to display",
                    options=[
                        "timestamp",
                        "attack_type",
                        "target",
                        "payload",
                        "response",
                        "success",
                        "severity",
                        "scorer",
                        "score"
                    ],
                    default=["timestamp", "attack_type", "target", "success", "severity"]
                ),
                BlockParameter(
                    name="filters",
                    type="multiselect",
                    description="Filter options to show",
                    options=["severity", "success", "attack_type", "date_range"],
                    default=["severity", "success"]
                ),
                BlockParameter(
                    name="max_rows",
                    type="number",
                    description="Maximum rows to display",
                    default=100,
                    validation={"min": 10, "max": 1000}
                ),
                BlockParameter(
                    name="highlight_successful",
                    type="boolean",
                    description="Highlight successful attacks",
                    default=True
                )
            ],
            required_variables={
                "scan_results",
                "scan_summary"
            },
            optional_variables={
                "pyrit_results",
                "garak_results"
            }
        )
        
    async def process(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process attack results into table format"""
        
        # Get data based on source
        source = parameters.get("data_source", "combined")
        attack_data = self._extract_attack_data(data, source)
        
        # Apply filtering
        filtered_data = self._apply_filters(attack_data, parameters)
        
        # Sort by timestamp (newest first)
        filtered_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Limit rows
        max_rows = parameters.get("max_rows", 100)
        filtered_data = filtered_data[:max_rows]
        
        # Prepare table data
        columns = parameters.get("columns", ["timestamp", "attack_type", "success"])
        table_data = {
            "columns": self._get_column_definitions(columns),
            "rows": self._format_rows(filtered_data, columns, parameters),
            "total_rows": len(attack_data),
            "displayed_rows": len(filtered_data),
            "filters_applied": parameters.get("filters", []),
            "summary": self._generate_table_summary(filtered_data)
        }
        
        return table_data
        
    def _extract_attack_data(
        self,
        data: Dict[str, Any],
        source: str
    ) -> List[Dict[str, Any]]:
        """Extract attack data from various sources"""
        
        attacks = []
        
        # Extract from scan results
        if "scan_results" in data and source in ["combined", "scan"]:
            for result in data["scan_results"]:
                attacks.append(self._normalize_scan_result(result))
                
        # Extract from PyRIT results
        if "pyrit_results" in data and source in ["combined", "pyrit"]:
            for result in data["pyrit_results"]:
                attacks.append(self._normalize_pyrit_result(result))
                
        # Extract from Garak results
        if "garak_results" in data and source in ["combined", "garak"]:
            for result in data["garak_results"]:
                attacks.append(self._normalize_garak_result(result))
                
        return attacks
        
    def _normalize_scan_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize scan result to common format"""
        
        return {
            "timestamp": result.get("timestamp", ""),
            "attack_type": result.get("attack_category", "unknown"),
            "target": result.get("target_component", "model"),
            "payload": result.get("prompt", "")[:200],  # Truncate long prompts
            "response": result.get("response", "")[:200],
            "success": result.get("attack_successful", False),
            "severity": result.get("severity", "medium"),
            "scorer": result.get("scorer_type", ""),
            "score": result.get("score_value", 0),
            "details": result
        }
        
    def _get_column_definitions(self, columns: List[str]) -> List[Dict[str, Any]]:
        """Get column definitions with metadata"""
        
        column_defs = {
            "timestamp": {
                "id": "timestamp",
                "name": "Time",
                "type": "datetime",
                "width": "150px",
                "sortable": True
            },
            "attack_type": {
                "id": "attack_type",
                "name": "Attack Type",
                "type": "text",
                "width": "200px",
                "sortable": True
            },
            "target": {
                "id": "target",
                "name": "Target",
                "type": "text",
                "width": "150px",
                "sortable": True
            },
            "payload": {
                "id": "payload",
                "name": "Payload",
                "type": "text",
                "width": "300px",
                "truncate": True
            },
            "response": {
                "id": "response",
                "name": "Response",
                "type": "text",
                "width": "300px",
                "truncate": True
            },
            "success": {
                "id": "success",
                "name": "Success",
                "type": "boolean",
                "width": "80px",
                "align": "center"
            },
            "severity": {
                "id": "severity",
                "name": "Severity",
                "type": "badge",
                "width": "100px",
                "align": "center"
            },
            "scorer": {
                "id": "scorer",
                "name": "Scorer",
                "type": "text",
                "width": "150px"
            },
            "score": {
                "id": "score",
                "name": "Score",
                "type": "number",
                "width": "80px",
                "align": "right",
                "format": ".2f"
            }
        }
        
        return [column_defs[col] for col in columns if col in column_defs]
```

### 5. Custom Content Block

```python
# app/services/report_setup/blocks/custom_content_block.py
from typing import Dict, Any, List, Optional
import markdown
from .base_block import BaseReportBlock, BlockDefinition, BlockCategory, BlockParameter

class CustomContentBlock(BaseReportBlock):
    """User-defined content with variable substitution"""
    
    def get_definition(self) -> BlockDefinition:
        return BlockDefinition(
            id="custom_content",
            name="Custom Content",
            category=BlockCategory.CONTENT,
            description="Custom markdown content with variable substitution",
            parameters=[
                BlockParameter(
                    name="content",
                    type="text",
                    description="Markdown content with {{variables}}",
                    required=True,
                    default="# Custom Section\n\nAdd your content here with {{variables}}"
                ),
                BlockParameter(
                    name="enable_html",
                    type="boolean",
                    description="Allow HTML in markdown",
                    default=False
                ),
                BlockParameter(
                    name="variable_not_found_behavior",
                    type="select",
                    description="What to do when variable not found",
                    options=["keep", "remove", "error"],
                    default="keep"
                )
            ],
            # No required variables - depends on content
            required_variables=set(),
            optional_variables={
                "scan_summary",
                "vulnerabilities",
                "severity_distribution",
                "metrics",
                "ai_insights"
            }
        )
        
    async def validate_data(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Validate that referenced variables exist"""
        
        errors = []
        content = parameters.get("content", "")
        
        # Extract variable references
        import re
        pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
        variables = re.findall(pattern, content)
        
        # Check if variables exist in data
        not_found_behavior = parameters.get("variable_not_found_behavior", "keep")
        
        if not_found_behavior == "error":
            for var_path in variables:
                parts = var_path.split('.')
                value = data
                
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        errors.append(f"Variable not found: {{{{{var_path}}}}}")
                        break
                        
        return errors
        
    async def process(
        self,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process custom content with variable substitution"""
        
        content = parameters.get("content", "")
        not_found_behavior = parameters.get("variable_not_found_behavior", "keep")
        
        # Perform variable substitution
        processed_content = self._substitute_variables(
            content,
            data,
            not_found_behavior
        )
        
        # Extract metadata
        variables_used = self._extract_used_variables(content, data)
        
        return {
            "content": processed_content,
            "variables_used": variables_used,
            "original_content": content
        }
        
    async def render(
        self,
        processed_data: Dict[str, Any],
        format: str = "html"
    ) -> str:
        """Render custom content"""
        
        content = processed_data["content"]
        
        if format == "html":
            # Convert markdown to HTML
            md = markdown.Markdown(
                extensions=['extra', 'codehilite', 'tables', 'toc'],
                output_format='html5'
            )
            
            if not self.parameters.get("enable_html", False):
                # Safe mode - escape HTML
                md = markdown.Markdown(
                    extensions=['extra', 'codehilite', 'tables', 'toc'],
                    output_format='html5',
                    safe_mode='escape'
                )
                
            return md.convert(content)
            
        elif format == "markdown":
            return content
            
        elif format == "json":
            return json.dumps({
                "content": content,
                "variables_used": processed_data["variables_used"]
            }, indent=2)
            
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _substitute_variables(
        self,
        content: str,
        data: Dict[str, Any],
        not_found_behavior: str
    ) -> str:
        """Substitute variables in content"""
        
        import re
        pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            # Navigate through nested data
            value = data
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif isinstance(value, list) and part.isdigit():
                    index = int(part)
                    if 0 <= index < len(value):
                        value = value[index]
                    else:
                        value = None
                        break
                else:
                    value = None
                    break
                    
            # Handle not found
            if value is None:
                if not_found_behavior == "keep":
                    return match.group(0)  # Keep original
                elif not_found_behavior == "remove":
                    return ""  # Remove
                else:  # error - handled in validation
                    return match.group(0)
                    
            # Format value
            if isinstance(value, (dict, list)):
                return json.dumps(value, indent=2)
            else:
                return str(value)
                
        return re.sub(pattern, replace_var, content)
```

## Block Registry System

```python
# app/services/report_setup/blocks/registry.py
from typing import Dict, Type, List, Optional, Any
from .base_block import BaseReportBlock, BlockCategory
import importlib
import pkgutil
import inspect

class BlockRegistry:
    """Registry for all available report blocks"""
    
    def __init__(self):
        self._blocks: Dict[str, Type[BaseReportBlock]] = {}
        self._categories: Dict[BlockCategory, List[str]] = {}
        self._loaded = False
        
    def register(self, block_class: Type[BaseReportBlock]):
        """Register a block class"""
        
        # Create instance to get definition
        instance = block_class()
        definition = instance.get_definition()
        
        # Register block
        self._blocks[definition.id] = block_class
        
        # Register in category
        if definition.category not in self._categories:
            self._categories[definition.category] = []
        self._categories[definition.category].append(definition.id)
        
    def auto_discover(self, package_name: str = "app.services.report_setup.blocks"):
        """Auto-discover and register all blocks in package"""
        
        if self._loaded:
            return
            
        # Import package
        package = importlib.import_module(package_name)
        
        # Iterate through modules
        for importer, modname, ispkg in pkgutil.iter_modules(
            package.__path__,
            package.__name__ + "."
        ):
            if ispkg:
                continue
                
            # Import module
            module = importlib.import_module(modname)
            
            # Find block classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseReportBlock) and
                    obj != BaseReportBlock and
                    not inspect.isabstract(obj)
                ):
                    self.register(obj)
                    
        self._loaded = True
        
    def get_block(self, block_id: str) -> Optional[Type[BaseReportBlock]]:
        """Get block class by ID"""
        return self._blocks.get(block_id)
        
    def create_block(self, block_id: str) -> Optional[BaseReportBlock]:
        """Create block instance by ID"""
        block_class = self.get_block(block_id)
        return block_class() if block_class else None
        
    def list_blocks(self) -> List[Dict[str, Any]]:
        """List all registered blocks"""
        blocks = []
        
        for block_id, block_class in self._blocks.items():
            instance = block_class()
            definition = instance.get_definition()
            
            blocks.append({
                "id": definition.id,
                "name": definition.name,
                "category": definition.category,
                "description": definition.description,
                "requires_ai": definition.requires_ai,
                "required_variables": list(definition.required_variables),
                "optional_variables": list(definition.optional_variables)
            })
            
        return blocks
        
    def get_blocks_by_category(self, category: BlockCategory) -> List[Dict[str, Any]]:
        """Get all blocks in a category"""
        block_ids = self._categories.get(category, [])
        
        blocks = []
        for block_id in block_ids:
            block_class = self._blocks[block_id]
            instance = block_class()
            definition = instance.get_definition()
            
            blocks.append({
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "required_variables": list(definition.required_variables)
            })
            
        return blocks
        
    def validate_block(self, block_id: str) -> bool:
        """Check if block ID is valid"""
        return block_id in self._blocks
        
    def get_all_variables(self) -> Dict[str, List[str]]:
        """Get all variables used by all blocks"""
        
        required_vars = set()
        optional_vars = set()
        output_vars = set()
        
        for block_class in self._blocks.values():
            instance = block_class()
            definition = instance.get_definition()
            
            required_vars.update(definition.required_variables)
            optional_vars.update(definition.optional_variables)
            output_vars.update(definition.output_variables)
            
        return {
            "required": sorted(list(required_vars)),
            "optional": sorted(list(optional_vars)),
            "output": sorted(list(output_vars))
        }
        
    def export_registry(self) -> Dict[str, Any]:
        """Export registry configuration"""
        
        return {
            "blocks": self.list_blocks(),
            "categories": {
                category.value: self.get_blocks_by_category(category)
                for category in BlockCategory
            },
            "variables": self.get_all_variables()
        }

# Global registry instance
block_registry = BlockRegistry()

# Auto-discover blocks on import
block_registry.auto_discover()
```

## Block Processor Service

```python
# app/services/report_setup/block_processor.py
from typing import Dict, Any, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class BlockProcessor:
    """Process blocks for report generation"""
    
    def __init__(self, block_registry, ai_service=None):
        self.block_registry = block_registry
        self.ai_service = ai_service
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def process_blocks(
        self,
        template: Dict[str, Any],
        configuration: Dict[str, Any],
        data: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Process all blocks in template"""
        
        results = {}
        total_blocks = len(template["blocks"])
        processed = 0
        
        # Group blocks by dependency
        block_groups = self._group_blocks_by_dependency(template["blocks"])
        
        # Process each group in order
        for group_index, block_group in enumerate(block_groups):
            # Process blocks in group concurrently
            tasks = []
            
            for block_config in block_group:
                if not block_config.get("enabled", True):
                    continue
                    
                task = self._process_single_block(
                    block_config,
                    configuration,
                    data,
                    results  # Previous results for dependencies
                )
                tasks.append(task)
                
            # Wait for group to complete
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for i, block_config in enumerate(block_group):
                if not block_config.get("enabled", True):
                    continue
                    
                block_id = block_config["id"]
                
                if isinstance(group_results[i], Exception):
                    logger.error(f"Block {block_id} failed: {group_results[i]}")
                    results[block_id] = {
                        "error": str(group_results[i]),
                        "content": None
                    }
                else:
                    results[block_id] = group_results[i]
                    
                    # Add output variables to data for dependent blocks
                    if "output_variables" in group_results[i]:
                        data.update(group_results[i]["output_variables"])
                        
                processed += 1
                
                # Progress callback
                if progress_callback:
                    await progress_callback(processed, total_blocks)
                    
        return results
        
    async def _process_single_block(
        self,
        block_config: Dict[str, Any],
        configuration: Dict[str, Any],
        data: Dict[str, Any],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single block"""
        
        block_id = block_config["id"]
        block_type = block_config["type"]
        
        # Get block instance
        block = self.block_registry.create_block(block_type)
        if not block:
            raise ValueError(f"Unknown block type: {block_type}")
            
        # Prepare context
        context = {
            "ai_service": self.ai_service,
            "configuration": configuration,
            "previous_results": previous_results
        }
        
        # Get block parameters
        parameters = block_config.get("parameters", {})
        
        # Validate data
        errors = await block.validate_data(data, parameters)
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")
            
        # Process block
        try:
            processed_data = await block.process(data, parameters, context)
            
            # Render to requested formats
            rendered = {}
            for format in configuration.get("output_formats", ["html"]):
                rendered[format] = await block.render(processed_data, format)
                
            return {
                "block_id": block_id,
                "block_type": block_type,
                "processed_data": processed_data,
                "rendered": rendered,
                "output_variables": processed_data
            }
            
        except Exception as e:
            logger.error(f"Error processing block {block_id}: {e}")
            raise
            
    def _group_blocks_by_dependency(
        self,
        blocks: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group blocks by dependency order"""
        
        # For now, simple implementation - process in order
        # TODO: Implement proper dependency resolution
        
        groups = []
        for block in blocks:
            # Blocks with no dependencies or only data dependencies
            if not block.get("depends_on_blocks", []):
                if not groups:
                    groups.append([])
                groups[0].append(block)
            else:
                # Add to appropriate group based on dependencies
                groups.append([block])
                
        return groups if groups else [[]]
```

## Block Development Guide

### Creating a New Block

1. **Create Block Class**:
```python
from typing import Dict, Any, List, Optional
from .base_block import BaseReportBlock, BlockDefinition, BlockCategory, BlockParameter

class MyCustomBlock(BaseReportBlock):
    """Description of what this block does"""
    
    def get_definition(self) -> BlockDefinition:
        return BlockDefinition(
            id="my_custom_block",
            name="My Custom Block",
            category=BlockCategory.ANALYSIS,
            description="Detailed description",
            parameters=[
                # Define configurable parameters
            ],
            required_variables={
                # Variables that must be present
            },
            optional_variables={
                # Variables that may be used
            },
            output_variables={
                # Variables this block produces
            }
        )
```

2. **Implement Required Methods**:
- `validate_data()`: Check data availability
- `process()`: Transform data
- `render()`: Generate output

3. **Register Block**:
- Place in `blocks/` directory
- Auto-discovery will register it

### Best Practices

1. **Data Validation**: Always validate required data
2. **Error Handling**: Graceful degradation
3. **Performance**: Use async where possible
4. **Output Formats**: Support multiple formats
5. **Documentation**: Clear descriptions and examples

## Conclusion

The block system provides a flexible, extensible framework for building complex reports from modular components. Each block is self-contained with clear interfaces, making it easy to add new functionality without affecting existing blocks.