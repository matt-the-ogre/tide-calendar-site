"""Bake an IANA `timezone` column into the station CSVs from each station's
lat/long, using timezonefinder.

Dev-only: timezonefinder is heavy (numpy/h3/cffi) and is NOT a runtime dependency.
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
