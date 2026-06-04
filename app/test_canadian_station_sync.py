"""
Unit tests for Canadian station normalization/filtering.

Covers the policy that any station with wlp-hilo predictions should be
importable (regardless of operating/type flags), and that the CHS
alternativeName is captured for name search.

Run from the app/ directory:
    ../venv/bin/python -m unittest test_canadian_station_sync
"""

import unittest

from canadian_station_sync import normalize_station


# Real CHS record shape for station 07837 (ḵalpilin / Pender Harbour):
# operating=False, type=TEMPORARY, but it DOES publish wlp-hilo predictions.
PENDER = {
    "code": "07837",
    "officialName": "ḵalpilin",
    "alternativeName": "Pender Harbour",
    "latitude": 49.633,
    "longitude": -124.032,
    "operating": False,
    "type": "TEMPORARY",
    "timeSeries": [{"code": "wlp"}, {"code": "wlp-hilo"}],
}


class TestNormalizeStation(unittest.TestCase):
    def test_includes_non_operating_temporary_station_with_hilo(self):
        """A non-operating TEMPORARY station with wlp-hilo must be included."""
        result = normalize_station(PENDER)
        self.assertIsNotNone(result)
        self.assertEqual(result["code"], "07837")

    def test_captures_alternative_name(self):
        """The CHS alternativeName (common name) must be captured."""
        result = normalize_station(PENDER)
        self.assertEqual(result["alternativeName"], "Pender Harbour")

    def test_missing_alternative_name_is_falsy(self):
        """Stations without an alternativeName should not error."""
        raw = dict(PENDER)
        raw.pop("alternativeName")
        result = normalize_station(raw)
        self.assertIsNotNone(result)
        self.assertFalse(result["alternativeName"])

    def test_excludes_station_without_hilo(self):
        """A station lacking wlp-hilo cannot produce a tide calendar -> excluded."""
        raw = dict(PENDER, timeSeries=[{"code": "wlp"}])
        self.assertIsNone(normalize_station(raw))

    def test_excludes_station_missing_code_or_name(self):
        self.assertIsNone(normalize_station(dict(PENDER, code=None)))
        self.assertIsNone(normalize_station(dict(PENDER, officialName="")))

    def test_still_includes_operating_permanent_station(self):
        """Regression: stations that passed the old filter still pass."""
        raw = dict(
            PENDER,
            code="07795",
            officialName="Point Atkinson",
            alternativeName="Caulfeild Cove",
            operating=True,
            type="PERMANENT",
        )
        result = normalize_station(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["code"], "07795")

    def test_place_name_has_province_and_excludes_alternative(self):
        """place_name stays the official name + province; the common name is
        kept separate (so filenames/notes don't get the parenthetical)."""
        result = normalize_station(PENDER)
        self.assertTrue(result["place_name"].endswith(", BC"))
        self.assertNotIn("Pender", result["place_name"])


if __name__ == "__main__":
    unittest.main()
