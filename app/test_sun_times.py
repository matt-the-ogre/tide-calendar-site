import os, sqlite3, tempfile, unittest, csv

import database


class TimezoneDBTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_station_info_returns_timezone(self):
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country, timezone) "
                         "VALUES ('9449639','Point Roberts, WA','USA','America/Vancouver')")
            conn.commit()
        info = database.get_station_info('9449639')
        self.assertEqual(info['timezone'], 'America/Vancouver')

    def test_backfill_timezones_from_csv(self):
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country) "
                         "VALUES ('07735','Vancouver, BC','Canada')")
            conn.commit()
        csv_path = self.tmp.name + '.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['station_id', 'timezone'])
            w.writeheader()
            w.writerow({'station_id': '07735', 'timezone': 'America/Vancouver'})
        n = database.backfill_timezones_from_csv([csv_path])
        self.assertEqual(n, 1)
        self.assertEqual(database.get_station_info('07735')['timezone'], 'America/Vancouver')


class SunTimesTest(unittest.TestCase):
    def test_point_roberts_june(self):
        import sun_times
        m = sun_times.sun_times_for_month(48.97, -123.07, 'America/Vancouver', 2026, 6)
        self.assertEqual(len(m), 30)
        rise, sset = m[15]
        self.assertRegex(rise, r'^\d{2}:\d{2}$')
        self.assertRegex(sset, r'^\d{2}:\d{2}$')
        self.assertIn(int(rise[:2]), range(4, 7))
        self.assertIn(int(sset[:2]), range(20, 23))

    def test_polar_day_returns_note(self):
        import sun_times
        m = sun_times.sun_times_for_month(78.0, 15.0, 'Arctic/Longyearbyen', 2026, 6)
        self.assertEqual(m[15], '24h daylight')

    def test_missing_tz_returns_empty(self):
        import sun_times
        self.assertEqual(sun_times.sun_times_for_month(48.0, -123.0, None, 2026, 6), {})

    def test_format_sun_line(self):
        import sun_times
        self.assertEqual(sun_times.format_sun_line(('05:14', '21:09')), 'Rise 05:14  Set 21:09')
        self.assertEqual(sun_times.format_sun_line('24h daylight'), 'Sun: 24h daylight')


class LocalizeCsvTest(unittest.TestCase):
    HEADER = 'Date Time,Prediction,Type'

    def test_chs_converts_and_crosses_midnight(self):
        import sun_times
        csv_in = self.HEADER + '\n2026-06-15 05:23,4.8,H'
        out = sun_times.localize_and_filter_csv(csv_in, 'CHS', 'America/Vancouver', 2026, 6)
        self.assertIn('2026-06-14 22:23,4.8,H', out)

    def test_chs_recovers_last_day_evening_and_drops_prev_month(self):
        import sun_times
        csv_in = (self.HEADER
                  + '\n2026-06-01 02:00,1.0,L'
                  + '\n2026-07-01 04:00,2.0,H')
        out = sun_times.localize_and_filter_csv(csv_in, 'CHS', 'America/Vancouver', 2026, 6)
        self.assertNotIn('05-31', out)
        self.assertIn('2026-06-30 21:00,2.0,H', out)

    def test_noaa_passthrough(self):
        import sun_times
        csv_in = self.HEADER + '\n2026-06-15 05:23,4.8,H'
        self.assertEqual(sun_times.localize_and_filter_csv(csv_in, 'NOAA', None, 2026, 6), csv_in)


class CivilWindowTest(unittest.TestCase):
    def test_normal_station_returns_dawn_dusk(self):
        import sun_times
        from datetime import date
        w = sun_times.civil_daylight_window(48.97, -123.07, 'America/Los_Angeles', date(2026, 6, 15))
        self.assertIsInstance(w, tuple)
        dawn, dusk = w
        self.assertLess(dawn, dusk)
        self.assertIn(dawn.hour, range(3, 6))
        self.assertIn(dusk.hour, range(21, 23))

    def test_polar_day_all(self):
        import sun_times
        from datetime import date
        self.assertEqual(
            sun_times.civil_daylight_window(78.0, 15.0, 'Arctic/Longyearbyen', date(2026, 6, 15)),
            'all')

    def test_polar_night_none(self):
        import sun_times
        from datetime import date
        self.assertIsNone(
            sun_times.civil_daylight_window(78.0, 15.0, 'Arctic/Longyearbyen', date(2026, 12, 15)))

    def test_missing_tz_none(self):
        import sun_times
        from datetime import date
        self.assertIsNone(sun_times.civil_daylight_window(48.0, -123.0, None, date(2026, 6, 15)))


if __name__ == '__main__':
    unittest.main()
