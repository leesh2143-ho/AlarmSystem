import smtplib
import yaml
import logging
import time
import os
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
import datetime
from datetime import timezone
from fastapi import BackgroundTasks

from models import AlertStatus, AlertState, SessionLocal

MAX_RETRIES = 3

def load_config():
    """Loads email configuration from config.yaml."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("config.yaml not found. Cannot send emails.")
        return None

def send_email(subject, body, config):
    """Sends an email using the provided SMTP configuration."""
    if not config:
        logging.error("Email configuration is missing. Aborting send.")
        return False

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config['SENDER_EMAIL']
    msg['To'] = ", ".join(config['RECIPIENT_EMAIL'])

    try:
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SMTP_USERNAME'], config['SMTP_PASSWORD'])
            server.sendmail(config['SENDER_EMAIL'], config['RECIPIENT_EMAIL'], msg.as_string())
        logging.info(f"Email '{subject}' sent successfully to {msg['To']}.")
        return True
    except Exception as e:
        logging.error(f"Failed to send email '{subject}'. Error: {e}")
        return False

def send_alert_email(alert_id: int, background_tasks: BackgroundTasks):
    """Sends an email for a new or re-opened alert."""
    db = SessionLocal()
    alert = db.query(AlertStatus).filter(AlertStatus.id == alert_id).first()
    if not alert:
        db.close()
        return

    config = load_config()
    subject = f"[ALERT] Service Down: {alert.url}"
    body = f"""
    Alert: The service at the following URL is down or responding with an error.

    URL: {alert.url}
    Status Code: {alert.status_code}
    Initial Timestamp: {alert.initial_timestamp}
    State: {alert.alert_state.value}

    This is an automated message.
    """

    success = send_email(subject, body, config)

    if success:
        alert.last_notification_time = datetime.datetime.now(timezone.utc)
        alert.retry_count = 0
        db.commit()
    else:
        background_tasks.add_task(retry_send_alert, alert.id, 1, background_tasks)
        logging.info(f"Scheduled retry for alert ID {alert.id}.")
    db.close()

def send_recovery_email(url: str):
    """Sends an email when a service has recovered."""
    config = load_config()
    subject = f"[RECOVERY] Service Restored: {url}"
    body = f"""
    Recovery Notification: The service at the following URL is back online.

    URL: {url}
    Timestamp: {datetime.datetime.now(timezone.utc).isoformat()}

    The service is now responding correctly.
    """
    send_email(subject, body, config)

def retry_send_alert(alert_id: int, attempt: int, background_tasks: BackgroundTasks):
    """Retries sending an alert email in the background."""
    db = SessionLocal()
    config = load_config()
    if not config or attempt > MAX_RETRIES:
        if attempt > MAX_RETRIES:
            logging.error(f"Max retries reached for alert ID {alert_id}. Stopping retries.")
        db.close()
        return

    time.sleep(config.get('RETRY_INTERVAL_SECONDS', 300))

    alert = db.query(AlertStatus).filter(AlertStatus.id == alert_id).first()

    if not alert or alert.alert_state != AlertState.OPEN:
        logging.info(f"Alert ID {alert_id} is no longer in an open state. Cancelling retry.")
        db.close()
        return

    logging.info(f"Retrying to send alert for {alert.url} (Attempt {attempt}/{MAX_RETRIES}).")

    subject = f"[ALERT] Service Down: {alert.url} (Retry {attempt})"
    body = f"""
    Alert: The service at the following URL is down or responding with an error.

    URL: {alert.url}
    Status Code: {alert.status_code}
    Initial Timestamp: {alert.initial_timestamp}
    State: {alert.alert_state.value}

    This is an automated message (Retry attempt {attempt}).
    """

    success = send_email(subject, body, config)

    if success:
        alert.last_notification_time = datetime.datetime.now(timezone.utc)
        alert.retry_count = 0
        db.commit()
    else:
        alert.retry_count = attempt
        db.commit()
        background_tasks.add_task(retry_send_alert, alert.id, attempt + 1, background_tasks)
        logging.info(f"Scheduled next retry for alert ID {alert.id}.")
    db.close()
