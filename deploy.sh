#!/bin/bash

# Change to the project directory
cd /opt/tide-calendar

# Reset any local changes
git reset --hard HEAD

# Pull the latest changes from GitHub
git pull origin main

# Copy the nginx.conf from the repo to the Nginx configuration directory
cp nginx.conf /etc/nginx/sites-available/tide-calendar

# Create a symlink in sites-enabled
ln -sf /etc/nginx/sites-available/tide-calendar /etc/nginx/sites-enabled/

# Reload Nginx to apply the new configuration
sudo systemctl reload nginx

# Bring down the Flask container to avoid conflicts
docker-compose down

# Build and restart the Flask container
docker-compose up --build -d
