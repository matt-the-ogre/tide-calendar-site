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
ANALYTICS_TOKEN=<random-string>  # optional; gates /admin/analytics dashboard. Endpoint returns 404 until env var is set AND a matching token is supplied.
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
ANALYTICS_TOKEN=<random-string>  # gates /admin/analytics dashboard
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
│   │   ├── base.html     # Base template (shared head, footer, analytics, email obfuscation)
│   │   ├── index.html    # Main page (extends base.html)
│   │   ├── tide_station_not_found.html  # Form error page (extends base.html)
│   │   ├── admin_analytics.html  # Standalone admin dashboard (no base.html — no tracking/ads)
│   │   └── 404.html      # Custom 404 page (extends base.html)
│   ├── static/          # CSS, images, and SEO files
│   │   ├── style.css    # Main stylesheet (CSS custom properties design system)
│   │   ├── robots.txt   # Search engine crawl rules (served via /robots.txt route)
│   │   ├── sitemap.xml  # Search engine sitemap (served via /sitemap.xml route)
│   │   ├── llms.txt     # LLM crawler description (served via /llms.txt route)
│   │   └── ads.txt      # Ad network verification (served via /ads.txt route)
│   ├── tide_stations_new.csv        # US/NOAA station data (imported at startup)
│   └── canadian_tide_stations.csv   # Canadian/CHS station data (CSV fallback only)
├── scripts/               # Development and maintenance scripts (NOT deployed)
│   ├── validate_tide_stations.py    # Validate CSV stations against NOAA API
│   ├── update_example_image.sh      # Monthly update of example calendar image
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
- **Backend**: Flask with Python 3.12+
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

### Running Tests
```bash
# Install Playwright (first time)
cd tests && npm install && npx playwright install chromium

# Run smoke tests against production
npx playwright test smoke.spec.ts --config=playwright.config.smoke.ts

# Run all tests against local dev server
npx playwright test
```

## Performance Benchmarks

See `docs/performance-benchmarks.md` for detailed performance targets, API latency tables, caching strategy, and monitoring thresholds.

### Important Notes
- **Branching workflow**: Work on `development` branch first, PR into `main`. Dev deploys to https://dev.tidecalendar.xyz, main deploys to https://tidecalendar.xyz
- **Local development**: Application runs on port 5001
- **Production (CapRover)**: Application runs on port 80 (CapRover proxies from 443→80)
- **Database location**: `/data/tide_station_ids.db` (configurable via `DB_PATH` env var)
- **PDF cache location**: `/data/calendars/` in production, `app/calendars/` in local dev (configurable via `PDF_OUTPUT_DIR` env var)
- **PDF caching**: Generated PDFs are cached for 30 days to reduce API calls and improve performance
- **Database sync**: On container startup, the database automatically syncs with the CSV files, removing any stations not present in the canonical CSVs
- **Default demo station**: Station ID 9449639 (Point Roberts, WA)
- **Low tides**: Events (<0.3m) are marked with asterisks in calendars
- **Form validation**: Validates station ID (numeric), year (2000-2030), month (1-12)
- **Docker file inclusion**: When adding new source files required at runtime, verify the Dockerfile copies them (explicitly or implicitly)
- **Playwright + hidden inputs**: Radio inputs in country filter are hidden via CSS (`display: none`) with pill-style labels as visible controls. Playwright tests must interact with the parent `<label>` elements (e.g., `locator('xpath=..')`) instead of calling `.check()` on the hidden inputs. See `tests/pages/HomePage.ts` `selectCountryFilter()`.
- **Root-level static files** (robots.txt, sitemap.xml, llms.txt, ads.txt) are served via Flask routes in `routes.py` using the `_serve_static_file()` helper, not Flask's default `/static/` path. New root-level files need both the static file and a route.
- **Dependency updates**: Before bumping Python package versions, check `requires_python` on PyPI against the Dockerfile base image (`python:3.12-slim-bookworm`). Use: `curl -s https://pypi.org/pypi/<pkg>/<ver>/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['requires_python'])"`
- **Testing pcal/PDF changes**: Cached PDFs mask code changes. Clear cache before testing: `ssh captain "docker exec <container> sh -c 'rm -f /data/calendars/*.pdf'"` (must use `sh -c` for glob expansion in `docker exec`)
- **CapRover containers**: SSH host `captain`, container names: `srv-captain--tide-calendar-{dev,prod}.1.<hash>`. Find with: `ssh captain "docker ps --format '{{.Names}}' | grep tide"`
- **subprocess.run gotcha**: When using list args (not `shell=True`), each flag and its value must be separate list elements. `["-s", "0.0:0.0:1.0"]` not `["-s 0.0:0.0:1.0"]`
- **pcal flags reference**: `-s r:g:b` sets day numeral color, `-S` suppresses mini-calendars (on by default), `-K` repositions mini-cals (prev upper-left, next lower-right), `-C text` adds centered footer, `-m` shows month name
- **Deploy verification**: After pushing, check `/health` endpoint for matching `commit_hash` to confirm CapRover deploy landed (~60s build time). Compare dev vs prod: `curl -s https://dev.tidecalendar.xyz/health | python3 -m json.tool`
- **Analytics**: Server-side `usage_events` table logs every request to `/` and `/api/generate_quick` (station_id, station_name, year, month, status, error_detail, source). No PII. `source='web'` for form submissions, `source='quick_api'` for embed/widget traffic. Dashboard at `/admin/analytics` — accepts `Authorization: Bearer $ANALYTICS_TOKEN` header (preferred, stays out of access logs) or `?token=$ANALYTICS_TOKEN` query param (fallback). Returns 404 on any unauth/unconfigured request (invisible to scanners). Events older than 365 days are pruned on container startup. Complements client-side Plausible (which misses cached serves, validation errors, and ad-blocked users). Tests: `python3 scripts/test_usage_events.py`.