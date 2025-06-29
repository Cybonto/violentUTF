"""
Test the new /orchestrators/executions endpoint for Dashboard_2 support
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from violentutf_api.fastapi_app.main import app

client = TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication dependency"""
    with patch("violentutf_api.fastapi_app.app.core.auth.get_current_user") as mock_auth:
        mock_auth.return_value = Mock(username="test_user", email="test@example.com")
        yield mock_auth


@pytest.fixture
def mock_db():
    """Mock database session"""
    with patch("violentutf_api.fastapi_app.app.db.database.get_session") as mock_get_session:
        mock_session = Mock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        yield mock_session


def test_list_all_orchestrator_executions(mock_auth, mock_db):
    """Test the /orchestrators/executions endpoint returns all executions"""
    # Create mock execution data
    execution1_id = uuid4()
    execution2_id = uuid4()
    orchestrator1_id = uuid4()
    orchestrator2_id = uuid4()

    # Mock executions with scorer results
    mock_execution1 = Mock(
        id=execution1_id,
        orchestrator_id=orchestrator1_id,
        execution_type="prompt_list",
        execution_name="Test Execution 1",
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        created_by="test_user",
        results={
            "scores": [
                {
                    "score_value": True,
                    "score_type": "true_false",
                    "score_category": "security",
                    "score_rationale": "Detected security issue",
                }
            ],
            "prompt_request_responses": [],
        },
    )

    mock_execution2 = Mock(
        id=execution2_id,
        orchestrator_id=orchestrator2_id,
        execution_type="dataset",
        execution_name="Test Execution 2",
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        created_by="test_user",
        results={"scores": [], "prompt_request_responses": []},  # No scorer results
    )

    # Mock orchestrator configurations
    mock_orchestrator1 = Mock(
        id=orchestrator1_id, name="Security Test Orchestrator", orchestrator_type="PromptSendingOrchestrator"
    )

    mock_orchestrator2 = Mock(
        id=orchestrator2_id, name="Dataset Test Orchestrator", orchestrator_type="RedTeamingOrchestrator"
    )

    # Setup mock database queries
    mock_executions_result = Mock()
    mock_executions_result.scalars.return_value.all.return_value = [mock_execution1, mock_execution2]

    mock_orchestrators_result = Mock()
    mock_orchestrators_result.scalars.return_value.all.return_value = [mock_orchestrator1, mock_orchestrator2]

    # Mock the execute method to return different results based on query
    call_count = 0

    def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # First call is for executions
            return mock_executions_result
        else:  # Second call is for orchestrators
            return mock_orchestrators_result

    mock_db.execute = Mock(side_effect=mock_execute)

    # Make the request
    response = client.get("/api/v1/orchestrators/executions")

    # Assert response
    assert response.status_code == 200
    data = response.json()

    assert "executions" in data
    assert "total" in data
    assert data["total"] == 2

    # Check first execution (has scorer results)
    exec1 = data["executions"][0]
    assert exec1["id"] == str(execution1_id)
    assert exec1["orchestrator_id"] == str(orchestrator1_id)
    assert exec1["name"] == "Security Test Orchestrator"
    assert exec1["orchestrator_type"] == "PromptSendingOrchestrator"
    assert exec1["has_scorer_results"] == True
    assert exec1["status"] == "completed"

    # Check second execution (no scorer results)
    exec2 = data["executions"][1]
    assert exec2["id"] == str(execution2_id)
    assert exec2["orchestrator_id"] == str(orchestrator2_id)
    assert exec2["name"] == "Dataset Test Orchestrator"
    assert exec2["orchestrator_type"] == "RedTeamingOrchestrator"
    assert exec2["has_scorer_results"] == False
    assert exec2["status"] == "completed"


def test_list_all_orchestrator_executions_no_auth():
    """Test that the endpoint requires authentication"""
    response = client.get("/api/v1/orchestrators/executions")
    assert response.status_code == 401


def test_list_all_orchestrator_executions_empty(mock_auth, mock_db):
    """Test the endpoint when no executions exist"""
    # Setup mock database queries
    mock_executions_result = Mock()
    mock_executions_result.scalars.return_value.all.return_value = []

    mock_orchestrators_result = Mock()
    mock_orchestrators_result.scalars.return_value.all.return_value = []

    # Mock the execute method
    call_count = 0

    def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # First call is for executions
            return mock_executions_result
        else:  # Second call is for orchestrators
            return mock_orchestrators_result

    mock_db.execute = Mock(side_effect=mock_execute)

    # Make the request
    response = client.get("/api/v1/orchestrators/executions")

    # Assert response
    assert response.status_code == 200
    data = response.json()

    assert "executions" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["executions"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
