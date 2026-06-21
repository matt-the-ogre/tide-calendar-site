# Sunrise/Sunset + Local Times Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each day of the downloaded PDF calendar shows a local-time `Rise HH:MM  Set HH:MM` line, and all tide times render in the station's local timezone (CHS converted UTC→local; NOAA already local).

**Architecture:** Precompute each station's IANA timezone offline (timezonefinder) and bake it into the CSVs; a light startup sync copies it into the warm DB. At PDF-generation time, `sun_times.py` converts CHS tide times to local and computes sunrise/sunset (astral + zoneinfo); `get_tides` writes the sun line into the pcal events file.

**Tech Stack:** Python 3.12, astral (runtime), timezonefinder (dev script only), stdlib zoneinfo, pcal/ghostscript.

**Test command:** `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`

---

## File Structure

**Create:**
- `app/sun_times.py` — timezone logic: `sun_times_for_month()`, `format_sun_line()`, `localize_and_filter_csv()`
- `app/test_sun_times.py` — unit tests for the above
- `scripts/fetch_station_timezones.py` — offline: bake `timezone` column into both CSVs
- `scripts/test_fetch_station_timezones.py` — unit test for the pure transform

**Modify:**
- `requirements.txt` — add `astral`
- `app/tide_stations_new.csv`, `app/canadian_tide_stations.csv` — gain `timezone` column (data)
- `app/database.py` — migrate `timezone` column; read it on import; `get_station_info` returns it; add `backfill_timezones_from_csv()`
- `app/run.py` — call `backfill_timezones_from_csv()` at startup
- `app/tide_adapters.py` — CHS fetch padded ±1 day (UTC)
- `app/get_tides.py` — localize CHS times, compute sun times, write sun line in pcal
- `Dockerfile` — `COPY app/sun_times.py`
- `CLAUDE.md` — document the script + feature

---

## Task 1: Add the astral runtime dependency

**Files:** Modify: `requirements.txt`

- [ ] **Step 1: Add astral** — append to `requirements.txt`:

```
astral==3.2
```

- [ ] **Step 2: Install into the venv**

Run: `venv/bin/pip install astral==3.2`
Expected: installs cleanly (no compiled deps).

- [ ] **Step 3: Verify import + Python compat**

Run: `venv/bin/python -c "import astral, astral.sun; print('astral', astral.__version__ if hasattr(astral,'__version__') else 'ok')"`
Expected: prints ok / a version, no error. (astral 3.2 requires_python `>=3.7,<4.0` — fine for the 3.12 base image.)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "Add astral dependency for sunrise/sunset computation"
```

---

## Task 2: Timezone-baking script (`fetch_station_timezones.py`)

**Files:**
- Create: `scripts/fetch_station_timezones.py`
- Create: `scripts/test_fetch_station_timezones.py`

The pure transform (`add_timezone_column`) takes CSV rows + a lookup function and returns rows with a `timezone` field. The script wires it to `timezonefinder` and rewrites both CSVs.

- [ ] **Step 1: Write the failing test**

```python
# scripts/test_fetch_station_timezones.py
import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from fetch_station_timezones import add_timezone_column

class AddTimezoneColumnTest(unittest.TestCase):
    def test_adds_timezone_from_lookup(self):
        rows = [{'station_id': '9449639', 'place_name': 'Point Roberts, WA',
                 'latitude': '48.97', 'longitude': '-123.07'}]
        # fake lookup: ignores inputs, returns a fixed zone
        out = add_timezone_column(rows, lambda lat, lng: 'America/Vancouver')
        self.assertEqual(out[0]['timezone'], 'America/Vancouver')
        self.assertEqual(out[0]['station_id'], '9449639')  # original fields preserved

    def test_blank_when_lookup_returns_none(self):
        rows = [{'station_id': 'x', 'place_name': 'Ocean', 'latitude': '', 'longitude': ''}]
        out = add_timezone_column(rows, lambda lat, lng: None)
        self.assertEqual(out[0]['timezone'], '')

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/test_fetch_station_timezones.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_station_timezones'`.

- [ ] **Step 3: Write the script**

```python
# scripts/fetch_station_timezones.py
"""Bake an IANA `timezone` column into the station CSVs from each station's
lat/long, using timezonefinder.

Dev-only: timezonefinder is heavy (numpy/h3) and is NOT a runtime dependency.
Runtime uses the baked column via stdlib zoneinfo. Mirrors the coordinate /
province precompute pattern.

Usage:
    pip install timezonefinder
    python scripts/fetch_station_timezones.py
"""
import csv
import logging
import os
import sys

APP_DIR = os.path.join(os.path.dirname(__file__), '..', 'app')
US_CSV = os.path.join(APP_DIR, 'tide_stations_new.csv')
CA_CSV = os.path.join(APP_DIR, 'canadian_tide_stations.csv')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def add_timezone_column(rows, lookup):
    """Pure transform: set row['timezone'] = lookup(lat, lng) (or '' if None).

    lookup takes (lat: float|None, lng: float|None) and returns an IANA tz or None.
    """
    out = []
    for row in rows:
        try:
            lat = float(row['latitude']) if row.get('latitude') else None
            lng = float(row['longitude']) if row.get('longitude') else None
        except (TypeError, ValueError):
            lat = lng = None
        tz = lookup(lat, lng) if (lat is not None and lng is not None) else None
        new = dict(row)
        new['timezone'] = tz or ''
        out.append(new)
    return out


def _rewrite_csv(path, lookup):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    merged = add_timezone_column(rows, lookup)
    if 'timezone' not in fieldnames:
        fieldnames.append('timezone')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(merged)
    matched = sum(1 for r in merged if r['timezone'])
    logging.info("%s: %d/%d rows got a timezone", os.path.basename(path), matched, len(merged))


def main():
    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()

    def lookup(lat, lng):
        return tf.timezone_at(lat=lat, lng=lng)

    for path in (US_CSV, CA_CSV):
        _rewrite_csv(path, lookup)
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/test_fetch_station_timezones.py`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_station_timezones.py scripts/test_fetch_station_timezones.py
git commit -m "Add scripts/fetch_station_timezones.py to bake IANA tz into CSVs"
```

---

## Task 3: Run the script to bake timezones (data change)

**Files:** Modify: `app/tide_stations_new.csv`, `app/canadian_tide_stations.csv`

- [ ] **Step 1: Install timezonefinder (dev only) and run**

```bash
venv/bin/pip install timezonefinder
venv/bin/python scripts/fetch_station_timezones.py
```
Expected: logs like `tide_stations_new.csv: 2132/2132 rows got a timezone` and a similar line for the Canadian CSV (a few ocean/edge points may be blank — acceptable).

- [ ] **Step 2: Verify the new column**

Run: `head -2 app/tide_stations_new.csv && echo '---' && head -2 app/canadian_tide_stations.csv`
Expected: both headers now end with `,timezone`; data rows show IANA zones (e.g. `America/Los_Angeles`, `America/Vancouver`).

- [ ] **Step 3: Spot-check a known station**

Run: `venv/bin/python -c "import csv; rows={r['station_id']:r for r in csv.DictReader(open('app/tide_stations_new.csv'))}; print(rows['9449639']['timezone'])"`
Expected: `America/Vancouver` (Point Roberts, WA sits in the Vancouver zone) or `America/Los_Angeles` — either is a valid Pacific zone; just confirm it's a real `America/...` value.

- [ ] **Step 4: Commit**

```bash
git add app/tide_stations_new.csv app/canadian_tide_stations.csv
git commit -m "Bake IANA timezone column into station CSVs"
```

---

## Task 4: DB — timezone column, import, get_station_info, startup backfill

**Files:**
- Modify: `app/database.py`
- Modify: `app/run.py`
- Test: `app/test_sun_times.py` (DB-facing tests live here for this feature)

- [ ] **Step 1: Write the failing tests**

```python
# app/test_sun_times.py
import os, sqlite3, tempfile, unittest, csv

import database


class TimezoneDBTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_station_info_returns_timezone(self):
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country, timezone) "
                         "VALUES ('9449639','Point Roberts, WA','USA','America/Vancouver')")
            conn.commit()
        info = database.get_station_info('9449639')
        self.assertEqual(info['timezone'], 'America/Vancouver')

    def test_backfill_timezones_from_csv(self):
        # row exists with NULL timezone; a CSV provides one
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country) "
                         "VALUES ('07735','Vancouver, BC','Canada')")
            conn.commit()
        csv_path = self.tmp.name + '.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['station_id', 'timezone'])
            w.writeheader()
            w.writerow({'station_id': '07735', 'timezone': 'America/Vancouver'})
        n = database.backfill_timezones_from_csv([csv_path])
        self.assertEqual(n, 1)
        self.assertEqual(database.get_station_info('07735')['timezone'], 'America/Vancouver')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.TimezoneDBTest -v`
Expected: FAIL — `get_station_info` has no `timezone` key / no `backfill_timezones_from_csv`.

- [ ] **Step 3a: Add the column to the migration** — in `app/database.py`, in `init_database`'s `_migrate_columns(cursor, 'tide_station_ids', {...})` dict, add:

```python
                'timezone': 'TEXT',
```

- [ ] **Step 3b: Return timezone from `get_station_info`** — change its SELECT and dict:

```python
            result = cursor.execute('''
                SELECT station_id, place_name, country, api_source, latitude, longitude, province, timezone
                FROM tide_station_ids
                WHERE station_id = ?
            ''', (station_id,)).fetchone()

            if result:
                return {
                    'station_id': result[0],
                    'place_name': result[1],
                    'country': result[2] if result[2] else 'USA',
                    'api_source': result[3] if result[3] else 'NOAA',
                    'latitude': result[4],
                    'longitude': result[5],
                    'province': result[6],
                    'timezone': result[7],
                }
```

- [ ] **Step 3c: Read timezone in the US importer** — in `_import_us_csv`, parse it and include in both statements:

```python
                    station_id = row['station_id']
                    place_name = row['place_name']
                    csv_station_ids.add(station_id)
                    latitude = _parse_coord(row.get('latitude'), station_id, place_name, 'latitude')
                    longitude = _parse_coord(row.get('longitude'), station_id, place_name, 'longitude')
                    tz = (row.get('timezone') or '').strip() or None

                    cursor.execute('''
                        INSERT OR IGNORE INTO tide_station_ids
                        (station_id, place_name, country, api_source, latitude, longitude, timezone, lookup_count, last_lookup)
                        VALUES (?, ?, 'USA', 'NOAA', ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name, latitude, longitude, tz))
                    cursor.execute('''
                        UPDATE tide_station_ids
                        SET place_name = ?, country = 'USA', api_source = 'NOAA',
                            latitude = ?, longitude = ?, timezone = COALESCE(?, timezone)
                        WHERE station_id = ?
                    ''', (place_name, latitude, longitude, tz, station_id))
                    imported_count += 1
```

- [ ] **Step 3d: Read timezone in the Canadian CSV importer** — in `import_canadian_stations_from_csv`, after `alternative_name = row.get('alternative_name') or None`, add `tz = (row.get('timezone') or '').strip() or None` and add `timezone` to the INSERT column list/values and the UPDATE `SET` (use `timezone = COALESCE(?, timezone)`), mirroring Step 3c. Full INSERT becomes:

```python
                    cursor.execute('''
                        INSERT OR IGNORE INTO tide_station_ids
                        (station_id, place_name, country, api_source, latitude, longitude, province, alternative_name, timezone, lookup_count, last_lookup)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (station_id, place_name, country, api_source, latitude, longitude, province, alternative_name, tz))
                    cursor.execute('''
                        UPDATE tide_station_ids
                        SET place_name = ?, country = ?, api_source = ?, latitude = ?, longitude = ?, province = ?, alternative_name = ?, timezone = COALESCE(?, timezone)
                        WHERE station_id = ?
                    ''', (place_name, country, api_source, latitude, longitude, province, alternative_name, tz, station_id))
```

- [ ] **Step 3e: Add `backfill_timezones_from_csv`** — add to `app/database.py`:

```python
def backfill_timezones_from_csv(csv_paths=None):
    """Fill NULL/empty `timezone` on existing DB rows from the shipped CSVs.

    Needed because the US CSV import short-circuits on a warm DB, and Canadian
    stations imported via the live CHS API have no timezone. Source is the
    shipped CSV (no network, no heavy library). Idempotent. Returns rows updated.
    """
    if csv_paths is None:
        here = os.path.dirname(__file__)
        csv_paths = [os.path.join(here, 'tide_stations_new.csv'),
                     os.path.join(here, 'canadian_tide_stations.csv')]
    updated = 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            for path in csv_paths:
                if not os.path.exists(path):
                    continue
                with open(path, 'r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        tz = (row.get('timezone') or '').strip()
                        sid = row.get('station_id')
                        if not tz or not sid:
                            continue
                        cur = conn.execute(
                            "UPDATE tide_station_ids SET timezone = ? "
                            "WHERE station_id = ? AND (timezone IS NULL OR timezone = '')",
                            (tz, sid))
                        updated += cur.rowcount
            conn.commit()
        logging.info("Timezone backfill: set timezone on %d station(s)", updated)
        return updated
    except (sqlite3.Error, OSError) as e:
        logging.error("Timezone backfill failed: %s", e)
        return updated
```

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.TimezoneDBTest -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire into startup** — in `app/run.py`, add after `backfill_missing_coordinates()`:

```python
from app.database import backfill_timezones_from_csv
...
backfill_missing_coordinates()
backfill_timezones_from_csv()
cleanup_previous_month_pdfs()
```

- [ ] **Step 6: Full suite + commit**

Run: `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`
Expected: all pass.

```bash
git add app/database.py app/run.py app/test_sun_times.py
git commit -m "DB: timezone column, import, get_station_info, startup backfill"
```

---

## Task 5: `sun_times.py` — sunrise/sunset computation

**Files:**
- Create: `app/sun_times.py`
- Test: `app/test_sun_times.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
class SunTimesTest(unittest.TestCase):
    def test_point_roberts_june(self):
        import sun_times
        m = sun_times.sun_times_for_month(48.97, -123.07, 'America/Vancouver', 2026, 6)
        self.assertEqual(len(m), 30)
        rise, sset = m[15]  # mid-June
        # 24h "HH:MM" strings; sunrise early morning, sunset late evening (PDT)
        self.assertRegex(rise, r'^\d{2}:\d{2}$')
        self.assertRegex(sset, r'^\d{2}:\d{2}$')
        self.assertIn(int(rise[:2]), range(4, 7))    # ~05:xx
        self.assertIn(int(sset[:2]), range(20, 23))  # ~21:xx

    def test_polar_day_returns_note(self):
        import sun_times
        m = sun_times.sun_times_for_month(78.0, 15.0, 'Arctic/Longyearbyen', 2026, 6)
        self.assertEqual(m[15], '24h daylight')

    def test_missing_tz_returns_empty(self):
        import sun_times
        self.assertEqual(sun_times.sun_times_for_month(48.0, -123.0, None, 2026, 6), {})

    def test_format_sun_line(self):
        import sun_times
        self.assertEqual(sun_times.format_sun_line(('05:14', '21:09')), 'Rise 05:14  Set 21:09')
        self.assertEqual(sun_times.format_sun_line('24h daylight'), 'Sun: 24h daylight')
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.SunTimesTest -v`
Expected: FAIL — no module `sun_times`.

- [ ] **Step 3: Implement `sun_times.py`**

```python
# app/sun_times.py
"""Local-timezone helpers for the PDF calendar: sunrise/sunset computation and
CHS UTC->local tide-time conversion.

Runtime deps: astral (pure-Python) + stdlib zoneinfo. The IANA timezone per
station is precomputed offline (scripts/fetch_station_timezones.py) and read
from the DB; nothing here needs timezonefinder.
"""
import calendar as _calendar
import logging
from datetime import date as _date, datetime as _datetime, timezone as _utc
from zoneinfo import ZoneInfo

from astral import Observer
from astral import sun as _astral_sun


def _zone(iana_tz):
    try:
        return ZoneInfo(iana_tz) if iana_tz else None
    except Exception:
        logging.warning("Unknown timezone %r", iana_tz)
        return None


def _day_sun(observer, d, tz):
    """Return ("HH:MM" rise, "HH:MM" set) or a polar note string for one day."""
    try:
        rise = _astral_sun.sunrise(observer, date=d, tzinfo=tz)
        sset = _astral_sun.sunset(observer, date=d, tzinfo=tz)
        return (rise.strftime('%H:%M'), sset.strftime('%H:%M'))
    except ValueError:
        # Polar day or night: classify by solar elevation at local noon.
        noon = _datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz)
        try:
            up = _astral_sun.elevation(observer, noon) > 0
        except Exception:
            return '24h daylight'  # benign default; extremely rare
        return '24h daylight' if up else 'polar night'


def sun_times_for_month(lat, lng, iana_tz, year, month):
    """{day:int -> ("HH:MM","HH:MM") | note str}. Empty dict if tz/coords missing."""
    tz = _zone(iana_tz)
    if lat is None or lng is None or tz is None:
        return {}
    observer = Observer(latitude=lat, longitude=lng)
    _, last = _calendar.monthrange(year, month)
    return {day: _day_sun(observer, _date(year, month, day), tz)
            for day in range(1, last + 1)}


def format_sun_line(value):
    """Render a day's sun value as the pcal cell text."""
    if isinstance(value, tuple):
        return f"Rise {value[0]}  Set {value[1]}"
    return f"Sun: {value}"


def localize_and_filter_csv(csv_data, api_source, iana_tz, year, month):
    """Convert CHS (UTC) tide rows to local time and keep only the target local
    month. NOAA rows (already local) pass through unchanged.

    csv_data: header line + `YYYY-MM-DD HH:MM,value,Type` rows.
    """
    if (api_source or '').upper() != 'CHS':
        return csv_data  # NOAA times are already local

    tz = _zone(iana_tz)
    lines = csv_data.splitlines()
    if not lines:
        return csv_data
    header, body = lines[0], lines[1:]
    out = [header]
    for line in body:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) != 3:
            continue
        dt_str, value, ttype = parts
        try:
            naive = _datetime.strptime(dt_str.strip(), '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        if tz is None:
            # No timezone known: keep UTC times but still drop the ±1-day pad so
            # the month is bounded (status-quo behaviour, minus the pad rows).
            local = naive
        else:
            local = naive.replace(tzinfo=_utc).astimezone(tz)
        if local.year == year and local.month == month:
            out.append(f"{local.strftime('%Y-%m-%d %H:%M')},{value},{ttype}")
    return '\n'.join(out)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.SunTimesTest -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/sun_times.py app/test_sun_times.py
git commit -m "Add sun_times: sunrise/sunset + CHS UTC->local conversion"
```

---

## Task 6: Test CHS localization + filtering

**Files:** Test: `app/test_sun_times.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
class LocalizeCsvTest(unittest.TestCase):
    HEADER = 'Date Time,Prediction,Type'

    def test_chs_converts_and_crosses_midnight(self):
        import sun_times
        csv_in = self.HEADER + '\n2026-06-15 05:23,4.8,H'  # UTC
        out = sun_times.localize_and_filter_csv(csv_in, 'CHS', 'America/Vancouver', 2026, 6)
        # 05:23Z -> 22:23 the previous local day (PDT, UTC-7)
        self.assertIn('2026-06-14 22:23,4.8,H', out)

    def test_chs_recovers_last_day_evening_and_drops_prev_month(self):
        import sun_times
        csv_in = (self.HEADER
                  + '\n2026-06-01 02:00,1.0,L'    # -> 2026-05-31 19:00 local: DROP
                  + '\n2026-07-01 04:00,2.0,H')   # -> 2026-06-30 21:00 local: KEEP
        out = sun_times.localize_and_filter_csv(csv_in, 'CHS', 'America/Vancouver', 2026, 6)
        self.assertNotIn('05-31', out)
        self.assertIn('2026-06-30 21:00,2.0,H', out)

    def test_noaa_passthrough(self):
        import sun_times
        csv_in = self.HEADER + '\n2026-06-15 05:23,4.8,H'
        self.assertEqual(sun_times.localize_and_filter_csv(csv_in, 'NOAA', None, 2026, 6), csv_in)
```

- [ ] **Step 2: Run to verify pass** (implementation already exists from Task 5)

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.LocalizeCsvTest -v`
Expected: PASS (3 tests). (If `test_noaa_passthrough` or conversion fails, fix `localize_and_filter_csv` in `sun_times.py`, not the test.)

- [ ] **Step 3: Commit**

```bash
git add app/test_sun_times.py
git commit -m "Test CHS UTC->local conversion, month filtering, NOAA passthrough"
```

---

## Task 7: CHS fetch padded ±1 day (UTC)

**Files:**
- Modify: `app/tide_adapters.py` (`CHSAdapter.get_predictions`)
- Test: `app/test_tide_adapters.py` (append) — or `app/test_sun_times.py` if simpler

The padded window lets Task 6's local-month filter recover edge events. Compute the padded UTC range from the month.

- [ ] **Step 1: Write the failing test** (append to `app/test_tide_adapters.py`)

```python
class CHSPaddingTest(unittest.TestCase):
    def test_get_predictions_pads_one_day(self):
        import tide_adapters
        from unittest import mock
        captured = {}

        class FakeResp:
            status_code = 200
            text = '[]'
        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith('/data'):
                captured['params'] = params
            return FakeResp()

        a = tide_adapters.CHSAdapter()
        with mock.patch.object(a, '_lookup_station_uuid', return_value='uuid'), \
             mock.patch('tide_adapters.requests.get', side_effect=fake_get):
            a.get_predictions('07735', 2026, 6)
        # June 2026: padded from May 31 to July 1 (UTC)
        self.assertEqual(captured['params']['from'], '2026-05-31T00:00:00Z')
        self.assertEqual(captured['params']['to'], '2026-07-01T23:59:59Z')
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_tide_adapters.CHSPaddingTest -v`
Expected: FAIL — current `from`/`to` are the exact month bounds.

- [ ] **Step 3: Implement padding** — in `CHSAdapter.get_predictions`, replace the `from_date`/`to_date` construction:

```python
        # Calculate date range for the month, padded ±1 day in UTC. The pad lets
        # the local-month filter (sun_times.localize_and_filter_csv) recover
        # events that fall in the target LOCAL month but land in an adjacent UTC
        # day after UTC->local conversion (west-of-UTC stations lose late-evening
        # tides on the last day otherwise).
        from datetime import date as _date, timedelta as _timedelta
        _, last_day = calendar.monthrange(year, month)
        pad_from = _date(year, month, 1) - _timedelta(days=1)
        pad_to = _date(year, month, last_day) + _timedelta(days=1)
        from_date = pad_from.strftime('%Y-%m-%dT00:00:00Z')
        to_date = pad_to.strftime('%Y-%m-%dT23:59:59Z')
```

(Remove the now-duplicate `_, last_day = calendar.monthrange(year, month)` line above if present, or keep a single one.)

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_tide_adapters.CHSPaddingTest -v`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

Run: `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`
Expected: all pass.

```bash
git add app/tide_adapters.py app/test_tide_adapters.py
git commit -m "CHS: fetch padded ±1 day so local-month filter recovers edge tides"
```

---

## Task 8: Integrate into `get_tides` (localize + sun line in pcal)

**Files:**
- Modify: `app/get_tides.py`
- Test: `app/test_get_tides_sun.py` (new — keeps get_tides tests isolated)

- [ ] **Step 1: Write the failing test**

```python
# app/test_get_tides_sun.py
import os, tempfile, unittest
import get_tides


class PcalSunLineTest(unittest.TestCase):
    def test_writes_sun_line_before_tides(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 05:23,4.8,H\n2026-06-15 11:40,0.1,L"
        sun = {15: ('05:14', '21:09')}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='Test',
                                                sun_times=sun)
            text = open(path).read()
        self.assertIn('6/15  Rise 05:14  Set 21:09', text)
        # sun line appears before that day's tide lines
        self.assertLess(text.index('Rise 05:14'), text.index('05:23 High'))

    def test_no_sun_times_is_backward_compatible(self):
        csv_data = "Date Time,Prediction,Type\n2026-06-15 05:23,4.8,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='Test')
            text = open(path).read()
        self.assertNotIn('Rise', text)
        self.assertIn('05:23 High', text)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_get_tides_sun.PcalSunLineTest -v`
Expected: FAIL — `convert_tide_data_to_pcal` has no `sun_times` parameter.

- [ ] **Step 3a: Add the dual import** near the top of `app/get_tides.py` (alongside the existing try/except imports):

```python
try:
    from app.sun_times import sun_times_for_month, format_sun_line, localize_and_filter_csv
except ImportError:
    from sun_times import sun_times_for_month, format_sun_line, localize_and_filter_csv
```

- [ ] **Step 3b: Write the sun block in `convert_tide_data_to_pcal`** — change the signature and emit sun lines first. Replace the function signature line and add the sun block immediately after `with open(pcal_filename, 'w') as pcal_file:`:

```python
def convert_tide_data_to_pcal(csv_data, pcal_filename, location_name=None, station_id=None, sun_times=None):
    """Convert tide CSV text to a pcal custom dates file.

    sun_times: optional {day:int -> ("HH:MM","HH:MM") | note str} from
    sun_times_for_month(); when present, a `Rise … Set …` line is written for
    each day BEFORE that day's tide lines so it sits at the top of the cell.
    """
    lines = csv_data.splitlines()

    with open(pcal_filename, 'w') as pcal_file:
        # Sun lines first so pcal places them above the tide events for each day.
        if sun_times:
            # Derive month from the first data row (all rows share the month).
            month_num = None
            for line in lines[1:]:
                if line.strip():
                    try:
                        month_num = int(line.strip().split(',')[0].split()[0].split('-')[1])
                        break
                    except (IndexError, ValueError):
                        continue
            if month_num is not None:
                for day in sorted(sun_times):
                    pcal_file.write(f"{month_num}/{day}  {format_sun_line(sun_times[day])}\n")

        valid_lines = 0
        skipped_lines = 0
        # ... (existing tide-parsing loop unchanged) ...
```

Keep the rest of the existing function body (the tide-parsing loop and the trailing `note/1` write) exactly as-is.

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_get_tides_sun.PcalSunLineTest -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire localization + sun computation into `generate_calendar`** — replace the body of `generate_calendar` up to the `convert_tide_data_to_pcal` call so it fetches station metadata once, localizes CHS data, and computes sun times:

```python
def generate_calendar(station_id, year, month, output_path, location_name=None):
    """Fetch tide data and render a PDF calendar at output_path. See module docs."""
    station_info = get_station_info(station_id) or {}
    api_source = station_info.get('api_source')
    iana_tz = station_info.get('timezone')
    lat = station_info.get('latitude')
    lng = station_info.get('longitude')

    csv_data = download_tide_data(station_id, year, month)
    # CHS times are UTC -> convert to the station's local zone and trim to the
    # local month (NOAA passes through unchanged).
    csv_data = localize_and_filter_csv(csv_data, api_source, iana_tz, year, month)
    sun = sun_times_for_month(lat, lng, iana_tz, year, month)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    tmp_pdf = f"{output_path}.tmp.{os.getpid()}.{threading.get_ident()}"

    try:
        with tempfile.TemporaryDirectory(prefix='tidecal-') as tmpdir:
            pcal_path = os.path.join(tmpdir, 'events.txt')
            ps_path = os.path.join(tmpdir, 'calendar.ps')

            convert_tide_data_to_pcal(csv_data, pcal_path,
                                      location_name=location_name,
                                      station_id=station_id,
                                      sun_times=sun)

            _run_tool(["pcal", "-f", pcal_path, "-o", ps_path,
                       "-s", "0.0:0.0:1.0", "-n", "Helvetica-Narrow/9",
                       "-m", "-C", "tidecalendar.xyz",
                       str(month), str(year)])
            _run_tool(["ps2pdf", ps_path, tmp_pdf])

            if not os.path.exists(tmp_pdf) or os.path.getsize(tmp_pdf) == 0:
                raise CalendarGenerationError("ps2pdf produced no output")
            os.replace(tmp_pdf, output_path)
    finally:
        if os.path.exists(tmp_pdf):
            os.remove(tmp_pdf)

    logging.info(f"PDF file created: {output_path}")
    return output_path
```

(`get_station_info` is already imported at the top of `get_tides.py`.)

- [ ] **Step 6: Full suite + commit**

Run: `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`
Expected: all pass.

```bash
git add app/get_tides.py app/test_get_tides_sun.py
git commit -m "get_tides: localize CHS times and render sunrise/sunset line in pcal"
```

---

## Task 9: Dockerfile — ship `sun_times.py`

**Files:** Modify: `Dockerfile`

- [ ] **Step 1: Add the COPY** — after `COPY app/station_coordinates.py /app/` in the Dockerfile, add:

```dockerfile
COPY app/sun_times.py /app/
```

- [ ] **Step 2: Build and verify**

Run: `docker build -t tide-calendar-app . && docker run --rm -w / tide-calendar-app python3 -c "import app.sun_times; print('ok')"`
Expected: prints `ok` (confirms the module ships and astral is installed in the image).

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "Ship app/sun_times.py in the Docker image"
```

---

## Task 10: Docs (CLAUDE.md)

**Files:** Modify: `CLAUDE.md`

- [ ] **Step 1: Document the script + feature** — add a Maintenance Scripts subsection for `scripts/fetch_station_timezones.py` (bakes the IANA `timezone` column into both CSVs from lat/long via timezonefinder; dev-only dep; run when stations are added). Add Important Notes bullets:
  - Tide times render in the station's **local** timezone: NOAA is fetched `lst_ldt` (already local); CHS is UTC and converted via `sun_times.localize_and_filter_csv` (with a ±1-day padded fetch + local-month filter).
  - Sunrise/sunset come from `app/sun_times.py` (astral + zoneinfo), shown as a 24h `Rise HH:MM  Set HH:MM` line per day; IANA tz is precomputed and stored in the DB `timezone` column; `backfill_timezones_from_csv()` populates it on the warm DB at startup.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Document timezone/sunrise-sunset feature and the tz-baking script"
```

---

## Self-Review (completed)

- **Spec coverage:** tz data + script + bake (Tasks 2–3), DB column/import/backfill (4), sun computation incl. polar (5), CHS localize+filter (5–6), CHS padding (7), pcal render + integration (8), deps (1), Docker (9), docs (10), tests throughout. All spec sections mapped.
- **Type consistency:** `sun_times_for_month` returns `{day: tuple|str}`; `format_sun_line` accepts tuple|str; `convert_tide_data_to_pcal(..., sun_times=)` consumes that dict; `localize_and_filter_csv(csv, api_source, iana_tz, year, month)` signature consistent across Tasks 5/6/8; `backfill_timezones_from_csv(csv_paths=None)` consistent across Tasks 4/run.py. `get_station_info` adds `timezone` (Task 4) consumed in Task 8.
- **Placeholders:** none — all code blocks complete.
- **Risk note:** Task 8 Step 5 rewrites `generate_calendar`; the existing atomic-rename/temp-dir logic is preserved verbatim. Full suite run guards regressions.
```
