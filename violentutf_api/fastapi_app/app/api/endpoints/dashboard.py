# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Dashboard-specific endpoints for efficient data loading"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.auth import User
from app.models.orchestrator import OrchestratorConfiguration, OrchestratorExecution
from app.schemas.dashboard import DataBrowseRequest, DataBrowseResponse, ScanDataSummary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", summary="Get dashboard summary data")
async def get_dashboard_summary(
    days_back: int = Query(30, description="Number of days to look back"),
    include_test: bool = Query(True, description="Include test executions"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
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
                    OrchestratorExecution.started_at >= start_date,
                    OrchestratorExecution.started_at <= end_date,
                    OrchestratorExecution.status == "completed",
                )
            )
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
                    "name": execution.execution_name,
                    "orchestrator_name": orchestrator_name,
                    "orchestrator_type": orchestrator_type,
                    "status": execution.status,
                    "created_at": execution.started_at.isoformat(),
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

        logger.info("Dashboard summary: %s executions, %s scores", summary["total_executions"], summary["total_scores"])
        return summary

    except Exception as e:
        logger.error("Error generating dashboard summary: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard summary: {str(e)}") from e


@router.get("/scores", summary="Get paginated score results")
async def get_dashboard_scores(
    days_back: int = Query(30, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Results per page"),
    execution_id: Optional[UUID] = Query(None, description="Filter by execution ID"),
    include_test: bool = Query(True, description="Include test executions"),
    include_responses: bool = Query(False, description="Include prompt/response data"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get paginated score results for dashboard display"""
    try:
        # Calculate pagination
        offset = (page - 1) * page_size

        # Build query
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        stmt = select(OrchestratorExecution).where(
            and_(
                OrchestratorExecution.started_at >= start_date,
                OrchestratorExecution.started_at <= end_date,
                OrchestratorExecution.status == "completed",
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
                    except Exception:
                        score_metadata = {}

                # Create complete score data with all required fields
                score_data = {
                    # Execution info
                    "execution_id": str(execution.id),
                    "execution_name": execution.execution_name,
                    "orchestrator_name": "Unknown",  # Would need a join to get this
                    # Score data
                    "score_value": score.get("score_value"),
                    "score_type": score.get("score_type", "unknown"),
                    "score_category": score.get("score_category", "unknown"),
                    "score_rationale": score.get("score_rationale", ""),
                    "timestamp": score.get("timestamp", execution.started_at.isoformat()),
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
        logger.error("Error fetching dashboard scores: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch scores: {str(e)}") from e


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


@router.post("/browse", response_model=DataBrowseResponse, summary="Browse scan data for reports")
async def browse_scan_data(
    request: DataBrowseRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DataBrowseResponse:
    """Browse scan data with enhanced filtering for report generation"""
    try:
        # Build base query with LEFT JOIN to handle missing orchestrator configs
        stmt = (
            select(
                OrchestratorExecution,
                OrchestratorConfiguration.name.label("orchestrator_name"),
                OrchestratorConfiguration.orchestrator_type,
            )
            .outerjoin(OrchestratorConfiguration, OrchestratorExecution.orchestrator_id == OrchestratorConfiguration.id)
            .where(OrchestratorExecution.status == "completed")
        )

        # Apply date filters - use same logic as dashboard summary
        end_date = request.end_date or datetime.utcnow()
        start_date = request.start_date or (end_date - timedelta(days=30))

        stmt = stmt.where(
            and_(OrchestratorExecution.started_at >= start_date, OrchestratorExecution.started_at <= end_date)
        )

        # Apply orchestrator type filter
        if request.orchestrator_types:
            stmt = stmt.where(OrchestratorConfiguration.orchestrator_type.in_(request.orchestrator_types))

        # Apply execution ID filter
        if request.execution_ids:
            stmt = stmt.where(OrchestratorExecution.id.in_(request.execution_ids))

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await db.scalar(count_stmt)

        # Apply sorting
        if request.sort_by == "date":
            order_col = OrchestratorExecution.started_at
        elif request.sort_by == "model":
            # Since target_model might not be a column, sort by started_at as fallback
            order_col = OrchestratorExecution.started_at
        else:
            order_col = OrchestratorExecution.started_at

        if request.sort_order == "asc":
            stmt = stmt.order_by(order_col.asc())
        else:
            stmt = stmt.order_by(order_col.desc())

        # Apply pagination
        offset = (request.page - 1) * request.page_size
        stmt = stmt.offset(offset).limit(request.page_size)

        # Execute query
        result = await db.execute(stmt)
        rows = result.all()

        # Process results into ScanDataSummary objects
        scan_summaries = []

        for row in rows:
            execution = row.OrchestratorExecution
            orchestrator_name = row.orchestrator_name or "Unknown"
            orchestrator_type = row.orchestrator_type or "Unknown"

            # Parse results
            results = execution.results or {}
            scores = results.get("scores", [])
            execution_metadata = results.get("execution_summary", {}).get("metadata", {})

            # Check test mode
            is_test = execution_metadata.get("is_test_execution", False)
            test_mode = execution_metadata.get("test_mode", "test_execution" if is_test else "full_execution")

            # Skip test executions if not included
            if not request.include_test and (is_test or test_mode == "test_execution"):
                continue

            # Calculate severity distribution
            severity_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0, "minimal": 0}
            score_categories = set()

            for score in scores:
                # Extract score category
                category = score.get("score_category", "unknown")
                if category != "unknown":
                    score_categories.add(category)

                # Calculate severity
                score_type = score.get("score_type", "")
                score_value = score.get("score_value")

                severity = "unknown"
                if score_type == "true_false":
                    severity = "high" if score_value is False else "low"
                elif score_type == "float_scale" and isinstance(score_value, (int, float)):
                    if score_value >= 0.8:
                        severity = "critical"
                    elif score_value >= 0.6:
                        severity = "high"
                    elif score_value >= 0.4:
                        severity = "medium"
                    elif score_value >= 0.2:
                        severity = "low"
                    else:
                        severity = "minimal"

                if severity in severity_dist:
                    severity_dist[severity] += 1

            # Apply severity filter only if we have severity data
            if request.min_severity and any(severity_dist.values()):
                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "minimal": 4}
                min_order = severity_order.get(request.min_severity, 4)

                # Check if any severity meets the minimum
                has_min_severity = any(
                    severity_dist[sev] > 0 for sev, order in severity_order.items() if order <= min_order
                )

                if not has_min_severity:
                    continue

            # Apply score category filter only if categories were found
            if request.score_categories and score_categories:
                if not any(cat in score_categories for cat in request.score_categories):
                    continue

            # Skip generator filtering if no generators found in scores
            # This prevents filtering out executions that don't have generator metadata
            if request.generators and scores:
                # Extract unique generators from this execution's scores
                execution_generators = set()
                for score in scores:
                    score_metadata = score.get("score_metadata", {})
                    if isinstance(score_metadata, str):
                        try:
                            score_metadata = json.loads(score_metadata)
                        except Exception:
                            score_metadata = {}
                    generator_name = score_metadata.get("generator_name")
                    if generator_name:
                        execution_generators.add(generator_name)

                # Only filter if we found generators in the data
                if execution_generators and not any(gen in execution_generators for gen in request.generators):
                    continue

            # Extract key findings (top 3 highest severity)
            key_findings = []
            for score in sorted(scores, key=lambda s: s.get("score_value", 0), reverse=True)[:3]:
                if score.get("score_value", 0) > 0.5:  # Threshold for significance
                    key_findings.append(
                        {
                            "severity": severity_dist.get(score.get("severity", "unknown"), "unknown"),
                            "category": score.get("score_category", "unknown"),
                            "description": score.get("score_rationale", "")[:200],  # Truncate
                        }
                    )

            # Determine scanner type
            scanner_type = "pyrit"  # Default since we're querying orchestrator_executions
            if "garak" in orchestrator_name.lower():
                scanner_type = "garak"

            # Calculate duration
            duration_seconds = None
            if execution.completed_at and execution.started_at:
                duration_seconds = int((execution.completed_at - execution.started_at).total_seconds())

            # Extract primary generator from scores
            primary_generator = "Unknown"
            if scores:
                # Get generator from first score's metadata
                first_score_metadata = scores[0].get("score_metadata", {})
                if isinstance(first_score_metadata, str):
                    try:
                        first_score_metadata = json.loads(first_score_metadata)
                    except Exception:
                        first_score_metadata = {}
                primary_generator = first_score_metadata.get("generator_name", "Unknown")

            # Create summary
            summary = ScanDataSummary(
                execution_id=execution.id,
                execution_name=execution.execution_name,
                orchestrator_name=orchestrator_name,
                orchestrator_type=orchestrator_type,
                scanner_type=scanner_type,
                generator=primary_generator,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                duration_seconds=duration_seconds,
                total_tests=len(scores),
                total_scores=len(scores),
                severity_distribution=severity_dist,
                score_categories=list(score_categories),
                key_findings=key_findings,
                is_test_execution=is_test,
                tags=execution_metadata.get("tags", []),
            )

            scan_summaries.append(summary)

        # Calculate aggregate statistics
        aggregate_stats = None
        if scan_summaries:
            total_tests = sum(s.total_tests for s in scan_summaries)
            aggregate_stats = {
                "total_executions": len(scan_summaries),
                "total_tests": total_tests,
                "avg_tests_per_execution": total_tests // len(scan_summaries) if scan_summaries else 0,
                "severity_totals": {
                    "critical": sum(s.severity_distribution.get("critical", 0) for s in scan_summaries),
                    "high": sum(s.severity_distribution.get("high", 0) for s in scan_summaries),
                    "medium": sum(s.severity_distribution.get("medium", 0) for s in scan_summaries),
                    "low": sum(s.severity_distribution.get("low", 0) for s in scan_summaries),
                },
            }

        # Build response
        response = DataBrowseResponse(
            results=scan_summaries,
            total_count=total_count,
            page=request.page,
            page_size=request.page_size,
            has_more=(offset + request.page_size) < total_count,
            filters_applied={
                "start_date": request.start_date,
                "end_date": request.end_date,
                "scanner_types": request.scanner_types,
                "orchestrator_types": request.orchestrator_types,
                "generators": request.generators,
                "min_severity": request.min_severity,
                "score_categories": request.score_categories,
                "include_test": request.include_test,
            },
            aggregate_stats=aggregate_stats,
        )

        return response

    except Exception as e:
        logger.error("Error browsing scan data: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to browse scan data: {str(e)}") from e
