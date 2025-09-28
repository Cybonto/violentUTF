#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Recovery Framework Setup - Issue #268

Comprehensive recovery procedures and testing framework for all ViolentUTF database systems.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabaseTier(Enum):
    """Database tier classification based on criticality and recovery requirements."""

    CRITICAL = ("critical", 15, 60)  # PostgreSQL: 15min RTO, 1hr RPO
    IMPORTANT = ("important", 5, 30)  # SQLite: 5min RTO, 30min RPO
    USER_SPECIFIC = ("user_specific", 30, 1440)  # DuckDB: 30min RTO, 24hr RPO
    REPLACEABLE = ("replaceable", 60, 1440)  # File configs: 1hr RTO, 24hr RPO

    def __init__(self, tier_name: str, rto_minutes: int, rpo_minutes: int) -> None:
        """Initialize database tier with recovery time objectives."""
        self.tier_name = tier_name
        self.rto_minutes = rto_minutes
        self.rpo_minutes = rpo_minutes


@dataclass
class RecoveryTarget:
    """Recovery time and point objectives for database systems."""

    database_type: str
    service_name: str
    tier: DatabaseTier
    rto_minutes: int
    rpo_minutes: int
    backup_frequency: str = "daily"
    test_frequency: str = "daily"
    criticality_level: int = 1  # 1=highest, 5=lowest

    def __post_init__(self) -> None:
        """Validate recovery targets after initialization."""
        if self.rto_minutes <= 0:
            raise ValueError(f"RTO must be positive, got {self.rto_minutes}")
        if self.rpo_minutes <= 0:
            raise ValueError(f"RPO must be positive, got {self.rpo_minutes}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "database_type": self.database_type,
            "service_name": self.service_name,
            "tier": self.tier.tier_name,
            "rto_minutes": self.rto_minutes,
            "rpo_minutes": self.rpo_minutes,
            "backup_frequency": self.backup_frequency,
            "test_frequency": self.test_frequency,
            "criticality_level": self.criticality_level,
        }


class RecoveryFramework:
    """
    Main recovery framework for ViolentUTF database systems.

    Manages recovery procedures, testing, and compliance tracking.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize recovery framework with configuration."""
        self.config_path = config_path or "scripts/recovery-management/recovery-config.yml"
        self.database_types = ["postgresql", "sqlite", "duckdb", "file_config"]
        self.recovery_targets = self._initialize_recovery_targets()
        self.test_environments = {}
        self.recovery_history = []

        # Create required directories
        self._create_directories()

        logger.info("Recovery framework initialized successfully")

    def _initialize_recovery_targets(self) -> Dict[str, RecoveryTarget]:
        """Initialize recovery targets for all database systems."""
        targets = {}

        # PostgreSQL (Keycloak) - Critical tier
        targets["postgresql"] = RecoveryTarget(
            database_type="postgresql",
            service_name="keycloak",
            tier=DatabaseTier.CRITICAL,
            rto_minutes=15,
            rpo_minutes=60,
            backup_frequency="daily",
            test_frequency="daily",
            criticality_level=1,
        )

        # SQLite (FastAPI) - Important tier
        targets["sqlite"] = RecoveryTarget(
            database_type="sqlite",
            service_name="fastapi",
            tier=DatabaseTier.IMPORTANT,
            rto_minutes=5,
            rpo_minutes=30,
            backup_frequency="daily",
            test_frequency="daily",
            criticality_level=2,
        )

        # DuckDB (User data) - User-specific tier
        targets["duckdb"] = RecoveryTarget(
            database_type="duckdb",
            service_name="user_data",
            tier=DatabaseTier.USER_SPECIFIC,
            rto_minutes=30,
            rpo_minutes=1440,  # 24 hours
            backup_frequency="configurable",
            test_frequency="weekly",
            criticality_level=3,
        )

        # File configuration - Replaceable tier
        targets["file_config"] = RecoveryTarget(
            database_type="file_config",
            service_name="configuration",
            tier=DatabaseTier.REPLACEABLE,
            rto_minutes=60,
            rpo_minutes=1440,  # 24 hours
            backup_frequency="weekly",
            test_frequency="weekly",
            criticality_level=4,
        )

        return targets

    def _create_directories(self) -> None:
        """Create required directories for recovery framework."""
        directories = [
            "scripts/recovery-management/logs",
            "scripts/recovery-management/test-results",
            "scripts/recovery-management/automation-scripts",
            "docs/runbooks",
            "tests/recovery_tests/reports",
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def classify_database(self, database_type: str, service_name: str) -> Dict[str, Any]:
        """
        Classify database type and return recovery configuration.

        Args:
            database_type: Type of database (postgresql, sqlite, duckdb)
            service_name: Service using the database

        Returns:
            Dictionary with recovery configuration
        """
        if database_type not in self.recovery_targets:
            raise ValueError(f"Unknown database type: {database_type}")

        target = self.recovery_targets[database_type]

        return {
            "tier": target.tier.tier_name,
            "rto_minutes": target.rto_minutes,
            "rpo_minutes": target.rpo_minutes,
            "rpo_hours": target.rpo_minutes / 60 if target.rpo_minutes >= 60 else None,
            "backup_frequency": target.backup_frequency,
            "test_frequency": target.test_frequency,
            "criticality_level": target.criticality_level,
            "service_name": service_name,
        }

    def get_all_recovery_targets(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured recovery targets."""
        return {db_type: target.to_dict() for db_type, target in self.recovery_targets.items()}

    async def setup_all_databases(self) -> Dict[str, Any]:
        """
        Set up recovery framework for all supported databases.

        Returns:
            Setup results for all databases
        """
        setup_results = {}

        for db_type in self.database_types:
            logger.info("Setting up recovery framework for %s", db_type)
            try:
                result = await self._setup_database_recovery(db_type)
                setup_results[db_type] = result
            except Exception as e:
                logger.error("Failed to setup recovery for %s: %s", db_type, e)
                setup_results[db_type] = {"status": "failed", "error": str(e)}

        return {
            "overall_status": "completed",
            "database_results": setup_results,
            "timestamp": datetime.now().isoformat(),
        }

    async def setup_database_recovery(self, database_type: str) -> Dict[str, Any]:
        """Public method to set up recovery procedures for specific database type."""
        return await self._setup_database_recovery(database_type)

    async def _setup_database_recovery(self, database_type: str) -> Dict[str, Any]:
        """Set up recovery procedures for specific database type."""
        target = self.recovery_targets[database_type]

        setup_steps = [
            self._validate_backup_infrastructure,
            self._create_recovery_procedures,
            self._setup_monitoring,
            self._configure_test_automation,
        ]

        results = []
        for step in setup_steps:
            try:
                result = await step(database_type, target)
                results.append(result)
            except Exception as e:
                logger.error("Setup step failed for %s: %s", database_type, e)
                results.append({"status": "failed", "step": step.__name__, "error": str(e)})

        return {
            "status": "completed",
            "database_type": database_type,
            "setup_steps": results,
        }

    async def _validate_backup_infrastructure(self, database_type: str, target: RecoveryTarget) -> Dict[str, Any]:
        """Validate backup infrastructure for database type."""
        # Import existing backup system
        try:
            from scripts.backup_management.backup_system import BackupManager

            backup_manager = BackupManager(backup_directory="./backups")

            # Check if method exists before calling
            if hasattr(backup_manager, "validate_backup_infrastructure"):
                validation_result = await backup_manager.validate_backup_infrastructure(database_type)
            else:
                validation_result = {
                    "validation": "backup_infrastructure",
                    "status": "not_implemented",
                }

            return {
                "status": "success",
                "step": "backup_infrastructure_validation",
                "details": validation_result,
            }
        except ImportError:
            return {
                "status": "warning",
                "step": "backup_infrastructure_validation",
                "message": "Backup system not available, recovery will use basic procedures",
            }

    async def _create_recovery_procedures(self, database_type: str, target: RecoveryTarget) -> Dict[str, Any]:
        """Create recovery procedures for database type."""
        procedures = {
            "detection_commands": self._generate_detection_commands(database_type),
            "recovery_steps": self._generate_recovery_steps(database_type, target),
            "validation_commands": self._generate_validation_commands(database_type),
            "rollback_procedures": self._generate_rollback_procedures(database_type),
        }

        # Save procedures to file
        procedures_file = f"scripts/recovery-management/procedures/{database_type}_recovery.yml"
        await self._save_procedures_file(procedures_file, procedures)

        return {
            "status": "success",
            "step": "recovery_procedures_creation",
            "procedures_file": procedures_file,
        }

    def _generate_detection_commands(self, database_type: str) -> List[Dict[str, str]]:
        """Generate detection commands for database failures."""
        commands = {
            "postgresql": [
                {
                    "name": "connection_test",
                    "command": "pg_isready -h localhost -p 5432 -U keycloak",
                    "expected_result": "accepting connections",
                },
                {
                    "name": "service_health",
                    "command": "curl -f http://localhost:8080/auth/realms/violentutf/protocol/openid_connect/certs",
                    "expected_result": "HTTP 200",
                },
            ],
            "sqlite": [
                {
                    "name": "database_integrity",
                    "command": 'sqlite3 violentutf_api/fastapi_app/app_database.db "PRAGMA integrity_check"',
                    "expected_result": "ok",
                },
                {
                    "name": "api_health",
                    "command": "curl -f http://localhost:9080/health",
                    "expected_result": "HTTP 200",
                },
            ],
            "duckdb": [
                {
                    "name": "user_database_check",
                    "command": (
                        'python3 -c "import duckdb; '
                        "conn = duckdb.connect('./app_data/violentutf/pyrit_memory_test.db'); print('OK')\""
                    ),
                    "expected_result": "OK",
                }
            ],
        }

        return commands.get(database_type, [])

    def _generate_recovery_steps(self, database_type: str, target: RecoveryTarget) -> List[Dict[str, Any]]:
        """Generate recovery steps for database type."""
        steps = {
            "postgresql": [
                {
                    "step": 1,
                    "title": "Stop affected services",
                    "commands": ["docker-compose -f keycloak/docker-compose.yml down"],
                    "estimated_time": 2,
                },
                {
                    "step": 2,
                    "title": "Restore database from backup",
                    "commands": [
                        "docker exec keycloak-postgres pg_restore -U keycloak -d keycloak /backups/latest.sql"
                    ],
                    "estimated_time": 10,
                },
                {
                    "step": 3,
                    "title": "Restart services",
                    "commands": ["docker-compose -f keycloak/docker-compose.yml up -d"],
                    "estimated_time": 3,
                },
            ],
            "sqlite": [
                {
                    "step": 1,
                    "title": "Stop FastAPI service",
                    "commands": ["docker-compose -f violentutf_api/docker-compose.yml down"],
                    "estimated_time": 1,
                },
                {
                    "step": 2,
                    "title": "Restore SQLite database",
                    "commands": ["cp backups/sqlite/latest.db violentutf_api/fastapi_app/app_database.db"],
                    "estimated_time": 1,
                },
                {
                    "step": 3,
                    "title": "Restart FastAPI service",
                    "commands": ["docker-compose -f violentutf_api/docker-compose.yml up -d"],
                    "estimated_time": 3,
                },
            ],
            "duckdb": [
                {
                    "step": 1,
                    "title": "Identify affected user databases",
                    "commands": ["ls -la ./app_data/violentutf/pyrit_memory_*.db"],
                    "estimated_time": 1,
                },
                {
                    "step": 2,
                    "title": "Restore user databases from backups",
                    "commands": ["python3 scripts/recovery-management/restore_user_duckdb.py --all"],
                    "estimated_time": 20,
                },
                {
                    "step": 3,
                    "title": "Notify affected users",
                    "commands": ["python3 scripts/recovery-management/notify_users.py --recovery-complete"],
                    "estimated_time": 5,
                },
            ],
        }

        return steps.get(database_type, [])

    def _generate_validation_commands(self, database_type: str) -> List[Dict[str, str]]:
        """Generate validation commands to verify recovery success."""
        return self._generate_detection_commands(database_type)  # Same as detection for now

    def _generate_rollback_procedures(self, database_type: str) -> List[Dict[str, Any]]:
        """Generate rollback procedures in case recovery fails."""
        procedures = {
            "postgresql": [
                {
                    "step": 1,
                    "title": "Restore from previous backup",
                    "commands": [
                        "docker exec keycloak-postgres pg_restore -U keycloak -d keycloak /backups/previous.sql"
                    ],
                }
            ],
            "sqlite": [
                {
                    "step": 1,
                    "title": "Restore from previous SQLite backup",
                    "commands": ["cp backups/sqlite/previous.db violentutf_api/fastapi_app/app_database.db"],
                }
            ],
            "duckdb": [
                {
                    "step": 1,
                    "title": "Recreate clean user databases",
                    "commands": ["python3 scripts/recovery-management/recreate_user_databases.py --clean"],
                }
            ],
        }

        return procedures.get(database_type, [])

    async def _save_procedures_file(self, filename: str, procedures: Dict[str, Any]) -> None:
        """Save recovery procedures to YAML file."""
        import yaml

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            yaml.dump(procedures, f, default_flow_style=False)

    async def _setup_monitoring(self, database_type: str, target: RecoveryTarget) -> Dict[str, Any]:
        """Set up monitoring for database recovery status."""
        monitoring_config = {
            "database_type": database_type,
            "health_check_interval": 60,  # seconds
            "failure_threshold": 3,
            "alert_channels": ["email", "slack"],
            "metrics": [
                "connection_status",
                "response_time",
                "error_rate",
                "backup_freshness",
            ],
        }

        # Save monitoring configuration
        config_file = f"scripts/recovery-management/monitoring/{database_type}_monitoring.yml"
        await self._save_procedures_file(config_file, monitoring_config)

        return {
            "status": "success",
            "step": "monitoring_setup",
            "config_file": config_file,
        }

    async def _configure_test_automation(self, database_type: str, target: RecoveryTarget) -> Dict[str, Any]:
        """Configure automated testing for recovery procedures."""
        test_config = {
            "database_type": database_type,
            "test_frequency": target.test_frequency,
            "test_environment": "isolated",
            "rto_target": target.rto_minutes,
            "rpo_target": target.rpo_minutes,
            "test_scenarios": [
                "complete_failure_recovery",
                "partial_corruption_recovery",
                "backup_restoration_test",
                "performance_validation",
            ],
        }

        # Save test configuration
        config_file = f"scripts/recovery-management/testing/{database_type}_test_config.yml"
        await self._save_procedures_file(config_file, test_config)

        return {
            "status": "success",
            "step": "test_automation_setup",
            "config_file": config_file,
        }


class RecoveryOrchestrator:
    """Orchestrates recovery across multiple database systems with dependency management."""

    def __init__(self) -> None:
        """Initialize recovery orchestrator."""
        self.dependencies = self._initialize_dependencies()
        self.recovery_sequence = []

    def _initialize_dependencies(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize service dependency mapping."""
        return {
            "keycloak": {
                "depends_on": [],  # No dependencies - authentication first
                "provides_to": ["fastapi", "user_services"],
            },
            "fastapi": {
                "depends_on": ["keycloak"],
                "provides_to": ["user_services", "streamlit"],
            },
            "user_services": {"depends_on": ["keycloak", "fastapi"], "provides_to": []},
        }

    def get_recovery_dependencies(self) -> Dict[str, Dict[str, List[str]]]:
        """Get service dependency mapping for recovery sequencing."""
        return self.dependencies

    async def create_recovery_plan(self, failure_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create recovery plan based on failure scenario.

        Args:
            failure_scenario: Description of failure including affected services

        Returns:
            Recovery plan with sequenced steps
        """
        affected_services = failure_scenario.get("affected_services", [])

        # Calculate recovery sequence based on dependencies
        recovery_sequence = self._calculate_recovery_sequence(affected_services)

        # Create detailed recovery steps
        recovery_steps = []
        for i, service in enumerate(recovery_sequence):
            step = {
                "sequence_number": i + 1,
                "service": service,
                "database_type": self._get_database_type(service),
                "estimated_time": self._get_estimated_recovery_time(service),
                "dependencies": self.dependencies[service]["depends_on"],
                "prerequisites": self._get_recovery_prerequisites(service),
            }
            recovery_steps.append(step)

        return {
            "scenario": failure_scenario,
            "sequence": recovery_sequence,
            "steps": recovery_steps,
            "total_estimated_time": sum(step["estimated_time"] for step in recovery_steps),
            "created_at": datetime.now().isoformat(),
        }

    def _calculate_recovery_sequence(self, affected_services: List[str]) -> List[str]:
        """Calculate optimal recovery sequence based on dependencies."""
        # Topological sort for dependency-based ordering
        sequence = []
        remaining = set(affected_services)

        while remaining:
            # Find services with no unmet dependencies
            ready = []
            for service in remaining:
                dependencies = self.dependencies[service]["depends_on"]
                if all(dep not in remaining for dep in dependencies):
                    ready.append(service)

            if not ready:
                # Circular dependency or missing dependency - use fallback order
                ready = [list(remaining)[0]]

            # Add ready services to sequence
            for service in ready:
                sequence.append(service)
                remaining.remove(service)

        return sequence

    def _get_database_type(self, service: str) -> str:
        """Get database type for service."""
        mapping = {
            "keycloak": "postgresql",
            "fastapi": "sqlite",
            "user_services": "duckdb",
        }
        return mapping.get(service, "unknown")

    def _get_estimated_recovery_time(self, service: str) -> int:
        """Get estimated recovery time for service in minutes."""
        times = {
            "keycloak": 15,
            "fastapi": 5,
            "user_services": 30,
        }  # PostgreSQL RTO  # SQLite RTO  # DuckDB RTO
        return times.get(service, 60)

    def _get_recovery_prerequisites(self, service: str) -> List[str]:
        """Get recovery prerequisites for service."""
        prerequisites = {
            "keycloak": ["docker_running", "backup_available"],
            "fastapi": ["keycloak_healthy", "backup_available"],
            "user_services": [
                "keycloak_healthy",
                "fastapi_healthy",
                "user_backups_available",
            ],
        }
        return prerequisites.get(service, [])

    async def execute_recovery_plan(self, recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute recovery plan with orchestrated sequencing.

        Args:
            recovery_plan: Recovery plan from create_recovery_plan()

        Returns:
            Execution results with step-by-step outcomes
        """
        step_results = []
        overall_success = True
        start_time = time.time()

        for step in recovery_plan["steps"]:
            logger.info(
                "Executing recovery step %s: %s",
                step["sequence_number"],
                step["service"],
            )

            try:
                step_start = time.time()

                # Execute recovery for this service
                result = await self._execute_service_recovery(step)

                step_end = time.time()
                result["actual_time"] = (step_end - step_start) / 60  # minutes
                result["step_number"] = step["sequence_number"]
                result["service"] = step["service"]

                step_results.append(result)

                if result["status"] != "success":
                    overall_success = False
                    logger.error(
                        "Recovery step %s failed: %s",
                        step["sequence_number"],
                        result.get("error"),
                    )
                    break  # Stop on first failure

            except Exception as e:
                logger.error("Recovery step %s exception: %s", step["sequence_number"], e)
                step_results.append(
                    {
                        "step_number": step["sequence_number"],
                        "service": step["service"],
                        "status": "failed",
                        "error": str(e),
                        "actual_time": 0,
                    }
                )
                overall_success = False
                break

        end_time = time.time()
        total_time = (end_time - start_time) / 60  # minutes

        return {
            "status": "success" if overall_success else "failed",
            "total_time_minutes": total_time,
            "step_results": step_results,
            "recovery_plan_id": recovery_plan.get("id", "unknown"),
            "completed_at": datetime.now().isoformat(),
        }

    async def _execute_service_recovery(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recovery for a specific service."""
        database_type = step["database_type"]

        # Import appropriate recovery module
        if database_type == "postgresql":
            from scripts.recovery_management.database_recovery import PostgreSQLRecovery

            recovery_handler = PostgreSQLRecovery()
        elif database_type == "sqlite":
            from scripts.recovery_management.database_recovery import SQLiteRecovery

            recovery_handler = SQLiteRecovery()
        elif database_type == "duckdb":
            from scripts.recovery_management.database_recovery import DuckDBRecovery

            recovery_handler = DuckDBRecovery(username="default_user")
        else:
            raise ValueError(f"Unknown database type: {database_type}")

        # Execute recovery procedure
        result = await recovery_handler.full_recovery_procedure()

        return result


async def main() -> None:
    """Set up and configure the recovery framework for all databases."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Recovery Framework Setup")
    parser.add_argument(
        "--all-databases",
        action="store_true",
        help="Setup recovery framework for all databases",
    )
    parser.add_argument(
        "--database",
        choices=["postgresql", "sqlite", "duckdb"],
        help="Setup recovery for specific database type",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate current setup without changes",
    )

    args = parser.parse_args()

    # Initialize recovery framework
    framework = RecoveryFramework()

    try:
        if args.validate_only:
            logger.info("Validating current recovery framework setup...")
            # Add validation logic here

        elif args.all_databases:
            logger.info("Setting up recovery framework for all databases...")
            result = await framework.setup_all_databases()
            print(f"Setup completed: {result}")

        elif args.database:
            logger.info("Setting up recovery framework for %s...", args.database)
            result = await framework.setup_database_recovery(args.database)
            print(f"Setup completed for {args.database}: {result}")

        else:
            print("Please specify --all-databases or --database <type>")
            return 1

        logger.info("Recovery framework setup completed successfully")
        return 0

    except Exception as e:
        logger.error("Recovery framework setup failed: %s", e)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
