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

# Copy requirements
COPY backend/requirements.txt /app/requirements.txt

# Copy external directory first (may contain unified-cloud-services)
COPY external/ /app/external/

# Check if unified-cloud-services exists locally, otherwise use GitHub token
# Priority: 1) Local copy, 2) GitHub token, 3) Direct (will fail for private repos)
ARG GITHUB_TOKEN
ARG GITHUB_USER=IggyIkenna

# Install Python dependencies
# Strategy: Try local copy first, then tokenized URL, then direct
RUN if [ -d "/app/external/unified-cloud-services" ] && ([ -f "/app/external/unified-cloud-services/setup.py" ] || [ -f "/app/external/unified-cloud-services/pyproject.toml" ]); then \
        echo "✅ Using local unified-cloud-services package"; \
        sed -i '/git+https:\/\/github.com\/IggyIkenna\/unified-cloud-services.git/d' /app/requirements.txt && \
        pip install --no-cache-dir /app/external/unified-cloud-services && \
        pip install --no-cache-dir -r requirements.txt; \
    elif [ -n "$GITHUB_TOKEN" ]; then \
        echo "🔐 Using GitHub token for private repo access"; \
        sed -i "s|git+https://github.com/${GITHUB_USER}/unified-cloud-services.git|git+https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/unified-cloud-services.git|g" /app/requirements.txt && \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "⚠️  No local copy or token found, attempting direct install (may fail for private repos)"; \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy backend code
COPY backend/ /app/backend/

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

