# Sunrise/Sunset + Local Times on the PDF Calendar — Design Spec

**Date:** 2026-06-20
**Branch:** `feature/sunrise-sunset-times` (off `development`)
**Status:** Approved for implementation
**Goal:** A downloaded calendar on dev.tidecalendar.xyz shows correct local-time
sunrise/sunset on each day, with all tide times in the station's local timezone,
matching this spec.

## Background

Adds local sunrise/sunset times to each day of the printable PDF calendar (via
`pcal`), and makes **all** tide times render in the tide station's local timezone.
Motivated by David's issue #96 (daylight-restricted extreme tides), which depends on
having sunrise/sunset data — this is that foundation.

### Timezone reality (the crux)
- **NOAA (US)** is requested with `time_zone=lst_ldt`, so US tide times are already
  **local** (DST-aware). ✅
- **CHS (Canada)** is requested/parsed in **UTC and kept as UTC** (`tide_adapters.py`
  comment "CHS returns UTC times - we keep them as-is"). So Canadian calendars
  currently show tide times in **UTC** — a pre-existing latent inaccuracy this feature
  fixes, because local sunrise/sunset on a UTC-tide calendar would be inconsistent.
- We now have **lat/long for every station** (from the map feature), which is what's
  needed to derive each station's timezone.

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tide-time timezones | **All local** | Convert CHS UTC→local; NOAA already local; consistent calendars |
| Timezone source | **Precompute IANA zone offline, bake into CSVs** | Matches coordinate/province pattern; keeps image lean (no runtime `timezonefinder`) |
| Time format | **24h** (military) | Per request; 12h/24h web toggle is a later feature |
| Day-cell display | Compact one-liner `Rise 05:14  Set 21:09` at top of cell | ASCII-safe for pcal's PostScript fonts; saves vertical space |
| Sun computation | `astral` + stdlib `zoneinfo` at runtime | Small, pure-Python; no heavy deps in the image |

## Non-goals (YAGNI)
12h/24h web toggle (later — formatting kept centralized so it's easy), moon phases,
twilight/golden-hour, daylight-restricted extreme tides (#96 — separate future feature
that builds on this), changing the NOAA local-time behavior.

## Architecture

### 1. Timezone data (foundation)
- **`scripts/fetch_station_timezones.py`** (new, dev-only): for every station in both
  CSVs, derive the IANA zone from lat/long via `timezonefinder`, and write a
  `timezone` column into `app/tide_stations_new.csv` and
  `app/canadian_tide_stations.csv`. Run occasionally / when stations are added.
- **DB**: add a `timezone` column to `tide_station_ids` via the existing
  `_migrate_columns`. Both CSV importers read/persist it.
- **Startup sync `backfill_timezones_from_csv()`** (in `database.py` or a small module,
  wired in `run.py`): fills DB `timezone` from the shipped CSVs for any rows missing it.
  Required because the US CSV import short-circuits on the warm prod DB — the source is
  the shipped CSV, so **no runtime library and no network**. Idempotent; non-fatal.
- `get_station_info()` returns `timezone`.

### 2. Make all tide times local
- New module **`app/sun_times.py`** owns timezone logic (and sun computation, §3).
- **NOAA**: leave tide times unchanged (already local `lst_ldt`).
- **CHS UTC→local**: in `get_tides`, convert each CHS event datetime to the station's
  IANA zone (`zoneinfo`). Because UTC→local shifts the wall clock and can cross
  midnight, the **CHS fetch is padded ±1 day in UTC**, then converted events are
  **filtered to the target *local* month** so every local day is complete (without
  padding, west-of-UTC stations lose late-evening tides on the last local day).
  - Mechanism: CHS `get_predictions` fetches `[first_day−1 .. last_day+1]` in UTC;
    `get_tides` localizes and drops events whose local date is outside the target month.
  - NOAA needs no padding (`lst_ldt` returns local-dated events for the month).

### 3. Sunrise/sunset computation
- `sun_times.py`: `sun_times_for_month(lat, lng, iana_tz, year, month)` →
  `{day:int -> ("HH:MM" rise, "HH:MM" set)}` using `astral` + `zoneinfo`, 24h local.
- **Polar edge cases**: `astral` raises when the sun doesn't rise/set at high latitude.
  Catch it and substitute a short ASCII note (`Sun: 24h daylight` / `Sun: polar night`)
  for that day instead of times. Never crash.

### 4. PDF rendering (pcal)
- `convert_tide_data_to_pcal` writes one `M/D  Rise 05:14  Set 21:09` line per day,
  emitted **before** that day's tide lines so it appears at the top of the cell.
- Missing timezone (e.g., a brand-new station not yet in the tz script run) → **omit**
  the sun line gracefully (logged); tides still render. For CHS specifically, a missing
  tz falls back to current UTC behavior for that station (logged) rather than failing.

### 5. Dependencies / Docker
- Add **`astral`** to `requirements.txt` (runtime; verify `requires_python` against
  `python:3.12-slim-bookworm` per the dep-check rule). `timezonefinder` is **dev-only**
  (used by the script; not shipped).
- Dockerfile must `COPY app/sun_times.py` (individual-file COPY list). CSVs already ship.

## Testing
- **Script**: `fetch_station_timezones.py` writes the expected `timezone` column shape
  (mock/`timezonefinder` smoke).
- **`sun_times.py`**:
  - Known case: Point Roberts WA (48.97, −123.07, `America/Vancouver`), mid-June →
    sunrise ~05:0x, sunset ~21:0x (assert within a sane window, not exact).
  - 24h formatting (e.g., `21:09` not `9:09 PM`).
  - Polar: a 78°N location in June → `24h daylight` note (no crash).
- **CHS localization**: a UTC event that crosses midnight converts to the correct local
  date+time (e.g., `2026-06-15 05:23Z` @ `America/Vancouver` → `2026-06-14 22:23`); and
  local-month filtering keeps/drops the right edge events.
- **pcal output**: generated events file contains a `Rise … Set …` line for a day.
- **DB**: `get_station_info()` returns `timezone`; `backfill_timezones_from_csv()` fills
  a NULL-tz row from the CSV.
- Full suite stays green (`cd app && python -m unittest discover -p 'test_*.py'`).

## Acceptance (the goal)
On **dev.tidecalendar.xyz**, a downloaded calendar:
- Shows `Rise HH:MM  Set HH:MM` (24h, local) on each day, plausible for the station's
  location and season.
- US calendar: tide times unchanged (local); sun line added.
- Canadian calendar: tide times now **local** (not UTC) and consistent with the sun line.

## Risks / notes
- `astral`'s sunrise/sunset is "official" (standard refraction) — minutes-level accuracy,
  fine for a printable calendar.
- The CHS UTC→local fix changes existing Canadian calendars (correctly). Cached Canadian
  PDFs predating this will differ; the monthly cache TTL / redeploy clears them.
- IANA tz via `timezonefinder` is authoritative incl. DST; far better than the rejected
  fixed-offset approach.
