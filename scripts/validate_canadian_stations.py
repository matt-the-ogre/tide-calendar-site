#!/usr/bin/env python3
"""
Validate Canadian tide stations against CHS IWLS API.

This script checks each station in canadian_tide_stations.csv to ensure:
1. Station exists in CHS API
2. Station is operating (operating: true)
3. Station has wlp-hilo (High/Low Tide Predictions) time series available

Stations that fail validation are removed from the CSV.
A timestamped backup is created before modification.
"""

import csv
import requests
import time
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add app directory to path for imports
APP_DIR = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# CHS API endpoints
CHS_BASE_URLS = [
    "https://api.iwls-sine.azure.cloud-nuage.dfo-mpo.gc.ca/api/v1",
    "https://api-iwls.dfo-mpo.gc.ca/api/v1"
]

HEADERS = {
    'User-Agent': 'TideCalendarSite/1.0 (https://tidecalendar.xyz; validation script)'
}

def validate_station(station_code, station_name):
    """
    Validate a single station against CHS API.

    Returns:
        tuple: (is_valid: bool, reason: str)
    """
    # Try to get station metadata from CHS API
    for base_url in CHS_BASE_URLS:
        try:
            url = f"{base_url}/stations"
            params = {"code": station_code}

            response = requests.get(url, params=params, headers=HEADERS, timeout=30)

            if response.status_code != 200:
                continue

            stations = response.json()

            if not stations or len(stations) == 0:
                return False, f"Station not found in CHS directory"

            station_data = stations[0]

            # Check if station is operating
            if not station_data.get('operating', False):
                return False, f"Station not operating (status: {station_data.get('operating')})"

            # Check if station type is PERMANENT or ACTIVE
            station_type = station_data.get('type', '')
            if station_type == 'TEMPORARY':
                return False, f"Station is temporary (type: {station_type})"

            # Check if wlp-hilo time series is available
            time_series = station_data.get('timeSeries', [])
            has_hilo = any(ts.get('code') == 'wlp-hilo' for ts in time_series)

            if not has_hilo:
                available_series = [ts.get('code') for ts in time_series]
                return False, f"No wlp-hilo predictions available (has: {available_series})"

            # All checks passed
            logging.debug(f"✓ {station_code} ({station_name}) - Valid")
            return True, "Valid"

        except requests.exceptions.RequestException as e:
            logging.warning(f"Network error checking {station_code} at {base_url}: {e}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error checking {station_code}: {e}")
            return False, f"Error: {e}"

    return False, "All API endpoints failed"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate Canadian tide stations CSV")
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be removed without modifying the CSV')
    args = parser.parse_args()

    csv_path = APP_DIR / 'canadian_tide_stations.csv'

    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        return 1

    # Read all stations
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        stations = list(reader)
        fieldnames = reader.fieldnames

    logging.info(f"Validating {len(stations)} Canadian stations...")
    logging.info("This may take several minutes...")

    valid_stations = []
    invalid_stations = []

    for i, station in enumerate(stations, 1):
        station_id = station['station_id']
        station_name = station['place_name']

        # Progress indicator
        if i % 10 == 0:
            logging.info(f"Progress: {i}/{len(stations)} stations checked")

        is_valid, reason = validate_station(station_id, station_name)

        if is_valid:
            valid_stations.append(station)
        else:
            invalid_stations.append((station, reason))
            logging.warning(f"✗ {station_id} ({station_name}): {reason}")

        # Rate limiting: 0.5s delay between requests (~2 req/sec)
        time.sleep(0.5)

    # Print summary
    logging.info("\n" + "="*70)
    logging.info("VALIDATION SUMMARY")
    logging.info("="*70)
    logging.info(f"Total stations checked: {len(stations)}")
    logging.info(f"Valid stations: {len(valid_stations)}")
    logging.info(f"Invalid stations: {len(invalid_stations)}")

    if invalid_stations:
        logging.info("\nInvalid stations to be removed:")
        for station, reason in invalid_stations:
            logging.info(f"  - {station['station_id']} ({station['place_name']}): {reason}")

    if args.dry_run:
        logging.info("\n[DRY RUN] No changes made to CSV file")
        return 0

    if not invalid_stations:
        logging.info("\nAll stations are valid! No changes needed.")
        return 0

    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = csv_path.parent.parent / 'backup' / f'canadian_tide_stations.csv.backup.{timestamp}'
    backup_path.parent.mkdir(exist_ok=True)

    import shutil
    shutil.copy2(csv_path, backup_path)
    logging.info(f"\nBackup created: {backup_path}")

    # Write updated CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_stations)

    logging.info(f"Updated CSV written: {csv_path}")
    logging.info(f"Removed {len(invalid_stations)} inactive stations")

    return 0


if __name__ == '__main__':
    sys.exit(main())
