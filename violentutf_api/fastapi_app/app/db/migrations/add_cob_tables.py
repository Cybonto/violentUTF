"""Add COB report tables

Revision ID: add_cob_tables
Revises: add_orchestrator_tables
Create Date: 2024-07-17 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "add_cob_tables"
down_revision = "add_orchestrator_tables"
branch_labels = None
depends_on = None


def upgrade():
    # Create cob_templates table
    op.create_table(
        "cob_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("template_config", postgresql.JSON, nullable=False),
        sa.Column("ai_prompts", postgresql.JSON),
        sa.Column("export_formats", postgresql.JSON, default=["markdown", "pdf", "json"]),
        sa.Column("tags", postgresql.JSON),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create cob_schedules table
    op.create_table(
        "cob_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("schedule_time", sa.String(8), nullable=False),
        sa.Column("timezone", sa.String(50), default="UTC"),
        sa.Column("days_of_week", postgresql.JSON),
        sa.Column("day_of_month", sa.String(2)),
        sa.Column("ai_model_config", postgresql.JSON),
        sa.Column("export_config", postgresql.JSON),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create cob_reports table
    op.create_table(
        "cob_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True)),
        sa.Column("report_name", sa.String(255), nullable=False),
        sa.Column("report_period_start", sa.DateTime(timezone=True)),
        sa.Column("report_period_end", sa.DateTime(timezone=True)),
        sa.Column("generation_status", sa.String(50), default="generating"),
        sa.Column("content_blocks", postgresql.JSON),
        sa.Column("ai_analysis_results", postgresql.JSON),
        sa.Column("export_results", postgresql.JSON),
        sa.Column("generation_metadata", postgresql.JSON),
        sa.Column("generated_by", sa.String(255)),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # Create cob_schedule_executions table
    op.create_table(
        "cob_schedule_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True)),
        sa.Column("execution_status", sa.String(50), default="started"),
        sa.Column("execution_log", postgresql.JSON),
        sa.Column("error_details", postgresql.JSON),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("execution_duration_seconds", sa.String(10)),
    )

    # Create indexes for performance
    op.create_index("idx_cob_templates_name", "cob_templates", ["name"])
    op.create_index("idx_cob_templates_active", "cob_templates", ["is_active"])
    op.create_index("idx_cob_schedules_template", "cob_schedules", ["template_id"])
    op.create_index("idx_cob_schedules_active", "cob_schedules", ["is_active"])
    op.create_index("idx_cob_schedules_next_run", "cob_schedules", ["next_run_at"])
    op.create_index("idx_cob_reports_template", "cob_reports", ["template_id"])
    op.create_index("idx_cob_reports_schedule", "cob_reports", ["schedule_id"])
    op.create_index("idx_cob_reports_status", "cob_reports", ["generation_status"])
    op.create_index("idx_cob_reports_generated_at", "cob_reports", ["generated_at"])
    op.create_index("idx_cob_executions_schedule", "cob_schedule_executions", ["schedule_id"])
    op.create_index("idx_cob_executions_status", "cob_schedule_executions", ["execution_status"])


def downgrade():
    # Drop indexes
    op.drop_index("idx_cob_executions_status")
    op.drop_index("idx_cob_executions_schedule")
    op.drop_index("idx_cob_reports_generated_at")
    op.drop_index("idx_cob_reports_status")
    op.drop_index("idx_cob_reports_schedule")
    op.drop_index("idx_cob_reports_template")
    op.drop_index("idx_cob_schedules_next_run")
    op.drop_index("idx_cob_schedules_active")
    op.drop_index("idx_cob_schedules_template")
    op.drop_index("idx_cob_templates_active")
    op.drop_index("idx_cob_templates_name")

    # Drop tables
    op.drop_table("cob_schedule_executions")
    op.drop_table("cob_reports")
    op.drop_table("cob_schedules")
    op.drop_table("cob_templates")
