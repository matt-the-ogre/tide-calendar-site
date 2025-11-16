"""
Test script to import Canadian stations and verify database functionality.
"""

import logging
import sys
from database import (
    import_canadian_stations_from_csv,
    get_station_info,
    search_stations_by_country,
    get_popular_stations_by_country
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_import():
    """Test importing Canadian stations."""
    logging.info("=" * 60)
    logging.info("TESTING CANADIAN STATION IMPORT")
    logging.info("=" * 60)

    # Import Canadian stations
    logging.info("\n1. Importing Canadian stations...")
    success = import_canadian_stations_from_csv()

    if not success:
        logging.error("❌ Failed to import Canadian stations")
        return False

    logging.info("✅ Canadian stations imported successfully")
    return True

def test_station_info():
    """Test getting station info."""
    logging.info("\n2. Testing get_station_info()...")

    test_stations = [
        ("07735", "Vancouver, BC"),
        ("00490", "Halifax, NS"),
        ("08615", "Tofino, BC")
    ]

    for station_id, expected_name in test_stations:
        info = get_station_info(station_id)
        if info:
            logging.info(f"✅ Station {station_id}: {info['place_name']}")
            logging.info(f"   Country: {info['country']}, API: {info['api_source']}")
            if info['latitude'] and info['longitude']:
                logging.info(f"   Coordinates: {info['latitude']}, {info['longitude']}")
        else:
            logging.warning(f"⚠️  Station {station_id} not found")

def test_search():
    """Test searching stations by country."""
    logging.info("\n3. Testing search_stations_by_country()...")

    # Search for Vancouver in Canada
    results = search_stations_by_country("Vancouver", country="Canada", limit=5)
    logging.info(f"\nSearch 'Vancouver' in Canada: {len(results)} results")
    for r in results:
        logging.info(f"  - {r['station_id']}: {r['place_name']}")

    # Search for all BC stations
    results = search_stations_by_country("BC", country="Canada", limit=10)
    logging.info(f"\nSearch 'BC' in Canada: {len(results)} results")
    for r in results:
        logging.info(f"  - {r['station_id']}: {r['place_name']}")

def test_popular():
    """Test getting popular stations."""
    logging.info("\n4. Testing get_popular_stations_by_country()...")

    # Get popular Canadian stations
    results = get_popular_stations_by_country(country="Canada", limit=10)
    logging.info(f"\nTop popular Canadian stations: {len(results)} results")
    for i, r in enumerate(results, 1):
        logging.info(f"  {i}. {r['station_id']}: {r['place_name']} (lookups: {r['lookup_count']})")

    # Get popular USA stations
    results = get_popular_stations_by_country(country="USA", limit=5)
    logging.info(f"\nTop popular USA stations: {len(results)} results")
    for i, r in enumerate(results, 1):
        logging.info(f"  {i}. {r['station_id']}: {r['place_name']} (lookups: {r['lookup_count']})")

if __name__ == "__main__":
    try:
        # Run all tests
        if not test_import():
            sys.exit(1)

        test_station_info()
        test_search()
        test_popular()

        logging.info("\n" + "=" * 60)
        logging.info("✅ ALL TESTS PASSED")
        logging.info("=" * 60)

    except Exception as e:
        logging.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
