#!/usr/bin/env python3

import csv
import os
import re

def convert_md_to_csv_final():
    """Convert tide-stations-raw-new.md to CSV, intelligently preserving state abbreviations."""

    input_file = os.path.join('app', 'tide-stations-raw-new.md')
    output_file = os.path.join('app', 'tide_stations_new.csv')

    stations = []

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and header lines
                if not line or line.startswith('Map icon') or line == '':
                    continue

                # First, check if line starts with date range pattern and remove it completely
                # Pattern: "MMM DD, YYYY - MMM DD, YYYY" at start of line
                date_range_pattern = r'^[A-Z][a-z]{2}\s+\d{2},\s*\d{4}\s*-\s*[A-Z][a-z]{2}\s+\d{2},\s*\d{4}\s*'
                line = re.sub(date_range_pattern, '', line).strip()

                # Look for 7-digit station IDs
                station_match = re.search(r'(\d{7})', line)
                if not station_match:
                    continue

                station_id = station_match.group(1)

                # Extract everything after the station ID
                after_id = line[station_match.end():].strip()

                # Remove date patterns from the end
                # Date patterns: "Jan 01, 2020 - present", "- Aug 11, 2021", etc.
                date_patterns = [
                    r'\s*-\s*present\s*$',
                    r'\s*-\s*[A-Z][a-z]{2}\s+\d{2},\s*\d{4}\s*$',
                    r'\s*[A-Z][a-z]{2}\s+\d{2},\s*\d{4}\s*-\s*[A-Z][a-z]{2}\s+\d{2},\s*\d{4}\s*$',
                    r'\s*[A-Z][a-z]{2}\s+\d{2},\s*\d{4}\s*-\s*present\s*$',
                    r'\s*-\s*[A-Z][a-z]{2}\s+\d{2},\s*\d{4}[0-9]*\s*$',
                ]

                place_name = after_id
                for pattern in date_patterns:
                    place_name = re.sub(pattern, '', place_name)

                # Clean up extra spaces and commas
                place_name = place_name.strip().rstrip(',').strip()

                # Skip if empty after cleaning
                if not place_name:
                    continue

                # Convert to title case (capitalize first letter of each word)
                place_name = place_name.title()

                # Check if it already ends with a state abbreviation pattern
                # Look for ", Xx" at the end where Xx is 2 letters (after title case)
                state_match = re.search(r',\s*([A-Za-z]{2})$', place_name)
                has_state = False
                if state_match:
                    state_abbrev = state_match.group(1).upper()
                    # Check if it's a valid US state
                    us_states = {
                        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
                        'DC', 'PR'  # Puerto Rico and DC
                    }
                    if state_abbrev in us_states:
                        # Replace with uppercase state abbreviation
                        place_name = place_name[:state_match.start(1)] + state_abbrev + place_name[state_match.end(1):]
                        has_state = True

                if not has_state:
                    # Try to infer state from context or common patterns
                    # Look for state abbreviations in the original line after place name
                    remaining_text = line[station_match.end() + len(place_name):] if len(line) > station_match.end() + len(place_name) else ""

                    # Look for state pattern in remaining text (case insensitive)
                    state_match = re.search(r'\b([A-Za-z]{2})\b', remaining_text)
                    if state_match:
                        potential_state = state_match.group(1).upper()
                        # Common US state abbreviations
                        us_states = {
                            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
                            'DC', 'PR'  # Puerto Rico and DC
                        }
                        if potential_state in us_states:
                            place_name = f"{place_name}, {potential_state}"

                # Avoid duplicates
                if not any(s['station_id'] == station_id for s in stations):
                    stations.append({
                        'station_id': station_id,
                        'place_name': place_name
                    })
                    print(f"Found: {station_id} -> {place_name}")

        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['station_id', 'place_name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for station in sorted(stations, key=lambda x: x['station_id']):
                writer.writerow(station)

        print(f"\nSuccessfully converted {len(stations)} stations to {output_file}")

        # Show statistics
        stations_with_states = [s for s in stations if re.search(r', [A-Z]{2}$', s['place_name'])]
        print(f"\nStations with state abbreviations: {len(stations_with_states)}")
        print(f"Stations without state abbreviations: {len(stations) - len(stations_with_states)}")

        # Show examples with states
        print("\nExamples with state abbreviations:")
        for station in stations_with_states[:10]:
            print(f"  {station['station_id']} -> {station['place_name']}")

        # Show examples without states (for debugging)
        stations_without_states = [s for s in stations if not re.search(r', [A-Z]{2}$', s['place_name'])]
        print("\nExamples without state abbreviations:")
        for station in stations_without_states[:10]:
            print(f"  {station['station_id']} -> {station['place_name']}")

        return True

    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return False
    except Exception as e:
        print(f"Error converting file: {e}")
        return False

if __name__ == "__main__":
    convert_md_to_csv_final()