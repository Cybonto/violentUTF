# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""OllaGen1 Data Splitter for GitHub Compatibility - Issue #122."""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ...utils.file_utils import calculate_checksum, check_disk_space, format_file_size
from ..file_splitter import FileSplitter


class OllaGen1Splitter(FileSplitter):
    """
    Specialized splitter for OllaGen1-QA-full.csv with scenario integrity preservation.

    Handles cognitive behavioral assessment data with 22-column schema,
    preserves scenario relationships across splits, and generates comprehensive
    reconstruction metadata for GitHub compatibility.
    """

    # OllaGen1 expected schema (22 columns)
    EXPECTED_SCHEMA = [
        "ID",
        "P1_name",
        "P1_cogpath",
        "P1_profile",
        "P1_risk_score",
        "P2_name",
        "P2_cogpath",
        "P2_profile",
        "P2_risk_score",
        "combined_risk_score",
        "WCP_Question",
        "WCP_Answer",
        "WHO_Question",
        "WHO_Answer",
        "TeamRisk_Question",
        "TeamRisk_Answer",
        "TargetFactor_Question",
        "TargetFactor_Answer",
        "scenario_metadata",
        "behavioral_construct",
        "cognitive_assessment",
        "validation_flags",
    ]

    QUESTION_TYPES = ["WCP", "WHO", "TeamRisk", "TargetFactor"]
    QA_PAIRS_PER_SCENARIO = 4

    def __init__(self, file_path: str, chunk_size: int = 10 * 1024 * 1024) -> None:
        """
        Initialize OllaGen1 splitter.

        Args:
            file_path: Path to OllaGen1 CSV file
            chunk_size: Target size for each chunk (default 10MB for GitHub)
        """
        super().__init__(file_path, chunk_size)

        self.dataset_type = "ollegen1_cognitive"
        self.headers: List[str] = []
        self.total_scenarios = 0
        self.total_qa_pairs = 0
        self.scenario_boundaries: List[int] = []
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None

        # Validate file on initialization
        self._validate_file_structure()

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set progress tracking callback function."""
        self.progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str) -> None:
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def _validate_file_structure(self) -> None:
        """Validate the CSV file structure and read headers."""
        try:
            with open(self.file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                self.headers = next(reader, [])

            if not self.validate_schema():
                raise ValueError(
                    f"Invalid OllaGen1 schema. Expected {len(self.EXPECTED_SCHEMA)} columns, got {len(self.headers)}"
                )

        except Exception as e:
            raise ValueError(f"Failed to validate file structure: {e}") from e

    def validate_schema(self) -> bool:
        """
        Validate CSV schema matches OllaGen1 expected structure.

        Returns:
            True if schema is valid, False otherwise
        """
        if len(self.headers) != len(self.EXPECTED_SCHEMA):
            return False

        # Check if all expected columns are present (order-agnostic)
        header_set = set(self.headers)
        expected_set = set(self.EXPECTED_SCHEMA)

        return header_set == expected_set

    def analyze_file_structure(self) -> Dict[str, Any]:
        """
        Analyze file structure for scenario counting and boundary detection.

        Returns:
            Analysis results dictionary
        """
        self._report_progress(0, 100, "Analyzing file structure...")

        row_count = 0
        scenario_ids = set()

        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header

            for row_num, row in enumerate(reader, start=1):
                if len(row) >= 1:
                    scenario_ids.add(row[0])  # ID column
                row_count += 1

                # Progress reporting every 1000 rows
                if row_num % 1000 == 0:
                    progress = min(50, (row_num / row_count) * 50) if row_count > 0 else 0
                    self._report_progress(int(progress), 100, f"Processed {row_num} rows...")

        self.total_scenarios = len(scenario_ids)
        self.total_qa_pairs = self.total_scenarios * self.QA_PAIRS_PER_SCENARIO

        self._report_progress(50, 100, "File analysis complete")

        return {
            "total_rows": row_count,
            "total_scenarios": self.total_scenarios,
            "total_qa_pairs": self.total_qa_pairs,
            "unique_scenario_ids": len(scenario_ids),
        }

    def analyze_cognitive_framework(self) -> Dict[str, Any]:
        """
        Analyze cognitive framework elements in the dataset.

        Returns:
            Cognitive framework metadata
        """
        behavioral_constructs = set()

        # Sample a subset of rows for analysis
        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)

            # Find relevant column indices
            construct_idx = headers.index("behavioral_construct") if "behavioral_construct" in headers else None

            sample_count = 0
            for row in reader:
                if sample_count >= 1000:  # Sample first 1000 rows
                    break

                if construct_idx and len(row) > construct_idx:
                    behavioral_constructs.add(row[construct_idx])

                sample_count += 1

        return {
            "question_types": self.QUESTION_TYPES,
            "behavioral_constructs": len(behavioral_constructs),
            "person_profiles": 2,  # P1 and P2 profiles
            "qa_pairs_per_scenario": self.QA_PAIRS_PER_SCENARIO,
        }

    def _calculate_optimal_rows_per_chunk(self) -> int:
        """
        Calculate optimal number of rows per chunk based on file analysis.

        Returns:
            Number of rows per chunk to achieve target chunk size
        """
        file_size = os.path.getsize(self.file_path)

        # Rough estimation: file_size / total_rows gives average bytes per row
        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            total_rows = sum(1 for _ in reader)

        if total_rows == 0:
            return 1

        avg_bytes_per_row = file_size / (total_rows + 1)  # +1 for header
        target_rows = int(self.chunk_size / avg_bytes_per_row)

        return max(1, target_rows)

    def split(self) -> Dict[str, Any]:
        """
        Split OllaGen1 CSV file preserving scenario integrity.

        Returns:
            Comprehensive manifest with OllaGen1-specific metadata
        """
        # Check available disk space
        estimated_split_size = os.path.getsize(self.file_path) * 1.1  # 10% overhead
        if not check_disk_space(str(self.output_dir), int(estimated_split_size)):
            raise ValueError("Insufficient disk space for split operation")

        self._report_progress(0, 100, "Starting split operation...")

        # Analyze file structure first
        file_analysis = self.analyze_file_structure()
        cognitive_framework = self.analyze_cognitive_framework()

        parts = []
        current_part = 1
        current_size = 0
        current_rows: List[List[str]] = []
        row_start = 1
        scenario_start = 1
        current_scenario_count = 0

        target_rows_per_chunk = self._calculate_optimal_rows_per_chunk()

        self._report_progress(10, 100, "Beginning row processing...")

        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)
            header_line = ",".join(headers) + "\n"
            header_size = len(header_line.encode("utf-8"))

            total_processed = 0

            for row_num, row in enumerate(reader, start=1):
                row_line = ",".join(f'"{field}"' if "," in field else field for field in row) + "\n"
                row_size = len(row_line.encode("utf-8"))

                # Check if adding this row would exceed chunk size or target row count
                should_split = current_size > 0 and (
                    current_size + row_size > self.chunk_size or len(current_rows) >= target_rows_per_chunk
                )

                if should_split:
                    # Write current chunk
                    part_info = self._write_chunk(
                        current_part,
                        headers,
                        current_rows,
                        row_start,
                        row_start + len(current_rows) - 1,
                        scenario_start,
                        scenario_start + current_scenario_count - 1,
                        current_scenario_count,
                    )
                    parts.append(part_info)

                    # Reset for next chunk
                    current_part += 1
                    current_rows = []
                    current_size = header_size
                    row_start = row_num
                    scenario_start += current_scenario_count
                    current_scenario_count = 0

                    self._report_progress(
                        min(90, (row_num / file_analysis["total_rows"]) * 80 + 10),
                        100,
                        f"Created part {current_part - 1}, processing row {row_num}...",
                    )

                current_rows.append(row)
                current_size += row_size
                current_scenario_count += 1
                total_processed += 1

        # Write final chunk if there are remaining rows
        if current_rows:
            part_info = self._write_chunk(
                current_part,
                headers,
                current_rows,
                row_start,
                row_start + len(current_rows) - 1,
                scenario_start,
                scenario_start + current_scenario_count - 1,
                current_scenario_count,
            )
            parts.append(part_info)

        self._report_progress(95, 100, "Generating manifest...")

        # Generate comprehensive manifest
        manifest = self._generate_ollagen1_manifest(parts, file_analysis, cognitive_framework)

        # Write manifest file
        self.write_manifest(manifest)

        self._report_progress(100, 100, "Split operation completed successfully")

        return manifest

    def _write_chunk(
        self,
        part_number: int,
        headers: List[str],
        rows: List[List[str]],
        row_start: int,
        row_end: int,
        scenario_start: int,
        scenario_end: int,
        scenario_count: int,
    ) -> Dict[str, Any]:
        """
        Write a chunk file and return its metadata.

        Returns:
            Part information dictionary
        """
        part_filename = f"{self.file_name}.part{part_number:02d}.csv"
        part_path = self.output_dir / part_filename

        with open(part_path, "w", encoding="utf-8", newline="") as part_file:
            writer = csv.writer(part_file, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            writer.writerows(rows)

        return {
            "part_number": part_number,
            "filename": part_filename,
            "size": os.path.getsize(part_path),
            "checksum": f"sha256:{calculate_checksum(str(part_path))}",
            "row_range": {"start": row_start, "end": row_end},
            "scenario_range": {"start": scenario_start, "end": scenario_end},
            "scenario_count": scenario_count,
            "qa_pairs": scenario_count * self.QA_PAIRS_PER_SCENARIO,
        }

    def _generate_ollagen1_manifest(
        self, parts: List[Dict[str, Any]], file_analysis: Dict[str, Any], cognitive_framework: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate OllaGen1-specific manifest with comprehensive metadata.

        Returns:
            Complete manifest dictionary
        """
        # Infer column data types
        column_types = self._infer_column_types()

        manifest = {
            "original_file": os.path.basename(self.file_path),
            "dataset_type": self.dataset_type,
            "split_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_size": os.path.getsize(self.file_path),
            "total_rows": file_analysis["total_rows"],
            "total_scenarios": file_analysis["total_scenarios"],
            "total_qa_pairs": file_analysis["total_qa_pairs"],
            "total_parts": len(parts),
            "chunk_size": self.chunk_size,
            "checksum": f"sha256:{calculate_checksum(self.file_path)}",
            # Schema information
            "schema": {
                "columns": self.headers,
                "column_count": len(self.headers),
                "column_types": column_types,
                "encoding": "utf-8",
            },
            # Cognitive framework metadata
            "cognitive_framework": cognitive_framework,
            # Split parts information
            "parts": parts,
            # Reconstruction information
            "reconstruction_info": {
                "merge_order": [part["part_number"] for part in parts],
                "validation_checksums": [part["checksum"] for part in parts],
                "total_validation_checksum": f"sha256:{calculate_checksum(self.file_path)}",
                "reconstruction_instructions": "Merge parts in order, removing duplicate headers",
            },
            # Performance metadata
            "split_performance": {
                "file_size_mb": format_file_size(os.path.getsize(self.file_path)),
                "estimated_split_time_seconds": None,  # Will be updated by caller
                "memory_efficient": True,
            },
        }

        return manifest

    def _infer_column_types(self) -> Dict[str, str]:
        """
        Infer data types for columns based on content analysis.

        Returns:
            Dictionary mapping column names to inferred types
        """
        column_types = {}

        # Sample rows for type inference
        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)

            # Initialize type counters
            type_samples = {col: [] for col in headers}

            # Sample up to 100 rows for type inference
            sample_count = 0
            for row in reader:
                if sample_count >= 100:
                    break

                for i, value in enumerate(row):
                    if i < len(headers):
                        type_samples[headers[i]].append(value)

                sample_count += 1

        # Infer types based on samples
        for col, samples in type_samples.items():
            column_types[col] = self._infer_column_type(col, samples)

        return column_types

    def _infer_column_type(self, column_name: str, samples: List[str]) -> str:
        """
        Infer data type for a single column.

        Returns:
            Inferred type string
        """
        if not samples:
            return "string"

        # Check for numeric types
        if "risk_score" in column_name.lower() or "score" in column_name.lower():
            try:
                # Test if sample values can be converted to float
                float_samples = [float(s) for s in samples[:10] if s.strip()]
                if float_samples:  # Ensure we have valid float samples
                    return "float"
            except (ValueError, TypeError):
                pass

        # ID columns are typically strings
        if column_name.lower() in ["id", "name"] or "_name" in column_name.lower():
            return "string"

        # Default to string
        return "string"


class OllaGen1Manifest:
    """Helper class for OllaGen1 manifest operations."""

    @staticmethod
    def validate(manifest: Dict[str, Any]) -> bool:
        """
        Validate OllaGen1 manifest structure.

        Returns:
            True if manifest is valid
        """
        required_fields = [
            "original_file",
            "dataset_type",
            "total_scenarios",
            "total_qa_pairs",
            "schema",
            "cognitive_framework",
            "parts",
        ]

        return all(field in manifest for field in required_fields)

    @staticmethod
    def get_scenario_count(manifest: Dict[str, Any]) -> int:
        """Get total scenario count from manifest."""
        return manifest.get("total_scenarios", 0)

    @staticmethod
    def get_qa_pair_count(manifest: Dict[str, Any]) -> int:
        """Get total Q&A pair count from manifest."""
        return manifest.get("total_qa_pairs", 0)


class OllaGen1Merger:
    """Merger class for reconstructing OllaGen1 files from splits."""

    def __init__(self, manifest_path: str) -> None:
        """
        Initialize OllaGen1 merger.

        Args:
            manifest_path: Path to OllaGen1 manifest file
        """
        self.manifest_path = manifest_path

        if not Path(manifest_path).exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        self.output_dir = Path(manifest_path).parent

        # Validate manifest
        if not OllaGen1Manifest.validate(self.manifest):
            raise ValueError("Invalid OllaGen1 manifest structure")

    def verify_integrity(self) -> bool:
        """
        Verify integrity of all split parts before merging.

        Returns:
            True if all parts are valid and complete
        """
        for part in self.manifest["parts"]:
            part_path = self.output_dir / part["filename"]

            # Check file exists
            if not part_path.exists():
                return False

            # Verify checksum
            expected_checksum = part["checksum"].replace("sha256:", "")
            actual_checksum = calculate_checksum(str(part_path))

            if actual_checksum != expected_checksum:
                return False

            # Verify file size
            if os.path.getsize(part_path) != part["size"]:
                return False

        return True

    def merge(self, output_path: Optional[str] = None) -> str:
        """
        Merge OllaGen1 split parts back into original file.

        Args:
            output_path: Optional output path for merged file

        Returns:
            Path to the merged file
        """
        if not self.verify_integrity():
            raise ValueError("Integrity verification failed for split parts")

        if not output_path:
            output_path = str(self.output_dir / self.manifest["original_file"])

        headers_written = False
        total_scenarios = 0

        with open(output_path, "w", encoding="utf-8", newline="") as outfile:
            writer = None

            # Process parts in merge order
            merge_order = self.manifest["reconstruction_info"]["merge_order"]
            parts_by_number = {part["part_number"]: part for part in self.manifest["parts"]}

            for part_number in merge_order:
                part = parts_by_number[part_number]
                part_path = self.output_dir / part["filename"]

                with open(part_path, "r", encoding="utf-8", newline="") as infile:
                    reader = csv.reader(infile)
                    headers = next(reader, None)

                    # Write headers only once
                    if not headers_written and headers:
                        writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
                        writer.writerow(headers)
                        headers_written = True

                    # Write data rows
                    if writer:
                        scenario_count = 0
                        for row in reader:
                            writer.writerow(row)
                            scenario_count += 1

                        # Verify scenario count matches expected
                        expected_count = part["scenario_count"]
                        if scenario_count != expected_count:
                            raise ValueError(
                                f"Scenario count mismatch in part {part_number}: "
                                f"expected {expected_count}, got {scenario_count}"
                            )

                        total_scenarios += scenario_count

        # Final validation
        expected_total = self.manifest["total_scenarios"]
        if total_scenarios != expected_total:
            raise ValueError(f"Total scenario count mismatch: expected {expected_total}, got {total_scenarios}")

        # Verify final checksum if available
        final_checksum = calculate_checksum(output_path)
        expected_final = self.manifest["reconstruction_info"]["total_validation_checksum"].replace("sha256:", "")

        if final_checksum != expected_final:
            raise ValueError("Final checksum verification failed after reconstruction")

        return output_path
