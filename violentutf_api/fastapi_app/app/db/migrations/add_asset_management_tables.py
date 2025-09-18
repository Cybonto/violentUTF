# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Add asset management tables for Issue #280

Revision ID: add_asset_management_tables
Revises: add_orchestrator_tables
Create Date: 2025-09-18 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "add_asset_management_tables"
down_revision = "add_orchestrator_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade - Create asset management tables."""
    
    # Create asset type enum
    asset_type_enum = postgresql.ENUM(
        'POSTGRESQL', 'SQLITE', 'DUCKDB', 'FILE_STORAGE', 'CONFIGURATION',
        name='assettype',
        create_type=False
    )
    asset_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create security classification enum
    security_classification_enum = postgresql.ENUM(
        'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED',
        name='securityclassification',
        create_type=False
    )
    security_classification_enum.create(op.get_bind(), checkfirst=True)
    
    # Create criticality level enum
    criticality_level_enum = postgresql.ENUM(
        'LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
        name='criticalitylevel',
        create_type=False
    )
    criticality_level_enum.create(op.get_bind(), checkfirst=True)
    
    # Create environment enum
    environment_enum = postgresql.ENUM(
        'DEVELOPMENT', 'TESTING', 'STAGING', 'PRODUCTION',
        name='environment',
        create_type=False
    )
    environment_enum.create(op.get_bind(), checkfirst=True)
    
    # Create validation status enum
    validation_status_enum = postgresql.ENUM(
        'PENDING', 'VALIDATED', 'FAILED', 'EXPIRED',
        name='validationstatus',
        create_type=False
    )
    validation_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create relationship type enum
    relationship_type_enum = postgresql.ENUM(
        'DEPENDS_ON', 'CONNECTED_TO', 'REPLICATED_FROM', 'BACKED_UP_TO', 'SERVES_DATA_TO',
        name='relationshiptype',
        create_type=False
    )
    relationship_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create relationship strength enum
    relationship_strength_enum = postgresql.ENUM(
        'WEAK', 'MEDIUM', 'STRONG', 'CRITICAL',
        name='relationshipstrength',
        create_type=False
    )
    relationship_strength_enum.create(op.get_bind(), checkfirst=True)
    
    # Create change type enum
    change_type_enum = postgresql.ENUM(
        'CREATE', 'UPDATE', 'DELETE', 'VALIDATE',
        name='changetype',
        create_type=False
    )
    change_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create database_assets table
    op.create_table(
        'database_assets',
        # Primary identification
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('asset_type', asset_type_enum, nullable=False, index=True),
        sa.Column('unique_identifier', sa.String(512), nullable=False, unique=True, index=True),
        
        # Location and access
        sa.Column('location', sa.Text, nullable=False),
        sa.Column('connection_string', sa.Text, nullable=True),
        sa.Column('network_location', sa.String(255), nullable=True),
        sa.Column('file_path', sa.Text, nullable=True),
        
        # Classification and security
        sa.Column('security_classification', security_classification_enum, nullable=False, index=True),
        sa.Column('criticality_level', criticality_level_enum, nullable=False, index=True),
        sa.Column('environment', environment_enum, nullable=False, index=True),
        sa.Column('encryption_enabled', sa.Boolean, default=False),
        sa.Column('access_restricted', sa.Boolean, default=True),
        
        # Technical metadata
        sa.Column('database_version', sa.String(100), nullable=True),
        sa.Column('schema_version', sa.String(100), nullable=True),
        sa.Column('estimated_size_mb', sa.Integer, nullable=True),
        sa.Column('table_count', sa.Integer, nullable=True),
        sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True),
        
        # Operational metadata
        sa.Column('owner_team', sa.String(100), nullable=True),
        sa.Column('technical_contact', sa.String(255), nullable=True),
        sa.Column('business_contact', sa.String(255), nullable=True),
        sa.Column('purpose_description', sa.Text, nullable=True),
        
        # Discovery and validation
        sa.Column('discovery_method', sa.String(100), nullable=False),
        sa.Column('discovery_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confidence_score', sa.Integer, nullable=False),
        sa.Column('last_validated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validation_status', validation_status_enum, nullable=False, default='PENDING'),
        
        # Compliance and governance
        sa.Column('backup_configured', sa.Boolean, default=False),
        sa.Column('backup_last_verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('compliance_requirements', sa.JSON, nullable=True),
        sa.Column('documentation_url', sa.String(512), nullable=True),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('updated_by', sa.String(100), nullable=False),
        
        # Soft delete
        sa.Column('is_deleted', sa.Boolean, default=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
    )
    
    # Create asset_relationships table
    op.create_table(
        'asset_relationships',
        # Primary identification
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('source_asset_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('target_asset_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Relationship details
        sa.Column('relationship_type', relationship_type_enum, nullable=False, index=True),
        sa.Column('relationship_strength', relationship_strength_enum, nullable=False),
        sa.Column('bidirectional', sa.Boolean, default=False),
        
        # Metadata
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('discovered_method', sa.String(100), nullable=False),
        sa.Column('confidence_score', sa.Integer, nullable=False),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False, default='system'),
        sa.Column('updated_by', sa.String(100), nullable=False, default='system'),
        
        # Soft delete
        sa.Column('is_deleted', sa.Boolean, default=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
    )
    
    # Create asset_audit_log table
    op.create_table(
        'asset_audit_log',
        # Primary identification
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Change details
        sa.Column('change_type', change_type_enum, nullable=False, index=True),
        sa.Column('field_changed', sa.String(100), nullable=True),
        sa.Column('old_value', sa.Text, nullable=True),
        sa.Column('new_value', sa.Text, nullable=True),
        sa.Column('change_reason', sa.String(255), nullable=True),
        
        # Attribution and context
        sa.Column('changed_by', sa.String(100), nullable=False, index=True),
        sa.Column('change_source', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        
        # Compliance metadata
        sa.Column('compliance_relevant', sa.Boolean, default=False, index=True),
        sa.Column('gdpr_relevant', sa.Boolean, default=False, index=True),
        sa.Column('soc2_relevant', sa.Boolean, default=False, index=True),
        
        # Timing
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_asset_relationships_source',
        'asset_relationships',
        'database_assets',
        ['source_asset_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_asset_relationships_target',
        'asset_relationships',
        'database_assets',
        ['target_asset_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_asset_audit_log_asset',
        'asset_audit_log',
        'database_assets',
        ['asset_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create additional indexes for performance
    op.create_index('idx_database_assets_created_at', 'database_assets', ['created_at'])
    op.create_index('idx_database_assets_updated_at', 'database_assets', ['updated_at'])
    op.create_index('idx_database_assets_discovery_timestamp', 'database_assets', ['discovery_timestamp'])
    op.create_index('idx_database_assets_confidence_score', 'database_assets', ['confidence_score'])
    
    op.create_index('idx_asset_relationships_source_target', 'asset_relationships', ['source_asset_id', 'target_asset_id'])
    op.create_index('idx_asset_relationships_created_at', 'asset_relationships', ['created_at'])
    
    op.create_index('idx_asset_audit_log_timestamp', 'asset_audit_log', ['timestamp'])
    op.create_index('idx_asset_audit_log_asset_timestamp', 'asset_audit_log', ['asset_id', 'timestamp'])
    op.create_index('idx_asset_audit_log_changed_by', 'asset_audit_log', ['changed_by'])


def downgrade() -> None:
    """Downgrade - Remove asset management tables."""
    
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('asset_audit_log')
    op.drop_table('asset_relationships')
    op.drop_table('database_assets')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS changetype')
    op.execute('DROP TYPE IF EXISTS relationshipstrength')
    op.execute('DROP TYPE IF EXISTS relationshiptype')
    op.execute('DROP TYPE IF EXISTS validationstatus')
    op.execute('DROP TYPE IF EXISTS environment')
    op.execute('DROP TYPE IF EXISTS criticalitylevel')
    op.execute('DROP TYPE IF EXISTS securityclassification')
    op.execute('DROP TYPE IF EXISTS assettype')