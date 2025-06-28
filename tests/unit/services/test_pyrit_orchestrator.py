"""
Unit tests for PyRIT orchestrator service (app.services.pyrit_orchestrator_service)

This module tests the PyRIT orchestrator service including:
- Orchestrator lifecycle management
- Memory management
- Target and scorer configuration
- Execution handling
- Error scenarios
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest
from app.services.pyrit_orchestrator_service import PyRITOrchestratorService
from pyrit.memory import CentralMemory, MemoryInterface
from pyrit.models import PromptRequestPiece, PromptRequestResponse, SeedPrompt
from pyrit.orchestrator import Orchestrator, PromptSendingOrchestrator
from pyrit.prompt_converter import PromptConverter
from pyrit.prompt_target import PromptChatTarget, PromptTarget
from pyrit.score.scorer import Scorer


class TestPyRITOrchestratorService:
    """Test PyRIT orchestrator service"""

    @pytest.fixture
    def orchestrator_service(self):
        """Create orchestrator service instance"""
        with patch(
            "app.services.pyrit_orchestrator_service.CentralMemory"
        ) as mock_memory:
            service = PyRITOrchestratorService()
            return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator"""
        orchestrator = Mock(spec=PromptSendingOrchestrator)
        orchestrator.id = str(uuid.uuid4())
        orchestrator.send_prompts_async = AsyncMock()
        orchestrator.print_conversation = Mock()
        orchestrator.dispose_db_engine = Mock()
        return orchestrator

    @pytest.fixture
    def mock_prompt_target(self):
        """Create mock prompt target"""
        target = Mock(spec=PromptChatTarget)
        target.send_prompt_async = AsyncMock()
        return target

    @pytest.fixture
    def mock_scorer(self):
        """Create mock scorer"""
        scorer = Mock(spec=Scorer)
        scorer.score_async = AsyncMock()
        scorer.scorer_type = "test_scorer"
        return scorer

    @pytest.fixture
    def mock_converter(self):
        """Create mock converter"""
        converter = Mock(spec=PromptConverter)
        converter.convert = Mock()
        converter.converter_type = "test_converter"
        return converter

    # ======================
    # Initialization Tests
    # ======================

    def test_service_initialization(self):
        """Test service initialization"""
        with patch(
            "app.services.pyrit_orchestrator_service.CentralMemory"
        ) as mock_memory:
            mock_memory.get_memory_instance.side_effect = ValueError("No memory")

            service = PyRITOrchestratorService()

            assert service.memory is None
            assert isinstance(service._orchestrator_instances, dict)
            assert isinstance(service._orchestrator_scorers, dict)
            assert isinstance(service._orchestrator_metadata, dict)
            assert "PromptSendingOrchestrator" in service._orchestrator_registry

    def test_initialize_memory_existing(self):
        """Test memory initialization with existing instance"""
        mock_memory_instance = Mock()

        with patch(
            "app.services.pyrit_orchestrator_service.CentralMemory"
        ) as mock_memory:
            mock_memory.get_memory_instance.return_value = mock_memory_instance

            service = PyRITOrchestratorService()

            assert service.memory == mock_memory_instance

    def test_initialize_memory_new(self):
        """Test memory initialization when no instance exists"""
        with patch(
            "app.services.pyrit_orchestrator_service.CentralMemory"
        ) as mock_memory:
            mock_memory.get_memory_instance.side_effect = ValueError("No memory")

            service = PyRITOrchestratorService()

            assert service.memory is None

    def test_validate_memory_access_with_memory(self, orchestrator_service):
        """Test memory validation with global memory"""
        orchestrator_service.memory = Mock()

        result = orchestrator_service.validate_memory_access()

        assert result is True

    def test_validate_memory_access_without_memory(self, orchestrator_service):
        """Test memory validation without global memory"""
        orchestrator_service.memory = None

        result = orchestrator_service.validate_memory_access()

        assert result is True  # Should still be valid

    def test_validate_memory_access_error(self, orchestrator_service):
        """Test memory validation with error"""
        with patch.object(
            orchestrator_service, "_get_memory", side_effect=Exception("Memory error")
        ):
            result = orchestrator_service.validate_memory_access()

            assert result is False

    # ======================
    # Orchestrator Discovery Tests
    # ======================

    def test_discover_orchestrator_types(self, orchestrator_service):
        """Test orchestrator type discovery"""
        types = orchestrator_service._discover_orchestrator_types()

        assert "PromptSendingOrchestrator" in types
        assert types["PromptSendingOrchestrator"] == PromptSendingOrchestrator

    def test_get_orchestrator_types(self, orchestrator_service):
        """Test getting orchestrator types with metadata"""
        types_info = orchestrator_service.get_orchestrator_types()

        assert len(types_info) > 0
        assert any(t["name"] == "PromptSendingOrchestrator" for t in types_info)

        # Check metadata structure
        for type_info in types_info:
            assert "name" in type_info
            assert "description" in type_info
            assert "parameters" in type_info

    # ======================
    # Target Creation Tests
    # ======================

    @patch("app.services.pyrit_orchestrator_service.import_module")
    def test_create_target_prompt_chat(self, mock_import, orchestrator_service):
        """Test creating PromptChatTarget"""
        mock_module = Mock()
        mock_target_class = Mock()
        mock_target_instance = Mock(spec=PromptChatTarget)
        mock_target_class.return_value = mock_target_instance
        mock_module.PromptChatTarget = mock_target_class
        mock_import.return_value = mock_module

        config = {
            "type": "PromptChatTarget",
            "model_name": "test-model",
            "endpoint": "http://test.com",
        }

        target = orchestrator_service.create_target(config)

        assert target == mock_target_instance
        mock_target_class.assert_called_once()

    def test_create_target_unknown_type(self, orchestrator_service):
        """Test creating target with unknown type"""
        config = {"type": "UnknownTarget"}

        with pytest.raises(ValueError) as exc_info:
            orchestrator_service.create_target(config)

        assert "Unknown target type" in str(exc_info.value)

    def test_create_target_import_error(self, orchestrator_service):
        """Test creating target with import error"""
        with patch(
            "app.services.pyrit_orchestrator_service.import_module",
            side_effect=ImportError("Module not found"),
        ):
            config = {"type": "PromptChatTarget"}

            with pytest.raises(ValueError) as exc_info:
                orchestrator_service.create_target(config)

            assert "Failed to import target" in str(exc_info.value)

    # ======================
    # Scorer Creation Tests
    # ======================

    @patch("app.services.pyrit_orchestrator_service.import_module")
    def test_create_scorers_single(self, mock_import, orchestrator_service):
        """Test creating single scorer"""
        mock_module = Mock()
        mock_scorer_class = Mock()
        mock_scorer_instance = Mock(spec=Scorer)
        mock_scorer_class.return_value = mock_scorer_instance
        mock_module.TestScorer = mock_scorer_class
        mock_import.return_value = mock_module

        configs = [{"type": "TestScorer", "param1": "value1"}]

        scorers = orchestrator_service.create_scorers(configs)

        assert len(scorers) == 1
        assert scorers[0] == mock_scorer_instance

    def test_create_scorers_multiple(self, orchestrator_service):
        """Test creating multiple scorers"""
        with patch.object(orchestrator_service, "create_scorer") as mock_create:
            mock_scorer1 = Mock(spec=Scorer)
            mock_scorer2 = Mock(spec=Scorer)
            mock_create.side_effect = [mock_scorer1, mock_scorer2]

            configs = [{"type": "Scorer1"}, {"type": "Scorer2"}]

            scorers = orchestrator_service.create_scorers(configs)

            assert len(scorers) == 2
            assert mock_create.call_count == 2

    def test_create_scorers_empty_list(self, orchestrator_service):
        """Test creating scorers with empty config"""
        scorers = orchestrator_service.create_scorers([])

        assert scorers == []

    # ======================
    # Converter Creation Tests
    # ======================

    @patch("app.services.pyrit_orchestrator_service.import_module")
    def test_create_converters(self, mock_import, orchestrator_service):
        """Test creating converters"""
        mock_module = Mock()
        mock_converter_class = Mock()
        mock_converter_instance = Mock(spec=PromptConverter)
        mock_converter_class.return_value = mock_converter_instance
        mock_module.TestConverter = mock_converter_class
        mock_import.return_value = mock_module

        configs = [{"type": "TestConverter"}]

        converters = orchestrator_service.create_converters(configs)

        assert len(converters) == 1
        assert converters[0] == mock_converter_instance

    # ======================
    # Orchestrator Creation Tests
    # ======================

    @patch("app.services.pyrit_orchestrator_service.DuckDBMemory")
    def test_create_orchestrator_prompt_sending(
        self, mock_memory_class, orchestrator_service
    ):
        """Test creating PromptSendingOrchestrator"""
        mock_memory_instance = Mock()
        mock_memory_class.return_value = mock_memory_instance

        mock_target = Mock(spec=PromptChatTarget)
        mock_scorers = [Mock(spec=Scorer)]

        config = {
            "type": "PromptSendingOrchestrator",
            "batch_size": 10,
            "verbose": True,
        }

        with patch(
            "app.services.pyrit_orchestrator_service.PromptSendingOrchestrator"
        ) as mock_orch_class:
            mock_orch_instance = Mock()
            mock_orch_instance.id = "test-orch-id"
            mock_orch_class.return_value = mock_orch_instance

            orch_id = orchestrator_service.create_orchestrator(
                config, mock_target, mock_scorers, memory_labels={"test": "label"}
            )

            assert orch_id == "test-orch-id"
            assert (
                orchestrator_service._orchestrator_instances[orch_id]
                == mock_orch_instance
            )
            assert orchestrator_service._orchestrator_scorers[orch_id] == mock_scorers

            # Verify orchestrator creation
            mock_orch_class.assert_called_once()
            call_kwargs = mock_orch_class.call_args[1]
            assert call_kwargs["prompt_target"] == mock_target
            assert call_kwargs["batch_size"] == 10
            assert call_kwargs["verbose"] is True

    def test_create_orchestrator_unknown_type(self, orchestrator_service):
        """Test creating orchestrator with unknown type"""
        config = {"type": "UnknownOrchestrator"}
        mock_target = Mock()

        with pytest.raises(ValueError) as exc_info:
            orchestrator_service.create_orchestrator(config, mock_target)

        assert "Unknown orchestrator type" in str(exc_info.value)

    def test_create_orchestrator_with_converters(self, orchestrator_service):
        """Test creating orchestrator with converters"""
        mock_target = Mock(spec=PromptChatTarget)
        mock_converters = [Mock(spec=PromptConverter)]

        config = {"type": "PromptSendingOrchestrator"}

        with patch(
            "app.services.pyrit_orchestrator_service.PromptSendingOrchestrator"
        ) as mock_orch_class:
            with patch("app.services.pyrit_orchestrator_service.DuckDBMemory"):
                mock_orch_instance = Mock()
                mock_orch_instance.id = "test-id"
                mock_orch_class.return_value = mock_orch_instance

                orch_id = orchestrator_service.create_orchestrator(
                    config, mock_target, converters=mock_converters
                )

                # Verify converters were passed
                call_kwargs = mock_orch_class.call_args[1]
                assert call_kwargs["prompt_converters"] == mock_converters

    # ======================
    # Orchestrator Execution Tests
    # ======================

    @pytest.mark.asyncio
    async def test_run_orchestrator_success(
        self, orchestrator_service, mock_orchestrator
    ):
        """Test successful orchestrator execution"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator
        orchestrator_service._orchestrator_metadata["test-id"] = {"status": "created"}

        # Mock response
        mock_response = Mock(spec=PromptRequestResponse)
        mock_response.request_pieces = [
            Mock(converted_value="Test prompt", original_value="Test prompt")
        ]
        mock_orchestrator.send_prompts_async.return_value = mock_response

        prompts = ["Test prompt 1", "Test prompt 2"]

        result = await orchestrator_service.run_orchestrator("test-id", prompts)

        assert result["status"] == "completed"
        assert "results" in result
        assert result["prompt_count"] == 2
        assert (
            orchestrator_service._orchestrator_metadata["test-id"]["status"]
            == "completed"
        )

        # Verify orchestrator was called
        mock_orchestrator.send_prompts_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_orchestrator_not_found(self, orchestrator_service):
        """Test running non-existent orchestrator"""
        with pytest.raises(ValueError) as exc_info:
            await orchestrator_service.run_orchestrator("non-existent", ["prompt"])

        assert "Orchestrator not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_orchestrator_with_seed_prompts(
        self, orchestrator_service, mock_orchestrator
    ):
        """Test running orchestrator with SeedPrompt objects"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator
        orchestrator_service._orchestrator_metadata["test-id"] = {"status": "created"}

        mock_response = Mock(spec=PromptRequestResponse)
        mock_response.request_pieces = []
        mock_orchestrator.send_prompts_async.return_value = mock_response

        # Create SeedPrompt objects
        prompts = [
            {"value": "Test 1", "data_type": "text"},
            {"value": "Test 2", "data_type": "text"},
        ]

        await orchestrator_service.run_orchestrator("test-id", prompts)

        # Verify SeedPrompt conversion
        call_args = mock_orchestrator.send_prompts_async.call_args[1]
        assert "prompt_list" in call_args
        assert all(isinstance(p, SeedPrompt) for p in call_args["prompt_list"])

    @pytest.mark.asyncio
    async def test_run_orchestrator_error_handling(
        self, orchestrator_service, mock_orchestrator
    ):
        """Test orchestrator execution error handling"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator
        orchestrator_service._orchestrator_metadata["test-id"] = {"status": "created"}

        mock_orchestrator.send_prompts_async.side_effect = Exception("Execution error")

        with pytest.raises(Exception) as exc_info:
            await orchestrator_service.run_orchestrator("test-id", ["prompt"])

        assert "Execution error" in str(exc_info.value)
        assert (
            orchestrator_service._orchestrator_metadata["test-id"]["status"] == "error"
        )

    # ======================
    # Results and Memory Tests
    # ======================

    def test_get_orchestrator_results_success(
        self, orchestrator_service, mock_orchestrator
    ):
        """Test getting orchestrator results"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator
        orchestrator_service._orchestrator_metadata["test-id"] = {
            "status": "completed",
            "results": [{"prompt": "Test", "response": "Response"}],
        }

        # Mock conversation
        mock_orchestrator.get_memory.return_value.get_conversation.return_value = [
            Mock(role="user", content="Test"),
            Mock(role="assistant", content="Response"),
        ]

        results = orchestrator_service.get_orchestrator_results("test-id")

        assert results["status"] == "completed"
        assert "results" in results
        assert "conversation" in results

    def test_get_orchestrator_results_not_found(self, orchestrator_service):
        """Test getting results for non-existent orchestrator"""
        with pytest.raises(ValueError) as exc_info:
            orchestrator_service.get_orchestrator_results("non-existent")

        assert "Orchestrator not found" in str(exc_info.value)

    def test_get_conversation_history(self, orchestrator_service, mock_orchestrator):
        """Test getting conversation history"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator

        mock_memory = Mock()
        mock_memory.get_conversation.return_value = [
            Mock(role="user", content="Hello", timestamp=datetime.now()),
            Mock(role="assistant", content="Hi there", timestamp=datetime.now()),
        ]
        mock_orchestrator.get_memory.return_value = mock_memory

        history = orchestrator_service.get_conversation_history("test-id")

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"

    # ======================
    # Cleanup Tests
    # ======================

    def test_cleanup_orchestrator(self, orchestrator_service, mock_orchestrator):
        """Test orchestrator cleanup"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator
        orchestrator_service._orchestrator_metadata["test-id"] = {"status": "completed"}
        orchestrator_service._orchestrator_scorers["test-id"] = []

        orchestrator_service.cleanup_orchestrator("test-id")

        assert "test-id" not in orchestrator_service._orchestrator_instances
        assert "test-id" not in orchestrator_service._orchestrator_metadata
        assert "test-id" not in orchestrator_service._orchestrator_scorers

        mock_orchestrator.dispose_db_engine.assert_called_once()

    def test_cleanup_orchestrator_error_handling(
        self, orchestrator_service, mock_orchestrator
    ):
        """Test orchestrator cleanup with disposal error"""
        orchestrator_service._orchestrator_instances["test-id"] = mock_orchestrator
        mock_orchestrator.dispose_db_engine.side_effect = Exception("Disposal error")

        # Should not raise, just log error
        orchestrator_service.cleanup_orchestrator("test-id")

        assert "test-id" not in orchestrator_service._orchestrator_instances

    def test_list_orchestrators(self, orchestrator_service):
        """Test listing all orchestrators"""
        # Add test orchestrators
        orchestrator_service._orchestrator_instances["orch1"] = Mock()
        orchestrator_service._orchestrator_metadata["orch1"] = {
            "type": "PromptSendingOrchestrator",
            "status": "running",
            "created_at": "2024-01-01",
        }

        orchestrator_service._orchestrator_instances["orch2"] = Mock()
        orchestrator_service._orchestrator_metadata["orch2"] = {
            "type": "PromptSendingOrchestrator",
            "status": "completed",
            "created_at": "2024-01-02",
        }

        orchestrators = orchestrator_service.list_orchestrators()

        assert len(orchestrators) == 2
        assert any(o["id"] == "orch1" for o in orchestrators)
        assert any(o["id"] == "orch2" for o in orchestrators)

    # ======================
    # Integration Tests
    # ======================

    @pytest.mark.asyncio
    async def test_full_orchestrator_lifecycle(self, orchestrator_service):
        """Test complete orchestrator lifecycle"""
        with patch(
            "app.services.pyrit_orchestrator_service.PromptSendingOrchestrator"
        ) as mock_orch_class:
            with patch("app.services.pyrit_orchestrator_service.DuckDBMemory"):
                # Setup
                mock_orch = Mock()
                mock_orch.id = "lifecycle-test"
                mock_orch.send_prompts_async = AsyncMock()
                mock_orch.get_memory = Mock()
                mock_orch.dispose_db_engine = Mock()
                mock_orch_class.return_value = mock_orch

                mock_target = Mock(spec=PromptChatTarget)

                # Create
                config = {"type": "PromptSendingOrchestrator"}
                orch_id = orchestrator_service.create_orchestrator(config, mock_target)

                assert orch_id == "lifecycle-test"
                assert (
                    orchestrator_service._orchestrator_instances[orch_id] == mock_orch
                )

                # Run
                mock_response = Mock()
                mock_response.request_pieces = []
                mock_orch.send_prompts_async.return_value = mock_response

                result = await orchestrator_service.run_orchestrator(
                    orch_id, ["Test prompt"]
                )
                assert result["status"] == "completed"

                # Get results
                results = orchestrator_service.get_orchestrator_results(orch_id)
                assert results["status"] == "completed"

                # Cleanup
                orchestrator_service.cleanup_orchestrator(orch_id)
                assert orch_id not in orchestrator_service._orchestrator_instances
                mock_orch.dispose_db_engine.assert_called_once()


class TestPyRITServiceEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_orchestrator_creation(self, orchestrator_service):
        """Test creating multiple orchestrators concurrently"""
        with patch(
            "app.services.pyrit_orchestrator_service.PromptSendingOrchestrator"
        ) as mock_orch_class:
            with patch("app.services.pyrit_orchestrator_service.DuckDBMemory"):
                # Create different orchestrators for each call
                mock_orch_class.side_effect = [Mock(id=f"orch-{i}") for i in range(5)]

                mock_target = Mock(spec=PromptChatTarget)
                config = {"type": "PromptSendingOrchestrator"}

                # Create orchestrators concurrently
                tasks = [
                    orchestrator_service.create_orchestrator(config, mock_target)
                    for _ in range(5)
                ]

                # Should not raise any concurrency issues
                results = await asyncio.gather(
                    *[
                        (
                            asyncio.create_task(t)
                            if asyncio.iscoroutine(t)
                            else asyncio.create_task(asyncio.coroutine(lambda: t)())
                        )
                        for t in tasks
                    ]
                )

                assert len(set(results)) == 5  # All unique IDs

    def test_memory_label_handling(self, orchestrator_service):
        """Test memory label creation and handling"""
        with patch(
            "app.services.pyrit_orchestrator_service.DuckDBMemory"
        ) as mock_memory_class:
            mock_memory_instance = Mock()
            mock_memory_class.return_value = mock_memory_instance

            labels = {"session": "test", "user": "admin"}

            # Call internal method
            memory = orchestrator_service._create_orchestrator_memory(labels)

            assert memory == mock_memory_instance

            # Verify labels were passed
            call_kwargs = mock_memory_class.call_args[1]
            assert call_kwargs["labels"] == labels
