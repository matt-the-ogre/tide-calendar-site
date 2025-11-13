#!/bin/bash
# Script to copy SQLite database from old droplet's Docker container
# Run this script ON THE OLD DROPLET

CONTAINER_NAME="tide-calendar_app"
DB_PATH="/app/tide_station_ids.db"
OUTPUT_FILE="./tide_station_ids.db"

echo "Attempting to copy database from container: $CONTAINER_NAME"

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container '$CONTAINER_NAME' not found"
    echo "Available containers:"
    docker ps -a --format '{{.Names}}'
    exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Warning: Container '$CONTAINER_NAME' is not running"
    echo "Attempting to copy anyway..."
fi

# Copy the database file
echo "Copying $DB_PATH from container to $OUTPUT_FILE..."
docker cp "${CONTAINER_NAME}:${DB_PATH}" "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Success! Database copied to: $(pwd)/$OUTPUT_FILE"
    ls -lh "$OUTPUT_FILE"

    # Show some stats about the database
    if command -v sqlite3 &> /dev/null; then
        echo ""
        echo "Database info:"
        sqlite3 "$OUTPUT_FILE" "SELECT COUNT(*) as total_stations FROM tide_station_ids;"
        sqlite3 "$OUTPUT_FILE" "SELECT COUNT(*) as stations_with_lookups FROM tide_station_ids WHERE lookup_count > 1;"
        echo ""
        echo "Top 5 most popular stations:"
        sqlite3 -header -column "$OUTPUT_FILE" "SELECT station_id, place_name, lookup_count FROM tide_station_ids ORDER BY lookup_count DESC LIMIT 5;"
    fi
else
    echo "✗ Error: Failed to copy database"
    exit 1
fi
