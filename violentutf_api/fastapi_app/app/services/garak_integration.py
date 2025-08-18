"""
Garak Integration Service
Provides NVIDIA Garak LLM vulnerability scanning functionality for ViolentUTF platform
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GarakService:
    """Service class for Garak integration"""

    def __init__(self):
        self.available = False
        self._initialize_garak()

    def _initialize_garak(self):
        """Initialize Garak scanner and core components"""
        try:
            import garak
            from garak import _plugins
            from garak.evaluators import Evaluator
            from garak.generators import Generator

            self.available = True
            logger.info("✅ Garak initialized successfully")

        except ImportError as e:
            logger.error(f"❌ Garak not available: {e}")
            self.available = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Garak: {e}")
            self.available = False

    def is_available(self) -> bool:
        """Check if Garak is properly initialized"""
        return self.available

    def list_available_probes(self) -> List[Dict[str, Any]]:
        """List all available Garak vulnerability probes"""
        if not self.is_available():
            return []

        try:
            import garak._plugins
            from garak._plugins import enumerate_plugins

            probes = []
            probe_modules = enumerate_plugins("probes")

            for module_name in probe_modules:
                try:
                    module = garak._plugins.load_plugin(f"probes.{module_name}")

                    # Get probe classes from module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and hasattr(attr, "probe") and attr_name != "Probe":
                            probe_info = {
                                "module": module_name,
                                "name": attr_name,
                                "description": getattr(attr, "description", "No description available"),
                                "tags": getattr(attr, "tags", []),
                                "goal": getattr(attr, "goal", "Unknown goal"),
                            }
                            probes.append(probe_info)

                except Exception as e:
                    logger.warning(f"Failed to load probe module {module_name}: {e}")
                    continue

            logger.info(f"Found {len(probes)} Garak probes")
            return probes

        except Exception as e:
            logger.error(f"Failed to list Garak probes: {e}")
            return []

    def list_available_generators(self) -> List[Dict[str, Any]]:
        """List all available Garak generators"""
        if not self.is_available():
            return []

        try:
            import garak._plugins
            from garak._plugins import enumerate_plugins

            generators = []
            generator_modules = enumerate_plugins("generators")

            for module_name in generator_modules:
                try:
                    module = garak._plugins.load_plugin(f"generators.{module_name}")

                    # Get generator classes from module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and hasattr(attr, "generate") and attr_name != "Generator":
                            generator_info = {
                                "module": module_name,
                                "name": attr_name,
                                "description": getattr(attr, "description", "No description available"),
                                "supported_models": getattr(attr, "supported_models", []),
                                "uri": getattr(attr, "uri", None),
                            }
                            generators.append(generator_info)

                except Exception as e:
                    logger.warning(f"Failed to load generator module {module_name}: {e}")
                    continue

            logger.info(f"Found {len(generators)} Garak generators")
            return generators

        except Exception as e:
            logger.error(f"Failed to list Garak generators: {e}")
            return []

    async def run_vulnerability_scan(
        self, target_config: Dict[str, Any], probe_config: Dict[str, Any], scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run Garak vulnerability scan against a target
        """
        if not self.is_available():
            raise RuntimeError("Garak is not available")

        scan_id = scan_id or str(uuid.uuid4())

        try:
            import garak.cli
            from garak._plugins import load_plugin
            from garak.generators import Generator

            # Create generator based on target configuration
            generator = await self._create_garak_generator(target_config)

            # Load the specified probe
            probe_module = probe_config.get("module", "encoding")
            probe_name = probe_config.get("name", "InjectBase64")

            probe_class = load_plugin(f"probes.{probe_module}")
            probe_instance = getattr(probe_class, probe_name)()

            # Run the scan
            logger.info(f"Starting Garak scan {scan_id} with probe {probe_module}.{probe_name}")

            # This is a simplified version - in production, you'd use Garak's full CLI
            # Generate test prompts
            test_prompts = probe_instance.probe(generator, attempts=5)

            scan_result = {
                "scan_id": scan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "target": target_config,
                "probe": probe_config,
                "results": test_prompts,
                "status": "completed",
                "summary": {
                    "total_attempts": len(test_prompts),
                    "vulnerabilities_found": sum(1 for r in test_prompts if r.get("passed", False)),
                    "success_rate": (
                        len([r for r in test_prompts if r.get("passed", False)]) / len(test_prompts)
                        if test_prompts
                        else 0
                    ),
                },
            }

            logger.info(
                f"Garak scan {scan_id} completed with {scan_result['summary']['vulnerabilities_found']} vulnerabilities found"
            )

            return scan_result

        except Exception as e:
            logger.error(f"Garak scan failed: {e}")
            return {
                "scan_id": scan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "target": target_config,
                "probe": probe_config,
                "status": "failed",
                "error": str(e),
            }

    async def _create_garak_generator(self, target_config: Dict[str, Any]):
        """Create Garak generator from target configuration"""
        try:
            import garak._plugins

            target_type = target_config.get("type", "rest")

            if target_type == "AI Gateway":
                # Map to REST generator for APISIX
                generator_class = garak._plugins.load_plugin("generators.rest")

                # Get APISIX endpoint
                from app.api.endpoints.generators import get_apisix_endpoint_for_model

                provider = target_config.get("provider", "openai")
                model = target_config.get("model", "gpt-3.5-turbo")
                base_url = target_config.get("base_url", "http://localhost:9080")

                endpoint = get_apisix_endpoint_for_model(provider, model)
                if not endpoint:
                    raise ValueError(f"No APISIX route for {provider}/{model}")

                full_url = f"{base_url}{endpoint}"

                # Create REST generator pointing to APISIX
                generator = generator_class.RestGenerator(name=f"apisix_{provider}_{model}", uri=full_url)

                return generator

            else:
                # Use default OpenAI generator as fallback
                generator_class = garak._plugins.load_plugin("generators.openai")
                return generator_class.OpenAIGenerator()

        except Exception as e:
            logger.error(f"Failed to create Garak generator: {e}")
            raise

    def get_scan_results(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get results for a specific scan"""
        # In a real implementation, this would query a database or file system
        # For now, return None
        return None

    def list_scan_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent scan history"""
        # In a real implementation, this would query stored scan results
        # For now, return empty list
        return []


# Global Garak service instance
garak_service = GarakService()
