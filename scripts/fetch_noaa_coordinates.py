"""Backfill latitude/longitude columns into app/tide_stations_new.csv from NOAA.

NOAA's Metadata API returns every tide-prediction station with lat/lng in one
call, so this needs no per-station requests. Run occasionally (and whenever new
US stations are added to the CSV) to refresh coordinates. Mirrors the Canadian
fallback-CSV pattern: coordinates ship as static data so the runtime has no hard
dependency on a live API.

Usage:
    python scripts/fetch_noaa_coordinates.py
"""
import csv
import logging
import os
import sys

import requests

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'app', 'tide_stations_new.csv')
NOAA_URL = ('https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/'
            'stations.json?type=tidepredictions')
OUTPUT_FIELDS = ['station_id', 'place_name', 'latitude', 'longitude']

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def fetch_noaa_coordinates(url=NOAA_URL):
    """Return {station_id: {'lat': float, 'lng': float}} from the NOAA MDAPI."""
    resp = requests.get(url, timeout=30, headers={'User-Agent': 'tidecalendar.xyz coordinate sync'})
    resp.raise_for_status()
    out = {}
    for s in resp.json().get('stations', []):
        sid, lat, lng = s.get('id'), s.get('lat'), s.get('lng')
        if sid is not None and lat is not None and lng is not None:
            out[str(sid)] = {'lat': float(lat), 'lng': float(lng)}
    return out


def merge_coordinates(rows, coords):
    """Pure transform: attach latitude/longitude to each CSV row.

    Unmatched stations get '' so the column stays present but empty (import
    code tolerates blanks).
    """
    merged = []
    for row in rows:
        c = coords.get(row['station_id'])
        merged.append({
            'station_id': row['station_id'],
            'place_name': row['place_name'],
            'latitude': c['lat'] if c else '',
            'longitude': c['lng'] if c else '',
        })
    return merged


def main():
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    logging.info("Read %d stations from CSV", len(rows))

    coords = fetch_noaa_coordinates()
    logging.info("Fetched %d coordinates from NOAA", len(coords))

    merged = merge_coordinates(rows, coords)
    matched = sum(1 for r in merged if r['latitude'] != '')
    logging.info("Matched %d/%d stations to coordinates", matched, len(merged))

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(merged)
    logging.info("Wrote %s", CSV_PATH)
    if matched < len(merged):
        logging.warning("%d stations had no NOAA coordinates", len(merged) - matched)
    return 0


if __name__ == '__main__':
    sys.exit(main())
