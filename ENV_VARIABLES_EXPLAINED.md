# Environment Variables Explained

## The 4 Main Environment Variables

### 1. `GCP_PROJECT_ID`
**Purpose:** Your Google Cloud Platform project identifier  
**Example:** `central-element-323112`  
**Usage:** Identifies which GCP project to use for all operations  
**Required:** ✅ Yes

```bash
GCP_PROJECT_ID=central-element-323112
```

---

### 2. `GOOGLE_APPLICATION_CREDENTIALS`
**Purpose:** Path to service account JSON key file for authentication  
**Example:** `.secrets/gcs/gcs-service-account.json`  
**Usage:** Google Cloud libraries automatically use this file for authentication  
**Required:** ✅ Yes (unless using Workload Identity Federation)

```bash
# Local development
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json

# Docker
GOOGLE_APPLICATION_CREDENTIALS=/app/.secrets/gcs/gcs-service-account.json
```

**What it does:**
- Points to your service account key file (`gcs-service-account.json`)
- Used by Google Cloud client libraries for authentication
- Standard method for service-to-service authentication

---

### 3. `UNIFIED_CLOUD_SERVICES_GCS_BUCKET`
**Purpose:** Main GCS bucket for market data and instruments  
**Example:** `market-data-tick-cefi-central-element-323112`  
**Usage:** Where UCS reads input data from (trades, book snapshots, instruments)  
**Required:** ✅ Yes

```bash
UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112
```

**What it's used for:**
- Downloading instrument definitions
- Downloading market tick data (trades, book snapshots)
- Primary data source bucket

---

### 4. `GCS_BUCKET`
**Purpose:** GCS bucket for backtest results output  
**Example:** `execution-store-cefi-central-element-323112`  
**Usage:** Where backtest results are uploaded (summary.json, Parquet files)  
**Required:** ✅ Yes

```bash
GCS_BUCKET=execution-store-cefi-central-element-323112
```

**What it's used for:**
- Uploading backtest results (`summary.json`)
- Uploading Parquet outputs (`orders.parquet`, `fills.parquet`, etc.)
- Storing execution logs and metadata

---

## Why `certs.json` Isn't Referenced

### What UCS Actually Uses (Based on Official Docs)

According to the [unified-cloud-services repository](https://github.com/IggyIkenna/unified-cloud-services), UCS uses:

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

### Your Current Setup

Your current setup uses **service account authentication** (correct!):
- ✅ `gcs-service-account.json` → Standard service account key
- ✅ `GOOGLE_APPLICATION_CREDENTIALS` → Points to service account key
- ✅ UCS will use this automatically
- ⚠️ `certs.json` → Available but not used by UCS (for future federated identity if needed)

### If You Want to Use `certs.json`

If you need to use federated identity instead of service account keys, you would need:

```bash
# Additional environment variables for federated identity
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/certs.json
# OR
GOOGLE_CLOUD_CERTIFICATES_PATH=.secrets/gcs/certs.json
GOOGLE_CLOUD_WORKLOAD_IDENTITY_POOL=your-pool-id
GOOGLE_CLOUD_WORKLOAD_IDENTITY_PROVIDER=your-provider-id
```

However, **most applications use service account keys** (`gcs-service-account.json`) because:
- ✅ Simpler setup
- ✅ Works out of the box
- ✅ Standard authentication method
- ✅ Sufficient for most use cases

---

## Summary

| Variable | Points To | Purpose | Required |
|----------|-----------|---------|----------|
| `GCP_PROJECT_ID` | Project ID string | Identify GCP project | ✅ Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | `gcs-service-account.json` | Authentication | ✅ Yes |
| `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` | Bucket name | Input data source | ✅ Yes |
| `GCS_BUCKET` | Bucket name | Output results | ✅ Yes |
| `certs.json` | N/A (not referenced) | Federated identity (optional) | ❌ No |

---

## Your Current Configuration

```bash
# .env file
GCP_PROJECT_ID=central-element-323112
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112
GCS_BUCKET=execution-store-cefi-central-element-323112
```

**Authentication Method:** Service Account Key (`gcs-service-account.json`)  
**Federated Identity:** Not used (`certs.json` available but not referenced)

---

## When to Use `certs.json`

Consider using `certs.json` if:
- 🔐 You need federated identity authentication
- ☁️ Authenticating from AWS/Azure workloads
- 🔒 You want to avoid long-lived service account keys
- 🌐 Using OIDC providers for authentication

For most use cases, **service account keys are sufficient** and simpler to set up.

---

*Your current setup is correct - `certs.json` is available for future use if needed, but service account authentication is the standard approach.*

