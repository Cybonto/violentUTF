# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""File splitter/merger utility for handling large dataset files."""

import csv
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileSplitter(ABC):
    """Abstract base class for file splitting operations."""

    def __init__(self, file_path: str, chunk_size: int = 10 * 1024 * 1024) -> None:
        """
        Initialize the file splitter.

        Args:
            file_path: Path to the file to split
            chunk_size: Size of each chunk in bytes (default 10MB)

        Raises:
            FileNotFoundError: If the input file doesn't exist
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.logger = logging.getLogger(__name__)

        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.file_name = Path(file_path).stem
        self.file_extension = Path(file_path).suffix
        self.output_dir = Path(file_path).parent

    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA-256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal string representation of the checksum
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @abstractmethod
    def split(self) -> Dict[str, Any]:
        """
        Split the file into chunks.

        Returns:
            Manifest dictionary containing split information
        """

    def generate_manifest(self, parts: List[Dict[str, Any]], format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a manifest for the split operation.

        Args:
            parts: List of part information dictionaries
            format_info: Format-specific information

        Returns:
            Complete manifest dictionary
        """
        return {
            "original_file": os.path.basename(self.file_path),
            "split_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_size": os.path.getsize(self.file_path),
            "total_parts": len(parts),
            "chunk_size": self.chunk_size,
            "checksum": self.calculate_checksum(self.file_path),
            "parts": parts,
            "format_info": format_info,
        }

    def write_manifest(self, manifest: Dict[str, Any]) -> str:
        """
        Write manifest to a JSON file.

        Args:
            manifest: Manifest dictionary

        Returns:
            Path to the manifest file
        """
        manifest_path = self.output_dir / f"{self.file_name}.manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return str(manifest_path)


class CSVSplitter(FileSplitter):
    """Splitter for CSV files with header preservation."""

    def split(self) -> Dict[str, Any]:
        """
        Split CSV file into chunks, preserving headers in each chunk.

        Returns:
            Manifest dictionary containing split information
        """
        parts = []
        headers = None
        current_part = 1
        current_size = 0
        current_rows: List[List[str]] = []
        row_start = 1
        total_rows = 0

        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)

            # Read headers
            try:
                headers = next(reader)
                header_line = ",".join(headers) + "\n"
                header_size = len(header_line.encode("utf-8"))
            except StopIteration:
                # Empty file
                return self.generate_manifest([], {"file_type": "csv", "headers": []})

            for row_num, row in enumerate(reader, start=1):
                row_line = ",".join(row) + "\n"
                row_size = len(row_line.encode("utf-8"))

                # Check if adding this row would exceed chunk size
                if current_size > 0 and current_size + row_size > self.chunk_size:
                    # Write current chunk
                    part_filename = f"{self.file_name}.part{current_part:02d}.csv"
                    part_path = self.output_dir / part_filename

                    with open(part_path, "w", encoding="utf-8", newline="") as part_file:
                        writer = csv.writer(part_file)
                        writer.writerow(headers)
                        writer.writerows(current_rows)

                    parts.append(
                        {
                            "part_number": current_part,
                            "filename": part_filename,
                            "size": os.path.getsize(part_path),
                            "checksum": self.calculate_checksum(str(part_path)),
                            "row_range": {"start": row_start, "end": row_start + len(current_rows) - 1},
                        }
                    )

                    # Reset for next chunk
                    current_part += 1
                    current_rows = []
                    current_size = header_size  # Include header size
                    row_start = row_num

                current_rows.append(row)
                current_size += row_size
                total_rows = row_num

        # Write final chunk if there are remaining rows
        if current_rows:
            part_filename = f"{self.file_name}.part{current_part:02d}.csv"
            part_path = self.output_dir / part_filename

            with open(part_path, "w", encoding="utf-8", newline="") as part_file:
                writer = csv.writer(part_file)
                writer.writerow(headers)
                writer.writerows(current_rows)

            parts.append(
                {
                    "part_number": current_part,
                    "filename": part_filename,
                    "size": os.path.getsize(part_path),
                    "checksum": self.calculate_checksum(str(part_path)),
                    "row_range": {"start": row_start, "end": total_rows},
                }
            )

        manifest = self.generate_manifest(parts, {"file_type": "csv", "headers": headers, "encoding": "utf-8"})

        self.write_manifest(manifest)
        return manifest


class JSONLSplitter(FileSplitter):
    """Splitter for JSONL (JSON Lines) files."""

    def split(self) -> Dict[str, Any]:
        """
        Split JSONL file into chunks, preserving line integrity.

        Returns:
            Manifest dictionary containing split information
        """
        parts = []
        current_part = 1
        current_size = 0
        current_lines: List[str] = []
        line_start = 1
        total_lines = 0

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                # Validate JSON
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    continue

                line_with_newline = line + "\n"
                line_size = len(line_with_newline.encode("utf-8"))

                # Check if adding this line would exceed chunk size
                if current_size > 0 and current_size + line_size > self.chunk_size:
                    # Write current chunk
                    part_filename = f"{self.file_name}.part{current_part:02d}.jsonl"
                    part_path = self.output_dir / part_filename

                    with open(part_path, "w", encoding="utf-8") as part_file:
                        for json_line in current_lines:
                            part_file.write(json_line + "\n")

                    parts.append(
                        {
                            "part_number": current_part,
                            "filename": part_filename,
                            "size": os.path.getsize(part_path),
                            "checksum": self.calculate_checksum(str(part_path)),
                            "line_range": {"start": line_start, "end": line_start + len(current_lines) - 1},
                        }
                    )

                    # Reset for next chunk
                    current_part += 1
                    current_lines = []
                    current_size = 0
                    line_start = line_num

                current_lines.append(line)
                current_size += line_size
                total_lines = line_num

        # Write final chunk if there are remaining lines
        if current_lines:
            part_filename = f"{self.file_name}.part{current_part:02d}.jsonl"
            part_path = self.output_dir / part_filename

            with open(part_path, "w", encoding="utf-8") as part_file:
                for json_line in current_lines:
                    part_file.write(json_line + "\n")

            parts.append(
                {
                    "part_number": current_part,
                    "filename": part_filename,
                    "size": os.path.getsize(part_path),
                    "checksum": self.calculate_checksum(str(part_path)),
                    "line_range": {"start": line_start, "end": total_lines},
                }
            )

        manifest = self.generate_manifest(parts, {"file_type": "jsonl", "encoding": "utf-8"})

        self.write_manifest(manifest)
        return manifest


class JSONSplitter(FileSplitter):
    """Splitter for JSON files with array/object boundary preservation."""

    def split(self) -> Dict[str, Any]:
        """
        Split JSON file into chunks, preserving JSON structure.

        Returns:
            Manifest dictionary containing split information
        """
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        parts = []
        current_part = 1

        if isinstance(data, list):
            # Split array into chunks
            items_per_chunk = max(1, self.chunk_size // (len(json.dumps(data[0]).encode("utf-8")) if data else 1))

            for i in range(0, len(data), items_per_chunk):
                chunk_data = data[i : i + items_per_chunk]
                part_filename = f"{self.file_name}.part{current_part:02d}.json"
                part_path = self.output_dir / part_filename

                with open(part_path, "w", encoding="utf-8") as part_file:
                    json.dump(chunk_data, part_file, ensure_ascii=False, indent=2)

                parts.append(
                    {
                        "part_number": current_part,
                        "filename": part_filename,
                        "size": os.path.getsize(part_path),
                        "checksum": self.calculate_checksum(str(part_path)),
                        "item_range": {"start": i, "end": min(i + items_per_chunk - 1, len(data) - 1)},
                    }
                )
                current_part += 1

        else:
            # For non-array JSON, store as single part
            part_filename = f"{self.file_name}.part01.json"
            part_path = self.output_dir / part_filename

            with open(part_path, "w", encoding="utf-8") as part_file:
                json.dump(data, part_file, ensure_ascii=False, indent=2)

            parts.append(
                {
                    "part_number": 1,
                    "filename": part_filename,
                    "size": os.path.getsize(part_path),
                    "checksum": self.calculate_checksum(str(part_path)),
                }
            )

        manifest = self.generate_manifest(
            parts,
            {"file_type": "json", "structure": "array" if isinstance(data, list) else "object", "encoding": "utf-8"},
        )

        self.write_manifest(manifest)
        return manifest


class TSVSplitter(FileSplitter):
    """Splitter for TSV (Tab-Separated Values) files with header preservation."""

    def split(self) -> Dict[str, Any]:
        """
        Split TSV file into chunks, preserving headers in each chunk.

        Returns:
            Manifest dictionary containing split information
        """
        parts = []
        headers = None
        current_part = 1
        current_size = 0
        current_rows: List[List[str]] = []
        row_start = 1
        total_rows = 0

        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")

            # Read headers
            try:
                headers = next(reader)
                header_line = "\t".join(headers) + "\n"
                header_size = len(header_line.encode("utf-8"))
            except StopIteration:
                # Empty file
                return self.generate_manifest([], {"file_type": "tsv", "headers": []})

            for row_num, row in enumerate(reader, start=1):
                row_line = "\t".join(row) + "\n"
                row_size = len(row_line.encode("utf-8"))

                # Check if adding this row would exceed chunk size
                if current_size > 0 and current_size + row_size > self.chunk_size:
                    # Write current chunk
                    part_filename = f"{self.file_name}.part{current_part:02d}.tsv"
                    part_path = self.output_dir / part_filename

                    with open(part_path, "w", encoding="utf-8", newline="") as part_file:
                        writer = csv.writer(part_file, delimiter="\t")
                        writer.writerow(headers)
                        writer.writerows(current_rows)

                    parts.append(
                        {
                            "part_number": current_part,
                            "filename": part_filename,
                            "size": os.path.getsize(part_path),
                            "checksum": self.calculate_checksum(str(part_path)),
                            "row_range": {"start": row_start, "end": row_start + len(current_rows) - 1},
                        }
                    )

                    # Reset for next chunk
                    current_part += 1
                    current_rows = []
                    current_size = header_size  # Include header size
                    row_start = row_num

                current_rows.append(row)
                current_size += row_size
                total_rows = row_num

        # Write final chunk if there are remaining rows
        if current_rows:
            part_filename = f"{self.file_name}.part{current_part:02d}.tsv"
            part_path = self.output_dir / part_filename

            with open(part_path, "w", encoding="utf-8", newline="") as part_file:
                writer = csv.writer(part_file, delimiter="\t")
                writer.writerow(headers)
                writer.writerows(current_rows)

            parts.append(
                {
                    "part_number": current_part,
                    "filename": part_filename,
                    "size": os.path.getsize(part_path),
                    "checksum": self.calculate_checksum(str(part_path)),
                    "row_range": {"start": row_start, "end": total_rows},
                }
            )

        manifest = self.generate_manifest(
            parts, {"file_type": "tsv", "headers": headers, "delimiter": "\\t", "encoding": "utf-8"}
        )

        self.write_manifest(manifest)
        return manifest


class FileMerger:
    """Class for merging split files back into original."""

    def __init__(self, manifest_path: str) -> None:
        """
        Initialize the file merger.

        Args:
            manifest_path: Path to the manifest JSON file

        Raises:
            FileNotFoundError: If the manifest file doesn't exist
        """
        self.manifest_path = manifest_path

        if not Path(manifest_path).exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        self.output_dir = Path(manifest_path).parent
        self.logger = logging.getLogger(__name__)

    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA-256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal string representation of the checksum
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def verify_integrity(self) -> bool:
        """
        Verify integrity of all split parts.

        Returns:
            True if all parts are valid, False otherwise
        """
        for part in self.manifest["parts"]:
            part_path = self.output_dir / part["filename"]
            if not part_path.exists():
                self.logger.error("Missing part: %s", part["filename"])
                return False

            actual_checksum = self.calculate_checksum(str(part_path))
            if actual_checksum != part["checksum"]:
                self.logger.error("Checksum mismatch for %s", part["filename"])
                return False

        return True

    def merge(self, output_path: Optional[str] = None) -> str:
        """
        Merge split parts back into original file.

        Args:
            output_path: Path for the merged file (optional)

        Returns:
            Path to the merged file

        Raises:
            FileNotFoundError: If any part file is missing
            ValueError: If integrity check fails
        """
        if not output_path:
            output_path = str(self.output_dir / self.manifest["original_file"])

        file_type = self.manifest["format_info"]["file_type"]

        if file_type == "csv":
            self._merge_csv(output_path)
        elif file_type == "tsv":
            self._merge_tsv(output_path)
        elif file_type == "jsonl":
            self._merge_jsonl(output_path)
        elif file_type == "json":
            self._merge_json(output_path)
        else:
            self._merge_binary(output_path)

        return output_path

    def _merge_csv(self, output_path: str) -> None:
        """Merge CSV parts, removing duplicate headers."""
        headers_written = False

        with open(output_path, "w", encoding="utf-8", newline="") as outfile:
            writer = None

            for part in sorted(self.manifest["parts"], key=lambda x: x["part_number"]):
                part_path = self.output_dir / part["filename"]
                if not part_path.exists():
                    raise FileNotFoundError(f"Part file not found: {part_path}")

                with open(part_path, "r", encoding="utf-8", newline="") as infile:
                    reader = csv.reader(infile)
                    headers = next(reader, None)

                    if not headers_written and headers:
                        writer = csv.writer(outfile)
                        writer.writerow(headers)
                        headers_written = True
                    elif headers:
                        # Skip headers in subsequent parts
                        pass

                    if writer:
                        for row in reader:
                            writer.writerow(row)

    def _merge_tsv(self, output_path: str) -> None:
        """Merge TSV parts, removing duplicate headers."""
        headers_written = False

        with open(output_path, "w", encoding="utf-8", newline="") as outfile:
            writer = None

            for part in sorted(self.manifest["parts"], key=lambda x: x["part_number"]):
                part_path = self.output_dir / part["filename"]
                if not part_path.exists():
                    raise FileNotFoundError(f"Part file not found: {part_path}")

                with open(part_path, "r", encoding="utf-8", newline="") as infile:
                    reader = csv.reader(infile, delimiter="\t")
                    headers = next(reader, None)

                    if not headers_written and headers:
                        writer = csv.writer(outfile, delimiter="\t")
                        writer.writerow(headers)
                        headers_written = True
                    elif headers:
                        # Skip headers in subsequent parts
                        pass

                    if writer:
                        for row in reader:
                            writer.writerow(row)

    def _merge_jsonl(self, output_path: str) -> None:
        """Merge JSONL parts."""
        with open(output_path, "w", encoding="utf-8") as outfile:
            for part in sorted(self.manifest["parts"], key=lambda x: x["part_number"]):
                part_path = self.output_dir / part["filename"]
                if not part_path.exists():
                    raise FileNotFoundError(f"Part file not found: {part_path}")

                with open(part_path, "r", encoding="utf-8") as infile:
                    for line in infile:
                        line = line.strip()
                        if line:
                            outfile.write(line + "\n")

    def _merge_json(self, output_path: str) -> None:
        """Merge JSON parts."""
        merged_data = []

        for part in sorted(self.manifest["parts"], key=lambda x: x["part_number"]):
            part_path = self.output_dir / part["filename"]
            if not part_path.exists():
                raise FileNotFoundError(f"Part file not found: {part_path}")

            with open(part_path, "r", encoding="utf-8") as infile:
                part_data = json.load(infile)
                if isinstance(part_data, list):
                    merged_data.extend(part_data)
                else:
                    merged_data.append(part_data)

        with open(output_path, "w", encoding="utf-8") as outfile:
            json.dump(merged_data if len(merged_data) > 1 else merged_data[0], outfile, ensure_ascii=False, indent=2)

    def _merge_binary(self, output_path: str) -> None:
        """Merge binary parts."""
        with open(output_path, "wb") as outfile:
            for part in sorted(self.manifest["parts"], key=lambda x: x["part_number"]):
                part_path = self.output_dir / part["filename"]
                if not part_path.exists():
                    raise FileNotFoundError(f"Part file not found: {part_path}")

                with open(part_path, "rb") as infile:
                    outfile.write(infile.read())


def get_splitter(file_path: str, chunk_size: int = 10 * 1024 * 1024) -> FileSplitter:
    """
    Get appropriate splitter based on file extension.

    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk in bytes

    Returns:
        Appropriate FileSplitter instance

    Raises:
        ValueError: If file format is not supported
    """
    extension = Path(file_path).suffix.lower()

    if extension == ".csv":
        return CSVSplitter(file_path, chunk_size)
    elif extension == ".tsv":
        return TSVSplitter(file_path, chunk_size)
    elif extension == ".jsonl":
        return JSONLSplitter(file_path, chunk_size)
    elif extension == ".json":
        return JSONSplitter(file_path, chunk_size)
    else:
        raise ValueError(f"Unsupported file format: {extension}")
