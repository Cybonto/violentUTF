"""
Pytest configuration and fixtures for security tests.

This module provides shared fixtures for database security audit testing.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
import yaml

# Test data constants
TEST_POSTGRES_HOST = os.getenv("TEST_POSTGRES_HOST", "localhost")
TEST_POSTGRES_PORT = int(os.getenv("TEST_POSTGRES_PORT", "5432"))
TEST_POSTGRES_DB = os.getenv("TEST_POSTGRES_DB", "keycloak_test")
TEST_POSTGRES_USER = os.getenv("TEST_POSTGRES_USER", "test_user")
TEST_POSTGRES_PASSWORD = os.getenv("TEST_POSTGRES_PASSWORD", "test_password")


@pytest.fixture
def test_postgres_config() -> Dict[str, Any]:
    """Provide PostgreSQL test configuration."""
    return {
        "host": TEST_POSTGRES_HOST,
        "port": TEST_POSTGRES_PORT,
        "database": TEST_POSTGRES_DB,
        "user": TEST_POSTGRES_USER,
        "password": TEST_POSTGRES_PASSWORD,
        "sslmode": "prefer",
    }


@pytest.fixture
def test_sqlite_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary SQLite database for testing."""
    db_path = tmp_path / "test_violentutf.db"

    # Create test database with sample schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create test tables
    cursor.execute(
        """
        CREATE TABLE orchestrator_configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            config_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE orchestrator_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id INTEGER,
            status TEXT,
            results TEXT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (config_id) REFERENCES orchestrator_configurations(id)
        )
    """
    )

    # Insert test data
    cursor.execute(
        """
        INSERT INTO orchestrator_configurations (name, config_data)
        VALUES ('test_config', '{"test": "data"}')
    """
    )

    cursor.execute(
        """
        INSERT INTO orchestrator_executions (config_id, status, results)
        VALUES (1, 'completed', '{"score": 0.95}')
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup handled by tmp_path fixture


@pytest.fixture
def test_sqlite_db_permissions(tmp_path: Path) -> Generator[Path, None, None]:
    """Create SQLite database with specific permissions for testing."""
    db_path = tmp_path / "test_permissions.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    conn.close()

    # Set specific permissions
    os.chmod(db_path, 0o600)  # Owner read/write only

    yield db_path


@pytest.fixture
def test_env_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test .env file with sample secrets."""
    env_file = tmp_path / ".env"

    env_content = """
# Test environment file
DATABASE_URL=postgresql://user:password@localhost:5432/testdb
API_KEY=test-api-key-12345
SECRET_KEY=super-secret-key-xyz
DEBUG=True
"""

    env_file.write_text(env_content)
    os.chmod(env_file, 0o600)

    yield env_file


@pytest.fixture
def test_config_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test YAML configuration file."""
    config_file = tmp_path / "test_config.yaml"

    config_content = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "testdb",
        },
        "security": {
            "ssl_enabled": True,
            "auth_method": "scram-sha-256",
        },
    }

    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    os.chmod(config_file, 0o644)

    yield config_file


@pytest.fixture
def test_log_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test log file with sample log entries."""
    log_file = tmp_path / "test_app.log"

    log_content = """
2025-10-10 10:00:00 INFO - Application started
2025-10-10 10:01:00 INFO - User login: user@example.com
2025-10-10 10:02:00 WARNING - Failed login attempt for user@example.com
2025-10-10 10:03:00 ERROR - Database connection failed
2025-10-10 10:04:00 INFO - Database connection restored
"""

    log_file.write_text(log_content)
    os.chmod(log_file, 0o640)

    yield log_file


@pytest.fixture
def mock_security_findings() -> list:
    """Provide mock security findings for testing."""
    return [
        {
            "severity": "CRITICAL",
            "category": "Authentication",
            "finding": "Default credentials detected in PostgreSQL",
            "description": "PostgreSQL is using default admin password",
            "risk_score": 100,
            "likelihood": 5,
            "impact": 5,
            "exploitability": 4,
            "affected_system": "PostgreSQL (Keycloak)",
            "remediation": "Change default password immediately",
        },
        {
            "severity": "HIGH",
            "category": "Encryption",
            "finding": "Weak encryption algorithm detected (MD5)",
            "description": "MD5 hashing used for password storage",
            "risk_score": 72,
            "likelihood": 4,
            "impact": 4,
            "exploitability": 4,
            "affected_system": "Authentication module",
            "remediation": "Migrate to bcrypt or scram-sha-256",
        },
        {
            "severity": "MEDIUM",
            "category": "Access Control",
            "finding": "Excessive user privileges detected",
            "description": "Service account has SUPERUSER privileges",
            "risk_score": 45,
            "likelihood": 3,
            "impact": 4,
            "exploitability": 3,
            "affected_system": "PostgreSQL",
            "remediation": "Apply least privilege principle",
        },
        {
            "severity": "LOW",
            "category": "Configuration",
            "finding": "Verbose error messages enabled",
            "description": "Detailed error messages may leak information",
            "risk_score": 12,
            "likelihood": 2,
            "impact": 2,
            "exploitability": 3,
            "affected_system": "API",
            "remediation": "Disable verbose errors in production",
        },
    ]


@pytest.fixture
def mock_compliance_data() -> Dict[str, Any]:
    """Provide mock compliance data for testing."""
    return {
        "gdpr": {
            "article_32_compliance": 0.85,
            "data_retention_compliant": True,
            "retention_policy_years": 2,
            "consent_tracking": True,
            "subject_rights_supported": ["access", "deletion", "portability"],
            "breach_notification_capable": True,
            "encryption_at_rest": True,
            "encryption_in_transit": True,
        },
        "soc2": {
            "access_controls": "implemented",
            "rbac_enabled": True,
            "mfa_for_privileged": False,
            "monitoring": "enabled",
            "audit_logging": "compliant",
            "log_retention_years": 7,
            "change_management": "documented",
            "incident_response_plan": True,
        },
        "gaps": [
            {
                "standard": "SOC2",
                "control": "CC6.1",
                "finding": "MFA not enabled for privileged users",
                "severity": "HIGH",
                "remediation": "Enable MFA for all admin accounts",
            }
        ],
    }


@pytest.fixture
def mock_access_control_matrix() -> Dict[str, Any]:
    """Provide mock access control matrix for testing."""
    return {
        "users": [
            {
                "username": "admin",
                "roles": ["superuser"],
                "privileges": ["ALL"],
                "last_login": "2025-10-10 09:00:00",
            },
            {
                "username": "keycloak",
                "roles": ["application"],
                "privileges": ["SELECT", "INSERT", "UPDATE"],
                "last_login": "2025-10-10 10:00:00",
            },
            {
                "username": "api_service",
                "roles": ["service_account"],
                "privileges": ["SELECT", "INSERT"],
                "last_login": "2025-10-10 10:15:00",
            },
        ],
        "roles": [
            {"role": "superuser", "privileges": ["ALL"], "member_count": 1},
            {
                "role": "application",
                "privileges": ["SELECT", "INSERT", "UPDATE"],
                "member_count": 1,
            },
            {
                "role": "service_account",
                "privileges": ["SELECT", "INSERT"],
                "member_count": 1,
            },
        ],
        "violations": [
            {
                "user": "keycloak",
                "violation": "excessive_privileges",
                "description": "Application user has UPDATE privilege",
                "severity": "MEDIUM",
            }
        ],
    }


@pytest.fixture
def security_standards_config(tmp_path: Path) -> Generator[Path, None, None]:
    """Load security standards configuration."""
    # In real implementation, this would load from the actual config file
    # For testing, we create a minimal version
    config_file = tmp_path / "security_standards.yaml"

    config_content = {
        "postgresql": {
            "authentication": {
                "allowed_methods": ["scram-sha-256", "md5"],
                "disallowed_methods": ["trust", "password"],
                "require_ssl": True,
            },
            "passwords": {
                "min_length": 16,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special": True,
            },
        },
        "sqlite": {"file_security": {"permissions": "0600", "directory_permissions": "0700"}},
        "risk_scoring": {
            "severity_levels": {
                "critical": {"score_min": 90},
                "high": {"score_min": 70},
                "medium": {"score_min": 40},
                "low": {"score_min": 1},
            }
        },
    }

    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    yield config_file


@pytest.fixture
def compliance_requirements_config(tmp_path: Path) -> Generator[Path, None, None]:
    """Load compliance requirements configuration."""
    config_file = tmp_path / "compliance_requirements.yaml"

    config_content = {
        "gdpr": {
            "data_retention": {"max_retention_years": 2},
            "audit_logging": {"retention_years": 7},
        },
        "soc2": {
            "access_reviews": {"frequency_days": 90},
            "password_policy": {
                "min_length": 16,
                "expiration_days": 90,
                "lockout_threshold": 5,
            },
        },
    }

    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    yield config_file


@pytest.fixture
def test_certificate(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test SSL/TLS certificate file."""
    cert_file = tmp_path / "test_cert.pem"

    # Mock certificate content (not a real cert, just for permission testing)
    cert_content = """
-----BEGIN CERTIFICATE-----
MIIC... (test certificate data)
-----END CERTIFICATE-----
"""

    cert_file.write_text(cert_content)
    os.chmod(cert_file, 0o600)

    yield cert_file


@pytest.fixture
def test_backup_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test database backup file."""
    backup_file = tmp_path / "test_backup.db.backup"

    # Create a simple backup (just copy test data)
    with open(backup_file, "wb") as f:
        f.write(b"test backup data")

    os.chmod(backup_file, 0o600)

    yield backup_file


@pytest.fixture(scope="session")
def docker_available() -> bool:
    """Check if Docker is available for testing."""
    try:
        import docker  # type: ignore

        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:  # nosec B110
        return False


@pytest.fixture
def skip_if_no_docker(docker_available: bool) -> None:
    """Skip test if Docker is not available."""
    if not docker_available:
        pytest.skip("Docker is not available")


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test configuration directory with security audit configs."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create security_standards.yaml
    security_standards = config_dir / "security_standards.yaml"
    security_content = {
        "postgresql": {
            "authentication": {
                "allowed_methods": ["scram-sha-256", "md5"],
                "require_ssl": True,
            },
            "passwords": {"min_length": 16},
        },
        "sqlite": {"file_security": {"permissions": "0600", "directory_permissions": "0700"}},
    }
    with open(security_standards, "w") as f:
        yaml.dump(security_content, f)

    # Create compliance_requirements.yaml
    compliance_req = config_dir / "compliance_requirements.yaml"
    compliance_content = {
        "gdpr": {
            "data_retention": {"max_retention_years": 2},
            "audit_logging": {"retention_years": 7},
        },
        "soc2": {"access_reviews": {"frequency_days": 90}},
    }
    with open(compliance_req, "w") as f:
        yaml.dump(compliance_content, f)

    # Create audit_rules.yaml
    audit_rules = config_dir / "audit_rules.yaml"
    audit_content = {
        "severity_threshold": "low",
        "scan_timeout_seconds": 300,
    }
    with open(audit_rules, "w") as f:
        yaml.dump(audit_content, f)

    yield config_dir


@pytest.fixture
def temp_sqlite_db(test_sqlite_db: Path) -> Path:
    """Alias for test_sqlite_db for compatibility."""
    return test_sqlite_db
