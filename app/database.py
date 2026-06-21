import sqlite3
import logging
import os
import csv
import re
import unicodedata
from pathlib import Path

# Get the app directory for relative database path
APP_DIR = Path(__file__).parent.resolve()

# Default to app directory if DB_PATH not set, allows production override to /data
DEFAULT_DB_PATH = str(APP_DIR / 'tide_station_ids.db')
DB_PATH = os.getenv('DB_PATH', DEFAULT_DB_PATH)

# error_detail values attributable to the CALLER (4xx-style: bad input, bot
# probes, unknown stations) vs. our own failures (everything else with
# status='error' — no_predictions, generation_failed, exception, legacy
# pdf_missing). get_usage_stats splits the error metric along this line so that
# bot/probe traffic can't masquerade as a server outage. 'rejected' is a
# separate status entirely (junk short-circuited before any work) and counts as
# neither success nor error.
CLIENT_ERROR_DETAILS = ('unknown_station', 'station_not_found', 'no_station',
                        'invalid_input', 'junk_station_id')


def _migrate_columns(cursor, table, columns_ddl):
    """Add any missing columns to a table (idempotent startup migration).

    table/column names are f-string-interpolated because SQLite placeholders
    only bind values, not identifiers; every caller passes hardcoded literals,
    never user input.
    """
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {column[1] for column in cursor.fetchall()}
    for name, ddl in columns_ddl.items():
        if name not in existing:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')
            logging.info(f"Added {name} column to {table} table")

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

            # Schema migration: Add missing columns if they don't exist
            _migrate_columns(cursor, 'tide_station_ids', {
                'place_name': 'TEXT',
                'country': "TEXT DEFAULT 'USA'",
                'api_source': "TEXT DEFAULT 'NOAA'",
                'latitude': 'REAL',
                'longitude': 'REAL',
                'province': 'TEXT',
                'alternative_name': 'TEXT',
                'timezone': 'TEXT',
            })

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    station_id TEXT,
                    station_name TEXT,
                    year INTEGER,
                    month INTEGER,
                    status TEXT NOT NULL,
                    error_detail TEXT,
                    source TEXT DEFAULT 'web'
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_events_timestamp ON usage_events(timestamp)')

            _migrate_columns(cursor, 'usage_events', {
                'source': "TEXT DEFAULT 'web'",
            })

            cursor.execute('''
                DELETE FROM usage_events
                WHERE timestamp < datetime('now', '-365 days')
            ''')
            if cursor.rowcount > 0:
                logging.info(f"Pruned {cursor.rowcount} usage_events older than 365 days")

            conn.commit()
            logging.debug("Database initialized successfully")
    except (sqlite3.Error, OSError) as e:
        logging.error(f"Database initialization error: {e}")
        raise

def log_usage_event(station_id, station_name, year, month, status, error_detail=None, source='web'):
    """Record a single usage event. Swallows errors so analytics never break the main flow.

    source: 'web' for the main form, 'quick_api' for /api/generate_quick.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO usage_events
                (station_id, station_name, year, month, status, error_detail, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (station_id, station_name, year, month, status, error_detail, source))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to log usage event: {e}")

def get_usage_stats(recent_limit=50, top_limit=10):
    """Return aggregate usage stats and a list of recent events for the admin surface."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # The client/server split keys off a fixed constant set, inlined as
            # ? placeholders (never user input — but parameterized for hygiene).
            client_placeholders = ','.join('?' * len(CLIENT_ERROR_DETAILS))
            totals = cursor.execute(f'''
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count,
                    SUM(CASE WHEN status = 'error' AND error_detail IN ({client_placeholders})
                             THEN 1 ELSE 0 END) AS client_error_count,
                    SUM(CASE WHEN status = 'error' AND (error_detail IS NULL
                             OR error_detail NOT IN ({client_placeholders}))
                             THEN 1 ELSE 0 END) AS server_error_count,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count,
                    SUM(CASE WHEN timestamp >= datetime('now', '-1 day') THEN 1 ELSE 0 END) AS last_24h,
                    SUM(CASE WHEN timestamp >= datetime('now', '-7 days') THEN 1 ELSE 0 END) AS last_7d,
                    SUM(CASE WHEN timestamp >= datetime('now', '-30 days') THEN 1 ELSE 0 END) AS last_30d,
                    SUM(CASE WHEN source = 'web' THEN 1 ELSE 0 END) AS web_count,
                    SUM(CASE WHEN source = 'quick_api' THEN 1 ELSE 0 END) AS quick_api_count
                FROM usage_events
            ''', CLIENT_ERROR_DETAILS + CLIENT_ERROR_DETAILS).fetchone()

            top_stations = cursor.execute('''
                SELECT
                    station_name,
                    station_id,
                    COUNT(*) AS hits
                FROM usage_events
                WHERE timestamp >= datetime('now', '-30 days')
                  AND station_name IS NOT NULL
                GROUP BY station_id, station_name
                ORDER BY hits DESC, station_name ASC
                LIMIT ?
            ''', (top_limit,)).fetchall()

            recent = cursor.execute('''
                SELECT timestamp, station_id, station_name, year, month, status, error_detail, source
                FROM usage_events
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (recent_limit,)).fetchall()

            return {
                'total': totals['total'] or 0,
                'success_count': totals['success_count'] or 0,
                'error_count': totals['error_count'] or 0,
                'client_error_count': totals['client_error_count'] or 0,
                'server_error_count': totals['server_error_count'] or 0,
                'rejected_count': totals['rejected_count'] or 0,
                'last_24h': totals['last_24h'] or 0,
                'last_7d': totals['last_7d'] or 0,
                'last_30d': totals['last_30d'] or 0,
                'web_count': totals['web_count'] or 0,
                'quick_api_count': totals['quick_api_count'] or 0,
                'top_stations': [dict(row) for row in top_stations],
                'recent_events': [dict(row) for row in recent],
            }
    except sqlite3.Error as e:
        logging.error(f"Failed to fetch usage stats: {e}")
        return {
            'total': 0, 'success_count': 0, 'error_count': 0,
            'client_error_count': 0, 'server_error_count': 0, 'rejected_count': 0,
            'last_24h': 0, 'last_7d': 0, 'last_30d': 0,
            'web_count': 0, 'quick_api_count': 0,
            'top_stations': [], 'recent_events': [],
            'error': str(e),
        }

def log_station_lookup(station_id):
    """Log a station ID lookup, incrementing count if it exists or creating new entry."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            result = cursor.execute('''
                INSERT INTO tide_station_ids (station_id, lookup_count)
                VALUES (?, 1)
                ON CONFLICT(station_id) DO UPDATE SET
                    lookup_count = lookup_count + 1,
                    last_lookup = CURRENT_TIMESTAMP
                RETURNING lookup_count
            ''', (station_id,)).fetchone()
            conn.commit()
            new_count = result[0]
            logging.info(f"Station ID {station_id} has been looked up {new_count} times.")
            return new_count

    except sqlite3.Error as e:
        logging.error(f"Database error logging station {station_id}: {e}")
        # Don't re-raise - logging is not critical to main functionality
        return None

def import_stations_from_csv():
    """Import US station data from the canonical CSV (sync DB to CSV)."""
    csv_path = os.path.join(os.path.dirname(__file__), 'tide_stations_new.csv')
    if not os.path.exists(csv_path):
        logging.warning(f"CSV file not found: {csv_path}")
        return False
    return _import_us_csv(csv_path)


def _parse_coord(value, station_id, place_name, kind):
    """Parse a CSV coordinate cell to float or None, tolerating blanks."""
    try:
        return float(value) if value and value.strip() else None
    except (ValueError, AttributeError):
        logging.warning(f"Invalid {kind} for station {station_id} ({place_name}): {value!r}")
        return None


def _import_us_csv(csv_path):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            MIN_STATION_THRESHOLD = 100
            result = cursor.execute(
                'SELECT COUNT(*) FROM tide_station_ids WHERE place_name IS NOT NULL').fetchone()
            if result[0] >= MIN_STATION_THRESHOLD:
                logging.debug(f"Station place names already populated (count: {result[0]})")
                return True

            imported_count = 0
            csv_station_ids = set()
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    station_id = row['station_id']
                    place_name = row['place_name']
                    csv_station_ids.add(station_id)
                    latitude = _parse_coord(row.get('latitude'), station_id, place_name, 'latitude')
                    longitude = _parse_coord(row.get('longitude'), station_id, place_name, 'longitude')
                    tz = (row.get('timezone') or '').strip() or None

                    cursor.execute('''
                        INSERT OR IGNORE INTO tide_station_ids
                        (station_id, place_name, country, api_source, latitude, longitude, timezone, lookup_count, last_lookup)
                        VALUES (?, ?, 'USA', 'NOAA', ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name, latitude, longitude, tz))
                    cursor.execute('''
                        UPDATE tide_station_ids
                        SET place_name = ?, country = 'USA', api_source = 'NOAA',
                            latitude = ?, longitude = ?, timezone = COALESCE(?, timezone)
                        WHERE station_id = ?
                    ''', (place_name, latitude, longitude, tz, station_id))
                    imported_count += 1

            if csv_station_ids:
                placeholders = ','.join('?' * len(csv_station_ids))
                cursor.execute(
                    f"DELETE FROM tide_station_ids WHERE country = 'USA' AND station_id NOT IN ({placeholders})",
                    tuple(csv_station_ids))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logging.info(f"Removed {deleted_count} invalid station(s) not present in CSV")

            conn.commit()
            logging.info(f"Imported {imported_count} stations from CSV")
            return True
    except Exception as e:
        logging.error(f"Error importing stations from CSV: {e}")
        return False

def get_popular_stations(limit=16):
    """Get the most popular tide stations by lookup count (all countries).

    Thin wrapper over get_popular_stations_by_country, kept for callers that
    predate the country filter (e.g. the /health DB check); preserves its
    original three-key dict shape.
    """
    return [{
        'station_id': s['station_id'],
        'place_name': s['place_name'],
        'lookup_count': s['lookup_count'],
    } for s in get_popular_stations_by_country(None, limit)]

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

def _extract_station_id(text):
    """Pull a station ID out of free-text the search box may submit: a bare
    numeric string ("9449639"), or the autocomplete's "Place Name (12345)"
    format. Returns the digit string, or None if the text is neither shape.
    Existence is NOT checked here — the caller verifies against the directory.
    """
    if not text:
        return None
    s = text.strip()
    if s.isdigit():
        return s
    match = re.search(r'\((\d+)\)\s*$', s)
    return match.group(1) if match else None


def get_station_id_by_place_name(place_name):
    """Get the station ID for a given name.

    First resolves the unambiguous shapes the search box invites but that aren't
    place names: a bare station ID, or the autocomplete's "Name (12345)" format
    (each verified to be a real station). Then tries the official place_name
    (exact, then case-insensitive), then the CHS common/alternative name (exact,
    then case-insensitive). The alternative name fallback lets a visitor who
    types a common name (e.g. "Pender Harbour") and submits without picking from
    the autocomplete still resolve the station, consistent with what the name
    search surfaces. Returns None when nothing resolves — never a wrong station.
    """
    if not place_name:
        return None

    # Match preference order: official name beats alternative name, exact
    # match beats case-insensitive. The clauses are compile-time constants
    # interpolated into the SQL below; the user-supplied value only ever
    # binds through the ? placeholder.
    match_clauses = (
        'place_name = ?',
        'LOWER(place_name) = LOWER(?)',
        'alternative_name = ?',
        'LOWER(alternative_name) = LOWER(?)',
    )

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Unambiguous ID shortcut: only resolves if it maps to a real
            # station, so a typo'd digit string falls through to None rather
            # than silently producing a calendar for the wrong place.
            candidate_id = _extract_station_id(place_name)
            if candidate_id:
                row = cursor.execute(
                    'SELECT station_id FROM tide_station_ids WHERE station_id = ? LIMIT 1',
                    (candidate_id,)).fetchone()
                if row:
                    return row[0]

            for clause in match_clauses:
                result = cursor.execute(
                    f'SELECT station_id FROM tide_station_ids WHERE {clause} LIMIT 1',
                    (place_name,)).fetchone()
                if result:
                    return result[0]
            return None

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
                SELECT station_id, place_name, country, api_source, latitude, longitude, province, timezone
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
                    'province': result[6],
                    'timezone': result[7],
                }

            return None

    except sqlite3.Error as e:
        logging.error(f"Database error getting station info for {station_id}: {e}")
        return None

def get_stations_with_coordinates():
    """Return all stations that have non-NULL coordinates, for the map.

    Shape: [{'station_id', 'name', 'country', 'latitude', 'longitude'}].
    'name' uses the combined display label so the popup matches the autocomplete.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT station_id, place_name, country, latitude, longitude, alternative_name, province
                FROM tide_station_ids
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND place_name IS NOT NULL
            ''').fetchall()
            return [{
                'station_id': r[0],
                'name': format_display_name(r[1], r[5], r[6]),
                'country': r[2] or 'USA',
                'latitude': r[3],
                'longitude': r[4],
            } for r in rows]
    except sqlite3.Error as e:
        logging.error(f"Database error getting stations with coordinates: {e}")
        return []


def stations_to_geojson(stations):
    """Convert station dicts (from get_stations_with_coordinates) to a GeoJSON
    FeatureCollection. Pure transform — no DB access — so it's trivially testable.
    """
    return {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [s['longitude'], s['latitude']]},
            'properties': {
                'station_id': s['station_id'],
                'name': s['name'],
                'country': s['country'],
            },
        } for s in stations],
    }


def import_canadian_stations_from_csv():
    """Import Canadian tide station data from the static CSV and remove Canadian
    stations not in the CSV.

    Note: this is the CSV-only importer used by the offline maintenance scripts
    under scripts/ (test_canadian_import.py, test_multi_country_offline.py,
    test_lookup_count_preservation.py). The runtime startup path uses the
    API-based importer in canadian_station_sync.py (which falls back to its own
    CSV reader). Both write alternative_name so the column stays consistent
    regardless of which path populates the DB; the static CSV simply has no
    alternative_name column today (see follow-up doc), so it imports as NULL.
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'canadian_tide_stations.csv')

    if not os.path.exists(csv_path):
        logging.warning(f"Canadian stations CSV file not found: {csv_path}")
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check if we already have Canadian stations
            result = cursor.execute("SELECT COUNT(*) FROM tide_station_ids WHERE country = 'Canada'").fetchone()
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
                    # Tolerate a CSV without the column (defaults to NULL)
                    alternative_name = row.get('alternative_name') or None
                    tz = (row.get('timezone') or '').strip() or None

                    # Insert or update station (Canadian stations)
                    # Use INSERT OR IGNORE to preserve lookup_count for existing stations
                    cursor.execute('''
                        INSERT OR IGNORE INTO tide_station_ids
                        (station_id, place_name, country, api_source, latitude, longitude, province, alternative_name, timezone, lookup_count, last_lookup)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name, country, api_source, latitude, longitude, province, alternative_name, tz))

                    # Update metadata for existing stations without touching lookup_count
                    cursor.execute('''
                        UPDATE tide_station_ids
                        SET place_name = ?, country = ?, api_source = ?, latitude = ?, longitude = ?, province = ?, alternative_name = ?, timezone = COALESCE(?, timezone)
                        WHERE station_id = ?
                    ''', (place_name, country, api_source, latitude, longitude, province, alternative_name, tz, station_id))
                    imported_count += 1

            # Remove Canadian stations from database that are NOT in the CSV
            if csv_station_ids:
                placeholders = ','.join('?' * len(csv_station_ids))
                delete_query = f"DELETE FROM tide_station_ids WHERE country = 'Canada' AND station_id NOT IN ({placeholders})"
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

def fold_for_search(text):
    """Fold a string to a diacritic-insensitive, lowercase form for matching.

    Uses NFKD decomposition + removal of combining marks, which collapses both
    Indigenous letters (e.g. "ḵalpilin" -> "kalpilin", since U+1E35 decomposes to
    k + combining macron) and accented characters (e.g. "Bécancour" -> "becancour",
    "Île" -> "ile"). Lets a visitor find a station whether or not they reproduce
    the exact diacritics. Returns '' for falsy input.
    """
    if not text:
        return ''
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).lower()


def format_display_name(place_name, alternative_name, province=None):
    """Build a search-friendly display label for the autocomplete dropdown.

    CHS increasingly stores the Indigenous name as the official name and the
    familiar common name in a separate field (e.g. official "ḵalpilin",
    alternative "Pender Harbour"). When a distinct common name exists, lead with
    it and show the official name in parentheses, keeping the province suffix
    outside the parens:

        "ḵalpilin, BC" + "Pender Harbour"  ->  "Pender Harbour (ḵalpilin), BC"

    Falls back to place_name when there is no alternative name or it merely
    duplicates the official name (e.g. USA/NOAA stations have no alias).
    """
    if not place_name:
        return place_name

    # Lead with the first comma-segment only. CHS alternativeName is often a messy
    # list of echoes/variants (e.g. "Dumb Bell Bay, DUMB BELL BAY" or "Sugluk,
    # Salluit, Saglouc"), but the first segment is reliably the primary common name.
    # The full value stays stored for search, so every variant remains matchable;
    # only the displayed label is trimmed.
    alt = (alternative_name or '').split(',')[0].strip()
    if not alt:
        return place_name

    # Split the trailing ", PROV" suffix off the official name, if present, so
    # the province stays at the end rather than inside the parentheses. Prefer
    # an explicit province; otherwise split the trailing ", <code>" that
    # construct_place_name appends (the province column is empty when the
    # province was inferred from longitude rather than parsed from the name).
    core, suffix = place_name, ''
    if province and place_name.endswith(f", {province}"):
        core = place_name[: -len(f", {province}")]
        suffix = f", {province}"
    elif ', ' in place_name:
        candidate_core, _, tail = place_name.rpartition(', ')
        # Only strip the tail when it looks like a province/state code (the form
        # construct_place_name appends, e.g. ", BC"). Guards against mis-splitting an
        # official name that contains a comma but no province suffix. Humanized
        # labels like "Greenland" always arrive via the explicit `province` arg above.
        if len(tail) == 2 and tail.isalpha():
            core, suffix = candidate_core, f", {tail}"

    # Don't duplicate when the common name already matches the official name.
    if alt.lower() in (core.strip().lower(), place_name.strip().lower()):
        return place_name

    return f"{alt} ({core}){suffix}"


def _station_rows_to_dicts(rows):
    """Map (station_id, place_name, country, lookup_count, alternative_name,
    province) rows to the dict shape the station APIs return."""
    return [{
        'station_id': row[0],
        'place_name': row[1],
        'country': row[2],
        'lookup_count': row[3],
        'alternative_name': row[4],
        'display_name': format_display_name(row[1], row[4], row[5])
    } for row in rows]


def search_stations_by_country(query, country=None, limit=10):
    """Search for stations by place name or common (alternative) name,
    optionally filtered by country."""
    if not query or len(query.strip()) < 1:
        return []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # fold() makes matching case- AND diacritic-insensitive, so e.g.
            # "kalpilin" matches "ḵalpilin" and "becancour" matches "Bécancour".
            conn.create_function('fold', 1, fold_for_search, deterministic=True)
            cursor = conn.cursor()

            # Diacritic/case-insensitive substring search across both the official
            # place name and the CHS alternative/common name so visitors can find a
            # station by whichever name they know, however they type it. Fold the
            # query in Python and apply fold() only to the columns in SQL.
            folded_query = f"%{fold_for_search(query.strip())}%"

            country_clause = 'AND country = ?' if country else ''
            params = [folded_query, folded_query] + ([country] if country else []) + [limit]
            results = cursor.execute(f'''
                SELECT station_id, place_name, country, lookup_count, alternative_name, province
                FROM tide_station_ids
                WHERE place_name IS NOT NULL
                AND (fold(place_name) LIKE ? OR fold(alternative_name) LIKE ?)
                {country_clause}
                ORDER BY lookup_count DESC, place_name ASC
                LIMIT ?
            ''', params).fetchall()

            return _station_rows_to_dicts(results)

    except sqlite3.Error as e:
        logging.error(f"Database error searching stations: {e}")
        return []

def get_popular_stations_by_country(country=None, limit=16):
    """Get the most popular tide stations, optionally filtered by country."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            country_clause = 'AND country = ?' if country else ''
            params = ([country] if country else []) + [limit]
            results = cursor.execute(f'''
                SELECT station_id, place_name, country, lookup_count, alternative_name, province
                FROM tide_station_ids
                WHERE place_name IS NOT NULL
                {country_clause}
                ORDER BY lookup_count DESC, place_name ASC
                LIMIT ?
            ''', params).fetchall()

            return _station_rows_to_dicts(results)

    except sqlite3.Error as e:
        logging.error(f"Database error getting popular stations: {e}")
        return []


def backfill_timezones_from_csv(csv_paths=None):
    """Fill NULL/empty `timezone` on existing DB rows from the shipped CSVs.

    Needed because the US CSV import short-circuits on a warm DB, and Canadian
    stations imported via the live CHS API have no timezone. Source is the
    shipped CSV (no network, no heavy library). Idempotent. Returns rows updated.
    """
    if csv_paths is None:
        here = os.path.dirname(__file__)
        csv_paths = [os.path.join(here, 'tide_stations_new.csv'),
                     os.path.join(here, 'canadian_tide_stations.csv')]
    updated = 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            for path in csv_paths:
                if not os.path.exists(path):
                    continue
                with open(path, 'r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        tz = (row.get('timezone') or '').strip()
                        sid = row.get('station_id')
                        if not tz or not sid:
                            continue
                        cur = conn.execute(
                            "UPDATE tide_station_ids SET timezone = ? "
                            "WHERE station_id = ? AND (timezone IS NULL OR timezone = '')",
                            (tz, sid))
                        updated += cur.rowcount
            conn.commit()
        logging.info("Timezone backfill: set timezone on %d station(s)", updated)
        return updated
    except (sqlite3.Error, OSError) as e:
        logging.error("Timezone backfill failed: %s", e)
        return updated