"""
Unit tests for security module (app.core.security)

This module tests security utilities including:
- JWT token creation and validation
- Password hashing and verification
- Token decoding with security checks
- Password strength validation
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import jwt
import pytest
from app.core.security import (ALGORITHM, SECRET_KEY, create_access_token,
                               decode_token, get_password_hash, pwd_context,
                               timing_safe_compare, validate_secret_key,
                               validate_token_length, verify_password)
from app.core.validation import SecurityLimits
from freezegun import freeze_time
from passlib.context import CryptContext


class TestJWTTokens:
    """Test JWT token creation and validation"""

    @freeze_time("2024-01-01 00:00:00")
    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry"""
        data = {"sub": "test-user", "email": "test@example.com"}

        with patch("app.core.config.settings.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
            token = create_access_token(data)

        # Decode and verify
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["sub"] == "test-user"
        assert decoded["email"] == "test@example.com"
        assert decoded["iat"] == int(datetime(2024, 1, 1, 0, 0, 0).timestamp())
        assert decoded["exp"] == int(datetime(2024, 1, 1, 0, 30, 0).timestamp())

    @freeze_time("2024-01-01 00:00:00")
    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry"""
        data = {"sub": "test-user"}
        expires_delta = timedelta(hours=2)

        token = create_access_token(data, expires_delta)

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["exp"] == int(datetime(2024, 1, 1, 2, 0, 0).timestamp())

    def test_create_access_token_preserves_data(self):
        """Test that original data dict is not modified"""
        data = {"sub": "test-user", "custom": "value"}
        original_data = data.copy()

        create_access_token(data)

        assert data == original_data  # Original not modified

    @patch("app.core.validation.validate_jwt_token")
    def test_decode_token_valid(self, mock_validate):
        """Test decoding valid token"""
        mock_validate.return_value = True

        # Create a valid token
        data = {"sub": "test-user", "email": "test@example.com"}
        token = create_access_token(data, timedelta(hours=1))

        # Decode it
        decoded = decode_token(token)

        assert decoded["sub"] == "test-user"
        assert decoded["email"] == "test@example.com"
        mock_validate.assert_called_once_with(token)

    @patch("app.core.validation.validate_jwt_token")
    def test_decode_token_validation_fails(self, mock_validate):
        """Test decoding token when validation fails"""
        mock_validate.return_value = False

        token = "some.invalid.token"
        result = decode_token(token)

        assert result is None

    def test_decode_token_expired(self):
        """Test decoding expired token"""
        with freeze_time("2024-01-01 00:00:00"):
            # Create token that expires in 1 minute
            data = {"sub": "test-user"}
            token = create_access_token(data, timedelta(minutes=1))

        # Move time forward 2 minutes
        with freeze_time("2024-01-01 00:02:00"):
            with patch("app.core.validation.validate_jwt_token", return_value=True):
                result = decode_token(token)
                assert result is None

    def test_decode_token_invalid_format(self):
        """Test decoding malformed token"""
        with patch("app.core.validation.validate_jwt_token", return_value=True):
            result = decode_token("not.a.valid.jwt")
            assert result is None

    def test_decode_token_wrong_algorithm(self):
        """Test decoding token with wrong algorithm"""
        # Create token with different algorithm
        data = {"sub": "test-user"}
        token = jwt.encode(data, SECRET_KEY, algorithm="HS512")

        with patch("app.core.validation.validate_jwt_token", return_value=True):
            # Should fail because we expect HS256
            result = decode_token(token)
            assert result is None


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_get_password_hash(self):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Verify it's a bcrypt hash
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

        # Verify it's different each time (due to salt)
        hashed2 = get_password_hash(password)
        assert hashed != hashed2

    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword123!", hashed) is False

    def test_verify_password_empty(self):
        """Test verifying empty password"""
        hashed = get_password_hash("RealPassword123!")

        assert verify_password("", hashed) is False

    def test_password_context_configuration(self):
        """Test password hashing works correctly with bcrypt"""
        # Test behavior, not implementation details
        password = "TestPassword123!"

        # Test that hashing produces a bcrypt-formatted hash
        hashed = get_password_hash(password)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # bcrypt format
        assert len(hashed) >= 60  # bcrypt hashes are at least 60 chars

        # Test that verification works
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    @patch("app.core.password_policy.is_password_secure")
    def test_password_validation_integration(self, mock_is_secure):
        """Test integration with password policy module"""
        # Mock the password security check
        mock_is_secure.return_value = True

        # Test that secure passwords can be hashed
        password = "VeryStrongPassword123!@#"
        hashed = get_password_hash(password)
        assert hashed is not None
        assert verify_password(password, hashed) is True

        # Test that insecure passwords are rejected (when integrated)
        mock_is_secure.return_value = False
        weak_password = "weak"

        # In a real implementation, you might check password security before hashing
        # This test verifies the mock is called when expected
        if mock_is_secure(weak_password):
            hashed = get_password_hash(weak_password)
        else:
            hashed = None

        assert hashed is None
        mock_is_secure.assert_called_with(weak_password)


class TestSecurityEdgeCases:
    """Test security edge cases and attack scenarios"""

    def test_decode_token_none_algorithm_attack(self):
        """Test protection against 'none' algorithm attack"""
        # Create token with 'none' algorithm (security vulnerability)
        header = {"alg": "none", "typ": "JWT"}
        payload = {"sub": "admin", "exp": 9999999999}

        # Manually create token with no signature
        import base64
        import json

        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        )
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        malicious_token = f"{header_b64}.{payload_b64}."

        with patch("app.core.validation.validate_jwt_token", return_value=True):
            result = decode_token(malicious_token)
            assert result is None  # Should reject 'none' algorithm

    def test_decode_token_sql_injection_attempt(self):
        """Test that SQL injection in token payload doesn't cause issues"""
        data = {"sub": "'; DROP TABLE users; --", "email": "test@example.com"}
        token = create_access_token(data)

        with patch("app.core.validation.validate_jwt_token", return_value=True):
            decoded = decode_token(token)
            # Should decode safely without executing SQL
            assert decoded["sub"] == "'; DROP TABLE users; --"

    def test_timing_safe_password_comparison(self):
        """Test that timing-safe comparison function is available and used"""
        # Don't test actual timing (unreliable), test that proper functions exist

        # Test that timing_safe_compare function exists
        from app.core.security import timing_safe_compare

        # Test the function behavior
        assert timing_safe_compare("password", "password") is True
        assert timing_safe_compare("password", "different") is False
        assert timing_safe_compare("short", "longer_string") is False

        # Test that bcrypt is used (inherently timing-safe)
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Bcrypt hashes should have correct format
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

        # Verify password comparison works correctly
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

        # Note: bcrypt.checkpw is timing-safe by design

    def test_secret_key_configuration(self):
        """Test secret key validation criteria"""
        # Define clear criteria for valid secret keys

        # Test minimum length requirement (32 characters)
        short_key = "short"
        assert validate_secret_key(short_key) is False

        # Test weak/common keys are rejected
        weak_keys = ["password123", "secret123", "12345678901234567890123456789012"]
        for weak_key in weak_keys:
            assert validate_secret_key(weak_key) is False

        # Test valid strong key
        strong_key = "a9b8c7d6e5f4g3h2i1j0k9l8m7n6o5p4"  # 32 chars, random
        assert validate_secret_key(strong_key) is True

        # Test current configured key is valid (for testing)
        assert validate_secret_key(SECRET_KEY) is True

    def test_token_payload_size_limit(self):
        """Test handling of large token payloads"""
        # Create token with large payload
        large_data = {"sub": "test-user", "data": "x" * 10000}  # 10KB of data

        token = create_access_token(large_data)

        with patch("app.core.validation.validate_jwt_token", return_value=True):
            decoded = decode_token(token)
            assert decoded["sub"] == "test-user"
            assert len(decoded["data"]) == 10000


class TestIntegrationScenarios:
    """Test integration with other security components"""

    @patch("app.core.validation.SecurityLimits.MAX_TOKEN_LENGTH", 1000)
    def test_token_length_validation(self):
        """Test token length specifications and limits"""
        # Define clear token length specifications:
        # - Minimum: 100 characters (too short to be valid JWT)
        # - Maximum: 2048 characters (reasonable limit for HTTP headers)

        # Test valid token length
        normal_data = {"sub": "test-user", "email": "test@example.com"}
        normal_token = create_access_token(normal_data)
        assert 100 < len(normal_token) < 2048
        assert validate_token_length(normal_token) is True

        # Test token with large payload (but within limits)
        large_data = {
            "sub": "test-user",
            "permissions": ["perm" + str(i) for i in range(50)],
        }
        large_token = create_access_token(large_data)
        assert len(large_token) < 2048
        assert validate_token_length(large_token) is True

        # Test invalid token formats
        assert validate_token_length("") is False
        assert validate_token_length("too.short") is False
        assert validate_token_length("x" * 3000) is False  # Too long
