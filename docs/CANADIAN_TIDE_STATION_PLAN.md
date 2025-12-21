# Comprehensive Plan: Integrating Canadian Tide Stations

Based on my research, here's a detailed plan for integrating Canadian tide stations into your web application.

1. Canadian Tide Data API Overview

Primary API: IWLS (Integrated Water Level System)
Provider: Canadian Hydrographic Service (CHS), Department of Fisheries and Oceans (DFO)
Base URL: https://api-iwls.dfo-mpo.gc.ca/api/v1/
Format: REST API with JSON responses
Documentation: https://api-iwls.dfo-mpo.gc.ca/swagger-ui/index.html
Coverage: 800+ tidal stations across Canada
License: Free under government open data license
Key API Endpoints

## Get station list

GET /stations

## Get predictions for a station

GET /stations/{station-id}/data?time-series-code=wlp-hilo&from={start-date}&to={end-date}

## Time series codes:

- wlp: Water level predictions (continuous)
- wlp-hilo: Water level predictions (high/low only)
- wlo: Water level observations
Station Data Download
CSV URL: https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/87b08750-4180-4d31-9414-a9470eba9b42/attachments/tide and water level station.csv
Contains: Station IDs, names, coordinates, metadata

2. Key Differences: NOAA vs Canadian API

| Feature | NOAA API | Canadian IWLS API | |---------|----------|-------------------| | Station ID Format | Numeric (e.g., 9449639) | Alphanumeric ObjectID (e.g., "5cebf1df3d0f4a073c4bbb38") | | Height Units | Metric/English selectable | Metric only (meters) | | Date Format | YYYYMMDD | ISO 8601 (YYYY-MM-DDTHH:MM:SSZ) | | Datum | Multiple (MLLW, MSL, etc.) | Multiple (similar to NOAA) | | Response Format | CSV by default | JSON by default | | High/Low Parameter | interval=hilo | time-series-code=wlp-hilo |

3. Database Schema Modifications

Current Schema
CREATE TABLE tide_station_ids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT UNIQUE NOT NULL,
    place_name TEXT,
    lookup_count INTEGER NOT NULL DEFAULT 1,
    last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
)
Proposed Enhanced Schema
CREATE TABLE tide_station_ids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT UNIQUE NOT NULL,
    place_name TEXT,
    country TEXT NOT NULL DEFAULT 'USA',  -- NEW: 'USA' or 'Canada'
    api_source TEXT NOT NULL DEFAULT 'NOAA',  -- NEW: 'NOAA' or 'CHS'
    latitude REAL,  -- NEW: for mapping/location features
    longitude REAL,  -- NEW: for mapping/location features
    lookup_count INTEGER NOT NULL DEFAULT 1,
    last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
)

Migration Strategy
Add new columns with ALTER TABLE statements
Default existing records to country='USA' and api_source='NOAA'
Populate Canadian stations from CHS CSV data

4. Architecture & Code Changes

A. Core Module: API Abstraction Layer
New file: app/tide_api_adapter.py

## Abstract base class for tide APIs

class TideAPIAdapter:
    def get_predictions(station_id, year, month):
        pass
    def validate_station(station_id):
        pass
    def parse_response(response):
        pass

class NOAATideAPI(TideAPIAdapter):
    # Existing NOAA logic from get_tides.py
    
class CHSTideAPI(TideAPIAdapter):
    # New Canadian API implementation
Benefits:

Clean separation of concerns
Easy to add more countries/APIs in the future
Testable in isolation

B. Modified get_tides.py

Changes needed:

Import the adapter factory
Determine API source from database lookup
Call appropriate adapter based on api_source field
Handle different response formats transparently

## Pseudo-code structure

def download_tide_data(station_id, year, month):
    # Look up station in database
    station_info = get_station_info(station_id)
    
    # Select appropriate API adapter
    if station_info['api_source'] == 'NOAA':
        adapter = NOAATideAPI()
    elif station_info['api_source'] == 'CHS':
        adapter = CHSTideAPI()
    
    # Get predictions (unified interface)
    predictions = adapter.get_predictions(station_id, year, month)
    
    # Convert to standard format for pcal
    return convert_to_csv(predictions)

C. Database Module Updates

Modified: app/database.py

Add functions:

def get_station_info(station_id):
    """Get full station metadata including api_source"""
    
def import_canadian_stations_from_csv():
    """Import Canadian stations from CHS CSV"""
    
def search_stations_by_country(query, country='USA'):
    """Filter search by country"""
D. UI/UX Enhancements
Modified: app/templates/index.html

Country selector in search form:

<select name="country">
  <option value="USA">USA</option>
  <option value="Canada">Canada</option>
</select>
Visual indicators in autocomplete:

Point Roberts, WA 🇺🇸
Vancouver, BC 🇨🇦
Grouped search results:

Show country in station search results
Group popular stations by country
E. Routes Updates
Modified: app/routes.py

Update /api/search_stations to accept country parameter
Update /api/popular_stations to group by country
Add validation for Canadian station ID format

5. Implementation Phases

Phase 1: Data Foundation (Week 1)

Download Canadian station CSV from CHS

Create database migration script

Add [object Object], [object Object], [object Object], [object Object] columns

Import Canadian stations into database

Update [object Object] with new query functions
Deliverable: Database with both USA and Canadian stations

Phase 2: API Adapter Layer (Week 1-2)

Create [object Object] with base class

Implement [object Object] (refactor existing code)

Implement [object Object] for Canadian data

Write unit tests for both adapters

Handle error cases (station not found, API timeout, etc.)
Deliverable: Working API abstraction layer

Phase 3: Integration (Week 2)

Modify [object Object] to use adapter pattern

Update station lookup logic in [object Object]

Handle different date/ID formats

Test PDF generation with Canadian stations
Deliverable: Working backend for both countries

Phase 4: UI Updates (Week 2-3)

Add country selector to search form

Update autocomplete to show country flags/labels

Modify popular stations display for dual-country support

Update error messages for Canadian stations

Add validation for Canadian station IDs
Deliverable: User-friendly multi-country interface

Phase 5: Testing & QA (Week 3)

Test with 10+ Canadian stations

Verify PDF calendar formatting

Test edge cases (leap years, timezone handling)

Performance testing with both APIs

Cross-browser testing
Deliverable: Verified, production-ready feature

Phase 6: Documentation & Deployment (Week 3-4)

Update [object Object] with new architecture

Add Canadian stations to README examples

Update CapRover deployment (no changes needed)

Monitor API usage and error rates

User acceptance testing
Deliverable: Live production deployment

6. Technical Implementation Details

A. Canadian API Data Fetcher

class CHSTideAPI(TideAPIAdapter):
    BASE_URL = "https://api-iwls.dfo-mpo.gc.ca/api/v1"
    
    def get_predictions(self, station_id, year, month):
        """Fetch tide predictions from CHS IWLS API"""
        # Calculate date range
        start_date = f"{year}-{month:02d}-01T00:00:00Z"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day}T23:59:59Z"
        
        # Build request
        url = f"{self.BASE_URL}/stations/{station_id}/data"
        params = {
            "time-series-code": "wlp-hilo",
            "from": start_date,
            "to": end_date
        }
        
        # Make request
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise APIError(f"CHS API error: {response.status_code}")
        
        # Parse JSON response
        data = response.json()
        
        # Convert to CSV format for pcal compatibility
        return self._convert_to_csv(data)
    
    def _convert_to_csv(self, json_data):
        """Convert CHS JSON to NOAA-compatible CSV format"""
        # Parse JSON and create CSV with columns:
        # Date Time, Prediction, Type
        # 2024-06-01 03:45, 2.3, H
        # ...
B. Station ID Mapping

Canadian station IDs are MongoDB ObjectIDs (24-character hex strings), while NOAA uses numeric IDs. The database will store both formats:

## USA example

station_id = "9449639"
api_source = "NOAA"

## Canada example  

station_id = "5cebf1df3d0f4a073c4bbb38"
api_source = "CHS"
C. Date Format Handling
def format_date_for_api(year, month, day, api_source):
    """Format date based on API requirements"""
    if api_source == "NOAA":
        return f"{year}{month:02d}{day:02d}"
    elif api_source == "CHS":
        return f"{year}-{month:02d}-{day:02d}T00:00:00Z"

7. Error Handling & Edge Cases

API-Specific Errors
NOAA: "No Predictions data was found"
CHS: HTTP 404 or empty JSON response
Solution: Unified error handling with user-friendly messages
Station ID Validation
def validate_station_id(station_id, api_source):
    if api_source == "NOAA":
        return station_id.isdigit() and len(station_id) == 7
    elif api_source == "CHS":
        return len(station_id) == 24 and is_hex(station_id)
Timezone Handling
NOAA: Uses lst_ldt (local standard/daylight time)
CHS: Uses UTC by default, local time available
Solution: Standardize on local time for calendar display

8. Testing Strategy

Unit Tests

## test_tide_api_adapters.py

def test_noaa_adapter():
    adapter = NOAATideAPI()
    data = adapter.get_predictions("9449639", 2024, 6)
    assert data is not None
    assert "Date Time" in data

def test_chs_adapter():
    adapter = CHSTideAPI()
    data = adapter.get_predictions("5cebf1df3d...", 2024, 6)
    assert data is not None
Integration Tests
Test full flow: Form submission → API call → PDF generation
Test with real station IDs from both countries
Verify PDF content matches API data
Example Test Stations
USA: 9449639 (Point Roberts, WA)
Canada: 07735 (Vancouver, BC) - need to get ObjectID

9. Deployment Considerations

Environment Variables

## .env additions (optional)

CHS_API_BASE_URL=https://api-iwls.dfo-mpo.gc.ca/api/v1
NOAA_API_BASE_URL=https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
CapRover Deployment
No changes required to captain-definition
Database migration runs automatically on startup
Consider API rate limits (may need caching)
Performance Optimizations
Caching: Cache station metadata in memory
API rate limiting: Implement exponential backoff
Parallel requests: Pre-fetch popular stations

10. Future Enhancements

Short-term
Add visual map with station pins
Support multiple months in single PDF
Email delivery of calendars
Medium-term
Support additional countries (UK, Australia, NZ)
Real-time water level observations
Tide charts/graphs in addition to calendars
Long-term
Mobile app
Subscription service for regular delivery
Commercial API for third-party integrations

11. Risk Assessment & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| CHS API changes/deprecation | High | Monitor API announcements, implement version detection |
| API rate limiting | Medium | Implement caching, respect rate limits |
| Different data quality | Medium | Add validation, show data source on PDF |
| Station ID confusion | Low | Clear UI labeling, validation |
| Database migration issues | Low | Test migration thoroughly, backup before deploy |

12. Success Metrics

Successfully generate PDFs for 10+ Canadian stations

API response time < 3 seconds for both sources

Zero crashes from invalid station IDs

User can search and select Canadian stations easily

Database contains 800+ Canadian stations

## Summary

This plan provides a comprehensive roadmap for integrating Canadian tide stations using the CHS IWLS API. The key strategy is:

API Abstraction: Create a clean adapter pattern to support multiple APIs
Database Enhancement: Add country/source metadata to existing schema
Unified Interface: Keep user experience consistent across both countries
Phased Rollout: Implement in testable increments
Estimated Timeline: 3-4 weeks for full implementation and testing

Primary Dependencies:

CHS IWLS API (free, official, well-documented)
Canadian station CSV data (publicly available)
No new external libraries required (uses existing requests package)
