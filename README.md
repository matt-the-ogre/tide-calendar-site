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
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Install system dependencies:**

    ```bash
    sudo apt-get update
    sudo apt-get install -y pcal ghostscript
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
    flask run
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
│   ├── routes.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       └── style.css
├── get_tides.py
├── run.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## Explanation of Key Files

- **app/__init__.py**: Initializes the Flask app.
- **app/routes.py**: Contains the route for the web interface.
- **app/templates/index.html**: HTML template for the web interface.
- **app/static/style.css**: CSS file for styling the web interface.
- **get_tides.py**: Script to generate the PDF calendar with tide information.
- **run.py**: Entry point to run the Flask app.
- **requirements.txt**: List of Python dependencies.
- **Dockerfile**: Instructions to build the Docker image.

## Usage

1. Enter the tide station ID, year, and month in the web form.
2. Click "Generate PDF" to create and download the tide calendar.

## Notes

- Ensure `pcal` and `ghostscript` are installed on your system if running locally.
- The default tide station ID is set to `9449639` for demonstration purposes.

## Troubleshooting

- If you encounter a `500 Internal Server Error`, check the Flask console output for detailed error messages.
- Ensure all environment variables are set correctly, and dependencies are installed.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for review.

## License

This project is licensed under the GNU GPL v3 License.
