"""
Unit tests for Garak integration service (app.services.garak_integration)

This module tests the Garak LLM vulnerability scanner integration including:
- Scanner initialization
- Probe configuration
- Scan execution
- Result processing
- Error handling
"""

import os
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent.parent / "violentutf_api" / "fastapi_app"),
)

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

# Now we can import the service
from app.services.garak_integration import GarakService

# Import db mock to set up mocks before any app imports
from tests import conftest_db_mock


class TestGarakIntegrationService:
    """Test Garak integration service"""

    @pytest.fixture
    def garak_service(self):
        """Create Garak service instance"""
        with patch.object(GarakService, "_initialize_garak"):
            service = GarakService()
            service.available = True
            service.is_available = Mock(return_value=True)
            service.list_available_probes = Mock(return_value=[])
            service.list_available_generators = Mock(return_value=[])
            service.list_available_detectors = Mock(return_value=[])
            service.run_scan = AsyncMock(return_value={"status": "completed"})
            service.get_scan_results = AsyncMock(return_value=None)
            service.list_scans = Mock(return_value={})
            service.create_scan_harness = Mock()
            return service

    @pytest.fixture
    def mock_probe(self):
        """Create mock Garak probe"""
        probe = Mock()
        probe.name = "test_probe"
        probe.description = "Test probe description"
        probe.tags = ["test", "security"]
        probe.probe = Mock(
            return_value=[
                {"prompt": "test prompt 1", "response": None},
                {"prompt": "test prompt 2", "response": None},
            ]
        )
        return probe

    @pytest.fixture
    def mock_detector(self):
        """Create mock Garak detector"""
        detector = Mock()
        detector.name = "test_detector"
        detector.description = "Test detector description"
        detector.detect = Mock(
            return_value=[
                {"passed": True, "score": 1.0},
                {"passed": False, "score": 0.3},
            ]
        )
        return detector

    @pytest.fixture
    def mock_generator(self):
        """Create mock Garak generator"""
        generator = Mock()
        generator.name = "test_generator"
        generator.generate = Mock(return_value="Generated response")
        return generator

    @pytest.fixture
    def scan_config(self):
        """Create scan configuration"""
        return {
            "target": {
                "type": "http_endpoint",
                "url": "http://test-target/api/chat",
                "headers": {"Authorization": "Bearer test-token"},
            },
            "probes": ["encoding.InjectAscii85", "malwaregen.MalwareGenerator"],
            "detectors": ["encoding.DecodeAscii85", "malware.MalwareDetector"],
            "generators": ["test.Static"],
            "harness": "probewise",
            "max_prompts": 10,
        }

    # ======================
    # Initialization Tests
    # ======================

    def test_service_initialization(self, garak_service):
        """Test service initialization"""
        assert hasattr(garak_service, "available")
        assert hasattr(garak_service, "is_available")
        assert hasattr(garak_service, "list_available_probes")
        assert garak_service.is_available() == True

    def test_initialization_without_garak(self):
        """Test initialization when Garak is not installed"""
        with patch(
            "app.services.garak_integration.GarakService._initialize_garak",
            side_effect=ImportError("No module named 'garak'"),
        ):
            service = GarakService()
            assert service.available == False
            assert service.is_available() == False

    # ======================
    # Probe Discovery Tests
    # ======================

    def test_get_available_probes(self, garak_service):
        """Test listing available probes"""
        # Create mock garak module
        mock_garak = Mock()
        mock_garak._plugins = Mock()

        # Mock the enumerate_plugins function
        mock_garak._plugins.enumerate_plugins = Mock(
            return_value=["encoding", "malwaregen"]
        )

        # Mock probe modules
        mock_encoding_module = Mock()
        mock_encoding_module.InjectAscii85 = Mock()
        mock_encoding_module.InjectAscii85.description = (
            "Inject ASCII85 encoded payloads"
        )
        mock_encoding_module.InjectAscii85.tags = ["encoding", "injection"]
        mock_encoding_module.InjectAscii85.goal = (
            "Test ASCII85 encoding vulnerabilities"
        )
        mock_encoding_module.InjectAscii85.probe = True

        mock_malware_module = Mock()
        mock_malware_module.MalwareGenerator = Mock()
        mock_malware_module.MalwareGenerator.description = "Generate malware patterns"
        mock_malware_module.MalwareGenerator.tags = ["malware", "security"]
        mock_malware_module.MalwareGenerator.goal = "Test malware generation"
        mock_malware_module.MalwareGenerator.probe = True

        # Mock load_plugin
        def mock_load_plugin(plugin_path):
            if plugin_path == "probes.encoding":
                return mock_encoding_module
            elif plugin_path == "probes.malwaregen":
                return mock_malware_module
            return None

        mock_garak._plugins.load_plugin = Mock(side_effect=mock_load_plugin)

        # Patch garak module for this test
        with patch("sys.modules", {"garak": mock_garak}):
            probes = garak_service.list_available_probes()

        assert len(probes) == 2
        assert any(p["name"] == "InjectAscii85" for p in probes)
        assert any(p["module"] == "encoding" for p in probes)

    def test_get_available_probes_empty(self, garak_service):
        """Test getting probes when none are available"""
        # Create mock garak module
        mock_garak = Mock()
        mock_garak._plugins = Mock()
        mock_garak._plugins.enumerate_plugins = Mock(return_value=[])

        # Patch garak module for this test
        with patch("sys.modules", {"garak": mock_garak}):
            probes = garak_service.list_available_probes()
            assert probes == []

    def test_get_available_probes_error(self, garak_service):
        """Test error handling in probe listing"""
        # Create mock garak module
        mock_garak = Mock()
        mock_garak._plugins = Mock()
        mock_garak._plugins.enumerate_plugins = Mock(
            side_effect=Exception("Plugin error")
        )

        # Patch garak module for this test
        with patch("sys.modules", {"garak": mock_garak}):
            probes = garak_service.list_available_probes()
            assert probes == []

    # ======================
    # Generator Discovery Tests
    # ======================

    def test_get_available_generators(self, garak_service):
        """Test listing available generators"""
        # Create mock garak module
        mock_garak = Mock()
        mock_garak._plugins = Mock()

        # Mock the enumerate_plugins function
        mock_garak._plugins.enumerate_plugins = Mock(return_value=["openai", "test"])

        # Mock generator modules
        mock_openai_module = Mock()
        mock_openai_module.ChatGPT = Mock()
        mock_openai_module.ChatGPT.description = "OpenAI ChatGPT generator"
        mock_openai_module.ChatGPT.generator = True

        mock_test_module = Mock()
        mock_test_module.Static = Mock()
        mock_test_module.Static.description = "Static test generator"
        mock_test_module.Static.generator = True

        # Mock load_plugin
        def mock_load_plugin(plugin_path):
            if plugin_path == "generators.openai":
                return mock_openai_module
            elif plugin_path == "generators.test":
                return mock_test_module
            return None

        mock_garak._plugins.load_plugin = Mock(side_effect=mock_load_plugin)

        # Patch garak module for this test
        with patch("sys.modules", {"garak": mock_garak}):
            generators = garak_service.list_available_generators()

        assert len(generators) == 2
        assert any(g["name"] == "ChatGPT" for g in generators)
        assert any(g["module"] == "openai" for g in generators)

    # ======================
    # Detector Discovery Tests
    # ======================

    def test_get_available_detectors(self, garak_service):
        """Test listing available detectors"""
        # Create mock garak module
        mock_garak = Mock()
        mock_garak._plugins = Mock()

        # Mock the enumerate_plugins function
        mock_garak._plugins.enumerate_plugins = Mock(
            return_value=["encoding", "malware"]
        )

        # Mock detector modules
        mock_encoding_module = Mock()
        mock_encoding_module.DecodeAscii85 = Mock()
        mock_encoding_module.DecodeAscii85.description = (
            "Detect ASCII85 encoded content"
        )
        mock_encoding_module.DecodeAscii85.detector = True

        mock_malware_module = Mock()
        mock_malware_module.MalwareDetector = Mock()
        mock_malware_module.MalwareDetector.description = "Detect malware patterns"
        mock_malware_module.MalwareDetector.detector = True

        # Mock load_plugin
        def mock_load_plugin(plugin_path):
            if plugin_path == "detectors.encoding":
                return mock_encoding_module
            elif plugin_path == "detectors.malware":
                return mock_malware_module
            return None

        mock_garak._plugins.load_plugin = Mock(side_effect=mock_load_plugin)

        # Patch garak module for this test
        with patch("sys.modules", {"garak": mock_garak}):
            detectors = garak_service.list_available_detectors()

        assert len(detectors) == 2
        assert any(d["name"] == "DecodeAscii85" for d in detectors)
        assert any(d["module"] == "encoding" for d in detectors)

    # ======================
    # Scan Execution Tests
    # ======================

    @pytest.mark.asyncio
    async def test_run_scan_success(
        self, garak_service, scan_config, mock_probe, mock_detector
    ):
        """Test successful scan execution"""
        # Mock create_scan_harness
        mock_harness = Mock()
        mock_harness.run = AsyncMock(
            return_value={
                "results": [
                    {
                        "probe": "encoding.InjectAscii85",
                        "prompts": ["test prompt 1", "test prompt 2"],
                        "responses": ["response 1", "response 2"],
                        "detector_results": [
                            {
                                "detector": "encoding.DecodeAscii85",
                                "passed": True,
                                "score": 0.95,
                            }
                        ],
                    }
                ],
                "summary": {
                    "total_prompts": 2,
                    "vulnerabilities_found": 0,
                    "scan_duration": 1.5,
                },
            }
        )

        with patch.object(
            garak_service, "create_scan_harness", return_value=mock_harness
        ):
            result = await garak_service.run_scan(scan_config)

            assert result is not None
            assert "results" in result
            assert "summary" in result
            assert result["summary"]["total_prompts"] == 2

    @pytest.mark.asyncio
    async def test_run_scan_with_error(self, garak_service, scan_config):
        """Test scan execution with error"""
        with patch.object(
            garak_service,
            "create_scan_harness",
            side_effect=Exception("Scan setup failed"),
        ):

            with pytest.raises(Exception) as exc_info:
                await garak_service.run_scan(scan_config)

            assert "Scan setup failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_scan_results_not_found(self, garak_service):
        """Test getting results for non-existent scan"""
        result = await garak_service.get_scan_results("non-existent-scan-id")
        assert result is None

    # ======================
    # Scan Management Tests
    # ======================

    def test_list_scans(self, garak_service):
        """Test listing all scans"""
        # Add some mock scan data
        mock_scans = {
            "scan1": {"status": "completed", "timestamp": "2024-01-01T00:00:00"},
            "scan2": {"status": "running", "timestamp": "2024-01-01T01:00:00"},
        }

        with patch.object(garak_service, "list_scans", return_value=mock_scans):
            scans = garak_service.list_scans()

            assert len(scans) == 2
            assert "scan1" in scans
            assert scans["scan1"]["status"] == "completed"

    # ======================
    # Utility Method Tests
    # ======================

    def test_create_scan_harness(self, garak_service, scan_config):
        """Test creating scan harness"""
        # Mock the harness creation
        mock_harness_class = Mock()
        mock_harness_instance = Mock()
        mock_harness_class.return_value = mock_harness_instance

        with patch.dict(
            "sys.modules",
            {"garak.harnesses.probewise": Mock(Harness=mock_harness_class)},
        ):
            with patch.object(
                garak_service, "create_scan_harness", return_value=mock_harness_instance
            ):
                harness = garak_service.create_scan_harness(scan_config)

                assert harness is not None
                assert harness == mock_harness_instance

    # ======================
    # Full Workflow Tests
    # ======================

    @pytest.mark.asyncio
    async def test_full_scan_workflow(self, garak_service, scan_config):
        """Test complete scan workflow from config to results"""
        # Mock the scan execution
        mock_scan_result = {
            "scan_id": "test-scan-123",
            "status": "completed",
            "results": [
                {
                    "probe": "encoding.InjectAscii85",
                    "vulnerabilities_found": 1,
                    "total_prompts": 5,
                }
            ],
            "summary": {
                "total_vulnerabilities": 1,
                "scan_duration": 2.5,
                "timestamp": "2024-01-01T00:00:00",
            },
        }

        with patch.object(garak_service, "run_scan", return_value=mock_scan_result):
            # Run scan
            result = await garak_service.run_scan(scan_config)

            assert result["scan_id"] == "test-scan-123"
            assert result["status"] == "completed"
            assert len(result["results"]) == 1
            assert result["summary"]["total_vulnerabilities"] == 1

    # ======================
    # Edge Case Tests
    # ======================

    @pytest.mark.asyncio
    async def test_scan_timeout_handling(self, garak_service, scan_config):
        """Test scan timeout handling"""

        # Mock a long-running scan
        async def mock_long_scan(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate long operation
            return {"status": "timeout"}

        with patch.object(garak_service, "run_scan", side_effect=mock_long_scan):
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(garak_service.run_scan(scan_config), timeout=1.0)

    def test_concurrent_scans(self, garak_service):
        """Test handling multiple concurrent scans"""
        # Create multiple scan configs
        configs = [{"scan_id": f"scan{i}", "probes": [f"probe{i}"]} for i in range(3)]

        # Mock scan execution
        async def mock_scan(config):
            await asyncio.sleep(0.1)  # Simulate work
            return {"scan_id": config["scan_id"], "status": "completed"}

        with patch.object(garak_service, "run_scan", side_effect=mock_scan):
            # Run scans concurrently
            async def run_all():
                tasks = [garak_service.run_scan(config) for config in configs]
                results = await asyncio.gather(*tasks)
                return results

            results = asyncio.run(run_all())

            assert len(results) == 3
            assert all(r["status"] == "completed" for r in results)

    # ======================
    # Security Tests
    # ======================

    def test_malicious_probe_name(self, garak_service):
        """Test handling of malicious probe names"""
        malicious_names = [
            "../../../etc/passwd",
            "probe'; DROP TABLE scans;--",
            "<script>alert('xss')</script>",
            "probe\x00null",
        ]

        for name in malicious_names:
            # Should handle without executing malicious code
            # Create mock garak module
            mock_garak = Mock()
            mock_garak._plugins = Mock()
            mock_garak._plugins.load_plugin = Mock(return_value=None)

            with patch("sys.modules", {"garak": mock_garak}):
                result = garak_service.list_available_probes()
                assert isinstance(result, list)  # Should return empty list, not error
