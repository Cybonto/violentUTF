"""
Test fixtures for change management tests.
Provides common test data, mocks, and utilities.
"""

import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path
import pytest
import sqlite3


@pytest.fixture
def sample_change_request() -> Dict[str, Any]:
    """Sample change request data for testing."""
    return {
        "title": "Add user preferences table",
        "description": "Add new table for storing user preferences",
        "change_type": "normal",
        "database": "postgresql",
        "risk_level": "medium",
        "impact_scope": ["keycloak", "api"],
        "submitter": "test_user",
        "timestamp": datetime.utcnow().isoformat(),
        "migration_file": "migrations/001_add_user_preferences.sql",
    }


@pytest.fixture
def sample_emergency_change() -> Dict[str, Any]:
    """Sample emergency change request."""
    return {
        "title": "Fix authentication deadlock",
        "description": "Emergency fix for deadlock in authentication flow",
        "change_type": "emergency",
        "database": "postgresql",
        "risk_level": "critical",
        "impact_scope": ["keycloak", "api", "streamlit"],
        "submitter": "oncall_engineer",
        "timestamp": datetime.utcnow().isoformat(),
        "hotfix_required": True,
    }


@pytest.fixture
def sample_major_change() -> Dict[str, Any]:
    """Sample major change request."""
    return {
        "title": "Migrate to new authentication architecture",
        "description": "Complete redesign of authentication system",
        "change_type": "major",
        "database": "multiple",
        "risk_level": "high",
        "impact_scope": ["keycloak", "api", "streamlit", "apisix"],
        "submitter": "architect",
        "timestamp": datetime.utcnow().isoformat(),
        "adr_required": True,
        "testing_required": True,
    }


@pytest.fixture
def sample_incident() -> Dict[str, Any]:
    """Sample incident data for testing."""
    return {
        "incident_id": "INC-2025-001",
        "incident_type": "database_failure",
        "severity": "critical",
        "database": "postgresql",
        "symptoms": [
            "Authentication unavailable",
            "HTTP 503 errors",
            "Database connection refused",
        ],
        "detected_at": datetime.utcnow().isoformat(),
        "rto_target": 15,
        "rpo_target": 60,
    }


@pytest.fixture
def sample_incident_p1() -> Dict[str, Any]:
    """Sample P1 incident."""
    return {
        "incident_id": "INC-2025-002",
        "incident_type": "performance_degradation",
        "severity": "high",
        "database": "sqlite",
        "symptoms": ["Slow query performance", "High CPU usage"],
        "detected_at": datetime.utcnow().isoformat(),
        "rto_target": 60,
        "rpo_target": 120,
    }


@pytest.fixture
def sample_adr() -> Dict[str, Any]:
    """Sample ADR data for testing."""
    return {
        "adr_number": 4,
        "title": "Change Management Framework",
        "status": "proposed",
        "context": "Need structured change management for database operations",
        "decision": "Implement approval workflow with risk-based routing",
        "consequences": {
            "positive": ["Reduced risk", "Better tracking"],
            "negative": ["Additional overhead"],
        },
        "author": "backend_engineer",
        "date": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def temp_sqlite_db(tmp_path: Path) -> Path:
    """Create temporary SQLite database for testing."""
    db_path = tmp_path / "test_database.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create sample schema
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Insert sample data
    cursor.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ("testuser", "test@example.com"),
    )
    cursor.execute(
        "INSERT INTO sessions (user_id, token) VALUES (?, ?)",
        (1, "test_token_123"),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def temp_config_files(tmp_path: Path) -> Dict[str, Path]:
    """Create temporary configuration files for testing."""
    yaml_config = tmp_path / "config.yml"
    yaml_config.write_text("""
database:
  host: localhost
  port: 5432
  name: testdb

security:
  encryption: true
  audit_logging: true
""")

    env_config = tmp_path / ".env"
    env_config.write_text("""
DATABASE_URL=postgresql://user:pass@localhost:5432/testdb
SECRET_KEY=test_secret_key_12345
API_KEY=test_api_key_67890
""")

    json_config = tmp_path / "settings.json"
    json_config.write_text("""{
    "app_name": "ViolentUTF",
    "version": "1.0.0",
    "debug": false,
    "max_connections": 100
}""")

    return {
        "yaml": yaml_config,
        "env": env_config,
        "json": json_config,
    }


@pytest.fixture
def mock_runbook() -> Dict[str, Any]:
    """Mock incident response runbook."""
    return {
        "title": "PostgreSQL Failure Recovery",
        "database_type": "postgresql",
        "severity": "critical",
        "rto_target": 15,
        "rpo_target": 60,
        "detection": {
            "symptoms": [
                "Database connection refused",
                "HTTP 503 from API",
            ],
            "monitoring_commands": [
                "pg_isready -h localhost -p 5432",
                "docker ps | grep postgres",
            ],
        },
        "recovery_steps": [
            {
                "step_number": 1,
                "title": "Assess database status",
                "commands": ["docker ps | grep postgres"],
                "estimated_time_minutes": 2,
            },
            {
                "step_number": 2,
                "title": "Restore from backup",
                "commands": ["python3 restore_backup.py --database postgresql"],
                "estimated_time_minutes": 8,
            },
        ],
    }


@pytest.fixture
def approval_matrix() -> Dict[str, Any]:
    """Approval matrix configuration."""
    return {
        "emergency": {
            "approvers_required": 0,
            "post_review": True,
            "notification": ["oncall", "dba_team"],
        },
        "standard": {
            "approvers_required": 0,
            "pre_approved": True,
            "notification": ["dba_team"],
        },
        "normal": {
            "approvers_required": 1,
            "approver_roles": ["dba", "tech_lead"],
            "notification": ["dba_team", "submitter"],
        },
        "major": {
            "approvers_required": 2,
            "approver_roles": ["dba", "tech_lead", "architect"],
            "notification": ["all_engineering", "management"],
            "additional_requirements": ["adr", "testing_plan"],
        },
    }


@pytest.fixture
def stakeholder_registry() -> Dict[str, List[str]]:
    """Stakeholder registry for notifications."""
    return {
        "dba_team": ["dba1@example.com", "dba2@example.com"],
        "tech_lead": ["techlead@example.com"],
        "architect": ["architect@example.com"],
        "oncall": ["oncall@example.com"],
        "security_team": ["security@example.com"],
        "all_engineering": ["engineering@example.com"],
        "management": ["mgmt@example.com"],
    }


@pytest.fixture
def maintenance_windows() -> List[Dict[str, Any]]:
    """Maintenance window schedule."""
    now = datetime.utcnow()
    return [
        {
            "id": "MW-001",
            "name": "Weekly maintenance",
            "start": (now + timedelta(days=1)).replace(
                hour=2, minute=0, second=0
            ).isoformat(),
            "end": (now + timedelta(days=1)).replace(
                hour=4, minute=0, second=0
            ).isoformat(),
            "recurring": "weekly",
            "day_of_week": "Sunday",
        },
        {
            "id": "MW-002",
            "name": "Emergency window",
            "start": now.isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
            "recurring": False,
            "type": "emergency",
        },
    ]


@pytest.fixture
def mock_postgresql_connection():
    """Mock PostgreSQL connection for testing."""

    class MockConnection:
        def __init__(self):
            self.closed = False
            self.in_transaction = False

        def cursor(self):
            return MockCursor()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    class MockCursor:
        def __init__(self):
            self.description = None
            self.rowcount = 0

        def execute(self, query, params=None):
            return True

        def fetchall(self):
            return []

        def fetchone(self):
            return None

        def close(self):
            pass

    return MockConnection()


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""

    class MockNotificationService:
        def __init__(self):
            self.sent_notifications = []

        def send_email(self, to: List[str], subject: str, body: str):
            self.sent_notifications.append(
                {
                    "type": "email",
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            return True

        def send_slack(self, channel: str, message: str):
            self.sent_notifications.append(
                {
                    "type": "slack",
                    "channel": channel,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            return True

        def get_sent_notifications(self):
            return self.sent_notifications

        def clear_notifications(self):
            self.sent_notifications = []

    return MockNotificationService()


@pytest.fixture
def test_backup_location(tmp_path: Path) -> Path:
    """Create temporary backup location."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "postgresql").mkdir(exist_ok=True)
    (backup_dir / "sqlite").mkdir(exist_ok=True)
    (backup_dir / "config").mkdir(exist_ok=True)
    return backup_dir


@pytest.fixture
def sample_migration_file(tmp_path: Path) -> Path:
    """Create sample Alembic migration file."""
    migration_file = tmp_path / "001_add_user_preferences.py"
    migration_file.write_text('''"""
Add user preferences table

Revision ID: 001
Create Date: 2025-10-11
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(50)),
        sa.Column('language', sa.String(10)),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('user_preferences')
''')
    return migration_file


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test."""
    yield
    # Cleanup will happen automatically with tmp_path fixture


# Utility functions for tests
def create_test_snapshot(db_path: Path, snapshot_dir: Path) -> Path:
    """Create a test database snapshot."""
    import shutil

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_path = snapshot_dir / f"snapshot_{timestamp}.db"
    shutil.copy2(db_path, snapshot_path)
    return snapshot_path


def verify_database_integrity(db_path: Path) -> bool:
    """Verify SQLite database integrity."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()
    conn.close()
    return result[0] == "ok"
