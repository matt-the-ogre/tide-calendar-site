# Tide Calendar Generator - User Guide

A comprehensive guide to generating printable tide calendars for US and Canadian coastal locations.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Understanding the Interface](#understanding-the-interface)
3. [Finding Your Tide Station](#finding-your-tide-station)
4. [Using the Country Filter](#using-the-country-filter)
5. [Generating Your Tide Calendar](#generating-your-tide-calendar)
6. [Reading Your Tide Calendar](#reading-your-tide-calendar)
7. [Popular Stations Feature](#popular-stations-feature)
8. [Advanced Features](#advanced-features)
9. [Tips and Best Practices](#tips-and-best-practices)
10. [Examples by Region](#examples-by-region)

---

## Quick Start

**Generate your first tide calendar in 30 seconds:**

1. Visit [tidecalendar.xyz](https://tidecalendar.xyz)
2. Start typing your coastal city name in the search box
3. Select your location from the dropdown
4. Choose the month and year
5. Click "Generate and download the PDF"
6. Your calendar will download automatically

That's it! Read on for detailed instructions and advanced features.

---

## Understanding the Interface

### Main Components

When you load the application, you'll see:

**1. Search Box**
- Large text input field with placeholder text
- Type to search for tide stations by name
- Shows autocomplete suggestions as you type
- Remembers your last successful search

**2. Country Filter (Radio Buttons)**
- Three options: USA, Canada, All
- Filters both search results and popular stations
- Default: "All" (shows all stations)

**3. Date Selection**
- **Month dropdown**: Select January through December
- **Year dropdown**: Choose from 2000-2030
- Default: Current month and year

**4. Generate Button**
- Large blue button to create your calendar
- Text: "Generate and download the PDF"
- Triggers PDF generation and automatic download

**5. Popular Stations Table**
- Shows most frequently requested stations
- Updates based on country filter selection
- Click any station name for instant generation (current month only)
- Shows station ID, location, and number of requests

### Mobile vs Desktop

The interface is fully responsive:
- **Desktop**: All elements in a comfortable multi-column layout
- **Tablet**: Adapts to medium screen sizes
- **Mobile**: Single column, touch-friendly buttons and dropdowns

---

## Finding Your Tide Station

### Method 1: Autocomplete Search (Recommended)

**Step-by-step:**

1. **Click in the search box** labeled "Enter tide station place name or station ID"

2. **Start typing** your location name:
   - City name: "Seattle", "Vancouver", "Halifax"
   - Harbor name: "Pearl Harbor", "Sydney Harbour"
   - Geographic feature: "Point Roberts", "Bay of Fundy"

3. **Watch the dropdown appear** with matching stations

4. **Navigate the suggestions:**
   - **Mouse**: Click on the station you want
   - **Keyboard**: Use arrow keys (↑/↓) to highlight, press Enter to select
   - **Touch**: Tap the desired station on mobile

5. **The selected station name fills the search box** automatically

**Autocomplete Features:**
- Searches as you type (after 2+ characters)
- Matches anywhere in the station name
- Shows up to 10 matching stations
- Displays full location details (city, state/province)
- Fast response with local caching

**Example Searches:**

| You Type | Suggested Stations |
|----------|-------------------|
| "seattle" | Seattle, WA; Seattle (offshore), WA |
| "van" | Vancouver, British Columbia; Vanderbilt Reef, AK |
| "miami" | Miami Beach, FL; Miami Harbor, FL |
| "victoria" | Victoria, British Columbia; Victoria Harbour, British Columbia |

### Method 2: Popular Stations

**Step-by-step:**

1. **Scroll down** to the "Popular Stations" table

2. **Browse the list** of frequently requested locations

3. **Click any station name** to instantly generate the current month's calendar

**Benefits:**
- No typing required
- See what other users are requesting
- Quick access to major harbors and ports
- One-click generation for current month

### Method 3: Direct Station ID (Advanced)

If you know the specific station ID:

1. **Enter the station ID** directly in the search box
   - USA: 7-digit number (e.g., `9449639`)
   - Canada: Alphanumeric code (shown in search results)

2. **No autocomplete needed** - just type the ID

3. **Proceed to generate** your calendar

**Where to find station IDs:**
- NOAA website: [tidesandcurrents.noaa.gov/stations.html](https://tidesandcurrents.noaa.gov/stations.html)
- CHS website: [isdm-gdsi.gc.ca/isdm-gdsi/twl-mne/index-eng.html](https://www.isdm-gdsi.gc.ca/isdm-gdsi/twl-mne/index-eng.html)
- Previous calendar PDF titles
- Bookmarked from past searches

---

## Using the Country Filter

The country filter helps you find stations more quickly by narrowing your search.

### USA Filter

**When to use:**
- Searching for US coastal locations
- Want to see only NOAA stations
- Focusing on Pacific, Atlantic, Gulf, or Alaska coasts

**What it does:**
- Limits autocomplete results to US stations
- Shows only US stations in popular stations table
- Filters out Canadian results

**Example stations shown:**
- Point Roberts, WA
- Seattle, WA
- San Francisco, CA
- Miami Beach, FL
- Boston, MA

### Canada Filter

**When to use:**
- Searching for Canadian coastal locations
- Want to see only CHS stations
- Focusing on British Columbia or Atlantic provinces

**What it does:**
- Limits autocomplete results to Canadian stations
- Shows only Canadian stations in popular stations table
- Filters out US results

**Example stations shown:**
- Vancouver, British Columbia
- Victoria, British Columbia
- Halifax, Nova Scotia
- St. John's, Newfoundland and Labrador
- Quebec, Quebec

### All Filter (Default)

**When to use:**
- Not sure which country your station is in
- Searching border areas (e.g., Puget Sound / Georgia Strait)
- Want maximum search results

**What it does:**
- Shows all matching stations regardless of country
- Displays both US and Canadian stations in popular stations
- Provides the widest search results

**Best for:**
- First-time users
- Unfamiliar locations
- Exploratory searching

### Changing the Filter

1. **Click a different radio button** (USA, Canada, or All)
2. **The change takes effect immediately**:
   - Popular stations table updates
   - Future autocomplete searches are filtered
3. **Your selection is remembered** for the current session

---

## Generating Your Tide Calendar

### Step-by-Step Calendar Generation

**1. Verify Your Station**
- Confirm the search box shows the correct station name
- Double-check you selected the right location from autocomplete

**2. Select Your Month**
- Click the "Month" dropdown
- Choose from January through December
- Default is the current month

**3. Select Your Year**
- Click the "Year" dropdown
- Choose from 2000 to 2030
- Default is the current year
- Predictions are most accurate for current year and 1-2 years ahead

**4. Click Generate**
- Click the large blue "Generate and download the PDF" button
- Wait 5-15 seconds for first-time generation (faster for cached calendars)
- The PDF will download automatically when ready

**5. Download Completes**
- Your browser downloads the PDF file
- Filename format: `tide_calendar_[Location]_[YYYY]_[MM].pdf`
- Example: `tide_calendar_Point_Roberts_WA_2024_11.pdf`

### What Happens When You Click Generate

Behind the scenes:

1. **Validation**: Application checks your inputs
2. **API Request**: Fetches tide predictions from NOAA or CHS
3. **Processing**: Extracts high and low tide times/heights
4. **Calendar Creation**: Generates calendar grid with tide data
5. **PDF Conversion**: Creates downloadable PDF
6. **Caching**: Saves the PDF for faster future requests
7. **Download**: PDF is sent to your browser

**First-time generation**: 5-15 seconds
**Cached calendars**: Instant download (<1 second)

### Understanding the Wait

**Normal generation time:**
- New calendars: 5-15 seconds
- Cached calendars: <1 second
- Canadian stations: May take slightly longer (API differences)

**If it takes longer than 30 seconds:**
- Check your internet connection
- The API might be experiencing high traffic
- Try again - the app has automatic retry logic

**Progress indicators:**
- Button may show "Processing..." (depending on browser)
- Browser download indicator appears when ready
- Page remains responsive - you can start a new search

---

## Reading Your Tide Calendar

### Calendar Layout

Your PDF calendar follows this format:

```
TIDE CALENDAR - [Station Name] - [Month] [Year]

[Standard monthly calendar grid]

Each day shows:
  H 06:45  2.8m  ← High tide at 6:45 AM, height 2.8 meters
  L 12:30  0.5m  ← Low tide at 12:30 PM, height 0.5 meters
  H 18:15  3.1m  ← High tide at 6:15 PM, height 3.1 meters
  L 00:20 -0.2m* ← Low tide at 12:20 AM, height -0.2m (very low)
```

### Tide Markers

**H = High Tide**
- Water level at local maximum
- Best time for boat launching (deep draft vessels)
- Higher water access to beaches and harbors

**L = Low Tide**
- Water level at local minimum
- Best time for beach exploration, tide pooling
- Accessing areas usually underwater

**Asterisk (*) = Very Low Tide**
- Tides below 0.3 meters
- Exceptional low water events
- Prime time for:
  - Clamming and shellfish harvesting
  - Tide pool exploration
  - Beachcombing
  - Accessing normally submerged areas

### Time Interpretation

**All times are in local time for the station's location:**
- Automatically adjusted for the correct time zone
- Includes Daylight Saving Time when in effect
- No conversion needed - use times as shown

**24-hour vs 12-hour format:**
- Times are shown in 24-hour format for clarity
- 06:45 = 6:45 AM
- 18:15 = 6:15 PM
- 00:20 = 12:20 AM (after midnight)

### Height Interpretation

**Heights are in meters:**
- Measured relative to station datum (usually Mean Lower Low Water)
- Positive values: Water level above datum
- Negative values: Water level below datum
- Higher numbers = deeper water

**Quick reference:**
- 0.3m ≈ 1 foot
- 1.0m ≈ 3.3 feet
- 2.0m ≈ 6.6 feet
- 3.0m ≈ 9.8 feet

**Example tide heights:**

| Height | Interpretation |
|--------|---------------|
| 3.5m | High tide, deep water |
| 2.0m | Moderate high tide |
| 0.5m | Low-ish water |
| 0.0m | At the datum reference |
| -0.3m* | Very low tide (marked with *) |
| -0.8m* | Extremely low tide |

### Understanding Negative Heights

Negative heights are **normal and expected**:
- The datum (0.0m) is typically Mean Lower Low Water (MLLW)
- MLLW is the average of the lower of the two daily low tides
- About half of low tides will be below MLLW (negative)
- More negative = better for tide pooling and beach access

### Tidal Patterns

**Semi-diurnal tides** (most common):
- Two high tides per day
- Two low tides per day
- Approximately 6 hours between high and low
- Pattern: H → L → H → L (repeats ~every 12.4 hours)

**Mixed tides** (Pacific coast):
- Two highs and two lows per day
- But significantly different heights
- "Higher high", "lower high", "higher low", "lower low"
- Common in Seattle, San Francisco, Alaska, British Columbia

**Diurnal tides** (rare):
- One high and one low per day
- Found in Gulf of Mexico locations
- Less common in this application

### Using Your Calendar

**For recreation:**
- **Beach walking**: Plan around low tides
- **Tide pooling**: Go during the lowest tides (marked with *)
- **Swimming**: Higher tides provide deeper water
- **Fishing**: Research your target species (some prefer incoming/outgoing tides)

**For boating:**
- **Launch timing**: High tides for shallow ramps
- **Navigation**: Plan passages through shallow areas near high tide
- **Anchoring**: Account for tidal range when setting anchor rode

**For photography:**
- **Sunrise/sunset with tides**: Coordinate with tide times
- **Reflections**: Lower tides expose more reflective sand
- **Waves and rocks**: Higher tides create more dramatic scenes

---

## Popular Stations Feature

### How It Works

The "Popular Stations" table shows tide stations that other users request most frequently:

1. **Ranking**: Based on number of calendar generation requests
2. **Country-filtered**: Updates based on your country filter selection
3. **Real-time**: Reflects actual usage patterns
4. **Top locations**: Shows the most-used stations

### Using Popular Stations

**Quick generation:**

1. Find an interesting station in the table
2. Click the station name
3. Calendar for the **current month** generates instantly
4. No need to select month/year - uses current date

**Why use popular stations:**
- Discover major harbors and popular locations
- Quick access without typing
- See where other users are located
- Often includes well-maintained, reliable stations

**Table columns:**

| Column | Meaning |
|--------|---------|
| Station ID | NOAA/CHS identifier (for reference) |
| Location | Full place name with state/province |
| Requests | Number of times this station has been requested |

### Country Filter Integration

The popular stations table updates automatically:

- **USA selected**: Shows top US stations (e.g., Seattle, Miami, Boston)
- **Canada selected**: Shows top Canadian stations (e.g., Vancouver, Halifax)
- **All selected**: Shows top 10 across both countries

This helps you discover popular locations in your region of interest.

---

## Advanced Features

### Remembering Your Last Location

**How it works:**
- The app saves your last successful station search
- When you return, the search box pre-fills with your last location
- Convenient for checking multiple months for the same location

**To use:**
1. Generate a calendar for any station
2. Close the browser or navigate away
3. Return to the site
4. Your last station will be pre-filled in the search box
5. Just change the month/year and regenerate

### Generating Multiple Months

**To create a series of calendars:**

1. Generate the first month (e.g., January 2025)
2. Download completes with unique filename
3. Change the month dropdown to February
4. Click generate again
5. Repeat for each month needed

**File naming:**
- Each PDF has a unique filename with location and date
- Files won't overwrite each other
- Easy to organize and print

**Example filenames:**
- `tide_calendar_Seattle_WA_2025_01.pdf`
- `tide_calendar_Seattle_WA_2025_02.pdf`
- `tide_calendar_Seattle_WA_2025_03.pdf`

### Caching for Speed

**How caching works:**
- Generated PDFs are cached for 30 days
- First request: 5-15 seconds
- Subsequent requests: <1 second (instant)
- Applies to the same station/month/year combination

**Benefits:**
- Much faster for popular stations and months
- Reduces load on government APIs
- Better user experience

**What's cached:**
- Completed PDF files
- Station search results (temporary)
- Popular stations list (updated periodically)

### Keyboard Shortcuts

**Search box autocomplete:**
- `↓` (Down arrow): Move to next suggestion
- `↑` (Up arrow): Move to previous suggestion
- `Enter`: Select highlighted suggestion
- `Esc`: Close autocomplete dropdown
- `Tab`: Accept first suggestion and move to next field

**Form navigation:**
- `Tab`: Move between search, month, year, generate button
- `Shift+Tab`: Move backwards through form
- `Enter`: Submit form (when on generate button)

---

## Tips and Best Practices

### Finding the Right Station

**If your exact location isn't listed:**
1. Search for the nearest major city or harbor
2. Try the county name or geographic feature
3. Use the "All" country filter for maximum results
4. Check the popular stations for nearby locations

**Border areas (US/Canada):**
- Puget Sound and Georgia Strait region: Try both USA and Canada filters
- Use "All" to see stations on both sides of the border
- Tide patterns may differ significantly between nearby stations

### Choosing a Time Period

**For current planning:**
- Current month and next 1-2 months are most accurate
- Weather patterns can affect actual tide times/heights
- Government predictions are updated periodically

**For historical research:**
- Past years are available (2000-2030 range)
- Good for comparing seasonal patterns
- Historical predictions, not observed data

**For advance planning:**
- Up to 6 years in advance
- Useful for long-term event planning
- Less accurate the further out you go

### Understanding Tide Variations

**Factors that affect tides:**
- **Moon phase**: Spring tides (new/full moon) are higher/lower
- **Season**: Some locations have seasonal patterns
- **Weather**: Storms and pressure systems can modify tides
- **Wind**: Sustained winds can raise or lower water levels

**These calendars show:**
- Predicted astronomical tides only
- Do not include weather effects
- Best-case scenario for planning

### Printing Your Calendars

**Recommended settings:**
- Paper size: Letter (8.5" × 11") or A4
- Orientation: Portrait (vertical)
- Color: Black and white is fine (calendars are monochrome)
- Scale: 100% (fit to page)

**For best results:**
- Use standard printer paper
- Select "actual size" or 100% scale
- Avoid "fit to page" which may distort the calendar
- Print quality: Standard or draft is sufficient

### Bookmarking Stations

**Browser bookmarks:**
- Generate a calendar for your favorite station
- Bookmark the result page if your browser supports it
- Note the station ID for quick future reference

**Keeping a reference list:**
- Write down station IDs for frequent locations
- Example: "My local beach: 9449639"
- Speeds up future searches

---

## Examples by Region

### Pacific Northwest (USA)

**Seattle, Washington:**
1. Type "seattle" in the search box
2. Select "Seattle, WA" from dropdown
3. Select your desired month and year
4. Generate calendar

**Characteristics:**
- Mixed semidiurnal tides (two unequal highs/lows daily)
- Large tidal range (up to 4+ meters)
- Lower low tides excellent for beachcombing

**Popular stations in region:**
- Seattle, WA (9447130)
- Point Roberts, WA (9449639)
- Port Townsend, WA (9444900)
- Neah Bay, WA (9443090)

### Pacific Northwest (Canada)

**Vancouver, British Columbia:**
1. Select "Canada" filter (optional)
2. Type "vancouver" in the search box
3. Select "Vancouver, British Columbia" from dropdown
4. Select month and year
5. Generate calendar

**Characteristics:**
- Similar patterns to Seattle (same tidal basin)
- Mixed tides with significant range
- Strong tidal currents in narrow passages

**Popular stations in region:**
- Vancouver, British Columbia
- Victoria, British Columbia
- Prince Rupert, British Columbia
- Campbell River, British Columbia

### Atlantic Coast (USA)

**Boston, Massachusetts:**
1. Type "boston" in search box
2. Select "Boston, MA"
3. Choose month and year
4. Generate

**Characteristics:**
- Semidiurnal tides (two equal highs/lows daily)
- Moderate to large tidal range
- More regular patterns than Pacific coast

**Popular stations in region:**
- Boston, MA (8443970)
- Portland, ME (8418150)
- Newport, RI (8452660)
- New York Harbor, NY (8518750)

### Atlantic Coast (Canada)

**Halifax, Nova Scotia:**
1. Select "Canada" filter (optional)
2. Type "halifax"
3. Select "Halifax, Nova Scotia"
4. Choose date and generate

**Characteristics:**
- Semidiurnal tides
- Some of the highest tides in the world (Bay of Fundy region)
- Can exceed 10+ meters in extreme locations

**Popular stations in region:**
- Halifax, Nova Scotia
- St. John's, Newfoundland and Labrador
- Saint John, New Brunswick (near Bay of Fundy)
- Charlottetown, Prince Edward Island

### Gulf Coast (USA)

**Example: Galveston, Texas:**
1. Type "galveston"
2. Select your station
3. Generate calendar

**Characteristics:**
- Smaller tidal ranges (often <1 meter)
- More influenced by wind and weather
- Some locations have diurnal (once daily) tides

### Alaska (USA)

**Juneau, Alaska:**
1. Type "juneau"
2. Select from available stations
3. Generate

**Characteristics:**
- Highly variable depending on location
- Can have very large ranges
- Complex patterns due to fjord geography

### California (USA)

**San Francisco, California:**
1. Type "san francisco"
2. Multiple stations available - choose the specific location
3. Generate calendar

**Characteristics:**
- Mixed semidiurnal tides
- Moderate tidal ranges
- Significant differences between Bay and outer coast

---

## Troubleshooting

For troubleshooting help, see the [FAQ](FAQ.md#troubleshooting) section.

Common issues covered:
- Station not found errors
- Autocomplete not working
- PDF generation failures
- Empty results

---

## Next Steps

Now that you know how to use the Tide Calendar Generator:

1. **Try it out**: Generate a calendar for your local area
2. **Explore stations**: Use the country filter to discover new locations
3. **Plan activities**: Use your calendars for beach trips, boating, fishing
4. **Share**: Tell others about this free tool
5. **Provide feedback**: Report bugs or suggest features on [GitHub](https://github.com/matt-the-ogre/tide-calendar-site/issues)

**Happy tide watching!**

---

## Additional Resources

- **FAQ**: [FAQ.md](FAQ.md) - Frequently asked questions
- **README**: [README.md](README.md) - Technical documentation
- **NOAA Tides**: [tidesandcurrents.noaa.gov](https://tidesandcurrents.noaa.gov)
- **CHS Water Levels**: [isdm-gdsi.gc.ca/isdm-gdsi/twl-mne/index-eng.html](https://www.isdm-gdsi.gc.ca/isdm-gdsi/twl-mne/index-eng.html)

---

*Last updated: November 2024*
