# custom_targets/apisix_ai_gateway.py

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from pyrit.models import PromptRequestPiece, PromptRequestResponse
from pyrit.models.prompt_request_response import construct_response_from_request
from pyrit.prompt_target import PromptChatTarget

# Import the TokenManager for APISIX integration
from utils.token_manager import TokenManager

# Configure logger
logger = logging.getLogger(__name__)


class APISIXAIGatewayTarget(PromptChatTarget):
    """
    A PyRIT PromptTarget that integrates with APISIX AI Gateway.
    This target uses the TokenManager to make authenticated calls to APISIX AI proxy endpoints.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = 1000,
        top_p: Optional[float] = 1.0,
        frequency_penalty: Optional[float] = 0.0,
        presence_penalty: Optional[float] = 0.0,
        seed: Optional[int] = None,
        max_requests_per_minute: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize APISIX AI Gateway target.

        Args:
            provider: AI provider (openai, anthropic, ollama, webui, gsai)
            model: Model name/identifier
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            seed: Random seed for reproducibility
            max_requests_per_minute: Rate limiting
        """
        # Initialize base class
        super().__init__(max_requests_per_minute=max_requests_per_minute)

        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.seed = seed

        # Initialize TokenManager for APISIX integration
        self.token_manager = TokenManager()

        # Verify provider and model are available
        self._verify_model_availability()

        logger.info(f"Initialized APISIX AI Gateway target for {provider}/{model}")

    def _verify_model_availability(self):
        """Verify that the specified provider and model are available through APISIX."""
        try:
            endpoints = self.token_manager.get_apisix_endpoints()
            if self.provider not in endpoints:
                available_providers = list(endpoints.keys())
                raise ValueError(
                    f"Provider '{self.provider}' not available. Available providers: {available_providers}"
                )

            provider_models = endpoints[self.provider]
            if self.model not in provider_models:
                available_models = list(provider_models.keys())
                raise ValueError(
                    f"Model '{self.model}' not available for provider '{self.provider}'. Available models: {available_models}"
                )

            logger.debug(f"Verified model availability: {self.provider}/{self.model}")

        except Exception as e:
            logger.error(f"Failed to verify model availability: {e}")
            raise

    def get_identifier(self) -> Dict[str, str]:
        """Return identifier for this target."""
        return {
            "type": "apisix_ai_gateway",
            "provider": self.provider,
            "model": self.model,
            "__typename__": "APISIXAIGatewayTarget",
        }

    def is_json_response_supported(self) -> bool:
        """
        Indicates whether this target supports JSON response format.

        APISIX AI Gateway supports JSON responses for OpenAI and Anthropic providers,
        but may not support it for Ollama or WebUI depending on the underlying model.

        Returns:
            bool: True if JSON response format is supported, False otherwise.
        """
        # OpenAI and Anthropic generally support JSON response format
        json_supported_providers = ["openai", "anthropic"]

        if not self.provider:
            return False

        return self.provider.lower() in json_supported_providers

    async def send_prompt_async(self, *, prompt_request: PromptRequestResponse) -> PromptRequestResponse:
        """
        Send a prompt to the APISIX AI Gateway and return the response.

        Args:
            prompt_request: The prompt request to send

        Returns:
            PromptRequestResponse with the AI response
        """
        # Debug logging for role consistency issue
        logger.debug(f"APISIX Gateway received prompt_request with {len(prompt_request.request_pieces)} pieces")
        for i, piece in enumerate(prompt_request.request_pieces):
            logger.debug(f"  Piece {i}: role='{piece.role}', conv_id='{piece.conversation_id}', seq={piece.sequence}")

        self._validate_request(prompt_request)

        try:
            # Get user token (for role checking, though we use API key auth)
            user_token = self.token_manager.extract_user_token()
            if not user_token:
                logger.warning("No user token available, proceeding with API key authentication only")

            # Convert PyRIT request to APISIX format
            messages = self._convert_request_to_messages(prompt_request)

            # Prepare parameters for APISIX call
            call_params = {}
            if self.temperature is not None:
                call_params["temperature"] = self.temperature

            # Anthropic requires max_tokens, ensure it's always provided
            if self.max_tokens is not None:
                call_params["max_tokens"] = self.max_tokens
            elif self.provider == "anthropic":
                call_params["max_tokens"] = 1000  # Default for Anthropic
                logger.debug("Using default max_tokens=1000 for Anthropic provider")

            if self.top_p is not None:
                call_params["top_p"] = self.top_p
            if self.frequency_penalty is not None:
                call_params["frequency_penalty"] = self.frequency_penalty
            if self.presence_penalty is not None:
                call_params["presence_penalty"] = self.presence_penalty
            if self.seed is not None:
                call_params["seed"] = self.seed

            # Make the call through TokenManager
            logger.debug(
                f"Calling APISIX AI endpoint: provider={self.provider}, model={self.model}, params={call_params}"
            )

            response_data = self.token_manager.call_ai_endpoint(
                token=user_token or "dummy_token",  # Use dummy token if no user token
                provider=self.provider,
                model=self.model,
                messages=messages,
                **call_params,
            )

            logger.debug(f"APISIX response received: {type(response_data)}, data={response_data}")

            if not response_data:
                error_msg = f"Failed to get response from APISIX AI Gateway for {self.provider}/{self.model}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Convert APISIX response back to PyRIT format
            return self._convert_response_to_pyrit(prompt_request, response_data)

        except Exception as e:
            logger.error(f"Error in APISIX AI Gateway call: {e}")
            # Return error response in PyRIT format
            return self._create_error_response(prompt_request, str(e))

    def _validate_request(self, prompt_request: PromptRequestResponse):
        """Validate the incoming prompt request."""
        if not prompt_request or not prompt_request.request_pieces:
            raise ValueError("Invalid prompt request: missing request pieces")

        # Check that we have at least one user message
        user_messages = [piece for piece in prompt_request.request_pieces if piece.role == "user"]
        if not user_messages:
            raise ValueError("Invalid prompt request: no user messages found")

    def _convert_request_to_messages(self, prompt_request: PromptRequestResponse) -> List[Dict[str, str]]:
        """Convert PyRIT request to APISIX messages format."""
        messages = []

        for piece in prompt_request.request_pieces:
            if piece.role in ["user", "assistant", "system"]:
                message = {"role": piece.role, "content": piece.converted_value or piece.original_value}
                messages.append(message)

        return messages

    def _convert_response_to_pyrit(
        self, original_request: PromptRequestResponse, response_data: Dict[str, Any]
    ) -> PromptRequestResponse:
        """Convert APISIX response to PyRIT format using proper PyRIT pattern."""
        try:
            # Extract content from different possible response formats
            content = ""

            # OpenAI format
            if "choices" in response_data:
                choices = response_data["choices"]
                if choices and len(choices) > 0:
                    choice = choices[0]
                    if "message" in choice:
                        content = choice["message"].get("content", "")
                    elif "text" in choice:
                        content = choice["text"]

            # Anthropic format
            elif "content" in response_data:
                if isinstance(response_data["content"], list):
                    for content_item in response_data["content"]:
                        if isinstance(content_item, dict) and content_item.get("type") == "text":
                            content = content_item.get("text", "")
                            break
                elif isinstance(response_data["content"], str):
                    content = response_data["content"]

            # Fallback - try to find any text content
            if not content:
                content = str(response_data.get("text", response_data.get("output", "No content in response")))

            # Get the first request piece to construct response from
            if not original_request.request_pieces:
                raise ValueError("No request pieces found in original request")

            request_piece = original_request.request_pieces[0]
            logger.debug(
                f"Creating response from request piece: role='{request_piece.role}', conv_id='{request_piece.conversation_id}'"
            )

            # Use PyRIT's proper helper function to create assistant response
            response = construct_response_from_request(
                request=request_piece,
                response_text_pieces=[content],  # List of response strings
                response_type="text",
                error="none",
            )

            logger.debug("Successfully created response using construct_response_from_request")
            return response

        except Exception as e:
            logger.error(f"Error converting APISIX response to PyRIT format: {e}")
            # For errors, create a simple error response using the helper
            if original_request.request_pieces:
                request_piece = original_request.request_pieces[0]
                return construct_response_from_request(
                    request=request_piece,
                    response_text_pieces=[f"Error: {e}"],
                    response_type="text",
                    error="processing",
                )
            else:
                # Fallback if no request pieces
                return self._create_simple_error_response(original_request, str(e))

    def _create_error_response(
        self, original_request: PromptRequestResponse, error_message: str
    ) -> PromptRequestResponse:
        """Create an error response in PyRIT format using proper pattern."""
        if original_request.request_pieces:
            request_piece = original_request.request_pieces[0]
            return construct_response_from_request(
                request=request_piece,
                response_text_pieces=[f"Error: {error_message}"],
                response_type="text",
                error="processing",
            )
        else:
            # Fallback if no request pieces
            return self._create_simple_error_response(original_request, error_message)

    def _create_simple_error_response(
        self, original_request: PromptRequestResponse, error_message: str
    ) -> PromptRequestResponse:
        """Create a simple error response that avoids role consistency issues."""
        conversation_id = str(uuid.uuid4())  # Use a fresh conversation ID

        # Create just a single user request and assistant error response
        user_piece = PromptRequestPiece(
            role="user",
            original_value="Error occurred during processing",
            converted_value="Error occurred during processing",
            conversation_id=conversation_id,
            sequence=0,
            prompt_target_identifier=self.get_identifier(),
            original_value_data_type="text",
            converted_value_data_type="text",
            response_error="none",
        )

        error_piece = PromptRequestPiece(
            role="assistant",
            original_value=f"Error: {error_message}",
            converted_value=f"Error: {error_message}",
            conversation_id=conversation_id,
            sequence=1,
            prompt_target_identifier=self.get_identifier(),
            original_value_data_type="text",
            converted_value_data_type="text",
            response_error="none",
        )

        return PromptRequestResponse(request_pieces=[user_piece, error_piece])
