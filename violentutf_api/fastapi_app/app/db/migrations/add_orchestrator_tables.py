"""Add orchestrator tables

Revision ID: add_orchestrator_tables
Revises: previous_migration
Create Date: 2024-01-01 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "add_orchestrator_tables"
down_revision = "previous_migration"  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Create orchestrator_configurations table
    op.create_table(
        "orchestrator_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("orchestrator_type", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("parameters", postgresql.JSON, nullable=False),
        sa.Column("tags", postgresql.JSON),
        sa.Column("status", sa.String(50), default="configured"),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()
        ),
        sa.Column("pyrit_identifier", postgresql.JSON),
        sa.Column("instance_active", sa.Boolean, default=False),
    )

    # Create orchestrator_executions table
    op.create_table(
        "orchestrator_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("orchestrator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_name", sa.String(255)),
        sa.Column("execution_type", sa.String(50)),
        sa.Column("input_data", postgresql.JSON),
        sa.Column("status", sa.String(50), default="running"),
        sa.Column("results", postgresql.JSON),
        sa.Column("execution_summary", postgresql.JSON),
        sa.Column("started_at", sa.DateTime, default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("created_by", sa.String(255)),
        sa.Column("pyrit_memory_session", sa.String(255)),
        sa.Column("conversation_ids", postgresql.JSON),
    )

    # Create indexes
    op.create_index(
        "idx_orchestrator_configs_type",
        "orchestrator_configurations",
        ["orchestrator_type"],
    )
    op.create_index(
        "idx_orchestrator_configs_status", "orchestrator_configurations", ["status"]
    )
    op.create_index(
        "idx_orchestrator_executions_orchestrator",
        "orchestrator_executions",
        ["orchestrator_id"],
    )
    op.create_index(
        "idx_orchestrator_executions_status", "orchestrator_executions", ["status"]
    )


def downgrade():
    # Drop indexes
    op.drop_index("idx_orchestrator_executions_status")
    op.drop_index("idx_orchestrator_executions_orchestrator")
    op.drop_index("idx_orchestrator_configs_status")
    op.drop_index("idx_orchestrator_configs_type")

    # Drop tables
    op.drop_table("orchestrator_executions")
    op.drop_table("orchestrator_configurations")
