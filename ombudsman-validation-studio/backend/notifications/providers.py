"""
Notification Providers

Implements different notification channels:
- Email via SMTP
- Slack via webhooks
- Generic webhooks
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from .models import NotificationConfig


class EmailProvider:
    """
    Email notification provider using SMTP.
    """

    def __init__(self, config: NotificationConfig):
        """
        Initialize email provider.

        Args:
            config: Notification configuration with SMTP settings
        """
        self.config = config

    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email notification.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not all([
                self.config.smtp_host,
                self.config.smtp_from_email,
                self.config.smtp_username,
                self.config.smtp_password
            ]):
                print("Email configuration incomplete. Skipping email notification.")
                return False

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.smtp_from_name} <{self.config.smtp_from_email}>"
            msg['To'] = ', '.join(to)

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Attach plain text
            msg.attach(MIMEText(body, 'plain'))

            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            # Combine all recipients
            all_recipients = to + (cc or []) + (bcc or [])

            # Connect to SMTP server
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.smtp_use_tls:
                    server.starttls()

                # Login
                server.login(self.config.smtp_username, self.config.smtp_password)

                # Send email
                server.sendmail(
                    self.config.smtp_from_email,
                    all_recipients,
                    msg.as_string()
                )

            print(f"Email sent successfully to {', '.join(to)}")
            return True

        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False


class SlackProvider:
    """
    Slack notification provider using webhooks.
    """

    def __init__(self, config: NotificationConfig):
        """
        Initialize Slack provider.

        Args:
            config: Notification configuration with Slack settings
        """
        self.config = config

    def send(
        self,
        webhook_url: str,
        title: str,
        message: str,
        priority: str = "medium",
        channel: Optional[str] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send Slack notification.

        Args:
            webhook_url: Slack webhook URL
            title: Notification title
            message: Notification message
            priority: Priority level (low, medium, high, critical)
            channel: Override default channel
            username: Bot username
            icon_emoji: Bot icon emoji
            blocks: Slack Block Kit blocks

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Priority color mapping
            color_map = {
                "low": "#36a64f",      # Green
                "medium": "#2196F3",   # Blue
                "high": "#ff9800",     # Orange
                "critical": "#f44336"  # Red
            }

            color = color_map.get(priority, "#2196F3")

            # Build payload
            payload = {
                "username": username or "Ombudsman Bot",
                "icon_emoji": icon_emoji or ":robot_face:",
            }

            if channel:
                payload["channel"] = channel

            # Use blocks if provided, otherwise create attachment
            if blocks:
                payload["blocks"] = blocks
            else:
                payload["attachments"] = [{
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "Ombudsman Validation Studio",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                    "ts": int(datetime.utcnow().timestamp())
                }]

            # Send to Slack
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.config.webhook_timeout
            )

            if response.status_code == 200:
                print(f"Slack notification sent successfully")
                return True
            else:
                print(f"Slack notification failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Failed to send Slack notification: {str(e)}")
            return False

    def send_blocks(
        self,
        webhook_url: str,
        blocks: List[Dict[str, Any]],
        channel: Optional[str] = None
    ) -> bool:
        """
        Send Slack notification with Block Kit blocks.

        Args:
            webhook_url: Slack webhook URL
            blocks: Slack Block Kit blocks
            channel: Override default channel

        Returns:
            True if sent successfully
        """
        return self.send(
            webhook_url=webhook_url,
            title="",
            message="",
            blocks=blocks,
            channel=channel
        )


class WebhookProvider:
    """
    Generic webhook notification provider.
    """

    def __init__(self, config: NotificationConfig):
        """
        Initialize webhook provider.

        Args:
            config: Notification configuration
        """
        self.config = config

    def send(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send webhook notification.

        Args:
            webhook_url: Webhook URL
            payload: JSON payload to send
            method: HTTP method (GET, POST, PUT, etc.)
            headers: Optional HTTP headers

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Default headers
            default_headers = {
                "Content-Type": "application/json",
                "User-Agent": "Ombudsman-Validation-Studio/2.0"
            }

            # Merge with custom headers
            if headers:
                default_headers.update(headers)

            # Send request
            response = requests.request(
                method=method.upper(),
                url=webhook_url,
                json=payload,
                headers=default_headers,
                timeout=self.config.webhook_timeout
            )

            if 200 <= response.status_code < 300:
                print(f"Webhook notification sent successfully to {webhook_url}")
                return True
            else:
                print(f"Webhook notification failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Failed to send webhook notification: {str(e)}")
            return False


# Import datetime for Slack provider
from datetime import datetime
