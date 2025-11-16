#!/usr/bin/env python3
"""
Test to verify that CSV imports preserve lookup_count values.
This validates the fix for the INSERT OR REPLACE bug.
"""

import sys
import os
from pathlib import Path

# Add app directory to path for imports
APP_DIR = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))

from database import (
    init_database,
    import_stations_from_csv,
    import_canadian_stations_from_csv,
    log_station_lookup,
    get_station_info,
    DB_PATH
)
import sqlite3

def test_usa_lookup_preservation():
    """Test that USA station lookup counts are preserved on re-import."""
    print("\n=== Testing USA Station Lookup Count Preservation ===")

    # Initialize and import
    init_database()
    import_stations_from_csv()

    # Get a test station (Point Roberts, WA)
    test_station = "9449639"

    # Check initial lookup count (should be 1 from import)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?',
                              (test_station,)).fetchone()
        initial_count = result[0] if result else 0
        print(f"Initial lookup_count for {test_station}: {initial_count}")

    # Log some lookups to increase the count
    log_station_lookup(test_station)
    log_station_lookup(test_station)
    log_station_lookup(test_station)

    # Check count after manual lookups
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?',
                              (test_station,)).fetchone()
        after_lookups = result[0] if result else 0
        print(f"Lookup_count after 3 manual lookups: {after_lookups}")

    # Re-import CSV (simulating app restart)
    print("Re-importing CSV (simulating app restart)...")
    import_stations_from_csv()

    # Check count after re-import (should be preserved!)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?',
                              (test_station,)).fetchone()
        after_reimport = result[0] if result else 0
        print(f"Lookup_count after CSV re-import: {after_reimport}")

    if after_reimport == after_lookups:
        print("✓ PASS: Lookup count preserved after re-import!")
        return True
    else:
        print(f"✗ FAIL: Lookup count changed! Expected {after_lookups}, got {after_reimport}")
        return False

def test_canadian_lookup_preservation():
    """Test that Canadian station lookup counts are preserved on re-import."""
    print("\n=== Testing Canadian Station Lookup Count Preservation ===")

    # Import Canadian stations
    import_canadian_stations_from_csv()

    # Get a test station (Vancouver, BC)
    test_station = "07735"

    # Check initial lookup count
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?',
                              (test_station,)).fetchone()
        initial_count = result[0] if result else 0
        print(f"Initial lookup_count for {test_station}: {initial_count}")

    # Log some lookups
    log_station_lookup(test_station)
    log_station_lookup(test_station)
    log_station_lookup(test_station)
    log_station_lookup(test_station)
    log_station_lookup(test_station)

    # Check count after manual lookups
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?',
                              (test_station,)).fetchone()
        after_lookups = result[0] if result else 0
        print(f"Lookup_count after 5 manual lookups: {after_lookups}")

    # Re-import CSV
    print("Re-importing Canadian CSV (simulating app restart)...")
    import_canadian_stations_from_csv()

    # Check count after re-import
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?',
                              (test_station,)).fetchone()
        after_reimport = result[0] if result else 0
        print(f"Lookup_count after CSV re-import: {after_reimport}")

    if after_reimport == after_lookups:
        print("✓ PASS: Lookup count preserved after re-import!")
        return True
    else:
        print(f"✗ FAIL: Lookup count changed! Expected {after_lookups}, got {after_reimport}")
        return False

def main():
    print("="*70)
    print("LOOKUP COUNT PRESERVATION TEST")
    print("="*70)
    print("This test verifies that CSV re-imports preserve lookup_count values.")
    print("Bug: INSERT OR REPLACE resets lookup_count to 1")
    print("Fix: INSERT OR IGNORE + UPDATE preserves lookup_count")
    print("="*70)

    usa_pass = test_usa_lookup_preservation()
    canadian_pass = test_canadian_lookup_preservation()

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"USA stations: {'✓ PASS' if usa_pass else '✗ FAIL'}")
    print(f"Canadian stations: {'✓ PASS' if canadian_pass else '✗ FAIL'}")

    if usa_pass and canadian_pass:
        print("\n✓ All tests PASSED - Lookup counts are preserved!")
        return 0
    else:
        print("\n✗ Some tests FAILED - Lookup counts are being reset!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
