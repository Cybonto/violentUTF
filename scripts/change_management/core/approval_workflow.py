# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Change Approval Workflow System.

Handles change request submission, approval routing, stakeholder management,
and maintenance window scheduling.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChangeRequestStatus:
    """Status of a change request."""

    request_id: str
    approval_status: str
    required_approvers: List[str] = field(default_factory=list)
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    scheduled: bool = False
    schedule_time: Optional[str] = None
    ready_for_execution: bool = False
    requires_maintenance_window: bool = True
    adr_required: bool = False
    adr_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    rejection_reason: str = ""
    created_at: str = ""
    updated_at: str = ""


class ApprovalWorkflow:
    """Manages change request approval workflows."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        """
        Initialize approval workflow manager.

        Args:
            storage_path: Optional path for persisting workflow data
        """
        self.storage_path = storage_path
        self.requests: Dict[str, Dict[str, Any]] = {}
        self.notification_service = None

        if self.storage_path:
            self.storage_path = Path(storage_path)
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def submit_change_request(self, change_request: Dict[str, Any]) -> str:
        """
        Submit a change request for approval.

        Args:
            change_request: Change request data

        Returns:
            Request ID
        """
        # Generate unique request ID
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8]
        request_id = f"CR-{timestamp}-{unique_id}"

        # Determine approval requirements based on change type
        change_type = change_request.get("change_type", "normal")
        approval_status = self._determine_initial_status(change_type)
        required_approvers = self._determine_required_approvers(change_type)
        requires_window = change_type not in ["emergency", "standard"]

        # Create request record
        now = datetime.utcnow().isoformat()
        self.requests[request_id] = {
            "request_id": request_id,
            "change_request": change_request,
            "approval_status": approval_status,
            "required_approvers": required_approvers,
            "approvals": [],
            "scheduled": False,
            "schedule_time": None,
            "ready_for_execution": approval_status == "auto_approved",
            "requires_maintenance_window": requires_window,
            "adr_required": change_request.get("adr_required", False),
            "adr_id": None,
            "snapshot_id": None,
            "rejection_reason": "",
            "created_at": now,
            "updated_at": now,
        }

        # Persist if storage path configured
        if self.storage_path:
            self._save_request(request_id)

        return request_id

    def _determine_initial_status(self, change_type: str) -> str:
        """Determine initial approval status based on change type."""
        if change_type == "emergency":
            return "auto_approved"
        elif change_type == "standard":
            return "approved"
        else:
            return "pending"

    def _determine_required_approvers(self, change_type: str) -> List[str]:
        """Determine required approvers based on change type."""
        if change_type == "emergency":
            return []
        elif change_type == "standard":
            return []
        elif change_type == "major":
            return ["dba", "tech_lead"]
        else:
            return ["dba"]

    def route_for_approval(self, request_id: str, stakeholder_registry: Dict[str, List[str]]) -> List[str]:
        """
        Route change request to appropriate stakeholders.

        Args:
            request_id: Change request ID
            stakeholder_registry: Registry of stakeholders

        Returns:
            List of stakeholder groups
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]
        required_approvers = request["required_approvers"]

        # Map approver roles to stakeholder groups
        stakeholder_groups = []
        for approver_role in required_approvers:
            if approver_role in stakeholder_registry:
                stakeholder_groups.append(approver_role)
            elif f"{approver_role}_team" in stakeholder_registry:
                stakeholder_groups.append(f"{approver_role}_team")

        # Always include dba_team for database changes
        if "dba_team" not in stakeholder_groups:
            stakeholder_groups.append("dba_team")

        return stakeholder_groups

    def add_approval(
        self,
        request_id: str,
        approver: str,
        decision: str,
        reason: str = "",
    ) -> bool:
        """
        Add approval or rejection to change request.

        Args:
            request_id: Change request ID
            approver: Approver email
            decision: "approved" or "rejected"
            reason: Optional reason for decision

        Returns:
            Success status
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        # Add approval record
        approval = {
            "approver": approver,
            "decision": decision,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        request["approvals"].append(approval)

        # Update status if rejected
        if decision == "rejected":
            request["approval_status"] = "rejected"
            request["rejection_reason"] = reason
            request["ready_for_execution"] = False

        request["updated_at"] = datetime.utcnow().isoformat()

        # Persist
        if self.storage_path:
            self._save_request(request_id)

        return True

    def validate_approvals(self, request_id: str) -> bool:
        """
        Validate if change request has sufficient approvals.

        Args:
            request_id: Change request ID

        Returns:
            True if approvals are sufficient
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        # If rejected, always return False
        if request["approval_status"] == "rejected":
            return False

        # If auto-approved or already approved, return True
        if request["approval_status"] in ["auto_approved", "approved"]:
            return True

        # Check if sufficient approvals received
        required_count = len(request["required_approvers"])
        approved_count = sum(1 for a in request["approvals"] if a["decision"] == "approved")

        is_valid = approved_count >= required_count

        # Update status if valid
        if is_valid:
            request["approval_status"] = "approved"
            request["updated_at"] = datetime.utcnow().isoformat()

            if self.storage_path:
                self._save_request(request_id)

        return is_valid

    def schedule_change(self, request_id: str, maintenance_window: Dict[str, Any]) -> bool:
        """
        Schedule change in maintenance window.

        Args:
            request_id: Change request ID
            maintenance_window: Maintenance window data

        Returns:
            Success status
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        # Schedule change
        request["scheduled"] = True
        request["schedule_time"] = maintenance_window.get("start")
        request["maintenance_window_id"] = maintenance_window.get("id")
        request["updated_at"] = datetime.utcnow().isoformat()

        if self.storage_path:
            self._save_request(request_id)

        return True

    def find_next_maintenance_window(self, maintenance_windows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find next available maintenance window.

        Args:
            maintenance_windows: List of maintenance windows

        Returns:
            Next available window or None
        """
        now = datetime.utcnow()

        for window in maintenance_windows:
            window_start = datetime.fromisoformat(window["start"])
            if window_start > now:
                return window

        return None

    def mark_ready_for_execution(self, request_id: str) -> bool:
        """
        Mark change request as ready for execution.

        Args:
            request_id: Change request ID

        Returns:
            Success status

        Raises:
            Exception: If change is rejected or not approved
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]

        # Validate status
        if request["approval_status"] == "rejected":
            raise ValueError(f"Cannot execute rejected change: {request['rejection_reason']}")

        if request["approval_status"] not in [
            "approved",
            "auto_approved",
        ]:
            raise ValueError("Change not approved for execution")

        # Mark ready
        request["ready_for_execution"] = True
        request["updated_at"] = datetime.utcnow().isoformat()

        if self.storage_path:
            self._save_request(request_id)

        return True

    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get status of change request.

        Args:
            request_id: Change request ID

        Returns:
            Request status data
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        return self.requests[request_id].copy()

    def get_notification_list(self, request_id: str) -> List[str]:
        """
        Get notification list for change request.

        Args:
            request_id: Change request ID

        Returns:
            List of stakeholder groups to notify
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        request = self.requests[request_id]
        change_type = request["change_request"].get("change_type", "normal")

        if change_type == "emergency":
            return ["oncall", "dba_team", "management"]
        elif change_type == "major":
            return ["dba_team", "tech_lead", "architect", "all_engineering"]
        else:
            return ["dba_team", "submitter"]

    def send_approval_request(self, request_id: str, recipients: List[str]) -> bool:
        """
        Send approval request notification.

        Args:
            request_id: Change request ID
            recipients: List of recipient emails

        Returns:
            Success status
        """
        if self.notification_service is None:
            return False

        request = self.requests[request_id]
        subject = f"Change Approval Required: {request_id}"
        body = (
            f"Change request {request_id} requires your approval.\n\n"
            f"Title: {request['change_request'].get('title', 'N/A')}\n"
            f"Type: {request['change_request'].get('change_type', 'N/A')}\n"
        )

        self.notification_service.send_email(recipients, subject, body)
        return True

    def link_adr(self, request_id: str, adr_id: str) -> bool:
        """
        Link ADR to change request.

        Args:
            request_id: Change request ID
            adr_id: ADR ID

        Returns:
            Success status
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        self.requests[request_id]["adr_id"] = adr_id
        self.requests[request_id]["updated_at"] = datetime.utcnow().isoformat()

        if self.storage_path:
            self._save_request(request_id)

        return True

    def link_snapshot(self, request_id: str, snapshot_id: str) -> bool:
        """
        Link snapshot to change request.

        Args:
            request_id: Change request ID
            snapshot_id: Snapshot ID

        Returns:
            Success status
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")

        self.requests[request_id]["snapshot_id"] = snapshot_id
        self.requests[request_id]["updated_at"] = datetime.utcnow().isoformat()

        if self.storage_path:
            self._save_request(request_id)

        return True

    def _save_request(self, request_id: str) -> None:
        """Save request to storage."""
        if not self.storage_path:
            return

        file_path = self.storage_path / f"{request_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.requests[request_id], f, indent=2)

    def _load_request(self, request_id: str) -> None:
        """Load request from storage."""
        if not self.storage_path:
            return

        file_path = self.storage_path / f"{request_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                self.requests[request_id] = json.load(f)
