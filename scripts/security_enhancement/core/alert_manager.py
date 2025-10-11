# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Alert Manager

Alert and notification system for security monitoring and certificate
expiration alerts.

Issue #273: Phase 6.2 - Database Encryption and Security Enhancement
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class AlertManager:
    """Alert and notification management"""

    def __init__(self) -> None:
        """Initialize alert manager"""
        self.alert_history: List[Dict[str, Any]] = []

    def send_alert(
        self,
        severity: str,
        title: str,
        details: str,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send security alert

        Args:
            severity: Alert severity (low, medium, high, critical)
            title: Alert title
            details: Alert details
            channels: Optional list of notification channels

        Returns:
            Alert sending result
        """
        if channels is None:
            channels = ["log"]

        alert = {
            "id": len(self.alert_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "title": title,
            "details": details,
            "channels": channels,
            "sent": True,
        }

        self.alert_history.append(alert)

        result = {"sent": True, "alert_id": alert["id"], "channels": channels}

        return result

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get alert history

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        return self.alert_history[-limit:]
