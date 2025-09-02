# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""File management schemas."""

from datetime import datetime
from typing import List

from pydantic import BaseModel


class FileInfo(BaseModel):
    """File information."""

    file_id: str
    filename: str
    original_filename: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime
    uploaded_by: str
    file_path: str = ""  # Don't expose in API responses


class FileUploadResponse(BaseModel):
    """Response from file upload."""

    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime
    message: str
    success: bool


class FileMetadataResponse(BaseModel):
    """File metadata response."""

    file_info: FileInfo
    download_url: str
    available: bool


class FileListResponse(BaseModel):
    """List of files response."""

    files: List[FileInfo]
    total_count: int
    limit: int
    offset: int
