# UCS Authentication Explained (Based on Official Docs)

Based on the [unified-cloud-services repository](https://github.com/IggyIkenna/unified-cloud-services), here's how authentication actually works:

## How UCS Handles Authentication

### Standard Authentication (What You're Using)

UCS uses **standard Google Cloud authentication** via `GOOGLE_APPLICATION_CREDENTIALS`:

```python
# UCS automatically uses GOOGLE_APPLICATION_CREDENTIALS environment variable
export GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
```

**How it works:**
1. UCS reads `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. Loads the service account JSON file
3. Uses it to authenticate with Google Cloud services (GCS, BigQuery, Secret Manager)

**From UCS docs:**
```bash
# Option A: Service account (recommended for production)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Option B: Personal credentials (for local development)
gcloud auth application-default login
```

---

## The 4 Environment Variables Explained

### 1. `GCP_PROJECT_ID`
**Purpose:** Identifies your Google Cloud project  
**Used by:** UCS to know which project to operate on  
**Example:** `central-element-323112`

```python
# UCS uses this for all cloud operations
cloud_target = CloudTarget(
    project_id=os.getenv('GCP_PROJECT_ID', 'central-element-323112'),
    ...
)
```

---

### 2. `GOOGLE_APPLICATION_CREDENTIALS`
**Purpose:** Path to service account JSON key file  
**Used by:** UCS (via Google Cloud libraries) for authentication  
**Points to:** `.secrets/gcs/gcs-service-account.json`

**How UCS uses it:**
```python
# From unified-cloud-services/core/cloud_auth_factory.py
credentials = service_account.Credentials.from_service_account_file(
    credentials_path  # This comes from GOOGLE_APPLICATION_CREDENTIALS
)
```

**Auto-detection:**
- UCS can auto-detect credentials in development mode
- Searches common locations if not explicitly set
- Production uses VM service account (no file needed)

---

### 3. `UNIFIED_CLOUD_SERVICES_GCS_BUCKET`
**Purpose:** Main GCS bucket for market data and instruments  
**Used by:** UCS to know where to read input data from  
**Example:** `market-data-tick-cefi-central-element-323112`

**UCS bucket structure:**
```
market-data-tick-*/
├── raw_tick_data/by_date/day-{YYYY-MM-DD}/
│   ├── data_type-trades/{instrument}.parquet
│   └── data_type-book_snapshot_5/{instrument}.parquet
└── processed_candles/by_date/day-{YYYY-MM-DD}/...
```

---

### 4. `GCS_BUCKET`
**Purpose:** GCS bucket for backtest results output  
**Used by:** Your execution-services to upload results  
**Example:** `execution-store-cefi-central-element-323112`

**Results structure:**
```
execution-store-cefi-central-element-323112/
└── backtest_results/{run_id}/
    ├── summary.json
    ├── orders.parquet
    ├── fills.parquet
    ├── positions.parquet
    └── equity_curve.parquet
```

---

## Why `certs.json` Isn't Referenced

### What UCS Actually Uses

Based on the UCS source code (`cloud_auth_factory.py`), UCS uses:

1. **Service Account JSON** (`gcs-service-account.json`)
   - Standard Google Cloud authentication
   - Used via `GOOGLE_APPLICATION_CREDENTIALS`
   - Works for all GCP services (GCS, BigQuery, Secret Manager)

2. **Application Default Credentials (ADC)**
   - Fallback when no service account file
   - Uses `gcloud auth application-default login`
   - For local development

### What `certs.json` Is For

`certs.json` contains **certificates for Workload Identity Federation** - an advanced Google Cloud feature that:

- Allows authentication from external providers (AWS, Azure, OIDC)
- Uses certificates to verify tokens from external identity providers
- **Not part of standard UCS authentication flow**

**When you'd use it:**
- Multi-cloud scenarios (AWS → GCS, Azure → GCS)
- Workload Identity Pool configuration
- OIDC provider authentication

**Current UCS implementation:**
- ✅ Uses service account keys (standard)
- ✅ Supports Application Default Credentials
- ❌ Does NOT use `certs.json` (not in UCS codebase)

---

## UCS Auto-Detection Features

### 1. GCS FUSE Auto-Detection

UCS automatically detects GCS FUSE mounts - **no code changes needed**:

```python
# UCS checks for FUSE mounts automatically
# No environment variable needed - it just works!
```

**Auto-detected paths:**
- `$GCS_FUSE_MOUNT_PATH` (if set)
- `/mnt/gcs/{bucket}` (Linux)
- `~/gcs/{bucket}` (macOS)
- `/mnt/disks/gcs/{bucket}` (GCE)

### 2. Credentials Auto-Detection (Development Only)

UCS can auto-detect credentials in development mode:

```python
# Searches for:
# - central-element-323112-e35fb0ddafe2.json
# - credentials.json
# - gcs-account.json
# - service-account.json

# In locations:
# - Current directory
# - Parent directories
# - Home directory
```

---

## Your Current Setup (Correct!)

```bash
# .env file
GCP_PROJECT_ID=central-element-323112
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112
GCS_BUCKET=execution-store-cefi-central-element-323112
```

**This is exactly what UCS expects:**
- ✅ `GOOGLE_APPLICATION_CREDENTIALS` → Points to service account JSON
- ✅ UCS will use this for all authentication
- ✅ GCS FUSE auto-detection will work if mounted
- ✅ `certs.json` available but not needed (for future federated identity if required)

---

## Summary

| Variable | What It Does | Used By |
|----------|--------------|---------|
| `GCP_PROJECT_ID` | Identifies GCP project | UCS for all operations |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account auth | UCS (Google Cloud libraries) |
| `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` | Input data bucket | UCS for reading data |
| `GCS_BUCKET` | Output results bucket | Your code for uploading results |
| `certs.json` | Federated identity certs | Not used by UCS (advanced feature) |

**Key Insight from UCS Docs:**
- UCS uses **standard Google Cloud authentication** (service account keys)
- **No `certs.json` needed** for normal operation
- GCS FUSE is **auto-detected** - no code changes needed
- Your setup is **correct** ✅

---

*Based on: https://github.com/IggyIkenna/unified-cloud-services*

