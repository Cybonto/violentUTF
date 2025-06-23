app_version = "0.1"
app_title = "IronUTF"
app_description = "Defense Module"
app_icon = "🛡️"

import streamlit as st
import requests
import json
import os
from typing import Dict, List, Optional, Any
import logging
from utils.jwt_manager import jwt_manager
from utils.auth_utils import handle_authentication_and_sidebar

# Load environment variables from .env file
from dotenv import load_dotenv
import pathlib

# Get the path to the .env file relative to this script
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="IronUTF - Defense Module",
    page_icon="🛡️",
    layout="wide"
)

# ViolentUTF API configuration  
VIOLENTUTF_API_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")

# Fix URL if it has trailing /api
if VIOLENTUTF_API_URL.endswith('/api'):
    VIOLENTUTF_API_URL = VIOLENTUTF_API_URL[:-4]  # Remove /api


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        from utils.jwt_manager import jwt_manager
        
        # Use jwt_manager for automatic token refresh
        token = jwt_manager.get_valid_token()
        
        # Fallback token creation if needed
        if not token and st.session_state.get('access_token'):
            token = create_compatible_api_token()
        
        if not token:
            return {}
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX"
        }
        
        # Add APISIX API key for AI model access
        apisix_api_key = (
            os.getenv("VIOLENTUTF_API_KEY") or 
            os.getenv("APISIX_API_KEY") or
            os.getenv("AI_GATEWAY_API_KEY")
        )
        if apisix_api_key:
            headers["apikey"] = apisix_api_key
        
        return headers
    except Exception as e:
        logger.error(f"Failed to get auth headers: {e}")
        return {}

def create_compatible_api_token():
    """Create a FastAPI-compatible token using JWT manager - NEVER implement manually"""
    try:
        from utils.jwt_manager import jwt_manager
        
        # Check for Keycloak token first
        keycloak_token = st.session_state.get('access_token')
        
        if keycloak_token:
            logger.info("Using existing Keycloak token for API token creation")
            # Use secure user data without decoding Keycloak token directly
            decoded = {
                "preferred_username": "keycloak_user", 
                "email": "user@keycloak.local",
                "roles": ["ai-api-access", "admin", "apisix-admin"]  # Include admin roles for IronUTF
            }
            api_token = jwt_manager.create_token(decoded)
        else:
            # Fallback to environment credentials with admin privileges
            logger.info("No Keycloak token found, creating token with environment credentials")
            mock_keycloak_data = {
                "preferred_username": os.getenv('KEYCLOAK_USERNAME', 'violentutf.web'),
                "email": "violentutf@example.com",
                "name": "ViolentUTF Admin",
                "sub": "violentutf-admin",
                "roles": ["ai-api-access", "admin", "apisix-admin"]  # Admin roles for IronUTF
            }
            api_token = jwt_manager.create_token(mock_keycloak_data)
        
        if api_token:
            logger.info("Successfully created admin API token for IronUTF using JWT manager")
            return api_token
        else:
            st.error("🚨 Security Error: JWT secret key not configured. Please set JWT_SECRET_KEY environment variable.")
            logger.error("Failed to create API token - JWT secret key not available")
            return None
        
    except Exception as e:
        st.error(f"❌ Failed to generate API token. Please try refreshing the page.")
        logger.error(f"Token creation failed: {e}")
        return None

class APISIXAdmin:
    """Class to interact with APISIX Admin through ViolentUTF API"""
    
    def __init__(self):
        self.api_url = f"{VIOLENTUTF_API_URL}/api/v1/apisix-admin"
        self.headers = get_auth_headers()
    
    def get_all_routes(self) -> Optional[Dict]:
        """Get all AI routes from APISIX through API"""
        try:
            response = requests.get(
                f"{self.api_url}/routes",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get routes: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting routes: {e}")
            return None
    
    def get_route(self, route_id: str) -> Optional[Dict]:
        """Get specific route configuration through API"""
        try:
            response = requests.get(
                f"{self.api_url}/routes/{route_id}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get route {route_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting route {route_id}: {e}")
            return None
    
    def update_route_plugins(self, route_id: str, route_config: Dict) -> tuple[bool, str]:
        """Update route configuration with new plugins through API"""
        try:
            response = requests.put(
                f"{self.api_url}/routes/{route_id}/plugins",
                headers=self.headers,
                json=route_config,
                timeout=10
            )
            if response.status_code in [200, 201]:
                return True, "Success"
            else:
                error_msg = f"Failed to update route {route_id}: {response.status_code}"
                try:
                    error_detail = response.json().get('detail', response.text)
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"
                logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"Error updating route {route_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

def render_ai_prompt_guard_config(current_config: Dict, route_id: str) -> Dict:
    """Render UI for ai-prompt-guard plugin configuration"""
    #st.subheader("🛡️ AI Prompt Guard Configuration")
    
    with st.expander("ℹ️ About AI Prompt Guard", expanded=False):
        st.markdown("""
        The **ai-prompt-guard** plugin helps protect your AI models from harmful or inappropriate prompts by:
        - Blocking prompts containing specific patterns or keywords
        - Allowing only prompts that match certain criteria
        - Customizing error messages for blocked requests
        
        [📚 Official Documentation](https://apisix.apache.org/docs/apisix/plugins/ai-prompt-guard/)
        """)
    
    config = current_config.get("ai-prompt-guard", {})
    
    # Initialize session state only if not already initialized for this route
    deny_patterns_key = f"deny_patterns_{route_id}"
    allow_patterns_key = f"allow_patterns_{route_id}"
    deny_message_key = f"deny_message_{route_id}"
    case_insensitive_key = f"case_insensitive_{route_id}"
    
    if deny_patterns_key not in st.session_state:
        if "deny_patterns" in config and config["deny_patterns"]:
            st.session_state[deny_patterns_key] = "\n".join(config["deny_patterns"])
        else:
            st.session_state[deny_patterns_key] = ""
    
    if allow_patterns_key not in st.session_state:
        if "allow_patterns" in config and config["allow_patterns"]:
            st.session_state[allow_patterns_key] = "\n".join(config["allow_patterns"])
        else:
            st.session_state[allow_patterns_key] = ""
    
    if deny_message_key not in st.session_state:
        if "deny_message" in config:
            st.session_state[deny_message_key] = config["deny_message"]
        else:
            st.session_state[deny_message_key] = "Your request has been blocked due to policy violations."
    
    if case_insensitive_key not in st.session_state:
        if "case_insensitive" in config:
            st.session_state[case_insensitive_key] = config["case_insensitive"]
        else:
            st.session_state[case_insensitive_key] = True
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Deny Patterns")
        st.caption("Prompts containing these patterns will be blocked")
        
        new_deny_patterns = st.text_area(
            "Enter patterns (one per line)",
            height=150,
            key=f"deny_patterns_{route_id}",
            help="Regular expressions or keywords to block"
        )
        
        # Deny message
        deny_message = st.text_input(
            "Custom deny message",
            key=f"deny_message_{route_id}",
            help="Message shown when a prompt is blocked"
        )
    
    with col2:
        st.markdown("### Allow Patterns")
        st.caption("Only prompts matching these patterns will be allowed (if specified)")
        
        new_allow_patterns = st.text_area(
            "Enter patterns (one per line)",
            height=150,
            key=f"allow_patterns_{route_id}",
            help="If specified, only prompts matching these patterns are allowed"
        )
        
        # Case sensitivity
        case_insensitive = st.checkbox(
            "Case insensitive matching",
            key=f"case_insensitive_{route_id}",
            help="Apply pattern matching without case sensitivity"
        )
    
    # Build new configuration
    new_config = {}
    
    if new_deny_patterns.strip():
        new_config["deny_patterns"] = [p.strip() for p in new_deny_patterns.strip().split("\n") if p.strip()]
    
    if new_allow_patterns.strip():
        new_config["allow_patterns"] = [p.strip() for p in new_allow_patterns.strip().split("\n") if p.strip()]
    
    if deny_message:
        new_config["deny_message"] = deny_message
    
    new_config["case_insensitive"] = case_insensitive
    
    return new_config

def test_plugin_configuration(route_id: str, provider: str, model: str, plugins: Dict) -> Dict:
    """Test plugin configuration with a simple prompt."""
    import requests
    
    try:
        # Get API key
        api_key = (
            os.getenv("VIOLENTUTF_API_KEY") or 
            os.getenv("APISIX_API_KEY") or
            os.getenv("AI_GATEWAY_API_KEY")
        )
        
        if not api_key:
            return {
                "success": False,
                "error": "No API key found",
                "suggestion": "Please ensure VIOLENTUTF_API_KEY is set in your .env file"
            }
        
        # Determine endpoint based on route
        base_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
        if base_url.endswith('/api'):
            base_url = base_url[:-4]
        
        # Extract endpoint from route_id
        if "openai" in route_id:
            endpoint = f"{base_url}/ai/openai/{model}"
        elif "anthropic" in route_id:
            endpoint = f"{base_url}/ai/anthropic/{model}"
        elif "ollama" in route_id:
            endpoint = f"{base_url}/ai/ollama/{model}"
        elif "webui" in route_id:
            endpoint = f"{base_url}/ai/webui/{model}"
        else:
            endpoint = f"{base_url}/ai/{provider}/{model}"
        
        # Test prompt
        test_prompt = "Hello, please respond with 'Test successful' if you receive this message."
        
        # Prepare request
        headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messages': [
                {'role': 'user', 'content': test_prompt}
            ],
            'max_tokens': 50,
            'temperature': 0
        }
        
        # Make test request
        response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract response based on format
            response_text = ""
            if 'choices' in data:
                response_text = data['choices'][0]['message']['content']
            elif 'content' in data and isinstance(data['content'], list):
                if data['content'] and 'text' in data['content'][0]:
                    response_text = data['content'][0]['text']
            elif 'content' in data and isinstance(data['content'], str):
                response_text = data['content']
            
            return {
                "success": True,
                "test_prompt": test_prompt,
                "response": response_text,
                "filtered": False
            }
        elif response.status_code == 400:
            # Check if it's a plugin-related error
            error_text = response.text
            if "system" in error_text and "anthropic" in route_id.lower():
                return {
                    "success": False,
                    "error": "System role not supported by Anthropic",
                    "suggestion": "Use 'user' or 'assistant' roles instead of 'system' for Anthropic routes"
                }
            elif "prohibited content" in error_text.lower():
                return {
                    "success": True,
                    "test_prompt": test_prompt,
                    "response": "Blocked by prompt guard",
                    "filtered": True,
                    "filter_reason": "Content matched deny patterns"
                }
            else:
                return {
                    "success": False,
                    "error": f"Bad request: {error_text}"
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def detect_provider_type(route_config: Dict) -> str:
    """Detect the AI provider type from route configuration."""
    plugins = route_config.get("plugins", {})
    ai_proxy = plugins.get("ai-proxy", {})
    
    provider = ai_proxy.get("provider", "")
    override = ai_proxy.get("override", {})
    endpoint = override.get("endpoint", "")
    
    # Direct provider detection
    if provider == "openai":
        return "openai"
    elif provider == "openai-compatible":
        # Check endpoint to determine actual provider
        if "anthropic.com" in endpoint:
            return "anthropic"
        elif "localhost" in endpoint or "host.docker.internal" in endpoint:
            if "ollama" in endpoint:
                return "ollama"
            else:
                return "webui"
    
    return "unknown"

def handle_prepend_role_change():
    """Handle prepend role changes - restore original content when switching back."""
    # Find the route_id from session state keys
    for key in st.session_state:
        if key.startswith("prepend_role_") and "_last_" not in key and "_original_" not in key:
            route_id = key.replace("prepend_role_", "")
            content_key = f"prepend_content_{route_id}"
            
            # Get current, previous, and original roles
            current_role = st.session_state.get(key)
            last_role_key = f"_last_prepend_role_{route_id}"
            last_role = st.session_state.get(last_role_key)
            original_role = st.session_state.get(f"_original_prepend_role_{route_id}")
            original_content = st.session_state.get(f"_original_prepend_content_{route_id}", "")
            
            # If role actually changed
            if last_role and current_role != last_role:
                if current_role == original_role:
                    # Restore original content when switching back to original role
                    st.session_state[content_key] = original_content
                else:
                    # Clear content when switching to a different role
                    st.session_state[content_key] = ""
            
            # Update last role
            st.session_state[last_role_key] = current_role
            break

def handle_append_role_change():
    """Handle append role changes - restore original content when switching back."""
    # Find the route_id from session state keys
    for key in st.session_state:
        if key.startswith("append_role_") and "_last_" not in key and "_original_" not in key:
            route_id = key.replace("append_role_", "")
            content_key = f"append_content_{route_id}"
            
            # Get current, previous, and original roles
            current_role = st.session_state.get(key)
            last_role_key = f"_last_append_role_{route_id}"
            last_role = st.session_state.get(last_role_key)
            original_role = st.session_state.get(f"_original_append_role_{route_id}")
            original_content = st.session_state.get(f"_original_append_content_{route_id}", "")
            
            # If role actually changed
            if last_role and current_role != last_role:
                if current_role == original_role:
                    # Restore original content when switching back to original role
                    st.session_state[content_key] = original_content
                else:
                    # Clear content when switching to a different role
                    st.session_state[content_key] = ""
            
            # Update last role
            st.session_state[last_role_key] = current_role
            break

def render_ai_prompt_decorator_config(current_config: Dict, route_config: Dict, route_id: str) -> Dict:
    """Render UI for ai-prompt-decorator plugin configuration"""
    #st.subheader("🎨 AI Prompt Decorator Configuration")
    
    # Detect provider type
    provider_type = detect_provider_type(route_config)
    
    # Show provider-specific warnings
    if provider_type == "anthropic":
        st.warning("""
        ⚠️ **Anthropic API Limitation**: System messages cannot be added to the messages array.
        Only 'user' and 'assistant' roles are supported for prepend/append operations.
        To add system-like instructions, use the 'user' role with clear directives.
        """)
    
    with st.expander("ℹ️ About AI Prompt Decorator", expanded=False):
        st.markdown("""
        The **ai-prompt-decorator** plugin allows you to modify prompts before they reach the AI model by:
        - Adding messages before the user prompt (prepend)
        - Adding messages after the user prompt (append)
        - Injecting system prompts or context
        
        Messages are added as chat conversation entries with specified roles (system, user, assistant).
        
        [📚 Official Documentation](https://apisix.apache.org/docs/apisix/plugins/ai-prompt-decorator/)
        """)
    
    # Show detected provider
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f"🤖 Detected Provider: **{provider_type.title()}**")
    
    config = current_config.get("ai-prompt-decorator", {})
    
    # Extract existing prepend/append messages
    prepend_messages = config.get("prepend", [])
    append_messages = config.get("append", [])
    
    # Determine available roles based on provider first
    if provider_type == "anthropic":
        available_roles = ["user", "assistant"]
        default_role = "user"
    else:
        available_roles = ["system", "user", "assistant"]
        default_role = "user"
    
    # Initialize session state keys
    prepend_content_key = f"prepend_content_{route_id}"
    prepend_role_key = f"prepend_role_{route_id}"
    append_content_key = f"append_content_{route_id}"
    append_role_key = f"append_role_{route_id}"
    
    # Track original configuration for change detection
    original_prepend_role_key = f"_original_prepend_role_{route_id}"
    original_append_role_key = f"_original_append_role_{route_id}"
    original_prepend_content_key = f"_original_prepend_content_{route_id}"
    original_append_content_key = f"_original_append_content_{route_id}"
    
    # Only initialize session state if keys don't exist (first time viewing this route)
    if prepend_content_key not in st.session_state:
        if prepend_messages and len(prepend_messages) > 0:
            prepend_content = prepend_messages[0].get("content", "")
            prepend_role = prepend_messages[0].get("role", default_role)
            # Ensure role is valid for current provider
            if prepend_role not in available_roles:
                prepend_role = default_role
            st.session_state[prepend_content_key] = prepend_content
            st.session_state[prepend_role_key] = prepend_role
            # Store original values
            st.session_state[original_prepend_role_key] = prepend_role
            st.session_state[original_prepend_content_key] = prepend_content
        else:
            st.session_state[prepend_content_key] = ""
            st.session_state[prepend_role_key] = default_role
            st.session_state[original_prepend_role_key] = None
            st.session_state[original_prepend_content_key] = ""
    
    if append_content_key not in st.session_state:
        if append_messages and len(append_messages) > 0:
            append_content = append_messages[0].get("content", "")
            append_role = append_messages[0].get("role", default_role)
            # Ensure role is valid for current provider
            if append_role not in available_roles:
                append_role = default_role
            st.session_state[append_content_key] = append_content
            st.session_state[append_role_key] = append_role
            # Store original values
            st.session_state[original_append_role_key] = append_role
            st.session_state[original_append_content_key] = append_content
        else:
            st.session_state[append_content_key] = ""
            st.session_state[append_role_key] = default_role
            st.session_state[original_append_role_key] = None
            st.session_state[original_append_content_key] = ""
    
    # Prepend configuration
    st.markdown("### Prepend Messages")
    st.caption("Messages to add before the user's prompt")
    
    # Role help text
    if provider_type == "anthropic":
        role_help = "For Anthropic, only 'user' and 'assistant' roles are supported"
    else:
        role_help = "The role of the message to prepend"
    
    # Initialize last role if not exists
    last_prepend_role_key = f"_last_prepend_role_{route_id}"
    if last_prepend_role_key not in st.session_state:
        st.session_state[last_prepend_role_key] = st.session_state.get(f"prepend_role_{route_id}", default_role)
    
    # Show role selection with session state value
    prepend_role_key = f"prepend_role_{route_id}"
    prepend_role = st.selectbox(
        "Role for prepend message",
        available_roles,
        key=prepend_role_key,
        help=role_help,
        on_change=handle_prepend_role_change
    )
    
    prepend_content_key = f"prepend_content_{route_id}"
    prepend_text = st.text_area(
        "Content to prepend",
        height=100,
        key=prepend_content_key,
        help="This message will be added before the user's prompt"
    )
    
    st.markdown("---")
    
    # Append configuration
    st.markdown("### Append Messages")
    st.caption("Messages to add after the user's prompt")
    
    # Initialize last role if not exists
    last_append_role_key = f"_last_append_role_{route_id}"
    if last_append_role_key not in st.session_state:
        st.session_state[last_append_role_key] = st.session_state.get(f"append_role_{route_id}", default_role)
    
    # Show role selection with session state value
    append_role_key = f"append_role_{route_id}"
    append_role = st.selectbox(
        "Role for append message",
        available_roles,
        key=append_role_key,
        help=role_help,
        on_change=handle_append_role_change
    )
    
    append_content_key = f"append_content_{route_id}"
    append_text = st.text_area(
        "Content to append",
        height=100,
        key=append_content_key,
        help="This message will be added after the user's prompt"
    )
    
    # Build new configuration using the correct schema
    new_config = {}
    
    # Add prepend messages if provided
    if prepend_text and prepend_text.strip():
        new_config["prepend"] = [{
            "role": prepend_role,
            "content": prepend_text.strip()
        }]
    
    # Add append messages if provided
    if append_text and append_text.strip():
        new_config["append"] = [{
            "role": append_role,
            "content": append_text.strip()
        }]
    
    # If no configuration is provided, return empty dict
    return new_config


def main():
    """Main function for IronUTF page"""
    # Handle authentication
    handle_authentication_and_sidebar("IronUTF - Defense Module")
    
    # Check authentication
    has_keycloak_token = bool(st.session_state.get('access_token'))
    has_env_credentials = bool(os.getenv('KEYCLOAK_USERNAME'))
    
    if not has_keycloak_token and not has_env_credentials:
        st.warning("⚠️ Authentication required: Please log in via Keycloak SSO or configure KEYCLOAK_USERNAME in environment.")
        st.info("💡 For local development, you can set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD in your .env file")
        return
    
    # For IronUTF, always create a fresh admin token
    with st.spinner("Generating admin API token for IronUTF..."):
        # Clear any existing token to force recreation with admin privileges
        if 'api_token' in st.session_state:
            del st.session_state['api_token']
        
        api_token = create_compatible_api_token()
        if not api_token:
            st.error("❌ Failed to generate API token. Please try refreshing the page.")
            return
        st.session_state['api_token'] = api_token
    
    
    # Page header
    st.title("🛡️ IronUTF - Defense Module")
    st.markdown("""
    Customize prompt filtering and decoration for your AI endpoints.
    """)
    
    # Initialize APISIX admin client
    apisix_admin = APISIXAdmin()
    
    # Get all routes
    with st.spinner("Loading APISIX routes..."):
        routes_response = apisix_admin.get_all_routes()
    
    if not routes_response:
        st.error("❌ Failed to load APISIX routes. Please check your connection and credentials.")
        return
    
    # Extract AI routes (already filtered by API)
    ai_routes = routes_response.get("list", [])
    
    if not ai_routes:
        st.warning("⚠️ No AI routes found. Please configure AI routes first using the setup scripts.")
        return
    
    # Route selection with provider filter
    # st.markdown("### Select AI Route to Configure")
    
    # Provider filter
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Get unique providers from routes
        all_providers = set()
        for route in ai_routes:
            route_value = route.get("value", {})
            provider_type = detect_provider_type(route_value)
            all_providers.add(provider_type.title())
        
        # Add "All" option
        provider_options = ["All"] + sorted(list(all_providers))
        selected_provider_filter = st.selectbox(
            "Filter by Provider",
            options=provider_options,
            help="Filter routes by AI provider"
        )
    
    with col2:
        # Create filtered route options
        route_options = {}
        for route in ai_routes:
            route_value = route.get("value", {})
            provider_type = detect_provider_type(route_value)
            
            # Apply filter
            if selected_provider_filter != "All" and provider_type.title() != selected_provider_filter:
                continue
            
            route_id = route.get("key", "").split("/")[-1]
            route_uri = route_value.get("uri", "Unknown")
            route_name = route_value.get("name", f"Route {route_id}")
            
            # Include provider in display name
            display_name = f"[{provider_type.upper()}] {route_name} ({route_uri})"
            route_options[display_name] = route
        
        # Check if we have a previously selected route in session state
        if 'selected_route_name' not in st.session_state:
            st.session_state.selected_route_name = None
        
        # Get current selection
        current_selection = st.session_state.selected_route_name
        if current_selection and current_selection not in route_options:
            # If filtered out, reset selection
            current_selection = None
        
        selected_route_name = st.selectbox(
            "Choose an AI route",
            options=list(route_options.keys()),
            index=list(route_options.keys()).index(current_selection) if current_selection and current_selection in route_options else 0,
            key="route_selector",
            help="Select the AI route you want to configure plugins for"
        )
        
        # Update session state and clear form fields when route changes
        if st.session_state.selected_route_name != selected_route_name:
            # Clear all form fields for the previous route to avoid state pollution
            if st.session_state.selected_route_name:
                old_route = route_options.get(st.session_state.selected_route_name, {})
                old_route_id = old_route.get("key", "").split("/")[-1]
                
                # Clear old route's form fields
                for key in list(st.session_state.keys()):
                    if key.endswith(f"_{old_route_id}"):
                        del st.session_state[key]
            
            st.session_state.selected_route_name = selected_route_name
            # Mark that we need to initialize this route's state
            st.session_state[f"route_initialized_{selected_route_name}"] = False
    
    if selected_route_name:
        selected_route = route_options[selected_route_name]
        route_id = selected_route.get("key", "").split("/")[-1]
        
        # Fetch current route configuration to ensure we have the latest state
        with st.spinner("Loading route configuration..."):
            current_route_data = apisix_admin.get_route(route_id)
            
        if current_route_data:
            # Use the fresh data
            route_value = current_route_data.get("value", selected_route.get("value", {}))
            current_plugins = route_value.get("plugins", {})
        else:
            # Fallback to cached data if fetch fails
            route_value = selected_route.get("value", {})
            current_plugins = route_value.get("plugins", {})
            st.warning("⚠️ Could not fetch latest route configuration, using cached data")
        
        # Plugin configuration tabs - removed "Current Plugins" tab
        tab1, tab2 = st.tabs(["🛡️ Prompt Guard", "🎨 Prompt Decorator"])
        
        with tab1:
            guard_config = render_ai_prompt_guard_config(current_plugins, route_id)
        
        with tab2:
            decorator_config = render_ai_prompt_decorator_config(current_plugins, route_value, route_id)
        
        # Update configuration
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Update checkbox states based on current plugins
            guard_key = f"enable_guard_{route_id}"
            if guard_key not in st.session_state:
                st.session_state[guard_key] = "ai-prompt-guard" in current_plugins
            
            decorator_key = f"enable_decorator_{route_id}"
            if decorator_key not in st.session_state:
                st.session_state[decorator_key] = "ai-prompt-decorator" in current_plugins
            
            enable_guard = st.checkbox(
                "Enable AI Prompt Guard",
                key=guard_key,
                help="Enable prompt filtering and blocking"
            )
            
            enable_decorator = st.checkbox(
                "Enable AI Prompt Decorator", 
                key=decorator_key,
                help="Enable prompt modification and enhancement"
            )
        
        with col2:
            if st.button("🧪 Test Configuration"):
                # Test the current configuration
                test_plugins = current_plugins.copy()
                
                # Add the plugins as configured
                if enable_guard:
                    test_plugins["ai-prompt-guard"] = guard_config if guard_config else {}
                if enable_decorator:
                    test_plugins["ai-prompt-decorator"] = decorator_config if decorator_config else {}
                
                # Test with a simple prompt
                with st.spinner("Testing configuration..."):
                    # Extract provider and model from route
                    provider_type = detect_provider_type(route_value)
                    model_name = route_value.get("uri", "").split("/")[-1]
                    
                    test_result = test_plugin_configuration(
                        route_id, 
                        provider_type,
                        model_name,
                        test_plugins
                    )
                    
                    if test_result["success"]:
                        st.success("✅ Configuration test passed!")
                        with st.expander("Test Details", expanded=True):
                            st.write(f"**Test Prompt**: {test_result['test_prompt']}")
                            st.write(f"**Response**: {test_result['response']}")
                            if test_result.get('filtered'):
                                st.warning(f"⚠️ Prompt was filtered: {test_result['filter_reason']}")
                    else:
                        st.error(f"❌ Configuration test failed: {test_result['error']}")
                        if test_result.get('suggestion'):
                            st.info(f"💡 {test_result['suggestion']}")
        
        with col3:
            if st.button("🚀 Apply Configuration", type="primary"):
                # Build new plugins configuration
                new_plugins = current_plugins.copy()
                
                # Handle ai-prompt-guard
                if enable_guard:
                    # Always add the guard config when enabled (even if empty)
                    new_plugins["ai-prompt-guard"] = guard_config if guard_config else {}
                elif "ai-prompt-guard" in new_plugins:
                    del new_plugins["ai-prompt-guard"]
                
                # Handle ai-prompt-decorator
                if enable_decorator:
                    # Always add the decorator config when enabled (even if empty)
                    new_plugins["ai-prompt-decorator"] = decorator_config if decorator_config else {}
                elif "ai-prompt-decorator" in new_plugins:
                    del new_plugins["ai-prompt-decorator"]
                
                # Debug: Show what we're sending
                logger.info(f"Updating route {route_id} with plugins: {new_plugins}")
                
                # Update route configuration
                route_value["plugins"] = new_plugins
                
                # Remove read-only fields that APISIX doesn't accept in updates
                fields_to_remove = ["create_time", "update_time", "createdIndex", "modifiedIndex"]
                for field in fields_to_remove:
                    route_value.pop(field, None)
                
                with st.spinner("Updating route configuration..."):
                    try:
                        success, error_msg = apisix_admin.update_route_plugins(route_id, route_value)
                        
                        if success:
                            st.success("✅ Route configuration updated successfully!")
                        else:
                            st.error(f"❌ Failed to update route configuration: {error_msg}")
                            # Show debugging info
                            with st.expander("Debug Information", expanded=True):
                                st.json({
                                    "route_id": route_id,
                                    "plugins_sent": new_plugins,
                                    "full_config": route_value,
                                    "error_details": error_msg
                                })
                    except Exception as e:
                        st.error(f"❌ Error updating configuration: {str(e)}")
                        logger.error(f"Error in IronUTF update: {e}")
                        with st.expander("Error Details", expanded=True):
                            st.code(str(e))
        
        # Security notice
        st.markdown("---")
        st.info("""
        🔒 **Security Notice**: Changes to AI plugin configurations take effect immediately. 
        Please test your changes thoroughly to ensure they don't inadvertently block legitimate requests.
        """)

if __name__ == "__main__":
    main()