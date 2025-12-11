FROM python:3.13-slim

WORKDIR /app

# Install system dependencies including curl and lsb-release for gcsfuse
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    lsb-release \
    ca-certificates \
    gnupg \
    fuse \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and README.md for package installation
COPY pyproject.toml README.md /app/

# Copy backend code (needed for package installation)
COPY backend/ /app/backend/

# Copy external directory (for configs only)
COPY external/ /app/external/

# Install unified-cloud-services from GitHub
# Supports GitHub token for private repos via build arg
ARG GITHUB_TOKEN
ARG GITHUB_USER=IggyIkenna

RUN if [ -n "$GITHUB_TOKEN" ]; then \
        echo "🔐 Installing unified-cloud-services with GitHub token"; \
        pip install --no-cache-dir "git+https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/unified-cloud-services.git"; \
    else \
        echo "📦 Installing unified-cloud-services from GitHub"; \
        pip install --no-cache-dir "git+https://github.com/${GITHUB_USER}/unified-cloud-services.git"; \
    fi

# Install execution-services package in editable mode (replaces PYTHONPATH)
RUN pip install --no-cache-dir -e .

# Set environment variables (PYTHONPATH no longer needed - package is installed)
ENV UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads
ENV UNIFIED_CLOUD_SERVICES_USE_PARQUET=true
ENV UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=false
ENV DATA_CATALOG_PATH=/app/backend/data/parquet

# Create necessary directories
RUN mkdir -p /app/backend/data/parquet \
    /app/backend/backtest_results/fast \
    /app/backend/backtest_results/report \
    /app/frontend/public/tickdata \
    /app/data_downloads \
    /app/backend/scripts

# Copy scripts
COPY backend/scripts/ /app/backend/scripts/

# Make scripts executable
RUN chmod +x /app/backend/run_backtest.py && \
    find /app/backend/scripts -name "*.sh" -type f -exec chmod +x {} \; || true

# Default command (use start.sh for API server, or run_backtest.py for CLI)
CMD ["bash", "/app/backend/scripts/start.sh"]

