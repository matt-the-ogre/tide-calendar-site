# Interactive Tide Station Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an embedded, clustered Leaflet/OpenStreetMap map of all selectable tide stations to the homepage; clicking a pin fills the existing form, and the country filter re-fits the map.

**Architecture:** US coordinates are baked into `tide_stations_new.csv` by a new maintenance script and read at import; a startup self-heal makes one NOAA Metadata API call to backfill any stations still missing coordinates (the only path that reaches production's warm DB). A new `/api/stations.geojson` route serves all coord-bearing stations as GeoJSON. A vendored Leaflet + markercluster front-end renders circle-marker pins, and a "Use this station" popup button populates `#station_search` / `#station_id` and scrolls to the form.

**Tech Stack:** Flask, SQLite, vanilla JS, Leaflet 1.9.4 + Leaflet.markercluster 1.5.3 (vendored), OpenStreetMap tiles.

**Test commands:**
- Backend unit tests: `cd app && python -m unittest discover -p 'test_*.py'`
- Script test: `python scripts/test_fetch_noaa_coordinates.py`
- E2E: `cd tests && npx playwright test station-map.spec.ts`

---

## File Structure

**Create:**
- `scripts/fetch_noaa_coordinates.py` — pulls NOAA MDAPI, writes lat/long columns into the US CSV
- `scripts/test_fetch_noaa_coordinates.py` — unit test for the CSV transform
- `app/station_coordinates.py` — startup self-heal: `backfill_missing_coordinates()` (one NOAA call)
- `app/static/vendor/leaflet/` — vendored Leaflet + markercluster CSS/JS
- `app/static/js/station_map.js` — map init, fetch, clustering, popup, country re-fit
- `app/test_station_map.py` — backend tests (geojson route, DB helper, backfill)
- `tests/station-map.spec.ts` — Playwright e2e

**Modify:**
- `app/tide_stations_new.csv` — gains `latitude,longitude` columns (data change via script)
- `app/database.py` — read coords in `import_stations_from_csv()`; add `get_stations_with_coordinates()`
- `app/routes.py` — add `/api/stations.geojson`
- `app/run.py` — call `backfill_missing_coordinates()` after imports
- `app/templates/index.html` — map container + Leaflet CSS/JS includes + country-filter hook
- `app/static/style.css` — map container styling
- `Dockerfile` — COPY the vendored static assets and new JS
- `CLAUDE.md` — document the new script + endpoint

---

## Task 1: Vendor Leaflet + markercluster

**Files:**
- Create: `app/static/vendor/leaflet/*`

- [ ] **Step 1: Download pinned assets**

```bash
mkdir -p app/static/vendor/leaflet
cd app/static/vendor/leaflet
curl -sSfLO https://unpkg.com/leaflet@1.9.4/dist/leaflet.css
curl -sSfLO https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
curl -sSfLO https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css
curl -sSfLO https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css
curl -sSfLO https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js
cd -
```

- [ ] **Step 2: Verify all five files exist and are non-empty**

Run: `ls -l app/static/vendor/leaflet/ && wc -c app/static/vendor/leaflet/leaflet.js`
Expected: 5 files; `leaflet.js` ~140KB+.

Note: we render pins with `L.circleMarker` (vector), so Leaflet's marker-icon PNGs are NOT needed — do not vendor them.

- [ ] **Step 3: Commit**

```bash
git add app/static/vendor/leaflet
git commit -m "Vendor Leaflet 1.9.4 + markercluster 1.5.3 for station map"
```

---

## Task 2: NOAA coordinate fetch script (US coords into CSV)

**Files:**
- Create: `scripts/fetch_noaa_coordinates.py`
- Create: `scripts/test_fetch_noaa_coordinates.py`

The script reads the existing `app/tide_stations_new.csv` (cols `station_id,place_name`), fetches the NOAA MDAPI station list once, and rewrites the CSV with two extra columns `latitude,longitude`. The pure transform (merge station rows + a `{id: {lat,lng}}` map → output rows) is unit-tested.

- [ ] **Step 1: Write the failing test**

```python
# scripts/test_fetch_noaa_coordinates.py
import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from fetch_noaa_coordinates import merge_coordinates

class MergeCoordinatesTest(unittest.TestCase):
    def test_adds_lat_long_for_matched_station(self):
        rows = [{'station_id': '9449639', 'place_name': 'Point Roberts, WA'}]
        coords = {'9449639': {'lat': 48.97, 'lng': -123.07}}
        out = merge_coordinates(rows, coords)
        self.assertEqual(out[0]['latitude'], 48.97)
        self.assertEqual(out[0]['longitude'], -123.07)
        self.assertEqual(out[0]['station_id'], '9449639')
        self.assertEqual(out[0]['place_name'], 'Point Roberts, WA')

    def test_missing_station_gets_blank_coords(self):
        rows = [{'station_id': '0000000', 'place_name': 'Nowhere'}]
        out = merge_coordinates(rows, {})
        self.assertEqual(out[0]['latitude'], '')
        self.assertEqual(out[0]['longitude'], '')

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/test_fetch_noaa_coordinates.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_noaa_coordinates'`.

- [ ] **Step 3: Write the script**

```python
# scripts/fetch_noaa_coordinates.py
"""Backfill latitude/longitude columns into app/tide_stations_new.csv from NOAA.

NOAA's Metadata API returns every tide-prediction station with lat/lng in one
call, so this needs no per-station requests. Run occasionally (and whenever new
US stations are added to the CSV) to refresh coordinates. Mirrors the Canadian
fallback-CSV pattern: coordinates ship as static data so the runtime has no hard
dependency on a live API.

Usage:
    python scripts/fetch_noaa_coordinates.py
"""
import csv
import logging
import os
import sys

import requests

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'app', 'tide_stations_new.csv')
NOAA_URL = ('https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/'
            'stations.json?type=tidepredictions')
OUTPUT_FIELDS = ['station_id', 'place_name', 'latitude', 'longitude']

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def fetch_noaa_coordinates(url=NOAA_URL):
    """Return {station_id: {'lat': float, 'lng': float}} from the NOAA MDAPI."""
    resp = requests.get(url, timeout=30, headers={'User-Agent': 'tidecalendar.xyz coordinate sync'})
    resp.raise_for_status()
    out = {}
    for s in resp.json().get('stations', []):
        sid, lat, lng = s.get('id'), s.get('lat'), s.get('lng')
        if sid is not None and lat is not None and lng is not None:
            out[str(sid)] = {'lat': float(lat), 'lng': float(lng)}
    return out


def merge_coordinates(rows, coords):
    """Pure transform: attach latitude/longitude to each CSV row.

    Unmatched stations get '' so the column stays present but empty (import
    code tolerates blanks).
    """
    merged = []
    for row in rows:
        c = coords.get(row['station_id'])
        merged.append({
            'station_id': row['station_id'],
            'place_name': row['place_name'],
            'latitude': c['lat'] if c else '',
            'longitude': c['lng'] if c else '',
        })
    return merged


def main():
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    logging.info("Read %d stations from CSV", len(rows))

    coords = fetch_noaa_coordinates()
    logging.info("Fetched %d coordinates from NOAA", len(coords))

    merged = merge_coordinates(rows, coords)
    matched = sum(1 for r in merged if r['latitude'] != '')
    logging.info("Matched %d/%d stations to coordinates", matched, len(merged))

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(merged)
    logging.info("Wrote %s", CSV_PATH)
    if matched < len(merged):
        logging.warning("%d stations had no NOAA coordinates", len(merged) - matched)
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/test_fetch_noaa_coordinates.py`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_noaa_coordinates.py scripts/test_fetch_noaa_coordinates.py
git commit -m "Add scripts/fetch_noaa_coordinates.py to bake US coords into CSV"
```

---

## Task 3: Run the script to populate the US CSV (data change)

**Files:**
- Modify: `app/tide_stations_new.csv`

- [ ] **Step 1: Run the fetch script**

Run: `python scripts/fetch_noaa_coordinates.py`
Expected log: `Matched 2132/2132 stations to coordinates` (count may grow over time).

- [ ] **Step 2: Verify the new columns**

Run: `head -2 app/tide_stations_new.csv`
Expected header: `station_id,place_name,latitude,longitude` and a data row with numeric lat/long.

- [ ] **Step 3: Commit**

```bash
git add app/tide_stations_new.csv
git commit -m "Bake latitude/longitude into tide_stations_new.csv"
```

---

## Task 4: Read coords in `import_stations_from_csv()`

**Files:**
- Modify: `app/database.py:197-260` (`import_stations_from_csv`)
- Test: `app/test_station_map.py`

The importer currently reads only `station_id`/`place_name`. Parse the new columns and persist them (INSERT + UPDATE), tolerating blanks. Keep the `INSERT OR IGNORE` + `UPDATE` two-step.

- [ ] **Step 1: Write the failing test**

```python
# app/test_station_map.py
import os, tempfile, unittest, csv
os.environ.setdefault('DB_PATH', os.path.join(tempfile.gettempdir(), 'test_station_map.db'))

import database


class ImportCoordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def _seed_csv(self, monkeypatch_rows):
        # write a tiny CSV next to the module and point the importer at it
        path = self.tmp.name + '.csv'
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['station_id', 'place_name', 'latitude', 'longitude'])
            w.writeheader()
            w.writerows(monkeypatch_rows)
        return path

    def test_import_persists_coordinates(self):
        import sqlite3
        rows = [{'station_id': '9449639', 'place_name': 'Point Roberts, WA',
                 'latitude': '48.97', 'longitude': '-123.07'}]
        csv_path = self._seed_csv(rows)
        database._import_us_csv(csv_path)  # helper extracted in Step 3
        with sqlite3.connect(database.DB_PATH) as conn:
            lat, lng = conn.execute(
                'SELECT latitude, longitude FROM tide_station_ids WHERE station_id=?',
                ('9449639',)).fetchone()
        self.assertAlmostEqual(lat, 48.97)
        self.assertAlmostEqual(lng, -123.07)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m unittest test_station_map.ImportCoordsTest -v`
Expected: FAIL — `AttributeError: module 'database' has no attribute '_import_us_csv'`.

- [ ] **Step 3: Refactor `import_stations_from_csv` to accept a path + parse coords**

In `app/database.py`, extract the import body into `_import_us_csv(csv_path)` and have `import_stations_from_csv()` call it with the default path. Add coord parsing mirroring the Canadian importer:

```python
def import_stations_from_csv():
    """Import US station data from the canonical CSV (sync DB to CSV)."""
    csv_path = os.path.join(os.path.dirname(__file__), 'tide_stations_new.csv')
    if not os.path.exists(csv_path):
        logging.warning(f"CSV file not found: {csv_path}")
        return False
    return _import_us_csv(csv_path)


def _parse_coord(value, station_id, place_name, kind):
    """Parse a CSV coordinate cell to float or None, tolerating blanks."""
    try:
        return float(value) if value and value.strip() else None
    except (ValueError, AttributeError):
        logging.warning(f"Invalid {kind} for station {station_id} ({place_name}): {value!r}")
        return None


def _import_us_csv(csv_path):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            MIN_STATION_THRESHOLD = 100
            result = cursor.execute(
                'SELECT COUNT(*) FROM tide_station_ids WHERE place_name IS NOT NULL').fetchone()
            if result[0] >= MIN_STATION_THRESHOLD:
                logging.debug(f"Station place names already populated (count: {result[0]})")
                return True

            imported_count = 0
            csv_station_ids = set()
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    station_id = row['station_id']
                    place_name = row['place_name']
                    csv_station_ids.add(station_id)
                    latitude = _parse_coord(row.get('latitude'), station_id, place_name, 'latitude')
                    longitude = _parse_coord(row.get('longitude'), station_id, place_name, 'longitude')

                    cursor.execute('''
                        INSERT OR IGNORE INTO tide_station_ids
                        (station_id, place_name, country, api_source, latitude, longitude, lookup_count, last_lookup)
                        VALUES (?, ?, 'USA', 'NOAA', ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name, latitude, longitude))
                    cursor.execute('''
                        UPDATE tide_station_ids
                        SET place_name = ?, country = 'USA', api_source = 'NOAA',
                            latitude = ?, longitude = ?
                        WHERE station_id = ?
                    ''', (place_name, latitude, longitude, station_id))
                    imported_count += 1

            if csv_station_ids:
                placeholders = ','.join('?' * len(csv_station_ids))
                cursor.execute(
                    f'DELETE FROM tide_station_ids WHERE country = \'USA\' AND station_id NOT IN ({placeholders})',
                    tuple(csv_station_ids))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logging.info(f"Removed {deleted_count} invalid station(s) not present in CSV")

            conn.commit()
            logging.info(f"Imported {imported_count} stations from CSV")
            return True
    except Exception as e:
        logging.error(f"Error importing stations from CSV: {e}")
        return False
```

Note the DELETE is now scoped to `country = 'USA'` so the US importer no longer deletes Canadian rows (it previously ran before the Canadian import, so this is safe and more correct).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m unittest test_station_map.ImportCoordsTest -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `cd app && python -m unittest discover -p 'test_*.py'`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/database.py app/test_station_map.py
git commit -m "Persist US station coordinates on CSV import"
```

---

## Task 5: `get_stations_with_coordinates()` DB helper

**Files:**
- Modify: `app/database.py` (add function near the other getters)
- Test: `app/test_station_map.py`

- [ ] **Step 1: Write the failing test**

```python
class StationsWithCoordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()
        import sqlite3
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country, latitude, longitude) "
                         "VALUES ('111','Has Coords','USA',47.6,-122.3)")
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country) "
                         "VALUES ('222','No Coords','USA')")
            conn.commit()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_excludes_null_coords(self):
        rows = database.get_stations_with_coordinates()
        ids = {r['station_id'] for r in rows}
        self.assertIn('111', ids)
        self.assertNotIn('222', ids)
        r = next(r for r in rows if r['station_id'] == '111')
        self.assertEqual(r['latitude'], 47.6)
        self.assertEqual(r['longitude'], -122.3)
        self.assertEqual(r['country'], 'USA')
        self.assertEqual(r['name'], 'Has Coords')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m unittest test_station_map.StationsWithCoordsTest -v`
Expected: FAIL — `AttributeError: ... 'get_stations_with_coordinates'`.

- [ ] **Step 3: Implement the helper**

```python
def get_stations_with_coordinates():
    """Return all stations that have non-NULL coordinates, for the map.

    Shape: [{'station_id', 'name', 'country', 'latitude', 'longitude'}].
    'name' uses the combined display label so the popup matches the autocomplete.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT station_id, place_name, country, latitude, longitude, alternative_name, province
                FROM tide_station_ids
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND place_name IS NOT NULL
            ''').fetchall()
            return [{
                'station_id': r[0],
                'name': format_display_name(r[1], r[5], r[6]),
                'country': r[2] or 'USA',
                'latitude': r[3],
                'longitude': r[4],
            } for r in rows]
    except sqlite3.Error as e:
        logging.error(f"Database error getting stations with coordinates: {e}")
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m unittest test_station_map.StationsWithCoordsTest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/database.py app/test_station_map.py
git commit -m "Add get_stations_with_coordinates() DB helper"
```

---

## Task 6: Startup self-heal — backfill missing US coordinates

**Files:**
- Create: `app/station_coordinates.py`
- Test: `app/test_station_map.py`
- Modify: `app/run.py`

On startup, find US stations with NULL coords. If any, make ONE NOAA MDAPI call and UPDATE just those. If none, make no call. All failures are logged and non-fatal.

- [ ] **Step 1: Write the failing test (mocked NOAA, no real network)**

```python
class BackfillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()
        import sqlite3
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country) "
                         "VALUES ('9449639','Point Roberts, WA','USA')")
            conn.commit()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_backfills_missing(self):
        import station_coordinates
        calls = []
        def fake_fetch(url=None):
            calls.append(url)
            return {'9449639': {'lat': 48.97, 'lng': -123.07}}
        n = station_coordinates.backfill_missing_coordinates(fetcher=fake_fetch)
        self.assertEqual(n, 1)
        self.assertEqual(len(calls), 1)
        info = database.get_station_info('9449639')
        self.assertAlmostEqual(info['latitude'], 48.97)

    def test_no_call_when_nothing_missing(self):
        import sqlite3, station_coordinates
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("UPDATE tide_station_ids SET latitude=1.0, longitude=2.0")
            conn.commit()
        calls = []
        station_coordinates.backfill_missing_coordinates(fetcher=lambda url=None: calls.append(url) or {})
        self.assertEqual(calls, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m unittest test_station_map.BackfillTest -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'station_coordinates'`.

- [ ] **Step 3: Implement the module**

```python
# app/station_coordinates.py
"""Startup self-heal: backfill coordinates for stations missing them.

The US CSV ships coordinates (see scripts/fetch_noaa_coordinates.py), but on a
warm production DB the CSV import short-circuits, so coordinates can be absent
there. This makes a single NOAA Metadata API call to fill any gaps. No-op (and
no network call) when nothing is missing. Always non-fatal.
"""
import logging
import sqlite3

from app.database import DB_PATH


def _default_fetcher(url=None):
    # Imported lazily so the script's requests dependency isn't required unless used.
    from scripts.fetch_noaa_coordinates import fetch_noaa_coordinates
    return fetch_noaa_coordinates()


def _missing_station_ids():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT station_id FROM tide_station_ids "
            "WHERE country = 'USA' AND (latitude IS NULL OR longitude IS NULL)"
        ).fetchall()
    return [r[0] for r in rows]


def backfill_missing_coordinates(fetcher=_default_fetcher):
    """Fill NULL coordinates for US stations. Returns the number updated."""
    try:
        missing = _missing_station_ids()
        if not missing:
            logging.info("Coordinate backfill: nothing missing, skipping NOAA call")
            return 0
        logging.info("Coordinate backfill: %d US stations missing coords; querying NOAA", len(missing))
        coords = fetcher()
        if not coords:
            logging.warning("Coordinate backfill: NOAA returned no coordinates")
            return 0
        updated = 0
        with sqlite3.connect(DB_PATH) as conn:
            for sid in missing:
                c = coords.get(sid)
                if c:
                    conn.execute(
                        "UPDATE tide_station_ids SET latitude=?, longitude=? WHERE station_id=?",
                        (c['lat'], c['lng'], sid))
                    updated += 1
            conn.commit()
        logging.info("Coordinate backfill: updated %d/%d stations", updated, len(missing))
        return updated
    except Exception as e:  # never fatal to startup
        logging.error("Coordinate backfill failed: %s", e)
        return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m unittest test_station_map.BackfillTest -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire into startup**

In `app/run.py`, add after the imports and after `import_canadian_stations_from_api()`:

```python
from app.station_coordinates import backfill_missing_coordinates
...
import_stations_from_csv()
import_canadian_stations_from_api()
backfill_missing_coordinates()
cleanup_previous_month_pdfs()
```

- [ ] **Step 6: Run full suite + commit**

Run: `cd app && python -m unittest discover -p 'test_*.py'`
Expected: all pass.

```bash
git add app/station_coordinates.py app/run.py app/test_station_map.py
git commit -m "Backfill missing US coordinates at startup (one NOAA call, non-fatal)"
```

---

## Task 7: `/api/stations.geojson` route

**Files:**
- Modify: `app/routes.py` (import + new route)
- Test: `app/test_station_map.py`

Serve a memoized GeoJSON FeatureCollection of all coord-bearing stations.

- [ ] **Step 1: Write the failing test**

```python
class GeoJsonRouteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()
        import sqlite3
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country, latitude, longitude) "
                         "VALUES ('9449639','Point Roberts, WA','USA',48.97,-123.07)")
            conn.commit()
        import routes
        routes._stations_geojson_cache = None  # reset memoization
        self.client = routes.app.test_client()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_returns_feature_collection(self):
        resp = self.client.get('/api/stations.geojson')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertEqual(len(data['features']), 1)
        f = data['features'][0]
        self.assertEqual(f['geometry']['type'], 'Point')
        self.assertEqual(f['geometry']['coordinates'], [-123.07, 48.97])  # [lng, lat]
        self.assertEqual(f['properties']['station_id'], '9449639')
        self.assertEqual(f['properties']['country'], 'USA')
```

Note: `app/test_station_map.py` already imports `database`; add `import routes` inside this test's setUp (routes imports the app). Ensure tests set `DB_PATH` before importing `routes` — since `routes`→`database` is already imported module-level by earlier tests, reset `database.DB_PATH` in setUp (done) and rely on `get_stations_with_coordinates()` reading the current `database.DB_PATH` at call time (it does).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m unittest test_station_map.GeoJsonRouteTest -v`
Expected: FAIL — 404 (route not defined).

- [ ] **Step 3: Implement the route**

In `app/routes.py`, add `get_stations_with_coordinates` to the `from app.database import (...)` block, and add:

```python
_stations_geojson_cache = None


@app.route('/api/stations.geojson')
def api_stations_geojson():
    """GeoJSON FeatureCollection of all selectable stations that have coordinates.

    Memoized in-process: the station set is static per container. Only stations
    present in the directory appear, so a pin click can never hit an unknown
    station.
    """
    global _stations_geojson_cache
    if _stations_geojson_cache is None:
        features = [{
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [s['longitude'], s['latitude']]},
            'properties': {
                'station_id': s['station_id'],
                'name': s['name'],
                'country': s['country'],
            },
        } for s in get_stations_with_coordinates()]
        _stations_geojson_cache = {'type': 'FeatureCollection', 'features': features}
    return jsonify(_stations_geojson_cache)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m unittest test_station_map.GeoJsonRouteTest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py app/test_station_map.py
git commit -m "Add /api/stations.geojson endpoint (memoized)"
```

---

## Task 8: Frontend — map container, styles, includes

**Files:**
- Modify: `app/templates/index.html` (head_extra CSS + map div + scripts include)
- Modify: `app/static/style.css`

- [ ] **Step 1: Add Leaflet CSS to `head_extra` in `index.html`**

Append inside the existing `{% block head_extra %}` (before `{% endblock %}`):

```html
    <!-- Leaflet (vendored) for the station map -->
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/leaflet/leaflet.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/leaflet/MarkerCluster.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/leaflet/MarkerCluster.Default.css') }}">
```

- [ ] **Step 2: Add the map container** between the `</figure>` (line ~45) and the `<section class="card form-card">`:

```html
        <section class="card map-card">
            <h2>Find a station on the map</h2>
            <p class="section-subtitle">Click a pin, then "Use this station" to fill the form below. The country filter zooms the map.</p>
            <div id="station-map" aria-label="Map of available tide stations"></div>
        </section>
```

- [ ] **Step 3: Add styles to `app/static/style.css`** (append):

```css
.map-card { padding-bottom: 1rem; }
#station-map {
    width: 100%;
    height: 420px;
    border-radius: 8px;
    z-index: 0; /* keep tiles under the autocomplete dropdown */
}
@media (max-width: 600px) {
    #station-map { height: 300px; }
}
.station-popup .popup-name { font-weight: 600; display: block; margin-bottom: 2px; }
.station-popup .popup-meta { color: #666; font-size: 0.85em; }
.station-popup button {
    margin-top: 8px; cursor: pointer; width: 100%;
}
```

- [ ] **Step 4: Add the script includes** at the top of `{% block scripts %}` in `index.html`, BEFORE the existing `<script>`:

```html
    <script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>
    <script src="{{ url_for('static', filename='vendor/leaflet/leaflet.markercluster.js') }}"></script>
    <script src="{{ url_for('static', filename='js/station_map.js') }}" defer></script>
```

- [ ] **Step 5: Manual check (placeholder until JS exists)**

Run the app (`cd app && flask run --port 5001`) and load `/`. Expected: an empty bordered map box renders (tiles appear after Task 9 JS). No console errors about missing Leaflet.

- [ ] **Step 6: Commit**

```bash
git add app/templates/index.html app/static/style.css
git commit -m "Add station map container, styles, and Leaflet includes"
```

---

## Task 9: Frontend — map behavior (`station_map.js`)

**Files:**
- Create: `app/static/js/station_map.js`
- Modify: `app/templates/index.html` (call country hook from the radio change handler)

Behavior: fetch geojson, build a markercluster of `circleMarker` pins colored by country, bind popups with a "Use this station" button that fills the form and scrolls to it, and expose `window.tideMap.showCountry(country)` to filter + re-fit. Re-fit uses the filtered markers' bounds (no hardcoded country boxes).

- [ ] **Step 1: Implement `station_map.js`**

```javascript
// app/static/js/station_map.js
// Embedded Leaflet map of selectable tide stations. Pins fill the existing form.
(function () {
  'use strict';

  var COUNTRY_COLORS = { USA: '#1f6feb', Canada: '#d1242f' };

  function fillForm(stationId, name) {
    var search = document.getElementById('station_search');
    var hidden = document.getElementById('station_id');
    if (!search || !hidden) return;
    search.value = name + ' (' + stationId + ')';
    hidden.value = stationId;
    document.querySelector('.form-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
    var year = document.getElementById('year');
    if (year) year.focus();
    if (window.plausible) {
      plausible('Map Station Selected', { props: { station_id: stationId, place_name: name } });
    }
  }
  window._tideMapFillForm = fillForm; // exposed for popup button + e2e

  function popupHtml(props) {
    var div = document.createElement('div');
    div.className = 'station-popup';
    var name = document.createElement('span');
    name.className = 'popup-name';
    name.textContent = props.name;
    var meta = document.createElement('span');
    meta.className = 'popup-meta';
    meta.textContent = props.country + ' · ' + props.station_id;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'quick-generate-btn';
    btn.textContent = 'Use this station';
    btn.addEventListener('click', function () { fillForm(props.station_id, props.name); });
    div.appendChild(name); div.appendChild(meta); div.appendChild(btn);
    return div;
  }

  function init() {
    var el = document.getElementById('station-map');
    if (!el || typeof L === 'undefined') return;

    var map = L.map(el, { scrollWheelZoom: false }).setView([45, -100], 3);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    var clusters = L.markerClusterGroup({ chunkedLoading: true });
    map.addLayer(clusters);

    var markersByCountry = { USA: [], Canada: [] };

    function rebuild(country) {
      clusters.clearLayers();
      var show = [];
      Object.keys(markersByCountry).forEach(function (c) {
        if (country === 'all' || country === c) show = show.concat(markersByCountry[c]);
      });
      clusters.addLayers(show);
      if (show.length) {
        var group = L.featureGroup(show);
        map.fitBounds(group.getBounds().pad(0.1));
      }
    }

    window.tideMap = { showCountry: rebuild };

    fetch('/api/stations.geojson')
      .then(function (r) { return r.json(); })
      .then(function (geo) {
        geo.features.forEach(function (f) {
          var p = f.properties;
          var coords = f.geometry.coordinates; // [lng, lat]
          var color = COUNTRY_COLORS[p.country] || '#666';
          var marker = L.circleMarker([coords[1], coords[0]], {
            radius: 5, color: color, weight: 1, fillColor: color, fillOpacity: 0.7,
          });
          marker.bindPopup(function () { return popupHtml(p); });
          (markersByCountry[p.country] || (markersByCountry[p.country] = [])).push(marker);
        });
        // Respect the current country filter selection on first paint.
        var checked = document.querySelector('input[name="country_filter"]:checked');
        rebuild(checked ? checked.value : 'all');
      })
      .catch(function (e) {
        console.error('Failed to load station map data:', e);
        el.innerHTML = '<p style="padding:1rem">Map data could not be loaded.</p>';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Hook the country filter** — in `index.html`, inside the existing `radio.addEventListener('change', ...)` in `initializeCountryFilter()` (after `reloadPopularStations();`), add:

```javascript
                    // Re-fit / filter the station map to the selected country
                    if (window.tideMap) {
                        window.tideMap.showCountry(selectedCountry);
                    }
```

- [ ] **Step 3: Manual verification in browser**

Run `cd app && flask run --port 5001`, open `/`:
- Map shows clustered pins across North America.
- Selecting "🇺🇸 USA" zooms to the US and shows only US pins; "🇨🇦 Canada" zooms to Canada; "All" shows both.
- Click a pin → popup → "Use this station" fills the search box as `Name (id)`, sets hidden `station_id`, scrolls to form.
- Submitting the form generates the PDF as before.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/station_map.js app/templates/index.html
git commit -m "Add station map behavior: clustered pins, popup-to-form, country re-fit"
```

---

## Task 10: Dockerfile — ship the new static assets

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Inspect how static/ is copied**

Run: `grep -n "COPY\|static" Dockerfile`
Determine whether `app/static/` is copied as a tree (then vendor/ and js/ are already included) or file-by-file.

- [ ] **Step 2: Ensure vendor + js are included**

If static is copied wholesale (e.g. `COPY app/ /app/` or `COPY app/static/ .../static/`), no change needed — note it. If individual files are listed, add:

```dockerfile
COPY app/static/vendor/ ./static/vendor/
COPY app/static/js/ ./static/js/
```

(Match the existing COPY style/paths in the file.)

- [ ] **Step 3: Build to verify**

Run: `docker build -t tide-calendar-app . && docker run --rm tide-calendar-app ls static/vendor/leaflet static/js`
Expected: lists the 5 leaflet files and `station_map.js`.
(If colima/docker isn't running, start it first: `colima start`.)

- [ ] **Step 4: Commit (only if Dockerfile changed)**

```bash
git add Dockerfile
git commit -m "Ship vendored Leaflet + station_map.js in Docker image"
```

---

## Task 11: Playwright e2e

**Files:**
- Create: `tests/station-map.spec.ts`

- [ ] **Step 1: Write the test**

```typescript
import { test, expect } from '@playwright/test';

test('station map renders and a pin fills the form', async ({ page }) => {
  await page.goto('/');
  // Map container present and Leaflet initialized (tile layer attached)
  const map = page.locator('#station-map');
  await expect(map).toBeVisible();
  await expect(map.locator('.leaflet-tile-pane')).toBeAttached();

  // Drive the fill-form path directly (clicking a specific clustered pin is flaky).
  await page.evaluate(() => window._tideMapFillForm('9449639', 'Point Roberts, WA'));
  await expect(page.locator('#station_id')).toHaveValue('9449639');
  await expect(page.locator('#station_search')).toHaveValue('Point Roberts, WA (9449639)');
});

test('country filter re-fits the map without errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('/');
  await expect(page.locator('#station-map .leaflet-tile-pane')).toBeAttached();
  // Country radios are visually hidden pills — click the parent label (see CLAUDE.md).
  await page.locator('#country_usa').locator('xpath=..').click();
  await page.waitForTimeout(500);
  expect(errors).toEqual([]);
});
```

- [ ] **Step 2: Run against local dev server**

Run: `cd app && flask run --port 5001 &` then `cd tests && npx playwright test station-map.spec.ts`
Expected: both tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/station-map.spec.ts
git commit -m "Add Playwright e2e for station map"
```

---

## Task 12: Docs

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Document the new script + endpoint**

Add to the Maintenance Scripts section a subsection for `scripts/fetch_noaa_coordinates.py` (what it does, when to run: whenever US stations are added), and note in Important Notes:
- `/api/stations.geojson` serves all coord-bearing stations for the homepage map (memoized in-process).
- US coordinates ship in `tide_stations_new.csv`; `app/station_coordinates.py` backfills any missing ones at startup with one NOAA call.
- Map uses vendored Leaflet + markercluster in `app/static/vendor/leaflet/`; pins are `circleMarker` (no marker-image assets needed).

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Document station map: fetch script, geojson endpoint, startup backfill"
```

---

## Self-Review (completed)

- **Spec coverage:** data layer (Tasks 2–6), backend endpoint (7), frontend embed + interaction + country re-fit (8–9), Docker (10), tests (4–7,11), docs (12). CSP item dropped — verified no CSP exists in `__init__.py`; recorded in docs instead.
- **Type consistency:** `merge_coordinates`/`fetch_noaa_coordinates` reused by `station_coordinates`; geojson `properties` keys (`station_id`,`name`,`country`) match `get_stations_with_coordinates()` and `station_map.js`. `window.tideMap.showCountry` defined in Task 9, called in Task 9 Step 2. `_tideMapFillForm` defined in Task 9, used in Task 11.
- **Placeholders:** none — all code blocks complete.
- **Risk note:** Task 4 changes the US importer's DELETE to be USA-scoped (was global). Verified safe: Canadian import runs after and has its own sync; full suite run in Task 4 Step 5 guards regressions.
```
