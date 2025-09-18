"""Tests for OllaGen1 Data Splitter implementation - Issue #122."""

import csv
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.core.splitters.ollegen1_splitter import (
    OllaGen1Manifest,
    OllaGen1Merger,
    OllaGen1Splitter,
)
from violentutf_api.fastapi_app.app.schemas.split_manifest import (
    CognitiveFrameworkMetadata,
    ColumnSchema,
    OllaGen1ManifestSchema,
    PartInfo,
    PerformanceMetadata,
    ReconstructionInfo,
    ScenarioRangeInfo,
)
from violentutf_api.fastapi_app.app.utils.csv_utils import (
    OllaGen1CSVAnalyzer,
    calculate_scenario_boundaries,
    validate_ollegen1_schema,
)


class TestOllaGen1Splitter(unittest.TestCase):
    """Test OllaGen1 Data Splitter functionality."""

    def setUp(self):
        """Set up test fixtures with OllaGen1-like data."""
        self.test_dir = tempfile.mkdtemp()
        self.csv_file = Path(self.test_dir) / "ollegen1_test.csv"
        
        # Create test data mimicking OllaGen1 structure (22 columns)
        self.test_headers = [
            "ID", "P1_name", "P1_cogpath", "P1_profile", "P1_risk_score",
            "P2_name", "P2_cogpath", "P2_profile", "P2_risk_score",
            "combined_risk_score", "WCP_Question", "WCP_Answer",
            "WHO_Question", "WHO_Answer", "TeamRisk_Question", "TeamRisk_Answer",
            "TargetFactor_Question", "TargetFactor_Answer", "scenario_metadata",
            "behavioral_construct", "cognitive_assessment", "validation_flags"
        ]
        
        # Create 1000 test scenarios (scaled down from 169,999)
        self.create_test_csv_data()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_csv_data(self):
        """Create realistic OllaGen1 test data."""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.test_headers)
            
            for i in range(1, 1001):  # 1000 scenarios
                row = [
                    f"SCENARIO_{i:06d}",  # ID
                    f"Person1_{i}", f"cognitive_path_{i}", f"profile_text_{i}", f"{50 + (i % 50)}",  # P1 data
                    f"Person2_{i}", f"cognitive_path_{i}", f"profile_text_{i}", f"{60 + (i % 40)}",  # P2 data
                    f"{(50 + (i % 50) + 60 + (i % 40)) / 2}",  # combined_risk_score
                    f"WCP question for scenario {i}", f"WCP answer for scenario {i}",
                    f"WHO question for scenario {i}", f"WHO answer for scenario {i}",
                    f"TeamRisk question for scenario {i}", f"TeamRisk answer for scenario {i}",
                    f"TargetFactor question for scenario {i}", f"TargetFactor answer for scenario {i}",
                    f"metadata_{i}", f"construct_{i % 15}", f"assessment_{i}", f"valid"
                ]
                writer.writerow(row)

    def test_ollegen1_splitter_initialization(self):
        """Test OllaGen1Splitter initialization with proper configuration."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        
        self.assertIsInstance(splitter, OllaGen1Splitter)
        self.assertEqual(splitter.file_path, str(self.csv_file))
        self.assertEqual(splitter.chunk_size, 10 * 1024 * 1024)  # 10MB default
        self.assertEqual(splitter.dataset_type, "ollegen1_cognitive")
        
    def test_ollegen1_splitter_with_custom_chunk_size(self):
        """Test splitter with custom chunk size for GitHub compatibility."""
        target_chunk_size = 10 * 1024 * 1024  # 10MB for GitHub compatibility
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=target_chunk_size)
        
        self.assertEqual(splitter.chunk_size, target_chunk_size)

    def test_ollegen1_schema_validation(self):
        """Test validation of OllaGen1 CSV schema (22 columns)."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        schema_valid = splitter.validate_schema()
        
        self.assertTrue(schema_valid)
        self.assertEqual(len(splitter.headers), 22)
        self.assertEqual(splitter.headers[0], "ID")
        self.assertIn("combined_risk_score", splitter.headers)
        self.assertIn("WCP_Question", splitter.headers)

    def test_scenario_boundary_analysis(self):
        """Test scenario boundary calculation for integrity preservation."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        splitter.analyze_file_structure()
        
        self.assertEqual(splitter.total_scenarios, 1000)
        self.assertEqual(splitter.total_qa_pairs, 4000)  # 4 Q&A per scenario
        self.assertIsNotNone(splitter.scenario_boundaries)

    def test_cognitive_framework_detection(self):
        """Test detection of cognitive framework elements."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        framework_info = splitter.analyze_cognitive_framework()
        
        self.assertIn("question_types", framework_info)
        self.assertIn("behavioral_constructs", framework_info)
        self.assertEqual(len(framework_info["question_types"]), 4)
        self.assertIn("WCP", framework_info["question_types"])
        self.assertIn("WHO", framework_info["question_types"])

    def test_split_with_scenario_preservation(self):
        """Test splitting preserves scenario integrity across boundaries."""
        chunk_size = 50 * 1024  # 50KB chunks to force multiple splits
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=chunk_size)
        manifest = splitter.split()
        
        self.assertIsNotNone(manifest)
        self.assertGreater(len(manifest["parts"]), 1)  # Should create multiple parts
        
        # Verify scenario boundaries are preserved
        total_scenarios_in_parts = 0
        for part in manifest["parts"]:
            scenario_range = part["scenario_range"]
            total_scenarios_in_parts += scenario_range["end"] - scenario_range["start"] + 1
            
        self.assertEqual(total_scenarios_in_parts, 1000)

    def test_manifest_generation_ollegen1_specific(self):
        """Test manifest generation with OllaGen1-specific metadata."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        manifest = splitter.split()
        
        # Verify OllaGen1-specific fields
        self.assertEqual(manifest["dataset_type"], "ollegen1_cognitive")
        self.assertEqual(manifest["total_scenarios"], 1000)
        self.assertEqual(manifest["total_qa_pairs"], 4000)
        
        # Verify cognitive framework information
        self.assertIn("cognitive_framework", manifest)
        cognitive_info = manifest["cognitive_framework"]
        self.assertIn("question_types", cognitive_info)
        self.assertIn("behavioral_constructs", cognitive_info)
        
        # Verify schema preservation
        self.assertIn("schema", manifest)
        self.assertEqual(len(manifest["schema"]["columns"]), 22)

    def test_data_type_preservation(self):
        """Test preservation of data types across splits."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        manifest = splitter.split()
        
        # Check data type validation
        schema_types = manifest["schema"]["column_types"]
        self.assertEqual(schema_types["ID"], "string")
        self.assertEqual(schema_types["combined_risk_score"], "float")
        self.assertEqual(schema_types["P1_risk_score"], "float")

    def test_checksum_validation_per_split(self):
        """Test checksum calculation and validation for each split."""
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=50 * 1024)
        manifest = splitter.split()
        
        # Verify checksums for each part
        for part in manifest["parts"]:
            self.assertIn("checksum", part)
            self.assertTrue(part["checksum"].startswith("sha256:"))
            # Verify SHA-256 hex length (64 chars + "sha256:" prefix = 71 chars)
            self.assertEqual(len(part["checksum"]), 71)
            
            # Verify file exists and checksum is valid
            part_path = Path(self.test_dir) / part["filename"]
            self.assertTrue(part_path.exists())

    def test_progress_tracking_during_split(self):
        """Test progress tracking functionality during splitting."""
        progress_updates = []
        
        def progress_callback(current, total, message):
            progress_updates.append((current, total, message))
        
        splitter = OllaGen1Splitter(str(self.csv_file))
        splitter.set_progress_callback(progress_callback)
        manifest = splitter.split()
        
        self.assertGreater(len(progress_updates), 0)
        # Verify final progress is 100%
        final_progress = progress_updates[-1]
        self.assertEqual(final_progress[0], final_progress[1])

    def test_error_handling_invalid_csv(self):
        """Test error handling with invalid CSV structure."""
        # Create invalid CSV (wrong number of columns)
        invalid_csv = Path(self.test_dir) / "invalid.csv"
        invalid_csv.write_text("id,name\n1,test\n2,incomplete")
        
        with self.assertRaises(ValueError):
            splitter = OllaGen1Splitter(str(invalid_csv))
            splitter.validate_schema()

    def test_memory_efficient_processing(self):
        """Test memory-efficient processing of large CSV files."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        
        # Mock memory monitoring
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 500 * 1024 * 1024  # 500MB
            
            manifest = splitter.split()
            self.assertIsNotNone(manifest)

    def test_reconstruction_metadata_completeness(self):
        """Test reconstruction metadata includes all necessary information."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        manifest = splitter.split()
        
        # Verify reconstruction information
        self.assertIn("reconstruction_info", manifest)
        recon_info = manifest["reconstruction_info"]
        
        self.assertIn("merge_order", recon_info)
        self.assertIn("validation_checksums", recon_info)
        self.assertIn("total_validation_checksum", recon_info)

    def test_split_file_naming_convention(self):
        """Test split file naming follows OllaGen1 conventions."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        manifest = splitter.split()
        
        # Verify naming pattern
        for i, part in enumerate(manifest["parts"], 1):
            expected_pattern = f"ollegen1_test.part{i:02d}.csv"
            self.assertEqual(part["filename"], expected_pattern)

    def test_qa_pair_calculation_accuracy(self):
        """Test Q&A pair calculation accuracy (4 per scenario)."""
        splitter = OllaGen1Splitter(str(self.csv_file))
        manifest = splitter.split()
        
        # Verify Q&A pair calculations
        total_qa_from_parts = sum(part["qa_pairs"] for part in manifest["parts"])
        self.assertEqual(total_qa_from_parts, 4000)  # 1000 scenarios × 4 Q&A pairs

    def test_performance_benchmark_splitting(self):
        """Test splitting performance meets requirements (<5 minutes for scaled data)."""
        start_time = time.time()
        
        splitter = OllaGen1Splitter(str(self.csv_file))
        manifest = splitter.split()
        
        end_time = time.time()
        splitting_time = end_time - start_time
        
        # For 1000 scenarios (vs 169,999), expect proportionally faster time
        # Should complete in well under 1 second for test data
        self.assertLess(splitting_time, 10)  # 10 seconds max for test data
        self.assertIsNotNone(manifest)


class TestOllaGen1Merger(unittest.TestCase):
    """Test OllaGen1 file reconstruction functionality."""

    def setUp(self):
        """Set up test fixtures for merger testing."""
        self.test_dir = tempfile.mkdtemp()
        self.csv_file = Path(self.test_dir) / "ollegen1_test.csv"
        
        # Create test data with proper OllaGen1 schema (22 columns)
        self.test_headers = [
            "ID", "P1_name", "P1_cogpath", "P1_profile", "P1_risk_score",
            "P2_name", "P2_cogpath", "P2_profile", "P2_risk_score",
            "combined_risk_score", "WCP_Question", "WCP_Answer",
            "WHO_Question", "WHO_Answer", "TeamRisk_Question", "TeamRisk_Answer",
            "TargetFactor_Question", "TargetFactor_Answer", "scenario_metadata",
            "behavioral_construct", "cognitive_assessment", "validation_flags"
        ]
        
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.test_headers)
            
            for i in range(100):
                row = [
                    f"SCENARIO_{i:06d}",  # ID
                    f"Person1_{i}", f"cognitive_path_{i}", f"profile_text_{i}", f"{50 + (i % 50)}",  # P1 data
                    f"Person2_{i}", f"cognitive_path_{i}", f"profile_text_{i}", f"{60 + (i % 40)}",  # P2 data
                    f"{(50 + (i % 50) + 60 + (i % 40)) / 2}",  # combined_risk_score
                    f"WCP question for scenario {i}", f"WCP answer for scenario {i}",
                    f"WHO question for scenario {i}", f"WHO answer for scenario {i}",
                    f"TeamRisk question for scenario {i}", f"TeamRisk answer for scenario {i}",
                    f"TargetFactor question for scenario {i}", f"TargetFactor answer for scenario {i}",
                    f"metadata_{i}", f"construct_{i % 15}", f"assessment_{i}", f"valid"
                ]
                writer.writerow(row)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_merger_initialization(self):
        """Test OllaGen1Merger initialization."""
        # First create a split to have a manifest
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=1024)
        manifest = splitter.split()
        manifest_path = splitter.write_manifest(manifest)
        
        merger = OllaGen1Merger(manifest_path)
        self.assertIsInstance(merger, OllaGen1Merger)
        self.assertEqual(merger.manifest_path, manifest_path)

    def test_integrity_verification(self):
        """Test integrity verification before merging."""
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=1024)
        manifest = splitter.split()
        manifest_path = splitter.write_manifest(manifest)
        
        merger = OllaGen1Merger(manifest_path)
        integrity_valid = merger.verify_integrity()
        
        self.assertTrue(integrity_valid)

    def test_complete_reconstruction(self):
        """Test complete file reconstruction from splits."""
        original_content = self.csv_file.read_text()
        
        # Split the file
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=1024)
        manifest = splitter.split()
        manifest_path = splitter.write_manifest(manifest)
        
        # Reconstruct the file
        merger = OllaGen1Merger(manifest_path)
        reconstructed_path = merger.merge()
        
        # Verify reconstruction
        reconstructed_content = Path(reconstructed_path).read_text()
        self.assertEqual(original_content, reconstructed_content)

    def test_scenario_count_preservation(self):
        """Test scenario count is preserved during reconstruction."""
        splitter = OllaGen1Splitter(str(self.csv_file), chunk_size=1024)
        manifest = splitter.split()
        manifest_path = splitter.write_manifest(manifest)
        
        merger = OllaGen1Merger(manifest_path)
        reconstructed_path = merger.merge()
        
        # Count scenarios in reconstructed file
        with open(reconstructed_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            scenario_count = sum(1 for _ in reader)
        
        self.assertEqual(scenario_count, 100)


class TestOllaGen1CSVAnalyzer(unittest.TestCase):
    """Test CSV analysis utilities for OllaGen1 format."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.csv_file = Path(self.test_dir) / "test.csv"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_validation_valid_ollegen1(self):
        """Test schema validation with valid OllaGen1 structure."""
        headers = [
            "ID", "P1_name", "P1_cogpath", "P1_profile", "P1_risk_score",
            "P2_name", "P2_cogpath", "P2_profile", "P2_risk_score",
            "combined_risk_score", "WCP_Question", "WCP_Answer",
            "WHO_Question", "WHO_Answer", "TeamRisk_Question", "TeamRisk_Answer",
            "TargetFactor_Question", "TargetFactor_Answer", "scenario_metadata",
            "behavioral_construct", "cognitive_assessment", "validation_flags"
        ]
        
        is_valid = validate_ollegen1_schema(headers)
        self.assertTrue(is_valid)

    def test_schema_validation_invalid_ollegen1(self):
        """Test schema validation with invalid structure."""
        invalid_headers = ["id", "name", "value"]  # Wrong structure
        
        is_valid = validate_ollegen1_schema(invalid_headers)
        self.assertFalse(is_valid)

    def test_scenario_boundary_calculation(self):
        """Test calculation of scenario boundaries for splitting."""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ID", "name"])
            for i in range(100):
                writer.writerow([f"SCENARIO_{i:03d}", f"name_{i}"])
        
        boundaries = calculate_scenario_boundaries(str(self.csv_file), chunk_size=2048)
        self.assertIsInstance(boundaries, list)
        self.assertGreater(len(boundaries), 0)

    def test_data_type_inference(self):
        """Test data type inference for OllaGen1 columns."""
        # Create test CSV with different data types first
        test_data = [
            ["ID", "risk_score", "name", "count"],
            ["SCENARIO_001", "75.5", "test", "10"],
            ["SCENARIO_002", "82.1", "test2", "15"]
        ]
        
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(test_data)
        
        # Now create analyzer
        analyzer = OllaGen1CSVAnalyzer(str(self.csv_file))
        data_types = analyzer.infer_column_types()
        
        self.assertEqual(data_types["ID"], "string")
        self.assertEqual(data_types["risk_score"], "float")
        self.assertEqual(data_types["count"], "integer")


class TestOllaGen1ManifestSchema(unittest.TestCase):
    """Test OllaGen1-specific manifest schema validation."""

    def test_manifest_schema_creation(self):
        """Test creation of OllaGen1 manifest schema."""
        from datetime import datetime, timezone
        
        schema = OllaGen1ManifestSchema(
            original_file="test.csv",
            dataset_type="ollegen1_cognitive",
            split_timestamp=datetime.now(timezone.utc),
            total_size=1024000,
            total_rows=1000,
            total_scenarios=1000,
            total_qa_pairs=4000,
            total_parts=3,
            chunk_size=10485760,
            checksum="sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            schema=ColumnSchema(
                columns=["ID", "name", "value"],
                column_count=3,
                column_types={"ID": "string", "name": "string", "value": "string"},
                encoding="utf-8"
            ),
            cognitive_framework=CognitiveFrameworkMetadata(
                question_types=["WCP", "WHO", "TeamRisk", "TargetFactor"],
                behavioral_constructs=15,
                person_profiles=2
            ),
            parts=[
                PartInfo(
                    part_number=1, filename="test.part01.csv", size=1000, 
                    checksum="sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3", 
                    row_range={"start": 1, "end": 333},
                    scenario_range={"start": 1, "end": 333}, scenario_count=333, qa_pairs=1332
                ),
                PartInfo(
                    part_number=2, filename="test.part02.csv", size=1000,
                    checksum="sha256:b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9", 
                    row_range={"start": 334, "end": 666},
                    scenario_range={"start": 334, "end": 666}, scenario_count=333, qa_pairs=1332
                ),
                PartInfo(
                    part_number=3, filename="test.part03.csv", size=1000,
                    checksum="sha256:c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2", 
                    row_range={"start": 667, "end": 1000},
                    scenario_range={"start": 667, "end": 1000}, scenario_count=334, qa_pairs=1336
                )
            ],
            reconstruction_info=ReconstructionInfo(
                merge_order=[1, 2, 3],
                validation_checksums=[
                    "sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                    "sha256:b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9", 
                    "sha256:c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"
                ],
                total_validation_checksum="sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
            ),
            split_performance=PerformanceMetadata(
                file_size_mb="1.0 MB",
                memory_efficient=True
            )
        )
        
        self.assertEqual(schema.dataset_type, "ollegen1_cognitive")
        self.assertEqual(schema.total_scenarios, 1000)
        self.assertEqual(schema.total_qa_pairs, 4000)

    def test_scenario_range_validation(self):
        """Test scenario range information validation."""
        scenario_range = ScenarioRangeInfo(start=1, end=100)
        
        self.assertEqual(scenario_range.start, 1)
        self.assertEqual(scenario_range.end, 100)
        self.assertEqual(scenario_range.count(), 100)

    def test_cognitive_framework_metadata(self):
        """Test cognitive framework metadata structure."""
        framework = CognitiveFrameworkMetadata(
            question_types=["WCP", "WHO", "TeamRisk", "TargetFactor"],
            behavioral_constructs=15,
            person_profiles=2
        )
        
        self.assertEqual(len(framework.question_types), 4)
        self.assertIn("WCP", framework.question_types)
        self.assertEqual(framework.behavioral_constructs, 15)


if __name__ == "__main__":
    unittest.main()