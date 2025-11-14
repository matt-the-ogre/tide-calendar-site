# Tide Calendar Generator

This project generates a PDF calendar with tide information for a specified tide station, year, and month. It includes a web interface built with Flask, and the application can be containerized using Docker.

## Prerequisites

- Python 3.9 or later
- Docker
- Git (for version control)

## Local Development

### Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/matt-the-ogre/tide-calendar-site.git
    cd tide-calendar-site
    ```

2. **Create and activate a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Install system dependencies:**

    **Linux:**

    ```bash
    sudo apt-get update
    sudo apt-get install -y pcal ghostscript
    ```

    **macOS:**

    ```bash
    brew update; brew upgrade
    brew install pcal ghostscript
    ```

### Running the App Locally

1. **Set environment variables:**

    Create a `.env` file in the project root with the following content:

    ```plaintext
    FLASK_APP=run.py
    FLASK_ENV=development
    ```

2. **Run the Flask app:**

    ```bash
    cd app
    flask run --debug --host 0.0.0.0 --port 5001
    ```

3. **Access the app:**

    Open your web browser and go to `http://127.0.0.1:5001/`.

## Containerized Deployment

### Building the Docker Image

1. **Build the Docker image:**

    ```bash
    docker build -t tide-calendar-app .
    ```

### Running the Docker Container

1. **Run the Docker container:**

    ```bash
    docker run -p 5001:5001 tide-calendar-app
    ```

2. **Access the app:**

    Open your web browser and go to `http://127.0.0.1:5001/`.

## Project Structure

```plaintext
tide_calendar/
├── app/
│   ├── __init__.py
│   ├── routes.py                    # Web routes with form validation and API endpoints
│   ├── get_tides.py                 # Tide data processing and PDF generation
│   ├── database.py                  # SQLite operations and station search functions
│   ├── tide_stations_new.csv        # Canonical tide station database (2,900+ stations)
│   ├── tide-stations-raw-new.md     # Raw NOAA station data source
│   ├── tide_station_ids.db          # SQLite database with usage tracking
│   ├── templates/
│   │   ├── index.html               # Main interface with autocomplete
│   │   └── tide_station_not_found.html
│   └── static/
│       ├── style.css
│       ├── favicon.ico
│       └── tide-calendar-example.webp
├── convert_stations_final.py        # Utility to convert MD to CSV with proper formatting
├── run.py                          # Application entry point
├── requirements.txt
├── Dockerfile
├── CLAUDE.md                       # Development documentation
└── README.md
```

## Explanation of Key Files

- **app/__init__.py**: Initializes the Flask app and database.
- **app/routes.py**: Web routes with form validation, API endpoints for autocomplete, and cookie management.
- **app/get_tides.py**: Script to generate the PDF calendar with tide information.
- **app/database.py**: SQLite operations including station search, autocomplete, and usage tracking.
- **app/tide_stations_new.csv**: Canonical database of 2,900+ tide stations with proper place names.
- **app/templates/index.html**: Main web interface with intelligent autocomplete and responsive design.
- **app/static/**: Contains CSS styling, favicon, and example images.
- **convert_stations_final.py**: Utility script to convert raw NOAA data to properly formatted CSV.
- **run.py**: Entry point to run the Flask app with automatic database initialization.
- **CLAUDE.md**: Development documentation and architecture overview.
- **requirements.txt**: List of Python dependencies.
- **Dockerfile**: Instructions to build the Docker image.

## Features

- **Smart Autocomplete**: Search tide stations by place name with intelligent suggestions
- **Comprehensive Database**: 2,900+ tide stations with proper geographic disambiguation
- **User-Friendly Interface**: Type place names like "Point Roberts, WA" or use station IDs
- **Remember Last Used**: Automatically remembers your last successful location
- **PDF Generation**: Creates downloadable monthly tide calendars

## Usage

### Method 1: Place Name Search (Recommended)
1. Start typing a place name (e.g., "Seattle", "Miami", "San Francisco")
2. Select from the autocomplete dropdown suggestions
3. Choose your desired year and month
4. Click "Generate and download the PDF"

### Method 2: Direct Entry
1. Type a complete place name (e.g., "Point Roberts, WA")
2. Choose your desired year and month
3. Click "Generate and download the PDF"

### Method 3: Station ID (Advanced)
1. Enter a 7-digit NOAA tide station ID directly
2. Choose your desired year and month
3. Click "Generate and download the PDF"

## Notes

- Ensure `pcal` and `ghostscript` are installed on your system if running locally.
- The app defaults to "Point Roberts, WA" for demonstration purposes.
- All tide stations are sourced from NOAA's official tide station database.
- The application automatically tracks popular stations for better autocomplete suggestions.

For deployment, it's common practice to use standard HTTP (port 80) or HTTPS (port 443) ports to make the application accessible over the web without specifying a port number in the URL. Here’s how you can set this up in your Docker deployment.

### Using Port 80 or 443

1. **Modify the Docker Run Command**
   
   To use port 80 or 443, map the internal port 5001 to the desired external port.

   **For HTTP (port 80):**
   ```bash
   docker run -p 80:5001 tide-calendar-app
   ```

   **For HTTPS (port 443):**
   ```bash
   docker run -p 443:5001 tide-calendar-app
   ```

2. **Using HTTPS (port 443)**

   If you are using HTTPS, you'll need to set up SSL/TLS certificates. This is typically done using a reverse proxy like Nginx or a cloud provider's load balancer that handles SSL termination.

### Example with Nginx as a Reverse Proxy

1. **Nginx Configuration**

   Create an Nginx configuration file to proxy requests to your Flask app running inside Docker.

   **nginx.conf:**

   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://localhost:5001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

2. **Docker Compose**

   You can use Docker Compose to run both your Flask app and Nginx.

   **docker-compose.yml:**

   ```yaml
   version: '3'
   services:
     app:
       build: .
       ports:
         - "5001:5001"
       environment:
         FLASK_ENV: production

     nginx:
       image: nginx:latest
       ports:
         - "80:80"
       volumes:
         - ./nginx.conf:/etc/nginx/conf.d/default.conf
       depends_on:
         - app
   ```

3. **Building and Running with Docker Compose**

   ```bash
   docker-compose up --build
   ```

### SSL with Let's Encrypt

If you are using port 443, you’ll need to set up SSL certificates. Let’s Encrypt is a popular free option. Here’s a basic setup using Certbot with Nginx.

1. **Install Certbot**

   Install Certbot and the Nginx plugin on your server.

   **For Ubuntu:**

   ```bash
   sudo apt-get update
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Obtain and Install SSL Certificate**

   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

   Follow the prompts to obtain and install the certificate.

3. **Automatic Renewal**

   Certbot automatically installs a cron job for certificate renewal. You can test the renewal process with:

   ```bash
   sudo certbot renew --dry-run
   ```

### Summary

- For production deployment, map port 5001 to port 80 for HTTP or port 443 for HTTPS in your Docker run command.
- Use Nginx as a reverse proxy to manage incoming traffic and SSL termination.
- Obtain and configure SSL certificates if using HTTPS, using tools like Certbot and Let's Encrypt.

## Troubleshooting

- If you encounter a `500 Internal Server Error`, check the Flask console output for detailed error messages.
- Ensure all environment variables are set correctly, and dependencies are installed.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for review.

## License

This project is licensed under the GNU GPL v3 License.

