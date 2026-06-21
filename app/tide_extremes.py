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

try:
    from app.units import convert as _uconv, suffix as _usuf
except ImportError:
    from units import convert as _uconv, suffix as _usuf


def _in_window(event_dt, window):
    """event_dt: naive local datetime. window: (dawn,dusk) tz-aware | 'all' | None."""
    if window == 'all':
        return True
    if not window:
        return False
    dawn, dusk = window
    return dawn.replace(tzinfo=None) <= event_dt <= dusk.replace(tzinfo=None)


def top_extreme_tides(local_csv, lat, lng, iana_tz, year, month, n=5, window_fn=_default_window):
    """Return (highs, lows): lists of {'day','time','height'}.

    Selection is by extremity (the n highest daylight high tides and the n lowest
    daylight low tides), but the returned lists are ordered by **date** (day
    ascending) for display — easier to scan/plan on a calendar, and extreme tides
    cluster around spring tides so the dates usually form a tidy consecutive run.
    Heights remain in each row so the ranking is still visible."""
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

    # Rank by extremity (highs descending, lows ascending), take the top n...
    highs.sort(key=lambda e: (-e['height'], e['_dt']))
    lows.sort(key=lambda e: (e['height'], e['_dt']))

    def _select(rows):
        # ...then display the selected n in date order.
        chosen = sorted(rows[:n], key=lambda e: e['_dt'])
        return [{'day': e['day'], 'time': e['time'], 'height': e['height']} for e in chosen]

    return _select(highs), _select(lows)


def format_extreme_rows(entries, month=None, unit='imperial'):
    """Render entries as ASCII pcal note rows: 'Mdd  HH:MM  X.X <unit>'.

    The day is prefixed with the month's first letter (e.g. June 14 -> 'J14') so a
    date can't be mistaken for the numeric tide height. `month` is 1-12; when None
    the letter is omitted. Heights are converted to the requested unit for display;
    ranking/selection must be done on raw metric values before calling this."""
    import calendar as _calendar
    letter = _calendar.month_abbr[month][0] if month else ''
    return [f"{letter}{e['day']:02d}  {e['time']}  {_uconv(e['height'], unit):.1f} {_usuf(unit)}"
            for e in entries]
