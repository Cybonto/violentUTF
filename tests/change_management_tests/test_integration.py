"""
Integration tests for change management system.
Tests end-to-end workflows and system integration.
"""

import pytest
from datetime import datetime
from pathlib import Path


class TestChangeManagementEndToEnd:
    """Test complete change management workflow."""

    def test_normal_change_complete_workflow(
        self,
        sample_change_request,
        stakeholder_registry,
        maintenance_windows,
        tmp_path,
    ):
        """Test complete normal change workflow from submission to execution."""
        from scripts.change_management.core.change_classifier import (
            ChangeClassifier,
        )
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        # Step 1: Classify change
        classifier = ChangeClassifier()
        change_type = classifier.classify_change(sample_change_request)
        risk = classifier.assess_risk(sample_change_request)
        impact = classifier.assess_impact(sample_change_request)

        assert change_type is not None
        assert risk is not None

        # Step 2: Validate change
        validator = ChangeValidator()
        validation = validator.perform_pre_change_checks(sample_change_request)

        assert validation.valid is True

        # Step 3: Submit for approval
        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        assert request_id is not None

        # Step 4: Route for approval
        stakeholders = workflow.route_for_approval(
            request_id, stakeholder_registry
        )

        assert len(stakeholders) > 0

        # Step 5: Approve change
        workflow.add_approval(request_id, "dba1@example.com", "approved")

        assert workflow.validate_approvals(request_id) is True

        # Step 6: Schedule change
        result = workflow.schedule_change(request_id, maintenance_windows[0])

        assert result is True

        # Step 7: Mark ready for execution
        workflow.mark_ready_for_execution(request_id)
        status = workflow.get_request_status(request_id)

        assert status["ready_for_execution"] is True

    def test_emergency_change_fast_track(self, sample_emergency_change):
        """Test emergency change fast-track workflow."""
        from scripts.change_management.core.change_classifier import (
            ChangeClassifier,
        )
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        # Classify as emergency
        classifier = ChangeClassifier()
        change_type = classifier.classify_change(sample_emergency_change)

        assert change_type.value == "emergency"

        # Submit - should auto-approve
        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_emergency_change)

        status = workflow.get_request_status(request_id)

        # Emergency changes skip approval
        assert status["approval_status"] in ["auto_approved", "approved"]

        # No maintenance window required
        assert not status.get("requires_maintenance_window", True)

    def test_major_change_extended_review(
        self, sample_major_change, stakeholder_registry
    ):
        """Test major change with extended review process."""
        from scripts.change_management.core.change_classifier import (
            ChangeClassifier,
        )
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        # Classify as major
        classifier = ChangeClassifier()
        change_type = classifier.classify_change(sample_major_change)

        assert change_type.value == "major"

        # Submit
        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_major_change)

        status = workflow.get_request_status(request_id)

        # Major changes require multiple approvers
        assert len(status["required_approvers"]) >= 2

        # Should require ADR
        assert status.get("adr_required") is True


class TestRollbackIntegration:
    """Test rollback system integration."""

    def test_sqlite_rollback_complete_workflow(self, temp_sqlite_db, tmp_path):
        """Test complete SQLite rollback workflow."""
        from scripts.change_management.rollback.sqlite_rollback import (
            SQLiteRollbackManager,
        )

        manager = SQLiteRollbackManager(backup_location=tmp_path)

        # Create snapshot before change
        snapshot_result = manager.backup_database(
            str(temp_sqlite_db), "TEST-001"
        )

        assert snapshot_result.success is True

        # Simulate change (insert data)
        import sqlite3

        conn = sqlite3.connect(str(temp_sqlite_db))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("newuser", "newuser@example.com"),
        )
        conn.commit()
        conn.close()

        # Rollback
        restore_result = manager.restore_from_backup(
            str(snapshot_result.backup_path), str(temp_sqlite_db)
        )

        assert restore_result.success is True

        # Verify rollback
        validation = manager.validate_restore(str(temp_sqlite_db))

        assert validation.valid is True

    def test_rollback_with_change_management(
        self, sample_change_request, temp_sqlite_db, tmp_path
    ):
        """Test rollback integration with change management."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )
        from scripts.change_management.rollback.sqlite_rollback import (
            SQLiteRollbackManager,
        )

        workflow = ApprovalWorkflow()
        rollback_manager = SQLiteRollbackManager(backup_location=tmp_path)

        # Submit change
        sample_change_request["database_path"] = str(temp_sqlite_db)
        request_id = workflow.submit_change_request(sample_change_request)

        # Create snapshot
        snapshot = rollback_manager.backup_database(
            str(temp_sqlite_db), request_id
        )

        assert snapshot.success is True

        # Link snapshot to change request
        workflow.link_snapshot(request_id, snapshot.snapshot_id)

        status = workflow.get_request_status(request_id)

        assert status.get("snapshot_id") is not None


class TestIncidentResponseIntegration:
    """Test incident response integration."""

    def test_incident_detection_and_response(self, sample_incident, tmp_path):
        """Test incident detection and response workflow."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )
        from scripts.change_management.incident.incident_orchestrator import (
            IncidentOrchestrator,
        )

        classifier = IncidentClassifier()
        orchestrator = IncidentOrchestrator(runbook_dir=tmp_path)

        # Classify incident
        incident_type = classifier.classify_incident(sample_incident["symptoms"])
        severity = classifier.determine_severity(sample_incident)
        rto, rpo = classifier.calculate_rto_rpo(sample_incident)

        assert incident_type is not None
        assert severity is not None

        # Initiate response
        sample_incident["incident_type"] = incident_type.value
        sample_incident["severity"] = severity.value

        response_plan = orchestrator.initiate_response(sample_incident)

        assert response_plan is not None
        assert "runbook_path" in response_plan
        assert "steps" in response_plan

    def test_incident_escalation_workflow(self, sample_incident):
        """Test incident escalation workflow."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )
        from scripts.change_management.incident.escalation_manager import (
            EscalationManager,
        )

        classifier = IncidentClassifier()
        escalation_mgr = EscalationManager()

        # Classify critical incident
        severity = classifier.determine_severity(sample_incident)

        assert severity.value == "critical"

        # Escalate
        escalation = escalation_mgr.escalate_incident(
            sample_incident, severity
        )

        assert escalation is not None
        assert escalation.immediate_escalation is True


class TestADRIntegration:
    """Test ADR system integration."""

    def test_adr_creation_for_major_change(self, sample_major_change, tmp_path):
        """Test ADR creation for major changes."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )
        from scripts.change_management.adr.adr_manager import ADRManager

        workflow = ApprovalWorkflow()
        adr_manager = ADRManager(adr_dir=tmp_path)

        # Submit major change
        request_id = workflow.submit_change_request(sample_major_change)

        status = workflow.get_request_status(request_id)

        # Major change requires ADR
        assert status.get("adr_required") is True

        # Create ADR
        adr_id = adr_manager.create_adr(
            title=sample_major_change["title"],
            context=sample_major_change["description"],
            change_request_id=request_id,
        )

        assert adr_id is not None

        # Link ADR to change request
        workflow.link_adr(request_id, adr_id)

        status = workflow.get_request_status(request_id)

        assert status.get("adr_id") is not None


class TestMonitoringIntegration:
    """Test monitoring and metrics integration."""

    def test_change_metrics_collection(self, sample_change_request):
        """Test change metrics collection."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )
        from scripts.change_management.monitoring.change_metrics import (
            ChangeMetrics,
        )

        workflow = ApprovalWorkflow()
        metrics = ChangeMetrics()

        # Submit and approve change
        request_id = workflow.submit_change_request(sample_change_request)
        workflow.add_approval(request_id, "dba1@example.com", "approved")

        # Collect metrics
        change_metrics = metrics.collect_change_metrics(request_id)

        assert change_metrics is not None
        assert "approval_time" in change_metrics
        assert "change_type" in change_metrics

    def test_incident_metrics_collection(self, sample_incident):
        """Test incident metrics collection."""
        from scripts.change_management.monitoring.incident_metrics import (
            IncidentMetrics,
        )

        metrics = IncidentMetrics()

        # Record incident
        metrics.record_incident_start(sample_incident["incident_id"])

        # Simulate resolution
        import time

        time.sleep(0.1)
        metrics.record_incident_resolution(sample_incident["incident_id"])

        # Collect metrics
        incident_metrics = metrics.get_incident_metrics(
            sample_incident["incident_id"]
        )

        assert incident_metrics is not None
        assert "mttr" in incident_metrics


class TestNotificationIntegration:
    """Test notification system integration."""

    def test_change_approval_notification(
        self, sample_change_request, mock_notification_service
    ):
        """Test change approval notifications."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        workflow.notification_service = mock_notification_service

        # Submit change
        request_id = workflow.submit_change_request(sample_change_request)

        # Send approval request
        workflow.send_approval_request(request_id, ["dba1@example.com"])

        # Verify notification sent
        notifications = mock_notification_service.get_sent_notifications()

        assert len(notifications) > 0

    def test_incident_escalation_notification(
        self, sample_incident, mock_notification_service
    ):
        """Test incident escalation notifications."""
        from scripts.change_management.incident.escalation_manager import (
            EscalationManager,
        )

        escalation_mgr = EscalationManager()
        escalation_mgr.notification_service = mock_notification_service

        # Escalate incident
        from scripts.change_management.incident.incident_classifier import (
            Severity,
        )

        escalation_mgr.escalate_incident(
            sample_incident, Severity.CRITICAL
        )

        # Verify escalation notification
        notifications = mock_notification_service.get_sent_notifications()

        assert len(notifications) > 0


class TestWorkflowValidation:
    """Test workflow validation for pytest --workflow-validation flag."""

    def test_workflow_validation_all_systems(
        self,
        sample_change_request,
        sample_incident,
        temp_sqlite_db,
        tmp_path,
    ):
        """Test complete workflow validation across all systems."""
        # This test validates all integrated workflows

        # 1. Change Management Workflow
        from scripts.change_management.core.change_classifier import (
            ChangeClassifier,
        )
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        classifier = ChangeClassifier()
        workflow = ApprovalWorkflow()

        change_type = classifier.classify_change(sample_change_request)
        assert change_type is not None

        request_id = workflow.submit_change_request(sample_change_request)
        assert request_id is not None

        # 2. Rollback Workflow
        from scripts.change_management.rollback.sqlite_rollback import (
            SQLiteRollbackManager,
        )

        rollback_mgr = SQLiteRollbackManager(backup_location=tmp_path)
        snapshot = rollback_mgr.backup_database(
            str(temp_sqlite_db), request_id
        )
        assert snapshot.success is True

        # 3. Incident Response Workflow
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        inc_classifier = IncidentClassifier()
        incident_type = inc_classifier.classify_incident(
            sample_incident["symptoms"]
        )
        assert incident_type is not None

        # All workflows validated
        assert True
