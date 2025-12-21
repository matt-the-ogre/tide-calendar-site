# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (required for PDF generation)
# Linux: sudo apt-get install -y pcal ghostscript
# macOS: brew install pcal ghostscript

# Run the Flask app locally (development uses port 5001)
cd app
flask run --host 0.0.0.0 --port 5001
```

### Docker Development
```bash
# Build Docker image
docker build -t tide-calendar-app .

# Run with Docker (maps local port 5001 to container port 80)
docker run -p 5001:80 tide-calendar-app

# Run with Docker Compose (configured for local dev on port 5001)
docker-compose up --build
```

### Environment Variables
Create `.env` file with:
```
FLASK_APP=run.py
FLASK_ENV=development  # or production
FLASK_RUN_PORT=5001  # local dev; production uses port 80
PDF_OUTPUT_DIR=/data/calendars  # production only; local dev uses app/calendars
TOP_STATIONS_COUNT=10  # number of popular stations to display (default: 10)
```

### CapRover Deployment
This application is deployed to CapRover at https://captain.mattmanuel.ca

**Deployment Configuration:**
- `captain-definition` file specifies Dockerfile-based deployment
- Application runs on port 80 (CapRover standard)
- Automatic deployments via GitHub webhook on pushes to `main` branch
- CapRover handles SSL/TLS certificates via Let's Encrypt
- CapRover provides reverse proxy (no nginx configuration needed)

**Environment Variables in CapRover:**
```
FLASK_APP=run.py
FLASK_ENV=production
FLASK_RUN_PORT=80
PDF_OUTPUT_DIR=/data/calendars
TOP_STATIONS_COUNT=10
```

**Persistent Data:**
- SQLite database: `/data/tide_station_ids.db`
- Generated PDF calendars: `/data/calendars/`
- Configure persistent volume in CapRover: Path in App = `/data`
- This preserves the database and cached PDFs across deployments and updates

**Manual Deployment:**
1. Push changes to `main` branch
2. GitHub webhook triggers CapRover deployment automatically
3. CapRover builds Docker image and deploys with zero downtime

**Initial Setup (already configured):**
- Created CapRover app at https://captain.mattmanuel.ca
- Configured custom domain: tidecalendar.xyz
- Enabled HTTPS with automatic Let's Encrypt certificate
- Set up GitHub webhook for automatic deployments

## Architecture Overview

### Core Components
- **Flask Web Application**: Serves tide calendar generation interface with form validation
- **Tide Data Fetcher**: `get_tides.py` retrieves NOAA/CHS tide data and generates PDF calendars
- **Database Module**: `database.py` centralized SQLite operations for station usage tracking
- **Canadian Station Sync**: `canadian_station_sync.py` dynamically imports Canadian stations from CHS API
- **Tide Adapters**: `tide_adapters.py` provides unified interface for NOAA and CHS APIs with retry logic
- **PDF Generation Pipeline**: Uses `pcal` and `ghostscript` for calendar creation

### Repository Structure
```
├── app/                    # Runtime application code (deployed to Docker)
│   ├── __init__.py        # Flask app initialization
│   ├── routes.py          # Web routes, form handling, and input validation
│   ├── get_tides.py       # Core tide data processing and PDF generation
│   ├── database.py        # Centralized SQLite database operations
│   ├── canadian_station_sync.py  # Dynamic Canadian station import from CHS API
│   ├── tide_adapters.py   # NOAA/CHS API adapters with retry logic
│   ├── run.py            # Application entry point with database initialization
│   ├── templates/        # Jinja2 HTML templates
│   ├── static/          # CSS and static assets
│   ├── tide_stations_new.csv        # US/NOAA station data (imported at startup)
│   └── canadian_tide_stations.csv   # Canadian/CHS station data (CSV fallback only)
├── scripts/               # Development and maintenance scripts (NOT deployed)
│   ├── validate_tide_stations.py    # Validate CSV stations against NOAA API
│   └── test_canadian_import.py      # Test Canadian station imports
├── backup/                # CSV backup files (NOT deployed)
│   └── tide_stations_new.csv.backup.*
├── tests/                 # Playwright end-to-end tests (NOT deployed)
├── docs/                  # Documentation (NOT deployed)
└── .dockerignore         # Excludes dev files from Docker image (~55 MB savings)
```

**Note**: The Docker image only includes files from `/app` that are necessary for runtime. Development tools, tests, scripts, and documentation are excluded via `.dockerignore`, reducing the image size by approximately 55 MB.

### Key Workflows
1. **Container Startup (Database Initialization)**:
   - Initialize SQLite database and schema
   - Import USA stations from `tide_stations_new.csv` (~2100 stations)
   - **Dynamically import Canadian stations** from CHS IWLS API (~73 active stations)
     - Filters: `operating: true`, `type: PERMANENT`, has `wlp-hilo` predictions
     - Logs: "Found X of Y stations operating with wlp-hilo data"
     - Fallback to `canadian_tide_stations.csv` if API unavailable
   - Sync database (remove inactive stations)
2. **PDF Generation with Caching**:
   - User submits form → `routes.py` validates input
   - Check if PDF exists in cache (`/data/calendars/` in production, `app/calendars/` in dev)
   - If cached: serve immediately
   - If not cached: call `get_tides.py` → NOAA/CHS API fetch → pcal conversion → PDF creation → save to cache
   - **API Retry Logic**: 3 attempts with exponential backoff for 502/503/504 gateway errors
3. **Database Tracking**: Station IDs and lookup counts stored in SQLite via `database.py` module
4. **Form Validation**: Input validation prevents crashes and provides user-friendly error messages
5. **Error Handling**: Missing/empty PDFs and invalid inputs trigger custom error templates

### Technology Stack
- **Backend**: Flask with Python 3.9+
- **External Dependencies**: `pcal` (calendar generation), `ghostscript` (PDF processing)
- **Data Sources**:
  - NOAA CO-OPS API for USA tide predictions
  - CHS IWLS API for Canadian tide predictions and station directory
- **Database**: SQLite for station tracking
- **Deployment**: CapRover (Docker-based PaaS with automatic SSL and reverse proxy)

### Maintenance Scripts

#### CSV Validation
The `scripts/validate_tide_stations.py` script validates all stations in the CSV against the NOAA API:

```bash
# Run validation (dry-run mode to preview changes)
python3 scripts/validate_tide_stations.py --dry-run

# Run validation and update CSV (creates timestamped backup)
python3 scripts/validate_tide_stations.py
```

**Features:**
- Tests each station for current month prediction data availability
- Rate limiting: 0.25s delay between requests (~4 req/sec) to respect NOAA API limits
- Creates timestamped backup before modifying CSV
- Generates detailed report with statistics
- Expected runtime: ~12-15 minutes for ~2900 stations

**When to run**: Monthly maintenance to keep the station list clean and prevent invalid stations from appearing in the popular stations list.

## Performance Benchmarks

### Overview

Performance targets and benchmarks for the Tide Calendar application, measured in production environment (tidecalendar.xyz) and local development.

### Application Performance

#### Page Load Times

| Metric | Target | Typical | Notes |
|--------|--------|---------|-------|
| Initial page load | <2s | 1.2-1.5s | First visit, no cache |
| Cached page load | <1s | 0.3-0.5s | Browser cache enabled |
| Time to Interactive (TTI) | <3s | 2.0-2.5s | All JavaScript loaded |
| Largest Contentful Paint (LCP) | <2.5s | 1.5-2.0s | Core Web Vital |
| First Input Delay (FID) | <100ms | 20-50ms | User interaction responsiveness |

**Measurement tools:**
- Lighthouse (Chrome DevTools)
- Playwright performance tests
- Real User Monitoring via Plausible

#### API Response Times

| Endpoint | Target | Typical | Notes |
|----------|--------|---------|-------|
| `/api/search` (autocomplete) | <500ms | 150-300ms | Cached popular stations |
| `/api/search` (database query) | <1000ms | 200-400ms | SQLite full-text search |
| `/api/popular_stations` | <200ms | 50-100ms | Cached query results |
| `/api/generate_quick` (cached) | <100ms | 20-50ms | Serving cached PDF |
| `/api/generate_quick` (new) | <15s | 5-12s | Full generation pipeline |

**Performance optimizations:**
- SQLite indices on `station_id`, `place_name`, `country`
- Query result caching for popular stations
- PDF file caching (30-day retention)

### External API Performance

#### NOAA CO-OPS API

| Operation | Target | Typical | Timeout |
|-----------|--------|---------|---------|
| Tide predictions fetch | <5s | 2-4s | 15s |
| Retry attempt (1st) | +2s | - | After 502/503/504 |
| Retry attempt (2nd) | +4s | - | Exponential backoff |
| Retry attempt (3rd) | +8s | - | Final attempt |

**Retry logic:**
- 3 attempts with exponential backoff (2s, 4s, 8s)
- Only retries on gateway errors (502, 503, 504)
- Total max time: 15s initial + 14s retries = 29s

**API endpoint:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`

#### Canadian Hydrographic Service (CHS) IWLS API

| Operation | Target | Typical | Timeout |
|-----------|--------|---------|---------|
| Tide predictions fetch | <8s | 3-6s | 20s |
| Station directory fetch | <10s | 4-8s | 20s |
| Retry attempt (1st) | +2s | - | After 502/503/504 |
| Retry attempt (2nd) | +4s | - | Exponential backoff |
| Retry attempt (3rd) | +8s | - | Final attempt |

**Retry logic:** Same as NOAA (3 attempts, exponential backoff)

**API endpoint:** `https://api-iwls.dfo-mpo.gc.ca/api/v1/`

**Notes:**
- CHS API typically slower than NOAA due to larger response payloads
- Uses `dateStart` parameter optimization to reduce data transfer
- Filters to `wlp-hilo` time series for high/low predictions only

### PDF Generation Pipeline

#### Generation Times

| Stage | Target | Typical | Notes |
|-------|--------|---------|-------|
| API data fetch | <8s | 2-6s | Varies by API (NOAA/CHS) |
| CSV data processing | <500ms | 100-200ms | Parse and extract H/L tides |
| pcal calendar generation | <1s | 300-500ms | Generate PostScript |
| ghostscript PDF conversion | <2s | 800-1200ms | PS to PDF |
| File I/O (save to cache) | <200ms | 50-100ms | Write PDF to disk |
| **Total (first-time)** | **<15s** | **5-12s** | Full pipeline |
| **Total (cached)** | **<100ms** | **20-50ms** | Serve from disk |

**Caching effectiveness:**
- Cache hit rate: ~60-70% (popular stations/months)
- Cache duration: 30 days
- Cache cleanup: Automatic (previous months removed)
- Storage impact: ~50-100 KB per PDF, ~500 MB typical cache size

#### Generation Rate Limits

| Limit Type | Value | Notes |
|------------|-------|-------|
| Concurrent generations | 10 | Flask default workers |
| API rate limiting | ~4 req/s | Self-imposed (NOAA courtesy) |
| PDF cache size | Unlimited | Cleaned up monthly |
| Database connections | 5 concurrent | SQLite default |

### Database Performance

#### Query Performance (SQLite)

| Query Type | Target | Typical | Rows Scanned |
|------------|--------|---------|--------------|
| Station search by name | <100ms | 20-50ms | ~2200 stations |
| Popular stations (top 10) | <50ms | 10-20ms | Full table scan + sort |
| Station by ID lookup | <10ms | 2-5ms | Indexed lookup |
| Insert/update station | <20ms | 5-10ms | Single row operation |
| Station count by country | <30ms | 10-15ms | Filtered count |

**Database size:**
- USA stations: ~2,100 rows
- Canadian stations: ~73 rows
- Total: ~2,200 rows
- Database file: ~500 KB - 1 MB (with usage history)

**Indices:**
```sql
CREATE UNIQUE INDEX idx_station_id ON tide_station_ids(station_id);
CREATE INDEX idx_place_name ON tide_station_ids(place_name);
CREATE INDEX idx_country ON tide_station_ids(country);
CREATE INDEX idx_lookup_count ON tide_station_ids(lookup_count DESC);
```

#### Container Startup Performance

| Stage | Target | Typical | Notes |
|-------|--------|---------|-------|
| Database initialization | <1s | 200-500ms | Schema creation |
| USA stations CSV import | <3s | 1-2s | ~2,100 stations |
| Canadian API fetch & import | <15s | 5-10s | ~73 stations from CHS |
| Database sync (cleanup) | <2s | 500ms-1s | Remove inactive stations |
| Flask app ready | <20s | 8-15s | Total startup time |

**Startup optimization:**
- CSV import only if database empty or outdated
- Canadian stations fetched with optimized API parameters
- Parallel imports possible (future optimization)

### Frontend Performance

#### Autocomplete Performance

| Metric | Target | Typical | Notes |
|--------|--------|---------|-------|
| Keystroke to API call | <300ms | 200-250ms | Debounced input |
| API response time | <500ms | 150-300ms | Cached popular stations |
| Render dropdown | <100ms | 20-50ms | DOM manipulation |
| Total response time | <1s | 400-600ms | End-to-end |

**Optimizations:**
- 250ms debounce on input
- Popular stations cached client-side
- Max 10 results to limit DOM size
- Keyboard navigation (no re-render)

#### User Interaction Performance

| Action | Target | Typical | Notes |
|--------|--------|---------|-------|
| Country filter change | <200ms | 50-100ms | Update popular stations table |
| Form submission | <500ms | 100-200ms | Validation + PDF request |
| Popular station click | <100ms | 20-50ms | Auto-fill form (cached PDF) |
| Dropdown navigation (↑/↓) | <16ms | 5-10ms | 60 FPS target |

### Caching Strategy

#### Multi-Level Caching

| Cache Level | Duration | Hit Rate | Notes |
|-------------|----------|----------|-------|
| Browser cache (static assets) | 7 days | 90%+ | CSS, JS, images |
| PDF file cache (server) | 30 days | 60-70% | Generated calendars |
| Popular stations (server) | App lifetime | 95%+ | In-memory cache |
| SQLite query results | None | - | Fast enough without caching |

**Cache invalidation:**
- PDF cache: Automatic cleanup of previous months
- Popular stations: Refreshes on each request (fast query)
- Static assets: Version-based (cache busting if needed)

### Network Performance

#### Bandwidth Usage

| Resource Type | Size | Notes |
|---------------|------|-------|
| Initial HTML page | 15-20 KB | Gzipped |
| CSS (style.css) | 8-12 KB | Gzipped |
| JavaScript (inline) | 10-15 KB | Gzipped |
| Font Awesome (CDN) | 70-80 KB | Cached by CDN |
| Analytics (Plausible) | 1-2 KB | Privacy-friendly, minimal |
| Generated PDF | 50-100 KB | Varies by month/station |
| **Total (first visit)** | **~150-200 KB** | Excluding PDFs |
| **Total (cached)** | **<5 KB** | Only API calls |

#### Geographic Performance

| Region | Page Load | PDF Generation | Notes |
|--------|-----------|----------------|-------|
| North America | 1-2s | 5-12s | Server in North America |
| Europe | 2-3s | 6-14s | Atlantic latency |
| Asia/Pacific | 3-4s | 8-16s | Higher latency |

**Server location:** CapRover deployment (North America)

### Performance Testing

#### Automated Tests (Playwright)

Performance thresholds enforced in test suite:

```typescript
// tests/config/test-config.ts
export const PERFORMANCE_THRESHOLDS = {
  PAGE_LOAD_TIME: 3000,          // 3s max
  API_RESPONSE_TIME: 2000,       // 2s max
  AUTOCOMPLETE_RESPONSE_TIME: 1000, // 1s max
};
```

**Test coverage:**
- Page load performance (Lighthouse metrics)
- API response times (all endpoints)
- Autocomplete responsiveness
- PDF generation (first-time and cached)
- Memory usage during interactions

#### Load Testing Recommendations

**Tools:**
- Apache Bench (ab): Simple load testing
- Locust: Distributed load testing
- Playwright: Automated performance regression

**Example load test (Apache Bench):**
```bash
# Test homepage under load
ab -n 1000 -c 10 https://tidecalendar.xyz/

# Test autocomplete API
ab -n 500 -c 5 "https://tidecalendar.xyz/api/search?query=seattle&country=all"

# Test PDF generation (cached)
ab -n 100 -c 5 "https://tidecalendar.xyz/?station_search=9449639&year=2024&month=11"
```

**Expected capacity (single instance):**
- Concurrent users: 50-100
- Requests per second: 20-50 (mixed workload)
- PDF generations per minute: 20-30 (uncached)
- PDF generations per minute: 200+ (cached)

### Monitoring and Alerting

#### Key Performance Indicators (KPIs)

**Production monitoring via Plausible Analytics:**
- Page load times (via custom events)
- Error rates (tracked via error events)
- Popular station usage patterns
- Country filter selection distribution

**Server-side monitoring:**
- Application logs (INFO level for performance events)
- PDF cache hit/miss rates
- API retry rates (NOAA and CHS)
- Database query slow-log (>500ms)

#### Performance Degradation Alerts

**Warning thresholds:**
- Page load time >3s (90th percentile)
- API response time >2s (90th percentile)
- PDF generation time >20s (timeout)
- Error rate >1% (24-hour average)

**Critical thresholds:**
- Page load time >5s (90th percentile)
- API response time >5s (90th percentile)
- PDF generation time >30s (timeout)
- Error rate >5% (24-hour average)

### Performance Optimization History

**Recent optimizations (2024):**
- ✅ Added PDF file caching (30-day retention) - 95% faster for cached PDFs
- ✅ Implemented CHS API `dateStart` parameter - 40% faster Canadian API calls
- ✅ Added retry logic with exponential backoff - 99%+ API success rate
- ✅ Optimized autocomplete with debouncing - 60% fewer API calls
- ✅ Added SQLite indices on key columns - 10x faster searches
- ✅ Reduced Docker image size via `.dockerignore` - 55 MB savings, faster deploys

**Future optimization opportunities:**
- Consider Redis for popular stations caching (if scaling needed)
- Implement CDN for static assets (currently served by Flask)
- Add database read replicas (if traffic increases 10x)
- Implement lazy loading for popular stations table
- Consider WebP images for better compression
- Add service worker for offline functionality

### Important Notes
- **Local development**: Application runs on port 5001
- **Production (CapRover)**: Application runs on port 80 (CapRover proxies from 443→80)
- **Database location**: `/data/tide_station_ids.db` (configurable via `DB_PATH` env var)
- **PDF cache location**: `/data/calendars/` in production, `app/calendars/` in local dev (configurable via `PDF_OUTPUT_DIR` env var)
- **PDF caching**: Generated PDFs are cached for 30 days to reduce API calls and improve performance
- **Database sync**: On container startup, the database automatically syncs with the CSV files, removing any stations not present in the canonical CSVs
- Station ID 9449639 is used as default demonstration value
- Low tide events (<0.3m) are marked with asterisks in calendars
- SQLite database auto-initializes on application startup via centralized `database.py` module
- Form validation prevents crashes: validates station ID (numeric), year (2000-2030), month (1-12)
- Cross-platform compatibility ensured with `sys.executable` instead of hardcoded Python command
- start new branches from `development` and also verify that `development` is the same or ahead of `main` first.
- I made a new app on caprover at https://dev.tidecalendar.xyz that is set to sync from the `development` branch on github.  in general, except for hotfixes, we are going to work on `development` first and then PR into `main` from there
- when adding a new source file required for the docker container check the Dockerfile to make sure it's listed explicitly or implicitly