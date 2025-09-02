# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

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


def upgrade() -> None:
    """Upgrade."""
    # Create orchestrator_configurations table

    op.create_table(  # pylint: disable=no-member
        "orchestrator_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("orchestrator_type", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("parameters", postgresql.JSON, nullable=False),
        sa.Column("tags", postgresql.JSON),
        sa.Column("status", sa.String(50), default="configured"),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),  # pylint: disable=not-callable
        sa.Column(  # pylint: disable=not-callable
            "updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()
        ),
        sa.Column("pyrit_identifier", postgresql.JSON),
        sa.Column("instance_active", sa.Boolean, default=False),
    )

    # Create orchestrator_executions table
    op.create_table(  # pylint: disable=no-member
        "orchestrator_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("orchestrator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_name", sa.String(255)),
        sa.Column("execution_type", sa.String(50)),
        sa.Column("input_data", postgresql.JSON),
        sa.Column("status", sa.String(50), default="running"),
        sa.Column("results", postgresql.JSON),
        sa.Column("execution_summary", postgresql.JSON),
        sa.Column("started_at", sa.DateTime, default=sa.func.now()),  # pylint: disable=not-callable
        sa.Column("completed_at", sa.DateTime),
        sa.Column("created_by", sa.String(255)),
        sa.Column("pyrit_memory_session", sa.String(255)),
        sa.Column("conversation_ids", postgresql.JSON),
    )

    # Create indexes
    # pylint: disable=no-member
    op.create_index("idx_orchestrator_configs_type", "orchestrator_configurations", ["orchestrator_type"])
    op.create_index("idx_orchestrator_configs_status", "orchestrator_configurations", ["status"])
    op.create_index("idx_orchestrator_executions_orchestrator", "orchestrator_executions", ["orchestrator_id"])
    op.create_index("idx_orchestrator_executions_status", "orchestrator_executions", ["status"])


def downgrade() -> None:
    """Downgrade."""
    # Drop indexes

    op.drop_index("idx_orchestrator_executions_status")  # pylint: disable=no-member
    op.drop_index("idx_orchestrator_executions_orchestrator")  # pylint: disable=no-member
    op.drop_index("idx_orchestrator_configs_status")  # pylint: disable=no-member
    op.drop_index("idx_orchestrator_configs_type")  # pylint: disable=no-member

    # Drop tables
    op.drop_table("orchestrator_executions")  # pylint: disable=no-member
    op.drop_table("orchestrator_configurations")  # pylint: disable=no-member
