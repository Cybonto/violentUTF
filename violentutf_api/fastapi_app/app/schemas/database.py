"""
Database management schemas
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class InitializeDatabaseRequest(BaseModel):
    """Request to initialize database"""

    force_recreate: Optional[bool] = False
    custom_salt: Optional[str] = None
    backup_existing: Optional[bool] = True


class DatabaseInitResponse(BaseModel):
    """Response from database initialization"""

    database_path: str
    database_filename: str
    initialization_status: Literal["success", "already_exists", "failed"]
    path_generation_method: str
    salt_hash_preview: str = Field(
        description="First 8 chars of salt hash for verification"
    )
    schema_version: str


class DatabaseStatusResponse(BaseModel):
    """Database status information"""

    is_initialized: bool
    database_path: str
    connection_healthy: bool
    schema_version: str
    last_accessed: Optional[datetime] = None
    file_size_mb: Optional[float] = None


class TableStats(BaseModel):
    """Statistics for a single table"""

    table_name: str
    row_count: int


class DatabaseStatsResponse(BaseModel):
    """Comprehensive database statistics"""

    tables: List[TableStats]
    total_records: int
    database_size_mb: float
    last_backup: Optional[datetime] = None
    health_status: str


class ResetDatabaseRequest(BaseModel):
    """Request to reset database"""

    confirmation: bool = Field(description="Must be True to confirm reset")
    backup_before_reset: Optional[bool] = True
    preserve_user_data: Optional[bool] = False
