# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Password strength validation and policy enforcement
SECURITY: Implements comprehensive password security requirements to prevent weak passwords
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PasswordStrength(Enum):
    """Password strength levels"""

    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class PasswordPolicy:
    """Password policy configuration"""

    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special_chars: bool = True
    min_special_chars: int = 1
    min_numbers: int = 1
    min_uppercase: int = 1
    min_lowercase: int = 1

    # Advanced requirements
    max_repeated_chars: int = 3
    max_sequential_chars: int = 3
    min_unique_chars: int = 8

    # Forbidden patterns
    forbid_common_passwords: bool = True
    forbid_keyboard_patterns: bool = True
    forbid_personal_info: bool = True


@dataclass
class PasswordValidationResult:
    """Result of password validation"""

    is_valid: bool
    strength: PasswordStrength
    score: int  # 0-100
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class PasswordValidator:
    """
    Comprehensive password validation and strength assessment
    """

    def __init__(self, policy: Optional[PasswordPolicy] = None):
        self.policy = policy or PasswordPolicy()
        self._load_common_passwords()
        self._load_keyboard_patterns()

    def _load_common_passwords(self):
        """Load common/weak passwords list"""
        # Top 100 most common passwords - in production, load from file
        self.common_passwords = {
            "password",
            "123456",
            "password123",
            "admin",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
            "1234567890",
            "abc123",
            "password1",
            "123456789",
            "welcome123",
            "admin123",
            "root",
            "toor",
            "pass",
            "test",
            "guest",
            "user",
            "login",
            "access",
            "secret",
            "changeme",
            "default",
            "system",
            "master",
            "super",
            "administrator",
            "support",
            "help",
            "service",
            "temp",
            "temporary",
            "backup",
            "database",
            "server",
            "network",
            "security",
            "firewall",
            "router",
            "switch",
            "demo",
            "example",
            "sample",
            "training",
            "development",
            "staging",
            "production",
            "live",
            "public",
            "private",
            "internal",
            "external",
            "local",
            "remote",
            "office",
            "home",
            "work",
            "business",
            "company",
            "corporate",
            "enterprise",
            "manager",
            "supervisor",
            "director",
            "executive",
            "president",
            "ceo",
            "cto",
            "cfo",
            "hr",
            "it",
            "tech",
            "support",
            "helpdesk",
            "maintenance",
            "facility",
            "building",
            "floor",
            "room",
            "desk",
            "computer",
            "laptop",
            "mobile",
            "phone",
            "tablet",
            "device",
            "application",
            "software",
            "hardware",
            "firmware",
            "operating",
            "windows",
            "linux",
            "unix",
            "macos",
            "android",
            "ios",
            "web",
            "site",
            "portal",
            "dashboard",
            "control",
            "panel",
            "console",
            "terminal",
        }

    def _load_keyboard_patterns(self):
        """Load keyboard pattern sequences"""
        self.keyboard_patterns = [
            # QWERTY rows
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
            # Number sequences
            "1234567890",
            "0987654321",
            # Common sequences
            "abcdefghijklmnopqrstuvwxyz",
            "zyxwvutsrqponmlkjihgfedcba",
            # Keyboard walks
            "qaz",
            "wsx",
            "edc",
            "rfv",
            "tgb",
            "yhn",
            "ujm",
            "ik",
            "ol",
            "p",
            "plm",
            "okn",
            "ijn",
            "uhb",
            "ygv",
            "tfc",
            "rdx",
            "esz",
            "waq",
            "147",
            "258",
            "369",
            "159",
            "753",
            "951",
            "357",
            "159",
            "753",
        ]

    def validate_password(
        self,
        password: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        personal_info: Optional[List[str]] = None,
    ) -> PasswordValidationResult:
        """
        Comprehensive password validation

        Args:
            password: Password to validate
            username: Username for personal info checking
            email: Email for personal info checking
            personal_info: Additional personal information to check against

        Returns:
            PasswordValidationResult with validation details
        """
        errors = []
        warnings = []
        suggestions = []
        score = 0

        if not password:
            return PasswordValidationResult(
                is_valid=False,
                strength=PasswordStrength.VERY_WEAK,
                score=0,
                errors=["Password is required"],
                warnings=[],
                suggestions=["Please provide a password"],
            )

        # Basic length checks
        if len(password) < self.policy.min_length:
            errors.append(f"Password must be at least {self.policy.min_length} characters long")
            suggestions.append(f"Add {self.policy.min_length - len(password)} more characters")
        elif len(password) >= self.policy.min_length:
            score += 15

        if len(password) > self.policy.max_length:
            errors.append(f"Password must not exceed {self.policy.max_length} characters")

        # Character type requirements
        uppercase_count = sum(1 for c in password if c.isupper())
        lowercase_count = sum(1 for c in password if c.islower())
        number_count = sum(1 for c in password if c.isdigit())
        special_count = sum(1 for c in password if not c.isalnum())

        if self.policy.require_uppercase and uppercase_count < self.policy.min_uppercase:
            errors.append(f"Password must contain at least {self.policy.min_uppercase} uppercase letter(s)")
            suggestions.append("Add uppercase letters (A-Z)")
        elif uppercase_count >= self.policy.min_uppercase:
            score += 15

        if self.policy.require_lowercase and lowercase_count < self.policy.min_lowercase:
            errors.append(f"Password must contain at least {self.policy.min_lowercase} lowercase letter(s)")
            suggestions.append("Add lowercase letters (a-z)")
        elif lowercase_count >= self.policy.min_lowercase:
            score += 15

        if self.policy.require_numbers and number_count < self.policy.min_numbers:
            errors.append(f"Password must contain at least {self.policy.min_numbers} number(s)")
            suggestions.append("Add numbers (0-9)")
        elif number_count >= self.policy.min_numbers:
            score += 15

        if self.policy.require_special_chars and special_count < self.policy.min_special_chars:
            errors.append(f"Password must contain at least {self.policy.min_special_chars} special character(s)")
            suggestions.append("Add special characters (!@#$%^&*)")
        elif special_count >= self.policy.min_special_chars:
            score += 15

        # Advanced pattern checks
        unique_chars = len(set(password.lower()))
        if unique_chars < self.policy.min_unique_chars:
            warnings.append(
                f"Password has only {unique_chars} unique characters (recommended: {self.policy.min_unique_chars})"
            )
            suggestions.append("Use more diverse characters")
        else:
            score += 10

        # Repetition check
        repeated_chars = self._check_repeated_characters(password)
        if repeated_chars > self.policy.max_repeated_chars:
            warnings.append(f"Password contains {repeated_chars} repeated characters in sequence")
            suggestions.append("Avoid repeating the same character multiple times")
        else:
            score += 5

        # Sequential characters check
        sequential_chars = self._check_sequential_characters(password)
        if sequential_chars > self.policy.max_sequential_chars:
            warnings.append(f"Password contains {sequential_chars} sequential characters")
            suggestions.append("Avoid sequences like 'abc' or '123'")
        else:
            score += 5

        # Common password check
        if self.policy.forbid_common_passwords:
            if password.lower() in self.common_passwords:
                errors.append("Password is too common and easily guessed")
                suggestions.append("Choose a more unique password")
            else:
                score += 15

        # Keyboard pattern check
        if self.policy.forbid_keyboard_patterns:
            keyboard_match = self._check_keyboard_patterns(password)
            if keyboard_match:
                warnings.append(f"Password contains keyboard pattern: {keyboard_match}")
                suggestions.append("Avoid keyboard patterns like 'qwerty'")
            else:
                score += 5

        # Personal information check
        if self.policy.forbid_personal_info:
            personal_match = self._check_personal_info(password, username, email, personal_info)
            if personal_match:
                errors.append(f"Password contains personal information: {personal_match}")
                suggestions.append("Don't use personal information in passwords")
            else:
                score += 10

        # Bonus points for length
        if len(password) >= 16:
            score += 5
        if len(password) >= 20:
            score += 5

        # Determine strength and validity
        strength = self._calculate_strength(score)
        is_valid = len(errors) == 0 and strength not in [PasswordStrength.VERY_WEAK, PasswordStrength.WEAK]

        # Add strength-based suggestions
        if strength == PasswordStrength.VERY_WEAK:
            suggestions.append("Consider using a password manager to generate a strong password")
        elif strength == PasswordStrength.WEAK:
            suggestions.append("Add more character types and length to improve strength")
        elif strength == PasswordStrength.MODERATE:
            suggestions.append("Consider adding more special characters or length")

        return PasswordValidationResult(
            is_valid=is_valid,
            strength=strength,
            score=min(score, 100),
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _check_repeated_characters(self, password: str) -> int:
        """Check for repeated character sequences"""
        max_repeated = 0
        current_repeated = 1

        for i in range(1, len(password)):
            if password[i].lower() == password[i - 1].lower():
                current_repeated += 1
            else:
                max_repeated = max(max_repeated, current_repeated)
                current_repeated = 1

        return max(max_repeated, current_repeated)

    def _check_sequential_characters(self, password: str) -> int:
        """Check for sequential character patterns"""
        max_sequential = 0

        # Check ascending sequences
        for i in range(len(password) - 2):
            seq_len = 1
            for j in range(i + 1, len(password)):
                if ord(password[j].lower()) == ord(password[j - 1].lower()) + 1:
                    seq_len += 1
                else:
                    break
            max_sequential = max(max_sequential, seq_len)

        # Check descending sequences
        for i in range(len(password) - 2):
            seq_len = 1
            for j in range(i + 1, len(password)):
                if ord(password[j].lower()) == ord(password[j - 1].lower()) - 1:
                    seq_len += 1
                else:
                    break
            max_sequential = max(max_sequential, seq_len)

        return max_sequential

    def _check_keyboard_patterns(self, password: str) -> Optional[str]:
        """Check for keyboard walking patterns"""
        password_lower = password.lower()

        for pattern in self.keyboard_patterns:
            # Check forward and reverse patterns
            for p in [pattern, pattern[::-1]]:
                for i in range(len(p) - 2):
                    if p[i : i + 3] in password_lower:
                        return p[i : i + 3]
                    if len(p) > 3 and p[i : i + 4] in password_lower:
                        return p[i : i + 4]

        return None

    def _check_personal_info(
        self,
        password: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        personal_info: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Check if password contains personal information"""
        password_lower = password.lower()

        # Check username
        if username and len(username) >= 3:
            if username.lower() in password_lower:
                return "username"

        # Check email parts
        if email:
            email_parts = email.lower().split("@")
            if len(email_parts[0]) >= 3 and email_parts[0] in password_lower:
                return "email"
            if len(email_parts) > 1:
                domain_parts = email_parts[1].split(".")
                for part in domain_parts:
                    if len(part) >= 3 and part in password_lower:
                        return "email domain"

        # Check additional personal info
        if personal_info:
            for info in personal_info:
                if info and len(info) >= 3 and info.lower() in password_lower:
                    return "personal information"

        return None

    def _calculate_strength(self, score: int) -> PasswordStrength:
        """Calculate password strength based on score"""
        if score < 30:
            return PasswordStrength.VERY_WEAK
        elif score < 50:
            return PasswordStrength.WEAK
        elif score < 70:
            return PasswordStrength.MODERATE
        elif score < 85:
            return PasswordStrength.STRONG
        else:
            return PasswordStrength.VERY_STRONG

    def generate_password_requirements(self) -> Dict:
        """Generate password requirements description for UI"""
        return {
            "min_length": self.policy.min_length,
            "max_length": self.policy.max_length,
            "requirements": {
                "uppercase": self.policy.require_uppercase,
                "lowercase": self.policy.require_lowercase,
                "numbers": self.policy.require_numbers,
                "special_chars": self.policy.require_special_chars,
                "min_special_chars": self.policy.min_special_chars,
                "min_numbers": self.policy.min_numbers,
            },
            "restrictions": {
                "max_repeated_chars": self.policy.max_repeated_chars,
                "max_sequential_chars": self.policy.max_sequential_chars,
                "min_unique_chars": self.policy.min_unique_chars,
                "no_common_passwords": self.policy.forbid_common_passwords,
                "no_keyboard_patterns": self.policy.forbid_keyboard_patterns,
                "no_personal_info": self.policy.forbid_personal_info,
            },
        }


# Default password validator instance
default_password_validator = PasswordValidator()


def validate_password_strength(
    password: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    personal_info: Optional[List[str]] = None,
) -> PasswordValidationResult:
    """
    Convenience function for password validation

    Args:
        password: Password to validate
        username: Username for personal info checking
        email: Email for personal info checking
        personal_info: Additional personal information

    Returns:
        PasswordValidationResult
    """
    return default_password_validator.validate_password(
        password=password, username=username, email=email, personal_info=personal_info
    )


def is_password_secure(password: str, **kwargs) -> bool:
    """
    Quick check if password meets security requirements

    Args:
        password: Password to check
        **kwargs: Additional arguments for validation

    Returns:
        True if password is secure, False otherwise
    """
    result = validate_password_strength(password, **kwargs)
    return result.is_valid and result.strength not in [PasswordStrength.VERY_WEAK, PasswordStrength.WEAK]
