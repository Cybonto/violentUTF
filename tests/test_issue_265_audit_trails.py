# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for Enhanced Configuration Change Tracking and Audit Trails - Issue #265."""

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.services.config_monitoring import (
    AuditEntry,
    AuditTrail,
    ChangeTracker,
    ConfigurationAuditor,
)


class TestAuditEntry:
    """Test AuditEntry class functionality."""

    def test_create_audit_entry(self):
        """Test creating an audit entry."""
        # GIVEN: Audit entry parameters
        entry = AuditEntry(
            entry_id="audit_123",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_456",
            user_id="admin",
            user_ip="192.168.1.100",
            user_agent="Mozilla/5.0",
            change_summary="Modified database password",
            change_details={
                "field": "database.password",
                "old_value_hash": "sha256_old_hash",
                "new_value_hash": "sha256_new_hash",
                "change_type": "modified"
            },
            metadata={
                "session_id": "session_789",
                "request_id": "req_abc123"
            }
        )
        
        # THEN: Entry should be created correctly
        assert entry.entry_id == "audit_123"
        assert entry.event_type == "configuration_changed"
        assert entry.service_name == "keycloak"
        assert entry.user_id == "admin"
        assert entry.change_summary == "Modified database password"
        assert entry.change_details["field"] == "database.password"

    def test_audit_entry_sanitize_sensitive_data(self):
        """Test audit entry sanitizes sensitive data."""
        # GIVEN: Audit entry with sensitive information
        entry = AuditEntry(
            entry_id="audit_123",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_456",
            user_id="admin",
            user_ip="192.168.1.100",
            user_agent="Mozilla/5.0",
            change_summary="Modified database configuration",
            change_details={
                "field": "database.password",
                "old_value": "secret123",  # Should be sanitized
                "new_value": "newsecret456",  # Should be sanitized
                "change_type": "modified"
            }
        )
        
        # WHEN: Serializing entry
        serialized = entry.to_dict()
        
        # THEN: Sensitive data should be sanitized
        assert "old_value" not in serialized["change_details"]
        assert "new_value" not in serialized["change_details"]
        assert "old_value_hash" in serialized["change_details"]
        assert "new_value_hash" in serialized["change_details"]

    def test_audit_entry_severity_classification(self):
        """Test audit entry severity classification."""
        # GIVEN: Different types of changes
        critical_entry = AuditEntry(
            entry_id="audit_1",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_1",
            user_id="admin",
            change_summary="Modified password",
            change_details={"field": "password", "change_type": "modified"}
        )
        
        low_entry = AuditEntry(
            entry_id="audit_2",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_2",
            user_id="admin",
            change_summary="Modified comment",
            change_details={"field": "comment", "change_type": "modified"}
        )
        
        # THEN: Severity should be classified correctly
        assert critical_entry.severity == "critical"
        assert low_entry.severity == "low"

    def test_audit_entry_serialization(self):
        """Test audit entry serialization."""
        # GIVEN: Audit entry
        entry = AuditEntry(
            entry_id="audit_123",
            event_type="baseline_created",
            service_name="fastapi",
            baseline_id="baseline_456",
            user_id="developer",
            change_summary="Created new baseline",
            change_details={"baseline_type": "sqlite"}
        )
        
        # WHEN: Serializing
        serialized = entry.to_dict()
        
        # THEN: All data should be preserved
        assert serialized["entry_id"] == "audit_123"
        assert serialized["event_type"] == "baseline_created"
        assert serialized["service_name"] == "fastapi"
        assert serialized["user_id"] == "developer"
        assert "timestamp" in serialized
        assert serialized["change_details"]["baseline_type"] == "sqlite"


class TestAuditTrail:
    """Test AuditTrail class functionality."""

    def test_create_audit_trail(self):
        """Test creating audit trail."""
        # GIVEN: Audit trail for a service
        trail = AuditTrail(
            service_name="keycloak",
            baseline_id="baseline_123"
        )
        
        # THEN: Trail should be initialized
        assert trail.service_name == "keycloak"
        assert trail.baseline_id == "baseline_123"
        assert len(trail.entries) == 0

    def test_add_audit_entry(self):
        """Test adding audit entry to trail."""
        # GIVEN: Audit trail and entry
        trail = AuditTrail(
            service_name="keycloak",
            baseline_id="baseline_123"
        )
        
        entry = AuditEntry(
            entry_id="audit_1",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="admin",
            change_summary="Modified host",
            change_details={"field": "host", "change_type": "modified"}
        )
        
        # WHEN: Adding entry
        trail.add_entry(entry)
        
        # THEN: Entry should be added
        assert len(trail.entries) == 1
        assert trail.entries[0] == entry

    def test_get_entries_by_user(self):
        """Test filtering entries by user."""
        # GIVEN: Audit trail with multiple entries from different users
        trail = AuditTrail("keycloak", "baseline_123")
        
        admin_entry = AuditEntry(
            entry_id="audit_1",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="admin",
            change_summary="Admin change"
        )
        
        dev_entry = AuditEntry(
            entry_id="audit_2",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="developer",
            change_summary="Developer change"
        )
        
        trail.add_entry(admin_entry)
        trail.add_entry(dev_entry)
        
        # WHEN: Filtering by user
        admin_entries = trail.get_entries_by_user("admin")
        dev_entries = trail.get_entries_by_user("developer")
        
        # THEN: Should return correct entries
        assert len(admin_entries) == 1
        assert admin_entries[0].user_id == "admin"
        assert len(dev_entries) == 1
        assert dev_entries[0].user_id == "developer"

    def test_get_entries_by_severity(self):
        """Test filtering entries by severity."""
        # GIVEN: Audit trail with entries of different severities
        trail = AuditTrail("keycloak", "baseline_123")
        
        critical_entry = AuditEntry(
            entry_id="audit_1",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="admin",
            change_summary="Password change",
            change_details={"field": "password", "change_type": "modified"}
        )
        
        low_entry = AuditEntry(
            entry_id="audit_2",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="admin",
            change_summary="Comment change",
            change_details={"field": "comment", "change_type": "modified"}
        )
        
        trail.add_entry(critical_entry)
        trail.add_entry(low_entry)
        
        # WHEN: Filtering by severity
        critical_entries = trail.get_entries_by_severity("critical")
        low_entries = trail.get_entries_by_severity("low")
        
        # THEN: Should return correct entries
        assert len(critical_entries) == 1
        assert critical_entries[0].severity == "critical"
        assert len(low_entries) == 1
        assert low_entries[0].severity == "low"

    def test_get_entries_by_date_range(self):
        """Test filtering entries by date range."""
        # GIVEN: Audit trail with entries at different times
        trail = AuditTrail("keycloak", "baseline_123")
        
        import time
        
        entry1 = AuditEntry(
            entry_id="audit_1",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="admin",
            change_summary="First change"
        )
        
        # Wait a bit to ensure different timestamps
        time.sleep(0.1)
        
        entry2 = AuditEntry(
            entry_id="audit_2",
            event_type="configuration_changed",
            service_name="keycloak",
            baseline_id="baseline_123",
            user_id="admin",
            change_summary="Second change"
        )
        
        trail.add_entry(entry1)
        trail.add_entry(entry2)
        
        # WHEN: Filtering by date range (last 1 second)
        cutoff_time = datetime.utcnow()
        entries = trail.get_entries_by_date_range(
            start_date=cutoff_time.replace(second=cutoff_time.second-1),
            end_date=cutoff_time
        )
        
        # THEN: Should return recent entries
        assert len(entries) >= 1  # At least the second entry should be included

    def test_generate_audit_summary(self):
        """Test generating audit summary."""
        # GIVEN: Audit trail with multiple entries
        trail = AuditTrail("keycloak", "baseline_123")
        
        entries = [
            AuditEntry("audit_1", "configuration_changed", "keycloak", "baseline_123", 
                      "admin", change_summary="Password change",
                      change_details={"field": "password", "change_type": "modified"}),
            AuditEntry("audit_2", "configuration_changed", "keycloak", "baseline_123",
                      "developer", change_summary="Port change", 
                      change_details={"field": "port", "change_type": "modified"}),
            AuditEntry("audit_3", "baseline_created", "keycloak", "baseline_123",
                      "admin", change_summary="Created baseline")
        ]
        
        for entry in entries:
            trail.add_entry(entry)
        
        # WHEN: Generating summary
        summary = trail.generate_summary()
        
        # THEN: Summary should contain key metrics
        assert summary["total_entries"] == 3
        assert summary["unique_users"] == 2
        assert "admin" in summary["users"]
        assert "developer" in summary["users"]
        assert "configuration_changed" in summary["event_types"]
        assert "baseline_created" in summary["event_types"]


class TestChangeTracker:
    """Test ChangeTracker class functionality."""

    def test_create_change_tracker(self):
        """Test creating change tracker."""
        # GIVEN: Change tracker initialization
        tracker = ChangeTracker()
        
        # THEN: Tracker should be initialized
        assert tracker is not None

    def test_track_configuration_change(self):
        """Test tracking configuration change."""
        # GIVEN: Change tracker and configuration change
        tracker = ChangeTracker()
        
        old_config = {"host": "old-host", "port": 5432}
        new_config = {"host": "new-host", "port": 5433}
        
        # WHEN: Tracking change
        changes = tracker.track_change(
            service_name="keycloak",
            baseline_id="baseline_123",
            old_config=old_config,
            new_config=new_config,
            user_context={
                "user_id": "admin",
                "user_ip": "192.168.1.100",
                "session_id": "session_123"
            }
        )
        
        # THEN: Changes should be tracked
        assert len(changes) == 2  # host and port changes
        assert any(change.change_details["field"] == "host" for change in changes)
        assert any(change.change_details["field"] == "port" for change in changes)

    def test_track_baseline_creation(self):
        """Test tracking baseline creation."""
        # GIVEN: Change tracker
        tracker = ChangeTracker()
        
        # WHEN: Tracking baseline creation
        entry = tracker.track_baseline_creation(
            service_name="fastapi",
            baseline_id="baseline_456",
            config_data={"database_url": "sqlite:///app.db"},
            user_context={
                "user_id": "developer",
                "user_ip": "10.0.0.1"
            }
        )
        
        # THEN: Creation should be tracked
        assert entry.event_type == "baseline_created"
        assert entry.service_name == "fastapi"
        assert entry.baseline_id == "baseline_456"
        assert entry.user_id == "developer"

    def test_track_baseline_deletion(self):
        """Test tracking baseline deletion."""
        # GIVEN: Change tracker
        tracker = ChangeTracker()
        
        # WHEN: Tracking baseline deletion
        entry = tracker.track_baseline_deletion(
            service_name="fastapi",
            baseline_id="baseline_456",
            user_context={
                "user_id": "admin",
                "user_ip": "192.168.1.1",
                "reason": "Outdated baseline"
            }
        )
        
        # THEN: Deletion should be tracked
        assert entry.event_type == "baseline_deleted"
        assert entry.service_name == "fastapi"
        assert entry.baseline_id == "baseline_456"
        assert entry.user_id == "admin"
        assert "reason" in entry.metadata

    def test_calculate_change_impact(self):
        """Test calculating change impact score."""
        # GIVEN: Change tracker and different types of changes
        tracker = ChangeTracker()
        
        # Critical change
        critical_changes = [
            {"field": "password", "change_type": "modified"},
            {"field": "secret_key", "change_type": "modified"}
        ]
        
        # Low impact change
        low_changes = [
            {"field": "comment", "change_type": "modified"},
            {"field": "description", "change_type": "added"}
        ]
        
        # WHEN: Calculating impact
        critical_impact = tracker.calculate_change_impact(critical_changes)
        low_impact = tracker.calculate_change_impact(low_changes)
        
        # THEN: Impact scores should reflect severity
        assert critical_impact > low_impact
        assert critical_impact >= 8  # High impact score
        assert low_impact <= 3  # Low impact score


@pytest.mark.asyncio
class TestConfigurationAuditor:
    """Test ConfigurationAuditor class functionality."""

    async def test_create_configuration_auditor(self):
        """Test creating configuration auditor."""
        # GIVEN: Configuration auditor initialization
        auditor = ConfigurationAuditor()
        
        # THEN: Auditor should be initialized
        assert auditor is not None
        assert len(auditor.audit_trails) == 0

    async def test_start_audit_session(self):
        """Test starting audit session."""
        # GIVEN: Configuration auditor
        auditor = ConfigurationAuditor()
        
        # WHEN: Starting audit session
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # THEN: Session should be created
        assert session_id is not None
        assert session_id in auditor.active_sessions

    async def test_end_audit_session(self):
        """Test ending audit session."""
        # GIVEN: Configuration auditor with active session
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100"
        )
        
        # WHEN: Ending session
        success = await auditor.end_audit_session(session_id)
        
        # THEN: Session should be ended
        assert success is True
        assert session_id not in auditor.active_sessions

    async def test_audit_configuration_change(self):
        """Test auditing configuration change."""
        # GIVEN: Configuration auditor with active session
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100"
        )
        
        # WHEN: Auditing configuration change
        await auditor.audit_configuration_change(
            session_id=session_id,
            service_name="keycloak",
            baseline_id="baseline_123",
            old_config={"host": "old-host"},
            new_config={"host": "new-host"},
            change_reason="Update hostname"
        )
        
        # THEN: Change should be audited
        trail_key = ("keycloak", "baseline_123")
        assert trail_key in auditor.audit_trails
        trail = auditor.audit_trails[trail_key]
        assert len(trail.entries) > 0

    async def test_audit_baseline_lifecycle(self):
        """Test auditing baseline lifecycle events."""
        # GIVEN: Configuration auditor with active session
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="developer",
            user_ip="10.0.0.1"
        )
        
        # WHEN: Auditing baseline creation
        await auditor.audit_baseline_creation(
            session_id=session_id,
            service_name="fastapi",
            baseline_id="baseline_456",
            config_data={"database_url": "sqlite:///app.db"}
        )
        
        # WHEN: Auditing baseline deletion
        await auditor.audit_baseline_deletion(
            session_id=session_id,
            service_name="fastapi",
            baseline_id="baseline_456",
            reason="Outdated"
        )
        
        # THEN: Both events should be audited
        trail_key = ("fastapi", "baseline_456")
        assert trail_key in auditor.audit_trails
        trail = auditor.audit_trails[trail_key]
        assert len(trail.entries) == 2
        
        event_types = [entry.event_type for entry in trail.entries]
        assert "baseline_created" in event_types
        assert "baseline_deleted" in event_types

    async def test_generate_compliance_report(self):
        """Test generating compliance report."""
        # GIVEN: Configuration auditor with audit history
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100"
        )
        
        # Create some audit entries
        await auditor.audit_configuration_change(
            session_id=session_id,
            service_name="keycloak",
            baseline_id="baseline_123",
            old_config={"host": "old"},
            new_config={"host": "new"}
        )
        
        await auditor.audit_baseline_creation(
            session_id=session_id,
            service_name="fastapi",
            baseline_id="baseline_456",
            config_data={"db": "sqlite"}
        )
        
        # WHEN: Generating compliance report
        report = await auditor.generate_compliance_report(
            start_date=datetime.utcnow().replace(hour=0, minute=0, second=0),
            end_date=datetime.utcnow()
        )
        
        # THEN: Report should contain audit information
        assert "total_events" in report
        assert "services_modified" in report
        assert "users_active" in report
        assert "compliance_score" in report
        assert report["total_events"] >= 2

    async def test_search_audit_entries(self):
        """Test searching audit entries."""
        # GIVEN: Configuration auditor with audit history
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100"
        )
        
        # Create audit entries with different criteria
        await auditor.audit_configuration_change(
            session_id=session_id,
            service_name="keycloak",
            baseline_id="baseline_123",
            old_config={"password": "old"},
            new_config={"password": "new"}
        )
        
        await auditor.audit_configuration_change(
            session_id=session_id,
            service_name="fastapi",
            baseline_id="baseline_456",
            old_config={"port": 8000},
            new_config={"port": 8080}
        )
        
        # WHEN: Searching by service
        keycloak_entries = await auditor.search_audit_entries(
            service_name="keycloak"
        )
        
        # WHEN: Searching by severity
        critical_entries = await auditor.search_audit_entries(
            severity="critical"
        )
        
        # THEN: Search should return correct entries
        assert len(keycloak_entries) >= 1
        assert all(entry.service_name == "keycloak" for entry in keycloak_entries)
        
        assert len(critical_entries) >= 1
        assert all(entry.severity == "critical" for entry in critical_entries)

    async def test_export_audit_trail(self):
        """Test exporting audit trail."""
        # GIVEN: Configuration auditor with audit history
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100"
        )
        
        await auditor.audit_configuration_change(
            session_id=session_id,
            service_name="keycloak",
            baseline_id="baseline_123",
            old_config={"host": "old"},
            new_config={"host": "new"}
        )
        
        # WHEN: Exporting audit trail
        export_data = await auditor.export_audit_trail(
            service_name="keycloak",
            baseline_id="baseline_123",
            format="json"
        )
        
        # THEN: Export should contain audit data
        assert "service_name" in export_data
        assert "baseline_id" in export_data
        assert "entries" in export_data
        assert len(export_data["entries"]) > 0
        assert export_data["service_name"] == "keycloak"

    async def test_get_audit_statistics(self):
        """Test getting audit statistics."""
        # GIVEN: Configuration auditor with audit history
        auditor = ConfigurationAuditor()
        session_id = await auditor.start_audit_session(
            user_id="admin",
            user_ip="192.168.1.100"
        )
        
        # Create various audit entries
        await auditor.audit_configuration_change(
            session_id=session_id,
            service_name="keycloak",
            baseline_id="baseline_123",
            old_config={"host": "old"},
            new_config={"host": "new"}
        )
        
        await auditor.audit_baseline_creation(
            session_id=session_id,
            service_name="fastapi",
            baseline_id="baseline_456",
            config_data={"db": "sqlite"}
        )
        
        # WHEN: Getting statistics
        stats = await auditor.get_audit_statistics()
        
        # THEN: Statistics should be comprehensive
        assert "total_trails" in stats
        assert "total_entries" in stats
        assert "active_sessions" in stats
        assert "services_tracked" in stats
        assert stats["total_trails"] >= 2
        assert stats["total_entries"] >= 2
        assert "keycloak" in stats["services_tracked"]
        assert "fastapi" in stats["services_tracked"]