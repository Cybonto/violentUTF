"""Dashboard-specific endpoints for efficient data loading"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.orchestrator import OrchestratorConfiguration, OrchestratorExecution
from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", summary="Get dashboard summary data")
async def get_dashboard_summary(
    days_back: int = Query(30, description="Number of days to look back"),
    include_test: bool = Query(True, description="Include test executions"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get aggregated dashboard data efficiently in a single query"""
    try:
        # Calculate time range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # Build base query with joins
        stmt = (
            select(
                OrchestratorExecution,
                OrchestratorConfiguration.name.label("orchestrator_name"),
                OrchestratorConfiguration.orchestrator_type,
            )
            .join(OrchestratorConfiguration, OrchestratorExecution.orchestrator_id == OrchestratorConfiguration.id)
            .where(
                and_(
                    OrchestratorExecution.created_at >= start_date,
                    OrchestratorExecution.created_at <= end_date,
                    OrchestratorExecution.status == "completed",
                )
            )
            .options(selectinload(OrchestratorExecution.orchestrator_config))
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Process results efficiently
        executions = []
        total_scores = 0

        for row in rows:
            execution = row.OrchestratorExecution
            orchestrator_name = row.orchestrator_name
            orchestrator_type = row.orchestrator_type

            # Parse results JSON if available
            results = execution.results or {}
            scores = results.get("scores", [])

            # Check if this is a test execution
            execution_metadata = results.get("execution_summary", {}).get("metadata", {})
            is_test = execution_metadata.get("is_test_execution", False)
            test_mode = execution_metadata.get("test_mode", "test_execution" if is_test else "full_execution")

            # Skip test executions if not included
            if not include_test and (is_test or test_mode == "test_execution"):
                continue

            total_scores += len(scores)

            executions.append(
                {
                    "id": str(execution.id),
                    "name": execution.name,
                    "orchestrator_name": orchestrator_name,
                    "orchestrator_type": orchestrator_type,
                    "status": execution.status,
                    "created_at": execution.created_at.isoformat(),
                    "score_count": len(scores),
                    "test_mode": test_mode,
                    "metadata": execution_metadata,
                }
            )

        # Calculate summary statistics
        summary = {
            "total_executions": len(executions),
            "total_scores": total_scores,
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days_back},
            "executions": executions,
        }

        logger.info(f"Dashboard summary: {summary['total_executions']} executions, {summary['total_scores']} scores")
        return summary

    except Exception as e:
        logger.error(f"Error generating dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard summary: {str(e)}")


@router.get("/scores", summary="Get paginated score results")
async def get_dashboard_scores(
    days_back: int = Query(30, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Results per page"),
    execution_id: Optional[UUID] = Query(None, description="Filter by execution ID"),
    include_test: bool = Query(True, description="Include test executions"),
    include_responses: bool = Query(False, description="Include prompt/response data"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get paginated score results for dashboard display"""
    try:
        # Calculate pagination
        offset = (page - 1) * page_size

        # Build query
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        stmt = (
            select(OrchestratorExecution)
            .options(joinedload(OrchestratorExecution.orchestrator_config))
            .where(
                and_(
                    OrchestratorExecution.created_at >= start_date,
                    OrchestratorExecution.created_at <= end_date,
                    OrchestratorExecution.status == "completed",
                )
            )
        )

        if execution_id:
            stmt = stmt.where(OrchestratorExecution.id == execution_id)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar()

        # Get paginated results
        stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(stmt)
        executions = result.scalars().all()

        # Extract scores
        all_scores = []
        for execution in executions:
            results = execution.results or {}
            scores = results.get("scores", [])
            execution_metadata = results.get("execution_summary", {}).get("metadata", {})

            # Check test mode
            is_test = execution_metadata.get("is_test_execution", False)
            test_mode = execution_metadata.get("test_mode", "test_execution" if is_test else "full_execution")

            # Skip test executions if not included
            if not include_test and (is_test or test_mode == "test_execution"):
                continue

            for score in scores:
                # Parse score metadata
                score_metadata = score.get("score_metadata", {})
                if isinstance(score_metadata, str):
                    try:
                        score_metadata = json.loads(score_metadata)
                    except:
                        score_metadata = {}

                # Create complete score data with all required fields
                score_data = {
                    # Execution info
                    "execution_id": str(execution.id),
                    "execution_name": execution.name,
                    "orchestrator_name": (
                        execution.orchestrator_config.name if execution.orchestrator_config else "Unknown"
                    ),
                    # Score data
                    "score_value": score.get("score_value"),
                    "score_type": score.get("score_type", "unknown"),
                    "score_category": score.get("score_category", "unknown"),
                    "score_rationale": score.get("score_rationale", ""),
                    "timestamp": score.get("timestamp", execution.created_at.isoformat()),
                    # Metadata fields
                    "scorer_type": score_metadata.get("scorer_type", "Unknown"),
                    "scorer_name": score_metadata.get("scorer_name", score.get("scorer_name", "Unknown")),
                    "generator_name": score_metadata.get("generator_name", "Unknown"),
                    "generator_type": score_metadata.get("generator_type", "Unknown"),
                    "dataset_name": score_metadata.get("dataset_name", "Unknown"),
                    "test_mode": test_mode,
                    "batch_index": score_metadata.get("batch_index", 0),
                    "total_batches": score_metadata.get("total_batches", 1),
                    # Additional fields that might be present
                    "prompt_id": score.get("prompt_id"),
                    "prompt_request_response_id": score.get("prompt_request_response_id"),
                    "text_scored": score.get("text_scored", ""),
                }

                # Calculate severity based on score type and value
                if score_data["score_type"] == "true_false":
                    # Boolean scorers - False = Fail (violation/high severity)
                    score_data["severity"] = "high" if score_data["score_value"] is False else "low"
                elif score_data["score_type"] == "float_scale":
                    # Scale scorers
                    val = score_data["score_value"]
                    if isinstance(val, (int, float)):
                        if val >= 0.8:
                            score_data["severity"] = "critical"
                        elif val >= 0.6:
                            score_data["severity"] = "high"
                        elif val >= 0.4:
                            score_data["severity"] = "medium"
                        elif val >= 0.2:
                            score_data["severity"] = "low"
                        else:
                            score_data["severity"] = "minimal"
                    else:
                        score_data["severity"] = "unknown"
                else:
                    score_data["severity"] = "unknown"

                # Add prompt/response data if requested
                if include_responses:
                    # Try to match score to prompt/response data
                    prompt_responses = results.get("prompt_request_responses", [])

                    # Find matching response by conversation_id or batch_index
                    matched_response = None
                    for resp in prompt_responses:
                        # Check by conversation_id first
                        if score_data.get("prompt_id") and resp.get("conversation_id") == score_data["prompt_id"]:
                            matched_response = resp
                            break
                        # Check by batch index
                        elif resp.get("metadata", {}).get("batch_index") == score_data["batch_index"]:
                            matched_response = resp
                            break

                    if matched_response:
                        # Extract prompt and response text
                        request_pieces = matched_response.get("request_pieces", [])
                        prompt_text = ""
                        response_text = ""

                        for piece in request_pieces:
                            if piece.get("role") == "user":
                                prompt_text = piece.get("original_value", "")
                            elif piece.get("role") == "assistant":
                                response_text = piece.get("original_value", "")

                        score_data["prompt_response"] = {
                            "prompt": prompt_text,
                            "response": response_text,
                            "conversation_id": matched_response.get("conversation_id", ""),
                            "timestamp": matched_response.get("timestamp", ""),
                        }

                        # Add response insights if available
                        score_data["response_insights"] = analyze_response_insights(response_text)
                    else:
                        score_data["prompt_response"] = None
                        score_data["response_insights"] = {}

                all_scores.append(score_data)

        return {
            "scores": all_scores,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch scores: {str(e)}")


def analyze_response_insights(response_text: str) -> Dict[str, Any]:
    """Analyze response text for insights (matching Dashboard functionality)"""
    insights = {
        "contains_code": False,
        "contains_url": False,
        "contains_instruction": False,
        "length": len(response_text),
        "prompt_type": "general",
    }

    if not response_text:
        return insights

    # Check for code patterns
    code_patterns = [
        r"```",
        r"def ",
        r"class ",
        r"import ",
        r"function",
        r"console.log",
        r"print\(",
        r"echo ",
        r"sudo ",
        r"chmod",
    ]
    for pattern in code_patterns:
        if pattern in response_text.lower():
            insights["contains_code"] = True
            break

    # Check for URLs
    if "http://" in response_text or "https://" in response_text:
        insights["contains_url"] = True

    # Check for instruction patterns
    instruction_patterns = [
        r"step \d",
        r"first,",
        r"second,",
        r"finally",
        r"to do this",
        r"follow these",
        r"instructions:",
    ]
    for pattern in instruction_patterns:
        if pattern in response_text.lower():
            insights["contains_instruction"] = True
            break

    # Detect prompt type based on content
    if any(word in response_text.lower() for word in ["sudo", "root", "admin", "privilege"]):
        insights["prompt_type"] = "privilege_escalation"
    elif any(word in response_text.lower() for word in ["hack", "exploit", "vulnerability"]):
        insights["prompt_type"] = "security_exploit"
    elif insights["contains_code"]:
        insights["prompt_type"] = "code_generation"

    return insights
