import unittest
import tide_extremes


def _day_window(lat, lng, tz, d):
    from datetime import datetime
    return (datetime(d.year, d.month, d.day, 6, 0),
            datetime(d.year, d.month, d.day, 20, 0))


CSV = (
    "Date Time,Prediction,Type\n"
    "2026-06-01 07:00,4.6,H\n"
    "2026-06-01 13:00,0.2,L\n"
    "2026-06-02 23:30,0.1,L\n"
    "2026-06-03 08:00,4.4,H\n"
    "2026-06-03 14:00,0.5,L\n"
    "2026-06-04 09:00,4.8,H\n"
)


class TopExtremeTidesTest(unittest.TestCase):
    def test_highs_highest_first(self):
        highs, _ = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5, window_fn=_day_window)
        self.assertEqual([h['height'] for h in highs], [4.8, 4.6, 4.4])

    def test_lows_lowest_first_and_excludes_night(self):
        _, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5, window_fn=_day_window)
        self.assertEqual([l['height'] for l in lows], [0.2, 0.5])
        self.assertEqual(lows[0], {'day': 1, 'time': '13:00', 'height': 0.2})

    def test_n_limits_count(self):
        highs, _ = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=2, window_fn=_day_window)
        self.assertEqual(len(highs), 2)

    def test_all_window_keeps_night(self):
        _, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5,
                                                  window_fn=lambda *a: 'all')
        self.assertEqual(lows[0]['height'], 0.1)

    def test_none_window_excludes_all(self):
        highs, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5,
                                                      window_fn=lambda *a: None)
        self.assertEqual((highs, lows), ([], []))

    def test_format_rows(self):
        rows = tide_extremes.format_extreme_rows([{'day': 6, 'time': '13:30', 'height': 4.6}])
        self.assertEqual(rows, [' 6  13:30  4.6 m'])


if __name__ == '__main__':
    unittest.main()
