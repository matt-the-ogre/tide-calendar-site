# External Integrations

**Analysis Date:** 2026-03-31

## APIs & External Services

### NOAA CO-OPS API (USA Tide Predictions)

- **Purpose:** Fetch high/low tide predictions for ~2,100 US tide stations
- **Adapter:** `app/tide_adapters.py` class `NOAAAdapter`
- **Base URL:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
- **Auth:** None (public API, no key required)
- **User-Agent:** `TideCalendarSite/1.0 (https://tidecalendar.xyz; contact@tidecalendar.xyz)`
- **Request timeout:** 30 seconds
- **Retry logic:** 3 attempts with exponential backoff (0, 2, 4 seconds) on 502/503/504 and timeouts
- **Rate limiting:** Not enforced in production; validation script uses 0.25s delay (~4 req/sec)
- **Parameters:**
  - `station`: 6-8 digit numeric station ID
  - `product`: `predictions`
  - `datum`: `MLLW`
  - `time_zone`: `lst_ldt`
  - `interval`: `hilo`
  - `units`: `metric`
  - `format`: `csv`
- **Response format:** CSV (two historical formats handled - 3-column and 4-column)
- **Station data source:** `app/tide_stations_new.csv` (~2,100 stations, imported at startup)

### CHS IWLS API (Canadian Tide Predictions)

- **Purpose:** Fetch high/low tide predictions for ~73 active Canadian tide stations
- **Adapter:** `app/tide_adapters.py` class `CHSAdapter`
- **Station sync:** `app/canadian_station_sync.py` (dynamic import on container startup)
- **Base URLs (failover, tried in order):**
  1. `https://api.iwls-sine.azure.cloud-nuage.dfo-mpo.gc.ca/api/v1` (new Azure endpoint)
  2. `https://api-iwls.dfo-mpo.gc.ca/api/v1` (legacy endpoint)
- **Auth:** None (public API, no key required)
- **User-Agent:** `TideCalendarSite/1.0 (https://tidecalendar.xyz; contact@tidecalendar.xyz)`
- **Request timeout:** 30 seconds
- **Retry logic:** 3 attempts with exponential backoff per endpoint, then failover to next endpoint
- **Endpoints used:**
  - `GET /stations` - List all stations (with `?dateStart=` and `?code=` params)
  - `GET /stations/{uuid}/data` - Fetch tide predictions (with `?time-series-code=wlp-hilo&from=&to=`)
- **Station ID resolution:** Numeric codes (4-6 digits) are resolved to UUIDs via `/stations?code=` lookup
- **Response format:** JSON array of `{eventDate, value, qcFlagCode}` objects
- **Tide type detection:** Determined algorithmically by comparing neighboring values (not in API response)
- **Filtering criteria for station sync:**
  - `operating: true`
  - `type: PERMANENT`
  - Has `wlp-hilo` in `timeSeries` array
- **Fallback:** `app/canadian_tide_stations.csv` (static CSV used when API is unavailable)

### Adapter Factory

- **Location:** `app/tide_adapters.py` function `get_adapter_for_station()`
- **Logic:** Returns `NOAAAdapter` or `CHSAdapter` based on station ID format or explicit `api_source` parameter
- **Station info lookup:** `app/database.py` function `get_station_info()` provides `api_source` field

## Data Storage

### SQLite Database

- **Engine:** Python stdlib `sqlite3` (no ORM)
- **Location:** Configurable via `DB_PATH` env var
  - Development: `app/tide_station_ids.db`
  - Production: `/data/tide_station_ids.db`
- **Client module:** `app/database.py`
- **Schema:**
  ```sql
  CREATE TABLE tide_station_ids (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      station_id TEXT UNIQUE NOT NULL,
      place_name TEXT,
      lookup_count INTEGER NOT NULL DEFAULT 1,
      last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP,
      country TEXT DEFAULT 'USA',
      api_source TEXT DEFAULT 'NOAA',
      latitude REAL,
      longitude REAL,
      province TEXT
  )
  ```
- **Schema migration:** Automatic column additions via `ALTER TABLE` on startup (`app/database.py` `init_database()`)
- **Key operations:**
  - `init_database()` - Create table and migrate schema
  - `import_stations_from_csv()` - Bulk import USA stations from CSV
  - `log_station_lookup()` - Increment usage counter for a station
  - `search_stations_by_name()` / `search_stations_by_country()` - Case-insensitive LIKE search
  - `get_popular_stations()` / `get_popular_stations_by_country()` - Top stations by lookup count

### PDF File Cache

- **Location:** `PDF_OUTPUT_DIR` env var
  - Development: `app/calendars/`
  - Production: `/data/calendars/`
- **Strategy:** File-based caching by station/year/month
- **Filename pattern:** `tide_calendar_{location}_{YYYY}_{MM}.pdf`
- **Cache invalidation:** Previous month's PDFs cleaned up on each request (`cleanup_previous_month_pdfs()` in `app/routes.py`)
- **Retention:** ~30 days (current month only)

### CSV Data Files

- **USA stations:** `app/tide_stations_new.csv` (~2,100 stations, fields: station_id, place_name)
- **Canadian stations (fallback):** `app/canadian_tide_stations.csv` (fields: station_id, place_name, province, latitude, longitude, country, api_source)

## Authentication & Identity

- **Auth Provider:** None
- **User sessions:** No login, no user accounts
- **State persistence:** Single cookie (`last_place_name`) to remember last-used station
- **API authentication:** All external APIs are public (no keys required)

## Monitoring & Observability

### Analytics

- **Plausible Analytics** (self-hosted)
  - Script: `https://plausible.mattmanuel.ca/js/script.file-downloads.outbound-links.pageview-props.revenue.tagged-events.js`
  - Domain tracking: `tidecalendar.xyz`
  - Features enabled: file downloads, outbound links, pageview props, revenue, tagged events
  - Integration point: `app/templates/base.html` line 18

### Advertising

- **Google AdSense**
  - Client ID: `ca-pub-4234134774434001`
  - Script loaded in `app/templates/base.html` line 20-21
  - Verification file: `app/static/ads.txt` (served at `/ads.txt` via `app/routes.py`)

### Health Check

- **Endpoint:** `GET /health` (`app/routes.py`)
- **Returns:** JSON with status, version, commit hash, branch, build timestamp, database connectivity
- **Status codes:** 200 (healthy), 503 (degraded/unhealthy)

### Error Tracking

- None (relies on Flask/Python logging to stdout)

### Logging

- Python `logging` module configured at INFO level
- Format: `%(levelname)s: %(message)s` (set in `app/run.py`)
- Logs to stdout (captured by Docker/CapRover)

## CI/CD & Deployment

### Hosting

- **Platform:** CapRover (Docker-based PaaS)
- **URL:** `https://tidecalendar.xyz` (production), `https://dev.tidecalendar.xyz` (development)
- **Admin:** `https://captain.mattmanuel.ca`
- **SSL:** Automatic via Let's Encrypt (managed by CapRover)
- **Reverse proxy:** CapRover handles SSL termination and proxying (443 -> 80)

### CI Pipeline

- **GitHub Actions** (`.github/workflows/playwright.yml`)
- **Trigger:** Push to `main`/`development`, PRs to `main`, daily cron at 06:00 UTC
- **Job:** `smoke-test` (runs Playwright smoke tests against production)
  - Node.js 18
  - Installs Chromium only
  - Health check against `https://www.tidecalendar.xyz/`
  - Runs `playwright.config.smoke.ts` with `BASE_URL=https://www.tidecalendar.xyz`
  - Uploads test artifacts on failure (7-day retention)

### Deployment Pipeline

- **Trigger:** Push to `main` branch
- **Mechanism:** GitHub webhook triggers CapRover automatic build and deploy
- **Build:** CapRover builds Docker image from `Dockerfile` (configured in `captain-definition`)
- **Zero-downtime deployment:** Handled by CapRover
- **Persistent data:** CapRover volume mounted at `/data` (survives deployments)

### Branch Strategy

- `development` branch -> deploys to `https://dev.tidecalendar.xyz`
- `main` branch -> deploys to `https://tidecalendar.xyz`
- PRs merge `development` into `main`

## CDN & External Resources

### Google Fonts
- DM Sans (400/500/600/700) and DM Serif Display
- Loaded via `fonts.googleapis.com` with `preconnect` in `app/templates/base.html`

### Font Awesome
- Version 6.0.0-beta3
- Loaded via `cdnjs.cloudflare.com` in `app/templates/base.html`

## SEO & Crawler Files

- **robots.txt:** `app/static/robots.txt` served at `/robots.txt` via Flask route
- **sitemap.xml:** `app/static/sitemap.xml` served at `/sitemap.xml` via Flask route
- **llms.txt:** `app/static/llms.txt` served at `/llms.txt` via Flask route (LLM crawler description)
- **ads.txt:** `app/static/ads.txt` served at `/ads.txt` via Flask route
- All served by `_serve_static_file()` helper in `app/routes.py`

## Webhooks & Callbacks

**Incoming:**
- GitHub webhook -> CapRover (triggers deployment on push to `main`)

**Outgoing:**
- None

## Sponsorship / Funding

- GitHub Sponsors: `matt-the-ogre` (`.github/FUNDING.yml`)
- Patreon: `BookofTPM` (`.github/FUNDING.yml`)

## Environment Configuration

**Required env vars (production):**
- `FLASK_APP=run.py`
- `FLASK_ENV=production`
- `FLASK_RUN_PORT=80`
- `PDF_OUTPUT_DIR=/data/calendars`

**Optional env vars:**
- `DB_PATH` - SQLite database path (default: `app/tide_station_ids.db`)
- `TOP_STATIONS_COUNT` - Number of popular stations to display (default: 10)

**Secrets:**
- None required (all external APIs are public)

---

*Integration audit: 2026-03-31*
