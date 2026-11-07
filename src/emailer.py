"""
NetZeroX Policy Pulse — Email Delivery
SMTP client for sending reports and flash alerts to subscribers.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import yaml
from dotenv import load_dotenv

from . import database as db

load_dotenv()


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def send_report(
    subject: str,
    body_markdown: str,
    recipients: list[str],
    config_path: str = "config.yaml",
) -> bool:
    """Send a report via SMTP."""
    config = load_config(config_path)
    email_config = config.get("email", {})

    if not email_config.get("enabled", False):
        print("📧 Email delivery is DISABLED in config.yaml")
        print(f"   Would send to: {len(recipients)} recipients")
        print(f"   Subject: {subject}")
        return False

    smtp_host = email_config.get("smtp_host", "smtp.gmail.com")
    smtp_port = email_config.get("smtp_port", 587)
    from_addr = email_config.get("from_address", "")
    email_user = os.getenv("POLICY_PULSE_EMAIL_USER", from_addr)
    email_pass = os.getenv("POLICY_PULSE_EMAIL_PASS", "")

    if not email_user or not email_pass:
        print("⚠️  Email credentials not set. Set POLICY_PULSE_EMAIL_USER and POLICY_PULSE_EMAIL_PASS.")
        return False

    print(f"📧 Sending report to {len(recipients)} recipients...")

    success_count = 0
    for recipient in recipients:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"NetZeroX Policy Pulse <{email_user}>"
            msg["To"] = recipient

            # Plain text version (the markdown)
            text_part = MIMEText(body_markdown, "plain")
            msg.attach(text_part)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_pass)
                server.sendmail(email_user, recipient, msg.as_string())

            success_count += 1
            print(f"  ✅ Sent to: {recipient}")

        except Exception as e:
            print(f"  ❌ Failed for {recipient}: {e}")

    print(f"📧 Delivery complete: {success_count}/{len(recipients)} sent")
    return success_count > 0


def send_weekly_pulse(report_path: str, config_path: str = "config.yaml"):
    """Send the weekly pulse report to all active subscribers."""
    config = load_config(config_path)
    subscribers = config.get("email", {}).get("subscribers", [])

    if not subscribers:
        print("⚠️  No subscribers configured in config.yaml")
        return

    with open(report_path, "r") as f:
        body = f.read()

    now = datetime.now()
    subject = f"🔍 Policy Pulse: Week of {now.strftime('%b %d, %Y')}"

    send_report(subject, body, subscribers, config_path)


def send_flash_alert(alert_path: str, config_path: str = "config.yaml"):
    """Send an urgent flash alert to all subscribers."""
    config = load_config(config_path)
    subscribers = config.get("email", {}).get("subscribers", [])

    if not subscribers:
        print("⚠️  No subscribers configured")
        return

    with open(alert_path, "r") as f:
        body = f.read()

    subject = "🚨 URGENT: NetZeroX Policy Flash Alert"
    send_report(subject, body, subscribers, config_path)


# ── CLI Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    print("📧 Email module loaded. Use send_weekly_pulse() or send_flash_alert().")
