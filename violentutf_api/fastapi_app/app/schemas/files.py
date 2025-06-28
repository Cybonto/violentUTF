"""
File management schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FileInfo(BaseModel):
    """File information"""

    file_id: str
    filename: str
    original_filename: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime
    uploaded_by: str
    file_path: str = ""  # Don't expose in API responses


class FileUploadResponse(BaseModel):
    """Response from file upload"""

    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime
    message: str
    success: bool


class FileMetadataResponse(BaseModel):
    """File metadata response"""

    file_info: FileInfo
    download_url: str
    available: bool


class FileListResponse(BaseModel):
    """List of files response"""

    files: List[FileInfo]
    total_count: int
    limit: int
    offset: int
