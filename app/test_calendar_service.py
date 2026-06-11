"""Tests for calendar_service: the filename contract and the cache/generate flow.

Run from the app/ directory (matches CI):
    python -m unittest test_calendar_service -v
"""
import os
import tempfile
import unittest
from unittest import mock

import calendar_service
from calendar_service import (GenerateResult, extract_location_with_state,
                              get_or_generate_pdf, pdf_filename_for,
                              sanitize_filename)
from get_tides import TideDataError


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
    def test_with_location(self):
        self.assertEqual(pdf_filename_for("Point Roberts, WA", "9449639", 2026, 6),
                         "tide_calendar_Point_Roberts_WA_2026_06.pdf")

    def test_without_location_falls_back_to_station_id(self):
        self.assertEqual(pdf_filename_for(None, "9449639", 2026, 6),
                         "tide_calendar_9449639_2026_06.pdf")

    def test_month_zero_padded(self):
        self.assertTrue(pdf_filename_for(None, "1", 2026, 1).endswith("_2026_01.pdf"))


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
        cached = os.path.join(self.tmpdir.name, "tide_calendar_Point_Roberts_WA_2026_06.pdf")
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
        cached = os.path.join(self.tmpdir.name, "tide_calendar_Point_Roberts_WA_2026_06.pdf")
        open(cached, 'wb').close()  # zero bytes

        def fake_generate(station_id, year, month, output_path, location_name=None):
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

        def fake_generate(station_id, year, month, output_path, location_name=None):
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

        def fake_generate(station_id, year, month, output_path, location_name=None):
            with open(output_path, 'wb') as f:
                f.write(b"%PDF-fake")
            return output_path

        with mock.patch.object(calendar_service, 'generate_calendar',
                               side_effect=fake_generate):
            result = get_or_generate_pdf("999", 2026, 6)

        self.assertTrue(result.ok)
        self.assertEqual(os.path.basename(result.pdf_path),
                         "tide_calendar_999_2026_06.pdf")

    def test_unknown_station_rejected_before_any_work(self):
        self.get_info.return_value = None

        with mock.patch.object(calendar_service, 'generate_calendar') as gen:
            result = get_or_generate_pdf("31337", 2026, 6)

        gen.assert_not_called()
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'unknown_station')
        self.log_usage.assert_called_once_with(
            "31337", None, 2026, 6, 'error', 'unknown_station', source='web')


if __name__ == '__main__':
    unittest.main()
