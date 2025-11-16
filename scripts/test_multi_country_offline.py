#!/usr/bin/env python3
"""
Offline testing script for multi-country tide station implementation.
Tests components that don't require API access.

Run from project root: python3 scripts/test_multi_country_offline.py
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add app directory to path for imports
APP_DIR = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))

from database import (
    get_station_info,
    search_stations_by_country,
    init_database,
    import_stations_from_csv,
    import_canadian_stations_from_csv
)
from tide_adapters import (
    NOAAAdapter,
    CHSAdapter,
    get_adapter_for_station
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestResults:
    """Track test results and statistics."""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.total += 1
        self.passed += 1
        logger.info(f"✓ PASS: {test_name}")

    def add_fail(self, test_name, error):
        self.total += 1
        self.failed += 1
        self.errors.append((test_name, error))
        logger.error(f"✗ FAIL: {test_name}")
        logger.error(f"  Error: {error}")

    def print_summary(self):
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {((self.passed/self.total*100) if self.total > 0 else 0):.1f}%")

        if self.errors:
            print("\n" + "-"*70)
            print("FAILED TESTS")
            print("-"*70)
            for test_name, error in self.errors:
                print(f"✗ {test_name}")
                print(f"  {error}")

        print("="*70)

results = TestResults()

def test_database_initialization():
    """Test database initialization and CSV import."""
    logger.info("\n--- Testing Database Initialization ---")

    try:
        # Initialize database schema
        init_database()
        results.add_pass("Database schema initialization")
    except Exception as e:
        results.add_fail("Database schema initialization", str(e))
        return

    try:
        # Import USA stations from CSV
        success = import_stations_from_csv()
        if success:
            results.add_pass("Import USA stations from CSV")
        else:
            results.add_fail("Import USA stations from CSV", "Import function returned False")
    except Exception as e:
        results.add_fail("Import USA stations from CSV", str(e))

    try:
        # Import Canadian stations from CSV
        success = import_canadian_stations_from_csv()
        if success:
            results.add_pass("Import Canadian stations from CSV")
        else:
            results.add_fail("Import Canadian stations from CSV", "Import function returned False")
    except Exception as e:
        results.add_fail("Import Canadian stations from CSV", str(e))

def test_adapter_validation():
    """Test adapter station ID validation."""
    logger.info("\n--- Testing Adapter Validation ---")

    # Test NOAA adapter
    noaa = NOAAAdapter()
    test_cases = [
        ("9449639", True, "Valid NOAA 7-digit"),
        ("944963", True, "Valid NOAA 6-digit"),
        ("94496391", True, "Valid NOAA 8-digit"),
        ("abc1234", False, "Invalid NOAA non-numeric"),
        ("12345", False, "Invalid NOAA too short"),
    ]

    for station_id, expected, description in test_cases:
        result = noaa.validate_station(station_id)
        if result == expected:
            results.add_pass(f"NOAA validation: {description}")
        else:
            results.add_fail(f"NOAA validation: {description}",
                           f"Expected {expected}, got {result}")

    # Test CHS adapter
    chs = CHSAdapter()
    test_cases = [
        ("07735", True, "Valid CHS 5-digit"),
        ("0773", True, "Valid CHS 4-digit"),
        ("077356", True, "Valid CHS 6-digit"),
        ("abc12", False, "Invalid CHS non-numeric"),
        ("123", False, "Invalid CHS too short"),
    ]

    for station_id, expected, description in test_cases:
        result = chs.validate_station(station_id)
        if result == expected:
            results.add_pass(f"CHS validation: {description}")
        else:
            results.add_fail(f"CHS validation: {description}",
                           f"Expected {expected}, got {result}")

def test_adapter_factory():
    """Test adapter factory function."""
    logger.info("\n--- Testing Adapter Factory ---")

    # Test explicit API source
    try:
        adapter = get_adapter_for_station("9449639", "NOAA")
        if isinstance(adapter, NOAAAdapter):
            results.add_pass("Factory creates NOAA adapter with explicit source")
        else:
            results.add_fail("Factory creates NOAA adapter with explicit source",
                           f"Got {type(adapter).__name__}")
    except Exception as e:
        results.add_fail("Factory creates NOAA adapter with explicit source", str(e))

    try:
        adapter = get_adapter_for_station("07735", "CHS")
        if isinstance(adapter, CHSAdapter):
            results.add_pass("Factory creates CHS adapter with explicit source")
        else:
            results.add_fail("Factory creates CHS adapter with explicit source",
                           f"Got {type(adapter).__name__}")
    except Exception as e:
        results.add_fail("Factory creates CHS adapter with explicit source", str(e))

    # Test auto-detection
    try:
        adapter = get_adapter_for_station("9449639")
        if isinstance(adapter, NOAAAdapter):
            results.add_pass("Factory auto-detects NOAA adapter")
        else:
            results.add_fail("Factory auto-detects NOAA adapter",
                           f"Got {type(adapter).__name__}")
    except Exception as e:
        results.add_fail("Factory auto-detects NOAA adapter", str(e))

    try:
        adapter = get_adapter_for_station("07735")
        if isinstance(adapter, CHSAdapter):
            results.add_pass("Factory auto-detects CHS adapter")
        else:
            results.add_fail("Factory auto-detects CHS adapter",
                           f"Got {type(adapter).__name__}")
    except Exception as e:
        results.add_fail("Factory auto-detects CHS adapter", str(e))

    # Test invalid station
    try:
        adapter = get_adapter_for_station("invalid")
        results.add_fail("Factory rejects invalid station",
                       "Expected ValueError but got adapter")
    except ValueError:
        results.add_pass("Factory rejects invalid station")
    except Exception as e:
        results.add_fail("Factory rejects invalid station",
                       f"Wrong exception: {type(e).__name__}")

def test_station_info():
    """Test station info retrieval from database."""
    logger.info("\n--- Testing Station Info Retrieval ---")

    # Test Canadian station
    try:
        info = get_station_info("07735")  # Vancouver
        if info and info.get('api_source') == 'CHS':
            results.add_pass(f"Get Canadian station info (Vancouver: {info.get('place_name')})")
        else:
            results.add_fail("Get Canadian station info",
                           f"Wrong API source: {info.get('api_source') if info else 'None'}")
    except Exception as e:
        results.add_fail("Get Canadian station info", str(e))

    try:
        info = get_station_info("00490")  # Halifax
        if info and info.get('api_source') == 'CHS':
            results.add_pass(f"Get Canadian station info (Halifax: {info.get('place_name')})")
        else:
            results.add_fail("Get Canadian station info (Halifax)",
                           f"Wrong API source: {info.get('api_source') if info else 'None'}")
    except Exception as e:
        results.add_fail("Get Canadian station info (Halifax)", str(e))

    # Test USA station
    try:
        info = get_station_info("9449639")  # Point Roberts
        if info and info.get('api_source') == 'NOAA':
            results.add_pass(f"Get USA station info (Point Roberts: {info.get('place_name')})")
        else:
            results.add_fail("Get USA station info",
                           f"Wrong API source: {info.get('api_source') if info else 'None'}")
    except Exception as e:
        results.add_fail("Get USA station info", str(e))

    try:
        info = get_station_info("9447130")  # Seattle
        if info and info.get('api_source') == 'NOAA':
            results.add_pass(f"Get USA station info (Seattle: {info.get('place_name')})")
        else:
            results.add_fail("Get USA station info (Seattle)",
                           f"Wrong API source: {info.get('api_source') if info else 'None'}")
    except Exception as e:
        results.add_fail("Get USA station info (Seattle)", str(e))

def test_database_country_search():
    """Test country-specific database queries."""
    logger.info("\n--- Testing Database Country Queries ---")

    # Test search by country - USA
    try:
        usa_results = search_stations_by_country("Seattle", "USA", limit=5)
        if len(usa_results) > 0:
            usa_only = all(r['country'] == 'USA' for r in usa_results)
            if usa_only:
                results.add_pass(f"Search USA stations (found {len(usa_results)})")
            else:
                results.add_fail("Search USA stations", "Non-USA stations in results")
        else:
            results.add_fail("Search USA stations", "No results")
    except Exception as e:
        results.add_fail("Search USA stations", str(e))

    # Test search by country - Canada
    try:
        canada_results = search_stations_by_country("Vancouver", "Canada", limit=5)
        if len(canada_results) > 0:
            canada_only = all(r['country'] == 'Canada' for r in canada_results)
            if canada_only:
                results.add_pass(f"Search Canadian stations (found {len(canada_results)})")
            else:
                results.add_fail("Search Canadian stations", "Non-Canadian stations in results")
        else:
            results.add_fail("Search Canadian stations", "No results")
    except Exception as e:
        results.add_fail("Search Canadian stations", str(e))

    # Test search all countries
    try:
        all_results = search_stations_by_country("Point", None, limit=10)
        if len(all_results) > 0:
            countries = set(r['country'] for r in all_results)
            results.add_pass(f"Search all countries (found {len(all_results)} across {len(countries)} countries)")
        else:
            results.add_fail("Search all countries", "No results")
    except Exception as e:
        results.add_fail("Search all countries", str(e))

    # Test Canadian stations exist in database
    try:
        bc_stations = search_stations_by_country("BC", "Canada", limit=20)
        if len(bc_stations) >= 5:
            results.add_pass(f"Canadian BC stations in database (found {len(bc_stations)})")
        else:
            results.add_fail("Canadian BC stations in database",
                           f"Expected at least 5, found {len(bc_stations)}")
    except Exception as e:
        results.add_fail("Canadian BC stations in database", str(e))

def test_csv_format_parsing():
    """Test parsing of CSV data format."""
    logger.info("\n--- Testing CSV Data Parsing ---")

    # Test NOAA CSV parsing
    noaa = NOAAAdapter()
    sample_noaa_csv = """Date,Time, Prediction, Type
2024-06-01,00:17, 3.245, H
2024-06-01,06:23, -0.142, L
2024-06-01,12:45, 3.456, H
2024-06-01,18:52, 0.123, L"""

    try:
        result = noaa.parse_response(sample_noaa_csv)
        if result and len(result.split('\n')) == 5:  # Header + 4 data lines
            results.add_pass("NOAA CSV parsing")
        else:
            line_count = len(result.split('\n')) if result else 0
            results.add_fail("NOAA CSV parsing", f"Wrong line count: {line_count}")
    except Exception as e:
        results.add_fail("NOAA CSV parsing", str(e))

    # Test CHS JSON parsing
    chs = CHSAdapter()
    sample_chs_json = """{
  "data": [
    {"eventDate": "2024-06-01T05:23:00Z", "value": 0.5},
    {"eventDate": "2024-06-01T11:45:00Z", "value": 4.8},
    {"eventDate": "2024-06-01T17:23:00Z", "value": 0.3},
    {"eventDate": "2024-06-01T23:45:00Z", "value": 5.1}
  ]
}"""

    try:
        result = chs.parse_response(sample_chs_json)
        if result and len(result.split('\n')) == 5:  # Header + 4 data lines
            results.add_pass("CHS JSON parsing")
        else:
            line_count = len(result.split('\n')) if result else 0
            results.add_fail("CHS JSON parsing", f"Wrong line count: {line_count}")
    except Exception as e:
        results.add_fail("CHS JSON parsing", str(e))

def test_edge_cases():
    """Test edge cases and error handling."""
    logger.info("\n--- Testing Edge Cases ---")

    # Test invalid month
    adapter = NOAAAdapter()
    try:
        result = adapter.get_predictions("9449639", 2024, 13)  # Invalid month
        if result is None:
            results.add_pass("Reject invalid month (13)")
        else:
            results.add_fail("Reject invalid month (13)", "Should return None")
    except Exception as e:
        results.add_fail("Reject invalid month (13)", str(e))

    # Test invalid year
    try:
        result = adapter.get_predictions("9449639", 1999, 1)  # Too early
        if result is None:
            results.add_pass("Reject invalid year (1999)")
        else:
            results.add_fail("Reject invalid year (1999)", "Should return None")
    except Exception as e:
        results.add_fail("Reject invalid year (1999)", str(e))

    # Test invalid station ID format
    try:
        result = adapter.get_predictions("invalid", 2024, 6)
        if result is None:
            results.add_pass("Reject invalid station ID format")
        else:
            results.add_fail("Reject invalid station ID format", "Should return None")
    except Exception as e:
        results.add_fail("Reject invalid station ID format", str(e))

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("MULTI-COUNTRY TIDE STATION OFFLINE TEST SUITE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNote: API tests skipped (require network access)")
    print("Testing: Adapters, Database, CSV parsing, Validation")

    # Run all test suites
    test_database_initialization()
    test_adapter_validation()
    test_adapter_factory()
    test_station_info()
    test_database_country_search()
    test_csv_format_parsing()
    test_edge_cases()

    # Print summary
    results.print_summary()

    # Return exit code
    return 0 if results.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
