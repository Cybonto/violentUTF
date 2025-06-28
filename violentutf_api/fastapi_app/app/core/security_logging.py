"""
Comprehensive security logging and monitoring
SECURITY: Implements detailed security event logging for audit, compliance, and threat detection
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Request


# Security event types
class SecurityEventType(Enum):
    """Types of security events to log"""

    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_LOCKOUT = "auth_lockout"
    TOKEN_CREATED = "token_created"
    TOKEN_VALIDATED = "token_validated"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"

    # Password events
    PASSWORD_CHANGED = "password_changed"
    WEAK_PASSWORD = "weak_password"
    PASSWORD_STRENGTH_CHECK = "password_strength_check"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_WARNING = "rate_limit_warning"

    # Input validation events
    VALIDATION_FAILURE = "validation_failure"
    INJECTION_ATTEMPT = "injection_attempt"
    MALICIOUS_INPUT = "malicious_input"

    # API security events
    API_KEY_CREATED = "api_key_created"
    API_KEY_USED = "api_key_used"
    API_KEY_INVALID = "api_key_invalid"

    # System security events
    CONFIG_CHANGED = "config_changed"
    SECURITY_HEADER_VIOLATION = "security_header_violation"
    CORS_VIOLATION = "cors_violation"

    # Error and exception events
    SECURITY_ERROR = "security_error"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ATTACK_DETECTED = "attack_detected"


class SecuritySeverity(Enum):
    """Security event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure"""

    event_id: str
    timestamp: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    success: bool = True
    message: str = ""
    details: Dict[str, Any] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SecurityLogger:
    """
    Comprehensive security logging system
    """

    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
        self._setup_security_logger()

    def _setup_security_logger(self):
        """Setup dedicated security logger with appropriate formatting"""
        # Create security-specific formatter
        security_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - SECURITY - %(message)s"
        )

        # Ensure security logger has proper handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(security_formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity = SecuritySeverity.MEDIUM,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        success: bool = True,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        **kwargs,
    ):
        """
        Log a security event with comprehensive context

        Args:
            event_type: Type of security event
            severity: Event severity level
            user_id: User identifier
            username: Username
            ip_address: Client IP address
            endpoint: API endpoint accessed
            method: HTTP method
            success: Whether operation was successful
            message: Event message
            details: Additional event details
            request: FastAPI request object for automatic context extraction
            **kwargs: Additional details to include
        """
        # Generate unique event ID
        event_id = str(uuid.uuid4())[:12]

        # Extract information from request if provided
        if request:
            if not ip_address:
                ip_address = self._extract_client_ip(request)
            if not endpoint:
                endpoint = str(request.url.path)
            if not method:
                method = request.method

            # Extract user agent
            user_agent = request.headers.get("user-agent", "unknown")

            # Add request-specific details
            if details is None:
                details = {}
            details.update(
                {
                    "user_agent": user_agent,
                    "headers": dict(request.headers),
                    "query_params": dict(request.query_params),
                }
            )

        # Merge additional kwargs into details
        if details is None:
            details = {}
        details.update(kwargs)

        # Create security event
        event = SecurityEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=details.get("user_agent"),
            endpoint=endpoint,
            method=method,
            success=success,
            message=message,
            details=details,
        )

        # Log based on severity
        log_method = self._get_log_method(severity)
        log_message = self._format_security_event(event)
        log_method(log_message)

        # For critical events, also log to application logger
        if severity == SecuritySeverity.CRITICAL:
            app_logger = logging.getLogger("app")
            app_logger.critical(
                f"CRITICAL SECURITY EVENT: {event.event_type.value} - {message}"
            )

    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (be careful of spoofing)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (leftmost is original client)
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to client host
        if request.client:
            return request.client.host

        return "unknown"

    def _get_log_method(self, severity: SecuritySeverity):
        """Get appropriate logging method based on severity"""
        if severity == SecuritySeverity.CRITICAL:
            return self.logger.critical
        elif severity == SecuritySeverity.HIGH:
            return self.logger.error
        elif severity == SecuritySeverity.MEDIUM:
            return self.logger.warning
        else:
            return self.logger.info

    def _format_security_event(self, event: SecurityEvent) -> str:
        """Format security event for logging"""
        # Create structured log entry
        log_data = {
            "event_id": event.event_id,
            "type": event.event_type.value,
            "severity": event.severity.value,
            "timestamp": event.timestamp,
            "success": event.success,
            "message": event.message,
        }

        # Add context information
        if event.user_id:
            log_data["user_id"] = event.user_id
        if event.username:
            log_data["username"] = event.username
        if event.ip_address:
            log_data["ip"] = event.ip_address
        if event.endpoint:
            log_data["endpoint"] = event.endpoint
        if event.method:
            log_data["method"] = event.method

        # Add sanitized details (remove sensitive info)
        if event.details:
            sanitized_details = self._sanitize_details(event.details)
            if sanitized_details:
                log_data["details"] = sanitized_details

        return json.dumps(log_data, separators=(",", ":"))

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from details before logging"""
        if not details:
            return {}

        sanitized = {}
        sensitive_keys = {
            "password",
            "token",
            "secret",
            "key",
            "auth",
            "authorization",
            "cookie",
            "session",
            "api_key",
            "private",
            "jwt",
        }

        for key, value in details.items():
            key_lower = key.lower()

            # Skip sensitive keys
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, (list, tuple)):
                # Sanitize lists/tuples
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Limit string length and convert to string
                if isinstance(value, str) and len(value) > 500:
                    sanitized[key] = value[:500] + "..."
                else:
                    sanitized[key] = str(value)[:500]

        return sanitized


# Global security logger instance
security_logger = SecurityLogger()


# Convenience functions for common security events
def log_authentication_success(
    username: str, user_id: str = None, request: Request = None, **kwargs
):
    """Log successful authentication"""
    security_logger.log_security_event(
        event_type=SecurityEventType.AUTH_SUCCESS,
        severity=SecuritySeverity.LOW,
        username=username,
        user_id=user_id,
        success=True,
        message=f"User {username} authenticated successfully",
        request=request,
        **kwargs,
    )


def log_authentication_failure(
    username: str = None,
    request: Request = None,
    reason: str = "Invalid credentials",
    **kwargs,
):
    """Log failed authentication attempt"""
    security_logger.log_security_event(
        event_type=SecurityEventType.AUTH_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        username=username,
        success=False,
        message=f"Authentication failed: {reason}",
        request=request,
        reason=reason,
        **kwargs,
    )


def log_access_denied(
    username: str = None,
    endpoint: str = None,
    request: Request = None,
    reason: str = "Insufficient permissions",
    **kwargs,
):
    """Log access denied event"""
    security_logger.log_security_event(
        event_type=SecurityEventType.ACCESS_DENIED,
        severity=SecuritySeverity.MEDIUM,
        username=username,
        endpoint=endpoint,
        success=False,
        message=f"Access denied to {endpoint}: {reason}",
        request=request,
        reason=reason,
        **kwargs,
    )


def log_rate_limit_exceeded(
    username: str = None, request: Request = None, limit_type: str = "general", **kwargs
):
    """Log rate limit exceeded event"""
    security_logger.log_security_event(
        event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
        severity=SecuritySeverity.HIGH,
        username=username,
        success=False,
        message=f"Rate limit exceeded for {limit_type}",
        request=request,
        limit_type=limit_type,
        **kwargs,
    )


def log_validation_failure(
    request: Request = None, field: str = None, error: str = "Invalid input", **kwargs
):
    """Log input validation failure"""
    security_logger.log_security_event(
        event_type=SecurityEventType.VALIDATION_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        success=False,
        message=f"Validation failed for field {field}: {error}",
        request=request,
        field=field,
        error=error,
        **kwargs,
    )


def log_injection_attempt(
    request: Request = None, attack_type: str = "unknown", details: str = "", **kwargs
):
    """Log potential injection attack"""
    security_logger.log_security_event(
        event_type=SecurityEventType.INJECTION_ATTEMPT,
        severity=SecuritySeverity.HIGH,
        success=False,
        message=f"Potential {attack_type} injection attempt detected",
        request=request,
        attack_type=attack_type,
        attack_details=details,
        **kwargs,
    )


def log_weak_password_attempt(
    username: str = None, strength: str = "weak", request: Request = None, **kwargs
):
    """Log weak password attempt"""
    security_logger.log_security_event(
        event_type=SecurityEventType.WEAK_PASSWORD,
        severity=SecuritySeverity.MEDIUM,
        username=username,
        success=False,
        message=f"Weak password detected for user {username} (strength: {strength})",
        request=request,
        password_strength=strength,
        **kwargs,
    )


def log_api_key_usage(
    user_id: str = None, key_name: str = None, request: Request = None, **kwargs
):
    """Log API key usage"""
    security_logger.log_security_event(
        event_type=SecurityEventType.API_KEY_USED,
        severity=SecuritySeverity.LOW,
        user_id=user_id,
        success=True,
        message=f"API key {key_name} used successfully",
        request=request,
        key_name=key_name,
        **kwargs,
    )


def log_suspicious_activity(
    activity_type: str, request: Request = None, details: str = "", **kwargs
):
    """Log suspicious activity"""
    security_logger.log_security_event(
        event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
        severity=SecuritySeverity.HIGH,
        success=False,
        message=f"Suspicious activity detected: {activity_type}",
        request=request,
        activity_type=activity_type,
        activity_details=details,
        **kwargs,
    )


def log_security_error(
    error_type: str, error_message: str, request: Request = None, **kwargs
):
    """Log security-related error"""
    security_logger.log_security_event(
        event_type=SecurityEventType.SECURITY_ERROR,
        severity=SecuritySeverity.HIGH,
        success=False,
        message=f"Security error: {error_type} - {error_message}",
        request=request,
        error_type=error_type,
        error_message=error_message,
        **kwargs,
    )


def log_token_event(
    event_type: str,
    username: str = None,
    token_type: str = "access",
    request: Request = None,
    **kwargs,
):
    """Log token-related events"""
    event_map = {
        "created": SecurityEventType.TOKEN_CREATED,
        "validated": SecurityEventType.TOKEN_VALIDATED,
        "expired": SecurityEventType.TOKEN_EXPIRED,
        "invalid": SecurityEventType.TOKEN_INVALID,
    }

    security_event_type = event_map.get(event_type, SecurityEventType.TOKEN_VALIDATED)
    severity = (
        SecuritySeverity.MEDIUM
        if event_type in ["expired", "invalid"]
        else SecuritySeverity.LOW
    )
    success = event_type in ["created", "validated"]

    security_logger.log_security_event(
        event_type=security_event_type,
        severity=severity,
        username=username,
        success=success,
        message=f"Token {event_type}: {token_type} token for user {username}",
        request=request,
        token_type=token_type,
        **kwargs,
    )


# Security metrics and monitoring
class SecurityMetrics:
    """Track security metrics for monitoring"""

    def __init__(self):
        self.metrics = {
            "auth_failures": 0,
            "rate_limit_exceeded": 0,
            "validation_failures": 0,
            "injection_attempts": 0,
            "suspicious_activities": 0,
        }
        self.last_reset = time.time()

    def increment(self, metric: str):
        """Increment a security metric"""
        if metric in self.metrics:
            self.metrics[metric] += 1

    def get_metrics(self) -> Dict[str, int]:
        """Get current security metrics"""
        return self.metrics.copy()

    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {key: 0 for key in self.metrics}
        self.last_reset = time.time()


# Global security metrics instance
security_metrics = SecurityMetrics()
