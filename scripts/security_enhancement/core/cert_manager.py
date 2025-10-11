# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Certificate Manager

Certificate lifecycle management including inventory, expiration monitoring,
validation, and renewal automation.

Issue #273: Phase 6.2 - Database Encryption and Security Enhancement
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class CertificateManager:
    """Certificate lifecycle management"""

    def __init__(self, cert_base_path: Optional[str] = None) -> None:
        """
        Initialize certificate manager

        Args:
            cert_base_path: Optional base path for certificate discovery
        """
        if cert_base_path is None:
            cert_base_path = "/Users/tamnguyen/Documents/GitHub/violentUTF"
        self.cert_base_path = Path(cert_base_path)
        self.certificates: List[Dict[str, Any]] = []

    def inventory_certificates(self) -> Dict[str, Any]:
        """
        Inventory all certificates in system

        Returns:
            Certificate inventory
        """
        result = {"certificates": []}

        cert_extensions = ["*.pem", "*.crt", "*.cer", "*.key"]
        cert_dirs = [
            self.cert_base_path / "certs",
            self.cert_base_path / "violentutf_api" / "certs",
            self.cert_base_path / "apisix" / "certs",
            self.cert_base_path / "keycloak" / "certs",
        ]

        for cert_dir in cert_dirs:
            if not cert_dir.exists():
                continue

            for ext in cert_extensions:
                for cert_file in cert_dir.rglob(ext):
                    try:
                        stat_info = os.stat(cert_file)
                        perms = oct(stat_info.st_mode)[-3:]

                        cert_info = {
                            "path": str(cert_file),
                            "name": cert_file.name,
                            "permissions": perms,
                            "secure_permissions": perms in ["600", "400"],
                            "size": stat_info.st_size,
                            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        }

                        result["certificates"].append(cert_info)
                        self.certificates.append(cert_info)

                    except Exception as e:
                        result.setdefault("errors", []).append({"path": str(cert_file), "error": str(e)})

        result["count"] = len(result["certificates"])
        return result

    def monitor_expiration(self, alert_days: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Monitor certificate expiration

        Args:
            alert_days: Days before expiration for alerts (default: [30, 60, 90])

        Returns:
            Expiration monitoring results
        """
        if alert_days is None:
            alert_days = [30, 60, 90]

        result = {"expiring_soon": [], "alerts": [], "checked": 0}

        # For validation purposes, we check modification dates
        # In production, you would parse actual certificate expiration dates
        now = datetime.now()

        for cert in self.certificates:
            result["checked"] += 1

            # Simulate expiration check based on file modification time
            # (In production, parse actual cert expiration from x509)
            modified = datetime.fromisoformat(cert["modified"])
            age_days = (now - modified).days

            # Treat files older than 300 days as potentially expiring soon
            if age_days > 300:
                days_to_expiry = 365 - age_days
                if days_to_expiry < max(alert_days):
                    result["expiring_soon"].append(
                        {
                            "certificate": cert["name"],
                            "path": cert["path"],
                            "estimated_expiry_days": days_to_expiry,
                        }
                    )

                    for alert_threshold in alert_days:
                        if days_to_expiry <= alert_threshold:
                            result["alerts"].append(
                                {
                                    "severity": "critical" if alert_threshold == 30 else "warning",  # noqa: E501
                                    "certificate": cert["name"],
                                    "days_remaining": days_to_expiry,
                                    "alert_threshold": alert_threshold,
                                }
                            )
                            break

        return result

    def validate_certificates(self) -> Dict[str, Any]:
        """
        Validate certificates

        Returns:
            Validation results
        """
        result = {"validation_results": [], "total": 0, "valid": 0, "invalid": 0}

        for cert in self.certificates:
            validation = {
                "certificate": cert["name"],
                "path": cert["path"],
                "checks": {},
            }

            # Check file permissions
            validation["checks"]["permissions"] = {
                "status": "pass" if cert["secure_permissions"] else "fail",
                "value": cert["permissions"],
            }

            # Check file size (basic sanity check)
            validation["checks"]["file_size"] = {
                "status": "pass" if cert["size"] > 0 else "fail",
                "value": cert["size"],
            }

            # Determine overall status
            all_checks_pass = all(check["status"] == "pass" for check in validation["checks"].values())
            validation["overall_status"] = "valid" if all_checks_pass else "invalid"

            if all_checks_pass:
                result["valid"] += 1
            else:
                result["invalid"] += 1

            result["validation_results"].append(validation)
            result["total"] += 1

        return result

    def prepare_renewal(self) -> Dict[str, Any]:
        """
        Prepare certificate renewal plan

        Returns:
            Renewal plan
        """
        result = {"renewal_plan": [], "status": "prepared"}

        expiring = self.monitor_expiration()

        for cert_info in expiring.get("expiring_soon", []):
            result["renewal_plan"].append(
                {
                    "certificate": cert_info["certificate"],
                    "path": cert_info["path"],
                    "priority": "high" if cert_info["estimated_expiry_days"] < 30 else "medium",  # noqa: E501
                    "action": "renew_before_expiration",
                }
            )

        return result
