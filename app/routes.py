import logging
import subprocess
from flask import render_template, request, send_file, make_response
import os

from app import app

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        station_id = request.form['station_id']
        year = request.form['year']
        month = request.form['month']

        # Call the get_tides.py script with the new argument format
        subprocess.run(['python', 'get_tides.py', '--station', station_id, '--year', year, '--month', month])

        # PDF is saved as "tide_calendar_{station_id}_{year}_{month}.pdf"
        pdf_filename = f"tide_calendar_{station_id}_{year}_{month}.pdf"

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
        
        # Create a response object to set the cookie
        response = make_response(send_file(pdf_filename, as_attachment=True))
        response.set_cookie('station_id', station_id)

        return response

    # If GET request, read the station_id from the cookie, if available
    station_id = request.cookies.get('station_id', '9449639')  # Default to '9449639' if no cookie is found

    return render_template('index.html', station_id=station_id)
