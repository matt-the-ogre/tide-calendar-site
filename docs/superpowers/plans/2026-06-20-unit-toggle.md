# Metric/Imperial Unit Toggle Implementation Plan

> Execute with TDD (test → fail → implement → pass → commit) per task. Run tests with `cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'` (venv: `../venv/bin/python`). Display-only conversion; internals stay metric.

## Task 1: `app/units.py` + tests
Create `app/test_units.py`:
```python
import unittest
import units

class UnitsTest(unittest.TestCase):
    def test_metric_passthrough(self):
        self.assertEqual(units.convert(3.0, 'metric'), 3.0)
    def test_imperial_feet(self):
        self.assertEqual(units.convert(1.0, 'imperial'), 3.3)   # 3.28084 -> 3.3
        self.assertEqual(units.convert(-1.2, 'imperial'), -3.9)
    def test_suffix(self):
        self.assertEqual(units.suffix('metric'), 'm')
        self.assertEqual(units.suffix('imperial'), 'ft')
    def test_unknown_unit_defaults_metric(self):
        self.assertEqual(units.convert(2.0, 'bogus'), 2.0)
        self.assertEqual(units.suffix('bogus'), 'm')

if __name__ == '__main__':
    unittest.main()
```
Create `app/units.py`:
```python
"""Display-unit helpers for tide heights. Internals stay metric; convert only
for display. 'imperial' -> feet; anything else -> metres."""
_M_TO_FT = 3.28084

def convert(height_m, unit):
    if unit == 'imperial':
        return round(height_m * _M_TO_FT, 1)
    return height_m

def suffix(unit):
    return 'ft' if unit == 'imperial' else 'm'
```
Commit: `git add app/units.py app/test_units.py && git commit -m "Add units module (metric/imperial height conversion)"`

## Task 2: unit in the cache filename
`app/calendar_service.py` `pdf_filename_for`: add `unit='imperial'` param; append a token. New:
```python
def pdf_filename_for(location_display, station_id, year, month, unit='imperial'):
    """The one place the cached-PDF filename is derived."""
    stem = sanitize_filename(location_display) if location_display else station_id
    token = 'ft' if unit == 'imperial' else 'm'
    return f"tide_calendar_{stem}_{year}_{month:02d}_{token}.pdf"
```
Add to `app/test_calendar_service.py` a test that metric vs imperial filenames differ and end in `_m.pdf`/`_ft.pdf`. Run suite (the existing pdf_filename_for tests may need the new suffix — update them to expect the token). Commit.

## Task 3: thread unit through generation
`app/calendar_service.py` `get_or_generate_pdf(station_id, year, month, source='web', unit='imperial')`:
- pass `unit` to `pdf_filename_for(location_display, station_id, year, month, unit)`
- pass `unit` to `generate_calendar(station_id, year, month, pdf_path, location_name=location_display, unit=unit)`

`app/get_tides.py`:
- `generate_calendar(station_id, year, month, output_path, location_name=None, unit='imperial')`: pass `unit` to `convert_tide_data_to_pcal(...)` and to `top_extreme_tides(...)` is NOT needed (ranking stays metric); pass `unit` to `format_extreme_rows`. So: keep `top_extreme_tides` metric; when rendering call `format_extreme_rows(entries, month, unit)`.
- Add `--unit` CLI arg (choices metric/imperial, default imperial) in `main()`, passed to `generate_calendar`.
- `convert_tide_data_to_pcal(csv_data, pcal_filename, location_name=None, station_id=None, sun_times=None, high_tides=None, low_tides=None, unit='imperial')`:
  - import units (dual import: `try: from app.units import convert as _uconv, suffix as _usuf except ImportError: from units import ...`).
  - The per-day tide line currently: `pcal_file.write(f"{pcal_date}  {time} {tide_type_full} {prediction} m\n")`. Keep the asterisk comparison `prediction < LOW_TIDE_THRESHOLD` on the raw metric `prediction`. Change the written height to `_uconv(prediction, unit)` with suffix `_usuf(unit)`: `f"{pcal_date}  {time} {tide_type_full} {_uconv(prediction, unit):.1f} {_usuf(unit)}\n"`. (Note: now formats to 1 decimal — keep that.)
  - `_write_extreme_note(...)` already calls `format_extreme_rows(entries, month)`; add a `unit` param threaded from convert (the high/low note writes), and pass to format_extreme_rows.
`app/tide_extremes.py` `format_extreme_rows(entries, month=None, unit='imperial')`: import units; render height as `f"{_uconv(e['height'], unit):.1f} {_usuf(unit)}"`. (top_extreme_tides unchanged — keeps metric heights.)

Update `app/test_tide_extremes.py` and `app/test_get_tides_sun.py` expectations: default unit is now imperial, so existing assertions that expect ` m`/`4.6 m` must either pass `unit='metric'` explicitly or expect feet. Prefer: update format tests to pass `unit='metric'` where they assert metres, and add an imperial case. For the pcal table test, pass `unit='metric'` to keep the `J04  09:00  4.8 m` assertions, OR update to feet — choose one and keep tests meaningful.
Run full suite. Commit.

## Task 4: routes
`app/routes.py`:
- Web `index` POST: `unit = request.form.get('unit', 'imperial'); unit = unit if unit in ('metric','imperial') else 'imperial'`. Pass to `get_or_generate_pdf(station_id, year, month, source='web', unit=unit)`.
- `/api/generate_quick`: read optional `unit` from JSON; if not in {metric,imperial}, default by station country: look up `from app.database import get_station_info` (already importable), `info = get_station_info(station_id)`, `unit = 'metric' if (info and info.get('country')=='Canada') else 'imperial'`. Pass to `get_or_generate_pdf(..., unit=unit)`.
Add/extend a routes-level test only if the suite already imports routes (it does NOT — skip route unit tests; covered by e2e + manual). Run suite. Commit.

## Task 5: frontend (`app/templates/index.html`)
- Add a "Units" pill group after the country-filter group, mirroring its markup (radio inputs `unit_metric`/`unit_imperial`, name `unit_toggle`, hidden `<input type="hidden" id="unit" name="unit">`).
- JS:
  - `getCookie('unit_preference')`; if in {metric,imperial} → set toggle + hidden, mark explicit. Else derive from country filter: USA/all→imperial, Canada→metric.
  - On unit radio change: set hidden `#unit`, `setCookie('unit_preference', value, 365)`.
  - In the existing `country_filter` change handler: if NO `unit_preference` cookie, update the unit toggle to the new country default; if cookie present, leave it (cookie wins). Also keep hidden `#unit` synced.
  - Popular-stations quick-generate (`handleQuickGenerate`): include `unit: document.getElementById('unit').value` in the POST JSON body.
- Keep styling consistent (reuse `.country-filter-group`/`.radio-label` classes or add `.unit-filter-group`).
Manual check: load page, toggle flips hidden field + cookie. Commit.

## Task 6: example image + Docker + docs
- `scripts/update_example_image.sh`: add `--unit imperial` to the `python "$APP_DIR/get_tides.py"` invocation (Point Roberts is US).
- `Dockerfile`: after `COPY app/sun_times.py /app/` (and tide_extremes), add `COPY app/units.py /app/`.
- `CLAUDE.md`: Important Notes bullet — units toggle: display-only conversion, unit in PDF cache key, defaults (USA/All imperial, Canada metric) with cookie override, quick-API defaults by station country.
- Build: `docker build -t tide-calendar-app . && docker run --rm -w / tide-calendar-app python3 -c "import app.units; print('ok')"`.
- Commit.

## Final
Run full suite; render a real US (imperial→ft) and a metric calendar locally to confirm; report.
