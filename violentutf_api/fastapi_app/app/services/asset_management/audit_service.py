# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Audit Service for Issue #280 Asset Management System.

This module provides comprehensive audit logging for all asset changes,
supporting compliance requirements and change tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import AssetAuditLog, ChangeType
from app.schemas.asset_schemas import AuditLogResponse


class AuditService:
    """Service class for asset audit trail management."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the audit service.

        Args:
            db: Database session
        """
        self.db = db

    async def log_asset_change(
        self,
        asset_id: uuid.UUID,
        change_type: ChangeType,
        changed_by: str,
        change_source: str,
        field_changed: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        change_reason: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        compliance_relevant: bool = False,
        gdpr_relevant: bool = False,
        soc2_relevant: bool = False,
    ) -> None:
        """Log an asset change to the audit trail.

        Args:
            asset_id: ID of the asset that changed
            change_type: Type of change (CREATE, UPDATE, DELETE, VALIDATE)
            changed_by: User who made the change
            change_source: Source of the change (API, DISCOVERY, MANUAL)
            field_changed: Specific field that changed (for updates)
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            change_reason: Reason for the change
            session_id: Session ID for tracking
            request_id: Request ID for tracking
            compliance_relevant: Whether change is compliance relevant
            gdpr_relevant: Whether change is GDPR relevant
            soc2_relevant: Whether change is SOC2 relevant
        """
        audit_log = AssetAuditLog(
            asset_id=asset_id,
            change_type=change_type,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            change_reason=change_reason,
            changed_by=changed_by,
            change_source=change_source,
            session_id=session_id,
            request_id=request_id,
            compliance_relevant=compliance_relevant,
            gdpr_relevant=gdpr_relevant,
            soc2_relevant=soc2_relevant,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(audit_log)
        await self.db.commit()

    async def get_asset_audit_trail(
        self, asset_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> List[AuditLogResponse]:
        """Get audit trail for a specific asset.

        Args:
            asset_id: Asset ID
            limit: Maximum number of records
            offset: Records offset

        Returns:
            List of audit log responses
        """
        query = (
            select(AssetAuditLog)
            .where(AssetAuditLog.asset_id == asset_id)
            .order_by(AssetAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        audit_logs = result.scalars().all()

        return [AuditLogResponse.model_validate(log) for log in audit_logs]

    async def get_compliance_audit_logs(
        self,
        gdpr_relevant: Optional[bool] = None,
        soc2_relevant: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[AuditLogResponse]:
        """Get compliance-relevant audit logs.

        Args:
            gdpr_relevant: Filter by GDPR relevance
            soc2_relevant: Filter by SOC2 relevance
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of records
            offset: Records offset

        Returns:
            List of compliance audit log responses
        """
        conditions = [AssetAuditLog.compliance_relevant.is_(True)]

        if gdpr_relevant is not None:
            conditions.append(AssetAuditLog.gdpr_relevant == gdpr_relevant)

        if soc2_relevant is not None:
            conditions.append(AssetAuditLog.soc2_relevant == soc2_relevant)

        if start_date:
            conditions.append(AssetAuditLog.timestamp >= start_date)

        if end_date:
            conditions.append(AssetAuditLog.timestamp <= end_date)

        query = (
            select(AssetAuditLog)
            .where(and_(*conditions))
            .order_by(AssetAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        audit_logs = result.scalars().all()

        return [AuditLogResponse.model_validate(log) for log in audit_logs]

    async def get_user_activity(
        self,
        changed_by: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogResponse]:
        """Get audit logs for a specific user.

        Args:
            changed_by: User to get activity for
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of records
            offset: Records offset

        Returns:
            List of user audit log responses
        """
        conditions = [AssetAuditLog.changed_by == changed_by]

        if start_date:
            conditions.append(AssetAuditLog.timestamp >= start_date)

        if end_date:
            conditions.append(AssetAuditLog.timestamp <= end_date)

        query = (
            select(AssetAuditLog)
            .where(and_(*conditions))
            .order_by(AssetAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        audit_logs = result.scalars().all()

        return [AuditLogResponse.model_validate(log) for log in audit_logs]

    async def get_recent_changes(self, hours: int = 24, limit: int = 100) -> List[AuditLogResponse]:
        """Get recent asset changes within specified hours.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of records

        Returns:
            List of recent audit log responses
        """
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            select(AssetAuditLog)
            .where(AssetAuditLog.timestamp >= cutoff_time)
            .order_by(AssetAuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        audit_logs = result.scalars().all()

        return [AuditLogResponse.model_validate(log) for log in audit_logs]

    async def count_changes_by_type(
        self,
        asset_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Count changes by type for analytics.

        Args:
            asset_id: Optional asset ID to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with change type counts
        """
        from sqlalchemy import func

        conditions = []

        if asset_id:
            conditions.append(AssetAuditLog.asset_id == asset_id)

        if start_date:
            conditions.append(AssetAuditLog.timestamp >= start_date)

        if end_date:
            conditions.append(AssetAuditLog.timestamp <= end_date)

        query = select(AssetAuditLog.change_type, func.count(AssetAuditLog.id).label("count")).group_by(
            AssetAuditLog.change_type
        )

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        rows = result.fetchall()

        return {str(row.change_type): row.count for row in rows}

    async def search_audit_logs(self, search_term: str, limit: int = 100, offset: int = 0) -> List[AuditLogResponse]:
        """Search audit logs by various fields.

        Args:
            search_term: Term to search for
            limit: Maximum number of records
            offset: Records offset

        Returns:
            List of matching audit log responses
        """
        from sqlalchemy import or_

        search_pattern = f"%{search_term}%"

        query = (
            select(AssetAuditLog)
            .where(
                or_(
                    AssetAuditLog.field_changed.ilike(search_pattern),
                    AssetAuditLog.old_value.ilike(search_pattern),
                    AssetAuditLog.new_value.ilike(search_pattern),
                    AssetAuditLog.change_reason.ilike(search_pattern),
                    AssetAuditLog.changed_by.ilike(search_pattern),
                )
            )
            .order_by(AssetAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        audit_logs = result.scalars().all()

        return [AuditLogResponse.model_validate(log) for log in audit_logs]

    async def delete_old_audit_logs(self, days_to_keep: int = 2555) -> int:  # 7 years default retention
        """Delete audit logs older than specified days.

        Args:
            days_to_keep: Number of days to retain logs

        Returns:
            Number of deleted logs
        """
        from datetime import timedelta

        from sqlalchemy import delete

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Only delete non-compliance relevant logs for general cleanup
        # Compliance logs should have separate retention policies
        delete_query = delete(AssetAuditLog).where(
            and_(
                AssetAuditLog.timestamp < cutoff_date,
                AssetAuditLog.compliance_relevant.is_(False),
                AssetAuditLog.gdpr_relevant.is_(False),
                AssetAuditLog.soc2_relevant.is_(False),
            )
        )

        result = await self.db.execute(delete_query)
        await self.db.commit()

        return result.rowcount
