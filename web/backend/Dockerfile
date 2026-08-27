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

# Install Poetry into its own virtualenv.
#
# Two things matter here:
#   1. The version must match the one that generated poetry.lock. The lock files
#      are lock-version 2.1, which only Poetry 2.x can read; Poetry 1.7 silently
#      ignored them and re-resolved every dependency from scratch.
#   2. Poetry must NOT share site-packages with the project. Because
#      `virtualenvs.create false` (below) installs project dependencies into the
#      system interpreter, a shared install lets dependency resolution overwrite
#      Poetry's own libraries mid-run -- which broke the build when `packaging`
#      was swapped out while Poetry was building the `multitasking` sdist.
ENV POETRY_VERSION=2.1.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1
# Only the `poetry` entrypoint is exposed, via symlink. Putting
# $POETRY_HOME/bin on PATH would shadow `python`/`python3` with the Poetry
# venv's interpreter, and supervisord starts every service as `python -m ...`
# -- the image would build fine and then fail to run.
RUN python -m venv "$POETRY_HOME" \
    && "$POETRY_HOME/bin/pip" install --no-cache-dir "poetry==$POETRY_VERSION" \
    && ln -s "$POETRY_HOME/bin/poetry" /usr/local/bin/poetry

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

# Install the application itself (root package) now that the code is present.
# --only main keeps pytest/black/ruff/mypy/pre-commit out of the runtime image.
RUN poetry install --no-interaction --no-ansi --only main

# NOTE: a `pip install google-generativeai` fallback used to live here. It is a
# locked main dependency, so it is installed above; running pip after Poetry
# would re-resolve packages outside the lock and risk the same corruption.

# Expose port
EXPOSE 8000

# Default command
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
