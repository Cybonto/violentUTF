"""
Unit test package initialization.
This file is loaded before any unit tests to set up the test environment.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

# Set test environment variables before importing any app modules
os.environ["APP_DATA_DIR"] = "./tests/test_data"
os.environ["CONFIG_DIR"] = "./tests/test_config"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./tests/test.db"
os.environ["ASYNC_DATABASE_URL"] = "sqlite+aiosqlite:///./tests/test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APISIX_GATEWAY_SECRET"] = "test-gateway-secret"

# Mock the database module before it's imported
mock_db_module = MagicMock()
mock_db_module.get_db_session = AsyncMock()
mock_db_module.AsyncSession = MagicMock()
mock_db_module.engine = MagicMock()

# Pre-insert the mock into sys.modules
sys.modules["app.db.database"] = mock_db_module
sys.modules["app.db"] = MagicMock(database=mock_db_module)
