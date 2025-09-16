# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Mathematical Processing Utilities for DocMath Dataset Converter (Issue #127).

Utility functions for mathematical processing including numerical type detection,
expression parsing, memory monitoring, and large file handling.

SECURITY: All functions include proper validation for defensive security research.
"""
import gc
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import psutil


def detect_numerical_type(value: Union[str, int, float]) -> str:
    """Detect the numerical type of a mathematical answer.

    Args:
        value: The value to analyze

    Returns:
        String indicating the detected type: 'int', 'float', 'expression', or 'str'
    """
    if isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif not isinstance(value, str):
        return "str"

    # String analysis
    value = value.strip()

    # Check for integer
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return "int"

    # Check for float
    try:
        float(value)
        return "float"
    except ValueError:
        pass

    # Check for mathematical expression
    if is_mathematical_expression(value):
        return "expression"

    return "str"


def is_mathematical_expression(text: str) -> bool:
    """Detect if text contains a mathematical expression.

    Args:
        text: Text to analyze

    Returns:
        True if text contains mathematical expressions
    """
    if not isinstance(text, str):
        return False

    math_patterns = [
        r"\d+\s*[+\-*/]\s*\d+",  # Basic arithmetic: 5+3, 10*2
        r"\d+\.\d+",  # Decimal numbers: 3.14
        r"\d+/\d+",  # Fractions: 3/4
        r"\d+%",  # Percentages: 25%
        r"\$\d+(\.\d+)?",  # Currency: $100, $4.50
        r"\d+e[+\-]?\d+",  # Scientific notation: 1.5e-10
        r"[a-zA-Z]\s*=\s*\d+",  # Variables: x=5
    ]

    for pattern in math_patterns:
        if re.search(pattern, text):
            return True

    return False


def parse_mathematical_expression(expression: str) -> Dict[str, Any]:
    """Parse a mathematical expression and extract components.

    Args:
        expression: Mathematical expression to parse

    Returns:
        Dictionary with parsed components
    """
    result = {
        "original": expression,
        "type": detect_numerical_type(expression),
        "components": [],
        "operators": [],
        "is_equation": "=" in expression,
    }

    # Extract operators
    operators = re.findall(r"[+\-*/=]", expression)
    result["operators"] = operators

    # Extract numeric components
    numbers = re.findall(r"\d+(?:\.\d+)?", expression)
    result["components"] = [float(n) if "." in n else int(n) for n in numbers]

    return result


def validate_mathematical_answer(answer: Union[int, float, str, bool], expected_type: str) -> Tuple[bool, str]:
    """Validate a mathematical answer against expected type.

    Args:
        answer: Answer to validate
        expected_type: Expected answer type

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if expected_type == "int":
            int(answer)
            return True, ""
        elif expected_type == "float":
            float(answer)
            return True, ""
        elif expected_type == "str":
            str(answer)
            return True, ""
        else:
            return True, ""  # Allow unknown types
    except (ValueError, TypeError) as e:
        return False, f"Invalid answer type: {str(e)}"


def extract_table_evidence(tables: List[Any]) -> List[str]:
    """Extract and format table evidence from DocMath data.

    Args:
        tables: List of table data structures

    Returns:
        List of formatted table strings
    """
    formatted_tables = []

    for i, table in enumerate(tables):
        if isinstance(table, dict):
            if "columns" in table and "rows" in table:
                # Structured table format
                formatted = f"Table {i+1}:\n"
                formatted += " | ".join(str(col) for col in table["columns"]) + "\n"
                for row in table["rows"]:
                    formatted += " | ".join(str(cell) for cell in row) + "\n"
                formatted_tables.append(formatted.strip())
            elif "data" in table:
                # Raw data format
                formatted_tables.append(f"Table {i+1}: {table['data']}")
            else:
                # Generic dict format
                formatted_tables.append(f"Table {i+1}: {str(table)}")
        else:
            # String or other format
            formatted_tables.append(f"Table {i+1}: {str(table)}")

    return formatted_tables


class MemoryMonitor:
    """Memory usage monitor for large file processing."""

    def __init__(self, max_usage_gb: float = 2.0) -> None:
        """Initialize memory monitor.

        Args:
            max_usage_gb: Maximum allowed memory usage in GB
        """
        self.max_usage_gb = max_usage_gb
        self.max_usage_bytes = max_usage_gb * 1024 * 1024 * 1024
        self.process = psutil.Process()

    def get_current_usage(self) -> int:
        """Get current memory usage in bytes.

        Returns:
            Current memory usage in bytes
        """
        return self.process.memory_info().rss

    def get_current_usage_gb(self) -> float:
        """Get current memory usage in GB.

        Returns:
            Current memory usage in GB
        """
        return self.get_current_usage() / (1024 * 1024 * 1024)

    def is_over_limit(self) -> bool:
        """Check if memory usage is over the limit.

        Returns:
            True if over memory limit
        """
        return self.get_current_usage() > self.max_usage_bytes

    def check_and_cleanup(self) -> None:
        """Check memory usage and trigger cleanup if needed."""
        if self.is_over_limit():
            gc.collect()  # Force garbage collection
            if self.is_over_limit():
                # Still over limit after cleanup
                current_gb = self.get_current_usage_gb()
                import logging

                logger = logging.getLogger(__name__)
                logger.warning("Memory usage %.2fGB exceeds limit %.2fGB", current_gb, self.max_usage_gb)

    @contextmanager
    def context(self) -> Generator[None, None, None]:
        """Context manager for memory monitoring.

        Yields:
            None
        """
        try:
            yield
        finally:
            self.check_and_cleanup()


class MathematicalJSONSplitter:
    """JSON file splitter that preserves mathematical context."""

    def __init__(self, target_size_mb: int = 20, preserve_mathematical_context: bool = True) -> None:
        """Initialize JSON splitter.

        Args:
            target_size_mb: Target size for split chunks in MB
            preserve_mathematical_context: Whether to preserve mathematical context
        """
        self.target_size = target_size_mb * 1024 * 1024  # Convert to bytes
        self.preserve_mathematical_context = preserve_mathematical_context

    def needs_splitting(self, file_path: str) -> bool:
        """Determine if file needs splitting based on size.

        Args:
            file_path: Path to file to check

        Returns:
            True if file needs splitting
        """
        if not os.path.exists(file_path):
            return False

        file_size = os.path.getsize(file_path)
        return file_size > (50 * 1024 * 1024)  # 50MB threshold

    def split_json_preserving_objects(
        self, file_path: str, target_size: Optional[int] = None, preserve_mathematical_context: Optional[bool] = None
    ) -> "SplitResult":
        """Split JSON file while preserving object boundaries.

        Args:
            file_path: Path to JSON file to split
            target_size: Target size for chunks (optional)
            preserve_mathematical_context: Whether to preserve context (optional)

        Returns:
            SplitResult with information about created chunks
        """
        if target_size is None:
            target_size = self.target_size
        if preserve_mathematical_context is None:
            preserve_mathematical_context = self.preserve_mathematical_context

        chunks = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Determine if data is list or dict
            if isinstance(data, list):
                chunks = self._split_list_data(data, file_path, target_size)
            elif isinstance(data, dict):
                chunks = self._split_dict_data(data, file_path, target_size)
            else:
                # Single object, no splitting needed
                chunks = [ChunkInfo(chunk_id=1, filename=file_path, size=os.path.getsize(file_path))]

        except (json.JSONDecodeError, IOError) as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("Error splitting JSON file %s: %s", file_path, e)
            chunks = []

        return SplitResult(original_file=file_path, chunks=chunks)

    def _split_list_data(self, data: List[Any], file_path: str, target_size: int) -> List["ChunkInfo"]:
        """Split list-based JSON data into chunks."""
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_id = 1

        base_path = Path(file_path)
        base_name = base_path.stem
        base_dir = base_path.parent

        for item in data:
            item_json = json.dumps(item, ensure_ascii=False)
            item_size = len(item_json.encode("utf-8"))

            if current_size + item_size > target_size and current_chunk:
                # Save current chunk
                chunk_filename = base_dir / f"{base_name}_chunk_{chunk_id}.json"
                with open(chunk_filename, "w", encoding="utf-8") as f:
                    json.dump(current_chunk, f, ensure_ascii=False, indent=2)

                chunks.append(ChunkInfo(chunk_id=chunk_id, filename=str(chunk_filename), size=current_size))

                # Start new chunk
                current_chunk = [item]
                current_size = item_size
                chunk_id += 1
            else:
                current_chunk.append(item)
                current_size += item_size

        # Save final chunk
        if current_chunk:
            chunk_filename = base_dir / f"{base_name}_chunk_{chunk_id}.json"
            with open(chunk_filename, "w", encoding="utf-8") as f:
                json.dump(current_chunk, f, ensure_ascii=False, indent=2)

            chunks.append(ChunkInfo(chunk_id=chunk_id, filename=str(chunk_filename), size=current_size))

        return chunks

    def _split_dict_data(self, data: Dict[str, Any], file_path: str, target_size: int) -> List["ChunkInfo"]:
        """Split dict-based JSON data into chunks."""
        # For dict data, try to split by keys if possible
        chunks = []

        # If data contains a list under a key, split that list
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 100:  # Large list
                # Split the list and create separate files
                list_chunks = self._split_list_data(value, file_path, target_size)

                # Update chunk data to include the key structure
                for chunk_info in list_chunks:
                    updated_data = {key: []}

                    # Load chunk data and wrap in original structure
                    with open(chunk_info.filename, "r", encoding="utf-8") as f:
                        chunk_data = json.load(f)

                    updated_data[key] = chunk_data

                    # Write back with structure
                    with open(chunk_info.filename, "w", encoding="utf-8") as f:
                        json.dump(updated_data, f, ensure_ascii=False, indent=2)

                chunks.extend(list_chunks)
                break

        if not chunks:
            # No splitting possible, return original file
            chunks = [ChunkInfo(chunk_id=1, filename=file_path, size=os.path.getsize(file_path))]

        return chunks


class ChunkInfo:
    """Information about a file chunk."""

    def __init__(self, chunk_id: int, filename: str, size: int) -> None:
        """Initialize chunk info.

        Args:
            chunk_id: Unique chunk identifier
            filename: Path to chunk file
            size: Size of chunk in bytes
        """
        self.chunk_id = chunk_id
        self.filename = filename
        self.size = size


class SplitResult:
    """Result of file splitting operation."""

    def __init__(self, original_file: str, chunks: List[ChunkInfo]) -> None:
        """Initialize split result.

        Args:
            original_file: Path to original file
            chunks: List of created chunks
        """
        self.original_file = original_file
        self.chunks = chunks

    def cleanup_chunks(self) -> None:
        """Clean up created chunk files."""
        for chunk in self.chunks:
            if os.path.exists(chunk.filename) and chunk.filename != self.original_file:
                try:
                    os.unlink(chunk.filename)
                except OSError as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning("Could not delete chunk file %s: %s", chunk.filename, e)


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB.

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    if not os.path.exists(file_path):
        return 0.0

    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)
