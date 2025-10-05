# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# Test Suite for Issue #326: Import Migration from DuckDB to SQLite

"""Test suite to verify migration from DuckDB to SQLite manager."""

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import List, Set

import pytest


class TestImportMigration:
    """Test class for verifying import migration from DuckDB to SQLite."""

    BASE_DIR = Path("/Users/tamnguyen/Documents/GitHub/violentUTF")
    ENDPOINT_DIR = BASE_DIR / "violentutf_api/fastapi_app/app/api/endpoints"

    ENDPOINT_FILES = [
        "converters.py",
        "datasets.py",
        "generators.py",
        "scorers.py",
        "sessions.py",
    ]

    @pytest.fixture
    def endpoint_files(self) -> List[Path]:
        """Get list of endpoint file paths."""
        return [self.ENDPOINT_DIR / filename for filename in self.ENDPOINT_FILES]

    def test_tc_326_001_converters_imports_sqlite_manager(self) -> None:
        """TC-326-001: Verify converters.py imports sqlite_manager."""
        file_path = self.ENDPOINT_DIR / "converters.py"
        content = file_path.read_text()

        # Should import from sqlite_manager
        assert (
            "from app.db.sqlite_manager import get_sqlite_manager" in content
        ), "converters.py should import get_sqlite_manager"

        # Should NOT import from duckdb_manager
        assert (
            "from app.db.duckdb_manager" not in content
        ), "converters.py should not import from duckdb_manager"

    def test_tc_326_002_datasets_imports_sqlite_manager(self) -> None:
        """TC-326-002: Verify datasets.py imports sqlite_manager."""
        file_path = self.ENDPOINT_DIR / "datasets.py"
        content = file_path.read_text()

        assert (
            "from app.db.sqlite_manager import get_sqlite_manager" in content
        ), "datasets.py should import get_sqlite_manager"

        assert (
            "from app.db.duckdb_manager" not in content
        ), "datasets.py should not import from duckdb_manager"

    def test_tc_326_003_generators_imports_sqlite_manager(self) -> None:
        """TC-326-003: Verify generators.py imports sqlite_manager."""
        file_path = self.ENDPOINT_DIR / "generators.py"
        content = file_path.read_text()

        assert (
            "from app.db.sqlite_manager import get_sqlite_manager" in content
        ), "generators.py should import get_sqlite_manager"

        assert (
            "from app.db.duckdb_manager" not in content
        ), "generators.py should not import from duckdb_manager"

    def test_tc_326_004_scorers_imports_sqlite_manager(self) -> None:
        """TC-326-004: Verify scorers.py imports sqlite_manager."""
        file_path = self.ENDPOINT_DIR / "scorers.py"
        content = file_path.read_text()

        assert (
            "from app.db.sqlite_manager import get_sqlite_manager" in content
        ), "scorers.py should import get_sqlite_manager"

        assert (
            "from app.db.duckdb_manager" not in content
        ), "scorers.py should not import from duckdb_manager"

    def test_tc_326_005_sessions_imports_sqlite_manager(self) -> None:
        """TC-326-005: Verify sessions.py imports sqlite_manager."""
        file_path = self.ENDPOINT_DIR / "sessions.py"
        content = file_path.read_text()

        assert (
            "from app.db.sqlite_manager import get_sqlite_manager" in content
        ), "sessions.py should import get_sqlite_manager"

        assert (
            "from app.db.duckdb_manager" not in content
        ), "sessions.py should not import from duckdb_manager"

    def test_tc_326_006_no_duckdb_references_in_endpoints(
        self, endpoint_files: List[Path]
    ) -> None:
        """TC-326-006: Verify no get_duckdb_manager references in endpoints."""
        for file_path in endpoint_files:
            content = file_path.read_text()
            # Check for function name references
            assert (
                "get_duckdb_manager" not in content
            ), f"{file_path.name} should not reference get_duckdb_manager"

    def test_tc_326_101_converters_uses_get_sqlite_manager(self) -> None:
        """TC-326-101: Verify converters.py uses get_sqlite_manager calls."""
        file_path = self.ENDPOINT_DIR / "converters.py"
        content = file_path.read_text()

        # Count occurrences of get_sqlite_manager calls
        pattern = r"get_sqlite_manager\s*\("
        matches = re.findall(pattern, content)

        # Should have 7 occurrences based on issue spec
        assert (
            len(matches) >= 7
        ), f"converters.py should have at least 7 get_sqlite_manager calls, found {len(matches)}"

    def test_tc_326_102_datasets_uses_get_sqlite_manager(self) -> None:
        """TC-326-102: Verify datasets.py uses get_sqlite_manager calls."""
        file_path = self.ENDPOINT_DIR / "datasets.py"
        content = file_path.read_text()

        pattern = r"get_sqlite_manager\s*\("
        matches = re.findall(pattern, content)

        # Should have 6 occurrences based on grep results
        assert (
            len(matches) >= 6
        ), f"datasets.py should have at least 6 get_sqlite_manager calls, found {len(matches)}"

    def test_tc_326_103_generators_uses_get_sqlite_manager(self) -> None:
        """TC-326-103: Verify generators.py uses get_sqlite_manager calls."""
        file_path = self.ENDPOINT_DIR / "generators.py"
        content = file_path.read_text()

        pattern = r"get_sqlite_manager\s*\("
        matches = re.findall(pattern, content)

        # Should have 4 occurrences
        assert (
            len(matches) >= 4
        ), f"generators.py should have at least 4 get_sqlite_manager calls, found {len(matches)}"

    def test_tc_326_104_scorers_uses_get_sqlite_manager(self) -> None:
        """TC-326-104: Verify scorers.py uses get_sqlite_manager calls."""
        file_path = self.ENDPOINT_DIR / "scorers.py"
        content = file_path.read_text()

        pattern = r"get_sqlite_manager\s*\("
        matches = re.findall(pattern, content)

        # Should have 6 occurrences
        assert (
            len(matches) >= 6
        ), f"scorers.py should have at least 6 get_sqlite_manager calls, found {len(matches)}"

    def test_tc_326_105_sessions_uses_get_sqlite_manager(self) -> None:
        """TC-326-105: Verify sessions.py uses get_sqlite_manager calls."""
        file_path = self.ENDPOINT_DIR / "sessions.py"
        content = file_path.read_text()

        pattern = r"get_sqlite_manager\s*\("
        matches = re.findall(pattern, content)

        # Should have 3 occurrences
        assert (
            len(matches) >= 3
        ), f"sessions.py should have at least 3 get_sqlite_manager calls, found {len(matches)}"

    def test_tc_326_201_violentutf_requirements_has_correct_pyrit(self) -> None:
        """TC-326-201: Verify violentutf/requirements.txt has pyrit>=0.10.0rc0."""
        req_file = self.BASE_DIR / "violentutf/requirements.txt"
        content = req_file.read_text()

        # Check for correct PyRIT version
        assert re.search(
            r"pyrit\s*>=\s*0\.10\.0rc0", content
        ), "violentutf/requirements.txt should specify pyrit>=0.10.0rc0"

    def test_tc_326_202_api_requirements_has_correct_pyrit(self) -> None:
        """TC-326-202: Verify API requirements.txt has pyrit>=0.10.0rc0."""
        req_file = self.BASE_DIR / "violentutf_api/fastapi_app/requirements.txt"
        content = req_file.read_text()

        # Check for correct PyRIT version
        assert re.search(
            r"pyrit\s*>=\s*0\.10\.0rc0", content
        ), "violentutf_api/fastapi_app/requirements.txt should specify pyrit>=0.10.0rc0"

    def test_tc_326_401_all_endpoints_importable(
        self, endpoint_files: List[Path]
    ) -> None:
        """TC-326-401: Verify all endpoint modules can be imported."""
        # This test verifies there are no import errors
        import sys

        api_app_path = str(self.BASE_DIR / "violentutf_api/fastapi_app")
        if api_app_path not in sys.path:
            sys.path.insert(0, api_app_path)

        for file_path in endpoint_files:
            module_name = f"app.api.endpoints.{file_path.stem}"
            try:
                # Try importing the module
                __import__(module_name)
            except ImportError as e:
                pytest.fail(
                    f"Failed to import {module_name}: {e}. "
                    "This indicates import migration was not successful."
                )

    def test_tc_326_402_no_duckdb_imports_anywhere(self) -> None:
        """TC-326-402: Comprehensive check for duckdb_manager imports."""
        # Search all Python files in API endpoints
        found_violations: List[str] = []

        for file_path in self.ENDPOINT_DIR.glob("*.py"):
            if file_path.name == "__init__.py":
                continue

            content = file_path.read_text()
            if "from app.db.duckdb_manager" in content:
                found_violations.append(str(file_path.name))

        assert (
            not found_violations
        ), f"Found duckdb_manager imports in: {', '.join(found_violations)}"

    def test_tc_326_403_all_get_duckdb_calls_replaced(self) -> None:
        """TC-326-403: Verify all get_duckdb_manager calls are replaced."""
        found_violations: List[tuple] = []

        for file_path in self.ENDPOINT_DIR.glob("*.py"):
            if file_path.name == "__init__.py":
                continue

            content = file_path.read_text()
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                if "get_duckdb_manager" in line:
                    found_violations.append((file_path.name, line_num, line.strip()))

        assert (
            not found_violations
        ), f"Found get_duckdb_manager calls: {found_violations}"


class TestSQLiteManagerFunctionality:
    """Test SQLite manager provides same functionality as DuckDB manager."""

    def test_tc_326_301_sqlite_manager_creates_generators(self, tmp_path: Path) -> None:
        """TC-326-301: Test generator creation with SQLite manager."""
        import sys

        api_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/violentutf_api/fastapi_app"
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from app.db.sqlite_manager import get_sqlite_manager

        # Create manager with temp directory
        manager = get_sqlite_manager("test_user")
        manager.app_data_dir = str(tmp_path)
        manager.db_path = manager._get_db_path()
        manager._ensure_tables()

        # Create generator
        gen_id = manager.create_generator(
            name="test_generator",
            generator_type="openai",
            parameters={"model": "gpt-4", "temperature": 0.7},
        )

        assert gen_id is not None
        assert isinstance(gen_id, str)

        # Retrieve generator
        generator = manager.get_generator(gen_id)
        assert generator is not None
        assert generator["name"] == "test_generator"
        assert generator["type"] == "openai"
        assert generator["parameters"]["model"] == "gpt-4"

    def test_tc_326_302_sqlite_manager_creates_datasets(self, tmp_path: Path) -> None:
        """TC-326-302: Test dataset creation with SQLite manager."""
        import sys

        api_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/violentutf_api/fastapi_app"
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from app.db.sqlite_manager import get_sqlite_manager

        manager = get_sqlite_manager("test_user")
        manager.app_data_dir = str(tmp_path)
        manager.db_path = manager._get_db_path()
        manager._ensure_tables()

        # Create dataset
        dataset_id = manager.create_dataset(
            name="test_dataset",
            source_type="huggingface",
            configuration={"dataset_name": "test/dataset"},
            prompts=["prompt1", "prompt2", "prompt3"],
        )

        assert dataset_id is not None

        # Retrieve dataset
        dataset = manager.get_dataset(dataset_id)
        assert dataset is not None
        assert dataset["name"] == "test_dataset"
        assert len(dataset["prompts"]) == 3

    def test_tc_326_303_sqlite_manager_creates_converters(self, tmp_path: Path) -> None:
        """TC-326-303: Test converter creation with SQLite manager."""
        import sys

        api_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/violentutf_api/fastapi_app"
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from app.db.sqlite_manager import get_sqlite_manager

        manager = get_sqlite_manager("test_user")
        manager.app_data_dir = str(tmp_path)
        manager.db_path = manager._get_db_path()
        manager._ensure_tables()

        # Create converter
        conv_id = manager.create_converter(
            name="test_converter", converter_type="base64", parameters={"encoding": "utf-8"}
        )

        assert conv_id is not None

        # Retrieve converter
        converter = manager.get_converter(conv_id)
        assert converter is not None
        assert converter["name"] == "test_converter"

    def test_tc_326_304_sqlite_manager_creates_scorers(self, tmp_path: Path) -> None:
        """TC-326-304: Test scorer creation with SQLite manager."""
        import sys

        api_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/violentutf_api/fastapi_app"
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from app.db.sqlite_manager import get_sqlite_manager

        manager = get_sqlite_manager("test_user")
        manager.app_data_dir = str(tmp_path)
        manager.db_path = manager._get_db_path()
        manager._ensure_tables()

        # Create scorer
        scorer_id = manager.create_scorer(
            name="test_scorer",
            scorer_type="sentiment",
            parameters={"threshold": 0.5},
        )

        assert scorer_id is not None

        # Retrieve scorer
        scorer = manager.get_scorer(scorer_id)
        assert scorer is not None
        assert scorer["name"] == "test_scorer"

    def test_tc_326_305_sqlite_manager_saves_sessions(self, tmp_path: Path) -> None:
        """TC-326-305: Test session save and retrieval with SQLite manager."""
        import sys

        api_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/violentutf_api/fastapi_app"
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from app.db.sqlite_manager import get_sqlite_manager

        manager = get_sqlite_manager("test_user")
        manager.app_data_dir = str(tmp_path)
        manager.db_path = manager._get_db_path()
        manager._ensure_tables()

        # Save session
        session_data = {"key1": "value1", "key2": "value2"}
        result = manager.save_session("test_session", session_data)
        assert result is True

        # Retrieve session
        session = manager.get_session("test_session")
        assert session is not None
        assert session["data"]["key1"] == "value1"
        assert session["data"]["key2"] == "value2"
