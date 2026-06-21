import os, tempfile, unittest
import get_tides


class PcalSunLineTest(unittest.TestCase):
    def test_writes_sun_line_before_tides(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 05:23,4.8,H\n2026-06-15 11:40,0.1,L"
        sun = {15: ('05:14', '21:09')}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='Test',
                                                sun_times=sun)
            with open(path) as f:
                text = f.read()
        self.assertIn('6/15  Rise 05:14  Set 21:09', text)
        self.assertLess(text.index('Rise 05:14'), text.index('05:23 High'))

    def test_no_sun_times_is_backward_compatible(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 05:23,4.8,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='Test')
            with open(path) as f:
                text = f.read()
        self.assertNotIn('Rise', text)
        self.assertIn('05:23 High', text)


if __name__ == '__main__':
    unittest.main()
