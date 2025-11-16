"""
Unit tests for tide adapter layer.

Tests cover:
- Abstract base class interface
- NOAA adapter functionality
- CHS adapter functionality
- Response parsing and standardization
- Error handling
"""

import unittest
from unittest.mock import Mock, patch
import json
import logging

from tide_adapters import (
    NOAAAdapter,
    CHSAdapter,
    get_adapter_for_station
)

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestNOAAAdapter(unittest.TestCase):
    """Test suite for NOAA adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.adapter = NOAAAdapter()

    def test_validate_station_valid(self):
        """Test validation of valid NOAA station IDs."""
        valid_ids = ['9449639', '8454000', '1234567']
        for station_id in valid_ids:
            self.assertTrue(
                self.adapter.validate_station(station_id),
                f"Station {station_id} should be valid"
            )

    def test_validate_station_invalid(self):
        """Test validation of invalid NOAA station IDs."""
        invalid_ids = ['', 'abc', '12345', '123456789', '12abc34']
        for station_id in invalid_ids:
            self.assertFalse(
                self.adapter.validate_station(station_id),
                f"Station {station_id} should be invalid"
            )

    def test_parse_response_valid(self):
        """Test parsing of valid NOAA API response (old 4-column format)."""
        # Sample NOAA response (old format with separate Date and Time columns)
        noaa_response = """Date,Time, Prediction, Type
2024-06-01,00:17, 3.245, H
2024-06-01,06:42, 0.123, L
2024-06-01,13:05, 3.456, H
2024-06-01,19:28, 0.234, L"""

        result = self.adapter.parse_response(noaa_response)

        self.assertIsNotNone(result)
        lines = result.strip().split('\n')

        # Check header
        self.assertEqual(lines[0], "Date Time,Prediction,Type")

        # Check first data line
        self.assertEqual(lines[1], "2024-06-01 00:17,3.245,H")

        # Check we have 4 data lines + 1 header
        self.assertEqual(len(lines), 5)

    def test_parse_response_new_format(self):
        """Test parsing of valid NOAA API response (new 3-column format)."""
        # Sample NOAA response (new format with combined Date Time column)
        noaa_response = """Date Time,Prediction,Type
2025-11-01 02:42,0.605,H
2025-11-01 10:32,0.06,L
2025-11-01 15:58,0.645,H
2025-11-01 22:55,0.168,L"""

        result = self.adapter.parse_response(noaa_response)

        self.assertIsNotNone(result)
        lines = result.strip().split('\n')

        # Check header
        self.assertEqual(lines[0], "Date Time,Prediction,Type")

        # Check first data line
        self.assertEqual(lines[1], "2025-11-01 02:42,0.605,H")

        # Check second data line
        self.assertEqual(lines[2], "2025-11-01 10:32,0.06,L")

        # Check we have 4 data lines + 1 header
        self.assertEqual(len(lines), 5)

    def test_parse_response_no_data(self):
        """Test parsing of response with no predictions."""
        noaa_response = """Date,Time, Prediction, Type
No Predictions data was found."""

        result = self.adapter.parse_response(noaa_response)
        self.assertIsNone(result)

    def test_parse_response_empty(self):
        """Test parsing of empty response."""
        result = self.adapter.parse_response("")
        self.assertIsNone(result)

    @patch('tide_adapters.requests.get')
    def test_get_predictions_success(self, mock_get):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """Date,Time, Prediction, Type
2024-06-01,00:17, 3.245, H
2024-06-01,06:42, 0.123, L"""
        mock_get.return_value = mock_response

        result = self.adapter.get_predictions('9449639', 2024, 6)

        self.assertIsNotNone(result)
        self.assertIn("Date Time,Prediction,Type", result)

    @patch('tide_adapters.requests.get')
    def test_get_predictions_api_error(self, mock_get):
        """Test API request with error response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.adapter.get_predictions('9449639', 2024, 6)
        self.assertIsNone(result)

    def test_get_predictions_invalid_inputs(self):
        """Test get_predictions with invalid inputs."""
        # Invalid station ID
        result = self.adapter.get_predictions('invalid', 2024, 6)
        self.assertIsNone(result)

        # Invalid month
        result = self.adapter.get_predictions('9449639', 2024, 13)
        self.assertIsNone(result)

        # Invalid year
        result = self.adapter.get_predictions('9449639', 1999, 6)
        self.assertIsNone(result)


class TestCHSAdapter(unittest.TestCase):
    """Test suite for CHS adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.adapter = CHSAdapter()

    def test_validate_station_valid(self):
        """Test validation of valid CHS station IDs."""
        valid_ids = ['07735', '00490', '08615', '12345']
        for station_id in valid_ids:
            self.assertTrue(
                self.adapter.validate_station(station_id),
                f"Station {station_id} should be valid"
            )

    def test_validate_station_invalid(self):
        """Test validation of invalid CHS station IDs."""
        invalid_ids = ['', 'abc', '123', '1234567', '12abc']
        for station_id in invalid_ids:
            self.assertFalse(
                self.adapter.validate_station(station_id),
                f"Station {station_id} should be invalid"
            )

    def test_determine_tide_type(self):
        """Test tide type determination logic."""
        # Mock prediction data with clear high/low pattern
        predictions = [
            {'value': 1.0},  # Low
            {'value': 4.5},  # High
            {'value': 0.5},  # Low
            {'value': 4.8},  # High
            {'value': 0.3}   # Low
        ]

        # Test high tide (index 1)
        self.assertEqual(self.adapter._determine_tide_type(predictions, 1, 4.5), 'H')

        # Test low tide (index 2)
        self.assertEqual(self.adapter._determine_tide_type(predictions, 2, 0.5), 'L')

        # Test high tide (index 3)
        self.assertEqual(self.adapter._determine_tide_type(predictions, 3, 4.8), 'H')

    def test_parse_response_valid(self):
        """Test parsing of valid CHS API response."""
        # Sample CHS JSON response
        chs_response = json.dumps({
            "data": [
                {
                    "eventDate": "2024-06-01T05:23:00Z",
                    "value": 0.82,
                    "qcFlagCode": "1"
                },
                {
                    "eventDate": "2024-06-01T11:45:00Z",
                    "value": 4.52,
                    "qcFlagCode": "1"
                },
                {
                    "eventDate": "2024-06-01T17:58:00Z",
                    "value": 0.65,
                    "qcFlagCode": "1"
                }
            ]
        })

        result = self.adapter.parse_response(chs_response)

        self.assertIsNotNone(result)
        lines = result.strip().split('\n')

        # Check header
        self.assertEqual(lines[0], "Date Time,Prediction,Type")

        # Check we have data lines
        self.assertGreater(len(lines), 1)

        # Verify CSV format
        for line in lines[1:]:
            parts = line.split(',')
            self.assertEqual(len(parts), 3)  # Date Time, Prediction, Type

    def test_parse_response_no_data(self):
        """Test parsing of response with no data."""
        chs_response = json.dumps({"data": []})

        result = self.adapter.parse_response(chs_response)
        self.assertIsNone(result)

    def test_parse_response_invalid_json(self):
        """Test parsing of invalid JSON response."""
        result = self.adapter.parse_response("not valid json")
        self.assertIsNone(result)

    @patch('tide_adapters.requests.get')
    def test_get_predictions_success(self, mock_get):
        """Test successful CHS API request."""
        # Mock two responses: one for UUID lookup, one for data
        # First call: UUID lookup
        mock_lookup_response = Mock()
        mock_lookup_response.status_code = 200
        mock_lookup_response.text = json.dumps([
            {"id": "test-uuid-123", "code": "07735", "officialName": "Vancouver, BC"}
        ])

        # Second call: Tide data
        mock_data_response = Mock()
        mock_data_response.status_code = 200
        mock_data_response.text = json.dumps({
            "data": [
                {
                    "eventDate": "2024-06-01T05:23:00Z",
                    "value": 0.82,
                    "qcFlagCode": "1"
                },
                {
                    "eventDate": "2024-06-01T11:45:00Z",
                    "value": 4.52,
                    "qcFlagCode": "1"
                }
            ]
        })

        # Configure mock to return different responses for different calls
        mock_get.side_effect = [mock_lookup_response, mock_data_response]

        result = self.adapter.get_predictions('07735', 2024, 6)

        self.assertIsNotNone(result)
        self.assertIn("Date Time,Prediction,Type", result)

    @patch('tide_adapters.requests.get')
    def test_get_predictions_api_error(self, mock_get):
        """Test CHS API request with error response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        result = self.adapter.get_predictions('07735', 2024, 6)
        self.assertIsNone(result)

    def test_get_predictions_invalid_inputs(self):
        """Test get_predictions with invalid inputs."""
        # Invalid station ID
        result = self.adapter.get_predictions('invalid', 2024, 6)
        self.assertIsNone(result)

        # Invalid month
        result = self.adapter.get_predictions('07735', 2024, 0)
        self.assertIsNone(result)


class TestAdapterFactory(unittest.TestCase):
    """Test suite for adapter factory function."""

    def test_get_adapter_by_api_source(self):
        """Test getting adapter by explicit API source."""
        # Test NOAA
        adapter = get_adapter_for_station('9449639', 'NOAA')
        self.assertIsInstance(adapter, NOAAAdapter)

        # Test CHS
        adapter = get_adapter_for_station('07735', 'CHS')
        self.assertIsInstance(adapter, CHSAdapter)

    def test_get_adapter_by_station_format(self):
        """Test getting adapter by station ID format."""
        # NOAA format (7 digits)
        adapter = get_adapter_for_station('9449639')
        self.assertIsInstance(adapter, NOAAAdapter)

        # CHS format (5 digits)
        adapter = get_adapter_for_station('07735')
        self.assertIsInstance(adapter, CHSAdapter)

    def test_get_adapter_invalid_station(self):
        """Test factory with invalid station ID."""
        with self.assertRaises(ValueError):
            get_adapter_for_station('')

        with self.assertRaises(ValueError):
            get_adapter_for_station('abc')

    def test_get_adapter_unsupported_api(self):
        """Test factory with unsupported API source."""
        with self.assertRaises(ValueError):
            get_adapter_for_station('12345', 'UNSUPPORTED')


class TestResponseStandardization(unittest.TestCase):
    """Test that both adapters produce consistent output format."""

    def test_noaa_output_format(self):
        """Verify NOAA adapter produces standardized format."""
        adapter = NOAAAdapter()

        noaa_response = """Date,Time, Prediction, Type
2024-06-01,00:17, 3.245, H
2024-06-01,06:42, 0.123, L"""

        result = adapter.parse_response(noaa_response)
        lines = result.strip().split('\n')

        # Check header matches standard
        self.assertEqual(lines[0], "Date Time,Prediction,Type")

        # Check data format
        parts = lines[1].split(',')
        self.assertEqual(len(parts), 3)
        self.assertIn(' ', parts[0])  # Date Time has space
        self.assertTrue(parts[2] in ['H', 'L'])  # Type is H or L

    def test_chs_output_format(self):
        """Verify CHS adapter produces standardized format."""
        adapter = CHSAdapter()

        chs_response = json.dumps({
            "data": [
                {
                    "eventDate": "2024-06-01T05:23:00Z",
                    "value": 0.82,
                    "qcFlagCode": "1"
                }
            ]
        })

        result = adapter.parse_response(chs_response)
        lines = result.strip().split('\n')

        # Check header matches standard
        self.assertEqual(lines[0], "Date Time,Prediction,Type")

        # Check data format
        parts = lines[1].split(',')
        self.assertEqual(len(parts), 3)
        self.assertIn(' ', parts[0])  # Date Time has space
        self.assertTrue(parts[2] in ['H', 'L'])  # Type is H or L


class TestErrorScenarios(unittest.TestCase):
    """Test error handling across all adapters."""

    @patch('tide_adapters.requests.get')
    def test_noaa_network_timeout(self, mock_get):
        """Test NOAA adapter handles network timeout."""
        mock_get.side_effect = Exception("Network timeout")

        adapter = NOAAAdapter()
        result = adapter.get_predictions('9449639', 2024, 6)

        self.assertIsNone(result)

    @patch('tide_adapters.requests.get')
    def test_chs_network_timeout(self, mock_get):
        """Test CHS adapter handles network timeout."""
        # Network timeout should happen during UUID lookup (first call)
        mock_get.side_effect = Exception("Network timeout")

        adapter = CHSAdapter()
        result = adapter.get_predictions('07735', 2024, 6)

        # Should return None and handle the exception gracefully
        self.assertIsNone(result)

    def test_noaa_malformed_response(self):
        """Test NOAA adapter handles malformed response."""
        adapter = NOAAAdapter()

        # Missing columns
        malformed = "Date,Time\n2024-06-01,00:17"
        result = adapter.parse_response(malformed)
        # Should handle gracefully, likely return None or skip bad lines

    def test_chs_malformed_response(self):
        """Test CHS adapter handles malformed JSON."""
        adapter = CHSAdapter()

        # Missing required fields
        malformed = json.dumps({
            "data": [
                {"value": 1.0}  # Missing eventDate
            ]
        })
        result = adapter.parse_response(malformed)
        # Should handle gracefully


def run_tests():
    """Run all unit tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestNOAAAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestCHSAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestAdapterFactory))
    suite.addTests(loader.loadTestsFromTestCase(TestResponseStandardization))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorScenarios))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    import sys
    sys.exit(run_tests())
