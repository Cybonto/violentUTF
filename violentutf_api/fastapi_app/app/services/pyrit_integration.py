"""
PyRIT Integration Service
Provides PyRIT-based AI red-teaming functionality for ViolentUTF platform
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PyRITService:
    """Service class for PyRIT integration"""
    
    def __init__(self):
        self.memory = None
        self._initialize_pyrit()
    
    def _initialize_pyrit(self):
        """Initialize PyRIT memory and core components"""
        try:
            from pyrit.memory import DuckDBMemory
            from pyrit.models import PromptRequestPiece, PromptRequestResponse
            
            # Don't initialize DuckDB memory here to avoid conflicts with orchestrator service
            # The orchestrator service handles its own memory management
            logger.info("✅ PyRIT models available (memory handled by orchestrator service)")
            self.memory = None  # Prevent conflicts
            
        except ImportError as e:
            logger.error(f"❌ PyRIT not available: {e}")
            self.memory = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize PyRIT: {e}")
            self.memory = None
    
    def is_available(self) -> bool:
        """Check if PyRIT is properly initialized"""
        try:
            from pyrit.models import PromptRequestPiece
            return True  # PyRIT is available if we can import its models
        except ImportError:
            return False
    
    async def create_prompt_target(self, target_config: Dict[str, Any]):
        """
        Create a PyRIT PromptTarget from configuration
        This replaces the simulated target creation in generators
        """
        if not self.is_available():
            raise RuntimeError("PyRIT is not available")
        
        try:
            target_type = target_config.get('type', 'HTTPTarget')
            
            if target_type == "AI Gateway":
                return await self._create_apisix_target(target_config)
            elif target_type == "HTTPTarget":
                return await self._create_http_target(target_config)
            else:
                raise ValueError(f"Unsupported target type: {target_type}")
                
        except Exception as e:
            logger.error(f"Failed to create PyRIT target: {e}")
            raise
    
    async def _create_apisix_target(self, config: Dict[str, Any]):
        """Create APISIX-based PyRIT target"""
        from pyrit.prompt_target import PromptChatTarget
        from pyrit.models import PromptRequestPiece, PromptRequestResponse
        
        class APISIXPromptTarget(PromptChatTarget):
            """Custom PyRIT target for APISIX AI Gateway"""
            
            def __init__(self, provider: str, model: str, base_url: str, **kwargs):
                super().__init__()
                self.provider = provider
                self.model = model
                self.base_url = base_url
                self.endpoint_url = self._get_endpoint_url(provider, model)
                
            def _get_endpoint_url(self, provider: str, model: str) -> str:
                """Map provider/model to APISIX endpoint"""
                # Import the mapping function from generators.py
                from app.api.endpoints.generators import get_apisix_endpoint_for_model
                endpoint = get_apisix_endpoint_for_model(provider, model)
                if endpoint:
                    return f"{self.base_url}{endpoint}"
                else:
                    raise ValueError(f"No APISIX route for {provider}/{model}")
            
            async def send_prompt_async(self, prompt_request: PromptRequestPiece) -> PromptRequestResponse:
                """Send prompt through APISIX gateway"""
                import requests
                import json
                
                try:
                    # Prepare request payload
                    payload = {
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt_request.original_value
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                    
                    headers = {
                        "Content-Type": "application/json",
                        "X-API-Gateway": "APISIX"
                    }
                    
                    # Make the API call
                    response = requests.post(
                        self.endpoint_url,
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Extract response based on provider
                        if self.provider == "openai":
                            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        elif self.provider == "anthropic":
                            content = result.get("content", [{}])[0].get("text", "")
                        else:
                            content = str(result.get("response", result))
                        
                        # Create response piece
                        response_piece = PromptRequestPiece(
                            role="assistant",
                            original_value=content,
                            converted_value=content,
                            prompt_target_identifier={"type": "apisix_gateway", "provider": self.provider, "model": self.model}
                        )
                        
                        return PromptRequestResponse(request_pieces=[response_piece])
                    
                    else:
                        error_msg = f"APISIX call failed: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                        
                except Exception as e:
                    logger.error(f"APISIX target error: {e}")
                    raise
            
            def is_json_response_supported(self) -> bool:
                return True
        
        # Create and return the target
        provider = config.get('provider', 'openai')
        model = config.get('model', 'gpt-3.5-turbo')
        base_url = config.get('base_url', 'http://localhost:9080')
        
        return APISIXPromptTarget(provider, model, base_url)
    
    async def _create_http_target(self, config: Dict[str, Any]):
        """Create HTTP-based PyRIT target"""
        from pyrit.prompt_target import PromptTarget
        
        # This would implement a generic HTTP target
        # For now, return a placeholder
        raise NotImplementedError("HTTP target not yet implemented")
    
    async def run_red_team_orchestrator(self, target, prompts: List[str], conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Run PyRIT orchestrator for red-teaming
        This replaces simulated orchestrator functionality
        """
        if not self.is_available():
            raise RuntimeError("PyRIT is not available")
        
        try:
            from pyrit.orchestrator import PromptSendingOrchestrator
            from pyrit.models import PromptRequestPiece
            
            # Create orchestrator
            orchestrator = PromptSendingOrchestrator(
                prompt_target=target,
                memory=self.memory
            )
            
            results = []
            
            for prompt in prompts:
                # Create prompt request piece
                prompt_piece = PromptRequestPiece(
                    role="user",
                    original_value=prompt,
                    converted_value=prompt,
                    conversation_id=conversation_id or str(uuid.uuid4())
                )
                
                # Send prompt and get response
                response = await orchestrator.send_prompts_async([prompt_piece])
                
                # Convert to result format
                result = {
                    "prompt": prompt,
                    "response": response[0].request_pieces[0].original_value if response else "No response",
                    "timestamp": datetime.utcnow().isoformat(),
                    "conversation_id": conversation_id
                }
                results.append(result)
                
                logger.info(f"PyRIT orchestrator processed prompt: {prompt[:50]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"PyRIT orchestrator error: {e}")
            raise
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history from PyRIT memory"""
        if not self.is_available():
            return []
        
        try:
            # Query memory for conversation history
            # This would use PyRIT's memory querying capabilities
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

# Global PyRIT service instance
pyrit_service = PyRITService()