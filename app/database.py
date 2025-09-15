import sqlite3
import logging
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'tide_station_ids.db')

def init_database():
    """Initialize the database and create tables if they don't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tide_station_ids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id TEXT UNIQUE NOT NULL,
                    place_name TEXT,
                    lookup_count INTEGER NOT NULL DEFAULT 1,
                    last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Check if place_name column exists and add it if not
            cursor.execute("PRAGMA table_info(tide_station_ids)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'place_name' not in columns:
                cursor.execute('ALTER TABLE tide_station_ids ADD COLUMN place_name TEXT')
                logging.info("Added place_name column to tide_station_ids table")
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

def import_stations_from_csv():
    """Import station data from CSV file if database is empty."""
    import csv
    import os

    csv_path = os.path.join(os.path.dirname(__file__), 'tide_stations_new.csv')

    if not os.path.exists(csv_path):
        logging.warning(f"CSV file not found: {csv_path}")
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check if we already have place names populated
            result = cursor.execute('SELECT COUNT(*) FROM tide_station_ids WHERE place_name IS NOT NULL').fetchone()
            if result[0] > 0:
                logging.debug("Station place names already populated")
                return True

            # Import from CSV
            imported_count = 0
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    station_id = row['station_id']
                    place_name = row['place_name']

                    # Insert or update station
                    cursor.execute('''
                        INSERT OR REPLACE INTO tide_station_ids
                        (station_id, place_name, lookup_count, last_lookup)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name))
                    imported_count += 1

            conn.commit()
            logging.info(f"Imported {imported_count} stations from CSV")
            return True

    except Exception as e:
        logging.error(f"Error importing stations from CSV: {e}")
        return False

def search_stations_by_name(query, limit=10):
    """Search for stations by place name with case-insensitive substring matching."""
    if not query or len(query.strip()) < 1:
        return []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Case-insensitive substring search
            search_query = f"%{query.strip()}%"
            results = cursor.execute('''
                SELECT station_id, place_name, lookup_count
                FROM tide_station_ids
                WHERE place_name IS NOT NULL
                AND LOWER(place_name) LIKE LOWER(?)
                ORDER BY lookup_count DESC, place_name ASC
                LIMIT ?
            ''', (search_query, limit)).fetchall()

            return [{
                'station_id': row[0],
                'place_name': row[1],
                'lookup_count': row[2]
            } for row in results]

    except sqlite3.Error as e:
        logging.error(f"Database error searching stations: {e}")
        return []

def get_popular_stations(limit=16):
    """Get the most popular tide stations by lookup count."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            results = cursor.execute('''
                SELECT station_id, place_name, lookup_count
                FROM tide_station_ids
                WHERE place_name IS NOT NULL
                ORDER BY lookup_count DESC, place_name ASC
                LIMIT ?
            ''', (limit,)).fetchall()

            return [{
                'station_id': row[0],
                'place_name': row[1],
                'lookup_count': row[2]
            } for row in results]

    except sqlite3.Error as e:
        logging.error(f"Database error getting popular stations: {e}")
        return []

def get_place_name_by_station_id(station_id):
    """Get the place name for a given station ID."""
    if not station_id:
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            result = cursor.execute('''
                SELECT place_name
                FROM tide_station_ids
                WHERE station_id = ?
            ''', (station_id,)).fetchone()

            return result[0] if result else None

    except sqlite3.Error as e:
        logging.error(f"Database error getting place name for station {station_id}: {e}")
        return None

def get_station_id_by_place_name(place_name):
    """Get the station ID for a given place name (exact match)."""
    if not place_name:
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Try exact match first
            result = cursor.execute('''
                SELECT station_id
                FROM tide_station_ids
                WHERE place_name = ?
            ''', (place_name,)).fetchone()

            if result:
                return result[0]

            # If no exact match, try case-insensitive match
            result = cursor.execute('''
                SELECT station_id
                FROM tide_station_ids
                WHERE LOWER(place_name) = LOWER(?)
                LIMIT 1
            ''', (place_name,)).fetchone()

            return result[0] if result else None

    except sqlite3.Error as e:
        logging.error(f"Database error getting station ID for place {place_name}: {e}")
        return None