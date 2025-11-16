import sqlite3
import logging
import os
import csv
from pathlib import Path

# Get the app directory for relative database path
APP_DIR = Path(__file__).parent.resolve()

# Default to app directory if DB_PATH not set, allows production override to /data
DEFAULT_DB_PATH = str(APP_DIR / 'tide_station_ids.db')
DB_PATH = os.getenv('DB_PATH', DEFAULT_DB_PATH)

def init_database():
    """Initialize the database and create tables if they don't exist."""
    try:
        # Ensure parent directory exists
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logging.info(f"Created database directory: {db_dir}")

        logging.info(f"Using database path: {DB_PATH}")

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
    except (sqlite3.Error, OSError) as e:
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
    """Import station data from CSV file and remove stations not in CSV (sync database to CSV)."""
    csv_path = os.path.join(os.path.dirname(__file__), 'tide_stations_new.csv')

    if not os.path.exists(csv_path):
        logging.warning(f"CSV file not found: {csv_path}")
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check if we already have place names populated
            MIN_STATION_THRESHOLD = 100
            result = cursor.execute('SELECT COUNT(*) FROM tide_station_ids WHERE place_name IS NOT NULL').fetchone()
            if result[0] >= MIN_STATION_THRESHOLD:
                logging.debug(f"Station place names already populated (count: {result[0]})")
                return True

            # Import from CSV and collect all valid station IDs
            imported_count = 0
            csv_station_ids = set()
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    station_id = row['station_id']
                    place_name = row['place_name']
                    csv_station_ids.add(station_id)

                    # Insert or update station
                    cursor.execute('''
                        INSERT OR REPLACE INTO tide_station_ids
                        (station_id, place_name, lookup_count, last_lookup)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name))
                    imported_count += 1

            # Remove stations from database that are NOT in the CSV (cleanup invalid stations)
            # This ensures the database stays in sync with the validated canonical CSV
            if csv_station_ids:
                # Build a parameterized query to delete stations not in CSV
                placeholders = ','.join('?' * len(csv_station_ids))
                delete_query = f'DELETE FROM tide_station_ids WHERE station_id NOT IN ({placeholders})'
                cursor.execute(delete_query, tuple(csv_station_ids))
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    logging.info(f"Removed {deleted_count} invalid station(s) not present in CSV")

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

def get_station_info(station_id):
    """Get full station metadata including api_source, country, coordinates."""
    if not station_id:
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            result = cursor.execute('''
                SELECT station_id, place_name, country, api_source, latitude, longitude, province
                FROM tide_station_ids
                WHERE station_id = ?
            ''', (station_id,)).fetchone()

            if result:
                return {
                    'station_id': result[0],
                    'place_name': result[1],
                    'country': result[2] if result[2] else 'USA',
                    'api_source': result[3] if result[3] else 'NOAA',
                    'latitude': result[4],
                    'longitude': result[5],
                    'province': result[6]
                }

            return None

    except sqlite3.Error as e:
        logging.error(f"Database error getting station info for {station_id}: {e}")
        return None

def import_canadian_stations_from_csv():
    """Import Canadian tide station data from CSV file and remove Canadian stations not in CSV."""
    csv_path = os.path.join(os.path.dirname(__file__), 'canadian_tide_stations.csv')

    if not os.path.exists(csv_path):
        logging.warning(f"Canadian stations CSV file not found: {csv_path}")
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check if we already have Canadian stations
            result = cursor.execute('SELECT COUNT(*) FROM tide_station_ids WHERE country = "Canada"').fetchone()
            if result[0] > 10:
                logging.debug(f"Canadian stations already populated (count: {result[0]})")
                return True

            # Import from CSV and collect all valid Canadian station IDs
            imported_count = 0
            csv_station_ids = set()
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    station_id = row['station_id']
                    place_name = row['place_name']
                    province = row.get('province', '')
                    csv_station_ids.add(station_id)

                    # Parse coordinates with error handling
                    try:
                        latitude = float(row['latitude']) if row.get('latitude') and row['latitude'].strip() else None
                    except (ValueError, AttributeError) as e:
                        logging.warning(f"Invalid latitude for station {station_id} ({place_name}): {row.get('latitude')}. Setting to None.")
                        latitude = None

                    try:
                        longitude = float(row['longitude']) if row.get('longitude') and row['longitude'].strip() else None
                    except (ValueError, AttributeError) as e:
                        logging.warning(f"Invalid longitude for station {station_id} ({place_name}): {row.get('longitude')}. Setting to None.")
                        longitude = None

                    country = row.get('country', 'Canada')
                    api_source = row.get('api_source', 'CHS')

                    # Insert or update station
                    cursor.execute('''
                        INSERT OR REPLACE INTO tide_station_ids
                        (station_id, place_name, country, api_source, latitude, longitude, province, lookup_count, last_lookup)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name, country, api_source, latitude, longitude, province))
                    imported_count += 1

            # Remove Canadian stations from database that are NOT in the CSV
            if csv_station_ids:
                placeholders = ','.join('?' * len(csv_station_ids))
                delete_query = f'DELETE FROM tide_station_ids WHERE country = "Canada" AND station_id NOT IN ({placeholders})'
                cursor.execute(delete_query, tuple(csv_station_ids))
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    logging.info(f"Removed {deleted_count} invalid Canadian station(s) not present in CSV")

            conn.commit()
            logging.info(f"Imported {imported_count} Canadian stations from CSV")
            return True

    except Exception as e:
        logging.error(f"Error importing Canadian stations from CSV: {e}")
        return False

def search_stations_by_country(query, country=None, limit=10):
    """Search for stations by place name, optionally filtered by country."""
    if not query or len(query.strip()) < 1:
        return []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Case-insensitive substring search
            search_query = f"%{query.strip()}%"

            if country:
                results = cursor.execute('''
                    SELECT station_id, place_name, country, lookup_count
                    FROM tide_station_ids
                    WHERE place_name IS NOT NULL
                    AND LOWER(place_name) LIKE LOWER(?)
                    AND country = ?
                    ORDER BY lookup_count DESC, place_name ASC
                    LIMIT ?
                ''', (search_query, country, limit)).fetchall()
            else:
                results = cursor.execute('''
                    SELECT station_id, place_name, country, lookup_count
                    FROM tide_station_ids
                    WHERE place_name IS NOT NULL
                    AND LOWER(place_name) LIKE LOWER(?)
                    ORDER BY lookup_count DESC, place_name ASC
                    LIMIT ?
                ''', (search_query, limit)).fetchall()

            return [{
                'station_id': row[0],
                'place_name': row[1],
                'country': row[2],
                'lookup_count': row[3]
            } for row in results]

    except sqlite3.Error as e:
        logging.error(f"Database error searching stations: {e}")
        return []

def get_popular_stations_by_country(country=None, limit=16):
    """Get the most popular tide stations, optionally filtered by country."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            if country:
                results = cursor.execute('''
                    SELECT station_id, place_name, country, lookup_count
                    FROM tide_station_ids
                    WHERE place_name IS NOT NULL
                    AND country = ?
                    ORDER BY lookup_count DESC, place_name ASC
                    LIMIT ?
                ''', (country, limit)).fetchall()
            else:
                results = cursor.execute('''
                    SELECT station_id, place_name, country, lookup_count
                    FROM tide_station_ids
                    WHERE place_name IS NOT NULL
                    ORDER BY lookup_count DESC, place_name ASC
                    LIMIT ?
                ''', (limit,)).fetchall()

            return [{
                'station_id': row[0],
                'place_name': row[1],
                'country': row[2],
                'lookup_count': row[3]
            } for row in results]

    except sqlite3.Error as e:
        logging.error(f"Database error getting popular stations: {e}")
        return []