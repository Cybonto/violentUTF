# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

# utils/token_manager.py
"""
Token management utilities for ViolentUTF Keycloak integration.

Handles JWT token extraction, validation, and APISIX endpoint access.
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import jwt
import requests
import streamlit as st

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages JWT tokens for APISIX AI Gateway access."""

    def __init__(self: "TokenManager") -> None:
        self._load_environment_variables()
        self.keycloak_config = self._load_keycloak_config()
        # Comprehensive fallback endpoints - updated to match setup script
        self.fallback_apisix_endpoints = {
            "openai": {
                "gpt-4": "/ai/openai/gpt4",
                "gpt-3.5-turbo": "/ai/openai/gpt35",
                "gpt-4-turbo": "/ai/openai/gpt4-turbo",
                "gpt-4o": "/ai/openai/gpt4o",
                "gpt-4o-mini": "/ai/openai/gpt4o-mini",
                "gpt-4.1": "/ai/openai/gpt41",
                "gpt-4.1-mini": "/ai/openai/gpt41-mini",
                "gpt-4.1-nano": "/ai/openai/gpt41-nano",
                "o1-preview": "/ai/openai/o1-preview",
                "o1-mini": "/ai/openai/o1-mini",
                "o3-mini": "/ai/openai/o3-mini",
                "o4-mini": "/ai/openai/o4-mini",
            },
            "anthropic": {
                "claude-3-opus-20240229": "/ai/anthropic/claude3-opus",
                "claude-3-sonnet-20240229": "/ai/anthropic/claude3-sonnet",
                "claude-3-haiku-20240307": "/ai/anthropic/claude3-haiku",
                "claude-3-5-sonnet-20241022": "/ai/anthropic/claude35-sonnet",
                "claude-3-5-haiku-20241022": "/ai/anthropic/claude35-haiku",
                "claude-3-7-sonnet-latest": "/ai/anthropic/sonnet37",
                "claude-sonnet-4-20250514": "/ai/anthropic/sonnet4",
                "claude-opus-4-20250514": "/ai/anthropic/opus4",
            },
            "ollama": {
                "llama2": "/ai/ollama/llama2",
                "codellama": "/ai/ollama/codellama",
                "mistral": "/ai/ollama/mistral",
                "llama3": "/ai/ollama/llama3",
            },
            "webui": {"llama2": "/ai/webui/llama2", "codellama": "/ai/webui/codellama"},
            "gsai": {
                "claude_3_5_sonnet": "/ai/gsai-api-1/chat/completions",
                "claude_3_7_sonnet": "/ai/gsai-api-1/chat/completions",
                "claude_3_haiku": "/ai/gsai-api-1/chat/completions",
                "llama3211b": "/ai/gsai-api-1/chat/completions",
                "cohere_english_v3": "/ai/gsai-api-1/chat/completions",
                "gemini-2.0-flash": "/ai/gsai-api-1/chat/completions",
                "gemini-2.0-flash-lite": "/ai/gsai-api-1/chat/completions",
                "gemini-2.5-pro-preview-05-06": "/ai/gsai-api-1/chat/completions",
            },
            "bedrock": {
                "claude-opus-4": "/ai/bedrock/claude-opus-4",
                "claude-sonnet-4": "/ai/bedrock/claude-sonnet-4",
                "claude-3-5-sonnet": "/ai/bedrock/claude-35-sonnet",
                "claude-3-5-haiku": "/ai/bedrock/claude-35-haiku",
                "llama3-3-70b": "/ai/bedrock/llama3-3-70b",
                "nova-pro": "/ai/bedrock/nova-pro",
                "nova-lite": "/ai/bedrock/nova-lite",
            },
        }

        # Dynamic endpoints cache
        self._dynamic_endpoints_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes cache TTL

        # Note: Bedrock endpoints are configured but not yet supported by APISIX ai-proxy plugin
        # Remove 'bedrock' from active endpoints until AWS SigV4 authentication is supported
        # Users can still access Bedrock via the standalone provider in Simple Chat
        self._remove_unsupported_providers()
        self.apisix_base_url = "http://localhost:9080"
        self.apisix_admin_url = "http://localhost:9180"
        self.apisix_admin_key = None  # Will be loaded dynamically

    def _load_environment_variables(self: "TokenManager") -> None:
        """Load APISIX-specific environment variables from .env file if it exists."""
        import os
        from pathlib import Path

        # Look for .env file in the violentutf directory
        env_file = Path(__file__).parent.parent / ".env"

        # Only load APISIX-specific variables to avoid interfering with Streamlit OAuth
        apisix_vars = [
            "KEYCLOAK_APISIX_CLIENT_ID",
            "KEYCLOAK_APISIX_CLIENT_SECRET",
            "KEYCLOAK_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_USERNAME",
            "KEYCLOAK_PASSWORD",
            "AI_PROXY_BASE_URL",
            "VIOLENTUTF_API_KEY",
        ]

        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            # Only load APISIX-specific variables and only if not already set
                            if key in apisix_vars and key not in os.environ:
                                os.environ[key] = value
                logger.debug(f"Loaded APISIX environment variables from {env_file}")
            except Exception as e:
                logger.warning(f"Could not load environment file {env_file}: {e}")
        else:
            logger.debug(f"Environment file {env_file} not found")

    def _load_keycloak_config(self: "TokenManager") -> Dict[str, Any]:
        """Load Keycloak configuration from Streamlit secrets and environment."""
        try:
            # Load main Keycloak config (for user authentication)
            keycloak_config = {
                "client_id": st.secrets["auth"]["keycloak"]["client_id"],
                "client_secret": st.secrets["auth"]["keycloak"]["client_secret"],
                "token_endpoint": st.secrets["auth"]["providers"]["keycloak"]["token_endpoint"],
                "userinfo_endpoint": st.secrets["auth"]["providers"]["keycloak"]["userinfo_endpoint"],
                "issuer": st.secrets["auth"]["providers"]["keycloak"]["issuer"],
            }

            # Load APISIX client config (for AI Gateway access)
            try:
                # Try to get APISIX credentials from secrets.toml first
                apisix_config = {
                    "apisix_client_id": st.secrets["apisix"]["client_id"],
                    "apisix_client_secret": st.secrets["apisix"]["client_secret"],
                }
                keycloak_config.update(apisix_config)
                logger.info("Loaded APISIX credentials from Streamlit secrets")
            except KeyError:
                # Fallback to environment variables
                import os

                apisix_client_id = os.getenv("KEYCLOAK_APISIX_CLIENT_ID", "apisix")
                apisix_client_secret = os.getenv("KEYCLOAK_APISIX_CLIENT_SECRET")

                if apisix_client_secret:
                    keycloak_config.update(
                        {"apisix_client_id": apisix_client_id, "apisix_client_secret": apisix_client_secret}
                    )
                    logger.info("Loaded APISIX credentials from environment variables")
                else:
                    logger.warning("APISIX client credentials not found in secrets or environment")

            return keycloak_config

        except KeyError as e:
            logger.error(f"Missing Keycloak configuration: {e}")
            return {}

    def extract_user_token(self: "TokenManager") -> Optional[str]:
        """
        Extract JWT token from Streamlit user session.
        Since Streamlit doesn't directly expose JWT tokens, we need to get a new one.
        """
        # Check if we have authentication in session state.
        if not st.session_state.get("access_token"):
            return None

        # Try to get token from session state first
        if "access_token" in st.session_state:
            token = st.session_state["access_token"]
            if self._is_token_valid(token):
                return token

        # If no valid token in session, try to get a fresh one
        return self._get_fresh_token()

    def _get_fresh_token(self: "TokenManager") -> Optional[str]:
        """Get a fresh token using direct Keycloak token endpoint."""
        try:
            # Get a real token from Keycloak using the APISIX client credentials
            # and the user's credentials that Streamlit already validated
            return self._get_token_from_keycloak()

        except Exception as e:
            logger.error(f"Error getting fresh token: {e}")
            return None

    def _get_token_from_keycloak(self: "TokenManager") -> Optional[str]:
        """
        Get a real JWT token from Keycloak using the user's session.
        """
        # Check if we have a user session.
        if not st.session_state.get("access_token"):
            logger.debug("No access token in session state")

        try:
            # Since user is authenticated via Keycloak SSO, get a token for API access
            # Use the configured user credentials from environment
            import os

            username = os.getenv("KEYCLOAK_USERNAME", "violentutf.web")
            if not username:
                logger.error("No username available for token request")
                return None

            # Use the configured credentials to get a token
            return self._request_token_for_user(username)

        except Exception as e:
            logger.error(f"Error getting token from Keycloak: {e}")
            return None

    def _request_token_for_user(self: "TokenManager", username: str) -> Optional[str]:
        """
        Request a token from Keycloak for the authenticated user.
        Since the user is already authenticated via Streamlit OAuth, we'll use
        the password grant with the configured user credentials.
        """
        import os

        import requests

        try:
            token_url = self.keycloak_config.get(
                "token_endpoint", "http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/token"
            )

            # Get APISIX client credentials from config
            apisix_client_id = self.keycloak_config.get("apisix_client_id", "apisix")
            apisix_client_secret = self.keycloak_config.get("apisix_client_secret")

            if not apisix_client_secret:
                logger.error("APISIX client secret not found in configuration")
                logger.debug(f"Available keycloak_config keys: {list(self.keycloak_config.keys())}")
                return None

            # Get user credentials from environment (set during setup)
            keycloak_username = os.getenv("KEYCLOAK_USERNAME", "").strip()
            keycloak_password = os.getenv("KEYCLOAK_PASSWORD", "")

            if not keycloak_username or not keycloak_password:
                logger.error("Keycloak user credentials not found in environment")
                logger.debug(
                    f"KEYCLOAK_USERNAME: '{keycloak_username}', KEYCLOAK_PASSWORD: {'***' if keycloak_password else 'EMPTY'}"
                )
                return None

            logger.info(
                f"Using APISIX client '{apisix_client_id}' and username '{keycloak_username}' for token request"
            )

            data = {
                "grant_type": "password",
                "client_id": apisix_client_id,
                "client_secret": apisix_client_secret,
                "username": keycloak_username,
                "password": keycloak_password,
                "scope": "openid profile email",
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = requests.post(token_url, data=data, headers=headers, timeout=10)

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")

                if access_token:
                    logger.info("Successfully obtained user access token from Keycloak")
                    # Verify the token has the required role
                    if self.has_ai_access(access_token):
                        logger.info("Token has ai-api-access role")
                        return access_token
                    else:
                        logger.warning("Token does not have ai-api-access role")
                        return access_token  # Still return it, role check will handle this
                else:
                    logger.error("No access token in Keycloak response")
                    return None
            else:
                logger.error(f"Failed to get token from Keycloak: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error requesting token from Keycloak: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error requesting token: {e}")
            return None

    def _is_token_valid(self: "TokenManager", token: str) -> bool:
        """Check if JWT token is valid and not expired."""
        try:
            # SECURITY FIX: Verify JWT signature properly
            secret_key = os.getenv("JWT_SECRET_KEY")
            if not secret_key:
                logger.error("JWT_SECRET_KEY not set - cannot verify token")
                return False

            # Properly verify the JWT signature and expiration
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            exp = payload.get("exp", 0)
            current_time = int(time.time())

            # Check if token expires in next 60 seconds (buffer for network calls)
            is_valid = exp > (current_time + 60)
            if is_valid:
                logger.debug("JWT token validation successful")
            else:
                logger.warning("JWT token is expired or expiring soon")
            return is_valid

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return False
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT signature verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False

    def get_user_roles(self: "TokenManager", token: str) -> list:
        """Extract user roles from JWT token."""
        try:
            # SECURITY FIX: Verify JWT signature properly
            secret_key = os.getenv("JWT_SECRET_KEY")
            if not secret_key:
                logger.error("JWT_SECRET_KEY not set - cannot verify token")
                return []

            # Properly verify the JWT signature
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])

            # Extract roles from the verified payload
            # ViolentUTF stores roles directly in the roles claim
            roles = payload.get("roles", [])

            # Also check Keycloak format if present
            if not roles:
                realm_access = payload.get("realm_access", {})
                roles = realm_access.get("roles", [])

            return roles

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired - cannot extract roles")
            return []
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT signature verification failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error extracting roles from token: {e}")
            return []

    def has_ai_access(self: "TokenManager", token: str) -> bool:
        """Check if user has ai-api-access role."""
        roles = self.get_user_roles(token)
        return "ai-api-access" in roles

    def _load_apisix_admin_key(self: "TokenManager") -> Optional[str]:
        """Load APISIX admin key from environment or config files."""
        import os
        from pathlib import Path

        # Try environment variable first
        admin_key = os.getenv("APISIX_ADMIN_KEY")
        if admin_key:
            return admin_key

        # Try to read from APISIX config file
        try:
            config_path = Path(__file__).parent.parent.parent / "apisix" / "conf" / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    content = f.read()
                    # Look for admin key in config - specifically under admin_key section
                    import re

                    # Find the admin_key section and extract the key value
                    admin_key_match = re.search(r"admin_key:\s*\n.*?key:\s*([A-Za-z0-9_-]+)", content, re.DOTALL)
                    if admin_key_match and admin_key_match.group(1) != "APISIX_ADMIN_KEY_PLACEHOLDER":
                        return admin_key_match.group(1)
        except Exception as e:
            logger.debug(f"Could not read APISIX config: {e}")

        # SECURITY: No hardcoded fallbacks allowed
        logger.error("APISIX_ADMIN_KEY environment variable not set and no fallback allowed for security")
        raise ValueError("APISIX_ADMIN_KEY environment variable must be set. No hardcoded fallbacks for security.")

    def _discover_apisix_routes(self: "TokenManager") -> Dict[str, Dict[str, str]]:
        """Dynamically discover available AI routes from APISIX Admin API."""
        if not self.apisix_admin_key:
            self.apisix_admin_key = self._load_apisix_admin_key()

        logger.info(f"Attempting dynamic discovery from APISIX Admin API: {self.apisix_admin_url}")
        logger.info(
            f"Using admin key: {self.apisix_admin_key[:8]}...{self.apisix_admin_key[-4:] if len(self.apisix_admin_key) > 12 else self.apisix_admin_key}"
        )

        try:
            # Query APISIX Admin API for all routes
            headers = {"X-API-KEY": self.apisix_admin_key, "Content-Type": "application/json"}

            response = requests.get(f"{self.apisix_admin_url}/apisix/admin/routes", headers=headers, timeout=10)

            logger.info(f"APISIX Admin API response: {response.status_code}")

            if response.status_code == 200:
                routes_data = response.json()
                logger.info(f"Received {len(routes_data.get('list', []))} routes from APISIX")
                discovered_endpoints = self._parse_ai_routes(routes_data)

                if discovered_endpoints:
                    logger.info(
                        f"Discovered {sum(len(models) for models in discovered_endpoints.values())} AI models from APISIX"
                    )
                    return discovered_endpoints
                else:
                    logger.warning("No AI routes found in APISIX configuration")
                    logger.debug(f"Raw routes data: {routes_data}")

            else:
                logger.warning(f"Failed to query APISIX routes: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error querying APISIX: {e}")
        except Exception as e:
            logger.warning(f"Error discovering APISIX routes: {e}")

        return {}

    def _parse_ai_routes(self: "TokenManager", routes_data: Dict) -> Dict[str, Dict[str, str]]:
        """Parse APISIX routes response to extract AI model endpoints."""
        endpoints = {"openai": {}, "anthropic": {}, "ollama": {}, "webui": {}, "bedrock": {}, "gsai": {}}

        try:
            routes_list = routes_data.get("list", [])

            for route_item in routes_list:
                route = route_item.get("value", {})
                route_id = route.get("id", "")
                uri = route.get("uri", "")
                plugins = route.get("plugins", {})

                # Check if this is an AI proxy route or GSAi proxy-rewrite route
                is_ai_proxy = "ai-proxy" in plugins
                is_gsai_proxy_rewrite = "proxy-rewrite" in plugins and "gsai" in uri

                if (is_ai_proxy or is_gsai_proxy_rewrite) and uri.startswith("/ai/"):
                    # Special handling for GSAi routes which use single endpoint for all models
                    if uri == "/ai/gsai-api-1/chat/completions" and route_id in [
                        "9001",
                        "gsai-static-chat-completions",
                        "gsai-api-1-chat-completions",
                    ]:
                        # Add all GSAi models to the same endpoint
                        for model in self.fallback_apisix_endpoints.get("gsai", {}).keys():
                            endpoints["gsai"][model] = uri
                    else:
                        # Standard provider/model extraction
                        provider, model_info = self._extract_provider_model(route_id, uri)
                        if provider and model_info:
                            model_name, endpoint_path = model_info
                            endpoints[provider][model_name] = endpoint_path

        except Exception as e:
            logger.error(f"Error parsing AI routes: {e}")

        # Remove empty providers
        return {k: v for k, v in endpoints.items() if v}

    def _extract_provider_model(self: "TokenManager", route_id: str, uri: str) -> tuple:
        """Extract provider and model information from route ID and URI."""
        try:
            # Parse URI pattern like /ai/openai/gpt4 or /ai/anthropic/sonnet
            parts = uri.strip("/").split("/")
            if len(parts) >= 3 and parts[0] == "ai":
                provider = parts[1]
                model_endpoint = parts[2]

                # Handle gsai-api-1 -> gsai mapping
                if provider.startswith("gsai-"):
                    provider = "gsai"

                # Map endpoint back to model name using route_id or known patterns
                model_name = self._map_endpoint_to_model(provider, model_endpoint, route_id)

                if model_name and provider in ["openai", "anthropic", "ollama", "webui", "bedrock", "gsai"]:
                    return provider, (model_name, uri)

        except Exception as e:
            logger.debug(f"Error extracting provider/model from route {route_id}: {e}")

        return None, None

    def _map_endpoint_to_model(self: "TokenManager", provider: str, endpoint: str, route_id: str) -> Optional[str]:
        """Map endpoint path to actual model name."""
        # Create reverse mapping from fallback endpoints.
        endpoint_to_model = {}
        for prov, models in self.fallback_apisix_endpoints.items():
            for model, path in models.items():
                path_key = path.split("/")[-1]  # Get last part like 'gpt4', 'sonnet'
                endpoint_to_model[f"{prov}:{path_key}"] = model

        # Try to find model by endpoint
        lookup_key = f"{provider}:{endpoint}"
        if lookup_key in endpoint_to_model:
            return endpoint_to_model[lookup_key]

        # Try to extract from route_id (e.g., 'openai-gpt-4' -> 'gpt-4')
        if route_id.startswith(f"{provider}-"):
            model_part = route_id[len(provider) + 1 :]
            # Convert back from route ID format (gpt-4 -> gpt-4)
            model_name = model_part.replace("-", ".")
            if model_name in [m for m in self.fallback_apisix_endpoints.get(provider, {}).keys()]:
                return model_name
            # Try without conversion
            if model_part in [m for m in self.fallback_apisix_endpoints.get(provider, {}).keys()]:
                return model_part

        # Fallback: use endpoint as model name
        return endpoint

    def get_apisix_endpoints(self: "TokenManager") -> Dict[str, Dict[str, str]]:
        """Get all available APISIX AI endpoints with dynamic discovery and fallback."""
        import time

        current_time = time.time()

        # Check cache first
        if self._dynamic_endpoints_cache and current_time - self._cache_timestamp < self._cache_ttl:
            return self._dynamic_endpoints_cache

        # Try dynamic discovery
        dynamic_endpoints = self._discover_apisix_routes()

        if dynamic_endpoints:
            # Use discovered endpoints
            self._dynamic_endpoints_cache = dynamic_endpoints
            self._cache_timestamp = current_time
            logger.info("Using dynamically discovered APISIX endpoints")
            return dynamic_endpoints
        else:
            # Fallback to static configuration
            logger.info("Using fallback APISIX endpoints configuration")
            return self.fallback_apisix_endpoints

    def get_endpoint_url(self: "TokenManager", provider: str, model: str) -> Optional[str]:
        """Get full URL for a specific provider/model endpoint."""
        endpoints = self.get_apisix_endpoints()
        endpoint_path = endpoints.get(provider, {}).get(model)
        if endpoint_path:
            return f"{self.apisix_base_url}{endpoint_path}"
        return None

    def get_model_display_name(self: "TokenManager", provider: str, model: str) -> str:
        """Get user-friendly display name for a model."""
        display_names = {
            "openai": {
                "gpt-4": "GPT-4",
                "gpt-3.5-turbo": "GPT-3.5 Turbo",
                "gpt-4-turbo": "GPT-4 Turbo",
                "gpt-4o": "GPT-4o",
                "gpt-4o-mini": "GPT-4o Mini",
                "gpt-4.1": "GPT-4.1",
                "gpt-4.1-mini": "GPT-4.1 Mini",
                "gpt-4.1-nano": "GPT-4.1 Nano",
                "o1-preview": "o1 Preview",
                "o1-mini": "o1 Mini",
                "o3-mini": "o3 Mini",
                "o4-mini": "o4 Mini",
            },
            "anthropic": {
                "claude-3-opus-20240229": "Claude 3 Opus",
                "claude-3-sonnet-20240229": "Claude 3 Sonnet",
                "claude-3-haiku-20240307": "Claude 3 Haiku",
                "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
                "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
                "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet",
                "claude-sonnet-4-20250514": "Claude Sonnet 4",
                "claude-opus-4-20250514": "Claude Opus 4",
            },
            "ollama": {"llama2": "Llama 2", "codellama": "Code Llama", "mistral": "Mistral", "llama3": "Llama 3"},
            "webui": {"llama2": "Llama 2 (WebUI)", "codellama": "Code Llama (WebUI)"},
            "gsai": {
                "claude_3_5_sonnet": "Claude 3.5 Sonnet",
                "claude_3_7_sonnet": "Claude 3.7 Sonnet",
                "claude_3_haiku": "Claude 3 Haiku",
                "llama3211b": "Llama 3.2 11B",
                "cohere_english_v3": "Cohere English v3",
                "gemini-2.0-flash": "Gemini 2.0 Flash",
                "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
                "gemini-2.5-pro-preview-05-06": "Gemini 2.5 Pro Preview",
            },
            "bedrock": {
                "claude-opus-4": "Claude Opus 4",
                "claude-sonnet-4": "Claude Sonnet 4",
                "claude-3-5-sonnet": "Claude 3.5 Sonnet",
                "claude-3-5-haiku": "Claude 3.5 Haiku",
                "llama3-3-70b": "Llama 3.3 70B",
                "nova-pro": "Amazon Nova Pro",
                "nova-lite": "Amazon Nova Lite",
            },
        }

        return display_names.get(provider, {}).get(model, model)

    def refresh_endpoints_cache(self: "TokenManager") -> bool:
        """Force refresh of the endpoints cache."""
        self._dynamic_endpoints_cache = None
        self._cache_timestamp = 0
        endpoints = self.get_apisix_endpoints()
        return len(endpoints) > 0

    def _remove_unsupported_providers(self: "TokenManager") -> None:
        """Remove providers not yet supported by APISIX ai-proxy plugin."""
        # Remove Bedrock until APISIX adds AWS SigV4 authentication support.
        if "bedrock" in self.fallback_apisix_endpoints:
            logger.info(
                "Bedrock endpoints configured but not active - APISIX ai-proxy plugin does not support AWS SigV4 auth"
            )
            # Don't remove, keep for future use when support is added
            # del self.fallback_apisix_endpoints['bedrock']

    def get_discovery_debug_info(self: "TokenManager") -> Dict[str, Any]:
        """Get debug information about dynamic discovery."""
        import os

        return {
            "apisix_admin_url": self.apisix_admin_url,
            "apisix_admin_key_source": "env" if os.getenv("APISIX_ADMIN_KEY") else "config_file",
            "apisix_admin_key_preview": (
                f"{self.apisix_admin_key[:8]}...{self.apisix_admin_key[-4:]}" if self.apisix_admin_key else "None"
            ),
            "cache_exists": self._dynamic_endpoints_cache is not None,
            "cache_timestamp": self._cache_timestamp,
            "fallback_model_count": sum(len(models) for models in self.fallback_apisix_endpoints.values()),
        }

    def call_ai_endpoint(
        self: "TokenManager", token: str, provider: str, model: str, messages: list, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated call to APISIX AI endpoint.

        Args:
            token: JWT bearer token (for role checking) - not used for API calls
            provider: AI provider (openai, anthropic, ollama, webui)
            model: Model name/identifier
            messages: Chat messages array
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            API response or None if error
        """
        # Note: Using API key authentication instead of JWT for APISIX.
        endpoint_url = self.get_endpoint_url(provider, model)
        if not endpoint_url:
            logger.error(f"No endpoint found for provider '{provider}' and model '{model}'")
            return None

        # Setup authentication and payload
        headers = self._setup_apisix_headers()
        payload = self._prepare_payload(provider, model, messages, **kwargs)

        # Execute with retry logic
        return self._execute_request_with_retry(endpoint_url, headers, payload)

    def _setup_apisix_headers(self: "TokenManager") -> Dict[str, str]:
        """Setup APISIX authentication headers."""
        import os

        api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")

        if not api_key:
            logger.error(
                "No APISIX API key found in environment variables (VIOLENTUTF_API_KEY, APISIX_API_KEY, AI_GATEWAY_API_KEY)"
            )
            raise ValueError(
                "APISIX API key must be set in environment variables. No hardcoded fallbacks for security."
            )
        else:
            logger.info(f"Using generated API key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else api_key}")

        return {"apikey": api_key, "Content-Type": "application/json"}

    def _prepare_payload(self: "TokenManager", provider: str, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """Prepare request payload with model-specific filtering."""
        payload = {"model": model, "messages": messages}

        # Filter parameters based on model type
        if provider == "openai" and any(reasoning_model in model for reasoning_model in ["o1-", "o3-", "o4-"]):
            # OpenAI reasoning models (o1, o3, o4) have restrictions
            logger.info(f"Using OpenAI reasoning model {model} - filtering incompatible parameters")
            # Only allow specific parameters for reasoning models
            allowed_params = ["max_completion_tokens"]  # No temperature, top_p, etc
            for key, value in kwargs.items():
                if key in allowed_params:
                    payload[key] = value
                elif key == "max_tokens":
                    # Convert max_tokens to max_completion_tokens for o1 models
                    payload["max_completion_tokens"] = value
                # Skip other parameters that cause errors
        else:
            # Regular models - use all provided parameters
            payload.update(kwargs)

        return payload

    def _execute_request_with_retry(
        self: "TokenManager", endpoint_url: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute HTTP request with retry logic."""
        import time

        max_retries = 3
        retry_delay = 1  # Start with 1 second delay

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{max_retries} after {retry_delay}s delay")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

                logger.info(f"Calling APISIX endpoint: {endpoint_url}")
                response = requests.post(endpoint_url, headers=headers, json=payload, timeout=45)

                # Handle response based on status code
                result = self._handle_response(response, attempt, max_retries)
                if result != "retry":
                    return result

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error calling APISIX endpoint: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying due to network error...")
                    continue
                return None

        return None

    def _handle_response(self: "TokenManager", response, attempt: int, max_retries: int) -> Any:
        """Handle HTTP response based on status code."""
        if response.status_code == 200:
            logger.info("Successfully received response from APISIX")
            return response.json()
        elif response.status_code == 401:
            logger.error("Authentication failed - API key may be invalid")
            return None
        elif response.status_code == 403:
            logger.error("Access forbidden - check API key permissions")
            return None
        elif response.status_code == 429:
            logger.warning(f"Rate limit hit (429). Attempt {attempt + 1}/{max_retries + 1}")
            if attempt < max_retries:
                return "retry"  # Signal to retry
            else:
                logger.error("Max retries exceeded for rate limiting")
                return None
        else:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
            return None


# Global instance
token_manager = TokenManager()
