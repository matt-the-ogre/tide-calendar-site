import logging
import subprocess
import sys
from flask import render_template, request, send_file, make_response, jsonify
import os
import glob
import time
import re

from app import app
from app.database import search_stations_by_name, get_popular_stations, get_place_name_by_station_id, get_station_id_by_place_name

def extract_location_with_state(place_name):
    """
    Extract location with state abbreviation from full place name.
    Examples:
        "Point Roberts, WA" -> "Point Roberts, WA"
        "Seattle, WA" -> "Seattle, WA"
        "Port Allen, Hanapepe Bay, Kauai Island, HI" -> "Port Allen, HI"
        "Esperanza, Antarctica" -> "Esperanza, Antarctica"
    """
    if not place_name:
        return None

    parts = [p.strip() for p in place_name.split(',')]

    if len(parts) == 0:
        return None
    elif len(parts) == 1:
        return parts[0]
    else:
        # Return first part + last part (city + state/country)
        return f"{parts[0]}, {parts[-1]}"

def sanitize_filename(text):
    """
    Convert location name to safe filename component.
    Examples:
        "Point Roberts, WA" -> "Point_Roberts_WA"
        "Seattle, WA" -> "Seattle_WA"
    """
    if not text:
        return "unknown"

    # Replace problematic characters with underscores
    safe = re.sub(r'[/\\:*?"<>|,]', '_', text)

    # Replace spaces with underscores
    safe = safe.replace(' ', '_')

    # Remove multiple consecutive underscores
    safe = re.sub(r'_+', '_', safe)

    # Remove leading/trailing underscores
    safe = safe.strip('_')

    # Limit length to avoid filesystem issues
    max_length = 100
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')

    return safe or "unknown"

def cleanup_old_pdfs(directory, max_age_hours=1):
    """Delete PDF files older than max_age_hours from the specified directory."""
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        pdf_pattern = os.path.join(directory, "tide_calendar_*.pdf")

        for pdf_file in glob.glob(pdf_pattern):
            try:
                file_age = current_time - os.path.getmtime(pdf_file)
                if file_age > max_age_seconds:
                    os.remove(pdf_file)
                    logging.info(f"Cleaned up old PDF: {pdf_file}")
            except OSError as e:
                logging.warning(f"Could not delete old PDF {pdf_file}: {e}")

    except Exception as e:
        logging.error(f"Error during PDF cleanup: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        station_id = request.form['station_id'].strip()
        year = request.form['year']
        month = request.form['month']

        # If station_id is empty, try to get it from the place name in the search field
        if not station_id:
            station_search = request.form.get('station_search', '').strip()
            if not station_search:
                return render_template('tide_station_not_found.html',
                                     message="No station selected. Please select a tide station from the autocomplete dropdown.")
            # Try to find station ID by place name
            found_station_id = get_station_id_by_place_name(station_search)
            if not found_station_id:
                return render_template('tide_station_not_found.html',
                                     message=f"Could not find tide station for '{station_search}'. Please select from the autocomplete dropdown.")
            station_id = found_station_id

        # Validate form inputs
        try:
            year = int(year)
            month = int(month)

            # Validate ranges
            if not (1 <= month <= 12):
                raise ValueError("Month must be between 1 and 12")
            if not (2000 <= year <= 2030):
                raise ValueError("Year must be between 2000 and 2030")
            if not station_id or not station_id.isdigit():
                raise ValueError("Station ID must be a number")

        except ValueError as e:
            logging.error(f"Form validation error: {str(e)}")
            return render_template('tide_station_not_found.html', message=f"Invalid input: {str(e)}")

        # Get the place name for the station ID
        place_name = get_place_name_by_station_id(station_id)

        # Extract and sanitize location name for filename
        location_display = extract_location_with_state(place_name)
        location_filename = sanitize_filename(location_display) if location_display else station_id

        # Call the get_tides.py script with location name
        script_path = os.path.join(os.path.dirname(__file__), 'get_tides.py')
        # Get the project root directory (parent of app directory)
        project_root = os.path.dirname(os.path.dirname(__file__))

        # Pass location_display to get_tides.py for calendar note text
        cmd = [sys.executable, script_path, '--station_id', station_id, '--year', str(year), '--month', str(month)]
        if location_display:
            cmd.extend(['--location_name', location_display])
        subprocess.run(cmd, cwd=project_root)

        # PDF is now saved with human-readable location name
        pdf_filename = os.path.join(project_root, f"tide_calendar_{location_filename}_{year}_{month:02d}.pdf")

        # Check if the PDF file exists
        if not os.path.exists(pdf_filename):
            # log an error message
            logging.error(f"File {pdf_filename} does not exist.")
            return render_template('tide_station_not_found.html', message="Error: PDF file not found.")

        # Check if the PDF file is empty
        if os.path.getsize(pdf_filename) == 0:
            # log an error message
            logging.error(f"File {pdf_filename} is empty.")
            return render_template('tide_station_not_found.html', message="Error: PDF file is empty.")

        # Create a response object to set the cookie (place_name already fetched above)
        response = make_response(send_file(pdf_filename, as_attachment=True))
        if place_name:
            response.set_cookie('last_place_name', place_name)

        # Clean up old PDF files (older than 1 hour)
        cleanup_old_pdfs(project_root, max_age_hours=1)

        return response

    # If GET request, read the last place name from the cookie, if available
    last_place_name = request.cookies.get('last_place_name', 'Point Roberts, WA')

    return render_template('index.html', last_place_name=last_place_name)

@app.route('/api/search_stations')
def api_search_stations():
    """API endpoint to search for tide stations by place name."""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 1:
        return jsonify([])

    try:
        results = search_stations_by_name(query, limit=10)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in search API: {e}")
        return jsonify([]), 500

@app.route('/api/popular_stations')
def api_popular_stations():
    """API endpoint to get the most popular tide stations."""
    try:
        results = get_popular_stations(limit=16)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in popular stations API: {e}")
        return jsonify([]), 500
