# Gmail Digest Assistant v2.0 Dockerfile
#
# Build:  docker build -t gmaildigest:2.0 .
# Run:    docker run -it --rm \
#           -v ./config/.env.json:/app/.env.json:ro \
#           -v ./config/credentials.json:/app/credentials.json:ro \
#           -v ./data:/app/data \
#           gmaildigest:2.0
#
# Note: Setup wizard not supported in Docker. Run it on your host first.

FROM python:3.11-slim AS builder

# Install system dependencies for building packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        libsqlite3-dev \
        git \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set up working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml ./
COPY README.md ./

# Install dependencies (without dev dependencies)
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Second stage: runtime image
FROM python:3.11-slim

# Set labels
LABEL maintainer="Kai Peace <kai@peacefamily.us>" \
      name="Gmail Digest Assistant" \
      version="2.0.0" \
      description="Intelligent email summarization and notification system"

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libffi7 \
        libsqlite3-0 \
        libsqlcipher0 \
        ca-certificates \
        tzdata && \
    rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ /app/src/
COPY README.md /app/

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/config && \
    chmod 755 /app/data /app/logs /app/config

# Create a non-root user to run the application
RUN groupadd -r gda && \
    useradd -r -g gda -d /app -s /bin/bash gda && \
    chown -R gda:gda /app

# Switch to non-root user
USER gda

# Set environment variables
ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    TZ=UTC \
    GDA_APP__DATA_DIR="/app/data" \
    GDA_APP__ENVIRONMENT="production"

# Set up a health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health') or exit(1)"

# Expose health check port
EXPOSE 8080

# Set the entrypoint
ENTRYPOINT ["python", "-m", "gda.cli", "run"]

# Default command (can be overridden)
CMD ["--log-level", "INFO"]
