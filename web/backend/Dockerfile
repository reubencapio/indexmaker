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

# Copy dependency files (cache bust when lock changes)
ARG CACHEBUST=1
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies (no-root to avoid installing the package itself yet)
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Copy application code
COPY . .

# Create supervisor configuration directory
RUN mkdir -p /etc/supervisor/conf.d

# Copy supervisor configuration (handle both build contexts)
RUN if [ -f supervisord.conf ]; then \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf; \
    elif [ -f web/backend/supervisord.conf ]; then \
    cp web/backend/supervisord.conf /etc/supervisor/conf.d/supervisord.conf; \
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
