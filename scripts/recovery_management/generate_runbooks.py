#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Emergency Runbook Generation - Issue #268

Generates comprehensive emergency response runbooks for all recovery scenarios.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RunbookGenerator:
    """Generates emergency response runbooks for database recovery procedures."""

    def __init__(self, output_dir: str = "docs/runbooks") -> None:
        """Initialize runbook generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.runbooks = {}

    def generate_all_runbooks(self) -> Dict[str, Dict[str, Any]]:
        """Generate all emergency response runbooks."""
        logger.info("Generating all emergency response runbooks")

        self.runbooks = {
            "postgresql_failure": self.generate_postgresql_runbook(),
            "sqlite_corruption": self.generate_sqlite_runbook(),
            "duckdb_user_failure": self.generate_duckdb_runbook(),
            "cross_database_inconsistency": self.generate_cross_database_runbook(),
            "complete_system_failure": self.generate_complete_system_runbook(),
        }

        # Save runbooks to files
        for runbook_name, runbook_content in self.runbooks.items():
            self._save_runbook(runbook_name, runbook_content)

        return self.runbooks

    def generate_postgresql_runbook(self) -> Dict[str, Any]:
        """Generate PostgreSQL (Keycloak) failure recovery runbook."""
        return {
            "title": "PostgreSQL (Keycloak) Failure Recovery",
            "database_type": "postgresql",
            "service": "keycloak",
            "rto_target": 15,  # minutes
            "rpo_target": 60,  # minutes
            "severity": "critical",
            "last_updated": datetime.now().isoformat(),
            "detection": {
                "symptoms": [
                    "Users cannot authenticate",
                    "Keycloak admin console inaccessible",
                    "HTTP 503 errors from authentication endpoints",
                    "PostgreSQL connection errors in logs",
                ],
                "monitoring_commands": [
                    {
                        "command": "curl -f http://localhost:8080/auth/realms/violentutf/protocol/openid_connect/certs",
                        "expected_result": "HTTP 200 with JSON response",
                        "failure_indication": "HTTP error or timeout",
                    },
                    {
                        "command": "docker ps | grep keycloak",
                        "expected_result": "Container running and healthy",
                        "failure_indication": "Container stopped or restarting",
                    },
                    {
                        "command": "pg_isready -h localhost -p 5432 -U keycloak",
                        "expected_result": "accepting connections",
                        "failure_indication": "no response or rejection",
                    },
                ],
                "health_check_endpoints": [
                    "http://localhost:8080/auth/realms/violentutf",
                    "http://localhost:8080/auth/admin",
                ],
                "log_locations": [
                    "keycloak/logs/keycloak.log",
                    "docker logs keycloak-postgres",
                ],
            },
            "immediate_response": {
                "alert_team": "Database and Security teams",
                "escalation_trigger": "RTO > 10 minutes",
                "initial_actions": [
                    {
                        "action": "Activate incident response",
                        "command": (
                            "python3 scripts/recovery-management/incident_response.py "
                            "--database postgresql --severity critical"
                        ),
                        "timeout": "2 minutes",
                    },
                    {
                        "action": "Enable cached authentication mode",
                        "command": "python3 violentutf/utils/auth_utils_keycloak.py --enable-cached-mode",
                        "timeout": "1 minute",
                    },
                    {
                        "action": "Notify users of degraded service",
                        "command": (
                            "python3 scripts/recovery-management/notify_users.py "
                            "--service keycloak --status degraded"
                        ),
                        "timeout": "2 minutes",
                    },
                ],
            },
            "recovery_steps": [
                {
                    "step_number": 1,
                    "title": "Assess PostgreSQL container status",
                    "description": "Determine if PostgreSQL container is running and accessible",
                    "commands": [
                        "docker ps | grep postgres",
                        "docker logs keycloak-postgres | tail -20",
                        "pg_isready -h localhost -p 5432 -U keycloak",
                    ],
                    "expected_result": "Container status and PostgreSQL availability determined",
                    "estimated_time_minutes": 2,
                    "troubleshooting": {
                        "container_stopped": "docker start keycloak-postgres",
                        "container_crashed": "docker-compose -f keycloak/docker-compose.yml up -d postgres",
                        "connection_refused": "Check PostgreSQL configuration and logs",
                    },
                },
                {
                    "step_number": 2,
                    "title": "Stop dependent services",
                    "description": "Stop Keycloak and dependent services to prevent data corruption",
                    "commands": [
                        "docker-compose -f keycloak/docker-compose.yml down",
                        'docker ps | grep -E "(keycloak|violentutf)"',
                    ],
                    "expected_result": "All Keycloak services stopped cleanly",
                    "estimated_time_minutes": 2,
                    "troubleshooting": {
                        "containers_not_stopping": "docker kill $(docker ps -q --filter name=keycloak)",
                        "services_still_running": "Check for external connections and force stop if needed",
                    },
                },
                {
                    "step_number": 3,
                    "title": "Create current database backup",
                    "description": "Backup current state before recovery attempts",
                    "commands": [
                        "mkdir -p backups/emergency/$(date +%Y%m%d_%H%M%S)",
                        (
                            "docker exec keycloak-postgres pg_dump -U keycloak keycloak > "
                            "backups/emergency/$(date +%Y%m%d_%H%M%S)/pre_recovery.sql || "
                            'echo "Backup failed - database may be corrupted"'
                        ),
                    ],
                    "expected_result": "Current state backed up or corruption confirmed",
                    "estimated_time_minutes": 3,
                    "troubleshooting": {
                        "backup_fails": "Database likely corrupted - proceed with restore from known good backup",
                        "insufficient_disk": "Clean up old backups or use alternative storage",
                    },
                },
                {
                    "step_number": 4,
                    "title": "Restore from latest backup",
                    "description": "Restore PostgreSQL from most recent known-good backup",
                    "commands": [
                        "LATEST_BACKUP=$(ls -t backups/postgresql/*.sql | head -1)",
                        'echo "Restoring from: $LATEST_BACKUP"',
                        "docker exec keycloak-postgres dropdb -U keycloak keycloak --if-exists",
                        "docker exec keycloak-postgres createdb -U keycloak keycloak",
                        'docker exec -i keycloak-postgres psql -U keycloak -d keycloak < "$LATEST_BACKUP"',
                    ],
                    "expected_result": "Database restored from backup",
                    "estimated_time_minutes": 8,
                    "troubleshooting": {
                        "no_backup_found": "Check alternative backup locations: scripts/backup_management/backups/",
                        "restore_fails": "Try older backup or initiate manual database reconstruction",
                        "permission_errors": "Verify Docker container permissions and volume mounts",
                    },
                },
                {
                    "step_number": 5,
                    "title": "Restart PostgreSQL and Keycloak",
                    "description": "Start services in correct order",
                    "commands": [
                        "docker-compose -f keycloak/docker-compose.yml up -d postgres",
                        "sleep 10",
                        "docker-compose -f keycloak/docker-compose.yml up -d keycloak",
                        "sleep 15",
                    ],
                    "expected_result": "Services started and initializing",
                    "estimated_time_minutes": 2,
                    "troubleshooting": {
                        "postgres_wont_start": "Check database corruption, disk space, and configuration",
                        "keycloak_startup_fails": "Check logs for database connection errors",
                    },
                },
            ],
            "validation": {
                "health_checks": [
                    {
                        "check": "PostgreSQL connection",
                        "command": "pg_isready -h localhost -p 5432 -U keycloak",
                        "expected": "accepting connections",
                    },
                    {
                        "check": "Keycloak authentication endpoint",
                        "command": "curl -f http://localhost:8080/auth/realms/violentutf/protocol/openid_connect/certs",
                        "expected": "HTTP 200 with valid JSON",
                    },
                    {
                        "check": "Admin console access",
                        "command": "curl -f http://localhost:8080/auth/admin/",
                        "expected": "HTTP 200",
                    },
                    {
                        "check": "User count validation",
                        "command": (
                            "docker exec keycloak-postgres psql -U keycloak -d keycloak -c "
                            '"SELECT COUNT(*) FROM user_entity"'
                        ),
                        "expected": "Non-zero user count",
                    },
                ],
                "functional_tests": [
                    "Authenticate test user",
                    "Create new user session",
                    "Validate JWT token generation",
                    "Test PyRIT integration authentication",
                ],
                "performance_validation": {
                    "rto_check": "Verify total recovery time <= 15 minutes",
                    "response_time": "Authentication endpoints respond within 2 seconds",
                    "throughput": "Handle normal authentication load",
                },
            },
            "escalation": {
                "rto_breach_15min": "Contact Database Administrator and Infrastructure Team",
                "multiple_restore_failures": "Engage vendor support and consider disaster recovery site",
                "data_corruption_detected": "Contact Security team and preserve forensic evidence",
                "complete_failure": "Activate business continuity plan",
            },
            "rollback_procedures": [
                {
                    "trigger": "Restored backup causes authentication failures",
                    "steps": [
                        "Stop Keycloak services",
                        "Restore from previous known-good backup",
                        "Restart services",
                        "Validate functionality",
                    ],
                },
                {
                    "trigger": "Service degradation after recovery",
                    "steps": [
                        "Revert to cached authentication mode",
                        "Investigate root cause",
                        "Plan maintenance window for proper fix",
                    ],
                },
            ],
            "communication_templates": {
                "initial_alert": {
                    "subject": "CRITICAL: Authentication services unavailable",
                    "body": (
                        "Keycloak authentication system is currently unavailable. "
                        "Users cannot log in. Recovery in progress. ETA: 15 minutes."
                    ),
                },
                "recovery_complete": {
                    "subject": "RESOLVED: Authentication services restored",
                    "body": (
                        "Keycloak authentication system has been restored. "
                        "All services operational. Recovery time: {duration} minutes."
                    ),
                },
            },
        }

    def generate_sqlite_runbook(self) -> Dict[str, Any]:
        """Generate SQLite (FastAPI) corruption recovery runbook."""
        return {
            "title": "SQLite (FastAPI) Corruption Recovery",
            "database_type": "sqlite",
            "service": "fastapi",
            "rto_target": 5,  # minutes
            "rpo_target": 30,  # minutes
            "severity": "high",
            "last_updated": datetime.now().isoformat(),
            "detection": {
                "symptoms": [
                    "API endpoints returning HTTP 500 errors",
                    "Database corruption errors in FastAPI logs",
                    "SQLite integrity check failures",
                    "Application data inconsistencies",
                ],
                "monitoring_commands": [
                    {
                        "command": "curl -f http://localhost:9080/health",
                        "expected_result": "HTTP 200 with healthy status",
                        "failure_indication": "HTTP error or database connection failure",
                    },
                    {
                        "command": 'sqlite3 violentutf_api/fastapi_app/app_database.db "PRAGMA integrity_check"',
                        "expected_result": "ok",
                        "failure_indication": "corruption errors or exceptions",
                    },
                ],
            },
            "corruption_detection": {
                "integrity_check": 'sqlite3 database.db "PRAGMA integrity_check"',
                "table_validation": 'sqlite3 database.db ".tables"',
                "record_count": "sqlite3 database.db \"SELECT COUNT(*) FROM sqlite_master WHERE type='table'\"",
            },
            "repair_procedures": {
                "integrity_check": 'sqlite3 database.db "PRAGMA integrity_check"',
                "sqlite_recover_command": 'sqlite3 corrupted.db ".recover" | sqlite3 repaired.db',
                "validation_queries": [
                    "SELECT COUNT(*) FROM executions",
                    "SELECT COUNT(*) FROM sessions",
                    "PRAGMA foreign_key_check",
                ],
            },
            "backup_restoration": {
                "find_latest": "ls -t backups/sqlite/*.db | head -1",
                "restore_command": 'cp "$LATEST_BACKUP" violentutf_api/fastapi_app/app_database.db',
                "service_restart": "docker-compose -f violentutf_api/docker-compose.yml restart",
            },
            "data_reconstruction": {
                "sources": [
                    "DuckDB user databases",
                    "Log files",
                    "Configuration files",
                ],
                "rebuild_script": "python3 scripts/recovery-management/rebuild_sqlite.py",
            },
            "recovery_steps": [
                {
                    "step_number": 1,
                    "title": "Stop FastAPI service",
                    "description": "Prevent further corruption by stopping the service",
                    "commands": ["docker-compose -f violentutf_api/docker-compose.yml down"],
                    "expected_result": "FastAPI container stopped",
                    "estimated_time_minutes": 1,
                },
                {
                    "step_number": 2,
                    "title": "Assess database corruption level",
                    "description": "Determine extent of corruption and recovery method",
                    "commands": [
                        'sqlite3 violentutf_api/fastapi_app/app_database.db "PRAGMA integrity_check"',
                        'sqlite3 violentutf_api/fastapi_app/app_database.db ".tables"',
                    ],
                    "expected_result": "Corruption extent determined",
                    "estimated_time_minutes": 1,
                },
                {
                    "step_number": 3,
                    "title": "Attempt database repair",
                    "description": "Try to repair using SQLite recover command",
                    "commands": [
                        'sqlite3 violentutf_api/fastapi_app/app_database.db ".recover" > recovered.sql',
                        "sqlite3 violentutf_api/fastapi_app/app_database_repaired.db < recovered.sql",
                        'sqlite3 violentutf_api/fastapi_app/app_database_repaired.db "PRAGMA integrity_check"',
                    ],
                    "expected_result": "Repaired database or repair failure confirmed",
                    "estimated_time_minutes": 2,
                },
                {
                    "step_number": 4,
                    "title": "Restore from backup if repair fails",
                    "description": "Use latest backup if repair was unsuccessful",
                    "commands": [
                        "LATEST_BACKUP=$(ls -t backups/sqlite/*.db | head -1)",
                        'cp "$LATEST_BACKUP" violentutf_api/fastapi_app/app_database.db',
                    ],
                    "expected_result": "Database restored from backup",
                    "estimated_time_minutes": 1,
                },
            ],
            "validation": {
                "integrity_validation": 'sqlite3 database.db "PRAGMA integrity_check"',
                "api_health_check": "curl -f http://localhost:9080/health",
                "functional_test": "curl -f http://localhost:9080/api/v1/status",
            },
        }

    def generate_duckdb_runbook(self) -> Dict[str, Any]:
        """Generate DuckDB user database recovery runbook."""
        return {
            "title": "DuckDB User Database Recovery",
            "database_type": "duckdb",
            "service": "user_data",
            "rto_target": 30,  # variable based on user criticality
            "rpo_target": 1440,  # 24 hours
            "severity": "medium",
            "last_updated": datetime.now().isoformat(),
            "user_impact_assessment": {
                "identify_affected_users": "ls -la ./app_data/violentutf/pyrit_memory_*.db",
                "assess_criticality": "Check user activity and data importance",
                "prioritize_recovery": "Critical users first, then by data volume",
            },
            "pyrit_data_recovery": {
                "extract_generators": "SELECT * FROM generators",
                "extract_datasets": "SELECT * FROM datasets",
                "extract_scorers": "SELECT * FROM scorers",
                "validate_schema": "Check table structure integrity",
            },
            "user_notification": {
                "template": "User database recovery in progress",
                "channels": ["Email", "In-app notification", "Recovery status page"],
                "updates": "Progress updates every 10 minutes",
            },
            "recovery_steps": [
                {
                    "step_number": 1,
                    "title": "Identify affected user databases",
                    "description": "List all user DuckDB files and assess status",
                    "commands": [
                        "ls -la ./app_data/violentutf/pyrit_memory_*.db",
                        (
                            'python3 -c "import duckdb; '
                            "[print(f'{f}: {duckdb.connect(f).execute("
                            '\\"SELECT COUNT(*) FROM information_schema.tables\\").fetchone()[0]} tables\') '
                            "for f in glob.glob('./app_data/violentutf/pyrit_memory_*.db')]\""
                        ),
                    ],
                    "expected_result": "List of user databases and their status",
                    "estimated_time_minutes": 5,
                },
                {
                    "step_number": 2,
                    "title": "Backup corrupted databases",
                    "description": "Create backups before attempting recovery",
                    "commands": [
                        "mkdir -p backups/duckdb/corrupted/$(date +%Y%m%d_%H%M%S)",
                        "cp ./app_data/violentutf/pyrit_memory_*.db backups/duckdb/corrupted/$(date +%Y%m%d_%H%M%S)/",
                    ],
                    "expected_result": "Corrupted databases backed up",
                    "estimated_time_minutes": 5,
                },
                {
                    "step_number": 3,
                    "title": "Attempt data extraction from corrupted databases",
                    "description": "Extract recoverable data before recreation",
                    "commands": [
                        "python3 scripts/recovery-management/extract_duckdb_data.py --all-users",
                        "python3 scripts/recovery-management/validate_extracted_data.py",
                    ],
                    "expected_result": "Recoverable data extracted and validated",
                    "estimated_time_minutes": 15,
                },
                {
                    "step_number": 4,
                    "title": "Recreate user databases with clean schema",
                    "description": "Create new databases with proper PyRIT schema",
                    "commands": [
                        "python3 scripts/recovery-management/recreate_user_databases.py --all",
                        "python3 scripts/recovery-management/restore_extracted_data.py",
                    ],
                    "expected_result": "Clean user databases created",
                    "estimated_time_minutes": 10,
                },
            ],
        }

    def generate_cross_database_runbook(self) -> Dict[str, Any]:
        """Generate cross-database consistency recovery runbook."""
        return {
            "title": "Cross-Database Consistency Recovery",
            "scope": "multi_database",
            "rto_target": 20,  # minutes
            "severity": "high",
            "last_updated": datetime.now().isoformat(),
            "dependency_analysis": {
                "service_dependencies": {
                    "keycloak": "No dependencies",
                    "fastapi": "Depends on Keycloak",
                    "user_services": "Depends on Keycloak and FastAPI",
                },
                "data_dependencies": {
                    "user_sessions": "Keycloak → SQLite → DuckDB",
                    "authentication_flow": "PostgreSQL → API calls → User data",
                },
            },
            "compensating_transactions": {
                "user_data_mismatch": "Sync user data across all databases",
                "session_inconsistency": "Rebuild sessions from authoritative source",
                "orphaned_records": "Clean up orphaned data",
            },
            "consistency_validation": {
                "user_count_check": "Compare user counts across databases",
                "session_sync_check": "Validate session consistency",
                "data_integrity_check": "Cross-reference critical data",
            },
        }

    def generate_complete_system_runbook(self) -> Dict[str, Any]:
        """Generate complete system failure recovery runbook."""
        return {
            "title": "Complete System Failure Recovery",
            "scope": "system_wide",
            "rto_target": 45,  # minutes
            "severity": "critical",
            "last_updated": datetime.now().isoformat(),
            "recovery_sequence": [
                "Infrastructure assessment",
                "PostgreSQL recovery",
                "SQLite recovery",
                "User data recovery",
                "Service validation",
                "User notification",
            ],
            "parallel_operations": {
                "infrastructure": "Docker and network setup",
                "database_prep": "Prepare backup restoration",
                "communication": "User and stakeholder notification",
            },
            "success_criteria": {
                "authentication_functional": True,
                "api_endpoints_responsive": True,
                "user_data_accessible": True,
                "rto_met": True,
                "data_loss_minimized": True,
            },
        }

    def generate_automation_scripts(self) -> Dict[str, str]:
        """Generate automation scripts for runbook procedures."""
        scripts = {}

        scripts["postgresql_recovery.sh"] = self._generate_postgresql_script()
        scripts["sqlite_recovery.sh"] = self._generate_sqlite_script()
        scripts["duckdb_recovery.sh"] = self._generate_duckdb_script()
        scripts["cross_database_recovery.sh"] = self._generate_cross_database_script()

        # Save scripts to files
        scripts_dir = Path("scripts/recovery-management/automation-scripts")
        scripts_dir.mkdir(parents=True, exist_ok=True)

        for script_name, script_content in scripts.items():
            script_path = scripts_dir / script_name
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            script_path.chmod(0o755)  # Make executable

        return scripts

    def _generate_postgresql_script(self) -> str:
        """Generate PostgreSQL recovery automation script."""
        return """#!/bin/bash
set -e

# PostgreSQL Recovery Automation Script
# Generated by ViolentUTF Recovery Framework

function log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/recovery.log
}

function validate_prerequisites() {
    log_message "Checking prerequisites for PostgreSQL recovery"

    # Check if Docker is running
    if ! docker ps >/dev/null 2>&1; then
        log_message "ERROR: Docker is not running"
        exit 1
    fi

    # Check if backup directory exists
    if [ ! -d "backups/postgresql" ]; then
        log_message "WARNING: PostgreSQL backup directory not found"
        mkdir -p backups/postgresql
    fi

    log_message "Prerequisites check completed"
}

function stop_services() {
    log_message "Stopping Keycloak services"
    docker-compose -f keycloak/docker-compose.yml down || true
    sleep 5
}

function restore_database() {
    log_message "Restoring PostgreSQL database from backup"

    LATEST_BACKUP=$(ls -t backups/postgresql/*.sql 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        log_message "ERROR: No PostgreSQL backup found"
        exit 1
    fi

    log_message "Using backup: $LATEST_BACKUP"

    # Start PostgreSQL container if not running
    docker-compose -f keycloak/docker-compose.yml up -d postgres
    sleep 10

    # Restore database
    docker exec -i keycloak-postgres psql -U keycloak -d postgres -c "DROP DATABASE IF EXISTS keycloak;"
    docker exec -i keycloak-postgres psql -U keycloak -d postgres -c "CREATE DATABASE keycloak;"
    docker exec -i keycloak-postgres psql -U keycloak -d keycloak < "$LATEST_BACKUP"

    log_message "Database restoration completed"
}

function start_services() {
    log_message "Starting Keycloak services"
    docker-compose -f keycloak/docker-compose.yml up -d
    sleep 15
}

function validate_recovery() {
    log_message "Validating PostgreSQL recovery"

    # Check PostgreSQL connection
    if ! pg_isready -h localhost -p 5432 -U keycloak >/dev/null 2>&1; then
        log_message "ERROR: PostgreSQL is not ready"
        return 1
    fi

    # Check Keycloak endpoint
    if ! curl -f -s http://localhost:8080/auth/realms/violentutf >/dev/null; then
        log_message "ERROR: Keycloak endpoint not responding"
        return 1
    fi

    log_message "Recovery validation successful"
    return 0
}

function cleanup() {
    log_message "Performing cleanup tasks"
    # Remove temporary files, reset permissions, etc.
}

function main() {
    log_message "Starting PostgreSQL recovery procedure"

    validate_prerequisites
    stop_services
    restore_database
    start_services

    if validate_recovery; then
        log_message "PostgreSQL recovery completed successfully"
        cleanup
        exit 0
    else
        log_message "PostgreSQL recovery validation failed"
        cleanup
        exit 1
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT

main "$@"
"""

    def _generate_sqlite_script(self) -> str:
        """Generate SQLite recovery automation script."""
        return """#!/bin/bash
set -e

# SQLite Recovery Automation Script
# Generated by ViolentUTF Recovery Framework

function log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/recovery.log
}

function validate_prerequisites() {
    log_message "Checking prerequisites for SQLite recovery"

    if [ ! -f "violentutf_api/fastapi_app/app_database.db" ]; then
        log_message "WARNING: SQLite database file not found"
    fi

    if [ ! -d "backups/sqlite" ]; then
        log_message "WARNING: SQLite backup directory not found"
        mkdir -p backups/sqlite
    fi
}

function stop_services() {
    log_message "Stopping FastAPI services"
    docker-compose -f violentutf_api/docker-compose.yml down || true
}

function backup_corrupted_database() {
    log_message "Backing up corrupted database"

    if [ -f "violentutf_api/fastapi_app/app_database.db" ]; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        cp violentutf_api/fastapi_app/app_database.db "backups/sqlite/corrupted_${TIMESTAMP}.db"
    fi
}

function attempt_repair() {
    log_message "Attempting SQLite database repair"

    if sqlite3 violentutf_api/fastapi_app/app_database.db ".recover" > /tmp/recovered.sql 2>/dev/null; then
        sqlite3 violentutf_api/fastapi_app/app_database_repaired.db < /tmp/recovered.sql

        if sqlite3 violentutf_api/fastapi_app/app_database_repaired.db "PRAGMA integrity_check" | grep -q "ok"; then
            mv violentutf_api/fastapi_app/app_database_repaired.db violentutf_api/fastapi_app/app_database.db
            log_message "Database repair successful"
            return 0
        fi
    fi

    log_message "Database repair failed"
    return 1
}

function restore_from_backup() {
    log_message "Restoring SQLite from backup"

    LATEST_BACKUP=$(ls -t backups/sqlite/*.db 2>/dev/null | grep -v corrupted | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        log_message "ERROR: No SQLite backup found"
        return 1
    fi

    cp "$LATEST_BACKUP" violentutf_api/fastapi_app/app_database.db
    log_message "Restored from backup: $LATEST_BACKUP"
    return 0
}

function start_services() {
    log_message "Starting FastAPI services"
    docker-compose -f violentutf_api/docker-compose.yml up -d
    sleep 10
}

function validate_recovery() {
    log_message "Validating SQLite recovery"

    # Check database integrity
    if ! sqlite3 violentutf_api/fastapi_app/app_database.db "PRAGMA integrity_check" | grep -q "ok"; then
        log_message "ERROR: Database integrity check failed"
        return 1
    fi

    # Check API health
    if ! curl -f -s http://localhost:9080/health >/dev/null; then
        log_message "ERROR: API health check failed"
        return 1
    fi

    log_message "Recovery validation successful"
    return 0
}

function cleanup() {
    log_message "Performing cleanup tasks"
    rm -f /tmp/recovered.sql
    rm -f violentutf_api/fastapi_app/app_database_repaired.db
}

function main() {
    log_message "Starting SQLite recovery procedure"

    validate_prerequisites
    stop_services
    backup_corrupted_database

    if ! attempt_repair; then
        if ! restore_from_backup; then
            log_message "ERROR: Both repair and backup restoration failed"
            cleanup
            exit 1
        fi
    fi

    start_services

    if validate_recovery; then
        log_message "SQLite recovery completed successfully"
        cleanup
        exit 0
    else
        log_message "SQLite recovery validation failed"
        cleanup
        exit 1
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT

main "$@"
"""

    def _generate_duckdb_script(self) -> str:
        """Generate DuckDB recovery automation script."""
        return """#!/bin/bash
set -e

# DuckDB Recovery Automation Script
# Generated by ViolentUTF Recovery Framework

function log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/recovery.log
}

function validate_prerequisites() {
    log_message "Checking prerequisites for DuckDB recovery"

    if [ ! -d "./app_data/violentutf" ]; then
        log_message "WARNING: DuckDB user data directory not found"
        mkdir -p ./app_data/violentutf
    fi

    if [ ! -d "backups/duckdb" ]; then
        log_message "WARNING: DuckDB backup directory not found"
        mkdir -p backups/duckdb
    fi

    log_message "Prerequisites check completed"
}

function identify_affected_users() {
    log_message "Identifying affected user databases"

    AFFECTED_DBS=$(find ./app_data/violentutf -name "pyrit_memory_*.db" -type f)
    if [ -z "$AFFECTED_DBS" ]; then
        log_message "No user databases found"
        return 0
    fi

    for db in $AFFECTED_DBS; do
        username=$(basename "$db" .db | sed 's/pyrit_memory_//')
        log_message "Found user database: $username"
    done
}

function backup_user_databases() {
    log_message "Backing up user databases"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "backups/duckdb/corrupted_${TIMESTAMP}"

    find ./app_data/violentutf -name "pyrit_memory_*.db" -type f \\
        -exec cp {} "backups/duckdb/corrupted_${TIMESTAMP}/" \\;
}

function recreate_user_databases() {
    log_message "Recreating user databases"

    python3 -c "
import glob
import os
from pathlib import Path

# Import DuckDBManager if available
try:
    from violentutf_api.fastapi_app.app.db.duckdb_manager import DuckDBManager

    for db_file in glob.glob('./app_data/violentutf/pyrit_memory_*.db'):
        username = Path(db_file).stem.replace('pyrit_memory_', '')
        print(f'Recreating database for user: {username}')

        # Remove corrupted database
        os.remove(db_file)

        # Create new clean database
        manager = DuckDBManager(username)
        print(f'Created clean database for {username}')

except ImportError:
    print('DuckDBManager not available - using fallback method')
    import duckdb

    for db_file in glob.glob('./app_data/violentutf/pyrit_memory_*.db'):
        username = Path(db_file).stem.replace('pyrit_memory_', '')
        print(f'Recreating database for user: {username}')

        # Remove corrupted database
        os.remove(db_file)

        # Create new database with basic schema
        conn = duckdb.connect(db_file)
        conn.execute('CREATE TABLE generators (id INTEGER, name TEXT, config TEXT)')
        conn.execute('CREATE TABLE datasets (id INTEGER, name TEXT, path TEXT)')
        conn.close()
        print(f'Created basic database for {username}')
"
}

function notify_users() {
    log_message "Notifying affected users"

    python3 scripts/recovery-management/notify_users.py --service duckdb --status recovered
}

function cleanup() {
    log_message "Performing cleanup tasks"
    # Remove temporary files if any
}

function main() {
    log_message "Starting DuckDB recovery procedure"

    validate_prerequisites
    identify_affected_users
    backup_user_databases
    recreate_user_databases
    notify_users

    log_message "DuckDB recovery completed successfully"
    cleanup
}

# Trap for cleanup on exit
trap cleanup EXIT

main "$@"
"""

    def _generate_cross_database_script(self) -> str:
        """Generate cross-database recovery automation script."""
        return """#!/bin/bash
set -e

# Cross-Database Recovery Automation Script
# Generated by ViolentUTF Recovery Framework

function log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/recovery.log
}

function validate_prerequisites() {
    log_message "Checking prerequisites for cross-database recovery"

    # Check if individual scripts exist
    required_scripts=(
        "scripts/recovery-management/automation-scripts/postgresql_recovery.sh"
        "scripts/recovery-management/automation-scripts/sqlite_recovery.sh"
        "scripts/recovery-management/automation-scripts/duckdb_recovery.sh"
    )

    for script in "${required_scripts[@]}"; do
        if [ ! -f "$script" ]; then
            log_message "ERROR: Required script not found: $script"
            exit 1
        fi
    done

    log_message "Prerequisites check completed"
}

function recovery_sequence() {
    log_message "Executing cross-database recovery sequence"

    # 1. PostgreSQL first (no dependencies)
    log_message "Step 1: PostgreSQL recovery"
    ./scripts/recovery-management/automation-scripts/postgresql_recovery.sh

    # 2. SQLite second (depends on PostgreSQL)
    log_message "Step 2: SQLite recovery"
    ./scripts/recovery-management/automation-scripts/sqlite_recovery.sh

    # 3. DuckDB third (depends on both)
    log_message "Step 3: DuckDB recovery"
    ./scripts/recovery-management/automation-scripts/duckdb_recovery.sh
}

function validate_consistency() {
    log_message "Validating cross-database consistency"

    python3 -c "
from scripts.recovery_management.database_recovery import CrossDatabaseRecovery
import asyncio

async def main():
    recovery = CrossDatabaseRecovery()
    result = await recovery.validate_cross_database_consistency()
    print(f'Consistency validation: {result}')

    if result.get('overall_consistency_score', 0) < 95:
        print('WARNING: Consistency issues detected')
        return 1

    return 0

exit(asyncio.run(main()))
"
}

function cleanup() {
    log_message "Performing cleanup tasks"
    # Remove temporary files if any
}

function main() {
    log_message "Starting cross-database recovery procedure"

    validate_prerequisites
    recovery_sequence

    if validate_consistency; then
        log_message "Cross-database recovery completed successfully"
        cleanup
        exit 0
    else
        log_message "Cross-database recovery validation failed"
        cleanup
        exit 1
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT

main "$@"
"""

    def validate_runbooks(self, runbooks: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated runbooks for completeness and accuracy."""
        validation_errors = []
        completeness_scores = []

        required_sections = ["title", "detection", "recovery_steps", "validation"]

        for runbook_name, runbook_content in runbooks.items():
            missing_sections = []

            for section in required_sections:
                if section not in runbook_content:
                    missing_sections.append(section)
                    validation_errors.append(f"{runbook_name}: Missing section '{section}'")

            # Calculate completeness score
            completeness = ((len(required_sections) - len(missing_sections)) / len(required_sections)) * 100
            completeness_scores.append(completeness)

            # Validate recovery steps structure
            if "recovery_steps" in runbook_content:
                steps = runbook_content["recovery_steps"]
                if isinstance(steps, list):
                    for i, step in enumerate(steps):
                        if "step_number" not in step:
                            validation_errors.append(f"{runbook_name}: Step {i+1} missing step_number")
                        if "commands" not in step:
                            validation_errors.append(f"{runbook_name}: Step {i+1} missing commands")

        overall_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0

        return {
            "valid": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "completeness_score": overall_completeness,
            "runbooks_validated": len(runbooks),
        }

    def _save_runbook(self, runbook_name: str, runbook_content: Dict[str, Any]) -> None:
        """Save runbook to file."""
        # Save as YAML
        yaml_file = self.output_dir / f"{runbook_name}.yml"
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(runbook_content, f, default_flow_style=False)

        # Save as JSON for programmatic access
        json_file = self.output_dir / f"{runbook_name}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(runbook_content, f, indent=2, default=str)

        logger.info("Saved runbook: %s", runbook_name)


class EmergencyResponseCoordinator:
    """Coordinates emergency response activities during incidents."""

    def __init__(self) -> None:
        """Initialize emergency response coordinator."""
        self.response_teams = {
            "database_team": ["DBA", "Database Engineer"],
            "infrastructure_team": ["DevOps", "SRE"],
            "security_team": ["Security Engineer", "Incident Commander"],
            "management": ["Team Lead", "Director"],
        }

    def classify_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Classify incident severity and required response."""
        service = incident.get("service", "unknown")
        impact_level = incident.get("impact_level", "medium")
        affected_users = incident.get("affected_users", "some")

        # Determine severity
        if service == "postgresql" or affected_users == "all":
            severity = "critical"
            response_team = "database_team"
            escalation_required = True
            estimated_rto = 15
        elif service == "sqlite" or impact_level == "high":
            severity = "high"
            response_team = "database_team"
            escalation_required = False
            estimated_rto = 5
        else:
            severity = "medium"
            response_team = "infrastructure_team"
            escalation_required = False
            estimated_rto = 30

        return {
            "severity": severity,
            "response_team": response_team,
            "escalation_required": escalation_required,
            "estimated_rto": estimated_rto,
            "classification_time": datetime.now().isoformat(),
        }

    def notify_response_team(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Notify appropriate response team."""
        severity = incident.get("severity", "medium")

        notification_channels = ["email"]
        if severity in ["critical", "high"]:
            notification_channels.append("slack")
            notification_channels.append("sms")

        return {
            "status": "sent",
            "notification_channels": notification_channels,
            "estimated_response_time": ("10 minutes" if severity == "critical" else "30 minutes"),
            "recipients": self._get_team_contacts(severity),
        }

    def check_escalation_triggers(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Check if escalation triggers have been met."""
        start_time = incident.get("start_time")
        rto_target = incident.get("rto_target", 30)

        escalation_required = False
        trigger_reason = None
        escalation_level = None

        if start_time:
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60

            if elapsed_minutes > rto_target:
                escalation_required = True
                trigger_reason = "rto_breach"
                escalation_level = "management"
            elif elapsed_minutes > rto_target * 0.75:
                escalation_required = True
                trigger_reason = "rto_warning"
                escalation_level = "senior_engineer"

        return {
            "escalation_required": escalation_required,
            "trigger_reason": trigger_reason,
            "escalation_level": escalation_level,
            "next_check_minutes": 5,
        }

    def generate_communication_templates(self, incident_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Generate communication templates for incident."""
        service = incident_data.get("service", "database")
        severity = incident_data.get("severity", "medium")
        impact = incident_data.get("impact", "service degradation")

        templates = {
            "initial_notification": {
                "subject": f"{severity.upper()}: {service} service incident",
                "body": f"""
{service} service is currently experiencing issues.

Impact: {impact}
Severity: {severity}
Estimated Resolution: {incident_data.get('estimated_resolution', 'unknown')}

Recovery team has been notified and is responding.
Updates will be provided every 15 minutes.

Incident ID: {incident_data.get('incident_id', 'N/A')}
""",
            },
            "status_update": {
                "subject": f"UPDATE: {service} service incident",
                "body": f"""
Update on {service} service incident:

Current Status: {{status}}
Progress: {{progress}}
Next Update: {{next_update}}

Recovery team continues to work on resolution.
""",
            },
            "resolution_notice": {
                "subject": f"RESOLVED: {service} service incident",
                "body": f"""
{service} service incident has been resolved.

Resolution Time: {{resolution_time}}
Root Cause: {{root_cause}}
Preventive Measures: {{preventive_measures}}

Service is now fully operational.
Post-incident review will be scheduled within 48 hours.
""",
            },
        }

        return templates

    def _get_team_contacts(self, severity: str) -> List[str]:
        """Get contact list based on severity."""
        if severity == "critical":
            return ["database_team", "infrastructure_team", "management"]
        elif severity == "high":
            return ["database_team", "infrastructure_team"]
        else:
            return ["database_team"]


async def main() -> int:
    """Generate runbooks and handle emergency response coordination."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Emergency Runbook Generator")
    parser.add_argument(
        "--emergency-procedures",
        action="store_true",
        help="Generate emergency response procedures",
    )
    parser.add_argument("--automation-scripts", action="store_true", help="Generate automation scripts")
    parser.add_argument("--validate", action="store_true", help="Validate generated runbooks")
    parser.add_argument("--output-dir", default="docs/runbooks", help="Output directory for runbooks")

    args = parser.parse_args()

    generator = RunbookGenerator(output_dir=args.output_dir)

    try:
        if args.emergency_procedures or not any([args.automation_scripts, args.validate]):
            logger.info("Generating emergency response procedures...")
            runbooks = generator.generate_all_runbooks()
            print(f"Generated {len(runbooks)} runbooks")

            if args.validate:
                validation_result = generator.validate_runbooks(runbooks)
                print(f"Validation result: {validation_result}")

        if args.automation_scripts:
            logger.info("Generating automation scripts...")
            scripts = generator.generate_automation_scripts()
            print(f"Generated {len(scripts)} automation scripts")

        logger.info("Runbook generation completed successfully")
        return 0

    except Exception as e:
        logger.error("Runbook generation failed: %s", e)
        return 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(main()))
