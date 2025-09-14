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
    git clone https://github.com/yourusername/tide-calendar-generator.git
    cd tide-calendar-generator
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

Linux

    ```bash
    sudo apt-get update
    sudo apt-get install -y pcal ghostscript
    ```

MacOS

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
    flask run --host 0.0.0.0 --port 5001
    ```

3. **Access the app:**

    Open your web browser and go to `http://127.0.0.1:5000/`.

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
│   ├── routes.py           # Web routes with form validation
│   ├── get_tides.py        # Tide data processing and PDF generation
│   ├── database.py         # Centralized SQLite database operations
│   ├── templates/
│   │   └── index.html
│   └── static/
│       └── style.css
├── run.py                  # Application entry point
├── requirements.txt
├── Dockerfile
├── CLAUDE.md              # Development documentation
└── README.md
```

## Explanation of Key Files

- **app/__init__.py**: Initializes the Flask app.
- **app/routes.py**: Contains the web routes with form validation and error handling.
- **app/get_tides.py**: Script to generate the PDF calendar with tide information.
- **app/database.py**: Centralized SQLite database operations for station tracking.
- **app/templates/index.html**: HTML template for the web interface.
- **app/static/style.css**: CSS file for styling the web interface.
- **run.py**: Entry point to run the Flask app with database initialization.
- **CLAUDE.md**: Development documentation and architecture overview.
- **requirements.txt**: List of Python dependencies.
- **Dockerfile**: Instructions to build the Docker image.

## Usage

1. Enter the tide station ID, year, and month in the web form.
2. Click "Generate PDF" to create and download the tide calendar.

## Notes

- Ensure `pcal` and `ghostscript` are installed on your system if running locally.
- The default tide station ID is set to `9449639` for demonstration purposes.

For deployment, it's common practice to use standard HTTP (port 80) or HTTPS (port 443) ports to make the application accessible over the web without specifying a port number in the URL. Here’s how you can set this up in your Docker deployment.

### Using Port 80 or 443

1. **Modify the Docker Run Command**
   
   To use port 80 or 443, map the internal port 5000 to the desired external port.

   **For HTTP (port 80):**
   ```bash
   docker run -p 80:5000 tide-calendar-app
   ```

   **For HTTPS (port 443):**
   ```bash
   docker run -p 443:5000 tide-calendar-app
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
           proxy_pass http://localhost:5000;
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
         - "5000:5000"
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

- For production deployment, map port 5000 to port 80 for HTTP or port 443 for HTTPS in your Docker run command.
- Use Nginx as a reverse proxy to manage incoming traffic and SSL termination.
- Obtain and configure SSL certificates if using HTTPS, using tools like Certbot and Let's Encrypt.

## Troubleshooting

- If you encounter a `500 Internal Server Error`, check the Flask console output for detailed error messages.
- Ensure all environment variables are set correctly, and dependencies are installed.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for review.

## License

This project is licensed under the GNU GPL v3 License.
