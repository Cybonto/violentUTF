# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Incident Classification System.

Classifies incidents by type, determines severity, calculates RTO/RPO,
and selects appropriate runbooks.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class IncidentType(Enum):
    """Types of database incidents."""

    DATABASE_FAILURE = "database_failure"
    DATA_INTEGRITY = "data_integrity"
    SECURITY_INCIDENT = "security_incident"
    CONFIGURATION_ERROR = "configuration_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class Severity(Enum):
    """Incident severity levels."""

    CRITICAL = "critical"  # P0
    HIGH = "high"  # P1
    MEDIUM = "medium"  # P2
    LOW = "low"  # P3


@dataclass
class IncidentImpact:
    """Incident impact assessment."""

    affected_services: List[str] = field(default_factory=list)
    affected_databases: List[str] = field(default_factory=list)
    user_impact: str = "unknown"
    user_count_affected: int = 0
    data_loss_risk: bool = False


@dataclass
class EscalationPath:
    """Incident escalation path."""

    immediate_escalation: bool = False
    escalation_level: int = 1
    contacts: List[str] = field(default_factory=list)
    escalation_threshold_minutes: int = 60


class IncidentClassifier:
    """Classifies incidents and determines response parameters."""

    # Symptom patterns for classification
    SYMPTOM_PATTERNS = {
        IncidentType.DATABASE_FAILURE: [
            "connection refused",
            "database unavailable",
            "503 errors",
            "database down",
        ],
        IncidentType.DATA_INTEGRITY: [
            "corruption",
            "referential integrity",
            "unexpected null",
            "data inconsistency",
        ],
        IncidentType.SECURITY_INCIDENT: [
            "unauthorized access",
            "failed authentication",
            "suspicious query",
            "security breach",
        ],
        IncidentType.CONFIGURATION_ERROR: [
            "configuration mismatch",
            "startup failure",
            "invalid parameter",
            "misconfiguration",
        ],
        IncidentType.PERFORMANCE_DEGRADATION: [
            "slow query",
            "high cpu",
            "high memory",
            "elevated response time",
        ],
    }

    # RTO/RPO targets by severity (in minutes)
    RTO_TARGETS = {
        Severity.CRITICAL: 15,
        Severity.HIGH: 60,
        Severity.MEDIUM: 240,
        Severity.LOW: 1440,
    }

    RPO_TARGETS = {
        Severity.CRITICAL: 60,
        Severity.HIGH: 120,
        Severity.MEDIUM: 480,
        Severity.LOW: 2880,
    }

    def __init__(self, runbook_dir: Optional[Path] = None) -> None:
        """
        Initialize incident classifier.

        Args:
            runbook_dir: Directory containing runbooks
        """
        self.runbook_dir = runbook_dir or Path("docs/runbooks")

    def classify_incident(self, symptoms: List[str]) -> IncidentType:
        """
        Classify incident based on symptoms.

        Args:
            symptoms: List of incident symptoms

        Returns:
            IncidentType
        """
        symptoms_lower = [s.lower() for s in symptoms]

        # Score each incident type
        scores = {}
        for incident_type, patterns in self.SYMPTOM_PATTERNS.items():
            score = 0
            for pattern in patterns:
                for symptom in symptoms_lower:
                    if pattern in symptom:
                        score += 1
            scores[incident_type] = score

        # Return type with highest score
        max_type = max(scores.items(), key=lambda x: x[1])
        return max_type[0]

    def determine_severity(self, incident: Dict[str, Any]) -> Severity:
        """
        Determine incident severity.

        Args:
            incident: Incident data

        Returns:
            Severity level
        """
        incident_type = incident.get("incident_type", "")
        symptoms = incident.get("symptoms", [])
        user_impact = incident.get("user_impact", "")

        # Critical indicators
        critical_indicators = [
            "complete failure",
            "authentication unavailable",
            "database down",
            "security breach",
            "data loss",
        ]

        symptoms_lower = [s.lower() for s in symptoms]
        for indicator in critical_indicators:
            for symptom in symptoms_lower:
                if indicator in symptom:
                    return Severity.CRITICAL

        # Check incident type for severity
        if incident_type == "database_failure":
            return Severity.CRITICAL
        elif incident_type == "security_incident":
            return Severity.CRITICAL
        elif incident_type == "data_integrity":
            return Severity.HIGH
        elif incident_type == "performance_degradation":
            if user_impact == "minimal" or user_impact == "none":
                return Severity.MEDIUM
            return Severity.HIGH
        elif incident_type == "configuration_error":
            return Severity.MEDIUM

        return Severity.LOW

    def calculate_rto_rpo(self, incident: Dict[str, Any]) -> Tuple[int, int]:
        """
        Calculate RTO and RPO for incident.

        Args:
            incident: Incident data

        Returns:
            Tuple of (RTO minutes, RPO minutes)
        """
        # Get severity
        severity_str = incident.get("severity", "")
        if severity_str:
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = self.determine_severity(incident)
        else:
            severity = self.determine_severity(incident)

        # Get targets from predefined values or incident specification
        rto = incident.get("rto_target", self.RTO_TARGETS[severity])
        rpo = incident.get("rpo_target", self.RPO_TARGETS[severity])

        return (rto, rpo)

    def assess_impact(self, incident: Dict[str, Any]) -> IncidentImpact:
        """
        Assess incident impact.

        Args:
            incident: Incident data

        Returns:
            IncidentImpact
        """
        incident_type = incident.get("incident_type", "")
        database = incident.get("database", "")

        # Determine affected services based on database
        affected_services = []
        affected_databases = []

        if database == "postgresql":
            affected_services = ["keycloak", "api", "streamlit"]
            affected_databases = ["postgresql"]
        elif database == "sqlite":
            affected_services = ["api"]
            affected_databases = ["sqlite"]
        elif database == "multiple":
            affected_services = [
                "keycloak",
                "api",
                "streamlit",
            ]
            affected_databases = ["postgresql", "sqlite"]

        # Determine user impact
        if incident_type in [
            "database_failure",
            "security_incident",
        ]:
            user_impact = "critical"
            user_count = 1000  # Estimate
        elif incident_type == "data_integrity":
            user_impact = "high"
            user_count = 500
        else:
            user_impact = "medium"
            user_count = 100

        return IncidentImpact(
            affected_services=affected_services,
            affected_databases=affected_databases,
            user_impact=user_impact,
            user_count_affected=user_count,
            data_loss_risk=incident_type in ["data_integrity", "database_failure"],
        )

    def select_runbook(self, incident: Dict[str, Any]) -> Optional[str]:
        """
        Select appropriate runbook for incident.

        Args:
            incident: Incident data

        Returns:
            Path to runbook file
        """
        incident_type = incident.get("incident_type", "")
        database = incident.get("database", "")

        # Map incident type to runbook
        runbook_map = {
            "database_failure": f"{database}_failure.yml",
            "data_integrity": "data_integrity_incident.yml",
            "security_incident": "security_incident_database.yml",
            "configuration_error": "configuration_incident.yml",
            "performance_degradation": "performance_degradation.yml",
        }

        runbook_filename = runbook_map.get(incident_type, "cross_service_incident.yml")
        runbook_path = self.runbook_dir / runbook_filename

        return str(runbook_path) if runbook_path.exists() else None

    def determine_escalation_path(self, incident: Dict[str, Any]) -> EscalationPath:
        """
        Determine escalation path for incident.

        Args:
            incident: Incident data

        Returns:
            EscalationPath
        """
        severity = self.determine_severity(incident)
        time_elapsed = incident.get("time_elapsed_minutes", 0)

        # Critical incidents escalate immediately
        if severity == Severity.CRITICAL:
            return EscalationPath(
                immediate_escalation=True,
                escalation_level=3,
                contacts=["oncall", "dba_team", "management"],
                escalation_threshold_minutes=15,
            )

        # High severity incidents
        if severity == Severity.HIGH:
            escalation_level = 1
            if time_elapsed > 60:
                escalation_level = 2

            return EscalationPath(
                immediate_escalation=False,
                escalation_level=escalation_level,
                contacts=["dba_team", "tech_lead"],
                escalation_threshold_minutes=60,
            )

        # Medium/Low severity
        return EscalationPath(
            immediate_escalation=False,
            escalation_level=1,
            contacts=["dba_team"],
            escalation_threshold_minutes=240,
        )

    def classify_from_monitoring(self, monitoring_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Classify incident from monitoring data.

        Args:
            monitoring_data: Monitoring metrics

        Returns:
            Incident data or None
        """
        symptoms = []

        # Check CPU
        if monitoring_data.get("cpu_usage", 0) > 90:
            symptoms.append("High CPU usage detected")

        # Check memory
        if monitoring_data.get("memory_usage", 0) > 85:
            symptoms.append("High memory usage detected")

        # Check query latency
        if monitoring_data.get("query_latency_p95", 0) > 1000:
            symptoms.append("Slow query performance detected")

        if not symptoms:
            return None

        incident_type = self.classify_incident(symptoms)

        return {
            "incident_type": incident_type.value,
            "symptoms": symptoms,
            "monitoring_data": monitoring_data,
        }

    def generate_incident_report(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive incident report.

        Args:
            incident: Incident data

        Returns:
            Complete incident report
        """
        # Classify if not already classified
        if "incident_type" not in incident:
            incident_type = self.classify_incident(incident.get("symptoms", []))
            incident["incident_type"] = incident_type.value

        # Determine severity
        severity = self.determine_severity(incident)

        # Calculate RTO/RPO
        rto, rpo = self.calculate_rto_rpo(incident)

        # Assess impact
        impact = self.assess_impact(incident)

        # Select runbook
        runbook_path = self.select_runbook(incident)

        # Determine escalation
        escalation = self.determine_escalation_path(incident)

        return {
            "incident_type": incident.get("incident_type"),
            "severity": severity.value,
            "rto_target": rto,
            "rpo_target": rpo,
            "affected_services": impact.affected_services,
            "affected_databases": impact.affected_databases,
            "user_impact": impact.user_impact,
            "recommended_runbook": runbook_path,
            "escalation_required": escalation.immediate_escalation,
            "escalation_contacts": escalation.contacts,
        }
