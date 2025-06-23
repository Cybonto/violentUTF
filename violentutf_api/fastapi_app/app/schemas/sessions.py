"""
Session management schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UpdateSessionRequest(BaseModel):
    """Request to update session state"""
    ui_preferences: Optional[Dict[str, Any]] = None
    workflow_state: Optional[Dict[str, Any]] = None
    temporary_data: Optional[Dict[str, Any]] = None
    cache_data: Optional[Dict[str, Any]] = None


class SessionStateResponse(BaseModel):
    """Session state response"""
    session_id: str
    user_id: str
    ui_preferences: Dict[str, Any]
    workflow_state: Dict[str, Any]
    temporary_data: Dict[str, Any]
    cache_data: Dict[str, Any]
    last_updated: datetime


class SessionSchemaResponse(BaseModel):
    """Session state schema definition"""
    schema: Dict[str, Any]
    version: str
    last_updated: datetime