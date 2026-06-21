# Daylight Extreme-Tide Tables (#96) — Design Spec

**Date:** 2026-06-20
**Branch:** `feature/extreme-tides` (off `development`)
**Status:** Approved for implementation
**Goal:** Each PDF calendar shows, in two otherwise-unused cells, a table of the
**top 5 daylight HIGH tides** and a table of the **top 5 daylight LOW tides** for the
month — each row a date, time, and elevation.

## Background

Implements David's issue #96, built on the sunrise/sunset foundation (`app/sun_times.py`,
local times). "Daylight" = between **civil dawn and civil dusk** (sun 6° below the
horizon — NOT a fixed offset; `astral` computes it per day/latitude). Uses the same
"unused calendar cell" mechanism as the existing "Tide Station" note.

## Semantics (confirmed)
- **Top 5 HIGH** = the 5 **highest** daylight high tides, ordered highest-first.
- **Top 5 LOW** = the 5 **lowest** daylight low tides, ordered lowest-first (the lowest
  tide of the month is row 1, then 2nd-lowest, …). "Lowest" = smallest/most-negative
  height in metres.
- **Daylight-only**: only tide events whose local time falls within that day's civil
  dawn–dusk window are eligible. A night-time record low is excluded by design (the
  table surfaces the best *daytime* windows).

## Key decisions

| Decision | Choice |
|----------|--------|
| Scope | Daylight-only (civil dawn–dusk) |
| Count | Top 5 high + top 5 low |
| Window | Civil twilight (astral `dawn()`/`dusk()`, depression 6°) |
| Row format | `DD  HH:MM  X.X m` (day-of-month, 24h local, metric) |
| Placement | pcal notes: `note/1`=station (existing), `note/2`=high table, `note/3`=low table |
| Units/format | Metric, 24h (consistent; 12h toggle is a separate future feature) |

## Feasibility (verified during brainstorming)
- Repeated `note/N all <row>` lines **stack vertically** in one pcal cell → a multi-row
  table renders cleanly.
- When a month has too few empty cells (e.g. Feb 2026: 28 days starting Sunday = 0 spare
  cells), pcal **auto-adds a notes row** at the bottom and places all notes + mini-cals
  there. So the tables render in **every** month; no fragile cell-counting required.

## Architecture

### 1. `app/sun_times.py` — add the daylight window
- `civil_daylight_window(lat, lng, iana_tz, date)` → one of:
  - `(dawn_dt, dusk_dt)` — civil dawn/dusk as tz-aware datetimes (normal case);
  - `"all"` — polar 24h daylight (every event counts);
  - `None` — polar night or missing tz/coords (no daylight events).
  Uses `astral.sun.dawn`/`dusk` (depression 6°); catches `ValueError` for polar and
  classifies via solar elevation at local noon (same pattern as `_day_sun`).

### 2. `app/tide_extremes.py` — new module
- `top_extreme_tides(local_csv, lat, lng, iana_tz, year, month, n=5)` → `(highs, lows)`.
  - Parse the **already-localized** CSV (`YYYY-MM-DD HH:MM,height,H|L`).
  - For each event, look up that day's `civil_daylight_window`; keep the event iff its
    local time is within the window (`"all"` keeps everything; `None` keeps nothing).
  - `highs` = eligible `H` events sorted by height descending, then time ascending; take n.
  - `lows` = eligible `L` events sorted by height ascending, then time ascending; take n.
  - Each entry: `{'day': int, 'time': 'HH:MM', 'height': float}`.
- `format_extreme_rows(entries)` → list of `"DD  HH:MM  X.X m"` strings (right-shaped).

### 3. `app/get_tides.py` — integrate
- In `generate_calendar`, after localizing the CSV and computing `sun_times`, compute
  `(highs, lows) = top_extreme_tides(local_csv, lat, lng, iana_tz, year, month)` and pass
  them to `convert_tide_data_to_pcal`.
- `convert_tide_data_to_pcal(..., high_tides=None, low_tides=None)` writes:
  - `note/2 all Top 5 High Tides (daylight)` + a `note/2 all <row>` per high entry;
  - `note/3 all Top 5 Low Tides (daylight)` + a `note/3 all <row>` per low entry.
  - Empty list → a single `note/N all No daylight high tides` (resp. low) line, so the
    cell isn't blank.
- Missing tz (no localization/window) → skip both tables (logged), like the sun line.

## Testing
- `tide_extremes.top_extreme_tides`:
  - Highs sorted highest-first; lows sorted **lowest-first** (lowest = row 1).
  - Daylight filter: a synthetic night-time low (outside the window) is excluded; a
    daytime low is included. Use a stub window function for determinism.
  - Fewer than 5 eligible → returns the shorter list. Ties broken by time.
- `sun_times.civil_daylight_window`: normal station/date returns dawn<dusk and dawn is
  before sunrise / dusk after sunset; polar June → `"all"`; polar Dec → `None`.
- `convert_tide_data_to_pcal`: output contains the `note/2`/`note/3` titles + rows;
  empty-list fallback line present; backward-compatible when both are None.
- Full suite green (`cd app && ../venv/bin/python -m unittest discover -p 'test_*.py'`).

## Acceptance (the goal, verified on dev.tidecalendar.xyz)
A downloaded calendar shows:
- one unused cell titled "Top 5 High Tides (daylight)" listing up to 5 rows of
  day / 24h time / metric height, highest-first;
- another unused cell titled "Top 5 Low Tides (daylight)", lowest-first;
- the existing "Tide Station" note and the prev/next mini-calendars still present.

## Risks / notes
- `astral`'s civil dawn/dusk is standard-refraction; minute-level accuracy, fine here.
- Daylight filtering uses the localized (local-time) events from the sunrise feature, so
  US (NOAA-local) and Canada (CHS→local) are handled uniformly.
- Cached PDFs predating this won't have the tables until regenerated (monthly TTL /
  redeploy).
