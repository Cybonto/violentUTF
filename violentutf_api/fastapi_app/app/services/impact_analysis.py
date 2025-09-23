# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Impact analysis service for change management and risk assessment."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.db.database import get_db_session
from app.models.dependency import ImpactAnalysisRecord
from app.schemas.dependency import ChangeRequest, ImpactAnalysisResult

logger = logging.getLogger(__name__)


class ImpactAnalysisService:
    """Service for analyzing change impact and generating risk assessments."""

    def __init__(self) -> None:
        """Initialize the impact analysis service."""
        self.risk_factors = {
            "database_schema": 8,
            "critical_service": 7,
            "authentication": 9,
            "configuration": 5,
            "network": 6,
        }

    async def analyze_change_impact(self, change_request: ChangeRequest) -> ImpactAnalysisResult:
        """Analyze the impact of a proposed change."""
        analysis_id = str(uuid.uuid4())

        try:
            # Get affected dependencies
            affected_dependencies = await self._get_affected_dependencies(change_request.affected_components)

            # Calculate risk score
            risk_score = await self._calculate_risk_score(change_request, affected_dependencies)

            # Identify affected services
            affected_services = await self._identify_affected_services(affected_dependencies)

            # Generate rollback plan
            rollback_plan = await self._generate_rollback_plan(change_request, affected_dependencies)

            # Create deployment sequence
            deployment_sequence = await self._create_deployment_sequence(change_request, affected_dependencies)

            # Generate recommendations and warnings
            recommendations = self._generate_recommendations(change_request, risk_score)
            warnings = self._generate_warnings(change_request, affected_dependencies)

            # Determine impact severity
            impact_severity = self._determine_impact_severity(risk_score)

            # Estimate downtime
            estimated_downtime = self._estimate_downtime(change_request, affected_services)

            # Assess rollback complexity
            rollback_complexity = self._assess_rollback_complexity(change_request, affected_dependencies)

            # Store analysis record
            await self._store_impact_analysis(
                analysis_id=analysis_id,
                change_request=change_request,
                risk_score=risk_score,
                affected_services=[dep["source_service"] for dep in affected_dependencies],
                rollback_plan=rollback_plan,
                deployment_sequence=deployment_sequence,
            )

            return ImpactAnalysisResult(
                analysis_id=analysis_id,
                change_request=change_request,
                risk_score=risk_score,
                affected_services=affected_services,
                affected_dependencies=[dep["id"] for dep in affected_dependencies],
                impact_severity=impact_severity,
                estimated_downtime=estimated_downtime,
                rollback_complexity=rollback_complexity,
                rollback_plan=rollback_plan,
                deployment_sequence=deployment_sequence,
                recommendations=recommendations,
                warnings=warnings,
            )

        except Exception as e:
            logger.error("Impact analysis failed for %s: %s", analysis_id, e)
            raise

    async def _get_affected_dependencies(self, affected_components: List[str]) -> List[Dict[str, Any]]:
        """Get dependencies that will be affected by the change."""
        dependencies = []

        for component in affected_components:
            # Query dependencies for this component
            # This is a simplified implementation
            # In practice, this would query the actual dependency relationships
            dependencies.append(
                {
                    "id": str(uuid.uuid4()),
                    "source_service": "violentutf-api",
                    "target_database": component,
                    "dependency_type": "database",
                    "criticality": "critical",
                }
            )

        return dependencies

    async def _calculate_risk_score(
        self, change_request: ChangeRequest, affected_dependencies: List[Dict[str, Any]]
    ) -> int:
        """Calculate risk score for the change (1-10 scale)."""
        base_score = 1

        # Risk based on change type
        change_type_risks = {
            "schema_change": 7,
            "service_change": 5,
            "configuration_change": 3,
            "network_change": 6,
            "security_change": 8,
            "deployment_change": 4,
        }

        base_score += change_type_risks.get(change_request.change_type, 3)

        # Risk based on urgency
        urgency_multipliers = {"critical": 1.5, "high": 1.2, "medium": 1.0, "low": 0.8}

        base_score *= urgency_multipliers.get(change_request.urgency, 1.0)

        # Risk based on affected dependencies
        critical_deps = sum(1 for dep in affected_dependencies if dep.get("criticality") == "critical")
        base_score += critical_deps * 0.5

        # Normalize to 1-10 scale
        risk_score = min(10, max(1, int(base_score)))

        return risk_score

    async def _identify_affected_services(self, dependencies: List[Dict[str, Any]]) -> List[str]:
        """Identify services that will be affected by the change."""
        services = set()

        for dep in dependencies:
            if dep.get("source_service"):
                services.add(dep["source_service"])
            if dep.get("target_service"):
                services.add(dep["target_service"])

        return list(services)

    async def _generate_rollback_plan(
        self, change_request: ChangeRequest, dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate step-by-step rollback plan."""
        rollback_steps = []

        if change_request.change_type == "schema_change":
            rollback_steps = [
                {
                    "step": 1,
                    "action": "Stop application services",
                    "description": "Stop all services that depend on the database",
                    "estimated_time": "2 minutes",
                },
                {
                    "step": 2,
                    "action": "Restore database backup",
                    "description": "Restore database from pre-change backup",
                    "estimated_time": "5-10 minutes",
                },
                {
                    "step": 3,
                    "action": "Restart services",
                    "description": "Restart services in dependency order",
                    "estimated_time": "3 minutes",
                },
                {
                    "step": 4,
                    "action": "Verify functionality",
                    "description": "Run health checks and basic functionality tests",
                    "estimated_time": "5 minutes",
                },
            ]
        elif change_request.change_type == "service_change":
            rollback_steps = [
                {
                    "step": 1,
                    "action": "Deploy previous version",
                    "description": "Redeploy the previous service version",
                    "estimated_time": "3 minutes",
                },
                {
                    "step": 2,
                    "action": "Verify deployment",
                    "description": "Check service health and dependencies",
                    "estimated_time": "2 minutes",
                },
            ]
        else:
            rollback_steps = [
                {
                    "step": 1,
                    "action": "Revert configuration",
                    "description": "Restore previous configuration",
                    "estimated_time": "1 minute",
                }
            ]

        return rollback_steps

    async def _create_deployment_sequence(
        self, change_request: ChangeRequest, dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create optimal deployment sequence considering dependencies."""
        sequence = []

        if change_request.change_type == "schema_change":
            sequence = [
                {
                    "step": 1,
                    "action": "Create database backup",
                    "description": "Create full backup of affected databases",
                    "estimated_time": "5 minutes",
                },
                {
                    "step": 2,
                    "action": "Stop dependent services",
                    "description": "Gracefully stop services that use the database",
                    "estimated_time": "2 minutes",
                },
                {
                    "step": 3,
                    "action": "Apply schema changes",
                    "description": "Execute database migrations",
                    "estimated_time": "3-5 minutes",
                },
                {
                    "step": 4,
                    "action": "Start services",
                    "description": "Restart services in dependency order",
                    "estimated_time": "3 minutes",
                },
                {
                    "step": 5,
                    "action": "Verify deployment",
                    "description": "Run comprehensive health checks",
                    "estimated_time": "5 minutes",
                },
            ]
        else:
            sequence = [
                {
                    "step": 1,
                    "action": "Apply changes",
                    "description": f"Apply {change_request.change_type}",
                    "estimated_time": "2-3 minutes",
                },
                {
                    "step": 2,
                    "action": "Verify changes",
                    "description": "Verify changes are working correctly",
                    "estimated_time": "2 minutes",
                },
            ]

        return sequence

    def _generate_recommendations(self, change_request: ChangeRequest, risk_score: int) -> List[str]:
        """Generate implementation recommendations based on risk assessment."""
        recommendations = []

        if risk_score >= 8:
            recommendations.extend(
                [
                    "Schedule during maintenance window",
                    "Have senior engineer available during deployment",
                    "Prepare detailed communication plan",
                    "Consider blue-green deployment strategy",
                ]
            )
        elif risk_score >= 6:
            recommendations.extend(
                [
                    "Schedule during low-traffic period",
                    "Ensure backup procedures are tested",
                    "Have rollback plan readily available",
                ]
            )
        else:
            recommendations.extend(
                ["Can be deployed during business hours", "Standard monitoring procedures sufficient"]
            )

        if change_request.change_type == "schema_change":
            recommendations.extend(
                [
                    "Test migrations on staging environment first",
                    "Verify backup and restore procedures",
                    "Plan for potential data migration time",
                ]
            )

        return recommendations

    def _generate_warnings(self, change_request: ChangeRequest, dependencies: List[Dict[str, Any]]) -> List[str]:
        """Generate warnings about potential issues."""
        warnings = []

        critical_deps = [dep for dep in dependencies if dep.get("criticality") == "critical"]
        if critical_deps:
            warnings.append(f"Change affects {len(critical_deps)} critical dependencies")

        if change_request.urgency == "critical":
            warnings.append("Critical urgency may limit testing time")

        if change_request.change_type == "schema_change":
            warnings.append("Database schema changes may require extended downtime")

        return warnings

    def _determine_impact_severity(self, risk_score: int) -> str:
        """Determine impact severity level."""
        if risk_score >= 8:
            return "high"
        elif risk_score >= 5:
            return "medium"
        else:
            return "low"

    def _estimate_downtime(self, change_request: ChangeRequest, affected_services: List[str]) -> Optional[str]:
        """Estimate potential downtime."""
        if change_request.change_type == "schema_change":
            return "10-20 minutes"
        elif change_request.change_type == "service_change" and len(affected_services) > 2:
            return "5-10 minutes"
        elif len(affected_services) > 0:
            return "2-5 minutes"
        else:
            return None

    def _assess_rollback_complexity(self, change_request: ChangeRequest, dependencies: List[Dict[str, Any]]) -> str:
        """Assess rollback complexity level."""
        if change_request.change_type == "schema_change":
            return "high"
        elif len(dependencies) > 5:
            return "medium"
        else:
            return "low"

    async def _store_impact_analysis(
        self,
        analysis_id: str,
        change_request: ChangeRequest,
        risk_score: int,
        affected_services: List[str],
        rollback_plan: List[Dict[str, Any]],
        deployment_sequence: List[Dict[str, Any]],
    ) -> None:
        """Store impact analysis record in database."""
        async with get_db_session() as session:
            analysis_record = ImpactAnalysisRecord(
                id=analysis_id,
                change_description=change_request.change_description,
                proposed_changes=json.dumps(change_request.proposed_changes),
                impact_assessment=json.dumps({"affected_services": affected_services, "risk_score": risk_score}),
                risk_score=risk_score,
                affected_services=json.dumps(affected_services),
                rollback_plan=json.dumps(rollback_plan),
                deployment_sequence=json.dumps(deployment_sequence),
                created_by=change_request.requestor,
                implemented=False,
            )

            session.add(analysis_record)
            await session.commit()
