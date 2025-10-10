#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Command-line interface for file splitter/merger utility."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from app.core.file_splitter import FileMerger, get_splitter
from app.utils.file_utils import (
    check_disk_space,
    clean_split_files,
    estimate_split_parts,
    format_file_size,
    is_format_supported,
    validate_file_integrity,
)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def split_file(
    file_path: str,
    chunk_size: Optional[int] = None,
    output_dir: Optional[str] = None,
    verify: bool = False,
    verbose: bool = False,
) -> int:
    """
    Split a file into chunks.

    Args:
        file_path: Path to the file to split
        chunk_size: Size of each chunk in bytes (optional)
        output_dir: Output directory (optional)
        verify: Whether to verify integrity after split
        verbose: Enable verbose output

    Returns:
        0 for success, non-zero for failure
    """
    file_path_obj = Path(file_path).resolve()

    if not file_path_obj.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    if not is_format_supported(str(file_path_obj)):
        print(f"Error: Unsupported file format: {file_path_obj.suffix}")
        print("Supported formats: .csv, .tsv, .json, .jsonl")
        return 1

    # Default chunk size: 10MB
    if chunk_size is None:
        chunk_size = 10 * 1024 * 1024

    # Check disk space
    file_size = file_path_obj.stat().st_size
    if not check_disk_space(str(file_path_obj.parent), file_size * 2):
        print("Error: Insufficient disk space for split operation")
        return 1

    try:
        if verbose:
            print(f"Splitting file: {file_path_obj}")
            print(f"File size: {format_file_size(file_size)}")
            print(f"Chunk size: {format_file_size(chunk_size)}")
            print(f"Estimated parts: {estimate_split_parts(str(file_path_obj), chunk_size)}")

        # Get appropriate splitter
        splitter = get_splitter(str(file_path_obj), chunk_size)

        # Perform split
        manifest = splitter.split()

        if verbose:
            print(f"Successfully split into {manifest['total_parts']} parts")
            print(f"Manifest saved to: {file_path_obj.stem}.manifest.json")

        # Verify if requested
        if verify:
            if verbose:
                print("Verifying split files...")

            merger = FileMerger(str(file_path_obj.parent / f"{file_path_obj.stem}.manifest.json"))
            if merger.verify_integrity():
                if verbose:
                    print("Integrity verification passed")
            else:
                print("Warning: Integrity verification failed")
                return 1

        return 0

    except Exception as e:
        print(f"Error during split: {e}")
        return 1


def merge_files(
    manifest_path: str, output_path: Optional[str] = None, verify: bool = False, verbose: bool = False
) -> int:
    """
    Merge split files back into original.

    Args:
        manifest_path: Path to the manifest file
        output_path: Output file path (optional)
        verify: Whether to verify integrity before merge
        verbose: Enable verbose output

    Returns:
        0 for success, non-zero for failure
    """
    manifest_path_obj = Path(manifest_path).resolve()

    if not manifest_path_obj.exists():
        print(f"Error: Manifest file not found: {manifest_path}")
        return 1

    try:
        merger = FileMerger(str(manifest_path))

        # Load manifest for info
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        if verbose:
            print(f"Merging {manifest['total_parts']} parts")
            print(f"Original file: {manifest['original_file']}")
            print(f"Total size: {format_file_size(manifest['total_size'])}")

        # Verify integrity if requested
        if verify:
            if verbose:
                print("Verifying part integrity...")

            if not merger.verify_integrity():
                print("Error: Integrity verification failed")
                return 1

            if verbose:
                print("Integrity verification passed")

        # Perform merge
        merged_path = merger.merge(output_path)

        if verbose:
            print(f"Successfully merged to: {merged_path}")

        # Verify merged file
        if verify and "checksum" in manifest:
            if verbose:
                print("Verifying merged file...")

            if validate_file_integrity(merged_path, manifest["checksum"]):
                if verbose:
                    print("Merged file integrity verified")
            else:
                print("Warning: Merged file checksum does not match original")

        return 0

    except Exception as e:
        print(f"Error during merge: {e}")
        return 1


def verify_files(manifest_path: str, verbose: bool = False) -> int:
    """
    Verify integrity of split files.

    Args:
        manifest_path: Path to the manifest file
        verbose: Enable verbose output

    Returns:
        0 for success, non-zero for failure
    """
    manifest_path_obj = Path(manifest_path).resolve()

    if not manifest_path_obj.exists():
        print(f"Error: Manifest file not found: {manifest_path}")
        return 1

    try:
        merger = FileMerger(str(manifest_path))

        if verbose:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            print(f"Verifying {manifest['total_parts']} parts")

        if merger.verify_integrity():
            print("All parts verified successfully")
            return 0
        else:
            print("Verification failed - one or more parts are missing or corrupted")
            return 1

    except Exception as e:
        print(f"Error during verification: {e}")
        return 1


def clean_files(directory: str, base_name: str, verbose: bool = False) -> int:
    """
    Clean up split files and manifest.

    Args:
        directory: Directory containing split files
        base_name: Base name of the split files
        verbose: Enable verbose output

    Returns:
        0 for success, non-zero for failure
    """
    try:
        deleted_count = clean_split_files(directory, base_name)

        if verbose:
            print(f"Deleted {deleted_count} files")

        return 0

    except Exception as e:
        print(f"Error during cleanup: {e}")
        return 1


def main() -> int:
    """Run the main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="File Splitter/Merger Utility - Split large files into GitHub-compatible chunks"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Split command
    split_parser = subparsers.add_parser("split", help="Split a file into chunks")
    split_parser.add_argument("file", help="File to split")
    split_parser.add_argument(
        "-s", "--size", type=int, help="Chunk size in bytes (default: 10MB)", default=10 * 1024 * 1024
    )
    split_parser.add_argument("-o", "--output", help="Output directory")
    split_parser.add_argument("-v", "--verify", action="store_true", help="Verify integrity after split")
    split_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge split files back into original")
    merge_parser.add_argument("manifest", help="Manifest file path")
    merge_parser.add_argument("-o", "--output", help="Output file path")
    merge_parser.add_argument("-v", "--verify", action="store_true", help="Verify integrity before merge")
    merge_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify integrity of split files")
    verify_parser.add_argument("manifest", help="Manifest file path")
    verify_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean up split files")
    clean_parser.add_argument("directory", help="Directory containing split files")
    clean_parser.add_argument("basename", help="Base name of split files")
    clean_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.command == "split":
        return split_file(args.file, args.size, args.output, args.verify, args.verbose)
    elif args.command == "merge":
        return merge_files(args.manifest, args.output, args.verify, args.verbose)
    elif args.command == "verify":
        return verify_files(args.manifest, args.verbose)
    elif args.command == "clean":
        return clean_files(args.directory, args.basename, args.verbose)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
