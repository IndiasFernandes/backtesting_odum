#!/bin/bash
# GCS FUSE mount script for backend container
# This script mounts a GCS bucket to /app/data_downloads if GCS_FUSE_BUCKET is set

set -e

MOUNT_POINT="/app/data_downloads"
GCS_BUCKET="${GCS_FUSE_BUCKET:-}"
SERVICE_ACCOUNT_KEY="${GCS_SERVICE_ACCOUNT_KEY:-}"
USE_FUSE="${USE_GCS_FUSE:-false}"

# Check if FUSE should be used
if [ "$USE_FUSE" != "true" ] || [ -z "$GCS_BUCKET" ]; then
    echo "GCS FUSE not enabled or bucket not specified. Using local volume."
    exit 0
fi

echo "Setting up GCS FUSE mount..."

# Install gcsfuse if not already installed
if ! command -v gcsfuse &> /dev/null; then
    echo "Installing gcsfuse..."
    export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
    echo "deb http://packages.cloud.google.com/apt $GCSFUSE_REPO main" | tee /etc/apt/sources.list.d/gcsfuse.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
    apt-get update
    apt-get install -y gcsfuse
fi

# Check if mount point is already mounted (local volume)
if mountpoint -q "$MOUNT_POINT"; then
    echo "Warning: $MOUNT_POINT is already mounted (likely a local volume)"
    echo "Unmounting local volume to allow FUSE mount..."
    umount "$MOUNT_POINT" 2>/dev/null || {
        echo "Error: Could not unmount existing mount. Please remove volume mount from docker-compose.yml"
        exit 1
    }
fi

# Create mount point if it doesn't exist
mkdir -p "$MOUNT_POINT"

# Handle authentication
if [ -n "$SERVICE_ACCOUNT_KEY" ]; then
    # Service account key provided as environment variable (base64 encoded)
    echo "Using service account key from environment variable..."
    echo "$SERVICE_ACCOUNT_KEY" | base64 -d > /tmp/gcs-key.json
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs-key.json
elif [ -f "/app/gcs-key.json" ]; then
    # Service account key file mounted as volume
    echo "Using service account key from mounted file..."
    export GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
else
    # Try IAM authentication (if running on GCP)
    echo "Attempting IAM authentication (requires running on GCP)..."
fi

# Mount options
MOUNT_OPTIONS="--file-cache-ttl=1h --stat-cache-ttl=1h --type-cache-ttl=1h"

# Mount the bucket
echo "Mounting GCS bucket '$GCS_BUCKET' to '$MOUNT_POINT'..."
gcsfuse $MOUNT_OPTIONS "$GCS_BUCKET" "$MOUNT_POINT"

# Verify mount succeeded
if mountpoint -q "$MOUNT_POINT"; then
    echo "✓ GCS FUSE mount successful"
    echo "Bucket '$GCS_BUCKET' mounted at '$MOUNT_POINT'"
    
    # List a few files to verify access
    echo "Verifying mount access..."
    ls -la "$MOUNT_POINT" | head -5
else
    echo "✗ GCS FUSE mount failed"
    exit 1
fi

