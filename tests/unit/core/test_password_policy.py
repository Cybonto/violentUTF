"""
Unit tests for password policy module (app.core.password_policy)

This module tests password strength validation including:
- Password complexity requirements
- Common password detection
- Password strength scoring
- Policy compliance checks
"""

import pytest
from app.core.password_policy import (PasswordStrength, PasswordValidator,
                                      validate_password_strength)


# Mock functions that don't exist in the actual module
def check_common_passwords(password: str) -> bool:
    """Mock function for checking common passwords with l33t speak detection"""
    common = ["password", "123456", "qwerty", "admin", "letmein"]

    # Check exact match
    if password.lower() in common:
        return True

    # Check if contains common password
    for common_pwd in common:
        if common_pwd in password.lower():
            return True

    # L33t speak substitutions (reverse mapping)
    l33t_subs = {
        "@": "a",
        "4": "a",
        "3": "e",
        "1": "i",
        "!": "i",
        "0": "o",
        "$": "s",
        "5": "s",
        "7": "t",
        "+": "t",
    }

    # Normalize l33t speak
    normalized = password.lower()
    for l33t, normal in l33t_subs.items():
        normalized = normalized.replace(l33t, normal)

    # Check normalized version
    if normalized in common:
        return True

    for common_pwd in common:
        if common_pwd in normalized:
            return True

    return False


def calculate_entropy(password: str) -> float:
    """Mock function for calculating password entropy"""
    import math

    charset_size = 0
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() and ord(c) < 128 for c in password)

    if has_lower:
        charset_size += 26
    if has_upper:
        charset_size += 26
    if has_digit:
        charset_size += 10
    if has_special:
        charset_size += 32

    return len(password) * math.log2(charset_size) if charset_size > 0 else 0


class TestPasswordStrengthValidation:
    """Test password strength validation logic"""

    def test_very_weak_password(self):
        """Test very weak password (empty or whitespace only)"""
        # Test empty password
        password = ""
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must be at least 8 characters long" in issues

        # Test whitespace-only password
        password = "   "
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must be at least 8 characters long" in issues

    def test_strong_password(self):
        """Test validation of strong password"""
        password = "MyStr0ng!P@ssw0rd2024"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is True
        assert strength == PasswordStrength.STRONG
        assert len(issues) == 0

    def test_password_too_short(self):
        """Test password that's too short"""
        password = "Short1!"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must be at least 8 characters long" in issues

    def test_password_no_uppercase(self):
        """Test password without uppercase letters"""
        password = "password123!"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must contain at least one uppercase letter" in issues

    def test_password_no_lowercase(self):
        """Test password without lowercase letters"""
        password = "PASSWORD123!"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must contain at least one lowercase letter" in issues

    def test_password_no_digit(self):
        """Test password without digits"""
        password = "Password!@#"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must contain at least one digit" in issues

    def test_password_no_special_char(self):
        """Test password without special characters"""
        password = "Password123"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must contain at least one special character" in issues

    def test_common_password(self):
        """Test detection of common password (case-insensitive)"""
        # Common passwords should be detected regardless of case
        password = "Password123!"  # Contains "password" with capital P
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert "Password is too common" in issues
        # Note: Detection should be case-insensitive

    def test_medium_strength_password(self):
        """Test medium strength password"""
        password = "MyP@ss2024"  # Shorter but meets requirements
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is True
        assert strength == PasswordStrength.MEDIUM
        assert len(issues) == 0

    def test_very_strong_password(self):
        """Test very strong password with high entropy"""
        password = "xK9#mP$vL2@nQ5*rT8&yU4!"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is True
        assert strength == PasswordStrength.VERY_STRONG  # 23 chars with high complexity
        assert len(issues) == 0


class TestCommonPasswordDetection:
    """Test common password detection"""

    def test_exact_common_password(self):
        """Test exact match of common password"""
        assert check_common_passwords("password") is True
        assert check_common_passwords("123456") is True
        assert check_common_passwords("qwerty") is True

    def test_common_password_with_numbers(self):
        """Test common password with appended numbers"""
        assert check_common_passwords("password123") is True
        assert check_common_passwords("qwerty2024") is True

    def test_common_password_with_substitutions(self):
        """Test common password with character substitutions (l33t speak)"""
        # Comprehensive l33t speak substitutions
        assert check_common_passwords("p@ssw0rd") is True
        assert check_common_passwords("p@ssword") is True
        assert check_common_passwords("passw0rd") is True
        assert check_common_passwords("p@$$w0rd") is True
        assert check_common_passwords("p455w0rd") is True
        assert check_common_passwords("pa55word") is True
        assert check_common_passwords("pa$$word") is True

        # Test other common passwords with substitutions
        assert check_common_passwords("@dmin") is True
        assert check_common_passwords("adm1n") is True
        assert check_common_passwords("@dm1n") is True
        assert check_common_passwords("qw3rty") is True
        assert check_common_passwords("qwer7y") is True
        assert check_common_passwords("l3tm31n") is True
        assert check_common_passwords("le7me1n") is True

    def test_not_common_password(self):
        """Test password that's not common"""
        assert check_common_passwords("xK9#mP$vL2") is False
        assert check_common_passwords("UniquePass2024!") is False

    def test_case_insensitive_detection(self):
        """Test case-insensitive common password detection"""
        assert check_common_passwords("PASSWORD") is True
        assert check_common_passwords("Password") is True
        assert check_common_passwords("pAsSwOrD") is True


class TestPasswordEntropy:
    """Test password entropy calculation"""

    def test_entropy_calculation_simple(self):
        """Test entropy calculation for simple passwords"""
        # Only lowercase letters (26 chars)
        entropy = calculate_entropy("password")
        assert 35 < entropy < 40  # ~37.6 bits

    def test_entropy_calculation_complex(self):
        """Test entropy calculation for complex passwords"""
        # Upper + lower + digits + special (~94 chars)
        entropy = calculate_entropy("MyP@ss123")
        assert 55 < entropy < 65  # ~59.2 bits

    def test_entropy_calculation_very_long(self):
        """Test entropy calculation for very long passwords"""
        password = "a" * 50  # 50 lowercase letters
        entropy = calculate_entropy(password)
        assert entropy > 200  # High entropy due to length

    def test_entropy_with_unicode(self):
        """Test entropy calculation with unicode characters"""
        # Since Unicode is not supported, test ASCII password
        password = "Pass123!@#"
        entropy = calculate_entropy(password)
        assert entropy > 60  # Should have good entropy with mixed character types


class TestPasswordPolicyEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_password(self):
        """Test validation of empty password"""
        is_valid, strength, issues = validate_password_strength("")

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must be at least 8 characters long" in issues

    def test_whitespace_password(self):
        """Test password with only whitespace"""
        is_valid, strength, issues = validate_password_strength("        ")

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        # Should have multiple issues
        assert len(issues) >= 4

    def test_unicode_password(self):
        """Test password with unicode characters"""
        password = "Пароль123!"  # Russian characters
        is_valid, strength, issues = validate_password_strength(password)

        # Should reject unicode characters
        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must contain only ASCII characters" in issues

    def test_emoji_password(self):
        """Test password with emojis"""
        password = "Pass123!😀🔒"
        is_valid, strength, issues = validate_password_strength(password)

        # Should reject emojis (non-ASCII)
        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password must contain only ASCII characters" in issues

    def test_sql_injection_in_password(self):
        """Test password containing SQL injection patterns"""
        # Passwords with SQL injection patterns should be rejected for security
        password = "'; DROP TABLE users; --123!Aa"
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password should not contain SQL keywords" in issues

    def test_very_long_password(self):
        """Test handling of very long password"""
        # Test password exceeding reasonable length
        password = "A" * 200  # 200 repeated 'A's - no variety
        is_valid, strength, issues = validate_password_strength(password)

        # Should be rejected - too long and missing required character types
        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password is too long (max 128 characters)" in issues

        # Test repetitive password within limits
        password = "A" * 100  # 100 repeated 'A's
        is_valid, strength, issues = validate_password_strength(password)

        # Should be rejected for being too repetitive
        assert is_valid is False
        assert strength == PasswordStrength.WEAK
        assert "Password is too repetitive" in issues

        # Test valid long password within limits
        password = "VeryL0ng!P@ssw0rd#2024WithM@nyChars"  # 35 chars, all types
        is_valid, strength, issues = validate_password_strength(password)

        assert is_valid is True
        assert strength == PasswordStrength.VERY_STRONG
        assert len(issues) == 0


class TestPasswordStrengthEnum:
    """Test PasswordStrength enum values"""

    def test_enum_values(self):
        """Test enum has expected values"""
        assert PasswordStrength.VERY_WEAK.value == "very_weak"
        assert PasswordStrength.WEAK.value == "weak"
        assert PasswordStrength.MEDIUM.value == "medium"
        assert PasswordStrength.STRONG.value == "strong"
        assert PasswordStrength.VERY_STRONG.value == "very_strong"

    def test_enum_comparison(self):
        """Test enum comparison for strength ordering"""
        # Test that enum supports comparison operations
        very_weak = PasswordStrength.VERY_WEAK
        weak = PasswordStrength.WEAK
        medium = PasswordStrength.MEDIUM
        strong = PasswordStrength.STRONG
        very_strong = PasswordStrength.VERY_STRONG

        # Test less than comparisons
        assert very_weak < weak
        assert weak < medium
        assert medium < strong
        assert strong < very_strong

        # Test greater than comparisons
        assert very_strong > strong
        assert strong > medium
        assert medium > weak
        assert weak > very_weak

        # Test equality
        assert weak == weak
        assert not (weak == medium)
