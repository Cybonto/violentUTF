# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Session management endpoints for user state persistence
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict

from app.core.auth import get_current_user
from app.db.duckdb_manager import get_duckdb_manager
from app.models.auth import User
from app.schemas.sessions import SessionSchemaResponse, SessionStateResponse, UpdateSessionRequest
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
logger = logging.getLogger(__name__)

# DuckDB storage replaces in-memory storage
# _session_storage: Dict[str, Dict[str, Any]] = {} - REMOVED


def get_session_file_path(username: str) -> str:
    """Get path to user's session file"""
    sessions_dir = os.getenv("SESSIONS_DIR", "./app_data/sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    return os.path.join(sessions_dir, f"{username}_session.json")


def load_session_data(username: str) -> Dict[str, Any]:
    """Load session data from file"""
    session_file = get_session_file_path(username)

    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return {}
        except Exception:
            pass

    # Return default session data
    return {
        "session_id": f"session_{username}_{datetime.now().isoformat()}",
        "user_id": username,
        "ui_preferences": {},
        "workflow_state": {},
        "temporary_data": {},
        "cache_data": {},
        "last_updated": datetime.now().isoformat(),
    }


def save_session_data(username: str, session_data: Dict[str, Any]) -> None:
    """Save session data to file"""
    session_file = get_session_file_path(username)
    session_data["last_updated"] = datetime.now().isoformat()

    try:
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving session data: {e}")


@router.get("", response_model=SessionStateResponse)
async def get_session_state(current_user: User = Depends(get_current_user)):
    """
    Get user's complete session state including UI preferences, workflow state, and cached data
    """
    try:
        # Get session data from DuckDB
        db_manager = get_duckdb_manager(current_user.username)
        session_result = db_manager.get_session("main_session")

        if session_result:
            session_data = session_result["data"]
            return SessionStateResponse(
                session_id=session_data.get("session_id", str(uuid.uuid4())),
                user_id=current_user.username,
                ui_preferences=session_data.get("ui_preferences", {}),
                workflow_state=session_data.get("workflow_state", {}),
                temporary_data=session_data.get("temporary_data", {}),
                cache_data=session_data.get("cache_data", {}),
                last_updated=datetime.fromisoformat(session_result["updated_at"]),
            )
        else:
            # Return default session state
            return SessionStateResponse(
                session_id=str(uuid.uuid4()),
                user_id=current_user.username,
                ui_preferences={},
                workflow_state={},
                temporary_data={},
                cache_data={},
                last_updated=datetime.utcnow(),
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error loading session state: {str(e)}"
        )


@router.put("", response_model=SessionStateResponse)
async def update_session_state(request: UpdateSessionRequest, current_user: User = Depends(get_current_user)):
    """
    Update session state (UI preferences, workflow state, temporary data)
    """
    try:
        # Get DuckDB manager and load existing session data
        db_manager = get_duckdb_manager(current_user.username)
        session_result = db_manager.get_session("main_session")

        if session_result:
            session_data = session_result["data"]
            # Ensure last_updated exists for backward compatibility
            if "last_updated" not in session_data:
                session_data["last_updated"] = datetime.utcnow().isoformat()
        else:
            # Create new session data
            session_data = {
                "session_id": str(uuid.uuid4()),
                "ui_preferences": {},
                "workflow_state": {},
                "temporary_data": {},
                "cache_data": {},
                "last_updated": datetime.utcnow().isoformat(),
            }

        # Update provided fields
        if request.ui_preferences is not None:
            session_data["ui_preferences"].update(request.ui_preferences)

        if request.workflow_state is not None:
            session_data["workflow_state"].update(request.workflow_state)

        if request.temporary_data is not None:
            session_data["temporary_data"].update(request.temporary_data)

        if request.cache_data is not None:
            session_data["cache_data"].update(request.cache_data)

        # Set last_updated timestamp
        session_data["last_updated"] = datetime.utcnow().isoformat()

        # Save updated session data to DuckDB
        db_manager.save_session("main_session", session_data)

        return SessionStateResponse(
            session_id=session_data["session_id"],
            user_id=current_user.username,
            ui_preferences=session_data["ui_preferences"],
            workflow_state=session_data["workflow_state"],
            temporary_data=session_data["temporary_data"],
            cache_data=session_data["cache_data"],
            last_updated=datetime.fromisoformat(session_data["last_updated"]),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating session state: {str(e)}"
        )


@router.post("/reset", response_model=SessionStateResponse)
async def reset_session_state(current_user: User = Depends(get_current_user)):
    """
    Reset session state to defaults, clearing all temporary data
    """
    try:
        # Create fresh session data
        session_data: Dict[str, Any] = {
            "session_id": f"session_{current_user.username}_{datetime.utcnow().isoformat()}",
            "user_id": current_user.username,
            "ui_preferences": {},
            "workflow_state": {},
            "temporary_data": {},
            "cache_data": {},
            "last_updated": datetime.utcnow().isoformat(),
        }

        # Save reset session data to DuckDB
        db_manager = get_duckdb_manager(current_user.username)
        db_manager.save_session("main_session", session_data)

        return SessionStateResponse(
            session_id=session_data["session_id"],
            user_id=current_user.username,
            ui_preferences=session_data["ui_preferences"],
            workflow_state=session_data["workflow_state"],
            temporary_data=session_data["temporary_data"],
            cache_data=session_data["cache_data"],
            last_updated=datetime.fromisoformat(session_data["last_updated"]),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error resetting session state: {str(e)}"
        )


@router.get("/schema", response_model=SessionSchemaResponse)
async def get_session_schema():
    """
    Get the complete session state schema definition for client implementation
    """
    schema = {
        "session_id": {"type": "string", "description": "Unique session identifier", "required": True},
        "user_id": {"type": "string", "description": "User identifier", "required": True},
        "ui_preferences": {
            "type": "object",
            "description": "User interface preferences and settings",
            "properties": {
                "theme": {"type": "string", "enum": ["light", "dark", "auto"]},
                "sidebar_collapsed": {"type": "boolean"},
                "default_page": {"type": "string"},
                "table_page_size": {"type": "integer", "minimum": 10, "maximum": 100},
            },
        },
        "workflow_state": {
            "type": "object",
            "description": "Current workflow and page state",
            "properties": {
                "current_step": {"type": "string"},
                "completed_steps": {"type": "array", "items": {"type": "string"}},
                "form_data": {"type": "object"},
                "selected_configs": {"type": "object"},
            },
        },
        "temporary_data": {
            "type": "object",
            "description": "Temporary data for current session",
            "properties": {
                "uploaded_files": {"type": "array"},
                "form_cache": {"type": "object"},
                "alerts": {"type": "array"},
            },
        },
        "cache_data": {
            "type": "object",
            "description": "Cached data for performance optimization",
            "properties": {
                "generator_configs": {"type": "object"},
                "dataset_summaries": {"type": "object"},
                "recent_runs": {"type": "array"},
            },
        },
    }

    return SessionSchemaResponse(schema=schema, version="1.0", last_updated=datetime.now())
