# Project Overview

  This project is a Python application designed to calculate employee attendance based on contract data. It
  appears to be a backend service that connects to a database to fetch employee and contract information, and
  then performs calculations based on this data.

  The application is containerized using Docker and orchestrated with Docker Compose, suggesting it's designed
  to be run as a microservice.

## Building and Running

  Dependencies:

   * Python
   * Docker
   * Docker Compose
   * uv (Python package manager)

## Running the application:

  The docker-compose.yml file suggests that the application can be started with the following command:

   1 docker-compose up

  This will build the Docker image and start the application and any services it depends on (like a database).

  TODO: Add specific instructions on how to set up the database and any other dependencies.

## Development Conventions

   * The project uses uv for package management, as indicated by the uv.lock and pyproject.toml files.
   * The code is structured into an app directory, with a clear separation of concerns:
       * models.py: Defines the database schema.
       * database_base.py: Handles the database connection.
       * attendance_contract_query.py: Contains queries for fetching data.
       * calc_work_classes3.py: Implements the core business logic for attendance calculation.
   * The main entry point of the application is main.py.
   * The project uses .flake8 for linting, so it's recommended to run flake8 before committing any changes.

## Testing

   * Tests can be run using `pytest`. From the project root, execute:
     `PYTHONPATH=. pytest`
