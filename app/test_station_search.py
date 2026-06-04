"""
Unit tests for station name search and display formatting.

Covers:
- alternative_name schema column
- searching by the CHS common name (alternativeName) finds the station
- display_name combines "Common (Official), PROV"
- USA stations (no alias) are unaffected

Run from the app/ directory:
    ../venv/bin/python -m unittest test_station_search
"""

import os
import sys
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def fresh_db():
    """Create a throwaway DB and (re)import the database module against it."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DB_PATH"] = path
    if "database" in sys.modules:
        del sys.modules["database"]
    import database

    database.init_database()
    return database, path


class _DBTest(unittest.TestCase):
    def setUp(self):
        self.db, self.path = fresh_db()

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass
        os.environ.pop("DB_PATH", None)

    def _insert(self, **cols):
        keys = ", ".join(cols)
        placeholders = ", ".join("?" * len(cols))
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                f"INSERT INTO tide_station_ids ({keys}) VALUES ({placeholders})",
                tuple(cols.values()),
            )
            conn.commit()


class TestSchema(_DBTest):
    def test_alternative_name_column_exists(self):
        with sqlite3.connect(self.path) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(tide_station_ids)")]
        self.assertIn("alternative_name", cols)


class TestFormatDisplayName(_DBTest):
    def test_combines_common_then_official_then_province(self):
        self.assertEqual(
            self.db.format_display_name("ḵalpilin, BC", "Pender Harbour", "BC"),
            "Pender Harbour (ḵalpilin), BC",
        )

    def test_combines_when_province_column_empty_but_in_place_name(self):
        """Real case: normalize_station infers the province into place_name (from
        longitude) but leaves the province field empty when the official name has
        no province code. The suffix must still be split out of place_name so the
        province lands outside the parentheses."""
        self.assertEqual(
            self.db.format_display_name("ḵalpilin, BC", "Pender Harbour", ""),
            "Pender Harbour (ḵalpilin), BC",
        )
        self.assertEqual(
            self.db.format_display_name("ḵalpilin, BC", "Pender Harbour", None),
            "Pender Harbour (ḵalpilin), BC",
        )

    def test_no_alternative_returns_place_name(self):
        self.assertEqual(self.db.format_display_name("Seattle, WA", None, None), "Seattle, WA")
        self.assertEqual(self.db.format_display_name("Seattle, WA", "", "WA"), "Seattle, WA")

    def test_alternative_equal_to_official_not_duplicated(self):
        self.assertEqual(
            self.db.format_display_name("Halifax, NS", "Halifax", "NS"), "Halifax, NS"
        )


class TestSearchByAlternativeName(_DBTest):
    def setUp(self):
        super().setUp()
        self._insert(
            station_id="07837",
            place_name="ḵalpilin, BC",
            country="Canada",
            api_source="CHS",
            province="BC",
            alternative_name="Pender Harbour",
            lookup_count=1,
        )

    def test_search_by_common_name_finds_station(self):
        results = self.db.search_stations_by_country("pender", "Canada", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["station_id"], "07837")

    def test_search_result_has_combined_display_name(self):
        results = self.db.search_stations_by_country("pender", "Canada", limit=10)
        self.assertEqual(results[0]["display_name"], "Pender Harbour (ḵalpilin), BC")

    def test_search_by_official_name_still_finds_station(self):
        results = self.db.search_stations_by_country("ḵalpilin", "Canada", limit=10)
        self.assertEqual(len(results), 1)

    def test_search_all_countries_matches_alternative(self):
        results = self.db.search_stations_by_country("pender", None, limit=10)
        self.assertEqual(len(results), 1)


class TestUSAUnaffected(_DBTest):
    def setUp(self):
        super().setUp()
        self._insert(
            station_id="9449639",
            place_name="Point Roberts, WA",
            country="USA",
            api_source="NOAA",
            lookup_count=5,
        )

    def test_usa_search_still_works(self):
        results = self.db.search_stations_by_country("roberts", "USA", limit=10)
        self.assertEqual(len(results), 1)

    def test_usa_display_name_is_plain_place_name(self):
        results = self.db.search_stations_by_country("roberts", "USA", limit=10)
        self.assertEqual(results[0]["display_name"], "Point Roberts, WA")


if __name__ == "__main__":
    unittest.main()
