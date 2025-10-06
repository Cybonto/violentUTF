"""
Smoke Tests for ViolentUTF Production Validation

This package contains smoke tests that validate critical functionality
after deployment or major changes (like the SQLite migration).

Smoke tests are designed to:
- Run quickly (< 5 minutes total)
- Test critical paths only
- Fail fast on major issues
- Provide clear error messages

Test Categories:
- API Health: Validate API endpoints are accessible and responding
- Database Connectivity: Validate database files are accessible and functional
- Key Workflows: Validate critical user workflows work end-to-end

Issue: #328 - Phase 4.3.7: Production Deployment and Cleanup
"""

__version__ = "1.0.0"
__author__ = "ViolentUTF Team"

# Test configuration defaults
DEFAULT_API_BASE_URL = "http://localhost:9080"
DEFAULT_STREAMLIT_URL = "http://localhost:8501"
DEFAULT_DB_PATH = "app_data/violentutf"
