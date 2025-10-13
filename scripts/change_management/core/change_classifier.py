# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Change Classification System.

Classifies database changes by type, assesses risk and impact,
and determines approval requirements based on classification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Union


class ChangeType(Enum):
    """Types of database changes."""

    EMERGENCY = "emergency"  # Immediate, post-review
    STANDARD = "standard"  # Pre-approved, automated
    NORMAL = "normal"  # Standard approval workflow
    MAJOR = "major"  # Extended review, architecture impact


class RiskLevel(Enum):
    """Risk levels for changes."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactLevel(Enum):
    """Impact levels for changes."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImpactAssessment:
    """Impact assessment result."""

    impact_level: ImpactLevel
    affected_databases: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)
    user_impact: str = ""
    downtime_required: bool = False
    estimated_downtime_minutes: int = 0


@dataclass
class DependencyAnalysis:
    """Dependency analysis result."""

    services: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    configurations: List[str] = field(default_factory=list)
    circular_dependencies: bool = False
    conflicts_detected: bool = False
    conflict_details: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Change request validation result."""

    valid: bool
    missing_fields: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> Union[bool, List[str], Dict[str, str]]:
        """Support dictionary-style access for backward compatibility."""
        return getattr(self, key)


class ChangeClassifier:
    """Classifies database changes and assesses their risk and impact."""

    VALID_DATABASES = ["postgresql", "sqlite", "multiple", "none"]
    VALID_CHANGE_TYPES = [ct.value for ct in ChangeType]

    def __init__(self) -> None:
        """Initialize the change classifier."""
        self.classification_rules = self._load_classification_rules()

    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load classification rules and thresholds."""
        return {
            "emergency_indicators": [
                "hotfix_required",
                "production_down",
                "security_breach",
                "data_loss",
            ],
            "major_indicators": [
                "adr_required",
                "architecture_change",
                "multiple_databases",
                "breaking_change",
            ],
            "risk_factors": {
                "database_count": {"1": "low", "2-3": "medium", ">3": "high"},
                "rollback_available": {"true": -1, "false": 2},
                "tested": {"true": -1, "false": 1},
            },
        }

    def classify_change(self, change_request: Dict[str, Any]) -> ChangeType:
        """
        Classify a change request by type.

        Args:
            change_request: Change request data

        Returns:
            ChangeType enum value
        """
        # Check for explicit change_type first
        if "change_type" in change_request:
            type_str = change_request["change_type"].lower()
            if type_str in self.VALID_CHANGE_TYPES:
                return ChangeType(type_str)

        # Classify based on indicators
        if self._is_emergency_change(change_request):
            return ChangeType.EMERGENCY

        if self._is_major_change(change_request):
            return ChangeType.MAJOR

        if self._is_standard_change(change_request):
            return ChangeType.STANDARD

        # Default to normal
        return ChangeType.NORMAL

    def _is_emergency_change(self, change_request: Dict[str, Any]) -> bool:
        """Check if change is emergency."""
        for indicator in self.classification_rules["emergency_indicators"]:
            if change_request.get(indicator) is True:
                return True
        return False

    def _is_major_change(self, change_request: Dict[str, Any]) -> bool:
        """Check if change is major."""
        for indicator in self.classification_rules["major_indicators"]:
            if change_request.get(indicator) is True:
                return True

        # Check database scope
        if change_request.get("database") == "multiple":
            return True

        # Check impact scope
        impact_scope = change_request.get("impact_scope", [])
        if len(impact_scope) > 3:
            return True

        return False

    def _is_standard_change(self, change_request: Dict[str, Any]) -> bool:
        """Check if change is standard (pre-approved)."""
        return change_request.get("pre_approved", False) is True

    def assess_risk(self, change_request: Dict[str, Any]) -> RiskLevel:
        """
        Assess the risk level of a change.

        Args:
            change_request: Change request data

        Returns:
            RiskLevel enum value
        """
        risk_score = 0

        # Emergency changes are always critical risk
        if self._is_emergency_change(change_request):
            return RiskLevel.CRITICAL

        # Check risk_level if explicitly provided
        if "risk_level" in change_request:
            risk_str = change_request["risk_level"].lower()
            return RiskLevel(risk_str)

        # Calculate risk score based on factors
        # Database scope
        database = change_request.get("database", "")
        if database == "multiple":
            risk_score += 3
        elif database in ["postgresql", "sqlite"]:
            risk_score += 1

        # Impact scope
        impact_scope = change_request.get("impact_scope", [])
        risk_score += len(impact_scope)

        # Rollback availability
        if not change_request.get("rollback_available", True):
            risk_score += 2

        # Testing status
        if not change_request.get("tested", False):
            risk_score += 1

        # Production impact
        if change_request.get("production_impact", False):
            risk_score += 2

        # Convert score to risk level
        if risk_score >= 8:
            return RiskLevel.CRITICAL
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def assess_impact(self, change_request: Dict[str, Any]) -> ImpactAssessment:
        """
        Assess the impact of a change.

        Args:
            change_request: Change request data

        Returns:
            ImpactAssessment object
        """
        impact_scope = change_request.get("impact_scope", [])
        database = change_request.get("database", "")

        # Determine affected databases
        affected_databases = []
        if database == "multiple":
            affected_databases = ["postgresql", "sqlite"]
        elif database in ["postgresql", "sqlite"]:
            affected_databases = [database]

        # Determine affected services
        affected_services = impact_scope.copy() if isinstance(impact_scope, list) else []

        # Calculate impact level
        impact_level = self._calculate_impact_level(len(affected_databases), len(affected_services))

        # Determine if downtime is required
        downtime_required = change_request.get("downtime_required", False)
        estimated_downtime = change_request.get("estimated_downtime_minutes", 0)

        return ImpactAssessment(
            impact_level=impact_level,
            affected_databases=affected_databases,
            affected_services=affected_services,
            downtime_required=downtime_required,
            estimated_downtime_minutes=estimated_downtime,
        )

    def _calculate_impact_level(self, database_count: int, service_count: int) -> ImpactLevel:
        """Calculate impact level based on affected resources."""
        total_impact = database_count + service_count

        if total_impact >= 6:
            return ImpactLevel.CRITICAL
        elif total_impact >= 4:
            return ImpactLevel.HIGH
        elif total_impact >= 2:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW

    def determine_approval_requirements(
        self,
        change_type: ChangeType,
        risk_level: RiskLevel,
        impact_level: ImpactLevel,
        approval_matrix: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Determine approval requirements based on classification.

        Args:
            change_type: Type of change
            risk_level: Risk level
            impact_level: Impact level
            approval_matrix: Approval matrix configuration

        Returns:
            Dict with approval requirements
        """
        change_type_str = change_type.value
        requirements = approval_matrix.get(change_type_str, {}).copy()

        # Add calculated risk and impact
        requirements["risk_level"] = risk_level.value
        requirements["impact_level"] = impact_level.value

        return requirements

    def analyze_dependencies(self, change_request: Dict[str, Any]) -> DependencyAnalysis:
        """
        Analyze dependencies affected by the change.

        Args:
            change_request: Change request data

        Returns:
            DependencyAnalysis object
        """
        analysis = DependencyAnalysis()

        # Extract service dependencies
        impact_scope = change_request.get("impact_scope", [])
        if isinstance(impact_scope, list):
            analysis.services = impact_scope.copy()

        # Extract database dependencies
        database = change_request.get("database", "")
        if database == "multiple":
            analysis.databases = ["postgresql", "sqlite"]
        elif database in ["postgresql", "sqlite"]:
            analysis.databases = [database]

        # Extract configuration dependencies
        config_files = change_request.get("config_files", [])
        if isinstance(config_files, list):
            analysis.configurations = config_files.copy()

        # Check for circular dependencies
        dependencies_list = change_request.get("dependencies", [])
        if self._has_circular_dependencies(dependencies_list):
            analysis.circular_dependencies = True

        # Check for conflicts
        conflicts = self._detect_conflicts(dependencies_list)
        if conflicts:
            analysis.conflicts_detected = True
            analysis.conflict_details = conflicts

        return analysis

    def _has_circular_dependencies(self, dependencies: List[Dict[str, Any]]) -> bool:
        """Check for circular dependencies."""
        if not dependencies:
            return False

        # Build dependency graph
        graph = {}
        for dep in dependencies:
            service = dep.get("service")
            depends_on = dep.get("depends_on", [])
            if service:
                graph[service] = depends_on

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True

        return False

    def _detect_conflicts(self, dependencies: List[Dict[str, Any]]) -> List[str]:
        """Detect version conflicts in dependencies."""
        conflicts = []

        if not dependencies:
            return conflicts

        # Track required versions
        version_requirements = {}

        for dep in dependencies:
            library = dep.get("library")
            if not library:
                continue

            required_version = dep.get("required_version")
            if required_version:
                if library in version_requirements:
                    if version_requirements[library] != required_version:
                        conflicts.append(
                            f"Version conflict for {library}: " f"{version_requirements[library]} vs {required_version}"
                        )
                else:
                    version_requirements[library] = required_version

            # Check transitive dependencies
            requires = dep.get("requires", {})
            for req_lib, req_ver in requires.items():
                if req_lib in version_requirements:
                    if not self._version_compatible(version_requirements[req_lib], req_ver):
                        conflicts.append(
                            f"Transitive conflict for {req_lib}: " f"{version_requirements[req_lib]} vs {req_ver}"
                        )

        return conflicts

    def _version_compatible(self, version1: str, version2: str) -> bool:
        """Check if two version requirements are compatible."""
        # Simplified version compatibility check
        # In production, use packaging.specifiers
        if version1 == version2:
            return True

        # Handle >= comparisons
        if ">=" in version2:
            return True

        return False

    def validate_change_request(self, change_request: Dict[str, Any]) -> ValidationResult:
        """
        Validate a change request.

        Args:
            change_request: Change request to validate

        Returns:
            ValidationResult object
        """
        result = ValidationResult(valid=True)

        # Check required fields
        required_fields = ["title", "description", "change_type", "database"]
        for req_field in required_fields:
            if req_field not in change_request:
                result.missing_fields.append(req_field)
                result.valid = False

        if not result.missing_fields:
            # Validate change_type
            change_type = change_request.get("change_type", "").lower()
            if change_type not in self.VALID_CHANGE_TYPES:
                result.errors["change_type"] = f"Invalid change type. Must be one of: {self.VALID_CHANGE_TYPES}"
                result.valid = False

            # Validate database
            database = change_request.get("database", "").lower()
            if database not in self.VALID_DATABASES:
                result.errors["database"] = f"Invalid database. Must be one of: {self.VALID_DATABASES}"
                result.valid = False

            # Check impact_scope format
            impact_scope = change_request.get("impact_scope")
            if impact_scope is not None and not isinstance(impact_scope, list):
                result.errors["impact_scope"] = "impact_scope must be a list"
                result.valid = False

        return result
