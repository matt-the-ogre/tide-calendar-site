"""Tests for calendar_service: the filename contract and the cache/generate flow.

Run from the app/ directory (matches CI):
    python -m unittest test_calendar_service -v
"""
import os
import tempfile
import threading
import unittest
from unittest import mock

import calendar_service
import get_tides
from calendar_service import (GenerateResult, extract_location_with_state,
                              get_or_generate_pdf, pdf_filename_for,
                              sanitize_filename)
from get_tides import TideDataError, generate_calendar


class TestSanitizeFilename(unittest.TestCase):
    def test_basic_location(self):
        self.assertEqual(sanitize_filename("Point Roberts, WA"), "Point_Roberts_WA")

    def test_problematic_characters(self):
        self.assertEqual(sanitize_filename('a/b\\c:d*e?f"g<h>i|j,k'), "a_b_c_d_e_f_g_h_i_j_k")

    def test_empty_and_none(self):
        self.assertEqual(sanitize_filename(""), "unknown")
        self.assertEqual(sanitize_filename(None), "unknown")

    def test_length_capped(self):
        self.assertLessEqual(len(sanitize_filename("x" * 300)), 100)


class TestExtractLocationWithState(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(extract_location_with_state("Point Roberts, WA"), "Point Roberts, WA")

    def test_collapses_middle_parts(self):
        self.assertEqual(
            extract_location_with_state("Port Allen, Hanapepe Bay, Kauai Island, HI"),
            "Port Allen, HI")

    def test_single_part(self):
        self.assertEqual(extract_location_with_state("Esperanza"), "Esperanza")

    def test_none(self):
        self.assertIsNone(extract_location_with_state(None))


class TestPdfFilenameContract(unittest.TestCase):
    def test_with_location_imperial(self):
        self.assertEqual(pdf_filename_for("Point Roberts, WA", "9449639", 2026, 6, 'imperial'),
                         "tide_calendar_Point_Roberts_WA_2026_06_ft.pdf")

    def test_with_location_metric(self):
        self.assertEqual(pdf_filename_for("Point Roberts, WA", "9449639", 2026, 6, 'metric'),
                         "tide_calendar_Point_Roberts_WA_2026_06_m.pdf")

    def test_default_unit_is_imperial(self):
        self.assertTrue(pdf_filename_for("Point Roberts, WA", "9449639", 2026, 6).endswith("_ft.pdf"))

    def test_without_location_falls_back_to_station_id(self):
        self.assertEqual(pdf_filename_for(None, "9449639", 2026, 6, 'imperial'),
                         "tide_calendar_9449639_2026_06_ft.pdf")

    def test_month_zero_padded(self):
        self.assertTrue(pdf_filename_for(None, "1", 2026, 1, 'imperial').endswith("_2026_01_ft.pdf"))

    def test_metric_and_imperial_filenames_differ(self):
        ft = pdf_filename_for("Point Roberts, WA", "9449639", 2026, 7, 'imperial')
        m = pdf_filename_for("Point Roberts, WA", "9449639", 2026, 7, 'metric')
        self.assertNotEqual(ft, m)
        self.assertTrue(ft.endswith("_ft.pdf"))
        self.assertTrue(m.endswith("_m.pdf"))


class TestGetOrGeneratePdf(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        patcher = mock.patch.object(calendar_service, 'PDF_OUTPUT_DIR', self.tmpdir.name)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.log_usage = mock.patch.object(calendar_service, 'log_usage_event').start()
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(calendar_service, 'log_station_lookup').start()
        self.get_info = mock.patch.object(
            calendar_service, 'get_station_info',
            return_value={'station_id': '9449639',
                          'place_name': 'Point Roberts, WA'}).start()

    def test_cache_hit_serves_existing_pdf_without_generating(self):
        cached = os.path.join(self.tmpdir.name, "tide_calendar_Point_Roberts_WA_2026_06_ft.pdf")
        with open(cached, 'wb') as f:
            f.write(b"%PDF-fake")

        with mock.patch.object(calendar_service, 'generate_calendar') as gen:
            result = get_or_generate_pdf("9449639", 2026, 6)

        gen.assert_not_called()
        self.assertTrue(result.ok)
        self.assertEqual(result.pdf_path, cached)
        self.log_usage.assert_called_once_with(
            "9449639", "Point Roberts, WA", 2026, 6, 'success', source='web')

    def test_empty_cached_file_triggers_regeneration(self):
        cached = os.path.join(self.tmpdir.name, "tide_calendar_Point_Roberts_WA_2026_06_ft.pdf")
        open(cached, 'wb').close()  # zero bytes

        def fake_generate(station_id, year, month, output_path, location_name=None, unit='imperial'):
            with open(output_path, 'wb') as f:
                f.write(b"%PDF-fake")
            return output_path

        with mock.patch.object(calendar_service, 'generate_calendar',
                               side_effect=fake_generate) as gen:
            result = get_or_generate_pdf("9449639", 2026, 6)

        gen.assert_called_once()
        self.assertTrue(result.ok)

    def test_generation_writes_to_predicted_path(self):
        """The cache check predicts the generator's output path — they must agree."""
        seen = {}

        def fake_generate(station_id, year, month, output_path, location_name=None, unit='imperial'):
            seen['path'] = output_path
            with open(output_path, 'wb') as f:
                f.write(b"%PDF-fake")
            return output_path

        with mock.patch.object(calendar_service, 'generate_calendar',
                               side_effect=fake_generate):
            result = get_or_generate_pdf("9449639", 2026, 6)

        self.assertEqual(seen['path'], result.pdf_path)
        self.assertEqual(os.path.basename(result.pdf_path),
                         pdf_filename_for("Point Roberts, WA", "9449639", 2026, 6))

    def test_no_predictions_maps_to_error_result(self):
        with mock.patch.object(calendar_service, 'generate_calendar',
                               side_effect=TideDataError("no data")):
            result = get_or_generate_pdf("12345", 2026, 6, source='quick_api')

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'no_predictions')
        self.log_usage.assert_called_once_with(
            "12345", "Point Roberts, WA", 2026, 6, 'error', 'no_predictions',
            source='quick_api')

    def test_station_without_place_name_uses_station_id_in_filename(self):
        self.get_info.return_value = {'station_id': '999', 'place_name': None}

        def fake_generate(station_id, year, month, output_path, location_name=None, unit='imperial'):
            with open(output_path, 'wb') as f:
                f.write(b"%PDF-fake")
            return output_path

        with mock.patch.object(calendar_service, 'generate_calendar',
                               side_effect=fake_generate):
            result = get_or_generate_pdf("999", 2026, 6)

        self.assertTrue(result.ok)
        self.assertEqual(os.path.basename(result.pdf_path),
                         "tide_calendar_999_2026_06_ft.pdf")

    def test_unknown_station_rejected_before_any_work(self):
        self.get_info.return_value = None

        with mock.patch.object(calendar_service, 'generate_calendar') as gen:
            result = get_or_generate_pdf("31337", 2026, 6)

        gen.assert_not_called()
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'unknown_station')
        self.log_usage.assert_called_once_with(
            "31337", None, 2026, 6, 'error', 'unknown_station', source='web')


class TestGenerateCalendarConcurrency(unittest.TestCase):
    """Concurrent same-station requests must not share temp files.

    gunicorn threads share a PID, so the temp-PDF suffix must be unique per
    thread — otherwise two cache-miss requests for the same station/month
    interleave writes and one thread's cleanup deletes the other's output.
    """

    CSV = "Date Time, Prediction, Type\n2026-06-01 04:30,1.2,H\n"

    def test_concurrent_generations_to_same_path_both_succeed(self):
        barrier = threading.Barrier(2, timeout=10)
        errors = []

        def fake_run_tool(cmd):
            if cmd[0] == "pcal":
                with open(cmd[4], 'w') as f:  # ["pcal","-f",in,"-o",out,...]
                    f.write("%!PS-fake\n")
            elif cmd[0] == "ps2pdf":
                with open(cmd[2], 'wb') as f:  # ["ps2pdf", in, out]
                    f.write(b"%PDF-fake\n")
                # Hold both threads here so their temp files coexist; with a
                # shared temp name the second os.replace() then fails.
                barrier.wait()

        def worker(out_path):
            try:
                generate_calendar("9449639", 2026, 6, out_path)
            except Exception as e:  # noqa: BLE001 — recording any failure
                errors.append(e)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "tide_calendar_X_2026_06.pdf")
            with mock.patch.object(get_tides, 'download_tide_data', return_value=self.CSV), \
                 mock.patch.object(get_tides, '_run_tool', side_effect=fake_run_tool):
                threads = [threading.Thread(target=worker, args=(out_path,)) for _ in range(2)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=15)

            self.assertEqual(errors, [])
            with open(out_path, 'rb') as f:
                self.assertEqual(f.read(), b"%PDF-fake\n")
            # No stray temp files left behind
            self.assertEqual(os.listdir(tmpdir), [os.path.basename(out_path)])


if __name__ == '__main__':
    unittest.main()
