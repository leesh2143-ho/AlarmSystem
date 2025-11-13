import datetime
import enum
import yaml
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, Field
from typing import List, Optional

# --- Pydantic Models for API data validation ---

class HealthCheckResult(BaseModel):
    url: str
    status: int
    response_time_ms: float
    timestamp: str

class HealthCheckPayload(BaseModel):
    results: List[HealthCheckResult]

# --- SQLAlchemy Database Models ---

def load_db_config():
    """Loads database configuration from config.yaml."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        # In a real application, you would log this error and handle it gracefully
        return None

db_config = load_db_config()
if db_config:
    DATABASE_URL = (
        f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
        f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{db_config['DB_NAME']}"
    )
else:
    # Fallback or error state
    DATABASE_URL = ""

Base = declarative_base()

class AlertState(str, enum.Enum):
    OPEN = "Open"
    ACK = "Ack"
    RESOLVED = "Resolved"

class AlertStatus(Base):
    __tablename__ = "alert_status"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255), unique=True, index=True, nullable=False)
    status_code = Column(Integer)
    initial_timestamp = Column(String(50))
    alert_state = Column(Enum(AlertState), default=AlertState.RESOLVED, nullable=False)
    last_notification_time = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)

# --- Database Setup ---
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def create_db_and_tables():
        """Create the database and tables if they don't exist."""
        Base.metadata.create_all(bind=engine)

    # Dependency to get a DB session
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
else:
    # Define dummy functions if config is missing
    def create_db_and_tables(): pass
    def get_db(): yield None
