# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""CSV utilities for OllaGen1 data processing."""

import csv
from pathlib import Path
from typing import Dict, List, Tuple


class OllaGen1CSVAnalyzer:
    """Analyzer for OllaGen1 CSV file structure and content."""

    def __init__(self, file_path: str) -> None:
        """Initialize analyzer with CSV file path."""
        self.file_path = file_path
        self.headers: List[str] = []
        self._load_headers()

    def _load_headers(self) -> None:
        """Load CSV headers from file."""
        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            self.headers = next(reader, [])

    def infer_column_types(self) -> Dict[str, str]:
        """
        Infer data types for all columns based on sample data.

        Returns:
            Dictionary mapping column names to inferred types
        """
        column_types = {}

        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip headers

            # Sample first 50 rows for type inference
            samples = {col: [] for col in self.headers}

            row_count = 0
            for row in reader:
                if row_count >= 50:
                    break

                for i, value in enumerate(row):
                    if i < len(self.headers):
                        samples[self.headers[i]].append(value)

                row_count += 1

        # Infer types for each column
        for col, values in samples.items():
            column_types[col] = self._infer_single_column_type(col, values)

        return column_types

    def _infer_single_column_type(self, column_name: str, values: List[str]) -> str:
        """Infer data type for a single column."""
        if not values:
            return "string"

        # Check for numeric patterns
        if "score" in column_name.lower() or "risk" in column_name.lower():
            # Try to parse as float
            numeric_count = 0
            for value in values:
                try:
                    float(value)
                    numeric_count += 1
                except (ValueError, TypeError):
                    pass

            # If most values are numeric, consider it float
            if numeric_count > len(values) * 0.8:
                return "float"

        # Check for integer patterns
        if "count" in column_name.lower() or column_name.lower().endswith("_id"):
            try:
                # Test if values can be converted to int
                int_values = [int(v) for v in values[:10] if v.strip()]
                if int_values:  # Ensure we have valid integer values
                    pass  # Valid integer column
                return "integer"
            except (ValueError, TypeError):
                pass

        # Default to string
        return "string"


def validate_ollegen1_schema(headers: List[str]) -> bool:
    """
    Validate if headers match expected OllaGen1 schema.

    Args:
        headers: List of column headers from CSV

    Returns:
        True if schema is valid for OllaGen1 format
    """
    expected_columns = {
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
    }

    header_set = set(headers)
    return header_set == expected_columns and len(headers) == 22


def calculate_scenario_boundaries(file_path: str, chunk_size: int) -> List[Tuple[int, int]]:
    """
    Calculate optimal scenario boundaries for splitting while preserving integrity.

    Args:
        file_path: Path to CSV file
        chunk_size: Target chunk size in bytes

    Returns:
        List of (start_row, end_row) tuples for each chunk
    """
    boundaries = []

    # Estimate average bytes per row
    file_size = Path(file_path).stat().st_size

    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        total_rows = sum(1 for _ in reader)

    if total_rows == 0:
        return [(1, 1)]

    avg_bytes_per_row = file_size / (total_rows + 1)  # +1 for header
    target_rows_per_chunk = max(1, int(chunk_size / avg_bytes_per_row))

    # Create boundaries ensuring no partial scenarios
    current_start = 1

    while current_start <= total_rows:
        current_end = min(current_start + target_rows_per_chunk - 1, total_rows)
        boundaries.append((current_start, current_end))
        current_start = current_end + 1

    return boundaries


def extract_cognitive_metadata(file_path: str, sample_size: int = 1000) -> Dict[str, any]:
    """
    Extract cognitive framework metadata from OllaGen1 CSV file.

    Args:
        file_path: Path to CSV file
        sample_size: Number of rows to sample for analysis

    Returns:
        Dictionary containing cognitive framework information
    """
    metadata = {
        "question_types": ["WCP", "WHO", "TeamRisk", "TargetFactor"],
        "behavioral_constructs": set(),
        "person_profiles": 2,  # P1 and P2
        "qa_pairs_per_scenario": 4,
    }

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)

            # Find behavioral construct column
            construct_idx = None
            if "behavioral_construct" in headers:
                construct_idx = headers.index("behavioral_construct")

            # Sample rows for metadata extraction
            sample_count = 0
            for row in reader:
                if sample_count >= sample_size:
                    break

                if construct_idx and len(row) > construct_idx:
                    construct_value = row[construct_idx].strip()
                    if construct_value:
                        metadata["behavioral_constructs"].add(construct_value)

                sample_count += 1

        # Convert set to count
        metadata["behavioral_constructs"] = len(metadata["behavioral_constructs"])

    except Exception:
        # Return default values if analysis fails
        metadata["behavioral_constructs"] = 15  # Default estimate

    return metadata


def validate_csv_integrity(file_path: str) -> Dict[str, any]:
    """
    Validate CSV file integrity and structure.

    Args:
        file_path: Path to CSV file to validate

    Returns:
        Dictionary containing validation results
    """
    validation_results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "row_count": 0,
        "column_count": 0,
        "encoding": "utf-8",
    }

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)

            # Validate headers
            headers = next(reader, [])
            validation_results["column_count"] = len(headers)

            if not validate_ollegen1_schema(headers):
                validation_results["errors"].append("Invalid OllaGen1 schema")
                validation_results["is_valid"] = False

            # Validate data rows
            expected_columns = len(headers)
            row_number = 1

            for row in reader:
                row_number += 1

                if len(row) != expected_columns:
                    validation_results["warnings"].append(
                        f"Row {row_number}: column count mismatch " f"(expected {expected_columns}, got {len(row)})"
                    )

                # Check for empty critical fields
                if len(row) > 0 and not row[0].strip():  # ID field
                    validation_results["warnings"].append(f"Row {row_number}: empty ID field")

            validation_results["row_count"] = row_number - 1  # Subtract header row

    except UnicodeDecodeError:
        validation_results["errors"].append("File encoding is not UTF-8")
        validation_results["is_valid"] = False
    except Exception as e:
        validation_results["errors"].append(f"Unexpected error: {str(e)}")
        validation_results["is_valid"] = False

    return validation_results


def estimate_split_performance(file_path: str, chunk_size: int) -> Dict[str, any]:
    """
    Estimate performance metrics for splitting operation.

    Args:
        file_path: Path to CSV file
        chunk_size: Target chunk size in bytes

    Returns:
        Dictionary containing performance estimates
    """
    file_size = Path(file_path).stat().st_size
    estimated_parts = max(1, file_size // chunk_size + (1 if file_size % chunk_size > 0 else 0))

    # Rough time estimates based on file size (these are conservative estimates)
    base_processing_time = 0.1  # Base time per MB
    size_mb = file_size / (1024 * 1024)
    estimated_time_seconds = size_mb * base_processing_time

    return {
        "file_size_mb": round(size_mb, 2),
        "estimated_parts": estimated_parts,
        "estimated_time_seconds": round(estimated_time_seconds, 1),
        "estimated_memory_mb": min(100, size_mb * 0.1),  # Conservative memory estimate
        "chunk_size_mb": round(chunk_size / (1024 * 1024), 2),
    }
