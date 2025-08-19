"""
Storage Service for ViolentUTF Report Files

This module provides file storage capabilities for report generation,
supporting local file storage with future extensibility for cloud storage.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

import aiofiles

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage operations"""

    def __init__(self, base_path: str = "/app/app_data/violentutf/reports"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized storage service with base path: {self.base_path}")

    def _get_file_path(self, file_key: str) -> Path:
        """Get the full file path from a storage key"""
        # Ensure file_key doesn't contain path traversal attempts
        safe_key = str(Path(file_key)).replace("../", "").replace("..\\", "")
        return self.base_path / safe_key

    def file_exists(self, file_key: str) -> bool:
        """Check if a file exists in storage"""
        try:
            file_path = self._get_file_path(file_key)
            return file_path.exists() and file_path.is_file()
        except Exception as e:
            logger.error(f"Error checking file existence for {file_key}: {str(e)}")
            return False

    def get_file_size(self, file_key: str) -> int:
        """Get the size of a file in bytes"""
        try:
            file_path = self._get_file_path(file_key)
            if file_path.exists():
                return file_path.stat().st_size
            return 0
        except Exception as e:
            logger.error(f"Error getting file size for {file_key}: {str(e)}")
            return 0

    async def upload_file_async(self, source_path: str, file_key: str) -> bool:
        """Upload a file to storage asynchronously"""
        try:
            source = Path(source_path)
            if not source.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False

            target_path = self._get_file_path(file_key)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file asynchronously
            async with aiofiles.open(source, "rb") as src:
                async with aiofiles.open(target_path, "wb") as dst:
                    while chunk := await src.read(8192):  # 8KB chunks
                        await dst.write(chunk)

            logger.info(f"File uploaded successfully: {file_key}")
            return True

        except Exception as e:
            logger.error(f"Error uploading file {file_key}: {str(e)}")
            return False

    def upload_file(self, source_path: str, file_key: str) -> bool:
        """Upload a file to storage synchronously"""
        try:
            source = Path(source_path)
            if not source.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False

            target_path = self._get_file_path(file_key)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source, target_path)
            logger.info(f"File uploaded successfully: {file_key}")
            return True

        except Exception as e:
            logger.error(f"Error uploading file {file_key}: {str(e)}")
            return False

    async def download_file_async(self, file_key: str, target_path: str) -> Optional[str]:
        """Download a file from storage asynchronously"""
        try:
            source_path = self._get_file_path(file_key)
            if not source_path.exists():
                logger.error(f"File not found in storage: {file_key}")
                return None

            target = Path(target_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            # Copy file asynchronously
            async with aiofiles.open(source_path, "rb") as src:
                async with aiofiles.open(target, "wb") as dst:
                    while chunk := await src.read(8192):  # 8KB chunks
                        await dst.write(chunk)

            logger.info(f"File downloaded successfully: {file_key} -> {target_path}")
            return str(target)

        except Exception as e:
            logger.error(f"Error downloading file {file_key}: {str(e)}")
            return None

    def download_file(self, file_key: str, target_path: str) -> Optional[str]:
        """Download a file from storage synchronously"""
        try:
            source_path = self._get_file_path(file_key)
            if not source_path.exists():
                logger.error(f"File not found in storage: {file_key}")
                return None

            target = Path(target_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source_path, target)
            logger.info(f"File downloaded successfully: {file_key} -> {target_path}")
            return str(target)

        except Exception as e:
            logger.error(f"Error downloading file {file_key}: {str(e)}")
            return None

    def get_download_url(self, file_key: str) -> Optional[str]:
        """Get a download URL for a file (for direct access)"""
        # For local storage, return a relative path
        # In production, this might return a signed URL for cloud storage
        if self.file_exists(file_key):
            return f"/api/v1/reports/download/{file_key}"
        return None

    def delete_file(self, file_key: str) -> bool:
        """Delete a file from storage"""
        try:
            file_path = self._get_file_path(file_key)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted successfully: {file_key}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_key}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file {file_key}: {str(e)}")
            return False

    def list_files(self, prefix: str = "") -> list[str]:
        """List files with optional prefix filter"""
        try:
            files = []
            search_path = self.base_path

            if prefix:
                search_path = self.base_path / prefix.split("/")[0]

            if search_path.exists():
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        # Get relative path from base_path
                        relative_path = file_path.relative_to(self.base_path)
                        file_key = str(relative_path).replace("\\", "/")

                        if not prefix or file_key.startswith(prefix):
                            files.append(file_key)

            return sorted(files)

        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {str(e)}")
            return []

    def cleanup_expired_files(self, max_age_hours: int = 24) -> int:
        """Clean up files older than specified hours"""
        try:
            import time

            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            deleted_count = 0

            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting expired file {file_path}: {str(e)}")

            logger.info(f"Cleaned up {deleted_count} expired files")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return 0


# Global storage service instance
_storage_service = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance"""
    global _storage_service
    if _storage_service is None:
        base_path = os.getenv("STORAGE_BASE_PATH", "/app/app_data/violentutf/reports")
        _storage_service = StorageService(base_path)
    return _storage_service
