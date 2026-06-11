#!/bin/sh
# Runs as root just long enough to fix ownership of the persistent volume
# (/data is mounted at runtime and is typically root-owned on the host),
# then drops privileges to appuser for the actual server process.
set -e

mkdir -p /data/calendars
chown -R appuser:appuser /data

exec setpriv --reuid appuser --regid appuser --init-groups "$@"
