# unified-cloud-services Scripts

Utility scripts for GCP resource management and domain data access.

## Directory Structure

```
scripts/
├── create_buckets_and_datasets/   # GCS bucket & BigQuery dataset creation
├── query_buckets_and_datasets/    # Domain data query utilities
├── setup_gcsfuse.sh               # GCS FUSE setup for local dev
└── store_secret.py                # Secret Manager utilities
```

## Quick Start

### Query Domain Data

Query tick data, candles, instruments, or features from GCS:

```bash
# Query raw tick trades
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --data-type trades

# Query book snapshots
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --data-type book_snapshot_5

# Query candles
python scripts/query_buckets_and_datasets/query_domain_data.py candles \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --timeframe 15s \
  --data-type trades

# Query instruments
python scripts/query_buckets_and_datasets/query_domain_data.py instruments \
  --date 2023-05-23 \
  --venue BINANCE-FUTURES

# Save to CSV
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --data-type trades \
  --output trades.csv
```

### Store Secrets

Store secrets in Google Secret Manager:

```bash
# Store a secret
python scripts/store_secret.py --secret-name my-api-key --secret-value "YOUR_KEY"

# Use Application Default Credentials (gcloud auth)
python scripts/store_secret.py --secret-name my-api-key --secret-value "YOUR_KEY" --use-adc
```

### Setup GCS FUSE (Fast Local I/O)

Mount GCS buckets as local filesystems for fast backtesting and development.

**After `pip install -e .` (recommended):**
```bash
# Install gcsfuse and mount default bucket (market-data-tick-central-element-323112)
# Automatically detects macOS vs Linux and installs appropriately
ucs-setup

# Or mount a specific bucket
ucs-setup instruments-store-cefi-central-element-323112

# Check status
ucs-status

# Mount/unmount individually
ucs-mount market-data-tick-central-element-323112
ucs-unmount market-data-tick-central-element-323112
```

**Platform Support:**
- **macOS**: ⚠️ gcsfuse doesn't provide macOS binaries. **Use Docker instead** (recommended) or work without gcsfuse
- **Linux**: Uses apt/yum package manager (Debian/Ubuntu/CentOS/RHEL supported)

**Alternative: Shell script**
```bash
./scripts/setup_gcsfuse.sh market-data-tick-central-element-323112
```

**Python API:**
```python
from unified_cloud_services import (
    GCSFuseHelper,
    check_gcsfuse_available,
    ensure_bucket_mounted,
)

# Check if gcsfuse is installed
if check_gcsfuse_available():
    # Mount a bucket
    success, msg = ensure_bucket_mounted("market-data-tick-central-element-323112")
    print(msg)
else:
    GCSFuseHelper().print_install_instructions()
```

**Docker (containerized):**
```bash
docker compose up -d
docker compose run --rm app bash
```

**Disable auto-check on import:**
```bash
export UCS_SKIP_GCSFUSE_CHECK=1
```

### Create GCP Resources

Create GCS buckets and BigQuery datasets for each domain:

```bash
# Create all domains
./scripts/create_buckets_and_datasets/create_all_domains.sh

# Create specific domain
./scripts/create_buckets_and_datasets/create_instruments_bucket.sh
./scripts/create_buckets_and_datasets/create_market_data_tick_bucket.sh
```

## Domain Data Paths

| Domain | GCS Bucket | Path Pattern |
|--------|------------|--------------|
| Tick Data | `market-data-tick` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-{type}/{instrument}.parquet` |
| Candles | `market-data-tick` | `processed_candles/by_date/day-{YYYY-MM-DD}/timeframe-{tf}/data_type-{type}/{instrument}.parquet` |
| Instruments | `instruments-store` | `by_date/day-{YYYY-MM-DD}/{venue}/instruments.parquet` |
| Features | `features-store` | `{feature_type}/by_date/day-{YYYY-MM-DD}/{instrument}.parquet` |

## Programmatic Usage

```python
from unified_cloud_services import (
    create_market_tick_data_client,
    create_market_candle_data_client,
    create_instruments_client,
    create_features_client,
)
from datetime import datetime

# Tick data
tick_client = create_market_tick_data_client()
trades_df = tick_client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
    data_type="trades"
)

# Candles
candle_client = create_market_candle_data_client()
candles_df = candle_client.get_candles(
    date=datetime(2023, 5, 23),
    instrument_id="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
    timeframe="15s",
    data_type="trades"
)

# Instruments
instruments_client = create_instruments_client()
instruments_df = instruments_client.get_instruments_for_date(
    date="2023-05-23",
    venue="BINANCE-FUTURES"
)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `central-element-323112` | GCP project ID |
| `GCS_REGION` | `asia-northeast1` | GCS bucket region |
| `MARKET_DATA_GCS_BUCKET` | `market-data-tick` | Market data bucket |
| `INSTRUMENTS_GCS_BUCKET` | `instruments-store` | Instruments bucket |
| `FEATURES_GCS_BUCKET` | `features-store` | Features bucket |
| `GCS_FUSE_MOUNT_PATH` | (auto-detected) | Custom GCS FUSE mount path |







