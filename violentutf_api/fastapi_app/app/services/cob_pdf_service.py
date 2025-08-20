# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
COB Report PDF Generation Service
Secure PDF generation with HTML sanitization and existing security patterns
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import bleach
import markdown
from weasyprint import CSS, HTML

logger = logging.getLogger(__name__)

# Allowed HTML tags for safe PDF generation
ALLOWED_TAGS = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "br",
    "strong",
    "em",
    "u",
    "ol",
    "ul",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "div",
    "span",
    "pre",
    "code",
    "blockquote",
    "hr",
    "a",
    "img",
]

# Allowed HTML attributes for safe PDF generation
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "table": ["class"],
    "th": ["scope", "class"],
    "td": ["class"],
    "div": ["class"],
    "span": ["class"],
    "p": ["class"],
    "h1": ["class"],
    "h2": ["class"],
    "h3": ["class"],
    "h4": ["class"],
    "h5": ["class"],
    "h6": ["class"],
}

# Default CSS for professional PDF appearance
DEFAULT_PDF_CSS = """
@page {
    size: A4;
    margin: 2cm;
    @top-center {
        content: "ViolentUTF - COB Report";
    }
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
    }
}

body {
    font-family: 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.4;
    color: #333;
}

h1 {
    color: #2c3e50;
    font-size: 18pt;
    border-bottom: 2px solid #3498db;
    padding-bottom: 5pt;
    margin-bottom: 15pt;
}

h2 {
    color: #34495e;
    font-size: 14pt;
    margin-top: 20pt;
    margin-bottom: 10pt;
}

h3 {
    color: #34495e;
    font-size: 12pt;
    margin-top: 15pt;
    margin-bottom: 8pt;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15pt 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 8pt;
    text-align: left;
}

th {
    background-color: #f8f9fa;
    font-weight: bold;
}

.executive-summary {
    background-color: #f8f9fa;
    border-left: 4px solid #3498db;
    padding: 15pt;
    margin: 15pt 0;
}

.ai-analysis {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 15pt;
    margin: 15pt 0;
}

.security-metrics {
    background-color: #d1ecf1;
    border-left: 4px solid #17a2b8;
    padding: 15pt;
    margin: 15pt 0;
}

.warning {
    background-color: #f8d7da;
    border-left: 4px solid #dc3545;
    padding: 15pt;
    margin: 15pt 0;
}

pre, code {
    background-color: #f4f4f4;
    padding: 5pt;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
}

blockquote {
    border-left: 3px solid #ccc;
    margin: 15pt 0;
    padding-left: 15pt;
    font-style: italic;
}
"""


class COBPDFGenerator:
    """Secure PDF generator for COB reports using existing security patterns"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def generate_pdf(self, report_data: Dict[str, Any], template_config: Dict[str, Any]) -> bytes:
        """
        Generate PDF from report data using template configuration

        Args:
            report_data: Report content and metadata
            template_config: Template structure and configuration

        Returns:
            bytes: PDF content as bytes

        Raises:
            ValueError: If template or data is invalid
            RuntimeError: If PDF generation fails
        """
        try:
            self.logger.info(f"Starting PDF generation for report: {report_data.get('report_name', 'Unknown')}")

            # Generate markdown content from template and data
            markdown_content = self._generate_markdown_content(report_data, template_config)

            # Convert markdown to HTML
            html_content = markdown.markdown(
                markdown_content, extensions=["tables", "toc", "codehilite", "fenced_code"]
            )

            # Sanitize HTML for security
            safe_html = self._sanitize_html(html_content)

            # Wrap in complete HTML document
            full_html = self._wrap_html_document(safe_html, report_data)

            # Generate PDF with secure CSS
            pdf_bytes = self._generate_pdf_bytes(full_html)

            self.logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            self.logger.error(f"PDF generation failed: {e}")
            raise RuntimeError(f"Failed to generate PDF: {str(e)}")

    def _generate_markdown_content(self, report_data: Dict[str, Any], template_config: Dict[str, Any]) -> str:
        """Generate markdown content from template blocks and report data"""
        markdown_parts = []

        # Add report header
        report_name = report_data.get("report_name", "COB Report")
        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        markdown_parts.append(f"# {report_name}")
        markdown_parts.append(f"**Generated:** {generation_date}")
        markdown_parts.append(
            f"**Period:** {report_data.get('report_period_start', 'N/A')} to {report_data.get('report_period_end', 'N/A')}"
        )
        markdown_parts.append("---\n")

        # Process template blocks
        blocks = template_config.get("blocks", [])
        content_blocks = report_data.get("content_blocks", {})
        ai_analysis_results = report_data.get("ai_analysis_results", {})

        for block in blocks:
            block_type = block.get("type", "")
            block_title = block.get("title", "Untitled Block")

            markdown_parts.append(f"## {block_title}")

            if block_type == "executive_summary":
                content = content_blocks.get("executive_summary", "No executive summary available.")
                markdown_parts.append(f'<div class="executive-summary">\n\n{content}\n\n</div>')

            elif block_type == "ai_analysis":
                analysis_key = block.get("analysis_key", block_title.lower().replace(" ", "_"))
                content = ai_analysis_results.get(analysis_key, "No AI analysis available.")
                markdown_parts.append(f'<div class="ai-analysis">\n\n{content}\n\n</div>')

            elif block_type == "security_metrics":
                content = content_blocks.get("security_metrics", "No security metrics available.")
                markdown_parts.append(f'<div class="security-metrics">\n\n{content}\n\n</div>')

            elif block_type == "data_table":
                table_data = content_blocks.get(block.get("data_key", "table_data"), [])
                if table_data and isinstance(table_data, list):
                    markdown_parts.append(self._generate_markdown_table(table_data))
                else:
                    markdown_parts.append("No table data available.")

            elif block_type == "custom_content":
                content_key = block.get("content_key", block_title.lower().replace(" ", "_"))
                content = content_blocks.get(content_key, block.get("default_content", "No content available."))
                markdown_parts.append(content)

            else:
                # Generic content block
                content_key = block_title.lower().replace(" ", "_")
                content = content_blocks.get(content_key, "Content not available.")
                markdown_parts.append(content)

            markdown_parts.append("")  # Add spacing between blocks

        # Add generation metadata
        metadata = report_data.get("generation_metadata", {})
        if metadata:
            markdown_parts.append("---")
            markdown_parts.append("## Generation Metadata")
            for key, value in metadata.items():
                markdown_parts.append(f"- **{key.replace('_', ' ').title()}:** {value}")

        return "\n".join(markdown_parts)

    def _generate_markdown_table(self, table_data: List[Dict[str, Any]]) -> str:
        """Generate markdown table from list of dictionaries"""
        if not table_data:
            return "No data available."

        # Get headers from first row
        headers = list(table_data[0].keys())

        # Create markdown table
        table_lines = []

        # Header row
        table_lines.append("| " + " | ".join(headers) + " |")

        # Separator row
        table_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Data rows
        for row in table_data:
            values = [str(row.get(header, "")) for header in headers]
            table_lines.append("| " + " | ".join(values) + " |")

        return "\n".join(table_lines)

    def _sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content using bleach for security"""
        try:
            # Clean HTML with allowed tags and attributes
            safe_html = bleach.clean(
                html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True, strip_comments=True
            )

            # Additional security: remove any remaining script-like content
            safe_html = bleach.clean(safe_html, tags=ALLOWED_TAGS, strip=True)

            return safe_html

        except Exception as e:
            self.logger.error(f"HTML sanitization failed: {e}")
            raise ValueError(f"Failed to sanitize HTML: {str(e)}")

    def _wrap_html_document(self, body_html: str, report_data: Dict[str, Any]) -> str:
        """Wrap sanitized HTML in complete document structure"""
        report_name = report_data.get("report_name", "COB Report")

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_name}</title>
    <style>
        {DEFAULT_PDF_CSS}
    </style>
</head>
<body>
    {body_html}
</body>
</html>
"""

    def _generate_pdf_bytes(self, html_content: str) -> bytes:
        """Generate PDF bytes from HTML using WeasyPrint"""
        try:
            # Create HTML object
            html_doc = HTML(string=html_content)

            # Generate PDF with secure settings
            pdf_bytes = html_doc.write_pdf(optimize_images=True, compress=True, pdf_version="1.7")  # Secure PDF version

            return pdf_bytes

        except Exception as e:
            self.logger.error(f"WeasyPrint PDF generation failed: {e}")
            raise RuntimeError(f"PDF generation failed: {str(e)}")


# Export service instance for use in endpoints
cob_pdf_generator = COBPDFGenerator()
