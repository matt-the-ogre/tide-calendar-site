# Technology Stack

**Analysis Date:** 2026-03-31

## Languages

**Primary:**
- Python 3.9+ - Backend application, all server-side logic (`app/*.py`)
- HTML/CSS/JavaScript - Frontend templates and styling (`app/templates/`, `app/static/`)

**Secondary:**
- TypeScript 5.3+ - Playwright E2E tests (`tests/`, `playwright.config*.ts`)

## Runtime

**Environment:**
- Python 3.9 (Docker base image: `python:3.9-slim-bullseye`)
- Node.js >= 18.0.0 (for Playwright tests only, not runtime)

**Package Manager:**
- pip (Python dependencies via `requirements.txt`)
- npm (Playwright test dependencies via root `package.json`)
- Lockfile: No `requirements.lock` or `package-lock.json` committed

## Frameworks

**Core:**
- Flask 3.1.1 - Web framework (`app/__init__.py`, `app/routes.py`)
- Jinja2 3.1.6 - HTML templating (via Flask, templates in `app/templates/`)

**Testing:**
- Playwright ^1.40.0 - E2E browser testing (`tests/`, `playwright.config*.ts`)
  - Configs: `playwright.config.ts` (local, all browsers), `playwright.config.local.ts`, `playwright.config.prod.ts`, `playwright.config.smoke.ts`
  - Browser targets: Chromium, Firefox, WebKit, Mobile Chrome (Pixel 5), Mobile Safari (iPhone 12)

**Build/Dev:**
- Docker - Containerization (`Dockerfile`)
- Docker Compose - Local dev orchestration (`docker-compose.yaml`)
- GitHub Actions - CI/CD for smoke tests (`.github/workflows/playwright.yml`)

## Key Dependencies

**Critical (Python - `requirements.txt`):**
- Flask==3.1.1 - Web framework
- requests==2.32.4 - HTTP client for NOAA/CHS API calls
- python-dotenv==1.1.0 - Environment variable loading from `.env`
- Werkzeug==3.1.5 - WSGI utilities (Flask dependency)
- Jinja2==3.1.6 - Template engine (Flask dependency)
- urllib3==2.6.3 - HTTP connection pooling (requests dependency)

**Infrastructure (Python):**
- click==8.1.7 - CLI framework (Flask dependency)
- itsdangerous==2.2.0 - Data signing (Flask sessions)
- blinker==1.9.0 - Signal support (Flask dependency)
- MarkupSafe==2.1.5 - HTML escaping (Jinja2 dependency)

**Testing (Node.js - `package.json`):**
- @playwright/test ^1.40.0 - Test framework
- @types/node ^20.10.0 - TypeScript type definitions
- typescript ^5.3.0 - TypeScript compiler

## System Dependencies

**Required at runtime (installed in Docker image):**
- `pcal` - Calendar layout generation (converts tide data to PostScript calendar format)
- `ghostscript` - PostScript to PDF conversion (converts pcal output to final PDF)
- `git` - Version info generation at build time only

**Installation:**
- Linux (Debian/Ubuntu): `apt-get install -y pcal ghostscript`
- macOS: `brew install pcal ghostscript`

## Configuration

**Environment:**
- `.env` file present at project root (contains environment configuration)
- Key env vars: `FLASK_APP`, `FLASK_ENV`, `FLASK_RUN_PORT`, `PDF_OUTPUT_DIR`, `TOP_STATIONS_COUNT`, `DB_PATH`
- Default dev port: 5001
- Default production port: 80

**Build:**
- `Dockerfile` - Python 3.9-slim-bullseye base, explicit COPY of runtime files
- `docker-compose.yaml` - Maps local port 5001 to container port 80
- `captain-definition` - CapRover deployment config (`{"schemaVersion": 2, "dockerfilePath": "./Dockerfile"}`)
- `.dockerignore` - Excludes tests, scripts, docs, node_modules (~55 MB savings)

**Docker Build Args:**
- `VERSION` - Application version (from `package.json`)
- `COMMIT_HASH` - Git commit hash
- `BRANCH` - Git branch name
- `BUILD_TIMESTAMP` - UTC build timestamp
- These are written to `/app/version_info.json` at build time

## Database

**Engine:** SQLite (via Python stdlib `sqlite3`)
- No ORM - direct SQL queries in `app/database.py`
- Schema migration: Inline `ALTER TABLE` statements with `PRAGMA table_info` checks
- Location: `DB_PATH` env var, defaults to `app/tide_station_ids.db` (local) or `/data/tide_station_ids.db` (production)

## Frontend Assets

**CSS:**
- Custom CSS with CSS custom properties design system (`app/static/style.css`)
- No CSS preprocessor or build step

**Fonts (CDN):**
- Google Fonts: DM Sans (400/500/600/700), DM Serif Display

**Icons (CDN):**
- Font Awesome 6.0.0-beta3 via cdnjs

**JavaScript:**
- Vanilla JS only (no framework, no bundler)
- Inline scripts in templates for email obfuscation and copyright year

## Platform Requirements

**Development:**
- Python 3.9+
- `pcal` and `ghostscript` system packages
- Node.js 18+ (for running Playwright tests only)
- Docker (optional, for containerized development)

**Production:**
- Docker container on CapRover
- Persistent volume at `/data` (SQLite DB + cached PDFs)
- Port 80 exposed (CapRover handles SSL termination)

## Version Management

- Application version tracked in `package.json` (`version: "1.26.01"`)
- `app/generate_version_info.py` and Dockerfile build step produce `version_info.json`
- Health endpoint `/health` exposes version, commit hash, branch, and build timestamp

---

*Stack analysis: 2026-03-31*
