FROM python:3.12-slim

# Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install poetry

# Configure Poetry to not create virtual environment
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_CREATE=false \
    POETRY_CACHE_DIR=/opt/poetry_cache \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock README.md ./

# Configure Poetry and install dependencies
RUN --mount=type=cache,target=/opt/poetry_cache \
    --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false && \
    poetry config virtualenvs.in-project false && \
    poetry install --only=main --no-root && \
    python -c "import uvicorn; import fastapi; print('All imports successful')"

# Create necessary directories
RUN mkdir -p /tmp/edgar_data /app/data /home/appuser/.edgar /home/appuser/.cache && \
    chmod -R 777 /tmp/edgar_data /app/data /home/appuser

# Set HOME environment variable
ENV HOME=/home/appuser

# Copy application and Alembic code
COPY ./src/ ./src/
COPY ./scripts/ ./scripts/
COPY ./alembic/ ./alembic/
COPY alembic.ini ./

# Change ownership to allow flexible user IDs and make scripts executable
RUN chmod -R 755 /app && \
    find /app/scripts -name "*.sh" -exec chmod +x {} \; && \
    find /app/scripts -name "*.py" -exec chmod +x {} \;

# Set entrypoint
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=3.0)"

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["app"]
