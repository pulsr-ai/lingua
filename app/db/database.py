"""
Database utilities
"""

import logging
from sqlalchemy import create_engine, text

from app.core.config import settings

logger = logging.getLogger(__name__)


def check_database_connection():
    """Check if database connection is working"""
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False