# --- Stage 1: version info ---------------------------------------------------
# .git is copied ONLY into this builder stage so the final image never carries
# repo history in its layers. CapRover clones the repo before building, so
# .git is present in webhook builds; local builds can override via build args.
FROM python:3.12-slim-bookworm AS version

ARG VERSION=unknown
ARG COMMIT_HASH=unknown
ARG BRANCH=unknown
ARG BUILD_TIMESTAMP=unknown

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY package.json /tmp/package.json
COPY .git /tmp/.git

RUN cd /tmp && \
    git config --global --add safe.directory /tmp && \
    VERSION=$(python3 -c "import json; print(json.load(open('/tmp/package.json'))['version'])" 2>/dev/null || echo "${VERSION}") && \
    COMMIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "${COMMIT_HASH}") && \
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "${BRANCH}") && \
    BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ") && \
    printf '{"version": "%s", "commit_hash": "%s", "branch": "%s", "build_timestamp": "%s"}\n' \
        "$VERSION" "$COMMIT_HASH" "$BRANCH" "$BUILD_TIMESTAMP" > /version_info.json && \
    cat /version_info.json

# --- Stage 2: runtime ---------------------------------------------------------
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (rarely change — keep this layer early for cache reuse)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    pcal \
    ghostscript && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies (change occasionally)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Non-root runtime user. /data is the CapRover persistent volume; it is mounted
# at runtime (typically root-owned), so the entrypoint chowns it at startup.
RUN useradd --system --create-home appuser && \
    mkdir -p /data && \
    chown appuser:appuser /data /app

# Application code (changes most often — keep these layers last)
COPY app/__init__.py /app/
COPY app/run.py /app/
COPY app/routes.py /app/
COPY app/get_tides.py /app/
COPY app/calendar_service.py /app/
COPY app/database.py /app/
COPY app/tide_adapters.py /app/
COPY app/canadian_station_sync.py /app/
COPY app/station_coordinates.py /app/
COPY app/sun_times.py /app/
COPY app/tide_extremes.py /app/
COPY app/units.py /app/

# Templates and static assets
COPY app/templates/ /app/templates/
COPY app/static/ /app/static/

# Required CSV data files (imported at startup)
COPY app/tide_stations_new.csv /app/
COPY app/canadian_tide_stations.csv /app/
COPY app/canadian_station_provinces.csv /app/

# Version info from the builder stage (no .git in this image)
COPY --from=version /version_info.json /app/version_info.json

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 80

# Startup imports ~3,200 stations (CSV + CHS API with fallback), so allow a
# generous start period before health probes count against the container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/health', timeout=4)"]

# run.py lives at /app/run.py inside the /app package dir, so import it as
# app.run from / (this mirrors how `flask run` resolved FLASK_APP=run.py).
# --preload runs the module-level startup (DB init, station import) once in
# the master instead of once per worker.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "--chdir", "/", "--preload", "--workers", "2", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:80", "app.run:app"]
