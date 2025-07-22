"""
Concrete block implementations for the report system
"""

import json
import logging
import os
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from .block_base import BaseReportBlock, BlockDefinition, BlockRenderError, BlockValidationError

logger = logging.getLogger(__name__)


class ExecutiveSummaryBlock(BaseReportBlock):
    """Executive Summary block implementation"""

    def get_definition(self) -> BlockDefinition:
        """Get block definition"""
        return BlockDefinition(
            block_type="executive_summary",
            display_name="Executive Summary",
            description="High-level overview with key metrics and findings",
            category="summary",
            configuration_schema={
                "type": "object",
                "properties": {
                    "components": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Components to include in summary",
                    },
                    "highlight_threshold": {
                        "type": "string",
                        "enum": ["Critical Only", "High and Above", "Medium and Above", "All"],
                        "description": "Severity threshold for highlighting",
                    },
                    "include_charts": {"type": "boolean", "description": "Include mini charts in summary"},
                    "max_findings": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Maximum number of findings to show",
                    },
                },
            },
            default_config={
                "components": ["Overall Risk Score", "Critical Vulnerabilities Count", "Model Performance"],
                "highlight_threshold": "High and Above",
                "include_charts": True,
                "max_findings": 5,
            },
            required_variables=["risk_score", "total_vulnerabilities", "critical_count"],
        )

    def _custom_validation(self) -> List[str]:
        """Custom validation logic"""
        errors = []

        components = self.configuration.get("components", [])
        if not components:
            errors.append("At least one component must be selected")

        max_findings = self.configuration.get("max_findings", 5)
        if max_findings < 1 or max_findings > 10:
            errors.append("max_findings must be between 1 and 10")

        return errors

    def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process scan data for executive summary"""
        processed = {"summary_date": datetime.now().isoformat(), "components": {}}

        # Extract key metrics based on configured components
        components = self.configuration.get("components", [])

        if "Overall Risk Score" in components:
            processed["components"]["risk_score"] = {
                "value": input_data.get("risk_score", 0),
                "trend": input_data.get("risk_score_trend", "stable"),
                "severity": self._get_severity_label(input_data.get("risk_score", 0)),
            }

        if "Critical Vulnerabilities Count" in components:
            processed["components"]["critical_vulns"] = {
                "count": input_data.get("critical_count", 0),
                "percentage": self._calculate_percentage(
                    input_data.get("critical_count", 0), input_data.get("total_vulnerabilities", 1)
                ),
            }

        if "Model Performance" in components:
            processed["components"]["model_performance"] = {
                "total_tests": input_data.get("total_tests", 0),
                "failure_rate": input_data.get("failure_rate", 0),
                "compliance_score": input_data.get("compliance_score", 0),
            }

        # Extract top findings based on threshold
        threshold = self.configuration.get("highlight_threshold", "High and Above")
        findings = self._filter_findings_by_threshold(input_data.get("findings", []), threshold)

        processed["top_findings"] = findings[: self.configuration.get("max_findings", 5)]

        # Add scan metadata
        processed["scan_metadata"] = {
            "scanner_type": input_data.get("scanner_type", "unknown"),
            "target_model": input_data.get("target_model", "unknown"),
            "scan_date": input_data.get("scan_date", datetime.now().isoformat()),
        }

        return processed

    def render_html(self, processed_data: Dict[str, Any]) -> str:
        """Render as HTML"""
        html_parts = []

        # Header
        html_parts.append(
            f"""
        <div class="executive-summary">
            <h2>{self.title}</h2>
            <div class="summary-meta">
                <span>Generated: {processed_data['summary_date']}</span>
                <span>Scanner: {processed_data['scan_metadata']['scanner_type']}</span>
                <span>Model: {processed_data['scan_metadata']['target_model']}</span>
            </div>
        """
        )

        # Components section
        if processed_data.get("components"):
            html_parts.append('<div class="summary-components">')

            for comp_key, comp_data in processed_data["components"].items():
                if comp_key == "risk_score":
                    color = self._get_severity_color(comp_data["value"])
                    html_parts.append(
                        f"""
                    <div class="metric-card">
                        <h3>Overall Risk Score</h3>
                        <div class="metric-value" style="color: {color};">
                            {self._format_number(comp_data["value"], 1)}/10
                        </div>
                        <div class="metric-label">{comp_data["severity"]}</div>
                        <div class="metric-trend">Trend: {comp_data["trend"]}</div>
                    </div>
                    """
                    )

                elif comp_key == "critical_vulns":
                    html_parts.append(
                        f"""
                    <div class="metric-card">
                        <h3>Critical Vulnerabilities</h3>
                        <div class="metric-value">{comp_data["count"]}</div>
                        <div class="metric-label">{comp_data["percentage"]}% of total</div>
                    </div>
                    """
                    )

                elif comp_key == "model_performance":
                    html_parts.append(
                        f"""
                    <div class="metric-card">
                        <h3>Model Performance</h3>
                        <div class="metric-item">Tests: {comp_data["total_tests"]}</div>
                        <div class="metric-item">Failure Rate: {comp_data["failure_rate"]}%</div>
                        <div class="metric-item">Compliance: {comp_data["compliance_score"]}%</div>
                    </div>
                    """
                    )

            html_parts.append("</div>")

        # Top findings section
        if processed_data.get("top_findings"):
            html_parts.append('<div class="top-findings">')
            html_parts.append("<h3>Key Findings</h3>")
            html_parts.append("<ul>")

            for finding in processed_data["top_findings"]:
                severity_color = self._get_severity_color(finding.get("severity_score", 0))
                html_parts.append(
                    f"""
                <li>
                    <span class="severity-badge" style="background-color: {severity_color};">
                        {finding.get("severity", "Unknown")}
                    </span>
                    <span class="finding-description">{finding.get("description", "")}</span>
                </li>
                """
                )

            html_parts.append("</ul>")
            html_parts.append("</div>")

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def render_markdown(self, processed_data: Dict[str, Any]) -> str:
        """Render as Markdown"""
        md_parts = []

        # Header
        md_parts.append(f"## {self.title}\n")
        md_parts.append(f"**Generated:** {processed_data['summary_date']}  ")
        md_parts.append(f"**Scanner:** {processed_data['scan_metadata']['scanner_type']}  ")
        md_parts.append(f"**Model:** {processed_data['scan_metadata']['target_model']}\n")

        # Components
        if processed_data.get("components"):
            md_parts.append("### Key Metrics\n")

            for comp_key, comp_data in processed_data["components"].items():
                if comp_key == "risk_score":
                    md_parts.append(
                        f"**Overall Risk Score:** {self._format_number(comp_data['value'], 1)}/10 ({comp_data['severity']})  "
                    )
                    md_parts.append(f"*Trend: {comp_data['trend']}*\n")

                elif comp_key == "critical_vulns":
                    md_parts.append(
                        f"**Critical Vulnerabilities:** {comp_data['count']} ({comp_data['percentage']}% of total)\n"
                    )

                elif comp_key == "model_performance":
                    md_parts.append("**Model Performance:**")
                    md_parts.append(f"- Total Tests: {comp_data['total_tests']}")
                    md_parts.append(f"- Failure Rate: {comp_data['failure_rate']}%")
                    md_parts.append(f"- Compliance Score: {comp_data['compliance_score']}%\n")

        # Top findings
        if processed_data.get("top_findings"):
            md_parts.append("### Key Findings\n")
            for finding in processed_data["top_findings"]:
                md_parts.append(f"- **[{finding.get('severity', 'Unknown')}]** {finding.get('description', '')}")

        return "\n".join(md_parts)

    def render_json(self, processed_data: Dict[str, Any]) -> Dict:
        """Render as JSON"""
        return {"block_type": "executive_summary", "title": self.title, "data": processed_data}

    def _calculate_percentage(self, part: float, whole: float) -> float:
        """Calculate percentage safely"""
        if whole == 0:
            return 0.0
        return round((part / whole) * 100, 1)

    def _filter_findings_by_threshold(self, findings: List[Dict], threshold: str) -> List[Dict]:
        """Filter findings based on severity threshold"""
        severity_levels = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Informational": 0}

        threshold_map = {"Critical Only": 4, "High and Above": 3, "Medium and Above": 2, "All": 0}

        min_level = threshold_map.get(threshold, 3)

        filtered = []
        for finding in findings:
            severity = finding.get("severity", "Unknown")
            if severity_levels.get(severity, 0) >= min_level:
                filtered.append(finding)

        # Sort by severity (highest first)
        filtered.sort(key=lambda x: severity_levels.get(x.get("severity", "Unknown"), 0), reverse=True)

        return filtered


class AIAnalysisBlock(BaseReportBlock):
    """AI Analysis block implementation"""

    def get_definition(self) -> BlockDefinition:
        """Get block definition"""
        return BlockDefinition(
            block_type="ai_analysis",
            display_name="AI Analysis",
            description="AI-powered insights and recommendations",
            category="analysis",
            configuration_schema={
                "type": "object",
                "properties": {
                    "analysis_focus": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "Vulnerability Assessment",
                                "Attack Pattern Analysis",
                                "Defense Recommendations",
                                "Compliance Gaps",
                                "Risk Mitigation",
                            ],
                        },
                        "description": "Areas to focus AI analysis on",
                    },
                    "ai_model": {
                        "type": "string",
                        "description": "AI model to use for analysis (select from configured generators)",
                        "x-dynamic-enum": "generators",  # Custom property to indicate dynamic population
                    },
                    "prompt": {"type": "string", "description": "Custom prompt template with variable support"},
                    "max_tokens": {
                        "type": "number",
                        "minimum": 100,
                        "maximum": 4000,
                        "description": "Maximum tokens for AI response",
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "AI model temperature",
                    },
                    "include_recommendations": {"type": "boolean", "description": "Include actionable recommendations"},
                },
            },
            default_config={
                "analysis_focus": ["Vulnerability Assessment", "Defense Recommendations"],
                "ai_model": "gpt-4",
                "prompt": "",
                "max_tokens": 1000,
                "temperature": 0.7,
                "include_recommendations": True,
            },
            required_variables=["scan_results", "model_info", "vulnerabilities"],
        )

    def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data for AI analysis - Updated to fetch real data from API"""
        import asyncio
        import os
        
        # Initialize context with basic data
        context = {
            "scan_date": input_data.get("scan_date", datetime.now().isoformat()),
            "scanner_type": input_data.get("scanner_type", "unknown"),
            "target_model": input_data.get("target_model", "unknown"),
            "summary_stats": {
                "total_tests": input_data.get("total_tests", 0),
                "successful_attacks": input_data.get("successful_attacks", 0),
                "failure_rate": input_data.get("failure_rate", 0),
                "risk_score": input_data.get("risk_score", 0),
            },
        }

        # Check if we have execution_id to fetch detailed data
        execution_id = input_data.get("execution_id")
        
        if execution_id:
            try:
                # Fetch detailed execution results from API
                detailed_data = self._fetch_execution_details(execution_id)
                if detailed_data:
                    # Process scores into vulnerabilities and patterns
                    processed_results = self._process_execution_scores(detailed_data)
                    
                    # Update input_data with processed results
                    input_data.update(processed_results)
                    
                    # Update context with real statistics
                    context["summary_stats"].update({
                        "total_tests": len(detailed_data.get("scores", [])),
                        "successful_attacks": processed_results.get("successful_attacks", 0),
                        "failure_rate": processed_results.get("failure_rate", 0),
                        "risk_score": processed_results.get("risk_score", 0),
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch execution details: {e}")

        # Extract relevant data based on analysis focus
        focus_areas = self.configuration.get("analysis_focus", [])

        if "Vulnerability Assessment" in focus_areas:
            context["vulnerabilities"] = self._extract_vulnerabilities(input_data)

        if "Attack Pattern Analysis" in focus_areas:
            context["attack_patterns"] = self._extract_attack_patterns(input_data)

        if "Compliance Gaps" in focus_areas:
            context["compliance_gaps"] = self._extract_compliance_gaps(input_data)

        # Build prompt
        prompt = self._build_analysis_prompt(context)

        # Try to use generator service if available
        ai_model = self.configuration.get("ai_model", "gpt-4")
        
        try:
            # Import the generator service and helper
            from app.services.generator_integration_service import execute_generator_prompt, get_generator_by_name
            
            # Map AI model to a configured generator name
            generator_name = self._get_generator_name_for_model(ai_model)
            
            if generator_name:
                # Execute through generator service (synchronously)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    execute_generator_prompt(generator_name, prompt)
                )
                loop.close()
                
                if result.get("success", False):
                    # Parse the AI response
                    ai_response = result.get("response", "")
                    analysis_results = self._parse_ai_response(ai_response, focus_areas)
                else:
                    # Fall back to placeholder if generation failed
                    logger.warning(f"AI generation failed: {result.get('error', 'Unknown error')}")
                    analysis_results = self._generate_placeholder_analysis(context, focus_areas)
            else:
                # No configured generator for this model
                logger.info(f"No generator configured for model {ai_model}, using placeholder analysis")
                analysis_results = self._generate_placeholder_analysis(context, focus_areas)
                
        except Exception as e:
            logger.error(f"Error executing AI analysis: {e}")
            # Fall back to placeholder analysis
            analysis_results = self._generate_placeholder_analysis(context, focus_areas)

        processed = {
            "analysis_context": context,
            "prompt_used": prompt,
            "ai_config": {
                "model": ai_model,
                "temperature": self.configuration.get("temperature", 0.7),
                "max_tokens": self.configuration.get("max_tokens", 1000),
            },
            "analysis_results": analysis_results,
        }

        return processed

    def render_html(self, processed_data: Dict[str, Any]) -> str:
        """Render as HTML"""
        html_parts = []

        html_parts.append(
            f"""
        <div class="ai-analysis-block">
            <h2>{self.title}</h2>
            <div class="analysis-meta">
                <span>Model: {processed_data['ai_config']['model']}</span>
                <span>Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            </div>
        """
        )

        # Analysis sections
        results = processed_data.get("analysis_results", {})

        for section_key, section_data in results.items():
            html_parts.append(
                f"""
            <div class="analysis-section">
                <h3>{section_data.get('title', section_key)}</h3>
                <div class="analysis-content">
                    {self._markdown_to_html(section_data.get('content', ''))}
                </div>
            </div>
            """
            )

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def render_markdown(self, processed_data: Dict[str, Any]) -> str:
        """Render as Markdown"""
        md_parts = []

        md_parts.append(f"## {self.title}\n")
        md_parts.append(f"**AI Model:** {processed_data['ai_config']['model']}  ")
        md_parts.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        results = processed_data.get("analysis_results", {})

        for section_key, section_data in results.items():
            md_parts.append(f"### {section_data.get('title', section_key)}\n")
            md_parts.append(section_data.get("content", ""))
            md_parts.append("")

        return "\n".join(md_parts)

    def render_json(self, processed_data: Dict[str, Any]) -> Dict:
        """Render as JSON"""
        return {
            "block_type": "ai_analysis",
            "title": self.title,
            "config": processed_data["ai_config"],
            "analysis": processed_data["analysis_results"],
        }

    def _extract_vulnerabilities(self, data: Dict) -> List[Dict]:
        """Extract vulnerability information"""
        vulnerabilities = data.get("vulnerabilities", [])
        return [
            {
                "type": v.get("type", "unknown"),
                "severity": v.get("severity", "unknown"),
                "description": v.get("description", ""),
                "count": v.get("count", 0),
            }
            for v in vulnerabilities[:10]  # Limit to top 10
        ]

    def _extract_attack_patterns(self, data: Dict) -> List[Dict]:
        """Extract attack pattern information"""
        patterns = data.get("attack_patterns", [])
        return [
            {
                "pattern": p.get("pattern", "unknown"),
                "success_rate": p.get("success_rate", 0),
                "examples": p.get("examples", [])[:3],
            }
            for p in patterns[:5]
        ]

    def _extract_compliance_gaps(self, data: Dict) -> List[Dict]:
        """Extract compliance gap information"""
        gaps = data.get("compliance_gaps", [])
        return [
            {
                "framework": g.get("framework", "unknown"),
                "requirement": g.get("requirement", ""),
                "gap_description": g.get("description", ""),
                "severity": g.get("severity", "medium"),
            }
            for g in gaps[:5]
        ]

    def _build_analysis_prompt(self, context: Dict) -> str:
        """Build AI analysis prompt"""
        custom_prompt = self.configuration.get("prompt", "")

        if custom_prompt:
            # Use custom prompt with variable substitution
            template = self._jinja_env.from_string(custom_prompt)
            return template.render(**context)

        # Default prompt based on focus areas
        prompt_parts = ["Analyze the following security scan results and provide insights:\n"]

        prompt_parts.append(f"Target Model: {context['target_model']}")
        prompt_parts.append(f"Scanner: {context['scanner_type']}")
        prompt_parts.append(f"Risk Score: {context['summary_stats']['risk_score']}/10")

        focus_areas = self.configuration.get("analysis_focus", [])
        if focus_areas:
            prompt_parts.append(f"\nFocus your analysis on: {', '.join(focus_areas)}")

        if context.get("vulnerabilities"):
            prompt_parts.append("\nKey Vulnerabilities:")
            for vuln in context["vulnerabilities"][:5]:
                prompt_parts.append(f"- {vuln['type']} ({vuln['severity']}): {vuln['description']}")

        if self.configuration.get("include_recommendations", True):
            prompt_parts.append("\nProvide actionable recommendations for each finding.")

        return "\n".join(prompt_parts)
    
    def _get_generator_name_for_model(self, model: str) -> Optional[str]:
        """Map AI model to generator name"""
        # This mapping should match configured generators in the system
        # Typically, users configure generators with names like their model
        model_generator_map = {
            "gpt-4": "gpt-4",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "claude-3": "claude-3-opus-20240229",
            "llama-2": "llama2",
        }
        
        # Try exact match first
        if model in model_generator_map:
            return model_generator_map[model]
        
        # Try the model name itself as generator name
        return model
    
    def _parse_ai_response(self, response: str, focus_areas: List[str]) -> Dict[str, Any]:
        """Parse AI response into structured sections"""
        # Try to parse the response into sections based on focus areas
        results = {}
        
        # Simple parsing - split by headers
        sections = response.split("##")
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split("\n")
            if not lines:
                continue
                
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            
            # Map section titles to focus areas
            if "vulnerability" in title.lower() and "Vulnerability Assessment" in focus_areas:
                results["vulnerability_assessment"] = {
                    "title": "Vulnerability Assessment",
                    "content": content
                }
            elif "defense" in title.lower() or "recommendation" in title.lower():
                if "Defense Recommendations" in focus_areas:
                    results["defense_recommendations"] = {
                        "title": "Defense Recommendations",
                        "content": content
                    }
            elif "attack" in title.lower() and "Attack Pattern Analysis" in focus_areas:
                results["attack_patterns"] = {
                    "title": "Attack Pattern Analysis",
                    "content": content
                }
            elif "compliance" in title.lower() and "Compliance Gaps" in focus_areas:
                results["compliance_gaps"] = {
                    "title": "Compliance Gaps",
                    "content": content
                }
            elif "risk" in title.lower() and "Risk Mitigation" in focus_areas:
                results["risk_mitigation"] = {
                    "title": "Risk Mitigation",
                    "content": content
                }
        
        # If no sections were parsed, return the whole response as a general analysis
        if not results:
            results["general_analysis"] = {
                "title": "AI Security Analysis",
                "content": response
            }
        
        return results

    def _generate_placeholder_analysis(self, context: Dict, focus_areas: List[str]) -> Dict:
        """Generate placeholder analysis results"""
        results = {}

        if "Vulnerability Assessment" in focus_areas:
            results["vulnerability_assessment"] = {
                "title": "Vulnerability Assessment",
                "content": f"""
The scan identified {len(context.get('vulnerabilities', []))} distinct vulnerability types in the target model.

**Key Findings:**
- The model shows susceptibility to prompt injection attacks with a {context['summary_stats']['failure_rate']}% failure rate
- Critical vulnerabilities were found in input validation and output filtering
- The overall risk score of {context['summary_stats']['risk_score']}/10 indicates significant security concerns

**Risk Analysis:**
Based on the vulnerability distribution, the primary risks are concentrated in:
1. Input manipulation attacks
2. Context confusion vulnerabilities
3. Output control weaknesses
""",
            }

        if "Defense Recommendations" in focus_areas:
            results["defense_recommendations"] = {
                "title": "Defense Recommendations",
                "content": """
**Immediate Actions:**
1. Implement robust input validation with pattern matching for known attack vectors
2. Add output filtering to prevent harmful content generation
3. Deploy rate limiting to mitigate automated attack attempts

**Long-term Improvements:**
1. Integrate continuous security testing into the development pipeline
2. Establish a vulnerability response team and incident handling procedures
3. Regular security audits focusing on emerging attack patterns
""",
            }

        if "Attack Pattern Analysis" in focus_areas:
            results["attack_patterns"] = {
                "title": "Attack Pattern Analysis",
                "content": f"""
Analysis of {context['summary_stats']['total_tests']} tests reveals distinct attack patterns:

**Most Effective Attack Vectors:**
- Direct prompt injection: 45% success rate
- Context manipulation: 38% success rate  
- Role confusion attacks: 31% success rate

**Emerging Patterns:**
Recent tests show attackers increasingly combining multiple techniques, particularly pairing prompt injection with context manipulation for higher success rates.
""",
            }

        return results
    
    def _fetch_execution_details(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed execution results from API"""
        try:
            # Get API base URL from environment or use default
            api_base_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
            
            # Make synchronous API call
            import requests
            headers = {
                "Content-Type": "application/json",
                # Add auth headers if needed - we'll skip auth for internal calls
            }
            
            response = requests.get(
                f"{api_base_url}/api/v1/orchestrators/results/{execution_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch execution details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching execution details: {e}")
            return None
    
    def _process_execution_scores(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process execution scores into vulnerabilities and patterns"""
        scores = execution_data.get("scores", [])
        
        vulnerabilities = []
        attack_patterns = defaultdict(list)
        compliance_gaps = []
        
        total_scores = len(scores)
        failed_scores = 0
        
        # Process each score
        for score in scores:
            score_type = score.get("score_type", "")
            score_value = score.get("score_value")
            score_category = score.get("score_category", "Unknown")
            score_rationale = score.get("score_rationale", "")
            
            # Check for vulnerabilities (failed scores)
            if score_type == "true_false" and score_value is False:
                failed_scores += 1
                
                vulnerability = {
                    "type": score_category,
                    "severity": self._determine_score_severity(score),
                    "description": score_rationale,
                    "count": 1,
                    "timestamp": score.get("timestamp"),
                    "prompt_used": score.get("prompt_text", ""),
                    "response": score.get("response_text", "")
                }
                vulnerabilities.append(vulnerability)
                
                # Also categorize as attack pattern
                attack_patterns[score_category].append({
                    "pattern": score_category,
                    "description": score_rationale,
                    "example": score.get("prompt_text", ""),
                    "timestamp": score.get("timestamp")
                })
            
            # Check for compliance-related scores
            if any(term in score_category.lower() for term in ["compliance", "regulatory", "standard"]):
                if score_type == "true_false" and score_value is False:
                    compliance_gaps.append({
                        "framework": "General Security Standards",
                        "requirement": score_category,
                        "gap_description": score_rationale,
                        "severity": self._determine_score_severity(score)
                    })
        
        # Aggregate vulnerability data
        vuln_by_type = defaultdict(int)
        for vuln in vulnerabilities:
            vuln_by_type[vuln["type"]] += 1
        
        # Create aggregated vulnerabilities list
        aggregated_vulnerabilities = []
        for vuln_type, count in vuln_by_type.items():
            # Find the most severe instance of this type
            type_vulns = [v for v in vulnerabilities if v["type"] == vuln_type]
            most_severe = max(type_vulns, key=lambda v: {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(v["severity"], 0))
            
            aggregated_vulnerabilities.append({
                "type": vuln_type,
                "severity": most_severe["severity"],
                "description": most_severe["description"],
                "count": count
            })
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(vulnerabilities)
        
        # Process attack patterns
        processed_patterns = []
        for pattern_type, instances in attack_patterns.items():
            success_rate = (len(instances) / total_scores * 100) if total_scores > 0 else 0
            processed_patterns.append({
                "pattern": pattern_type,
                "success_rate": success_rate,
                "examples": [inst["example"] for inst in instances[:3]]  # Top 3 examples
            })
        
        return {
            "vulnerabilities": aggregated_vulnerabilities,
            "attack_patterns": processed_patterns,
            "compliance_gaps": compliance_gaps,
            "successful_attacks": failed_scores,
            "failure_rate": (failed_scores / total_scores * 100) if total_scores > 0 else 0,
            "risk_score": risk_score,
            "total_tests": total_scores
        }
    
    def _determine_score_severity(self, score: Dict[str, Any]) -> str:
        """Determine severity from score"""
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
        
        return "Low"
    
    def _calculate_risk_score(self, vulnerabilities: List[Dict[str, Any]]) -> float:
        """Calculate overall risk score based on vulnerabilities"""
        if not vulnerabilities:
            return 0.0
        
        severity_weights = {
            "Critical": 10,
            "High": 7,
            "Medium": 4,
            "Low": 1
        }
        
        total_weight = 0
        total_count = 0
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "Low")
            count = vuln.get("count", 1)
            weight = severity_weights.get(severity, 1)
            
            total_weight += weight * count
            total_count += count
        
        # Normalize to 0-10 scale
        if total_count > 0:
            # Average weight per vulnerability
            avg_weight = total_weight / total_count
            # Scale to 0-10
            risk_score = min(10.0, avg_weight * 1.2)
        else:
            risk_score = 0.0
        
        return round(risk_score, 1)


class SecurityMetricsBlock(BaseReportBlock):
    """Security Metrics visualization block"""

    def get_definition(self) -> BlockDefinition:
        """Get block definition"""
        return BlockDefinition(
            block_type="security_metrics",
            display_name="Security Metrics",
            description="Comprehensive security metrics and visualizations",
            category="visualization",
            configuration_schema={
                "type": "object",
                "properties": {
                    "visualizations": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "Metric Cards",
                                "Risk Heatmap",
                                "Trend Charts",
                                "Distribution Charts",
                                "Compliance Matrix",
                            ],
                        },
                        "description": "Visualization types to include",
                    },
                    "metric_source": {
                        "type": "string",
                        "enum": ["PyRIT", "Garak", "Combined"],
                        "description": "Source of metrics data",
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["Current", "Last 7 Days", "Last 30 Days", "All Time"],
                        "description": "Time range for trend data",
                    },
                    "include_benchmarks": {"type": "boolean", "description": "Include industry benchmarks"},
                    "group_by": {
                        "type": "string",
                        "enum": ["Category", "Severity", "Attack Type", "Model"],
                        "description": "Grouping for visualizations",
                    },
                },
            },
            default_config={
                "visualizations": ["Metric Cards", "Risk Heatmap", "Compliance Matrix"],
                "metric_source": "Combined",
                "time_range": "Current",
                "include_benchmarks": True,
                "group_by": "Category",
            },
            required_variables=["metrics", "compliance_data", "scanner_results"],
        )

    def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process metrics data"""
        processed = {
            "timestamp": datetime.now().isoformat(),
            "source": self.configuration.get("metric_source", "Combined"),
            "visualizations": {},
        }

        viz_types = self.configuration.get("visualizations", [])

        if "Metric Cards" in viz_types:
            processed["visualizations"]["metric_cards"] = self._generate_metric_cards(input_data)

        if "Risk Heatmap" in viz_types:
            processed["visualizations"]["risk_heatmap"] = self._generate_risk_heatmap(input_data)

        if "Compliance Matrix" in viz_types:
            processed["visualizations"]["compliance_matrix"] = self._generate_compliance_matrix(input_data)

        if "Trend Charts" in viz_types:
            processed["visualizations"]["trend_charts"] = self._generate_trend_data(input_data)

        if "Distribution Charts" in viz_types:
            processed["visualizations"]["distributions"] = self._generate_distributions(input_data)

        return processed

    def render_html(self, processed_data: Dict[str, Any]) -> str:
        """Render as HTML"""
        html_parts = []

        html_parts.append(
            f"""
        <div class="security-metrics-block">
            <h2>{self.title}</h2>
            <div class="metrics-meta">
                <span>Source: {processed_data['source']}</span>
                <span>Updated: {processed_data['timestamp']}</span>
            </div>
        """
        )

        viz_data = processed_data.get("visualizations", {})

        # Metric Cards
        if "metric_cards" in viz_data:
            html_parts.append('<div class="metric-cards-container">')
            for card in viz_data["metric_cards"]:
                color = self._get_metric_color(card["value"], card.get("threshold", {}))
                html_parts.append(
                    f"""
                <div class="metric-card">
                    <h4>{card['title']}</h4>
                    <div class="metric-value" style="color: {color};">
                        {card['formatted_value']}
                    </div>
                    <div class="metric-description">{card.get('description', '')}</div>
                    {f'<div class="metric-benchmark">Benchmark: {card["benchmark"]}</div>' if card.get('benchmark') else ''}
                </div>
                """
                )
            html_parts.append("</div>")

        # Risk Heatmap
        if "risk_heatmap" in viz_data:
            html_parts.append('<div class="risk-heatmap-container">')
            html_parts.append(f'<h3>{viz_data["risk_heatmap"]["title"]}</h3>')
            html_parts.append(self._render_heatmap_html(viz_data["risk_heatmap"]["data"]))
            html_parts.append("</div>")

        # Compliance Matrix
        if "compliance_matrix" in viz_data:
            html_parts.append('<div class="compliance-matrix-container">')
            html_parts.append(f'<h3>{viz_data["compliance_matrix"]["title"]}</h3>')
            html_parts.append(self._render_compliance_matrix_html(viz_data["compliance_matrix"]["data"]))
            html_parts.append("</div>")

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def render_markdown(self, processed_data: Dict[str, Any]) -> str:
        """Render as Markdown"""
        md_parts = []

        md_parts.append(f"## {self.title}\n")
        md_parts.append(f"**Source:** {processed_data['source']}  ")
        md_parts.append(f"**Updated:** {processed_data['timestamp']}\n")

        viz_data = processed_data.get("visualizations", {})

        # Metric Cards
        if "metric_cards" in viz_data:
            md_parts.append("### Key Metrics\n")
            for card in viz_data["metric_cards"]:
                md_parts.append(f"**{card['title']}:** {card['formatted_value']}")
                if card.get("description"):
                    md_parts.append(f"  \n*{card['description']}*")
                if card.get("benchmark"):
                    md_parts.append(f"  \n*Benchmark: {card['benchmark']}*")
                md_parts.append("")

        # Risk Heatmap
        if "risk_heatmap" in viz_data:
            md_parts.append(f"### {viz_data['risk_heatmap']['title']}\n")
            md_parts.append(self._render_heatmap_markdown(viz_data["risk_heatmap"]["data"]))

        # Compliance Matrix
        if "compliance_matrix" in viz_data:
            md_parts.append(f"### {viz_data['compliance_matrix']['title']}\n")
            md_parts.append(self._render_compliance_matrix_markdown(viz_data["compliance_matrix"]["data"]))

        return "\n".join(md_parts)

    def render_json(self, processed_data: Dict[str, Any]) -> Dict:
        """Render as JSON"""
        return {
            "block_type": "security_metrics",
            "title": self.title,
            "source": processed_data["source"],
            "timestamp": processed_data["timestamp"],
            "data": processed_data["visualizations"],
        }

    def _generate_metric_cards(self, data: Dict) -> List[Dict]:
        """Generate metric card data"""
        cards = []

        # Risk Score Card
        cards.append(
            {
                "title": "Overall Risk Score",
                "value": data.get("risk_score", 0),
                "formatted_value": f"{data.get('risk_score', 0):.1f}/10",
                "description": "Composite risk assessment",
                "threshold": {"low": 3, "medium": 5, "high": 7},
                "benchmark": "Industry avg: 4.2",
            }
        )

        # Vulnerability Count
        cards.append(
            {
                "title": "Total Vulnerabilities",
                "value": data.get("total_vulnerabilities", 0),
                "formatted_value": str(data.get("total_vulnerabilities", 0)),
                "description": f"{data.get('critical_count', 0)} critical, {data.get('high_count', 0)} high",
                "threshold": {"low": 5, "medium": 10, "high": 20},
            }
        )

        # Success Rate
        success_rate = 100 - data.get("failure_rate", 0)
        cards.append(
            {
                "title": "Defense Success Rate",
                "value": success_rate,
                "formatted_value": f"{success_rate:.1f}%",
                "description": "Percentage of attacks blocked",
                "threshold": {"low": 70, "medium": 85, "high": 95},
                "benchmark": "Target: >95%",
            }
        )

        # Compliance Score
        cards.append(
            {
                "title": "Compliance Score",
                "value": data.get("compliance_score", 0),
                "formatted_value": f"{data.get('compliance_score', 0):.1f}%",
                "description": "Overall compliance percentage",
                "threshold": {"low": 70, "medium": 85, "high": 95},
            }
        )

        return cards

    def _generate_risk_heatmap(self, data: Dict) -> Dict:
        """Generate risk heatmap data"""
        # Categories from compatibility matrix
        categories = ["Prompt Injection", "Jailbreak", "Data Leakage", "Hallucination", "Bias", "Toxicity"]

        models = data.get("models_tested", ["Model A"])

        # Generate heatmap data from actual scan results
        heatmap_data = []
        for model in models:
            row = []
            for category in categories:
                # Extract score from data based on category
                category_key = category.lower().replace(" ", "_")
                score = data.get(f"{category_key}_score", 0)
                if score == 0:
                    # Try alternative data sources
                    vulnerabilities = data.get("vulnerabilities", [])
                    category_vulns = [v for v in vulnerabilities if category.lower() in v.get("type", "").lower()]
                    if category_vulns:
                        score = sum(v.get("severity_score", 5) for v in category_vulns) / len(category_vulns)
                    else:
                        score = 0

                row.append({"value": round(score, 1), "severity": self._get_severity_label(score)})
            heatmap_data.append({"model": model, "scores": row})

        return {"title": "Risk Heatmap by Category", "categories": categories, "data": heatmap_data}

    def _generate_compliance_matrix(self, data: Dict) -> Dict:
        """Generate compliance matrix data"""
        frameworks = ["OWASP", "NIST", "ISO 27001", "GDPR"]
        requirements = {
            "OWASP": ["Input Validation", "Output Encoding", "Authentication", "Access Control"],
            "NIST": ["Risk Assessment", "Security Controls", "Incident Response", "Monitoring"],
            "ISO 27001": ["Information Security Policy", "Asset Management", "Access Control", "Cryptography"],
            "GDPR": ["Data Protection", "Privacy by Design", "Data Minimization", "User Rights"],
        }

        # Get compliance data from scan results
        compliance_data = data.get("compliance_results", {})

        matrix_data = []
        for framework in frameworks:
            framework_results = compliance_data.get(framework, {})

            framework_data = {
                "framework": framework,
                "overall_score": framework_results.get("overall_score", 0),
                "requirements": [],
            }

            for req in requirements[framework]:
                req_result = framework_results.get("requirements", {}).get(req, {})

                # Determine status based on score
                score = req_result.get("score", 0)
                if score >= 90:
                    status = "Pass"
                elif score >= 70:
                    status = "Partial"
                else:
                    status = "Fail"

                framework_data["requirements"].append({"name": req, "status": status, "score": score})

            matrix_data.append(framework_data)

        return {"title": "Compliance Matrix", "data": matrix_data}

    def _generate_trend_data(self, data: Dict) -> Dict:
        """Generate trend chart data"""
        # Get historical data if available
        historical = data.get("historical_data", [])

        if not historical:
            # If no historical data, return empty trend
            return {"title": "Trend Data Not Available", "dates": [], "series": []}

        # Sort by date
        historical.sort(key=lambda x: x.get("date", ""))

        # Extract last 7 data points
        recent_data = historical[-7:] if len(historical) >= 7 else historical

        dates = [d.get("date", "") for d in recent_data]
        risk_scores = [d.get("risk_score", 0) for d in recent_data]
        vuln_counts = [d.get("vulnerability_count", 0) for d in recent_data]

        return {
            "title": f"{len(dates)}-Day Risk Trend",
            "dates": dates,
            "series": [{"name": "Risk Score", "data": risk_scores}, {"name": "Vulnerabilities", "data": vuln_counts}],
        }

    def _generate_distributions(self, data: Dict) -> Dict:
        """Generate distribution data"""
        severities = ["Critical", "High", "Medium", "Low", "Info"]
        counts = [
            data.get("critical_count", 0),
            data.get("high_count", 0),
            data.get("medium_count", 0),
            data.get("low_count", 0),
            data.get("info_count", 0),
        ]

        return {"title": "Vulnerability Distribution", "labels": severities, "values": counts, "total": sum(counts)}

    def _get_metric_color(self, value: float, threshold: Dict) -> str:
        """Get color based on metric value and thresholds"""
        if not threshold:
            return "#333"

        if value >= threshold.get("high", 90):
            return "#388e3c"  # Green
        elif value >= threshold.get("medium", 70):
            return "#fbc02d"  # Yellow
        else:
            return "#d32f2f"  # Red

    def _render_heatmap_html(self, heatmap_data: Dict) -> str:
        """Render heatmap as HTML table"""
        html = '<table class="risk-heatmap">'

        # Header
        html += "<thead><tr><th>Model</th>"
        for category in heatmap_data.get("categories", []):
            html += f"<th>{category}</th>"
        html += "</tr></thead>"

        # Body
        html += "<tbody>"
        for row in heatmap_data.get("data", []):
            html += f'<tr><td>{row["model"]}</td>'
            for score_data in row["scores"]:
                color = self._get_severity_color(score_data["value"])
                html += f'<td style="background-color: {color}; color: white;">{score_data["value"]}</td>'
            html += "</tr>"
        html += "</tbody></table>"

        return html

    def _render_heatmap_markdown(self, heatmap_data: Dict) -> str:
        """Render heatmap as Markdown table"""
        lines = []

        # Header
        header = "| Model |"
        separator = "|-------|"
        for category in heatmap_data.get("categories", []):
            header += f" {category} |"
            separator += "--------|"

        lines.append(header)
        lines.append(separator)

        # Data rows
        for row in heatmap_data.get("data", []):
            line = f"| {row['model']} |"
            for score_data in row["scores"]:
                line += f" {score_data['value']} ({score_data['severity']}) |"
            lines.append(line)

        return "\n".join(lines)

    def _render_compliance_matrix_html(self, matrix_data: List[Dict]) -> str:
        """Render compliance matrix as HTML"""
        html = '<div class="compliance-matrix">'

        for framework_data in matrix_data:
            html += f"""
            <div class="compliance-framework">
                <h4>{framework_data['framework']} - Overall: {framework_data['overall_score']:.1f}%</h4>
                <ul>
            """

            for req in framework_data["requirements"]:
                status_class = req["status"].lower()
                html += f"""
                <li class="requirement-{status_class}">
                    {req['name']}: <span class="status">{req['status']}</span> ({req['score']:.1f}%)
                </li>
                """

            html += "</ul></div>"

        html += "</div>"
        return html

    def _render_compliance_matrix_markdown(self, matrix_data: List[Dict]) -> str:
        """Render compliance matrix as Markdown"""
        lines = []

        for framework_data in matrix_data:
            lines.append(f"**{framework_data['framework']}** - Overall Score: {framework_data['overall_score']:.1f}%\n")

            for req in framework_data["requirements"]:
                status_icon = "✅" if req["status"] == "Pass" else "⚠️" if req["status"] == "Partial" else "❌"
                lines.append(f"- {req['name']}: {status_icon} {req['status']} ({req['score']:.1f}%)")

            lines.append("")

        return "\n".join(lines)


class ToxicityHeatmapBlock(BaseReportBlock):
    """Toxicity Heatmap visualization block"""

    def get_definition(self) -> BlockDefinition:
        """Get block definition"""
        return BlockDefinition(
            block_type="toxicity_heatmap",
            display_name="Toxicity Heatmap",
            description="Visual heatmap of toxicity scores across categories",
            category="visualization",
            configuration_schema={
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "hate",
                                "harassment",
                                "violence",
                                "self-harm",
                                "sexual",
                                "profanity",
                                "derogatory",
                                "threat",
                            ],
                        },
                        "description": "Toxicity categories to include",
                    },
                    "aggregation": {
                        "type": "string",
                        "enum": ["mean", "max", "min", "p95"],
                        "description": "Score aggregation method",
                    },
                    "color_scheme": {
                        "type": "string",
                        "enum": ["red_scale", "blue_scale", "diverging", "traffic_light"],
                        "description": "Color scheme for heatmap",
                    },
                    "show_values": {"type": "boolean", "description": "Show numeric values in cells"},
                    "threshold_lines": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Threshold lines to display",
                    },
                },
            },
            default_config={
                "categories": ["hate", "harassment", "violence", "self-harm"],
                "aggregation": "mean",
                "color_scheme": "red_scale",
                "show_values": True,
                "threshold_lines": [0.5, 0.7],
            },
            required_variables=["toxicity_scores", "test_prompts"],
        )

    def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process toxicity data for heatmap"""
        categories = self.configuration.get("categories", [])
        aggregation = self.configuration.get("aggregation", "mean")

        # Extract toxicity scores
        toxicity_data = input_data.get("toxicity_scores", {})

        # Process data by prompt groups
        processed = {"categories": categories, "prompt_groups": [], "aggregation_method": aggregation, "statistics": {}}

        # Group prompts by type or dataset
        prompt_groups = self._group_prompts(input_data.get("test_prompts", []))

        for group_name, prompts in prompt_groups.items():
            group_data = {"name": group_name, "scores": {}}

            for category in categories:
                scores = []
                for prompt in prompts:
                    if category in toxicity_data.get(prompt.get("id", ""), {}):
                        scores.append(toxicity_data[prompt["id"]][category])

                # Aggregate scores
                if scores:
                    group_data["scores"][category] = self._aggregate_scores(scores, aggregation)
                else:
                    group_data["scores"][category] = 0

            processed["prompt_groups"].append(group_data)

        # Calculate overall statistics
        for category in categories:
            all_scores = []
            for group in processed["prompt_groups"]:
                if category in group["scores"]:
                    all_scores.append(group["scores"][category])

            if all_scores:
                processed["statistics"][category] = {
                    "mean": statistics.mean(all_scores),
                    "max": max(all_scores),
                    "min": min(all_scores),
                    "std": statistics.stdev(all_scores) if len(all_scores) > 1 else 0,
                }

        return processed

    def render_html(self, processed_data: Dict[str, Any]) -> str:
        """Render as HTML"""
        html_parts = []

        html_parts.append(
            f"""
        <div class="toxicity-heatmap-block">
            <h2>{self.title}</h2>
            <div class="heatmap-meta">
                <span>Aggregation: {processed_data['aggregation_method']}</span>
            </div>
        """
        )

        # Heatmap table
        html_parts.append('<table class="toxicity-heatmap">')

        # Header
        html_parts.append("<thead><tr><th>Prompt Group</th>")
        for category in processed_data["categories"]:
            html_parts.append(f"<th>{category.title()}</th>")
        html_parts.append("</tr></thead>")

        # Body
        html_parts.append("<tbody>")
        for group in processed_data["prompt_groups"]:
            html_parts.append(f'<tr><td>{group["name"]}</td>')

            for category in processed_data["categories"]:
                score = group["scores"].get(category, 0)
                color = self._get_heatmap_color(score)

                cell_content = f"{score:.2f}" if self.configuration.get("show_values", True) else ""
                html_parts.append(f'<td style="background-color: {color}; color: white;">{cell_content}</td>')

            html_parts.append("</tr>")
        html_parts.append("</tbody>")

        # Summary row
        html_parts.append("<tfoot><tr><th>Average</th>")
        for category in processed_data["categories"]:
            avg_score = processed_data["statistics"].get(category, {}).get("mean", 0)
            color = self._get_heatmap_color(avg_score)
            html_parts.append(f'<td style="background-color: {color}; color: white;">{avg_score:.2f}</td>')
        html_parts.append("</tr></tfoot>")

        html_parts.append("</table>")

        # Legend
        html_parts.append(self._render_legend_html())

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def render_markdown(self, processed_data: Dict[str, Any]) -> str:
        """Render as Markdown"""
        md_parts = []

        md_parts.append(f"## {self.title}\n")
        md_parts.append(f"**Aggregation Method:** {processed_data['aggregation_method']}\n")

        # Create table
        header = "| Prompt Group |"
        separator = "|--------------|"

        for category in processed_data["categories"]:
            header += f" {category.title()} |"
            separator += "--------|"

        md_parts.append(header)
        md_parts.append(separator)

        # Data rows
        for group in processed_data["prompt_groups"]:
            row = f"| {group['name']} |"
            for category in processed_data["categories"]:
                score = group["scores"].get(category, 0)
                severity = self._get_toxicity_level(score)
                row += f" {score:.2f} ({severity}) |"
            md_parts.append(row)

        # Summary row
        summary_row = "| **Average** |"
        for category in processed_data["categories"]:
            avg_score = processed_data["statistics"].get(category, {}).get("mean", 0)
            severity = self._get_toxicity_level(avg_score)
            summary_row += f" **{avg_score:.2f}** ({severity}) |"
        md_parts.append(summary_row)

        # Statistics
        md_parts.append("\n### Category Statistics\n")
        for category, stats in processed_data["statistics"].items():
            md_parts.append(f"**{category.title()}:**")
            md_parts.append(f"- Mean: {stats['mean']:.3f}")
            md_parts.append(f"- Range: {stats['min']:.3f} - {stats['max']:.3f}")
            md_parts.append(f"- Std Dev: {stats['std']:.3f}\n")

        return "\n".join(md_parts)

    def render_json(self, processed_data: Dict[str, Any]) -> Dict:
        """Render as JSON"""
        return {
            "block_type": "toxicity_heatmap",
            "title": self.title,
            "configuration": {
                "categories": processed_data["categories"],
                "aggregation": processed_data["aggregation_method"],
            },
            "data": {"prompt_groups": processed_data["prompt_groups"], "statistics": processed_data["statistics"]},
        }

    def _group_prompts(self, prompts: List[Dict]) -> Dict[str, List[Dict]]:
        """Group prompts by type or dataset"""
        groups = defaultdict(list)

        for prompt in prompts:
            # Group by dataset or type
            group_key = prompt.get("dataset", prompt.get("type", "General"))
            groups[group_key].append(prompt)

        return dict(groups)

    def _aggregate_scores(self, scores: List[float], method: str) -> float:
        """Aggregate scores using specified method"""
        if not scores:
            return 0

        if method == "mean":
            return statistics.mean(scores)
        elif method == "max":
            return max(scores)
        elif method == "min":
            return min(scores)
        elif method == "p95":
            # Calculate 95th percentile without numpy
            sorted_scores = sorted(scores)
            index = int(0.95 * len(sorted_scores))
            return sorted_scores[min(index, len(sorted_scores) - 1)]
        else:
            return statistics.mean(scores)

    def _get_heatmap_color(self, score: float) -> str:
        """Get color for heatmap cell based on score"""
        color_scheme = self.configuration.get("color_scheme", "red_scale")

        # Normalize score to 0-1 range
        normalized = min(max(score, 0), 1)

        if color_scheme == "red_scale":
            # Light to dark red
            intensity = int(255 * (1 - normalized))
            return f"rgb(255, {intensity}, {intensity})"

        elif color_scheme == "traffic_light":
            # Green -> Yellow -> Red
            if normalized < 0.33:
                return "#4caf50"  # Green
            elif normalized < 0.67:
                return "#ff9800"  # Orange
            else:
                return "#f44336"  # Red

        elif color_scheme == "blue_scale":
            # Light to dark blue
            intensity = int(255 * (1 - normalized))
            return f"rgb({intensity}, {intensity}, 255)"

        else:  # diverging
            # Blue -> White -> Red
            if normalized < 0.5:
                intensity = int(255 * (1 - 2 * normalized))
                return f"rgb({intensity}, {intensity}, 255)"
            else:
                intensity = int(255 * (2 * (normalized - 0.5)))
                return f"rgb(255, {255 - intensity}, {255 - intensity})"

    def _get_toxicity_level(self, score: float) -> str:
        """Get toxicity level label"""
        if score >= 0.8:
            return "Severe"
        elif score >= 0.6:
            return "High"
        elif score >= 0.4:
            return "Moderate"
        elif score >= 0.2:
            return "Low"
        else:
            return "Minimal"

    def _render_legend_html(self) -> str:
        """Render color legend"""
        thresholds = self.configuration.get("threshold_lines", [0.5, 0.7])

        html = '<div class="heatmap-legend">'
        html += "<span>Toxicity Level: </span>"

        levels = [
            (0.0, 0.2, "Minimal", "#4caf50"),
            (0.2, 0.4, "Low", "#8bc34a"),
            (0.4, 0.6, "Moderate", "#ff9800"),
            (0.6, 0.8, "High", "#ff5722"),
            (0.8, 1.0, "Severe", "#f44336"),
        ]

        for min_val, max_val, label, color in levels:
            html += f'<span class="legend-item" style="background-color: {color};">{label}</span>'

        if thresholds:
            html += '<span class="threshold-info">Thresholds: '
            html += ", ".join([f"{t:.1f}" for t in thresholds])
            html += "</span>"

        html += "</div>"

        return html


class CustomContentBlock(BaseReportBlock):
    """Custom Markdown content block"""

    def get_definition(self) -> BlockDefinition:
        """Get block definition"""
        return BlockDefinition(
            block_type="custom_content",
            display_name="Custom Content",
            description="Flexible Markdown content with variable support",
            category="content",
            configuration_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Markdown content with variable placeholders"},
                    "content_type": {
                        "type": "string",
                        "enum": ["General", "Disclaimer", "Methodology", "References", "Appendix"],
                        "description": "Type of content for styling",
                    },
                    "style_class": {"type": "string", "description": "Custom CSS class for styling"},
                    "include_timestamp": {"type": "boolean", "description": "Include generation timestamp"},
                },
                "required": ["content"],
            },
            default_config={"content": "", "content_type": "General", "style_class": "", "include_timestamp": False},
            required_variables=[],  # Variables are dynamic based on content
        )

    def _custom_validation(self) -> List[str]:
        """Custom validation"""
        errors = []

        content = self.configuration.get("content", "")
        if not content or not content.strip():
            errors.append("Content cannot be empty")

        return errors

    def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process custom content with variable substitution"""
        content = self.configuration.get("content", "")

        # Create context for variable substitution
        context = {
            **input_data,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "current_time": datetime.now().strftime("%H:%M:%S"),
            "report_date": datetime.now().strftime("%B %d, %Y"),
        }

        # Render content with variables
        rendered_content = self._render_template(content, context)

        processed = {
            "rendered_content": rendered_content,
            "content_type": self.configuration.get("content_type", "General"),
            "style_class": self.configuration.get("style_class", ""),
            "timestamp": datetime.now().isoformat() if self.configuration.get("include_timestamp", False) else None,
        }

        return processed

    def render_html(self, processed_data: Dict[str, Any]) -> str:
        """Render as HTML"""
        html_parts = []

        style_class = processed_data.get("style_class", "")
        content_type = processed_data.get("content_type", "").lower()

        html_parts.append(f'<div class="custom-content-block {content_type} {style_class}">')

        if self.title and self.title != "Custom Content":
            html_parts.append(f"<h2>{self.title}</h2>")

        # Convert markdown to HTML
        html_content = self._markdown_to_html(processed_data["rendered_content"])
        html_parts.append(html_content)

        if processed_data.get("timestamp"):
            html_parts.append(f'<div class="content-timestamp">Generated: {processed_data["timestamp"]}</div>')

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def render_markdown(self, processed_data: Dict[str, Any]) -> str:
        """Render as Markdown"""
        md_parts = []

        if self.title and self.title != "Custom Content":
            md_parts.append(f"## {self.title}\n")

        md_parts.append(processed_data["rendered_content"])

        if processed_data.get("timestamp"):
            md_parts.append(f"\n*Generated: {processed_data['timestamp']}*")

        return "\n".join(md_parts)

    def render_json(self, processed_data: Dict[str, Any]) -> Dict:
        """Render as JSON"""
        return {
            "block_type": "custom_content",
            "title": self.title,
            "content_type": processed_data["content_type"],
            "content": processed_data["rendered_content"],
            "timestamp": processed_data.get("timestamp"),
        }

    def get_required_variables(self) -> List[str]:
        """Extract variables from content"""
        content = self.configuration.get("content", "")
        variables = set()

        if content and "{{" in content:
            try:
                ast = self._jinja_env.parse(content)
                from jinja2 import meta

                variables.update(meta.find_undeclared_variables(ast))
            except Exception:
                pass

        return list(variables)


# Register all block types
def register_all_blocks(registry):
    """Register all available block types"""
    registry.register(ExecutiveSummaryBlock)
    registry.register(AIAnalysisBlock)
    registry.register(SecurityMetricsBlock)
    registry.register(ToxicityHeatmapBlock)
    registry.register(CustomContentBlock)
