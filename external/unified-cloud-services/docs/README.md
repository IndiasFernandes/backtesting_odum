# Unified Cloud Services

Standalone Python package for cloud operations across the unified trading system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [First-Time Setup](#first-time-setup)
3. [Core Features](#core-features)
4. [Usage Examples](#usage-examples)
5. [CLI Commands](#cli-commands)
6. [Configuration](#configuration)
7. [Package Structure](#package-structure)

---

## Quick Start

```bash
# 1. Install package
pip install -e ./unified-cloud-services

# 2. Setup GCS FUSE for fast I/O (optional but recommended)
ucs-setup

# 3. Verify setup
ucs-status
```

```python
# Query tick data
from unified_cloud_services import create_market_tick_data_client
from datetime import datetime

client = create_market_tick_data_client()
trades = client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)
```

---

## First-Time Setup

### Step 1: Install the Package

```bash
cd unified-cloud-services
pip install -e .
```

This installs:
- Core cloud services (GCS, BigQuery, Secret Manager)
- Domain clients for tick data, candles, instruments, features
- Performance monitoring and observability
- Byte-range streaming (`fsspec`, `gcsfs`)
- CLI tools (`ucs-setup`, `ucs-status`, `ucs-mount`)

### Step 2: GCP Authentication

```bash
# Option A: Service account (recommended for production)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Option B: Personal credentials (for local development)
gcloud auth application-default login
```

### Step 3: GCS FUSE Setup (Optional - for Fast Local I/O)

GCS FUSE mounts GCS buckets as local filesystems for 10-100x faster reads.

```bash
# One command setup (installs gcsfuse + mounts default bucket)
ucs-setup

# Or setup specific bucket
ucs-setup market-data-tick-central-element-323112
```

**What `ucs-setup` does:**
1. Detects your OS (macOS/Linux)
2. Installs gcsfuse via Homebrew (macOS) or apt (Linux)
3. Mounts the tick data bucket
4. Shows you what to add to your shell config

**Manual setup (if automatic fails):**
```bash
# macOS
brew install --cask macfuse
brew install gcsfuse

# Ubuntu/Debian
export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s)
echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update && sudo apt-get install -y gcsfuse
```

**Note:** UCS works without gcsfuse - it's optional for faster local I/O.

### Step 4: Verify Setup

```bash
# Check GCS FUSE status
ucs-status

# Test Python import
python -c "from unified_cloud_services import UnifiedCloudService; print('✅ Ready')"
```

---

## Core Features

### 1. Domain Clients (Data Access)

High-level clients for querying domain data:

| Client | Purpose | Data Location |
|--------|---------|---------------|
| `create_market_tick_data_client()` | Trades, order book snapshots | `market-data-tick` bucket |
| `create_market_candle_data_client()` | Processed candles | `market-data-tick` bucket |
| `create_instruments_client()` | Instrument definitions | `instruments-store` bucket |
| `create_features_client()` | ML features | `features-store` bucket |

### 2. Byte-Range Streaming (Efficient Parquet Reads)

Read only the data you need from large Parquet files:

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget
from datetime import datetime, timedelta

service = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="market-data-tick-central-element-323112",
    bigquery_dataset="market_data",
)

# Read only 5-minute window (not entire 24hr file!)
df = await service.download_from_gcs_streaming(
    target=target,
    gcs_path="tick_data/2023-05-23/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet",
    timestamp_range=(
        datetime(2023, 5, 23, 9, 30),
        datetime(2023, 5, 23, 9, 35),
    ),
    columns=["timestamp", "price", "size"],  # Only needed columns
)
```

**How it works:**
1. Reads only Parquet footer (~64KB) to get metadata
2. Uses row group statistics to find relevant data
3. Downloads only matching row groups (not entire file)
4. **Result:** 70-95% bandwidth reduction for sparse queries

**Use case - Sparse signal loading:**
```python
# Load only 10 signal periods out of 288 (24hr / 5min)
signal_times = [datetime(2023, 5, 23, 9, 30), ...]  # Your 10 signals

for signal_time in signal_times:
    df = await service.download_from_gcs_streaming(
        target=target,
        gcs_path="tick_data/...",
        timestamp_range=(signal_time, signal_time + timedelta(minutes=5)),
    )
    # Process signal...
```

### 3. GCS FUSE Auto-Detection

UCS automatically detects mounted GCS buckets for fastest possible I/O:

```python
from unified_cloud_services import GCSFuseHelper, check_gcsfuse_available

# Check if gcsfuse is available
if check_gcsfuse_available():
    helper = GCSFuseHelper()
    helper.print_status()
```

**Auto-detected mount paths:**
- `$GCS_FUSE_MOUNT_PATH` (environment variable)
- `/mnt/gcs/{bucket}` (Linux standard)
- `~/gcs/{bucket}` (macOS)
- `/mnt/disks/gcs/{bucket}` (GCE)

### 4. Secret Management

```python
from unified_cloud_services import get_secret_with_fallback

# Tries Secret Manager first, falls back to env var
api_key = get_secret_with_fallback(
    secret_name='tardis-api-key',
    project_id='central-element-323112',
    fallback_env_var='TARDIS_API_KEY'
)
```

### 5. Observability & Monitoring

```python
from unified_cloud_services import PerformanceMonitor, MemoryMonitor

# Performance tracking
monitor = PerformanceMonitor()
monitor.start_monitoring(interval=30)
# ... operations ...
monitor.stop_monitoring()

# Memory monitoring
memory = MemoryMonitor(threshold_percent=85.0)
if memory.is_memory_threshold_exceeded():
    print("⚠️ High memory usage")
```

---

## Usage Examples

### Query Tick Data

```python
from unified_cloud_services import create_market_tick_data_client
from datetime import datetime

client = create_market_tick_data_client()

# Get trades
trades = client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)

# Get order book snapshots
book = client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='book_snapshot_5'
)
```

### Query Candles

```python
from unified_cloud_services import create_market_candle_data_client
from datetime import datetime

client = create_market_candle_data_client()
candles = client.get_candles(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    timeframe='15s',
    data_type='trades'
)
```

### Query Instruments

```python
from unified_cloud_services import create_instruments_client

client = create_instruments_client()
instruments = client.get_instruments_for_date(
    date='2023-05-23',
    venue='BINANCE-FUTURES'
)
```

### Low-Level Cloud Operations

```python
from unified_cloud_services import StandardizedDomainCloudService, CloudTarget

target = CloudTarget(
    gcs_bucket="market-data-tick-central-element-323112",
    bigquery_dataset="market_data",
)

service = StandardizedDomainCloudService(domain='market_data', cloud_target=target)

# Upload data
await service.upload_to_gcs(df, gcs_path="my_data/file.parquet")

# Download data
df = await service.download_from_gcs(gcs_path="my_data/file.parquet")
```

---

## CLI Commands

After `pip install -e .`, these commands are available:

| Command | Description |
|---------|-------------|
| `ucs-setup` | Install gcsfuse and mount default bucket |
| `ucs-setup <bucket>` | Install gcsfuse and mount specific bucket |
| `ucs-status` | Show GCS FUSE installation and mount status |
| `ucs-mount <bucket>` | Mount a GCS bucket |
| `ucs-unmount <bucket>` | Unmount a GCS bucket |

```bash
# Examples
ucs-setup                                          # Setup with default bucket
ucs-setup instruments-store-cefi-central-element-323112  # Setup specific bucket
ucs-status                                         # Check status
ucs-mount market-data-tick-central-element-323112  # Mount bucket
ucs-unmount market-data-tick-central-element-323112 # Unmount
```

**Disable auto-check on import:**
```bash
export UCS_SKIP_GCSFUSE_CHECK=1
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `central-element-323112` | GCP project ID |
| `GCS_REGION` | `asia-northeast1` | GCS bucket region |
| `GOOGLE_APPLICATION_CREDENTIALS` | (auto-detect) | Path to service account JSON |
| `GCS_FUSE_MOUNT_PATH` | (auto-detect) | Custom GCS FUSE mount path |
| `UCS_SKIP_GCSFUSE_CHECK` | `0` | Set to `1` to disable import hint |

### GCS Data Paths

| Domain | Bucket | Path Pattern |
|--------|--------|--------------|
| Tick Data | `market-data-tick-*` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-{type}/{instrument}.parquet` |
| Candles | `market-data-tick-*` | `processed_candles/by_date/day-{YYYY-MM-DD}/timeframe-{tf}/data_type-{type}/{instrument}.parquet` |
| Instruments | `instruments-store-*` | `instrument_availability/by_date/day-{YYYY-MM-DD}/instruments.parquet` |
| Features | `features-store-*` | `{feature_type}/by_date/day-{YYYY-MM-DD}/{instrument}.parquet` |

---

## Package Structure

```
unified_cloud_services/
├── core/                    # Core cloud operations
│   ├── unified_cloud_service.py   # Main GCS/BigQuery service
│   ├── gcsfuse_helper.py          # GCS FUSE mounting
│   ├── performance_monitor.py     # Performance tracking
│   ├── memory_monitor.py          # Memory monitoring
│   ├── secret_manager.py          # Secret Manager client
│   └── ...
├── domain/                  # Domain-specific services
│   ├── clients.py                 # Domain clients (tick, candles, instruments)
│   ├── standardized_service.py    # StandardizedDomainCloudService
│   └── validation.py              # Domain validation
├── models/                  # Data models
│   ├── venue_config.py            # Venue mappings
│   └── schemas.py                 # Shared schemas
├── cli.py                   # CLI entry points
└── __init__.py              # Package exports

scripts/
├── setup_gcsfuse.sh         # Shell script for GCS FUSE setup
├── query_buckets_and_datasets/    # Data query utilities
└── create_buckets_and_datasets/   # GCP resource creation
```

---

## Additional Documentation

- **[PATTERNS.md](PATTERNS.md)** - Usage patterns and best practices
- **[DEV_SETUP.md](DEV_SETUP.md)** - Development environment setup
- **[scripts/README.md](../scripts/README.md)** - Script documentation
- **[archive/](archive/)** - Historical migration guides

---

*Last Updated: 2025-12-08*
