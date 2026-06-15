import hmac
import json
import logging
import os
from datetime import datetime

from flask import render_template, request, send_file, make_response, jsonify

from app import app, limiter
from app.calendar_service import get_or_generate_pdf
from app.database import (get_popular_stations, get_place_name_by_station_id,
                          get_station_id_by_place_name, search_stations_by_country,
                          get_popular_stations_by_country, log_usage_event,
                          get_usage_stats, get_stations_with_coordinates, stations_to_geojson)

# Top stations count configuration
TOP_STATIONS_COUNT = int(os.getenv('TOP_STATIONS_COUNT', '10'))

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


def _int_or_none(v):
    """Coerce form value to int for analytics logging; returns None on failure."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _no_predictions_message(where, year, month):
    """User-facing message when a calendar can't be generated.

    The usual cause, now that inactive/temporary stations are listed, is that the
    station has no published predictions for the requested period; a transient
    tide-service outage is also possible, so the message hedges both.
    """
    return (
        f"We couldn't generate a tide calendar for {where} for {year}-{month:02d}. "
        f"This station may have no published tide predictions for that period "
        f"(some stations are inactive or have only historical data), or the tide "
        f"data service may be temporarily unavailable. Please try again, or choose "
        f"a different station or month."
    )


@app.route('/', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def index():
    if request.method == 'POST':
        station_id = request.form['station_id'].strip()
        year = request.form['year']
        month = request.form['month']

        # If station_id is empty, try to get it from the place name in the search field
        if not station_id:
            station_search = request.form.get('station_search', '').strip()
            if not station_search:
                log_usage_event(None, None, _int_or_none(year), _int_or_none(month), 'error', 'no_station')
                return render_template('tide_station_not_found.html',
                                     message="No station selected. Please select a tide station from the autocomplete dropdown.")
            # Try to find station ID by place name
            found_station_id = get_station_id_by_place_name(station_search)
            if not found_station_id:
                log_usage_event(None, None, _int_or_none(year), _int_or_none(month), 'error', 'station_not_found')
                return render_template('tide_station_not_found.html',
                                     message=f"Could not find tide station for '{station_search}'. Please select from the autocomplete dropdown.")
            station_id = found_station_id

        # Validate form inputs
        try:
            year = int(year)
            month = int(month)
            current_year = datetime.utcnow().year
            # NOAA tide predictions are typically only published a few years
            # out, so cap requests at current_year + 4.
            max_year = current_year + 4

            if not (1 <= month <= 12):
                raise ValueError("Month must be between 1 and 12")
            if not (current_year <= year <= max_year):
                raise ValueError(f"Year must be between {current_year} and {max_year}")
            if not station_id or not station_id.isdigit():
                raise ValueError("Station ID must be a number (USA: 7 digits, Canada: 5 digits)")

        except ValueError as e:
            logging.error(f"Form validation error: {str(e)}")
            log_usage_event(station_id, None, _int_or_none(year), _int_or_none(month), 'error', 'invalid_input')
            return render_template('tide_station_not_found.html', message=f"Invalid input: {str(e)}")

        result = get_or_generate_pdf(station_id, year, month, source='web')

        if not result.ok:
            if result.error_code == 'unknown_station':
                message = (f"Station ID '{station_id}' was not found. "
                           f"Please select a tide station from the autocomplete dropdown.")
            else:
                message = _no_predictions_message(
                    result.location_display or station_id, year, month)
            return render_template('tide_station_not_found.html', message=message)

        response = make_response(send_file(result.pdf_path, as_attachment=True))
        if result.place_name:
            response.set_cookie('last_place_name', result.place_name)
        return response

    # If GET request, read the last place name from the cookie, if available
    last_place_name = request.cookies.get('last_place_name', 'Point Roberts, WA')

    return render_template('index.html', last_place_name=last_place_name)


@app.route('/api/search_stations')
def api_search_stations():
    """API endpoint to search for tide stations by place name."""
    query = request.args.get('q', '').strip()
    country = request.args.get('country', '').strip()  # Optional country filter

    if not query or len(query) < 1:
        return jsonify([])

    try:
        # Use country-specific search if country parameter is provided
        if country and country in ['USA', 'Canada']:
            results = search_stations_by_country(query, country, limit=10)
        else:
            # If no country or "All Countries", search all stations (include country field)
            results = search_stations_by_country(query, None, limit=10)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in search API: {e}")
        return jsonify([]), 500


@app.route('/api/popular_stations')
def api_popular_stations():
    """API endpoint to get the most popular tide stations."""
    country = request.args.get('country', '').strip()  # Optional country filter

    try:
        # Use country-specific query if country parameter is provided
        if country and country in ['USA', 'Canada']:
            results = get_popular_stations_by_country(country, limit=TOP_STATIONS_COUNT)
        else:
            # If no country or "All Countries", get from all stations (include country field)
            results = get_popular_stations_by_country(None, limit=TOP_STATIONS_COUNT)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in popular stations API: {e}")
        return jsonify([]), 500


_stations_geojson_cache = None


@app.route('/api/stations.geojson')
def api_stations_geojson():
    """GeoJSON FeatureCollection of all selectable stations that have coordinates.

    Memoized in-process: the station set is static per container. Only stations
    present in the directory appear, so a pin click can never hit an unknown
    station.
    """
    global _stations_geojson_cache
    if _stations_geojson_cache is None:
        _stations_geojson_cache = stations_to_geojson(get_stations_with_coordinates())
    return jsonify(_stations_geojson_cache)


@app.route('/api/generate_quick', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate_quick():
    """API endpoint to quickly generate current month's PDF."""
    try:
        data = request.get_json(silent=True)
        if not data or 'station_id' not in data:
            log_usage_event(None, None, None, None, 'error', 'invalid_input', source='quick_api')
            return jsonify({'error': 'station_id is required'}), 400

        station_id = data['station_id']
        if not isinstance(station_id, str) or not station_id.strip().isdigit():
            log_usage_event(str(station_id) or None, None, None, None, 'error', 'invalid_input', source='quick_api')
            return jsonify({'error': 'Invalid station_id (USA: 7 digits, Canada: 5 digits)'}), 400
        station_id = station_id.strip()

        today = datetime.now()
        result = get_or_generate_pdf(station_id, today.year, today.month, source='quick_api')

        if not result.ok:
            if result.error_code == 'unknown_station':
                return jsonify({'error': f"Unknown station_id '{station_id}'"}), 404
            return jsonify({'error': _no_predictions_message(
                result.location_display or station_id, today.year, today.month)}), 500

        return send_file(result.pdf_path, as_attachment=True,
                         download_name=result.download_name)

    except Exception:
        logging.exception("Error in quick generate API")
        log_usage_event(None, None, None, None, 'error', 'exception', source='quick_api')
        return jsonify({'error': 'Internal server error'}), 500


def _serve_static_file(filename, mimetype):
    """Serve a static file, returning 404 if missing."""
    try:
        return send_file(os.path.join(STATIC_DIR, filename), mimetype=mimetype)
    except FileNotFoundError:
        logging.warning(f"{filename} file not found")
        return f"{filename} not found", 404


@app.route('/ads.txt')
def ads_txt():
    """Serve ads.txt file for ad network verification."""
    return _serve_static_file('ads.txt', 'text/plain')


@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engine crawlers."""
    return _serve_static_file('robots.txt', 'text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml for search engine discovery."""
    return _serve_static_file('sitemap.xml', 'application/xml')


@app.route('/llms.txt')
def llms_txt():
    """Serve llms.txt for LLM crawlers."""
    return _serve_static_file('llms.txt', 'text/plain')


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page."""
    return render_template('404.html'), 404


@app.errorhandler(429)
def rate_limited(e):
    """Friendly response when the PDF-generation rate limit is hit."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Too many requests — please wait a minute and try again.'}), 429
    return render_template('tide_station_not_found.html',
                           message="Too many calendar requests — please wait a minute and try again."), 429


@app.route('/admin/analytics')
def admin_analytics():
    """Read-only usage dashboard gated by ANALYTICS_TOKEN env var.

    Accepts the token via `Authorization: Bearer <token>` (preferred — kept out
    of access logs, browser history, and referrer headers) or `?token=<token>`
    query param (fallback for quick bookmarks).

    Returns 404 for all failure modes (unconfigured, missing token, wrong token)
    so the endpoint is invisible to scanners. If ANALYTICS_TOKEN is unset, logs
    a warning server-side so the admin can spot the misconfig in logs.
    """
    expected = os.getenv('ANALYTICS_TOKEN')

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        supplied = auth_header[len('Bearer '):]
    else:
        supplied = request.args.get('token', '')

    if not expected:
        if supplied:
            logging.warning("ANALYTICS_TOKEN not set — /admin/analytics cannot authenticate")
        return render_template('404.html'), 404

    if not hmac.compare_digest(supplied, expected):
        return render_template('404.html'), 404

    stats = get_usage_stats(recent_limit=100, top_limit=20)
    return render_template('admin_analytics.html', stats=stats)


@app.route('/health')
def health_check():
    """Health check endpoint with version and build information."""
    try:
        # Load version info from JSON file (generated at build time)
        version_info_path = os.path.join(os.path.dirname(__file__), 'version_info.json')
        version_data = {
            'version': 'unknown',
            'commit_hash': 'unknown',
            'branch': 'unknown',
            'build_timestamp': 'unknown'
        }

        if os.path.exists(version_info_path):
            try:
                with open(version_info_path, 'r') as f:
                    version_data = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load version info: {e}")

        # Check database connectivity
        db_status = 'ok'
        try:
            get_popular_stations(limit=1)
        except Exception as e:
            db_status = f'error: {str(e)}'
            logging.error(f"Database health check failed: {e}")

        health_response = {
            'status': 'healthy' if db_status == 'ok' else 'degraded',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': version_data.get('version', 'unknown'),
            'commit_hash': version_data.get('commit_hash', 'unknown'),
            'branch': version_data.get('branch', 'unknown'),
            'build_timestamp': version_data.get('build_timestamp', 'unknown'),
            'checks': {
                'database': db_status
            }
        }

        status_code = 200 if db_status == 'ok' else 503
        return jsonify(health_response), status_code

    except Exception as e:
        logging.error(f"Health check endpoint error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        }), 503
