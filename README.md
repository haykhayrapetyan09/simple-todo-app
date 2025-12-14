# simple-todo-app

A todo app with web UI built with Flask and PostgreSQL.

## App UI

![Todo App UI](resources/image.png)

## Run with Docker Compose

```bash
# Start both app and database
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (clears data)
docker-compose down -v

# Open browser: http://localhost:5000
```

## Run Locally

```bash
# Start PostgreSQL database
docker run -d \
  --name postgres-todo \
  -e POSTGRES_DB=tododb \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=tododb
export DB_USER=postgres
export DB_PASSWORD=postgres

# Run app
cd src && python3 app.py

# Open browser: http://localhost:5000
```
