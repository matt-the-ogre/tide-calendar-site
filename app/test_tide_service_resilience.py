"""
Tests for upstream-outage handling and the raw tide-data cache.

Two behaviours, both motivated by a real NOAA `datagetter` outage (all requests
returning 504) that surfaced on production as a generic "no predictions" error:

1. Adapters distinguish an *upstream outage* (gateway 5xx / timeout / network,
   after retries) from a station genuinely having *no data*. The former raises
   TideServiceUnavailableError; the latter returns None.

2. get_tide_data caches the (unit-independent) standardized CSV per
   (station, year, month), so a cache hit never touches the API — making a
   cache-missed PDF resilient to an outage once the data has been fetched once.

Run from the app/ directory:
    python -m unittest test_tide_service_resilience
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

import get_tides
from tide_adapters import NOAAAdapter, CHSAdapter, TideServiceUnavailableError

VALID_CSV = "Date Time,Prediction,Type\n2026-08-01 02:42,0.605,H\n2026-08-01 09:10,2.1,L"


class TestAdapterOutageSignal(unittest.TestCase):
    @patch('time.sleep', lambda *a, **k: None)  # don't actually back off
    @patch('tide_adapters.requests.get')
    def test_noaa_persistent_504_raises_unavailable(self, mock_get):
        resp = Mock(status_code=504, text='<html>504 Gateway Time-out</html>')
        mock_get.return_value = resp
        with self.assertRaises(TideServiceUnavailableError):
            NOAAAdapter().get_predictions('9449639', 2026, 8)
        self.assertEqual(mock_get.call_count, 3)  # all retries exhausted

    @patch('time.sleep', lambda *a, **k: None)
    @patch('tide_adapters.requests.get')
    def test_noaa_timeout_raises_unavailable(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("timed out")
        with self.assertRaises(TideServiceUnavailableError):
            NOAAAdapter().get_predictions('9449639', 2026, 8)

    @patch('tide_adapters.requests.get')
    def test_noaa_404_is_not_an_outage(self, mock_get):
        # A definitive non-gateway HTTP error means "no usable data", not an
        # outage — must return None, never raise.
        mock_get.return_value = Mock(status_code=404, text='not found')
        self.assertIsNone(NOAAAdapter().get_predictions('9449639', 2026, 8))

    @patch('time.sleep', lambda *a, **k: None)
    @patch('tide_adapters.requests.get')
    def test_chs_all_endpoints_504_raises_unavailable(self, mock_get):
        # UUID station id skips the code->UUID lookup and goes straight to /data.
        mock_get.return_value = Mock(status_code=504, text='gateway timeout')
        uuid = '5cebf1df3d0f4a073c4bb9a8x'
        with self.assertRaises(TideServiceUnavailableError):
            CHSAdapter().get_predictions(uuid, 2026, 8)


class TestRawDataCache(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self._patch = patch.object(get_tides, '_raw_cache_dir', lambda: self.dir)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_caches_after_first_fetch(self):
        calls = []

        def fake_download(sid, y, m):
            calls.append((sid, y, m))
            return VALID_CSV

        with patch.object(get_tides, 'download_tide_data', side_effect=fake_download):
            a = get_tides.get_tide_data('9449639', 2026, 8)
            b = get_tides.get_tide_data('9449639', 2026, 8)
        self.assertEqual(a, VALID_CSV)
        self.assertEqual(b, VALID_CSV)
        self.assertEqual(len(calls), 1, "second call must hit the cache, not the API")
        self.assertTrue(os.path.exists(get_tides.raw_cache_path_for('9449639', 2026, 8)))

    def test_cache_hit_survives_upstream_outage(self):
        # Warm the cache, then make every live fetch fail as if NOAA is down.
        with patch.object(get_tides, 'download_tide_data', return_value=VALID_CSV):
            get_tides.get_tide_data('9449639', 2026, 8)

        def outage(*a, **k):
            raise TideServiceUnavailableError("NOAA 504")

        with patch.object(get_tides, 'download_tide_data', side_effect=outage):
            # Same (cached) month: served from disk despite the outage.
            self.assertEqual(get_tides.get_tide_data('9449639', 2026, 8), VALID_CSV)
            # A cold month still propagates the outage.
            with self.assertRaises(TideServiceUnavailableError):
                get_tides.get_tide_data('9449639', 2026, 9)

    def test_invalid_cache_file_is_ignored_and_refetched(self):
        # A truncated/garbage cache file must not be served.
        path = get_tides.raw_cache_path_for('9449639', 2026, 8)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as fh:
            fh.write("garbage-no-newline")
        with patch.object(get_tides, 'download_tide_data', return_value=VALID_CSV) as dl:
            self.assertEqual(get_tides.get_tide_data('9449639', 2026, 8), VALID_CSV)
            dl.assert_called_once()


if __name__ == '__main__':
    unittest.main()
