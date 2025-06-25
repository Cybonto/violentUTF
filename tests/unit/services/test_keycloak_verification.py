"""
Unit tests for Keycloak verification service (app.services.keycloak_verification)

This module tests Keycloak JWT token verification including:
- Token signature verification
- Public key retrieval
- Token claims validation
- User info retrieval
- Error handling and caching
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time
import json
from datetime import datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import httpx

from app.services.keycloak_verification import KeycloakJWTVerifier


class TestKeycloakJWTVerifier:
    """Test Keycloak JWT verification service"""
    
    @pytest.fixture
    def verifier(self):
        """Create Keycloak verifier instance"""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.KEYCLOAK_URL = "http://localhost:8080"
            mock_settings.KEYCLOAK_REALM = "test-realm"
            mock_settings.KEYCLOAK_CLIENT_ID = "test-client"
            
            verifier = KeycloakJWTVerifier()
            return verifier
    
    @pytest.fixture
    def mock_keycloak_config(self):
        """Mock Keycloak OpenID configuration"""
        return {
            "issuer": "http://localhost:8080/realms/test-realm",
            "authorization_endpoint": "http://localhost:8080/realms/test-realm/protocol/openid-connect/auth",
            "token_endpoint": "http://localhost:8080/realms/test-realm/protocol/openid-connect/token",
            "userinfo_endpoint": "http://localhost:8080/realms/test-realm/protocol/openid-connect/userinfo",
            "jwks_uri": "http://localhost:8080/realms/test-realm/protocol/openid-connect/certs",
            "end_session_endpoint": "http://localhost:8080/realms/test-realm/protocol/openid-connect/logout"
        }
    
    @pytest.fixture
    def mock_jwks_response(self):
        """Mock JWKS response with RSA key"""
        # Generate a test RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Convert to JWK format
        public_numbers = public_key.public_numbers()
        
        def to_base64url(num):
            """Convert number to base64url encoding"""
            import base64
            byte_length = (num.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(num.to_bytes(byte_length, 'big')).decode('ascii').rstrip('=')
        
        return {
            "keys": [
                {
                    "kid": "test-key-id",
                    "kty": "RSA",
                    "alg": "RS256",
                    "use": "sig",
                    "n": to_base64url(public_numbers.n),
                    "e": to_base64url(public_numbers.e)
                }
            ]
        }, private_key
    
    @pytest.fixture
    def mock_jwt_token(self, mock_jwks_response):
        """Create a mock JWT token signed with test key"""
        _, private_key = mock_jwks_response
        
        payload = {
            "sub": "test-user-123",
            "iss": "http://localhost:8080/realms/test-realm",
            "aud": "test-client",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "preferred_username": "testuser",
            "email": "test@example.com",
            "name": "Test User",
            "realm_access": {
                "roles": ["user", "admin"]
            }
        }
        
        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-id"}
        )
        
        return token, payload
    
    # ======================
    # Configuration Tests
    # ======================
    
    @pytest.mark.asyncio
    async def test_get_keycloak_config_success(self, verifier, mock_keycloak_config):
        """Test successful Keycloak config retrieval"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_keycloak_config
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            config = await verifier._get_keycloak_config()
            
            assert config == mock_keycloak_config
            assert verifier._config_cache == mock_keycloak_config
            assert verifier._config_cache_time > 0
    
    @pytest.mark.asyncio
    async def test_get_keycloak_config_cached(self, verifier, mock_keycloak_config):
        """Test Keycloak config cache usage"""
        # Set up cache
        verifier._config_cache = mock_keycloak_config
        verifier._config_cache_time = time.time()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            config = await verifier._get_keycloak_config()
            
            assert config == mock_keycloak_config
            # Should not make HTTP request
            mock_client_class.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_keycloak_config_cache_expired(self, verifier, mock_keycloak_config):
        """Test Keycloak config cache expiration"""
        # Set expired cache
        verifier._config_cache = {"old": "config"}
        verifier._config_cache_time = time.time() - 7200  # 2 hours ago
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_keycloak_config
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            config = await verifier._get_keycloak_config()
            
            assert config == mock_keycloak_config
            # Should make new HTTP request
            mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_keycloak_config_error(self, verifier):
        """Test Keycloak config retrieval error"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPError("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await verifier._get_keycloak_config()
            
            assert exc_info.value.status_code == 503
            assert "Failed to get Keycloak configuration" in exc_info.value.detail
    
    # ======================
    # Token Verification Tests
    # ======================
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, verifier, mock_jwt_token, mock_keycloak_config, mock_jwks_response):
        """Test successful token verification"""
        token, expected_payload = mock_jwt_token
        jwks_data, _ = mock_jwks_response
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient') as mock_jwks_client_class:
                mock_jwks_client = Mock()
                mock_signing_key = Mock()
                mock_signing_key.key = jwks_data["keys"][0]
                mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
                mock_jwks_client_class.return_value = mock_jwks_client
                
                # Mock jwt.decode to return our payload
                with patch('jwt.decode', return_value=expected_payload):
                    payload = await verifier.verify_token(token)
                    
                    assert payload["sub"] == "test-user-123"
                    assert payload["email"] == "test@example.com"
                    assert "realm_access" in payload
    
    @pytest.mark.asyncio
    async def test_verify_token_expired(self, verifier, mock_keycloak_config):
        """Test expired token verification"""
        # Create expired token
        expired_payload = {
            "sub": "test-user",
            "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
            "iss": "http://localhost:8080/realms/test-realm"
        }
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient'):
                with patch('jwt.decode', side_effect=jwt.ExpiredSignatureError("Token expired")):
                    with pytest.raises(HTTPException) as exc_info:
                        await verifier.verify_token("expired.token")
                    
                    assert exc_info.value.status_code == 401
                    assert "Token has expired" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid_signature(self, verifier, mock_keycloak_config):
        """Test token with invalid signature"""
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient'):
                with patch('jwt.decode', side_effect=jwt.InvalidSignatureError("Invalid signature")):
                    with pytest.raises(HTTPException) as exc_info:
                        await verifier.verify_token("invalid.signature.token")
                    
                    assert exc_info.value.status_code == 401
                    assert "Invalid token signature" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_verify_token_wrong_issuer(self, verifier, mock_keycloak_config, mock_jwt_token, mock_jwks_response):
        """Test token with wrong issuer"""
        token, payload = mock_jwt_token
        payload["iss"] = "http://wrong-issuer.com"
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient'):
                with patch('jwt.decode', return_value=payload):
                    with pytest.raises(HTTPException) as exc_info:
                        await verifier.verify_token(token)
                    
                    assert exc_info.value.status_code == 401
                    assert "Invalid token issuer" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_verify_token_wrong_audience(self, verifier, mock_keycloak_config, mock_jwt_token, mock_jwks_response):
        """Test token with wrong audience"""
        token, payload = mock_jwt_token
        payload["aud"] = "wrong-client"
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient'):
                with patch('jwt.decode', return_value=payload):
                    with pytest.raises(HTTPException) as exc_info:
                        await verifier.verify_token(token)
                    
                    assert exc_info.value.status_code == 401
                    assert "Invalid token audience" in exc_info.value.detail
    
    # ======================
    # User Info Tests
    # ======================
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, verifier, mock_keycloak_config):
        """Test successful user info retrieval"""
        mock_user_info = {
            "sub": "test-user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User"
        }
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.json.return_value = mock_user_info
                mock_response.raise_for_status = Mock()
                mock_client.get.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                user_info = await verifier.get_user_info("test-access-token")
                
                assert user_info == mock_user_info
                
                # Verify authorization header
                call_args = mock_client.get.call_args
                assert call_args[1]["headers"]["Authorization"] == "Bearer test-access-token"
    
    @pytest.mark.asyncio
    async def test_get_user_info_unauthorized(self, verifier, mock_keycloak_config):
        """Test user info retrieval with invalid token"""
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Unauthorized", request=Mock(), response=mock_response
                )
                mock_client.get.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                with pytest.raises(HTTPException) as exc_info:
                    await verifier.get_user_info("invalid-token")
                
                assert exc_info.value.status_code == 401
                assert "Invalid or expired token" in exc_info.value.detail
    
    # ======================
    # Edge Cases and Security Tests
    # ======================
    
    @pytest.mark.asyncio
    async def test_verify_token_none_algorithm_attack(self, verifier, mock_keycloak_config):
        """Test protection against 'none' algorithm attack"""
        # Token with 'none' algorithm
        malicious_token = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9."
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient'):
                with pytest.raises(HTTPException) as exc_info:
                    await verifier.verify_token(malicious_token)
                
                assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_key_confusion_attack(self, verifier, mock_keycloak_config):
        """Test protection against key confusion attacks"""
        # Token signed with symmetric key instead of RSA
        fake_token = jwt.encode(
            {"sub": "admin", "iss": verifier.issuer},
            "secret-key",
            algorithm="HS256"
        )
        
        with patch.object(verifier, '_get_keycloak_config', return_value=mock_keycloak_config):
            with patch('jwt.PyJWKClient'):
                with patch('jwt.decode', side_effect=jwt.InvalidAlgorithmError("Invalid algorithm")):
                    with pytest.raises(HTTPException) as exc_info:
                        await verifier.verify_token(fake_token)
                    
                    assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_concurrent_config_requests(self, verifier, mock_keycloak_config):
        """Test handling of concurrent configuration requests"""
        request_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            response = Mock()
            response.json.return_value = mock_keycloak_config
            response.raise_for_status = Mock()
            return response
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Clear cache
            verifier._config_cache = {}
            verifier._config_cache_time = 0
            
            # Make concurrent requests
            import asyncio
            configs = await asyncio.gather(*[
                verifier._get_keycloak_config() for _ in range(5)
            ])
            
            # Should only make one request due to caching
            assert request_count == 1
            assert all(c == mock_keycloak_config for c in configs)