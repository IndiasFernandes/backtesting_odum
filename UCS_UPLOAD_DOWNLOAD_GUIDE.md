# UCS Upload & Download Guide

Based on the [unified-cloud-services repository](https://github.com/IggyIkenna/unified-cloud-services), here's how uploads and downloads work:

---

## Core Concepts

### CloudTarget - Runtime Bucket Configuration

UCS uses `CloudTarget` to specify which bucket/dataset to use for each operation:

```python
from unified_cloud_services import CloudTarget

target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",  # Which bucket
    bigquery_dataset="market_data",                              # Which BigQuery dataset
    project_id="central-element-323112",                         # Which GCP project
    region="asia-northeast1"                                     # Which region
)
```

**Key Point:** You can use different buckets for different operations - no hardcoding!

---

## Download Operations

### 1. Full File Download

**Method:** `download_from_gcs()`

**Use Case:** Download entire files (instruments, small datasets)

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget

ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="instruments-store-cefi-central-element-323112",
    bigquery_dataset="instruments_data"
)

# Download instrument definitions (full file, ~82 KB)
df = await ucs.download_from_gcs(
    target=target,
    gcs_path="instrument_availability/by_date/day-2023-05-23/instruments.parquet",
    format="parquet"
)
```

**What happens:**
1. Downloads entire file from GCS
2. Converts to DataFrame (or bytes/string based on format)
3. Returns data in memory

**Performance:**
- Small files (< 100 MB): Fast, simple
- Large files (> 100 MB): Slower, uses more memory

---

### 2. Byte-Range Streaming Download

**Method:** `download_from_gcs_streaming()`

**Use Case:** Download only specific time windows from large Parquet files

```python
from datetime import datetime, timezone

ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",
    bigquery_dataset="market_tick_data"
)

# Stream only 5-minute window (instead of entire 48 MB file!)
start_ts = datetime(2023, 5, 23, 0, 0, 0, tzinfo=timezone.utc)
end_ts = datetime(2023, 5, 23, 0, 5, 0, tzinfo=timezone.utc)

df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path="raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
    timestamp_range=(start_ts, end_ts),
    timestamp_column="ts_event",  # Column with timestamps
    use_byte_range=True
)
```

**What happens:**
1. Downloads only Parquet footer (~64 KB) to get metadata
2. Uses row group statistics to find matching time range
3. Downloads only relevant row groups (not entire file!)
4. Applies timestamp filter
5. Returns filtered DataFrame

**Performance:**
- **70-95% bandwidth reduction** for sparse queries
- Example: 48 MB file → only 0.1 MB downloaded for 5-min window

**How it works:**
```
Full File: 48 MB, 3.2M rows
    ↓
Read Footer: ~64 KB (metadata only)
    ↓
Check Row Group Stats: Find matching time ranges
    ↓
Download Only Matching Row Groups: ~0.1 MB (0.13% of file)
    ↓
Result: 4,053 rows instead of 3.2M rows
```

---

### 3. Column Projection (Reduce Memory)

**Use Case:** Only need specific columns

```python
# Download with column projection - only fetch needed columns
df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path="...",
    timestamp_range=(start_ts, end_ts),
    timestamp_column="ts_event",
    columns=["ts_event", "price", "size"],  # Only these columns
    use_byte_range=True
)
```

**Benefits:**
- Reduces memory usage
- Faster downloads
- Less data transfer

---

### 4. GCS FUSE Auto-Detection

**UCS automatically detects FUSE mounts** - no code changes needed!

```python
# UCS checks these paths automatically:
# 1. $GCS_FUSE_MOUNT_PATH (if set)
# 2. /mnt/gcs/{bucket}
# 3. /gcs/{bucket}
# 4. ~/gcs/{bucket}
# 5. /mnt/disks/gcs/{bucket} (GCE)

# If FUSE mount found, reads directly from local filesystem
# If not found, uses GCS API
```

**Performance:**
- FUSE mount: **10-100x faster** than API calls
- Same code works for both!

---

## Upload Operations

### 1. Upload DataFrame to GCS

**Method:** `upload_to_gcs()`

**Use Case:** Upload backtest results, Parquet files

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget
import pandas as pd

ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="execution-store-cefi-central-element-323112",
    bigquery_dataset="execution"
)

# Upload summary JSON
summary = {
    "run_id": "BT-20231223-001",
    "status": "COMPLETED",
    "pnl": {"net_pnl": 1200.00}
}

await ucs.upload_to_gcs(
    target=target,
    gcs_path="backtest_results/BT-20231223-001/summary.json",
    data=summary,
    format="json"
)

# Upload Parquet file (orders)
orders_df = pd.DataFrame([...])  # Your orders data

await ucs.upload_to_gcs(
    target=target,
    gcs_path="backtest_results/BT-20231223-001/orders.parquet",
    data=orders_df,
    format="parquet"
)
```

**Supported Formats:**
- `parquet` - DataFrame → Parquet file
- `csv` - DataFrame → CSV file
- `json` - Dict/DataFrame → JSON file
- `pickle` - Python objects → Pickle file
- `joblib` - ML models → Joblib file
- `bytes` - Raw bytes
- `text` - String

---

## Bucket Configuration

### Input Buckets (Download)

| Data Type | Bucket Name | Path Pattern |
|-----------|-------------|--------------|
| **Instruments** | `instruments-store-cefi-central-element-323112` | `instrument_availability/by_date/day-{YYYY-MM-DD}/instruments.parquet` |
| **Market Tick Data** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-trades/{INSTRUMENT}.parquet` |
| **Book Snapshots** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-book_snapshot_5/{INSTRUMENT}.parquet` |

### Output Bucket (Upload)

| Data Type | Bucket Name | Path Pattern |
|-----------|-------------|--------------|
| **Backtest Results** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/summary.json`<br>`backtest_results/{run_id}/orders.parquet`<br>`backtest_results/{run_id}/fills.parquet`<br>`backtest_results/{run_id}/positions.parquet`<br>`backtest_results/{run_id}/equity_curve.parquet` |

---

## Complete Examples

### Example 1: Download Instruments

```python
import asyncio
from unified_cloud_services import UnifiedCloudService, CloudTarget

async def load_instruments(date: str):
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="instruments-store-cefi-central-element-323112",
        bigquery_dataset="instruments_data"
    )
    
    # Full file download (~82 KB, ~3s)
    df = await ucs.download_from_gcs(
        target=target,
        gcs_path=f"instrument_availability/by_date/day-{date}/instruments.parquet",
        format="parquet"
    )
    
    # Filter to specific instrument
    inst = df[df["instrument_key"] == "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"]
    return inst

# Usage
instruments = asyncio.run(load_instruments("2023-05-23"))
```

---

### Example 2: Download Tick Data (Full File)

```python
async def load_full_day():
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="market-data-tick-cefi-central-element-323112",
        bigquery_dataset="market_tick_data"
    )
    
    # Full file: 48 MB, 3.2M rows, ~7s
    df = await ucs.download_from_gcs(
        target=target,
        gcs_path="raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
        format="parquet"
    )
    return df
```

---

### Example 3: Download Tick Data (Byte-Range Streaming)

```python
from datetime import datetime, timezone

async def stream_5min_window():
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="market-data-tick-cefi-central-element-323112",
        bigquery_dataset="market_tick_data"
    )
    
    # Stream only 5-minute window: 4,053 rows (0.13% of file), ~5s
    start_ts = datetime(2023, 5, 23, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = datetime(2023, 5, 23, 0, 5, 0, tzinfo=timezone.utc)
    
    df = await ucs.download_from_gcs_streaming(
        target=target,
        gcs_path="raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
        timestamp_range=(start_ts, end_ts),
        timestamp_column="ts_event",
        use_byte_range=True
    )
    return df  # Only 4,053 rows instead of 3.2M
```

---

### Example 4: Upload Backtest Results

```python
async def save_backtest_results(run_id: str, summary: dict, fills_df, equity_df):
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="execution-store-cefi-central-element-323112",
        bigquery_dataset="execution"
    )
    
    # Upload summary JSON
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f"backtest_results/{run_id}/summary.json",
        data=summary,
        format="json"
    )
    
    # Upload fills Parquet
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f"backtest_results/{run_id}/fills.parquet",
        data=fills_df,
        format="parquet"
    )
    
    # Upload equity curve Parquet
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f"backtest_results/{run_id}/equity_curve.parquet",
        data=equity_df,
        format="parquet"
    )
```

---

## Performance Comparison

| Method | File Size | Rows Downloaded | Time | Memory | Data Reduction |
|--------|-----------|-----------------|------|--------|----------------|
| **Full file download** | 48 MB | 3,213,051 | 7.0s | 548 MB | 100% |
| **5-min streaming** | 48 MB → 0.1 MB | 4,053 | 5.3s | <1 MB | **0.13%** |
| **5-min + projection** | 48 MB → 0.05 MB | 4,053 | 2.8s | <0.5 MB | **0.1%** |
| **1-hour streaming** | 48 MB → 1.3 MB | 89,869 | 3.4s | ~15 MB | **2.8%** |

**Key Insight:** For sparse signal-driven backtesting, only load tick data for intervals where signals change direction. This reduces I/O by 90-99%.

---

## How UCS Chooses Download Method

```
┌─────────────────────────────────────┐
│  download_from_gcs_streaming()      │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Is .parquet file?    │
    └──┬───────────────┬───┘
       │               │
    Yes│               │No
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────────┐
│ Check FUSE  │  │ Full download   │
│ mount?      │  │ (download_from_ │
└──┬───────┬──┘  │  gcs)           │
   │       │     └─────────────────┘
Yes│       │No
   │       │
   ▼       ▼
┌──────┐ ┌──────────────────┐
│ Read │ │ Check byte-range │
│ from │ │ streaming?       │
│ FUSE │ └──┬────────────┬───┘
└──────┘    │            │
         Yes│            │No
            │            │
            ▼            ▼
    ┌──────────────┐ ┌──────────────┐
    │ Byte-range   │ │ Full download│
    │ (fsspec)     │ │ (GCS API)    │
    └──────────────┘ └──────────────┘
```

---

## Integration Pattern for execution-services

### Step 1: Create UCS Service Wrapper

```python
# backend/services/ucs_service.py
from unified_cloud_services import UnifiedCloudService, CloudTarget
import os

class UCSService:
    def __init__(self):
        self.ucs = UnifiedCloudService()
    
    def get_instruments_target(self) -> CloudTarget:
        return CloudTarget(
            gcs_bucket=os.getenv("INSTRUMENTS_BUCKET", "instruments-store-cefi-central-element-323112"),
            bigquery_dataset="instruments_data"
        )
    
    def get_market_data_target(self) -> CloudTarget:
        return CloudTarget(
            gcs_bucket=os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET", "market-data-tick-cefi-central-element-323112"),
            bigquery_dataset="market_tick_data"
        )
    
    def get_results_target(self) -> CloudTarget:
        return CloudTarget(
            gcs_bucket=os.getenv("GCS_BUCKET", "execution-store-cefi-central-element-323112"),
            bigquery_dataset="execution"
        )
    
    async def download_instruments(self, date: str):
        target = self.get_instruments_target()
        return await self.ucs.download_from_gcs(
            target=target,
            gcs_path=f"instrument_availability/by_date/day-{date}/instruments.parquet",
            format="parquet"
        )
    
    async def download_tick_data(
        self,
        date: str,
        instrument: str,
        data_type: str = "trades",
        start_ts=None,
        end_ts=None,
        use_streaming=True
    ):
        target = self.get_market_data_target()
        gcs_path = f"raw_tick_data/by_date/day-{date}/data_type-{data_type}/{instrument}.parquet"
        
        if use_streaming and start_ts and end_ts:
            return await self.ucs.download_from_gcs_streaming(
                target=target,
                gcs_path=gcs_path,
                timestamp_range=(start_ts, end_ts),
                timestamp_column="ts_event",
                use_byte_range=True
            )
        else:
            return await self.ucs.download_from_gcs(
                target=target,
                gcs_path=gcs_path,
                format="parquet"
            )
    
    async def upload_result(self, run_id: str, filename: str, data, format="json"):
        target = self.get_results_target()
        gcs_path = f"backtest_results/{run_id}/{filename}"
        return await self.ucs.upload_to_gcs(
            target=target,
            gcs_path=gcs_path,
            data=data,
            format=format
        )
```

---

## Key Takeaways

1. **CloudTarget specifies bucket** - No hardcoding, runtime configuration
2. **Byte-range streaming** - Only downloads what you need (90-99% reduction)
3. **FUSE auto-detection** - Works with mounts automatically (10-100x faster)
4. **Multiple formats** - Supports Parquet, JSON, CSV, Pickle, Joblib
5. **Async operations** - All methods are async for performance

---

## Next Steps for Integration

1. ✅ Create `UCSService` wrapper (see pattern above)
2. ✅ Update `backtest_engine.py` to use UCS for data loading
3. ✅ Update `results.py` to use UCS for uploading results
4. ✅ Test with actual buckets

---

*Based on: https://github.com/IggyIkenna/unified-cloud-services*

