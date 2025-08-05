import argparse
import os
import requests
from datetime import datetime
import calendar
import subprocess
import logging
import sqlite3

# sample call: python get_tide_data.py --station_id 9449639 --year 2024 --month 6

def convert_tide_data_to_pcal(tide_data_filename, pcal_filename):
    """
    Converts tide data to a pcal compatible custom dates file.

    Parameters:
    - tide_data_filename: The path to the file containing the tide data.
    - pcal_filename: The path to the output pcal custom dates file.
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

        # write the tide station id in a note at the end of the file
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
    
    # Check if the request was successful
    if response.status_code == 200:
        # Save the response content to a CSV file
        filename = f"{station_id}_{year}_{month:02d}.csv"
        with open(filename, 'wb') as file:
            file.write(response.content)
        logging.debug(f"Data successfully saved to {filename}")
    else:
        logging.error(f"Failed to download data: {response.status_code}")
    
    # return the filename for further processing
    return filename

def log_station_id(station_id):
    db_path = 'tide_station_ids.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tide_station_ids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT UNIQUE NOT NULL,
            lookup_count INTEGER NOT NULL DEFAULT 1,
            last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Try to update lookup_count if station_id exists
    result = c.execute('SELECT lookup_count FROM tide_station_ids WHERE station_id = ?', (station_id,)).fetchone()
    if result:
        c.execute('''
            UPDATE tide_station_ids
            SET lookup_count = lookup_count + 1,
                last_lookup = CURRENT_TIMESTAMP
            WHERE station_id = ?
        ''', (station_id,))
        # Get the new lookup_count after update
        new_count = result[0] + 1
    else:
        c.execute('''
            INSERT INTO tide_station_ids (station_id, lookup_count)
            VALUES (?, 1)
        ''', (station_id,))
        new_count = 1
    conn.commit()
    conn.close()
    logging.info(f"Station ID {station_id} has been looked up {new_count} times.")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Download tide data as CSV.")
    parser.add_argument('--station_id', type=str, default='9449639', help='Station ID (default: 9449639)')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='Year (default: current year)')
    parser.add_argument('--month', type=int, default=datetime.now().month, help='Month (default: current month)')
    
    args = parser.parse_args()

    # Ensure month is in the correct format
    if args.month < 1 or args.month > 12:
        logging.error("Month must be between 1 and 12")
        exit(1)
    else:
        # Log the station ID lookup
        log_station_id(args.station_id)
        downloaded_filename = download_tide_data(args.station_id, args.year, args.month)

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
    
    convert_tide_data_to_pcal(downloaded_filename, pcal_filename)

    logging.debug(f"PCAL file created: {pcal_filename}")

    # now make a calendar page using `pcal` and the pcal file with the tide events for that month and year
    # print("To create a calendar page with the tide events, run the following command:")
    # print(f"pcal -f {pcal_filename} -o {pcal_filename.replace('.txt', '.ps')}")
    # print("This will create a PostScript file that you can print or view.")
    # print("You can also convert the PostScript file to PDF using `ps2pdf`.")
    # print("For example: `ps2pdf pcal_tide_events_2024_06.ps pcal_tide_events_2024_06.pdf`")
    # print("This will create a PDF file that you can view or print.")
    # print("You can also customize the appearance of the calendar page using pcal options.")
    # print("For more information, see the pcal documentation.")
    # print("https://manpages.debian.org/testing/pcal/pcal.1.en.html")

    # -s r1.r2:g1.g2.b1.b2 -- colour of highlighted days
    # -m -- show the month name
    # -S -- show the year
    # -f -- specify the input file
    # -o -- specify the output file

    # Call the shell command to create the calendar page
    subprocess.run(["pcal", "-f", pcal_filename, "-o", pcal_filename.replace('.txt', '.ps'), "-s 0.0:0.0:1.0", "-m", "-S", str(args.month), str(args.year)])

    # Convert the PostScript file to PDF
    subprocess.run(["ps2pdf", pcal_filename.replace('.txt', '.ps'), pcal_filename.replace('.txt', '.pdf')])

    # delete the PostScript file
    subprocess.run(["rm", pcal_filename.replace('.txt', '.ps')])
    # delete the CSV file
    subprocess.run(["rm", downloaded_filename])
    # delete the pcal file
    subprocess.run(["rm", pcal_filename])

    # move the PDF file to the app folder
    # subprocess.run(["mv", pcal_filename.replace('.txt', '.pdf'), "app/"])
    
    # Print a message indicating the PDF file creation
    logging.info(f"PDF file created: {pcal_filename.replace('.txt', '.pdf')}")
    # call the shell command to create the calendar page
