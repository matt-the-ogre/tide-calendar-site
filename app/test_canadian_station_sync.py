"""
Unit tests for Canadian station normalization/filtering.

Covers the policy that any station with wlp-hilo predictions should be
importable (regardless of operating/type flags), and that the CHS
alternativeName is captured for name search.

Run from the app/ directory:
    ../venv/bin/python -m unittest test_canadian_station_sync
"""

import os
import tempfile
import unittest

from canadian_station_sync import normalize_station, _load_province_map


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


class TestProvinceMap(unittest.TestCase):
    """The authoritative provinceCode map (from CHS /metadata, baked offline) must
    take precedence over the longitude-based guess, which is wrong ~50% of the time."""

    def _digby(self):
        # Digby, NS — its longitude (~-65.76) makes construct_place_name guess "QC".
        return dict(PENDER, code="00325", officialName="Digby",
                    latitude=44.6, longitude=-65.76)

    def test_uses_authoritative_province_from_map(self):
        result = normalize_station(self._digby(), province_map={"00325": "NS"})
        self.assertEqual(result["province"], "NS")
        self.assertEqual(result["place_name"], "Digby, NS")

    def test_map_overrides_wrong_longitude_inference(self):
        no_map = normalize_station(self._digby(), province_map={})
        with_map = normalize_station(self._digby(), province_map={"00325": "NS"})
        self.assertEqual(with_map["place_name"], "Digby, NS")
        self.assertNotEqual(no_map["place_name"], with_map["place_name"])

    def test_falls_back_to_longitude_when_code_absent(self):
        raw = dict(PENDER, code="09999", officialName="Somewhere",
                   latitude=49.0, longitude=-124.0)  # BC longitude
        result = normalize_station(raw, province_map={})
        self.assertTrue(result["place_name"].endswith(", BC"))

    def test_province_in_name_used_when_not_in_map(self):
        raw = dict(PENDER, code="09998", officialName="Halifax, NS",
                   latitude=44.6, longitude=-63.5)
        result = normalize_station(raw, province_map={})
        self.assertEqual(result["province"], "NS")
        self.assertEqual(result["place_name"], "Halifax, NS")

    def test_non_canadian_province_code_is_humanized(self):
        # CHS carries Greenland stations with provinceCode "GRL_DEN"; show a readable
        # label rather than leaking the raw region code into the UI.
        raw = dict(PENDER, code="03575", officialName="Nuuk",
                   latitude=64.18, longitude=-51.75)
        result = normalize_station(raw, province_map={"03575": "GRL_DEN"})
        self.assertEqual(result["province"], "Greenland")
        self.assertEqual(result["place_name"], "Nuuk, Greenland")


class TestLoadProvinceMap(unittest.TestCase):
    def test_loads_code_province_pairs(self):
        fd, p = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(p, "w", encoding="utf-8") as f:
            f.write("code,province\n00325,NS\n07837,BC\n")
        try:
            self.assertEqual(_load_province_map(p), {"00325": "NS", "07837": "BC"})
        finally:
            os.remove(p)

    def test_missing_file_returns_empty(self):
        self.assertEqual(_load_province_map("/nonexistent/does-not-exist.csv"), {})


if __name__ == "__main__":
    unittest.main()
