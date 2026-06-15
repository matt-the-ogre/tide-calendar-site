# Interactive Tide Station Map — Design Spec

**Date:** 2026-06-14
**Branch:** `feature/station-map` (off `development`)
**Status:** Approved for implementation

## Goal

Let users find and select a tide station **visually on a map** instead of by name or
station ID. The map is embedded on the homepage (single-serving site). Selecting USA
or Canada in the existing country filter zooms the map to that country; "all" shows
North America.

## Non-goals (YAGNI)

Geolocation / "near me", search-on-map, custom/self-hosted tile servers, per-station
detail pages, tide-type marker icons. These may come later but are out of scope.

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Map placement | **Embedded on homepage**, above the form | Single-serving site; max discoverability |
| Pin click behavior | **Fill the form** ("Use this station") | Reuses existing validation/submit; one code path |
| Map provider | **Leaflet + OpenStreetMap standard tiles** | Open, no API key, no billing |
| Map library delivery | **Vendored / self-hosted** in `app/static/vendor/` | Keeps CSP `'self'`; no third-party CDN dependency |
| US coordinates source | **Baked into `tide_stations_new.csv`** (cache) + startup backfill for new/missing | Mirrors Canadian CSV pattern; no hard runtime API dependency |
| Canada coordinates | Already present (CSV + CHS sync) | No change |

## Data layer

- **US coords (cache):** New maintenance script `scripts/fetch_noaa_coordinates.py`
  pulls NOAA's Metadata API (`https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions`,
  one call, all stations with `lat`/`lng`) and writes `latitude`/`longitude` columns
  into `app/tide_stations_new.csv`. Verified: 100% of the 2,132 current CSV stations
  resolve in this feed. Documented in CLAUDE.md beside the other maintenance scripts.
- **Canada coords:** Unchanged — `app/canadian_tide_stations.csv` already carries
  lat/long, and the live CHS sync populates them.
- **Startup self-heal:** After the existing CSV/DB import, `run.py` checks for stations
  with `NULL` latitude/longitude. If any **US** stations are missing coords → make **one**
  NOAA MDAPI call and backfill just those. If none are missing → **no** network call.
  Failure is non-fatal: logged, the affected station simply has no pin that boot.
- **Schema:** `tide_station_ids` already has `latitude`/`longitude` columns
  (via `_migrate_columns`). No migration needed.

## Backend

- **New route:** `GET /api/stations.geojson` in `app/routes.py`. Returns a GeoJSON
  `FeatureCollection`; each feature = `{type, geometry:{type:"Point", coordinates:[lng,lat]},
  properties:{station_id, name, country}}`. Only includes stations that have coordinates,
  so a pin click can never produce an "unknown station" error.
- **Caching:** Built once and memoized in-process (station set is static per container).
  Gzip-friendly (~200–400 KB raw).
- **DB helper:** `database.py` gains `get_stations_with_coordinates()` returning rows with
  non-NULL lat/long.

## Frontend

- **Vendoring:** Leaflet (CSS + JS) and Leaflet.markercluster (CSS + JS) downloaded into
  `app/static/vendor/`. No CDN.
- **Placement:** A map container `<div>` in `app/templates/index.html` between the
  example-image figure and the form-card. Height ~420px desktop, reduced on mobile.
  Leaflet init deferred to `DOMContentLoaded` so it doesn't block first paint.
- **Clustering:** Leaflet.markercluster for ~3,200 pins; clusters expand on zoom.
- **Tiles:** OSM standard tiles with required attribution and a descriptive request header.
- **Pin → popup:** Shows station name + source/ID + a **"Use this station"** button. The
  button sets `#station_search` (visible) and `#station_id` (hidden), smooth-scrolls to the
  form, and focuses Year — reusing the existing submit path entirely.
- **Country filter integration:** Extend the existing `country_filter` radio change handler
  to also (a) show/hide US vs Canada markers and (b) re-fit the map: `all` → North America
  bounds, `USA` → US bounds, `Canada` → Canada bounds. Single source of truth for country
  state (shared with the popular-stations reload + cookie logic already present).

## Cross-cutting

- **CSP / security headers:** Add OSM tile origin(s) to `img-src`. Scripts and styles stay
  `'self'` (vendored). Update the baseline security headers added in the recent hardening.
- **Docker:** Add the vendored static files to the Dockerfile `COPY` lines; confirm
  `tide_stations_new.csv` (now with coord columns) still ships.
- **Branch / PR:** `feature/station-map` → PR into `development`. PR review includes an
  adversarial review by a Sonnet agent.

## Testing

- **Python unit tests:**
  - `/api/stations.geojson`: valid GeoJSON, expected feature count, every feature has
    finite coordinates and a station_id.
  - Startup backfill: missing coords → filled (mocked NOAA response); none missing →
    no network call made.
  - `get_stations_with_coordinates()` excludes NULL-coord rows.
- **Script test:** `fetch_noaa_coordinates.py` writes the expected CSV columns/shape
  (mocked feed).
- **Playwright e2e:** map renders; clicking a marker's popup "Use this station" fills the
  form's station fields; country filter re-fits the map. Respect the hidden-radio/`label`
  interaction gotcha documented in CLAUDE.md.

## Risks / notes

- OSM's public tile policy targets low-traffic use; acceptable for this niche
  single-serving site with proper attribution. Carto Positron is a documented fallback if
  volume ever warrants it.
- Embedded map adds JS/tile load to the homepage (accepted trade-off for discoverability);
  mitigated by deferred init and clustering.
