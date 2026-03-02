# Project Overview

This project is a Python application designed to calculate employee attendance based on contract data. It appears to be a backend service that connects to a database to fetch employee and contract information, and then performs calculations based on this data.

The application is containerized using Docker and orchestrated with Docker Compose, suggesting it's designed to be run as a microservice.

# Building and Running

Dependencies:

- Python
- Docker
- Docker Compose

## Running the application:

The `docker-compose.yml` file suggests that the application can be started with the following command:

```
docker-compose up
```

This will build the Docker image and start the application and any services it depends on (like a database).

# Development Conventions

- The project uses `uv` for package management, as indicated by the `pyproject.toml` file.
- The code is structured into an `app` directory, with a clear separation of concerns:
    - `models/`: Defines the database schema.
    - `database/`: Handles the database connection and queries.
    - `calculation/`: Implements the core business logic for attendance calculation.
    - `logics/`: Contains business logic for features like CSV comparison.
    - `server/`: Defines the API endpoints.
- The main entry point of the application is `app.server.endpoint:app`, and it's started with `uvicorn`.

# Testing

- Tests can be run using `pytest`. From the project root, execute:

```
PYTHONPATH=. pytest
```

This file was created by a Gemini agent.
