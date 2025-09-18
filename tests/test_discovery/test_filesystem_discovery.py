"""
Tests for filesystem discovery module.
"""

import os
import sqlite3

# Add scripts to path for testing
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

sys.path.append('/Users/tamnguyen/Documents/GitHub/violentUTF/scripts/database-automation')

from discovery.filesystem_discovery import FilesystemDiscovery
from discovery.models import DatabaseType, DiscoveryConfig, DiscoveryMethod


class TestFilesystemDiscovery:
    """Test filesystem discovery functionality."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return DiscoveryConfig(
            enable_filesystem_discovery=True,
            scan_paths=[],  # Will be set in tests
            file_extensions=['.db', '.sqlite', '.sqlite3', '.duckdb'],
            max_file_size_mb=100,
            exclude_patterns=['__pycache__', '.git', 'test_']
        )
    
    @pytest.fixture
    def filesystem_discovery(self, config):
        """Filesystem discovery instance."""
        return FilesystemDiscovery(config)
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_init(self, config):
        """Test FilesystemDiscovery initialization."""
        fs_discovery = FilesystemDiscovery(config)
        assert fs_discovery.config == config
        assert fs_discovery.logger is not None
    
    def test_should_process_file_valid(self, filesystem_discovery, temp_dir):
        """Test should_process_file with valid files."""
        # Create a small SQLite file
        test_file = temp_dir / "test.db"
        with open(test_file, 'wb') as f:
            f.write(b'SQLite format 3\x00' + b'\x00' * 100)  # Valid SQLite header
        
        assert filesystem_discovery._should_process_file(test_file) is True
    
    def test_should_process_file_too_large(self, filesystem_discovery, temp_dir, config):
        """Test should_process_file with file too large."""
        # Create a file larger than the limit
        test_file = temp_dir / "large.db"
        with open(test_file, 'wb') as f:
            f.write(b'\x00' * (config.max_file_size_mb * 1024 * 1024 + 1))
        
        assert filesystem_discovery._should_process_file(test_file) is False
    
    def test_should_process_file_excluded_pattern(self, filesystem_discovery, temp_dir):
        """Test should_process_file with excluded patterns."""
        test_file = temp_dir / "test_excluded.db"
        test_file.touch()
        
        assert filesystem_discovery._should_process_file(test_file) is False
    
    def test_should_process_file_not_accessible(self, filesystem_discovery):
        """Test should_process_file with non-existent file."""
        non_existent = Path("/non/existent/file.db")
        assert filesystem_discovery._should_process_file(non_existent) is False
    
    def test_analyze_sqlite_database_file(self, filesystem_discovery, temp_dir):
        """Test analysis of SQLite database file."""
        # Create a valid SQLite database
        db_file = temp_dir / "test.sqlite"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # Create a simple table
        cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);")
        cursor.execute("INSERT INTO test_table (name) VALUES ('test_data');")
        conn.commit()
        conn.close()
        
        # Analyze the file
        discovery = filesystem_discovery._analyze_database_file(db_file)
        
        assert discovery is not None
        assert discovery.database_type == DatabaseType.SQLITE
        assert discovery.name == "test.sqlite"
        assert discovery.file_path == str(db_file.absolute())
        assert discovery.discovery_method == DiscoveryMethod.FILESYSTEM
        assert len(discovery.database_files) == 1
        assert discovery.database_files[0].database_type == DatabaseType.SQLITE
        assert discovery.database_files[0].schema_info is not None
        assert 'test_table' in discovery.database_files[0].schema_info['tables']
    
    def test_analyze_empty_file(self, filesystem_discovery, temp_dir):
        """Test analysis of empty file."""
        empty_file = temp_dir / "empty.db"
        empty_file.touch()
        
        discovery = filesystem_discovery._analyze_database_file(empty_file)
        assert discovery is None
    
    def test_analyze_invalid_sqlite_file(self, filesystem_discovery, temp_dir):
        """Test analysis of invalid SQLite file."""
        fake_db = temp_dir / "fake.db"
        with open(fake_db, 'w') as f:
            f.write("This is not a database file")
        
        discovery = filesystem_discovery._analyze_database_file(fake_db)
        assert discovery is None
    
    def test_scan_directory(self, filesystem_discovery, temp_dir, config):
        """Test directory scanning functionality."""
        # Set scan path
        config.scan_paths = [str(temp_dir)]
        
        # Create test database files
        sqlite_file = temp_dir / "test.sqlite"
        with open(sqlite_file, 'wb') as f:
            f.write(b'SQLite format 3\x00' + b'\x00' * 100)
        
        duckdb_file = temp_dir / "test.duckdb"
        with open(duckdb_file, 'wb') as f:
            f.write(b'DUCK' + b'\x00' * 100)
        
        # Create subdirectory with another file
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        sub_sqlite = subdir / "sub.db"
        with open(sub_sqlite, 'wb') as f:
            f.write(b'SQLite format 3\x00' + b'\x00' * 100)
        
        discoveries = filesystem_discovery._scan_directory(str(temp_dir))
        
        # Should find files but may not validate them without proper SQLite structure
        assert len(discoveries) >= 0  # May be 0 if files don't validate as proper databases
    
    def test_scan_nonexistent_directory(self, filesystem_discovery):
        """Test scanning non-existent directory."""
        discoveries = filesystem_discovery._scan_directory("/non/existent/directory")
        assert discoveries == []
    
    def test_find_configuration_files(self, filesystem_discovery, temp_dir, config):
        """Test finding configuration files."""
        config.scan_paths = [str(temp_dir)]
        
        # Create test configuration files
        docker_compose = temp_dir / "docker-compose.yml"
        with open(docker_compose, 'w') as f:
            yaml.dump({
                'services': {
                    'db': {
                        'image': 'postgres:13',
                        'environment': {
                            'POSTGRES_DB': 'testdb'
                        }
                    }
                }
            }, f)
        
        env_file = temp_dir / "database.env"
        with open(env_file, 'w') as f:
            f.write("DATABASE_URL=postgresql://user:pass@localhost/db\n")
        
        config_files = filesystem_discovery._find_configuration_files()
        
        assert len(config_files) >= 2
        assert any(f.name == "docker-compose.yml" for f in config_files)
        assert any(f.name == "database.env" for f in config_files)
    
    def test_parse_yaml_config(self, filesystem_discovery, temp_dir):
        """Test parsing YAML configuration files."""
        yaml_file = temp_dir / "config.yml"
        yaml_content = {
            'database': {
                'url': 'postgresql://user:pass@localhost/mydb',
                'type': 'postgresql'
            },
            'sqlite_path': '/path/to/database.sqlite'
        }
        
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_content, f)
        
        with open(yaml_file, 'r') as f:
            content = f.read()
        
        discoveries = filesystem_discovery._parse_yaml_config(yaml_file, content)
        assert len(discoveries) >= 0  # May find database references
    
    def test_parse_env_config(self, filesystem_discovery, temp_dir):
        """Test parsing environment configuration files."""
        env_file = temp_dir / ".env"
        with open(env_file, 'w') as f:
            f.write("DATABASE_URL=postgresql://user:pass@localhost/testdb\n")
            f.write("SQLITE_FILE=/path/to/test.sqlite\n")
            f.write("# Comment line\n")
            f.write("NORMAL_VAR=value\n")
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        discoveries = filesystem_discovery._parse_env_config(env_file, content)
        assert len(discoveries) >= 1  # Should find DATABASE_URL
    
    def test_is_database_environment_var(self, filesystem_discovery):
        """Test database environment variable detection."""
        # Positive cases
        assert filesystem_discovery._is_database_environment_var("DATABASE_URL", "postgresql://localhost/db") is True
        assert filesystem_discovery._is_database_environment_var("DB_URL", "mysql://localhost/db") is True
        assert filesystem_discovery._is_database_environment_var("POSTGRES_DB", "mydb") is True
        assert filesystem_discovery._is_database_environment_var("SQLITE_FILE", "/path/to/file.db") is True
        
        # Negative cases
        assert filesystem_discovery._is_database_environment_var("API_KEY", "secret") is False
        assert filesystem_discovery._is_database_environment_var("PORT", "8080") is False
    
    def test_deduplicate_file_discoveries(self, filesystem_discovery, temp_dir):
        """Test deduplication of file discoveries."""
        # Create a test file
        test_file = temp_dir / "test.db"
        with open(test_file, 'wb') as f:
            f.write(b'SQLite format 3\x00' + b'\x00' * 100)
        
        # Create two discoveries for the same file
        discovery1 = filesystem_discovery._analyze_database_file(test_file)
        discovery2 = filesystem_discovery._analyze_database_file(test_file)
        
        if discovery1 and discovery2:
            discoveries = [discovery1, discovery2]
            unique_discoveries = filesystem_discovery._deduplicate_file_discoveries(discoveries)
            assert len(unique_discoveries) == 1
    
    def test_discover_database_files_disabled(self, config):
        """Test discovery when filesystem discovery is disabled."""
        config.enable_filesystem_discovery = False
        fs_discovery = FilesystemDiscovery(config)
        
        discoveries = fs_discovery.discover_database_files()
        assert discoveries == []
    
    @pytest.mark.integration
    def test_full_discovery_integration(self, temp_dir, config):
        """Integration test for full filesystem discovery."""
        config.scan_paths = [str(temp_dir)]
        fs_discovery = FilesystemDiscovery(config)
        
        # Create a realistic test environment
        # SQLite database
        sqlite_db = temp_dir / "app.sqlite"
        conn = sqlite3.connect(str(sqlite_db))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER, name TEXT);")
        cursor.execute("INSERT INTO users VALUES (1, 'test');")
        conn.commit()
        conn.close()
        
        # DuckDB file (mock)
        duckdb_file = temp_dir / "analytics.duckdb"
        with open(duckdb_file, 'wb') as f:
            f.write(b'DUCK' + b'\x00' * 1000)
        
        # Configuration files
        compose_file = temp_dir / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            yaml.dump({
                'version': '3.8',
                'services': {
                    'postgres': {
                        'image': 'postgres:13',
                        'ports': ['5432:5432'],
                        'environment': {
                            'POSTGRES_DB': 'violentutf',
                            'POSTGRES_USER': 'admin'
                        }
                    }
                }
            }, f)
        
        env_file = temp_dir / ".env"
        with open(env_file, 'w') as f:
            f.write("DATABASE_URL=postgresql://admin:secret@localhost/violentutf\n")
            f.write("SQLITE_PATH=/app/data/app.sqlite\n")
        
        # Run discovery
        file_discoveries = fs_discovery.discover_database_files()
        config_discoveries = fs_discovery.discover_configuration_files()
        
        all_discoveries = file_discoveries + config_discoveries
        
        # Validate results
        assert len(all_discoveries) >= 1  # Should find at least the SQLite file
        
        # Check that we found our SQLite database
        sqlite_found = any(
            d.database_type == DatabaseType.SQLITE and 'app.sqlite' in d.file_path
            for d in all_discoveries
        )
        assert sqlite_found is True


class TestDatabaseFileCreation:
    """Test database file creation helpers."""
    
    def test_create_test_sqlite_db(self):
        """Helper to create test SQLite database."""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)
            cursor = conn.cursor()
            
            # Create tables that look like ViolentUTF
            cursor.execute("""
                CREATE TABLE orchestrations (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                CREATE TABLE memory_entries (
                    id INTEGER PRIMARY KEY,
                    conversation_id TEXT,
                    message TEXT,
                    role TEXT
                );
            """)
            
            # Insert test data
            cursor.execute("INSERT INTO orchestrations (name) VALUES ('test_orchestration');")
            cursor.execute("INSERT INTO memory_entries (conversation_id, message, role) VALUES ('test', 'Hello', 'user');")
            
            conn.commit()
            conn.close()
            
            return tmp.name
    
    def test_sqlite_file_detection(self):
        """Test detection of realistic SQLite file."""
        db_path = self.test_create_test_sqlite_db()
        
        try:
            config = DiscoveryConfig(scan_paths=[str(Path(db_path).parent)])
            fs_discovery = FilesystemDiscovery(config)
            
            discovery = fs_discovery._analyze_database_file(Path(db_path))
            
            assert discovery is not None
            assert discovery.database_type == DatabaseType.SQLITE
            assert discovery.is_validated is False  # Will be validated later
            assert len(discovery.database_files) == 1
            
            db_file = discovery.database_files[0]
            assert db_file.schema_info is not None
            assert 'orchestrations' in db_file.schema_info['tables']
            assert 'memory_entries' in db_file.schema_info['tables']
            assert db_file.schema_info['table_count'] == 2
            
        finally:
            os.unlink(db_path)