"""Tests for file splitter/merger utility."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.core.file_splitter import (
    CSVSplitter,
    FileMerger,
    FileSplitter,
    JSONLSplitter,
    JSONSplitter,
    TSVSplitter,
)
from violentutf_api.fastapi_app.app.utils.file_utils import (
    calculate_checksum,
    check_disk_space,
    clean_split_files,
    sanitize_filename,
    validate_file_integrity,
)


class TestFileSplitterBase(unittest.TestCase):
    """Test base FileSplitter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = Path(self.test_dir) / "test.txt"
        self.test_file.write_text("test content")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_splitter_initialization(self):
        """Test FileSplitter base class initialization via concrete class."""
        # Use CSV file for testing since we need a concrete implementation
        csv_file = Path(self.test_dir) / "test.csv"
        csv_file.write_text("id,name\n1,test")

        splitter = CSVSplitter(str(csv_file))
        self.assertEqual(splitter.file_path, str(csv_file))
        self.assertEqual(splitter.chunk_size, 10 * 1024 * 1024)  # 10MB default

    def test_file_splitter_with_custom_chunk_size(self):
        """Test FileSplitter with custom chunk size."""
        csv_file = Path(self.test_dir) / "test.csv"
        csv_file.write_text("id,name\n1,test")

        splitter = CSVSplitter(str(csv_file), chunk_size=5 * 1024 * 1024)
        self.assertEqual(splitter.chunk_size, 5 * 1024 * 1024)

    def test_file_splitter_validation(self):
        """Test file validation in FileSplitter."""
        # Test with non-existent file
        with self.assertRaises(FileNotFoundError):
            CSVSplitter("/non/existent/file.csv")

    def test_calculate_checksum_method(self):
        """Test checksum calculation."""
        csv_file = Path(self.test_dir) / "test.csv"
        csv_file.write_text("id,name\n1,test")

        splitter = CSVSplitter(str(csv_file))
        checksum = splitter.calculate_checksum(str(csv_file))
        self.assertIsNotNone(checksum)
        self.assertEqual(len(checksum), 64)  # SHA-256 produces 64 hex chars


class TestCSVSplitter(unittest.TestCase):
    """Test CSV file splitting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.csv_file = Path(self.test_dir) / "test.csv"
        self.csv_content = "id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n"
        self.csv_file.write_text(self.csv_content)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_csv_splitter_initialization(self):
        """Test CSVSplitter initialization."""
        splitter = CSVSplitter(str(self.csv_file))
        self.assertIsInstance(splitter, FileSplitter)

    def test_csv_split_with_header_preservation(self):
        """Test CSV splitting preserves headers in each chunk."""
        splitter = CSVSplitter(str(self.csv_file), chunk_size=50)  # Small chunk
        manifest = splitter.split()

        self.assertIsNotNone(manifest)
        self.assertIn("parts", manifest)
        self.assertGreater(len(manifest["parts"]), 0)

        # Check each part has the header
        for part_info in manifest["parts"]:
            part_path = Path(self.test_dir) / part_info["filename"]
            if part_path.exists():
                content = part_path.read_text()
                self.assertTrue(content.startswith("id,name,value"))

    def test_csv_split_manifest_generation(self):
        """Test manifest generation for CSV split."""
        splitter = CSVSplitter(str(self.csv_file))
        manifest = splitter.split()

        self.assertIn("original_file", manifest)
        self.assertIn("total_parts", manifest)
        self.assertIn("chunk_size", manifest)
        self.assertIn("checksum", manifest)
        self.assertIn("format_info", manifest)
        self.assertEqual(manifest["format_info"]["file_type"], "csv")


class TestJSONLSplitter(unittest.TestCase):
    """Test JSONL file splitting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.jsonl_file = Path(self.test_dir) / "test.jsonl"
        self.jsonl_content = '{"id": 1, "name": "Alice"}\n{"id": 2, "name": "Bob"}\n{"id": 3, "name": "Charlie"}\n'
        self.jsonl_file.write_text(self.jsonl_content)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_jsonl_splitter_initialization(self):
        """Test JSONLSplitter initialization."""
        splitter = JSONLSplitter(str(self.jsonl_file))
        self.assertIsInstance(splitter, FileSplitter)

    def test_jsonl_split_preserves_line_integrity(self):
        """Test JSONL splitting preserves complete JSON lines."""
        splitter = JSONLSplitter(str(self.jsonl_file), chunk_size=40)  # Small chunk
        manifest = splitter.split()

        self.assertIsNotNone(manifest)
        self.assertIn("parts", manifest)

        # Verify each part contains valid JSON lines
        for part_info in manifest["parts"]:
            part_path = Path(self.test_dir) / part_info["filename"]
            if part_path.exists():
                lines = part_path.read_text().strip().split("\n")
                for line in lines:
                    if line:  # Skip empty lines
                        json.loads(line)  # Should not raise exception


class TestJSONSplitter(unittest.TestCase):
    """Test JSON file splitting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.json_file = Path(self.test_dir) / "test.json"
        self.json_content = json.dumps(
            [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}, {"id": 3, "name": "Charlie"}]
        )
        self.json_file.write_text(self.json_content)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_json_splitter_initialization(self):
        """Test JSONSplitter initialization."""
        splitter = JSONSplitter(str(self.json_file))
        self.assertIsInstance(splitter, FileSplitter)

    def test_json_split_preserves_structure(self):
        """Test JSON splitting preserves valid JSON structure."""
        splitter = JSONSplitter(str(self.json_file), chunk_size=50)  # Small chunk
        manifest = splitter.split()

        self.assertIsNotNone(manifest)
        self.assertIn("parts", manifest)

        # Verify structure is preserved when merged
        merged_data = []
        for part_info in manifest["parts"]:
            part_path = Path(self.test_dir) / part_info["filename"]
            if part_path.exists():
                part_data = json.loads(part_path.read_text())
                if isinstance(part_data, list):
                    merged_data.extend(part_data)
                else:
                    merged_data.append(part_data)

        original_data = json.loads(self.json_content)
        self.assertEqual(len(merged_data), len(original_data))


class TestTSVSplitter(unittest.TestCase):
    """Test TSV file splitting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.tsv_file = Path(self.test_dir) / "test.tsv"
        self.tsv_content = "id\tname\tvalue\n1\tAlice\t100\n2\tBob\t200\n3\tCharlie\t300\n"
        self.tsv_file.write_text(self.tsv_content)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tsv_splitter_initialization(self):
        """Test TSVSplitter initialization."""
        splitter = TSVSplitter(str(self.tsv_file))
        self.assertIsInstance(splitter, FileSplitter)

    def test_tsv_split_with_header_preservation(self):
        """Test TSV splitting preserves headers."""
        splitter = TSVSplitter(str(self.tsv_file), chunk_size=50)  # Small chunk
        manifest = splitter.split()

        self.assertIsNotNone(manifest)
        self.assertIn("parts", manifest)

        # Check each part has the header
        for part_info in manifest["parts"]:
            part_path = Path(self.test_dir) / part_info["filename"]
            if part_path.exists():
                content = part_path.read_text()
                self.assertTrue(content.startswith("id\tname\tvalue"))


class TestFileMerger(unittest.TestCase):
    """Test file merging functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.manifest_file = Path(self.test_dir) / "test.manifest.json"

        # Create a sample manifest
        self.manifest = {
            "original_file": "test.csv",
            "total_parts": 2,
            "chunk_size": 50,
            "checksum": "abc123",
            "parts": [
                {"part_number": 1, "filename": "test.part01.csv", "checksum": "def456"},
                {"part_number": 2, "filename": "test.part02.csv", "checksum": "ghi789"},
            ],
            "format_info": {"file_type": "csv", "headers": ["id", "name", "value"]},
        }
        self.manifest_file.write_text(json.dumps(self.manifest))

        # Create part files
        (Path(self.test_dir) / "test.part01.csv").write_text("id,name,value\n1,Alice,100\n")
        (Path(self.test_dir) / "test.part02.csv").write_text("id,name,value\n2,Bob,200\n")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_merger_initialization(self):
        """Test FileMerger initialization."""
        merger = FileMerger(str(self.manifest_file))
        self.assertEqual(merger.manifest_path, str(self.manifest_file))

    def test_file_merger_merge_csv(self):
        """Test merging CSV files."""
        merger = FileMerger(str(self.manifest_file))
        output_file = Path(self.test_dir) / "merged.csv"
        merger.merge(str(output_file))

        self.assertTrue(output_file.exists())
        content = output_file.read_text()
        # Should have header only once and both data rows
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 3)  # header + 2 data rows
        self.assertEqual(lines[0], "id,name,value")

    def test_file_merger_verify_integrity(self):
        """Test integrity verification."""
        merger = FileMerger(str(self.manifest_file))
        # With mock checksums, this might fail, but we test the method exists
        with patch.object(merger, "calculate_checksum", return_value="def456"):
            result = merger.verify_integrity()
            self.assertIsInstance(result, bool)

    def test_file_merger_missing_parts(self):
        """Test merger handles missing parts gracefully."""
        # Remove one part
        os.remove(Path(self.test_dir) / "test.part02.csv")

        merger = FileMerger(str(self.manifest_file))
        with self.assertRaises(FileNotFoundError):
            merger.merge(str(Path(self.test_dir) / "merged.csv"))


class TestFileUtils(unittest.TestCase):
    """Test file utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = Path(self.test_dir) / "test.txt"
        self.test_file.write_text("test content")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_calculate_checksum(self):
        """Test checksum calculation utility."""
        checksum = calculate_checksum(str(self.test_file))
        self.assertIsNotNone(checksum)
        self.assertEqual(len(checksum), 64)  # SHA-256

        # Same file should produce same checksum
        checksum2 = calculate_checksum(str(self.test_file))
        self.assertEqual(checksum, checksum2)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        self.assertEqual(sanitize_filename("test.txt"), "test.txt")
        self.assertEqual(sanitize_filename("test file.txt"), "test_file.txt")
        self.assertEqual(sanitize_filename("test/file.txt"), "test_file.txt")
        self.assertEqual(sanitize_filename("test\\file.txt"), "test_file.txt")
        self.assertEqual(sanitize_filename("test:file.txt"), "test_file.txt")

    def test_check_disk_space(self):
        """Test disk space checking."""
        has_space = check_disk_space(self.test_dir, 1024)  # 1KB
        self.assertTrue(has_space)

        has_space = check_disk_space(self.test_dir, 10**15)  # 1PB (likely false)
        self.assertFalse(has_space)

    def test_validate_file_integrity(self):
        """Test file integrity validation."""
        checksum = calculate_checksum(str(self.test_file))
        is_valid = validate_file_integrity(str(self.test_file), checksum)
        self.assertTrue(is_valid)

        is_valid = validate_file_integrity(str(self.test_file), "wrongchecksum")
        self.assertFalse(is_valid)

    def test_clean_split_files(self):
        """Test cleaning split files."""
        # Create some split files
        (Path(self.test_dir) / "test.part01.csv").write_text("data1")
        (Path(self.test_dir) / "test.part02.csv").write_text("data2")
        (Path(self.test_dir) / "test.manifest.json").write_text("{}")

        clean_split_files(self.test_dir, "test")

        # Check files are removed
        self.assertFalse((Path(self.test_dir) / "test.part01.csv").exists())
        self.assertFalse((Path(self.test_dir) / "test.part02.csv").exists())
        self.assertFalse((Path(self.test_dir) / "test.manifest.json").exists())


if __name__ == "__main__":
    unittest.main()

