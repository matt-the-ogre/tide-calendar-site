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
        noon = _datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz)
        try:
            up = _astral_sun.elevation(observer, noon) > 0
        except Exception:
            return '24h daylight'
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
        return csv_data

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
            local = naive
        else:
            local = naive.replace(tzinfo=_utc.utc).astimezone(tz)
        if local.year == year and local.month == month:
            out.append(f"{local.strftime('%Y-%m-%d %H:%M')},{value},{ttype}")
    return '\n'.join(out)
