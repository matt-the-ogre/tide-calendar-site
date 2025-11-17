"""
Canadian Tide Station Synchronization Module

Dynamically imports Canadian tide stations from the CHS IWLS API on container startup.
Ensures only active, operating stations with high/low tide prediction data are available.

This replaces the static canadian_tide_stations.csv approach with real-time API data.
"""

import logging
import requests
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Database path
APP_DIR = Path(__file__).parent.resolve()
DEFAULT_DB_PATH = str(APP_DIR / 'tide_station_ids.db')
DB_PATH = os.getenv('DB_PATH', DEFAULT_DB_PATH)

# CHS API endpoints (try both Azure and legacy)
CHS_BASE_URLS = [
    "https://api.iwls-sine.azure.cloud-nuage.dfo-mpo.gc.ca/api/v1",
    "https://api-iwls.dfo-mpo.gc.ca/api/v1"
]

HEADERS = {
    'User-Agent': 'TideCalendarSite/1.0 (https://tidecalendar.xyz; dynamic station sync)'
}

# Province codes for Canadian provinces/territories
PROVINCE_CODES = {
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
}


def extract_province_from_name(official_name: str) -> Optional[str]:
    """
    Extract province code from official station name.

    Examples:
        "Vancouver" -> None (no province in name)
        "Point Atkinson, BC" -> "BC"
        "Halifax, NS" -> "NS"

    Args:
        official_name: Station's official name from CHS API

    Returns:
        Two-letter province code or None if not found
    """
    if not official_name:
        return None

    # Check if last part after comma is a province code
    parts = [p.strip() for p in official_name.split(',')]
    if len(parts) > 1:
        last_part = parts[-1].upper()
        if last_part in PROVINCE_CODES:
            return last_part

    return None


def construct_place_name(official_name: str, province: Optional[str], latitude: float, longitude: float) -> str:
    """
    Construct a human-readable place name with province.

    If province is not in the name, infer from longitude:
    - Western provinces (BC, AB, SK, MB): longitude < -95
    - Eastern provinces: longitude >= -95

    Args:
        official_name: Station's official name
        province: Province code if known
        latitude: Station latitude
        longitude: Station longitude

    Returns:
        Formatted place name (e.g., "Vancouver, BC")
    """
    if not official_name:
        return "Unknown"

    # If province already in name, return as-is
    if province and official_name.endswith(f", {province}"):
        return official_name

    # If we have province code, append it
    if province:
        return f"{official_name}, {province}"

    # Infer province from longitude (rough approximation)
    # Most Canadian tide stations are on the coasts (BC, NS, NL, etc.)
    if longitude < -120:
        inferred_province = "BC"
    elif longitude < -95:
        inferred_province = "MB"  # or other prairie province
    elif longitude >= -95 and latitude > 50:
        inferred_province = "NT"  # Northern territories
    elif longitude >= -95 and longitude < -60:
        inferred_province = "QC"  # Quebec/Maritime
    else:
        inferred_province = "NL"  # Newfoundland/Atlantic

    return f"{official_name}, {inferred_province}"


def fetch_canadian_stations_from_api() -> Tuple[Optional[List[Dict]], str]:
    """
    Fetch all operating Canadian stations with wlp-hilo predictions from CHS API.

    Filtering criteria:
    - operating: true (station is active)
    - type: "PERMANENT" (exclude temporary/discontinued stations)
    - Has "wlp-hilo" in timeSeries array (high/low tide predictions available)

    Returns:
        Tuple of (stations_list, endpoint_used) or (None, error_message)
        Each station dict contains: code, officialName, latitude, longitude, province, place_name
    """
    import json

    # Try each API endpoint
    for base_url in CHS_BASE_URLS:
        try:
            url = f"{base_url}/stations"
            logging.info(f"Fetching Canadian stations from {base_url}...")

            response = requests.get(url, headers=HEADERS, timeout=30)

            if response.status_code != 200:
                logging.warning(f"CHS API at {base_url} returned status {response.status_code}")
                continue

            # Parse JSON response
            all_stations = json.loads(response.text)
            logging.debug(f"Received {len(all_stations)} total stations from API")

            # Filter stations
            valid_stations = []
            for station in all_stations:
                # Check if operating
                if not station.get('operating', False):
                    continue

                # Check if type is PERMANENT
                station_type = station.get('type', '')
                if station_type != 'PERMANENT':
                    continue

                # Check if has wlp-hilo time series
                time_series = station.get('timeSeries', [])
                has_hilo = any(ts.get('code') == 'wlp-hilo' for ts in time_series)
                if not has_hilo:
                    continue

                # Extract station data
                code = station.get('code')
                official_name = station.get('officialName', '')
                latitude = station.get('latitude', 0.0)
                longitude = station.get('longitude', 0.0)

                if not code or not official_name:
                    logging.warning(f"Station missing code or name: {station}")
                    continue

                # Extract province and construct place name
                province = extract_province_from_name(official_name)
                place_name = construct_place_name(official_name, province, latitude, longitude)

                valid_stations.append({
                    'code': code,
                    'officialName': official_name,
                    'latitude': latitude,
                    'longitude': longitude,
                    'province': province or '',
                    'place_name': place_name
                })

            logging.info(f"Found {len(valid_stations)} of {len(all_stations)} stations operating with wlp-hilo data")
            return valid_stations, base_url

        except requests.exceptions.RequestException as e:
            logging.warning(f"Network error fetching from {base_url}: {e}")
            continue
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from {base_url}: {e}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error fetching from {base_url}: {e}")
            continue

    # All endpoints failed
    error_msg = "All CHS API endpoints failed"
    logging.error(error_msg)
    return None, error_msg


def import_canadian_stations_from_csv() -> bool:
    """
    Fallback: Import Canadian stations from static CSV file.

    This is used when the API is unavailable.

    Returns:
        True if successful, False otherwise
    """
    import csv

    csv_path = APP_DIR / 'canadian_tide_stations.csv'

    if not csv_path.exists():
        logging.warning(f"CSV fallback file not found: {csv_path}")
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Read CSV
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                stations = list(reader)

            logging.info(f"Importing {len(stations)} Canadian stations from CSV fallback...")

            # Import each station
            for station in stations:
                cursor.execute('''
                    INSERT INTO tide_station_ids (station_id, place_name, country, api_source, latitude, longitude, province)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(station_id) DO UPDATE SET
                        place_name = excluded.place_name,
                        country = excluded.country,
                        api_source = excluded.api_source,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        province = excluded.province
                ''', (
                    station['station_id'],
                    station.get('place_name', ''),
                    'Canada',
                    'CHS',
                    float(station.get('latitude', 0)),
                    float(station.get('longitude', 0)),
                    station.get('province', '')
                ))

            conn.commit()
            logging.info(f"Successfully imported {len(stations)} Canadian stations from CSV")
            return True

    except (sqlite3.Error, IOError, ValueError) as e:
        logging.error(f"Error importing Canadian stations from CSV: {e}")
        return False


def import_canadian_stations_from_api() -> bool:
    """
    Import Canadian tide stations from CHS API with CSV fallback.

    This function is called on container startup to sync the database with
    the latest operating stations from the CHS IWLS API.

    Behavior:
    1. Try to fetch stations from CHS API
    2. If successful, sync database with API data
    3. If API fails, fall back to CSV import
    4. If both fail, log error but don't crash app

    Returns:
        True if import succeeded (API or CSV), False otherwise
    """
    # Try API import first
    stations, source = fetch_canadian_stations_from_api()

    if stations is None:
        # API failed, try CSV fallback
        logging.warning("CHS API import failed, attempting CSV fallback...")
        return import_canadian_stations_from_csv()

    # API succeeded, import to database
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Get list of station codes from API for sync
            api_station_codes = set(s['code'] for s in stations)

            # Import/update each station
            for station in stations:
                cursor.execute('''
                    INSERT INTO tide_station_ids (station_id, place_name, country, api_source, latitude, longitude, province)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(station_id) DO UPDATE SET
                        place_name = excluded.place_name,
                        country = excluded.country,
                        api_source = excluded.api_source,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        province = excluded.province
                ''', (
                    station['code'],
                    station['place_name'],
                    'Canada',
                    'CHS',
                    station['latitude'],
                    station['longitude'],
                    station['province']
                ))

            # Sync: Remove Canadian stations not in API response (preserving lookup_count)
            # This removes stations that are no longer operating or have been removed from API
            cursor.execute('''
                DELETE FROM tide_station_ids
                WHERE country = 'Canada'
                AND api_source = 'CHS'
                AND station_id NOT IN ({})
            '''.format(','.join('?' * len(api_station_codes))), tuple(api_station_codes))

            deleted_count = cursor.rowcount

            conn.commit()

            logging.info(f"Successfully imported {len(stations)} Canadian stations from API ({source})")
            if deleted_count > 0:
                logging.info(f"Removed {deleted_count} Canadian stations no longer in API")

            return True

    except sqlite3.Error as e:
        logging.error(f"Database error importing Canadian stations: {e}")
        logging.warning("Attempting CSV fallback after database error...")
        return import_canadian_stations_from_csv()
    except Exception as e:
        logging.error(f"Unexpected error importing Canadian stations: {e}")
        logging.warning("Attempting CSV fallback after unexpected error...")
        return import_canadian_stations_from_csv()
