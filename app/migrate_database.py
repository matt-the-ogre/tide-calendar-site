"""
Database migration script to add support for Canadian tide stations.

This script adds new columns to support multiple countries and data sources:
- country: 'USA' or 'Canada'
- api_source: 'NOAA' or 'CHS'
- latitude: Station latitude coordinate
- longitude: Station longitude coordinate
- province: Province/state code (optional, for Canadian stations)
"""

import sqlite3
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get database path from environment or use default
APP_DIR = Path(__file__).parent.resolve()
DEFAULT_DB_PATH = str(APP_DIR / 'tide_station_ids.db')
DB_PATH = os.getenv('DB_PATH', DEFAULT_DB_PATH)

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    # Whitelist allowed table names to prevent SQL injection
    allowed_tables = ['tide_station_ids']
    if table_name not in allowed_tables:
        raise ValueError(f"Invalid table name: {table_name}. Allowed tables: {allowed_tables}")

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def migrate_database():
    """Run database migration to add new columns."""
    logging.info(f"Starting database migration for: {DB_PATH}")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tide_station_ids'")
            if not cursor.fetchone():
                logging.error("Table 'tide_station_ids' does not exist. Run init_database() first.")
                return False

            # Add 'country' column
            if not check_column_exists(cursor, 'tide_station_ids', 'country'):
                logging.info("Adding 'country' column...")
                cursor.execute('ALTER TABLE tide_station_ids ADD COLUMN country TEXT NOT NULL DEFAULT "USA"')
                logging.info("✓ Added 'country' column")
            else:
                logging.info("Column 'country' already exists, skipping")

            # Add 'api_source' column
            if not check_column_exists(cursor, 'tide_station_ids', 'api_source'):
                logging.info("Adding 'api_source' column...")
                cursor.execute('ALTER TABLE tide_station_ids ADD COLUMN api_source TEXT NOT NULL DEFAULT "NOAA"')
                logging.info("✓ Added 'api_source' column")
            else:
                logging.info("Column 'api_source' already exists, skipping")

            # Add 'latitude' column
            if not check_column_exists(cursor, 'tide_station_ids', 'latitude'):
                logging.info("Adding 'latitude' column...")
                cursor.execute('ALTER TABLE tide_station_ids ADD COLUMN latitude REAL')
                logging.info("✓ Added 'latitude' column")
            else:
                logging.info("Column 'latitude' already exists, skipping")

            # Add 'longitude' column
            if not check_column_exists(cursor, 'tide_station_ids', 'longitude'):
                logging.info("Adding 'longitude' column...")
                cursor.execute('ALTER TABLE tide_station_ids ADD COLUMN longitude REAL')
                logging.info("✓ Added 'longitude' column")
            else:
                logging.info("Column 'longitude' already exists, skipping")

            # Add 'province' column for Canadian stations
            if not check_column_exists(cursor, 'tide_station_ids', 'province'):
                logging.info("Adding 'province' column...")
                cursor.execute('ALTER TABLE tide_station_ids ADD COLUMN province TEXT')
                logging.info("✓ Added 'province' column")
            else:
                logging.info("Column 'province' already exists, skipping")

            conn.commit()

            # Display updated schema
            logging.info("\nUpdated table schema:")
            cursor.execute("PRAGMA table_info(tide_station_ids)")
            for column in cursor.fetchall():
                logging.info(f"  {column[1]}: {column[2]}")

            logging.info("\n✅ Database migration completed successfully!")
            return True

    except sqlite3.Error as e:
        logging.error(f"❌ Database migration failed: {e}")
        return False

def verify_migration():
    """Verify that migration was successful."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check all required columns exist
            required_columns = ['country', 'api_source', 'latitude', 'longitude', 'province']
            cursor.execute("PRAGMA table_info(tide_station_ids)")
            existing_columns = [column[1] for column in cursor.fetchall()]

            missing = [col for col in required_columns if col not in existing_columns]

            if missing:
                logging.error(f"Migration verification failed. Missing columns: {missing}")
                return False

            logging.info("✅ Migration verification passed. All columns present.")
            return True

    except sqlite3.Error as e:
        logging.error(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info("DATABASE MIGRATION SCRIPT")
    logging.info("=" * 60)

    # Run migration
    success = migrate_database()

    if success:
        # Verify migration
        verify_migration()
    else:
        logging.error("Migration failed. Please check errors above.")
        exit(1)
