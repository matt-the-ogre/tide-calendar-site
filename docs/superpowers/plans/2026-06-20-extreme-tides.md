# Daylight Extreme-Tide Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render two tables in unused calendar cells — top 5 daylight HIGH tides (highest-first) and top 5 daylight LOW tides (lowest-first) — each row day / 24h time / metric height.

**Architecture:** Reuse the localized tide CSV + per-day civil dawn/dusk (astral) to pick and rank daylight extremes, then write them as stacked `note/2` and `note/3` pcal entries (verified: stacked notes form a table and pcal auto-adds a row when cells are scarce).

**Tech Stack:** Python 3.12, astral, stdlib zoneinfo, pcal.

**Test command:** `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`

---

## File Structure

**Create:**
- `app/tide_extremes.py` — `top_extreme_tides()`, `format_extreme_rows()`
- `app/test_tide_extremes.py` — tests

**Modify:**
- `app/sun_times.py` — add `civil_daylight_window()`
- `app/test_sun_times.py` — tests for the window
- `app/get_tides.py` — compute extremes in `generate_calendar`; render tables in `convert_tide_data_to_pcal`
- `app/test_get_tides_sun.py` — pcal table tests
- `Dockerfile` — `COPY app/tide_extremes.py`
- `CLAUDE.md` — document the feature

---

## Task 1: `civil_daylight_window` in `sun_times.py`

**Files:**
- Modify: `app/sun_times.py`
- Test: `app/test_sun_times.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
class CivilWindowTest(unittest.TestCase):
    def test_normal_station_returns_dawn_dusk(self):
        import sun_times
        from datetime import date
        w = sun_times.civil_daylight_window(48.97, -123.07, 'America/Los_Angeles', date(2026, 6, 15))
        self.assertIsInstance(w, tuple)
        dawn, dusk = w
        self.assertLess(dawn, dusk)
        # civil dawn is before sunrise; sunrise ~05:0x local in mid-June
        self.assertIn(dawn.hour, range(3, 6))
        self.assertIn(dusk.hour, range(21, 23))

    def test_polar_day_all(self):
        import sun_times
        from datetime import date
        self.assertEqual(
            sun_times.civil_daylight_window(78.0, 15.0, 'Arctic/Longyearbyen', date(2026, 6, 15)),
            'all')

    def test_polar_night_none(self):
        import sun_times
        from datetime import date
        self.assertIsNone(
            sun_times.civil_daylight_window(78.0, 15.0, 'Arctic/Longyearbyen', date(2026, 12, 15)))

    def test_missing_tz_none(self):
        import sun_times
        from datetime import date
        self.assertIsNone(sun_times.civil_daylight_window(48.0, -123.0, None, date(2026, 6, 15)))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.CivilWindowTest -v`
Expected: FAIL — no `civil_daylight_window`.

- [ ] **Step 3: Implement** — add to `app/sun_times.py` (after `_day_sun`):

```python
def civil_daylight_window(lat, lng, iana_tz, d):
    """Civil-twilight daylight window for date d at a station.

    Returns (dawn_dt, dusk_dt) as tz-aware datetimes (civil dawn/dusk, sun 6°
    below horizon), or 'all' for polar 24h daylight, or None for polar night /
    missing tz/coords.
    """
    tz = _zone(iana_tz)
    if lat is None or lng is None or tz is None:
        return None
    observer = Observer(latitude=lat, longitude=lng)
    try:
        dawn = _astral_sun.dawn(observer, date=d, tzinfo=tz)  # depression 6° (civil) by default
        dusk = _astral_sun.dusk(observer, date=d, tzinfo=tz)
        return (dawn, dusk)
    except ValueError:
        noon = _datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz)
        try:
            up = _astral_sun.elevation(observer, noon) > 0
        except Exception:
            return 'all'
        return 'all' if up else None
```

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_sun_times.CivilWindowTest -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/sun_times.py app/test_sun_times.py
git commit -m "sun_times: add civil_daylight_window (civil dawn/dusk, polar-safe)"
```

---

## Task 2: `tide_extremes.py`

**Files:**
- Create: `app/tide_extremes.py`
- Create: `app/test_tide_extremes.py`

- [ ] **Step 1: Write the failing tests**

```python
# app/test_tide_extremes.py
import unittest
import tide_extremes


# Stub window: daylight is 06:00–20:00 every day (naive-local comparison).
def _day_window(lat, lng, tz, d):
    from datetime import datetime
    return (datetime(d.year, d.month, d.day, 6, 0),
            datetime(d.year, d.month, d.day, 20, 0))


CSV = (
    "Date Time,Prediction,Type\n"
    "2026-06-01 07:00,4.6,H\n"   # daylight high
    "2026-06-01 13:00,0.2,L\n"   # daylight low (lowest)
    "2026-06-02 23:30,0.1,L\n"   # NIGHT low (excluded despite being lowest)
    "2026-06-03 08:00,4.4,H\n"
    "2026-06-03 14:00,0.5,L\n"
    "2026-06-04 09:00,4.8,H\n"   # daylight high (highest)
)


class TopExtremeTidesTest(unittest.TestCase):
    def test_highs_highest_first(self):
        highs, _ = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5, window_fn=_day_window)
        self.assertEqual([h['height'] for h in highs], [4.8, 4.6, 4.4])

    def test_lows_lowest_first_and_excludes_night(self):
        _, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5, window_fn=_day_window)
        # 0.1 at 23:30 is excluded (night); lowest daylight is 0.2 then 0.5
        self.assertEqual([l['height'] for l in lows], [0.2, 0.5])
        self.assertEqual(lows[0], {'day': 1, 'time': '13:00', 'height': 0.2})

    def test_n_limits_count(self):
        highs, _ = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=2, window_fn=_day_window)
        self.assertEqual(len(highs), 2)

    def test_all_window_keeps_night(self):
        _, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5,
                                                  window_fn=lambda *a: 'all')
        self.assertEqual(lows[0]['height'], 0.1)  # night low now included

    def test_none_window_excludes_all(self):
        highs, lows = tide_extremes.top_extreme_tides(CSV, 1, 1, 'X', 2026, 6, n=5,
                                                      window_fn=lambda *a: None)
        self.assertEqual((highs, lows), ([], []))

    def test_format_rows(self):
        rows = tide_extremes.format_extreme_rows([{'day': 6, 'time': '13:30', 'height': 4.6}])
        self.assertEqual(rows, [' 6  13:30  4.6 m'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_tide_extremes -v`
Expected: FAIL — no module `tide_extremes`.

- [ ] **Step 3: Implement `tide_extremes.py`**

```python
# app/tide_extremes.py
"""Top-N daylight extreme tides (highest highs, lowest lows) for the month.

Consumes the already-localized tide CSV (local times) plus a per-day civil
daylight window (sun_times.civil_daylight_window). Daytime-only by design.
"""
from datetime import datetime as _datetime

try:
    from app.sun_times import civil_daylight_window as _default_window
except ImportError:
    from sun_times import civil_daylight_window as _default_window


def _in_window(event_dt, window):
    """event_dt: naive local datetime. window: (dawn,dusk) tz-aware | 'all' | None."""
    if window == 'all':
        return True
    if not window:
        return False
    dawn, dusk = window
    # Compare wall-clock: same date and zone, so strip tz for a naive comparison.
    return dawn.replace(tzinfo=None) <= event_dt <= dusk.replace(tzinfo=None)


def top_extreme_tides(local_csv, lat, lng, iana_tz, year, month, n=5, window_fn=_default_window):
    """Return (highs, lows): lists of {'day','time','height'} for the top-n
    daylight high tides (highest-first) and low tides (lowest-first)."""
    highs, lows = [], []
    window_cache = {}
    for line in local_csv.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) != 3:
            continue
        dt_str, height_str, ttype = parts
        try:
            dt = _datetime.strptime(dt_str.strip(), '%Y-%m-%d %H:%M')
            height = round(float(height_str), 1)
        except ValueError:
            continue
        d = dt.date()
        if d not in window_cache:
            window_cache[d] = window_fn(lat, lng, iana_tz, d)
        if not _in_window(dt, window_cache[d]):
            continue
        entry = {'day': dt.day, 'time': dt.strftime('%H:%M'), 'height': height, '_dt': dt}
        ttype = ttype.strip().upper()
        if ttype == 'H':
            highs.append(entry)
        elif ttype == 'L':
            lows.append(entry)

    highs.sort(key=lambda e: (-e['height'], e['_dt']))
    lows.sort(key=lambda e: (e['height'], e['_dt']))

    def _clean(rows):
        return [{'day': e['day'], 'time': e['time'], 'height': e['height']} for e in rows[:n]]

    return _clean(highs), _clean(lows)


def format_extreme_rows(entries):
    """Render entries as ASCII pcal note rows: 'DD  HH:MM  X.X m' (day right-aligned)."""
    return [f"{e['day']:>2}  {e['time']}  {e['height']:.1f} m" for e in entries]
```

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_tide_extremes -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add app/tide_extremes.py app/test_tide_extremes.py
git commit -m "Add tide_extremes: top-N daylight high/low tides"
```

---

## Task 3: Render the tables in `convert_tide_data_to_pcal`

**Files:**
- Modify: `app/get_tides.py`
- Test: `app/test_get_tides_sun.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
class PcalExtremeTablesTest(unittest.TestCase):
    def test_writes_high_and_low_tables(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        highs = [{'day': 4, 'time': '09:00', 'height': 4.8}]
        lows = [{'day': 1, 'time': '13:00', 'height': 0.2}]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                high_tides=highs, low_tides=lows)
            with open(path) as f:
                text = f.read()
        self.assertIn('note/2 all Top 5 High Tides (daylight)', text)
        self.assertIn('note/2 all  4  09:00  4.8 m', text)
        self.assertIn('note/3 all Top 5 Low Tides (daylight)', text)
        self.assertIn('note/3 all  1  13:00  0.2 m', text)

    def test_empty_tables_show_fallback(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T',
                                                high_tides=[], low_tides=[])
            with open(path) as f:
                text = f.read()
        self.assertIn('note/2 all No daylight high tides', text)
        self.assertIn('note/3 all No daylight low tides', text)

    def test_none_tables_omitted(self):
        import os, tempfile, get_tides
        csv_data = "Date Time,Prediction,Type\n2026-06-15 12:00,4.6,H"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'events.txt')
            get_tides.convert_tide_data_to_pcal(csv_data, path, location_name='T')
            with open(path) as f:
                text = f.read()
        self.assertNotIn('note/2', text)
        self.assertNotIn('note/3', text)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd app && ../venv/bin/python -m unittest test_get_tides_sun.PcalExtremeTablesTest -v`
Expected: FAIL — `convert_tide_data_to_pcal` has no `high_tides`/`low_tides` params.

- [ ] **Step 3a: Import the formatter** — in `app/get_tides.py`, extend the dual-import block that already imports from `sun_times` to also import the formatter:

```python
try:
    from app.tide_extremes import top_extreme_tides, format_extreme_rows
except ImportError:
    from tide_extremes import top_extreme_tides, format_extreme_rows
```

- [ ] **Step 3b: Add a helper + params** — in `app/get_tides.py`, add a module-level helper:

```python
def _write_extreme_note(pcal_file, box, title, entries, empty_msg):
    """Write a stacked pcal note table into the given empty-cell box."""
    pcal_file.write(f"note/{box} all {title}\n")
    rows = format_extreme_rows(entries)
    if rows:
        for row in rows:
            pcal_file.write(f"note/{box} all {row}\n")
    else:
        pcal_file.write(f"note/{box} all {empty_msg}\n")
```

Then change `convert_tide_data_to_pcal`'s signature and append the table writes just before the existing `note/1` station-note block (so all note/* lines sit together). The signature becomes:

```python
def convert_tide_data_to_pcal(csv_data, pcal_filename, location_name=None, station_id=None,
                              sun_times=None, high_tides=None, low_tides=None):
```

And immediately before the `if location_name:` station-note block at the end of the function, add:

```python
        # Daylight extreme-tide tables in unused cells (note/2, note/3).
        if high_tides is not None:
            _write_extreme_note(pcal_file, 2, "Top 5 High Tides (daylight)",
                                high_tides, "No daylight high tides")
        if low_tides is not None:
            _write_extreme_note(pcal_file, 3, "Top 5 Low Tides (daylight)",
                                low_tides, "No daylight low tides")

```

- [ ] **Step 4: Run to verify pass**

Run: `cd app && ../venv/bin/python -m unittest test_get_tides_sun.PcalExtremeTablesTest -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/get_tides.py app/test_get_tides_sun.py
git commit -m "get_tides: render daylight extreme-tide tables as pcal notes"
```

---

## Task 4: Wire extremes into `generate_calendar`

**Files:**
- Modify: `app/get_tides.py` (`generate_calendar`)
- Test: covered by Task 3 unit tests + the dev acceptance check (extremes need live data)

- [ ] **Step 1: Compute and pass the extremes** — in `generate_calendar`, after the `sun = sun_times_for_month(...)` line, add:

```python
    # Top-5 daylight high/low tables (only when we have a timezone to define the
    # daylight window; otherwise skip, like the sun line).
    if iana_tz:
        high_tides, low_tides = top_extreme_tides(csv_data, lat, lng, iana_tz, year, month)
    else:
        high_tides, low_tides = None, None
```

Then update the `convert_tide_data_to_pcal(...)` call inside `generate_calendar` to pass them:

```python
            convert_tide_data_to_pcal(csv_data, pcal_path,
                                      location_name=location_name,
                                      station_id=station_id,
                                      sun_times=sun,
                                      high_tides=high_tides,
                                      low_tides=low_tides)
```

- [ ] **Step 2: Full suite**

Run: `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`
Expected: all pass.

- [ ] **Step 3: Local end-to-end smoke** (real data; needs network + pcal)

Run this from `app/` with a temp DB seeded from the CSVs (mirrors the sunrise verification):

```bash
cd app && rm -f /tmp/ext.db && DB_PATH=/tmp/ext.db ../venv/bin/python -c "
import os; os.environ['DB_PATH']='/tmp/ext.db'
import database; database.DB_PATH='/tmp/ext.db'
database.init_database(); database.import_stations_from_csv(); database.import_canadian_stations_from_csv()
import get_tides
get_tides.generate_calendar('9449639', 2026, 7, '/tmp/ext_us.pdf', location_name='Point Roberts WA')
print('PDF bytes:', os.path.getsize('/tmp/ext_us.pdf'))
"
```
Expected: a non-empty PDF. (Visual confirmation of the tables happens on dev.)

- [ ] **Step 4: Commit**

```bash
git add app/get_tides.py
git commit -m "get_tides: compute and pass daylight extreme tides in generate_calendar"
```

---

## Task 5: Dockerfile + docs

**Files:**
- Modify: `Dockerfile`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Ship the module** — in `Dockerfile`, after `COPY app/sun_times.py /app/`, add:

```dockerfile
COPY app/tide_extremes.py /app/
```

- [ ] **Step 2: Build + verify import**

Run: `docker build -t tide-calendar-app . && docker run --rm -w / tide-calendar-app python3 -c "import app.tide_extremes; print('ok')"`
Expected: `ok`. (If docker isn't running, make the edit and note the skip.)

- [ ] **Step 3: Document** — in `CLAUDE.md` Important Notes, add a bullet:

```markdown
- **Daylight extreme-tide tables**: each PDF shows two unused-cell tables — top 5 daylight HIGH tides (highest-first) and top 5 daylight LOW tides (lowest-first), via `app/tide_extremes.py`. "Daylight" = civil dawn–dusk (`sun_times.civil_daylight_window`, astral 6° depression). Rendered as stacked `note/2`/`note/3` pcal entries (pcal auto-adds a row when empty cells are scarce). Skipped (logged) when the station has no timezone.
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile CLAUDE.md
git commit -m "Ship tide_extremes.py; document daylight extreme-tide tables"
```

---

## Self-Review (completed)

- **Spec coverage:** civil window (Task 1), ranking + daylight filter + lowest-first lows (Task 2), pcal table rendering + empty fallback + omit-when-None (Task 3), integration incl. skip-when-no-tz (Task 4), Docker + docs (Task 5), dev acceptance (Task 4 Step 3 + post-merge). All spec sections mapped.
- **Type consistency:** `civil_daylight_window(lat,lng,iana_tz,d)` → tuple|'all'|None, consumed by `_in_window`; `top_extreme_tides(local_csv,lat,lng,iana_tz,year,month,n=5,window_fn=...)` → (list[{day,time,height}], …); `format_extreme_rows(entries)` consumed via `_write_extreme_note`; `convert_tide_data_to_pcal(..., high_tides=None, low_tides=None)` consistent across Tasks 3/4. Window comparison uses naive-local on both sides (event is naive local; dawn/dusk stripped of tz on same date).
- **Placeholders:** none — all code complete.
- **Note ordering:** note/1 (station), note/2 (high), note/3 (low) — pcal assigns by the /N index positionally; file order doesn't matter. Verified during brainstorming that stacked same-N notes form a table and pcal auto-expands rows.
```
