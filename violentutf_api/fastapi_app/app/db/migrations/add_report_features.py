"""Add advanced report features

Revision ID: 003
Revises: 002
Create Date: 2024-01-19

"""
import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    """Add advanced report features to database"""

    # Add metadata and version columns to cob_templates
    op.add_column("cob_templates", sa.Column("metadata", sa.JSON(), nullable=True, server_default="{}"))
    op.add_column("cob_templates", sa.Column("version", sa.String(20), nullable=True, server_default="1.0.0"))
    op.add_column("cob_templates", sa.Column("version_notes", sa.Text(), nullable=True))

    # Create template versions table
    op.create_table(
        "cob_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("change_notes", sa.Text()),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["template_id"], ["cob_templates.id"]),
    )

    # Add data selection and notification config to schedules
    op.add_column("cob_schedules", sa.Column("data_selection", sa.JSON(), nullable=True, server_default="{}"))
    op.add_column("cob_schedules", sa.Column("notification_config", sa.JSON(), nullable=True, server_default="{}"))

    # Create scan data cache table
    op.create_table(
        "cob_scan_data_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("execution_id", sa.String(), unique=True),
        sa.Column("scanner_type", sa.String(50)),
        sa.Column("target_model", sa.String(255)),
        sa.Column("scan_date", sa.DateTime()),
        sa.Column("score_data", sa.JSON()),
        sa.Column("raw_results", sa.JSON()),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime()),
    )

    # Create report variables registry
    op.create_table(
        "cob_report_variables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("category", sa.String(100)),
        sa.Column("variable_name", sa.String(255), unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("data_type", sa.String(50)),
        sa.Column("source", sa.String(50)),
        sa.Column("example_value", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Create block definitions table
    op.create_table(
        "cob_block_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("block_type", sa.String(100), unique=True),
        sa.Column("display_name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(100)),
        sa.Column("configuration_schema", sa.JSON()),
        sa.Column("default_config", sa.JSON()),
        sa.Column("supported_formats", sa.JSON(), server_default='["PDF", "JSON", "Markdown"]'),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index("idx_template_versions_template_id", "cob_template_versions", ["template_id"])
    op.create_index("idx_scan_cache_execution_id", "cob_scan_data_cache", ["execution_id"])
    op.create_index("idx_scan_cache_scanner", "cob_scan_data_cache", ["scanner_type"])
    op.create_index("idx_scan_cache_expires", "cob_scan_data_cache", ["expires_at"])
    op.create_index("idx_variables_category", "cob_report_variables", ["category"])
    op.create_index("idx_blocks_category", "cob_block_definitions", ["category"])

    # Insert default block definitions
    op.bulk_insert(
        sa.table(
            "cob_block_definitions",
            sa.column("id", sa.String),
            sa.column("block_type", sa.String),
            sa.column("display_name", sa.String),
            sa.column("category", sa.String),
            sa.column("description", sa.Text),
            sa.column("configuration_schema", sa.JSON),
            sa.column("default_config", sa.JSON),
        ),
        [
            {
                "id": str(uuid.uuid4()),
                "block_type": "executive_summary",
                "display_name": "Executive Summary",
                "category": "summary",
                "description": "High-level overview with key metrics and findings",
                "configuration_schema": json.dumps(
                    {
                        "type": "object",
                        "properties": {
                            "components": {"type": "array", "items": {"type": "string"}},
                            "highlight_threshold": {"type": "string"},
                        },
                    }
                ),
                "default_config": json.dumps(
                    {
                        "components": ["Overall Risk Score", "Critical Vulnerabilities Count"],
                        "highlight_threshold": "High and Above",
                    }
                ),
            },
            {
                "id": str(uuid.uuid4()),
                "block_type": "ai_analysis",
                "display_name": "AI Analysis",
                "category": "analysis",
                "description": "AI-powered insights and recommendations",
                "configuration_schema": json.dumps(
                    {
                        "type": "object",
                        "properties": {
                            "analysis_focus": {"type": "array"},
                            "ai_model": {"type": "string"},
                            "prompt": {"type": "string"},
                        },
                    }
                ),
                "default_config": json.dumps({"analysis_focus": ["Vulnerability Assessment"], "ai_model": "gpt-4"}),
            },
            {
                "id": str(uuid.uuid4()),
                "block_type": "security_metrics",
                "display_name": "Security Metrics",
                "category": "visualization",
                "description": "Comprehensive security metrics and visualizations",
                "configuration_schema": json.dumps(
                    {
                        "type": "object",
                        "properties": {"visualizations": {"type": "array"}, "metric_source": {"type": "string"}},
                    }
                ),
                "default_config": json.dumps(
                    {"visualizations": ["Metric Cards", "Risk Heatmap"], "metric_source": "Combined"}
                ),
            },
            {
                "id": str(uuid.uuid4()),
                "block_type": "toxicity_heatmap",
                "display_name": "Toxicity Heatmap",
                "category": "visualization",
                "description": "Visual heatmap of toxicity scores across categories",
                "configuration_schema": json.dumps(
                    {
                        "type": "object",
                        "properties": {"categories": {"type": "array"}, "aggregation": {"type": "string"}},
                    }
                ),
                "default_config": json.dumps({"categories": ["hate", "harassment", "violence"], "aggregation": "mean"}),
            },
            {
                "id": str(uuid.uuid4()),
                "block_type": "custom_content",
                "display_name": "Custom Content",
                "category": "content",
                "description": "Flexible Markdown content with variable support",
                "configuration_schema": json.dumps(
                    {
                        "type": "object",
                        "properties": {"content": {"type": "string"}, "content_type": {"type": "string"}},
                    }
                ),
                "default_config": json.dumps({"content": "", "content_type": "General"}),
            },
        ],
    )

    # Insert default report variables
    op.bulk_insert(
        sa.table(
            "cob_report_variables",
            sa.column("id", sa.String),
            sa.column("category", sa.String),
            sa.column("variable_name", sa.String),
            sa.column("description", sa.Text),
            sa.column("data_type", sa.String),
            sa.column("source", sa.String),
            sa.column("example_value", sa.Text),
        ),
        [
            # Scan Results Variables
            {
                "id": str(uuid.uuid4()),  # var_total_tests',
                "category": "scan_results",
                "variable_name": "total_tests",
                "description": "Total number of tests executed",
                "data_type": "number",
                "source": "system",
                "example_value": "1500",
            },
            {
                "id": str(uuid.uuid4()),  # var_successful_attacks',
                "category": "scan_results",
                "variable_name": "successful_attacks",
                "description": "Number of successful attacks",
                "data_type": "number",
                "source": "system",
                "example_value": "45",
            },
            {
                "id": str(uuid.uuid4()),  # var_failure_rate',
                "category": "scan_results",
                "variable_name": "failure_rate",
                "description": "Percentage of failed defenses",
                "data_type": "number",
                "source": "system",
                "example_value": "3.0",
            },
            # Vulnerability Variables
            {
                "id": str(uuid.uuid4()),  # var_total_vulns',
                "category": "vulnerabilities",
                "variable_name": "total_vulnerabilities",
                "description": "Total vulnerabilities found",
                "data_type": "number",
                "source": "system",
                "example_value": "12",
            },
            {
                "id": str(uuid.uuid4()),  # var_critical_count',
                "category": "vulnerabilities",
                "variable_name": "critical_count",
                "description": "Number of critical vulnerabilities",
                "data_type": "number",
                "source": "system",
                "example_value": "2",
            },
            # Model Information
            {
                "id": str(uuid.uuid4()),  # var_target_model',
                "category": "model_info",
                "variable_name": "target_model",
                "description": "Target model name",
                "data_type": "string",
                "source": "system",
                "example_value": "gpt-4-turbo",
            },
            # Metrics
            {
                "id": str(uuid.uuid4()),  # var_risk_score',
                "category": "metrics",
                "variable_name": "risk_score",
                "description": "Overall risk score (0-10)",
                "data_type": "number",
                "source": "system",
                "example_value": "7.5",
            },
            {
                "id": str(uuid.uuid4()),  # var_compliance_score',
                "category": "metrics",
                "variable_name": "compliance_score",
                "description": "Compliance percentage",
                "data_type": "number",
                "source": "system",
                "example_value": "85.0",
            },
        ],
    )


def downgrade():
    """Remove advanced report features"""

    # Drop indexes
    op.drop_index("idx_blocks_category")
    op.drop_index("idx_variables_category")
    op.drop_index("idx_scan_cache_expires")
    op.drop_index("idx_scan_cache_scanner")
    op.drop_index("idx_scan_cache_execution_id")
    op.drop_index("idx_template_versions_template_id")

    # Drop tables
    op.drop_table("cob_block_definitions")
    op.drop_table("cob_report_variables")
    op.drop_table("cob_scan_data_cache")
    op.drop_table("cob_template_versions")

    # Remove columns from existing tables
    op.drop_column("cob_schedules", "notification_config")
    op.drop_column("cob_schedules", "data_selection")
    op.drop_column("cob_templates", "version_notes")
    op.drop_column("cob_templates", "version")
    op.drop_column("cob_templates", "metadata")
