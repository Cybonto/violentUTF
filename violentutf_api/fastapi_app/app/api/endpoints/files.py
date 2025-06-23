"""
File management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Response
from fastapi.responses import FileResponse
from typing import Optional, List
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.core.auth import get_current_user
from app.models.auth import User
from app.schemas.files import (
    FileUploadResponse, FileMetadataResponse, 
    FileListResponse, FileInfo
)

router = APIRouter()


def get_user_files_dir(username: str) -> str:
    """Get user's files directory"""
    files_dir = os.path.join(os.getenv("APP_DATA_DIR", "./app_data"), "files", username)
    os.makedirs(files_dir, exist_ok=True)
    return files_dir


def get_file_metadata(file_path: str, file_id: str, username: str) -> FileInfo:
    """Get file metadata"""
    stat = os.stat(file_path)
    return FileInfo(
        file_id=file_id,
        filename=os.path.basename(file_path),
        original_filename=os.path.basename(file_path),
        size_bytes=stat.st_size,
        content_type="application/octet-stream",  # Would be detected in real implementation
        uploaded_at=datetime.fromtimestamp(stat.st_ctime),
        uploaded_by=username,
        file_path=file_path
    )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Upload parameter files, datasets, or other configuration files
    """
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Get user's files directory
        user_files_dir = get_user_files_dir(current_user.username)
        
        # Create safe filename
        safe_filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(user_files_dir, safe_filename)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create metadata
        metadata = {
            "file_id": file_id,
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
            "description": description,
            "uploaded_at": datetime.now().isoformat(),
            "uploaded_by": current_user.username
        }
        
        # Save metadata file
        metadata_path = os.path.join(user_files_dir, f"{file_id}.metadata.json")
        import json
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size_bytes=len(content),
            content_type=file.content_type or "application/octet-stream",
            uploaded_at=datetime.now(),
            message=f"Successfully uploaded {file.filename}",
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileMetadataResponse)
async def get_file_metadata_endpoint(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get file metadata and download URL
    """
    try:
        user_files_dir = get_user_files_dir(current_user.username)
        
        # Load metadata
        metadata_path = os.path.join(user_files_dir, f"{file_id}.metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        import json
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Find actual file
        safe_filename = f"{file_id}_{metadata['original_filename']}"
        file_path = os.path.join(user_files_dir, safe_filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File data not found"
            )
        
        file_info = FileInfo(
            file_id=file_id,
            filename=metadata["original_filename"],
            original_filename=metadata["original_filename"],
            size_bytes=metadata["size_bytes"],
            content_type=metadata["content_type"],
            uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
            uploaded_by=metadata["uploaded_by"],
            file_path=file_path
        )
        
        return FileMetadataResponse(
            file_info=file_info,
            download_url=f"/api/v1/files/{file_id}/download",
            available=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file metadata: {str(e)}"
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download file by ID
    """
    try:
        user_files_dir = get_user_files_dir(current_user.username)
        
        # Load metadata
        metadata_path = os.path.join(user_files_dir, f"{file_id}.metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        import json
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Find actual file
        safe_filename = f"{file_id}_{metadata['original_filename']}"
        file_path = os.path.join(user_files_dir, safe_filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File data not found"
            )
        
        return FileResponse(
            path=file_path,
            filename=metadata["original_filename"],
            media_type=metadata["content_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )


@router.get("", response_model=FileListResponse)
async def list_files(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    List user's uploaded files
    """
    try:
        user_files_dir = get_user_files_dir(current_user.username)
        
        # Find all metadata files
        metadata_files = list(Path(user_files_dir).glob("*.metadata.json"))
        
        files = []
        for metadata_file in metadata_files:
            try:
                import json
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                
                file_info = FileInfo(
                    file_id=metadata["file_id"],
                    filename=metadata["original_filename"],
                    original_filename=metadata["original_filename"],
                    size_bytes=metadata["size_bytes"],
                    content_type=metadata["content_type"],
                    uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
                    uploaded_by=metadata["uploaded_by"],
                    file_path=""  # Don't expose full path
                )
                files.append(file_info)
            except Exception:
                continue  # Skip corrupted metadata files
        
        # Sort by upload date (newest first)
        files.sort(key=lambda x: x.uploaded_at, reverse=True)
        
        # Apply pagination
        total_files = len(files)
        paginated_files = files[offset:offset + limit]
        
        return FileListResponse(
            files=paginated_files,
            total_count=total_files,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete uploaded file
    """
    try:
        user_files_dir = get_user_files_dir(current_user.username)
        
        # Load metadata to get original filename
        metadata_path = os.path.join(user_files_dir, f"{file_id}.metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        import json
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Delete actual file
        safe_filename = f"{file_id}_{metadata['original_filename']}"
        file_path = os.path.join(user_files_dir, safe_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete metadata file
        os.remove(metadata_path)
        
        return {"message": f"File {metadata['original_filename']} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )