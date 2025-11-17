# Tide Calendar Generator - Frequently Asked Questions

## Table of Contents
- [General Questions](#general-questions)
- [Station Search](#station-search)
- [Canadian Stations](#canadian-stations)
- [PDF Calendars](#pdf-calendars)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)

---

## General Questions

### What is the Tide Calendar Generator?

The Tide Calendar Generator is a free web application that creates downloadable PDF tide calendars for coastal locations across the United States and Canada. Simply select a tide station, choose your desired month and year, and get a printable calendar showing high and low tides for that period.

### Is this service free?

Yes, the Tide Calendar Generator is completely free to use. It's provided as a public service using official tide prediction data from NOAA (United States) and the Canadian Hydrographic Service.

### How accurate are the tide predictions?

The tide predictions are sourced directly from official government agencies:
- **USA Stations**: NOAA Center for Operational Oceanographic Products and Services (CO-OPS)
- **Canadian Stations**: Canadian Hydrographic Service (CHS) Integrated Water Level System (IWLS)

These predictions are as accurate as the official government forecasts and are suitable for general planning purposes. However, actual tide heights and times can vary due to weather conditions, atmospheric pressure, and other factors.

### Can I use these tide calendars for navigation?

While the tide predictions are from official sources, this tool is intended for general planning and informational purposes only. For critical navigation decisions, always consult official nautical charts and local tide tables.

---

## Station Search

### How do I find a tide station?

There are three ways to find a tide station:

1. **Search by place name** (Recommended):
   - Start typing a city, harbor, or coastal location name
   - Use the autocomplete dropdown to select from matching stations
   - Example: "Vancouver", "Seattle", "Halifax"

2. **Filter by country**:
   - Use the country radio buttons (USA, Canada, or All) to narrow your search
   - Popular stations for the selected country will be displayed

3. **Direct station ID** (Advanced):
   - If you know the station ID, enter it directly
   - USA stations: 7-digit numbers (e.g., 9449639)
   - Canadian stations: Alphanumeric codes displayed in search results

### Why can't I find my local beach?

Not all beaches and coastal areas have tide stations. Tide stations are typically located at:
- Commercial harbors and ports
- Major bays and inlets
- Popular recreational areas
- Locations with significant tidal variation

If your specific location isn't listed, find the nearest available station. Tide times are generally similar for locations within 10-20 miles along the same coastline.

### What does "Point Roberts, WA" mean vs just "Seattle"?

Station names follow this format: `City/Location, State/Province`

Some stations include additional detail for clarity:
- "Port Allen, Hanapepe Bay, Kauai Island, HI" - Multiple geographic identifiers
- "Vancouver, British Columbia" - City and province
- "Miami Beach, FL" - Common place name

The autocomplete shows the full official name to help you identify the exact location.

### How do I search for Canadian stations?

1. Select the "Canada" radio button to filter only Canadian stations
2. Start typing a Canadian city or location name
3. Canadian stations will show with their province (e.g., "Vancouver, British Columbia")
4. You can also select "All" to see both US and Canadian stations together

---

## Canadian Stations

### How many Canadian tide stations are available?

The application provides access to 73+ active Canadian tide stations with high/low tide predictions, covering:
- British Columbia
- Atlantic provinces (Nova Scotia, New Brunswick, Newfoundland and Labrador, Prince Edward Island)
- Quebec
- Arctic regions

### What's the difference between US and Canadian stations?

| Feature | USA Stations | Canadian Stations |
|---------|-------------|-------------------|
| Data Source | NOAA CO-OPS | CHS IWLS |
| Number of Stations | 2,100+ | 73+ (with high/low predictions) |
| Height Units | Meters | Meters |
| Station ID Format | 7-digit numeric | Alphanumeric |
| Predictions | High/Low tides | High/Low tides |

Both use metric units (meters) for tide heights and provide the same calendar format.

### Why are there fewer Canadian stations than US stations?

The application only includes Canadian stations that provide high/low tide predictions (time-series-code: wlp-hilo). While Canada operates 800+ water level stations, not all provide the high/low prediction data needed for tide calendars.

The 73+ stations included cover all major harbors, ports, and coastal population centers across Canada.

### Can I request a Canadian station to be added?

Canadian stations are imported automatically from the Canadian Hydrographic Service API. If a station is listed as "operating" with high/low tide predictions in the CHS system, it will appear in our database after the next update.

If you believe a station should be available but isn't listed, please check the [CHS IWLS website](https://www.isdm-gdsi.gc.ca/isdm-gdsi/twl-mne/index-eng.html) to verify it provides high/low predictions.

---

## PDF Calendars

### What information is shown on the tide calendars?

Each PDF calendar includes:
- **Month and year** at the top
- **Daily grid** showing each day of the month
- **High tide times and heights** (H markers)
- **Low tide times and heights** (L markers)
- **Asterisks (*)** marking very low tides (< 0.3m)
- **Station name and ID** in the calendar title

### Why do some low tides have asterisks?

Low tides below 0.3 meters (approximately 1 foot) are marked with asterisks (*) to highlight exceptionally low tide events. These are often the best times for:
- Beach exploration
- Tide pooling
- Clamming and shellfish harvesting
- Accessing areas normally underwater

### What time zone are the tide times shown in?

Tide times are shown in the **local time zone** for that station's location. The times are automatically adjusted for:
- Pacific Time (US and Canadian west coast)
- Atlantic Time (Canadian east coast)
- Eastern, Central, Mountain time zones (as applicable)
- Daylight Saving Time (when in effect)

You don't need to do any time conversions - the times shown are correct for the local area.

### How do I read the tide heights?

Tide heights are shown in **meters** relative to the station's datum (reference point):
- **Positive values** (e.g., 2.5m): Tide is above the reference level
- **Negative values** (e.g., -0.5m): Tide is below the reference level
- **Higher numbers**: Higher water levels
- **Lower numbers**: Lower water levels

Most stations use Mean Lower Low Water (MLLW) as the datum, which is the average of the lower of the two daily low tides.

### Can I generate calendars for future years?

Yes, you can generate tide calendars for any year from 2000 to 2030. However, predictions are most accurate within the current year and near-term future (1-2 years ahead).

### Why does my PDF take a few seconds to generate?

The application:
1. Fetches tide prediction data from NOAA or CHS APIs
2. Processes the data to extract high/low tides
3. Generates a calendar using the pcal utility
4. Converts it to PDF format

The first time a particular station/month/year is requested, it takes 5-15 seconds. After that, the PDF is cached and downloads instantly.

### Can I download multiple months at once?

Currently, the application generates one month at a time. To get multiple months:
1. Generate the first month and download the PDF
2. Change the month selection
3. Generate and download the next month
4. Repeat as needed

Each PDF is saved with a unique filename including the location and date, so they won't overwrite each other.

---

## Troubleshooting

### I get an error saying "Station ID must be numeric"

This error occurs if:
- You're using a Canadian station ID format with the USA filter selected
- You've entered text instead of numbers for a US station

**Solution**: Make sure the country filter matches your station type, or use the autocomplete search to select the station.

### The error page says "Tide station not found"

This can happen if:
- The station ID doesn't exist in the database
- The station has been decommissioned
- There was a typo in the station ID

**Solution**:
1. Use the autocomplete search instead of entering a station ID directly
2. Check the popular stations list for nearby locations
3. Try searching by city or location name

### My autocomplete search returns no results

Possible causes:
- Typo in the search term
- Location doesn't have a tide station
- Country filter is limiting results

**Solution**:
1. Check your spelling
2. Try searching for a nearby larger city or harbor
3. Change the country filter to "All" to see all matching stations
4. Try a broader search (e.g., "Victoria" instead of "Victoria Harbour")

### The PDF download failed or is empty

This is rare but can happen if:
- The NOAA or CHS API is temporarily unavailable
- Network connectivity issues
- The station doesn't have prediction data for the requested time period

**Solution**:
1. Try generating the calendar again (the app retries failed API calls automatically)
2. Try a different month or year
3. Check if the station is still active by searching for it in the autocomplete
4. If the problem persists, try a different station to verify the service is working

### Popular stations table is empty

If no popular stations appear:
- The application may be starting up and loading station data
- The database may be initializing

**Solution**: Refresh the page after 10-20 seconds. The popular stations should appear once the database is ready.

### I clicked a popular station but nothing happened

This may indicate:
- JavaScript is disabled in your browser
- A browser extension is blocking scripts
- Slow network connection

**Solution**:
1. Make sure JavaScript is enabled
2. Try disabling ad blockers temporarily
3. Manually enter the station name in the search box

---

## Technical Details

### What technology powers this application?

**Backend:**
- Python Flask web framework
- SQLite database for station tracking
- pcal calendar generation utility
- Ghostscript for PDF creation

**APIs:**
- NOAA CO-OPS API for US tide predictions
- CHS IWLS API for Canadian tide predictions

**Frontend:**
- HTML5, CSS3, JavaScript
- Responsive design for mobile devices
- Plausible Analytics (privacy-friendly, no cookies)

### How often is the station data updated?

- **Canadian stations**: Imported automatically from the CHS API at application startup
- **USA stations**: Updated periodically from NOAA sources
- **Tide predictions**: Fetched on-demand when you generate a calendar

### Where is my data stored?

The application stores:
- **Station lookup counts**: Used to show popular stations (no personal data)
- **Generated PDFs**: Cached for 30 days to improve performance
- **No user accounts or personal information**

We don't track or store any personal information. Analytics are privacy-friendly and anonymous.

### Can I run this application myself?

Yes! The code is open source under the GNU GPL v3 license. Visit the [GitHub repository](https://github.com/matt-the-ogre/tide-calendar-site) for:
- Complete source code
- Setup instructions
- Docker deployment guides
- Developer documentation

### How can I report a bug or request a feature?

Please open an issue on the [GitHub Issues page](https://github.com/matt-the-ogre/tide-calendar-site/issues) with:
- Description of the bug or feature request
- Steps to reproduce (for bugs)
- Station ID and date if applicable
- Browser and device information

### Why do you show ads?

The small ads help cover server hosting costs while keeping the service free for everyone. They're minimal and don't interfere with calendar generation or downloads.

---

## Still Have Questions?

If your question isn't answered here:
1. Check the [User Guide](USER_GUIDE.md) for detailed tutorials
2. Review the [README](README.md) for technical information
3. Open an issue on [GitHub](https://github.com/matt-the-ogre/tide-calendar-site/issues)

---

*Last updated: November 2024*
