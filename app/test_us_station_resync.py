"""
Regression test for warm-DB self-healing of US station metadata.

Background: production runs on a persistent-volume SQLite DB that survives
container restarts. If a US station row's metadata drifts away from the
canonical CSV (most damagingly `api_source`, which selects the API adapter),
the station routes to the wrong adapter and every calendar generation fails
with "no_predictions" — even though the upstream API has the data. Dev never
shows this because its DB is rebuilt from the CSV on every cold start.

`import_stations_from_csv()` is the only path that re-applies the CSV's
authoritative metadata to US rows, so it must run (not short-circuit) on a
warm DB. These tests lock in that self-healing behavior.

Run from the app/ directory:
    python -m unittest test_us_station_resync
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

POINT_ROBERTS = "9449639"  # NOAA station, US demo/default station


def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DB_PATH"] = path
    if "database" in sys.modules:
        del sys.modules["database"]
    import database

    database.DB_PATH = path  # tests reassign this dynamically
    database.init_database()
    return database, path


class TestWarmDbSelfHeal(unittest.TestCase):
    def setUp(self):
        self.db, self.path = fresh_db()
        self.assertTrue(self.db.import_stations_from_csv(), "cold CSV import failed")

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass
        os.environ.pop("DB_PATH", None)

    def _api_source(self, station_id):
        info = self.db.get_station_info(station_id)
        return info["api_source"] if info else None

    def test_cold_import_marks_point_roberts_as_noaa(self):
        self.assertEqual(self._api_source(POINT_ROBERTS), "NOAA")

    def test_drifted_api_source_self_heals_on_reimport(self):
        # Simulate a warm-DB row that has drifted (the production failure mode).
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "UPDATE tide_station_ids SET api_source = 'CHS', country = 'Canada' "
                "WHERE station_id = ?",
                (POINT_ROBERTS,),
            )
            conn.commit()
        self.assertEqual(self._api_source(POINT_ROBERTS), "CHS")  # drift present

        # A warm-DB startup re-import must repair it (previously short-circuited).
        self.assertTrue(self.db.import_stations_from_csv())

        info = self.db.get_station_info(POINT_ROBERTS)
        self.assertEqual(info["api_source"], "NOAA")
        self.assertEqual(info["country"], "USA")

    def test_reimport_preserves_lookup_count(self):
        # Self-healing must not clobber usage counters on existing rows.
        self.db.log_station_lookup(POINT_ROBERTS)
        self.db.log_station_lookup(POINT_ROBERTS)
        with sqlite3.connect(self.path) as conn:
            before = conn.execute(
                "SELECT lookup_count FROM tide_station_ids WHERE station_id = ?",
                (POINT_ROBERTS,),
            ).fetchone()[0]

        self.assertTrue(self.db.import_stations_from_csv())

        with sqlite3.connect(self.path) as conn:
            after = conn.execute(
                "SELECT lookup_count FROM tide_station_ids WHERE station_id = ?",
                (POINT_ROBERTS,),
            ).fetchone()[0]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
