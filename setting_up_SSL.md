# Setting up SSL

For deployment, it’s common to run Nginx directly on your server rather than inside a Docker container. This allows you to manage SSL certificates, reverse proxy configurations, and other Nginx settings more easily. However, having an Nginx instance running in a container can still be useful for local development and testing.

## Deployment Scenario

- **Server Nginx**: You run Nginx directly on your DigitalOcean Droplet (or any server) to handle SSL, reverse proxy, and static file serving. This is managed through the configuration files located in `/etc/nginx/sites-available/` and `/etc/nginx/sites-enabled/`.
- **Docker Nginx**: Useful for local development to simulate the production environment. This allows developers to test the application with an Nginx reverse proxy without needing a separate server.

## Steps to Configure for Deployment and Local Development

### For Deployment (Server Nginx)

1. **Configure Nginx on the Server**:
   - Place your Nginx configuration in `/etc/nginx/sites-available/` and create a symlink in `/etc/nginx/sites-enabled/`.
   - Example deployment configuration:

     **/etc/nginx/sites-available/tide-calendar**:

     ```nginx
     server {
         listen 80;
         server_name your_domain www.your_domain;
         return 301 https://$host$request_uri;
     }

     server {
         listen 443 ssl;
         server_name your_domain www.your_domain;

         ssl_certificate /etc/letsencrypt/live/your_domain/fullchain.pem;
         ssl_certificate_key /etc/letsencrypt/live/your_domain/privkey.pem;
         include /etc/letsencrypt/options-ssl-nginx.conf;
         ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

         location / {
             proxy_pass http://localhost:5001;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
             proxy_set_header X-Forwarded-Proto $scheme;
         }
     }
     ```

2. **Deploy Configuration Changes**:
   - Use your CI/CD pipeline to deploy changes to the Nginx configuration on the server.

3. **Reload Nginx**:

   ```bash
   sudo systemctl reload nginx
   ```

### For Local Development (Docker Nginx)

1. **Docker Compose Configuration**:
   - Configure Docker Compose to use Nginx for local development.
   - Example `docker-compose.yml`:

     ```yaml
     version: '3'
     services:
       app:
         build: .
         ports:
           - "5001:5001"
         environment:
           FLASK_APP: run.py
           FLASK_ENV: development
           FLASK_RUN_PORT: 5001

       nginx:
         image: nginx:latest
         ports:
           - "80:80"
         volumes:
           - ./nginx.conf:/etc/nginx/conf.d/default.conf
         depends_on:
           - app
     ```

2. **Local Nginx Configuration**:
   - Example `nginx.conf` for local development:

     **nginx.conf**:

     ```nginx
     server {
         listen 80;
         server_name localhost;

         location / {
             proxy_pass http://app:5001;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
             proxy_set_header X-Forwarded-Proto $scheme;
         }
     }
     ```

## CI/CD Pipeline Configuration

Ensure your CI/CD pipeline copies the Nginx configuration from your repository to the server’s Nginx configuration directory and reloads Nginx.

**Example CI/CD Workflow**:

```yaml
name: Deploy to DigitalOcean

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up SSH
      uses: webfactory/ssh-agent@v0.5.3
      with:
        ssh-private-key: ${{ secrets.DO_SSH_KEY }}

    - name: Deploy to DigitalOcean Droplet
      run: |
        ssh -o StrictHostKeyChecking=no root@your_droplet_ip '
        cd /opt/tide-calendar &&
        git pull origin main &&
        cp nginx.conf /etc/nginx/sites-available/tide-calendar &&
        ln -sf /etc/nginx/sites-available/tide-calendar /etc/nginx/sites-enabled/ &&
        systemctl reload nginx &&
        docker-compose down &&
        docker-compose up --build -d
        '
```

## Summary

- **Deployment (Server Nginx)**: Use Nginx on the server for handling SSL and reverse proxying in production.
- **Local Development (Docker Nginx)**: Use Nginx within a Docker container to simulate the production environment.
- **CI/CD Pipeline**: Ensure the pipeline updates the Nginx configuration on the server and reloads Nginx.

By following these practices, you can maintain a consistent and efficient deployment process while leveraging the benefits of both server and containerized Nginx setups.
