#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
API Client utilities for Issue #284

Provides client interfaces for accessing dashboard API endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class DashboardAPIClient:
    """Client for dashboard API endpoints"""

    def __init__(self, base_url: str = "http://localhost:9080/api/v1") -> None:
        """Initialize API client"""
        self.base_url = base_url
        self.session = requests.Session()
        # Add authentication headers if needed
        # self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_asset_inventory_metrics(self) -> Dict[str, Any]:
        """Get asset inventory dashboard metrics"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/asset-inventory-metrics")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error getting asset inventory metrics: %s", e)
            # Return mock data on error
            return {
                "total_assets": 125,
                "assets_by_type": {"POSTGRESQL": 45, "SQLITE": 30, "DUCKDB": 25, "FILE_STORAGE": 25},
                "assets_by_environment": {"PRODUCTION": 50, "STAGING": 35, "DEVELOPMENT": 40},
                "critical_assets": 15,
                "high_risk_assets": 8,
                "compliance_score": 84.2,
                "monitoring_coverage": 92.0,
            }

    def get_risk_dashboard_metrics(self) -> Dict[str, Any]:
        """Get risk dashboard metrics"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/risk-metrics")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error getting risk dashboard metrics: %s", e)
            # Return mock data on error
            return {
                "average_risk_score": 12.5,
                "risk_distribution": {"LOW": 85, "MEDIUM": 25, "HIGH": 12, "CRITICAL": 3},
                "risk_velocity": 0.05,
                "predicted_30_day_change": 1.2,
                "high_priority_vulnerabilities": 15,
                "assets_requiring_attention": [],
            }

    def get_executive_report_data(self) -> Dict[str, Any]:
        """Get executive report data"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/executive-report")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error getting executive report data: %s", e)
            # Return mock data on error
            return {
                "summary": {
                    "total_assets": 125,
                    "security_posture_score": 78.5,
                    "compliance_percentage": 84.2,
                    "critical_findings": 5,
                },
                "trends": {"security_improvement": 5.2, "new_assets_30_days": 8, "resolved_vulnerabilities": 23},
                "recommendations": [],
            }

    def get_operational_metrics(self) -> Dict[str, Any]:
        """Get operational dashboard metrics"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard/operational-metrics")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error getting operational metrics: %s", e)
            # Return mock data on error
            return {
                "system_health": {
                    "api_response_time": 150,
                    "database_connections": 45,
                    "error_rate": 0.02,
                    "uptime_percentage": 99.95,
                },
                "alerts": [],
                "performance_metrics": {
                    "avg_query_time": 45,
                    "throughput_requests_per_second": 1250,
                    "memory_usage_percentage": 75.2,
                },
            }

    def get_compliance_summary(self, framework: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance dashboard summary"""
        try:
            url = f"{self.base_url}/dashboard/compliance-summary"
            if framework:
                url += f"?framework={framework}"

            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error getting compliance summary: %s", e)
            # Return mock data on error
            return {
                "overall_compliance_score": 82.3,
                "frameworks": {
                    "SOC2": {"score": 85.5, "compliant": True, "gaps": 2},
                    "GDPR": {"score": 78.1, "compliant": False, "gaps": 5},
                    "NIST": {"score": 83.7, "compliant": True, "gaps": 1},
                },
                "trending": {"direction": "improving", "change_percentage": 5.2, "period": "30_days"},
                "high_priority_gaps": 3,
                "total_assets_assessed": 15,
            }


class AssetManagementAPI:
    """Client for asset management API endpoints"""

    def __init__(self, base_url: str = "http://localhost:9080/api/v1") -> None:
        """Initialize asset management API client"""
        self.base_url = base_url
        self.session = requests.Session()

    async def get_assets(self, **filters: str) -> List[Dict[str, Any]]:
        """Get assets with optional filters"""
        try:
            # For now, return mock data
            # In real implementation, would make actual API call
            assets = [
                {
                    "id": f"asset-{i}",
                    "name": f"database-{i}",
                    "asset_type": ["POSTGRESQL", "SQLITE", "DUCKDB"][i % 3],
                    "environment": ["PRODUCTION", "STAGING", "DEVELOPMENT"][i % 3],
                    "risk_score": 10 + (i % 15),
                    "compliance_score": 80 + (i % 20),
                    "criticality_level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"][i % 4],
                    "owner_team": f"team-{i % 3}",
                    "technical_contact": f"admin{i}@example.com",
                    "updated_at": (datetime.now() - timedelta(days=i % 30)).isoformat(),
                }
                for i in range(1, 26)
            ]

            # Apply filters if provided
            if filters:
                filtered_assets = []
                for asset in assets:
                    include_asset = True

                    asset_types: Any = filters.get("asset_types", [])
                    if "asset_types" in filters and asset["asset_type"] not in asset_types:
                        include_asset = False
                    environments: Any = filters.get("environments", [])
                    if "environments" in filters and asset["environment"] not in environments:
                        include_asset = False

                    if include_asset:
                        filtered_assets.append(asset)

                return filtered_assets

            return assets

        except Exception as e:
            logger.error("Error getting assets: %s", e)
            return []

    async def get_latest_risk_assessment(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get latest risk assessment for an asset"""
        try:
            # Mock risk assessment data
            return {"risk_score": 15.5, "risk_level": "HIGH", "assessment_date": datetime.now().isoformat()}
        except Exception as e:
            logger.error("Error getting risk assessment for %s: %s", asset_id, e)
            return None

    async def get_compliance_status(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get compliance status for an asset"""
        try:
            # Mock compliance data
            return {
                "overall_score": 85.2,
                "frameworks": {"SOC2": {"score": 88.0, "compliant": True}, "GDPR": {"score": 82.4, "compliant": True}},
            }
        except Exception as e:
            logger.error("Error getting compliance status for %s: %s", asset_id, e)
            return None

    async def get_monitoring_status(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get monitoring status for an asset"""
        try:
            # Mock monitoring data
            return {"status": "ACTIVE", "last_check": datetime.now().isoformat(), "health": "HEALTHY"}
        except Exception as e:
            logger.error("Error getting monitoring status for %s: %s", asset_id, e)
            return None


class RiskAssessmentAPI:
    """Client for risk assessment API endpoints"""

    def __init__(self, base_url: str = "http://localhost:9080/api/v1") -> None:
        """Initialize risk assessment API client"""
        self.base_url = base_url
        self.session = requests.Session()

    async def get_risk_trends(self, asset_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get risk trend data for an asset"""
        try:
            # Mock trend data
            trend_data = []
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                trend_data.append(
                    {"date": date.strftime("%Y-%m-%d"), "risk_score": 10 + (i % 10), "vulnerability_count": 2 + (i % 5)}
                )
            return trend_data
        except Exception as e:
            logger.error("Error getting risk trends for %s: %s", asset_id, e)
            return []

    async def get_risk_predictions(self, asset_id: str) -> Dict[str, Any]:
        """Get risk predictions for an asset"""
        try:
            return {
                "asset_id": asset_id,
                "current_risk": 15.5,
                "predicted_risk_30_days": 18.2,
                "confidence": 0.85,
                "recommended_actions": [],
            }
        except Exception as e:
            logger.error("Error getting risk predictions for %s: %s", asset_id, e)
            return {}


class ComplianceMonitoringAPI:
    """Client for compliance monitoring API endpoints"""

    def __init__(self, base_url: str = "http://localhost:9080/api/v1") -> None:
        """Initialize compliance monitoring API client"""
        self.base_url = base_url
        self.session = requests.Session()

    async def get_compliance_gaps(self, asset_id: str) -> List[Dict[str, Any]]:
        """Get compliance gaps for an asset"""
        try:
            # Mock compliance gaps
            return [
                {
                    "framework": "SOC2",
                    "control_id": "CC6.1",
                    "description": "Logical access controls",
                    "severity": "MEDIUM",
                    "remediation_steps": ["Implement multi-factor authentication", "Review user access permissions"],
                }
            ]
        except Exception as e:
            logger.error("Error getting compliance gaps for %s: %s", asset_id, e)
            return []
