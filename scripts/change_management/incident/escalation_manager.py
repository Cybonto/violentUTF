# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Escalation Manager.

Manages incident escalation procedures and notifications.
"""

from dataclasses import dataclass
from typing import Any, Dict

from .incident_classifier import Severity


@dataclass
class EscalationResult:
    """Result of escalation operation."""

    success: bool
    escalation_level: int
    immediate_escalation: bool
    contacts_notified: int = 0
    error_message: str = ""


class EscalationManager:
    """Manages incident escalation."""

    def __init__(self) -> None:
        """Initialize escalation manager."""
        self.notification_service = None

    def escalate_incident(self, incident: Dict[str, Any], severity: Severity) -> EscalationResult:
        """
        Escalate incident based on severity.

        Args:
            incident: Incident data
            severity: Severity enum value

        Returns:
            EscalationResult
        """
        severity_str = severity.value if hasattr(severity, "value") else str(severity)
        contacts_notified = 0

        # Send notifications based on severity
        if self.notification_service:
            incident_id = incident.get("id", "UNKNOWN")
            incident_title = incident.get("title", "Incident Escalation")

            try:
                if severity_str == "critical":
                    # Send both email and Slack for critical incidents
                    self.notification_service.send_email(
                        to="oncall@company.com",
                        subject=f"CRITICAL INCIDENT: {incident_title}",
                        body=f"Critical incident {incident_id} requires immediate attention.",
                    )
                    self.notification_service.send_slack(
                        channel="#incidents", message=f"🚨 CRITICAL: {incident_title} ({incident_id})"
                    )
                    contacts_notified = 3
                elif severity_str == "high":
                    # Send email for high severity
                    self.notification_service.send_email(
                        to="team@company.com",
                        subject=f"HIGH SEVERITY INCIDENT: {incident_title}",
                        body=f"High severity incident {incident_id} needs attention.",
                    )
                    contacts_notified = 2
                else:
                    # Send Slack notification for other severities
                    self.notification_service.send_slack(
                        channel="#general", message=f"Incident escalated: {incident_title} ({incident_id})"
                    )
                    contacts_notified = 1
            except Exception:
                # Continue with escalation even if notifications fail
                pass

        # Determine escalation parameters
        if severity_str == "critical":
            return EscalationResult(
                success=True,
                escalation_level=3,
                immediate_escalation=True,
                contacts_notified=contacts_notified,
            )
        elif severity_str == "high":
            return EscalationResult(
                success=True,
                escalation_level=2,
                immediate_escalation=False,
                contacts_notified=contacts_notified,
            )
        else:
            return EscalationResult(
                success=True,
                escalation_level=1,
                immediate_escalation=False,
                contacts_notified=contacts_notified,
            )
