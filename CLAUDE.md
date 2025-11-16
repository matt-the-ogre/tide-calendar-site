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
- **Tide Data Fetcher**: `get_tides.py` retrieves NOAA tide data and generates PDF calendars
- **Database Module**: `database.py` centralized SQLite operations for station usage tracking
- **PDF Generation Pipeline**: Uses `pcal` and `ghostscript` for calendar creation

### Application Structure
```
app/
├── __init__.py          # Flask app initialization
├── routes.py            # Web routes, form handling, and input validation
├── get_tides.py         # Core tide data processing and PDF generation
├── database.py          # Centralized SQLite database operations
├── run.py              # Application entry point with database initialization
├── templates/          # Jinja2 HTML templates
└── static/            # CSS and static assets
```

### Key Workflows
1. **PDF Generation with Caching**:
   - User submits form → `routes.py` validates input
   - Check if PDF exists in cache (`/data/calendars/` in production, `app/calendars/` in dev)
   - If cached: serve immediately
   - If not cached: call `get_tides.py` → NOAA/CHS API fetch → pcal conversion → PDF creation → save to cache
2. **Database Tracking**: Station IDs and lookup counts stored in SQLite via `database.py` module
3. **Form Validation**: Input validation prevents crashes and provides user-friendly error messages
4. **Error Handling**: Missing/empty PDFs and invalid inputs trigger custom error templates

### Technology Stack
- **Backend**: Flask with Python 3.9+
- **External Dependencies**: `pcal` (calendar generation), `ghostscript` (PDF processing)
- **Data Source**: NOAA CO-OPS API for tide predictions
- **Database**: SQLite for station tracking
- **Deployment**: CapRover (Docker-based PaaS with automatic SSL and reverse proxy)

### Important Notes
- **Local development**: Application runs on port 5001
- **Production (CapRover)**: Application runs on port 80 (CapRover proxies from 443→80)
- **Database location**: `/data/tide_station_ids.db` (configurable via `DB_PATH` env var)
- **PDF cache location**: `/data/calendars/` in production, `app/calendars/` in local dev (configurable via `PDF_OUTPUT_DIR` env var)
- **PDF caching**: Generated PDFs are cached for 30 days to reduce API calls and improve performance
- Station ID 9449639 is used as default demonstration value
- Low tide events (<0.3m) are marked with asterisks in calendars
- SQLite database auto-initializes on application startup via centralized `database.py` module
- Form validation prevents crashes: validates station ID (numeric), year (2000-2030), month (1-12)
- Cross-platform compatibility ensured with `sys.executable` instead of hardcoded Python command