# Dockerfile for unified-cloud-services with GCS FUSE support
#
# This Dockerfile provides a Python environment with:
# - unified-cloud-services package
# - gcsfuse for mounting GCS buckets
# - gcloud CLI for authentication
#
# Build:
#   docker build -t unified-cloud-services .
#
# Run with GCS FUSE:
#   docker run --privileged -v /dev/fuse:/dev/fuse unified-cloud-services
#
# For production (GKE with Workload Identity):
#   - Use the sidecar pattern with gcsfuse CSI driver
#   - See: https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/cloud-storage-fuse-csi-driver

FROM python:3.11-slim

# Install system dependencies for gcsfuse
# Clean cache before and after to save space
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    lsb-release \
    fuse \
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install gcsfuse
# Use modern GPG key method (apt-key is deprecated in newer Debian)
RUN export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s) && \
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/gcsfuse.gpg && \
    echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | tee /etc/apt/sources.list.d/gcsfuse.list && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    apt-get update && \
    apt-get install -y gcsfuse && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install Google Cloud SDK (for gcloud auth)
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir=/opt \
    && ln -s /opt/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud \
    && ln -s /opt/google-cloud-sdk/bin/gsutil /usr/local/bin/gsutil

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create default mount point
RUN mkdir -p /mnt/gcs

# Environment variables for GCS FUSE auto-detection
ENV GCS_FUSE_MOUNT_PATH=/mnt/gcs
ENV PYTHONUNBUFFERED=1

# Health check script
RUN echo '#!/bin/bash\npython -c "from unified_cloud_services import UnifiedCloudService; print(\"OK\")"' > /healthcheck.sh \
    && chmod +x /healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /healthcheck.sh

# Default entrypoint - can be overridden
ENTRYPOINT ["python"]
CMD ["-c", "from unified_cloud_services.core.gcsfuse_helper import GCSFuseHelper; GCSFuseHelper().print_status()"]

