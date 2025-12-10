"""
Cloud Configuration

Generic cloud configuration classes for unified cloud services.
Works across all domains (market_data, features, strategy, ml, execution).

Automatically loads .env files if they exist (DRY: centralized env loading).

GCS FUSE MOUNTING (for local development and cloud deployment):
==============================================================
GCS FUSE allows mounting a GCS bucket as a local filesystem for fast I/O.
This is particularly useful for backtesting where you need to read large
amounts of tick data efficiently.

INSTALLATION:
  macOS:   brew install gcsfuse
  Ubuntu:  apt-get install gcsfuse
  Docker:  gcsfuse is available as an apt package

LOCAL DEV MOUNTING:
  # Create mount point
  mkdir -p ~/gcs/market-data-tick-central-element-323112

  # Mount bucket (requires gcloud auth)
  gcsfuse --implicit-dirs market-data-tick-central-element-323112 ~/gcs/market-data-tick-central-element-323112

  # Set environment variable for UCS auto-detection
  export GCS_FUSE_MOUNT_PATH=~/gcs/market-data-tick-central-element-323112

CLOUD DEPLOYMENT (GCE):
  # GCS FUSE is pre-installed on most GCE images
  # Mount at /mnt/gcs for auto-detection by UCS

  gcsfuse --implicit-dirs market-data-tick-central-element-323112 /mnt/gcs/market-data-tick-central-element-323112

AUTO-DETECTION:
  UCS automatically checks these paths for mounted buckets:
  - $GCS_FUSE_MOUNT_PATH (environment variable)
  - /mnt/gcs/{bucket_name}
  - /gcs/{bucket_name}
  - ~/gcs/{bucket_name}
  - /mnt/disks/gcs/{bucket_name} (GCE default)

PERFORMANCE NOTES:
  - GCS FUSE is significantly faster than network API calls for local I/O
  - Best used when running in the same region as the GCS bucket
  - For backtesting, this can reduce data loading time by 10-100x
"""

import logging
from dataclasses import dataclass
from unified_cloud_services.core.config import unified_config

logger = logging.getLogger(__name__)


@dataclass
class CloudConfig:
    """Unified cloud configuration for all use cases"""

    default_project_id: str = unified_config.gcp_project_id
    default_region: str = unified_config.gcs_region
    default_location: str = unified_config.bigquery_location

    # Credentials handling
    credentials_path: str = unified_config.google_application_credentials_path
    environment: str = unified_config.environment

    # Performance optimization
    connection_pool_size: int = 3
    max_concurrent_uploads: int = 5
    warmup_enabled: bool = True

    # Retry configuration
    retry_attempts: int = 3
    retry_initial_delay: float = 1.0
    retry_max_delay: float = 60.0

    # Timeouts
    upload_timeout: int = 300
    download_timeout: int = 300
    query_timeout: int = 60


@dataclass
class CloudTarget:
    """Runtime-configurable cloud target for specific operations"""

    gcs_bucket: str
    bigquery_dataset: str
    project_id: str = unified_config.gcp_project_id
    region: str = unified_config.gcs_region
    bigquery_location: str = unified_config.bigquery_location

    def __post_init__(self):
        """Fill in defaults from environment if not specified and apply test suffix if needed"""
        # Auto-append _test suffix for datasets/buckets when ENVIRONMENT=test
        environment = unified_config.environment.lower()
        if environment == "test":
            test_suffix = "_test"
            if not self.gcs_bucket.endswith(test_suffix):
                self.gcs_bucket = f"{self.gcs_bucket}{test_suffix}"
            if not self.bigquery_dataset.endswith(test_suffix):
                self.bigquery_dataset = f"{self.bigquery_dataset}{test_suffix}"
