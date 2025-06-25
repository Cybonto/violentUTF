"""
Unit tests for JWT Manager utility (violentutf.utils.jwt_manager)

This module tests JWT token management including:
- Token creation and validation
- Token refresh logic
- Secret key management
- Environment configuration
- Error handling and retries
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import time
import jwt
from datetime import datetime, timedelta
import os
import threading
import streamlit as st

# Mock streamlit before import
st.session_state = {}

# Add parent paths to sys.path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from violentutf.utils.jwt_manager import JWTManager


class TestJWTManager:
    """Test JWT Manager utility"""
    
    @pytest.fixture
    def jwt_manager(self):
        """Create JWT manager instance"""
        with patch('utils.jwt_manager.JWTManager._load_environment'):
            with patch('utils.jwt_manager.JWTManager._get_api_base_url', return_value="http://localhost:9080"):
                manager = JWTManager()
                return manager
    
    @pytest.fixture
    def mock_session_state(self):
        """Mock Streamlit session state"""
        session_state = {
            "jwt_token": None,
            "jwt_payload": None,
            "jwt_expiry": None,
            "keycloak_token": None
        }
        with patch('streamlit.session_state', session_state):
            yield session_state
    
    @pytest.fixture
    def valid_token_payload(self):
        """Create valid token payload"""
        return {
            "sub": "test-user",
            "email": "test@example.com",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
    
    # ======================
    # Initialization Tests
    # ======================
    
    def test_initialization(self):
        """Test JWT manager initialization"""
        with patch('utils.jwt_manager.JWTManager._load_environment'):
            with patch('utils.jwt_manager.JWTManager._get_api_base_url', return_value="http://localhost:9080"):
                manager = JWTManager()
                
                assert manager.api_base_url == "http://localhost:9080"
                assert manager._cached_secret is None
                assert manager._refresh_enabled is True
                assert manager._refresh_buffer == 600
                assert manager._max_retry_attempts == 3
    
    @patch('os.path.exists')
    @patch('dotenv.load_dotenv')
    def test_load_environment(self, mock_load_dotenv, mock_exists):
        """Test environment loading"""
        mock_exists.side_effect = [False, True, False]  # Second location exists
        
        manager = JWTManager()
        
        mock_load_dotenv.assert_called_once()
    
    def test_get_api_base_url_from_env(self):
        """Test API base URL from environment"""
        with patch.dict(os.environ, {'API_BASE_URL': 'http://custom-api:8000'}):
            manager = JWTManager()
            assert manager.api_base_url == "http://custom-api:8000"
    
    def test_get_api_base_url_default(self):
        """Test API base URL default"""
        with patch.dict(os.environ, {}, clear=True):
            manager = JWTManager()
            assert manager.api_base_url == "http://localhost:9080"
    
    # ======================
    # Secret Key Management Tests
    # ======================
    
    def test_get_secret_key_from_cache(self, jwt_manager):
        """Test getting secret key from cache"""
        jwt_manager._cached_secret = "cached-secret"
        jwt_manager._secret_cache_time = time.time()
        
        secret = jwt_manager._get_secret_key()
        
        assert secret == "cached-secret"
    
    def test_get_secret_key_cache_expired(self, jwt_manager):
        """Test getting secret key with expired cache"""
        jwt_manager._cached_secret = "old-secret"
        jwt_manager._secret_cache_time = time.time() - 400  # Expired
        
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'new-secret'}):
            secret = jwt_manager._get_secret_key()
            
            assert secret == "new-secret"
            assert jwt_manager._cached_secret == "new-secret"
    
    def test_get_secret_key_from_env(self, jwt_manager):
        """Test getting secret key from environment"""
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'env-secret'}):
            secret = jwt_manager._get_secret_key()
            
            assert secret == "env-secret"
    
    def test_get_secret_key_from_api(self, jwt_manager):
        """Test getting secret key from API"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {"secret_key": "api-secret"}
                mock_get.return_value = mock_response
                
                secret = jwt_manager._get_secret_key()
                
                assert secret == "api-secret"
                mock_get.assert_called_with(
                    "http://localhost:9080/api/v1/jwt-keys/secret",
                    timeout=10
                )
    
    def test_get_secret_key_api_error(self, jwt_manager):
        """Test getting secret key with API error"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('requests.get', side_effect=Exception("API Error")):
                secret = jwt_manager._get_secret_key()
                
                assert secret == "your-secret-key-here"  # Fallback
    
    # ======================
    # Token Creation Tests
    # ======================
    
    def test_create_token_success(self, jwt_manager, valid_token_payload, mock_session_state):
        """Test successful token creation"""
        with patch.object(jwt_manager, '_get_secret_key', return_value="test-secret"):
            token = jwt_manager.create_token(valid_token_payload)
            
            assert token is not None
            assert isinstance(token, str)
            
            # Verify session state updated
            assert mock_session_state["jwt_token"] == token
            assert mock_session_state["jwt_payload"] == valid_token_payload
            assert mock_session_state["jwt_expiry"] is not None
    
    def test_create_token_with_expiry(self, jwt_manager, mock_session_state):
        """Test token creation with custom expiry"""
        payload = {"sub": "test-user"}
        
        with patch.object(jwt_manager, '_get_secret_key', return_value="test-secret"):
            token = jwt_manager.create_token(payload, expires_delta=timedelta(minutes=15))
            
            # Decode to verify expiry
            decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
            exp_time = datetime.fromtimestamp(decoded["exp"])
            iat_time = datetime.fromtimestamp(decoded["iat"])
            
            assert (exp_time - iat_time).seconds == 900  # 15 minutes
    
    def test_create_token_error(self, jwt_manager):
        """Test token creation with error"""
        with patch.object(jwt_manager, '_get_secret_key', side_effect=Exception("Secret error")):
            token = jwt_manager.create_token({"sub": "test"})
            
            assert token is None
    
    # ======================
    # Token Validation Tests
    # ======================
    
    def test_validate_token_valid(self, jwt_manager, valid_token_payload):
        """Test validating valid token"""
        secret = "test-secret"
        token = jwt.encode(valid_token_payload, secret, algorithm="HS256")
        
        with patch.object(jwt_manager, '_get_secret_key', return_value=secret):
            payload = jwt_manager.validate_token(token)
            
            assert payload is not None
            assert payload["sub"] == "test-user"
            assert payload["email"] == "test@example.com"
    
    def test_validate_token_expired(self, jwt_manager):
        """Test validating expired token"""
        secret = "test-secret"
        expired_payload = {
            "sub": "test-user",
            "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(expired_payload, secret, algorithm="HS256")
        
        with patch.object(jwt_manager, '_get_secret_key', return_value=secret):
            payload = jwt_manager.validate_token(token)
            
            assert payload is None
    
    def test_validate_token_invalid_signature(self, jwt_manager, valid_token_payload):
        """Test validating token with invalid signature"""
        token = jwt.encode(valid_token_payload, "wrong-secret", algorithm="HS256")
        
        with patch.object(jwt_manager, '_get_secret_key', return_value="correct-secret"):
            payload = jwt_manager.validate_token(token)
            
            assert payload is None
    
    def test_validate_token_malformed(self, jwt_manager):
        """Test validating malformed token"""
        with patch.object(jwt_manager, '_get_secret_key', return_value="secret"):
            payload = jwt_manager.validate_token("not.a.valid.token")
            
            assert payload is None
    
    # ======================
    # Session Token Tests
    # ======================
    
    def test_get_current_token_from_session(self, jwt_manager, mock_session_state):
        """Test getting current token from session"""
        mock_session_state["jwt_token"] = "session-token"
        
        token = jwt_manager.get_current_token()
        
        assert token == "session-token"
    
    def test_get_current_token_none(self, jwt_manager, mock_session_state):
        """Test getting current token when none exists"""
        token = jwt_manager.get_current_token()
        
        assert token is None
    
    def test_is_token_valid_true(self, jwt_manager, mock_session_state):
        """Test checking if token is valid"""
        future_time = datetime.utcnow() + timedelta(hours=1)
        mock_session_state["jwt_expiry"] = future_time.timestamp()
        
        assert jwt_manager.is_token_valid() is True
    
    def test_is_token_valid_expired(self, jwt_manager, mock_session_state):
        """Test checking if token is expired"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        mock_session_state["jwt_expiry"] = past_time.timestamp()
        
        assert jwt_manager.is_token_valid() is False
    
    def test_is_token_valid_no_expiry(self, jwt_manager, mock_session_state):
        """Test checking token validity with no expiry"""
        mock_session_state["jwt_expiry"] = None
        
        assert jwt_manager.is_token_valid() is False
    
    # ======================
    # Token Refresh Tests
    # ======================
    
    def test_should_refresh_token_true(self, jwt_manager, mock_session_state):
        """Test determining if token should be refreshed"""
        # Token expires in 5 minutes (less than buffer)
        expire_time = datetime.utcnow() + timedelta(minutes=5)
        mock_session_state["jwt_expiry"] = expire_time.timestamp()
        mock_session_state["jwt_token"] = "some-token"
        
        assert jwt_manager.should_refresh_token() is True
    
    def test_should_refresh_token_false(self, jwt_manager, mock_session_state):
        """Test token doesn't need refresh yet"""
        # Token expires in 20 minutes (more than buffer)
        expire_time = datetime.utcnow() + timedelta(minutes=20)
        mock_session_state["jwt_expiry"] = expire_time.timestamp()
        mock_session_state["jwt_token"] = "some-token"
        
        assert jwt_manager.should_refresh_token() is False
    
    def test_refresh_token_from_keycloak(self, jwt_manager, mock_session_state):
        """Test refreshing token from Keycloak token"""
        mock_session_state["keycloak_token"] = {
            "sub": "keycloak-user",
            "email": "keycloak@example.com"
        }
        
        with patch.object(jwt_manager, 'create_token', return_value="new-token") as mock_create:
            result = jwt_manager.refresh_token()
            
            assert result is True
            mock_create.assert_called_once()
            
            # Verify Keycloak data was used
            call_args = mock_create.call_args[0][0]
            assert call_args["sub"] == "keycloak-user"
            assert call_args["email"] == "keycloak@example.com"
    
    def test_refresh_token_with_retry(self, jwt_manager, mock_session_state):
        """Test token refresh with retry logic"""
        mock_session_state["keycloak_token"] = {"sub": "user"}
        
        # First attempt fails, second succeeds
        with patch.object(jwt_manager, 'create_token', side_effect=[None, "new-token"]):
            with patch('time.sleep'):  # Don't actually sleep in tests
                result = jwt_manager.refresh_token()
                
                assert result is True
    
    def test_refresh_token_all_attempts_fail(self, jwt_manager, mock_session_state):
        """Test token refresh when all attempts fail"""
        mock_session_state["keycloak_token"] = {"sub": "user"}
        
        with patch.object(jwt_manager, 'create_token', return_value=None):
            with patch('time.sleep'):
                result = jwt_manager.refresh_token()
                
                assert result is False
                assert jwt_manager._last_error is not None
    
    def test_refresh_token_in_progress(self, jwt_manager):
        """Test preventing concurrent refresh attempts"""
        jwt_manager._refresh_in_progress = True
        
        result = jwt_manager.refresh_token()
        
        assert result is False  # Should return immediately
    
    # ======================
    # Proactive Refresh Tests
    # ======================
    
    def test_start_proactive_refresh(self, jwt_manager):
        """Test starting proactive refresh thread"""
        with patch('threading.Thread') as mock_thread:
            jwt_manager.start_proactive_refresh()
            
            mock_thread.assert_called_once()
            assert mock_thread.return_value.daemon is True
            mock_thread.return_value.start.assert_called_once()
    
    def test_stop_proactive_refresh(self, jwt_manager):
        """Test stopping proactive refresh"""
        jwt_manager._refresh_enabled = True
        
        jwt_manager.stop_proactive_refresh()
        
        assert jwt_manager._refresh_enabled is False
    
    @patch('time.sleep')
    def test_proactive_refresh_loop(self, mock_sleep, jwt_manager, mock_session_state):
        """Test proactive refresh loop execution"""
        jwt_manager._refresh_enabled = True
        
        # Set up token that needs refresh
        expire_time = datetime.utcnow() + timedelta(minutes=5)
        mock_session_state["jwt_expiry"] = expire_time.timestamp()
        mock_session_state["jwt_token"] = "old-token"
        mock_session_state["keycloak_token"] = {"sub": "user"}
        
        refresh_called = False
        
        def mock_refresh():
            nonlocal refresh_called
            refresh_called = True
            jwt_manager._refresh_enabled = False  # Stop loop
            return True
        
        with patch.object(jwt_manager, 'refresh_token', side_effect=mock_refresh):
            jwt_manager._proactive_refresh_loop()
            
            assert refresh_called is True
    
    # ======================
    # Error Handling Tests
    # ======================
    
    def test_create_token_with_invalid_payload(self, jwt_manager):
        """Test creating token with invalid payload"""
        # Payload with non-serializable data
        payload = {"sub": "user", "data": object()}
        
        with patch.object(jwt_manager, '_get_secret_key', return_value="secret"):
            token = jwt_manager.create_token(payload)
            
            assert token is None
    
    def test_concurrent_secret_key_fetching(self, jwt_manager):
        """Test concurrent secret key fetching"""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # Simulate slow API
            response = Mock()
            response.json.return_value = {"secret_key": f"secret-{call_count}"}
            return response
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('requests.get', side_effect=mock_get):
                # Clear cache
                jwt_manager._cached_secret = None
                jwt_manager._secret_cache_time = None
                
                # Simulate concurrent calls
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [
                        executor.submit(jwt_manager._get_secret_key)
                        for _ in range(3)
                    ]
                    results = [f.result() for f in futures]
                
                # Should use cached value after first call
                assert all(r == results[0] for r in results)
                assert call_count <= 2  # May have some race conditions but should be limited