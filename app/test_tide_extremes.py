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
    "2026-06-02 23:30,0.1,L\n"   # night low — excluded by the daylight window
    "2026-06-03 08:00,4.4,H\n"
    "2026-06-03 14:00,0.5,L\n"
    "2026-06-04 09:00,4.8,H\n"
)


class TopExtremeTidesTest(unittest.TestCase):
    def test_highs_selected_by_elevation_displayed_by_date(self):
        # n=2: pick the 2 HIGHEST (4.8, 4.6 — drops 4.4), but DISPLAY by date.
        highs, _ = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=2, window_fn=_day_window)
        self.assertEqual([(h['day'], h['height']) for h in highs], [(1, 4.6), (4, 4.8)])

    def test_lows_displayed_by_date_and_excludes_night(self):
        _, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5, window_fn=_day_window)
        # 0.1 at 23:30 excluded (night); remaining daylight lows in DATE order
        self.assertEqual([(l['day'], l['height']) for l in lows], [(1, 0.2), (3, 0.5)])

    def test_n_limits_count(self):
        highs, _ = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=2, window_fn=_day_window)
        self.assertEqual(len(highs), 2)

    def test_all_window_keeps_night(self):
        _, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5,
                                                  window_fn=lambda *a: 'all')
        self.assertIn(0.1, [l['height'] for l in lows])  # night low now eligible

    def test_none_window_excludes_all(self):
        highs, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5,
                                                      window_fn=lambda *a: None)
        self.assertEqual((highs, lows), ([], []))

    def test_lows_select_most_negative_then_date_order(self):
        # 4 lows; n=3 must drop the +0.5 (least extreme) and keep the 3 most
        # negative, displayed in DATE order.
        csv = ("Date Time,Prediction,Type\n"
               "2026-06-01 10:00,-0.2,L\n"
               "2026-06-02 11:00,-1.8,L\n"
               "2026-06-03 12:00,-1.5,L\n"
               "2026-06-04 12:00,0.5,L\n")
        _, lows = tide_extremes.top_extreme_tides(csv, 1, 1, 'X', 2026, 6, n=3, window_fn=_day_window)
        self.assertEqual([(l['day'], l['height']) for l in lows],
                         [(1, -0.2), (2, -1.8), (3, -1.5)])

    def test_format_rows_with_month_letter(self):
        rows = tide_extremes.format_extreme_rows([{'day': 6, 'time': '13:30', 'height': 4.6}], 6)
        self.assertEqual(rows, ['J06  13:30  4.6 m'])

    def test_format_negative_height(self):
        rows = tide_extremes.format_extreme_rows([{'day': 13, 'time': '11:08', 'height': -1.2}], 6)
        self.assertEqual(rows, ['J13  11:08  -1.2 m'])

    def test_format_no_month_omits_letter(self):
        rows = tide_extremes.format_extreme_rows([{'day': 6, 'time': '13:30', 'height': 4.6}])
        self.assertEqual(rows, ['06  13:30  4.6 m'])


if __name__ == '__main__':
    unittest.main()
