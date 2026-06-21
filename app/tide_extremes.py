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
