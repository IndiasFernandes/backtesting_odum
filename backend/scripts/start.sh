#!/bin/bash
# Startup script for backend container
# Handles GCS FUSE mounting and API server startup

set -e

# Validate required environment variables (fail-fast for security)
# Following best practices: sensitive values should not have defaults and must be explicitly set
REQUIRED_VARS=(
    "GCP_PROJECT_ID"
    "UNIFIED_CLOUD_SERVICES_GCS_BUCKET"
    "EXECUTION_STORE_GCS_BUCKET"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "ERROR: Required environment variables are not set:" >&2
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var" >&2
    done
    echo "" >&2
    echo "Please set these variables in your .env file." >&2
    echo "See .env.example for a template." >&2
    exit 1
fi

# Install unified-cloud-services if available (for runtime installation when using volume mounts)
if [ -d "/app/external/unified-cloud-services" ] && [ -f "/app/external/unified-cloud-services/pyproject.toml" ]; then
    if ! python3 -c "import unified_cloud_services" 2>/dev/null; then
        echo "Installing unified-cloud-services from mounted directory..."
        cd /app/external/unified-cloud-services
        pip install --no-cache-dir . 2>&1 | grep -E "(Successfully|Requirement|ERROR)" || true
        cd /app
    fi
fi

# Run GCS FUSE mount script if needed
if [ -f "/app/backend/scripts/mount_gcs.sh" ]; then
    bash /app/backend/scripts/mount_gcs.sh || {
        echo "Warning: GCS FUSE mount failed, but continuing with local volume..."
    }
fi

# Start API server
echo "Starting API server..."
exec python -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8000

