import logging
import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Header, status, BackgroundTasks
from sqlalchemy.orm import Session
import datetime

import models
import email_service
from models import HealthCheckPayload, AlertStatus, AlertState, get_db, create_db_and_tables

# --- App and Logging Setup ---
app = FastAPI()

# Setup logging
log_file = Path("server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# --- Database Initialization ---
@app.on_event("startup")
def on_startup():
    """Create database and tables on application startup."""
    create_db_and_tables()
    logging.info("Database and tables created if they did not exist.")

# --- API Key Authentication ---
def get_api_key_from_file():
    """Reads the API key from the user's home directory."""
    api_key_path = Path.home() / "API_KEY"
    try:
        with open(api_key_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.error(f"API key file not found at {api_key_path}. Please create it.")
        return None

API_KEY = get_api_key_from_file()

async def verify_api_key(x_api_key: str = Header(...)):
    """Dependency to verify the X-API-Key header."""
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return x_api_key

# --- API Endpoint ---
@app.post("/events", dependencies=[Depends(verify_api_key)])
async def receive_events(
    payload: HealthCheckPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receives health check results, logs them, and processes alerts.
    """
    logging.info(f"Received payload: {payload.dict()}")

    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    for result in payload.results:
        alert = db.query(AlertStatus).filter(AlertStatus.url == result.url).first()

        is_error = result.status >= 400
        is_recovered = 200 <= result.status < 300

        if is_error:
            if not alert:
                # New alert
                alert = AlertStatus(
                    url=result.url,
                    status_code=result.status,
                    initial_timestamp=result.timestamp,
                    alert_state=AlertState.OPEN
                )
                db.add(alert)
                db.commit()
                db.refresh(alert) # Refresh to get the ID for the background task
                logging.info(f"New alert for {result.url}. State: OPEN. Triggering notification.")
                background_tasks.add_task(email_service.send_alert_email, alert_id=alert.id, background_tasks=background_tasks)
            elif alert.alert_state == AlertState.RESOLVED:
                # Recovered service failed again
                alert.alert_state = AlertState.OPEN
                alert.status_code = result.status
                alert.initial_timestamp = result.timestamp
                alert.last_notification_time = None
                alert.retry_count = 0
                db.commit()
                logging.info(f"Alert for recovered service {result.url}. State: OPEN. Triggering notification.")
                background_tasks.add_task(email_service.send_alert_email, alert_id=alert.id, background_tasks=background_tasks)
            else:
                # Ongoing issue, do nothing
                logging.info(f"Duplicate alert for {result.url}. State: {alert.alert_state}. No action taken.")

        elif is_recovered:
            if alert and alert.alert_state in [AlertState.OPEN, AlertState.ACK]:
                # Service has recovered
                previous_state = alert.alert_state
                alert.alert_state = AlertState.RESOLVED
                alert.retry_count = 0
                db.commit()
                logging.info(f"Service {result.url} has recovered from state {previous_state}. Triggering recovery notification.")
                background_tasks.add_task(email_service.send_recovery_email, url=result.url)

    return {"status": "Payload received and processed"}
