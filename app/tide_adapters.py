"""
Tide Adapter Layer - Abstract interface for multiple tide prediction APIs

This module provides a standardized interface for fetching tide predictions
from different APIs (NOAA, Canadian Hydrographic Service, etc.).

All adapters return tide data in a unified CSV format with columns:
- Date Time: ISO format datetime (YYYY-MM-DD HH:MM)
- Prediction: Tide height in meters (float)
- Type: H for High tide, L for Low tide
"""

import logging
import requests
import calendar
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class TideAdapter(ABC):
    """
    Abstract base class for tide prediction API adapters.

    All concrete adapters must implement:
    - get_predictions(): Fetch tide predictions for a station/month/year
    - validate_station(): Check if a station ID is valid for this API
    - parse_response(): Convert API response to standardized CSV format
    """

    def __init__(self):
        """Initialize the adapter with any necessary configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_predictions(self, station_id: str, year: int, month: int) -> Optional[str]:
        """
        Fetch tide predictions for a given station and time period.

        Args:
            station_id: The station identifier (format varies by API)
            year: Year for predictions (e.g., 2024)
            month: Month for predictions (1-12)

        Returns:
            CSV string with columns: Date Time, Prediction, Type
            Returns None if the request fails or no data is available

        Raises:
            ValueError: If input parameters are invalid
        """
        pass

    @abstractmethod
    def validate_station(self, station_id: str) -> bool:
        """
        Validate that a station ID is in the correct format for this API.

        Args:
            station_id: The station identifier to validate

        Returns:
            True if the station ID format is valid, False otherwise
        """
        pass

    @abstractmethod
    def parse_response(self, response_data: str) -> Optional[str]:
        """
        Parse API response and convert to standardized CSV format.

        Args:
            response_data: Raw response data from the API

        Returns:
            Standardized CSV string with columns: Date Time, Prediction, Type
            Returns None if parsing fails
        """
        pass


class NOAAAdapter(TideAdapter):
    """
    Adapter for NOAA CO-OPS API (United States tide predictions).

    Station IDs: 7-digit numeric codes (e.g., 9449639)
    API Endpoint: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
    Date Format: YYYYMMDD
    """

    BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    def validate_station(self, station_id: str) -> bool:
        """
        Validate NOAA station ID format.

        NOAA stations are 7-digit numeric codes.
        """
        if not station_id or not station_id.isdigit():
            return False
        # NOAA stations are typically 7 digits, but can be 6-8
        return 6 <= len(station_id) <= 8

    def get_predictions(self, station_id: str, year: int, month: int) -> Optional[str]:
        """
        Fetch tide predictions from NOAA CO-OPS API.

        Args:
            station_id: 7-digit NOAA station ID
            year: Year for predictions
            month: Month for predictions (1-12)

        Returns:
            CSV string with standardized format or None if request fails
        """
        # Validate inputs
        if not self.validate_station(station_id):
            self.logger.error(f"Invalid NOAA station ID: {station_id}")
            return None

        if not (1 <= month <= 12):
            self.logger.error(f"Invalid month: {month}")
            return None

        if not (2000 <= year <= 2030):
            self.logger.error(f"Year out of range: {year}")
            return None

        # Calculate date range for the month
        _, last_day = calendar.monthrange(year, month)

        # Build request parameters
        params = {
            "begin_date": f"{year}{month:02d}01",
            "end_date": f"{year}{month:02d}{last_day}",
            "station": station_id,
            "product": "predictions",
            "datum": "MLLW",
            "time_zone": "lst_ldt",
            "interval": "hilo",
            "units": "metric",
            "format": "csv",
        }

        try:
            # Make the API request with User-Agent header
            headers = {
                'User-Agent': 'TideCalendarSite/1.0 (https://tidecalendar.xyz; contact@tidecalendar.xyz)'
            }
            self.logger.debug(f"Requesting NOAA data for station {station_id}, {year}-{month:02d}")
            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                self.logger.error(f"NOAA API request failed with status {response.status_code}")
                return None

            # Parse and validate response
            return self.parse_response(response.text)

        except requests.exceptions.RequestException as e:
            self.logger.error(f"NOAA API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in NOAA API request: {e}")
            return None

    def parse_response(self, response_data: str) -> Optional[str]:
        """
        Parse NOAA CSV response and convert to standardized format.

        NOAA API has changed formats over time:
        - Old format (4 columns): Date,Time, Prediction, Type
          Example: 2024-06-01,00:17, 3.245, H
        - New format (3 columns): Date Time,Prediction,Type
          Example: 2025-11-01 02:42,0.605,H

        This parser handles both formats automatically.

        Args:
            response_data: Raw CSV response from NOAA API

        Returns:
            Standardized CSV string or None if parsing fails
        """
        try:
            lines = response_data.strip().split('\n')

            # Check for error messages
            if len(lines) < 2:
                self.logger.error("NOAA response contains no data")
                return None

            if "No Predictions data was found" in response_data:
                self.logger.error("NOAA API returned no predictions")
                return None

            # Build standardized CSV output
            output_lines = ["Date Time,Prediction,Type"]

            # Skip header line and process data
            for line in lines[1:]:
                if not line.strip():
                    continue

                parts = [p.strip() for p in line.split(',')]

                if len(parts) < 3:
                    self.logger.warning(f"Skipping invalid NOAA data line: {line}")
                    continue

                # Detect format based on number of fields
                if len(parts) >= 4:
                    # Old format: Date,Time,Prediction,Type (4 columns)
                    date = parts[0]
                    time = parts[1]
                    prediction = parts[2]
                    tide_type = parts[3]
                    date_time = f"{date} {time}"
                else:
                    # New format: Date Time,Prediction,Type (3 columns)
                    date_time = parts[0]
                    prediction = parts[1]
                    tide_type = parts[2]

                # Standardize type (H or L)
                tide_type = tide_type.upper().strip()
                if tide_type not in ['H', 'L']:
                    tide_type = 'H' if 'H' in line.upper() else 'L'

                output_lines.append(f"{date_time},{prediction},{tide_type}")

            if len(output_lines) <= 1:
                self.logger.error("No valid tide predictions in NOAA response")
                return None

            result = '\n'.join(output_lines)
            self.logger.debug(f"Parsed {len(output_lines) - 1} NOAA tide predictions")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing NOAA response: {e}")
            return None


class CHSAdapter(TideAdapter):
    """
    Adapter for Canadian Hydrographic Service IWLS API (Canadian tide predictions).

    Station IDs: 4-6 digit numeric codes (typically 5 digits, e.g., 07735 for Vancouver)
                 OR UUID strings (e.g., 05cebf1df3d0f4a073c4bb9a8)
    API Endpoint: https://api-iwls.dfo-mpo.gc.ca/api/v1
    Time Series Code: wlp-hilo (water level predictions - high/low)
    Times: Returned in UTC, formatted as YYYY-MM-DD HH:MM

    Note: The CHS API requires UUID station IDs in data requests. If a numeric
    station code is provided, it will be automatically looked up to get the UUID.
    """

    BASE_URL = "https://api-iwls.dfo-mpo.gc.ca/api/v1"

    def validate_station(self, station_id: str) -> bool:
        """
        Validate CHS station ID format.

        CHS stations can be:
        - 4-6 digit numeric codes (station codes)
        - UUID strings (alphanumeric, typically 24+ characters)
        """
        if not station_id:
            return False

        # Accept UUID format (alphanumeric string, typically 24+ chars)
        if len(station_id) > 10 and station_id.replace('-', '').isalnum():
            return True

        # Accept numeric station codes (4-6 digits)
        if station_id.isdigit() and 4 <= len(station_id) <= 6:
            return True

        return False

    def _lookup_station_uuid(self, station_code: str) -> Optional[str]:
        """
        Look up the UUID for a given station code.

        The CHS API requires UUIDs for data requests, but stations are commonly
        identified by numeric codes. This method queries the stations endpoint
        to get the UUID for a given code.

        Args:
            station_code: Numeric station code (e.g., "07735")

        Returns:
            UUID string if found, None if lookup fails
        """
        import json

        try:
            # Query stations endpoint with station code
            params = {"code": station_code}
            headers = {
                'User-Agent': 'TideCalendarSite/1.0 (https://tidecalendar.xyz; contact@tidecalendar.xyz)'
            }

            self.logger.debug(f"Looking up UUID for station code {station_code}")
            response = requests.get(
                f"{self.BASE_URL}/stations",
                params=params,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                self.logger.error(f"Station lookup failed with status {response.status_code}: {response.text}")
                return None

            # Parse JSON response
            stations = json.loads(response.text)

            # Response should be an array with at least one station
            if not stations or len(stations) == 0:
                self.logger.error(f"No station found with code {station_code}")
                return None

            # Get the UUID from the first matching station
            station_uuid = stations[0].get('id')
            if not station_uuid:
                self.logger.error(f"Station data missing 'id' field for code {station_code}")
                return None

            self.logger.debug(f"Found UUID {station_uuid} for station code {station_code}")
            return station_uuid

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse station lookup response: {e}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error during station lookup: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during station lookup: {e}")
            return None

    def get_predictions(self, station_id: str, year: int, month: int) -> Optional[str]:
        """
        Fetch tide predictions from Canadian Hydrographic Service IWLS API.

        Args:
            station_id: CHS station ID (numeric code or UUID string)
            year: Year for predictions
            month: Month for predictions (1-12)

        Returns:
            CSV string with standardized format or None if request fails
        """
        # Validate inputs
        if not self.validate_station(station_id):
            self.logger.error(f"Invalid CHS station ID: {station_id}")
            return None

        if not (1 <= month <= 12):
            self.logger.error(f"Invalid month: {month}")
            return None

        if not (2000 <= year <= 2030):
            self.logger.error(f"Year out of range: {year}")
            return None

        # Determine if we need to lookup the UUID
        # If station_id is a numeric code (5 digits), lookup the UUID
        # If station_id is already a UUID (alphanumeric, >10 chars), use it directly
        if station_id.isdigit() and 4 <= len(station_id) <= 6:
            # This is a numeric station code, need to lookup UUID
            self.logger.debug(f"Station {station_id} is a numeric code, looking up UUID")
            station_uuid = self._lookup_station_uuid(station_id)
            if not station_uuid:
                self.logger.error(f"Failed to lookup UUID for station code {station_id}")
                return None
        else:
            # This is already a UUID
            station_uuid = station_id

        # Calculate date range for the month
        _, last_day = calendar.monthrange(year, month)

        # Build request parameters for CHS IWLS API
        # Format: ISO 8601 datetime (YYYY-MM-DDTHH:MM:SSZ)
        from_date = f"{year}-{month:02d}-01T00:00:00Z"
        to_date = f"{year}-{month:02d}-{last_day}T23:59:59Z"

        # CHS API endpoint for high/low predictions (using UUID)
        endpoint = f"{self.BASE_URL}/stations/{station_uuid}/data"

        params = {
            "time-series-code": "wlp-hilo",
            "from": from_date,
            "to": to_date
        }

        try:
            # Make the API request with User-Agent header
            headers = {
                'User-Agent': 'TideCalendarSite/1.0 (https://tidecalendar.xyz; contact@tidecalendar.xyz)'
            }
            self.logger.debug(f"Requesting CHS data for station UUID {station_uuid}, {year}-{month:02d}")
            response = requests.get(endpoint, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                self.logger.error(f"CHS API request failed with status {response.status_code}: {response.text}")
                return None

            # Parse JSON response
            return self.parse_response(response.text)

        except requests.exceptions.RequestException as e:
            self.logger.error(f"CHS API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in CHS API request: {e}")
            return None

    def parse_response(self, response_data: str) -> Optional[str]:
        """
        Parse CHS JSON response and convert to standardized CSV format.

        CHS returns JSON with structure:
        {
            "data": [
                {
                    "eventDate": "2024-06-01T05:23:00Z",
                    "value": 4.82,
                    "qcFlagCode": "1",
                    "timeSeriesId": "...",
                    "eventId": "..."
                },
                ...
            ]
        }

        The "value" alternates between high and low tides.

        Args:
            response_data: Raw JSON response from CHS API

        Returns:
            Standardized CSV string or None if parsing fails
        """
        try:
            import json

            # Parse JSON response
            data = json.loads(response_data)

            if 'data' not in data or not data['data']:
                self.logger.error("CHS response contains no data")
                return None

            predictions = data['data']

            # Build standardized CSV output
            output_lines = ["Date Time,Prediction,Type"]

            # CHS alternates high and low tides in chronological order
            # Typically: Low, High, Low, High, ...
            # We need to determine which is which based on the pattern
            for i, prediction in enumerate(predictions):
                event_date = prediction.get('eventDate')
                value = prediction.get('value')

                if not event_date or value is None:
                    self.logger.warning(f"Skipping invalid CHS prediction: {prediction}")
                    continue

                # Parse ISO 8601 datetime
                # CHS returns UTC times - we keep them as-is for consistency
                # (NOAA also uses local standard time without DST adjustment)
                try:
                    dt = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                    # Format as YYYY-MM-DD HH:MM (keeping UTC)
                    date_time = dt.strftime('%Y-%m-%d %H:%M')
                except ValueError as e:
                    self.logger.warning(f"Invalid date format in CHS response: {event_date}")
                    continue

                # Determine tide type based on neighboring values
                # If value is higher than neighbors, it's a high tide
                # If value is lower than neighbors, it's a low tide
                tide_type = self._determine_tide_type(predictions, i, value)

                output_lines.append(f"{date_time},{value},{tide_type}")

            if len(output_lines) <= 1:
                self.logger.error("No valid tide predictions in CHS response")
                return None

            result = '\n'.join(output_lines)
            self.logger.debug(f"Parsed {len(output_lines) - 1} CHS tide predictions")
            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing CHS JSON response: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error processing CHS response: {e}")
            return None

    def _determine_tide_type(self, predictions: list, index: int, value: float) -> str:
        """
        Determine if a tide event is High or Low based on neighboring values.

        Args:
            predictions: List of all predictions
            index: Current prediction index
            value: Current tide height

        Returns:
            'H' for high tide, 'L' for low tide
        """
        # Get neighboring values for comparison
        prev_value = predictions[index - 1].get('value') if index > 0 else None
        next_value = predictions[index + 1].get('value') if index < len(predictions) - 1 else None

        # If we have both neighbors, check if this is a peak or trough
        if prev_value is not None and next_value is not None:
            if value > prev_value and value > next_value:
                return 'H'  # Local maximum = high tide
            elif value < prev_value and value < next_value:
                return 'L'  # Local minimum = low tide

        # If we only have previous value
        if prev_value is not None:
            return 'H' if value > prev_value else 'L'

        # If we only have next value
        if next_value is not None:
            return 'H' if value > next_value else 'L'

        # Default to alternating pattern (usually starts with Low)
        return 'L' if index % 2 == 0 else 'H'


def get_adapter_for_station(station_id: str, api_source: Optional[str] = None) -> TideAdapter:
    """
    Factory function to get the appropriate adapter for a station.

    Args:
        station_id: The station identifier
        api_source: Optional API source hint ('NOAA' or 'CHS')
                   If not provided, determined by station ID format

    Returns:
        Appropriate TideAdapter instance (NOAAAdapter or CHSAdapter)

    Raises:
        ValueError: If station ID format is invalid or unsupported
    """
    # If API source is explicitly specified, use it
    if api_source:
        if api_source.upper() == 'NOAA':
            return NOAAAdapter()
        elif api_source.upper() == 'CHS':
            return CHSAdapter()
        else:
            raise ValueError(f"Unsupported API source: {api_source}")

    # Otherwise, determine by station ID format
    if not station_id:
        raise ValueError("Station ID cannot be empty")

    # Try NOAA format first (7-digit)
    noaa_adapter = NOAAAdapter()
    if noaa_adapter.validate_station(station_id):
        return noaa_adapter

    # Try CHS format (5-digit)
    chs_adapter = CHSAdapter()
    if chs_adapter.validate_station(station_id):
        return chs_adapter

    raise ValueError(f"Station ID format not recognized: {station_id}")
