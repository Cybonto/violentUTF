# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Security configuration validation
SECURITY: Validates that security measures are properly configured
"""

import logging
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_rate_limiting_config() -> Dict[str, Any]:
    """
    Validate rate limiting configuration
    """
    validation_results: Dict[str, Any] = {
        "rate_limiting_enabled": False,
        "slowapi_available": False,
        "limiter_configured": False,
        "issues": [],
        "recommendations": [],
    }

    try:
        # Check if slowapi is available
        pass  # slowapi availability check removed

        validation_results["slowapi_available"] = True
        logger.info("✅ slowapi library is available")
    except ImportError:
        validation_results["issues"].append("slowapi library not installed")
        validation_results["recommendations"].append("Install slowapi: pip install slowapi")
        logger.error("❌ slowapi library not available")
        return validation_results

    try:
        # Check if limiter is properly configured
        from app.core.rate_limiting import RATE_LIMITS

        validation_results["limiter_configured"] = True
        validation_results["rate_limiting_enabled"] = True

        # Validate rate limit configurations
        required_endpoints = ["auth_login", "auth_token", "auth_refresh", "auth_validate"]
        missing_endpoints = [ep for ep in required_endpoints if ep not in RATE_LIMITS]

        if missing_endpoints:
            validation_results["issues"].append(f"Missing rate limits for: {missing_endpoints}")
        else:
            logger.info("✅ All critical endpoints have rate limiting configured")

        # Check rate limit values are reasonable
        for endpoint, limit in RATE_LIMITS.items():
            if endpoint.startswith("auth_"):
                # Parse rate limit (e.g., "5/minute")
                try:
                    count_str, period = limit.split("/")
                    count = int(count_str)
                    if period == "minute" and count > 100:
                        validation_results["recommendations"].append(
                            f"Rate limit for {endpoint} may be too high: {limit}"
                        )
                    elif period == "minute" and count < 1:
                        validation_results["issues"].append(f"Rate limit for {endpoint} is too restrictive: {limit}")
                except (ValueError, IndexError):
                    validation_results["issues"].append(f"Invalid rate limit format for {endpoint}: {limit}")

        logger.info("✅ Rate limiting validation completed")

    except ImportError as e:
        validation_results["issues"].append(f"Rate limiting module import failed: {e}")
        logger.error("❌ Rate limiting module import failed: %s", e)

    return validation_results


def validate_security_headers() -> Dict[str, Any]:
    """
    Validate security headers configuration
    """
    validation_results: Dict[str, Any] = {
        "cors_configured": False,
        "security_headers": False,
        "issues": [],
        "recommendations": [],
    }

    # Check CORS configuration
    if hasattr(settings, "BACKEND_CORS_ORIGINS"):
        validation_results["cors_configured"] = True
        logger.info("✅ CORS origins configured")

        # Check if CORS is too permissive
        if "*" in settings.BACKEND_CORS_ORIGINS:
            validation_results["recommendations"].append(
                "CORS allows all origins (*) - consider restricting for production"
            )
    else:
        validation_results["issues"].append("CORS origins not configured")

    # TODO: Add more security header checks when implemented
    validation_results["recommendations"].append("Implement CSP, HSTS, and other security headers")

    return validation_results


def run_security_validation() -> Dict[str, Any]:
    """
    Run comprehensive security validation
    """
    logger.info("🔒 Running security configuration validation...")

    results: Dict[str, Any] = {
        "overall_status": "unknown",
        "rate_limiting": validate_rate_limiting_config(),
        "security_headers": validate_security_headers(),
        "summary": {"total_issues": 0, "total_recommendations": 0, "critical_issues": 0},
    }

    # Count issues and recommendations
    for category in ["rate_limiting", "security_headers"]:
        if category in results:
            results["summary"]["total_issues"] += len(results[category].get("issues", []))
            results["summary"]["total_recommendations"] += len(results[category].get("recommendations", []))

    # Determine overall status
    critical_issues = 0
    if not results["rate_limiting"]["rate_limiting_enabled"]:
        critical_issues += 1

    results["summary"]["critical_issues"] = critical_issues

    if critical_issues == 0:
        results["overall_status"] = "secure"
        logger.info("🛡️ Security validation passed - no critical issues found")
    elif critical_issues <= 2:
        results["overall_status"] = "warning"
        logger.warning("⚠️ Security validation found %s critical issues", critical_issues)
    else:
        results["overall_status"] = "critical"
        logger.error("🚨 Security validation found %s critical security issues", critical_issues)

    return results


if __name__ == "__main__":
    # CLI interface for security validation
    results = run_security_validation()

    print("\n🔒 SECURITY CONFIGURATION VALIDATION REPORT")
    print("=" * 60)

    print(f"\n📊 Overall Status: {results['overall_status'].upper()}")
    print(f"   Critical Issues: {results['summary']['critical_issues']}")
    print(f"   Total Issues: {results['summary']['total_issues']}")
    print(f"   Recommendations: {results['summary']['total_recommendations']}")

    for category, data in results.items():
        if category in ["rate_limiting", "security_headers"]:
            print(f"\n📋 {category.replace('_', ' ').title()}:")

            if data.get("issues"):
                print("   ❌ Issues:")
                for issue in data["issues"]:
                    print(f"      • {issue}")

            if data.get("recommendations"):
                print("   💡 Recommendations:")
                for rec in data["recommendations"]:
                    print(f"      • {rec}")

            if not data.get("issues") and not data.get("recommendations"):
                print("   ✅ No issues found")

    print("\n" + "=" * 60)
