# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for AuditService (Issue #280).

This module provides comprehensive unit tests for the AuditService class,
covering audit logging, compliance tracking, and change history management.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import (
    AssetAuditLog,
    AssetType,
    ChangeType,
    CriticalityLevel,
    DatabaseAsset,
    Environment,
    SecurityClassification,
)
from app.services.asset_management.audit_service import AuditService


class TestAuditService:
    """Test cases for AuditService class."""
    
    @pytest.mark.asyncio
    async def test_log_asset_change_create(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test logging asset creation changes."""
        # Act
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.CREATE,
            changed_by="test_user",
            change_source="API",
            change_reason="Initial asset creation",
            session_id="session_123",
            request_id="req_456"
        )
        
        # Assert
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == sample_database_asset.id)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log.asset_id == sample_database_asset.id
        assert log.change_type == ChangeType.CREATE
        assert log.changed_by == "test_user"
        assert log.change_source == "API"
        assert log.change_reason == "Initial asset creation"
        assert log.session_id == "session_123"
        assert log.request_id == "req_456"
        assert log.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_log_asset_change_update_with_field_changes(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test logging asset update changes with field-specific tracking."""
        # Act
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="name",
            old_value="Old Asset Name",
            new_value="New Asset Name",
            changed_by="update_user",
            change_source="API",
            change_reason="Asset name standardization"
        )
        
        # Assert
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == sample_database_asset.id)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log.change_type == ChangeType.UPDATE
        assert log.field_changed == "name"
        assert log.old_value == "Old Asset Name"
        assert log.new_value == "New Asset Name"
        assert log.changed_by == "update_user"
        assert log.change_reason == "Asset name standardization"
    
    @pytest.mark.asyncio
    async def test_log_asset_change_delete(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test logging asset deletion changes."""
        # Act
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.DELETE,
            changed_by="admin_user",
            change_source="MANUAL",
            change_reason="Asset decommissioned",
            compliance_relevant=True,
            gdpr_relevant=True,
            soc2_relevant=True
        )
        
        # Assert
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == sample_database_asset.id)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log.change_type == ChangeType.DELETE
        assert log.changed_by == "admin_user"
        assert log.change_source == "MANUAL"
        assert log.compliance_relevant is True
        assert log.gdpr_relevant is True
        assert log.soc2_relevant is True
    
    @pytest.mark.asyncio
    async def test_log_asset_change_validate(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test logging asset validation changes."""
        # Act
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.VALIDATE,
            field_changed="validation_status",
            old_value="PENDING",
            new_value="VALIDATED",
            changed_by="validation_system",
            change_source="DISCOVERY",
            change_reason="Automated validation completed successfully"
        )
        
        # Assert
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == sample_database_asset.id)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log.change_type == ChangeType.VALIDATE
        assert log.field_changed == "validation_status"
        assert log.old_value == "PENDING"
        assert log.new_value == "VALIDATED"
        assert log.changed_by == "validation_system"
        assert log.change_source == "DISCOVERY"
    
    @pytest.mark.asyncio
    async def test_get_asset_audit_history(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test retrieving complete audit history for an asset."""
        # Arrange - Create multiple audit log entries
        audit_entries = [
            {
                "change_type": ChangeType.CREATE,
                "changed_by": "creator_user",
                "change_source": "API",
                "change_reason": "Initial creation"
            },
            {
                "change_type": ChangeType.UPDATE,
                "field_changed": "name",
                "old_value": "Old Name",
                "new_value": "New Name",
                "changed_by": "editor_user",
                "change_source": "API",
                "change_reason": "Name update"
            },
            {
                "change_type": ChangeType.UPDATE,
                "field_changed": "criticality_level",
                "old_value": "MEDIUM",
                "new_value": "HIGH",
                "changed_by": "security_user",
                "change_source": "MANUAL",
                "change_reason": "Security review",
                "compliance_relevant": True
            },
            {
                "change_type": ChangeType.VALIDATE,
                "changed_by": "validation_system",
                "change_source": "DISCOVERY",
                "change_reason": "Automated validation"
            }
        ]
        
        for entry in audit_entries:
            await audit_service.log_asset_change(
                asset_id=sample_database_asset.id,
                **entry
            )
        
        # Act
        audit_history = await audit_service.get_asset_audit_history(sample_database_asset.id)
        
        # Assert
        assert len(audit_history) == 4
        
        # Verify logs are ordered by timestamp (most recent first)
        timestamps = [log.timestamp for log in audit_history]
        assert timestamps == sorted(timestamps, reverse=True)
        
        # Verify specific log entries
        create_log = next(log for log in audit_history if log.change_type == ChangeType.CREATE)
        assert create_log.changed_by == "creator_user"
        
        name_update_log = next(log for log in audit_history if log.field_changed == "name")
        assert name_update_log.old_value == "Old Name"
        assert name_update_log.new_value == "New Name"
        
        security_log = next(log for log in audit_history if log.field_changed == "criticality_level")
        assert security_log.compliance_relevant is True
    
    @pytest.mark.asyncio
    async def test_get_asset_audit_history_with_pagination(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test retrieving audit history with pagination."""
        # Arrange - Create 10 audit log entries
        for i in range(10):
            await audit_service.log_asset_change(
                asset_id=sample_database_asset.id,
                change_type=ChangeType.UPDATE,
                field_changed=f"field_{i}",
                old_value=f"old_value_{i}",
                new_value=f"new_value_{i}",
                changed_by=f"user_{i}",
                change_source="API",
                change_reason=f"Update {i}"
            )
        
        # Act - Get first page
        first_page = await audit_service.get_asset_audit_history(
            sample_database_asset.id, 
            limit=5, 
            offset=0
        )
        
        # Act - Get second page
        second_page = await audit_service.get_asset_audit_history(
            sample_database_asset.id, 
            limit=5, 
            offset=5
        )
        
        # Assert
        assert len(first_page) == 5
        assert len(second_page) == 5
        
        # Ensure no overlap between pages
        first_page_ids = {log.id for log in first_page}
        second_page_ids = {log.id for log in second_page}
        assert len(first_page_ids & second_page_ids) == 0
        
        # Ensure proper ordering (most recent first)
        assert first_page[0].timestamp >= first_page[-1].timestamp
        assert second_page[0].timestamp >= second_page[-1].timestamp
        assert first_page[-1].timestamp >= second_page[0].timestamp
    
    @pytest.mark.asyncio
    async def test_get_compliance_audit_logs(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test retrieving compliance-relevant audit logs."""
        # Arrange - Create mix of compliance and non-compliance logs
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="security_classification",
            old_value="INTERNAL",
            new_value="RESTRICTED",
            changed_by="compliance_officer",
            change_source="MANUAL",
            change_reason="Data sensitivity review",
            compliance_relevant=True,
            gdpr_relevant=True,
            soc2_relevant=True
        )
        
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="description",
            old_value="Old description",
            new_value="New description",
            changed_by="regular_user",
            change_source="API",
            change_reason="Description update",
            compliance_relevant=False
        )
        
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.DELETE,
            changed_by="admin_user",
            change_source="MANUAL",
            change_reason="Asset decommissioned",
            compliance_relevant=True,
            soc2_relevant=True
        )
        
        # Act
        compliance_logs = await audit_service.get_compliance_audit_logs(sample_database_asset.id)
        
        # Assert
        assert len(compliance_logs) == 2  # Only compliance-relevant logs
        
        for log in compliance_logs:
            assert log.compliance_relevant is True
        
        # Verify specific compliance logs
        security_log = next(log for log in compliance_logs if log.field_changed == "security_classification")
        assert security_log.gdpr_relevant is True
        assert security_log.soc2_relevant is True
        
        delete_log = next(log for log in compliance_logs if log.change_type == ChangeType.DELETE)
        assert delete_log.soc2_relevant is True
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_user(
        self, 
        async_session: AsyncSession, 
        audit_service: AuditService
    ):
        """Test retrieving audit logs by specific user."""
        # Arrange - Create multiple assets and audit logs
        assets = []
        for i in range(3):
            asset = DatabaseAsset(
                name=f"Asset {i}",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier=f"asset-{i}",
                location=f"server{i}:5432",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset)
            assets.append(asset)
        
        await async_session.commit()
        for asset in assets:
            await async_session.refresh(asset)
        
        # Create audit logs for different users
        target_user = "target_user"
        other_user = "other_user"
        
        # Target user logs
        for i, asset in enumerate(assets):
            await audit_service.log_asset_change(
                asset_id=asset.id,
                change_type=ChangeType.UPDATE,
                field_changed=f"field_{i}",
                old_value=f"old_{i}",
                new_value=f"new_{i}",
                changed_by=target_user,
                change_source="API",
                change_reason=f"Update by target user {i}"
            )
        
        # Other user logs
        await audit_service.log_asset_change(
            asset_id=assets[0].id,
            change_type=ChangeType.UPDATE,
            field_changed="other_field",
            old_value="other_old",
            new_value="other_new",
            changed_by=other_user,
            change_source="API",
            change_reason="Update by other user"
        )
        
        # Act
        target_user_logs = await audit_service.get_audit_logs_by_user(target_user)
        
        # Assert
        assert len(target_user_logs) == 3  # Only target user's logs
        
        for log in target_user_logs:
            assert log.changed_by == target_user
        
        # Verify logs span multiple assets
        asset_ids = {log.asset_id for log in target_user_logs}
        assert len(asset_ids) == 3  # Logs for all 3 assets
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_date_range(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test retrieving audit logs within a specific date range."""
        # Arrange - Create audit logs with different timestamps
        base_time = datetime.now(timezone.utc)
        
        # Log from 3 days ago (outside range)
        old_time = base_time - timedelta(days=3)
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.CREATE,
            changed_by="old_user",
            change_source="API",
            change_reason="Old log",
            timestamp=old_time
        )
        
        # Log from 1 day ago (inside range)
        recent_time = base_time - timedelta(days=1)
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="recent_field",
            old_value="recent_old",
            new_value="recent_new",
            changed_by="recent_user",
            change_source="API",
            change_reason="Recent log",
            timestamp=recent_time
        )
        
        # Log from now (inside range)
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.VALIDATE,
            changed_by="current_user",
            change_source="API",
            change_reason="Current log"
        )
        
        # Act - Get logs from last 2 days
        start_date = base_time - timedelta(days=2)
        end_date = base_time + timedelta(hours=1)  # Slight buffer for current log
        
        date_range_logs = await audit_service.get_audit_logs_by_date_range(
            start_date=start_date,
            end_date=end_date
        )
        
        # Assert
        assert len(date_range_logs) == 2  # Only recent and current logs
        
        for log in date_range_logs:
            assert start_date <= log.timestamp <= end_date
        
        # Verify specific logs
        recent_log = next(log for log in date_range_logs if log.changed_by == "recent_user")
        assert recent_log.field_changed == "recent_field"
        
        current_log = next(log for log in date_range_logs if log.changed_by == "current_user")
        assert current_log.change_type == ChangeType.VALIDATE
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_change_type(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test retrieving audit logs by specific change type."""
        # Arrange - Create logs with different change types
        change_types_data = [
            (ChangeType.CREATE, "creator", "Initial creation"),
            (ChangeType.UPDATE, "updater", "Name update"),
            (ChangeType.UPDATE, "updater2", "Classification update"),
            (ChangeType.DELETE, "deleter", "Asset removal"),
            (ChangeType.VALIDATE, "validator", "Validation check")
        ]
        
        for change_type, user, reason in change_types_data:
            await audit_service.log_asset_change(
                asset_id=sample_database_asset.id,
                change_type=change_type,
                changed_by=user,
                change_source="API",
                change_reason=reason
            )
        
        # Act - Get only UPDATE logs
        update_logs = await audit_service.get_audit_logs_by_change_type(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.UPDATE
        )
        
        # Assert
        assert len(update_logs) == 2  # Two UPDATE logs
        
        for log in update_logs:
            assert log.change_type == ChangeType.UPDATE
        
        update_users = {log.changed_by for log in update_logs}
        assert update_users == {"updater", "updater2"}
    
    @pytest.mark.asyncio
    async def test_log_bulk_change(
        self, 
        async_session: AsyncSession, 
        audit_service: AuditService
    ):
        """Test logging bulk changes across multiple assets."""
        # Arrange - Create multiple assets
        assets = []
        for i in range(3):
            asset = DatabaseAsset(
                name=f"Bulk Asset {i}",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier=f"bulk-{i}",
                location=f"server{i}:5432",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset)
            assets.append(asset)
        
        await async_session.commit()
        for asset in assets:
            await async_session.refresh(asset)
        
        # Act - Log bulk change
        bulk_session_id = "bulk_session_123"
        bulk_request_id = "bulk_req_456"
        
        for asset in assets:
            await audit_service.log_asset_change(
                asset_id=asset.id,
                change_type=ChangeType.UPDATE,
                field_changed="security_classification",
                old_value="INTERNAL",
                new_value="CONFIDENTIAL",
                changed_by="bulk_updater",
                change_source="API",
                change_reason="Bulk security classification update",
                session_id=bulk_session_id,
                request_id=bulk_request_id,
                compliance_relevant=True
            )
        
        # Assert
        for asset in assets:
            result = await async_session.execute(
                select(AssetAuditLog).where(AssetAuditLog.asset_id == asset.id)
            )
            audit_logs = result.scalars().all()
            
            assert len(audit_logs) == 1
            log = audit_logs[0]
            assert log.session_id == bulk_session_id
            assert log.request_id == bulk_request_id
            assert log.field_changed == "security_classification"
            assert log.compliance_relevant is True
    
    @pytest.mark.asyncio
    async def test_audit_log_effective_date(
        self, 
        async_session: AsyncSession, 
        sample_database_asset: DatabaseAsset,
        audit_service: AuditService
    ):
        """Test audit logging with effective date for scheduled changes."""
        # Arrange
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Act
        await audit_service.log_asset_change(
            asset_id=sample_database_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="environment",
            old_value="DEVELOPMENT",
            new_value="PRODUCTION",
            changed_by="deployment_system",
            change_source="MANUAL",
            change_reason="Scheduled production deployment",
            effective_date=future_date,
            compliance_relevant=True
        )
        
        # Assert
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == sample_database_asset.id)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log.effective_date == future_date
        assert log.field_changed == "environment"
        assert log.change_reason == "Scheduled production deployment"