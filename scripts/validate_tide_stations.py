#!/usr/bin/env python3
"""
Validate tide stations CSV by testing each station against NOAA API.
Removes stations that don't have prediction data available.

Rate Limiting: Includes 0.25s delay between requests (~4 req/sec) to respect NOAA API limits.
Expected runtime: ~12-15 minutes for ~2900 stations.

Usage:
    python3 validate_tide_stations.py [--dry-run]

Options:
    --dry-run    Show what would be removed without making changes
"""

import csv
import requests
import calendar
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_station(station_id, year, month):
    """
    Test if a station has prediction data available from NOAA API.

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    # Calculate the last day of the month
    _, last_day = calendar.monthrange(year, month)

    # Construct the NOAA API request
    base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    params = {
        "begin_date": f"{year}{month:02d}01",
        "end_date": f"{year}{month:02d}{last_day}",
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "interval": "hilo",
        "units": "metric",
        "format": "csv",
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        # Check if response contains actual data (not just an error message)
        content = response.text
        lines = content.strip().split('\n')

        if len(lines) < 2:
            return False, "Empty response"

        # Check for NOAA's error message
        if "No Predictions data was found" in content:
            return False, "No predictions data"

        if "Error" in lines[0] or "error" in content.lower():
            return False, "API error response"

        return True, None

    except requests.Timeout:
        return False, "Request timeout"
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def validate_csv(csv_path, dry_run=False):
    """
    Validate all stations in the CSV file.

    Args:
        csv_path: Path to the tide_stations_new.csv file
        dry_run: If True, don't modify the CSV, just report what would change

    Returns:
        dict: Statistics about the validation run
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        return None

    # Get current month and year for testing
    now = datetime.now()
    year = now.year
    month = now.month

    logging.info(f"Testing stations with NOAA API for {year}-{month:02d}")
    logging.info(f"Reading from: {csv_path}")

    # Read all stations from CSV
    valid_stations = []
    invalid_stations = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            station_id = row['station_id']
            place_name = row['place_name']

            logging.info(f"Testing station {station_id}: {place_name}")

            success, error = test_station(station_id, year, month)

            if success:
                valid_stations.append(row)
                logging.info(f"  ✓ Valid")
            else:
                invalid_stations.append({
                    'station_id': station_id,
                    'place_name': place_name,
                    'reason': error
                })
                logging.warning(f"  ✗ Invalid: {error}")

            # Add 0.25 second delay between requests to respect NOAA API rate limits
            # This limits us to ~4 requests/second, well below the 5/second limit seen in other NOAA APIs
            time.sleep(0.25)

    # Generate statistics
    total = len(valid_stations) + len(invalid_stations)
    stats = {
        'total_tested': total,
        'valid_count': len(valid_stations),
        'invalid_count': len(invalid_stations),
        'valid_stations': valid_stations,
        'invalid_stations': invalid_stations
    }

    # Create backup and write new CSV (unless dry-run)
    if not dry_run and invalid_stations:
        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_path = csv_path.with_suffix(f'.csv.backup.{timestamp}')

        logging.info(f"Creating backup: {backup_path}")
        import shutil
        shutil.copy2(csv_path, backup_path)

        # Write validated CSV
        logging.info(f"Writing validated CSV with {len(valid_stations)} stations")
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(valid_stations)

        logging.info(f"✓ CSV updated successfully")

    return stats

def print_report(stats, dry_run=False):
    """Print a detailed validation report."""

    print("\n" + "="*70)
    print("TIDE STATIONS VALIDATION REPORT")
    print("="*70)

    if dry_run:
        print("MODE: DRY RUN (no changes made)")
    else:
        print("MODE: LIVE (CSV updated)")

    print(f"\nTotal Stations Tested: {stats['total_tested']}")
    print(f"Valid Stations:        {stats['valid_count']} ({stats['valid_count']/stats['total_tested']*100:.1f}%)")
    print(f"Invalid Stations:      {stats['invalid_count']} ({stats['invalid_count']/stats['total_tested']*100:.1f}%)")

    if stats['invalid_stations']:
        print(f"\n{'='*70}")
        print("INVALID STATIONS (to be removed)")
        print("="*70)
        print(f"{'Station ID':<15} {'Place Name':<40} {'Reason':<15}")
        print("-"*70)

        for station in stats['invalid_stations']:
            station_id = station['station_id']
            place_name = station['place_name'][:38]  # Truncate if too long
            reason = station['reason'][:13]  # Truncate if too long
            print(f"{station_id:<15} {place_name:<40} {reason:<15}")

    print("\n" + "="*70)

    if dry_run and stats['invalid_stations']:
        print("\nTo actually remove invalid stations, run without --dry-run flag:")
        print("  python3 validate_tide_stations.py")
    elif not dry_run and stats['invalid_stations']:
        print(f"\n✓ CSV has been updated with {stats['valid_count']} valid stations")
        print(f"✓ Backup created with timestamp")
    elif not stats['invalid_stations']:
        print("\n✓ All stations are valid! No changes needed.")

    print()

def main():
    parser = argparse.ArgumentParser(
        description="Validate tide stations CSV against NOAA API"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without making changes'
    )

    args = parser.parse_args()

    # Path to CSV file
    csv_path = Path(__file__).parent / 'tide_stations_new.csv'

    # Run validation
    stats = validate_csv(csv_path, dry_run=args.dry_run)

    if stats:
        print_report(stats, dry_run=args.dry_run)
    else:
        logging.error("Validation failed")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
