# Backtest Component Environment Variables Review

## Summary

This document reviews the `.env` file configuration for the backtest component, identifies issues, and provides a reorganized structure.

## Issues Found

### 1. Missing Critical Variable
- **`EXECUTION_STORE_GCS_BUCKET`** is used in code (`backend/results/serializer.py`) but missing from `.env`
  - Code uses: `os.getenv("EXECUTION_STORE_GCS_BUCKET", "execution-store-cefi-central-element-323112")`
  - This is the bucket where backtest results are uploaded

### 2. Confusing/Unused Variable
- **`GCS_BUCKET`** is mentioned in `.env` as "GCS Bucket for backtest results" but:
  - It's NOT actually used in the backtest codebase
  - Only used as fallback in one script: `backend/scripts/utils/list_gcs_dates_and_files.py`
  - The actual variable used is `EXECUTION_STORE_GCS_BUCKET`

### 3. Inconsistent Bucket Naming
- Input data bucket: `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` (for reading market data)
- Output results bucket: `EXECUTION_STORE_GCS_BUCKET` (for uploading results)
- FUSE bucket: `GCS_FUSE_BUCKET` (for mounting)
- Legacy/unused: `GCS_BUCKET` (confusing, should be removed)

### 4. Poor Organization
- Variables are mixed together without clear sections
- No clear separation between input/output/authentication/config
- Comments are unclear about which variables are required vs optional

## Reorganized .env Structure

```bash
# ==============================================================================
# BACKTEST COMPONENT - Environment Configuration
# ==============================================================================
# Copy this file to .env and fill in your values
# DO NOT commit .env to version control (it contains sensitive credentials)
#
# This configuration is specifically for the backtest component.
# Variables are organized by purpose for clarity.
# ==============================================================================

# ------------------------------------------------------------------------------
# Google Cloud Platform (GCP) Authentication
# ------------------------------------------------------------------------------
# Required for all GCS operations (reading data, uploading results)

# GCP Project ID
GCP_PROJECT_ID=central-element-323112

# Path to GCP service account JSON key file
# This file must exist and contain valid credentials for GCS access
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json


# ------------------------------------------------------------------------------
# Input Data Storage (Market Data)
# ------------------------------------------------------------------------------
# Configuration for reading raw market data (trades, book snapshots) from GCS

# GCS bucket containing raw market data Parquet files
# Used by: backend/data/loader.py (UCSDataLoader)
UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick

# Local path for data when using FUSE mount or local filesystem
# Used when: UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=false (FUSE mode)
# Default: /app/data_downloads (Docker) or ./data_downloads (local)
UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads

# Use direct GCS API access instead of FUSE mount
# Set to 'true' to use GCS API directly (recommended for cloud deployments)
# Set to 'false' to use FUSE mount or local filesystem
# Used by: backend/data/loader.py, backend/config/loader.py
UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true

# Use Parquet format for data (always true for this system)
UNIFIED_CLOUD_SERVICES_USE_PARQUET=true


# ------------------------------------------------------------------------------
# Backtest Catalog Storage (NautilusTrader Catalog)
# ------------------------------------------------------------------------------
# Configuration for storing converted Parquet data in NautilusTrader catalog format
# The catalog is where converted data is stored for fast backtest execution

# Path to catalog root directory
# Local path: /app/backend/data/parquet (Docker) or backend/data/parquet (local)
# GCS path: gcs://bucket-name/path/to/catalog/ (for cloud storage)
# Used by: backend/core/engine.py, backend/catalog_manager.py, backend/data/catalog.py
DATA_CATALOG_PATH=/app/backend/data/parquet


# ------------------------------------------------------------------------------
# Backtest Results Storage (Output)
# ------------------------------------------------------------------------------
# Configuration for uploading backtest results to GCS

# GCS bucket for storing backtest results (output)
# Used by: backend/results/serializer.py, backend/scripts/utils/upload_backtest_results_to_gcs.py
# Results are uploaded to: gs://{EXECUTION_STORE_GCS_BUCKET}/fast/ and gs://{EXECUTION_STORE_GCS_BUCKET}/report/
EXECUTION_STORE_GCS_BUCKET=execution-store-cefi-central-element-323112


# ------------------------------------------------------------------------------
# GCS FUSE Mount Configuration (Optional)
# ------------------------------------------------------------------------------
# Configuration for mounting GCS buckets as local filesystem (alternative to direct GCS API)

# Enable GCS FUSE mounting
# Set to 'true' to mount GCS bucket as local filesystem
# Set to 'false' to use direct GCS API (recommended)
# Used by: backend/api/mount_status.py, backend/scripts/mount_gcs.sh
USE_GCS_FUSE=false

# GCS bucket name for FUSE mounting (if USE_GCS_FUSE=true)
# Typically same as UNIFIED_CLOUD_SERVICES_GCS_BUCKET for input data
# Used by: backend/api/mount_status.py, backend/scripts/mount_gcs.sh
GCS_FUSE_BUCKET=

# GCS Service Account Key for FUSE mounting (if different from GOOGLE_APPLICATION_CREDENTIALS)
# Usually not needed - uses GOOGLE_APPLICATION_CREDENTIALS by default
GCS_SERVICE_ACCOUNT_KEY=
```

## Variable Usage Map

### Authentication
| Variable | Used In | Purpose |
|----------|---------|---------|
| `GCP_PROJECT_ID` | `catalog_manager.py`, `data/catalog.py` | GCP project identification |
| `GOOGLE_APPLICATION_CREDENTIALS` | All GCS operations | Service account key path |

### Input Data (Market Data)
| Variable | Used In | Purpose |
|----------|---------|---------|
| `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` | `data/loader.py` | GCS bucket for raw market data |
| `UNIFIED_CLOUD_LOCAL_PATH` | `data/loader.py`, `config/loader.py`, `core/engine.py` | Local path for FUSE/local data |
| `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS` | `data/loader.py`, `config/loader.py` | Enable direct GCS API vs FUSE |
| `UNIFIED_CLOUD_SERVICES_USE_PARQUET` | `docker-compose.yml` | Use Parquet format |

### Catalog Storage
| Variable | Used In | Purpose |
|----------|---------|---------|
| `DATA_CATALOG_PATH` | `core/engine.py`, `catalog_manager.py`, `data/catalog.py` | NautilusTrader catalog location |

### Output (Results)
| Variable | Used In | Purpose |
|----------|---------|---------|
| `EXECUTION_STORE_GCS_BUCKET` | `results/serializer.py`, `scripts/utils/upload_backtest_results_to_gcs.py` | GCS bucket for backtest results |

### FUSE Mount (Optional)
| Variable | Used In | Purpose |
|----------|---------|---------|
| `USE_GCS_FUSE` | `api/mount_status.py` | Enable FUSE mounting |
| `GCS_FUSE_BUCKET` | `api/mount_status.py`, `scripts/mount_gcs.sh` | Bucket to mount via FUSE |
| `GCS_SERVICE_ACCOUNT_KEY` | `scripts/mount_gcs.sh` | Alternative credentials for FUSE |

## Key Changes from Current .env

1. **Added** `EXECUTION_STORE_GCS_BUCKET` (was missing but used in code)
2. **Removed** `GCS_BUCKET` (confusing, not actually used)
3. **Removed** commented-out optional bucket variables (kept only active ones)
4. **Organized** into clear sections by purpose
5. **Added** detailed comments explaining each variable's usage
6. **Clarified** which variables are required vs optional

## Required vs Optional Variables

### Required (must be set)
- `GCP_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `UNIFIED_CLOUD_SERVICES_GCS_BUCKET`
- `DATA_CATALOG_PATH`
- `EXECUTION_STORE_GCS_BUCKET`

### Optional (have defaults)
- `UNIFIED_CLOUD_LOCAL_PATH` (defaults to `/app/data_downloads`)
- `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS` (defaults to `false`)
- `UNIFIED_CLOUD_SERVICES_USE_PARQUET` (defaults to `true`)
- `USE_GCS_FUSE` (defaults to `false`)
- `GCS_FUSE_BUCKET` (only needed if `USE_GCS_FUSE=true`)
- `GCS_SERVICE_ACCOUNT_KEY` (uses `GOOGLE_APPLICATION_CREDENTIALS` by default)

## Recommendations

1. **Update `.env` file** with the reorganized structure above
2. **Remove** `GCS_BUCKET` variable (not used)
3. **Add** `EXECUTION_STORE_GCS_BUCKET` variable (currently missing)
4. **Consider** using the same bucket for input and output if appropriate:
   - If using same bucket: `EXECUTION_STORE_GCS_BUCKET=market-data-tick`
   - If using different buckets: Keep them separate as shown
5. **Document** bucket organization strategy in project README

## Bucket Organization Strategy

The system uses two separate buckets by default:

1. **Input Bucket** (`UNIFIED_CLOUD_SERVICES_GCS_BUCKET`):
   - Contains raw market data (Parquet files)
   - Structure: `raw_tick_data/by_date/day-YYYY-MM-DD/data_type-{trades|book_snapshot_5}/{instrument_id}.parquet`
   - Read-only access needed

2. **Output Bucket** (`EXECUTION_STORE_GCS_BUCKET`):
   - Contains backtest results
   - Structure: `fast/{run_id}.json` and `report/{run_id}/summary.json` + parquet files
   - Write access needed

These can be the same bucket or different buckets depending on your organization's needs.

