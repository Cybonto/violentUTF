# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Incident Response Orchestrator.

Orchestrates incident response including runbook execution,
escalation coordination, and stakeholder notification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ResponsePlan:
    """Incident response plan."""

    runbook_path: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    requires_escalation: bool = False
    stakeholders: List[str] = field(default_factory=list)


class IncidentOrchestrator:
    """Orchestrates incident response procedures."""

    def __init__(self, runbook_dir: Optional[Path] = None) -> None:
        """
        Initialize incident orchestrator.

        Args:
            runbook_dir: Directory containing runbooks
        """
        self.runbook_dir = runbook_dir or Path("docs/runbooks")
        self.active_incidents: Dict[str, Dict[str, Any]] = {}

    def initiate_response(self, incident: Dict[str, Any]) -> ResponsePlan:
        """
        Initiate incident response.

        Args:
            incident: Incident data

        Returns:
            ResponsePlan
        """
        incident_type = incident.get("incident_type", "")
        severity = incident.get("severity", "")

        # Load appropriate runbook
        runbook_path = self._select_runbook(incident_type, incident.get("database"))

        if not runbook_path or not runbook_path.exists():
            # Fallback to generic runbook
            runbook_path = self.runbook_dir / "cross_service_incident.yml"

        runbook_data = self._load_runbook(runbook_path)

        # Extract steps
        steps = runbook_data.get("recovery_steps", [])

        # Calculate estimated duration
        estimated_duration = sum(step.get("estimated_time_minutes", 0) for step in steps)

        # Determine stakeholders
        stakeholders = self._determine_stakeholders(severity)

        return ResponsePlan(
            runbook_path=str(runbook_path),
            steps=steps,
            estimated_duration_minutes=estimated_duration,
            requires_escalation=severity in ["critical", "high"],
            stakeholders=stakeholders,
        )

    def execute_runbook(self, incident_type: str, severity: str) -> Dict[str, Any]:
        """
        Execute incident response runbook.

        Args:
            incident_type: Type of incident
            severity: Incident severity

        Returns:
            Execution result
        """
        runbook_path = self._select_runbook(incident_type, None)

        if not runbook_path or not runbook_path.exists():
            return {
                "success": False,
                "error": "Runbook not found",
            }

        runbook_data = self._load_runbook(runbook_path)

        return {
            "success": True,
            "runbook": runbook_data.get("title", ""),
            "steps_count": len(runbook_data.get("recovery_steps", [])),
        }

    def coordinate_escalation(self, incident: Dict[str, Any], escalation_level: int) -> bool:
        """
        Coordinate incident escalation.

        Args:
            incident: Incident data
            escalation_level: Escalation level (1-3)

        Returns:
            Success status
        """
        incident_id = incident.get("incident_id", "")

        # Track escalation
        if incident_id not in self.active_incidents:
            self.active_incidents[incident_id] = incident

        self.active_incidents[incident_id]["escalation_level"] = escalation_level
        self.active_incidents[incident_id]["escalated_at"] = datetime.utcnow().isoformat()

        return True

    def notify_stakeholders(self, incident: Dict[str, Any], message: str) -> bool:
        """
        Notify stakeholders about incident.

        Args:
            incident: Incident data
            message: Notification message

        Returns:
            Success status
        """
        severity = incident.get("severity", "")
        stakeholders = self._determine_stakeholders(severity)

        # In production, this would send actual notifications
        # For now, just track the notification

        incident_id = incident.get("incident_id", "")
        if incident_id not in self.active_incidents:
            self.active_incidents[incident_id] = incident

        if "notifications" not in self.active_incidents[incident_id]:
            self.active_incidents[incident_id]["notifications"] = []

        self.active_incidents[incident_id]["notifications"].append(
            {
                "stakeholders": stakeholders,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return True

    def _select_runbook(self, incident_type: str, database: Optional[str]) -> Optional[Path]:
        """Select appropriate runbook."""
        runbook_map = {
            "database_failure": f"{database}_failure.yml" if database else "postgresql_failure.yml",
            "data_integrity": "data_integrity_incident.yml",
            "security_incident": "security_incident_database.yml",
            "configuration_error": "configuration_incident.yml",
            "performance_degradation": "performance_degradation.yml",
        }

        runbook_filename = runbook_map.get(incident_type, "cross_service_incident.yml")
        return self.runbook_dir / runbook_filename

    def _load_runbook(self, runbook_path: Path) -> Dict[str, Any]:
        """Load runbook from file."""
        try:
            with open(runbook_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def _determine_stakeholders(self, severity: str) -> List[str]:
        """Determine stakeholders to notify based on severity."""
        if severity == "critical":
            return ["oncall", "dba_team", "management", "all_engineering"]
        elif severity == "high":
            return ["dba_team", "tech_lead", "oncall"]
        elif severity == "medium":
            return ["dba_team"]
        else:
            return ["dba_team"]
