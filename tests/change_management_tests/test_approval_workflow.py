"""
Tests for change approval workflow system.
Tests change request submission, approval routing, and workflow validation.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any


class TestChangeRequestSubmission:
    """Test change request submission functionality."""

    def test_submit_normal_change_request(self, sample_change_request):
        """Test submitting a normal change request."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        assert request_id is not None
        assert request_id.startswith("CR-")
        assert len(request_id) > 8

    def test_submit_emergency_change_request(self, sample_emergency_change):
        """Test submitting an emergency change request."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_emergency_change)

        assert request_id is not None
        # Emergency changes should be auto-approved
        status = workflow.get_request_status(request_id)
        assert status["approval_status"] in ["auto_approved", "approved"]

    def test_submit_major_change_request(self, sample_major_change):
        """Test submitting a major change request."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_major_change)

        assert request_id is not None
        status = workflow.get_request_status(request_id)
        assert status["approval_status"] == "pending"
        assert len(status["required_approvers"]) >= 2


class TestApprovalRouting:
    """Test approval routing functionality."""

    def test_route_normal_change_to_dba(
        self, sample_change_request, stakeholder_registry
    ):
        """Test routing normal change to appropriate stakeholders."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        stakeholders = workflow.route_for_approval(request_id, stakeholder_registry)
        assert "dba_team" in stakeholders
        assert len(stakeholders) >= 1

    def test_route_major_change_to_multiple_approvers(
        self, sample_major_change, stakeholder_registry
    ):
        """Test routing major change to multiple approvers."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_major_change)

        stakeholders = workflow.route_for_approval(request_id, stakeholder_registry)
        assert "dba_team" in stakeholders
        assert "tech_lead" in stakeholders or "architect" in stakeholders
        assert len(stakeholders) >= 2

    def test_emergency_change_notification_routing(
        self, sample_emergency_change, stakeholder_registry
    ):
        """Test emergency change notification routing."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_emergency_change)

        notifications = workflow.get_notification_list(request_id)
        assert "oncall" in notifications
        assert "dba_team" in notifications


class TestApprovalValidation:
    """Test approval validation functionality."""

    def test_validate_single_approval_sufficient(self, sample_change_request):
        """Test that single approval is sufficient for normal changes."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        # Simulate approval
        workflow.add_approval(request_id, "dba1@example.com", "approved")

        is_valid = workflow.validate_approvals(request_id)
        assert is_valid is True

    def test_validate_multiple_approvals_required(self, sample_major_change):
        """Test that multiple approvals are required for major changes."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_major_change)

        # Add one approval
        workflow.add_approval(request_id, "dba1@example.com", "approved")

        # Should not be sufficient
        is_valid = workflow.validate_approvals(request_id)
        assert is_valid is False

        # Add second approval
        workflow.add_approval(request_id, "techlead@example.com", "approved")

        # Now should be sufficient
        is_valid = workflow.validate_approvals(request_id)
        assert is_valid is True

    def test_validate_rejection_blocks_change(self, sample_change_request):
        """Test that rejection blocks change execution."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        # Add rejection
        workflow.add_approval(
            request_id, "dba1@example.com", "rejected", reason="Insufficient testing"
        )

        is_valid = workflow.validate_approvals(request_id)
        assert is_valid is False

        status = workflow.get_request_status(request_id)
        assert status["approval_status"] == "rejected"


class TestMaintenanceWindowScheduling:
    """Test maintenance window scheduling."""

    def test_schedule_change_in_maintenance_window(
        self, sample_change_request, maintenance_windows
    ):
        """Test scheduling change during maintenance window."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        # Schedule in available window
        result = workflow.schedule_change(request_id, maintenance_windows[0])
        assert result is True

        status = workflow.get_request_status(request_id)
        assert status["scheduled"] is True
        assert "schedule_time" in status

    def test_emergency_change_bypasses_maintenance_window(
        self, sample_emergency_change
    ):
        """Test that emergency changes bypass maintenance window."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_emergency_change)

        status = workflow.get_request_status(request_id)
        assert status.get("requires_maintenance_window") is False

    def test_find_available_maintenance_window(
        self, sample_change_request, maintenance_windows
    ):
        """Test finding next available maintenance window."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        request_id = workflow.submit_change_request(sample_change_request)

        next_window = workflow.find_next_maintenance_window(maintenance_windows)
        assert next_window is not None
        assert "start" in next_window
        assert "end" in next_window


class TestWorkflowLifecycle:
    """Test complete workflow lifecycle."""

    def test_complete_normal_change_workflow(
        self, sample_change_request, stakeholder_registry, maintenance_windows
    ):
        """Test complete workflow from submission to execution."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()

        # Submit
        request_id = workflow.submit_change_request(sample_change_request)
        assert workflow.get_request_status(request_id)["approval_status"] == "pending"

        # Route for approval
        stakeholders = workflow.route_for_approval(request_id, stakeholder_registry)
        assert len(stakeholders) > 0

        # Approve
        workflow.add_approval(request_id, "dba1@example.com", "approved")
        assert workflow.validate_approvals(request_id) is True

        # Schedule
        workflow.schedule_change(request_id, maintenance_windows[0])
        status = workflow.get_request_status(request_id)
        assert status["scheduled"] is True

        # Mark as ready for execution
        workflow.mark_ready_for_execution(request_id)
        status = workflow.get_request_status(request_id)
        assert status["ready_for_execution"] is True

    def test_rejected_change_workflow(self, sample_change_request):
        """Test workflow when change is rejected."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()

        # Submit
        request_id = workflow.submit_change_request(sample_change_request)

        # Reject
        workflow.add_approval(
            request_id, "dba1@example.com", "rejected", reason="Security concerns"
        )

        assert workflow.validate_approvals(request_id) is False

        status = workflow.get_request_status(request_id)
        assert status["approval_status"] == "rejected"
        assert "Security concerns" in status.get("rejection_reason", "")

        # Cannot execute rejected change
        with pytest.raises(Exception):
            workflow.mark_ready_for_execution(request_id)


class TestApprovalWorkflowIntegration:
    """Test integration with other systems."""

    def test_workflow_with_change_classifier(self, sample_major_change):
        """Test integration with change classifier."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )
        from scripts.change_management.core.change_classifier import (
            ChangeClassifier,
        )

        classifier = ChangeClassifier()
        workflow = ApprovalWorkflow()

        # Classify change
        change_type = classifier.classify_change(sample_major_change)
        risk = classifier.assess_risk(sample_major_change)

        # Submit with classification
        sample_major_change["classified_type"] = change_type.value
        sample_major_change["classified_risk"] = risk.value

        request_id = workflow.submit_change_request(sample_major_change)
        status = workflow.get_request_status(request_id)

        # Major changes require multiple approvals
        assert len(status["required_approvers"]) >= 2

    def test_workflow_notification_integration(
        self, sample_change_request, mock_notification_service
    ):
        """Test integration with notification service."""
        from scripts.change_management.core.approval_workflow import (
            ApprovalWorkflow,
        )

        workflow = ApprovalWorkflow()
        workflow.notification_service = mock_notification_service

        request_id = workflow.submit_change_request(sample_change_request)
        workflow.send_approval_request(request_id, ["dba1@example.com"])

        notifications = mock_notification_service.get_sent_notifications()
        assert len(notifications) > 0
        assert any("approval" in n["subject"].lower() for n in notifications)
