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