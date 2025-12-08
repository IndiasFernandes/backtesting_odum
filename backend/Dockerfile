FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl and lsb-release for gcsfuse
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    lsb-release \
    ca-certificates \
    gnupg \
    fuse \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/backend/
COPY external/ /app/external/

# Set environment variables
ENV PYTHONPATH=/app
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
RUN chmod +x /app/backend/run_backtest.py \
    /app/backend/scripts/*.sh

# Default command (use start.sh for API server, or run_backtest.py for CLI)
CMD ["bash", "/app/backend/scripts/start.sh"]

