# Metric/Imperial Unit Toggle (#93) — Design Spec

**Date:** 2026-06-20 · **Branch:** `feature/unit-toggle` (off `development`) · **Status:** Approved

## Goal
Let visitors choose metric (m) or imperial (ft) tide heights on the PDF. Default by
country filter (USA/All → imperial, Canada → metric); a UI toggle overrides; choice saved
in a cookie (cookie wins over the filter default once set).

## Decisions
- 2-state toggle **Metric/Imperial**; default from country filter (USA/All→imperial, Canada→metric).
- **Cookie wins**: an explicit choice persists; changing the country filter only sets the default for visitors who haven't chosen.
- Convert **at display only** — all internals (extreme-tide ranking, the `<0.3 m` low-tide asterisk) stay metric, so unit choice never changes *which* tides are flagged/ranked.
- Heights only (the sole unit on the calendar). YAGNI: no other units, no per-row mixing.

## Architecture
### `app/units.py` (new)
- `convert(height_m, unit)` → `height_m` (metric) or `round(height_m * 3.28084, 1)` (imperial; `unit == 'imperial'`).
- `suffix(unit)` → `'m'` / `'ft'`.

### Cache key (critical)
- `pdf_filename_for(location_display, station_id, year, month, unit='imperial')` appends a unit token: `…_{year}_{month:02d}_{ft|m}.pdf`. Metric and imperial cache separately; pre-existing unit-less files just regenerate.

### Generation
- `get_or_generate_pdf(station_id, year, month, source='web', unit='imperial')` threads `unit` into `pdf_filename_for` (cache path) **and** `generate_calendar(..., unit=unit)`.
- `generate_calendar(..., unit='imperial')` passes `unit` to `convert_tide_data_to_pcal` (per-day tide line) and `top_extreme_tides`→`format_extreme_rows` (extreme tables). Each converts the displayed height via `units.convert` and uses `units.suffix`. The `<0.3 m` asterisk comparison stays on the raw metric value.

### Routes
- Web `index` POST: read `unit` form field; validate ∈ {`metric`,`imperial`}, else `imperial`; pass to `get_or_generate_pdf`.
- `/api/generate_quick`: optional JSON `unit`; if absent/invalid, default by **station country** (`get_station_info`: `USA`→imperial, `Canada`→metric) — no cookie there.

### Frontend (`index.html`)
- A **Units** pill toggle (Metric/Imperial) like the country-filter pills; hidden `unit` field on the form.
- JS default: `unit` cookie if present (cookie wins); else from country filter (USA/all→imperial, Canada→metric). Country-filter change updates the toggle only when no unit cookie exists. Clicking the toggle sets the `unit` cookie + hidden field. Popular-stations quick-generate sends `unit`; the map "Use this station" path round-trips through the same form.

### Example image
- `scripts/update_example_image.sh`: Point Roberts is US → generate in **imperial** (pass `unit imperial` / `--unit imperial`). (`get_tides.py` CLI gains a `--unit` arg.)

## Testing
- `units.convert` (m passthrough; ft = ×3.28084 rounded) + `suffix`.
- `pdf_filename_for` differs by unit (`_ft.pdf` vs `_m.pdf`).
- `convert_tide_data_to_pcal` emits `ft` heights + extreme rows in `ft` when imperial; metric unchanged; asterisk threshold unaffected by unit.
- quick-API country default (US station no unit → imperial; CA → metric).
- Full suite green.

## Acceptance (on dev.tidecalendar.xyz)
- US calendar defaults to feet; Canadian defaults to metres; toggling flips heights (m↔ft) on the per-day lines and both extreme tables; choice persists via cookie; metric and imperial don't cross-serve from cache.
