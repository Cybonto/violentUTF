# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Utility functions for file operations."""

import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Callable, Optional


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA-256 checksum of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal string representation of the checksum

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove or replace invalid characters
    # Keep alphanumeric, dots, dashes, and underscores
    filename = re.sub(r"[^\w\.-]", "_", filename)

    # Remove multiple consecutive underscores
    filename = re.sub(r"_+", "_", filename)

    # Remove leading/trailing underscores and dots
    filename = filename.strip("_.")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename


def check_disk_space(directory: str, required_bytes: int) -> bool:
    """
    Check if there's enough disk space in the directory.

    Args:
        directory: Directory path to check
        required_bytes: Required space in bytes

    Returns:
        True if there's enough space, False otherwise
    """
    try:
        stat = shutil.disk_usage(directory)
        return stat.free >= required_bytes
    except Exception:
        # If we can't determine disk space, assume it's available
        return True


def validate_file_integrity(file_path: str, expected_checksum: str) -> bool:
    """
    Validate file integrity by comparing checksums.

    Args:
        file_path: Path to the file to validate
        expected_checksum: Expected SHA-256 checksum

    Returns:
        True if checksums match, False otherwise
    """
    try:
        actual_checksum = calculate_checksum(file_path)
        return actual_checksum == expected_checksum
    except Exception:
        return False


def clean_split_files(directory: str, base_name: str) -> int:
    """
    Clean up split files and manifest for a given base name.

    Args:
        directory: Directory containing the split files
        base_name: Base name of the split files

    Returns:
        Number of files deleted
    """
    deleted_count = 0
    dir_path = Path(directory)

    if not dir_path.exists():
        return 0

    # Patterns to match split files and manifest
    patterns = [
        f"{base_name}.part*.csv",
        f"{base_name}.part*.tsv",
        f"{base_name}.part*.json",
        f"{base_name}.part*.jsonl",
        f"{base_name}.manifest.json",
    ]

    for pattern in patterns:
        for file_path in dir_path.glob(pattern):
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception:
                pass

    return deleted_count


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def estimate_split_parts(file_path: str, chunk_size_bytes: int) -> int:
    """
    Estimate the number of parts a file will be split into.

    Args:
        file_path: Path to the file
        chunk_size_bytes: Size of each chunk in bytes

    Returns:
        Estimated number of parts

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    parts = file_size // chunk_size_bytes
    if file_size % chunk_size_bytes > 0:
        parts += 1
    return max(1, parts)


def create_directory_if_not_exists(directory: str) -> Path:
    """
    Create a directory if it doesn't exist.

    Args:
        directory: Directory path

    Returns:
        Path object for the directory
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_supported_formats() -> list:
    """
    Get list of supported file formats for splitting.

    Returns:
        List of supported file extensions
    """
    return [".csv", ".tsv", ".json", ".jsonl"]


def is_format_supported(file_path: str) -> bool:
    """
    Check if a file format is supported for splitting.

    Args:
        file_path: Path to the file

    Returns:
        True if format is supported, False otherwise
    """
    extension = Path(file_path).suffix.lower()
    return extension in get_supported_formats()


def format_file_size(size_bytes: float) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def copy_file_with_progress(
    source: str, destination: str, callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """
    Copy a file with optional progress callback.

    Args:
        source: Source file path
        destination: Destination file path
        callback: Optional callback function(bytes_copied, total_bytes)

    Returns:
        Destination file path

    Raises:
        FileNotFoundError: If source file doesn't exist
    """
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    dest_path = Path(destination)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    total_size = source_path.stat().st_size
    bytes_copied = 0

    with open(source, "rb") as src, open(destination, "wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            dst.write(chunk)
            bytes_copied += len(chunk)

            if callback:
                callback(bytes_copied, total_size)

    return str(dest_path)
