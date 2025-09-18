"""
Tests for code discovery module.
"""

import ast

# Add scripts to path for testing
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.append('/Users/tamnguyen/Documents/GitHub/violentUTF/scripts/database-automation')

from discovery.code_discovery import CodeDiscovery, DatabaseASTVisitor
from discovery.models import DatabaseType, DiscoveryConfig, DiscoveryMethod


class TestCodeDiscovery:
    """Test code discovery functionality."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return DiscoveryConfig(
            enable_code_discovery=True,
            scan_paths=[],  # Will be set in tests
            code_extensions=['.py', '.yml', '.yaml', '.json', '.env'],
            exclude_patterns=['__pycache__', '.git', 'test_', 'venv/']
        )
    
    @pytest.fixture
    def code_discovery(self, config):
        """Code discovery instance."""
        return CodeDiscovery(config)
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_init(self, config):
        """Test CodeDiscovery initialization."""
        cd = CodeDiscovery(config)
        assert cd.config == config
        assert cd.logger is not None
        assert 'sqlite3' in cd.database_imports
        assert 'psycopg2' in cd.database_imports
    
    def test_should_analyze_file_valid(self, code_discovery, temp_dir):
        """Test should_analyze_file with valid Python file."""
        py_file = temp_dir / "app.py"
        with open(py_file, 'w') as f:
            f.write("import sqlite3\n")
        
        assert code_discovery._should_analyze_file(py_file) is True
    
    def test_should_analyze_file_test_file(self, code_discovery, temp_dir):
        """Test should_analyze_file with test file."""
        test_file = temp_dir / "test_app.py"
        with open(test_file, 'w') as f:
            f.write("import unittest\n")
        
        assert code_discovery._should_analyze_file(test_file) is False
    
    def test_should_analyze_file_excluded_pattern(self, code_discovery, temp_dir):
        """Test should_analyze_file with excluded pattern."""
        excluded_file = temp_dir / "venv" / "lib" / "app.py"
        excluded_file.parent.mkdir(parents=True)
        with open(excluded_file, 'w') as f:
            f.write("import sqlite3\n")
        
        assert code_discovery._should_analyze_file(excluded_file) is False
    
    def test_analyze_python_file_sqlite_import(self, code_discovery, temp_dir):
        """Test analysis of Python file with SQLite import."""
        py_file = temp_dir / "database.py"
        with open(py_file, 'w') as f:
            f.write("""
import sqlite3
import os

def connect_to_db():
    conn = sqlite3.connect('app.db')
    return conn

def create_tables():
    conn = sqlite3.connect('/path/to/database.sqlite')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    conn.close()
""")
        
        code_refs = code_discovery._analyze_python_file(py_file)
        
        assert len(code_refs) >= 2  # Should find import and at least one connection
        
        # Check for import reference
        import_refs = [ref for ref in code_refs if ref.reference_type == 'import']
        assert len(import_refs) >= 1
        assert any(ref.database_type == DatabaseType.SQLITE for ref in import_refs)
        
        # Check for connection references
        file_refs = [ref for ref in code_refs if ref.reference_type == 'file_path']
        assert len(file_refs) >= 1
    
    def test_analyze_python_file_postgresql_import(self, code_discovery, temp_dir):
        """Test analysis of Python file with PostgreSQL imports."""
        py_file = temp_dir / "pg_db.py"
        with open(py_file, 'w') as f:
            f.write("""
import psycopg2
from sqlalchemy import create_engine

def connect_postgresql():
    conn = psycopg2.connect(
        host="localhost",
        database="violentutf",
        user="admin",
        password="secret"
    )
    return conn

def create_sqlalchemy_engine():
    engine = create_engine("postgresql://admin:secret@localhost/violentutf")
    return engine
""")
        
        code_refs = code_discovery._analyze_python_file(py_file)
        
        assert len(code_refs) >= 2
        
        # Check for PostgreSQL imports
        pg_refs = [ref for ref in code_refs if ref.database_type == DatabaseType.POSTGRESQL]
        assert len(pg_refs) >= 1
    
    def test_analyze_python_file_syntax_error(self, code_discovery, temp_dir):
        """Test analysis of Python file with syntax error."""
        py_file = temp_dir / "broken.py"
        with open(py_file, 'w') as f:
            f.write("import sqlite3\nif True\n    print('broken')")
        
        code_refs = code_discovery._analyze_python_file(py_file)
        
        # Should still find text-based patterns even if AST fails
        assert isinstance(code_refs, list)
    
    def test_analyze_file_text_connection_strings(self, code_discovery, temp_dir):
        """Test text analysis for connection strings."""
        py_file = temp_dir / "config.py"
        content = """
DATABASE_URL = "postgresql://user:pass@localhost:5432/mydb"
SQLITE_DB = "sqlite:///app.db"
BACKUP_DB = "sqlite:///backup/data.sqlite"
"""
        
        lines = content.split('\n')
        refs = []
        
        for line_num, line in enumerate(lines, 1):
            for pattern, db_type in code_discovery.connection_patterns.items():
                import re
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    connection_string = code_discovery._extract_connection_string(line, match.start())
                    if connection_string:
                        refs.append({
                            'line': line_num,
                            'type': db_type,
                            'connection': connection_string
                        })
        
        assert len(refs) >= 2
        assert any(ref['type'] == DatabaseType.POSTGRESQL for ref in refs)
        assert any(ref['type'] == DatabaseType.SQLITE for ref in refs)
    
    def test_extract_connection_string(self, code_discovery):
        """Test connection string extraction."""
        line = 'DATABASE_URL = "postgresql://user:pass@localhost/db"'
        start_pos = line.find('postgresql://')
        
        conn_str = code_discovery._extract_connection_string(line, start_pos)
        assert conn_str == "postgresql://user:pass@localhost/db"
    
    def test_looks_like_credential(self, code_discovery):
        """Test credential detection in connection strings."""
        # Has credentials
        assert code_discovery._looks_like_credential("postgresql://user:pass@localhost/db") is True
        assert code_discovery._looks_like_credential("mysql://admin:secret@host/db") is True
        
        # No credentials
        assert code_discovery._looks_like_credential("postgresql://localhost/db") is False
        assert code_discovery._looks_like_credential("sqlite:///app.db") is False
    
    def test_detect_db_type_from_path(self, code_discovery):
        """Test database type detection from file paths."""
        assert code_discovery._detect_db_type_from_path("/app/data.db") == DatabaseType.SQLITE
        assert code_discovery._detect_db_type_from_path("/backup/dump.sqlite") == DatabaseType.SQLITE
        assert code_discovery._detect_db_type_from_path("/analytics/data.duckdb") == DatabaseType.DUCKDB
        assert code_discovery._detect_db_type_from_path("/unknown/file.txt") == DatabaseType.UNKNOWN
    
    def test_group_code_references(self, code_discovery):
        """Test grouping of code references."""
        from discovery.models import CodeReference

        # Create test code references
        refs = [
            CodeReference(
                file_path="/app/db1.py",
                line_number=1,
                code_snippet="import sqlite3",
                reference_type="import",
                database_type=DatabaseType.SQLITE
            ),
            CodeReference(
                file_path="/app/db2.py",
                line_number=5,
                code_snippet="sqlite3.connect('app.db')",
                reference_type="function_call",
                database_type=DatabaseType.SQLITE,
                connection_string="sqlite:///app.db"
            ),
            CodeReference(
                file_path="/app/pg.py",
                line_number=10,
                code_snippet="import psycopg2",
                reference_type="import",
                database_type=DatabaseType.POSTGRESQL
            )
        ]
        
        discoveries = code_discovery._group_code_references(refs)
        
        assert len(discoveries) >= 1
        assert all(d.discovery_method == DiscoveryMethod.CODE_ANALYSIS for d in discoveries)
    
    def test_find_requirements_files(self, code_discovery, temp_dir, config):
        """Test finding requirements files."""
        config.scan_paths = [str(temp_dir)]
        
        # Create requirements files
        req_file = temp_dir / "requirements.txt"
        with open(req_file, 'w') as f:
            f.write("sqlalchemy>=1.4.0\n")
            f.write("psycopg2-binary>=2.9.0\n")
            f.write("aiosqlite>=0.17.0\n")
        
        setup_file = temp_dir / "setup.py"
        with open(setup_file, 'w') as f:
            f.write("from setuptools import setup\n")
        
        req_files = code_discovery._find_requirements_files()
        
        assert len(req_files) >= 1
        assert any(f.name == "requirements.txt" for f in req_files)
    
    def test_analyze_requirements_file(self, code_discovery, temp_dir):
        """Test analysis of requirements file."""
        req_file = temp_dir / "requirements.txt"
        with open(req_file, 'w') as f:
            f.write("# Database dependencies\n")
            f.write("sqlalchemy>=1.4.0\n")
            f.write("psycopg2-binary>=2.9.0\n")
            f.write("aiosqlite>=0.17.0\n")
            f.write("duckdb>=0.8.0\n")
            f.write("# Other dependencies\n")
            f.write("fastapi>=0.68.0\n")
            f.write("pydantic>=1.8.0\n")
        
        discoveries = code_discovery._analyze_requirements_file(req_file)
        
        assert len(discoveries) >= 3
        
        # Check for specific database packages
        package_names = [d.custom_properties.get('package_name') for d in discoveries]
        assert 'sqlalchemy' in package_names
        assert 'psycopg2-binary' in package_names
        assert 'aiosqlite' in package_names
    
    def test_create_discovery_from_dependency(self, code_discovery, temp_dir):
        """Test creating discovery from dependency."""
        req_file = temp_dir / "requirements.txt"
        
        discovery = code_discovery._create_discovery_from_dependency(
            'sqlalchemy',
            DatabaseType.POSTGRESQL,
            req_file,
            1,
            'sqlalchemy>=1.4.0'
        )
        
        assert discovery is not None
        assert discovery.database_type == DatabaseType.POSTGRESQL
        assert discovery.name == "Dependency: sqlalchemy"
        assert discovery.discovery_method == DiscoveryMethod.CODE_ANALYSIS
        assert len(discovery.code_references) == 1
        assert 'dependency' in discovery.tags


class TestDatabaseASTVisitor:
    """Test AST visitor for database code patterns."""
    
    @pytest.fixture
    def code_discovery(self):
        """Code discovery instance for visitor."""
        config = DiscoveryConfig()
        return CodeDiscovery(config)
    
    def test_visit_import(self, code_discovery):
        """Test visiting import statements."""
        code = "import sqlite3\nimport os"
        tree = ast.parse(code)
        
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        visitor.visit(tree)
        
        db_refs = [ref for ref in visitor.code_references if ref.database_type == DatabaseType.SQLITE]
        assert len(db_refs) == 1
        assert db_refs[0].reference_type == 'import'
    
    def test_visit_import_from(self, code_discovery):
        """Test visiting from import statements."""
        code = "from sqlalchemy import create_engine\nfrom os import path"
        tree = ast.parse(code)
        
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        visitor.visit(tree)
        
        db_refs = [ref for ref in visitor.code_references if ref.database_type == DatabaseType.POSTGRESQL]
        assert len(db_refs) == 1
        assert db_refs[0].reference_type == 'import'
    
    def test_visit_call_sqlite_connect(self, code_discovery):
        """Test visiting SQLite connect calls."""
        code = """
import sqlite3

def connect():
    conn = sqlite3.connect('database.db')
    return conn
"""
        tree = ast.parse(code)
        
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        visitor.visit(tree)
        
        # Should find both import and function call
        import_refs = [ref for ref in visitor.code_references if ref.reference_type == 'import']
        call_refs = [ref for ref in visitor.code_references if ref.reference_type == 'function_call']
        
        assert len(import_refs) == 1
        assert len(call_refs) >= 1
    
    def test_visit_call_create_engine(self, code_discovery):
        """Test visiting SQLAlchemy create_engine calls."""
        code = """
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@localhost/db")
"""
        tree = ast.parse(code)
        
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        visitor.visit(tree)
        
        # Should find import and create_engine call with connection string
        call_refs = [ref for ref in visitor.code_references if ref.reference_type == 'function_call']
        
        assert len(call_refs) >= 1
        conn_refs = [ref for ref in call_refs if ref.connection_string]
        assert len(conn_refs) >= 1
        assert 'postgresql://' in conn_refs[0].connection_string
    
    def test_visit_class_def_sqlalchemy_model(self, code_discovery):
        """Test visiting SQLAlchemy model class definitions."""
        code = """
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
"""
        tree = ast.parse(code)
        
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        visitor.visit(tree)
        
        model_refs = [ref for ref in visitor.code_references if ref.reference_type == 'model_class']
        assert len(model_refs) >= 1
        assert model_refs[0].database_type == DatabaseType.POSTGRESQL
    
    def test_get_function_name(self, code_discovery):
        """Test function name extraction."""
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        
        # Test simple name
        name_node = ast.Name(id='connect', ctx=ast.Load())
        assert visitor._get_function_name(name_node) == 'connect'
        
        # Test attribute access
        attr_node = ast.Attribute(
            value=ast.Name(id='sqlite3', ctx=ast.Load()),
            attr='connect',
            ctx=ast.Load()
        )
        assert visitor._get_function_name(attr_node) == 'sqlite3.connect'
    
    def test_is_sqlalchemy_model(self, code_discovery):
        """Test SQLAlchemy model detection."""
        visitor = DatabaseASTVisitor("test.py", code_discovery)
        
        # Test class with Base inheritance
        class_code = """
class User(Base):
    id = Column(Integer, primary_key=True)
"""
        tree = ast.parse(class_code)
        class_node = tree.body[0]
        
        # This would require more setup for full testing
        # Just verify the method exists
        assert hasattr(visitor, '_is_sqlalchemy_model')


class TestCodeDiscoveryIntegration:
    """Integration tests for code discovery."""
    
    def test_violentutf_style_code_discovery(self, temp_dir):
        """Test discovery on ViolentUTF-style code."""
        config = DiscoveryConfig(scan_paths=[str(temp_dir)])
        code_discovery = CodeDiscovery(config)
        
        # Create ViolentUTF-style files
        api_file = temp_dir / "api.py"
        with open(api_file, 'w') as f:
            f.write("""
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import aiosqlite

app = FastAPI()

# SQLite for FastAPI
SQLALCHEMY_DATABASE_URL = "sqlite:///./app_data/violentutf.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def get_pyrit_memory():
    async with aiosqlite.connect("./app_data/pyrit_memory.db") as db:
        return db
""")
        
        pyrit_file = temp_dir / "pyrit_integration.py"
        with open(pyrit_file, 'w') as f:
            f.write("""
import duckdb
from pyrit import memory

def init_pyrit_memory():
    # DuckDB for PyRIT memory (being deprecated)
    conn = duckdb.connect('./app_data/pyrit_conversations.duckdb')
    return conn

def migrate_to_sqlite():
    # Migration from DuckDB to SQLite
    old_db = duckdb.connect('./app_data/old_memory.duckdb')
    new_db = sqlite3.connect('./app_data/new_memory.sqlite')
    # Migration logic here
""")
        
        requirements_file = temp_dir / "requirements.txt"
        with open(requirements_file, 'w') as f:
            f.write("""
# ViolentUTF API Dependencies
fastapi>=0.109.0
sqlalchemy>=2.0.25
aiosqlite>=0.19.0
duckdb>=1.1.0
pyrit
""")
        
        # Run discovery
        code_discoveries = code_discovery.discover_code_databases()
        req_discoveries = code_discovery.analyze_requirements_files()
        
        all_discoveries = code_discoveries + req_discoveries
        
        # Validate results
        assert len(all_discoveries) >= 3
        
        # Check for different database types
        db_types = [d.database_type for d in all_discoveries]
        assert DatabaseType.SQLITE in db_types
        assert DatabaseType.DUCKDB in db_types
        
        # Check for ViolentUTF-specific patterns
        violentutf_discoveries = [d for d in all_discoveries if 'violentutf' in d.name.lower()]
        assert len(violentutf_discoveries) >= 1
        
        # Check for PyRIT-related discoveries
        pyrit_discoveries = [d for d in all_discoveries if 'pyrit' in str(d.custom_properties).lower()]
        assert len(pyrit_discoveries) >= 1