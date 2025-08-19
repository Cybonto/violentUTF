# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service import PyRITOrchestratorService


@pytest.fixture
def orchestrator_service() -> Any:
    """Create orchestrator service instance for testing."""
    return PyRITOrchestratorService()


@pytest.mark.asyncio
async def test_get_orchestrator_types(orchestrator_service) -> None:
    """Test orchestrator type discovery."""
    types = orchestrator_service.get_orchestrator_types()

    assert len(types) > 0
    assert any(t["name"] == "PromptSendingOrchestrator" for t in types)

    # Check PromptSendingOrchestrator details
    pso_type = next(t for t in types if t["name"] == "PromptSendingOrchestrator")
    assert pso_type["category"] == "single_turn"
    assert "basic_prompting" in pso_type["use_cases"]
    assert any(p["name"] == "objective_target" for p in pso_type["parameters"])


@pytest.mark.asyncio
async def test_create_orchestrator_instance(orchestrator_service) -> None:
    """Test orchestrator instance creation."""
    config = {
        "orchestrator_type": "PromptSendingOrchestrator",
        "parameters": {
            "objective_target": {"type": "configured_generator", "generator_name": "test_generator"},
            "batch_size": 5,
            "verbose": True,
        },
    }

    with patch.object(orchestrator_service, "_create_generator_target") as mock_target:
        mock_target.return_value = Mock()

        orchestrator_id = await orchestrator_service.create_orchestrator_instance(config)

        assert orchestrator_id is not None
        assert orchestrator_id in orchestrator_service._orchestrator_instances


@pytest.mark.asyncio
async def test_execute_prompt_list(orchestrator_service) -> None:
    """Test executing orchestrator with prompt list."""
    # Create mock orchestrator.
    mock_orchestrator = Mock()
    mock_results = [Mock()]
    mock_orchestrator.send_prompts_async = AsyncMock(return_value=mock_results)
    mock_orchestrator.get_score_memory.return_value = []
    mock_orchestrator.get_memory.return_value = []

    orchestrator_id = "test-id"
    orchestrator_service._orchestrator_instances[orchestrator_id] = mock_orchestrator

    execution_config = {
        "execution_type": "prompt_list",
        "input_data": {
            "prompt_list": ["Test prompt 1", "Test prompt 2"],
            "prompt_type": "text",
            "memory_labels": {"test": "true"},
        },
    }

    results = await orchestrator_service.execute_orchestrator(orchestrator_id, execution_config)

    assert "execution_summary" in results
    assert "prompt_request_responses" in results
    mock_orchestrator.send_prompts_async.assert_called_once()


@pytest.mark.asyncio
async def test_execute_dataset(orchestrator_service) -> None:
    """Test executing orchestrator with dataset."""
    # Create mock orchestrator.
    mock_orchestrator = Mock()
    mock_results = [Mock()]
    mock_orchestrator.send_prompts_async = AsyncMock(return_value=mock_results)
    mock_orchestrator.get_score_memory.return_value = []
    mock_orchestrator.get_memory.return_value = []

    orchestrator_id = "test-id"
    orchestrator_service._orchestrator_instances[orchestrator_id] = mock_orchestrator

    execution_config = {
        "execution_type": "dataset",
        "input_data": {"dataset_id": "test_dataset", "sample_size": 5, "memory_labels": {"dataset_test": "true"}},
    }

    # Mock dataset loading
    with patch.object(orchestrator_service, "_load_dataset_prompts") as mock_load:
        mock_load.return_value = ["prompt1", "prompt2", "prompt3"]

        results = await orchestrator_service.execute_orchestrator(orchestrator_id, execution_config)

        assert "execution_summary" in results
        assert "prompt_request_responses" in results
        mock_orchestrator.send_prompts_async.assert_called_once()
        mock_load.assert_called_once_with("test_dataset", 5)


@pytest.mark.asyncio
async def test_generator_target_bridge() -> None:
    """Test ConfiguredGeneratorTarget bridge functionality."""
    from pyrit.models import PromptRequestPiece

    from violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service import ConfiguredGeneratorTarget

    generator_config = {"name": "test_generator", "type": "test_type"}

    target = ConfiguredGeneratorTarget(generator_config)

    # Test identifier
    identifier = target.get_identifier()
    assert identifier["__type__"] == "ConfiguredGeneratorTarget"
    assert identifier["generator_name"] == "test_generator"

    # Test send prompt with mocked execution
    with patch(
        "violentutf_api.fastapi_app.app.services.generator_integration_service.execute_generator_prompt"
    ) as mock_execute:
        mock_execute.return_value = {"success": True, "response": "Test response"}

        prompt_piece = PromptRequestPiece(role="user", original_value="Test prompt", conversation_id="test_conv")

        response = await target.send_prompt_async(prompt_piece)

        assert response is not None
        assert len(response.request_pieces) == 2  # user + assistant
        mock_execute.assert_called_once()


def test_parameter_descriptions(orchestrator_service) -> None:
    """Test parameter description generation."""
    descriptions = orchestrator_service._get_parameter_description(Mock, "objective_target")
    assert "target" in descriptions.lower()

    descriptions = orchestrator_service._get_parameter_description(Mock, "batch_size")
    assert "batch" in descriptions.lower()


def test_use_cases(orchestrator_service) -> None:
    """Test use case mapping."""
    use_cases = orchestrator_service._get_use_cases("PromptSendingOrchestrator")
    assert "basic_prompting" in use_cases
    assert "dataset_testing" in use_cases

    unknown_cases = orchestrator_service._get_use_cases("UnknownOrchestrator")
    assert unknown_cases == ["general_purpose"]


@pytest.mark.asyncio
async def test_orchestrator_memory_retrieval(orchestrator_service) -> None:
    """Test orchestrator memory retrieval."""
    mock_orchestrator = Mock()
    mock_memory_pieces = [Mock(id="1", role="user", original_value="test")]
    mock_orchestrator.get_memory.return_value = mock_memory_pieces

    orchestrator_id = "test-id"
    orchestrator_service._orchestrator_instances[orchestrator_id] = mock_orchestrator

    memory_pieces = orchestrator_service.get_orchestrator_memory(orchestrator_id)

    assert len(memory_pieces) == 1
    mock_orchestrator.get_memory.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_scores_retrieval(orchestrator_service) -> None:
    """Test orchestrator scores retrieval."""
    mock_orchestrator = Mock()
    mock_scores = [Mock(id="1", score_value=0.8, score_type="test")]
    mock_orchestrator.get_score_memory.return_value = mock_scores

    orchestrator_id = "test-id"
    orchestrator_service._orchestrator_instances[orchestrator_id] = mock_orchestrator

    scores = orchestrator_service.get_orchestrator_scores(orchestrator_id)

    assert len(scores) == 1
    mock_orchestrator.get_score_memory.assert_called_once()


def test_orchestrator_disposal(orchestrator_service) -> None:
    """Test orchestrator instance cleanup."""
    mock_orchestrator = Mock()
    orchestrator_id = "test-id"
    orchestrator_service._orchestrator_instances[orchestrator_id] = mock_orchestrator

    orchestrator_service.dispose_orchestrator(orchestrator_id)

    assert orchestrator_id not in orchestrator_service._orchestrator_instances
    mock_orchestrator.dispose_db_engine.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_orchestrator_type(orchestrator_service) -> None:
    """Test error handling for invalid orchestrator type."""
    config = {"orchestrator_type": "InvalidOrchestrator", "parameters": {}}

    with pytest.raises(ValueError, match="Unknown orchestrator type"):
        await orchestrator_service.create_orchestrator_instance(config)


@pytest.mark.asyncio
async def test_missing_orchestrator_execution(orchestrator_service) -> None:
    """Test error handling for missing orchestrator during execution."""
    execution_config = {"execution_type": "prompt_list", "input_data": {"prompt_list": ["test"]}}

    with pytest.raises(ValueError, match="Orchestrator not found"):
        await orchestrator_service.execute_orchestrator("nonexistent", execution_config)


@pytest.mark.asyncio
async def test_unsupported_execution_type(orchestrator_service) -> None:
    """Test error handling for unsupported execution type."""
    mock_orchestrator = Mock()
    orchestrator_id = "test-id"
    orchestrator_service._orchestrator_instances[orchestrator_id] = mock_orchestrator

    execution_config = {"execution_type": "unsupported_type", "input_data": {}}

    with pytest.raises(ValueError, match="Unsupported execution type"):
        await orchestrator_service.execute_orchestrator(orchestrator_id, execution_config)
