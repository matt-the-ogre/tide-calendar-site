import argparse
import os
import requests
from datetime import datetime
import calendar
import subprocess
import logging
import re
try:
    from app.database import log_station_lookup
except ImportError:
    from database import log_station_lookup

# sample call: python get_tide_data.py --station_id 9449639 --year 2024 --month 6

# Directory for storing generated PDF calendars
# Default to app/calendars for local dev, override with PDF_OUTPUT_DIR env var for production
from pathlib import Path
APP_DIR = Path(__file__).parent.resolve()
DEFAULT_PDF_DIR = str(APP_DIR / 'calendars')
PDF_OUTPUT_DIR = os.getenv('PDF_OUTPUT_DIR', DEFAULT_PDF_DIR)

def ensure_pdf_directory():
    """Ensure the PDF output directory exists."""
    if not os.path.exists(PDF_OUTPUT_DIR):
        os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
        logging.info(f"Created PDF output directory: {PDF_OUTPUT_DIR}")

def sanitize_filename(text):
    """Convert location name to safe filename component."""
    if not text:
        return "unknown"

    safe = re.sub(r'[/\\:*?"<>|,]', '_', text)
    safe = safe.replace(' ', '_')
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')

    max_length = 100
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')

    return safe or "unknown"

def convert_tide_data_to_pcal(tide_data_filename, pcal_filename, location_name=None):
    """
    Converts tide data to a pcal compatible custom dates file.

    Parameters:
    - tide_data_filename: The path to the file containing the tide data.
    - pcal_filename: The path to the output pcal custom dates file.
    - location_name: Optional human-readable location name for display in calendar.
    """
    # Open the tide data file and the output pcal file
    with open(tide_data_filename, 'r') as tide_file, open(pcal_filename, 'w') as pcal_file:
        # Skip the header line
        next(tide_file)
        
        for line in tide_file:
            # Parse the tide data
            date_time, prediction, tide_type = line.strip().split(',')

            # round prediction to one decimal place
            prediction = round(float(prediction), 1)

            date, time = date_time.split()
            year, month, day = date.split('-')
            
            # Convert tide type from single character to full word
            tide_type_full = "High" if tide_type == "H" else "Low"
            
            # Format the date for pcal (mm/dd)
            pcal_date = f"{int(month)}/{int(day)}"
            
            if prediction < 0.3:
                # add an asterisk to the pcal_date if the tide is less than the prediction value specified above
                # this indicates the day is special to pcal and it will be colour-coded
                pcal_date += "*"
            
            # Write the event to the pcal file
            # Including time and tide type in the event description
            pcal_file.write(f"{pcal_date}  {time} {tide_type_full} {prediction} m\n")
        
        # write a blank line at the end of the file
        pcal_file.write("\n")

        # write the tide station location in a note at the end of the file
        # Use location_name if provided, otherwise fallback to station ID
        if location_name:
            pcal_file.write(f"note/1 all Tide Station: {location_name}\n")
        else:
            pcal_file.write(f"note/1 all Tide Station ID: {tide_data_filename.split('_')[0]}\n")


def download_tide_data(station_id, year, month):
    # Calculate the last day of the month
    _, last_day = calendar.monthrange(year, month)

    # Construct the request URL based on the provided sample API call
    base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    params = {
        "begin_date": f"{year}{month:02d}01",
        "end_date": f"{year}{month:02d}{last_day}",
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "interval": "hilo",
        "units": "metric",
        "format": "csv",
    }

    # Make the request
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        logging.error(f"Failed to download data for station {station_id}: {response.status_code}")
        return None

    filename = f"{station_id}_{year}_{month:02d}.csv"
    with open(filename, 'wb') as file:
        file.write(response.content)

    # Check if the file contains "No Predictions data was found."
    with open(filename, 'r') as file:
        lines = file.readlines()
        if len(lines) < 2 or "No Predictions data was found." in lines[1]:
            logging.error(f"No predictions data found for station {station_id} in {year}-{month:02d}.")
            os.remove(filename)
            return None

    logging.debug(f"Data successfully saved to {filename}")
    return filename


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Download tide data as CSV.")
    parser.add_argument('--station_id', type=str, default='9449639', help='Station ID (default: 9449639)')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='Year (default: current year)')
    parser.add_argument('--month', type=int, default=datetime.now().month, help='Month (default: current month)')
    parser.add_argument('--location_name', type=str, default=None, help='Human-readable location name for display')

    args = parser.parse_args()

    # Ensure month is in the correct format
    if args.month < 1 or args.month > 12:
        logging.error("Month must be between 1 and 12")
        exit(1)
    else:
        # Log the station ID lookup
        log_station_lookup(args.station_id)
        downloaded_filename = download_tide_data(args.station_id, args.year, args.month)
        if not downloaded_filename:
            logging.error("Could not retrieve tide data. Please check the station ID and try again.")
            exit(1)

    # convert the tide data to pcal format

    # check if the downloaded file exists
    if not downloaded_filename:
        logging.error(f"File {downloaded_filename} does not exist.")
        exit(1)
    # check if the downloaded file is empty
    if downloaded_filename and os.path.getsize(downloaded_filename) == 0:
        logging.error(f"File {downloaded_filename} is empty.")
        exit(1)

    # check if the downloaded file's second line starts with the string "No Predictions data was found.", and if so, exit
    with open(downloaded_filename, 'r') as file:
        lines = file.readlines()
        if len(lines) < 2:
            logging.error(f"File {downloaded_filename} does not contain enough data.")
            exit(1)
        second_line = lines[1]
        if "No Predictions data was found." in second_line:
            logging.error(f"No predictions data found for {args.station_id} in {args.year}-{args.month:02d}.")
            exit(1)
    
    # make a pcal file with the tide events using the month and year in the filename
    pcal_filename = f"tide_calendar_{args.station_id}_{args.year}_{args.month:02d}.txt"

    convert_tide_data_to_pcal(downloaded_filename, pcal_filename, args.location_name)

    logging.debug(f"PCAL file created: {pcal_filename}")

    # Ensure PDF output directory exists
    ensure_pdf_directory()

    # Determine PDF filename based on location_name or station_id
    if args.location_name:
        location_safe = sanitize_filename(args.location_name)
        pdf_filename = f"tide_calendar_{location_safe}_{args.year}_{args.month:02d}.pdf"
    else:
        pdf_filename = f"tide_calendar_{args.station_id}_{args.year}_{args.month:02d}.pdf"

    # Full path for PDF output
    pdf_output_path = os.path.join(PDF_OUTPUT_DIR, pdf_filename)

    # now make a calendar page using `pcal` and the pcal file with the tide events for that month and year

    # -s r1.r2:g1.g2.b1.b2 -- colour of highlighted days
    # -m -- show the month name
    # -S -- show the year
    # -f -- specify the input file
    # -o -- specify the output file

    # Call the shell command to create the calendar page
    subprocess.run(["pcal", "-f", pcal_filename, "-o", pcal_filename.replace('.txt', '.ps'), "-s 0.0:0.0:1.0", "-m", "-S", str(args.month), str(args.year)])

    # Convert the PostScript file to PDF and save to /data/calendars
    subprocess.run(["ps2pdf", pcal_filename.replace('.txt', '.ps'), pdf_output_path])

    # delete the PostScript file
    subprocess.run(["rm", pcal_filename.replace('.txt', '.ps')])
    # delete the CSV file
    subprocess.run(["rm", downloaded_filename])
    # delete the pcal file
    subprocess.run(["rm", pcal_filename])

    # Print a message indicating the PDF file creation
    logging.info(f"PDF file created: {pdf_output_path}")
    # call the shell command to create the calendar page
