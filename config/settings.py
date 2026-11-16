import os
from typing import Dict, Optional

from dotenv import load_dotenv


load_dotenv()


def get_db_config() -> Dict[str, Optional[str]]:
    """Return PostgreSQL connection settings from the local .env file."""
    return {
        "dbname": os.getenv("DB_NAME", "stock_analysis"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
    }


def get_required_setting(name: str) -> str:
    """Return a required environment variable without exposing its value."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
