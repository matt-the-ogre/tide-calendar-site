"""Startup self-heal: backfill coordinates for stations missing them.

The US CSV ships coordinates (see scripts/fetch_noaa_coordinates.py), but on a
warm production DB the CSV import short-circuits, so coordinates can be absent
there. This makes a single NOAA Metadata API call to fill any gaps. No-op (and
no network call) when nothing is missing. Always non-fatal.
"""
import logging
import sqlite3

import requests

# Dual import so this works both as the `app` package (flask/gunicorn) and as a
# top-level sibling module under `cd app && python -m unittest`. Reference
# database.DB_PATH dynamically (NOT `from ... import DB_PATH`) so tests that
# reassign database.DB_PATH are honored.
try:
    import app.database as database
except ImportError:
    import database

NOAA_URL = ('https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/'
            'stations.json?type=tidepredictions')


def fetch_noaa_coordinates(url=NOAA_URL):
    """Return {station_id: {'lat': float, 'lng': float}} from the NOAA MDAPI.

    Inlined here (NOT imported from scripts/) on purpose: scripts/ is excluded
    from the Docker image (.dockerignore), so a runtime import of the script
    would raise ModuleNotFoundError in production. This module ships in the
    image, so the fetch must live here. scripts/fetch_noaa_coordinates.py keeps
    its own copy for the offline maintenance/CSV-baking workflow.
    """
    resp = requests.get(url, timeout=30,
                        headers={'User-Agent': 'tidecalendar.xyz coordinate sync'})
    resp.raise_for_status()
    out = {}
    for s in resp.json().get('stations', []):
        sid, lat, lng = s.get('id'), s.get('lat'), s.get('lng')
        if sid is not None and lat is not None and lng is not None:
            out[str(sid)] = {'lat': float(lat), 'lng': float(lng)}
    return out


def _missing_station_ids():
    with sqlite3.connect(database.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT station_id FROM tide_station_ids "
            "WHERE country = 'USA' AND (latitude IS NULL OR longitude IS NULL)"
        ).fetchall()
    return [r[0] for r in rows]


def backfill_missing_coordinates(fetcher=fetch_noaa_coordinates):
    """Fill NULL coordinates for US stations. Returns the number updated."""
    try:
        missing = _missing_station_ids()
        if not missing:
            logging.info("Coordinate backfill: nothing missing, skipping NOAA call")
            return 0
        logging.info("Coordinate backfill: %d US stations missing coords; querying NOAA", len(missing))
        coords = fetcher()
        if not coords:
            logging.warning("Coordinate backfill: NOAA returned no coordinates")
            return 0
        updated = 0
        with sqlite3.connect(database.DB_PATH) as conn:
            for sid in missing:
                c = coords.get(sid)
                if c:
                    conn.execute(
                        "UPDATE tide_station_ids SET latitude=?, longitude=? WHERE station_id=?",
                        (c['lat'], c['lng'], sid))
                    updated += 1
            conn.commit()
        logging.info("Coordinate backfill: updated %d/%d stations", updated, len(missing))
        return updated
    except Exception as e:  # never fatal to startup
        logging.error("Coordinate backfill failed: %s", e)
        return 0
