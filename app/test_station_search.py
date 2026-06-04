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

    def test_core_name_containing_comma_splits_on_province_only(self):
        """Some official names themselves contain a comma; only the trailing
        ', PROV' is the province suffix. Real example: station 07786."""
        expected = "Sandy Cove (West Vancouver Laboratories, Ettershank Cove), BC"
        # Explicit province column
        self.assertEqual(
            self.db.format_display_name(
                "West Vancouver Laboratories, Ettershank Cove, BC", "Sandy Cove", "BC"
            ),
            expected,
        )
        # Province inferred (column empty) -> rpartition fallback splits last comma
        self.assertEqual(
            self.db.format_display_name(
                "West Vancouver Laboratories, Ettershank Cove, BC", "Sandy Cove", ""
            ),
            expected,
        )

    def test_messy_alternative_uses_first_segment_only(self):
        # CHS alternativeName "Dumb Bell Bay, DUMB BELL BAY" -> lead with the clean
        # first name, not the uppercase echo.
        self.assertEqual(
            self.db.format_display_name("Alert, NT", "Dumb Bell Bay, DUMB BELL BAY", "NT"),
            "Dumb Bell Bay (Alert), NT",
        )

    def test_duplicated_multi_segment_alternative_uses_first_segment(self):
        self.assertEqual(
            self.db.format_display_name(
                "Henslung Cove, BC", "Parry Passage, B.C., Parry Passage, B.C.", "BC"
            ),
            "Parry Passage (Henslung Cove), BC",
        )

    def test_uppercase_alternative_matching_official_not_duplicated(self):
        # First segment "BAY OF WOE" equals the official (case-insensitively) -> no parens.
        self.assertEqual(
            self.db.format_display_name("Bay of Woe, NU", "BAY OF WOE, JONES SD.", "NU"),
            "Bay of Woe, NU",
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


class TestGetStationIdByName(_DBTest):
    """The form-submit fallback (when no station_id is selected) must resolve a
    typed common name, not just the official place_name."""

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

    def test_resolves_by_common_name(self):
        self.assertEqual(self.db.get_station_id_by_place_name("Pender Harbour"), "07837")

    def test_resolves_by_common_name_case_insensitive(self):
        self.assertEqual(self.db.get_station_id_by_place_name("pender harbour"), "07837")

    def test_resolves_by_official_place_name_still(self):
        self.assertEqual(self.db.get_station_id_by_place_name("ḵalpilin, BC"), "07837")

    def test_unknown_name_returns_none(self):
        self.assertIsNone(self.db.get_station_id_by_place_name("Nowhere, ZZ"))


class TestPopularStationsDisplayName(_DBTest):
    def setUp(self):
        super().setUp()
        self._insert(
            station_id="07837",
            place_name="ḵalpilin, BC",
            country="Canada",
            api_source="CHS",
            province="BC",
            alternative_name="Pender Harbour",
            lookup_count=3,
        )

    def test_popular_includes_combined_display_name(self):
        results = self.db.get_popular_stations_by_country("Canada", limit=10)
        match = [r for r in results if r["station_id"] == "07837"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["display_name"], "Pender Harbour (ḵalpilin), BC")


class TestFoldForSearch(_DBTest):
    def test_strips_diacritics_and_lowercases(self):
        self.assertEqual(self.db.fold_for_search("ḵalpilin"), "kalpilin")
        self.assertEqual(self.db.fold_for_search("Bécancour"), "becancour")
        self.assertEqual(self.db.fold_for_search("Île-aux-Coudres"), "ile-aux-coudres")

    def test_ascii_unchanged_except_case(self):
        self.assertEqual(self.db.fold_for_search("Pender Harbour"), "pender harbour")

    def test_empty_and_none(self):
        self.assertEqual(self.db.fold_for_search(""), "")
        self.assertEqual(self.db.fold_for_search(None), "")


class TestDiacriticInsensitiveSearch(_DBTest):
    def setUp(self):
        super().setUp()
        self._insert(
            station_id="07837", place_name="ḵalpilin, BC", country="Canada",
            api_source="CHS", province="BC", alternative_name="Pender Harbour",
            lookup_count=1,
        )
        self._insert(
            station_id="03353", place_name="Bécancour, QC", country="Canada",
            api_source="CHS", province="QC", lookup_count=1,
        )

    def test_ascii_query_matches_diacritic_official_name(self):
        results = self.db.search_stations_by_country("kalpilin", "Canada", limit=10)
        self.assertEqual([r["station_id"] for r in results], ["07837"])

    def test_ascii_query_matches_accented_name(self):
        results = self.db.search_stations_by_country("becancour", "Canada", limit=10)
        self.assertEqual([r["station_id"] for r in results], ["03353"])

    def test_diacritic_query_still_matches(self):
        results = self.db.search_stations_by_country("ḵalpilin", "Canada", limit=10)
        self.assertEqual([r["station_id"] for r in results], ["07837"])

    def test_common_name_still_matches(self):
        results = self.db.search_stations_by_country("pender", "Canada", limit=10)
        self.assertEqual([r["station_id"] for r in results], ["07837"])

    def test_all_countries_diacritic_fold(self):
        results = self.db.search_stations_by_country("becancour", None, limit=10)
        self.assertEqual([r["station_id"] for r in results], ["03353"])

    def test_ascii_query_matches_diacritic_in_alternative_name(self):
        # Diacritic lives in the *alternative* name and the place_name cannot match
        # the query, so a hit proves the alternative_name column is folded too.
        self._insert(
            station_id="03250", place_name="Saint-Joseph, QC", country="Canada",
            api_source="CHS", province="QC", alternative_name="Rivière-du-Loup",
            lookup_count=1,
        )
        results = self.db.search_stations_by_country("riviere", "Canada", limit=10)
        self.assertIn("03250", [r["station_id"] for r in results])


class TestMessyAlternativeNameSearchAndDisplay(_DBTest):
    """A multi-name alternativeName (e.g. "Sugluk, Salluit, Saglouc") stays fully
    searchable by any segment, while the display leads with just the first."""

    def setUp(self):
        super().setUp()
        self._insert(
            station_id="04470", place_name="Salluit, QC", country="Canada",
            api_source="CHS", province="QC",
            alternative_name="Sugluk, Salluit, Saglouc", lookup_count=1,
        )

    def test_non_first_alt_segment_still_searchable(self):
        results = self.db.search_stations_by_country("saglouc", "Canada", limit=10)
        self.assertEqual([r["station_id"] for r in results], ["04470"])

    def test_display_leads_with_first_alt_segment(self):
        results = self.db.search_stations_by_country("sugluk", "Canada", limit=10)
        self.assertEqual(results[0]["display_name"], "Sugluk (Salluit), QC")


if __name__ == "__main__":
    unittest.main()
