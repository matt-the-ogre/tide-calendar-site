import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from fetch_station_timezones import add_timezone_column

class AddTimezoneColumnTest(unittest.TestCase):
    def test_adds_timezone_from_lookup(self):
        rows = [{'station_id': '9449639', 'place_name': 'Point Roberts, WA',
                 'latitude': '48.97', 'longitude': '-123.07'}]
        out = add_timezone_column(rows, lambda lat, lng: 'America/Vancouver')
        self.assertEqual(out[0]['timezone'], 'America/Vancouver')
        self.assertEqual(out[0]['station_id'], '9449639')

    def test_blank_when_lookup_returns_none(self):
        rows = [{'station_id': 'x', 'place_name': 'Ocean', 'latitude': '', 'longitude': ''}]
        out = add_timezone_column(rows, lambda lat, lng: None)
        self.assertEqual(out[0]['timezone'], '')

if __name__ == '__main__':
    unittest.main()
