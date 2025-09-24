#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration Deployment Tool for ViolentUTF - Issue #266.

Automated deployment of configurations with validation and rollback capabilities.
"""

import hashlib
import json
import logging
import shutil
import sqlite3
import subprocess  # nosec B404
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DeploymentPlan:
    """Represents a configuration deployment plan."""

    deployment_id: str
    service: str
    environment: str
    configuration_files: Dict[str, str]  # file_path -> content
    backup_paths: Dict[str, str] = field(default_factory=dict)  # original -> backup
    validation_results: Dict[str, Any] = field(default_factory=dict)
    deployment_strategy: str = "rolling"  # "rolling", "blue_green", "canary"
    rollback_timeout_seconds: int = 300
    health_check_enabled: bool = True
    created_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DeploymentResult:
    """Represents the result of a configuration deployment."""

    deployment_id: str
    success: bool
    duration_seconds: float
    deployed_files: List[str] = field(default_factory=list)
    failed_files: List[str] = field(default_factory=list)
    services_restarted: List[str] = field(default_factory=list)
    rollback_performed: bool = False
    rollback_reason: str = ""
    health_checks_passed: bool = False
    error_message: str = ""
    deployment_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConfigurationDeployer:
    """Main configuration deployment engine with rollback capabilities."""

    def __init__(self, database_path: str = "config_deployment.db") -> None:
        """Initialize the configuration deployment tool.

        Args:
            database_path: Path to SQLite database for deployment tracking
        """
        self.database_path = database_path
        self.service_configs = self._load_service_configurations()
        self._setup_database()

    def _setup_database(self) -> None:
        """Set up SQLite database for deployment tracking."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL UNIQUE,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                deployment_strategy TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                duration_seconds REAL NOT NULL,
                deployed_files_count INTEGER NOT NULL,
                services_restarted TEXT NOT NULL,
                rollback_performed BOOLEAN NOT NULL,
                health_checks_passed BOOLEAN NOT NULL,
                deployment_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deployment_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                backup_path TEXT,
                deployed BOOLEAN NOT NULL,
                checksum_before TEXT,
                checksum_after TEXT,
                FOREIGN KEY (deployment_id) REFERENCES deployments (deployment_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rollback_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                backup_directory TEXT NOT NULL,
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deployment_id) REFERENCES deployments (deployment_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def _load_service_configurations(self) -> Dict[str, Any]:
        """Load service-specific configuration for deployment."""
        return {
            "apisix": {
                "config_files": ["conf/config.yaml", "conf/dashboard.yaml"],
                "restart_command": ["docker", "compose", "restart", "apisix"],
                "health_check_url": "http://localhost:9180/apisix/admin/routes",
                "health_check_timeout": 30,
            },
            "keycloak": {
                "config_files": ["realm-export.json"],
                "restart_command": ["docker", "compose", "restart", "keycloak"],
                "health_check_url": "http://localhost:8080/realms/ViolentUTF/.well-known/openid_configuration",
                "health_check_timeout": 60,
            },
            "violentutf_api": {
                "config_files": [".env", "app/core/config.py"],
                "restart_command": ["docker", "compose", "restart", "violentutf-api"],
                "health_check_url": "http://localhost:9080/health",
                "health_check_timeout": 30,
            },
            "postgres": {
                "config_files": ["postgresql.conf", "pg_hba.conf"],
                "restart_command": ["docker", "compose", "restart", "postgres"],
                "health_check_command": ["docker", "exec", "postgres", "pg_isready"],
                "health_check_timeout": 30,
            },
        }

    def deploy_configuration(self, plan: DeploymentPlan, dry_run: bool = False) -> DeploymentResult:
        """Deploy configuration according to the deployment plan.

        Args:
            plan: DeploymentPlan with configuration details
            dry_run: If True, validate without actually deploying

        Returns:
            DeploymentResult with deployment outcome
        """
        start_time = time.time()
        logger.info("Starting deployment %s for %s (%s)", plan.deployment_id, plan.service, plan.environment)

        result = DeploymentResult(deployment_id=plan.deployment_id, success=False, duration_seconds=0.0)

        try:
            # Step 1: Pre-deployment validation
            validation_result = self._validate_pre_deployment(plan)
            if not validation_result["valid"]:
                result.error_message = f"Pre-deployment validation failed: {validation_result['errors']}"
                return result

            plan.validation_results = validation_result

            if dry_run:
                result.success = True
                result.duration_seconds = time.time() - start_time
                logger.info("Dry run completed successfully for %s", plan.deployment_id)
                return result

            # Step 2: Create rollback point
            rollback_point = self._create_rollback_point(plan)
            logger.info("Created rollback point: %s", rollback_point)

            # Step 3: Deploy configuration files
            deployment_success = self._deploy_configuration_files(plan, result)
            if not deployment_success:
                logger.error("Configuration file deployment failed, initiating rollback")
                self._perform_rollback(plan.deployment_id, "Configuration file deployment failed")
                result.rollback_performed = True
                result.rollback_reason = "Configuration file deployment failed"
                return result

            # Step 4: Restart affected services
            restart_success = self._restart_services(plan, result)
            if not restart_success:
                logger.error("Service restart failed, initiating rollback")
                self._perform_rollback(plan.deployment_id, "Service restart failed")
                result.rollback_performed = True
                result.rollback_reason = "Service restart failed"
                return result

            # Step 5: Health checks
            if plan.health_check_enabled:
                health_check_success = self._perform_health_checks(plan, result)
                if not health_check_success:
                    logger.error("Health checks failed, initiating rollback")
                    self._perform_rollback(plan.deployment_id, "Health checks failed")
                    result.rollback_performed = True
                    result.rollback_reason = "Health checks failed"
                    return result

                result.health_checks_passed = True

            # Deployment successful
            result.success = True
            logger.info("Deployment %s completed successfully", plan.deployment_id)

        except Exception as e:
            logger.error("Deployment failed with exception: %s", e)
            result.error_message = str(e)

            # Attempt rollback on exception
            try:
                self._perform_rollback(plan.deployment_id, f"Exception during deployment: {e}")
                result.rollback_performed = True
                result.rollback_reason = f"Exception: {e}"
            except Exception as rollback_error:
                logger.error("Rollback also failed: %s", rollback_error)
                result.error_message += f"; Rollback failed: {rollback_error}"

        finally:
            result.duration_seconds = time.time() - start_time
            self._store_deployment_result(plan, result)

        return result

    def _validate_pre_deployment(self, plan: DeploymentPlan) -> Dict[str, Any]:
        """Validate configuration before deployment.

        Args:
            plan: Deployment plan to validate

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        # Check if all configuration files exist and are readable
        for file_path, content in plan.configuration_files.items():
            if not content:
                errors.append(f"Configuration file {file_path} has no content")

            # Try to parse configuration based on file type
            try:
                if file_path.endswith((".yaml", ".yml")):
                    yaml.safe_load(content)
                elif file_path.endswith(".json"):
                    json.loads(content)
            except Exception as e:
                errors.append(f"Configuration file {file_path} has invalid syntax: {e}")

        # Check if service exists in service configurations
        if plan.service not in self.service_configs:
            warnings.append(f"No service configuration found for {plan.service}")

        # Check environment-specific requirements
        if plan.environment == "prod":
            # Production-specific validations
            if plan.deployment_strategy not in ["blue_green", "canary"]:
                warnings.append("Consider using blue-green or canary deployment for production")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validation_timestamp": datetime.now().isoformat(),
        }

    def _create_rollback_point(self, plan: DeploymentPlan) -> str:
        """Create a rollback point by backing up current configurations.

        Args:
            plan: Deployment plan

        Returns:
            Path to backup directory
        """
        # Create backup directory
        backup_dir = Path(tempfile.mkdtemp(prefix=f"rollback_{plan.deployment_id}_"))

        # Backup existing configuration files
        # service_config would be retrieved here but is not used in this method
        base_path = self._get_service_base_path(plan.service)

        for file_path in plan.configuration_files.keys():
            full_path = base_path / file_path
            if full_path.exists():
                backup_path = backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                # Create backup
                shutil.copy2(full_path, backup_path)
                plan.backup_paths[str(full_path)] = str(backup_path)

                logger.debug("Backed up %s to %s", full_path, backup_path)

        # Store rollback point in database
        self._store_rollback_point(plan.deployment_id, plan.service, plan.environment, str(backup_dir))

        return str(backup_dir)

    def _deploy_configuration_files(self, plan: DeploymentPlan, result: DeploymentResult) -> bool:
        """Deploy configuration files.

        Args:
            plan: Deployment plan
            result: Result object to update

        Returns:
            True if all files deployed successfully
        """
        base_path = self._get_service_base_path(plan.service)
        success_count = 0

        for file_path, content in plan.configuration_files.items():
            full_path = base_path / file_path

            try:
                # Ensure directory exists
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Calculate checksums
                checksum_before = self._calculate_file_checksum(full_path) if full_path.exists() else None

                # Write new configuration
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

                checksum_after = self._calculate_file_checksum(full_path)

                # Store file deployment record
                self._store_file_deployment(
                    plan.deployment_id,
                    str(full_path),
                    plan.backup_paths.get(str(full_path)),
                    True,
                    checksum_before,
                    checksum_after,
                )

                result.deployed_files.append(str(full_path))
                success_count += 1
                logger.debug("Successfully deployed %s", full_path)

            except Exception as e:
                logger.error("Failed to deploy %s: %s", full_path, e)
                result.failed_files.append(str(full_path))

                # Store failed deployment record
                self._store_file_deployment(
                    plan.deployment_id, str(full_path), plan.backup_paths.get(str(full_path)), False, None, None
                )

        return success_count == len(plan.configuration_files)

    def _restart_services(self, plan: DeploymentPlan, result: DeploymentResult) -> bool:
        """Restart affected services.

        Args:
            plan: Deployment plan
            result: Result object to update

        Returns:
            True if all services restarted successfully
        """
        service_config = self.service_configs.get(plan.service)
        if not service_config or "restart_command" not in service_config:
            logger.warning("No restart command configured for service %s", plan.service)
            return True

        restart_command = service_config["restart_command"]

        try:
            logger.info("Restarting service %s with command: %s", plan.service, " ".join(restart_command))

            # Execute restart command
            result_cmd = subprocess.run(  # nosec B603
                restart_command,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout for restart
                cwd=self._get_service_base_path(plan.service),
                check=False,  # Don't raise exception on non-zero exit
            )

            if result_cmd.returncode == 0:
                result.services_restarted.append(plan.service)
                logger.info("Successfully restarted service %s", plan.service)
                return True
            else:
                logger.error("Service restart failed: %s", result_cmd.stderr)
                return False

        except subprocess.TimeoutExpired:
            logger.error("Service restart timed out for %s", plan.service)
            return False
        except Exception as e:
            logger.error("Exception during service restart: %s", e)
            return False

    def _perform_health_checks(self, plan: DeploymentPlan, result: DeploymentResult) -> bool:
        """Perform health checks on deployed services.

        Args:
            plan: Deployment plan
            result: Result object to update

        Returns:
            True if health checks pass
        """
        service_config = self.service_configs.get(plan.service)
        if not service_config:
            logger.warning("No health check configuration for service %s", plan.service)
            return True

        timeout = service_config.get("health_check_timeout", 30)

        # HTTP health check
        if "health_check_url" in service_config:
            return self._perform_http_health_check(service_config["health_check_url"], timeout)

        # Command-based health check
        elif "health_check_command" in service_config:
            return self._perform_command_health_check(service_config["health_check_command"], timeout)

        logger.warning("No health check method configured for service %s", plan.service)
        return True

    def _perform_http_health_check(self, url: str, timeout: int) -> bool:
        """Perform HTTP health check.

        Args:
            url: Health check URL
            timeout: Timeout in seconds

        Returns:
            True if health check passes
        """
        import requests

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 404]:  # 404 might be OK for some endpoints
                    logger.info("HTTP health check passed for %s", url)
                    return True
                else:
                    logger.debug("Health check returned status %s", response.status_code)
            except requests.RequestException as e:
                logger.debug("Health check attempt failed: %s", e)

            time.sleep(2)  # Wait before retry

        logger.error("HTTP health check failed for %s after %s seconds", url, timeout)
        return False

    def _perform_command_health_check(self, command: List[str], timeout: int) -> bool:
        """Perform command-based health check.

        Args:
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            True if health check passes
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)  # nosec B603

                if result.returncode == 0:
                    logger.info("Command health check passed: %s", " ".join(command))
                    return True
                else:
                    logger.debug("Health check command returned %s", result.returncode)

            except subprocess.TimeoutExpired:
                logger.debug("Health check command timed out")
            except Exception as e:
                logger.debug("Health check command failed: %s", e)

            time.sleep(2)  # Wait before retry

        logger.error("Command health check failed after %s seconds", timeout)
        return False

    def _perform_rollback(self, deployment_id: str, reason: str) -> bool:
        """Perform rollback of a deployment.

        Args:
            deployment_id: Deployment ID to rollback
            reason: Reason for rollback

        Returns:
            True if rollback successful
        """
        logger.info("Performing rollback for deployment %s: %s", deployment_id, reason)

        try:
            # Get rollback point
            rollback_info = self._get_rollback_point(deployment_id)
            if not rollback_info:
                logger.error("No rollback point found for deployment %s", deployment_id)
                return False

            backup_dir = Path(rollback_info["backup_directory"])
            service = rollback_info["service"]

            # Restore backed up files
            base_path = self._get_service_base_path(service)

            for backup_file in backup_dir.rglob("*"):
                if backup_file.is_file():
                    relative_path = backup_file.relative_to(backup_dir)
                    target_path = base_path / relative_path

                    # Restore file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, target_path)
                    logger.debug("Restored %s from backup", target_path)

            # Restart service
            service_config = self.service_configs.get(service)
            if service_config and "restart_command" in service_config:
                restart_command = service_config["restart_command"]

                result = subprocess.run(  # nosec B603
                    restart_command, capture_output=True, text=True, timeout=120, cwd=base_path, check=False
                )

                if result.returncode != 0:
                    logger.error("Service restart during rollback failed: %s", result.stderr)
                    return False

            logger.info("Rollback completed successfully for deployment %s", deployment_id)
            return True

        except Exception as e:
            logger.error("Rollback failed: %s", e)
            return False

    def _get_service_base_path(self, service: str) -> Path:
        """Get the base path for a service.

        Args:
            service: Service name

        Returns:
            Path object for service base directory
        """
        # Service base path mapping
        service_paths = {
            "apisix": Path(".") / "apisix",
            "keycloak": Path(".") / "keycloak",
            "violentutf_api": Path(".") / "violentutf_api" / "fastapi_app",
            "violentutf": Path(".") / "violentutf",
            "postgres": Path(".") / "postgres",
        }

        return service_paths.get(service, Path("."))

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 checksum as hex string
        """
        if not file_path.exists():
            return ""

        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("Error calculating checksum for %s: %s", file_path, e)
            return "error"

    def _store_deployment_result(self, plan: DeploymentPlan, result: DeploymentResult) -> None:
        """Store deployment result in database.

        Args:
            plan: Deployment plan
            result: Deployment result
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO deployments
            (deployment_id, service, environment, deployment_strategy, success,
             duration_seconds, deployed_files_count, services_restarted,
             rollback_performed, health_checks_passed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.deployment_id,
                plan.service,
                plan.environment,
                plan.deployment_strategy,
                result.success,
                result.duration_seconds,
                len(result.deployed_files),
                ",".join(result.services_restarted),
                result.rollback_performed,
                result.health_checks_passed,
            ),
        )

        conn.commit()
        conn.close()

    def _store_file_deployment(
        self,
        deployment_id: str,
        file_path: str,
        backup_path: Optional[str],
        deployed: bool,
        checksum_before: Optional[str],
        checksum_after: Optional[str],
    ) -> None:
        """Store file deployment record in database.

        Args:
            deployment_id: Deployment ID
            file_path: Path to deployed file
            backup_path: Path to backup file
            deployed: Whether deployment was successful
            checksum_before: Checksum before deployment
            checksum_after: Checksum after deployment
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO deployment_files
            (deployment_id, file_path, backup_path, deployed, checksum_before, checksum_after)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (deployment_id, file_path, backup_path, deployed, checksum_before, checksum_after),
        )

        conn.commit()
        conn.close()

    def _store_rollback_point(self, deployment_id: str, service: str, environment: str, backup_directory: str) -> None:
        """Store rollback point information in database.

        Args:
            deployment_id: Deployment ID
            service: Service name
            environment: Environment name
            backup_directory: Path to backup directory
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO rollback_points
            (deployment_id, service, environment, backup_directory)
            VALUES (?, ?, ?, ?)
        """,
            (deployment_id, service, environment, backup_directory),
        )

        conn.commit()
        conn.close()

    def _get_rollback_point(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get rollback point information for a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Dictionary with rollback point information or None
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT service, environment, backup_directory, created_timestamp
            FROM rollback_points
            WHERE deployment_id = ?
            ORDER BY created_timestamp DESC
            LIMIT 1
        """,
            (deployment_id,),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "service": result[0],
                "environment": result[1],
                "backup_directory": result[2],
                "created_timestamp": result[3],
            }

        return None

    def create_deployment_plan(
        self, service: str, environment: str, configuration_files: Dict[str, str], deployment_strategy: str = "rolling"
    ) -> DeploymentPlan:
        """Create a deployment plan.

        Args:
            service: Service name
            environment: Environment name
            configuration_files: Dictionary of file paths to content
            deployment_strategy: Deployment strategy

        Returns:
            DeploymentPlan object
        """
        deployment_id = f"{service}_{environment}_{int(time.time())}"

        return DeploymentPlan(
            deployment_id=deployment_id,
            service=service,
            environment=environment,
            configuration_files=configuration_files,
            deployment_strategy=deployment_strategy,
        )

    def get_deployment_history(
        self, service: Optional[str] = None, environment: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get deployment history.

        Args:
            service: Optional service filter
            environment: Optional environment filter
            limit: Maximum number of records

        Returns:
            List of deployment records
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        query = "SELECT * FROM deployments WHERE 1=1"
        params = []

        if service:
            query += " AND service = ?"
            params.append(service)

        if environment:
            query += " AND environment = ?"
            params.append(environment)

        query += " ORDER BY deployment_timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results


def main() -> None:
    """Run configuration deployment from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Configuration Deployment Tool")
    parser.add_argument("--service", required=True, help="Service name")
    parser.add_argument("--environment", required=True, help="Environment name")
    parser.add_argument("--config-dir", help="Directory containing configuration files")
    parser.add_argument("--config-file", help="Single configuration file to deploy")
    parser.add_argument(
        "--strategy", default="rolling", choices=["rolling", "blue_green", "canary"], help="Deployment strategy"
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without deploying")
    parser.add_argument("--rollback", help="Rollback specific deployment ID")
    parser.add_argument("--history", action="store_true", help="Show deployment history")
    parser.add_argument("--database", default="config_deployment.db", help="Database file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize deployer
    deployer = ConfigurationDeployer(args.database)

    # Show deployment history
    if args.history:
        history = deployer.get_deployment_history(args.service, args.environment)
        print("Deployment History:")
        for record in history:
            print(
                f"  {record['deployment_id']}: {record['service']}/{record['environment']} "
                f"- {'SUCCESS' if record['success'] else 'FAILED'} "
                f"({record['deployment_timestamp']})"
            )
        return

    # Perform rollback
    if args.rollback:
        success = deployer._perform_rollback(  # pylint: disable=protected-access
            args.rollback, "Manual rollback requested"
        )
        if success:
            print(f"Rollback of deployment {args.rollback} completed successfully")
        else:
            print(f"Rollback of deployment {args.rollback} failed")
        return

    # Prepare configuration files
    config_files = {}

    if args.config_file:
        # Single file deployment
        with open(args.config_file, "r", encoding="utf-8") as f:
            content = f.read()
        config_files[args.config_file] = content

    elif args.config_dir:
        # Directory deployment
        config_dir = Path(args.config_dir)
        for file_path in config_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".yaml", ".yml", ".json", ".conf", ".env"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                relative_path = file_path.relative_to(config_dir)
                config_files[str(relative_path)] = content

    else:
        print("Either --config-file or --config-dir must be specified")
        return

    if not config_files:
        print("No configuration files found to deploy")
        return

    # Create deployment plan
    plan = deployer.create_deployment_plan(
        service=args.service,
        environment=args.environment,
        configuration_files=config_files,
        deployment_strategy=args.strategy,
    )

    # Execute deployment
    result = deployer.deploy_configuration(plan, dry_run=args.dry_run)

    # Output results
    print(f"Deployment {plan.deployment_id}: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Duration: {result.duration_seconds:.2f} seconds")

    if result.deployed_files:
        print(f"Deployed files: {', '.join(result.deployed_files)}")

    if result.failed_files:
        print(f"Failed files: {', '.join(result.failed_files)}")

    if result.services_restarted:
        print(f"Services restarted: {', '.join(result.services_restarted)}")

    if result.rollback_performed:
        print(f"Rollback performed: {result.rollback_reason}")

    if result.error_message:
        print(f"Error: {result.error_message}")


if __name__ == "__main__":
    main()
