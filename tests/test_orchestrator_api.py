# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

from unittest.mock import AsyncMock, Mock, patch

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
    with patch("violentutf_api.fastapi_app.app.db.database.get_db") as mock_db:
        yield mock_db


def test_list_orchestrator_types(mock_auth):
    """Test listing orchestrator types"""
    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.get_orchestrator_types"
    ) as mock_get_types:
        mock_get_types.return_value = [
            {
                "name": "PromptSendingOrchestrator",
                "module": "pyrit.orchestrator.single_turn.prompt_sending_orchestrator",
                "category": "single_turn",
                "description": "Test orchestrator",
                "use_cases": ["basic_prompting"],
                "parameters": [],
            }
        ]

        response = client.get("/api/v1/orchestrators/types")

        assert response.status_code == 200
        types = response.json()
        assert len(types) == 1
        assert types[0]["name"] == "PromptSendingOrchestrator"


def test_get_orchestrator_type_details(mock_auth):
    """Test getting specific orchestrator type details"""
    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.get_orchestrator_types"
    ) as mock_get_types:
        mock_get_types.return_value = [
            {
                "name": "PromptSendingOrchestrator",
                "module": "pyrit.orchestrator.single_turn.prompt_sending_orchestrator",
                "category": "single_turn",
                "description": "Test orchestrator",
                "use_cases": ["basic_prompting"],
                "parameters": [],
            }
        ]

        response = client.get("/api/v1/orchestrators/types/PromptSendingOrchestrator")

        assert response.status_code == 200
        type_info = response.json()
        assert type_info["name"] == "PromptSendingOrchestrator"


def test_get_orchestrator_type_not_found(mock_auth):
    """Test getting non-existent orchestrator type"""
    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.get_orchestrator_types"
    ) as mock_get_types:
        mock_get_types.return_value = []

        response = client.get("/api/v1/orchestrators/types/NonExistentOrchestrator")

        assert response.status_code == 404


def test_create_orchestrator_configuration(mock_auth, mock_db):
    """Test creating orchestrator configuration"""
    config_data = {
        "name": "test_orchestrator",
        "orchestrator_type": "PromptSendingOrchestrator",
        "description": "Test orchestrator for API testing",
        "parameters": {
            "objective_target": {"type": "configured_generator", "generator_name": "test_generator"},
            "batch_size": 5,
            "verbose": True,
        },
        "tags": ["test"],
    }

    # Mock database operations
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session
    mock_db_session.query.return_value.filter.return_value.first.return_value = None  # No existing config

    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.create_orchestrator_instance"
    ) as mock_create:
        mock_create.return_value = "test-uuid"

        response = client.post("/api/v1/orchestrators", json=config_data)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "test_orchestrator"
        assert result["status"] == "configured"
        assert result["parameters_validated"] is True


def test_create_orchestrator_duplicate_name(mock_auth, mock_db):
    """Test creating orchestrator with duplicate name"""
    config_data = {
        "name": "existing_orchestrator",
        "orchestrator_type": "PromptSendingOrchestrator",
        "parameters": {},
        "tags": [],
    }

    # Mock existing configuration
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session
    mock_existing = Mock()
    mock_existing.name = "existing_orchestrator"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_existing

    response = client.post("/api/v1/orchestrators", json=config_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_orchestrator_configurations(mock_auth, mock_db):
    """Test listing orchestrator configurations"""
    # Mock database query
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    mock_config = Mock()
    mock_config.id = "test-uuid"
    mock_config.name = "test_orchestrator"
    mock_config.orchestrator_type = "PromptSendingOrchestrator"
    mock_config.description = "Test description"
    mock_config.status = "configured"
    mock_config.tags = ["test"]
    mock_config.created_at = "2024-01-01T00:00:00Z"
    mock_config.instance_active = True

    mock_db_session.query.return_value.all.return_value = [mock_config]

    response = client.get("/api/v1/orchestrators")

    assert response.status_code == 200
    configs = response.json()
    assert len(configs) == 1
    assert configs[0]["name"] == "test_orchestrator"


def test_get_orchestrator_configuration(mock_auth, mock_db):
    """Test getting specific orchestrator configuration"""
    # Mock database query
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    mock_config = Mock()
    mock_config.id = "test-uuid"
    mock_config.name = "test_orchestrator"
    mock_config.orchestrator_type = "PromptSendingOrchestrator"
    mock_config.description = "Test description"
    mock_config.parameters = {"test": "param"}
    mock_config.status = "configured"
    mock_config.tags = ["test"]
    mock_config.created_at = "2024-01-01T00:00:00Z"
    mock_config.updated_at = "2024-01-01T00:00:00Z"
    mock_config.instance_active = True
    mock_config.pyrit_identifier = {}

    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config

    response = client.get("/api/v1/orchestrators/test-uuid")

    assert response.status_code == 200
    config = response.json()
    assert config["name"] == "test_orchestrator"
    assert config["parameters"]["test"] == "param"


def test_get_orchestrator_configuration_not_found(mock_auth, mock_db):
    """Test getting non-existent orchestrator configuration"""
    # Mock database query
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.get("/api/v1/orchestrators/nonexistent-uuid")

    assert response.status_code == 404


def test_execute_orchestrator(mock_auth, mock_db):
    """Test executing orchestrator"""
    execution_data = {
        "execution_type": "prompt_list",
        "execution_name": "test_execution",
        "input_data": {"prompt_list": ["Test prompt"], "memory_labels": {"test": "true"}},
    }

    # Mock database operations
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    # Mock orchestrator config
    mock_config = Mock()
    mock_config.id = "test-uuid"
    mock_config.name = "test_orchestrator"
    mock_config.orchestrator_type = "PromptSendingOrchestrator"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config

    # Mock execution record
    mock_execution = Mock()
    mock_execution.id = "exec-uuid"
    mock_execution.status = "completed"
    mock_execution.execution_name = "test_execution"
    mock_execution.started_at = "2024-01-01T00:00:00Z"
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.execute_orchestrator"
    ) as mock_execute:
        mock_execute.return_value = {
            "execution_summary": {"total_prompts": 1},
            "prompt_request_responses": [],
            "scores": [],
            "memory_export": {},
        }

        response = client.post("/api/v1/orchestrators/test-uuid/execute", json=execution_data)

        assert response.status_code == 200
        result = response.json()
        assert result["orchestrator_id"] == "test-uuid"
        assert result["orchestrator_type"] == "PromptSendingOrchestrator"


def test_execute_orchestrator_not_found(mock_auth, mock_db):
    """Test executing non-existent orchestrator"""
    execution_data = {"execution_type": "prompt_list", "input_data": {"prompt_list": ["test"]}}

    # Mock database query
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/api/v1/orchestrators/nonexistent-uuid/execute", json=execution_data)

    assert response.status_code == 404


def test_get_execution_results(mock_auth, mock_db):
    """Test getting execution results"""
    # Mock database operations
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    # Mock execution record
    mock_execution = Mock()
    mock_execution.id = "exec-uuid"
    mock_execution.status = "completed"
    mock_execution.orchestrator_id = "orch-uuid"
    mock_execution.execution_summary = {"total_prompts": 1}
    mock_execution.results = {"prompt_request_responses": [], "scores": [], "memory_export": {}}

    # Mock orchestrator config
    mock_config = Mock()
    mock_config.name = "test_orchestrator"
    mock_config.orchestrator_type = "PromptSendingOrchestrator"

    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_execution, mock_config]

    response = client.get("/api/v1/orchestrators/executions/exec-uuid/results")

    assert response.status_code == 200
    results = response.json()
    assert results["orchestrator_name"] == "test_orchestrator"
    assert results["status"] == "completed"


def test_get_orchestrator_memory(mock_auth, mock_db):
    """Test getting orchestrator memory"""
    # Mock database operations
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    mock_config = Mock()
    mock_config.id = "test-uuid"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config

    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.get_orchestrator_memory"
    ) as mock_get_memory:
        mock_get_memory.return_value = [
            {"id": "1", "role": "user", "conversation_id": "conv1"},
            {"id": "2", "role": "assistant", "conversation_id": "conv1"},
        ]

        response = client.get("/api/v1/orchestrators/test-uuid/memory")

        assert response.status_code == 200
        memory = response.json()
        assert memory["total_pieces"] == 2
        assert memory["conversations"] == 1


def test_get_orchestrator_scores(mock_auth, mock_db):
    """Test getting orchestrator scores"""
    # Mock database operations
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    mock_config = Mock()
    mock_config.id = "test-uuid"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config

    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.get_orchestrator_scores"
    ) as mock_get_scores:
        mock_get_scores.return_value = [{"id": "1", "score_value": 0.8, "score_type": "test"}]

        response = client.get("/api/v1/orchestrators/test-uuid/scores")

        assert response.status_code == 200
        scores = response.json()
        assert scores["total_scores"] == 1


def test_delete_orchestrator_configuration(mock_auth, mock_db):
    """Test deleting orchestrator configuration"""
    # Mock database operations
    mock_db_session = Mock()
    mock_db.return_value = mock_db_session

    mock_config = Mock()
    mock_config.name = "test_orchestrator"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config

    with patch(
        "violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service.pyrit_orchestrator_service.dispose_orchestrator"
    ) as mock_dispose:
        response = client.delete("/api/v1/orchestrators/test-uuid")

        assert response.status_code == 200
        result = response.json()
        assert "deleted successfully" in result["message"]
        mock_dispose.assert_called_once_with("test-uuid")
