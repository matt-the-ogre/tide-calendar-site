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
# Local Docker runs via colima (docker CLI is the brew formula, client only)
colima start   # if it fails with "vz driver is running but host agent is not": colima stop --force, retry

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
- **Flask Web Application**: Serves tide calendar generation interface with form validation and per-IP rate limiting (Flask-Limiter, 10/min on the two generation endpoints)
- **Calendar Service**: `calendar_service.py` single owner of the PDF contract — filename derivation (`pdf_filename_for`), cache check, generation, usage-event logging. Both web routes and the CLI go through it.
- **Tide Data Pipeline**: `get_tides.py` importable `generate_calendar()` (fetch → pcal → ps2pdf, per-invocation temp dir, atomic rename into cache); also a CLI used by `scripts/update_example_image.sh`
- **Database Module**: `database.py` centralized SQLite operations for station usage tracking
- **Canadian Station Sync**: `canadian_station_sync.py` dynamically imports Canadian stations from CHS API
- **Tide Adapters**: `tide_adapters.py` provides unified interface for NOAA and CHS APIs with retry logic
- **PDF Generation Pipeline**: Uses `pcal` and `ghostscript` for calendar creation

### Repository Structure
```
├── app/                    # Runtime application code (deployed to Docker)
│   ├── __init__.py        # Flask app initialization
│   ├── routes.py          # Web routes, form handling, and input validation
│   ├── calendar_service.py  # PDF filename contract, cache, generation orchestration
│   ├── get_tides.py       # Tide data fetch + pcal/ps2pdf pipeline (importable + CLI)
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
│   ├── canadian_tide_stations.csv   # Canadian/CHS fallback (full ~1076-station snapshot; gen: scripts/generate_canadian_fallback_csv.py)
│   └── canadian_station_provinces.csv  # Authoritative code→province map (gen: scripts/fetch_canadian_provinces.py)
├── scripts/               # Development and maintenance scripts (NOT deployed)
│   ├── validate_tide_stations.py    # Validate CSV stations against NOAA API
│   ├── update_example_image.sh      # Example calendar image (current month); auto-run monthly by .github/workflows/update-example-image.yml
│   ├── fetch_canadian_provinces.py  # Build authoritative code→province map from CHS /metadata
│   ├── generate_canadian_fallback_csv.py  # Snapshot full live import to the fallback CSV
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
   - **Dynamically import Canadian stations** from CHS IWLS API (~1076 stations)
     - Filter: has `wlp-hilo` predictions (high/low tide data) + a code and official name.
       The `operating`/`type` flags are intentionally NOT used — many `operating:false`/
       `TEMPORARY` stations (e.g. 07837 ḵalpilin / Pender Harbour) still publish full
       forward predictions; gating on them hid ~93% of calendar-capable stations. No
       `dateStart` param either (it prunes stations that still have current predictions).
     - Captures CHS `alternativeName` (common name) into the `alternative_name` column so
       name search/autocomplete matches either name (see `normalize_station`).
     - Logs: "Found X of Y stations with wlp-hilo predictions"
     - Fallback to `canadian_tide_stations.csv` if API unavailable
   - Sync database (remove inactive stations)
2. **PDF Generation with Caching**:
   - User submits form → `routes.py` validates input → `calendar_service.get_or_generate_pdf()`
   - Unknown station IDs are rejected before any upstream work (logged as `unknown_station`)
   - Check if PDF exists in cache (`/data/calendars/` in production, `app/calendars/` in dev)
   - If cached: serve immediately
   - If not cached: `get_tides.generate_calendar()` in-process → NOAA/CHS API fetch → pcal conversion → ps2pdf → atomic rename into cache (intermediates live in a temp dir; pcal/ps2pdf have 60s timeouts)
   - **API Retry Logic**: 3 attempts with exponential backoff for 502/503/504 gateway errors
   - Old-month PDFs are swept once at container startup (`run.py`), not per request
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

#### Canadian Province Map
The `scripts/fetch_canadian_provinces.py` script builds the authoritative
`code → province` lookup for Canadian stations, written to `app/canadian_station_provinces.csv`:

```bash
python3 scripts/fetch_canadian_provinces.py
```

**Why it exists**: CHS official names almost never include a province, and the bulk
`/stations` list omits `provinceCode` (only per-station `/metadata` has it). The old
longitude-based guess in `construct_place_name()` was wrong ~50% of the time. This
script precomputes the map from `/metadata` (the CHS API rate-limits too hard to do
this at container startup; ~30-50 min for ~1,076 stations as throttling slows it
partway — it is resumable/checkpointed, so don't kill a slow run). At runtime
`canadian_station_sync.PROVINCE_BY_CODE` loads the CSV and `normalize_station()` uses
**map → province-in-name → longitude fallback**.

**When to run**: Occasionally (e.g. monthly), and whenever new Canadian stations appear.
The script is resumable. The output CSV must stay listed in the Dockerfile `COPY` lines
so it ships in the image.

#### Canadian Fallback CSV
The `scripts/generate_canadian_fallback_csv.py` script regenerates
`app/canadian_tide_stations.csv` — the offline fallback used only when the CHS API is
unreachable at startup:

```bash
python3 scripts/generate_canadian_fallback_csv.py
```

It snapshots a full live import (all ~1,076 stations with correct provinces, alternative
names, and place names) so degraded mode matches normal operation. Fast: one bulk
`/stations` call + the local province map (no per-station calls), so run
`fetch_canadian_provinces.py` first if provinces are stale. Run it after that whenever
the station set changes meaningfully.

#### NOAA Coordinate Sync (US station lat/long for the map)
The `scripts/fetch_noaa_coordinates.py` script bakes `latitude`/`longitude` columns
into `app/tide_stations_new.csv` for the homepage station map:

```bash
python scripts/fetch_noaa_coordinates.py
```

It makes **one** call to NOAA's Metadata API (`mdapi/.../stations.json?type=tidepredictions`),
which returns every tide-prediction station with `lat`/`lng`, and rewrites the CSV
(`station_id,place_name,latitude,longitude`). No per-station requests. Mirrors the
Canadian fallback-CSV pattern: coordinates ship as static data, so the runtime has no
hard dependency on a live API. Canadian coordinates already live in
`canadian_tide_stations.csv` + the CHS sync, so this script is US-only.

**When to run**: whenever new US stations are added to the CSV (so they get map pins).
The output CSV must stay listed in the Dockerfile `COPY` lines.

#### Example Calendar Image (automated monthly)
`scripts/update_example_image.sh` regenerates `app/static/tide-calendar-example.webp`
with the **current** month's calendar for Point Roberts, WA (station 9449639), using
pcal → ps2pdf → ImageMagick. You can run it manually, but it normally runs **on its own**:

- **Workflow**: `.github/workflows/update-example-image.yml`, cron `0 0 1 * *`
  (00:00 UTC on the 1st of each month). Scheduled workflows only fire from the default
  branch, so the workflow must live on `main`.
- Each run regenerates + validates the image, **commits to `main`** (→ production deploy),
  then **back-merges `main` into `development`** so `development` never falls behind.
- Manual `workflow_dispatch` runs default to **`dry_run=true`** (generate + validate only,
  no push); set `dry_run=false` to publish.
- Runner note: Ubuntu ships ImageMagick 6 (`convert`, not `magick`) and disables PDF
  reading by default — the workflow shims `magick`→`convert` and relaxes the PDF policy.

### Running Tests
```bash
# Run Python unit tests (same as CI; must run from app/ — tests import sibling modules)
cd app && python -m unittest discover -p 'test_*.py'
python scripts/test_usage_events.py

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
- **dev→main merge-commit drift**: after a `development → main` PR merge, `development` lags `main` by the merge commit (file trees identical). Resync with `git checkout development && git merge --ff-only origin/main && git push` so new work starts current.
- **`app/` must NOT import from `scripts/`**: `.dockerignore` excludes `scripts/` from the image, so any runtime `import scripts.*` from `app/` raises ModuleNotFoundError in the container. Cold-DB dev hides it; warm-DB prod surfaces it. Inline shared logic into the shipped `app/` module (e.g. `station_coordinates.py` has its own `fetch_noaa_coordinates`).
- **Dual-import idiom**: modules imported by the unittest suite use `try: from app.X import … except ImportError: from X import …` (tests run `cd app && python -m unittest` → siblings top-level; gunicorn runs the `app` package). `routes.py` is NOT unittest-importable (`from app import app`) and no test imports it — test pure helpers by putting them in `database.py`, not in routes.
- **Tests reassign `database.DB_PATH`** at runtime, so reference `database.DB_PATH` dynamically; never `from database import DB_PATH` (the binding goes stale and tests clobber the real DB).
- **Local manual testing**: seed a temp DB fast with `database.import_stations_from_csv()` + `import_canadian_stations_from_csv()` (CSV, no API), then `DB_PATH=… FLASK_APP=app flask run` to bypass run.py's slow CHS API sync.
- **Claude Code sandbox can't reach localhost**: curl to a local flask server returns HTTP 000 — verify via the Playwright/Chrome MCP browser (real env) or `dangerouslyDisableSandbox` for localhost-targeting Bash. Run the dev server as a harness background task (`run_in_background`), not `&`/nohup (the sandbox reaps detached processes).
- **Local development**: Application runs on port 5001
- **Production (CapRover)**: Application runs on port 80 (CapRover proxies from 443→80)
- **Database location**: `/data/tide_station_ids.db` (configurable via `DB_PATH` env var)
- **PDF cache location**: `/data/calendars/` in production, `app/calendars/` in local dev (configurable via `PDF_OUTPUT_DIR` env var)
- **PDF caching**: Generated PDFs are cached for 30 days to reduce API calls and improve performance
- **Database sync**: On container startup, the database automatically syncs with the CSV files, removing any stations not present in the canonical CSVs
- **Default demo station**: Station ID 9449639 (Point Roberts, WA)
- **Low tides**: Events (<0.3m) are marked with asterisks in calendars
- **Form validation**: Validates station ID (numeric + must exist in the station directory), year (current year through current year + 4), month (1-12). Note: `tide_adapters.py` still hardcodes a 2000-2030 year range — needs a dynamic bound before 2031.
- **Production server**: gunicorn (2 workers × 4 threads, `--preload`, 120s timeout) as non-root `appuser`; `docker-entrypoint.sh` chowns the runtime-mounted `/data` volume before dropping privileges. `flask run` remains for local dev only.
- **Docker file inclusion**: When adding new source files required at runtime, verify the Dockerfile copies them (explicitly or implicitly)
- **Playwright + hidden inputs**: Radio inputs in country filter are hidden via CSS (`display: none`) with pill-style labels as visible controls. Playwright tests must interact with the parent `<label>` elements (e.g., `locator('xpath=..')`) instead of calling `.check()` on the hidden inputs. See `tests/pages/HomePage.ts` `selectCountryFilter()`.
- **Root-level static files** (robots.txt, sitemap.xml, llms.txt, ads.txt) are served via Flask routes in `routes.py` using the `_serve_static_file()` helper, not Flask's default `/static/` path. New root-level files need both the static file and a route.
- **Dependency updates**: Before bumping Python package versions, check `requires_python` on PyPI against the Dockerfile base image (`python:3.12-slim-bookworm`). Use: `curl -s https://pypi.org/pypi/<pkg>/<ver>/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['requires_python'])"`
- **Testing pcal/PDF changes**: Cached PDFs mask code changes. Clear cache before testing: `ssh captain "docker exec <container> sh -c 'rm -f /data/calendars/*.pdf'"` (must use `sh -c` for glob expansion in `docker exec`)
- **CapRover containers**: SSH host `captain`, container names: `srv-captain--tide-calendar-{dev,prod}.1.<hash>`. Find with: `ssh captain "docker ps --format '{{.Names}}' | grep tide"`
- **subprocess.run gotcha**: When using list args (not `shell=True`), each flag and its value must be separate list elements. `["-s", "0.0:0.0:1.0"]` not `["-s 0.0:0.0:1.0"]`
- **Docker build context**: `.dockerignore` must NOT exclude `.git` — the Dockerfile's builder stage derives /health's commit_hash from it (only that stage sees it; history never ships in the final image)
- **pip-audit CI gate**: a red build with no code change usually means a newly published advisory, not a regression — bump the affected pin (it's non-deterministic by design)
- **"submit-pypi" CI check**: GitHub's built-in Automatic Dependency Submission (dependency graph), not a PyPI publish
- **Rate-limit testing**: limiter counters are per-gunicorn-worker (in-memory), so effective ceiling ≈ limit × 2 workers; burst tests need 25+ requests to reliably trip 429s
- **pcal flags reference**: `-s r:g:b` sets day numeral color, `-S` suppresses mini-calendars (on by default), `-K` repositions mini-cals (prev upper-left, next lower-right), `-C text` adds centered footer, `-m` shows month name
- **Deploy verification**: After pushing, check `/health` endpoint for matching `commit_hash` to confirm CapRover deploy landed (observed 10–60s including container startup). Compare dev vs prod: `curl -s https://dev.tidecalendar.xyz/health | python3 -m json.tool`
- **Station map**: The homepage embeds a Leaflet/OpenStreetMap map of all selectable stations (`app/static/js/station_map.js`). Pins are `L.circleMarker` (vector — no marker-image assets needed), clustered via Leaflet.markercluster. Clicking a pin's "Use this station" popup button fills the existing form (`#station_search` + `#station_id`) and scrolls to it; the country filter radios re-fit the map (all → North America, USA/Canada → that country's bounds, computed from the markers, not hardcoded). Leaflet + markercluster are **vendored** in `app/static/vendor/leaflet/` (no CDN, no CSP changes — there is no CSP). Data comes from `GET /api/stations.geojson` (GeoJSON FeatureCollection, memoized in-process; only stations with coordinates appear, so a pin click can never hit an unknown station). US coordinates ship in `tide_stations_new.csv` (see the NOAA Coordinate Sync script); `app/station_coordinates.py` `backfill_missing_coordinates()` runs at startup (`run.py`) and makes **one** NOAA call to fill any US stations still missing coords (the only path that reaches production's *warm* persistent-volume DB, where the CSV import short-circuits) — non-fatal, and a no-op/no-network-call when nothing is missing.
- **Analytics**: Server-side `usage_events` table logs every request to `/` and `/api/generate_quick` (station_id, station_name, year, month, status, error_detail, source). No PII. `source='web'` for form submissions, `source='quick_api'` for embed/widget traffic. Dashboard at `/admin/analytics` — accepts `Authorization: Bearer $ANALYTICS_TOKEN` header (preferred, stays out of access logs) or `?token=$ANALYTICS_TOKEN` query param (fallback). Returns 404 on any unauth/unconfigured request (invisible to scanners). Events older than 365 days are pruned on container startup. Complements client-side Plausible (which misses cached serves, validation errors, and ad-blocked users). Tests: `python3 scripts/test_usage_events.py`.