# Environment Configuration Setup

## Quick Start

### 1. Create .env File

```bash
# Option A: Use setup script
bash backend/scripts/setup_env.sh

# Option B: Manual copy
cp .env.example .env
```

### 2. Edit .env File

Open `.env` and fill in your values:

```bash
nano .env
# or
vim .env
```

### 3. Required Variables

```bash
# Google Cloud Project ID
GCP_PROJECT_ID=your-project-id

# Path to service account key file (default: .secrets/gcs/gcs-service-account.json)
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json

# Main GCS bucket for market data/instruments
UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112

# GCS bucket for backtest results
GCS_BUCKET=execution-store-cefi-central-element-323112
```

**Note:** Credential files are stored in `.secrets/gcs/`:
- `gcs-service-account.json` - GCS service account credentials
- `certs.json` - Certificate files (if needed)

### 4. Optional Variables

```bash
# Use direct GCS access (instead of FUSE mount)
UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=false

# Enable GCS FUSE mounting
USE_GCS_FUSE=false
GCS_FUSE_BUCKET=your-bucket-name
```

---

## Environment Variables Reference

### Google Cloud Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GCP_PROJECT_ID` | Yes | Your GCP project ID | `central-element-323112` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to service account JSON key | `.secrets/gcs/gcs-service-account.json` |

### Bucket Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` | Yes | Main bucket for market data/instruments | `market-data-tick-cefi-central-element-323112` |
| `GCS_BUCKET` | Yes | Bucket for backtest results | `execution-store-cefi-central-element-323112` |
| `INSTRUMENTS_BUCKET` | No | Instruments bucket (if different) | `instruments-store-cefi-central-element-323112` |
| `MARKET_DATA_BUCKET` | No | Market data bucket (if different) | `market-data-tick-cefi-central-element-323112` |
| `RESULTS_BUCKET` | No | Results bucket (if different) | `execution-store-cefi-central-element-323112` |

### UCS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS` | No | `false` | Use direct GCS access (not FUSE) |
| `UNIFIED_CLOUD_LOCAL_PATH` | No | `/app/data_downloads` | Local path for data (FUSE mount) |
| `UNIFIED_CLOUD_SERVICES_USE_PARQUET` | No | `true` | Use Parquet format |
| `DATA_CATALOG_PATH` | No | `/app/backend/data/parquet` | NautilusTrader catalog path |

### GCS FUSE Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_GCS_FUSE` | No | `false` | Enable GCS FUSE mounting |
| `GCS_FUSE_BUCKET` | No | - | Bucket name for FUSE mount |
| `GCS_SERVICE_ACCOUNT_KEY` | No | - | Service account key (if different) |

---

## Docker Configuration

For Docker containers, you can either:

### Option 1: Use .env file (Recommended)

```bash
# Create .env file
cp .env.example .env
# Edit .env with your values

# Docker Compose will automatically load .env
docker-compose up -d
```

### Option 2: Mount service account key

```yaml
# In docker-compose.yml
volumes:
  - ./gcs-key.json:/app/gcs-key.json:ro
environment:
  - GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
```

---

## Security Notes

⚠️ **Important:**
- `.env` file is in `.gitignore` - **DO NOT commit it**
- `.env.example` is safe to commit (no secrets)
- Keep service account keys secure
- Use least-privilege IAM roles

---

## Testing Configuration

After setting up `.env`, test the configuration:

```bash
# Test UCS connection
python3 backend/scripts/test_ucs_connection.py

# Test with specific buckets from .env
python3 backend/scripts/test_ucs_connection.py \
  --bucket $GCS_BUCKET \
  --instruments-bucket $INSTRUMENTS_BUCKET \
  --market-data-bucket $MARKET_DATA_BUCKET
```

---

## Troubleshooting

### .env file not found
```bash
# Create from template
cp .env.example .env
```

### Service account key not found
```bash
# Check if credential file exists in .secrets
ls -la .secrets/gcs/gcs-service-account.json

# Verify path in .env file
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS

# For Docker, use absolute path
export GOOGLE_APPLICATION_CREDENTIALS=/app/.secrets/gcs/gcs-service-account.json
```

### Bucket access denied
- Verify service account has Storage Object Viewer/Admin role
- Check bucket name is correct
- Verify project ID matches

---

*See `.env.example` for complete template with all options*

