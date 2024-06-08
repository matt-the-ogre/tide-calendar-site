import subprocess
from flask import render_template, request, send_file
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
        pdf_filename = f"tide_calendar_{station_id}_{year}_{month}.pdf" # e.g., tide_calendar_9449639_2024_06.pdf

        # Assuming the PDF is saved as tide_calendar.pdf
        return send_file(pdf_filename, as_attachment=True)

    return render_template('index.html')
