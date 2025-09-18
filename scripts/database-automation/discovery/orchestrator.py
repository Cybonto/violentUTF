# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Discovery orchestrator that coordinates all discovery modules and generates reports.

Main entry point for the database discovery system.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .code_discovery import CodeDiscovery
from .container_discovery import ContainerDiscovery
from .exceptions import DiscoveryError
from .filesystem_discovery import FilesystemDiscovery
from .models import ConfidenceLevel, DatabaseDiscovery, DatabaseType, DiscoveryConfig, DiscoveryReport
from .network_discovery import NetworkDiscovery
from .security_scanner import SecurityScanner
from .utils import create_report_directory, measure_execution_time, setup_logging


class DiscoveryOrchestrator:
    """Main orchestrator for database discovery operations."""

    def __init__(self, config: Optional[DiscoveryConfig] = None) -> None:
        """Initialize the discovery orchestrator with optional configuration."""
        self.config = config or DiscoveryConfig()
        self.logger = setup_logging("discovery_orchestrator")

        # Initialize discovery modules
        self.container_discovery = ContainerDiscovery(self.config)
        self.network_discovery = NetworkDiscovery(self.config)
        self.filesystem_discovery = FilesystemDiscovery(self.config)
        self.code_discovery = CodeDiscovery(self.config)
        self.security_scanner = SecurityScanner(self.config)

        # Performance tracking
        self.start_time = None
        self.end_time = None
        self.module_timings = {}

    @measure_execution_time
    def execute_full_discovery(self) -> DiscoveryReport:
        """
        Execute complete database discovery process across all modules.

        Returns:
            Comprehensive discovery report
        """
        self.start_time = time.time()
        self.logger.info("Starting full database discovery process")

        try:
            # Execute discovery modules
            all_discoveries = []

            if self.config.enable_parallel_processing:
                all_discoveries = self._execute_parallel_discovery()
            else:
                all_discoveries = self._execute_sequential_discovery()

            # Cross-validate and deduplicate discoveries
            validated_discoveries = self._cross_validate_discoveries(all_discoveries)

            # Apply security scanning
            if self.config.enable_security_scanning:
                validated_discoveries = self.security_scanner.scan_for_database_secrets(validated_discoveries)
                validated_discoveries = self.security_scanner.validate_discovered_credentials(validated_discoveries)

            # Generate comprehensive report
            report = self._generate_discovery_report(validated_discoveries)

            self.end_time = time.time()
            execution_time = self.end_time - self.start_time
            report.execution_time_seconds = execution_time

            self.logger.info(
                "Discovery completed in %.2f seconds. Found %d databases.", execution_time, len(validated_discoveries)
            )

            return report

        except Exception as e:
            self.logger.error("Discovery process failed: %s", e)
            raise DiscoveryError(f"Full discovery execution failed: {e}") from e

    def _execute_parallel_discovery(self) -> List[DatabaseDiscovery]:
        """Execute discovery modules in parallel."""
        all_discoveries = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit discovery tasks
            future_to_module = {}

            if self.config.enable_container_discovery:
                future_to_module[executor.submit(self._run_container_discovery)] = "container"

            if self.config.enable_network_discovery:
                future_to_module[executor.submit(self._run_network_discovery)] = "network"

            if self.config.enable_filesystem_discovery:
                future_to_module[executor.submit(self._run_filesystem_discovery)] = "filesystem"

            if self.config.enable_code_discovery:
                future_to_module[executor.submit(self._run_code_discovery)] = "code"

            # Collect results
            for future in as_completed(future_to_module, timeout=self.config.max_execution_time_seconds):
                module_name = future_to_module[future]
                try:
                    discoveries = future.result()
                    all_discoveries.extend(discoveries)
                    self.logger.info("Completed %s discovery: %d found", module_name, len(discoveries))

                except Exception as e:
                    self.logger.error("Error in %s discovery: %s", module_name, e)
                    continue

        return all_discoveries

    def _execute_sequential_discovery(self) -> List[DatabaseDiscovery]:
        """Execute discovery modules sequentially."""
        all_discoveries = []

        # Container discovery
        if self.config.enable_container_discovery:
            discoveries = self._run_container_discovery()
            all_discoveries.extend(discoveries)

        # Network discovery
        if self.config.enable_network_discovery:
            discoveries = self._run_network_discovery()
            all_discoveries.extend(discoveries)

        # Filesystem discovery
        if self.config.enable_filesystem_discovery:
            discoveries = self._run_filesystem_discovery()
            all_discoveries.extend(discoveries)

        # Code discovery
        if self.config.enable_code_discovery:
            discoveries = self._run_code_discovery()
            all_discoveries.extend(discoveries)

        return all_discoveries

    def _run_container_discovery(self) -> List[DatabaseDiscovery]:
        """Run container discovery with timing."""
        start_time = time.time()
        try:
            # Discover running containers
            container_discoveries = self.container_discovery.discover_containers()

            # Discover from compose files
            compose_discoveries = self.container_discovery.discover_compose_files()

            all_discoveries = container_discoveries + compose_discoveries

            self.module_timings["container"] = time.time() - start_time
            self.logger.info("Container discovery found %d databases", len(all_discoveries))

            return all_discoveries

        except Exception as e:
            self.module_timings["container"] = time.time() - start_time
            self.logger.error("Container discovery failed: %s", e)
            return []

    def _run_network_discovery(self) -> List[DatabaseDiscovery]:
        """Run network discovery with timing."""
        start_time = time.time()
        try:
            # General network discovery
            network_discoveries = self.network_discovery.discover_network_databases()

            # ViolentUTF-specific localhost discovery
            localhost_discoveries = self.network_discovery.discover_localhost_services()

            # Combine and deduplicate
            all_discoveries = network_discoveries + localhost_discoveries
            # pylint: disable=protected-access
            unique_discoveries = self.network_discovery._deduplicate_discoveries(all_discoveries)

            self.module_timings["network"] = time.time() - start_time
            self.logger.info("Network discovery found %d databases", len(unique_discoveries))

            return unique_discoveries

        except Exception as e:
            self.module_timings["network"] = time.time() - start_time
            self.logger.error("Network discovery failed: %s", e)
            return []

    def _run_filesystem_discovery(self) -> List[DatabaseDiscovery]:
        """Run filesystem discovery with timing."""
        start_time = time.time()
        try:
            # Database file discovery
            file_discoveries = self.filesystem_discovery.discover_database_files()

            # Configuration file discovery
            config_discoveries = self.filesystem_discovery.discover_configuration_files()

            all_discoveries = file_discoveries + config_discoveries

            self.module_timings["filesystem"] = time.time() - start_time
            self.logger.info("Filesystem discovery found %d databases", len(all_discoveries))

            return all_discoveries

        except Exception as e:
            self.module_timings["filesystem"] = time.time() - start_time
            self.logger.error("Filesystem discovery failed: %s", e)
            return []

    def _run_code_discovery(self) -> List[DatabaseDiscovery]:
        """Run code discovery with timing."""
        start_time = time.time()
        try:
            # Python code analysis
            code_discoveries = self.code_discovery.discover_code_databases()

            # Requirements file analysis
            req_discoveries = self.code_discovery.analyze_requirements_files()

            all_discoveries = code_discoveries + req_discoveries

            self.module_timings["code"] = time.time() - start_time
            self.logger.info("Code discovery found %d databases", len(all_discoveries))

            return all_discoveries

        except Exception as e:
            self.module_timings["code"] = time.time() - start_time
            self.logger.error("Code discovery failed: %s", e)
            return []

    def _cross_validate_discoveries(self, discoveries: List[DatabaseDiscovery]) -> List[DatabaseDiscovery]:
        """
        Cross-validate discoveries and improve confidence scores.

        Args:
            discoveries: Raw discoveries from all modules

        Returns:
            Validated and deduplicated discoveries
        """
        self.logger.info("Cross-validating discoveries")

        # Group similar discoveries
        discovery_groups = self._group_similar_discoveries(discoveries)

        # Merge and validate each group
        validated_discoveries = []
        for group in discovery_groups:
            merged_discovery = self._merge_discovery_group(group)
            if merged_discovery:
                validated_discoveries.append(merged_discovery)

        # Validate each discovery
        for discovery in validated_discoveries:
            self._validate_discovery(discovery)

        self.logger.info("Cross-validation completed: %d validated databases", len(validated_discoveries))
        return validated_discoveries

    def _group_similar_discoveries(self, discoveries: List[DatabaseDiscovery]) -> List[List[DatabaseDiscovery]]:
        """Group similar discoveries for merging."""
        groups = []
        processed = set()

        for i, discovery in enumerate(discoveries):
            if i in processed:
                continue

            # Start a new group
            group = [discovery]
            processed.add(i)

            # Find similar discoveries
            for j, other_discovery in enumerate(discoveries):
                if j in processed or i == j:
                    continue

                if self._are_discoveries_similar(discovery, other_discovery):
                    group.append(other_discovery)
                    processed.add(j)

            groups.append(group)

        return groups

    def _are_discoveries_similar(self, discovery1: DatabaseDiscovery, discovery2: DatabaseDiscovery) -> bool:
        """Check if two discoveries refer to the same database."""
        # Same database type is required
        if discovery1.database_type != discovery2.database_type:
            return False

        # Check for matching connection details
        if discovery1.host and discovery2.host:
            if discovery1.host == discovery2.host and discovery1.port == discovery2.port:
                return True

        # Check for matching file paths
        if discovery1.file_path and discovery2.file_path:
            path1 = Path(discovery1.file_path).resolve()
            path2 = Path(discovery2.file_path).resolve()
            if path1 == path2:
                return True

        # Check for matching connection strings
        if discovery1.connection_string and discovery2.connection_string:
            if discovery1.connection_string == discovery2.connection_string:
                return True

        # Check for overlapping database files
        if discovery1.database_files and discovery2.database_files:
            files1 = {Path(f.file_path).resolve() for f in discovery1.database_files}
            files2 = {Path(f.file_path).resolve() for f in discovery2.database_files}
            if files1 & files2:  # Intersection
                return True

        return False

    def _merge_discovery_group(self, group: List[DatabaseDiscovery]) -> Optional[DatabaseDiscovery]:
        """Merge a group of similar discoveries into a single discovery."""
        if not group:
            return None

        if len(group) == 1:
            return group[0]

        # Use the discovery with highest confidence as the base
        base_discovery = max(group, key=lambda d: d.confidence_score)

        # Merge information from all discoveries
        merged_discovery = DatabaseDiscovery(
            database_id=base_discovery.database_id,
            database_type=base_discovery.database_type,
            name=base_discovery.name,
            description=f"Merged from {len(group)} discovery methods",
            host=base_discovery.host,
            port=base_discovery.port,
            file_path=base_discovery.file_path,
            connection_string=base_discovery.connection_string,
            discovery_method=base_discovery.discovery_method,
            confidence_level=base_discovery.confidence_level,
            confidence_score=base_discovery.confidence_score,
            discovered_at=min(d.discovered_at for d in group),
            version=base_discovery.version,
            size_mb=base_discovery.size_mb,
            is_active=any(d.is_active for d in group),
            is_accessible=all(d.is_accessible for d in group),
            is_validated=False,  # Will be validated later
        )

        # Merge container info (use first available)
        for discovery in group:
            if discovery.container_info and not merged_discovery.container_info:
                merged_discovery.container_info = discovery.container_info
                break

        # Merge network service (use first available)
        for discovery in group:
            if discovery.network_service and not merged_discovery.network_service:
                merged_discovery.network_service = discovery.network_service
                break

        # Merge database files
        all_files = []
        for discovery in group:
            all_files.extend(discovery.database_files)
        merged_discovery.database_files = list({f.file_path: f for f in all_files}.values())

        # Merge code references
        all_code_refs = []
        for discovery in group:
            all_code_refs.extend(discovery.code_references)
        merged_discovery.code_references = all_code_refs

        # Merge security findings
        all_security_findings = []
        for discovery in group:
            all_security_findings.extend(discovery.security_findings)
        merged_discovery.security_findings = all_security_findings

        # Merge tags
        all_tags = set()
        for discovery in group:
            all_tags.update(discovery.tags)
        all_tags.add("merged")
        merged_discovery.tags = list(all_tags)

        # Merge custom properties
        merged_properties = {}
        for discovery in group:
            merged_properties.update(discovery.custom_properties)
        merged_properties["merged_from_count"] = len(group)
        merged_properties["discovery_methods"] = [d.discovery_method.value for d in group]
        merged_discovery.custom_properties = merged_properties

        # Recalculate confidence score based on multiple detections
        detection_methods = [d.discovery_method.value for d in group]
        validation_results = {
            "multiple_methods": len(set(detection_methods)) > 1,
            "high_confidence_sources": sum(1 for d in group if d.confidence_level == ConfidenceLevel.HIGH) > 0,
            "consensus": len(group) >= 2,
        }

        from .utils import calculate_confidence_score

        confidence_score, confidence_level = calculate_confidence_score(
            detection_methods, validation_results, consistency_score=1.0
        )

        merged_discovery.confidence_score = confidence_score
        merged_discovery.confidence_level = confidence_level

        return merged_discovery

    def _validate_discovery(self, discovery: DatabaseDiscovery) -> None:
        """Validate a discovery and update validation status."""
        validation_errors = []

        try:
            # Validate basic requirements
            if not discovery.database_type or discovery.database_type == DatabaseType.UNKNOWN:
                validation_errors.append("Unknown database type")

            # Validate connection details
            if not any([discovery.host, discovery.file_path, discovery.connection_string]):
                validation_errors.append("No connection information available")

            # Validate file-based databases
            if discovery.file_path:
                if not Path(discovery.file_path).exists():
                    validation_errors.append("Database file not found: %s" % discovery.file_path)
                    discovery.is_accessible = False

            # Validate network-based databases
            if discovery.host and discovery.port:
                # Test connectivity for network databases
                if hasattr(self.network_discovery, "test_database_connectivity"):
                    is_accessible = self.network_discovery.test_database_connectivity(discovery)
                    discovery.is_accessible = is_accessible
                    if not is_accessible:
                        validation_errors.append("Cannot connect to %s:%d" % (discovery.host, discovery.port))

            # Update validation status
            discovery.validation_errors = validation_errors
            discovery.is_validated = len(validation_errors) == 0

        except Exception as e:
            validation_errors.append("Validation error: %s" % e)
            discovery.validation_errors = validation_errors
            discovery.is_validated = False

    def _generate_discovery_report(self, discoveries: List[DatabaseDiscovery]) -> DiscoveryReport:
        """Generate comprehensive discovery report."""
        # Create report
        report = DiscoveryReport(
            report_id=f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            databases=discoveries,
            total_discoveries=len(discoveries),
        )

        # Calculate statistics
        report.type_counts = {}
        report.method_counts = {}
        report.confidence_distribution = {}

        for discovery in discoveries:
            # Type counts
            db_type = discovery.database_type
            report.type_counts[db_type] = report.type_counts.get(db_type, 0) + 1

            # Method counts
            method = discovery.discovery_method
            report.method_counts[method] = report.method_counts.get(method, 0) + 1

            # Confidence distribution
            confidence = discovery.confidence_level
            report.confidence_distribution[confidence] = report.confidence_distribution.get(confidence, 0) + 1

        # Performance metrics
        report.processing_stats = self.module_timings.copy()

        # Scan targets
        report.scan_targets = {
            "paths_scanned": len(self.config.scan_paths),
            "containers_checked": (
                len(self.container_discovery.database_images)
                if hasattr(self.container_discovery, "database_images")
                else 0
            ),
            "ports_scanned": len(self.config.database_ports),
            "file_extensions": len(self.config.file_extensions),
        }

        # Security summary
        report.security_findings_count = sum(len(d.security_findings) for d in discoveries)
        report.credential_exposures = sum(
            1 for d in discoveries for finding in d.security_findings if finding.finding_type == "credential"
        )
        report.high_severity_findings = sum(
            1 for d in discoveries for finding in d.security_findings if finding.severity == "high"
        )

        # Validation summary
        report.validated_discoveries = sum(1 for d in discoveries if d.is_validated)
        report.validation_errors = sum(len(d.validation_errors) for d in discoveries)

        # Configuration
        report.configuration = {
            "parallel_processing": self.config.enable_parallel_processing,
            "security_scanning": self.config.enable_security_scanning,
            "max_workers": self.config.max_workers,
            "timeout_seconds": self.config.max_execution_time_seconds,
        }

        # Discovery scope
        report.discovery_scope = [
            f"Container discovery: {'enabled' if self.config.enable_container_discovery else 'disabled'}",
            f"Network discovery: {'enabled' if self.config.enable_network_discovery else 'disabled'}",
            f"Filesystem discovery: {'enabled' if self.config.enable_filesystem_discovery else 'disabled'}",
            f"Code discovery: {'enabled' if self.config.enable_code_discovery else 'disabled'}",
            f"Security scanning: {'enabled' if self.config.enable_security_scanning else 'disabled'}",
        ]

        return report

    def save_report(self, report: DiscoveryReport, output_dir: Optional[str] = None) -> Path:
        """
        Save discovery report to files.

        Args:
            report: Discovery report to save
            output_dir: Output directory (default: creates timestamped directory)

        Returns:
            Path to the saved report directory
        """
        try:
            # Create output directory
            if output_dir:
                report_dir = Path(output_dir)
                report_dir.mkdir(parents=True, exist_ok=True)
            else:
                report_dir = create_report_directory()

            # Save JSON report
            json_file = report_dir / f"{report.report_id}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(report.to_json())

            # Save summary report
            summary_file = report_dir / f"{report.report_id}_summary.md"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(self._generate_markdown_summary(report))

            # Save detailed findings
            if report.databases:
                detailed_file = report_dir / f"{report.report_id}_detailed.md"
                with open(detailed_file, "w", encoding="utf-8") as f:
                    f.write(self._generate_detailed_markdown(report))

            self.logger.info("Report saved to: %s", report_dir)
            return report_dir

        except Exception as e:
            self.logger.error("Failed to save report: %s", e)
            raise DiscoveryError(f"Report saving failed: {e}") from e

    def _generate_markdown_summary(self, report: DiscoveryReport) -> str:
        """Generate markdown summary report."""
        summary_stats = report.get_summary_stats()

        md = f"""# Database Discovery Report Summary

**Report ID:** {report.report_id}
**Generated:** {report.generated_at.isoformat()}
**Execution Time:** {report.execution_time_seconds:.2f} seconds

## Summary Statistics

- **Total Databases Found:** {summary_stats['total_databases']}
- **Active Databases:** {summary_stats['active_databases']}
- **High Confidence:** {summary_stats['high_confidence']}
- **Security Findings:** {summary_stats['security_findings']}
- **Validation Rate:** {summary_stats['validation_rate']:.1f}%

## Database Types

"""

        for db_type, count in report.type_counts.items():
            md += f"- **{db_type.value.title()}:** {count}\n"

        md += "\n## Discovery Methods\n\n"

        for method, count in report.method_counts.items():
            md += f"- **{method.value.replace('_', ' ').title()}:** {count}\n"

        md += "\n## Confidence Distribution\n\n"

        for confidence, count in report.confidence_distribution.items():
            md += f"- **{confidence.value.title()}:** {count}\n"

        if report.security_findings_count > 0:
            md += "\n## Security Summary\n\n"
            md += f"- **Total Security Findings:** {report.security_findings_count}\n"
            md += f"- **Credential Exposures:** {report.credential_exposures}\n"
            md += f"- **High Severity:** {report.high_severity_findings}\n"

        return md

    def _generate_detailed_markdown(self, report: DiscoveryReport) -> str:
        """Generate detailed markdown report."""
        md = f"""# Detailed Database Discovery Report

**Report ID:** {report.report_id}
**Generated:** {report.generated_at.isoformat()}

## Discovered Databases

"""

        for i, discovery in enumerate(report.databases, 1):
            md += f"### {i}. {discovery.name}\n\n"
            md += f"- **Type:** {discovery.database_type.value}\n"
            md += f"- **Method:** {discovery.discovery_method.value}\n"
            md += f"- **Confidence:** {discovery.confidence_level.value} ({discovery.confidence_score:.2f})\n"
            md += f"- **Active:** {'Yes' if discovery.is_active else 'No'}\n"
            md += f"- **Validated:** {'Yes' if discovery.is_validated else 'No'}\n"

            if discovery.host:
                md += f"- **Host:** {discovery.host}\n"
            if discovery.port:
                md += f"- **Port:** {discovery.port}\n"
            if discovery.file_path:
                md += f"- **File:** {discovery.file_path}\n"

            if discovery.security_findings:
                md += f"- **Security Findings:** {len(discovery.security_findings)}\n"
                for finding in discovery.security_findings:
                    md += f"  - {finding.severity.upper()}: {finding.description}\n"

            if discovery.tags:
                md += f"- **Tags:** {', '.join(discovery.tags)}\n"

            md += "\n"

        return md
