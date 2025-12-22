# Use the official Python image from the Docker Hub
FROM python:3.9-slim-bullseye

# Build arguments for version info (passed at build time)
ARG VERSION=unknown
ARG COMMIT_HASH=unknown
ARG BRANCH=unknown
ARG BUILD_TIMESTAMP=unknown

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_RUN_PORT=80

# Create and set the working directory
WORKDIR /app

# Create persistent data directory
RUN mkdir -p /data

# # Install any needed packages specified in requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# Copy only runtime application files (not dev tools, tests, or generated files)
# Core Python application files
COPY app/__init__.py /app/
COPY app/run.py /app/
COPY app/routes.py /app/
COPY app/get_tides.py /app/
COPY app/database.py /app/
COPY app/tide_adapters.py /app/
COPY app/canadian_station_sync.py /app/
COPY app/generate_version_info.py /app/

# Templates and static assets
COPY app/templates/ /app/templates/
COPY app/static/ /app/static/

# Required CSV data files (imported at startup)
COPY app/tide_stations_new.csv /app/
COPY app/canadian_tide_stations.csv /app/

# Copy package.json for version info
COPY package.json /app/

# Install system dependencies (including git for version info generation)
RUN apt-get update && \
apt-get install -y --no-install-recommends \
pcal \
ghostscript \
git && \
rm -rf /var/lib/apt/lists/*

# Copy only the requirements file to the container
COPY requirements.txt /app

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy .git directory temporarily for version info generation
COPY .git /tmp/.git

# Generate version info JSON from git (for CapRover) or build args (for local builds)
RUN if [ -d "/tmp/.git" ]; then \
        cd /tmp && \
        export VERSION=$(python3 -c "import json; print(json.load(open('/app/package.json'))['version'])" 2>/dev/null || echo "unknown") && \
        export COMMIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown") && \
        export BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown") && \
        export BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ") && \
        cd /app && \
        echo "{\"version\": \"$VERSION\", \"commit_hash\": \"$COMMIT_HASH\", \"branch\": \"$BRANCH\", \"build_timestamp\": \"$BUILD_TIMESTAMP\"}" > /app/version_info.json; \
    else \
        echo "{\"version\": \"${VERSION:-unknown}\", \"commit_hash\": \"${COMMIT_HASH:-unknown}\", \"branch\": \"${BRANCH:-unknown}\", \"build_timestamp\": \"${BUILD_TIMESTAMP:-unknown}\"}" > /app/version_info.json; \
    fi && \
    rm -rf /tmp/.git && \
    cat /app/version_info.json

# Expose the port the app runs on
EXPOSE 80

# Command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
