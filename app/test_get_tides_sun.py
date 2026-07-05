import os, tempfile, unittest
import get_tides


class PcalSunLineTest(unittest.TestCase):
    def test_writes_sun_line_before_tides(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 05:23,4.8,H\n2026-06-15 11:40,0.1,L"
        sun = {15: ('05:14', '21:09')}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='Test',
                                                sun_times=sun, unit='metric')
            with open(path) as f:
                text = f.read()
        self.assertIn('6/15  Rise 05:14  Set 21:09', text)
        self.assertLess(text.index('Rise 05:14'), text.index('05:23 High'))

    def test_no_sun_times_is_backward_compatible(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 05:23,4.8,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='Test',
                                                unit='metric')
            with open(path) as f:
                text = f.read()
        self.assertNotIn('Rise', text)
        self.assertIn('05:23 High', text)


class PcalExtremeTablesTest(unittest.TestCase):
    def test_writes_high_and_low_tables_metric(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        highs = [{'day': 4, 'time': '09:00', 'height': 4.8}]
        lows = [{'day': 1, 'time': '13:00', 'height': 0.2}]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                high_tides=highs, low_tides=lows,
                                                unit='metric')
            with open(path) as f:
                text = f.read()
        # month derived from the data row (June) -> 'J' prefix on the day
        self.assertIn('note/2 all Top 5 High Tides (daylight)', text)
        self.assertIn('note/2 all J04  09:00  4.8 m', text)
        self.assertIn('note/3 all Top 5 Low Tides (daylight)', text)
        self.assertIn('note/3 all J01  13:00  0.2 m', text)

    def test_writes_high_and_low_tables_imperial(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        highs = [{'day': 4, 'time': '09:00', 'height': 4.8}]
        lows = [{'day': 1, 'time': '13:00', 'height': 0.2}]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                high_tides=highs, low_tides=lows,
                                                unit='imperial')
            with open(path) as f:
                text = f.read()
        # 4.8 m * 3.28084 = 15.7 ft; 0.2 m * 3.28084 = 0.7 ft
        self.assertIn('note/2 all J04  09:00  15.7 ft', text)
        self.assertIn('note/3 all J01  13:00  0.7 ft', text)

    def test_empty_tables_show_fallback(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                high_tides=[], low_tides=[])
            with open(path) as f:
                text = f.read()
        self.assertIn('note/2 all No daylight high tides', text)
        self.assertIn('note/3 all No daylight low tides', text)

    def test_none_tables_omitted(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T')
            with open(path) as f:
                text = f.read()
        self.assertNotIn('note/2', text)
        self.assertNotIn('note/3', text)


class PcalLowTideOrderingTest(unittest.TestCase):
    """Regression coverage for the removed low-tide "callout" behaviour.

    pcal renders "*"-flagged entries before regular ones within a day's cell,
    which is how the old code (starring the tide line itself) pulled a
    below-threshold low tide ahead of earlier same-day events. These tests
    verify the pcal input file's contract: tide lines are written in
    chronological (CSV) order and are never starred; only a separate,
    text-less "mm/dd*" marker line is starred, to colour the day number
    without affecting pcal's within-day ordering. See get_tides.py
    LOW_TIDE_THRESHOLD."""

    def test_low_tide_stays_in_chronological_position(self):
        csv_data = ("Date Time,Prediction,Type\n"
                     "2026-06-15 09:00,3.0,H\n"
                     "2026-06-15 21:00,0.1,L")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                unit='metric')
            with open(path) as f:
                text = f.read()
        self.assertLess(text.index('09:00 High'), text.index('21:00 Low'))

    def test_low_tide_day_gets_text_less_colour_marker(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 21:00,0.1,L"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                unit='metric')
            with open(path) as f:
                text = f.read()
        self.assertIn('6/15*\n', text)
        self.assertNotIn('6/15*  21:00', text)
        self.assertIn('6/15  21:00 Low', text)

    def test_day_without_low_tide_has_no_marker(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 09:00,3.0,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                unit='metric')
            with open(path) as f:
                text = f.read()
        self.assertNotIn('*', text)


if __name__ == '__main__':
    unittest.main()
