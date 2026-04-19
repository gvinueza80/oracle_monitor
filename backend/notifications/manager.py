"""Notification delivery system"""

import logging
import smtplib
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiohttp
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Base class for notification channels"""

    @abstractmethod
    async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """Send notification through this channel"""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel"""

    async def send(
        self,
        recipient: str,
        subject: str,
        message: str,
        html: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send email notification"""
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM_ADDRESS
            msg["To"] = recipient

            # Plain text part
            msg.attach(MIMEText(message, "plain"))

            # HTML part (if provided)
            if html:
                msg.attach(MIMEText(html, "html"))

            # Send in async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_smtp,
                msg
            )

            logger.info(f"Email sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

    def _send_smtp(self, msg: MIMEMultipart):
        """Send SMTP email (blocking operation)"""
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)


class SlackChannel(NotificationChannel):
    """Slack notification channel"""

    async def send(
        self,
        recipient: str,  # channel or user ID
        subject: str,
        message: str,
        severity: str = "info",
        **kwargs
    ) -> bool:
        """Send Slack notification"""
        if not settings.SLACK_WEBHOOK_URL:
            logger.warning("Slack not configured, skipping notification")
            return False

        try:
            color_map = {
                "info": "#36a64f",
                "warning": "#ff9900",
                "critical": "#ff0000"
            }
            color = color_map.get(severity, "#36a64f")

            payload = {
                "channel": recipient or settings.SLACK_ALERT_CHANNEL,
                "attachments": [
                    {
                        "color": color,
                        "title": subject,
                        "text": message,
                        "footer": "Oracle Monitor",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent to {recipient}")
                        return True
                    else:
                        logger.error(f"Slack error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Generic HTTP webhook notification channel"""

    async def send(
        self,
        recipient: str,  # webhook URL
        subject: str,
        message: str,
        **kwargs
    ) -> bool:
        """Send webhook notification"""
        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "subject": subject,
                "message": message,
                "severity": kwargs.get("severity", "info"),
                "alert_id": kwargs.get("alert_id"),
                "metric_value": kwargs.get("metric_value"),
                **kwargs
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    recipient,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201, 202]:
                        logger.info(f"Webhook notification sent to {recipient}")
                        return True
                    else:
                        logger.error(f"Webhook error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class NotificationManager:
    """Manages notification delivery through multiple channels"""

    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {
            "email": EmailChannel(),
            "slack": SlackChannel(),
            "webhook": WebhookChannel(),
        }

    async def send_alert_notification(
        self,
        alert_id: int,
        rule_name: str,
        severity: str,
        metric_value: float,
        metric_unit: str,
        message: str,
        notification_config: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Send alert notification through configured channels"""
        results = {}

        if not notification_config:
            return results

        channels = notification_config.get("channels", [])

        for channel_config in channels:
            channel_type = channel_config.get("type")
            recipients = channel_config.get("recipients", [])

            if not channel_type or not recipients:
                continue

            if channel_type not in self.channels:
                logger.warning(f"Unknown notification channel: {channel_type}")
                continue

            channel = self.channels[channel_type]

            # Format message based on channel type
            subject = f"[{severity.upper()}] {rule_name}"
            formatted_message = self._format_message(
                channel_type,
                alert_id,
                rule_name,
                severity,
                metric_value,
                metric_unit,
                message
            )

            # Send to each recipient
            for recipient in recipients:
                try:
                    success = await channel.send(
                        recipient=recipient,
                        subject=subject,
                        message=formatted_message,
                        severity=severity,
                        alert_id=alert_id,
                        metric_value=metric_value,
                        rule_name=rule_name
                    )
                    results[f"{channel_type}:{recipient}"] = success
                except Exception as e:
                    logger.error(f"Error sending {channel_type} to {recipient}: {e}")
                    results[f"{channel_type}:{recipient}"] = False

        return results

    def _format_message(
        self,
        channel_type: str,
        alert_id: int,
        rule_name: str,
        severity: str,
        metric_value: float,
        metric_unit: str,
        message: str
    ) -> str:
        """Format message based on channel type"""
        if channel_type == "email":
            return f"""
Alert Notification
==================

Rule: {rule_name}
Severity: {severity.upper()}
Alert ID: {alert_id}
Timestamp: {datetime.utcnow().isoformat()}

Metric Value: {metric_value} {metric_unit}

{message}

---
Oracle Database Monitoring System
"""
        elif channel_type == "slack":
            return f"""
*Rule*: {rule_name}
*Severity*: {severity.upper()}
*Alert ID*: {alert_id}
*Value*: {metric_value} {metric_unit}

{message}
"""
        else:
            return message

    async def send_bulk(
        self,
        alerts: List[Dict[str, Any]]
    ) -> Dict[int, Dict[str, bool]]:
        """Send multiple alerts in batch"""
        results = {}

        tasks = [
            self.send_alert_notification(
                alert_id=alert['id'],
                rule_name=alert['rule_name'],
                severity=alert['severity'],
                metric_value=alert['metric_value'],
                metric_unit=alert.get('metric_unit', ''),
                message=alert['message'],
                notification_config=alert.get('notification_config')
            )
            for alert in alerts
        ]

        bulk_results = await asyncio.gather(*tasks)

        for alert, result in zip(alerts, bulk_results):
            results[alert['id']] = result

        return results


# Global notification manager
notification_manager = NotificationManager()
