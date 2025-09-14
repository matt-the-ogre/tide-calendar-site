import sqlite3
import logging
import os

DB_PATH = 'tide_station_ids.db'

def init_database():
    """Initialize the database and create tables if they don't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tide_station_ids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id TEXT UNIQUE NOT NULL,
                    lookup_count INTEGER NOT NULL DEFAULT 1,
                    last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            logging.debug("Database initialized successfully")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
        raise

def log_station_lookup(station_id):
    """Log a station ID lookup, incrementing count if it exists or creating new entry."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Try to get existing lookup count
            result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?', (station_id,)).fetchone()

            if result:
                # Update existing record
                cursor.execute('''
                    UPDATE tide_station_ids
                    SET lookup_count = lookup_count + 1,
                        last_lookup = CURRENT_TIMESTAMP
                    WHERE station_id = ?
                ''', (station_id,))
                new_count = result[0] + 1
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO tide_station_ids (station_id, lookup_count)
                    VALUES (?, 1)
                ''', (station_id,))
                new_count = 1

            conn.commit()
            logging.info(f"Station ID {station_id} has been looked up {new_count} times.")
            return new_count

    except sqlite3.Error as e:
        logging.error(f"Database error logging station {station_id}: {e}")
        # Don't re-raise - logging is not critical to main functionality
        return None