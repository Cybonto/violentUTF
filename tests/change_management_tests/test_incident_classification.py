"""
Tests for incident classification system.
Tests incident type classification, severity determination, and RTO/RPO calculation.
"""

import pytest
from typing import Dict, Any


class TestIncidentTypeClassification:
    """Test incident type classification."""

    def test_classify_database_failure_incident(self, sample_incident):
        """Test classification of database failure incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            IncidentType,
        )

        classifier = IncidentClassifier()
        incident_type = classifier.classify_incident(sample_incident["symptoms"])

        assert incident_type == IncidentType.DATABASE_FAILURE

    def test_classify_performance_degradation(self, sample_incident_p1):
        """Test classification of performance degradation incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            IncidentType,
        )

        classifier = IncidentClassifier()
        incident_type = classifier.classify_incident(sample_incident_p1["symptoms"])

        assert incident_type == IncidentType.PERFORMANCE_DEGRADATION

    def test_classify_security_incident(self):
        """Test classification of security incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            IncidentType,
        )

        classifier = IncidentClassifier()
        symptoms = [
            "Unauthorized access detected",
            "Multiple failed authentication attempts",
            "Suspicious SQL queries",
        ]

        incident_type = classifier.classify_incident(symptoms)

        assert incident_type == IncidentType.SECURITY_INCIDENT

    def test_classify_data_integrity_incident(self):
        """Test classification of data integrity incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            IncidentType,
        )

        classifier = IncidentClassifier()
        symptoms = [
            "Data corruption detected",
            "Referential integrity violation",
            "Unexpected NULL values",
        ]

        incident_type = classifier.classify_incident(symptoms)

        assert incident_type == IncidentType.DATA_INTEGRITY

    def test_classify_configuration_error(self):
        """Test classification of configuration error incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            IncidentType,
        )

        classifier = IncidentClassifier()
        symptoms = [
            "Configuration mismatch",
            "Service startup failure",
            "Invalid connection parameters",
        ]

        incident_type = classifier.classify_incident(symptoms)

        assert incident_type == IncidentType.CONFIGURATION_ERROR


class TestSeverityDetermination:
    """Test incident severity determination."""

    def test_determine_critical_severity(self, sample_incident):
        """Test determination of critical severity."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            Severity,
        )

        classifier = IncidentClassifier()
        severity = classifier.determine_severity(sample_incident)

        assert severity == Severity.CRITICAL

    def test_determine_high_severity(self, sample_incident_p1):
        """Test determination of high severity."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            Severity,
        )

        classifier = IncidentClassifier()
        severity = classifier.determine_severity(sample_incident_p1)

        assert severity == Severity.HIGH

    def test_determine_medium_severity(self):
        """Test determination of medium severity."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            Severity,
        )

        classifier = IncidentClassifier()
        incident = {
            "incident_type": "configuration_error",
            "symptoms": ["Non-critical configuration issue"],
            "user_impact": "minimal",
        }

        severity = classifier.determine_severity(incident)

        assert severity == Severity.MEDIUM

    def test_determine_low_severity(self):
        """Test determination of low severity."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
            Severity,
        )

        classifier = IncidentClassifier()
        incident = {
            "incident_type": "performance_degradation",
            "symptoms": ["Slightly elevated response time"],
            "user_impact": "none",
        }

        severity = classifier.determine_severity(incident)

        assert severity == Severity.LOW


class TestRTORPOCalculation:
    """Test RTO and RPO calculation."""

    def test_calculate_rto_critical_incident(self, sample_incident):
        """Test RTO calculation for critical incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        rto, rpo = classifier.calculate_rto_rpo(sample_incident)

        # Critical incidents: 15-minute RTO
        assert rto == 15
        assert rpo <= 60

    def test_calculate_rto_high_incident(self, sample_incident_p1):
        """Test RTO calculation for high severity incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        rto, rpo = classifier.calculate_rto_rpo(sample_incident_p1)

        # High severity: 1-hour RTO
        assert rto == 60
        assert rpo <= 120

    def test_calculate_rto_medium_incident(self):
        """Test RTO calculation for medium severity incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        incident = {
            "incident_type": "configuration_error",
            "severity": "medium",
        }

        rto, rpo = classifier.calculate_rto_rpo(incident)

        # Medium severity: 4-hour RTO
        assert rto == 240
        assert rpo <= 480

    def test_calculate_rto_low_incident(self):
        """Test RTO calculation for low severity incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        incident = {
            "incident_type": "performance_degradation",
            "severity": "low",
        }

        rto, rpo = classifier.calculate_rto_rpo(incident)

        # Low severity: 24-hour RTO
        assert rto == 1440
        assert rpo <= 2880


class TestIncidentImpactAssessment:
    """Test incident impact assessment."""

    def test_assess_multi_service_impact(self, sample_incident):
        """Test assessment of multi-service impact."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        impact = classifier.assess_impact(sample_incident)

        assert len(impact.affected_services) > 0
        assert any(
            service in impact.affected_services
            for service in ["keycloak", "api", "streamlit"]
        )

    def test_assess_database_impact(self, sample_incident):
        """Test assessment of database impact."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        impact = classifier.assess_impact(sample_incident)

        assert "postgresql" in impact.affected_databases

    def test_assess_user_impact_critical(self, sample_incident):
        """Test assessment of critical user impact."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        impact = classifier.assess_impact(sample_incident)

        assert impact.user_impact == "critical"
        assert impact.user_count_affected > 0


class TestRunbookSelection:
    """Test runbook selection for incidents."""

    def test_select_runbook_for_database_failure(self, sample_incident):
        """Test runbook selection for database failure."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        runbook_path = classifier.select_runbook(sample_incident)

        assert runbook_path is not None
        assert "postgresql_failure" in runbook_path.lower()

    def test_select_runbook_for_security_incident(self):
        """Test runbook selection for security incident."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        incident = {
            "incident_type": "security_incident",
            "database": "postgresql",
        }

        runbook_path = classifier.select_runbook(incident)

        assert runbook_path is not None
        assert "security" in runbook_path.lower()

    def test_select_runbook_for_performance_degradation(self, sample_incident_p1):
        """Test runbook selection for performance degradation."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        runbook_path = classifier.select_runbook(sample_incident_p1)

        assert runbook_path is not None
        assert "performance" in runbook_path.lower()


class TestEscalationDetermination:
    """Test escalation path determination."""

    def test_determine_immediate_escalation(self, sample_incident):
        """Test immediate escalation for critical incidents."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        escalation = classifier.determine_escalation_path(sample_incident)

        assert escalation.immediate_escalation is True
        assert "oncall" in escalation.contacts
        assert "management" in escalation.contacts

    def test_determine_standard_escalation(self, sample_incident_p1):
        """Test standard escalation for high severity incidents."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        escalation = classifier.determine_escalation_path(sample_incident_p1)

        assert escalation.immediate_escalation is False
        assert "dba_team" in escalation.contacts

    def test_escalation_based_on_time_threshold(self, sample_incident_p1):
        """Test escalation based on time threshold."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()

        # Simulate incident exceeding time threshold
        sample_incident_p1["time_elapsed_minutes"] = 90

        escalation = classifier.determine_escalation_path(sample_incident_p1)

        # Should escalate after exceeding RTO threshold
        assert escalation.escalation_level > 1


class TestIncidentClassifierIntegration:
    """Test integration with other systems."""

    def test_classifier_with_monitoring_data(self):
        """Test classifier with real monitoring data."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()

        monitoring_data = {
            "cpu_usage": 95,
            "memory_usage": 88,
            "database_connections": 250,
            "query_latency_p95": 5000,
        }

        incident = classifier.classify_from_monitoring(monitoring_data)

        assert incident is not None
        assert incident.incident_type is not None

    def test_classifier_generates_incident_report(self, sample_incident):
        """Test classifier generates complete incident report."""
        from scripts.change_management.incident.incident_classifier import (
            IncidentClassifier,
        )

        classifier = IncidentClassifier()
        report = classifier.generate_incident_report(sample_incident)

        assert report["incident_type"] is not None
        assert report["severity"] is not None
        assert report["rto_target"] is not None
        assert report["rpo_target"] is not None
        assert "affected_services" in report
        assert "recommended_runbook" in report
