# Backend Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Create supervisor configuration directory
RUN mkdir -p /etc/supervisor/conf.d

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Install the application
RUN poetry install --no-interaction --no-ansi

# Expose port
EXPOSE 8000

# Default command
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

