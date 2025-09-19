# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Notification Service for Issue #283.

This module implements a multi-channel notification system for monitoring alerts,
supporting Slack, email, webhook, and SMS delivery channels with escalation support.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import AlertSeverity, MonitoringAlert, NotificationChannel, NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing multi-channel notifications and alerts."""

    def __init__(self, db: AsyncSession, config: Dict[str, Any]) -> None:
        """Initialize the notification service.

        Args:
            db: Database session
            config: Configuration dictionary with channel settings
        """
        self.db = db
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.retry_intervals = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr

    async def send_notification(
        self,
        channel: NotificationChannel,
        subject: str,
        message: str,
        priority: str = "MEDIUM",
        recipient: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification through specified channel.

        Args:
            channel: Notification channel to use
            subject: Notification subject
            message: Notification message
            priority: Priority level (LOW, MEDIUM, HIGH, CRITICAL)
            recipient: Specific recipient (optional)
            metadata: Additional metadata

        Returns:
            True if notification was sent successfully
        """
        try:
            # Determine recipient if not specified
            if not recipient:
                recipient = self.get_default_recipient(channel, priority)

            # Format message for channel
            formatted_message = await self.format_message_for_channel(channel, subject, message, metadata)

            # Send via appropriate channel
            if channel == NotificationChannel.SLACK_MONITORING:
                success = await self.send_slack_notification(recipient, formatted_message)
            elif channel == NotificationChannel.SLACK_CRITICAL:
                success = await self.send_slack_notification(recipient, formatted_message)
            elif channel == NotificationChannel.EMAIL:
                success = await self.send_email_notification(recipient, subject, formatted_message)
            elif channel == NotificationChannel.WEBHOOK:
                success = await self.send_webhook_notification(recipient, formatted_message, metadata)
            elif channel == NotificationChannel.SMS:
                success = await self.send_sms_notification(recipient, formatted_message)
            else:
                logger.error("Unsupported notification channel: %s", channel)
                return False

            logger.info("Notification sent via %s to %s: %s", channel.value, recipient, success)
            return success

        except Exception as e:
            logger.error("Error sending notification via %s: %s", channel.value, e)
            return False

    async def send_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        affected_assets: Optional[List[str]] = None,
        correlation_key: Optional[str] = None,
        escalation_rules: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send an alert with escalation support.

        Args:
            severity: Alert severity level
            title: Alert title
            message: Alert message
            affected_assets: List of affected asset IDs
            correlation_key: Key for alert correlation
            escalation_rules: Custom escalation rules

        Returns:
            Alert ID for tracking
        """
        try:
            # Create alert record
            alert = await self.create_alert_record(
                severity=severity,
                title=title,
                message=message,
                affected_assets=affected_assets,
                correlation_key=correlation_key,
                escalation_rules=escalation_rules,
            )

            # Determine notification channels based on severity
            channels = self.get_channels_for_severity(severity)

            # Send initial notifications
            for channel in channels:
                success = await self.send_notification(
                    channel=channel,
                    subject=f"[{severity.value}] {title}",
                    message=message,
                    priority=severity.value,
                    metadata={
                        "alert_id": str(alert.id),
                        "severity": severity.value,
                        "affected_assets": affected_assets or [],
                    },
                )

                # Log notification attempt
                await self.log_notification_attempt(
                    alert_id=alert.id,
                    channel=channel,
                    recipient=self.get_default_recipient(channel, severity.value),
                    subject=f"[{severity.value}] {title}",
                    message=message,
                    success=success,
                )

            # Schedule escalation if rules are defined
            if escalation_rules or severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                await self.schedule_alert_escalation(alert.id, escalation_rules)

            return str(alert.id)

        except Exception as e:
            logger.error("Error sending alert: %s", e)
            raise

    async def send_slack_notification(self, webhook_url: str, message: str) -> bool:
        """Send notification via Slack webhook.

        Args:
            webhook_url: Slack webhook URL
            message: Message to send

        Returns:
            True if sent successfully
        """
        try:
            payload = {"text": message}

            response = await self.http_client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            return response.status_code == 200

        except Exception as e:
            logger.error("Error sending Slack notification: %s", e)
            return False

    async def send_email_notification(self, recipient: str, subject: str, message: str) -> bool:
        """Send notification via email.

        Args:
            recipient: Email recipient
            subject: Email subject
            message: Email message

        Returns:
            True if sent successfully
        """
        try:
            # This would integrate with an email service (SMTP, SendGrid, etc.)
            # For now, just log the notification
            logger.info("Email notification: To=%s, Subject=%s", recipient, subject)

            # Placeholder for actual email sending logic
            email_config = self.config.get("email", {})
            smtp_server = email_config.get("smtp_server")

            if not smtp_server:
                logger.warning("Email SMTP server not configured")
                return False

            # Actual email sending would happen here
            return True

        except Exception as e:
            logger.error("Error sending email notification: %s", e)
            return False

    async def send_webhook_notification(
        self, webhook_url: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification via webhook.

        Args:
            webhook_url: Webhook URL
            message: Message to send
            metadata: Additional metadata

        Returns:
            True if sent successfully
        """
        try:
            payload = {
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }

            response = await self.http_client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            return response.status_code in [200, 201, 202]

        except Exception as e:
            logger.error("Error sending webhook notification: %s", e)
            return False

    async def send_sms_notification(self, phone_number: str, message: str) -> bool:
        """Send notification via SMS.

        Args:
            phone_number: Phone number to send to
            message: SMS message

        Returns:
            True if sent successfully
        """
        try:
            # This would integrate with an SMS service (Twilio, AWS SNS, etc.)
            # For now, just log the notification
            logger.info("SMS notification: To=%s, Message=%s...", phone_number, message[:50])

            sms_config = self.config.get("sms", {})
            if not sms_config.get("enabled", False):
                logger.warning("SMS notifications not enabled")
                return False

            # Actual SMS sending would happen here
            return True

        except Exception as e:
            logger.error("Error sending SMS notification: %s", e)
            return False

    async def format_message_for_channel(
        self,
        channel: NotificationChannel,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format message for specific notification channel.

        Args:
            channel: Notification channel
            subject: Message subject
            message: Message content
            metadata: Additional metadata

        Returns:
            Formatted message string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        if channel in [NotificationChannel.SLACK_MONITORING, NotificationChannel.SLACK_CRITICAL]:
            # Format for Slack with markdown
            formatted = f"*{subject}*\n\n{message}\n\n_Time: {timestamp}_"

            if metadata:
                formatted += f"\n_Metadata: {json.dumps(metadata, indent=2)}_"

            return formatted

        elif channel == NotificationChannel.EMAIL:
            # Format for email (HTML could be added here)
            return f"{message}\n\nTime: {timestamp}"

        elif channel in [NotificationChannel.WEBHOOK, NotificationChannel.SMS]:
            # Plain text format
            return f"{subject}\n\n{message}\n\nTime: {timestamp}"

        return message

    def get_default_recipient(self, channel: NotificationChannel, priority: str) -> str:
        """Get default recipient for channel and priority.

        Args:
            channel: Notification channel
            priority: Message priority

        Returns:
            Default recipient string
        """
        channel_config = self.config.get("channels", {}).get(channel.value, {})

        # Check for priority-specific recipients
        priority_recipients = channel_config.get("recipients_by_priority", {})
        if priority in priority_recipients:
            return priority_recipients[priority]

        # Fallback to default recipient
        return channel_config.get("default_recipient", "")

    def get_channels_for_severity(self, severity: AlertSeverity) -> List[NotificationChannel]:
        """Get notification channels for alert severity.

        Args:
            severity: Alert severity level

        Returns:
            List of notification channels
        """
        severity_config = self.config.get("severity_channels", {})

        if severity == AlertSeverity.CRITICAL:
            return severity_config.get(
                "CRITICAL",
                [
                    NotificationChannel.SLACK_CRITICAL,
                    NotificationChannel.EMAIL,
                    NotificationChannel.SMS,
                ],
            )
        elif severity == AlertSeverity.HIGH:
            return severity_config.get(
                "HIGH",
                [
                    NotificationChannel.SLACK_CRITICAL,
                    NotificationChannel.EMAIL,
                ],
            )
        elif severity == AlertSeverity.MEDIUM:
            return severity_config.get(
                "MEDIUM",
                [
                    NotificationChannel.SLACK_MONITORING,
                    NotificationChannel.EMAIL,
                ],
            )
        else:  # LOW
            return severity_config.get(
                "LOW",
                [
                    NotificationChannel.SLACK_MONITORING,
                ],
            )

    async def create_alert_record(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        affected_assets: Optional[List[str]] = None,
        correlation_key: Optional[str] = None,
        escalation_rules: Optional[Dict[str, Any]] = None,
    ) -> MonitoringAlert:
        """Create alert record in database.

        Args:
            severity: Alert severity
            title: Alert title
            message: Alert message
            affected_assets: List of affected asset IDs
            correlation_key: Correlation key for deduplication
            escalation_rules: Custom escalation rules

        Returns:
            Created MonitoringAlert instance
        """
        import uuid

        from app.models.monitoring import AlertStatus

        alert = MonitoringAlert(
            id=uuid.uuid4(),
            event_id=uuid.uuid4(),  # This would be linked to an actual event
            asset_id=uuid.UUID(affected_assets[0]) if affected_assets else None,
            title=title,
            message=message,
            severity=severity,
            status=AlertStatus.ACTIVE,
            escalation_rules=escalation_rules,
            correlation_key=correlation_key,
            notification_channels=[channel.value for channel in self.get_channels_for_severity(severity)],
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def log_notification_attempt(
        self,
        alert_id: str,
        channel: NotificationChannel,
        recipient: str,
        subject: str,
        message: str,
        success: bool,
    ) -> None:
        """Log notification attempt in database.

        Args:
            alert_id: Alert ID
            channel: Notification channel
            recipient: Notification recipient
            subject: Notification subject
            message: Notification message
            success: Whether notification was successful
        """
        import uuid

        notification_log = NotificationLog(
            id=uuid.uuid4(),
            alert_id=uuid.UUID(alert_id),
            channel=channel,
            recipient=recipient,
            subject=subject,
            message=message,
            delivery_status="SENT" if success else "FAILED",
            delivered_at=datetime.now(timezone.utc) if success else None,
        )

        self.db.add(notification_log)
        await self.db.commit()

    async def schedule_alert_escalation(self, alert_id: str, escalation_rules: Optional[Dict[str, Any]] = None) -> None:
        """Schedule alert escalation.

        Args:
            alert_id: Alert ID
            escalation_rules: Custom escalation rules
        """
        # This would schedule escalation tasks
        # For now, just log the escalation scheduling
        logger.info("Scheduling escalation for alert %s", alert_id)

        # Default escalation rules
        if not escalation_rules:
            escalation_rules = {
                "intervals": [900, 3600, 7200],  # 15min, 1hr, 2hr
                "escalate_to": ["manager", "on-call"],
            }

        # Schedule escalation tasks (would use Celery, RQ, or similar)
        for i, interval in enumerate(escalation_rules.get("intervals", [])):
            asyncio.create_task(self.escalate_alert_after_delay(alert_id, interval, i + 1))

    async def escalate_alert_after_delay(self, alert_id: str, delay_seconds: int, escalation_level: int) -> None:
        """Escalate alert after specified delay.

        Args:
            alert_id: Alert ID
            delay_seconds: Delay in seconds
            escalation_level: Escalation level
        """
        await asyncio.sleep(delay_seconds)

        # Check if alert is still active
        alert = await self.get_alert_by_id(alert_id)
        if alert and alert.status == "ACTIVE":
            logger.info("Escalating alert %s to level %s", alert_id, escalation_level)

            # Send escalation notification
            await self.send_escalation_notification(alert, escalation_level)

            # Update alert escalation level
            await self.update_alert_escalation_level(alert_id, escalation_level)

    async def send_escalation_notification(self, alert: MonitoringAlert, escalation_level: int) -> None:
        """Send escalation notification.

        Args:
            alert: Alert to escalate
            escalation_level: Escalation level
        """
        escalation_message = (
            f"ESCALATION LEVEL {escalation_level}\n\n"
            f"Alert: {alert.title}\n"
            f"Original Message: {alert.message}\n"
            f"Alert has not been acknowledged after {escalation_level * 15} minutes."
        )

        # Send via critical channels
        for channel in [NotificationChannel.SLACK_CRITICAL, NotificationChannel.EMAIL]:
            await self.send_notification(
                channel=channel,
                subject=f"[ESCALATION L{escalation_level}] {alert.title}",
                message=escalation_message,
                priority="CRITICAL",
                metadata={
                    "alert_id": str(alert.id),
                    "escalation_level": escalation_level,
                },
            )

    async def get_alert_by_id(self, alert_id: str) -> Optional[MonitoringAlert]:
        """Get alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            MonitoringAlert instance if found
        """
        import uuid

        from sqlalchemy import select

        result = await self.db.execute(select(MonitoringAlert).where(MonitoringAlert.id == uuid.UUID(alert_id)))
        return result.scalar_one_or_none()

    async def update_alert_escalation_level(self, alert_id: str, escalation_level: int) -> None:
        """Update alert escalation level.

        Args:
            alert_id: Alert ID
            escalation_level: New escalation level
        """
        alert = await self.get_alert_by_id(alert_id)
        if alert:
            alert.escalation_level = escalation_level
            await self.db.commit()

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str, reason: Optional[str] = None) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: User acknowledging the alert
            reason: Optional acknowledgment reason

        Returns:
            True if acknowledgment was successful
        """
        try:
            alert = await self.get_alert_by_id(alert_id)
            if not alert:
                return False

            from app.models.monitoring import AlertStatus

            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by = acknowledged_by

            await self.db.commit()

            # Send acknowledgment notification
            await self.send_notification(
                channel=NotificationChannel.SLACK_MONITORING,
                subject=f"Alert Acknowledged: {alert.title}",
                message=f"Alert has been acknowledged by {acknowledged_by}\n"
                f"Reason: {reason or 'No reason provided'}",
                priority="LOW",
                metadata={
                    "alert_id": str(alert.id),
                    "acknowledged_by": acknowledged_by,
                },
            )

            return True

        except Exception as e:
            logger.error("Error acknowledging alert %s: %s", alert_id, e)
            return False

    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_reason: str) -> bool:
        """Resolve an alert.

        Args:
            alert_id: Alert ID
            resolved_by: User resolving the alert
            resolution_reason: Reason for resolution

        Returns:
            True if resolution was successful
        """
        try:
            alert = await self.get_alert_by_id(alert_id)
            if not alert:
                return False

            from app.models.monitoring import AlertStatus

            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by = resolved_by
            alert.resolution_reason = resolution_reason

            await self.db.commit()

            # Send resolution notification
            await self.send_notification(
                channel=NotificationChannel.SLACK_MONITORING,
                subject=f"Alert Resolved: {alert.title}",
                message=f"Alert has been resolved by {resolved_by}\n" f"Resolution: {resolution_reason}",
                priority="LOW",
                metadata={
                    "alert_id": str(alert.id),
                    "resolved_by": resolved_by,
                },
            )

            return True

        except Exception as e:
            logger.error("Error resolving alert %s: %s", alert_id, e)
            return False

    async def close(self) -> None:
        """Close the notification service and cleanup resources."""
        await self.http_client.aclose()
