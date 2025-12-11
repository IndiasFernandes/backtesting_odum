#!/bin/bash
# Startup script for backend container
# Handles GCS FUSE mounting and API server startup

set -e

# Run GCS FUSE mount script if needed
if [ -f "/app/backend/scripts/mount_gcs.sh" ]; then
    bash /app/backend/scripts/mount_gcs.sh || {
        echo "Warning: GCS FUSE mount failed, but continuing with local volume..."
    }
fi

# Start API server
echo "Starting API server..."
exec python -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8000

