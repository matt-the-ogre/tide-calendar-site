import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from fetch_noaa_coordinates import merge_coordinates

class MergeCoordinatesTest(unittest.TestCase):
    def test_adds_lat_long_for_matched_station(self):
        rows = [{'station_id': '9449639', 'place_name': 'Point Roberts, WA'}]
        coords = {'9449639': {'lat': 48.97, 'lng': -123.07}}
        out = merge_coordinates(rows, coords)
        self.assertEqual(out[0]['latitude'], 48.97)
        self.assertEqual(out[0]['longitude'], -123.07)
        self.assertEqual(out[0]['station_id'], '9449639')
        self.assertEqual(out[0]['place_name'], 'Point Roberts, WA')

    def test_missing_station_gets_blank_coords(self):
        rows = [{'station_id': '0000000', 'place_name': 'Nowhere'}]
        out = merge_coordinates(rows, {})
        self.assertEqual(out[0]['latitude'], '')
        self.assertEqual(out[0]['longitude'], '')

if __name__ == '__main__':
    unittest.main()
