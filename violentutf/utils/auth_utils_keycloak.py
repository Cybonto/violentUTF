"""
Authentication utilities for Keycloak SSO
This version is for local deployment with Keycloak, not Streamlit Community Cloud
"""
import streamlit as st
from .logging import get_logger
logger = get_logger(__name__)
from .token_manager import token_manager

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        logger.debug(f"Loaded environment from {env_file}")
except ImportError:
    logger.warning("python-dotenv not available")
except Exception as e:
    logger.error(f"Failed to load environment: {e}")

def _clear_invalid_jwt_tokens():
    """
    HOTFIX: Clear invalid JWT tokens from session state.
    This fixes the issue where old tokens with wrong signatures are cached.
    """
    try:
        # Check if we have an API token
        if 'api_token' in st.session_state:
            token = st.session_state['api_token']
            
            # Use the JWT manager for consistent validation
            try:
                from .jwt_manager import jwt_manager
                
                # Use the same validation method that creates tokens
                if jwt_manager._validate_token_signature(token):
                    # Token is valid, keep it
                    logger.debug("JWT token signature validated successfully")
                    return
                else:
                    # Token has invalid signature, clear it
                    logger.warning("Clearing invalid JWT token from session state (signature validation failed)")
                    _clear_jwt_session_data()
                    
            except ImportError:
                # Fallback to direct validation if JWT manager not available
                import jwt
                import os
                
                secret_key = os.getenv("JWT_SECRET_KEY")
                if secret_key:
                    try:
                        # Attempt to decode the token
                        jwt.decode(token, secret_key, algorithms=["HS256"])
                        # Token is valid, keep it
                        return
                    except jwt.InvalidSignatureError:
                        # Token has invalid signature, clear it
                        logger.warning("Clearing invalid JWT token from session state (fallback validation)")
                        _clear_jwt_session_data()
                    except jwt.ExpiredSignatureError:
                        # Token is expired but signature is valid, let normal flow handle it
                        return
                    except Exception as e:
                        # Other JWT errors, clear the token
                        logger.warning(f"Clearing invalid JWT token due to error: {e}")
                        _clear_jwt_session_data()
                else:
                    logger.warning("No JWT secret available for token validation")
    except Exception as e:
        logger.error(f"Error in JWT token validation: {e}")

def _clear_jwt_session_data():
    """Clear JWT-related session data"""
    jwt_keys = ['api_token', 'api_token_exp', 'api_token_created']
    for key in jwt_keys:
        if key in st.session_state:
            del st.session_state[key]
            logger.info(f"Cleared {key} from session state")

def handle_authentication_and_sidebar(page_name: str = None):
    """
    Simplified authentication handler for Keycloak SSO.
    For local deployment, we assume users authenticate through Keycloak directly.
    
    Args:
        page_name (str, optional): Name of the current page for logging
    
    Returns:
        str: Username if authenticated (from environment/session)
    """
    # HOTFIX: Clear invalid JWT tokens on every page load
    _clear_invalid_jwt_tokens()
    
    # Initialize session state
    if 'auth_initialized' not in st.session_state:
        st.session_state['auth_initialized'] = True
        st.session_state['access_token'] = None
        st.session_state['has_ai_access'] = False
        
        # Try to get token from Keycloak
        try:
            token = token_manager._get_token_from_keycloak()
            if token:
                st.session_state['access_token'] = token
                st.session_state['has_ai_access'] = token_manager.has_ai_access(token)
                logger.info(f"Keycloak token obtained for page: {page_name}")
            else:
                logger.warning(f"No Keycloak token available for page: {page_name}")
        except Exception as e:
            logger.error(f"Error getting Keycloak token: {e}")
    
    # Display sidebar
    display_sidebar(page_name)
    
    # Return username from environment or default
    import os
    username = os.getenv('KEYCLOAK_USERNAME', 'local_user')
    return username

def display_sidebar(page_name: str = None):
    """Display the sidebar with navigation and user info"""
    with st.sidebar:
        st.title("🔐 ViolentUTF")
        
        # Show authentication status
        has_keycloak_token = bool(st.session_state.get('access_token'))
        has_api_token = bool(st.session_state.get('api_token'))
        
        if has_keycloak_token:
            st.success("✓ Authenticated via Keycloak SSO")
            if st.session_state.get('has_ai_access'):
                st.info("🤖 AI API Access Enabled")
        elif has_api_token:
            st.success("✓ Environment Authentication Active")
            st.info("🤖 AI API Access Enabled")
        else:
            import os
            if os.getenv('KEYCLOAK_USERNAME'):
                st.info("🔑 Environment credentials available")
                st.info("System will authenticate using .env file")
            else:
                st.warning("⚠️ No authentication available")
                st.info("Configure Keycloak credentials in .env file")
        
        # JWT Token Display (collapsed by default)
        with st.expander("🔐 Developer Tools", expanded=False):
            st.subheader("JWT Token")
            if st.session_state.get('api_token'):
                st.code(st.session_state['api_token'], language=None)
                if st.button("📋 Copy Token", key=f"copy_jwt_{page_name or 'keycloak'}"):
                    st.write("Token copied! Use it with:")
                    st.code('curl -H "Authorization: Bearer <token>" ...', language="bash")
            else:
                st.warning("No JWT token available. Please ensure you're logged in.")

def clear_user_session():
    """Clear all user-related session state"""
    keys_to_clear = [
        'access_token', 'has_ai_access', 'auth_initialized',
        # Clear API token and API-related session data
        'api_token', 'api_user_info', 'api_session_data', 
        'api_config_params', 'api_db_initialized'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    logger.info("User session cleared")

# For compatibility with existing code
check_authentication = handle_authentication_and_sidebar