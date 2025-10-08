#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Setup Performance Monitoring Infrastructure.

Issue #270 - Automated deployment of Prometheus/Grafana/AlertManager stack

This script automates the deployment of the complete monitoring infrastructure
for ViolentUTF database performance monitoring.

Usage:
    python3 setup_performance_monitoring.py [--dry-run] [--validate] [--cleanup]
"""

import argparse
import json
import logging
import subprocess  # nosec B404
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


class MonitoringSetup:
    """Automated monitoring infrastructure setup and deployment."""

    def __init__(self, dry_run: bool = False) -> None:
        """
        Initialize monitoring setup.

        Args:
            dry_run: If True, show planned actions without executing them
        """
        self.dry_run = dry_run
        self.required_dirs = [
            PROJECT_ROOT / "configs" / "monitoring",
            PROJECT_ROOT / "dashboards",
            PROJECT_ROOT / "scripts" / "monitoring-setup",
        ]
        self.docker_compose_file = PROJECT_ROOT / "docker-compose.monitoring.yml"

    def validate_prerequisites(self) -> Tuple[bool, List[str]]:
        """
        Validate that all prerequisites are met.

        Returns:
            Tuple of (success, list of error messages)
        """
        errors = []

        # Check Docker availability
        try:
            result = subprocess.run(  # nosec B603 B607
                ["docker", "--version"], capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                errors.append("Docker is not available")
        except FileNotFoundError:
            errors.append("Docker is not installed")

        # Check Docker Compose availability
        try:
            result = subprocess.run(  # nosec B603 B607
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                errors.append("Docker Compose is not available")
        except FileNotFoundError:
            errors.append("Docker Compose is not installed")

        # Check required configuration files exist
        required_configs = [
            PROJECT_ROOT / "configs" / "monitoring" / "prometheus.yml",
            PROJECT_ROOT / "configs" / "monitoring" / "alertmanager.yml",
            PROJECT_ROOT / "configs" / "monitoring" / "alert_rules.yaml",
            PROJECT_ROOT / "configs" / "monitoring" / "grafana-datasources.yml",
            PROJECT_ROOT / "configs" / "monitoring" / "grafana-dashboards.yml",
        ]

        for config_file in required_configs:
            if not config_file.exists():
                errors.append(f"Required config file not found: {config_file}")

        # Check docker-compose.monitoring.yml exists
        if not self.docker_compose_file.exists():
            errors.append(f"Docker Compose file not found: {self.docker_compose_file}")

        # Check dashboard files exist
        dashboard_files = [
            PROJECT_ROOT / "dashboards" / "database_overview.json",
            PROJECT_ROOT / "dashboards" / "postgresql_performance.json",
            PROJECT_ROOT / "dashboards" / "sqlite_performance.json",
        ]

        for dashboard in dashboard_files:
            if not dashboard.exists():
                errors.append(f"Dashboard file not found: {dashboard}")

        return (len(errors) == 0, errors)

    def create_required_directories(self) -> bool:
        """
        Create all required directories for monitoring infrastructure.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating required directories...")

        for directory in self.required_dirs:
            if self.dry_run:
                logger.info("[DRY RUN] Would create directory: %s", directory)
            else:
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    logger.info("Created directory: %s", directory)
                except Exception as e:
                    logger.error("Failed to create directory %s: %s", directory, e)
                    return False

        return True

    def validate_yaml_configs(self) -> Tuple[bool, List[str]]:
        """
        Validate all YAML configuration files.

        Returns:
            Tuple of (success, list of error messages)
        """
        errors = []
        yaml_files = [
            PROJECT_ROOT / "configs" / "monitoring" / "prometheus.yml",
            PROJECT_ROOT / "configs" / "monitoring" / "alertmanager.yml",
            PROJECT_ROOT / "configs" / "monitoring" / "alert_rules.yaml",
            PROJECT_ROOT / "configs" / "monitoring" / "grafana-datasources.yml",
            PROJECT_ROOT / "configs" / "monitoring" / "grafana-dashboards.yml",
            self.docker_compose_file,
        ]

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    yaml.safe_load(f)
                logger.info("Validated YAML: %s", yaml_file.name)
            except Exception as e:
                errors.append(f"Invalid YAML in {yaml_file.name}: {str(e)}")

        return (len(errors) == 0, errors)

    def validate_dashboard_json(self) -> Tuple[bool, List[str]]:
        """
        Validate all dashboard JSON files.

        Returns:
            Tuple of (success, list of error messages)
        """
        errors = []
        dashboard_files = list((PROJECT_ROOT / "dashboards").glob("*.json"))

        for dashboard_file in dashboard_files:
            try:
                with open(dashboard_file, "r", encoding="utf-8") as f:
                    dashboard_data = json.load(f)

                # Validate required dashboard fields
                required_fields = ["title", "panels"]
                for field in required_fields:
                    if field not in dashboard_data:
                        errors.append(f"Dashboard {dashboard_file.name} missing " f"required field: {field}")

                logger.info("Validated dashboard: %s", dashboard_file.name)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in {dashboard_file.name}: {str(e)}")
            except Exception as e:
                errors.append(f"Error validating {dashboard_file.name}: {str(e)}")

        return (len(errors) == 0, errors)

    def deploy_monitoring_stack(self) -> bool:
        """
        Deploy the monitoring stack using docker-compose.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Deploying monitoring stack...")

        if self.dry_run:
            logger.info("[DRY RUN] Would execute: docker compose -f %s up -d", self.docker_compose_file)
            return True

        try:
            result = subprocess.run(  # nosec B603 B607
                ["docker", "compose", "-f", str(self.docker_compose_file), "up", "-d"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error("Failed to deploy stack: %s", result.stderr)
                return False

            logger.info("Monitoring stack deployed successfully")
            logger.info(result.stdout)
            return True

        except Exception as e:
            logger.error("Exception during deployment: %s", e)
            return False

    def wait_for_services(self, timeout: int = 60) -> bool:
        """
        Wait for all monitoring services to become healthy.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all services are healthy, False otherwise
        """
        logger.info("Waiting for services to become healthy (timeout: %ss)...", timeout)

        if self.dry_run:
            logger.info("[DRY RUN] Would wait for services to be healthy")
            return True

        start_time = time.time()
        services = [
            "violentutf-prometheus",
            "violentutf-grafana",
            "violentutf-alertmanager",
        ]

        while time.time() - start_time < timeout:
            all_healthy = True

            for service in services:
                try:
                    result = subprocess.run(  # nosec B603 B607
                        [
                            "docker",
                            "inspect",
                            "--format",
                            "{{.State.Health.Status}}",
                            service,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if result.returncode != 0 or "healthy" not in result.stdout:
                        all_healthy = False
                        break

                except Exception as e:
                    logger.warning("Error checking service %s: %s", service, e)
                    all_healthy = False
                    break

            if all_healthy:
                logger.info("All services are healthy")
                return True

            time.sleep(5)

        logger.error("Services did not become healthy within %s seconds", timeout)
        return False

    def validate_deployment(self) -> Tuple[bool, Dict[str, bool]]:
        """
        Validate that all monitoring components are operational.

        Returns:
            Tuple of (overall success, dict of service statuses)
        """
        logger.info("Validating monitoring deployment...")

        if self.dry_run:
            logger.info("[DRY RUN] Would validate deployment")
            return (True, {})

        statuses = {}

        # Check Prometheus
        try:
            result = subprocess.run(  # nosec B603 B607
                ["curl", "-s", "http://localhost:9090/-/healthy"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            statuses["prometheus"] = result.returncode == 0
        except Exception as e:
            logger.warning("Prometheus health check failed: %s", e)
            statuses["prometheus"] = False

        # Check Grafana
        try:
            result = subprocess.run(  # nosec B603 B607
                ["curl", "-s", "http://localhost:3000/api/health"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            statuses["grafana"] = result.returncode == 0
        except Exception as e:
            logger.warning("Grafana health check failed: %s", e)
            statuses["grafana"] = False

        # Check AlertManager
        try:
            result = subprocess.run(  # nosec B603 B607
                ["curl", "-s", "http://localhost:9093/-/healthy"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            statuses["alertmanager"] = result.returncode == 0
        except Exception as e:
            logger.warning("AlertManager health check failed: %s", e)
            statuses["alertmanager"] = False

        all_healthy = all(statuses.values())

        if all_healthy:
            logger.info("All monitoring components are operational")
        else:
            logger.error("Some monitoring components failed health checks")
            for service, status in statuses.items():
                logger.error("  %s: %s", service, "HEALTHY" if status else "FAILED")

        return (all_healthy, statuses)

    def cleanup_deployment(self) -> bool:
        """
        Clean up monitoring stack deployment.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Cleaning up monitoring stack...")

        if self.dry_run:
            logger.info("[DRY RUN] Would execute: docker compose -f %s down -v", self.docker_compose_file)
            return True

        try:
            result = subprocess.run(  # nosec B603 B607
                [
                    "docker",
                    "compose",
                    "-f",
                    str(self.docker_compose_file),
                    "down",
                    "-v",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error("Failed to cleanup stack: %s", result.stderr)
                return False

            logger.info("Monitoring stack cleaned up successfully")
            return True

        except Exception as e:
            logger.error("Exception during cleanup: %s", e)
            return False

    def print_access_info(self) -> None:
        """Print access information for monitoring services."""
        logger.info("%s", "\n" + "=" * 60)
        logger.info("MONITORING SERVICES ACCESS INFORMATION")
        logger.info("=" * 60)
        logger.info("Prometheus:     http://localhost:9090")
        logger.info("Grafana:        http://localhost:3000")
        logger.info("                (admin/admin - change on first login)")
        logger.info("AlertManager:   http://localhost:9093")
        logger.info("%s", "=" * 60 + "\n")


def main() -> int:
    """Execute main monitoring setup workflow."""
    parser = argparse.ArgumentParser(description="Setup ViolentUTF Performance Monitoring Infrastructure")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without executing them",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing deployment without making changes",
    )
    parser.add_argument("--cleanup", action="store_true", help="Remove monitoring stack deployment")

    args = parser.parse_args()

    setup = MonitoringSetup(dry_run=args.dry_run)

    # Cleanup mode
    if args.cleanup:
        logger.info("Running cleanup mode...")
        success = setup.cleanup_deployment()
        return 0 if success else 1

    # Validate prerequisites
    logger.info("Validating prerequisites...")
    prereq_valid, prereq_errors = setup.validate_prerequisites()

    if not prereq_valid:
        logger.error("Prerequisites validation failed:")
        for error in prereq_errors:
            logger.error("  - %s", error)
        return 1

    logger.info("Prerequisites validation passed")

    # Validate mode
    if args.validate:
        logger.info("Running validation mode...")
        success, _ = setup.validate_deployment()
        return 0 if success else 1

    # Create required directories
    if not setup.create_required_directories():
        logger.error("Failed to create required directories")
        return 1

    # Validate configurations
    logger.info("Validating YAML configurations...")
    yaml_valid, yaml_errors = setup.validate_yaml_configs()

    if not yaml_valid:
        logger.error("YAML validation failed:")
        for error in yaml_errors:
            logger.error("  - %s", error)
        return 1

    logger.info("Validating dashboard JSON files...")
    json_valid, json_errors = setup.validate_dashboard_json()

    if not json_valid:
        logger.error("Dashboard JSON validation failed:")
        for error in json_errors:
            logger.error("  - %s", error)
        return 1

    # Deploy monitoring stack
    if not setup.deploy_monitoring_stack():
        logger.error("Failed to deploy monitoring stack")
        return 1

    # Wait for services to become healthy
    if not setup.wait_for_services():
        logger.warning("Services did not become healthy, but deployment may still succeed")

    # Validate deployment
    success, _ = setup.validate_deployment()

    if not success:
        logger.error("Deployment validation failed")
        return 1

    # Print access information
    setup.print_access_info()

    logger.info("Monitoring infrastructure setup completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
