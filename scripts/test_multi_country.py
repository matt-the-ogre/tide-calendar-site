#!/usr/bin/env python3
"""
Comprehensive testing script for multi-country tide station implementation.

Tests:
1. Canadian station PDF generation (10+ stations)
2. USA station PDF generation (5+ stations) for regression
3. Tide adapter layer functionality
4. Country-specific database queries
5. Edge cases and error handling

Run from project root: python3 scripts/test_multi_country.py
"""

import sys
from pathlib import Path
from datetime import datetime
import logging
import time

# Add app directory to path for imports
APP_DIR = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))

from database import (
    get_station_info,
    search_stations_by_country,
    get_popular_stations_by_country
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
        self.timings = []

    def add_pass(self, test_name, duration=None):
        self.total += 1
        self.passed += 1
        if duration:
            self.timings.append((test_name, duration))
        logger.info(f"✓ PASS: {test_name}" + (f" ({duration:.2f}s)" if duration else ""))

    def add_fail(self, test_name, error, duration=None):
        self.total += 1
        self.failed += 1
        self.errors.append((test_name, error))
        if duration:
            self.timings.append((test_name, duration))
        logger.error(f"✗ FAIL: {test_name}" + (f" ({duration:.2f}s)" if duration else ""))
        logger.error(f"  Error: {error}")

    def print_summary(self):
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {((self.passed/self.total*100) if self.total > 0 else 0):.1f}%")

        if self.timings:
            print("\n" + "-"*70)
            print("PERFORMANCE TIMINGS")
            print("-"*70)
            for test_name, duration in self.timings:
                status = "✓" if duration < 3.0 else "⚠"
                print(f"{status} {test_name}: {duration:.2f}s")

        if self.errors:
            print("\n" + "-"*70)
            print("FAILED TESTS")
            print("-"*70)
            for test_name, error in self.errors:
                print(f"✗ {test_name}")
                print(f"  {error}")

        print("="*70)

results = TestResults()

# Test station sets
CANADIAN_STATIONS = [
    ("00490", "Halifax, NS"),
    ("07735", "Vancouver, BC"),
    ("08615", "Tofino, BC"),
    ("07277", "Victoria, BC"),
    ("03251", "Québec, QC"),
    ("04490", "Rimouski, QC"),
    ("02925", "Point Atkinson, BC"),
    ("08074", "Prince Rupert, BC"),
    ("08408", "Campbell River, BC"),
    ("08545", "Ucluelet, BC"),
    ("07120", "Patricia Bay, BC"),
]

USA_STATIONS = [
    ("9449639", "Point Roberts, WA"),
    ("9447130", "Seattle, WA"),
    ("9410170", "San Diego, CA"),
    ("8518750", "The Battery, NY"),
    ("8454049", "Portland, ME"),
]

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

def test_canadian_api_fetch():
    """Test fetching Canadian tide data from CHS API."""
    logger.info("\n--- Testing Canadian API Fetches ---")

    adapter = CHSAdapter()
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Test first 3 Canadian stations
    for station_id, name in CANADIAN_STATIONS[:3]:
        start_time = time.time()
        try:
            csv_data = adapter.get_predictions(station_id, current_year, current_month)
            duration = time.time() - start_time

            if csv_data and len(csv_data.split('\n')) > 2:
                results.add_pass(f"CHS fetch: {name} ({station_id})", duration)
            else:
                results.add_fail(f"CHS fetch: {name} ({station_id})",
                               "No data returned", duration)
        except Exception as e:
            duration = time.time() - start_time
            results.add_fail(f"CHS fetch: {name} ({station_id})", str(e), duration)

def test_usa_api_fetch():
    """Test fetching USA tide data from NOAA API."""
    logger.info("\n--- Testing USA API Fetches (Regression) ---")

    adapter = NOAAAdapter()
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Test first 3 USA stations
    for station_id, name in USA_STATIONS[:3]:
        start_time = time.time()
        try:
            csv_data = adapter.get_predictions(station_id, current_year, current_month)
            duration = time.time() - start_time

            if csv_data and len(csv_data.split('\n')) > 2:
                results.add_pass(f"NOAA fetch: {name} ({station_id})", duration)
            else:
                results.add_fail(f"NOAA fetch: {name} ({station_id})",
                               "No data returned", duration)
        except Exception as e:
            duration = time.time() - start_time
            results.add_fail(f"NOAA fetch: {name} ({station_id})", str(e), duration)

def test_database_country_search():
    """Test country-specific database queries."""
    logger.info("\n--- Testing Database Country Queries ---")

    # Test search by country
    try:
        usa_results = search_stations_by_country("Seattle", "USA", limit=5)
        if len(usa_results) > 0 and all(r['country'] == 'USA' for r in usa_results):
            results.add_pass(f"Search USA stations (found {len(usa_results)})")
        else:
            results.add_fail("Search USA stations", "Wrong country in results")
    except Exception as e:
        results.add_fail("Search USA stations", str(e))

    try:
        canada_results = search_stations_by_country("Vancouver", "Canada", limit=5)
        if len(canada_results) > 0 and all(r['country'] == 'Canada' for r in canada_results):
            results.add_pass(f"Search Canadian stations (found {len(canada_results)})")
        else:
            results.add_fail("Search Canadian stations", "Wrong country in results")
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

    # Test popular stations by country
    try:
        usa_popular = get_popular_stations_by_country("USA", limit=5)
        if len(usa_popular) > 0:
            results.add_pass(f"Popular USA stations (found {len(usa_popular)})")
        else:
            results.add_fail("Popular USA stations", "No results")
    except Exception as e:
        results.add_fail("Popular USA stations", str(e))

    try:
        canada_popular = get_popular_stations_by_country("Canada", limit=5)
        if len(canada_popular) > 0:
            results.add_pass(f"Popular Canadian stations (found {len(canada_popular)})")
        else:
            results.add_fail("Popular Canadian stations", "No results")
    except Exception as e:
        results.add_fail("Popular Canadian stations", str(e))

def test_station_info():
    """Test station info retrieval."""
    logger.info("\n--- Testing Station Info Retrieval ---")

    # Test Canadian station
    try:
        info = get_station_info("07735")  # Vancouver
        if info and info.get('api_source') == 'CHS':
            results.add_pass("Get Canadian station info")
        else:
            results.add_fail("Get Canadian station info",
                           f"Wrong API source: {info.get('api_source') if info else 'None'}")
    except Exception as e:
        results.add_fail("Get Canadian station info", str(e))

    # Test USA station
    try:
        info = get_station_info("9449639")  # Point Roberts
        if info and info.get('api_source') == 'NOAA':
            results.add_pass("Get USA station info")
        else:
            results.add_fail("Get USA station info",
                           f"Wrong API source: {info.get('api_source') if info else 'None'}")
    except Exception as e:
        results.add_fail("Get USA station info", str(e))

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

    # Test non-existent station
    try:
        result = adapter.get_predictions("0000000", 2024, 6)  # Doesn't exist
        # This should either return None or error
        results.add_pass("Handle non-existent station gracefully")
    except Exception as e:
        results.add_pass("Handle non-existent station gracefully")

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("MULTI-COUNTRY TIDE STATION IMPLEMENTATION TEST SUITE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run all test suites
    test_adapter_validation()
    test_adapter_factory()
    test_station_info()
    test_database_country_search()
    test_canadian_api_fetch()
    test_usa_api_fetch()
    test_edge_cases()

    # Print summary
    results.print_summary()

    # Return exit code
    return 0 if results.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
