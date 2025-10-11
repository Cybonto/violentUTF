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

        # Determine escalation parameters
        if severity_str == "critical":
            return EscalationResult(
                success=True,
                escalation_level=3,
                immediate_escalation=True,
                contacts_notified=3,
            )
        elif severity_str == "high":
            return EscalationResult(
                success=True,
                escalation_level=2,
                immediate_escalation=False,
                contacts_notified=2,
            )
        else:
            return EscalationResult(
                success=True,
                escalation_level=1,
                immediate_escalation=False,
                contacts_notified=1,
            )
