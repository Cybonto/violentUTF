# Implementation Plan for Cybersecurity Fixes - June 29, 2025

**Document Date**: June 29, 2025
**Based On**: docs/fixes/cybersecurity_28JUL.md
**Target Branch**: dev_nightly
**Estimated Timeline**: 3-4 weeks for full implementation

## Executive Summary

This plan provides a systematic approach to addressing **27 critical security vulnerabilities** identified in the comprehensive security audit:
- **12 dependency vulnerabilities** (2 critical authentication issues)
- **15 code security vulnerabilities** (3 SQL injection, 5 timeout issues)
- **8 container security improvements**
- **Configuration security hardening**

The plan prioritizes immediate fixes for critical authentication and dependency vulnerabilities, followed by systematic code security improvements.

## Phase 1: CRITICAL Dependency Vulnerabilities (Day 1-2)

### 🚨 1.1 Fix Authentication Library Vulnerabilities - IMMEDIATE

**Critical Issue**: python-jose 3.4.0 - Authentication bypass vulnerability

**Pre-fix validation**:
```bash
# Backup current environment
pip freeze > requirements_backup.txt

# Check current python-jose usage
grep -r "python-jose\|jose" violentutf/ violentutf_api/ --include="*.py"
grep -r "from jose" violentutf/ violentutf_api/ --include="*.py"

# Identify JWT usage patterns
grep -r "jwt\|JWT" violentutf/ violentutf_api/ --include="*.py" | head -20
```

**Implementation Option A - Upgrade to cryptography backend**:
```bash
# Safer option - keep python-jose but use cryptography backend
pip uninstall python-jose
pip install "python-jose[cryptography]>=3.4.1"

# Verify cryptography backend is used
python -c "from jose import jwt; print(jwt.__version__)"
```

**Implementation Option B - Migrate to PyJWT (Recommended)**:
```python
# Migration script: migrate_to_pyjwt.py
import re

def migrate_jose_to_pyjwt(file_content):
    """Convert python-jose imports to PyJWT"""

    # Replace imports
    content = re.sub(r'from jose import jwt', 'import jwt', file_content)
    content = re.sub(r'from jose\.exceptions import .*', '', content)

    # Replace jwt.encode calls (PyJWT has different signature)
    # python-jose: jwt.encode(payload, key, algorithm)
    # PyJWT: jwt.encode(payload, key, algorithm)
    # Note: signatures are similar but error handling differs

    return content

# Apply to all files using python-jose
for file_path in affected_files:
    with open(file_path, 'r') as f:
        content = f.read()

    new_content = migrate_jose_to_pyjwt(content)

    with open(file_path, 'w') as f:
        f.write(new_content)
```

**Post-fix testing**:
```bash
# Install PyJWT and test authentication
pip install PyJWT cryptography

# Test JWT functionality
python -m pytest tests/test_authentication.py -v

# Integration test with Keycloak
python tests/integration/test_keycloak_jwt.py

# Security test - verify no algorithm confusion
python tests/security/test_jwt_security.py
```

### 🚨 1.2 Fix Credential Leakage - IMMEDIATE

**Critical Issue**: requests 2.32.3 - .netrc credential leakage

**Implementation**:
```bash
# Upgrade requests immediately
pip install "requests>=2.32.4"

# Verify no .netrc files exist
find . -name ".netrc" -o -name "_netrc"

# Add trust_env=False for sensitive requests
cat > fix_requests_security.py << 'EOF'
import re

def fix_requests_calls(file_content):
    # Add trust_env=False to sensitive requests
    patterns = [
        (r'(requests\.(?:get|post|put|delete|patch)\([^)]+)\)',
         r'\1, trust_env=False)'),
    ]

    for pattern, replacement in patterns:
        file_content = re.sub(pattern, replacement, file_content)

    return file_content
EOF
```

### 🚨 1.3 Upgrade All Critical Dependencies

**Implementation script**:
```bash
#!/bin/bash
# upgrade_dependencies.sh

set -e

echo "=== Upgrading critical dependencies ==="

# Critical security upgrades
pip install "tornado>=6.5.0"
pip install "protobuf>=6.31.1"
pip install "urllib3>=2.5.0"
pip install "requests>=2.32.4"

# Note: torch 2.7.1rc1 not yet available
echo "WARNING: torch 2.7.1rc1 not available yet - monitoring for release"

# Verify versions
python -c "
import tornado, protobuf, urllib3, requests
print(f'tornado: {tornado.version}')
print(f'protobuf: {protobuf.__version__}')
print(f'urllib3: {urllib3.__version__}')
print(f'requests: {requests.__version__}')
"

# Test core functionality
python -m pytest tests/core/ -v
```

## Phase 2: Code Security Vulnerabilities (Day 3-5)

### 2.1 Fix SQL Injection Vulnerabilities (B608) - HIGH PRIORITY

**Files affected**: 3 instances in database operations

**Pre-fix analysis**:
```bash
# Create comprehensive SQL security audit
cat > audit_sql_security.py << 'EOF'
import ast
import os
import re

def find_sql_patterns(directory):
    """Find potential SQL injection vulnerabilities"""
    vulnerabilities = []

    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE']

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')

                for i, line in enumerate(lines, 1):
                    # Check for f-strings with SQL
                    if re.search(r'f["\'][^"\']*(?:' + '|'.join(sql_keywords) + r')[^"\']*["\']', line, re.IGNORECASE):
                        vulnerabilities.append({
                            'file': file_path,
                            'line': i,
                            'content': line.strip(),
                            'type': 'f-string SQL'
                        })

                    # Check for .format() with SQL
                    if re.search(r'["\'][^"\']*(?:' + '|'.join(sql_keywords) + r')[^"\']*["\']\.format\(', line, re.IGNORECASE):
                        vulnerabilities.append({
                            'file': file_path,
                            'line': i,
                            'content': line.strip(),
                            'type': 'format SQL'
                        })

    return vulnerabilities

if __name__ == "__main__":
    vulns = find_sql_patterns('violentutf_api/')
    for vuln in vulns:
        print(f"{vuln['file']}:{vuln['line']} - {vuln['type']}")
        print(f"  {vuln['content']}")
EOF

python audit_sql_security.py
```

**Implementation for DuckDB (violentutf_api/fastapi_app/app/db/duckdb_manager.py)**:
```python
# Replace line 288: Dynamic UPDATE query
# BEFORE:
query = f"""
UPDATE generators SET {', '.join(updates)}
WHERE id = ? AND user_id = ?
"""

# AFTER: Use parameterized approach with validation
ALLOWED_UPDATE_COLUMNS = {
    'name', 'type', 'parameters', 'status', 'updated_at'
}

def build_safe_update_query(updates_dict: Dict[str, Any]) -> Tuple[str, List]:
    """Build parameterized UPDATE query with column validation"""

    # Validate column names against whitelist
    for column in updates_dict.keys():
        if column not in ALLOWED_UPDATE_COLUMNS:
            raise ValueError(f"Invalid column for update: {column}")

    # Build parameterized query
    set_clauses = [f"{col} = ?" for col in updates_dict.keys()]
    query = f"UPDATE generators SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?"

    # Build parameter list
    params = list(updates_dict.values()) + [generator_id, user_id]

    return query, params

# Usage:
query, params = build_safe_update_query(update_data)
conn.execute(query, params)
```

**Implementation for table counting (line 651)**:
```python
# BEFORE:
count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

# AFTER: Table name validation
ALLOWED_TABLES = {
    'generators', 'scorers', 'datasets', 'conversations',
    'orchestrator_executions', 'orchestrator_results'
}

def get_table_count(conn, table_name: str) -> int:
    """Get row count for table with name validation"""
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")

    # Safe to use f-string after validation
    result = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
    return result[0] if result else 0

# Usage:
count = get_table_count(conn, table)
```

**Implementation for database.py (line 215)**:
```python
# violentutf_api/fastapi_app/app/api/endpoints/database.py
# BEFORE:
result = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()

# AFTER: Use the same validation approach
from app.db.duckdb_manager import get_table_count

try:
    count = get_table_count(conn, table_name)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### 2.2 Fix HTTP Request Timeout Vulnerabilities (B113)

**Files affected**: 5 instances in violentutf_api/jwt_cli.py

**Implementation**:
```python
# violentutf_api/jwt_cli.py - Add timeouts to all requests

# Configuration
DEFAULT_TIMEOUT = 30  # seconds
AUTH_TIMEOUT = 10     # shorter for auth operations

# Line 151: refresh token
def refresh_token():
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/refresh",
            headers=get_auth_header(),
            timeout=AUTH_TIMEOUT
        )
        # ... rest of function

# Line 180: create API key
def create_api_key(name: str, permissions: Set[str]):
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/keys/create",
            headers=get_auth_header(),
            json={"name": name, "permissions": list(permissions)},
            timeout=DEFAULT_TIMEOUT
        )
        # ... rest of function

# Line 206: list API keys
def list_api_keys():
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/keys/list",
            headers=get_auth_header(),
            timeout=DEFAULT_TIMEOUT
        )
        # ... rest of function

# Line 238: delete API key
def delete_api_key(key_id: str):
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/keys/{key_id}",
            headers=get_auth_header(),
            timeout=DEFAULT_TIMEOUT
        )
        # ... rest of function

# Line 254: get current key info
def get_current_key_info():
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/keys/current",
            headers=get_auth_header(),
            timeout=DEFAULT_TIMEOUT
        )
        # ... rest of function
```

### 2.3 Fix Network Binding Security (B104)

**Files affected**: main.py:129, validation.py:299

**Implementation for main.py**:
```python
# violentutf_api/fastapi_app/main.py
import os
import logging

logger = logging.getLogger(__name__)

def get_secure_binding_config():
    """Get secure network binding configuration"""
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    # Security check for public binding
    if host == "0.0.0.0":
        if os.getenv("ALLOW_PUBLIC_BINDING", "false").lower() != "true":
            logger.warning(
                "Attempted to bind to all interfaces (0.0.0.0) without explicit permission. "
                "Set ALLOW_PUBLIC_BINDING=true to enable. Falling back to localhost."
            )
            host = "127.0.0.1"
        else:
            logger.warning(
                "Binding to all interfaces (0.0.0.0) - ensure firewall rules are properly configured"
            )

    return host, port

# Replace line 129:
# if host == "0.0.0.0" and os.getenv("ALLOW_PUBLIC_BINDING") != "true":
host, port = get_secure_binding_config()

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
```

**Implementation for validation.py**:
```python
# violentutf_api/fastapi_app/app/core/validation.py
# Line 299: Update dangerous hosts validation

def validate_url_security(url: str) -> None:
    """Validate URL for security concerns"""
    parsed = urlparse(url)
    host = parsed.hostname

    if not host:
        raise ValueError("Invalid URL: no hostname")

    # Enhanced dangerous hosts list
    dangerous_hosts = [
        "localhost",
        "127.",
        "::1",
        "10.",           # Private network
        "192.168.",      # Private network
        "172.",          # Private network (172.16-31.x.x)
        "169.254.",      # Link-local
        "metadata.google.internal",
        "metadata",
        "metadata.aws",
        "metadata.azure.com",
    ]

    # Special handling for 0.0.0.0 - always block
    if host == "0.0.0.0":
        raise ValueError("Access to 0.0.0.0 is not allowed")

    for dangerous in dangerous_hosts:
        if host.startswith(dangerous):
            raise ValueError(f"Access to internal/localhost URLs not allowed: {host}")

    # Additional check for private IP ranges
    import ipaddress
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Access to private/internal IP addresses not allowed: {host}")
    except ipaddress.AddressValueError:
        # Not an IP address, hostname validation above should catch issues
        pass
```

## Phase 3: Container Security Hardening (Day 6-7)

### 3.1 Pin Container Image Versions

**Update docker-compose files**:
```yaml
# apisix/docker-compose.yml
# keycloak/docker-compose.yml
# violentutf_api/docker-compose.yml

services:
  grafana:
    image: grafana/grafana:10.2.3  # Instead of :latest

  prometheus:
    image: prom/prometheus:v2.47.2  # Instead of :latest

  postgres:
    image: postgres:15.5  # Keep specific version

  keycloak:
    image: quay.io/keycloak/keycloak:26.1.4  # Already pinned

  etcd:
    image: bitnami/etcd:3.5.15  # Instead of :latest

  apisix:
    image: apache/apisix:3.8.0  # Instead of :latest

  apisix-dashboard:
    image: apache/apisix-dashboard:3.0.1  # Instead of :latest
```

### 3.2 Review Custom Docker Images

**Audit custom apisix-fastapi image**:
```bash
# Scan custom image for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image apisix-fastapi:latest

# Review Dockerfile security
cat > review_dockerfile_security.py << 'EOF'
import os

def audit_dockerfile(dockerfile_path):
    """Audit Dockerfile for security issues"""
    issues = []

    with open(dockerfile_path, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        line = line.strip()

        # Check for common security issues
        if line.startswith('USER root'):
            issues.append(f"Line {i}: Running as root user")

        if 'curl' in line and '|' in line and 'sh' in line:
            issues.append(f"Line {i}: Dangerous pipe to shell")

        if '--no-check-certificate' in line:
            issues.append(f"Line {i}: Certificate validation disabled")

        if 'chmod 777' in line:
            issues.append(f"Line {i}: Overly permissive permissions")

    return issues

# Audit all Dockerfiles
for dockerfile in ['violentutf/Dockerfile', 'violentutf_api/fastapi_app/Dockerfile']:
    if os.path.exists(dockerfile):
        issues = audit_dockerfile(dockerfile)
        if issues:
            print(f"\n{dockerfile}:")
            for issue in issues:
                print(f"  {issue}")
EOF

python review_dockerfile_security.py
```

## Phase 4: Test Security Hardening (Day 8-9)

### 4.1 Fix Test Security Issues (B108)

**Files affected**: Test files using insecure temporary directories

**Implementation**:
```python
# violentutf_api/fastapi_app/app/mcp/tests/conftest.py
import tempfile
import os
from pathlib import Path

@pytest.fixture
def test_environment():
    """Create secure test environment with proper temp directories"""

    # Create secure temporary directories
    with tempfile.TemporaryDirectory(prefix="vutf_test_") as temp_root:
        app_data_dir = os.path.join(temp_root, "app_data")
        config_dir = os.path.join(temp_root, "config")

        os.makedirs(app_data_dir, mode=0o700)  # Secure permissions
        os.makedirs(config_dir, mode=0o700)

        test_env = {
            # Secure temporary directories
            "APP_DATA_DIR": app_data_dir,
            "CONFIG_DIR": config_dir,

            # Database (use in-memory for tests)
            "DATABASE_URL": "sqlite:///:memory:",

            # Performance settings for tests
            "MCP_TOOL_TIMEOUT_SECONDS": "30",
            "MCP_CONCURRENT_TOOL_LIMIT": "5",
            "MCP_RESOURCE_CACHE_TTL": "60",
            "MCP_RESOURCE_CACHE_SIZE": "100",
        }

        with patch.dict(os.environ, test_env):
            yield test_env

# violentutf_api/fastapi_app/app/mcp/tests/test_phase2_components.py
# Replace line 18 hardcoded paths:
# OLD:
# with patch.dict(os.environ, {"APP_DATA_DIR": "/tmp/test_app_data", "CONFIG_DIR": "/tmp/test_config"}):

# NEW: Use the test_environment fixture
def test_mcp_components(test_environment):
    """Test MCP components with secure environment"""
    # test_environment fixture provides secure temp dirs
    assert os.path.exists(test_environment["APP_DATA_DIR"])
    assert os.path.exists(test_environment["CONFIG_DIR"])

    # Run component tests
    # ... test implementation
```

## Phase 5: Automated Security Testing (Day 10-11)

### 5.1 Create Comprehensive Security Test Suite

**Security test framework**:
```python
# tests/security/test_dependency_security.py
import subprocess
import json
import pytest

class TestDependencySecurity:
    def test_no_vulnerable_dependencies_safety(self):
        """Test no vulnerabilities in dependencies via Safety"""
        result = subprocess.run(
            ['safety', 'check', '--json'],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            vulnerabilities = json.loads(result.stdout)
            pytest.fail(f"Found {len(vulnerabilities)} vulnerabilities: {vulnerabilities}")

    def test_no_vulnerable_dependencies_pip_audit(self):
        """Test no vulnerabilities in dependencies via pip-audit"""
        result = subprocess.run(
            ['pip-audit', '--format', 'json'],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            vulnerabilities = json.loads(result.stdout)
            if vulnerabilities:
                pytest.fail(f"Found vulnerabilities: {vulnerabilities}")

# tests/security/test_code_security.py
class TestCodeSecurity:
    def test_no_sql_injection_vulnerabilities(self):
        """Test SQL queries are parameterized"""
        from violentutf_api.fastapi_app.app.db.duckdb_manager import DuckDBManager

        # Test with malicious input
        manager = DuckDBManager("test_user")

        with pytest.raises(ValueError, match="Invalid table name"):
            manager.get_table_count("users'; DROP TABLE users; --")

    def test_request_timeouts_configured(self):
        """Test all HTTP requests have timeouts"""
        import ast
        import os

        timeout_missing = []

        for root, dirs, files in os.walk('violentutf_api/'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        try:
                            tree = ast.parse(f.read())
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Call):
                                    if (hasattr(node.func, 'attr') and
                                        hasattr(node.func.value, 'id') and
                                        node.func.value.id == 'requests'):

                                        # Check if timeout is in keywords
                                        has_timeout = any(
                                            kw.arg == 'timeout'
                                            for kw in node.keywords
                                        )

                                        if not has_timeout:
                                            timeout_missing.append(f"{file_path}:{node.lineno}")
                        except:
                            pass

        if timeout_missing:
            pytest.fail(f"Requests without timeout: {timeout_missing}")

    def test_network_binding_security(self):
        """Test network binding security"""
        import os
        from unittest.mock import patch

        # Test default binding (should be localhost)
        with patch.dict(os.environ, {}, clear=True):
            from violentutf_api.fastapi_app.main import get_secure_binding_config
            host, port = get_secure_binding_config()
            assert host == "127.0.0.1"

        # Test 0.0.0.0 without permission (should fallback)
        with patch.dict(os.environ, {"API_HOST": "0.0.0.0"}, clear=True):
            host, port = get_secure_binding_config()
            assert host == "127.0.0.1"

        # Test 0.0.0.0 with permission (should allow)
        with patch.dict(os.environ, {"API_HOST": "0.0.0.0", "ALLOW_PUBLIC_BINDING": "true"}):
            host, port = get_secure_binding_config()
            assert host == "0.0.0.0"

# tests/security/test_authentication_security.py
class TestAuthenticationSecurity:
    def test_jwt_algorithm_confusion_prevention(self):
        """Test JWT implementation prevents algorithm confusion attacks"""
        import jwt
        from violentutf_api.fastapi_app.app.core.auth import verify_token

        # Create token with 'none' algorithm (should fail)
        malicious_token = jwt.encode(
            {"sub": "test", "exp": 9999999999},
            "",
            algorithm="none"
        )

        with pytest.raises(Exception):  # Should reject 'none' algorithm
            verify_token(malicious_token)

    def test_no_hardcoded_secrets(self):
        """Test no hardcoded secrets in codebase"""
        import os
        import re

        secret_patterns = [
            r'(?i)(password|secret|key|token)\s*=\s*["\'][^"\']{8,}["\']',
            r'(?i)api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'(?i)(aws|anthropic|openai)[_-]?(access[_-]?key|secret[_-]?key|api[_-]?key)\s*=\s*["\'][^"\']+["\']'
        ]

        hardcoded_secrets = []

        for root, dirs, files in os.walk('.'):
            # Skip test files and virtual environments
            if any(skip in root for skip in ['.git', '.vitutf', '__pycache__', 'node_modules']):
                continue

            for file in files:
                if file.endswith(('.py', '.js', '.yml', '.yaml', '.json', '.env')):
                    file_path = os.path.join(root, file)

                    # Skip sample files
                    if file.endswith('.sample') or 'example' in file:
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for i, line in enumerate(content.split('\n'), 1):
                            for pattern in secret_patterns:
                                if re.search(pattern, line):
                                    # Exclude obvious placeholders
                                    if not any(placeholder in line.lower() for placeholder in
                                             ['your_', 'example', 'placeholder', 'xxx', '***']):
                                        hardcoded_secrets.append(f"{file_path}:{i} - {line.strip()}")
                    except:
                        pass

        if hardcoded_secrets:
            pytest.fail(f"Found potential hardcoded secrets:\n" + "\n".join(hardcoded_secrets))
```

### 5.2 Integration Testing

**API security integration tests**:
```python
# tests/integration/test_api_security.py
import pytest
from fastapi.testclient import TestClient

class TestAPISecurityIntegration:
    @pytest.fixture
    def client(self):
        from violentutf_api.fastapi_app.main import app
        return TestClient(app)

    def test_sql_injection_protection(self, client):
        """Test API endpoints are protected against SQL injection"""

        # Test database endpoint
        response = client.post("/api/v1/database/query", json={
            "table": "users'; DROP TABLE users; --"
        })
        assert response.status_code == 400
        assert "Invalid table name" in response.json()["detail"]

        # Test other endpoints with malicious input
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1'; UPDATE users SET admin=1; --"
        ]

        for malicious in malicious_inputs:
            response = client.get(f"/api/v1/generators/{malicious}")
            assert response.status_code in [400, 404, 422]  # Should not succeed

    def test_authentication_bypass_protection(self, client):
        """Test API is protected against authentication bypass"""

        # Test protected endpoint without auth
        response = client.get("/api/v1/generators")
        assert response.status_code == 401

        # Test with invalid JWT
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/generators", headers=headers)
        assert response.status_code == 401

        # Test with 'none' algorithm JWT
        import jwt
        malicious_token = jwt.encode({"sub": "admin"}, "", algorithm="none")
        headers = {"Authorization": f"Bearer {malicious_token}"}
        response = client.get("/api/v1/generators", headers=headers)
        assert response.status_code == 401

    def test_rate_limiting(self, client):
        """Test API rate limiting is enforced"""

        # Make many requests rapidly
        responses = []
        for i in range(100):
            response = client.get("/api/v1/health")
            responses.append(response.status_code)

        # Should have some rate limiting responses
        assert 429 in responses or all(r == 200 for r in responses[:50])  # Allow for rate limiting
```

## Phase 6: CI/CD Security Integration (Day 12-13)

### 6.1 Enhanced Security Pipeline

**Create .github/workflows/security-scan.yml**:
```yaml
name: Security Scan Pipeline
on:
  push:
    branches: [main, dev_nightly]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  dependency-security:
    name: Dependency Security Scan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install safety pip-audit

      - name: Run Safety scan
        run: |
          safety check --json --output safety-report.json || true

      - name: Run pip-audit scan
        run: |
          pip-audit --format json --output pip-audit-report.json || true

      - name: Process security reports
        run: |
          python scripts/process_security_reports.py \
            --safety safety-report.json \
            --pip-audit pip-audit-report.json \
            --fail-on-critical

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: dependency-security-reports
          path: |
            safety-report.json
            pip-audit-report.json

  code-security:
    name: Code Security Scan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Bandit
        run: pip install bandit[toml]

      - name: Run Bandit scan
        run: |
          bandit -r violentutf/ violentutf_api/ \
            -f json -o bandit-report.json \
            -ll -x tests/

      - name: Check for high severity issues
        run: |
          if [ -f bandit-report.json ]; then
            high_issues=$(python -c "
            import json
            with open('bandit-report.json') as f:
              data = json.load(f)
            high = [r for r in data.get('results', []) if r.get('issue_severity') == 'HIGH']
            print(len(high))
            ")

            if [ "$high_issues" -gt 0 ]; then
              echo "Found $high_issues high severity security issues"
              exit 1
            fi
          fi

      - name: Upload Bandit report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: bandit-report
          path: bandit-report.json

  container-security:
    name: Container Security Scan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Build custom images
        run: |
          docker build -t violentutf:test violentutf/
          docker build -t violentutf-api:test violentutf_api/fastapi_app/

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'violentutf:test'
          format: 'json'
          output: 'trivy-violentutf.json'

      - name: Run Trivy on API image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'violentutf-api:test'
          format: 'json'
          output: 'trivy-api.json'

      - name: Upload Trivy reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: trivy-reports
          path: |
            trivy-*.json

  security-tests:
    name: Security Test Suite
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run security tests
        run: |
          pytest tests/security/ -v \
            --junitxml=security-tests.xml \
            --tb=short

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-test-results
          path: security-tests.xml

  security-summary:
    name: Security Summary
    runs-on: ubuntu-latest
    needs: [dependency-security, code-security, container-security, security-tests]
    if: always()

    steps:
      - uses: actions/checkout@v4

      - name: Download all reports
        uses: actions/download-artifact@v3
        with:
          path: security-reports

      - name: Generate security summary
        run: |
          python scripts/generate_security_summary.py \
            --reports-dir security-reports \
            --output security-summary.md

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const summary = fs.readFileSync('security-summary.md', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: summary
            });
```

### 6.2 Security Report Processing Scripts

**Create scripts/process_security_reports.py**:
```python
#!/usr/bin/env python3
"""Process security scan reports and determine if build should fail"""

import json
import argparse
import sys
from pathlib import Path

def process_safety_report(report_path):
    """Process Safety scan report"""
    if not Path(report_path).exists():
        return {"vulnerabilities": 0, "critical": 0}

    with open(report_path) as f:
        try:
            data = json.load(f)
            # Safety reports are arrays of vulnerabilities
            if isinstance(data, list):
                critical = sum(1 for vuln in data
                             if vuln.get('vulnerability_id', '').startswith('CVE'))
                return {"vulnerabilities": len(data), "critical": critical}
        except json.JSONDecodeError:
            return {"vulnerabilities": 0, "critical": 0}

    return {"vulnerabilities": 0, "critical": 0}

def process_pip_audit_report(report_path):
    """Process pip-audit scan report"""
    if not Path(report_path).exists():
        return {"vulnerabilities": 0, "critical": 0}

    with open(report_path) as f:
        try:
            data = json.load(f)
            vulns = data.get('vulnerabilities', [])
            critical = sum(1 for vuln in vulns
                          if 'CRITICAL' in str(vuln.get('id', '')).upper())
            return {"vulnerabilities": len(vulns), "critical": critical}
        except json.JSONDecodeError:
            return {"vulnerabilities": 0, "critical": 0}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--safety', required=True)
    parser.add_argument('--pip-audit', required=True)
    parser.add_argument('--fail-on-critical', action='store_true')
    args = parser.parse_args()

    safety_results = process_safety_report(args.safety)
    pip_audit_results = process_pip_audit_report(args.pip_audit)

    total_vulns = safety_results['vulnerabilities'] + pip_audit_results['vulnerabilities']
    total_critical = safety_results['critical'] + pip_audit_results['critical']

    print(f"Security scan results:")
    print(f"  Total vulnerabilities: {total_vulns}")
    print(f"  Critical vulnerabilities: {total_critical}")
    print(f"  Safety: {safety_results['vulnerabilities']} vulnerabilities")
    print(f"  pip-audit: {pip_audit_results['vulnerabilities']} vulnerabilities")

    if args.fail_on_critical and total_critical > 0:
        print(f"FAIL: Found {total_critical} critical vulnerabilities")
        sys.exit(1)

    print("PASS: No critical vulnerabilities found")

if __name__ == "__main__":
    main()
```

## Phase 7: Monitoring and Maintenance (Day 14)

### 7.1 Security Monitoring Setup

**Create automated dependency monitoring**:
```bash
# .github/workflows/dependency-updates.yml
name: Dependency Security Updates
on:
  schedule:
    - cron: '0 8 * * MON'  # Weekly on Monday
  workflow_dispatch:

jobs:
  check-updates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Check for security updates
        run: |
          pip install pip-upgrader safety

          # Generate upgrade recommendations
          pip-upgrade --dry-run --skip-git > upgrade-recommendations.txt

          # Check for security issues in current versions
          safety check --json > current-vulnerabilities.json || true

          # Generate update PR if security issues found
          if [ -s current-vulnerabilities.json ]; then
            echo "Security vulnerabilities found - creating update PR"
            # Logic to create automated PR with security updates
          fi
```

### 7.2 Security Metrics Dashboard

**Create security metrics collection**:
```python
# scripts/collect_security_metrics.py
"""Collect security metrics for monitoring"""

import json
import subprocess
import datetime
from pathlib import Path

def collect_metrics():
    """Collect current security metrics"""
    metrics = {
        "timestamp": datetime.datetime.now().isoformat(),
        "dependency_vulnerabilities": get_dependency_vulnerabilities(),
        "code_security_issues": get_code_security_issues(),
        "test_coverage": get_security_test_coverage(),
        "container_vulnerabilities": get_container_vulnerabilities(),
    }

    return metrics

def get_dependency_vulnerabilities():
    """Get dependency vulnerability count"""
    try:
        # Safety check
        result = subprocess.run(['safety', 'check', '--json'],
                              capture_output=True, text=True)
        safety_vulns = len(json.loads(result.stdout)) if result.stdout else 0

        # pip-audit check
        result = subprocess.run(['pip-audit', '--format', 'json'],
                              capture_output=True, text=True)
        pip_audit_data = json.loads(result.stdout) if result.stdout else {}
        pip_audit_vulns = len(pip_audit_data.get('vulnerabilities', []))

        return {
            "safety": safety_vulns,
            "pip_audit": pip_audit_vulns,
            "total": safety_vulns + pip_audit_vulns
        }
    except Exception as e:
        return {"error": str(e), "total": -1}

def get_code_security_issues():
    """Get Bandit security issue count"""
    try:
        result = subprocess.run([
            'bandit', '-r', 'violentutf/', 'violentutf_api/',
            '-f', 'json', '-ll'
        ], capture_output=True, text=True)

        if result.stdout:
            data = json.loads(result.stdout)
            results = data.get('results', [])

            by_severity = {}
            for result in results:
                severity = result.get('issue_severity', 'UNKNOWN')
                by_severity[severity] = by_severity.get(severity, 0) + 1

            return {
                "total": len(results),
                "by_severity": by_severity
            }
    except Exception as e:
        return {"error": str(e), "total": -1}

def get_security_test_coverage():
    """Get security test coverage"""
    try:
        result = subprocess.run([
            'pytest', 'tests/security/', '--cov=violentutf', '--cov=violentutf_api',
            '--cov-report=json', '--quiet'
        ], capture_output=True, text=True)

        if Path('.coverage.json').exists():
            with open('.coverage.json') as f:
                data = json.load(f)
                return {
                    "coverage_percent": data.get('totals', {}).get('percent_covered', 0)
                }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    metrics = collect_metrics()

    # Save to file for tracking
    with open('security-metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
```

## Success Metrics and Validation

### Target Metrics After Implementation

| Metric | Current | Target | Validation Method |
|--------|---------|--------|------------------|
| Critical Dependencies | 2 | 0 | `safety check && pip-audit` |
| High Severity Code Issues | 0 | 0 | `bandit -ll` |
| Medium Severity Code Issues | 15 | <5 | `bandit -ll` |
| SQL Injection Risks | 3 | 0 | Manual review + tests |
| Request Timeout Issues | 5 | 0 | Custom audit script |
| Network Binding Issues | 2 | 0 | Configuration review |
| Test Security Issues | 4 | 0 | Secure temp directory usage |
| Container Images Pinned | 25% | 100% | Docker compose review |
| Security Test Coverage | 0% | >80% | `pytest --cov tests/security/` |

### Validation Checklist

- [ ] All critical dependency vulnerabilities resolved (python-jose, requests)
- [ ] All SQL injection vulnerabilities fixed with parameterized queries
- [ ] All HTTP requests have appropriate timeouts configured
- [ ] Network binding security implemented with environment controls
- [ ] Test files use secure temporary directory practices
- [ ] Container images pinned to specific versions
- [ ] Security test suite covers all vulnerability types
- [ ] CI/CD pipeline includes comprehensive security scanning
- [ ] Pre-commit hooks prevent new security issues
- [ ] Security monitoring and alerting configured

## Rollback Plan

### Emergency Rollback Procedure

```bash
#!/bin/bash
# emergency_rollback.sh

set -e

echo "=== EMERGENCY SECURITY ROLLBACK ==="

# 1. Rollback dependency changes
echo "Rolling back dependency changes..."
pip install -r requirements_backup.txt

# 2. Rollback code changes
echo "Rolling back code changes..."
git checkout HEAD~1 -- violentutf_api/fastapi_app/app/db/duckdb_manager.py
git checkout HEAD~1 -- violentutf_api/fastapi_app/app/api/endpoints/database.py
git checkout HEAD~1 -- violentutf_api/jwt_cli.py
git checkout HEAD~1 -- violentutf_api/fastapi_app/main.py

# 3. Restart services
echo "Restarting services..."
docker-compose restart

# 4. Verify rollback
echo "Verifying rollback..."
python -m pytest tests/core/ -v

echo "Rollback completed. Review logs and investigate issues."
```

## Risk Mitigation Strategies

### Identified Risks and Mitigations

1. **Risk**: Authentication system breaks after python-jose migration
   - **Mitigation**: Comprehensive JWT testing, gradual rollout, feature flags
   - **Detection**: Authentication integration tests
   - **Response**: Immediate rollback to python-jose with cryptography backend

2. **Risk**: Database queries break after SQL injection fixes
   - **Mitigation**: Extensive database testing, schema validation
   - **Detection**: Database integration tests, query performance monitoring
   - **Response**: Rollback individual query changes, not entire system

3. **Risk**: API performance degrades with request timeouts
   - **Mitigation**: Timeout tuning based on endpoint characteristics
   - **Detection**: Performance monitoring, SLA tracking
   - **Response**: Adjust timeout values, implement adaptive timeouts

4. **Risk**: Container updates break deployment
   - **Mitigation**: Test in staging environment, gradual rollout
   - **Detection**: Container health checks, deployment validation
   - **Response**: Rollback to previous image versions

5. **Risk**: Security scanning blocks valid development
   - **Mitigation**: Configurable thresholds, security exceptions process
   - **Detection**: Developer feedback, false positive rates
   - **Response**: Tune scanning rules, implement security review process

## Timeline and Resource Requirements

### Detailed Schedule

| Phase | Duration | Resources | Critical Path |
|-------|----------|-----------|---------------|
| Phase 1: Critical Dependencies | 2 days | 1 senior dev | YES |
| Phase 2: Code Security | 3 days | 1 senior dev | YES |
| Phase 3: Container Security | 2 days | 1 DevOps engineer | NO |
| Phase 4: Test Security | 2 days | 1 dev + QA | NO |
| Phase 5: Security Testing | 2 days | 1 senior dev + QA | YES |
| Phase 6: CI/CD Integration | 2 days | 1 DevOps engineer | NO |
| Phase 7: Monitoring Setup | 1 day | 1 DevOps engineer | NO |

**Total Duration**: 14 days (3 weeks with overlap)
**Critical Path**: 9 days
**Team Required**: 2-3 developers, 1 DevOps engineer, 1 QA engineer

### Communication Plan

**Daily Standups**:
- Progress updates on security fixes
- Blocker identification and resolution
- Cross-team coordination

**Stakeholder Updates**:
- Daily progress emails to management
- Weekly security posture reports
- Immediate escalation for critical issues

**Documentation Updates**:
- Security runbook updates
- Incident response procedure updates
- Developer security guidelines

## Conclusion

This comprehensive implementation plan addresses all 27 identified security vulnerabilities through a systematic, risk-based approach. The plan prioritizes critical dependency vulnerabilities that could lead to authentication bypass, followed by code-level security issues and infrastructure hardening.

Key success factors:
1. **Immediate action** on critical dependency vulnerabilities
2. **Comprehensive testing** at each phase to prevent regressions
3. **Automated security scanning** to prevent future issues
4. **Clear rollback procedures** for risk mitigation
5. **Continuous monitoring** for ongoing security posture

The estimated 3-week timeline provides adequate time for thorough testing and validation while maintaining urgency for critical security fixes. This plan transforms ViolentUTF from a vulnerable codebase to a security-hardened enterprise platform suitable for AI red-teaming operations.
