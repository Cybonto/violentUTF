# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Code-based database discovery using Abstract Syntax Tree (AST) analysis.

Analyzes Python source code for database imports, connections, and patterns.
"""

import ast
import logging
import re
from pathlib import Path
from typing import List, Optional

from .exceptions import CodeDiscoveryError
from .models import CodeReference, DatabaseDiscovery, DatabaseType, DiscoveryConfig, DiscoveryMethod
from .utils import (
    calculate_confidence_score,
    generate_database_id,
    is_likely_test_file,
    measure_execution_time,
    parse_connection_string,
)


class CodeDiscovery:
    """Python code analysis for database discovery using AST."""

    def __init__(self, config: DiscoveryConfig) -> None:
        """Initialize the code discovery module with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Database-related imports to look for
        self.database_imports = {
            # SQLite imports
            "sqlite3": DatabaseType.SQLITE,
            "aiosqlite": DatabaseType.SQLITE,
            "sqlite": DatabaseType.SQLITE,
            # PostgreSQL imports
            "psycopg2": DatabaseType.POSTGRESQL,
            "psycopg": DatabaseType.POSTGRESQL,
            "asyncpg": DatabaseType.POSTGRESQL,
            "pg8000": DatabaseType.POSTGRESQL,
            # DuckDB imports
            "duckdb": DatabaseType.DUCKDB,
            # ORM imports (typically PostgreSQL in ViolentUTF)
            "sqlalchemy": DatabaseType.POSTGRESQL,
            "alembic": DatabaseType.POSTGRESQL,
            "databases": DatabaseType.POSTGRESQL,
            # FastAPI database dependencies
            "fastapi": DatabaseType.SQLITE,  # ViolentUTF uses SQLite with FastAPI
        }

        # Connection string patterns
        self.connection_patterns = {
            r"postgresql://": DatabaseType.POSTGRESQL,
            r"postgres://": DatabaseType.POSTGRESQL,
            r"sqlite:///": DatabaseType.SQLITE,
            r"sqlite://": DatabaseType.SQLITE,
            r"duckdb://": DatabaseType.DUCKDB,
        }

        # Database-related function calls
        self.database_functions = {
            "sqlite3.connect": DatabaseType.SQLITE,
            "aiosqlite.connect": DatabaseType.SQLITE,
            "psycopg2.connect": DatabaseType.POSTGRESQL,
            "asyncpg.connect": DatabaseType.POSTGRESQL,
            "duckdb.connect": DatabaseType.DUCKDB,
            "create_engine": DatabaseType.POSTGRESQL,  # SQLAlchemy
        }

        # SQLAlchemy model indicators
        self.sqlalchemy_indicators = [
            "declarative_base",
            "DeclarativeBase",
            "Base",
            "Column",
            "relationship",
            "ForeignKey",
        ]

    @measure_execution_time
    def discover_code_databases(self) -> List[DatabaseDiscovery]:
        """
        Discover databases through Python code analysis.

        Returns:
            List of database discoveries from code analysis
        """
        if not self.config.enable_code_discovery:
            self.logger.info("Code discovery disabled in configuration")
            return []

        discoveries = []

        try:
            # Find all Python files
            python_files = self._find_python_files()
            self.logger.info("Found %d Python files to analyze", len(python_files))

            # Analyze each file
            for file_path in python_files:
                try:
                    file_discoveries = self._analyze_python_file(file_path)
                    discoveries.extend(file_discoveries)

                except Exception as e:
                    self.logger.warning("Error analyzing Python file %s: %s", file_path, e)
                    continue

            # Group code references into discoveries
            grouped_discoveries = self._group_code_references(discoveries)

            self.logger.info("Discovered %d databases from code analysis", len(grouped_discoveries))
            return grouped_discoveries

        except Exception as e:
            raise CodeDiscoveryError(f"Code discovery failed: {e}") from e

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the configured scan paths."""
        python_files = []

        for scan_path in self.config.scan_paths:
            base_path = Path(scan_path)

            if not base_path.exists():
                continue

            # Find .py files recursively
            for py_file in base_path.rglob("*.py"):
                if self._should_analyze_file(py_file):
                    python_files.append(py_file)

        return python_files

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if a Python file should be analyzed."""
        # Skip test files
        if is_likely_test_file(str(file_path)):
            return False

        # Skip excluded patterns
        file_str = str(file_path).lower()
        for pattern in self.config.exclude_patterns:
            if pattern.lower() in file_str:
                return False

        # Skip files that are too large
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 10:  # Skip files larger than 10MB
                return False
        except OSError:
            return False

        return True

    def _analyze_python_file(self, file_path: Path) -> List[CodeReference]:
        """Analyze a Python file for database-related code."""
        code_references = []

        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                self.logger.debug("Syntax error in %s: %s", file_path, e)
                return []

            # Analyze AST
            visitor = DatabaseASTVisitor(str(file_path), self)
            visitor.visit(tree)
            code_references.extend(visitor.code_references)

            # Also do text-based analysis for patterns AST might miss
            text_references = self._analyze_file_text(file_path, content)
            code_references.extend(text_references)

        except Exception as e:
            self.logger.warning("Error reading file %s: %s", file_path, e)

        return code_references

    def _analyze_file_text(self, file_path: Path, content: str) -> List[CodeReference]:
        """Analyze file content for database connection strings and patterns."""
        references = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Look for connection string patterns
            for pattern, db_type in self.connection_patterns.items():
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Extract the full connection string
                    start_pos = match.start()
                    connection_string = self._extract_connection_string(line, start_pos)

                    if connection_string:
                        ref = CodeReference(
                            file_path=str(file_path),
                            line_number=line_num,
                            code_snippet=line.strip(),
                            reference_type="connection_string",
                            database_type=db_type,
                            connection_string=connection_string,
                            is_credential=self._looks_like_credential(connection_string),
                        )
                        references.append(ref)

            # Look for database file paths
            db_file_patterns = [
                r'[\'"](/[^/]*)*\.db[\'"]',  # Unix paths to .db files
                r'[\'"](/[^/]*)*\.sqlite[\'"]',  # Unix paths to .sqlite files
                r'[\'"](/[^/]*)*\.duckdb[\'"]',  # Unix paths to .duckdb files
            ]

            for pattern in db_file_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    file_path_match = match.group().strip("'\"")
                    db_type = self._detect_db_type_from_path(file_path_match)

                    ref = CodeReference(
                        file_path=str(file_path),
                        line_number=line_num,
                        code_snippet=line.strip(),
                        reference_type="file_path",
                        database_type=db_type,
                        connection_string=f"file://{file_path_match}",
                    )
                    references.append(ref)

        return references

    def _extract_connection_string(self, line: str, start_pos: int) -> Optional[str]:
        """Extract a complete connection string from a line."""
        # Look for quoted strings containing the connection string
        for quote in ['"', "'"]:
            quote_start = line.rfind(quote, 0, start_pos)
            if quote_start != -1:
                quote_end = line.find(quote, start_pos + 1)
                if quote_end != -1:
                    return line[quote_start + 1 : quote_end]

        # Fallback: extract until whitespace
        end_pos = len(line)
        for i in range(start_pos, len(line)):
            if line[i].isspace():
                end_pos = i
                break

        return line[start_pos:end_pos]

    def _looks_like_credential(self, connection_string: str) -> bool:
        """Check if a connection string contains credentials."""
        return ":" in connection_string and "@" in connection_string

    def _detect_db_type_from_path(self, file_path: str) -> DatabaseType:
        """Detect database type from file path."""
        path_lower = file_path.lower()

        if path_lower.endswith(".db") or path_lower.endswith(".sqlite") or path_lower.endswith(".sqlite3"):
            return DatabaseType.SQLITE
        elif path_lower.endswith(".duckdb"):
            return DatabaseType.DUCKDB
        else:
            return DatabaseType.UNKNOWN

    def _group_code_references(self, code_references: List[CodeReference]) -> List[DatabaseDiscovery]:
        """Group code references into database discoveries."""
        discoveries = []

        # Group by database type and connection
        groups = {}

        for ref in code_references:
            if ref.database_type == DatabaseType.UNKNOWN:
                continue

            # Create grouping key
            key_parts = [ref.database_type.value]

            if ref.connection_string:
                parsed = parse_connection_string(ref.connection_string)
                if parsed:
                    if parsed.get("host"):
                        key_parts.append(f"host:{parsed['host']}")
                    if parsed.get("port"):
                        key_parts.append(f"port:{parsed['port']}")
                    if parsed.get("database"):
                        key_parts.append(f"db:{parsed['database']}")
                    if parsed.get("path"):
                        key_parts.append(f"path:{parsed['path']}")
                else:
                    key_parts.append(f"conn:{ref.connection_string}")
            else:
                # Group by file for imports without explicit connections
                key_parts.append(f"file:{Path(ref.file_path).parent}")

            group_key = "|".join(key_parts)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(ref)

        # Create discoveries from groups
        for group_key, refs in groups.items():
            discovery = self._create_discovery_from_code_group(group_key, refs)
            if discovery:
                discoveries.append(discovery)

        return discoveries

    def _create_discovery_from_code_group(
        self, group_key: str, refs: List[CodeReference]
    ) -> Optional[DatabaseDiscovery]:
        """Create DatabaseDiscovery from grouped code references."""
        if not refs:
            return None

        try:
            # Use the first reference as the primary reference
            primary_ref = refs[0]
            database_type = primary_ref.database_type

            # Generate unique ID
            db_id = generate_database_id(database_type, f"code:{group_key}")

            # Extract connection details
            host = None
            port = None
            file_path = None
            connection_string = None

            for ref in refs:
                if ref.connection_string:
                    connection_string = ref.connection_string
                    parsed = parse_connection_string(ref.connection_string)
                    if parsed:
                        host = parsed.get("host") or host
                        port = int(parsed["port"]) if parsed.get("port") else port
                        file_path = parsed.get("path") or file_path
                    break

            # Calculate confidence score
            detection_methods = []
            unique_files = set(ref.file_path for ref in refs)

            if any(ref.reference_type == "import" for ref in refs):
                detection_methods.append("imports")
            if any(ref.reference_type == "function_call" for ref in refs):
                detection_methods.append("function_calls")
            if any(ref.reference_type == "connection_string" for ref in refs):
                detection_methods.append("connection_strings")

            validation_results = {
                "multiple_files": len(unique_files) > 1,
                "has_connection_string": connection_string is not None,
                "has_function_calls": any(ref.reference_type == "function_call" for ref in refs),
                "consistent_type": all(ref.database_type == database_type for ref in refs),
            }

            confidence_score, confidence_level = calculate_confidence_score(detection_methods, validation_results)

            # Determine if this appears to be an active ViolentUTF database
            is_violentutf = any(
                "violentutf" in ref.file_path.lower() or "pyrit" in ref.file_path.lower() for ref in refs
            )

            # Create discovery
            discovery = DatabaseDiscovery(
                database_id=db_id,
                database_type=database_type,
                name=f"Code: {database_type.value} ({len(refs)} references)",
                description=f"Database discovered through code analysis in {len(unique_files)} files",
                host=host,
                port=port,
                file_path=file_path,
                connection_string=connection_string,
                discovery_method=DiscoveryMethod.CODE_ANALYSIS,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                is_active=True,  # If code references exist, likely active
                code_references=refs,
                tags=["code-analysis", database_type.value] + (["violentutf"] if is_violentutf else []),
                custom_properties={
                    "reference_count": len(refs),
                    "file_count": len(unique_files),
                    "has_credentials": any(ref.is_credential for ref in refs),
                    "reference_types": list(set(ref.reference_type for ref in refs)),
                },
            )

            return discovery

        except Exception as e:
            self.logger.error("Failed to create discovery from code group: %s", e)
            return None

    @measure_execution_time
    def analyze_requirements_files(self) -> List[DatabaseDiscovery]:
        """
        Analyze requirements.txt files for database dependencies.

        Returns:
            List of database discoveries from requirements analysis
        """
        discoveries = []

        try:
            # Find requirements files
            req_files = self._find_requirements_files()
            self.logger.info("Found %d requirements files to analyze", len(req_files))

            for req_file in req_files:
                try:
                    file_discoveries = self._analyze_requirements_file(req_file)
                    discoveries.extend(file_discoveries)

                except Exception as e:
                    self.logger.warning("Error analyzing requirements file %s: %s", req_file, e)
                    continue

            self.logger.info("Discovered %d database dependencies", len(discoveries))
            return discoveries

        except Exception as e:
            self.logger.error("Requirements analysis failed: %s", e)
            return []

    def _find_requirements_files(self) -> List[Path]:
        """Find requirements files in the project."""
        req_files = []

        for scan_path in self.config.scan_paths:
            base_path = Path(scan_path)
            if not base_path.exists():
                continue

            # Look for various requirements file patterns
            patterns = ["requirements*.txt", "pyproject.toml", "setup.py", "Pipfile"]

            for pattern in patterns:
                req_files.extend(base_path.rglob(pattern))

        return req_files

    def _analyze_requirements_file(self, req_file: Path) -> List[DatabaseDiscovery]:
        """Analyze a requirements file for database dependencies."""
        discoveries = []

        try:
            with open(req_file, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Extract package name (before version specifiers)
                package = re.split(r"[>=<!=]", line)[0].strip()

                # Check if this is a database-related package
                if package.lower() in self.database_imports:
                    database_type = self.database_imports[package.lower()]

                    discovery = self._create_discovery_from_dependency(package, database_type, req_file, line_num, line)

                    if discovery:
                        discoveries.append(discovery)

        except Exception as e:
            self.logger.warning("Error reading requirements file %s: %s", req_file, e)

        return discoveries

    def _create_discovery_from_dependency(
        self, package: str, database_type: DatabaseType, req_file: Path, line_num: int, line: str
    ) -> Optional[DatabaseDiscovery]:
        """Create DatabaseDiscovery from a dependency."""
        try:
            # Generate unique ID
            db_id = generate_database_id(database_type, f"dependency:{req_file.name}:{package}")

            # Calculate confidence score (lower for dependencies alone)
            detection_methods = ["dependency"]
            validation_results = {
                "known_db_package": True,
                "in_requirements": True,
                "explicit_version": "=" in line or ">" in line or "<" in line,
            }

            confidence_score, confidence_level = calculate_confidence_score(
                detection_methods, validation_results, consistency_score=0.6
            )

            # Create code reference
            code_ref = CodeReference(
                file_path=str(req_file),
                line_number=line_num,
                code_snippet=line,
                reference_type="dependency",
                database_type=database_type,
            )

            # Create discovery
            discovery = DatabaseDiscovery(
                database_id=db_id,
                database_type=database_type,
                name=f"Dependency: {package}",
                description=f"Database dependency in {req_file.name}",
                discovery_method=DiscoveryMethod.CODE_ANALYSIS,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                is_active=False,  # Dependencies don't indicate active usage
                code_references=[code_ref],
                tags=["dependency", database_type.value, req_file.suffix[1:]],
                custom_properties={
                    "package_name": package,
                    "requirements_file": str(req_file),
                    "requirement_line": line,
                },
            )

            return discovery

        except Exception as e:
            self.logger.error("Failed to create discovery from dependency %s: %s", package, e)
            return None


class DatabaseASTVisitor(ast.NodeVisitor):
    """AST visitor to find database-related code patterns."""

    def __init__(self, file_path: str, code_discovery: CodeDiscovery) -> None:
        """Initialize the AST visitor with file path and discovery instance."""
        self.file_path = file_path
        self.code_discovery = code_discovery
        self.code_references = []

        # Track imports for context
        self.imports = {}  # module_name -> alias or module_name
        self.from_imports = {}  # name -> module

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            module_name = alias.name
            alias_name = alias.asname or module_name

            # Check if this is a database-related import
            if module_name in self.code_discovery.database_imports:
                database_type = self.code_discovery.database_imports[module_name]

                ref = CodeReference(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    code_snippet=self._get_code_snippet(node),
                    reference_type="import",
                    database_type=database_type,
                )
                self.code_references.append(ref)

            self.imports[alias_name] = module_name

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from import statements."""
        if node.module:
            for alias in node.names:
                name = alias.name
                alias_name = alias.asname or name

                # Check if importing from a database module
                if node.module in self.code_discovery.database_imports:
                    database_type = self.code_discovery.database_imports[node.module]

                    ref = CodeReference(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        code_snippet=self._get_code_snippet(node),
                        reference_type="import",
                        database_type=database_type,
                    )
                    self.code_references.append(ref)

                self.from_imports[alias_name] = node.module

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls."""
        # Get the function name
        func_name = self._get_function_name(node.func)

        if func_name:
            # Check for database function calls
            for db_func, db_type in self.code_discovery.database_functions.items():
                if func_name == db_func or func_name.endswith("." + db_func.split(".")[-1]):
                    ref = CodeReference(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        code_snippet=self._get_code_snippet(node),
                        reference_type="function_call",
                        database_type=db_type,
                    )
                    self.code_references.append(ref)
                    break

            # Special handling for SQLAlchemy create_engine
            if func_name.endswith("create_engine"):
                # Try to extract connection string from arguments
                if node.args and isinstance(node.args[0], ast.Constant):
                    connection_string = node.args[0].value
                    if isinstance(connection_string, str):
                        parsed = parse_connection_string(connection_string)
                        if parsed:
                            db_type = DatabaseType.POSTGRESQL  # Default for SQLAlchemy in ViolentUTF
                            if parsed.get("type") == "sqlite":
                                db_type = DatabaseType.SQLITE

                            ref = CodeReference(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                code_snippet=self._get_code_snippet(node),
                                reference_type="function_call",
                                database_type=db_type,
                                connection_string=connection_string,
                                # pylint: disable=protected-access
                                is_credential=self.code_discovery._looks_like_credential(connection_string),
                            )
                            self.code_references.append(ref)

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to find SQLAlchemy models."""
        # Check if this looks like a SQLAlchemy model
        if self._is_sqlalchemy_model(node):
            ref = CodeReference(
                file_path=self.file_path,
                line_number=node.lineno,
                code_snippet=f"class {node.name}:",
                reference_type="model_class",
                database_type=DatabaseType.POSTGRESQL,  # SQLAlchemy typically PostgreSQL in ViolentUTF
            )
            self.code_references.append(ref)

        self.generic_visit(node)

    def _get_function_name(self, func_node: ast.expr) -> Optional[str]:
        """Extract function name from a function call node."""
        try:
            if isinstance(func_node, ast.Name):
                return func_node.id
            elif isinstance(func_node, ast.Attribute):
                # Handle module.function calls
                if isinstance(func_node.value, ast.Name):
                    return f"{func_node.value.id}.{func_node.attr}"
                else:
                    return func_node.attr
            return None
        except Exception:
            return None

    def _is_sqlalchemy_model(self, class_node: ast.ClassDef) -> bool:
        """Check if a class definition is a SQLAlchemy model."""
        # Check base classes
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                if base.id in ["Base", "DeclarativeBase"]:
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ["Base", "DeclarativeBase"]:
                    return True

        # Check for SQLAlchemy indicators in class body
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Look for Column assignments
                        if isinstance(node.value, ast.Call):
                            func_name = self._get_function_name(node.value.func)
                            if func_name and "Column" in func_name:
                                return True

        return False

    def _get_code_snippet(self, node: ast.AST) -> str:
        """Get a code snippet for the AST node."""
        try:
            # This is a simplified version - in a real implementation,
            # you might want to use the ast.get_source_segment function
            # or maintain the original source code
            return f"Line {node.lineno}"
        except Exception:
            return "Unknown"
