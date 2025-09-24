# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for Alerting and Notification System functionality - Issue #265."""

import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.services.config_monitoring import (
    AlertManager,
    AlertRule,
    AlertChannel,
    NotificationResult,
    DriftAlert,
)


class TestAlertRule:
    """Test AlertRule class functionality."""

    def test_create_alert_rule(self):
        """Test creating an alert rule."""
        # GIVEN: Alert rule parameters
        rule = AlertRule(
            rule_id="critical_config_change",
            name="Critical Configuration Change",
            description="Alert on critical configuration changes",
            severity_threshold="critical",
            service_filter=["keycloak", "fastapi"],
            enabled=True
        )
        
        # THEN: Rule should be created correctly
        assert rule.rule_id == "critical_config_change"
        assert rule.name == "Critical Configuration Change"
        assert rule.severity_threshold == "critical"
        assert rule.service_filter == ["keycloak", "fastapi"]
        assert rule.enabled is True

    def test_alert_rule_matches_drift_critical(self):
        """Test alert rule matching for critical drift."""
        # GIVEN: Critical severity rule
        rule = AlertRule(
            rule_id="critical_rule",
            name="Critical Rule",
            description="Critical changes only",
            severity_threshold="critical",
            service_filter=None,  # All services
            enabled=True
        )
        
        # WHEN: Checking drift with critical severity
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "password", "old", "new", "critical")
            ]
        )
        
        # THEN: Rule should match
        assert rule.matches_drift(drift_result, "keycloak") is True

    def test_alert_rule_matches_drift_high_with_critical_threshold(self):
        """Test alert rule not matching when severity below threshold."""
        # GIVEN: Critical severity rule
        rule = AlertRule(
            rule_id="critical_rule",
            name="Critical Rule",
            description="Critical changes only",
            severity_threshold="critical",
            service_filter=None,
            enabled=True
        )
        
        # WHEN: Checking drift with high severity (below threshold)
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "port", 5432, 5433, "high")
            ]
        )
        
        # THEN: Rule should not match
        assert rule.matches_drift(drift_result, "keycloak") is False

    def test_alert_rule_service_filter(self):
        """Test alert rule service filtering."""
        # GIVEN: Rule with specific service filter
        rule = AlertRule(
            rule_id="keycloak_rule",
            name="Keycloak Rule",
            description="Keycloak only",
            severity_threshold="medium",
            service_filter=["keycloak"],
            enabled=True
        )
        
        # WHEN: Checking drift for different services
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "host", "old", "new", "medium")
            ]
        )
        
        # THEN: Should match keycloak but not fastapi
        assert rule.matches_drift(drift_result, "keycloak") is True
        assert rule.matches_drift(drift_result, "fastapi") is False

    def test_alert_rule_disabled(self):
        """Test disabled alert rule."""
        # GIVEN: Disabled alert rule
        rule = AlertRule(
            rule_id="disabled_rule",
            name="Disabled Rule",
            description="Disabled rule",
            severity_threshold="low",
            service_filter=None,
            enabled=False
        )
        
        # WHEN: Checking any drift
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "anything", "old", "new", "critical")
            ]
        )
        
        # THEN: Should not match (disabled)
        assert rule.matches_drift(drift_result, "any_service") is False


class TestAlertChannel:
    """Test AlertChannel class functionality."""

    def test_create_email_alert_channel(self):
        """Test creating email alert channel."""
        # GIVEN: Email channel parameters
        channel = AlertChannel(
            channel_id="ops_email",
            name="Operations Email",
            channel_type="email",
            configuration={
                "recipients": ["ops@example.com", "admin@example.com"],
                "smtp_server": "smtp.example.com",
                "smtp_port": 587
            },
            enabled=True
        )
        
        # THEN: Channel should be created correctly
        assert channel.channel_id == "ops_email"
        assert channel.channel_type == "email"
        assert channel.configuration["recipients"] == ["ops@example.com", "admin@example.com"]
        assert channel.enabled is True

    def test_create_slack_alert_channel(self):
        """Test creating Slack alert channel."""
        # GIVEN: Slack channel parameters
        channel = AlertChannel(
            channel_id="ops_slack",
            name="Operations Slack",
            channel_type="slack",
            configuration={
                "webhook_url": "https://hooks.slack.com/services/...",
                "channel": "#operations",
                "username": "ConfigBot"
            },
            enabled=True
        )
        
        # THEN: Channel should be created correctly
        assert channel.channel_id == "ops_slack"
        assert channel.channel_type == "slack"
        assert channel.configuration["channel"] == "#operations"

    def test_create_webhook_alert_channel(self):
        """Test creating webhook alert channel."""
        # GIVEN: Webhook channel parameters
        channel = AlertChannel(
            channel_id="monitoring_webhook",
            name="Monitoring Webhook",
            channel_type="webhook",
            configuration={
                "url": "https://monitoring.example.com/alerts",
                "method": "POST",
                "headers": {"Authorization": "Bearer token123"}
            },
            enabled=True
        )
        
        # THEN: Channel should be created correctly
        assert channel.channel_id == "monitoring_webhook"
        assert channel.channel_type == "webhook"
        assert channel.configuration["url"] == "https://monitoring.example.com/alerts"


class TestDriftAlert:
    """Test DriftAlert class functionality."""

    def test_create_drift_alert(self):
        """Test creating drift alert."""
        # GIVEN: Drift alert parameters
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "password", "old", "new", "critical")
            ]
        )
        
        alert = DriftAlert(
            alert_id="alert_123",
            service_name="keycloak",
            baseline_id="baseline_456",
            drift_result=drift_result,
            rule_id="critical_rule",
            triggered_at=None
        )
        
        # THEN: Alert should be created correctly
        assert alert.alert_id == "alert_123"
        assert alert.service_name == "keycloak"
        assert alert.baseline_id == "baseline_456"
        assert alert.rule_id == "critical_rule"
        assert alert.severity == "critical"
        assert alert.change_count == 1

    def test_drift_alert_generate_title(self):
        """Test drift alert title generation."""
        # GIVEN: Drift alert
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "password", "old", "new", "critical"),
                DriftChange("modified", "port", 5432, 5433, "high")
            ]
        )
        
        alert = DriftAlert(
            alert_id="alert_123",
            service_name="keycloak",
            baseline_id="baseline_456",
            drift_result=drift_result,
            rule_id="critical_rule"
        )
        
        # WHEN: Generating title
        title = alert.generate_title()
        
        # THEN: Title should contain key information
        assert "keycloak" in title.lower()
        assert "critical" in title.lower()
        assert "2" in title  # Change count

    def test_drift_alert_generate_message(self):
        """Test drift alert message generation."""
        # GIVEN: Drift alert
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "database.password", "old_pass", "new_pass", "critical")
            ]
        )
        
        alert = DriftAlert(
            alert_id="alert_123",
            service_name="keycloak",
            baseline_id="baseline_456",
            drift_result=drift_result,
            rule_id="critical_rule"
        )
        
        # WHEN: Generating message
        message = alert.generate_message()
        
        # THEN: Message should contain detailed information
        assert "keycloak" in message
        assert "database.password" in message
        assert "critical" in message.lower()
        assert "baseline_456" in message


class TestNotificationResult:
    """Test NotificationResult class functionality."""

    def test_notification_result_success(self):
        """Test successful notification result."""
        # GIVEN: Successful notification
        result = NotificationResult(
            channel_id="ops_email",
            success=True,
            message="Email sent successfully",
            sent_at=None
        )
        
        # THEN: Result should indicate success
        assert result.channel_id == "ops_email"
        assert result.success is True
        assert result.message == "Email sent successfully"
        assert result.sent_at is not None

    def test_notification_result_failure(self):
        """Test failed notification result."""
        # GIVEN: Failed notification
        result = NotificationResult(
            channel_id="ops_slack",
            success=False,
            message="Failed to send Slack message: Connection timeout",
            sent_at=None
        )
        
        # THEN: Result should indicate failure
        assert result.channel_id == "ops_slack"
        assert result.success is False
        assert "timeout" in result.message.lower()


@pytest.mark.asyncio
class TestAlertManager:
    """Test AlertManager class functionality."""

    async def test_create_alert_manager(self):
        """Test creating alert manager."""
        # GIVEN: Alert manager initialization
        manager = AlertManager()
        
        # THEN: Manager should be initialized
        assert manager is not None
        assert len(manager.rules) == 0
        assert len(manager.channels) == 0

    async def test_add_alert_rule(self):
        """Test adding alert rule."""
        # GIVEN: Alert manager and rule
        manager = AlertManager()
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test rule",
            severity_threshold="high",
            service_filter=None,
            enabled=True
        )
        
        # WHEN: Adding rule
        await manager.add_rule(rule)
        
        # THEN: Rule should be added
        assert len(manager.rules) == 1
        assert manager.rules["test_rule"] == rule

    async def test_add_alert_channel(self):
        """Test adding alert channel."""
        # GIVEN: Alert manager and channel
        manager = AlertManager()
        channel = AlertChannel(
            channel_id="test_channel",
            name="Test Channel",
            channel_type="email",
            configuration={"recipients": ["test@example.com"]},
            enabled=True
        )
        
        # WHEN: Adding channel
        await manager.add_channel(channel)
        
        # THEN: Channel should be added
        assert len(manager.channels) == 1
        assert manager.channels["test_channel"] == channel

    async def test_process_drift_alert_match(self):
        """Test processing drift that matches alert rules."""
        # GIVEN: Alert manager with rule and channel
        manager = AlertManager()
        
        rule = AlertRule(
            rule_id="critical_rule",
            name="Critical Rule",
            description="Critical changes",
            severity_threshold="critical",
            service_filter=None,
            enabled=True
        )
        await manager.add_rule(rule)
        
        channel = AlertChannel(
            channel_id="test_channel",
            name="Test Channel",
            channel_type="test",
            configuration={},
            enabled=True
        )
        await manager.add_channel(channel)
        
        # Configure rule to use channel
        rule.channel_ids = ["test_channel"]
        
        # Mock the notification sending
        with patch.object(manager, '_send_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = NotificationResult(
                channel_id="test_channel",
                success=True,
                message="Test notification sent"
            )
            
            # WHEN: Processing critical drift
            from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
            drift_result = DriftResult(
                has_drift=True,
                changes=[
                    DriftChange("modified", "password", "old", "new", "critical")
                ]
            )
            
            results = await manager.process_drift_detection(
                service_name="keycloak",
                baseline_id="baseline_123",
                drift_result=drift_result
            )
            
            # THEN: Alert should be generated and notification sent
            assert len(results) == 1
            assert results[0].success is True
            mock_send.assert_called_once()

    async def test_process_drift_no_match(self):
        """Test processing drift that doesn't match any rules."""
        # GIVEN: Alert manager with high threshold rule
        manager = AlertManager()
        
        rule = AlertRule(
            rule_id="high_rule",
            name="High Rule",
            description="High changes only",
            severity_threshold="high",
            service_filter=None,
            enabled=True
        )
        await manager.add_rule(rule)
        
        # WHEN: Processing low severity drift
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "comment", "old", "new", "low")
            ]
        )
        
        results = await manager.process_drift_detection(
            service_name="keycloak",
            baseline_id="baseline_123",
            drift_result=drift_result
        )
        
        # THEN: No alerts should be generated
        assert len(results) == 0

    async def test_process_drift_disabled_rule(self):
        """Test processing drift with disabled rule."""
        # GIVEN: Alert manager with disabled rule
        manager = AlertManager()
        
        rule = AlertRule(
            rule_id="disabled_rule",
            name="Disabled Rule",
            description="Disabled rule",
            severity_threshold="low",
            service_filter=None,
            enabled=False  # Disabled
        )
        await manager.add_rule(rule)
        
        # WHEN: Processing any drift
        from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
        drift_result = DriftResult(
            has_drift=True,
            changes=[
                DriftChange("modified", "anything", "old", "new", "critical")
            ]
        )
        
        results = await manager.process_drift_detection(
            service_name="keycloak",
            baseline_id="baseline_123",
            drift_result=drift_result
        )
        
        # THEN: No alerts should be generated
        assert len(results) == 0

    async def test_send_email_notification(self):
        """Test sending email notification."""
        # GIVEN: Alert manager with email channel
        manager = AlertManager()
        
        channel = AlertChannel(
            channel_id="email_channel",
            name="Email Channel",
            channel_type="email",
            configuration={
                "recipients": ["ops@example.com"],
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "alerts@example.com",
                "password": "${EMAIL_PASSWORD}"
            },
            enabled=True
        )
        
        # Mock email sending
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # WHEN: Sending email notification
            from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
            drift_result = DriftResult(
                has_drift=True,
                changes=[
                    DriftChange("modified", "password", "old", "new", "critical")
                ]
            )
            
            alert = DriftAlert(
                alert_id="alert_123",
                service_name="keycloak",
                baseline_id="baseline_456",
                drift_result=drift_result,
                rule_id="critical_rule"
            )
            
            result = await manager._send_email_notification(channel, alert)
            
            # THEN: Email should be sent successfully
            assert result.success is True
            assert result.channel_id == "email_channel"
            mock_server.send_message.assert_called_once()

    async def test_send_slack_notification(self):
        """Test sending Slack notification."""
        # GIVEN: Alert manager with Slack channel
        manager = AlertManager()
        
        channel = AlertChannel(
            channel_id="slack_channel",
            name="Slack Channel",
            channel_type="slack",
            configuration={
                "webhook_url": "https://hooks.slack.com/services/test",
                "channel": "#ops",
                "username": "ConfigBot"
            },
            enabled=True
        )
        
        # Mock HTTP request
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="ok")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # WHEN: Sending Slack notification
            from violentutf_api.fastapi_app.app.services.config_monitoring import DriftResult, DriftChange
            drift_result = DriftResult(
                has_drift=True,
                changes=[
                    DriftChange("modified", "password", "old", "new", "critical")
                ]
            )
            
            alert = DriftAlert(
                alert_id="alert_123",
                service_name="keycloak",
                baseline_id="baseline_456",
                drift_result=drift_result,
                rule_id="critical_rule"
            )
            
            result = await manager._send_slack_notification(channel, alert)
            
            # THEN: Slack message should be sent successfully
            assert result.success is True
            assert result.channel_id == "slack_channel"

    async def test_get_alert_statistics(self):
        """Test getting alert statistics."""
        # GIVEN: Alert manager with rules and recent alerts
        manager = AlertManager()
        
        # Add some rules
        rule1 = AlertRule("rule1", "Rule 1", "Desc 1", "critical", None, True)
        rule2 = AlertRule("rule2", "Rule 2", "Desc 2", "high", None, False)
        await manager.add_rule(rule1)
        await manager.add_rule(rule2)
        
        # Add some channels
        channel1 = AlertChannel("chan1", "Channel 1", "email", {}, True)
        channel2 = AlertChannel("chan2", "Channel 2", "slack", {}, True)
        await manager.add_channel(channel1)
        await manager.add_channel(channel2)
        
        # WHEN: Getting statistics
        stats = await manager.get_alert_statistics()
        
        # THEN: Statistics should be correct
        assert stats["total_rules"] == 2
        assert stats["enabled_rules"] == 1
        assert stats["total_channels"] == 2
        assert stats["enabled_channels"] == 2