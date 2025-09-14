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

# Run the Flask app locally
cd app
flask run --host 0.0.0.0 --port 5001
```

### Docker Development
```bash
# Build Docker image
docker build -t tide-calendar-app .

# Run with Docker
docker run -p 5001:5001 tide-calendar-app

# Run with Docker Compose
docker-compose up --build
```

### Environment Variables
Create `.env` file with:
```
FLASK_APP=run.py
FLASK_ENV=development  # or production
FLASK_RUN_PORT=5001
```

## Architecture Overview

### Core Components
- **Flask Web Application**: Serves tide calendar generation interface
- **Tide Data Fetcher**: `get_tides.py` retrieves NOAA tide data and generates PDF calendars
- **Database**: SQLite database (`tide_station_ids.db`) tracks station usage statistics
- **PDF Generation Pipeline**: Uses `pcal` and `ghostscript` for calendar creation

### Application Structure
```
app/
├── __init__.py          # Flask app initialization
├── routes.py            # Web routes and form handling
├── get_tides.py         # Core tide data processing and PDF generation
├── run.py              # Application entry point with SQLite initialization
├── templates/          # Jinja2 HTML templates
└── static/            # CSS and static assets
```

### Key Workflows
1. **PDF Generation**: User submits form → `routes.py` calls `get_tides.py` → NOAA API fetch → pcal conversion → PDF creation
2. **Database Tracking**: Station IDs and lookup counts stored in SQLite for analytics
3. **Error Handling**: Missing/empty PDFs trigger custom error templates

### Technology Stack
- **Backend**: Flask with Python 3.9+
- **External Dependencies**: `pcal` (calendar generation), `ghostscript` (PDF processing)
- **Data Source**: NOAA CO-OPS API for tide predictions
- **Database**: SQLite for station tracking
- **Deployment**: Docker with nginx reverse proxy support

### Important Notes
- Application runs on port 5001 by default
- PDF files are generated in the app directory and served as downloads
- Station ID 9449639 is used as default demonstration value
- Low tide events (<0.3m) are marked with asterisks in calendars
- SQLite database auto-initializes on application startup