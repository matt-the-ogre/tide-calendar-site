# Tide Adapter System

## Overview

The tide adapter system provides a unified interface for fetching tide predictions from multiple APIs (NOAA, Canadian Hydrographic Service, and potentially others in the future).

## Architecture

### Abstract Base Class: `TideAdapter`

All adapters inherit from the abstract `TideAdapter` class and must implement:

- `get_predictions(station_id, year, month)`: Fetch tide predictions
- `validate_station(station_id)`: Validate station ID format
- `parse_response(response_data)`: Parse API response to standardized CSV

### Standardized Output Format

All adapters return tide data in a consistent CSV format:

```csv
Date Time,Prediction,Type
2024-06-01 00:17,3.245,H
2024-06-01 06:42,0.123,L
2024-06-01 13:05,3.456,H
```

**Columns:**
- `Date Time`: ISO format datetime (YYYY-MM-DD HH:MM)
- `Prediction`: Tide height in meters (float)
- `Type`: `H` for High tide, `L` for Low tide

## Supported APIs

### NOAA CO-OPS API (United States)

**Class:** `NOAAAdapter`

**Station ID Format:** 7-digit numeric codes (e.g., `9449639`)

**API Endpoint:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`

**Date Format:** YYYYMMDD

**Example:**
```python
from tide_adapters import NOAAAdapter

adapter = NOAAAdapter()
csv_data = adapter.get_predictions('9449639', 2024, 6)
```

### Canadian Hydrographic Service IWLS API

**Class:** `CHSAdapter`

**Station ID Format:** 5-digit numeric codes (e.g., `07735`)

**API Endpoint:** `https://api-iwls.dfo-mpo.gc.ca/api/v1`

**Time Series Code:** `wlp-hilo` (water level predictions - high/low)

**Example:**
```python
from tide_adapters import CHSAdapter

adapter = CHSAdapter()
csv_data = adapter.get_predictions('07735', 2024, 6)  # Vancouver, BC
```

## Usage

### Factory Function

The recommended way to get the appropriate adapter is using the factory function:

```python
from tide_adapters import get_adapter_for_station
from database import get_station_info

# Get station info from database to determine API source
station_info = get_station_info('07735')
api_source = station_info.get('api_source') if station_info else None

# Get the appropriate adapter
adapter = get_adapter_for_station('07735', api_source)

# Fetch predictions
csv_data = adapter.get_predictions('07735', 2024, 6)
```

### Direct Instantiation

You can also instantiate adapters directly if you know the API type:

```python
from tide_adapters import NOAAAdapter, CHSAdapter

# For NOAA stations
noaa = NOAAAdapter()
data = noaa.get_predictions('9449639', 2024, 6)

# For Canadian stations
chs = CHSAdapter()
data = chs.get_predictions('07735', 2024, 6)
```

## Integration with get_tides.py

The `download_tide_data()` function in `get_tides.py` has been refactored to use the adapter system:

1. Retrieves station info from database (including `api_source`)
2. Uses `get_adapter_for_station()` to get the appropriate adapter
3. Calls `adapter.get_predictions()` to fetch data
4. Saves the standardized CSV to a file
5. Continues with existing pcal conversion and PDF generation

## Testing

Comprehensive unit tests are available in `test_tide_adapters.py`:

```bash
python3 app/test_tide_adapters.py
```

**Test Coverage:**
- Station ID validation for both adapters
- Response parsing and standardization
- Error handling (network errors, invalid data, malformed responses)
- Factory function behavior
- Output format consistency

## Adding New Adapters

To add support for a new tide prediction API:

1. Create a new class that inherits from `TideAdapter`
2. Implement the three required methods:
   - `validate_station()`
   - `get_predictions()`
   - `parse_response()`
3. Ensure the output matches the standardized CSV format
4. Add the adapter to the `get_adapter_for_station()` factory function
5. Write comprehensive unit tests

**Example:**

```python
class NewCountryAdapter(TideAdapter):
    """Adapter for New Country Tide API."""

    BASE_URL = "https://api.newcountry.gov/tides"

    def validate_station(self, station_id: str) -> bool:
        # Validate station ID format
        return station_id.isdigit() and len(station_id) == 4

    def get_predictions(self, station_id: str, year: int, month: int) -> Optional[str]:
        # Fetch data from API
        # Return standardized CSV or None
        pass

    def parse_response(self, response_data: str) -> Optional[str]:
        # Parse API response
        # Return "Date Time,Prediction,Type" CSV format
        pass
```

## API-Specific Notes

### NOAA
- Returns CSV format directly
- Uses MLLW datum (Mean Lower Low Water)
- Times are in local standard/daylight time (LST/LDT)
- Supports predictions for years 2000-2030

### CHS
- Returns JSON format
- Alternates high and low tides in chronological order
- Times are in UTC (converted to local format)
- Requires tide type determination based on value patterns
- May return 403 errors if proper User-Agent headers are not provided

## Error Handling

All adapters implement robust error handling:

- **Invalid inputs:** Returns `None` and logs error
- **Network failures:** Catches `RequestException` and returns `None`
- **API errors:** Checks status codes, returns `None` for non-200 responses
- **Parse failures:** Validates data format, returns `None` for invalid data
- **No data available:** Detects empty responses, returns `None`

## Database Integration

Station metadata is stored in the `tide_station_ids` table with the following columns:

- `station_id`: Unique station identifier
- `place_name`: Human-readable location name
- `country`: Country code (USA, Canada, etc.)
- `api_source`: API to use (NOAA, CHS, etc.)
- `latitude`, `longitude`: Geographic coordinates
- `province`: Province/state code
- `lookup_count`: Number of times station has been queried
- `last_lookup`: Timestamp of last query

The `get_station_info()` function retrieves this metadata to determine which adapter to use.

## Performance Considerations

- PDF files are cached for 30 days to reduce API calls
- Failed API requests are logged but don't crash the application
- Timeout set to 30 seconds for all API requests
- Database queries are optimized with indexes on `station_id`

## Future Enhancements

Potential improvements for the adapter system:

1. Add caching layer for API responses
2. Implement retry logic with exponential backoff
3. Add support for more countries (UK, Australia, etc.)
4. Implement request rate limiting
5. Add API key management for authenticated APIs
6. Support for real-time tide data (not just predictions)
7. Support for currents data alongside tides
