import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from violentutf_api.fastapi_app.app.services.dataset_integration_service import (
    get_dataset_prompts,
)
from violentutf_api.fastapi_app.app.services.generator_integration_service import (
    execute_generator_prompt,
)
from violentutf_api.fastapi_app.app.services.scorer_integration_service import (
    execute_scorer,
)


@pytest.mark.asyncio
async def test_generator_integration_apisix():
    """Test generator integration through APISIX"""
    generator_name = "test_apisix_generator"
    prompt = "Test prompt"
    conversation_id = "test_conv"

    # Mock generator configuration
    mock_generator_config = {
        "name": generator_name,
        "type": "apisix_ai_gateway",
        "parameters": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000,
        },
    }

    with patch(
        "violentutf_api.fastapi_app.app.services.generator_integration_service.get_generator_by_name"
    ) as mock_get_gen:
        mock_get_gen.return_value = mock_generator_config

        with patch("requests.post") as mock_post:
            # Mock successful APISIX response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response from OpenAI"}}]
            }
            mock_post.return_value = mock_response

            result = await execute_generator_prompt(
                generator_name, prompt, conversation_id
            )

            assert result["success"] is True
            assert result["response"] == "Test response from OpenAI"
            assert result["provider"] == "openai"
            assert result["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_generator_integration_error():
    """Test generator integration error handling"""
    generator_name = "nonexistent_generator"
    prompt = "Test prompt"

    with patch(
        "violentutf_api.fastapi_app.app.services.generator_integration_service.get_generator_by_name"
    ) as mock_get_gen:
        mock_get_gen.return_value = None

        result = await execute_generator_prompt(generator_name, prompt)

        assert result["success"] is False
        assert "not found" in result["response"]


@pytest.mark.asyncio
async def test_dataset_integration_native():
    """Test dataset integration for native datasets"""
    dataset_id = "test_native_dataset"
    sample_size = 3

    # Mock dataset configuration
    mock_dataset_config = {
        "id": dataset_id,
        "source_type": "native",
        "prompts": [
            {"value": "Prompt 1"},
            {"value": "Prompt 2"},
            {"value": "Prompt 3"},
            {"value": "Prompt 4"},
            {"value": "Prompt 5"},
        ],
    }

    with patch(
        "violentutf_api.fastapi_app.app.services.dataset_integration_service._get_dataset_by_id"
    ) as mock_get_dataset:
        mock_get_dataset.return_value = mock_dataset_config

        prompts = await get_dataset_prompts(dataset_id, sample_size)

        assert len(prompts) == sample_size
        assert all(isinstance(p, str) for p in prompts)
        assert all(p.startswith("Prompt") for p in prompts)


@pytest.mark.asyncio
async def test_dataset_integration_memory():
    """Test dataset integration for memory datasets"""
    dataset_id = "test_memory_dataset"

    # Mock dataset configuration
    mock_dataset_config = {
        "id": dataset_id,
        "name": "test_memory_dataset",
        "source_type": "memory",
    }

    with patch(
        "violentutf_api.fastapi_app.app.services.dataset_integration_service._get_dataset_by_id"
    ) as mock_get_dataset:
        mock_get_dataset.return_value = mock_dataset_config

        with patch(
            "violentutf_api.fastapi_app.app.api.endpoints.datasets.get_memory_datasets"
        ) as mock_get_memory:
            mock_get_memory.return_value = [
                {
                    "dataset_name": "test_memory_dataset",
                    "prompts": ["Memory prompt 1", "Memory prompt 2"],
                }
            ]

            prompts = await get_dataset_prompts(dataset_id)

            assert len(prompts) == 2
            assert prompts[0] == "Memory prompt 1"
            assert prompts[1] == "Memory prompt 2"


@pytest.mark.asyncio
async def test_dataset_integration_not_found():
    """Test dataset integration for non-existent dataset"""
    dataset_id = "nonexistent_dataset"

    with patch(
        "violentutf_api.fastapi_app.app.services.dataset_integration_service._get_dataset_by_id"
    ) as mock_get_dataset:
        mock_get_dataset.return_value = None

        with pytest.raises(ValueError, match="Dataset not found"):
            await get_dataset_prompts(dataset_id)


@pytest.mark.asyncio
async def test_scorer_integration_true_false():
    """Test scorer integration for true/false scorer"""
    scorer_name = "test_true_false_scorer"
    text = "This is a helpful response"

    # Mock scorer configuration
    mock_scorer_config = {
        "name": scorer_name,
        "type": "true_false_scorer",
        "category": "helpfulness",
        "criteria": "helpful",
    }

    with patch(
        "violentutf_api.fastapi_app.app.services.scorer_integration_service.get_scorer_by_name"
    ) as mock_get_scorer:
        mock_get_scorer.return_value = mock_scorer_config

        result = await execute_scorer(scorer_name, text)

        assert (
            result["score_value"] == 1.0
        )  # Should be 1.0 because text contains "helpful"
        assert result["score_type"] == "true_false"
        assert result["score_category"] == "helpfulness"
        assert "helpful" in result["score_rationale"]


@pytest.mark.asyncio
async def test_scorer_integration_likert():
    """Test scorer integration for Likert scale scorer"""
    scorer_name = "test_likert_scorer"
    text = "This is a medium length response that should score somewhere in the middle range."

    # Mock scorer configuration
    mock_scorer_config = {
        "name": scorer_name,
        "type": "likert_scorer",
        "category": "quality",
    }

    with patch(
        "violentutf_api.fastapi_app.app.services.scorer_integration_service.get_scorer_by_name"
    ) as mock_get_scorer:
        mock_get_scorer.return_value = mock_scorer_config

        result = await execute_scorer(scorer_name, text)

        assert isinstance(result["score_value"], float)
        assert result["score_value"] >= 1.0 and result["score_value"] <= 5.0
        assert result["score_type"] == "likert_scale"
        assert result["score_category"] == "quality"


@pytest.mark.asyncio
async def test_scorer_integration_error():
    """Test scorer integration error handling"""
    scorer_name = "nonexistent_scorer"
    text = "Test text"

    with patch(
        "violentutf_api.fastapi_app.app.services.scorer_integration_service.get_scorer_by_name"
    ) as mock_get_scorer:
        mock_get_scorer.return_value = None

        result = await execute_scorer(scorer_name, text)

        assert result["score_type"] == "error"
        assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_end_to_end_orchestrator_workflow():
    """Test complete orchestrator workflow from creation to execution"""
    from violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service import (
        PyRITOrchestratorService,
    )

    orchestrator_service = PyRITOrchestratorService()

    # Mock all integration services
    with patch(
        "violentutf_api.fastapi_app.app.services.generator_integration_service.get_generator_by_name"
    ) as mock_get_gen:
        mock_get_gen.return_value = {
            "name": "test_generator",
            "type": "apisix_ai_gateway",
            "parameters": {"provider": "openai", "model": "gpt-4"},
        }

        with patch(
            "violentutf_api.fastapi_app.app.services.generator_integration_service.execute_generator_prompt"
        ) as mock_exec_gen:
            mock_exec_gen.return_value = {
                "success": True,
                "response": "Generated response",
            }

            # Create orchestrator configuration
            config = {
                "orchestrator_type": "PromptSendingOrchestrator",
                "parameters": {
                    "objective_target": {
                        "type": "configured_generator",
                        "generator_name": "test_generator",
                    },
                    "batch_size": 1,
                    "verbose": False,
                },
            }

            # Create orchestrator instance
            orchestrator_id = await orchestrator_service.create_orchestrator_instance(
                config
            )
            assert orchestrator_id is not None

            # Execute with prompt list
            execution_config = {
                "execution_type": "prompt_list",
                "input_data": {
                    "prompt_list": ["Test prompt 1", "Test prompt 2"],
                    "memory_labels": {"test": "integration"},
                },
            }

            results = await orchestrator_service.execute_orchestrator(
                orchestrator_id, execution_config
            )

            # Verify results structure
            assert "execution_summary" in results
            assert "prompt_request_responses" in results
            assert "scores" in results
            assert "memory_export" in results

            # Verify execution summary
            summary = results["execution_summary"]
            assert summary["total_prompts"] == 2
            assert summary["successful_responses"] >= 0
            assert summary["failed_responses"] >= 0

            # Clean up
            orchestrator_service.dispose_orchestrator(orchestrator_id)


@pytest.mark.asyncio
async def test_orchestrator_with_dataset_execution():
    """Test orchestrator execution with dataset input"""
    from violentutf_api.fastapi_app.app.services.pyrit_orchestrator_service import (
        PyRITOrchestratorService,
    )

    orchestrator_service = PyRITOrchestratorService()

    # Mock generator integration
    with patch(
        "violentutf_api.fastapi_app.app.services.generator_integration_service.get_generator_by_name"
    ) as mock_get_gen:
        mock_get_gen.return_value = {
            "name": "test_generator",
            "type": "test_type",
            "parameters": {},
        }

        with patch(
            "violentutf_api.fastapi_app.app.services.generator_integration_service.execute_generator_prompt"
        ) as mock_exec_gen:
            mock_exec_gen.return_value = {
                "success": True,
                "response": "Dataset response",
            }

            # Mock dataset integration
            with patch(
                "violentutf_api.fastapi_app.app.services.dataset_integration_service.get_dataset_prompts"
            ) as mock_get_dataset:
                mock_get_dataset.return_value = [
                    "Dataset prompt 1",
                    "Dataset prompt 2",
                    "Dataset prompt 3",
                ]

                # Create orchestrator
                config = {
                    "orchestrator_type": "PromptSendingOrchestrator",
                    "parameters": {
                        "objective_target": {
                            "type": "configured_generator",
                            "generator_name": "test_generator",
                        }
                    },
                }

                orchestrator_id = (
                    await orchestrator_service.create_orchestrator_instance(config)
                )

                # Execute with dataset
                execution_config = {
                    "execution_type": "dataset",
                    "input_data": {
                        "dataset_id": "test_dataset",
                        "sample_size": 2,
                        "memory_labels": {"dataset_test": "true"},
                    },
                }

                results = await orchestrator_service.execute_orchestrator(
                    orchestrator_id, execution_config
                )

                # Verify dataset was loaded with sampling
                mock_get_dataset.assert_called_once_with("test_dataset", 2)

                # Verify results
                assert "execution_summary" in results
                summary = results["execution_summary"]
                assert summary["total_prompts"] >= 0

                # Clean up
                orchestrator_service.dispose_orchestrator(orchestrator_id)
