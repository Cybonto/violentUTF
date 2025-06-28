"""
Unit tests for authentication module (app.core.auth)

This module tests the AuthMiddleware class and its authentication methods including:
- JWT authentication
- API key authentication
- APISIX gateway verification
- HMAC signature verification
- Error handling and security
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

# Import the module to test
from app.core.auth import AuthMiddleware, api_key_header, bearer_scheme
from app.models.api_key import APIKey
from app.models.auth import User
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt


class TestAuthMiddleware:
    """Test suite for AuthMiddleware class"""

    @pytest.fixture
    def auth_middleware(self):
        """Create AuthMiddleware instance for testing"""
        return AuthMiddleware()

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request with APISIX headers"""
        request = Mock(spec=Request)
        request.headers = {
            "X-API-Gateway": "APISIX",
            "X-Forwarded-For": "10.0.0.1",
            "X-Forwarded-Host": "api.violentutf.com",
            "X-Real-IP": "192.168.1.100",
            "User-Agent": "test-client/1.0",
        }
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_credentials(self, mock_jwt_token):
        """Create mock HTTP authorization credentials"""
        creds = Mock(spec=HTTPAuthorizationCredentials)
        creds.credentials = mock_jwt_token
        creds.scheme = "Bearer"
        return creds

    @pytest.fixture
    def mock_api_key(self):
        """Create mock API key"""
        return "test-api-key-12345-abcdef"

    # ======================
    # APISIX Gateway Tests
    # ======================

    def test_is_from_apisix_valid_headers(self, auth_middleware, mock_request):
        """Test APISIX verification with valid headers"""
        result = auth_middleware._is_from_apisix(mock_request)
        assert result is True

    def test_is_from_apisix_missing_gateway_header(self, auth_middleware, mock_request):
        """Test APISIX verification fails without gateway header"""
        del mock_request.headers["X-API-Gateway"]
        result = auth_middleware._is_from_apisix(mock_request)
        assert result is False

    def test_is_from_apisix_invalid_gateway_header(self, auth_middleware, mock_request):
        """Test APISIX verification fails with invalid gateway header"""
        mock_request.headers["X-API-Gateway"] = "NGINX"
        result = auth_middleware._is_from_apisix(mock_request)
        assert result is False

    def test_is_from_apisix_missing_proxy_headers(self, auth_middleware):
        """Test APISIX verification fails without proxy headers"""
        request = Mock(spec=Request)
        request.headers = {"X-API-Gateway": "APISIX"}
        result = auth_middleware._is_from_apisix(request)
        assert result is False

    @patch("time.time")
    def test_is_from_apisix_with_valid_hmac(
        self, mock_time, auth_middleware, mock_request
    ):
        """Test APISIX verification with valid HMAC signature"""
        # Set up time
        current_time = 1704067200  # 2024-01-01 00:00:00
        mock_time.return_value = current_time

        # Add HMAC headers
        timestamp = str(current_time)
        mock_request.headers["X-APISIX-Timestamp"] = timestamp

        # Mock the HMAC verification to return True
        with patch.object(
            auth_middleware, "_verify_apisix_signature", return_value=True
        ):
            result = auth_middleware._is_from_apisix(mock_request)
            assert result is True

    @patch("time.time")
    def test_is_from_apisix_expired_timestamp(
        self, mock_time, auth_middleware, mock_request
    ):
        """Test APISIX verification fails with expired timestamp"""
        current_time = 1704067200
        mock_time.return_value = current_time

        # Set timestamp 10 minutes ago (outside 5-minute window)
        old_timestamp = str(current_time - 600)
        mock_request.headers["X-APISIX-Timestamp"] = old_timestamp
        mock_request.headers["X-APISIX-Signature"] = "fake-signature"

        result = auth_middleware._is_from_apisix(mock_request)
        assert result is False

    # ======================
    # HMAC Signature Tests
    # ======================

    @patch("app.core.config.settings")
    def test_verify_apisix_signature_valid(
        self, mock_settings, auth_middleware, mock_request
    ):
        """Test valid HMAC signature verification"""
        # Configure settings
        secret = "test-secret-key"
        mock_settings.APISIX_GATEWAY_SECRET = secret

        # Create valid signature
        timestamp = "1704067200"
        signature_payload = f"{mock_request.method}:{mock_request.url.path}:{timestamp}"
        expected_signature = hmac.new(
            secret.encode("utf-8"), signature_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        result = auth_middleware._verify_apisix_signature(
            mock_request, expected_signature, timestamp
        )
        assert result is True

    @patch("app.core.config.settings")
    def test_verify_apisix_signature_invalid(
        self, mock_settings, auth_middleware, mock_request
    ):
        """Test invalid HMAC signature verification"""
        mock_settings.APISIX_GATEWAY_SECRET = "test-secret-key"

        result = auth_middleware._verify_apisix_signature(
            mock_request, "invalid-signature", "1704067200"
        )
        assert result is False

    @patch("app.core.config.settings")
    def test_verify_apisix_signature_no_secret(
        self, mock_settings, auth_middleware, mock_request
    ):
        """Test HMAC verification fails without secret"""
        mock_settings.APISIX_GATEWAY_SECRET = None

        result = auth_middleware._verify_apisix_signature(
            mock_request, "any-signature", "1704067200"
        )
        assert result is False

    # ======================
    # JWT Authentication Tests
    # ======================

    @pytest.mark.asyncio
    @patch("app.core.security.decode_token")
    async def test_authenticate_jwt_valid(
        self, mock_decode, auth_middleware, mock_jwt_payload
    ):
        """Test successful JWT authentication"""
        mock_decode.return_value = mock_jwt_payload

        user = await auth_middleware._authenticate_jwt("valid-token")

        assert user.username == "test-user-123"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert "user" in user.roles

    @pytest.mark.asyncio
    @patch("app.core.security.decode_token")
    async def test_authenticate_jwt_invalid_token(self, mock_decode, auth_middleware):
        """Test JWT authentication with invalid token"""
        mock_decode.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._authenticate_jwt("invalid-token")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.core.security.decode_token")
    async def test_authenticate_jwt_missing_sub(self, mock_decode, auth_middleware):
        """Test JWT authentication with missing subject"""
        mock_decode.return_value = {"email": "test@example.com"}  # No 'sub' field

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._authenticate_jwt("token-without-sub")

        assert exc_info.value.status_code == 401
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.core.security.decode_token")
    async def test_authenticate_jwt_error(self, mock_decode, auth_middleware):
        """Test JWT authentication with JWT error"""
        mock_decode.side_effect = JWTError("Token decode error")

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._authenticate_jwt("malformed-token")

        assert exc_info.value.status_code == 401
        assert "Could not validate token" in exc_info.value.detail

    # ======================
    # API Key Authentication Tests
    # ======================

    @pytest.mark.asyncio
    @patch("app.db.database.get_db_session")
    async def test_authenticate_api_key_valid(
        self, mock_get_db, auth_middleware, mock_db_session
    ):
        """Test successful API key authentication"""
        # Set up mock database
        mock_get_db.return_value = mock_db_session

        # Create mock API key in database
        mock_api_key = Mock(spec=APIKey)
        mock_api_key.key = "test-api-key-12345"
        mock_api_key.user_id = "api-user-123"
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.utcnow() + timedelta(days=30)

        # Mock query result
        mock_db_session.query().filter_by().first.return_value = mock_api_key

        user = await auth_middleware._authenticate_api_key("test-api-key-12345")

        assert user.username == "api-user-123"
        assert user.roles == ["api_user"]
        assert user.is_active is True

    @pytest.mark.asyncio
    @patch("app.db.database.get_db_session")
    async def test_authenticate_api_key_not_found(
        self, mock_get_db, auth_middleware, mock_db_session
    ):
        """Test API key authentication with non-existent key"""
        mock_get_db.return_value = mock_db_session
        mock_db_session.query().filter_by().first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._authenticate_api_key("non-existent-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.db.database.get_db_session")
    async def test_authenticate_api_key_inactive(
        self, mock_get_db, auth_middleware, mock_db_session
    ):
        """Test API key authentication with inactive key"""
        mock_get_db.return_value = mock_db_session

        mock_api_key = Mock(spec=APIKey)
        mock_api_key.is_active = False
        mock_db_session.query().filter_by().first.return_value = mock_api_key

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._authenticate_api_key("inactive-key")

        assert exc_info.value.status_code == 401
        assert "API key is not active" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.db.database.get_db_session")
    async def test_authenticate_api_key_expired(
        self, mock_get_db, auth_middleware, mock_db_session
    ):
        """Test API key authentication with expired key"""
        mock_get_db.return_value = mock_db_session

        mock_api_key = Mock(spec=APIKey)
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.utcnow() - timedelta(
            days=1
        )  # Expired yesterday
        mock_db_session.query().filter_by().first.return_value = mock_api_key

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware._authenticate_api_key("expired-key")

        assert exc_info.value.status_code == 401
        assert "API key has expired" in exc_info.value.detail

    # ======================
    # Main Authentication Flow Tests
    # ======================

    @pytest.mark.asyncio
    @patch("app.core.security_logging.log_suspicious_activity")
    async def test_call_direct_access_blocked(
        self, mock_log, auth_middleware, mock_credentials
    ):
        """Test direct API access is blocked"""
        # Create request without APISIX headers
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware(request, credentials=mock_credentials, api_key=None)

        assert exc_info.value.status_code == 403
        assert "Direct access not allowed" in exc_info.value.detail

        # Verify security logging
        mock_log.assert_called_once()
        call_args = mock_log.call_args[1]
        assert call_args["activity_type"] == "direct_api_access_attempt"
        assert "bypass APISIX gateway" in call_args["details"]

    @pytest.mark.asyncio
    async def test_call_jwt_success(
        self, auth_middleware, mock_request, mock_credentials, mock_jwt_payload
    ):
        """Test successful authentication with JWT"""
        with patch.object(auth_middleware, "_authenticate_jwt") as mock_auth_jwt:
            mock_user = User(
                username="test-user", email="test@example.com", roles=["user"]
            )
            mock_auth_jwt.return_value = mock_user

            user = await auth_middleware(
                mock_request, credentials=mock_credentials, api_key=None
            )

            assert user == mock_user
            mock_auth_jwt.assert_called_once_with(mock_credentials.credentials)

    @pytest.mark.asyncio
    async def test_call_api_key_success(
        self, auth_middleware, mock_request, mock_api_key
    ):
        """Test successful authentication with API key"""
        with patch.object(auth_middleware, "_authenticate_api_key") as mock_auth_key:
            mock_user = User(username="api-user", email=None, roles=["api_user"])
            mock_auth_key.return_value = mock_user

            user = await auth_middleware(
                mock_request, credentials=None, api_key=mock_api_key
            )

            assert user == mock_user
            mock_auth_key.assert_called_once_with(mock_api_key)

    @pytest.mark.asyncio
    async def test_call_no_credentials(self, auth_middleware, mock_request):
        """Test authentication fails without credentials"""
        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware(mock_request, credentials=None, api_key=None)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_call_jwt_takes_precedence(
        self, auth_middleware, mock_request, mock_credentials, mock_api_key
    ):
        """Test JWT authentication takes precedence over API key"""
        with patch.object(auth_middleware, "_authenticate_jwt") as mock_auth_jwt:
            with patch.object(
                auth_middleware, "_authenticate_api_key"
            ) as mock_auth_key:
                mock_user = User(
                    username="jwt-user", email="jwt@example.com", roles=["user"]
                )
                mock_auth_jwt.return_value = mock_user

                user = await auth_middleware(
                    mock_request, credentials=mock_credentials, api_key=mock_api_key
                )

                assert user.username == "jwt-user"
                mock_auth_jwt.assert_called_once()
                mock_auth_key.assert_not_called()


class TestAuthenticationHelpers:
    """Test authentication helper functions and security schemes"""

    def test_bearer_scheme_configuration(self):
        """Test bearer scheme is configured correctly"""
        assert bearer_scheme.scheme_name == "HTTPBearer"
        assert bearer_scheme.auto_error is False

    def test_api_key_header_configuration(self):
        """Test API key header is configured correctly"""
        assert api_key_header.model.alias == "X-API-Key"
        assert api_key_header.auto_error is False


class TestSecurityScenarios:
    """Test various security scenarios and edge cases"""

    @pytest.mark.asyncio
    async def test_sql_injection_in_api_key(self, auth_middleware, mock_request):
        """Test SQL injection attempt in API key is handled safely"""
        malicious_key = "'; DROP TABLE users; --"

        with patch("app.db.database.get_db_session") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            mock_db.query().filter_by().first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware(
                    mock_request, credentials=None, api_key=malicious_key
                )

            assert exc_info.value.status_code == 401
            # Verify the malicious key was passed safely to the query
            mock_db.query().filter_by.assert_called_once()

    @pytest.mark.asyncio
    async def test_jwt_algorithm_confusion(self, auth_middleware, mock_request):
        """Test protection against JWT algorithm confusion attacks"""
        # Create token with 'none' algorithm
        malicious_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9."
        credentials = Mock()
        credentials.credentials = malicious_token

        with patch("app.core.security.decode_token") as mock_decode:
            mock_decode.side_effect = JWTError("Invalid algorithm")

            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware(
                    mock_request, credentials=credentials, api_key=None
                )

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_timing_attack_prevention(self, auth_middleware):
        """Test that signature comparison uses constant-time comparison"""
        import time

        secret = "test-secret"
        correct_sig = hmac.new(
            secret.encode("utf-8"), b"test-payload", hashlib.sha256
        ).hexdigest()

        # Test with correct signature
        start = time.perf_counter()
        with patch("app.core.config.settings.APISIX_GATEWAY_SECRET", secret):
            auth_middleware._verify_apisix_signature(
                Mock(method="GET", url=Mock(path="/test")), correct_sig, "123"
            )
        correct_time = time.perf_counter() - start

        # Test with incorrect signature (different at first character)
        wrong_sig = "0" + correct_sig[1:]
        start = time.perf_counter()
        with patch("app.core.config.settings.APISIX_GATEWAY_SECRET", secret):
            auth_middleware._verify_apisix_signature(
                Mock(method="GET", url=Mock(path="/test")), wrong_sig, "123"
            )
        wrong_time = time.perf_counter() - start

        # Times should be similar (within 50%) if using constant-time comparison
        time_ratio = max(correct_time, wrong_time) / min(correct_time, wrong_time)
        assert time_ratio < 1.5  # Allow some variance but not too much
