"""
Migration script to add missing 'name' column to gifs table.
Run this once to update your existing database schema.
"""

import asyncio
import sqlite3
from utils.config import get_config
from utils.logging import get_logger

logger = get_logger(__name__)


async def migrate_gifs_table():
    """Add the 'name' column to the gifs table if it doesn't exist."""
    config = get_config()
    db_path = config.db_path
    
    logger.info(f"Starting migration for database: {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(gifs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "name" in columns:
            logger.info("Column 'name' already exists in gifs table. No migration needed.")
            return
        
        logger.info("Adding 'name' column to gifs table...")
        
        # Add the new column (nullable since existing rows won't have values)
        cursor.execute("ALTER TABLE gifs ADD COLUMN name VARCHAR(100) NULL")
        
        # Set default value for existing rows (optional, can be left as NULL)
        # cursor.execute("UPDATE gifs SET name = 'legacy' WHERE name IS NULL")
        
        conn.commit()
        logger.info("Successfully added 'name' column to gifs table!")
        
    except sqlite3.Error as e:
        logger.error(f"Database error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(migrate_gifs_table())
