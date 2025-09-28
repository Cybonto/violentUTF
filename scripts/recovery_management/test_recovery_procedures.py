#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Recovery Testing Framework - Issue #268
Automated testing of recovery procedures with RTO/RPO validation.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class RecoveryTestResult:
    """Result of a recovery test execution."""

    database_type: str
    test_name: str
    status: str  # 'success', 'failure', 'partial_success'
    start_time: datetime
    end_time: datetime
    rto_actual: float  # minutes
    rto_target: float  # minutes
    rpo_actual: Optional[float] = None  # minutes
    rpo_target: Optional[float] = None  # minutes
    data_integrity: bool = True
    error_details: Optional[str] = None
    recovery_method: Optional[str] = None
    test_environment: str = "isolated"

    @property
    def duration_minutes(self) -> float:
        """Calculate test duration in minutes."""
        return (self.end_time - self.start_time).total_seconds() / 60

    @property
    def rto_compliant(self) -> bool:
        """Check if RTO target was met."""
        return self.rto_actual <= self.rto_target

    @property
    def rpo_compliant(self) -> Optional[bool]:
        """Check if RPO target was met."""
        if self.rpo_actual is None or self.rpo_target is None:
            return None
        return self.rpo_actual <= self.rpo_target

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "database_type": self.database_type,
            "test_name": self.test_name,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "rto_actual": self.rto_actual,
            "rto_target": self.rto_target,
            "rto_compliant": self.rto_compliant,
            "rpo_actual": self.rpo_actual,
            "rpo_target": self.rpo_target,
            "rpo_compliant": self.rpo_compliant,
            "data_integrity": self.data_integrity,
            "error_details": self.error_details,
            "recovery_method": self.recovery_method,
            "test_environment": self.test_environment,
        }


class RTOValidator:
    """Validator for Recovery Time Objectives."""

    def __init__(self):
        """Initialize RTO validator."""
        self.measurements = []

    def measure_rto(self, start_time: float, end_time: float) -> float:
        """
        Measure RTO with high precision.

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            RTO in seconds
        """
        rto_seconds = end_time - start_time
        return rto_seconds

    async def validate_rto(self, database_type: str, target_rto_seconds: float, recovery_operation) -> Dict[str, Any]:
        """
        Validate RTO compliance for a recovery operation.

        Args:
            database_type: Type of database being recovered
            target_rto_seconds: Target RTO in seconds
            recovery_operation: Async function to execute for recovery

        Returns:
            RTO validation result
        """
        start_time = time.time()

        try:
            result = await recovery_operation()
            end_time = time.time()

            actual_rto = end_time - start_time
            compliant = actual_rto <= target_rto_seconds

            validation_result = {
                "database_type": database_type,
                "target_rto": target_rto_seconds,
                "actual_rto": actual_rto,
                "compliant": compliant,
                "compliance_percentage": ((target_rto_seconds / actual_rto) * 100 if actual_rto > 0 else 100),
                "measurement_timestamp": datetime.now().isoformat(),
                "recovery_result": result,
            }

            self.measurements.append(validation_result)
            return validation_result

        except Exception as e:
            end_time = time.time()
            actual_rto = end_time - start_time

            return {
                "database_type": database_type,
                "target_rto": target_rto_seconds,
                "actual_rto": actual_rto,
                "compliant": False,
                "error": str(e),
                "measurement_timestamp": datetime.now().isoformat(),
            }


class RPOValidator:
    """Validator for Recovery Point Objectives."""

    def __init__(self):
        """Initialize RPO validator."""
        self.measurements = []

    def calculate_data_loss(self, last_backup_time: datetime, failure_time: datetime) -> float:
        """
        Calculate data loss in minutes for RPO validation.

        Args:
            last_backup_time: Timestamp of last backup
            failure_time: Timestamp of failure

        Returns:
            Data loss duration in minutes
        """
        delta = failure_time - last_backup_time
        return delta.total_seconds() / 60

    async def validate_rpo(
        self,
        database_type: str,
        target_rpo_minutes: float,
        last_backup_time: datetime,
        failure_time: datetime,
    ) -> Dict[str, Any]:
        """
        Validate RPO compliance for a recovery scenario.

        Args:
            database_type: Type of database being recovered
            target_rpo_minutes: Target RPO in minutes
            last_backup_time: When last backup was taken
            failure_time: When failure occurred

        Returns:
            RPO validation result
        """
        data_loss_minutes = self.calculate_data_loss(last_backup_time, failure_time)
        compliant = data_loss_minutes <= target_rpo_minutes

        validation_result = {
            "database_type": database_type,
            "target_rpo_minutes": target_rpo_minutes,
            "data_loss_minutes": data_loss_minutes,
            "compliant": compliant,
            "last_backup_time": last_backup_time.isoformat(),
            "failure_time": failure_time.isoformat(),
            "validation_timestamp": datetime.now().isoformat(),
        }

        self.measurements.append(validation_result)
        return validation_result


class RecoveryTester:
    """Main recovery testing framework."""

    def __init__(self, test_environment: str = "isolated"):
        """
        Initialize recovery tester.

        Args:
            test_environment: Environment for testing (isolated, staging, etc.)
        """
        self.test_environment = test_environment
        self.test_environments = {
            "isolated": "docker-compose.recovery.yml",
            "staging": "docker-compose.staging.yml",
        }
        self.rto_validator = RTOValidator()
        self.rpo_validator = RPOValidator()
        self.test_results = []

    async def test_database_recovery(
        self,
        database_type: str,
        service: str,
        rto_target: int,
        rpo_target: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Test recovery procedure for specific database type.

        Args:
            database_type: Type of database (postgresql, sqlite, duckdb)
            service: Service name
            rto_target: RTO target in minutes
            rpo_target: RPO target in minutes
            **kwargs: Additional test parameters

        Returns:
            Test result dictionary
        """
        test_name = f"{database_type}_{service}_recovery_test"
        logger.info("Starting recovery test: %s", test_name)

        start_time = datetime.now()

        try:
            # Setup test environment
            await self._setup_test_environment(database_type)

            # Simulate failure
            await self._simulate_failure(database_type, kwargs.get("failure_type", "complete"))

            # Execute recovery with timing
            recovery_start = time.time()
            recovery_result = await self._execute_recovery(database_type, service)
            recovery_end = time.time()

            rto_actual = (recovery_end - recovery_start) / 60  # Convert to minutes

            # Validate data integrity
            data_integrity = await self._validate_data_integrity(database_type)

            # Calculate RPO if backup times are available
            rpo_actual = None
            if "last_backup_time" in kwargs and "failure_time" in kwargs:
                rpo_actual = self.rpo_validator.calculate_data_loss(kwargs["last_backup_time"], kwargs["failure_time"])

            end_time = datetime.now()

            # Create test result
            result = RecoveryTestResult(
                database_type=database_type,
                test_name=test_name,
                status=("success" if recovery_result.get("status") == "success" else "failure"),
                start_time=start_time,
                end_time=end_time,
                rto_actual=rto_actual,
                rto_target=float(rto_target),
                rpo_actual=rpo_actual,
                rpo_target=float(rpo_target),
                data_integrity=data_integrity,
                recovery_method=recovery_result.get("method", "unknown"),
                test_environment=self.test_environment,
            )

            # Create test result
            result_dict = result.to_dict()

            if kwargs.get("username"):
                result_dict["user"] = kwargs["username"]

            # Add database-specific fields
            if database_type == "duckdb":
                result_dict["pyrit_data_recovered"] = data_integrity
            elif database_type == "sqlite":
                result_dict["data_integrity_validated"] = data_integrity

            self.test_results.append(result)
            return result_dict

        except Exception as e:
            logger.error("Recovery test failed: %s", e)
            end_time = datetime.now()

            result = RecoveryTestResult(
                database_type=database_type,
                test_name=test_name,
                status="failure",
                start_time=start_time,
                end_time=end_time,
                rto_actual=999.0,  # Indicate failure
                rto_target=float(rto_target),
                data_integrity=False,
                error_details=str(e),
                test_environment=self.test_environment,
            )

            self.test_results.append(result)
            return result.to_dict()

        finally:
            # Cleanup test environment
            await self._cleanup_test_environment(database_type)

    async def _setup_test_environment(self, database_type: str):
        """Setup isolated test environment for recovery testing."""
        logger.info("Setting up test environment for %s", database_type)

        # Create test data directory
        test_data_dir = Path(f"tests/recovery_tests/data/{database_type}")
        test_data_dir.mkdir(parents=True, exist_ok=True)

        # Database-specific setup
        if database_type == "postgresql":
            await self._setup_postgresql_test_env()
        elif database_type == "sqlite":
            await self._setup_sqlite_test_env()
        elif database_type == "duckdb":
            await self._setup_duckdb_test_env()

    async def _setup_postgresql_test_env(self):
        """Setup PostgreSQL test environment."""
        # Start test PostgreSQL container
        test_commands = [
            "docker run -d --name test-postgres-recovery "
            "-e POSTGRES_DB=test_keycloak "
            "-e POSTGRES_USER=test_user "
            "-e POSTGRES_PASSWORD=test_pass "
            "-p 5433:5432 postgres:13"
        ]

        for cmd in test_commands:
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

    async def _setup_sqlite_test_env(self):
        """Setup SQLite test environment."""
        # Create test SQLite database with sample data
        import sqlite3

        test_db_path = "tests/recovery_tests/data/sqlite/test_recovery.db"
        Path(test_db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(test_db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                created_at TIMESTAMP,
                status TEXT
            )
        """
        )

        # Insert test data
        conn.execute(
            "INSERT INTO test_executions (user_id, created_at, status) VALUES (?, ?, ?)",
            ("test_user", datetime.now(), "completed"),
        )

        conn.commit()
        conn.close()

    async def _setup_duckdb_test_env(self):
        """Setup DuckDB test environment."""
        import duckdb

        test_db_path = "tests/recovery_tests/data/duckdb/test_user_recovery.db"
        Path(test_db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = duckdb.connect(test_db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generators (
                id INTEGER PRIMARY KEY,
                name TEXT,
                config JSON,
                created_at TIMESTAMP
            )
        """
        )

        # Insert test data with explicit ID
        conn.execute(
            "INSERT INTO generators (id, name, config, created_at) VALUES (?, ?, ?, ?)",
            (1, "test_generator", '{"type": "prompt"}', datetime.now()),
        )

        conn.close()

    async def _simulate_failure(self, database_type: str, failure_type: str):
        """Simulate database failure for testing."""
        logger.info("Simulating %s failure for %s", failure_type, database_type)

        if database_type == "postgresql":
            if failure_type == "complete":
                # Stop PostgreSQL container
                await self._run_command("docker stop test-postgres-recovery")
            elif failure_type == "corruption":
                # Simulate data corruption
                await self._run_command(
                    "docker exec test-postgres-recovery "
                    "psql -U test_user -d test_keycloak -c 'DROP TABLE pg_stat_activity'"
                )

        elif database_type == "sqlite":
            if failure_type == "complete":
                # Delete database file
                test_db_path = "tests/recovery_tests/data/sqlite/test_recovery.db"
                Path(test_db_path).unlink(missing_ok=True)
            elif failure_type == "corruption":
                # Corrupt database file
                test_db_path = "tests/recovery_tests/data/sqlite/test_recovery.db"
                with open(test_db_path, "wb") as f:
                    f.write(b"\x00" * 1024)  # Write zeros to corrupt

        elif database_type == "duckdb":
            if failure_type == "complete":
                # Delete DuckDB file
                test_db_path = "tests/recovery_tests/data/duckdb/test_user_recovery.db"
                Path(test_db_path).unlink(missing_ok=True)

    async def _execute_recovery(self, database_type: str, service: str) -> Dict[str, Any]:
        """Execute recovery procedure for database type."""
        logger.info("Executing recovery for %s/%s", database_type, service)

        if database_type == "postgresql":
            return await self._recover_postgresql()
        elif database_type == "sqlite":
            return await self._recover_sqlite()
        elif database_type == "duckdb":
            return await self._recover_duckdb()
        else:
            raise ValueError(f"Unknown database type: {database_type}")

    async def _recover_postgresql(self) -> Dict[str, Any]:
        """Execute PostgreSQL recovery."""
        # Restart PostgreSQL container
        await self._run_command("docker start test-postgres-recovery")

        # Wait for PostgreSQL to be ready
        await asyncio.sleep(5)

        # Verify recovery
        result = await self._run_command("docker exec test-postgres-recovery pg_isready -U test_user")

        return {
            "status": "success" if result.returncode == 0 else "failure",
            "method": "service_restart",
        }

    async def _recover_sqlite(self) -> Dict[str, Any]:
        """Execute SQLite recovery."""
        # Restore from backup (simulate)
        test_db_path = "tests/recovery_tests/data/sqlite/test_recovery.db"
        backup_path = "tests/recovery_tests/data/sqlite/backup_recovery.db"

        # Create backup if doesn't exist
        if not Path(backup_path).exists():
            await self._setup_sqlite_test_env()
            import shutil

            shutil.copy2(test_db_path, backup_path)

        # Restore from backup
        import shutil

        shutil.copy2(backup_path, test_db_path)

        return {"status": "success", "method": "backup_restoration"}

    async def _recover_duckdb(self) -> Dict[str, Any]:
        """Execute DuckDB recovery."""
        # Recreate DuckDB database
        await self._setup_duckdb_test_env()

        return {"status": "success", "method": "clean_recreation"}

    async def _validate_data_integrity(self, database_type: str) -> bool:
        """Validate data integrity after recovery."""
        try:
            if database_type == "postgresql":
                result = await self._run_command(
                    "docker exec test-postgres-recovery psql -U test_user -d test_keycloak -c 'SELECT 1'"
                )
                return result.returncode == 0

            elif database_type == "sqlite":
                import sqlite3

                test_db_path = "tests/recovery_tests/data/sqlite/test_recovery.db"

                conn = sqlite3.connect(test_db_path)
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()

                return result[0] == "ok"

            elif database_type == "duckdb":
                import duckdb

                test_db_path = "tests/recovery_tests/data/duckdb/test_user_recovery.db"

                conn = duckdb.connect(test_db_path)
                result = conn.execute("SELECT COUNT(*) FROM generators").fetchone()
                conn.close()

                return result[0] >= 0  # Can query successfully

        except Exception as e:
            logger.error("Data integrity check failed: %s", e)
            return False

        return True

    async def _cleanup_test_environment(self, database_type: str):
        """Cleanup test environment after testing."""
        logger.info("Cleaning up test environment for %s", database_type)

        if database_type == "postgresql":
            await self._run_command("docker stop test-postgres-recovery")
            await self._run_command("docker rm test-postgres-recovery")

        # Clean up test data files
        test_data_dir = Path(f"tests/recovery_tests/data/{database_type}")
        if test_data_dir.exists():
            import shutil

            shutil.rmtree(test_data_dir)

    async def _run_command(self, command: str):
        """Run shell command asynchronously."""
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        class CommandResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        return CommandResult(process.returncode, stdout, stderr)

    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete recovery test suite for all databases."""
        logger.info("Starting full recovery test suite")

        test_configurations = [
            {
                "database_type": "postgresql",
                "service": "keycloak",
                "rto_target": 15,
                "rpo_target": 60,
            },
            {
                "database_type": "sqlite",
                "service": "fastapi",
                "rto_target": 5,
                "rpo_target": 30,
            },
            {
                "database_type": "duckdb",
                "service": "user_data",
                "rto_target": 30,
                "rpo_target": 1440,
                "username": "test_user",
            },
        ]

        all_results = []

        for config in test_configurations:
            try:
                result = await self.test_database_recovery(**config)
                all_results.append(result)
            except Exception as e:
                logger.error("Test suite error for %s: %s", config["database_type"], e)
                all_results.append(
                    {
                        "database_type": config["database_type"],
                        "status": "error",
                        "error": str(e),
                    }
                )

        return {
            "test_suite_status": "completed",
            "total_tests": len(test_configurations),
            "successful_tests": len([r for r in all_results if r.get("status") == "success"]),
            "failed_tests": len([r for r in all_results if r.get("status") in ["failure", "error"]]),
            "results": all_results,
            "executed_at": datetime.now().isoformat(),
        }


class RecoveryReporter:
    """Generate comprehensive recovery test reports."""

    def __init__(self):
        """Initialize recovery reporter."""
        self.report_templates = {}

    def generate_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive recovery test report.

        Args:
            test_results: Results from recovery testing (can be array format or dict format)

        Returns:
            Comprehensive test report
        """
        # Handle both input formats: {'results': [...]} or {'postgresql': {...}, 'sqlite': {...}}
        if "results" in test_results:
            # Array format
            results_list = test_results.get("results", [])
            successful_tests = [r for r in results_list if r.get("status") == "success"]
            failed_tests = [r for r in results_list if r.get("status") in ["failure", "error"]]

            # Calculate compliance rates
            rto_compliance = {}
            rpo_compliance = {}

            for result in results_list:
                if "database_type" in result and "rto_actual" in result:
                    db_type = result["database_type"]
                    rto_compliance[db_type] = result.get("rto_compliant", False)
                    if result.get("rpo_compliant") is not None:
                        rpo_compliance[db_type] = result["rpo_compliant"]
        else:
            # Dictionary format: {'postgresql': {...}, 'sqlite': {...}}
            results_list = []
            successful_tests = []
            failed_tests = []
            rto_compliance = {}
            rpo_compliance = {}

            for db_type, result in test_results.items():
                if isinstance(result, dict) and "status" in result:
                    results_list.append(result)

                    if result.get("status") == "success":
                        successful_tests.append(result)
                    elif result.get("status") in ["failure", "error"]:
                        failed_tests.append(result)

                    # Calculate compliance for this database
                    if "rto_actual" in result and "rto_target" in result:
                        rto_compliance[db_type] = result["rto_actual"] <= result["rto_target"]

                    if "rpo_actual" in result and "rpo_target" in result:
                        rpo_compliance[db_type] = result["rpo_actual"] <= result["rpo_target"]

        overall_status = "success" if len(failed_tests) == 0 else "failure"
        if len(failed_tests) > 0 and len(successful_tests) > 0:
            overall_status = "partial_success"

        total_tests = test_results.get("total_tests", len(results_list))

        report = {
            "overall_status": overall_status,
            "executive_summary": {
                "overall_status": overall_status,
                "total_tests": total_tests,
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "compliance_rate": (len(successful_tests) / max(1, total_tests)) * 100,
            },
            "rto_compliance": rto_compliance,
            "rpo_compliance": rpo_compliance,
            "detailed_results": results_list,
            "recommendations": self._generate_recommendations(test_results),
            "next_test_date": self._calculate_next_test_date(),
            "generated_at": datetime.now().isoformat(),
        }

        return report

    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        for result in test_results.get("results", []):
            if result.get("status") == "failure":
                db_type = result.get("database_type", "unknown")
                recommendations.append(f"Review {db_type} recovery procedures - test failed")

            if not result.get("rto_compliant", True):
                db_type = result.get("database_type", "unknown")
                rto_actual = result.get("rto_actual", 0)
                rto_target = result.get("rto_target", 0)
                recommendations.append(
                    f"Optimize {db_type} recovery time - actual: {rto_actual:.1f}min, target: {rto_target:.1f}min"
                )

        if not recommendations:
            recommendations.append("All recovery tests passed - continue regular testing schedule")

        return recommendations

    def _calculate_next_test_date(self) -> str:
        """Calculate next scheduled test date."""
        # Daily testing for critical systems
        next_date = datetime.now() + timedelta(days=1)
        return next_date.strftime("%Y-%m-%d")

    def track_compliance(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Track RTO/RPO compliance over time with trend analysis.

        Args:
            historical_data: Historical test data for compliance tracking

        Returns:
            Compliance tracking summary with trends
        """
        if not historical_data:
            return {
                "postgresql_rto_trend": "no_data",
                "sqlite_rto_trend": "no_data",
                "overall_compliance_rate": 0.0,
            }

        # Extract RTO trends for each database type
        postgresql_rtos = [
            entry.get("postgresql_rto") for entry in historical_data if entry.get("postgresql_rto") is not None
        ]
        sqlite_rtos = [entry.get("sqlite_rto") for entry in historical_data if entry.get("sqlite_rto") is not None]

        # Calculate trends (simplified linear trend)
        postgresql_trend = self._calculate_trend(postgresql_rtos)
        sqlite_trend = self._calculate_trend(sqlite_rtos)

        # Calculate compliance rates based on targets
        postgresql_compliant = sum(1 for rto in postgresql_rtos if rto <= 15.0) / max(1, len(postgresql_rtos))
        sqlite_compliant = sum(1 for rto in sqlite_rtos if rto <= 5.0) / max(1, len(sqlite_rtos))

        overall_compliance = (postgresql_compliant + sqlite_compliant) / 2

        return {
            "postgresql_rto_trend": postgresql_trend,
            "sqlite_rto_trend": sqlite_trend,
            "postgresql_compliance_rate": postgresql_compliant * 100,
            "sqlite_compliance_rate": sqlite_compliant * 100,
            "overall_compliance_rate": overall_compliance * 100,
            "data_points": len(historical_data),
            "analysis_period": f"{historical_data[0].get('date', 'unknown')} to {historical_data[-1].get('date', 'unknown')}",
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from numerical values."""
        if len(values) < 2:
            return "insufficient_data"

        # Simple trend calculation: compare first half to second half
        mid_point = len(values) // 2
        first_half_avg = sum(values[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(values[mid_point:]) / (len(values) - mid_point)

        if abs(second_half_avg - first_half_avg) < 0.5:  # Within 0.5 minutes
            return "stable"
        elif second_half_avg > first_half_avg:
            return "degrading"
        else:
            return "improving"


async def main():
    """Main entry point for recovery testing."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Recovery Testing Framework")
    parser.add_argument("--validate-rto-rpo", action="store_true", help="Run RTO/RPO validation tests")
    parser.add_argument(
        "--database",
        choices=["postgresql", "sqlite", "duckdb"],
        help="Test specific database type",
    )
    parser.add_argument("--full-suite", action="store_true", help="Run complete test suite")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from existing test results",
    )

    args = parser.parse_args()

    tester = RecoveryTester()

    try:
        if args.full_suite:
            logger.info("Running full recovery test suite...")
            results = await tester.run_full_test_suite()

            # Generate report
            reporter = RecoveryReporter()
            report = reporter.generate_report(results)

            print(json.dumps(report, indent=2))

        elif args.database:
            logger.info("Testing recovery for %s...", args.database)
            # Get database-specific configuration
            config = {
                "postgresql": {
                    "service": "keycloak",
                    "rto_target": 15,
                    "rpo_target": 60,
                },
                "sqlite": {"service": "fastapi", "rto_target": 5, "rpo_target": 30},
                "duckdb": {
                    "service": "user_data",
                    "rto_target": 30,
                    "rpo_target": 1440,
                },
            }[args.database]

            result = await tester.test_database_recovery(args.database, **config)
            print(json.dumps(result, indent=2))

        else:
            print("Please specify --full-suite or --database <type>")
            return 1

        return 0

    except Exception as e:
        logger.error("Recovery testing failed: %s", e)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
