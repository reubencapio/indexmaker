# Backend Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    supervisor \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# -------------------------------------------------------------------
# Monorepo setup: Copy root library (indexforge) for local dependency
# -------------------------------------------------------------------
# Copy root config
COPY pyproject.toml poetry.lock* README.md LICENSE* ./
# Copy root source (indexforge)
COPY src ./src

# -------------------------------------------------------------------
# Backend Setup
# -------------------------------------------------------------------
WORKDIR /app/web/backend

# Copy backend dependency files
COPY web/backend/pyproject.toml web/backend/poetry.lock* ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies
# (poetry.lock refers to ../../ which maps to /app containing indexforge)
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Copy application code
COPY web/backend .

# Create supervisor configuration directory
RUN mkdir -p /etc/supervisor/conf.d

# Copy supervisor configuration
RUN if [ -f supervisord.conf ]; then \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf; \
    else \
    echo "ERROR: supervisord.conf not found" && exit 1; \
    fi

# Install the application
RUN poetry install --no-interaction --no-ansi

# Ensure google-generativeai is installed (explicit fallback)
RUN pip install google-generativeai>=0.8.0

# Expose port
EXPOSE 8000

# Default command
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
