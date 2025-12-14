# IndexMaker Backend

FastAPI backend for the IndexMaker web platform.

## Quick Start

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload --port 8000
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_PORT`: PostgreSQL port
- `POSTGRES_USER`: Database username
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_DB`: Database name
- `SECRET_KEY`: JWT secret key

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc



